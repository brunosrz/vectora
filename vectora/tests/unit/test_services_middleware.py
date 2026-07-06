"""Middleware stack — HITL (A4): modo "plan" pausa uma vez por turno, não a cada tool.

Antes desta mudança, `_interrupt_on_for_mode("plan")` caía no mesmo `case _`
de `"ask"` — zero diferença de comportamento. Agora "plan" usa um predicate
`when` que só interrompe na PRIMEIRA tool destrutiva do turno; aprovada uma
vez, as chamadas seguintes na mesma resposta (antes da próxima mensagem do
usuário) rodam sem novas pausas.
"""

from __future__ import annotations

from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from backend.services.middleware import (
    _interrupt_on_for_mode,
    _plan_mode_should_interrupt,
    build_middleware_stack,
)


def _fake_request(messages: list) -> ToolCallRequest:
    return ToolCallRequest(
        tool_call={"name": "file_write", "args": {}, "id": "x"},
        tool=None,
        state={"messages": messages},
        runtime=None,  # ty: ignore[invalid-argument-type]
    )


def test_plan_mode_interrupts_on_first_destructive_tool_of_turn():
    messages = [HumanMessage(content="apague o arquivo x")]
    req = _fake_request(messages)

    assert _plan_mode_should_interrupt(req) is True


def test_plan_mode_does_not_interrupt_again_after_gate_passed_this_turn():
    """Depois de 1 ToolMessage de tool destrutiva no turno, não interrompe mais."""
    messages = [
        HumanMessage(content="apague o arquivo x e depois o y"),
        AIMessage(
            content="", tool_calls=[{"name": "file_write", "args": {}, "id": "1"}]
        ),
        ToolMessage(content="ok", name="file_write", tool_call_id="1"),
    ]
    req = _fake_request(messages)

    assert _plan_mode_should_interrupt(req) is False


def test_plan_mode_resets_gate_on_new_human_turn():
    """Edge — uma nova mensagem do usuário reabre o gate (novo turno)."""
    messages = [
        HumanMessage(content="apague x"),
        AIMessage(
            content="", tool_calls=[{"name": "file_write", "args": {}, "id": "1"}]
        ),
        ToolMessage(content="ok", name="file_write", tool_call_id="1"),
        HumanMessage(content="agora apague y"),
    ]
    req = _fake_request(messages)

    assert _plan_mode_should_interrupt(req) is True


def test_plan_mode_and_ask_mode_produce_different_interrupt_on():
    """Confirma que "plan" não é mais um alias de "ask" (bug original do A4)."""
    ask_config = _interrupt_on_for_mode("ask")
    plan_config = _interrupt_on_for_mode("plan")

    assert "when" not in ask_config["terminal"]
    assert plan_config["terminal"]["when"] is _plan_mode_should_interrupt


def test_build_middleware_stack_includes_hitl_for_plan_mode():
    stack = build_middleware_stack(permission_mode="plan")
    assert len(stack) == 1


def test_build_middleware_stack_empty_for_bypass():
    stack = build_middleware_stack(permission_mode="bypass")
    assert stack == []
