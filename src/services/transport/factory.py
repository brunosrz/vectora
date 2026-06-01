"""Factory que escolhe o transport correto por workspace.

Cache por ``workspace.id``: cada workspace tem uma única instância de
backend, reaproveitada entre chamadas (pool de conexões SSH, processo
filho do ``gh codespace ssh``, etc.).
"""

from __future__ import annotations

import logging
from typing import Any

from src.services.transport.base import TransportBackend
from src.services.transport.local import LocalTransport

logger = logging.getLogger(__name__)

#: Cache de instâncias por workspace.id.
_CACHE: dict[str, TransportBackend] = {}


def get_transport(workspace: Any) -> TransportBackend:
    """Resolve o backend correto para um workspace.

    G.2.4/5 vão acrescentar ``SshTransport`` e ``CodespaceTransport``
    aqui. Por ora só ``LocalTransport`` está implementado; transports
    remotos caem em ``NotImplementedError`` até que cheguem.
    """
    ws_id = getattr(workspace, "id", None)
    if ws_id is None:
        # Sem id — devolve singleton local efêmero (não cacheia).
        return LocalTransport()

    cached = _CACHE.get(ws_id)
    if cached is not None:
        return cached

    transport = str(getattr(workspace, "transport", "local"))
    backend: TransportBackend
    if transport == "local":
        backend = LocalTransport()
    elif transport == "ssh":
        # G.2.4 — implementado em src/services/transport/ssh.py
        raise NotImplementedError("SSH transport ainda não implementado (G.2.4).")
    elif transport == "codespace":
        # G.2.5 — implementado em src/services/transport/codespace.py
        raise NotImplementedError("Codespace transport ainda não implementado (G.2.5).")
    else:
        logger.warning(
            "Workspace %s tem transport desconhecido '%s'; usando local.",
            ws_id,
            transport,
        )
        backend = LocalTransport()

    _CACHE[ws_id] = backend
    return backend


async def close_all_transports() -> None:
    """Encerra todos os backends cacheados (chamar no shutdown do server)."""
    for ws_id, backend in list(_CACHE.items()):
        try:
            await backend.close()
        except Exception:
            logger.warning("Falha ao fechar transport de %s", ws_id, exc_info=True)
    _CACHE.clear()
