"""Factory de ``RedisChatMessageHistory``.

Habilitado por ``settings.cache_history_backend == "redis"``. Quando desabilitado
ou sem Redis acessível, ``get_chat_history`` retorna ``None`` e o chamador usa o
backend de history padrão (SQLite/Postgres).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_chat_history(session_id: str) -> Any | None:
    """Retorna ``RedisChatMessageHistory`` para ``session_id`` ou ``None``.

    ``None`` quando ``cache_history_backend != "redis"``, sem ``redis_url`` ou
    Redis inacessível — o chamador então usa o history padrão (SQLite/Postgres).
    """
    from backend.settings import settings

    if settings.cache_history_backend != "redis":
        return None

    url = (settings.redis_url or "").strip()
    if not url:
        return None

    from backend.services.kv import redis_reachable

    if not redis_reachable(url):
        logger.info(
            "chat_history: cache_history_backend=redis mas Redis inacessível — "
            "usando backend padrão"
        )
        return None

    from langchain_redis import RedisChatMessageHistory

    return RedisChatMessageHistory(session_id=session_id, redis_url=url)
