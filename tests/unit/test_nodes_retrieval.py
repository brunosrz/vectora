"""Tests for vectora/nodes/retrieval.py"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from vectora.nodes.retrieval import _rerank, retrieval_node
from vectora.state import Document, State


def _state(query="test query") -> State:
    return {
        "messages": [HumanMessage(content=query)],
        "session_metadata": {},
    }


class TestRetrievalNode:
    @pytest.mark.asyncio
    async def test_rag_disabled_returns_empty(self):
        # settings importado localmente em retrieval_node → patch no módulo de origem
        with patch("vectora.config.settings.settings") as mock_settings:
            mock_settings.enable_rag = False
            # re-importa dentro do contexto do patch não funciona facilmente;
            # melhor testar via resultado com settings real desabilitado
            from vectora.config.settings import settings as real_settings

            original = real_settings.enable_rag
            try:
                real_settings.enable_rag = False  # type: ignore[misc]
                result = await retrieval_node(_state())
            finally:
                real_settings.enable_rag = original  # type: ignore[misc]
        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self):
        state: State = {"messages": [], "session_metadata": {}}
        result = await retrieval_node(state)
        # sem mensagem humana → sem query → retorna {}
        assert result == {}

    @pytest.mark.asyncio
    async def test_no_results_returns_empty(self):
        with patch(
            "vectora.nodes.rag_subgraph._call_vector_search", new_callable=AsyncMock
        ) as mock_vs:
            mock_vs.return_value = []
            result = await retrieval_node(_state())
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_rag_docs_on_success(self):
        docs = [
            Document(page_content="doc1", metadata={}, relevance_score=0.9),
            Document(page_content="doc2", metadata={}, relevance_score=0.7),
        ]
        with patch(
            "vectora.nodes.rag_subgraph._call_vector_search", new_callable=AsyncMock
        ) as mock_vs:
            with patch(
                "vectora.nodes.retrieval._rerank", new_callable=AsyncMock
            ) as mock_rerank:
                mock_vs.return_value = docs
                mock_rerank.return_value = docs
                result = await retrieval_node(_state("JWT token"))

        assert "rag_docs" in result
        assert result["rag_query"] == "JWT token"
        assert len(result["rag_docs"]) == 2


class TestRerank:
    def _docs(self, n: int = 2) -> list[Document]:
        return [
            Document(page_content=f"doc {i}", metadata={}, relevance_score=0.5)
            for i in range(n)
        ]

    @pytest.mark.asyncio
    async def test_no_api_key_returns_docs_unchanged(self):
        docs = self._docs(2)
        with patch("vectora.config.settings.settings") as mock_settings:
            mock_settings.get_cohere_api_key.return_value = None
            result = await _rerank(docs, "query")
        assert result is docs

    @pytest.mark.asyncio
    async def test_exception_returns_docs_unchanged(self):
        docs = self._docs(2)
        with patch("langchain_cohere.CohereRerank", side_effect=Exception("API err")):
            result = await _rerank(docs, "query")
        # Exception in the try block → fallback to original docs
        assert result is docs

    @pytest.mark.asyncio
    async def test_rerank_success_returns_reranked(self):
        from langchain_core.documents import Document as LCDoc

        docs = self._docs(3)
        reranked_lc = [
            LCDoc(page_content="doc 2", metadata={}),
            LCDoc(page_content="doc 0", metadata={}),
        ]

        mock_reranker = MagicMock()
        mock_reranker.compress_documents.return_value = reranked_lc

        from vectora.config.settings import settings as real_settings

        original_key = real_settings.cohere_api_key
        try:
            real_settings.cohere_api_key = "test-key-123"  # type: ignore[misc]
            with patch("langchain_cohere.CohereRerank", return_value=mock_reranker):
                result = await _rerank(docs, "test query")
        finally:
            real_settings.cohere_api_key = original_key  # type: ignore[misc]

        assert len(result) == 2
        assert result[0]["page_content"] == "doc 2"

    @pytest.mark.asyncio
    async def test_compress_documents_failure_fallback(self):
        docs = self._docs(2)

        mock_reranker = MagicMock()
        mock_reranker.compress_documents.side_effect = Exception("Cohere API error")

        from vectora.config.settings import settings as real_settings

        original_key = real_settings.cohere_api_key
        try:
            real_settings.cohere_api_key = "test-key-123"  # type: ignore[misc]
            with patch("langchain_cohere.CohereRerank", return_value=mock_reranker):
                result = await _rerank(docs, "query")
        finally:
            real_settings.cohere_api_key = original_key  # type: ignore[misc]

        assert result is docs
