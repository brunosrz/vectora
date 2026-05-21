"""/new, /sessions, /session commands — session lifecycle management."""

import logging
import re
from pathlib import Path
from typing import Any

from vectora.config.settings import settings
from vectora.services.runtime_settings import runtime_settings
from vectora.ui.main import SuccessPanel

logger = logging.getLogger(__name__)


async def handle_new_session(context: Any, console: Any) -> Any:
    """Create a new chat session associated with the current working directory.

    Args:
        context: Current context object
        console: Rich console for output

    Returns:
        Updated context with new thread_id
    """
    from vectora.context import Context
    from vectora.services.session import SessionService

    cwd = str(Path.cwd())

    try:
        session_service = SessionService(settings)
        await session_service.initialize()
        new_thread_id = await session_service.create(working_directory=cwd)
    except Exception:
        # Fallback: simple increment (no DB available)
        new_thread_id = (context.thread_id or 1) + 1
        logger.warning(
            "SessionService unavailable, using fallback thread_id=%d", new_thread_id
        )

    # Update directory mapping so the next startup resumes this session
    runtime_settings.set_session_for_dir(cwd, new_thread_id)

    new_context = Context(
        user_type=context.user_type or "default", thread_id=new_thread_id
    )

    console.print(
        SuccessPanel.render(
            f"New session created: [bold]{new_thread_id}[/bold]\n"
            f"[dim]Linked to: {cwd}[/dim]",
            title="New Session",
        )
    )
    logger.info("New session created: thread_id=%d cwd=%s", new_thread_id, cwd)
    return new_context


async def handle_list_sessions(context: Any, console: Any) -> None:
    """List all available sessions.

    Args:
        context: Current context object
        console: Rich console for output
    """
    from rich.panel import Panel
    from rich.table import Table

    from vectora.services.checkpoint import Checkpointer
    from vectora.services.session import SessionService

    try:
        # Use SessionService for richer metadata (includes working_directory)
        session_service = SessionService(settings)
        await session_service.initialize()
        sessions = await session_service.list_all()

        table = Table(title="Sessions", show_lines=True, border_style="cyan")
        table.add_column("ID", style="bold green", justify="center", width=6)
        table.add_column("Messages", justify="center", width=9)
        table.add_column("Last Activity", style="dim", width=22)
        table.add_column("Directory", style="dim")
        table.add_column("", width=10)

        for s in sessions:
            tid = s.get("thread_id", "?")
            msgs = str(s.get("message_count", 0))
            activity = str(s.get("last_activity", ""))[:19].replace("T", " ")
            wdir = str(s.get("working_directory", "—"))
            # Abbreviate home dir for readability
            home = str(Path.home())
            if wdir.startswith(home):
                wdir = "~" + wdir[len(home) :]
            current = "◀ current" if tid == context.thread_id else ""
            style = "on dark_cyan" if tid == context.thread_id else ""
            table.add_row(str(tid), msgs, activity, wdir, current, style=style)

        console.print(Panel(table, style="cyan", expand=False))

    except Exception as e:
        # Graceful fallback — just show the current thread_id
        logger.exception("Failed to list sessions")
        try:
            async with Checkpointer(settings.db_dsn) as checkpointer:
                table = Table(title="Sessions", style="cyan")
                table.add_column("Thread ID", style="bold green")
                table.add_column("Status")
                table.add_row(str(context.thread_id or 1), "← current")
                console.print(Panel(table, style="cyan", expand=False))
        except Exception:
            console.print(f"[red]Error listing sessions: {e}[/red]")


async def handle_switch_session(args: str, context: Any, console: Any) -> Any:
    """Switch to a different session and update the directory mapping.

    Args:
        args: Session ID to switch to
        context: Current context object
        console: Rich console for output

    Returns:
        Updated context with the new thread_id
    """
    from vectora.context import Context

    new_thread_id = args.strip()

    if not new_thread_id:
        console.print("[red]Usage: /session <thread_id>[/red]")
        return context

    if not re.fullmatch(r"\d{6}", new_thread_id):
        console.print(
            f"[red]Invalid session ID '{new_thread_id}'. "
            f"Expected 6-digit format, e.g. '042731'[/red]"
        )
        return context

    old_thread_id = context.thread_id

    new_context = Context(
        user_type=context.user_type or "default", thread_id=new_thread_id
    )

    # Update directory mapping so next startup returns to this session
    cwd = str(Path.cwd())
    runtime_settings.set_session_for_dir(cwd, new_thread_id)

    console.print(
        SuccessPanel.render(
            f"Switched to session [bold]{new_thread_id}[/bold] "
            f"(from {old_thread_id})\n"
            f"[dim]{cwd} -> session {new_thread_id}[/dim]",
            title="Session Switched",
        )
    )
    logger.info(
        "Session switched: %s -> %s (cwd=%s)", old_thread_id, new_thread_id, cwd
    )
    return new_context


# Backward-compat aliases
_handle_new_session = handle_new_session
_handle_list_sessions = handle_list_sessions
_handle_switch_session = handle_switch_session
