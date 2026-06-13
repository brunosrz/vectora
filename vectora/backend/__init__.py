"""Vectora — assistente de IA com RAG e MCP. Pacote raiz do backend.

Reexporta os dois entry-points do binário:

  main()  (`src.launcher`) → valida licença e delega para `run()`
  run()   (`src.main`)     → parser de argumentos + dispatch (chat/server/mcp/...)
"""

from __future__ import annotations

from backend.launcher import main
from backend.main import run

__all__ = ["main", "run"]
