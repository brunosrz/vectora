"""/debug command - set verbosity level (0-5)."""

import logging
from typing import Any

from rich.table import Table

from vectora.services.runtime_settings import runtime_settings
from vectora.ui.main import ErrorPanel, SuccessPanel

logger = logging.getLogger(__name__)

# ─── Level descriptions ───────────────────────────────────────────────────────

VERBOSITY_LEVELS: dict[int, tuple[str, str]] = {
    0: ("OFF", "Silent — no tool/routing output"),
    1: ("Minimal", "Routing only — which agent was selected"),
    2: ("Tools", "Tool name + success/error status, no content"),
    3: ("Standard", "Tool args (truncated) + response summary"),
    4: ("Verbose", "Full tool args + full response content"),
    5: ("Full", "Everything + live log panel on the side"),
}


# ─── Persistence helpers ──────────────────────────────────────────────────────


def load_debug_config() -> int:
    """Returns current verbosity level from runtime_settings."""
    return runtime_settings.verbosity


def save_debug_config(level: int) -> None:
    """Persists verbosity level to settings.json."""
    runtime_settings.set_verbosity(level)


# ─── Command handler ──────────────────────────────────────────────────────────


async def handle_debug_command(
    args: str,
    console: Any,
    current_verbosity: int,
) -> int:
    """Handle /debug command — show levels or set a specific level.

    Usage:
        /debug          → show current level and all options
        /debug 0-5      -> set verbosity to that level
        /debug off      → alias for /debug 0
        /debug on       → alias for /debug 5

    Args:
        args: Arguments after /debug
        console: Rich console for output
        current_verbosity: Current verbosity level

    Returns:
        New verbosity level
    """
    args = args.strip().lower()

    # No args → show current level and menu
    if not args:
        _print_level_table(console, current_verbosity)
        return current_verbosity

    # Aliases
    if args in {"off", "false", "no"}:
        args = "0"
    elif args in {"on", "true", "yes", "full"}:
        args = "5"

    # Numeric level
    if args.isdigit():
        level = int(args)
        if level not in VERBOSITY_LEVELS:
            console.print(
                ErrorPanel.render(
                    f"Invalid level '{level}'. Choose between 0 and 5.",
                    title="Debug",
                )
            )
            return current_verbosity

        save_debug_config(level)
        name, desc = VERBOSITY_LEVELS[level]
        console.print(
            SuccessPanel.render(
                f"Verbosity set to [bold]{level} — {name}[/bold]\n[dim]{desc}[/dim]",
                title="Debug Mode",
            )
        )
        logger.info("Verbosity set to %d (%s)", level, name)
        return level

    console.print(
        ErrorPanel.render(
            "Usage: /debug [0–5 | off | on]\nRun /debug with no arguments to see all levels.",
            title="Debug",
        )
    )
    return current_verbosity


def _print_level_table(console: Any, current: int) -> None:
    """Print a Rich table showing all verbosity levels."""
    table = Table(title="Verbosity Levels", show_lines=True, border_style="cyan")
    table.add_column("Level", style="bold", justify="center", width=6)
    table.add_column("Name", style="bold cyan", width=12)
    table.add_column("Description", style="dim")
    table.add_column("", width=4)

    for level, (name, desc) in VERBOSITY_LEVELS.items():
        active = "◀" if level == current else ""
        style = "on dark_cyan" if level == current else ""
        table.add_row(str(level), name, desc, active, style=style)

    console.print(table)
    console.print(
        f"[dim]Current level: [bold cyan]{current}[/bold cyan] — "
        f"{VERBOSITY_LEVELS[current][0]}. "
        "Use [bold]/debug <0–5>[/bold] to change.[/dim]"
    )


# Backward-compat aliases
_load_debug_config = load_debug_config
_save_debug_config = save_debug_config
_handle_debug_command = handle_debug_command
