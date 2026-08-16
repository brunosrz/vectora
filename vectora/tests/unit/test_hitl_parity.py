"""Paridade HITL entre o caminho LangChain (`backend/services/middleware.py`)
e o motor nativo (`backend/engine/hitl.py`) — mesmo cenário, mesmo resultado.

Roda o MESMO conjunto de cenários contra as duas implementações via um
adaptador comum por lado (`ToolCallRequest`/`runtime.context` de um lado,
`ToolContext`/`history: list[VMessage]` do outro) e compara a decisão
booleana. Enquanto a migração para o motor nativo estiver em andamento, um
gap aqui é bypass silencioso de aprovação humana — risco de segurança real,
não só divergência de teste.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from backend.engine.hitl import should_require_approval
from backend.services.middleware import _dynamic_hitl_when
from backend.tools.context import ToolContext
from backend.vtypes.message import ContentBlock, MessageRole, VMessage, text_message


def _lc_req(
    tool_name: str,
    mode: str,
    *,
    messages: list | None = None,
    workspace_id: str = "ws-1",
    args: dict | None = None,
    background_task_id: str = "",
) -> ToolCallRequest:
    return ToolCallRequest(
        tool_call={"name": tool_name, "args": args or {}, "id": "x"},
        tool=None,
        state={"messages": messages or [HumanMessage(content="faça algo")]},
        runtime=SimpleNamespace(
            context=SimpleNamespace(
                permission_mode=mode,
                workspace_id=workspace_id,
                background_task_id=background_task_id,
            )
        ),  # ty: ignore[invalid-argument-type]
    )


def _native_ctx(
    mode: str, *, workspace_id: str = "ws-1", background_task_id: str = ""
) -> ToolContext:
    return ToolContext(
        user_id="alice",
        thread_id="thread-1",
        permission_mode=mode,
        workspace_id=workspace_id,
        background_task_id=background_task_id,
    )


#: Histórico nativo equivalente ao `messages` LangChain "já passou o gate do
#: plano neste turno" (um USER seguido de um TOOL de tool destrutiva).
_PLAN_JA_PASSOU_HISTORY: list[VMessage] = [
    text_message(MessageRole.USER, "apague x e y"),
    VMessage(
        role=MessageRole.ASSISTANT, content=[ContentBlock(kind="text", text="ok")]
    ),
    VMessage(
        role=MessageRole.TOOL,
        content=[ContentBlock(kind="text", text="ok")],
        name="file_write",
    ),
]

_PLAN_JA_PASSOU_MESSAGES = [
    HumanMessage(content="apague x e y"),
    AIMessage(content="", tool_calls=[{"name": "file_write", "args": {}, "id": "1"}]),
    ToolMessage(content="ok", name="file_write", tool_call_id="1"),
]


# Cada cenário: (id, tool_name, mode, workspace_id, background_task_id,
# args, plan_ja_passou, esperado).
_PARITY_CASES = [
    ("read_only_tool_ask", "web_search", "ask", "ws-1", "", {}, False, False),
    ("read_only_tool_bypass", "web_search", "bypass", "ws-1", "", {}, False, False),
    ("file_write_ask_pausa", "file_write", "ask", "ws-1", "", {}, False, True),
    ("terminal_ask_pausa", "terminal", "ask", "ws-1", "", {}, False, True),
    (
        "file_write_accept_edits_auto_aprova",
        "file_write",
        "accept_edits",
        "ws-1",
        "",
        {},
        False,
        False,
    ),
    (
        "terminal_accept_edits_pausa",
        "terminal",
        "accept_edits",
        "ws-1",
        "",
        {},
        False,
        True,
    ),
    ("file_write_auto_nao_pausa", "file_write", "auto", "ws-1", "", {}, False, False),
    (
        "file_write_bypass_nao_pausa",
        "file_write",
        "bypass",
        "ws-1",
        "",
        {},
        False,
        False,
    ),
    (
        "computer_use_sempre_pausa_mesmo_bypass",
        "computer_use",
        "bypass",
        "ws-1",
        "",
        {},
        False,
        True,
    ),
    (
        "plan_primeira_tool_do_turno_pausa",
        "file_write",
        "plan",
        "ws-1",
        "",
        {},
        False,
        True,
    ),
    (
        "plan_gate_ja_passado_nao_pausa",
        "file_write",
        "plan",
        "ws-1",
        "",
        {},
        True,
        False,
    ),
    (
        "modo_desconhecido_cai_em_ask",
        "file_write",
        "modo-invalido",
        "ws-1",
        "",
        {},
        False,
        True,
    ),
    (
        "kanban_update_status_propria_task_nao_pausa",
        "kanban_update_status",
        "ask",
        "ws-1",
        "task-1",
        {"task_id": "task-1"},
        False,
        False,
    ),
    (
        "kanban_update_status_outra_task_pausa",
        "kanban_update_status",
        "ask",
        "ws-1",
        "task-1",
        {"task_id": "task-2"},
        False,
        True,
    ),
    (
        "install_learned_skill_fora_do_jail_bypass_pausa",
        "install_learned_skill",
        "ask",
        "ws-jail",
        "",
        {},
        False,
        True,
    ),
]


@pytest.mark.parametrize(
    (
        "case_id",
        "tool_name",
        "mode",
        "workspace_id",
        "background_task_id",
        "args",
        "plan_ja_passou",
        "esperado",
    ),
    _PARITY_CASES,
    ids=[c[0] for c in _PARITY_CASES],
)
def test_paridade_middleware_langchain_vs_hitl_nativo(
    case_id: str,
    tool_name: str,
    mode: str,
    workspace_id: str,
    background_task_id: str,
    args: dict,
    plan_ja_passou: bool,
    esperado: bool,
) -> None:
    lc_messages = _PLAN_JA_PASSOU_MESSAGES if plan_ja_passou else None
    native_history = _PLAN_JA_PASSOU_HISTORY if plan_ja_passou else []

    resultado_langchain = _dynamic_hitl_when(
        _lc_req(
            tool_name,
            mode,
            messages=lc_messages,
            workspace_id=workspace_id,
            args=args,
            background_task_id=background_task_id,
        )
    )
    resultado_nativo = should_require_approval(
        tool_name,
        _native_ctx(
            mode, workspace_id=workspace_id, background_task_id=background_task_id
        ),
        args,
        native_history,
    )

    assert resultado_langchain is esperado, (
        f"{case_id}: middleware.py (LangChain) devolveu {resultado_langchain}, "
        f"esperado {esperado}"
    )
    assert resultado_nativo is esperado, (
        f"{case_id}: hitl.py (nativo) devolveu {resultado_nativo}, esperado {esperado}"
    )
    assert resultado_langchain == resultado_nativo, (
        f"{case_id}: divergência entre middleware.py ({resultado_langchain}) e "
        f"hitl.py ({resultado_nativo}) — gap de paridade HITL"
    )


def test_jailed_workspace_bypassa_hitl_nas_duas_implementacoes(monkeypatch) -> None:
    """`terminal`/`file_write` numa workspace com `[sandbox]` habilitado não
    pausam em nenhuma das duas implementações; `install_learned_skill`
    continua pedindo aprovação nas duas (fora do escopo do jail)."""
    import backend.engine.hitl as hitl_module
    import backend.services.middleware as mw_module

    monkeypatch.setattr(mw_module, "_workspace_is_jailed", lambda wid: wid == "ws-jail")
    monkeypatch.setattr(
        hitl_module, "_workspace_is_jailed", lambda wid: wid == "ws-jail"
    )

    for tool_name in ("terminal", "file_write"):
        assert (
            _dynamic_hitl_when(_lc_req(tool_name, "ask", workspace_id="ws-jail"))
            is False
        )
        assert (
            should_require_approval(
                tool_name, _native_ctx("ask", workspace_id="ws-jail"), {}, []
            )
            is False
        )

    assert (
        _dynamic_hitl_when(
            _lc_req("install_learned_skill", "ask", workspace_id="ws-jail")
        )
        is True
    )
    assert (
        should_require_approval(
            "install_learned_skill", _native_ctx("ask", workspace_id="ws-jail"), {}, []
        )
        is True
    )
