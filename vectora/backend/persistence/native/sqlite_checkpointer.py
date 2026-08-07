"""``VectoraSqliteSaver`` — checkpointer nativo do LangGraph sobre ``aiosqlite``.

Substitui ``langgraph.checkpoint.sqlite.aio.AsyncSqliteSaver`` (lib
``langgraph-checkpoint-sqlite``). Segue fielmente o schema e a semântica da
implementação oficial (mesmas 2 tabelas, mesmo uso do ``serde``/
``WRITES_IDX_MAP``/``get_checkpoint_id``/``get_checkpoint_metadata`` de
``langgraph.checkpoint.base`` — esses continuam vindo do pacote ``langgraph``
em si, não da lib ``-sqlite`` removida) — só o transporte SQL é nosso.

Vectora é async-only (CLAUDE.md regra 10): implementa só o lado
``a*``/``async``; os métodos síncronos (``get_tuple``/``list``/``put``/
``put_writes``/``delete_thread``) ficam com o ``NotImplementedError`` default
de ``BaseCheckpointSaver`` — nenhum caller do Vectora os invoca.
"""

from __future__ import annotations

import json
import random
import re
from collections.abc import AsyncIterator, Sequence
from typing import TYPE_CHECKING, Any, cast

from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    SerializerProtocol,
    get_checkpoint_id,
    get_checkpoint_metadata,
)

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig

    from backend.storage.sqlite.pool import AsyncConnectionPool

_SETUP_SQL = """
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint BLOB NOT NULL,
    metadata BLOB NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    value BLOB,
    task_path TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread
    ON checkpoints(thread_id, checkpoint_ns, checkpoint_id DESC);
"""

_FILTER_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+$")


def _metadata_where(metadata_filter: dict[str, Any]) -> tuple[list[str], list[Any]]:
    """Predicados SQL pra filtro de metadata — mesma forma de
    ``json_extract`` que a lib oficial usa, reimplementada aqui pra não
    depender de ``langgraph.checkpoint.sqlite.utils`` (parte da lib removida).
    """
    predicates: list[str] = []
    values: list[Any] = []
    for key, value in metadata_filter.items():
        if not _FILTER_KEY_PATTERN.match(key):
            msg = f"Filter key inválida: {key!r}"
            raise ValueError(msg)
        if value is None:
            predicates.append(f"json_extract(CAST(metadata AS TEXT), '$.{key}') IS ?")
            values.append(None)
        elif isinstance(value, bool):
            predicates.append(f"json_extract(CAST(metadata AS TEXT), '$.{key}') = ?")
            values.append(1 if value else 0)
        elif isinstance(value, (str, int, float)):
            predicates.append(f"json_extract(CAST(metadata AS TEXT), '$.{key}') = ?")
            values.append(value)
        else:
            predicates.append(f"json_extract(CAST(metadata AS TEXT), '$.{key}') = ?")
            values.append(json.dumps(value, separators=(",", ":")))
    return predicates, values


def _search_where(
    config: RunnableConfig | None,
    filter_: dict[str, Any] | None,
    before: RunnableConfig | None,
) -> tuple[str, list[Any]]:
    wheres: list[str] = []
    params: list[Any] = []

    if config is not None:
        wheres.append("thread_id = ?")
        params.append(str(config["configurable"]["thread_id"]))
        checkpoint_ns = config["configurable"].get("checkpoint_ns")
        if checkpoint_ns is not None:
            wheres.append("checkpoint_ns = ?")
            params.append(checkpoint_ns)
        if checkpoint_id := get_checkpoint_id(config):
            wheres.append("checkpoint_id = ?")
            params.append(checkpoint_id)

    if filter_:
        predicates, values = _metadata_where(filter_)
        wheres.extend(predicates)
        params.extend(values)

    if before is not None:
        wheres.append("checkpoint_id < ?")
        params.append(get_checkpoint_id(before))

    return ("WHERE " + " AND ".join(wheres) if wheres else "", params)


