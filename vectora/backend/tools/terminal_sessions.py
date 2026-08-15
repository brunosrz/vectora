"""Tools de gestão dos terminais PTY abertos manualmente pelo usuário via WebSocket.

Reaproveita o mesmo ``pty_registry`` que o handler REST
(``backend/api/handlers/terminal.py``) usa — não duplica o tracking de sessões.
"""

from __future__ import annotations

import json
import logging

from backend.services.pty_registry import pty_registry
from backend.tools.context import ToolContext
from backend.tools.registry import ToolExtras, vtool

logger = logging.getLogger(__name__)


@vtool(
    extras=ToolExtras(
        render_hint="code_block",
        category="filesystem",
        destructive=False,
        icon="terminal",
    )
)
async def list_terminals(ctx: ToolContext) -> str:
    """Lista os terminais PTY abertos manualmente pelo usuário nesta sessão."""
    thread_id = ctx.thread_id
    sessions = (
        pty_registry.list_for_thread(thread_id)
        if thread_id
        else list(pty_registry._sessions.values())
    )
    return json.dumps(
        {
            "terminals": [
                {
                    "terminal_id": s.terminal_id,
                    "thread_id": s.thread_id,
                    "workspace_id": s.workspace_id,
                    "alive": s.is_alive(),
                }
                for s in sessions
            ]
        }
    )


@vtool(
    extras=ToolExtras(
        render_hint="code_block",
        category="filesystem",
        destructive=True,
        icon="terminal",
    )
)
async def close_terminal(terminal_id: str) -> str:
    """Encerra um terminal PTY aberto manualmente pelo usuário, pelo id."""
    if not terminal_id:
        return json.dumps({"status": "error", "message": "terminal_id é obrigatório."})
    if not pty_registry.close(terminal_id):
        return json.dumps(
            {"status": "error", "message": f"Terminal {terminal_id!r} não encontrado."}
        )
    return json.dumps({"status": "closed", "terminal_id": terminal_id})


__all__ = ["close_terminal", "list_terminals"]
