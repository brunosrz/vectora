"""HelpScreen — cheatsheet auto-gerada a partir de BINDINGS e SLASH_COMMANDS.

Gerada por reflexão sobre ``ChatScreen.BINDINGS`` + ``VectoraChatApp.BINDINGS``
e ``ChatScreen.SLASH_COMMANDS`` — nenhuma string de ajuda duplicada em código.
Atalho ``Ctrl+?``.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from backend.ui.i18n import t


class HelpScreen(ModalScreen[None]):
    """Cheatsheet de atalhos e comandos gerada dinamicamente."""

    BINDINGS = [
        Binding("escape", "dismiss", "Fechar", show=True),
        Binding("question_mark", "dismiss", "Fechar", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-modal"):
            yield Static(f"[bold]{t('tui.help.screen_title')}[/bold]", id="help-title")
            yield Static(self._build_content(), id="help-body")
            yield Button(t("tui.help.close"), id="help-close")

    @staticmethod
    def _build_content() -> str:
        from backend.ui.app import VectoraChatApp
        from backend.ui.screens.chat_screen import ChatScreen
        from backend.ui.slash_handlers import build_help_text

        lines: list[str] = []

        # ── Atalhos de teclado ────────────────────────────────────────────────
        lines.append(f"[bold cyan]{t('tui.help.shortcuts_section')}[/bold cyan]")
        all_bindings = list(VectoraChatApp.BINDINGS) + list(ChatScreen.BINDINGS)
        for b in all_bindings:
            key = getattr(b, "key", "?")
            desc = getattr(b, "description", "")
            key_fmt = str(key).replace("ctrl+", "^").replace("_", " ")
            lines.append(f"  [cyan]{key_fmt:<16}[/cyan] {desc}")

        lines.append("")
        # ── Slash commands ────────────────────────────────────────────────────
        lines.append(build_help_text())
        return "\n".join(lines)

    def on_button_pressed(self, _event: Button.Pressed) -> None:
        self.dismiss()
