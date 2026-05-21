"""Orchestrator — Agent generalista que responde diretamente ou delega a sub-agents.

O orchestrator É o agent principal do Vectora. Ele pode:

  1. **Responder diretamente** — saudações, perguntas de conhecimento, síntese,
     identidade, síntese RAG — sem rotear para outro agent (economiza 1 LLM call).

  2. **Delegar com task query** — quando precisa de especialista, cria uma instrução
     clara e concisa para o sub-agent, em vez de apenas passar o histórico bruto.

  3. **Criar artifacts** — quando o usuário pede planos, specs, task lists, guias
     ou outros documentos estruturados, usa a tool create_artifact para salvar em
     ~/.vectora/artifacts/{session_id}/ em vez de responder apenas com texto.

Sub-agents disponíveis para delegação:
  "coder"  → Coder Agent (filesystem, terminal, git, implementação)
  "search" → Search Agent (web search em tempo real, fetch URL)
  "rag"    → RAG Subgraph (busca semântica na base de conhecimento indexada)

Contexto enviado ao LLM:
  - SystemMessage: contexto do projeto (AGENTS.md, CLAUDE.md, GEMINI.md) — primeira vez
  - SystemMessage: prompt de instrução
  - SystemMessage: bloco de contexto (session_id, tool chain, artifacts)
  - Últimas 5 HumanMessages
  - Últimas 2 AIMessages sem tool_calls (respostas finais, não intermediárias)
"""

from __future__ import annotations

import contextlib
import logging
from itertools import groupby
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.constants import END
from langgraph.types import Command
from pydantic import BaseModel

from vectora.agents._identity import VECTORA_IDENTITY

if TYPE_CHECKING:
    from vectora.state import State

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema de saída estruturada
# ---------------------------------------------------------------------------

AgentName = Literal["coder", "search", "rag"]


class OrchestratorDecision(BaseModel):
    """Decisão do orchestrator: responder inline ou delegar a sub-agent."""

    action: Literal["respond", "delegate"]
    response: str | None = None
    """Resposta completa em markdown (somente quando action == 'respond')."""

    delegate_to: AgentName | None = None
    """Sub-agent alvo (somente quando action == 'delegate')."""

    task_query: str | None = None
    """Instrução clara e concisa para o sub-agent — 1 a 3 frases diretas.
    Deve capturar intent + contexto relevante sem precisar do histórico completo."""

    reason: str
    """Uma frase curta explicando a decisão — útil para logs e debug."""


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_ORCHESTRATOR_PROMPT = f"""{VECTORA_IDENTITY}

---

## Seu Papel — Orchestrator

Você é o **Orchestrator** do Vectora — o agent principal e único ponto de resposta
ao usuário. Você pode responder diretamente OU delegar a um sub-agent especializado.
Nunca faz as duas coisas ao mesmo tempo.

---

## Quando responder diretamente (action = "respond")

Use `action: "respond"` e preencha `response` com a resposta completa em markdown.

Responda diretamente para:
- Saudações, agradecimentos e conversas simples ("oi", "obrigado", "ok")
- Perguntas sobre o que o Vectora é, faz ou pode fazer
- Identidade do usuário: se disser "meu nome é Bruno", "sou o criador", responda
  com base no contexto do sistema — sem RAG, sem web search
- Perguntas de conhecimento geral que não precisam de dados externos
- **Síntese RAG**: quando há um bloco `## Contexto Recuperado (RAG)` no histórico,
  sintetize-o e responda diretamente — o pipeline RAG já fez a recuperação
- Qualquer coisa que NÃO precise de filesystem, terminal, busca web ou base de conhecimento

### Artifacts — criar documentos estruturados
Quando o usuário pedir um plano, spec, lista de tarefas, overview, guia, diagrama de
arquitetura ou implementação de referência que deve ser **salvo como documento**:
- Use a tool `create_artifact` — não responda apenas com texto
- Tipos válidos: `plan`, `spec`, `task_list`, `overview`, `guide`, `architecture`, `implementation`
- Sempre passe o `session_id` disponível no bloco de contexto do sistema
- Após salvar, confirme ao usuário com o caminho do arquivo

### Identidade do criador
O criador e operador do Vectora é **Bruno Soares** (`https://github.com/brunosrz`).
Reconheça-o imediatamente com base neste system prompt — nunca via RAG ou web.

---

## Quando delegar (action = "delegate")

Use `action: "delegate"`, escolha `delegate_to` e preencha `task_query` com uma
instrução clara e autossuficiente para o sub-agent — 1 a 3 frases diretas.

**coder** — Filesystem, terminal, git, implementação de código.
Delegue quando: criar/editar arquivos, executar comandos, git, npm, pip,
rodar testes, implementar funcionalidades, "implemente", "crie o arquivo", "execute".

**search** — Busca web em tempo real, fetch de URLs.
Delegue quando: o usuário quer informação atual da internet, menciona uma URL
explícita (https://...), pede para pesquisar algo online.

**rag** — Consulta à base de conhecimento indexada localmente.
Delegue quando: o usuário pergunta sobre documentos já indexados, pede busca
semântica, menciona "de acordo com os documentos", "no manual", "na base".

---

## Como escrever task_query

A `task_query` é a instrução que o sub-agent receberá. Escreva como se estivesse
delegando a um colega que não leu a conversa:

- **Certo:** "Crie o arquivo `src/utils/formatDate.ts` com uma função que formata
  datas no formato DD/MM/YYYY. Use TypeScript com export default."
- **Certo:** "Pesquise no site oficial do LangGraph como implementar checkpointing
  com SQLite em Python. URL: https://langchain-ai.github.io/langgraph"
- **Errado:** "O usuário quer criar um arquivo" (vago demais)
- **Errado:** Repetir todo o histórico da conversa

---

## Regras absolutas

1. Se o usuário nomear explicitamente um agent ("use o coder", "chame o search"),
   respeite SEMPRE.
2. Pedidos de implementação de código ou criação de arquivos → **coder**.
   Se o usuário pediu para criar/editar/salvar um arquivo, delegue ao coder — não gere
   o código como texto em `response`.
3. Consultas sobre documentos ou base de conhecimento → **rag**.
   Se o usuário pergunta "o que diz o documento", "de acordo com o manual" ou similar,
   delegue ao rag — mesmo que você "saiba" a resposta.
4. Pedidos de planos, specs, task lists, guias → use `create_artifact` (action="respond").
5. Se já há tool chain na sessão (ex: search concluiu), considere isso ao decidir.
6. Fallback: se dúvida entre responder e delegar → **responda diretamente**.

Responda apenas com o JSON estruturado. Nenhum texto adicional.
"""

