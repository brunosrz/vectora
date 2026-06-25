"""Testes para backend/services/context_graph/graph_index.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.context_graph.graph_index import (
    index_graph_nodes,
    purge_graph_index,
    search_graph_nodes,
)

_GRAPH_DATA = {
    "nodes": [
        {
            "id": "n.auth",
            "label": "AuthService",
            "file_type": "code",
            "source_file": "auth.py",
            "docstring": "Handles authentication.",
        },
        {
            "id": "n.token",
            "label": "TokenHandler",
            "file_type": "code",
            "source_file": "token.py",
        },
        {
            "id": "n.db",
            "label": "Database",
            "file_type": "code",
            "source_file": "db.py",
        },
    ],
    "edges": [],
}


def _mock_lancedb():
    """Mock do LanceDB para testes sem conexão real."""
    db = AsyncMock()
    table = AsyncMock()
    table.count_rows = AsyncMock(return_value=0)
    db.table_names = AsyncMock(return_value=[])
    db.create_table = AsyncMock(return_value=table)
    db.open_table = AsyncMock(return_value=table)
    db.drop_table = AsyncMock()
    return db


class TestIndexGraphNodes:
    @pytest.mark.asyncio
    async def test_empty_graph_indexes_zero(self) -> None:
        db = _mock_lancedb()
        with (
            patch(
                "backend.services.context_graph.graph_index._get_db",
                new_callable=AsyncMock,
                return_value=db,
            ),
            patch(
                "backend.services.context_graph.graph_index._embed_texts",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            count = await index_graph_nodes("ws-1", {"nodes": [], "edges": []})
        assert count == 0

    @pytest.mark.asyncio
    async def test_three_nodes_indexes_three(self) -> None:
        db = _mock_lancedb()
        fake_vectors = [[0.1] * 10, [0.2] * 10, [0.3] * 10]
        with (
            patch(
                "backend.services.context_graph.graph_index._get_db",
                new_callable=AsyncMock,
                return_value=db,
            ),
            patch(
                "backend.services.context_graph.graph_index._embed_texts",
                new_callable=AsyncMock,
                return_value=fake_vectors,
            ),
        ):
            count = await index_graph_nodes("ws-1", _GRAPH_DATA)
        assert count == 3

    @pytest.mark.asyncio
    async def test_node_without_docstring_does_not_break(self) -> None:
        db = _mock_lancedb()
        data = {
            "nodes": [{"id": "n.x", "label": "X", "file_type": "code"}],
            "edges": [],
        }
        fake_vectors = [[0.5] * 10]
        with (
            patch(
                "backend.services.context_graph.graph_index._get_db",
                new_callable=AsyncMock,
                return_value=db,
            ),
            patch(
                "backend.services.context_graph.graph_index._embed_texts",
                new_callable=AsyncMock,
                return_value=fake_vectors,
            ),
        ):
            count = await index_graph_nodes("ws-1", data)
        assert count == 1


class TestSearchGraphNodes:
    @pytest.mark.asyncio
    async def test_returns_node_ids_from_search(self) -> None:
        db = _mock_lancedb()
        table = db.open_table.return_value
        mock_df = MagicMock()
        mock_df.iterrows.return_value = iter(
            [
                (
                    0,
                    {
                        "id": "n.auth",
                        "metadata": '{"node_id": "n.auth", "workspace_id": "ws-1"}',
                    },
                ),
            ]
        )
        table.vector_search.return_value.limit.return_value.to_pandas = AsyncMock(
            return_value=mock_df
        )
        db.table_names = AsyncMock(return_value=["context_graph_nodes"])

        with (
            patch(
                "backend.services.context_graph.graph_index._get_db",
                new_callable=AsyncMock,
                return_value=db,
            ),
            patch(
                "backend.services.context_graph.graph_index._embed_texts",
                new_callable=AsyncMock,
                return_value=[[0.1] * 10],
            ),
        ):
            node_ids = await search_graph_nodes("authentication", "ws-1", top_k=5)
        assert isinstance(node_ids, list)

    @pytest.mark.asyncio
    async def test_lancedb_unavailable_returns_empty(self) -> None:
        with patch(
            "backend.services.context_graph.graph_index._get_db",
            side_effect=Exception("LanceDB not available"),
        ):
            node_ids = await search_graph_nodes("anything", "ws-1")
        assert node_ids == []


class TestPurgeGraphIndex:
    @pytest.mark.asyncio
    async def test_purge_without_nodes_does_not_break(self) -> None:
        db = _mock_lancedb()
        db.table_names = AsyncMock(return_value=[])
        with patch(
            "backend.services.context_graph.graph_index._get_db",
            new_callable=AsyncMock,
            return_value=db,
        ):
            await purge_graph_index("ws-1")

    @pytest.mark.asyncio
    async def test_purge_calls_delete_on_existing_table(self) -> None:
        db = _mock_lancedb()
        table = AsyncMock()
        table.delete = AsyncMock()
        db.table_names = AsyncMock(return_value=["context_graph_nodes"])
        db.open_table = AsyncMock(return_value=table)
        with patch(
            "backend.services.context_graph.graph_index._get_db",
            new_callable=AsyncMock,
            return_value=db,
        ):
            await purge_graph_index("ws-1")
        table.delete.assert_called_once()