class VectoraSqliteSaver(BaseCheckpointSaver[str]):
    """Checkpointer async sobre um ``AsyncConnectionPool`` (aiosqlite) com os
    PRAGMAs de hardening já aplicados por conexão (WAL/busy_timeout/etc —
    ver ``backend/storage/sqlite/pool.py``)."""

    def __init__(
        self, pool: AsyncConnectionPool, *, serde: SerializerProtocol | None = None
    ) -> None:
        super().__init__(serde=serde)
        self._pool = pool
        self._is_setup = False

    async def setup(self) -> None:
        """Cria as tabelas se não existirem. Idempotente — chamado
        automaticamente por todo método público antes de qualquer query."""
        if self._is_setup:
            return
        async with self._pool.acquire() as conn:
            await conn.executescript(_SETUP_SQL)
            await conn.commit()
        self._is_setup = True

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        await self.setup()
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        thread_id = str(config["configurable"]["thread_id"])

        async with self._pool.acquire() as conn:
            if checkpoint_id := get_checkpoint_id(config):
                cur = await conn.execute(
                    "SELECT thread_id, checkpoint_id, parent_checkpoint_id, type, "
                    "checkpoint, metadata FROM checkpoints "
                    "WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?",
                    (thread_id, checkpoint_ns, checkpoint_id),
                )
            else:
                cur = await conn.execute(
                    "SELECT thread_id, checkpoint_id, parent_checkpoint_id, type, "
                    "checkpoint, metadata FROM checkpoints "
                    "WHERE thread_id = ? AND checkpoint_ns = ? "
                    "ORDER BY checkpoint_id DESC LIMIT 1",
                    (thread_id, checkpoint_ns),
                )
            row = await cur.fetchone()
            if row is None:
                return None

            (
                row_thread_id,
                row_checkpoint_id,
                parent_checkpoint_id,
                ckpt_type,
                checkpoint_blob,
                metadata_blob,
            ) = row

            resolved_config: RunnableConfig = {
                "configurable": {
                    "thread_id": row_thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": row_checkpoint_id,
                }
            }

            writes_cur = await conn.execute(
                "SELECT task_id, channel, type, value FROM checkpoint_writes "
                "WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ? "
                "ORDER BY task_id, idx",
                (row_thread_id, checkpoint_ns, row_checkpoint_id),
            )
            writes_rows = await writes_cur.fetchall()

        return CheckpointTuple(
            resolved_config,
            self.serde.loads_typed((ckpt_type, checkpoint_blob)),
            cast(
                "CheckpointMetadata",
                json.loads(metadata_blob) if metadata_blob is not None else {},
            ),
            (
                {
                    "configurable": {
                        "thread_id": row_thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent_checkpoint_id,
                    }
                }
                if parent_checkpoint_id
                else None
            ),
            [
                (task_id, channel, self.serde.loads_typed((wtype, value)))
                for task_id, channel, wtype, value in writes_rows
            ],
        )

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,  # noqa: A002 — nome exigido pelo override de BaseCheckpointSaver.alist
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        await self.setup()
        where, params = _search_where(config, filter, before)
        # `where` é montado só com predicados fixos ("thread_id = ?" etc,
        # nunca interpolando valor de usuário — valores sempre viajam em
        # `params`); f-string aqui é concatenação de cláusula, não de dado.
        base = "SELECT thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata FROM checkpoints"
        query = f"{base} {where} ORDER BY checkpoint_id DESC"
        if limit is not None:
            query += " LIMIT ?"
            params = [*params, limit]

        async with self._pool.acquire() as conn:
            cur = await conn.execute(query, params)
            rows = await cur.fetchall()

            for (
                thread_id,
                checkpoint_ns,
                checkpoint_id,
                parent_checkpoint_id,
                ckpt_type,
                checkpoint_blob,
                metadata_blob,
            ) in rows:
                wcur = await conn.execute(
                    "SELECT task_id, channel, type, value FROM checkpoint_writes "
                    "WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ? "
                    "ORDER BY task_id, idx",
                    (thread_id, checkpoint_ns, checkpoint_id),
                )
                writes_rows = await wcur.fetchall()

                yield CheckpointTuple(
                    {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": checkpoint_id,
                        }
                    },
                    self.serde.loads_typed((ckpt_type, checkpoint_blob)),
                    cast(
                        "CheckpointMetadata",
                        json.loads(metadata_blob) if metadata_blob is not None else {},
                    ),
                    (
                        {
                            "configurable": {
                                "thread_id": thread_id,
                                "checkpoint_ns": checkpoint_ns,
                                "checkpoint_id": parent_checkpoint_id,
                            }
                        }
                        if parent_checkpoint_id
                        else None
                    ),
                    [
                        (task_id, channel, self.serde.loads_typed((wtype, value)))
                        for task_id, channel, wtype, value in writes_rows
                    ],
                )

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        await self.setup()
        thread_id = str(config["configurable"]["thread_id"])
        checkpoint_ns = config["configurable"]["checkpoint_ns"]
        ckpt_type, checkpoint_blob = self.serde.dumps_typed(checkpoint)
        metadata_blob = json.dumps(
            get_checkpoint_metadata(config, metadata), ensure_ascii=False
        ).encode("utf-8", "ignore")

        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO checkpoints (thread_id, checkpoint_ns, "
                "checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    thread_id,
                    checkpoint_ns,
                    checkpoint["id"],
                    config["configurable"].get("checkpoint_id"),
                    ckpt_type,
                    checkpoint_blob,
                    metadata_blob,
                ),
            )
            await conn.commit()

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        await self.setup()
        thread_id = str(config["configurable"]["thread_id"])
        checkpoint_ns = str(config["configurable"]["checkpoint_ns"])
        checkpoint_id = str(config["configurable"]["checkpoint_id"])

        # Writes especiais (erro/scheduled/interrupt/resume, índice negativo
        # via WRITES_IDX_MAP) são idempotentes por natureza — sobrescrever é
        # seguro. Writes regulares (índice >= 0, um por posição na lista)
        # usam INSERT OR IGNORE: uma segunda tentativa da mesma task não deve
        # duplicar nem sobrescrever o que já foi persistido.
        query = (
            "INSERT OR REPLACE INTO checkpoint_writes (thread_id, checkpoint_ns, "
            "checkpoint_id, task_id, idx, channel, type, value, task_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            if all(channel in WRITES_IDX_MAP for channel, _ in writes)
            else "INSERT OR IGNORE INTO checkpoint_writes (thread_id, checkpoint_ns, "
            "checkpoint_id, task_id, idx, channel, type, value, task_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )

        rows = []
        for idx, (channel, value) in enumerate(writes):
            wtype, blob = self.serde.dumps_typed(value)
            rows.append(
                (
                    thread_id,
                    checkpoint_ns,
                    checkpoint_id,
                    task_id,
                    WRITES_IDX_MAP.get(channel, idx),
                    channel,
                    wtype,
                    blob,
                    task_path,
                )
            )

        async with self._pool.acquire() as conn:
            await conn.executemany(query, rows)
            await conn.commit()

    async def adelete_thread(self, thread_id: str) -> None:
        await self.setup()
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM checkpoints WHERE thread_id = ?", (str(thread_id),)
            )
            await conn.execute(
                "DELETE FROM checkpoint_writes WHERE thread_id = ?", (str(thread_id),)
            )
            await conn.commit()

    def get_next_version(self, current: str | None, channel: Any = None) -> str:
        """Versão string monotônica com desempate aleatório — mesmo formato
        de ``AsyncSqliteSaver.get_next_version`` (evita colisão entre
        writes concorrentes no mesmo step)."""
        if current is None:
            current_v = 0
        elif isinstance(current, int):
            current_v = current
        else:
            current_v = int(current.split(".")[0])
        next_v = current_v + 1
        next_h = random.random()  # noqa: S311  # nosec B311 (tie-break, nao seguranca)
        return f"{next_v:032}.{next_h:016}"
