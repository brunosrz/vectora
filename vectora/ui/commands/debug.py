"""/debug command — toggle or set debug mode."""

import logging
from typing import Any

from vectora.services.runtime_settings import runtime_settings
from vectora.ui.main import SuccessPanel

logger = logging.getLogger(__name__)


def load_debug_config() -> bool:
    """Carrega debug_mode do runtime_settings (settings.json)."""
    return runtime_settings.debug_mode


def save_debug_config(debug_mode: bool) -> None:
    """Persiste debug_mode no runtime_settings (settings.json)."""
    runtime_settings.set_debug_mode(debug_mode)


async def handle_debug_command(
    args: str,
    console: Any,
    current_debug_mode: bool,
) -> bool:
    """Handle /debug command — toggle or explicitly set debug mode.

    Args:
        args: Arguments after /debug (empty to toggle, "true"/"false" to set)
        console: Rich console for output
        current_debug_mode: Current debug mode state

    Returns:
        New debug mode state
    """
    args = args.strip().lower()

    if not args:
        new_debug_mode = not current_debug_mode
        console.print(
            SuccessPanel.render(
                f"Debug Mode toggled: {new_debug_mode}",
                title="Debug Mode",
            )
        )
        logger.info("Debug mode toggled to: %s", new_debug_mode)
        save_debug_config(new_debug_mode)
        return new_debug_mode

    if args in {"true", "on", "yes"}:
        if current_debug_mode:
            console.print("[yellow]Debug Mode is already enabled[/yellow]")
            return current_debug_mode
        console.print(SuccessPanel.render("Debug Mode enabled", title="Debug Mode"))
        logger.info("Debug mode enabled")
        save_debug_config(True)
        return True

    if args in {"false", "off", "no"}:
        if not current_debug_mode:
            console.print("[yellow]Debug Mode is already disabled[/yellow]")
            return current_debug_mode
        console.print(SuccessPanel.render("Debug Mode disabled", title="Debug Mode"))
        logger.info("Debug mode disabled")
        save_debug_config(False)
        return False

    console.print(
        f"[red]Invalid argument: {args}[/red]\n"
        "[dim]Usage: /debug [true|false] or /debug to toggle[/dim]"
    )
    return current_debug_mode


# Backward-compat aliases
_load_debug_config = load_debug_config
_save_debug_config = save_debug_config
_handle_debug_command = handle_debug_command
