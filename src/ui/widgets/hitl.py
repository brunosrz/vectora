"""HITL approval modal (ModalScreen) — render_hint: hitl."""

from __future__ import annotations

import json

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class HITLModal(ModalScreen[str]):
    """Approval modal for HITL interrupts.

    Returns one of: ``"approve"`` | ``"reject"``
    """

    BINDINGS = [
        Binding("escape", "reject", "Rejeitar"),
    ]

    DEFAULT_CSS = """
    HITLModal {
        align: center middle;
    }
    #hitl-dialog {
        background: $surface;
        border: round $warning;
        padding: 1 2;
        width: 70;
        max-width: 80%;
        height: auto;
    }
    #hitl-title {
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    #hitl-args {
        background: $panel;
        padding: 0 1;
        margin-bottom: 1;
        height: auto;
        max-height: 10;
        overflow-y: auto;
    }
    #hitl-buttons {
        margin-top: 1;
    }
    """

    def __init__(
        self,
        tool_name: str,
        args_json: str,
        interrupt_id: str,
    ) -> None:
        super().__init__()
        self._tool_name = tool_name
        self._args_json = args_json
        self._interrupt_id = interrupt_id

    def compose(self) -> ComposeResult:
        try:
            pretty = json.dumps(
                json.loads(self._args_json), indent=2, ensure_ascii=False
            )
        except Exception:
            pretty = self._args_json
        pretty_truncated = pretty[:800] + ("…" if len(pretty) > 800 else "")

        with Center():
            with Vertical(id="hitl-dialog"):
                yield Label(
                    f"[bold yellow]⚡ Aprovação necessária:[/bold yellow] {self._tool_name}",
                    id="hitl-title",
                )
                yield Static(pretty_truncated, id="hitl-args")
                with Horizontal(id="hitl-buttons"):
                    yield Button("Aprovar", id="approve", variant="success")
                    yield Button("Rejeitar", id="reject", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve":
            self.dismiss("approve")
        else:
            self.dismiss("reject")

    def action_reject(self) -> None:
        self.dismiss("reject")
