"""Testes unitários de `QdrantBackend` — mocka `AsyncQdrantClient` pra pegar
bug estrutural (nome de parâmetro errado, parsing de forma de resposta
errada) sem depender de um Qdrant real rodando (isso é coberto pelos
testes reais em `tests/integration/test_storage_qdrant.py`)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from qdrant_client.http.models import (
    CollectionDescription,
    CollectionsResponse,
    CountResult,
    QueryResponse,
    Record,
    ScoredPoint,
)

from backend.storage.vectorstore.base import VectorRow
from backend.storage.vectorstore.qdrant_backend import QdrantBackend


@pytest.fixture
def backend():
    return QdrantBackend(url="http://localhost:6333")


@pytest.fixture
def mock_client():
    with patch("backend.storage.vectorstore.qdrant_backend.AsyncQdrantClient") as cls:
        instance = AsyncMock()
        cls.return_value = instance
        yield instance


class TestQdrantBackendSearch:
    @pytest.mark.asyncio
    async def test_search_converte_score_em_distancia_e_parseia_payload(
        self, backend, mock_client
    ):
        mock_client.collection_exists.return_value = True
        mock_client.query_points.return_value = QueryResponse(
            points=[
                ScoredPoint(
                    id="p1",
                    version=1,
                    score=0.9,
                    payload={"text": "conteúdo", "metadata": {"workspace_id": "w1"}},
                )
            ]
        )

        hits = await backend.search("articles", [0.1, 0.2], limit=5)

        assert len(hits) == 1
        assert hits[0].id == "p1"
        assert hits[0].score == pytest.approx(1.0 - 0.9)
        assert hits[0].content == "conteúdo"
        assert hits[0].metadata == {"workspace_id": "w1"}

    @pytest.mark.asyncio
    async def test_search_colecao_inexistente_retorna_vazio_sem_propagar(
        self, backend, mock_client
    ):
        mock_client.collection_exists.return_value = False

        hits = await backend.search("nao-existe", [0.1], limit=5)

        assert hits == []
        mock_client.query_points.assert_not_called()


class TestQdrantBackendUpsert:
    @pytest.mark.asyncio
    async def test_upsert_cria_colecao_e_envia_pontos(self, backend, mock_client):
        mock_client.collection_exists.return_value = False

        await backend.upsert(
            "articles",
            [VectorRow(id="p1", vector=[0.1, 0.2], text="a", metadata={"k": "v"})],
        )

        mock_client.create_collection.assert_awaited_once()
        mock_client.upsert.assert_awaited_once()
        _, kwargs = mock_client.upsert.call_args
        assert kwargs["collection_name"] == "articles"
        assert kwargs["points"][0].id == "p1"

    @pytest.mark.asyncio
    async def test_upsert_lista_vazia_nao_chama_cliente(self, backend, mock_client):
        await backend.upsert("articles", [])

        mock_client.create_collection.assert_not_called()
        mock_client.upsert.assert_not_called()


class TestQdrantBackendListRows:
    @pytest.mark.asyncio
    async def test_list_rows_pagina_via_scroll_ate_offset_none(
        self, backend, mock_client
    ):
        mock_client.collection_exists.return_value = True
        page1 = [
            Record(
                id="p1",
                payload={"text": "a", "metadata": {}},
                vector=[0.1, 0.2],
            )
        ]
        page2 = [
            Record(
                id="p2",
                payload={"text": "b", "metadata": {}},
                vector=[0.3, 0.4],
            )
        ]
        mock_client.scroll.side_effect = [(page1, "next-offset"), (page2, None)]

        rows = await backend.list_rows("articles")

        assert [r.id for r in rows] == ["p1", "p2"]
        assert mock_client.scroll.await_count == 2

    @pytest.mark.asyncio
    async def test_list_rows_colecao_inexistente_retorna_vazio(
        self, backend, mock_client
    ):
        mock_client.collection_exists.return_value = False

        rows = await backend.list_rows("nao-existe")

        assert rows == []
        mock_client.scroll.assert_not_called()


class TestQdrantBackendDelete:
    @pytest.mark.asyncio
    async def test_delete_envia_point_ids_list(self, backend, mock_client):
        count = await backend.delete("articles", ["p1", "p2"])

        assert count == 2
        _, kwargs = mock_client.delete.call_args
        assert kwargs["collection_name"] == "articles"
        assert kwargs["points_selector"].points == ["p1", "p2"]

    @pytest.mark.asyncio
    async def test_delete_lista_vazia_nao_chama_cliente(self, backend, mock_client):
        count = await backend.delete("articles", [])

        assert count == 0
        mock_client.delete.assert_not_called()


class TestQdrantBackendCollections:
    @pytest.mark.asyncio
    async def test_list_collections_extrai_nomes(self, backend, mock_client):
        mock_client.get_collections.return_value = CollectionsResponse(
            collections=[
                CollectionDescription(name="articles"),
                CollectionDescription(name="notes"),
            ]
        )

        names = await backend.list_collections()

        assert names == ["articles", "notes"]

    @pytest.mark.asyncio
    async def test_list_collections_erro_retorna_vazio_sem_propagar(
        self, backend, mock_client
    ):
        mock_client.get_collections.side_effect = RuntimeError("conexão recusada")

        names = await backend.list_collections()

        assert names == []


class TestQdrantBackendCount:
    @pytest.mark.asyncio
    async def test_count_retorna_valor_exato(self, backend, mock_client):
        mock_client.count.return_value = CountResult(count=42)

        result = await backend.count("articles")

        assert result == 42
        _, kwargs = mock_client.count.call_args
        assert kwargs["exact"] is True

    @pytest.mark.asyncio
    async def test_count_erro_retorna_none_sem_propagar(self, backend, mock_client):
        mock_client.count.side_effect = RuntimeError("timeout")

        result = await backend.count("articles")

        assert result is None


class TestQdrantBackendPurge:
    @pytest.mark.asyncio
    async def test_purge_apaga_colecao(self, backend, mock_client):
        await backend.purge("articles")

        mock_client.delete_collection.assert_awaited_once_with("articles")

    @pytest.mark.asyncio
    async def test_purge_idempotente_em_colecao_inexistente(self, backend, mock_client):
        mock_client.delete_collection.side_effect = RuntimeError("not found")

        await backend.purge("nao-existe")
