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
from langchain_core.runnables import RunnableConfig
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

#: Tools auto-aprovadas no modo "accept_edits" — escrita de arquivos passa sem
#: confirmação; terminal continua exigindo aprovação por executar shell arbitrário.
ACCEPT_EDITS_AUTO: frozenset[str] = frozenset(
    {
        "file_write",
        "file_write_tool",
    }
)


def _permission_mode(config: RunnableConfig | None) -> str:
    """Lê o modo de permissão do RunnableConfig (default: 'ask')."""
    if not isinstance(config, dict):
        return "ask"
    configurable = config.get("configurable")
    if not isinstance(configurable, dict):
        return "ask"
    return str(configurable.get("permission_mode") or "ask").lower()


# ---------------------------------------------------------------------------
# Nó do grafo
# ---------------------------------------------------------------------------


async def hitl_check(
    state: State,
    config: RunnableConfig = None,  # type: ignore[assignment]  # ty: ignore[invalid-parameter-default]
) -> dict[str, Any]:
    """Inspeciona tool_calls pendentes e pede confirmação quando necessário.

    O comportamento depende do modo de permissão (``configurable.permission_mode``):

    - ``ask`` (default): pausa via ``interrupt()`` em toda tool destrutiva.
    - ``accept_edits``: auto-aprova escrita de arquivos; ainda confirma terminal.
    - ``plan``: não executa ações destrutivas — injeta ToolMessages de cancelamento.
    - ``auto`` / ``bypass``: auto-aprova tudo sem pausar.

    Quando o grafo pausa, só continua quando o chat loop retomar com
    ``Command(resume=decision)``. ``decision`` deve ser um dict
    ``{"action": "approve" | "reject" | "edit"}``; uma string nua "approve"
    (ou vazia) também é tratada como aprovação.
    """
    last_msg = state["messages"][-1]
    tool_calls: list[dict[str, Any]] = getattr(last_msg, "tool_calls", None) or []

    sensitive = [tc for tc in tool_calls if tc.get("name", "") in REQUIRE_APPROVAL]

    if not sensitive:
        # Nenhuma tool destrutiva — prosseguir direto para coder_tools
        return {"hitl_cancelled": False}

    mode = _permission_mode(config)

    if mode in ("auto", "bypass"):
        logger.info("HITL: modo '%s' — auto-aprovando %d tool(s)", mode, len(sensitive))
        return {"hitl_cancelled": False}

    if mode == "plan":
        logger.info(
            "HITL: modo planejamento — cancelando %d ação(ões) destrutiva(s)",
            len(sensitive),
        )
        cancel_msgs = [
            ToolMessage(
                content="Modo de planejamento ativo: ação não executada. "
                "Descreva o plano e aguarde aprovação para sair do modo.",
                tool_call_id=tc["id"],
            )
            for tc in sensitive
        ]
        return {"messages": cancel_msgs, "hitl_cancelled": True}

    if mode == "accept_edits":
        to_confirm = [
            tc for tc in sensitive if tc.get("name", "") not in ACCEPT_EDITS_AUTO
        ]
        if not to_confirm:
            logger.info("HITL: modo accept_edits — escrita de arquivos auto-aprovada")
            return {"hitl_cancelled": False}
    else:
        to_confirm = sensitive

    logger.info(
        "HITL: aguardando aprovação para %d tool(s): %s",
        len(to_confirm),
        [tc["name"] for tc in to_confirm],
    )

    # Monta payload legível para a UI: lista de {name, args, id}
    payload: list[dict[str, Any]] = [
        {
            "id": tc["id"],
            "name": tc["name"],
            "args": tc.get("args", {}),
        }
        for tc in to_confirm
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

    if action == "edit":
        # Usuário editou os args da primeira tool sensível antes de aprovar.
        # Recria a AIMessage com os args atualizados para que coder_tools
        # execute a versão editada pelo usuário.
        new_args = decision.get("args") if isinstance(decision, dict) else {}
        logger.info("HITL: args editados pelo usuário: %s", new_args)
        try:
            import copy

            from langchain_core.messages import AIMessage

            last_msg = state["messages"][-1]
            target_id = to_confirm[0]["id"]
            new_tool_calls = copy.deepcopy(
                list(getattr(last_msg, "tool_calls", []) or [])
            )
            for tc in new_tool_calls:
                if tc.get("id") == target_id:
                    tc["args"] = new_args or {}
                    break
            updated_msg = AIMessage(
                content=getattr(last_msg, "content", ""),
                id=getattr(last_msg, "id", None),
                tool_calls=new_tool_calls,
            )
            return {"messages": [updated_msg], "hitl_cancelled": False}
        except Exception as exc:
            logger.warning(
                "HITL: falha ao aplicar edit, aprovando com args originais: %s", exc
            )
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
        for tc in to_confirm
    ]
    return {"messages": cancel_msgs, "hitl_cancelled": True}
