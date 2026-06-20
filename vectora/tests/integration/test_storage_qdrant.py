"""Testes de integração — Qdrant (conectividade, coleções, busca vetorial).

Requer Qdrant rodando (vectora-qdrant via docker).
Os fixtures de conftest.py sobem o container automaticamente se Docker estiver
disponível; do contrário, todos os testes são pulados.
"""

from __future__ import annotations

import pytest


class TestQdrantConnectivity:
    """Conectividade básica ao Qdrant."""

    @pytest.mark.storage
    def test_health_endpoint(self, qdrant_client):
        """Qdrant responde ao health check (list_collections bem-sucedido)."""
        result = qdrant_client.get_collections()
        assert hasattr(result, "collections")

    @pytest.mark.storage
    def test_list_collections(self, qdrant_client):
        """list_collections() retorna lista (pode estar vazia)."""
        collections = qdrant_client.get_collections()
        assert hasattr(collections, "collections")

    @pytest.mark.storage
    def test_create_and_delete_collection(self, qdrant_client):
        """Cria e deleta coleção de teste."""
        from qdrant_client.models import Distance, VectorParams

        name = "_test_vectora_integration"
        try:
            qdrant_client.delete_collection(name)
        except Exception:
            pass

        qdrant_client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=4, distance=Distance.COSINE),
        )

        collections = [c.name for c in qdrant_client.get_collections().collections]
        assert name in collections

        qdrant_client.delete_collection(name)
        collections_after = [
            c.name for c in qdrant_client.get_collections().collections
        ]
        assert name not in collections_after

    @pytest.mark.storage
    def test_upsert_and_search(self, qdrant_client):
        """Insere vetores e recupera por busca de similaridade."""
        from qdrant_client.models import Distance, PointStruct, VectorParams

        name = "_test_vectora_search"
        try:
            qdrant_client.delete_collection(name)
        except Exception:
            pass

        qdrant_client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=4, distance=Distance.COSINE),
        )

        qdrant_client.upsert(
            collection_name=name,
            points=[
                PointStruct(id=1, vector=[1.0, 0.0, 0.0, 0.0], payload={"text": "a"}),
                PointStruct(id=2, vector=[0.0, 1.0, 0.0, 0.0], payload={"text": "b"}),
                PointStruct(id=3, vector=[0.0, 0.0, 1.0, 0.0], payload={"text": "c"}),
            ],
        )

        results = qdrant_client.search(
            collection_name=name,
            query_vector=[1.0, 0.0, 0.0, 0.0],
            limit=1,
        )
        assert len(results) == 1
        assert results[0].id == 1

        qdrant_client.delete_collection(name)

    @pytest.mark.storage
    def test_search_error_wrong_dimension(self, qdrant_client):
        """Erro: busca com vetor de dimensão errada levanta exceção."""
        from qdrant_client.models import Distance, VectorParams

        name = "_test_dim_error"
        try:
            qdrant_client.delete_collection(name)
        except Exception:
            pass

        qdrant_client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=4, distance=Distance.COSINE),
        )

        with pytest.raises(Exception):
            qdrant_client.search(
                collection_name=name,
                query_vector=[1.0, 0.0],  # dimensão errada (2 em vez de 4)
                limit=1,
            )

        qdrant_client.delete_collection(name)
