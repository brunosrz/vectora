"""/new, /sessions, /session commands — session lifecycle management."""

import logging
from typing import Any

from vectora.config.settings import settings
from vectora.ui.main import SuccessPanel

logger = logging.getLogger(__name__)


async def handle_new_session(context: Any, console: Any) -> Any:
    """Create a new chat session.

    Args:
        context: Current context object
        console: Rich console for output

    Returns:
        Updated context with new thread_id
    """
    from vectora.context import Context

    new_thread_id = (context.thread_id or 1) + 1
    new_context = Context(
        user_type=context.user_type or "default", thread_id=new_thread_id
    )

    console.print(
        SuccessPanel.render(
            f"New session created with ID: {new_thread_id}",
            title="New Session",
        )
    )
    logger.info("New session created: thread_id=%d", new_thread_id)
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

    try:
        async with Checkpointer(settings.db_dsn) as checkpointer:
            table = Table(title="Available Sessions", style="cyan")
            table.add_column("Thread ID", style="bold green")
            table.add_column("Status", style="bold cyan")

            current_marker = "← Current" if context.thread_id else ""
            table.add_row(str(context.thread_id or 1), current_marker)

            console.print(Panel(table, style="cyan", expand=False))

    except Exception as e:
        console.print(f"[red]Error listing sessions: {e}[/red]")
        logger.exception("Failed to list sessions")


async def handle_switch_session(args: str, context: Any, console: Any) -> Any:
    """Switch to a different session.

    Args:
        args: Session ID to switch to
        context: Current context object
        console: Rich console for output

    Returns:
        Updated context with the new thread_id
    """
    from vectora.context import Context

    if not args.strip():
        console.print("[red]Usage: /session <thread_id>[/red]")
        return context

    try:
        new_thread_id = int(args.strip())
        old_thread_id = context.thread_id

        new_context = Context(
            user_type=context.user_type or "default", thread_id=new_thread_id
        )

        console.print(
            SuccessPanel.render(
                f"Switched to session {new_thread_id} (from {old_thread_id})",
                title="Session Switched",
            )
        )
        logger.info("Session switched: %d → %d", old_thread_id, new_thread_id)
        return new_context
    except ValueError:
        console.print(f"[red]Invalid session ID: {args.strip()}[/red]")
        return context


# Backward-compat aliases
_handle_new_session = handle_new_session
_handle_list_sessions = handle_list_sessions
_handle_switch_session = handle_switch_session
