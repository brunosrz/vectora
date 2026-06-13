"""VectoraChatApp — shell da TUI Vectora.

Responsável apenas por:
  - Configurar CSS (tema), bindings globais e título
  - Montar a ChatScreen na inicialização

Toda a lógica de chat (layout, input, callbacks de streaming, slash-commands)
vive em ``src/ui/screens/chat_screen.py``.
"""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding

from src.services.runtime_settings import runtime_settings
from src.ui.screens.chat_screen import ChatScreen
from src.ui.theme import get_theme_css


class VectoraChatApp(App[None]):
    """Vectora TUI — App shell que monta o ChatScreen."""

    TITLE = "Vectora"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Sair", show=True),
        Binding("ctrl+c", "quit", "Sair", show=False),
    ]

    # CSS resolvido a partir de `runtime_settings.theme` (persistido em
    # `~/.vectora/settings.json`, trocável com `/theme`). Textual lê
    # `DEFAULT_CSS` como atributo de classe — troca em runtime exige
    # reabrir a TUI até existir mecanismo de `refresh_css` dedicado
    # (ver B.14 no plano de implementação).
    DEFAULT_CSS = get_theme_css(runtime_settings.theme)

    def __init__(
        self,
        chat_thread_id: str | None = None,
        permission_mode: str = "ask",
        user_id: str = "local",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._chat_thread_id = chat_thread_id
        self._permission_mode = permission_mode
        self._user_id = user_id

    def compose(self) -> ComposeResult:
        # Vazio — on_mount empurra ChatScreen como tela inicial
        return iter(())

    async def on_mount(self) -> None:
        await self.push_screen(
            ChatScreen(
                chat_thread_id=self._chat_thread_id,
                permission_mode=self._permission_mode,
                user_id=self._user_id,
            )
        )
