"""Command dispatcher for Vectora Chat.

Handles system commands (e.g., /quit, /model, /rag) separately from chat input.
Each command group lives in its own module — import from here for all public needs.

Structure:
  _shared.py   — shared constants and provider utilities
  debug.py     — /debug
  model.py     — /model
  rag.py       — /rag, /rag add, /rag failed
  session.py   — /new, /sessions, /session
  help.py      — /help, /tools, /list
"""

import logging
from typing import Any

from vectora.ui.commands._shared import AVAILABLE_MODELS, get_available_models
from vectora.ui.commands.debug import (
    handle_debug_command,
    load_debug_config,
    save_debug_config,
)
from vectora.ui.commands.help import (
    display_command_list,
    display_help,
    handle_tools_command,
)
from vectora.ui.commands.model import handle_model_command
from vectora.ui.commands.rag import handle_rag_command
from vectora.ui.commands.session import (
    handle_list_sessions,
    handle_new_session,
    handle_switch_session,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backward-compat aliases (used by chat.py and tests importing private names)
# ---------------------------------------------------------------------------
_load_debug_config = load_debug_config
_save_debug_config = save_debug_config
_handle_debug_command = handle_debug_command
_handle_model_command = handle_model_command
_handle_rag_command = handle_rag_command
_handle_new_session = handle_new_session
_handle_list_sessions = handle_list_sessions
_handle_switch_session = handle_switch_session
_handle_tools_command = handle_tools_command
_display_command_list = display_command_list
_display_help = display_help


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------


async def handle_command(
    user_input: str,
    config: Any,
    console: Any,
    context: Any = None,
    debug_mode: bool = False,
) -> tuple[bool, Any, bool]:
    """Process system commands (user input starting with /).

    Args:
        user_input: Raw user input (should start with /)
        config: Config instance (kept for backward compatibility, unused)
        console: Rich console for output
        context: Context object that may be modified by commands
        debug_mode: Current debug mode state

    Returns:
        Tuple of (should_exit, updated_context, debug_mode)
    """
    parts = user_input.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if cmd in {"/quit", "/sair", "/q"}:
        logger.info("Chat ended by command: %s", cmd)
        return True, context, debug_mode

    if cmd == "/model":
        await handle_model_command(args, console)

    elif cmd == "/help":
        display_help(console)

    elif cmd == "/debug":
        debug_mode = await handle_debug_command(args, console, debug_mode)

    elif cmd == "/new":
        context = await handle_new_session(context, console)

    elif cmd == "/sessions":
        await handle_list_sessions(context, console)

    elif cmd == "/session":
        context = await handle_switch_session(args, context, console)

    elif cmd in {"/tools", "/tool"}:
        await handle_tools_command(console)

    elif cmd == "/rag":
        await handle_rag_command(args, console)

    elif cmd == "/list":
        display_command_list(console)

    else:
        console.print(f"[dim][red]Unknown command:[/red] {cmd}[/dim]")

    return False, context, debug_mode


__all__ = [
    "AVAILABLE_MODELS",
    "get_available_models",
    "handle_command",
    "load_debug_config",
    "save_debug_config",
]
