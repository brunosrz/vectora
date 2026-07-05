"""Fallback de embeddings Cohere↔Voyage por quota (Parte B).

Contrato:
- FallbackEmbeddings usa o primário; em quota error troca para o secundário e
  registra record_switch. Erro não-quota propaga sem troca.
- Cobre embed_query/embed_documents (sync) e aembed_query/aembed_documents (async).
- _build_lc_embeddings: ambos → FallbackEmbeddings; só um → esse; nenhum → None.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from langchain_core.embeddings import Embeddings

from backend.llm import provider_fallback as pf
from backend.llm.fallback_embeddings import FallbackEmbeddings


class _FakeEmb(Embeddings):
    def __init__(self, *, tag: float, error: Exception | None = None) -> None:
        self._tag = tag
        self._error = error

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._error is not None:
            raise self._error
        return [[self._tag] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        if self._error is not None:
            raise self._error
        return [self._tag]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._error is not None:
            raise self._error
        return [[self._tag] for _ in texts]

    async def aembed_query(self, text: str) -> list[float]:
        if self._error is not None:
            raise self._error
        return [self._tag]


def _wrap(primary: Embeddings, secondary: Embeddings) -> FallbackEmbeddings:
    return FallbackEmbeddings(
        primary,
        secondary,
        primary_id="cohere:embed-v4",
        secondary_id="voyage:voyage-3",
    )


class TestFallbackEmbeddingsSync:
    def test_query_primary_ok_no_switch(self):
        pf.drain_switches()
        emb = _wrap(_FakeEmb(tag=1.0), _FakeEmb(tag=2.0))
        assert emb.embed_query("x") == [1.0]
        assert pf.drain_switches() == []

    def test_query_primary_quota_switches(self):
        pf.drain_switches()
        emb = _wrap(_FakeEmb(tag=1.0, error=Exception("429 quota")), _FakeEmb(tag=2.0))
        assert emb.embed_query("x") == [2.0]
        assert pf.drain_switches() == [
            {"from": "cohere:embed-v4", "to": "voyage:voyage-3"}
        ]

    def test_query_non_quota_reraises(self):
        emb = _wrap(_FakeEmb(tag=1.0, error=ValueError("boom")), _FakeEmb(tag=2.0))
        with pytest.raises(ValueError):
            emb.embed_query("x")

    def test_documents_quota_switches(self):
        emb = _wrap(_FakeEmb(tag=1.0, error=Exception("rate limit")), _FakeEmb(tag=2.0))
        assert emb.embed_documents(["a", "b"]) == [[2.0], [2.0]]

    def test_documents_both_fail_propagates(self):
        emb = _wrap(
            _FakeEmb(tag=1.0, error=Exception("429")),
            _FakeEmb(tag=2.0, error=Exception("boom secundário")),
        )
        with pytest.raises(Exception, match="secund"):
            emb.embed_documents(["a"])


class TestFallbackEmbeddingsAsync:
    async def test_aquery_primary_ok(self):
        pf.drain_switches()
        emb = _wrap(_FakeEmb(tag=1.0), _FakeEmb(tag=2.0))
        assert await emb.aembed_query("x") == [1.0]
        assert pf.drain_switches() == []

    async def test_aquery_quota_switches(self):
        pf.drain_switches()
        emb = _wrap(_FakeEmb(tag=1.0, error=Exception("429 quota")), _FakeEmb(tag=2.0))
        assert await emb.aembed_query("x") == [2.0]
        assert pf.drain_switches() == [
            {"from": "cohere:embed-v4", "to": "voyage:voyage-3"}
        ]

    async def test_adocuments_quota_switches(self):
        emb = _wrap(
            _FakeEmb(tag=1.0, error=Exception("RESOURCE_EXHAUSTED")), _FakeEmb(tag=2.0)
        )
        assert await emb.aembed_documents(["a"]) == [[2.0]]

    async def test_aquery_non_quota_reraises(self):
        emb = _wrap(_FakeEmb(tag=1.0, error=ValueError("boom")), _FakeEmb(tag=2.0))
        with pytest.raises(ValueError):
            await emb.aembed_query("x")


class TestBuildLcEmbeddings:
    def test_both_configured_returns_fallback(self):
        from backend.storage import factory

        with (
            patch.object(
                factory, "_build_cohere_embeddings", lambda: _FakeEmb(tag=1.0)
            ),
            patch.object(
                factory, "_build_voyage_embeddings", lambda: _FakeEmb(tag=2.0)
            ),
        ):
            emb = factory._build_lc_embeddings()
        assert isinstance(emb, FallbackEmbeddings)

    def test_only_cohere_returns_cohere(self):
        from backend.storage import factory

        cohere = _FakeEmb(tag=1.0)
        with (
            patch.object(factory, "_build_cohere_embeddings", lambda: cohere),
            patch.object(factory, "_build_voyage_embeddings", lambda: None),
        ):
            assert factory._build_lc_embeddings() is cohere

    def test_only_voyage_returns_voyage(self):
        from backend.storage import factory

        voyage = _FakeEmb(tag=2.0)
        with (
            patch.object(factory, "_build_cohere_embeddings", lambda: None),
            patch.object(factory, "_build_voyage_embeddings", lambda: voyage),
        ):
            assert factory._build_lc_embeddings() is voyage

    def test_none_configured_returns_none(self):
        from backend.storage import factory

        with (
            patch.object(factory, "_build_cohere_embeddings", lambda: None),
            patch.object(factory, "_build_voyage_embeddings", lambda: None),
        ):
            assert factory._build_lc_embeddings() is None
