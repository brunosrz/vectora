"""Smoke tests do TUI Textual.

Validações:
  - widgets importáveis
  - VectoraChatApp instanciável
  - StreamHandler dispatcha eventos LangGraph para os hooks do app
  - HITLModal constrói payload pretty-printed
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# imports estruturais
# ---------------------------------------------------------------------------


def test_textual_app_importable() -> None:
    from src.ui.app import VectoraChatApp

    assert VectoraChatApp.TITLE == "Vectora"


def test_textual_widgets_importable() -> None:
    from src.ui.widgets.code_block import CodeBlockWidget
    from src.ui.widgets.diff import DiffWidget
    from src.ui.widgets.hitl import HITLModal
    from src.ui.widgets.thinking import ThinkingWidget


def test_streaming_module_constants() -> None:
    from src.ui import streaming

    assert "invoke_llm" in streaming._STREAMING_NODES
    assert streaming._CHAT_STREAM == "on_chat_model_stream"
    assert streaming._CHAIN_STREAM == "on_chain_stream"


# ---------------------------------------------------------------------------
# VectoraChatApp — construção e bindings
# ---------------------------------------------------------------------------


def test_vectora_app_construct_defaults() -> None:
    from src.ui.app import VectoraChatApp

    app = VectoraChatApp()
    assert app._permission_mode == "ask"
    assert app._user_id == "local"
    assert app._chat_thread_id  # UUID gerado
    assert app._streaming is False


def test_vectora_app_construct_custom() -> None:
    from src.ui.app import VectoraChatApp

    app = VectoraChatApp(
        chat_thread_id="abc-123",
        permission_mode="bypass",
        user_id="bruno",
    )
    assert app._chat_thread_id == "abc-123"
    assert app._permission_mode == "bypass"
    assert app._user_id == "bruno"


def test_vectora_app_bindings_include_shortcuts() -> None:
    from src.ui.app import VectoraChatApp

    keys = {
        getattr(b, "key", b[0] if isinstance(b, tuple) else None)
        for b in VectoraChatApp.BINDINGS
    }
    assert "ctrl+n" in keys
    assert "ctrl+q" in keys


# ---------------------------------------------------------------------------
# StreamHandler — dispatcher
# ---------------------------------------------------------------------------


@dataclass
class _FakeChunk:
    content: str


def _make_app() -> MagicMock:
    """App mock com os hooks que StreamHandler chama."""
    app = MagicMock()
    app.append_token = MagicMock()
    app.append_line = MagicMock()
    app.show_thinking = MagicMock()
    app.show_tool_result = MagicMock()
    app.show_hitl = MagicMock()
    app.begin_response = MagicMock()
    app.end_response = MagicMock()
    return app


async def test_stream_handler_dispatch_token() -> None:
    from src.ui.streaming import StreamHandler

    app = _make_app()
    handler = StreamHandler(app, graph=MagicMock(), thread_id="t1")

    await handler._dispatch(
        {
            "event": "on_chat_model_stream",
            "name": "invoke_llm",
            "data": {"chunk": _FakeChunk(content="hello")},
        }
    )

    app.append_token.assert_called_once_with("hello")


async def test_stream_handler_dispatch_thinking_from_orchestrator() -> None:
    from src.ui.streaming import StreamHandler

    app = _make_app()
    handler = StreamHandler(app, graph=MagicMock(), thread_id="t1")

    await handler._dispatch(
        {
            "event": "on_chain_end",
            "name": "orchestrator",
            "data": {
                "output": {
                    "thinking": {
                        "reason": "User wants code review",
                        "action": "delegate",
                        "delegate_to": "coder",
                    }
                }
            },
        }
    )

    app.show_thinking.assert_called_once_with(
        "User wants code review", "delegate", "coder"
    )


async def test_stream_handler_dispatch_tool_end() -> None:
    from src.ui.streaming import StreamHandler

    app = _make_app()
    handler = StreamHandler(app, graph=MagicMock(), thread_id="t1")

    tool_output = MagicMock(content="ok", status="success")

    await handler._dispatch(
        {
            "event": "on_tool_end",
            "name": "file_read",
            "data": {"output": tool_output},
        }
    )

    app.show_tool_result.assert_called_once()
    args = app.show_tool_result.call_args.args
    assert args[0] == "file_read"
    assert args[2] is False  # is_error


async def test_stream_handler_dispatch_tool_start_appends_line() -> None:
    from src.ui.streaming import StreamHandler

    app = _make_app()
    handler = StreamHandler(app, graph=MagicMock(), thread_id="t1")

    await handler._dispatch({"event": "on_tool_start", "name": "terminal", "data": {}})

    app.append_line.assert_called_once()
    assert "terminal" in app.append_line.call_args.args[0]


async def test_stream_handler_dispatch_interrupt() -> None:
    from src.ui.streaming import StreamHandler

    app = _make_app()
    handler = StreamHandler(app, graph=MagicMock(), thread_id="t1")

    fake_interrupt = MagicMock()
    fake_interrupt.value = {
        "tool_name": "terminal",
        "args_json": '{"cmd": "rm -rf /"}',
        "interrupt_id": "i-42",
    }

    await handler._dispatch(
        {
            "event": "on_chain_stream",
            "name": "LangGraph",
            "data": {"chunk": {"__interrupt__": (fake_interrupt,)}},
        }
    )

    app.show_hitl.assert_called_once()
    args = app.show_hitl.call_args.args
    assert args[0] == "terminal"
    assert args[1] == '{"cmd": "rm -rf /"}'
    assert args[2] == "i-42"


async def test_stream_handler_stream_calls_begin_and_end() -> None:
    from src.ui.streaming import StreamHandler

    app = _make_app()

    async def _no_events(*_a: Any, **_kw: Any):
        return
        yield

    graph = MagicMock()
    graph.astream_events = MagicMock(return_value=_no_events())

    handler = StreamHandler(app, graph=graph, thread_id="t1")
    await handler.stream("hello")

    app.begin_response.assert_called_once()
    app.end_response.assert_called_once()


async def test_stream_handler_stream_recovers_from_errors() -> None:
    from src.ui.streaming import StreamHandler

    app = _make_app()

    async def _raises(*_a: Any, **_kw: Any):
        raise RuntimeError("boom")
        yield  # pragma: no cover

    graph = MagicMock()
    graph.astream_events = MagicMock(return_value=_raises())

    handler = StreamHandler(app, graph=graph, thread_id="t1")
    await handler.stream("hello")

    app.append_line.assert_called()
    assert any("Erro" in c.args[0] for c in app.append_line.call_args_list)
    app.end_response.assert_called_once()


# ---------------------------------------------------------------------------
# HITLModal
# ---------------------------------------------------------------------------


def test_hitl_modal_constructs_with_pretty_json() -> None:
    from src.ui.widgets.hitl import HITLModal

    modal = HITLModal(
        tool_name="terminal",
        args_json='{"cmd": "ls -la"}',
        interrupt_id="i-1",
    )
    assert modal._tool_name == "terminal"
    assert modal._interrupt_id == "i-1"


def test_hitl_modal_handles_invalid_json() -> None:
    from src.ui.widgets.hitl import HITLModal

    # Não deve levantar mesmo com JSON inválido
    modal = HITLModal(tool_name="x", args_json="{not json}", interrupt_id="i")
    assert modal._args_json == "{not json}"
