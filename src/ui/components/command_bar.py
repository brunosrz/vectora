"""CommandBar — chips clicáveis na barra de comando da TUI Vectora.

Cada chip exibe um dado de contexto (branch, modelo, modo de permissão) e,
ao ser clicado, emite uma mensagem `CommandBar.ChipPressed` para que a screen
hospedeira abra a tela correspondente.

Espelha conceitualmente a barra inferior do chat web
(`◈ Vectora │ 🌿 branch │ model │ ⚙ mode`).
"""

from __future__ import annotations

import subprocess  # nosec B404
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Static

from src.services.runtime_settings import runtime_settings


class CommandBar(Widget):
    """Barra horizontal com chips clicáveis de contexto."""

    DEFAULT_CSS = """
    CommandBar {
        height: 1;
        dock: bottom;
    }
    CommandBar Horizontal {
        height: 1;
        background: $panel;
    }
    CommandBar Button {
        height: 1;
        min-width: 0;
        border: none;
        padding: 0 1;
        background: transparent;
        color: $text-muted;
    }
    CommandBar Button:hover {
        background: $surface;
        color: $text;
    }
    CommandBar Static {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    """

    # ── Mensagem emitida quando um chip é clicado ─────────────────────────────

    class ChipPressed(Message):
        """Emitida quando o usuário clica em um chip da command bar."""

        def __init__(self, chip_id: str) -> None:
            super().__init__()
            self.chip_id = chip_id

    # ── Layout ────────────────────────────────────────────────────────────────

    def __init__(
        self,
        permission_mode: str = "ask",
        *,
        name: str | None = None,
        id: str | None = None,  # noqa: A002
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self._permission_mode = permission_mode

    def compose(self) -> ComposeResult:
        branch = _current_branch(Path.cwd())
        model = runtime_settings.active_model or "–"
        mode = self._permission_mode

        with Horizontal():
            yield Static("◈ Vectora", id="chip-logo")
            if branch:
                yield Button(f"🌿 {branch}", id="chip-branch", variant="default")
            yield Button(model, id="chip-model", variant="default")
            yield Button(f"⚙ {mode}", id="chip-mode", variant="default")

    # ── Eventos ───────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.post_message(self.ChipPressed(event.button.id or ""))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _current_branch(cwd: Path) -> str:
    """Lê o branch git atual; string vazia fora de um repo ou sem git."""
    try:
        result = subprocess.run(  # noqa: S603 # nosec B603 B607
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(cwd),
            timeout=2,
        )
        return result.stdout.strip()
    except Exception:  # noqa: BLE001
        return ""
