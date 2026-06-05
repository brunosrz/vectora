"""LangGraph astream_events v2 -> Textual widget dispatcher (E7)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage

if TYPE_CHECKING:
    from src.ui.app import VectoraChatApp

logger = logging.getLogger(__name__)

# LangGraph event type strings
_CHAIN_END = "on_chain_end"
_CHAIN_STREAM = "on_chain_stream"
_CHAT_STREAM = "on_chat_model_stream"
_TOOL_START = "on_tool_start"
_TOOL_END = "on_tool_end"

# Nodes that emit user-facing tokens
_STREAMING_NODES = {"invoke_llm", "search_agent", "coder_agent", "rag_agent"}


class StreamHandler:
    """Handles ``astream_events v2`` from a compiled LangGraph graph.

    Used inside a ``thread=False`` async Worker — direct app method
    calls are safe because everything runs on the same event loop.
    """

    def __init__(
        self,
        app: VectoraChatApp,
        graph: Any,
        thread_id: str,
        permission_mode: str = "ask",
        user_id: str = "local",
    ) -> None:
        self._app = app
        self._graph = graph
        self._thread_id = thread_id
        self._permission_mode = permission_mode
        self._user_id = user_id

    async def stream(self, text: str) -> None:
        """Stream a user message and dispatch events to the TUI."""
        config: dict[str, Any] = {
            "configurable": {
                "thread_id": self._thread_id,
                "user_id": self._user_id,
                "permission_mode": self._permission_mode,
            },
            "recursion_limit": 50,
        }

        self._app.begin_response()

        try:
            async for event in self._graph.astream_events(
                {"messages": [HumanMessage(content=text)]},
                config=config,
                version="v2",
            ):
                await self._dispatch(event)
        except Exception as exc:
            logger.exception("stream: erro inesperado")
            self._app.append_line(f"[red]Erro: {exc}[/red]")

        self._app.end_response()

    async def resume(self, decision: str) -> None:
        """Resume a paused HITL execution."""
        from langgraph.types import Command

        config: dict[str, Any] = {
            "configurable": {
                "thread_id": self._thread_id,
                "user_id": self._user_id,
            },
            "recursion_limit": 50,
        }

        resume_value = {"action": "approve" if decision == "approve" else "reject"}

        self._app.begin_response()

        try:
            async for event in self._graph.astream_events(
                Command(resume=resume_value),
                config=config,
                version="v2",
            ):
                await self._dispatch(event)
        except Exception as exc:
            logger.exception("resume: erro inesperado")
            self._app.append_line(f"[red]Erro ao retomar: {exc}[/red]")

        self._app.end_response()

    async def _dispatch(self, event: dict[str, Any]) -> None:
        event_type = event.get("event", "")
        name = event.get("name", "")
        data = event.get("data", {}) or {}

        if event_type == _CHAT_STREAM and name in _STREAMING_NODES:
            chunk = data.get("chunk")
            if chunk is not None:
                content = getattr(chunk, "content", None)
                if content and isinstance(content, str):
                    self._app.append_token(content)

        elif event_type == _CHAIN_END and name == "orchestrator":
            self._handle_orchestrator_end(event)

        elif event_type == _CHAIN_STREAM:
            chunk = data.get("chunk")
            if isinstance(chunk, dict) and "__interrupt__" in chunk:
                self._handle_interrupt(chunk["__interrupt__"])

        elif event_type == _TOOL_START:
            self._app.append_line(f"[dim cyan]⚙ {name}[/dim cyan]")

        elif event_type == _TOOL_END:
            output = data.get("output")
            if output is not None:
                content = getattr(output, "content", None) or str(output)
                is_error = getattr(output, "status", "") == "error"
                self._app.show_tool_result(name, str(content)[:1000], is_error)

    def _handle_orchestrator_end(self, event: dict[str, Any]) -> None:
        data = event.get("data", {}) or {}
        output = data.get("output")
        if output is None:
            return

        candidate: dict[str, Any] | None = None
        if isinstance(output, dict):
            candidate = output
        elif hasattr(output, "update") and isinstance(
            getattr(output, "update", None), dict
        ):
            candidate = output.update  # type: ignore[assignment]

        if candidate:
            thinking = candidate.get("thinking")
            if isinstance(thinking, dict):
                reason = thinking.get("reason", "")
                action = thinking.get("action", "respond")
                delegate_to = thinking.get("delegate_to")
                if reason:
                    self._app.show_thinking(reason, action, delegate_to)

    def _handle_interrupt(self, interrupts: Any) -> None:
        """LangGraph emite `tuple[Interrupt, ...]` em `__interrupt__`."""
        if not interrupts:
            return
        if isinstance(interrupts, (list, tuple)):
            interrupt = interrupts[0]
        else:
            interrupt = interrupts
        value = (
            getattr(interrupt, "value", interrupt)
            if not isinstance(interrupt, dict)
            else interrupt
        )
        tool_name = (
            value.get("tool_name", "tool") if isinstance(value, dict) else str(value)
        )
        args_json = value.get("args_json", "{}") if isinstance(value, dict) else "{}"
        interrupt_id = (
            value.get("interrupt_id", "0") if isinstance(value, dict) else "0"
        )
        self._app.show_hitl(tool_name, args_json, interrupt_id)