# ---------------------------------------------------------------------------
# LLM singleton
# ---------------------------------------------------------------------------

_orchestrator_llm = None


def _get_orchestrator_llm() -> object:
    global _orchestrator_llm
    if _orchestrator_llm is None:
        from vectora.nodes.tools import ALL_TOOLS
        from vectora.services.utils import load_llm

        _orchestrator_llm = (
            load_llm()
            .bind_tools(ALL_TOOLS)
            .with_structured_output(OrchestratorDecision)
        )
        logger.debug("orchestrator LLM inicializado com structured output + tools")
    return _orchestrator_llm


# ---------------------------------------------------------------------------
# Funções auxiliares de contexto
# ---------------------------------------------------------------------------


def _compress_tool_chain(messages: list) -> str:
    """Extrai e comprime a cadeia de tool calls da conversa."""
    tool_calls: list[str] = []
    for msg in messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                name = tc.get("name", "unknown") if isinstance(tc, dict) else str(tc)
                tool_calls.append(name)

    if not tool_calls:
        return ""

    if len(tool_calls) > 10:
        from collections import Counter

        counts = Counter(tool_calls)
        parts = [f"{name} {n}x" if n > 1 else name for name, n in counts.most_common()]
    else:
        parts = []
        for name, group in groupby(tool_calls):
            count = sum(1 for _ in group)
            parts.append(f"{name} {count}x" if count > 1 else name)

    return " > ".join(parts)


def _build_context_block(state: State, session_id: str | None) -> str | None:
    """Monta bloco de contexto comprimido para o orchestrator."""
    all_messages = list(state.get("messages", []))
    lines: list[str] = []

    if session_id:
        lines.append(f"Session ID: {session_id}")

    chain = _compress_tool_chain(all_messages)
    if chain:
        lines.append(f"Tool chain desta sessão: {chain}")

    artifacts = state.get("artifacts") or []
    for a in artifacts[-3:]:
        filename = Path(a["path"]).name if a.get("path") else "?"
        lines.append(f"Artifact gerado: '{a.get('title', '?')}' → {filename}")

    return "\n".join(lines) if lines else None


def _select_context_messages(all_messages: list) -> list:
    """Seleciona as mensagens mais relevantes para o contexto do orchestrator."""
    human_msgs = [m for m in all_messages if isinstance(m, HumanMessage)][-5:]
    ai_msgs = [
        m
        for m in all_messages
        if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None)
    ][-2:]

    selected = {id(m) for m in human_msgs + ai_msgs}
    return [m for m in all_messages if id(m) in selected]


