"""Remember — learning loop do agente.

``learn_from_session`` destila o transcript da thread atual em skills e
fatos duráveis, mas NÃO persiste nada — só devolve a proposta pro agente
apresentar ao usuário. ``install_learned_skill`` (skills) e
``save_learned_fact`` (fatos) são quem persiste, ambas em
``_REQUIRE_APPROVAL`` (``backend/services/middleware.py``) — pausam para
aprovação HITL antes de gravar, mesmo tratamento de
``terminal``/``file_write``. ``save_learned_fact`` reaproveita a escrita de
``save_memory`` (``metadata={"tag": "user_model"}``), sem duplicar o
mecanismo de persistência de memória — a diferença é só a pausa HITL, que
``save_memory`` direto (uso explícito do usuário) não tem. As duas, uma vez
aprovadas, espelham o resultado como artifact (``create_artifact``) — fica
visível na aba Plan em vez de sumir depois do diff de aprovação.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from backend.services.learning import dedupe_skill_drafts, distill_transcript

logger = logging.getLogger(__name__)


@tool(
    extras={
        "destructive": False,
        "category": "memory",
        "icon": "sparkles",
    }
)
async def learn_from_session(
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Analisa o transcript da thread atual e propõe skills reutilizáveis
    e fatos duráveis a aprender — não grava nada ainda.

    Devolva a proposta ao usuário para revisão antes de chamar
    ``install_learned_skill`` (por skill) e ``save_memory`` (por fato),
    que exigem confirmação explícita. Se não houver nada de reaproveitável
    no transcript, a lista vem vazia — isso é um resultado válido, não um
    erro; não force a criação de uma skill genérica.
    """
    try:
        configurable = (config or {}).get("configurable") or {}
        thread_id = configurable.get("thread_id", "")
        user_id = configurable.get("user_id", "local")

        if not thread_id:
            return json.dumps(
                {"status": "error", "error": "thread_id ausente no config"}
            )

        from backend.services import agent_factory

        pairs = await agent_factory.aget_thread_messages(thread_id)
        transcript = "\n".join(f"{role}: {text}" for role, text, _ in pairs)

        result = await distill_transcript(transcript)

        from backend.workspace.skills import list_skills

        existing_names = {s.name for s in list_skills(user_id)}
        skills = dedupe_skill_drafts(result.skills, existing_names)

        return json.dumps(
            {
                "status": "ok",
                "skills": [s.model_dump() for s in skills],
                "facts": result.facts,
            }
        )
    except Exception as exc:
        logger.exception("learn_from_session: falha ao destilar transcript")
        return json.dumps({"status": "error", "error": str(exc)})


@tool(
    extras={
        "invalidates": ["skills"],
        "destructive": True,
        "category": "memory",
        "icon": "sparkles",
    }
)
async def install_learned_skill(
    name: str,
    description: str,
    content: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Grava uma skill proposta por ``learn_from_session`` como
    ``SKILL.md`` — pausa para aprovação do usuário antes de executar
    (mesmo tratamento HITL de ``terminal``/``file_write``).

    Args:
        name: Nome curto da skill (vira o slug da pasta).
        description: Quando usar essa skill.
        content: Passo a passo em Markdown (corpo do SKILL.md).
    """
    try:
        configurable = (config or {}).get("configurable") or {}
        user_id = configurable.get("user_id", "local")

        from backend.workspace.skills import install_skill_from_content

        skill = install_skill_from_content(user_id, name, description, content)
        logger.info("learning: skill instalada id=%s user=%s", skill.id, user_id)
        _mirror_to_plan_tab("skill_learned", name, description, content, config)
        await _resolve_remember_pending(config)
        return json.dumps({"status": "installed", "skill_id": skill.id})
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc)})


async def _resolve_remember_pending(config: RunnableConfig | None) -> None:
    """Limpa a proposta pendente do gatilho automático (WB-5) — instalar uma
    skill ou salvar um fato aprendido é o sinal de que a proposta foi
    resolvida, libera um novo gatilho automático a partir daqui."""
    try:
        thread_id = str((config or {}).get("configurable", {}).get("thread_id", ""))
        if not thread_id:
            return
        from backend.api.handlers.threads import set_remember_pending

        await set_remember_pending(thread_id, False)
    except Exception:
        logger.warning(
            "learning: falha ao limpar remember_pending (não bloqueia)",
            exc_info=True,
        )


def _mirror_to_plan_tab(
    artifact_type: str,
    title: str,
    description: str,
    content: str,
    config: RunnableConfig | None,
) -> None:
    """Espelha uma skill/fato aprovado como artifact — aparece na aba Plan
    em vez de sumir depois do diff de aprovação. Best-effort: falha aqui
    nunca desfaz a gravação já concluída (skill/fato já persistidos)."""
    try:
        from backend.tools.fs import create_artifact

        body = f"{description}\n\n---\n\n{content}" if description else content
        create_artifact.invoke(
            {
                "artifact_type": artifact_type,
                "title": title,
                "content": body,
                "config": config,
            }
        )
    except Exception:
        logger.warning(
            "learning: falha ao espelhar artifact na aba Plan (não bloqueia)",
            exc_info=True,
        )


@tool(
    extras={
        "invalidates": ["memory"],
        "destructive": True,
        "category": "memory",
        "icon": "sparkles",
    }
)
async def save_learned_fact(
    fact: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Grava um fato durável proposto por ``learn_from_session`` na memória
    do usuário — pausa para aprovação antes de executar (mesmo tratamento
    HITL de ``install_learned_skill``). Distinto de ``save_memory`` direto
    (uso explícito do usuário, sem pausa): este é o caminho específico para
    fatos que o Remember descobriu sozinho.

    Args:
        fact: O fato durável a lembrar, em uma frase.
    """
    try:
        from backend.tools.memory import save_memory

        key = f"learned-fact-{abs(hash(fact)) % 10**8}"
        await save_memory.ainvoke(
            {
                "key": key,
                "content": fact,
                "config": config,
                "metadata": {"tag": "user_model", "source": "learn_from_session"},
            }
        )
        logger.info("learning: fato aprendido salvo key=%s", key)
        _mirror_to_plan_tab("fact_learned", fact[:80], "", fact, config)
        await _resolve_remember_pending(config)
        return json.dumps({"status": "saved", "key": key})
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc)})
