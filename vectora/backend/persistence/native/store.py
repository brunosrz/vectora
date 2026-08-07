"""``VectoraStore`` — Store nativo do LangGraph (memória cross-thread) sobre
``aiosqlite``.

Substitui ``langgraph.store.sqlite.aio.AsyncSqliteStore`` (lib
``langgraph-checkpoint-sqlite``, que também empacota o Store). ``BaseStore``
(``langgraph.store.base`` — parte do pacote ``langgraph`` em si, mantido)
só exige ``batch()``/``abatch()`` como abstratos; ``get``/``put``/``search``/
``delete``/``list_namespaces`` (e as versões ``a*``) já vêm implementadas na
classe base como wrappers finos sobre ``(a)batch()`` — só ``abatch()``
precisa de implementação real aqui.
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

if TYPE_CHECKING:
    from collections.abc import Iterable

    from backend.storage.sqlite.pool import AsyncConnectionPool

_SETUP_SQL = """
CREATE TABLE IF NOT EXISTS store_items (
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    embedding TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (namespace, key)
);
CREATE INDEX IF NOT EXISTS idx_store_items_namespace ON store_items(namespace);
"""

_NS_SEP = "\x1e"


def _ns_to_str(namespace: tuple[str, ...]) -> str:
    return _NS_SEP.join(namespace)


def _ns_from_str(namespace: str) -> tuple[str, ...]:
    return tuple(namespace.split(_NS_SEP)) if namespace else ()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


_FILTER_OPERATORS = {
    "$eq": lambda v, target: v == target,
    "$ne": lambda v, target: v != target,
    "$gt": lambda v, target: v is not None and v > target,
    "$gte": lambda v, target: v is not None and v >= target,
    "$lt": lambda v, target: v is not None and v < target,
    "$lte": lambda v, target: v is not None and v <= target,
}


def _matches_filter(value: dict[str, Any], filter_: dict[str, Any] | None) -> bool:
    if not filter_:
        return True
    for key, condition in filter_.items():
        actual = value.get(key)
        if isinstance(condition, dict):
            for op, target in condition.items():
                fn = _FILTER_OPERATORS.get(op)
                if fn is None or not fn(actual, target):
                    return False
        elif actual != condition:
            return False
    return True


class VectoraStore(BaseStore):
    """Store async sobre ``AsyncConnectionPool`` (aiosqlite), com busca
    semântica opcional via ``index`` (mesmo shape de ``IndexConfig`` que
    ``AsyncSqliteStore``/``AsyncPostgresStore`` aceitam:
    ``{"dims": int, "embed": Callable[[list[str]], Awaitable[list[list[float]]]], "fields": list[str]}``).
    """

    def __init__(
        self, pool: AsyncConnectionPool, *, index: dict[str, Any] | None = None
    ) -> None:
        self._pool = pool
        self._index = index
        self._is_setup = False

    async def setup(self) -> None:
        if self._is_setup:
            return
        async with self._pool.acquire() as conn:
            await conn.executescript(_SETUP_SQL)
            await conn.commit()
        self._is_setup = True

    def batch(self, ops: Iterable[Op]) -> list[Result]:
        msg = "VectoraStore é async-only (CLAUDE.md regra 10) — use abatch/aget/aput."
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
                msg = f"Op não suportada por VectoraStore: {type(op)!r}"
                raise NotImplementedError(msg)
        return results

    async def _get(self, op: GetOp) -> Item | None:
        async with self._pool.acquire() as conn:
            cur = await conn.execute(
                "SELECT value, created_at, updated_at FROM store_items "
                "WHERE namespace = ? AND key = ?",
                (_ns_to_str(op.namespace), op.key),
            )
            row = await cur.fetchone()
        if row is None:
            return None
        value_json, created_at, updated_at = row
        return Item(
            value=json.loads(value_json),
            key=op.key,
            namespace=op.namespace,
            created_at=datetime.fromisoformat(created_at),
            updated_at=datetime.fromisoformat(updated_at),
        )

    async def _put(self, op: PutOp) -> None:
        namespace_str = _ns_to_str(op.namespace)
        async with self._pool.acquire() as conn:
            if op.value is None:
                await conn.execute(
                    "DELETE FROM store_items WHERE namespace = ? AND key = ?",
                    (namespace_str, op.key),
                )
                await conn.commit()
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
                    # Um item pode indexar múltiplos campos/trechos — guarda
                    # a média dos vetores (aproximação simples, suficiente
                    # pro volume de memórias do agente; não é um índice
                    # multi-vetor por chunk como o RAG de documentos).
                    dims = self._index["dims"]
                    avg = [
                        sum(v[i] for v in vectors) / len(vectors) for i in range(dims)
                    ]
                    embedding_json = json.dumps(avg)

            now = datetime.now(UTC).isoformat()
            cur = await conn.execute(
                "SELECT created_at FROM store_items WHERE namespace = ? AND key = ?",
                (namespace_str, op.key),
            )
            existing = await cur.fetchone()
            created_at = existing[0] if existing else now

            await conn.execute(
                "INSERT OR REPLACE INTO store_items "
                "(namespace, key, value, embedding, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    namespace_str,
                    op.key,
                    json.dumps(op.value, ensure_ascii=False),
                    embedding_json,
                    created_at,
                    now,
                ),
            )
            await conn.commit()

    async def _search(self, op: SearchOp) -> list[SearchItem]:
        prefix = _ns_to_str(op.namespace_prefix)
        async with self._pool.acquire() as conn:
            if prefix:
                cur = await conn.execute(
                    "SELECT namespace, key, value, embedding, created_at, updated_at "
                    "FROM store_items WHERE namespace = ? OR namespace LIKE ?",
                    (prefix, f"{prefix}{_NS_SEP}%"),
                )
            else:
                cur = await conn.execute(
                    "SELECT namespace, key, value, embedding, created_at, updated_at "
                    "FROM store_items"
                )
            rows = await cur.fetchall()

        query_vector: list[float] | None = None
        if op.query and self._index is not None:
            vectors = await self._index["embed"]([op.query])
            query_vector = vectors[0] if vectors else None

        candidates: list[tuple[float | None, SearchItem]] = []
        for namespace, key, value_json, embedding_json, created_at, updated_at in rows:
            value = json.loads(value_json)
            if not _matches_filter(value, op.filter):
                continue
            score: float | None = None
            if query_vector is not None and embedding_json:
                score = _cosine_similarity(query_vector, json.loads(embedding_json))
            elif query_vector is not None:
                continue  # query semântica pedida, item sem embedding — exclui
            candidates.append(
                (
                    score,
                    SearchItem(
                        namespace=_ns_from_str(namespace),
                        key=key,
                        value=value,
                        created_at=datetime.fromisoformat(created_at),
                        updated_at=datetime.fromisoformat(updated_at),
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
            cur = await conn.execute("SELECT DISTINCT namespace FROM store_items")
            rows = await cur.fetchall()

        namespaces = {_ns_from_str(row[0]) for row in rows}

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
