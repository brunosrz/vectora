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

from src.ui.streaming import StreamHandler
from src.ui.widgets.code_block import CodeBlockWidget
from src.ui.widgets.diff import DiffWidget
from src.ui.widgets.hitl import HITLModal
from src.ui.widgets.thinking import ThinkingWidget

_HELP_TEXT = """\
[bold]Comandos disponíveis:[/bold]
  [cyan]/help[/cyan]              Esta ajuda
  [cyan]/new[/cyan]               Nova sessao
  [cyan]/clear[/cyan]             Limpar mensagens
  [cyan]/session <id>[/cyan]      Trocar de sessao
  [cyan]/sessions[/cyan]          Listar sessoes recentes
  [cyan]/model[/cyan]             Listar modelos disponiveis
  [cyan]/model <nome>[/cyan]      Trocar modelo
  [cyan]/debug[/cyan]             Ver nivel de verbosidade atual
  [cyan]/debug <0-5>[/cyan]       Definir verbosidade (0=Silencio, 5=Full)
  [cyan]/rag[/cyan]               Status do pipeline RAG
  [cyan]/traces[/cyan]            Ultimos traces do agente
  [cyan]/workspaces[/cyan]        Listar workspaces
  [cyan]/quit[/cyan]              Sair"""

_VERBOSITY_LABELS: dict[int, str] = {
    0: "Silencio",
    1: "Roteamento",
    2: "Status tools",
    3: "Standard",
    4: "Verbose",
    5: "Full",
}


