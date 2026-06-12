"""ChatScreen — tela principal do chat na TUI Vectora.

Contém o layout, manipuladores de eventos e callbacks de streaming que
antes viviam diretamente em ``app.py``. O ``VectoraChatApp`` monta esta
tela na inicialização e delega toda a lógica de UI de chat para ela.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Input, OptionList, Static

from src.ui.components import build_popup_options
from src.ui.components.command_bar import CommandBar
from src.ui.i18n import t
from src.ui.slash_handlers import SlashCommandsMixin
from src.ui.widgets.code_block import CodeBlockWidget
from src.ui.widgets.diff import DiffWidget
from src.ui.widgets.hitl import HITLModal
from src.ui.widgets.thinking import ThinkingWidget

if TYPE_CHECKING:
    from src.ui.streaming import StreamHandler

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


class ChatScreen(SlashCommandsMixin, Screen[None]):
    """Tela principal de chat — layout, input e callbacks de streaming."""

    BINDINGS = [
        Binding("ctrl+n", "new_session", "Nova sessao", show=True),
        Binding("ctrl+l", "clear_messages", "Limpar", show=False),
        Binding("ctrl+comma", "settings", "Config", show=False),
        Binding("ctrl+grave_accent", "workbench", "Workbench", show=False),
        Binding("ctrl+m", "model_picker", "Modelo", show=False),
        Binding("ctrl+u", "usage", "Uso", show=False),
        Binding("ctrl+question_mark", "help_screen", "Ajuda", show=False),
        Binding("ctrl+r", "rewind", "Rewind", show=False),
    ]

    SLASH_COMMANDS: list[tuple[str, str]] = [
        (cmd, t(key)) for cmd, key in _SLASH_COMMAND_KEYS
    ]

    def exit(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """Delega app.exit() para o App pai."""
        self.app.exit(*args, **kwargs)

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

    # ── Layout ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(id="messages")
        with Vertical(id="bottom-area"):
            yield OptionList(id="command-popup")
            with Horizontal(id="input-row"):
                yield Static(">", id="input-prompt")
                yield Input(placeholder=t("tui.input.placeholder"), id="chat-input")
            yield CommandBar(
                permission_mode=self._permission_mode,
                user_id=self._user_id,
                id="cmd-bar",
            )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def on_mount(self) -> None:
        from src.graph import get_user_agent
        from src.ui.streaming import StreamHandler as _StreamHandler

        self._graph = await get_user_agent(self._user_id)
        self._stream_handler = _StreamHandler(
            screen=self,
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

    async def action_settings(self) -> None:
        from src.ui.screens.settings_screen import SettingsScreen

        await self.app.push_screen(SettingsScreen())

    async def action_workbench(self) -> None:
        from src.ui.screens.workbench_screen import WorkbenchScreen

        await self.app.push_screen(WorkbenchScreen())

    async def action_model_picker(self) -> None:
        from src.ui.screens.model_picker_screen import ModelPickerScreen

        await self.app.push_screen(ModelPickerScreen())

    async def action_usage(self) -> None:
        from src.ui.screens.usage_screen import UsageScreen

        await self.app.push_screen(UsageScreen())

    async def action_help_screen(self) -> None:
        from src.ui.screens.help_screen import HelpScreen

        await self.app.push_screen(HelpScreen())

    async def action_rewind(self) -> None:
        from src.ui.screens.rewind_screen import RewindScreen

        def on_result(cp_id: str | None) -> None:
            if cp_id:
                self.run_worker(self._do_rewind(cp_id), exclusive=False, thread=False)

        await self.app.push_screen(RewindScreen(self._chat_thread_id), on_result)

    async def _do_rewind(self, checkpoint_id: str) -> None:
        try:
            import git as gitpkg  # type: ignore[import-untyped]

            from src.services.checkpoint import restore_git_checkpoint
            from src.services.workspace import workspace_registry

            workspaces = workspace_registry.list_all()
            if not workspaces:
                self.append_line(f"[red]{t('tui.rewind.no_workspace')}[/red]")
                return
            ws = workspaces[0]
            repo = gitpkg.Repo(ws.cwd, search_parent_directories=True)
            restore_git_checkpoint(repo, checkpoint_id)
            area = self.query_one("#messages", ScrollableContainer)
            await area.remove_children()
            await area.mount(
                Static(
                    f"[bold #60a5fa]Vectora[/bold #60a5fa] [dim]— "
                    f"{t('tui.rewind.done')}[/dim]",
                    classes="msg-system",
                )
            )
        except Exception as exc:
            self.append_line(f"[red]{t('tui.rewind.error', error=exc)}[/red]")

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

    async def action_clear_messages(self) -> None:
        area = self.query_one("#messages", ScrollableContainer)
        await area.remove_children()

    def on_command_bar_chip_pressed(self, event: CommandBar.ChipPressed) -> None:
        """Abre a tela correspondente ao chip clicado."""
        chip = event.chip_id
        if chip == "chip-mode":
            self.run_worker(self.action_settings(), exclusive=False, thread=False)
        elif chip == "chip-model":
            self.run_worker(self.action_model_picker(), exclusive=False, thread=False)
        elif chip == "chip-branch":
            self.run_worker(self.action_workbench(), exclusive=False, thread=False)

    # ── Stream callbacks (chamados pelo StreamHandler) ────────────────────────

    def begin_response(self) -> None:
        self._response_buffer = "[bold #60a5fa]◈ vectora[/bold #60a5fa] "
        self._current_response = Static(self._response_buffer, classes="msg-assistant")
        area = self.query_one("#messages", ScrollableContainer)
        area.mount(self._current_response)

    def end_response(self) -> None:
        self._current_response = None
        self._response_buffer = ""
        area = self.query_one("#messages", ScrollableContainer)
        area.scroll_end(animate=False)

    def append_token(self, token: str) -> None:
        self._response_buffer += token
        if self._current_response is not None:
            self._current_response.update(self._response_buffer)
            area = self.query_one("#messages", ScrollableContainer)
            area.scroll_end(animate=False)

    def append_line(self, text: str) -> None:
        area = self.query_one("#messages", ScrollableContainer)
        area.mount(Static(text, classes="msg-system"))
        area.scroll_end(animate=False)

    def show_thinking(
        self,
        reason: str,
        action: str = "respond",
        delegate_to: str | None = None,
    ) -> None:
        area = self.query_one("#messages", ScrollableContainer)
        area.mount(ThinkingWidget(reason, action, delegate_to))

    def show_tool_result(self, tool_name: str, content: str, is_error: bool) -> None:
        area = self.query_one("#messages", ScrollableContainer)
        if not is_error and content.startswith(("---", "+++ ")):
            area.mount(DiffWidget(tool_name, content))
        else:
            area.mount(CodeBlockWidget(tool_name, content, is_error))

    def show_hitl(self, tool_name: str, args_json: str, interrupt_id: str) -> None:
        def on_result(decision: str | None) -> None:
            result = decision or "reject"
            if self._stream_handler:
                self._streaming = True
                self.run_worker(
                    self._resume_after_hitl(result),
                    exclusive=True,
                    thread=False,
                )

        self.app.push_screen(HITLModal(tool_name, args_json, interrupt_id), on_result)

    async def _resume_after_hitl(self, decision: str) -> None:
        try:
            if self._stream_handler:
                await self._stream_handler.resume(decision)
        finally:
            self._streaming = False
