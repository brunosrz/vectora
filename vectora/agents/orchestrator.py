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


def _is_llm_quota_error(err: str) -> bool:
    """Retorna True se o erro indica quota/rate-limit do LLM (Gemini, OpenAI…)."""
    err_lower = err.lower()
    return (
        "429" in err
        or "resource_exhausted" in err_lower
        or "too many requests" in err_lower
        or "rate limit" in err_lower
        or "quota" in err_lower
        or "rateLimitExceeded" in err
        or "quota_exceeded" in err_lower
    )


def _classify_quota_error(exc: Exception) -> str:
    """Classifica o tipo de limite atingido: 'rpm', 'rpd' ou 'unknown'.

    O Gemini inclui `retryDelay` apenas para limites por minuto (RPM).
    Limites diários (RPD/quota total) não têm retry_delay — a API retorna
    RESOURCE_EXHAUSTED sem informar quando vai resetar.
    """
    err_str = str(exc).lower()
    # Sinais de cota diária / total esgotada
    if any(
        s in err_str
        for s in (
            "daily",
            "per day",
            "quota exceeded",
            "quota_exceeded",
            "free tier",
            "billing",
        )
    ):
        return "rpd"
    # Se tem retry_delay → é RPM (limite por minuto)
    if _extract_retry_delay(exc) is not None:
        return "rpm"
    # Genérico: sem retry_delay → provavelmente RPD ou desconhecido
    return "unknown"


def _extract_retry_delay(exc: Exception) -> int | None:
    """Tenta extrair o tempo de retry (segundos) do erro 429 do Gemini/Google API.

    A Google API Core inclui `retryDelay` nos detalhes do erro 429 quando o
    limite é por minuto (RPM). Retorna None se não encontrar o campo.
    """
    try:
        # google.api_core.exceptions.ResourceExhausted tem .details()
        details = getattr(exc, "details", None)
        if callable(details):
            details = details()
        if isinstance(details, list):
            for d in details:
                # d pode ser um proto RetryInfo com retry_delay
                rd = getattr(d, "retry_delay", None)
                if rd is not None:
                    return max(1, int(getattr(rd, "seconds", 0)))
        # Fallback: parsear string do erro (ex: "retry_delay { seconds: 30 }")
        import re

        err_str = str(exc)
        m = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", err_str)
        if m:
            return int(m.group(1))
        # Header Retry-After em formato numérico
        m = re.search(r"retry.after['\"]?\s*[:=]\s*['\"]?(\d+)", err_str, re.IGNORECASE)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


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
- Qualquer coisa que NÃO precise de filesystem, terminal, busca web ou base de
  conhecimento

### Artifacts — criar documentos estruturados
Quando o usuário pedir um plano, spec, lista de tarefas, overview, guia, diagrama de
arquitetura ou implementação de referência que deve ser **salvo como documento**:
- Use a tool `create_artifact` — não responda apenas com texto
- Tipos válidos: `plan`, `spec`, `task_list`, `overview`, `guide`, `architecture`,
  `implementation`
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
4. Pedidos de planos, specs, task lists, guias → use `create_artifact`
   (action="respond").
5. Se já há tool chain na sessão (ex: search concluiu), considere isso ao decidir.
6. Correção do RAG: se o usuário fornecer uma fonte autoritativa (repositório
   canônico, doc oficial) que contradiz algo buscado antes na web, delegue ao
   **search** com a instrução de reavaliar e remover do RAG o conteúdo errado.
7. Fallback: se dúvida entre responder e delegar → **responda diretamente**.

Responda apenas com o JSON estruturado. Nenhum texto adicional.
"""

# Prompt da síntese pós-RAG — usado quando o subgrafo RAG já recuperou o
# contexto e o orchestrator precisa apenas redigir a resposta final.
_RAG_SYNTHESIS_PROMPT = """Você é o Vectora. O pipeline de RAG já recuperou o \
contexto abaixo da base de conhecimento indexada. Sua tarefa é responder à \
pergunta do usuário usando ESSE contexto como fonte primária.

Regras:
- Baseie a resposta no contexto recuperado; cite as fontes quando relevante.
- Se o contexto não contém a informação necessária, diga isso honestamente —
  não invente. Sugira indexar a documentação correta ou refinar a pergunta.
