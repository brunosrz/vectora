"""``VectoraPostgresSaver`` — checkpointer nativo do LangGraph sobre ``asyncpg``.

Substitui ``langgraph.checkpoint.postgres.aio.AsyncPostgresSaver`` (lib
``langgraph-checkpoint-postgres``). Mesma semântica/contrato de
``VectoraSqliteSaver`` (``backend/persistence/native/sqlite_checkpointer.py``)
— schema simplificado de 2 tabelas (a lib oficial usa um schema mais
elaborado com ``checkpoint_blobs`` separado, otimizado pra granularidade de
delta-channel; aqui o `checkpoint` inteiro vai num único ``BYTEA``, suficiente
pro contrato que ``BaseCheckpointSaver`` exige) — só os tipos de coluna e a
sintaxe SQL mudam (``$1``/``$2`` de placeholder, ``BYTEA``/``JSONB``).
"""

from __future__ import annotations

import json
import random
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

from backend.persistence.native.sqlite_checkpointer import _FILTER_KEY_PATTERN

if TYPE_CHECKING:
    import asyncpg
    from langchain_core.runnables import RunnableConfig

_SETUP_SQL = """
CREATE TABLE IF NOT EXISTS vectora_checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint BYTEA NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
CREATE TABLE IF NOT EXISTS vectora_checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    value BYTEA,
    task_path TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
CREATE INDEX IF NOT EXISTS idx_vectora_checkpoints_thread
    ON vectora_checkpoints(thread_id, checkpoint_ns, checkpoint_id DESC);
"""


def _metadata_where(
    metadata_filter: dict[str, Any], start_idx: int
) -> tuple[list[str], list[Any]]:
    predicates: list[str] = []
    values: list[Any] = []
    for key, value in metadata_filter.items():
        if not _FILTER_KEY_PATTERN.match(key):
            msg = f"Filter key inválida: {key!r}"
            raise ValueError(msg)
        idx = start_idx + len(values)
        if isinstance(value, (dict, list)):
            predicates.append(f"metadata->>{key!r} = ${idx}")
            values.append(json.dumps(value, separators=(",", ":")))
        else:
            predicates.append(f"metadata->>'{key}' = ${idx}::text")
            values.append(str(value) if value is not None else None)
    return predicates, values


def _search_where(
    config: RunnableConfig | None,
    filter_: dict[str, Any] | None,
    before: RunnableConfig | None,
) -> tuple[str, list[Any]]:
    wheres: list[str] = []
    params: list[Any] = []

    if config is not None:
        params.append(str(config["configurable"]["thread_id"]))
        wheres.append(f"thread_id = ${len(params)}")
        checkpoint_ns = config["configurable"].get("checkpoint_ns")
        if checkpoint_ns is not None:
            params.append(checkpoint_ns)
            wheres.append(f"checkpoint_ns = ${len(params)}")
        if checkpoint_id := get_checkpoint_id(config):
            params.append(checkpoint_id)
            wheres.append(f"checkpoint_id = ${len(params)}")

    if filter_:
        predicates, values = _metadata_where(filter_, len(params) + 1)
        wheres.extend(predicates)
        params.extend(values)

    if before is not None:
        params.append(get_checkpoint_id(before))
        wheres.append(f"checkpoint_id < ${len(params)}")

    return ("WHERE " + " AND ".join(wheres) if wheres else "", params)


