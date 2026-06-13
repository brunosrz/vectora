"""Tests para C4 — Semantic Memory (cosine similarity + search_semantic + search_memory tool)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.memory import MemoryStore, _cosine_similarity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unit(v: list[float]) -> list[float]:
    """Retorna vetor normalizado (norma 1)."""
    norm = math.sqrt(sum(x**2 for x in v))
    return [x / norm for x in v]


# ---------------------------------------------------------------------------
# C4 — _cosine_similarity
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    def test_identical_vectors_return_one(self):
        v = _unit([1.0, 2.0, 3.0])
        assert _cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors_return_zero(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert _cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors_return_minus_one(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert _cosine_similarity(a, b) == pytest.approx(-1.0, abs=1e-6)

    def test_zero_vector_returns_zero(self):
        assert _cosine_similarity([0.0, 0.0], [1.0, 2.0]) == pytest.approx(0.0)

    def test_partial_overlap(self):
        a = _unit([1.0, 1.0])
        b = _unit([1.0, 0.0])
        sim = _cosine_similarity(a, b)
        # cos(45°) ≈ 0.707
        assert 0.6 < sim < 0.8

    def test_similar_vectors_rank_higher_than_dissimilar(self):
        anchor = _unit([1.0, 0.5, 0.0])
        similar = _unit([0.9, 0.4, 0.1])
        dissimilar = _unit([0.0, 0.0, 1.0])
        assert _cosine_similarity(anchor, similar) > _cosine_similarity(
            anchor, dissimilar
        )


# ---------------------------------------------------------------------------
# C4 — MemoryStore.search_semantic
# ---------------------------------------------------------------------------


@pytest.fixture
async def mem_store(tmp_path: Path):
    """MemoryStore em banco temporário."""
    db_path = str(tmp_path / "test_memories.db")
    store = MemoryStore(db_dsn=db_path)
    await store.initialize()
    return store


class TestSearchSemantic:
    @pytest.mark.asyncio
    async def test_returns_closest_memory(self, mem_store: MemoryStore):
        """Memória com embedding mais próximo da query deve ranquear primeiro."""
        # Salva dois docs com vetores opostos
        emb_jwt = _unit([1.0, 0.0, 0.0])
        emb_python = _unit([0.0, 1.0, 0.0])

        await mem_store.save("u1", "jwt_doc", "JWT é um token", embedding=emb_jwt)
        await mem_store.save("u1", "python_doc", "Python é legal", embedding=emb_python)

        # Query próxima a jwt
        query_emb = _unit([0.95, 0.05, 0.0])
        results = await mem_store.search_semantic("u1", query_emb, limit=2)

        assert len(results) == 2
        assert results[0]["key"] == "jwt_doc"

    @pytest.mark.asyncio
    async def test_memories_without_embedding_appended_last(
        self, mem_store: MemoryStore
    ):
        """Memórias sem embedding devem aparecer após as com embedding."""
        emb = _unit([1.0, 0.0])
        await mem_store.save("u2", "with_emb", "tem embedding", embedding=emb)
        await mem_store.save("u2", "without_emb", "sem embedding")  # sem embedding

        query = _unit([1.0, 0.0])
        results = await mem_store.search_semantic("u2", query, limit=5)

        assert len(results) == 2
        assert results[0]["key"] == "with_emb"
        assert results[1]["key"] == "without_emb"

    @pytest.mark.asyncio
    async def test_limit_is_respected(self, mem_store: MemoryStore):
        for i in range(5):
            emb = _unit([float(i + 1), 0.0])
            await mem_store.save("u3", f"key{i}", f"content {i}", embedding=emb)

        results = await mem_store.search_semantic("u3", _unit([1.0, 0.0]), limit=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_empty_store_returns_empty(self, mem_store: MemoryStore):
        results = await mem_store.search_semantic("nobody", [1.0, 0.0], limit=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_isolation_between_users(self, mem_store: MemoryStore):
        """Busca semântica deve respeitar o user_id."""
        emb = _unit([1.0, 0.0])
        await mem_store.save("user_a", "note", "pertence ao A", embedding=emb)

        results = await mem_store.search_semantic("user_b", emb, limit=5)
        assert results == []


# ---------------------------------------------------------------------------
# C4 — search_memory tool
# ---------------------------------------------------------------------------


class _FakeStoreItem:
    """Item retornado pelo BaseStore.asearch — com .key, .value, .score.

    O ``search_memory`` agora delega ao store do LangGraph (``_get_store()``);
    a flag ``semantic`` é derivada de o item ter ``.score`` não-nulo (o store
    com índice vetorial retorna score; sem índice, score é None).
    """

    def __init__(self, key: str, content: str, score: float | None = None) -> None:
        self.key = key
        self.value = {"content": content, "updated_at": "2025"}
        self.score = score


class TestSearchMemoryTool:
    @pytest.mark.asyncio
    async def test_search_with_scores_is_semantic(self):
        """Itens com score (store indexado) → semantic=True e score exposto."""
        from backend.tools.memory import search_memory

        config = {"configurable": {"thread_id": "t1"}}
        store = AsyncMock()
        store.asearch = AsyncMock(
            return_value=[_FakeStoreItem("k1", "resultado semântico", score=0.9)]
        )

        with patch("backend.tools.memory._get_store", return_value=store):
            raw = await search_memory.ainvoke(
                {"query": "jwt auth", "config": config, "limit": 5}
            )

        data = json.loads(raw)
        assert data["status"] == "success"
        assert data["semantic"] is True
        assert data["count"] == 1
        assert data["memories"][0]["key"] == "k1"
        assert data["memories"][0]["score"] == 0.9

    @pytest.mark.asyncio
    async def test_search_without_scores_is_not_semantic(self):
        """Itens sem score (store sem índice) → semantic=False, sem ranqueamento."""
        from backend.tools.memory import search_memory

        config = {"configurable": {"thread_id": "t2"}}
        store = AsyncMock()
        store.asearch = AsyncMock(
            return_value=[_FakeStoreItem("k1", "m1"), _FakeStoreItem("k2", "m2")]
        )

        with patch("backend.tools.memory._get_store", return_value=store):
            raw = await search_memory.ainvoke(
                {"query": "qualquer coisa", "config": config, "limit": 5}
            )

        data = json.loads(raw)
        assert data["status"] == "success"
        assert data["semantic"] is False
        assert data["count"] == 2

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Store vazio → success com count 0."""
        from backend.tools.memory import search_memory

        config = {"configurable": {"thread_id": "t3"}}
        store = AsyncMock()
        store.asearch = AsyncMock(return_value=[])

        with patch("backend.tools.memory._get_store", return_value=store):
            raw = await search_memory.ainvoke(
                {"query": "teste", "config": config, "limit": 5}
            )

        data = json.loads(raw)
        assert data["status"] == "success"
        assert data["count"] == 0

    @pytest.mark.asyncio
    async def test_error_returns_failed(self):
        """Exceção ao obter o store retorna status failed com a mensagem."""
        from backend.tools.memory import search_memory

        config = {"configurable": {"thread_id": "t4"}}

        with patch(
            "backend.tools.memory._get_store",
            side_effect=Exception("db error"),
        ):
            raw = await search_memory.ainvoke(
                {"query": "teste", "config": config, "limit": 5}
            )

        data = json.loads(raw)
        assert data["status"] == "failed"
        assert "db error" in data["error"]
