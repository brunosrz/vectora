"""Persistência nativa do motor de conversa: ``session_store.py``/
``postgres_session_store.py`` (fonte única de verdade de threads/mensagens/
aprovações pendentes, consumida por ``backend/engine/conversation_loop.py``).

``store.py``/``postgres_store.py`` implementam ``BaseStore`` do LangGraph
(``langgraph.store.base``) via ``aiosqlite``/``asyncpg`` direto, sem a lib
``langgraph-checkpoint-postgres`` — usados pelas tools de memória do agente.
"""

from __future__ import annotations
