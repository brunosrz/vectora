"""VectoraChatApp — Textual TUI (E7).

Layout:
  ┌─────────────────────────────────────────────┐
  │  VECTORA CHAT                               │  Header
  ├────────────────────────────┬────────────────┤
  │  Messages (ScrollableArea) │  Side Panel    │
  │  (Static widgets per msg)  │  (Tabs)        │
  ├────────────────────────────┴────────────────┤
  │  [Input]                        [mode]      │  Input row
  └─────────────────────────────────────────────┘
"""

from __future__ import annotations

import uuid
from typing import Any

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import (
    Header,
    Input,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option

from src.services.runtime_settings import runtime_settings
from src.ui.components.slash_popup import build_popup_options
from src.ui.components.status_bar import build_status_text
from src.ui.i18n import t
from src.ui.slash_handlers import SlashCommandsMixin
from src.ui.streaming import StreamHandler
from src.ui.theme import get_theme_css
from src.ui.widgets.code_block import CodeBlockWidget
from src.ui.widgets.diff import DiffWidget
from src.ui.widgets.hitl import HITLModal
from src.ui.widgets.thinking import ThinkingWidget

# Comandos do popup de autocomplete (forma de uso, chave i18n da descrição —
# ver `tui.popup.cmd.*` em `src/ui/i18n/strings.csv`). Resolvidos para o
# idioma corrente na definição da classe — mesma limitação documentada em
# `src/ui/theme.py` quanto a troca de idioma sem reiniciar a TUI.
_SLASH_COMMAND_KEYS: list[tuple[str, str]] = [
    ("/rag add", "tui.popup.cmd.rag_add"),
    ("/rag list", "tui.popup.cmd.rag_list"),
    ("/workspace", "tui.popup.cmd.workspace"),
    ("/branch", "tui.popup.cmd.branch"),
    ("/pr", "tui.popup.cmd.pr"),
    ("/model", "tui.popup.cmd.model"),
    ("/clear", "tui.popup.cmd.clear"),
    ("/export", "tui.popup.cmd.export"),
    ("/share", "tui.popup.cmd.share"),
    ("/auth logout", "tui.popup.cmd.auth_logout"),
    ("/help", "tui.popup.cmd.help"),
]


class VectoraChatApp(SlashCommandsMixin, App[None]):
    """Vectora TUI — split-layout interactive chat.

    Connects directly to the compiled LangGraph graph via
    ``agent_factory.get_user_agent()`` (no HTTP layer).
    """

    TITLE = "Vectora"

    BINDINGS = [
        Binding("ctrl+n", "new_session", "Nova sessao", show=True),
        Binding("ctrl+l", "clear_messages", "Limpar", show=False),
        Binding("ctrl+q", "quit", "Sair", show=True),
        Binding("ctrl+c", "quit", "Sair", show=False),
    ]

    SLASH_COMMANDS: list[tuple[str, str]] = [
        (cmd, t(key)) for cmd, key in _SLASH_COMMAND_KEYS
    ]

    # CSS resolvido a partir de `runtime_settings.theme` (persistido em
    # `~/.vectora/settings.json`, trocável com `/theme`). Textual lê
    # `DEFAULT_CSS` como atributo de classe — troca em runtime exige reabrir
    # a TUI até existir um mecanismo de `refresh_css` dedicado (ver TODO em
    # `src/ui/theme.py`).
    DEFAULT_CSS = get_theme_css(runtime_settings.theme)

    def __init__(
        self,
        chat_thread_id: str | None = None,
        permission_mode: str = "ask",
        user_id: str = "local",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._chat_thread_id = chat_thread_id or str(uuid.uuid4())
        self._permission_mode = permission_mode
        self._user_id = user_id
        self._stream_handler: StreamHandler | None = None
        self._streaming = False
        self._current_response: Static | None = None
        self._response_buffer = ""

    # ── Compose ──────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(id="messages")
        with Vertical(id="bottom-area"):
            yield OptionList(id="command-popup")
            with Horizontal(id="input-row"):
                yield Static(">", id="input-prompt")
                yield Input(placeholder=t("tui.input.placeholder"), id="chat-input")
            with Horizontal(id="status-bar"):
                yield Static("", id="status-info")
                yield Static(t("tui.status.keys_hint"), id="status-keys")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def on_mount(self) -> None:
        from src.services.agent_factory import get_user_agent

        self._graph = await get_user_agent(self._user_id)
        self._stream_handler = StreamHandler(
            app=self,
            graph=self._graph,
            thread_id=self._chat_thread_id,
            permission_mode=self._permission_mode,
            user_id=self._user_id,
        )
        area = self.query_one("#messages", ScrollableContainer)
        await area.mount(
            Static(
                f"[bold #60a5fa]Vectora[/bold #60a5fa] [dim]— "
                f"{t('tui.welcome.session', id=self._chat_thread_id[:8])}[/dim]",
                classes="msg-system",
            )
        )
        await area.mount(
            Static(f"[dim]{t('tui.welcome.hint')}[/dim]", classes="msg-system")
        )
        self.query_one("#status-info", Static).update(self._build_status())
        self.query_one("#chat-input", Input).focus()

    # ── Input ─────────────────────────────────────────────────────────────────

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text or self._streaming:
            return
        event.input.clear()

        if text.startswith("/"):
            self.run_worker(self._handle_slash(text), exclusive=False, thread=False)
            return

        area = self.query_one("#messages", ScrollableContainer)
        await area.mount(
            Static(
                f"[bold white on #1e3a5f] você [/bold white on #1e3a5f] {text}",
                classes="msg-user",
            )
        )
        area.scroll_end(animate=False)

        self._streaming = True
        self.run_worker(self._do_stream(text), exclusive=True, thread=False)

    def on_input_changed(self, event: Input.Changed) -> None:
        popup = self.query_one("#command-popup", OptionList)
        text = event.value
        if not text.startswith("/"):
            popup.display = False
            return

        options = build_popup_options(text, self.SLASH_COMMANDS)
        popup.clear_options()
        for opt in options:
            popup.add_option(opt)
        popup.display = bool(options)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        inp = self.query_one("#chat-input", Input)
        selected = str(event.option.id)
        self.query_one("#command-popup", OptionList).display = False
        # Sub-comandos completos (com espaço) executam imediatamente; comandos
        # parciais ganham espaço para o usuário continuar digitando args.
        if " " in selected:
            inp.value = ""
            self.run_worker(self._handle_slash(selected), exclusive=False, thread=False)
        else:
            inp.value = selected + " "
        inp.focus()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.query_one("#command-popup", OptionList).display = False

    def on_click(self, event: events.Click) -> None:
        if not isinstance(event.widget, (Input, OptionList)):
            self.query_one("#chat-input", Input).focus()

    async def _do_stream(self, text: str) -> None:
        try:
            if self._stream_handler:
                await self._stream_handler.stream(text)
        finally:
            self._streaming = False

    # ── Actions ───────────────────────────────────────────────────────────────

    async def action_new_session(self) -> None:
        self._chat_thread_id = str(uuid.uuid4())
        area = self.query_one("#messages", ScrollableContainer)
        await area.remove_children()
        await area.mount(
            Static(
                f"[bold #60a5fa]Vectora[/bold #60a5fa] [dim]— "
                f"{t('tui.welcome.new_session', id=self._chat_thread_id[:8])}[/dim]",
                classes="msg-system",
            )
        )
        if self._stream_handler:
            self._stream_handler._thread_id = self._chat_thread_id
        self.query_one("#status-info", Static).update(self._build_status())

    async def action_clear_messages(self) -> None:
        area = self.query_one("#messages", ScrollableContainer)
        await area.remove_children()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_status(self) -> str:
        """Builds the bottom status bar text (path · branch · model · mode)."""
        return build_status_text(self._permission_mode)

    # ── Stream callbacks (called from StreamHandler on the same event loop) ───

    def begin_response(self) -> None:
        """Creates a new streaming response widget."""
        self._response_buffer = "[bold #60a5fa]◈ vectora[/bold #60a5fa] "
        self._current_response = Static(self._response_buffer, classes="msg-assistant")
        area = self.query_one("#messages", ScrollableContainer)
        area.mount(self._current_response)

    def end_response(self) -> None:
        """Finalizes the current streaming response."""
        self._current_response = None
        self._response_buffer = ""
        area = self.query_one("#messages", ScrollableContainer)
        area.scroll_end(animate=False)

    def append_token(self, token: str) -> None:
        """Appends a streaming token to the current response widget."""
        self._response_buffer += token
        if self._current_response is not None:
            self._current_response.update(self._response_buffer)
            area = self.query_one("#messages", ScrollableContainer)
            area.scroll_end(animate=False)

    def append_line(self, text: str) -> None:
        """Mounts a new system/status line to the messages area."""
        area = self.query_one("#messages", ScrollableContainer)
        area.mount(Static(text, classes="msg-system"))
        area.scroll_end(animate=False)

    def show_thinking(
        self,
        reason: str,
        action: str = "respond",
        delegate_to: str | None = None,
    ) -> None:
        """Shows an orchestrator reasoning block using ThinkingWidget."""
        area = self.query_one("#messages", ScrollableContainer)
        area.mount(ThinkingWidget(reason, action, delegate_to))

    def show_tool_result(self, tool_name: str, content: str, is_error: bool) -> None:
        """Shows a tool result using CodeBlockWidget or DiffWidget."""
        area = self.query_one("#messages", ScrollableContainer)
        if not is_error and content.startswith(("---", "+++ ")):
            area.mount(DiffWidget(tool_name, content))
        else:
            area.mount(CodeBlockWidget(tool_name, content, is_error))

    def show_hitl(self, tool_name: str, args_json: str, interrupt_id: str) -> None:
        """Shows HITL modal and resumes after user decision."""

        def on_result(decision: str | None) -> None:
            result = decision or "reject"
            if self._stream_handler:
                self._streaming = True
                self.run_worker(
                    self._resume_after_hitl(result),
                    exclusive=True,
                    thread=False,
                )

        self.push_screen(HITLModal(tool_name, args_json, interrupt_id), on_result)

    async def _resume_after_hitl(self, decision: str) -> None:
        try:
            if self._stream_handler:
                await self._stream_handler.resume(decision)
        finally:
            self._streaming = False
