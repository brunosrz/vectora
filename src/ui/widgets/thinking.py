"""ThinkingWidget — render_hint: thinking (orchestrator reasoning block)."""

from __future__ import annotations

from textual.widgets import Static


class ThinkingWidget(Static):
    """Collapsible thinking block for orchestrator reasoning."""

    DEFAULT_CSS = """
    ThinkingWidget {
        background: $panel;
        border-left: thick $primary;
        padding: 0 1;
        margin: 0 0 1 0;
        color: $text-muted;
    }
    """

    def __init__(
        self, reason: str, action: str = "respond", delegate_to: str | None = None
    ) -> None:
        label = f"[dim]Pensando -> {action}"
        if delegate_to:
            label += f" [{delegate_to}]"
        label += "[/dim]"
        super().__init__(f"{label}\n[italic]{reason}[/italic]")
