"""Tests para C4 — Semantic Memory (cosine similarity + search_semantic + search_memory tool)."""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from vectora.services.memory import MemoryStore, _cosine_similarity

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


class TestSearchMemoryTool:
    @pytest.mark.asyncio
    async def test_semantic_search_with_cohere(self):
        """Quando Cohere disponível e semantic enabled, usa cosine similarity."""
        from vectora.tools.memory import search_memory

        config = {"configurable": {"thread_id": "t1"}}

        query_emb = [0.1, 0.2, 0.3]
        mock_result = [
            {"key": "k1", "content": "resultado semântico", "updated_at": "2025"}
        ]

        with (
            patch("vectora.config.settings.settings") as ms,
            patch("vectora.services.memory.get_memory_store") as mock_gs,
        ):
            ms.memory_semantic_enabled = True
            ms.get_cohere_api_key.return_value = "fake-key"
            ms.embedding_model = "embed-multilingual-v3.0"

            mock_store = AsyncMock()
            mock_store.search_semantic = AsyncMock(return_value=mock_result)
            mock_gs.return_value = mock_store

            # Mock do client Cohere
            mock_embed_resp = AsyncMock()
            mock_embed_resp.embeddings = [query_emb]

            mock_client = AsyncMock()
            mock_client.embed = AsyncMock(return_value=mock_embed_resp)

            with patch("cohere.AsyncClient", return_value=mock_client):
                raw = await search_memory.ainvoke(
                    {"query": "jwt auth", "config": config, "limit": 5}
                )

        data = json.loads(raw)
        assert data["status"] == "success"
        assert data["semantic"] is True
        assert data["count"] == 1
        assert data["memories"][0]["key"] == "k1"

    @pytest.mark.asyncio
    async def test_fallback_when_semantic_disabled(self):
        """Quando semantic desabilitado, retorna todas sem ranqueamento."""
        from vectora.tools.memory import search_memory

        config = {"configurable": {"thread_id": "t2"}}
        all_mems = [
            {"key": "k1", "content": "m1", "updated_at": "2025"},
            {"key": "k2", "content": "m2", "updated_at": "2025"},
        ]

        with (
            patch("vectora.config.settings.settings") as ms,
            patch("vectora.services.memory.get_memory_store") as mock_gs,
        ):
            ms.memory_semantic_enabled = False

            mock_store = AsyncMock()
            mock_store.get_all = AsyncMock(return_value=all_mems)
            mock_gs.return_value = mock_store

            raw = await search_memory.ainvoke(
                {"query": "qualquer coisa", "config": config, "limit": 5}
            )

        data = json.loads(raw)
        assert data["status"] == "success"
        assert data["semantic"] is False
        assert data["count"] == 2

    @pytest.mark.asyncio
    async def test_fallback_when_no_api_key(self):
        """Sem API key Cohere, degrada para retornar todas as memórias."""
        from vectora.tools.memory import search_memory

        config = {"configurable": {"thread_id": "t3"}}

        with (
            patch("vectora.config.settings.settings") as ms,
            patch("vectora.services.memory.get_memory_store") as mock_gs,
        ):
            ms.memory_semantic_enabled = True
            ms.get_cohere_api_key.return_value = None  # sem key

            mock_store = AsyncMock()
            mock_store.get_all = AsyncMock(return_value=[])
            mock_gs.return_value = mock_store

            raw = await search_memory.ainvoke(
                {"query": "teste", "config": config, "limit": 5}
            )

        data = json.loads(raw)
        assert data["status"] == "success"
        assert data["semantic"] is False

    @pytest.mark.asyncio
    async def test_error_returns_failed(self):
        """Exceção em qualquer ponto retorna status failed."""
        from vectora.tools.memory import search_memory

        config = {"configurable": {"thread_id": "t4"}}

        with patch(
            "vectora.services.memory.get_memory_store",
            side_effect=Exception("db error"),
        ):
            raw = await search_memory.ainvoke(
                {"query": "teste", "config": config, "limit": 5}
            )

        data = json.loads(raw)
        assert data["status"] == "failed"
        assert "db error" in data["error"]