- Responda em português, de forma clara e completa, em markdown.
"""

# ---------------------------------------------------------------------------
# LLM singletons
# ---------------------------------------------------------------------------

_orchestrator_llm = None
_synthesis_llm = None


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


def _get_synthesis_llm() -> object:
    """LLM plano (sem structured output, sem tools) para síntese pós-RAG.

    Separado do `_get_orchestrator_llm` de propósito: a síntese precisa
    gerar texto livre, não uma `OrchestratorDecision`. Usar o LLM estruturado
    aqui reabriria a porta para re-rotear ao RAG — exatamente o loop que o
    Bloco A6 elimina.
    """
    global _synthesis_llm
    if _synthesis_llm is None:
        from vectora.services.utils import load_llm

        _synthesis_llm = load_llm()
        logger.debug("orchestrator: LLM de síntese pós-RAG inicializado")
    return _synthesis_llm


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

    Retorna conteúdo concatenado com cabeçalho por arquivo, ou None se não
    encontrar nada.
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


def _is_post_rag(all_messages: list) -> bool:
    """True se a última mensagem é o marcador `rag_context` do subgrafo RAG.

    É o sinal determinístico de que o turno atual já passou pelo pipeline
    RAG. `rag_inject` sempre emite esse `SystemMessage` (mesmo sem docs),
    então a detecção é confiável.
    """
    if not all_messages:
        return False
    last = all_messages[-1]
    return (
        isinstance(last, SystemMessage) and getattr(last, "name", "") == "rag_context"
    )


async def _synthesize_after_rag(
    all_messages: list,
    session_id: str | None,
    state_update_extra: dict,
) -> Command:
    """Síntese pós-RAG: o subgrafo RAG já recuperou o contexto; aqui o
    orchestrator apenas redige a resposta final e encerra o turno.

    Este caminho vai SEMPRE para `END` com um LLM plano — nunca toma decisão
    de roteamento. Isso elimina estruturalmente o loop orchestrator ↔
    rag_subgraph: é impossível re-rotear para o RAG a partir daqui.
    """
    from vectora.services.tracer import tracer

    # A última mensagem é o bloco rag_context (garantido por _is_post_rag).
    rag_context_msg = all_messages[-1]

    user_question = ""
    for msg in reversed(all_messages):
        if isinstance(msg, HumanMessage):
            user_question = str(msg.content)
            break

    payload: list = [
        SystemMessage(content=_RAG_SYNTHESIS_PROMPT),
        rag_context_msg,
        HumanMessage(content=user_question or "Responda com base no contexto acima."),
    ]

    answer = ""
    try:
        llm = _get_synthesis_llm()
        result = await llm.ainvoke(payload)  # type: ignore[attr-defined]
        answer = str(getattr(result, "content", "") or "").strip()
    except Exception as e:
        err_str = str(e)
        if _is_llm_quota_error(err_str):
            logger.warning("orchestrator: quota/rate-limit do LLM na síntese pós-RAG")
            retry_s = _extract_retry_delay(e)
            kind = _classify_quota_error(e)
            suffix = f":{retry_s}:{kind}" if retry_s else f":0:{kind}"
            answer = f"quota rate limit{suffix}"
        else:
            logger.warning("orchestrator: síntese pós-RAG falhou: %s", e)

    if not answer:
        answer = (
            "Não consegui sintetizar uma resposta a partir do contexto "
            "recuperado. Tente reformular a pergunta ou indexar a "
            "documentação relevante."
        )

    logger.info("Orchestrator: síntese pós-RAG → END (%d chars)", len(answer))

    with contextlib.suppress(Exception):
        async with tracer.span(
            "orchestrator", "rag_synthesis", session_id=session_id
        ) as s:
            s.set(answer_len=len(answer), question_len=len(user_question))

    return Command(
        goto=END,
        update={
            **state_update_extra,
            "routing_decision": "respond",
            "messages": [AIMessage(content=answer)],
        },  # type: ignore[arg-type]
    )


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

    # --- Modo pós-RAG ---
    # Se a última mensagem é o marcador `rag_context`, o subgrafo RAG já rodou
    # neste turno. O orchestrator NÃO decide rota agora — apenas sintetiza a
    # resposta final e encerra. Sem isto, ele re-decidiria "rag" (o usuário
    # ainda pediu RAG) e voltaria ao subgrafo: loop infinito → recursão.
    if _is_post_rag(all_messages):
        return await _synthesize_after_rag(all_messages, session_id, state_update_extra)

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
        err_str = str(e)
        if _is_llm_quota_error(err_str):
            logger.warning("orchestrator: quota/rate-limit do LLM atingida")
            retry_s = _extract_retry_delay(e)
            suffix = f":{retry_s}" if retry_s else ""
            response = f"quota rate limit{suffix}"
        else:
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
