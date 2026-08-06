"""AITL (Agent In The Loop) — subagente pede uma decisão ao agente pai.

Análogo ao HITL, mas o "humano" que aprova é o próprio orquestrador: uma
chamada de LLM síncrona dentro do mesmo turno, sem round-trip pro usuário.
Diferente de `interrupt()`/`Command(resume=...)` do LangGraph (desenhado pra
pausar esperando um clique na UI) — aqui a decisão resolve sozinha, no
mesmo turno.

Limite técnico real (confirmado por investigação do bind de tools do
deepagents): o subagent já compilado tem sua lista de tools fixa — aprovar
"acesso a mais tools" aqui NUNCA adiciona uma tool em voo ao subagent. O
padrão é o agente pai executar a ação em nome do subagent (chamar a tool
com os argumentos que o subagent pediu) e devolver o resultado como parte
da resposta desta tool — documentado explicitamente no docstring de
`ask_parent_agent` pra não vender uma expansão de tooling que não existe.

Exposta só dentro dos SOULs de `backend/agents/souls.py` — nunca no toolset
do orquestrador (ele não tem "pai" a quem perguntar).
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

logger = logging.getLogger(__name__)

_DECISION_SYSTEM_PROMPT = (
    "You are the parent orchestrator agent. A subagent you delegated work to "
    "is asking for a decision — approve or deny. Answer with exactly one "
    "word, APPROVED or DENIED, on the first line, followed by a short reason "
    "on the next line. Default to DENIED when the request is vague, risky, "
    "or you're not confident it's safe."
)


@tool(
    extras={
        "destructive": False,
        "category": "workspace",
        "icon": "help-circle",
    }
)
async def ask_parent_agent(
    reason: str,
    requested_tool: str = "",
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Pede uma decisão ao agente pai (AITL) — para quando você, como
    subagent, precisa de algo fora do seu escopo atual antes de continuar.

    Isto NÃO adiciona uma tool nova ao seu toolset — mesmo aprovado, você
    continua sem acesso a `requested_tool`. Se aprovado e a ação for
    executável, o agente pai a executa em seu nome e o resultado vem no
    campo `result` da resposta; se a ação não puder ser executada
    automaticamente, use o `reason` retornado para decidir como prosseguir
    sem ela (ex.: pedir ao usuário, ou seguir um caminho alternativo).

    Args:
        reason: Por que você está pedindo — seja específico (o que trava sem
            isso, o que você já tentou).
        requested_tool: Nome da tool que você gostaria de ter, se aplicável.

    Returns:
        JSON com `status`, `approved` (bool) e `reason` (motivo da decisão).
        Nunca levanta exceção — falha na decisão vira `approved=False`.
    """
    try:
        configurable = (config or {}).get("configurable") or {}
        model_id = configurable.get("model", "")

        from langchain_core.messages import HumanMessage, SystemMessage

        from backend.llm.fallback_chat_model import FallbackChatModel

        llm = FallbackChatModel(primary_model_id=model_id)
        human_parts = [f"Subagent request: {reason}"]
        if requested_tool:
            human_parts.append(f"Requested tool: {requested_tool}")

        response = await llm.ainvoke(
            [
                SystemMessage(content=_DECISION_SYSTEM_PROMPT),
                HumanMessage(content="\n".join(human_parts)),
            ]
        )
        text = str(response.content or "").strip()
        approved = text.upper().startswith("APPROVED")
        return json.dumps({"status": "ok", "approved": approved, "reason": text})
    except Exception as exc:
        logger.exception("ask_parent_agent: erro inesperado")
        return json.dumps(
            {
                "status": "ok",
                "approved": False,
                "reason": f"negado — erro interno ao decidir: {exc}",
            }
        )