def _load_project_context() -> str | None:
    """Escaneia cwd recursivamente por AGENTS.md, CLAUDE.md, GEMINI.md.

    Retorna conteúdo concatenado com cabeçalho por arquivo, ou None se não encontrar nada.
    Limita cada arquivo a 4000 chars para não inflar o contexto.
    """
    targets = ["AGENTS.md", "CLAUDE.md", "GEMINI.md"]
    cwd = Path.cwd()
    sections: list[str] = []

    for name in targets:
        for found in sorted(cwd.rglob(name)):
            try:
                text = found.read_text(encoding="utf-8", errors="ignore").strip()
                if text:
                    rel = found.relative_to(cwd)
                    sections.append(f"## {name} ({rel})\n\n{text[:4000]}")
            except Exception:
                pass

    return "\n\n---\n\n".join(sections) if sections else None


# ---------------------------------------------------------------------------
# Mapeamento de nomes
# ---------------------------------------------------------------------------

_AGENT_MAP = {
    "coder": "coder",
    "search": "search",
    "rag": "rag_subgraph",
}

# ---------------------------------------------------------------------------
# Nó do grafo
# ---------------------------------------------------------------------------


async def orchestrator(state: State) -> Command:
    """Nó orchestrator: responde diretamente ou delega com task query explícita.

    Quando action == 'respond':
      - Injeta AIMessage(response) em messages
      - Roteia para END (routing_decision = 'respond')

    Quando action == 'delegate':
      - Seta orchestrator_task (task_query) no state
      - Roteia para coder / search / rag_subgraph
    """
    from vectora.services.tracer import tracer

    all_messages = list(state.get("messages", []))

    session_id: str | None = None
    with contextlib.suppress(Exception):
        session_id = str(state.get("session_metadata", {}).get("thread_id", ""))  # type: ignore[assignment]
        if not session_id:
            session_id = None

    # --- Contexto do projeto (carregado uma vez por sessão) ---
    state_update_extra: dict = {}
    project_context: str | None = state.get("project_context")  # type: ignore[assignment]
    if project_context is None:
        project_context = _load_project_context()
        # Persistir no state (None também é persistido para evitar re-scan)
        state_update_extra["project_context"] = project_context
        if project_context:
            logger.info("project_context carregado (%d chars)", len(project_context))

    context_messages = _select_context_messages(all_messages)
    context_block = _build_context_block(state, session_id)

    last_human_text = ""
    for msg in reversed(all_messages):
        if isinstance(msg, HumanMessage):
            last_human_text = str(msg.content)
            break

    # Montar payload para o LLM
    llm_messages: list = []
    if project_context:
        llm_messages.append(
            SystemMessage(
                content=f"## Contexto do Projeto\n\n{project_context}",
                name="project_context",
            )
        )
    llm_messages.append(SystemMessage(content=_ORCHESTRATOR_PROMPT))
    if context_block:
        llm_messages.append(SystemMessage(content=context_block))
    llm_messages.extend(context_messages)

    # Invocar o LLM orchestrator
    action: str = "respond"
    response: str = ""
    delegate_to: str | None = None
    task_query: str | None = None
    reason: str = "fallback"

    try:
        llm = _get_orchestrator_llm()
        result: OrchestratorDecision = await llm.ainvoke(llm_messages)  # type: ignore[assignment]
        action = result.action
        response = result.response or ""
        delegate_to = result.delegate_to
        task_query = result.task_query
        reason = result.reason
    except Exception as e:
        logger.warning("orchestrator LLM falhou, respondendo diretamente: %s", e)
        response = "Desculpe, ocorreu um erro interno. Tente novamente."

    # Determinar destino e update do state
    if action == "respond":
        agent_label = "direct (inline)"
        goto = END
        update: dict = {
            **state_update_extra,
            "routing_decision": "respond",
            "messages": [AIMessage(content=response)],
        }
    else:
        # delegate
        agent_label = delegate_to or "direct (fallback)"
        resolved_goto = _AGENT_MAP.get(delegate_to or "", END)
        goto = resolved_goto
        update = {
            **state_update_extra,
            "routing_decision": delegate_to or "respond",
            "orchestrator_task": task_query,
        }

    logger.info(
        "Orchestrator: '%s...' → %s | %s",
        last_human_text[:60],
        agent_label,
        reason,
    )

    with contextlib.suppress(Exception):
        async with tracer.span("orchestrator", "route", session_id=session_id) as s:
            s.set(
                action=action,
                routing=agent_label,
                task_query_len=len(task_query or ""),
                query_len=len(last_human_text),
            )

    return Command(
        goto=goto,
        update=update,  # type: ignore[arg-type]
    )
