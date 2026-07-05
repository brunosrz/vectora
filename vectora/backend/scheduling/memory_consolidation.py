"""Background Memory Consolidation (FASE 4.3).

Job periódico que lê as últimas 10 threads do usuário, sintetiza via LLM
e atualiza ``~/.vectora/AGENTS.md``. O arquivo é injetado automaticamente
no contexto do agente por ``_agents_md_paths()`` em ``agent_factory.py``.

Operação best-effort: qualquer falha é registrada em log e ignorada
para não impactar o fluxo principal.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_MAX_THREADS = 10
_MSG_PREVIEW_CHARS = 400

_PROMPT_TEMPLATE = """\
Você é um assistente que sintetiza memória de conversas passadas.

Abaixo estão os resumos das últimas conversas do usuário:

{threads_text}

Com base nessas conversas, escreva um resumo conciso (máx. 400 palavras)
sobre o que o usuário está construindo, suas preferências técnicas e
os principais aprendizados. Use bullet points. Escreva em português.
Inclua apenas informações factuais e úteis para o futuro — sem repetição.
"""


# ---------------------------------------------------------------------------
# Helpers internos (mockáveis em testes)
# ---------------------------------------------------------------------------


def _agents_md_path() -> Path:
    return Path.home() / ".vectora" / "AGENTS.md"


async def _fetch_recent_threads(
    user_id: str,
) -> list[list[tuple[str, str]]]:
    """Retorna as últimas _MAX_THREADS threads como lista de (role, text) pairs."""
    try:
        from backend.api.handlers.threads import _get_db

        db = await _get_db()
        rows = await db.execute_fetchall(
            "SELECT thread_id FROM vectora_sessions WHERE user_id = ? "
            "ORDER BY updated_at DESC LIMIT ?",
            (user_id, _MAX_THREADS),
        )
        if not rows:
            return []

        from backend.services.agent_factory import aget_thread_messages

        threads = []
        for row in rows:
            thread_id = row[0]
            try:
                messages = await aget_thread_messages(thread_id)
                if messages:
                    threads.append(messages)
            except Exception:
                logger.debug("memory_consolidation: falha ao ler thread=%s", thread_id)
        return threads
    except Exception:
        logger.exception("memory_consolidation: _fetch_recent_threads falhou")
        return []


async def _invoke_llm(prompt: str) -> Any:
    """Invoca o LLM padrão com o prompt de consolidação."""
    from langchain_core.messages import HumanMessage

    from backend.services.utils import load_llm

    llm = load_llm()
    return await llm.ainvoke([HumanMessage(content=prompt)])


# ---------------------------------------------------------------------------
# Funções públicas (testáveis)
# ---------------------------------------------------------------------------


def _build_consolidation_prompt(
    threads: list[list[tuple[str, str]]],
) -> str:
    """Constrói o prompt de síntese a partir de uma lista de threads."""
    if not threads:
        return _PROMPT_TEMPLATE.format(threads_text="(sem conversas recentes)")

    parts: list[str] = []
    for i, messages in enumerate(threads, 1):
        lines: list[str] = []
        for role, text in messages:
            prefix = "Usuário" if role == "human" else "Agente"
            truncated = text[:_MSG_PREVIEW_CHARS]
            if len(text) > _MSG_PREVIEW_CHARS:
                truncated += "…"
            lines.append(f"{prefix}: {truncated}")
        parts.append(f"--- Conversa {i} ---\n" + "\n".join(lines))

    return _PROMPT_TEMPLATE.format(threads_text="\n\n".join(parts))


def _parse_llm_output(raw: str) -> str:
    """Remove markdown fences e normaliza espaços."""
    text = raw.strip()
    if not text:
        return ""
    # Remove ``` fences (```markdown, ```md, etc.)
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove primeira linha (```...`) e última (```)
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner).strip()
    return text


async def consolidate_memory(user_id: str) -> None:
    """Sintetiza as últimas threads e atualiza ~/.vectora/AGENTS.md.

    Best-effort: qualquer exceção é capturada e logada sem propagar.
    """
    try:
        threads = await _fetch_recent_threads(user_id)
        if not threads:
            logger.debug("memory_consolidation: sem threads para user=%s", user_id)
            return

        prompt = _build_consolidation_prompt(threads)
        response = await _invoke_llm(prompt)
        summary = _parse_llm_output(getattr(response, "content", "") or "")

        if not summary:
            logger.warning(
                "memory_consolidation: LLM retornou conteúdo vazio user=%s", user_id
            )
            return

        path = _agents_md_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        header = "# Memória do Agente\n\n_Atualizado automaticamente por memory consolidation._\n\n"
        path.write_text(header + summary + "\n", encoding="utf-8")
        logger.info(
            "memory_consolidation: AGENTS.md atualizado user=%s threads=%d",
            user_id,
            len(threads),
        )
    except Exception:
        logger.exception("memory_consolidation: falha inesperada user=%s", user_id)


async def run_consolidation_for_all_users() -> None:
    """Dispara consolidação para todos os usuários ativos (últimos 7 dias).

    Chamado pelo scheduler a cada 6 horas.
    """
    try:
        from backend.api.handlers.threads import _get_db

        db = await _get_db()
        rows = await db.execute_fetchall(
            "SELECT DISTINCT user_id FROM vectora_sessions "
            "WHERE updated_at >= datetime('now', '-7 days') AND user_id IS NOT NULL",
        )
        users = [r[0] for r in rows if r[0]]
        logger.info("memory_consolidation: iniciando para %d usuários", len(users))
        for user_id in users:
            await consolidate_memory(user_id)
    except Exception:
        logger.exception("memory_consolidation: run_consolidation_for_all_users falhou")