class VectoraPostgresSaver(BaseCheckpointSaver[str]):
    """Checkpointer async sobre um ``asyncpg.Pool`` compartilhado (mesmo pool
    de ``backend.storage.factory.get_pg_pool()``)."""

    def __init__(
        self, pool: asyncpg.Pool, *, serde: SerializerProtocol | None = None
    ) -> None:
        super().__init__(serde=serde)
        self._pool = pool
        self._is_setup = False

    async def setup(self) -> None:
        if self._is_setup:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(_SETUP_SQL)
        self._is_setup = True

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        await self.setup()
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        thread_id = str(config["configurable"]["thread_id"])

        async with self._pool.acquire() as conn:
            if checkpoint_id := get_checkpoint_id(config):
                row = await conn.fetchrow(
                    "SELECT thread_id, checkpoint_id, parent_checkpoint_id, type, "
                    "checkpoint, metadata FROM vectora_checkpoints "
                    "WHERE thread_id = $1 AND checkpoint_ns = $2 AND checkpoint_id = $3",
                    thread_id,
                    checkpoint_ns,
                    checkpoint_id,
                )
            else:
                row = await conn.fetchrow(
                    "SELECT thread_id, checkpoint_id, parent_checkpoint_id, type, "
                    "checkpoint, metadata FROM vectora_checkpoints "
                    "WHERE thread_id = $1 AND checkpoint_ns = $2 "
                    "ORDER BY checkpoint_id DESC LIMIT 1",
                    thread_id,
                    checkpoint_ns,
                )
            if row is None:
                return None

            resolved_config: RunnableConfig = {
                "configurable": {
                    "thread_id": row["thread_id"],
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": row["checkpoint_id"],
                }
            }

            writes_rows = await conn.fetch(
                "SELECT task_id, channel, type, value FROM vectora_checkpoint_writes "
                "WHERE thread_id = $1 AND checkpoint_ns = $2 AND checkpoint_id = $3 "
                "ORDER BY task_id, idx",
                row["thread_id"],
                checkpoint_ns,
                row["checkpoint_id"],
            )

        metadata_raw = row["metadata"]
        return CheckpointTuple(
            resolved_config,
            self.serde.loads_typed((row["type"], bytes(row["checkpoint"]))),
            cast(
                "CheckpointMetadata",
                json.loads(metadata_raw)
                if isinstance(metadata_raw, str)
                else (metadata_raw or {}),
            ),
            (
                {
                    "configurable": {
                        "thread_id": row["thread_id"],
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": row["parent_checkpoint_id"],
                    }
                }
                if row["parent_checkpoint_id"]
                else None
            ),
            [
                (
                    w["task_id"],
                    w["channel"],
                    self.serde.loads_typed((w["type"], bytes(w["value"]))),
                )
                for w in writes_rows
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
        # `where` é montado só com predicados fixos (`$N`, nunca interpolando
        # valor de usuário — valores sempre viajam em `params`); f-string
        # aqui é concatenação de cláusula, não de dado.
        base = "SELECT thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata FROM vectora_checkpoints"
        query = f"{base} {where} ORDER BY checkpoint_id DESC"
        if limit is not None:
            params = [*params, limit]
            query += f" LIMIT ${len(params)}"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            for row in rows:
                writes_rows = await conn.fetch(
                    "SELECT task_id, channel, type, value FROM "
                    "vectora_checkpoint_writes WHERE thread_id = $1 AND "
                    "checkpoint_ns = $2 AND checkpoint_id = $3 ORDER BY task_id, idx",
                    row["thread_id"],
                    row["checkpoint_ns"],
                    row["checkpoint_id"],
                )
                metadata_raw = row["metadata"]
                yield CheckpointTuple(
                    {
                        "configurable": {
                            "thread_id": row["thread_id"],
                            "checkpoint_ns": row["checkpoint_ns"],
                            "checkpoint_id": row["checkpoint_id"],
                        }
                    },
                    self.serde.loads_typed((row["type"], bytes(row["checkpoint"]))),
                    cast(
                        "CheckpointMetadata",
                        json.loads(metadata_raw)
                        if isinstance(metadata_raw, str)
                        else (metadata_raw or {}),
                    ),
                    (
                        {
                            "configurable": {
                                "thread_id": row["thread_id"],
                                "checkpoint_ns": row["checkpoint_ns"],
                                "checkpoint_id": row["parent_checkpoint_id"],
                            }
                        }
                        if row["parent_checkpoint_id"]
                        else None
                    ),
                    [
                        (
                            w["task_id"],
                            w["channel"],
                            self.serde.loads_typed((w["type"], bytes(w["value"]))),
                        )
                        for w in writes_rows
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
        metadata_json = json.dumps(
            get_checkpoint_metadata(config, metadata), ensure_ascii=False
        )

        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO vectora_checkpoints (thread_id, checkpoint_ns, "
                "checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb) "
                "ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id) DO UPDATE SET "
                "parent_checkpoint_id = EXCLUDED.parent_checkpoint_id, "
                "type = EXCLUDED.type, checkpoint = EXCLUDED.checkpoint, "
                "metadata = EXCLUDED.metadata",
                thread_id,
                checkpoint_ns,
                checkpoint["id"],
                config["configurable"].get("checkpoint_id"),
                ckpt_type,
                checkpoint_blob,
                metadata_json,
            )

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
        is_special = all(channel in WRITES_IDX_MAP for channel, _ in writes)

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

        conflict_clause = (
            "DO UPDATE SET type = EXCLUDED.type, value = EXCLUDED.value, "
            "task_path = EXCLUDED.task_path"
            if is_special
            else "DO NOTHING"
        )
        # `conflict_clause` é uma de duas strings literais fixas (nunca
        # interpolação de dado) escolhida acima por `is_special`.
        insert_sql = (
            "INSERT INTO vectora_checkpoint_writes (thread_id, checkpoint_ns, "
            "checkpoint_id, task_id, idx, channel, type, value, task_path) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) "
            "ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id, task_id, idx) "
        )
        query = f"{insert_sql}{conflict_clause}"
        async with self._pool.acquire() as conn:
            await conn.executemany(
                query,
                rows,
            )

    async def adelete_thread(self, thread_id: str) -> None:
        await self.setup()
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM vectora_checkpoints WHERE thread_id = $1", str(thread_id)
            )
            await conn.execute(
                "DELETE FROM vectora_checkpoint_writes WHERE thread_id = $1",
                str(thread_id),
            )

    def get_next_version(self, current: str | None, channel: Any = None) -> str:
        if current is None:
            current_v = 0
        elif isinstance(current, int):
            current_v = current
        else:
            current_v = int(current.split(".")[0])
        next_v = current_v + 1
        next_h = random.random()  # noqa: S311  # nosec B311 (tie-break, nao seguranca)
        return f"{next_v:032}.{next_h:016}"
