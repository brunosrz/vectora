"""Persistência nativa do motor de conversa: ``session_store.py``/
``postgres_session_store.py`` (fonte única de verdade de threads/mensagens/
aprovações pendentes, consumida por ``backend/engine/conversation_loop.py``).

``sqlite_checkpointer.py``/``postgres_checkpointer.py``/``store.py``/
``postgres_store.py`` implementam ``BaseCheckpointSaver``/``BaseStore`` do
LangGraph (``langgraph.checkpoint.base``/``langgraph.store.base``) via
``aiosqlite``/``asyncpg`` direto, sem as libs ``langgraph-checkpoint-sqlite``/
``langgraph-checkpoint-postgres`` — órfãos desde o corte de dispatch pro
motor nativo, pendentes de remoção.
"""

from __future__ import annotations
