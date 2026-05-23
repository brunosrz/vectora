"""HITL — Human-in-the-Loop: pausa o grafo antes de ações destrutivas.

Inserido entre `coder` e `coder_tools` no grafo principal.

Fluxo:
    coder → hitl_check ──(aprovado)──► coder_tools → coder
                       ──(rejeitado)─► coder  (com ToolMessages de cancelamento)

Tools que exigem aprovação:
    - terminal    — executa shell arbitrário na máquina do usuário
    - file_write  — cria ou sobrescreve arquivo completo

Tools que NÃO exigem aprovação (cirúrgicas / somente-leitura):
    - file_edit, file_read, list_dir, grep, create_artifact, etc.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.types import interrupt

from vectora.state import State

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração — quais tools exigem confirmação humana antes de executar
# ---------------------------------------------------------------------------

#: Tools destrutivas que pausam o grafo para aprovação do usuário.
#: `file_edit` é intencialmente excluído — edições cirúrgicas são seguras.
REQUIRE_APPROVAL: frozenset[str] = frozenset(
    {
        "terminal",
        "terminal_tool",
        "file_write",
        "file_write_tool",
    }
)


# ---------------------------------------------------------------------------
# Nó do grafo
# ---------------------------------------------------------------------------


async def hitl_check(state: State) -> dict[str, Any]:
    """Inspeciona tool_calls pendentes e pede confirmação quando necessário.

    Se nenhuma tool destrutiva está na fila, retorna imediatamente sem pausar.
    Caso contrário, chama ``interrupt()`` — o grafo pausa, salva o checkpoint,
    e só continua quando o chat loop retomar com ``Command(resume=decision)``.

    ``decision`` deve ser um dict ``{"action": "approve" | "reject"}``.
    Qualquer outro valor (ou string nua "approve") também é tratado como aprovação.
    """
    last_msg = state["messages"][-1]
    tool_calls: list[dict[str, Any]] = getattr(last_msg, "tool_calls", None) or []

    sensitive = [tc for tc in tool_calls if tc.get("name", "") in REQUIRE_APPROVAL]

    if not sensitive:
        # Nenhuma tool destrutiva — prosseguir direto para coder_tools
        return {"hitl_cancelled": False}

    logger.info(
        "HITL: aguardando aprovação para %d tool(s): %s",
        len(sensitive),
        [tc["name"] for tc in sensitive],
    )

    # Monta payload legível para a UI: lista de {name, args, id}
    payload: list[dict[str, Any]] = [
        {
            "id": tc["id"],
            "name": tc["name"],
            "args": tc.get("args", {}),
        }
        for tc in sensitive
    ]

    # ── Pausa o grafo ────────────────────────────────────────────────────────
    # O chat loop vai ler esse payload via graph.aget_state(), exibir o
    # HITLPanel e chamar astream_events(Command(resume=decision), ...).
    decision: Any = interrupt(payload)
    # ── Grafo retoma aqui com o valor passado em Command(resume=...) ─────────

    # Normaliza decision para dict
    if isinstance(decision, str):
        action = decision.lower()
    elif isinstance(decision, dict):
        action = str(decision.get("action", "approve")).lower()
    else:
        action = "approve"

    if action in ("approve", "yes", "sim", "s", "y", ""):
        logger.info("HITL: ações aprovadas pelo usuário")
        return {"hitl_cancelled": False}

    # Rejeitado — injeta ToolMessages de cancelamento para cada tool sensível.
    # O coder recebe essas mensagens e sabe que a ação não foi executada,
    # podendo informar o usuário ou propor alternativas.
    logger.info("HITL: ações rejeitadas pelo usuário")
    cancel_msgs: list[ToolMessage] = [
        ToolMessage(
            content="Ação cancelada pelo usuário.",
            tool_call_id=tc["id"],
        )
        for tc in sensitive
    ]
    return {"messages": cancel_msgs, "hitl_cancelled": True}
