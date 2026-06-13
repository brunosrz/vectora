"""Funções puras de montagem de UI da Vectora TUI (status bar, popup `/comando`).

Cada submódulo transforma dados (texto digitado, modo de permissão etc.) em
texto/opções prontos para os widgets consumirem — sem montar nada, o que
permite testar a lógica sem instanciar a App completa. Reexporta as funções
para que os consumidores importem direto de `src.ui.components`.
"""

from __future__ import annotations

from src.ui.components.slash_popup import build_popup_options
from src.ui.components.status_bar import build_status_text

__all__ = ["build_popup_options", "build_status_text"]
