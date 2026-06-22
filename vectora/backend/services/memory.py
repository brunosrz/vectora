"""Gerenciador de memórias persistentes em SQLite — DEPRECATED (E.B-11).

.. deprecated::
    Este módulo está depreciado. As memory tools (``src/tools/memory.py``) foram
    migradas para ``langgraph.config.get_store()`` + LangGraph BaseStore (E.B-11).

    Mantido temporariamente para:
    - ``src/api/handlers/memory.py`` (HTTP API de memórias)
    - ``src/nodes/base.py`` (injeção legada de memórias no system prompt)

    Remoção planejada em F5 quando a HTTP API de memórias for migrada para
    o BaseStore e ``src/nodes/base.py`` for atualizado.

Cada memória tem: chave, conteúdo, TTL (opcional), metadados e embedding.
Embeddings Cohere para busca semântica via ``search_semantic()``.
"""

import contextlib
import json
import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Any

import aiosqlite

from backend.settings import settings

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similaridade coseno em Python puro — sem numpy/scipy."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x**2 for x in a))
    norm_b = math.sqrt(sum(x**2 for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class MemoryStore:
    """Armazenador de memórias persistentes em SQLite."""

    def __init__(self, db_dsn: str | None = None) -> None:
        """Inicializa o store de memórias.

        Args:
            db_dsn: Caminho do SQLite. Se None, usa o padrão de settings.db_dsn.
        """
        dsn = db_dsn or settings.db_dsn
        if dsn is None:
            msg = "db_dsn must be provided or configured in settings"
            raise ValueError(msg)
        # Converte file:/// URLs para caminhos normais se necessário
        if dsn.startswith("file:///"):
            self.db_dsn = dsn[8:]  # Remove file:///
        else:
            self.db_dsn = dsn

    async def initialize(self) -> None:
        """Cria a tabela de memórias e adiciona coluna embedding se necessário."""
        async with aiosqlite.connect(self.db_dsn) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    embedding TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP,
                    UNIQUE(user_id, key)
                )
                """
            )
            # Migração graciosa: adiciona coluna embedding se tabela já existia sem ela
            with contextlib.suppress(Exception):
                await db.execute("ALTER TABLE memories ADD COLUMN embedding TEXT")
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_key ON memories(user_id, key)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_expires_at ON memories(expires_at)"
            )
            await db.commit()
            logger.info("Tabela de memórias inicializada")

    async def save(
        self,
        user_id: str,
        key: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        ttl_days: int | None = None,
        embedding: list[float] | None = None,
    ) -> str:
        """Salva ou atualiza uma memória.

        Args:
            user_id: ID do usuário (thread_id ou similar)
            key: Chave única da memória (ex: 'user_preferences', 'project_context')
            content: Conteúdo da memória (string)
            metadata: Metadados adicionais (dict)
            ttl_days: Dias até expiração (None = nunca expira)
            embedding: Vetor Cohere do conteúdo (C4 — busca semântica)

        Returns:
            ID da memória salva
        """
        now = datetime.now(UTC)
        expires_at = None
        if ttl_days is not None:
            expires_at = now + timedelta(days=ttl_days)

        memory_id = f"{user_id}:{key}"
        meta_json = json.dumps(metadata or {})
        emb_json = json.dumps(embedding) if embedding is not None else None

        async with aiosqlite.connect(self.db_dsn) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO memories
                (id, user_id, key, content, metadata, embedding,
                 created_at, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    user_id,
                    key,
                    content,
                    meta_json,
                    emb_json,
                    now.isoformat(),
                    now.isoformat(),
                    expires_at.isoformat() if expires_at else None,
                ),
            )
            await db.commit()

        logger.debug(
            "Memória salva: %s", memory_id, extra={"key": key, "user_id": user_id}
        )
        return memory_id

    async def get(self, user_id: str, key: str) -> dict[str, Any] | None:
        """Recupera uma memória pela chave.

        Args:
            user_id: ID do usuário
            key: Chave da memória

        Returns:
            Dict com {content, metadata, created_at, updated_at} ou None se não existe
        """
        async with aiosqlite.connect(self.db_dsn) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT content, metadata, created_at, updated_at, expires_at
                FROM memories
                WHERE user_id = ? AND key = ? AND (expires_at IS NULL OR expires_at > ?)
                """,
                (user_id, key, datetime.now(UTC).isoformat()),
            )
            row = await cursor.fetchone()

        if row is None:
            return None

        return {
            "content": row["content"],
            "metadata": json.loads(row["metadata"] or "{}"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "expires_at": row["expires_at"],
        }

    async def get_all(self, user_id: str) -> list[dict[str, Any]]:
        """Recupera todas as memórias ativas do usuário.

        Args:
            user_id: ID do usuário

        Returns:
            Lista de memórias {key, content, metadata, created_at, updated_at}
        """
        async with aiosqlite.connect(self.db_dsn) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT key, content, metadata, created_at, updated_at
                FROM memories
                WHERE user_id = ? AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY updated_at DESC
                """,
                (user_id, datetime.now(UTC).isoformat()),
            )
            rows = await cursor.fetchall()

        return [
            {
                "key": row["key"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"] or "{}"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    async def get_all_with_embeddings(self, user_id: str) -> list[dict[str, Any]]:
        """Recupera todas as memórias ativas incluindo o campo embedding (C4)."""
        async with aiosqlite.connect(self.db_dsn) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT key, content, metadata, embedding, created_at, updated_at
                FROM memories
                WHERE user_id = ? AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY updated_at DESC
                """,
                (user_id, datetime.now(UTC).isoformat()),
            )
            rows = await cursor.fetchall()

        return [
            {
                "key": row["key"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"] or "{}"),
                "embedding": row["embedding"],  # JSON string ou None
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    async def search_semantic(
        self,
        user_id: str,
        query_embedding: list[float],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Busca semântica: retorna memórias ordenadas por similaridade coseno (C4).

        Compara o `query_embedding` com os embeddings armazenados em Python puro —
        sem deps externas. Memórias sem embedding são incluídas no final com score 0.
        """
        all_mems = await self.get_all_with_embeddings(user_id)

        with_score: list[tuple[float, dict[str, Any]]] = []
        without_embedding: list[dict[str, Any]] = []

        for mem in all_mems:
            emb_json = mem.get("embedding")
            if emb_json:
                try:
                    emb = json.loads(emb_json)
                    score = _cosine_similarity(query_embedding, emb)
                    with_score.append((score, mem))
                except Exception:
                    without_embedding.append(mem)
            else:
                without_embedding.append(mem)

        with_score.sort(key=lambda x: x[0], reverse=True)
        ranked = [m for _, m in with_score] + without_embedding
        return ranked[:limit]

    async def delete(self, user_id: str, key: str) -> bool:
        """Deleta uma memória.

        Args:
            user_id: ID do usuário
            key: Chave da memória

        Returns:
            True se deletada, False se não existia
        """
        async with aiosqlite.connect(self.db_dsn) as db:
            cursor = await db.execute(
                "DELETE FROM memories WHERE user_id = ? AND key = ?",
                (user_id, key),
            )
            await db.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.debug("Memória deletada: %s:%s", user_id, key)
        return deleted

    async def delete_all(self) -> None:
        """Limpa todas as memórias (para testes)."""
        async with aiosqlite.connect(self.db_dsn) as db:
            await db.execute("DELETE FROM memories")
            await db.commit()

    async def cleanup_expired(self) -> int:
        """Remove memórias expiradas.

        Returns:
            Número de memórias removidas
        """
        async with aiosqlite.connect(self.db_dsn) as db:
            cursor = await db.execute(
                "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?",
                (datetime.now(UTC).isoformat(),),
            )
            await db.commit()
            deleted = cursor.rowcount

        if deleted > 0:
            logger.debug("Memórias expiradas removidas: %d", deleted)
        return deleted


# Instância global
_memory_store: MemoryStore | None = None


async def get_memory_store(db_dsn: str | None = None) -> MemoryStore:
    """Obtém a instância global de MemoryStore (lazy init)."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore(db_dsn)
        await _memory_store.initialize()
    return _memory_store
