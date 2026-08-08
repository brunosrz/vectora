"""Exercício real de ``VectoraStore`` — o único teste existente antes desta
auditoria (`test_e_b_parity.py::TestBuildStore`) fazia só
`isinstance(store, VectoraStore)`, sem nunca chamar `put`/`get`/`search`."""

from __future__ import annotations

from typing import Any, cast

import pytest
from langgraph.store.base import (
    GetOp,
    Item,
    ListNamespacesOp,
    MatchCondition,
    PutOp,
    SearchItem,
    SearchOp,
)

from backend.persistence.native.store import VectoraStore
from backend.storage.sqlite.pool import AsyncConnectionPool


@pytest.fixture
async def store(tmp_path):
    pool = AsyncConnectionPool(str(tmp_path / "store.db"), min_size=1, max_size=2)
    await pool.open()
    store = VectoraStore(pool)
    await store.setup()
    try:
        yield store
    finally:
        await pool.close()


async def _fake_embed(texts: list[str]) -> list[list[float]]:
    """Embedding determinístico só pra exercitar o caminho semântico sem
    depender de um provider real — dimensão fixa de 3."""
    return [[float(len(t)), float(len(t) % 3), 1.0] for t in texts]


@pytest.fixture
async def indexed_store(tmp_path):
    pool = AsyncConnectionPool(
        str(tmp_path / "store_indexed.db"), min_size=1, max_size=2
    )
    await pool.open()
    store = VectoraStore(
        pool, index={"dims": 3, "embed": _fake_embed, "fields": ["text"]}
    )
    await store.setup()
    try:
        yield store
    finally:
        await pool.close()


async def _put(
    store: VectoraStore, namespace: tuple[str, ...], key: str, value: dict | None
) -> None:
    await store.abatch([PutOp(namespace=namespace, key=key, value=value)])


async def _get(
    store: VectoraStore, namespace: tuple[str, ...], key: str
) -> Item | None:
    [result] = await store.abatch([GetOp(namespace=namespace, key=key)])
    return cast("Item | None", result)


async def _search(
    store: VectoraStore,
    namespace_prefix: tuple[str, ...],
    *,
    query: str | None = None,
    filter: dict[str, Any] | None = None,  # noqa: A002 — mesmo nome do SearchOp
    limit: int = 10,
    offset: int = 0,
) -> list[SearchItem]:
    [results] = await store.abatch(
        [
            SearchOp(
                namespace_prefix=namespace_prefix,
                query=query,
                filter=filter,
                limit=limit,
                offset=offset,
            )
        ]
    )
    return cast("list[SearchItem]", results)


async def _list_namespaces(
    store: VectoraStore,
    *,
    match_conditions: tuple[MatchCondition, ...] | None = None,
    max_depth: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[tuple[str, ...]]:
    [namespaces] = await store.abatch(
        [
            ListNamespacesOp(
                match_conditions=match_conditions,
                max_depth=max_depth,
                limit=limit,
                offset=offset,
            )
        ]
    )
    return cast("list[tuple[str, ...]]", namespaces)


class TestPutGet:
    async def test_round_trip_grava_e_le_um_item(self, store: VectoraStore):
        await _put(store, ("user", "u1", "memories"), "k1", {"fact": "gosta de café"})

        result = await _get(store, ("user", "u1", "memories"), "k1")

        assert result is not None
        assert result.value == {"fact": "gosta de café"}

    async def test_chave_inexistente_retorna_none(self, store: VectoraStore):
        result = await _get(store, ("user", "u1", "memories"), "ausente")

        assert result is None

    async def test_put_com_value_none_apaga_o_item(self, store: VectoraStore):
        await _put(store, ("user", "u1", "memories"), "k1", {"fact": "x"})
        await _put(store, ("user", "u1", "memories"), "k1", None)

        result = await _get(store, ("user", "u1", "memories"), "k1")
        assert result is None

    async def test_isolamento_entre_namespaces_de_usuarios_diferentes(
        self, store: VectoraStore
    ):
        await _put(store, ("user", "alice", "memories"), "k1", {"fact": "a"})
        await _put(store, ("user", "bob", "memories"), "k1", {"fact": "b"})

        alice_item = await _get(store, ("user", "alice", "memories"), "k1")
        assert alice_item is not None
        assert alice_item.value == {"fact": "a"}


class TestSearch:
    async def test_search_filtra_por_prefixo_de_namespace(self, store: VectoraStore):
        await _put(store, ("user", "u1", "memories"), "k1", {"fact": "x"})
        await _put(store, ("user", "u1", "prefs"), "k1", {"pref": "y"})

        results = await _search(store, ("user", "u1", "memories"))

        assert len(results) == 1
        assert results[0].value == {"fact": "x"}

    async def test_search_filtra_por_valor(self, store: VectoraStore):
        await _put(store, ("user", "u1", "memories"), "k1", {"category": "food"})
        await _put(store, ("user", "u1", "memories"), "k2", {"category": "travel"})

        results = await _search(
            store, ("user", "u1", "memories"), filter={"category": "food"}
        )

        assert len(results) == 1
        assert results[0].key == "k1"

    async def test_search_semantico_ordena_por_similaridade(
        self, indexed_store: VectoraStore
    ):
        await _put(indexed_store, ("user", "u1", "memories"), "curto", {"text": "ab"})
        await _put(
            indexed_store, ("user", "u1", "memories"), "longo", {"text": "abcdefgh"}
        )

        results = await _search(
            indexed_store, ("user", "u1", "memories"), query="abcdefgh"
        )

        assert results[0].key == "longo"
        assert results[0].score is not None


class TestListNamespaces:
    async def test_lista_namespaces_distintos(self, store: VectoraStore):
        await _put(store, ("user", "u1", "memories"), "k1", {})
        await _put(store, ("user", "u2", "memories"), "k1", {})

        namespaces = await _list_namespaces(store)

        assert set(namespaces) == {
            ("user", "u1", "memories"),
            ("user", "u2", "memories"),
        }

    async def test_filtra_por_prefixo(self, store: VectoraStore):
        await _put(store, ("user", "u1", "memories"), "k1", {})
        await _put(store, ("workspace", "w1", "files"), "k1", {})

        namespaces = await _list_namespaces(
            store,
            match_conditions=(MatchCondition(match_type="prefix", path=("user",)),),
        )

        assert namespaces == [("user", "u1", "memories")]


class TestBatchSincronoNaoSuportado:
    def test_batch_sincrono_levanta_not_implemented(self, store: VectoraStore):
        """`VectoraStore` é async-only (CLAUDE.md regra 10) — o método
        síncrono precisa falhar de forma explícita, nunca silenciosamente
        devolver lista vazia ou travar."""
        with pytest.raises(NotImplementedError, match="async-only"):
            store.batch([GetOp(namespace=("x",), key="k")])
