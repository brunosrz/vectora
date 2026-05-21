"""Gerenciador de memórias persistentes em SQLite.

Armazena memórias globais do usuário que transcendem sessões individuais.
Cada memória tem: chave, conteúdo, TTL (opcional), e metadados.
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import aiosqlite

from vectora.config.settings import settings

logger = logging.getLogger(__name__)


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
        """Cria a tabela de memórias se não existir."""
        async with aiosqlite.connect(self.db_dsn) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP,
                    UNIQUE(user_id, key)
                )
                """
            )
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
    ) -> str:
        """Salva ou atualiza uma memória.

        Args:
            user_id: ID do usuário (thread_id ou similar)
            key: Chave única da memória (ex: 'user_preferences', 'project_context')
            content: Conteúdo da memória (string)
            metadata: Metadados adicionais (dict)
            ttl_days: Dias até expiração (None = nunca expira)

        Returns:
            ID da memória salva
        """
        now = datetime.now(UTC)
        expires_at = None
        if ttl_days is not None:
            expires_at = now + timedelta(days=ttl_days)

        memory_id = f"{user_id}:{key}"
        meta_json = json.dumps(metadata or {})

        async with aiosqlite.connect(self.db_dsn) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO memories
                (id, user_id, key, content, metadata, created_at, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    user_id,
                    key,
                    content,
                    meta_json,
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
