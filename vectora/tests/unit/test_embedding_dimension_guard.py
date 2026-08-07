"""Guard de dimensão de embedding (backend/storage/factory.py).

Contrato:
- Primeira checagem pra uma coleção: persiste a dimensão passada,
  não levanta erro.
- Checagem seguinte com a MESMA dimensão: não levanta erro.
- Checagem seguinte com dimensão DIFERENTE: EmbeddingDimensionMismatchError,
  com mensagem citando as duas dimensões e orientando reindexação.
"""

from __future__ import annotations

import pytest

from backend.storage import factory


async def _cleanup(collection: str) -> None:
    db = await factory._embedding_meta_db()
    await factory._ensure_embedding_meta_table(db)
    await db.execute(
        "DELETE FROM embedding_index_meta WHERE collection = ?", (collection,)
    )
    await db.commit()


class TestCheckEmbeddingDimension:
    async def test_first_time_persists_dimension_without_raising(self):
        collection = "test-dim-guard-first-time"
        await _cleanup(collection)
        try:
            await factory._check_embedding_dimension(
                collection, 1024, provider="cohere"
            )
        finally:
            await _cleanup(collection)

    async def test_same_dimension_does_not_raise(self):
        collection = "test-dim-guard-same"
        await _cleanup(collection)
        try:
            await factory._check_embedding_dimension(collection, 768, provider="cohere")
            await factory._check_embedding_dimension(collection, 768, provider="cohere")
        finally:
            await _cleanup(collection)

    async def test_different_dimension_raises_with_clear_message(self):
        collection = "test-dim-guard-mismatch"
        await _cleanup(collection)
        try:
            await factory._check_embedding_dimension(
                collection, 1024, provider="cohere"
            )
            with pytest.raises(factory.EmbeddingDimensionMismatchError) as exc_info:
                await factory._check_embedding_dimension(
                    collection, 768, provider="cohere"
                )
            msg = str(exc_info.value)
            assert "1024" in msg
            assert "768" in msg
            assert "reindex" in msg.lower()
        finally:
            await _cleanup(collection)

    async def test_different_collections_are_independent(self):
        collection_a = "test-dim-guard-independent-a"
        collection_b = "test-dim-guard-independent-b"
        await _cleanup(collection_a)
        await _cleanup(collection_b)
        try:
            await factory._check_embedding_dimension(
                collection_a, 1024, provider="cohere"
            )
            # Coleção diferente, dimensão diferente — não deve ver o registro de A.
            await factory._check_embedding_dimension(
                collection_b, 768, provider="cohere"
            )
        finally:
            await _cleanup(collection_a)
            await _cleanup(collection_b)
