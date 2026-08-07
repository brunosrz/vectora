"""Implementações nativas dos protocolos ``BaseCheckpointSaver``/``BaseStore``
do LangGraph (``langgraph.checkpoint.base``/``langgraph.store.base``) — HTTP/DB
direto via ``aiosqlite``/``asyncpg``, sem as libs ``langgraph-checkpoint-sqlite``/
``langgraph-checkpoint-postgres``.

O LangGraph em si (grafo, ``interrupt()``, ``HumanInTheLoopMiddleware``,
``astream_events``) continua intocado — só a camada de storage do
checkpointer/Store é nativizada, mesmo padrão já usado em
``backend/llm/native_redis_cache.py`` (cache) e nos clients de provider de
``backend/llm/{openai,anthropic,google,cohere,voyage}/``.
"""

from __future__ import annotations
