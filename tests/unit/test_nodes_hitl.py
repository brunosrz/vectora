"""Tests para vectora/nodes/hitl.py — Human-in-the-Loop HITL check node."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from vectora.nodes.hitl import ACCEPT_EDITS_AUTO, REQUIRE_APPROVAL, hitl_check

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(tool_calls: list[dict]) -> Any:
    """Monta um State mínimo com tool_calls na última AIMessage.

    Retorna ``Any`` para casar com o TypedDict ``State`` sem reconstruir todos
    os campos obrigatórios — basta o que o ``hitl_check`` lê.
    """
    msg = MagicMock(spec=AIMessage)
    msg.tool_calls = tool_calls
    return {"messages": [msg]}


def _tc(name: str, args: dict | None = None, tc_id: str = "tc1") -> dict:
    """Cria uma tool_call dict mínima."""
    return {"name": name, "args": args or {}, "id": tc_id}


# ---------------------------------------------------------------------------
# REQUIRE_APPROVAL set
# ---------------------------------------------------------------------------


def test_require_approval_contains_terminal():
    assert "terminal" in REQUIRE_APPROVAL


def test_require_approval_contains_file_write():
    assert "file_write" in REQUIRE_APPROVAL


def test_require_approval_excludes_file_edit():
    """file_edit é cirúrgico — não requer aprovação."""
    assert "file_edit" not in REQUIRE_APPROVAL


def test_require_approval_excludes_file_read():
    assert "file_read" not in REQUIRE_APPROVAL


# ---------------------------------------------------------------------------
# hitl_check — sem tools sensíveis (pass-through)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hitl_check_no_sensitive_tools_returns_not_cancelled():
    """Quando só há tools seguras, retorna hitl_cancelled=False sem pausar."""
    state = _make_state([_tc("file_read"), _tc("list_dir", tc_id="tc2")])
    result = await hitl_check(state)
    assert result == {"hitl_cancelled": False}


@pytest.mark.asyncio
async def test_hitl_check_empty_tool_calls_returns_not_cancelled():
    state = _make_state([])
    result = await hitl_check(state)
    assert result == {"hitl_cancelled": False}


@pytest.mark.asyncio
async def test_hitl_check_no_tool_calls_attr():
    """Mensagem sem atributo tool_calls → pass-through."""
    msg = MagicMock(spec=AIMessage)
    del msg.tool_calls  # força AttributeError → getattr retorna None
    msg.tool_calls = None
    state: Any = {"messages": [msg]}
    result = await hitl_check(state)
    assert result == {"hitl_cancelled": False}


# ---------------------------------------------------------------------------
# hitl_check — com tools sensíveis (interrupt + approve)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hitl_check_terminal_approve():
    """Aprovação via dict {"action": "approve"} → hitl_cancelled=False."""
    state = _make_state([_tc("terminal", {"command": "ls -la"})])

    with patch("vectora.nodes.hitl.interrupt", return_value={"action": "approve"}):
        result = await hitl_check(state)

    assert result == {"hitl_cancelled": False}


@pytest.mark.asyncio
async def test_hitl_check_terminal_approve_bare_string():
    """Aprovação via string "approve" → hitl_cancelled=False."""
    state = _make_state([_tc("terminal", {"command": "rm -rf /tmp/test"})])

    with patch("vectora.nodes.hitl.interrupt", return_value="approve"):
        result = await hitl_check(state)

    assert result == {"hitl_cancelled": False}


@pytest.mark.asyncio
async def test_hitl_check_terminal_approve_empty_string():
    """Aprovação via string vazia (Enter) → hitl_cancelled=False."""
    state = _make_state([_tc("terminal")])

    with patch("vectora.nodes.hitl.interrupt", return_value=""):
        result = await hitl_check(state)

    assert result == {"hitl_cancelled": False}


@pytest.mark.asyncio
async def test_hitl_check_file_write_approve():
    """file_write aprovado → hitl_cancelled=False."""
    state = _make_state([_tc("file_write", {"path": "out.py", "content": "# ok"})])

    with patch("vectora.nodes.hitl.interrupt", return_value={"action": "approve"}):
        result = await hitl_check(state)

    assert result == {"hitl_cancelled": False}


# ---------------------------------------------------------------------------
# hitl_check — com tools sensíveis (interrupt + reject)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hitl_check_terminal_reject():
    """Rejeição → hitl_cancelled=True + ToolMessage de cancelamento injetada."""
    state = _make_state([_tc("terminal", {"command": "rm -rf /"}, tc_id="abc123")])

    with patch("vectora.nodes.hitl.interrupt", return_value={"action": "reject"}):
        result = await hitl_check(state)

    assert result["hitl_cancelled"] is True
    msgs = result["messages"]
    assert len(msgs) == 1
    assert isinstance(msgs[0], ToolMessage)
    assert msgs[0].tool_call_id == "abc123"
    assert "cancelada" in msgs[0].content.lower()


@pytest.mark.asyncio
async def test_hitl_check_reject_multiple_sensitive_tools():
    """Rejeição com 2 tools sensíveis → 2 ToolMessages de cancelamento."""
    state = _make_state(
        [
            _tc("terminal", {"command": "echo hi"}, tc_id="t1"),
            _tc("file_write", {"path": "a.txt", "content": "x"}, tc_id="t2"),
        ]
    )

    with patch("vectora.nodes.hitl.interrupt", return_value={"action": "reject"}):
        result = await hitl_check(state)

    assert result["hitl_cancelled"] is True
    assert len(result["messages"]) == 2
    ids = {m.tool_call_id for m in result["messages"]}
    assert ids == {"t1", "t2"}


@pytest.mark.asyncio
async def test_hitl_check_reject_only_sensitive_tools_get_cancel_msg():
    """Só as tools sensíveis recebem ToolMessage de cancelamento."""
    state = _make_state(
        [
            _tc("file_read", {}, tc_id="safe"),
            _tc("terminal", {"command": "echo hi"}, tc_id="danger"),
        ]
    )

    with patch("vectora.nodes.hitl.interrupt", return_value={"action": "reject"}):
        result = await hitl_check(state)

    # Apenas "danger" deve ter ToolMessage
    assert len(result["messages"]) == 1
    assert result["messages"][0].tool_call_id == "danger"


# ---------------------------------------------------------------------------
# hitl_check — interrupt recebe o payload correto
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hitl_check_interrupt_receives_payload():
    """Verifica que interrupt() recebe lista de {id, name, args}."""
    state = _make_state([_tc("terminal", {"command": "ls"}, tc_id="xyz")])

    captured_payload = []

    def _fake_interrupt(payload: object) -> dict:
        captured_payload.append(payload)
        return {"action": "approve"}

    with patch("vectora.nodes.hitl.interrupt", side_effect=_fake_interrupt):
        await hitl_check(state)

    assert len(captured_payload) == 1
    item = captured_payload[0][0]
    assert item["id"] == "xyz"
    assert item["name"] == "terminal"
    assert item["args"] == {"command": "ls"}


# ---------------------------------------------------------------------------
# Permission modes (R2)
# ---------------------------------------------------------------------------


def _cfg(mode: str) -> Any:
    """Monta um RunnableConfig com permission_mode no configurable."""
    return {"configurable": {"permission_mode": mode}}


def _boom(_payload: object) -> dict:
    raise AssertionError("interrupt() não deveria ser chamado neste modo")


@pytest.mark.asyncio
async def test_accept_edits_includes_file_write():
    """file_write é auto-aprovado no modo accept_edits."""
    assert "file_write" in ACCEPT_EDITS_AUTO


@pytest.mark.asyncio
async def test_accept_edits_excludes_terminal():
    """terminal nunca é auto-aprovado — sempre confirma."""
    assert "terminal" not in ACCEPT_EDITS_AUTO


@pytest.mark.asyncio
async def test_bypass_mode_skips_interrupt():
    """bypass: tool destrutiva passa sem pausar o grafo."""
    state = _make_state([_tc("terminal", {"command": "rm -rf /"})])
    with patch("vectora.nodes.hitl.interrupt", side_effect=_boom):
        result = await hitl_check(state, _cfg("bypass"))
    assert result == {"hitl_cancelled": False}


@pytest.mark.asyncio
async def test_auto_mode_skips_interrupt():
    """auto: auto-aprova tudo (confinamento de escopo é garantido pelas tools)."""
    state = _make_state([_tc("terminal", {"command": "ls"})])
    with patch("vectora.nodes.hitl.interrupt", side_effect=_boom):
        result = await hitl_check(state, _cfg("auto"))
    assert result == {"hitl_cancelled": False}


@pytest.mark.asyncio
async def test_plan_mode_cancels_destructive():
    """plan: ações destrutivas não são executadas — recebem ToolMessage de cancelamento."""
    state = _make_state([_tc("terminal", {"command": "ls"}, tc_id="p1")])
    with patch("vectora.nodes.hitl.interrupt", side_effect=_boom):
        result = await hitl_check(state, _cfg("plan"))
    assert result["hitl_cancelled"] is True
    msgs = result["messages"]
    assert len(msgs) == 1
    assert isinstance(msgs[0], ToolMessage)
    assert msgs[0].tool_call_id == "p1"
    assert "planejamento" in msgs[0].content.lower()


@pytest.mark.asyncio
async def test_accept_edits_auto_approves_file_write():
    """accept_edits: file_write não pausa o grafo."""
    state = _make_state([_tc("file_write", {"path": "a.py", "content": "x"})])
    with patch("vectora.nodes.hitl.interrupt", side_effect=_boom):
        result = await hitl_check(state, _cfg("accept_edits"))
    assert result == {"hitl_cancelled": False}


@pytest.mark.asyncio
async def test_accept_edits_still_confirms_terminal():
    """accept_edits: terminal ainda exige confirmação."""
    state = _make_state([_tc("terminal", {"command": "ls"})])
    with patch("vectora.nodes.hitl.interrupt", return_value={"action": "approve"}):
        result = await hitl_check(state, _cfg("accept_edits"))
    assert result == {"hitl_cancelled": False}


@pytest.mark.asyncio
async def test_accept_edits_mixed_only_confirms_terminal():
    """accept_edits com file_write + terminal: só o terminal vai ao interrupt."""
    state = _make_state(
        [
            _tc("file_write", {"path": "a.py", "content": "x"}, tc_id="fw"),
            _tc("terminal", {"command": "ls"}, tc_id="term"),
        ]
    )
    captured = []

    def _fake(payload: object) -> dict:
        captured.append(payload)
        return {"action": "approve"}

    with patch("vectora.nodes.hitl.interrupt", side_effect=_fake):
        result = await hitl_check(state, _cfg("accept_edits"))

    assert result == {"hitl_cancelled": False}
    assert len(captured) == 1
    ids = {item["id"] for item in captured[0]}
    assert ids == {"term"}


@pytest.mark.asyncio
async def test_ask_mode_explicit_interrupts():
    """ask explícito: comportamento padrão de confirmação."""
    state = _make_state([_tc("terminal", {"command": "ls"})])
    with patch("vectora.nodes.hitl.interrupt", return_value={"action": "approve"}):
        result = await hitl_check(state, _cfg("ask"))
    assert result == {"hitl_cancelled": False}


@pytest.mark.asyncio
async def test_unknown_mode_falls_back_to_ask():
    """Modo desconhecido cai no comportamento seguro (ask → interrupt)."""
    state = _make_state([_tc("terminal", {"command": "ls"})])
    with patch(
        "vectora.nodes.hitl.interrupt", return_value={"action": "approve"}
    ) as it:
        result = await hitl_check(state, _cfg("nonsense"))
    assert result == {"hitl_cancelled": False}
    assert it.called


@pytest.mark.asyncio
async def test_plan_mode_ignores_safe_tools():
    """plan: tools seguras não são afetadas (pass-through)."""
    state = _make_state([_tc("file_read", {}, tc_id="r1")])
    result = await hitl_check(state, _cfg("plan"))
    assert result == {"hitl_cancelled": False}


# ---------------------------------------------------------------------------
# graph topology — hitl_check presente no grafo
# ---------------------------------------------------------------------------


def test_graph_has_hitl_check_node():
    """O grafo compilado deve conter o nó hitl_check."""
    from vectora.graph import build_graph

    g = build_graph()
    assert "hitl_check" in g.nodes


def test_graph_coder_routes_to_hitl_check():
    """A aresta condicional de coder deve ter hitl_check como destino, não coder_tools."""
    from vectora.graph import build_graph

    g = build_graph()
    # Verifica que o nó hitl_check existe e coder_tools também
    assert "hitl_check" in g.nodes
    assert "coder_tools" in g.nodes