class VectoraChatApp(App[None]):
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
        ("/rag add", "Indexa pasta ou arquivo no RAG"),
        ("/rag list", "Exibe estatísticas do RAG"),
        ("/workspace", "Troca o workspace ativo"),
        ("/branch", "Cria ou troca de branch"),
        ("/pr", "Abre um pull request"),
        ("/model", "Troca o modelo de linguagem"),
        ("/clear", "Limpa o histórico da thread"),
        ("/export", "Exporta a conversa (md ou json)"),
        ("/share", "Gera URL de leitura da thread"),
        ("/auth logout", "Encerra a sessão"),
        ("/help", "Lista todos os comandos"),
    ]

    DEFAULT_CSS = """
    Screen {
        background: #0a0e1a;
    }

    Header {
        background: #0a0e1a;
        color: #60a5fa;
        height: 1;
    }

    #messages {
        width: 1fr;
        height: 1fr;
        padding: 1 2;
        background: #0a0e1a;
        scrollbar-size: 1 1;
        scrollbar-color: #1e3a5f #0a0e1a;
    }

    #bottom-area {
        dock: bottom;
        height: auto;
        background: #0a0e1a;
        border-top: solid #1e2d40;
    }

    #command-popup {
        display: none;
        background: #0d1525;
        border: round #3b82f6;
        height: auto;
        max-height: 8;
        margin: 0 2;
    }

    #input-row {
        height: 3;
        padding: 0;
        align: left middle;
    }

    #input-prompt {
        width: 3;
        color: #3b82f6;
        content-align: center middle;
        text-style: bold;
    }

    Input {
        width: 1fr;
        background: #0a0e1a;
        border: tall #0a0e1a;
        color: #e2e8f0;
        padding: 0 2 0 0;
        margin: 0 1 0 0;
    }

    Input:focus {
        border: tall #3b82f6;
        background: #0a0e1a;
    }

    #status-bar {
        height: 1;
        background: #0d1525;
        padding: 0 2;
    }

    #status-info {
        width: 1fr;
        color: #374151;
        content-align: left middle;
    }

    #status-keys {
        width: auto;
        color: #1e3a5f;
        content-align: right middle;
    }

    .msg-user {
        color: #e2e8f0;
        margin: 1 0 0 0;
    }

    .msg-assistant {
        color: #93c5fd;
        margin: 0 0 1 0;
    }

    .msg-system {
        color: #374151;
        text-style: italic;
    }

    OptionList {
        background: #0d1525;
        padding: 0;
        scrollbar-size: 1 1;
    }

    OptionList > .option-list--option {
        padding: 0 1;
        height: 1;
        color: #a0aec0;
    }

    OptionList > .option-list--option-highlighted {
        background: #1e3a5f;
        color: #60a5fa;
    }
    """

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
                yield Input(placeholder="Mensagem...", id="chat-input")
            with Horizontal(id="status-bar"):
                yield Static("", id="status-info")
                yield Static("^N Nova  ^L Limpar  ^Q Sair", id="status-keys")

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
                f"[bold #60a5fa]Vectora[/bold #60a5fa] [dim]— sessão {self._chat_thread_id[:8]}[/dim]",
                classes="msg-system",
            )
        )
        await area.mount(
            Static(
                "[dim]Digite ou [bold #3b82f6]/[/bold #3b82f6] para comandos · "
                "[bold #3b82f6]^N[/bold #3b82f6] nova sessão · "
                "[bold #3b82f6]^Q[/bold #3b82f6] sair[/dim]",
                classes="msg-system",
            )
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

        options = self._build_popup_options(text)
        popup.clear_options()
        for opt in options:
            popup.add_option(opt)
        popup.display = bool(options)

    def _build_popup_options(self, text: str) -> list[Option]:
        """Builds popup options based on input text.

        - "/" or "/cmd" → list matching slash commands.
        - "/model " or "/model <prefix>" → list matching models from settings.
        """
        from src.settings import AVAILABLE_MODELS

        stripped = text.rstrip()
        if stripped == "/model" or text.startswith("/model "):
            prefix = text[len("/model ") :].strip().lower() if " " in text else ""
            opts: list[Option] = []
            for provider, models in AVAILABLE_MODELS.items():
                for model in models:
                    if not prefix or prefix in model.lower():
                        label = f" [b]{model:<32}[/b] [dim]{provider}[/dim]"
                        opts.append(Option(label, id=f"/model {model}"))
            return opts

        return [
            Option(f" {cmd:<14}  {desc}", id=cmd)
            for cmd, desc in self.SLASH_COMMANDS
            if cmd.startswith(text)
        ]

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

    # ── Slash command dispatcher ──────────────────────────────────────────────

    async def _handle_slash(self, text: str) -> None:
        parts = text[1:].strip().split(None, 1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("quit", "q", "sair", "exit"):
            self.exit()

        elif cmd in ("help", "h", "ajuda", "list", "tools"):
            self.append_line(_HELP_TEXT)

        elif cmd == "new":
            await self.action_new_session()

        elif cmd == "clear":
            await self.action_clear_messages()

        elif cmd in ("sessions", "sessoes"):
            await self._cmd_sessions()

        elif cmd == "session":
            await self._cmd_session(args)

        elif cmd == "model":
            await self._cmd_model(args)

        elif cmd == "debug":
            await self._cmd_debug(args)

        elif cmd == "rag":
            await self._cmd_rag()

        elif cmd == "traces":
            await self._cmd_traces()

        elif cmd in ("workspaces", "workspace"):
            await self._cmd_workspaces()

        else:
            self.append_line(
                f"[yellow]Comando desconhecido: /{cmd}. Use /help para ver os comandos.[/yellow]"
            )

    # ── Slash command handlers ────────────────────────────────────────────────

    async def _cmd_sessions(self) -> None:
        try:
            import json
            from pathlib import Path

            import aiosqlite

            db_path = Path.home() / ".vectora" / "checkpoints.db"
            if not db_path.exists():
                self.append_line("[dim]Nenhuma sessao encontrada.[/dim]")
                return

            async with aiosqlite.connect(str(db_path)) as db:
                async with db.execute(
                    "SELECT thread_id, last_activity, extra FROM vectora_sessions "
                    "ORDER BY last_activity DESC LIMIT 10"
                ) as cur:
                    rows = await cur.fetchall()

            if not rows:
                self.append_line("[dim]Nenhuma sessao encontrada.[/dim]")
                return

            lines = ["[bold]Sessoes recentes:[/bold]"]
            for thread_id, last_activity, extra_json in rows:
                try:
                    extra = json.loads(extra_json or "{}")
                    title = extra.get("title", "")
                except Exception:
                    title = ""
                active = (
                    " [green]<- atual[/green]"
                    if thread_id == self._chat_thread_id
                    else ""
                )
                ts = last_activity[:16] if last_activity else "?"
                label = f" {title}" if title else ""
                lines.append(f"  [cyan]{thread_id}[/cyan] {ts}{label}{active}")
            self.append_line("\n".join(lines))
        except Exception as exc:
            self.append_line(f"[red]Erro ao listar sessoes: {exc}[/red]")

    async def _cmd_session(self, args: str) -> None:
        if not args:
            self.append_line(f"[dim]Sessao atual: {self._chat_thread_id}[/dim]")
            return
        self._chat_thread_id = args
        if self._stream_handler:
            self._stream_handler._thread_id = args
        self.append_line(f"[green]Sessao trocada para: {args}[/green]")

    async def _cmd_model(self, args: str) -> None:
        from src.services.runtime_settings import apply_model_change
        from src.settings import AVAILABLE_MODELS, find_provider_for_model

        if not args:
            lines = [
                "[bold]Modelos disponíveis:[/bold]  [dim](use /model <nome>)[/dim]"
            ]
            for provider, models in AVAILABLE_MODELS.items():
                lines.append(f"  [bold cyan]{provider}[/bold cyan]")
                lines.extend(f"    [dim]·[/dim] {model}" for model in models)
            self.append_line("\n".join(lines))
        else:
            provider = find_provider_for_model(args)
            if provider:
                apply_model_change(provider, args)
                self.append_line(
                    f"[green]✓ Modelo alterado para: {args} ({provider})[/green]"
                )
                self.query_one("#status-info", Static).update(self._build_status())
            else:
                self.append_line(
                    f"[red]✗ Modelo não encontrado: {args}[/red]  "
                    f"[dim](use /model para listar)[/dim]"
                )

    async def _cmd_debug(self, args: str) -> None:
        from src.services.runtime_settings import runtime_settings

        if not args:
            v = runtime_settings.verbosity
            self.append_line(
                f"[dim]Verbosidade atual: {v} ({_VERBOSITY_LABELS.get(v, '?')})[/dim]"
            )
            return
        try:
            level = int(args)
            if level < 0 or level > 5:
                raise ValueError
            runtime_settings.set_verbosity(level)
            self.append_line(
                f"[green]Verbosidade definida: {level} "
                f"({_VERBOSITY_LABELS.get(level, '?')})[/green]"
            )
        except ValueError:
            self.append_line("[red]Nivel invalido. Use um numero de 0 a 5.[/red]")

    async def _cmd_rag(self) -> None:
        try:
            from src.services.background import get_background_worker

            worker = await get_background_worker()
            queue = await worker._get_queue()
            stats = await queue.get_stats() if queue is not None else {}
            lines = [
                "[bold]RAG Pipeline:[/bold]",
                f"  Pendentes:    {stats.get('pending', 0)}",
                f"  Processando:  {stats.get('processing', 0)}",
                f"  Sucesso:      {stats.get('success', 0)}",
                f"  Falhas:       {stats.get('failed', 0)}",
            ]
            self.append_line("\n".join(lines))
        except Exception as exc:
            self.append_line(f"[yellow]RAG stats indisponivel: {exc}[/yellow]")

    async def _cmd_traces(self) -> None:
        try:
            from src.services.tracer import tracer

            spans = await tracer.get_recent(n=10)
            if not spans:
                self.append_line("[dim]Nenhum trace encontrado.[/dim]")
                return
            lines = ["[bold]Ultimos traces:[/bold]"]
            for s in spans:
                node = s.get("node", "?")
                ms = s.get("duration_ms")
                ms_str = f"{ms:.0f}ms" if ms else "?"
                status = s.get("status", "?")
                color = "green" if status == "ok" else "red"
                lines.append(
                    f"  [{color}]{status}[/{color}] [cyan]{node}[/cyan] {ms_str}"
                )
            self.append_line("\n".join(lines))
        except Exception as exc:
            self.append_line(f"[yellow]Traces indisponivel: {exc}[/yellow]")

    async def _cmd_workspaces(self) -> None:
        try:
            from src.services.workspace import workspace_registry

            workspaces = workspace_registry.list_all()
            if not workspaces:
                self.append_line("[dim]Nenhum workspace registrado.[/dim]")
                return
            lines = ["[bold]Workspaces:[/bold]"]
            for ws in workspaces:
                trusted = (
                    "[green]confiado[/green]"
                    if getattr(ws, "trusted", False)
                    else "[dim]nao confiado[/dim]"
                )
                name = getattr(ws, "name", str(getattr(ws, "id", ws)))
                path = getattr(ws, "cwd", "")
                lines.append(f"  {trusted} [cyan]{name}[/cyan] {path}")
            self.append_line("\n".join(lines))
        except Exception as exc:
            self.append_line(f"[yellow]Workspaces indisponivel: {exc}[/yellow]")

    # ── Actions ───────────────────────────────────────────────────────────────

    async def action_new_session(self) -> None:
        self._chat_thread_id = str(uuid.uuid4())
        area = self.query_one("#messages", ScrollableContainer)
        await area.remove_children()
        await area.mount(
            Static(
                f"[bold #60a5fa]Vectora[/bold #60a5fa] [dim]— nova sessão {self._chat_thread_id[:8]}[/dim]",
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
        import os
        from pathlib import Path

        cwd = Path.cwd()
        home = Path.home()
        try:
            path_str = "~/" + str(cwd.relative_to(home))
        except ValueError:
            path_str = str(cwd)

        branch = ""
        try:
            import subprocess  # nosec B404

            result = subprocess.run(
                ["git", "branch", "--show-current"],  # noqa: S607  # nosec B603 B607
                capture_output=True,
                text=True,
                check=False,
                cwd=str(cwd),
                timeout=2,
            )
            branch = result.stdout.strip()
        except Exception:
            pass

        model = (
            os.environ.get("GOOGLE_MODEL")
            or os.environ.get("OPENAI_MODEL")
            or os.environ.get("ANTHROPIC_MODEL")
            or os.environ.get("COHERE_MODEL")
            or ""
        )

        sep = "  ·  "
        parts: list[str] = [path_str]
        if branch:
            parts.append(branch)
        if model:
            parts.append(model)
        parts.append(self._permission_mode)
        return sep.join(parts)

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
