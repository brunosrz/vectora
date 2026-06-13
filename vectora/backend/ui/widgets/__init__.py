"""Widgets Textual da TUI da Vectora — um por tipo de conteúdo renderizado.

Reexporta as classes para que `app.py`/`slash_handlers.py` importem direto
de `src.ui.widgets`.
"""

from __future__ import annotations

from backend.ui.widgets.code_block import CodeBlockWidget
from backend.ui.widgets.diff import DiffWidget
from backend.ui.widgets.hitl import HITLModal
from backend.ui.widgets.thinking import ThinkingWidget

__all__ = ["CodeBlockWidget", "DiffWidget", "HITLModal", "ThinkingWidget"]
