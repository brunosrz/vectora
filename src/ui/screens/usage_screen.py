"""UsageScreen — popover de consumo de requests na TUI Vectora.

Lê o ``usage_tracker`` diretamente (processo único) e exibe barras de
progresso para janelas curta, 5h e semanal. Espelha a lógica de
``getUsageColor`` do frontend. Atalho ``Ctrl+U``.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from src.services.runtime_settings import runtime_settings
from src.ui.i18n import t


def _color_for_ratio(ratio: float) -> str:
    """Espelha ``getUsageColor`` do frontend: verde → amarelo → vermelho."""
    if ratio >= 0.95:
        return "red"
    if ratio >= 0.8:
        return "yellow"
    return "green"


class UsageScreen(ModalScreen[None]):
    """Popover de consumo de requests."""

    BINDINGS = [
        Binding("escape", "dismiss", "Fechar", show=True),
        Binding("ctrl+u", "dismiss", "Fechar", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="usage-modal"):
            yield Static(f"[bold]{t('tui.usage.title')}[/bold]", id="usage-title")
            yield Static("", id="usage-body")
            yield Button(t("tui.usage.close"), id="usage-close")

    def on_mount(self) -> None:
        self._refresh_usage()

    def _refresh_usage(self) -> None:
        body = self.query_one("#usage-body", Static)
        try:
            from src.services.usage import usage_tracker

            user_id = runtime_settings.get("user_id", "local")
            data = usage_tracker.usage(str(user_id))
            lines = self._format_usage(data)
            body.update("\n".join(lines))
        except Exception:  # noqa: BLE001
            body.update(t("tui.usage.unavailable"))

    @staticmethod
    def _format_usage(data: dict) -> list[str]:  # type: ignore[type-arg]
        lines: list[str] = []
        windows = [
            ("tui.usage.window_short", "short"),
            ("tui.usage.window_5h", "five_hour"),
            ("tui.usage.window_weekly", "weekly"),
        ]
        for label_key, window_key in windows:
            window = data.get(window_key, {})
            used = int(window.get("used", 0))
            limit = int(window.get("limit", 1))
            remaining = int(window.get("remaining", limit))
            ratio = used / limit if limit else 0
            color = _color_for_ratio(ratio)
            pct = int(ratio * 100)
            bar = _ascii_bar(ratio, width=20)
            lines.append(
                f"{t(label_key)}: [{color}]{bar}[/{color}] "
                f"[bold]{used}[/bold]/{limit} ({pct}%)"
                f"  {t('tui.usage.remaining', n=remaining)}"
            )
        return lines

    def on_button_pressed(self, _event: Button.Pressed) -> None:
        self.dismiss()


def _ascii_bar(ratio: float, width: int = 20) -> str:
    """Barra ASCII simples: `████░░░░░░`."""
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)
