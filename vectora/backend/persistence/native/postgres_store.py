"""``VectoraPostgresStore`` — Store nativo do LangGraph sobre ``asyncpg``.

Substitui ``langgraph.store.postgres.aio.AsyncPostgresStore`` (lib
``langgraph-checkpoint-postgres``). Mesma lógica de
``backend/persistence/native/store.py::VectoraStore`` (SQLite) — só o
transporte SQL muda (``$1``/``$2``, ``JSONB``).
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from langgraph.store.base import (
    BaseStore,
    GetOp,
    Item,
    ListNamespacesOp,
    Op,
    PutOp,
    Result,
    SearchItem,
    SearchOp,
)
from langgraph.store.base.embed import get_text_at_path

from backend.persistence.native.store import (
    _matches_filter,
    _ns_from_str,
    _ns_to_str,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    import asyncpg

_SETUP_SQL = """
CREATE TABLE IF NOT EXISTS vectora_store_items (
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    embedding JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (namespace, key)
);
CREATE INDEX IF NOT EXISTS idx_vectora_store_items_namespace
    ON vectora_store_items(namespace);
"""


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class VectoraPostgresStore(BaseStore):
    """Store async sobre ``asyncpg.Pool``. Mesmo shape de ``index``
    (``IndexConfig``) que ``VectoraStore``/``AsyncPostgresStore`` aceitam."""

    def __init__(
        self, pool: asyncpg.Pool, *, index: dict[str, Any] | None = None
    ) -> None:
        self._pool = pool
        self._index = index
        self._is_setup = False

    async def setup(self) -> None:
        if self._is_setup:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(_SETUP_SQL)
        self._is_setup = True

    def batch(self, ops: Iterable[Op]) -> list[Result]:
        msg = (
            "VectoraPostgresStore é async-only (CLAUDE.md regra 10) — "
            "use abatch/aget/aput."
        )
        raise NotImplementedError(msg)

    async def abatch(self, ops: Iterable[Op]) -> list[Result]:
        await self.setup()
        results: list[Result] = []
        for op in ops:
            if isinstance(op, GetOp):
                results.append(await self._get(op))
            elif isinstance(op, PutOp):
                await self._put(op)
                results.append(None)
            elif isinstance(op, SearchOp):
                results.append(await self._search(op))
            elif isinstance(op, ListNamespacesOp):
                results.append(await self._list_namespaces(op))
            else:
                msg = f"Op não suportada por VectoraPostgresStore: {type(op)!r}"
                raise NotImplementedError(msg)
        return results

    async def _get(self, op: GetOp) -> Item | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value, created_at, updated_at FROM vectora_store_items "
                "WHERE namespace = $1 AND key = $2",
                _ns_to_str(op.namespace),
                op.key,
            )
        if row is None:
            return None
        value = row["value"]
        return Item(
            value=json.loads(value) if isinstance(value, str) else value,
            key=op.key,
            namespace=op.namespace,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def _put(self, op: PutOp) -> None:
        namespace_str = _ns_to_str(op.namespace)
        async with self._pool.acquire() as conn:
            if op.value is None:
                await conn.execute(
                    "DELETE FROM vectora_store_items WHERE namespace = $1 AND key = $2",
                    namespace_str,
                    op.key,
                )
                return

            embedding_json: str | None = None
            if self._index is not None and op.index is not False:
                fields = (
                    op.index
                    if isinstance(op.index, list)
                    else self._index.get("fields", ["$"])
                )
                texts: list[str] = []
                for field in fields:
                    texts.extend(get_text_at_path(op.value, field))
                if texts:
                    vectors = await self._index["embed"](texts)
                    dims = self._index["dims"]
                    avg = [
                        sum(v[i] for v in vectors) / len(vectors) for i in range(dims)
                    ]
                    embedding_json = json.dumps(avg)

            now = datetime.now(UTC)
            await conn.execute(
                "INSERT INTO vectora_store_items "
                "(namespace, key, value, embedding, created_at, updated_at) "
                "VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $5) "
                "ON CONFLICT (namespace, key) DO UPDATE SET "
                "value = EXCLUDED.value, embedding = EXCLUDED.embedding, "
                "updated_at = EXCLUDED.updated_at",
                namespace_str,
                op.key,
                json.dumps(op.value, ensure_ascii=False),
                embedding_json,
                now,
            )

    async def _search(self, op: SearchOp) -> list[SearchItem]:
        prefix = _ns_to_str(op.namespace_prefix)
        async with self._pool.acquire() as conn:
            if prefix:
                rows = await conn.fetch(
                    "SELECT namespace, key, value, embedding, created_at, updated_at "
                    "FROM vectora_store_items WHERE namespace = $1 OR namespace LIKE $2",
                    prefix,
                    f"{prefix}\x1e%",
                )
            else:
                rows = await conn.fetch(
                    "SELECT namespace, key, value, embedding, created_at, updated_at "
                    "FROM vectora_store_items"
                )

        query_vector: list[float] | None = None
        if op.query and self._index is not None:
            vectors = await self._index["embed"]([op.query])
            query_vector = vectors[0] if vectors else None

        candidates: list[tuple[float | None, SearchItem]] = []
        for row in rows:
            value = row["value"]
            value = json.loads(value) if isinstance(value, str) else value
            if not _matches_filter(value, op.filter):
                continue
            embedding = row["embedding"]
            score: float | None = None
            if query_vector is not None and embedding:
                embedding_vec = (
                    json.loads(embedding) if isinstance(embedding, str) else embedding
                )
                score = _cosine_similarity(query_vector, embedding_vec)
            elif query_vector is not None:
                continue
            candidates.append(
                (
                    score,
                    SearchItem(
                        namespace=_ns_from_str(row["namespace"]),
                        key=row["key"],
                        value=value,
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        score=score,
                    ),
                )
            )

        if query_vector is not None:
            candidates.sort(key=lambda pair: pair[0] or 0.0, reverse=True)

        page = candidates[op.offset : op.offset + op.limit]
        return [item for _, item in page]

    async def _list_namespaces(self, op: ListNamespacesOp) -> list[tuple[str, ...]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT namespace FROM vectora_store_items"
            )

        namespaces = {_ns_from_str(row["namespace"]) for row in rows}

        if op.match_conditions:
            filtered = set()
            for ns in namespaces:
                for cond in op.match_conditions:
                    path = tuple(p for p in cond.path if p != "*")
                    if (cond.match_type == "prefix" and ns[: len(path)] == path) or (
                        cond.match_type == "suffix"
                        and (not path or ns[-len(path) :] == path)
                    ):
                        filtered.add(ns)
            namespaces = filtered

        if op.max_depth is not None:
            namespaces = {ns[: op.max_depth] for ns in namespaces}

        ordered = sorted(namespaces)
        return ordered[op.offset : op.offset + op.limit]
