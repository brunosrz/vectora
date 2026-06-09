"""Dispatcher e handlers dos comandos `/slash` da Vectora TUI.

Isola "o que cada `/comando` faz" de "como a tela é montada":
`SlashCommandsMixin` espera ser combinado com `App` (ou algo compatível)
que exponha:

  - `self._chat_thread_id: str`, `self._stream_handler: StreamHandler | None`
  - `self.append_line(text: str) -> None` (mount de linha na área de mensagens)
  - `self.action_new_session()` / `self.action_clear_messages()`
  - `self.query_one(...)` (herdado de `App`)

Ver `VectoraChatApp` em `app.py` — única classe concreta que usa este mixin.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.widgets import Static

from src.ui.i18n import t

if TYPE_CHECKING:
    from src.ui.streaming import StreamHandler

# Nível de verbosidade -> chave i18n do rótulo (ver `tui.verbosity.*` no CSV).
_VERBOSITY_KEYS: dict[int, str] = {
    0: "tui.verbosity.silent",
    1: "tui.verbosity.routing",
    2: "tui.verbosity.tool_status",
    3: "tui.verbosity.standard",
    4: "tui.verbosity.verbose",
    5: "tui.verbosity.full",
}


def _verbosity_label(level: int) -> str:
    key = _VERBOSITY_KEYS.get(level)
    return t(key) if key else "?"


# Comandos embutidos exibidos por `/help` — (forma de uso, chave i18n da
# descrição). A ordem aqui é a ordem de exibição.
_HELP_ENTRIES: list[tuple[str, str]] = [
    ("/help", "tui.help.cmd.help"),
    ("/new", "tui.help.cmd.new"),
    ("/clear", "tui.help.cmd.clear"),
    ("/session <id>", "tui.help.cmd.session"),
    ("/sessions", "tui.help.cmd.sessions"),
    ("/model", "tui.help.cmd.model_list"),
    ("/model <nome>", "tui.help.cmd.model_set"),
    ("/debug", "tui.help.cmd.debug_show"),
    ("/debug <0-5>", "tui.help.cmd.debug_set"),
    ("/rag", "tui.help.cmd.rag"),
    ("/traces", "tui.help.cmd.traces"),
    ("/workspaces", "tui.help.cmd.workspaces"),
    ("/theme <dark|light|system>", "tui.help.cmd.theme"),
    ("/quit", "tui.help.cmd.quit"),
]


def build_help_text() -> str:
    """Monta o texto de `/help` traduzido, alinhando comando e descrição.

    Construído em runtime (em vez de uma string `_HELP_TEXT` estática) para
    que a tradução siga `runtime_settings.language` sem exigir reinício —
    cada chamada a `/help` resolve o idioma corrente.
    """
    lines = [f"[bold]{t('tui.help.title')}[/bold]"]
    for usage, key in _HELP_ENTRIES:
        lines.append(f"  [cyan]{usage:<16}[/cyan] {t(key)}")
    return "\n".join(lines)


class SlashCommandsMixin:
    """Dispatcher `/comando` + handlers — combinado em `VectoraChatApp`."""

    # Atributos/métodos fornecidos por `VectoraChatApp`/`App` em tempo de
    # execução — declarados aqui só para o type checker enxergar o "contrato"
    # que este mixin espera do hospedeiro (a implementação real vive lá).
    if TYPE_CHECKING:
        _chat_thread_id: str
        _stream_handler: StreamHandler | None

        def append_line(self, text: str) -> None: ...
        def action_new_session(self) -> Any: ...
        def action_clear_messages(self) -> Any: ...
        def exit(self, *_args: Any, **_kwargs: Any) -> None: ...
        def query_one(self, *_args: Any, **_kwargs: Any) -> Any: ...
        def _build_status(self) -> str: ...

    # ── Dispatcher ────────────────────────────────────────────────────────────

    async def _handle_slash(self, text: str) -> None:
        parts = text[1:].strip().split(None, 1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("quit", "q", "sair", "exit"):
            self.exit()

        elif cmd in ("help", "h", "ajuda", "list", "tools"):
            self.append_line(build_help_text())

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

        elif cmd == "theme":
            await self._cmd_theme(args)

        else:
            self.append_line(
                f"[yellow]{t('tui.error.unknown_command', cmd=cmd)}[/yellow]"
            )

    # ── Handlers ──────────────────────────────────────────────────────────────

    async def _cmd_sessions(self) -> None:
        try:
            import json
            from pathlib import Path

            import aiosqlite

            db_path = Path.home() / ".vectora" / "checkpoints.db"
            if not db_path.exists():
                self.append_line(f"[dim]{t('tui.sessions.empty')}[/dim]")
                return

            async with aiosqlite.connect(str(db_path)) as db:
                async with db.execute(
                    "SELECT thread_id, last_activity, extra FROM vectora_sessions "
                    "ORDER BY last_activity DESC LIMIT 10"
                ) as cur:
                    rows = await cur.fetchall()

            if not rows:
                self.append_line(f"[dim]{t('tui.sessions.empty')}[/dim]")
                return

            lines = [f"[bold]{t('tui.sessions.title')}[/bold]"]
            for thread_id, last_activity, extra_json in rows:
                try:
                    extra = json.loads(extra_json or "{}")
                    title = extra.get("title", "")
                except Exception:
                    title = ""
                active = (
                    f" [green]{t('tui.sessions.current_suffix')}[/green]"
                    if thread_id == self._chat_thread_id
                    else ""
                )
                ts = last_activity[:16] if last_activity else "?"
                label = f" {title}" if title else ""
                lines.append(f"  [cyan]{thread_id}[/cyan] {ts}{label}{active}")
            self.append_line("\n".join(lines))
        except Exception as exc:
            self.append_line(f"[red]{t('tui.sessions.error', error=exc)}[/red]")

    async def _cmd_session(self, args: str) -> None:
        if not args:
            self.append_line(
                f"[dim]{t('tui.session.current', id=self._chat_thread_id)}[/dim]"
            )
            return
        self._chat_thread_id = args
        if self._stream_handler:
            self._stream_handler._thread_id = args
        self.append_line(f"[green]{t('tui.session.switched', id=args)}[/green]")

    async def _cmd_model(self, args: str) -> None:
        from src.services.runtime_settings import apply_model_change
        from src.settings import AVAILABLE_MODELS, find_provider_for_model

        if not args:
            lines = [f"[bold]{t('tui.model.available_title')}[/bold]"]
            for provider, models in AVAILABLE_MODELS.items():
                lines.append(f"  [bold cyan]{provider}[/bold cyan]")
                lines.extend(f"    [dim]·[/dim] {model}" for model in models)
            self.append_line("\n".join(lines))
        else:
            provider = find_provider_for_model(args)
            if provider:
                apply_model_change(provider, args)
                self.append_line(
                    f"[green]{t('tui.model.changed', model=args, provider=provider)}[/green]"
                )
                self.query_one("#status-info", Static).update(self._build_status())
            else:
                self.append_line(
                    f"[red]{t('tui.model.not_found', model=args)}[/red]  "
                    f"[dim]{t('tui.model.list_hint')}[/dim]"
                )

    async def _cmd_debug(self, args: str) -> None:
        from src.services.runtime_settings import runtime_settings

        if not args:
            v = runtime_settings.verbosity
            self.append_line(
                f"[dim]{t('tui.debug.current', level=v, label=_verbosity_label(v))}[/dim]"
            )
            return
        try:
            level = int(args)
            if level < 0 or level > 5:
                raise ValueError
            runtime_settings.set_verbosity(level)
            self.append_line(
                f"[green]{t('tui.debug.changed', level=level, label=_verbosity_label(level))}[/green]"
            )
        except ValueError:
            self.append_line(f"[red]{t('tui.debug.invalid')}[/red]")

    async def _cmd_rag(self) -> None:
        try:
            from src.services.background import get_background_worker

            worker = await get_background_worker()
            queue = await worker._get_queue()
            stats = await queue.get_stats() if queue is not None else {}
            lines = [
                f"[bold]{t('tui.rag.title')}[/bold]",
                f"  {t('tui.rag.pending')}    {stats.get('pending', 0)}",
                f"  {t('tui.rag.processing')}  {stats.get('processing', 0)}",
                f"  {t('tui.rag.success')}      {stats.get('success', 0)}",
                f"  {t('tui.rag.failed')}       {stats.get('failed', 0)}",
            ]
            self.append_line("\n".join(lines))
        except Exception as exc:
            self.append_line(f"[yellow]{t('tui.rag.unavailable', error=exc)}[/yellow]")

    async def _cmd_traces(self) -> None:
        try:
            from src.services.tracer import tracer

            spans = await tracer.get_recent(n=10)
            if not spans:
                self.append_line(f"[dim]{t('tui.traces.empty')}[/dim]")
                return
            lines = [f"[bold]{t('tui.traces.title')}[/bold]"]
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
            self.append_line(
                f"[yellow]{t('tui.traces.unavailable', error=exc)}[/yellow]"
            )

    async def _cmd_workspaces(self) -> None:
        try:
            from src.services.workspace import workspace_registry

            workspaces = workspace_registry.list_all()
            if not workspaces:
                self.append_line(f"[dim]{t('tui.workspaces.empty')}[/dim]")
                return
            lines = [f"[bold]{t('tui.workspaces.title')}[/bold]"]
            for ws in workspaces:
                trusted = (
                    f"[green]{t('tui.workspaces.trusted')}[/green]"
                    if getattr(ws, "trusted", False)
                    else f"[dim]{t('tui.workspaces.untrusted')}[/dim]"
                )
                name = getattr(ws, "name", str(getattr(ws, "id", ws)))
                path = getattr(ws, "cwd", "")
                lines.append(f"  {trusted} [cyan]{name}[/cyan] {path}")
            self.append_line("\n".join(lines))
        except Exception as exc:
            self.append_line(
                f"[yellow]{t('tui.workspaces.unavailable', error=exc)}[/yellow]"
            )

    async def _cmd_theme(self, args: str) -> None:
        from src.services.runtime_settings import runtime_settings
        from src.ui.app import VectoraChatApp
        from src.ui.theme import get_theme_css

        valid = ("dark", "light", "system")
        theme = args.strip().lower()
        if theme not in valid:
            self.append_line(
                f"[yellow]{t('tui.theme.invalid', valid=', '.join(valid))}[/yellow]"
            )
            return
        runtime_settings.set_theme(theme)
        VectoraChatApp.DEFAULT_CSS = get_theme_css(theme)
        # Tenta refresh_css() no app pai se disponível
        try:
            app = getattr(self, "app", None)
            if app is not None and hasattr(app, "refresh_css"):
                app.refresh_css()
        except Exception:  # noqa: BLE001
            pass
        self.append_line(f"[green]{t('tui.theme.changed', theme=theme)}[/green]")
