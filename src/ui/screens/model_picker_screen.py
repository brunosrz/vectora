"""ModelPickerScreen — seletor de modelo da TUI Vectora.

Exibe todos os modelos disponíveis agrupados por provider, com fuzzy match
na busca por nome, badge do modelo ativo e contexto em tokens.
Atalho ``Ctrl+M``.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from src.services.runtime_settings import runtime_settings
from src.settings import AVAILABLE_MODELS, get_context_window
from src.ui.i18n import t


def _ctx_label(ctx: int) -> str:
    """Formata janela de contexto: 128000 → '128k', 1000000 → '1M'."""
    if ctx >= 1_000_000:
        return f"{ctx // 1_000_000}M"
    return f"{ctx // 1_000}k"


def _build_options(query: str = "") -> list[Option]:
    """Monta opções para o OptionList, filtrando por query (fuzzy simples)."""
    current = runtime_settings.active_model or ""
    q = query.lower()
    options: list[Option] = []
    for provider, models in AVAILABLE_MODELS.items():
        for model in models:
            if q and q not in model.lower() and q not in provider.lower():
                continue
            ctx = _ctx_label(get_context_window(model))
            badge = " ✓" if model == current else ""
            label = f"{model}  [{provider}]  {ctx}{badge}"
            options.append(Option(label, id=f"{provider}::{model}"))
    return options


class ModelPickerScreen(ModalScreen[None]):
    """Modal de seleção de modelo com busca fuzzy e badge do ativo."""

    BINDINGS = [
        Binding("escape", "dismiss", "Fechar", show=True),
        Binding("ctrl+m", "dismiss", "Fechar", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="model-picker-modal"):
            yield Static(f"[bold]{t('tui.model_picker.title')}[/bold]", id="mp-title")
            yield Input(
                placeholder=t("tui.model_picker.search_placeholder"),
                id="mp-search",
            )
            yield OptionList(*_build_options(), id="mp-list")
            with Horizontal(id="mp-footer"):
                yield Label(t("tui.model_picker.hint"), id="mp-hint")
                yield Button(t("tui.model_picker.cancel"), id="mp-cancel")

    def on_mount(self) -> None:
        self.query_one("#mp-search", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        ol = self.query_one("#mp-list", OptionList)
        ol.clear_options()
        for opt in _build_options(event.value):
            ol.add_option(opt)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = str(event.option.id)
        if "::" in option_id:
            provider, model = option_id.split("::", 1)
            runtime_settings.set_active_model(provider, model)
        self.dismiss()

    def on_button_pressed(self, _event: Button.Pressed) -> None:
        self.dismiss()
