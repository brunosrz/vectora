"""Tests para o search_memory tool (busca semântica via LangGraph BaseStore)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# search_memory tool
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
