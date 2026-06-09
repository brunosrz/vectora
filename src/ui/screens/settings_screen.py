"""SettingsScreen — tela modal de configurações da TUI Vectora.

Espelha as seções do SettingsDialog do frontend: Tema e Idioma.
Persistência via ``runtime_settings``. Atalho ``Ctrl+,``.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select, Static

from src.services.runtime_settings import runtime_settings
from src.ui.i18n import t

_THEMES = [
    ("dark", "tui.settings.theme_dark"),
    ("light", "tui.settings.theme_light"),
    ("system", "tui.settings.theme_system"),
]
_LANGUAGES = [("en", "English"), ("es", "Español"), ("pt-BR", "Português (BR)")]


class SettingsScreen(ModalScreen[None]):
    """Modal de configurações — Tema e Idioma."""

    BINDINGS = [
        Binding("escape", "dismiss", "Fechar", show=True),
        Binding("ctrl+comma", "dismiss", "Fechar", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-modal"):
            yield Static(f"[bold]{t('tui.settings.title')}[/bold]", id="settings-title")
            with Vertical(id="settings-body"):
                yield Label(t("tui.settings.theme"))
                theme_options: list[tuple[str, str]] = [
                    (t(key), val) for val, key in _THEMES
                ]
                yield Select(
                    theme_options,
                    value=runtime_settings.theme,
                    id="select-theme",
                )
                yield Label(t("tui.settings.language"))
                lang_options: list[tuple[str, str]] = [
                    (label, val) for val, label in _LANGUAGES
                ]
                yield Select(
                    lang_options,
                    value=runtime_settings.language,
                    id="select-language",
                )
            with Horizontal(id="settings-footer"):
                yield Button(t("tui.settings.save"), variant="primary", id="btn-save")
                yield Button(t("tui.settings.cancel"), id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._apply()
        self.dismiss()

    def _apply(self) -> None:
        from src.ui.app import VectoraChatApp
        from src.ui.theme import get_theme_css

        theme_sel = self.query_one("#select-theme", Select)
        lang_sel = self.query_one("#select-language", Select)
        if theme_sel.value and theme_sel.value is not Select.BLANK:
            new_theme = str(theme_sel.value)
            runtime_settings.set_theme(new_theme)
            # Troca o CSS em runtime — Textual 8.x suporta refresh_css()
            VectoraChatApp.DEFAULT_CSS = get_theme_css(new_theme)
            self.app.refresh_css()
        if lang_sel.value and lang_sel.value is not Select.BLANK:
            runtime_settings.set_language(str(lang_sel.value))
