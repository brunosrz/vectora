"""Tests para C1/C2/C3 — Hybrid RAG, Multi-query e HyDE."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from vectora.nodes.rag_subgraph import (
    _bm25_search,
    _deduplicate_docs,
    _generate_query_variants,
    _rrf_merge,
    _tokenize,
    rag_expand_query,
)
from vectora.state import Document, State

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doc(
    content: str = "doc", source: str = "src", score: float | None = 0.8
) -> Document:
    return Document(
        page_content=content, metadata={"source": source}, relevance_score=score
    )


def _state(**kw) -> State:
    base: State = {
        "messages": [HumanMessage(content="como funciona o JWT?")],
        "session_metadata": {},
    }
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# C1 — _tokenize
# ---------------------------------------------------------------------------


class TestTokenize:
    def test_lowercase(self):
        assert _tokenize("Hello World") == ["hello", "world"]

    def test_removes_punctuation(self):
        assert _tokenize("JWT, auth.") == ["jwt", "auth"]

    def test_code_tokens(self):
        tokens = _tokenize("def my_function(x):")
        assert "def" in tokens
        assert "my_function" in tokens

    def test_empty(self):
        assert _tokenize("") == []

    def test_multilingual(self):
        tokens = _tokenize("autenticação via JWT")
        assert "autenticação" in tokens
        assert "jwt" in tokens


# ---------------------------------------------------------------------------
# C1 — _bm25_search
# ---------------------------------------------------------------------------


class TestBm25Search:
    def test_returns_top_n(self):
        docs = [_doc(f"doc about jwt token {i}", f"src{i}") for i in range(10)]
        result = _bm25_search("jwt token", docs, n_results=3)
        assert len(result) == 3

    def test_ranks_by_relevance(self):
        docs = [
            _doc("jwt authentication bearer token", "jwt_doc"),
            _doc("python programming language basics", "python_doc"),
            _doc("jwt bearer token validation", "jwt2_doc"),
        ]
        result = _bm25_search("jwt bearer", docs, n_results=3)
        sources = [d.get("metadata", {}).get("source") for d in result]
        # Docs com jwt/bearer devem rankear acima do python_doc
        assert sources.index("python_doc") > sources.index("jwt_doc")

    def test_empty_docs_returns_empty(self):
        assert _bm25_search("query", [], n_results=5) == []

    def test_single_doc_returns_it(self):
        docs = [_doc("único documento")]
        result = _bm25_search("único", docs)
        assert len(result) == 1

    def test_graceful_degradation_without_rank_bm25(self):
        """Sem rank-bm25, retorna os primeiros n_results."""
        docs = [_doc(f"doc{i}", f"s{i}") for i in range(10)]
        with patch.dict("sys.modules", {"rank_bm25": None}):
            result = _bm25_search("query", docs, n_results=3)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# C1 — _rrf_merge
# ---------------------------------------------------------------------------


class TestRrfMerge:
    def test_deduplicates_same_doc(self):
        doc = _doc("jwt doc", "src_jwt")
        result = _rrf_merge([doc], [doc], n_results=5)
        # Mesmo doc em ambas as listas → deve aparecer apenas uma vez
        assert len(result) == 1

    def test_promotes_doc_in_both_lists(self):
        shared = _doc("shared jwt content", "shared")
        dense_only = _doc("only in dense", "dense")
        sparse_only = _doc("only in sparse", "sparse")

        result = _rrf_merge([shared, dense_only], [sparse_only, shared], n_results=3)
        sources = [d.get("metadata", {}).get("source") for d in result]
        # shared está em ambas as listas → deve ter maior score → primeiro lugar
        assert sources[0] == "shared"

    def test_respects_n_results(self):
        docs_a = [_doc(f"dense{i}", f"d{i}") for i in range(5)]
        docs_b = [_doc(f"sparse{i}", f"s{i}") for i in range(5)]
        result = _rrf_merge(docs_a, docs_b, n_results=4)
        assert len(result) == 4

    def test_empty_lists(self):
        assert _rrf_merge([], [], n_results=5) == []

    def test_one_empty_list(self):
        docs = [_doc("doc", "src")]
        result = _rrf_merge(docs, [], n_results=5)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# C1 — _call_vector_search_all com hybrid
# ---------------------------------------------------------------------------


class TestCallVectorSearchAllHybrid:
    @pytest.mark.asyncio
    async def test_hybrid_enabled_applies_rrf(self):
        """Com hybrid enabled, _call_vector_search_all aplica BM25+RRF."""
        from unittest.mock import patch

        from vectora.nodes.rag_subgraph import _call_vector_search_all

        docs = [
            _doc("jwt authentication bearer", "jwt"),
            _doc("python basics", "python"),
            _doc("oauth2 flow jwt", "oauth"),
        ]

        async def fake_search(query, collection, limit):
            return docs[:]

        with (
            patch(
                "vectora.nodes.rag_subgraph._list_collections",
                new_callable=AsyncMock,
                return_value=["articles"],
            ),
            patch(
                "vectora.nodes.rag_subgraph._call_vector_search",
                side_effect=fake_search,
            ),
            patch("vectora.nodes.rag_subgraph.settings") as ms,
        ):
            ms.rag_hybrid_enabled = True
            ms.rag_hybrid_fetch_limit = 20
            ms.rag_collection_web = "web_cache"
            result = await _call_vector_search_all("jwt bearer", limit=3)

        assert len(result) <= 3

    @pytest.mark.asyncio
    async def test_hybrid_disabled_skips_bm25(self):
        """Com hybrid disabled, retorna apenas os primeiros N sem BM25."""
        from unittest.mock import patch

        from vectora.nodes.rag_subgraph import _call_vector_search_all

        docs = [_doc(f"doc{i}", f"s{i}") for i in range(5)]

        async def fake_search(query, collection, limit):
            return docs[:limit]

        with (
            patch(
                "vectora.nodes.rag_subgraph._list_collections",
                new_callable=AsyncMock,
                return_value=["articles"],
            ),
            patch(
                "vectora.nodes.rag_subgraph._call_vector_search",
                side_effect=fake_search,
            ),
            patch("vectora.nodes.rag_subgraph.settings") as ms,
        ):
            ms.rag_hybrid_enabled = False
            ms.rag_hybrid_fetch_limit = 20
            ms.rag_collection_web = "web_cache"
            result = await _call_vector_search_all("query", limit=3)

        assert len(result) == 3


# ---------------------------------------------------------------------------
# C1 — _deduplicate_docs
# ---------------------------------------------------------------------------


class TestDeduplicateDocs:
    def test_removes_duplicates(self):
        doc = _doc("same content", "same_src")
        result = _deduplicate_docs([doc, doc, doc])
        assert len(result) == 1

    def test_preserves_unique(self):
        docs = [_doc(f"content {i}", f"src_{i}") for i in range(5)]
        result = _deduplicate_docs(docs)
        assert len(result) == 5

    def test_empty(self):
        assert _deduplicate_docs([]) == []


# ---------------------------------------------------------------------------
# C2 — _generate_query_variants
# ---------------------------------------------------------------------------


class TestGenerateQueryVariants:
    @pytest.mark.asyncio
    async def test_includes_original(self):
        """Variantes sempre incluem a query original."""
        mock_response = AsyncMock()
        mock_response.content = "variante 1\nvariante 2"
        with patch(
            "vectora.services.utils.load_llm",
            return_value=AsyncMock(ainvoke=AsyncMock(return_value=mock_response)),
        ):
            variants = await _generate_query_variants("query original", n=3)
        assert "query original" in variants

    @pytest.mark.asyncio
    async def test_returns_original_on_failure(self):
        """Em caso de falha do LLM, retorna só a query original."""
        with patch(
            "vectora.services.utils.load_llm",
            side_effect=Exception("LLM error"),
        ):
            variants = await _generate_query_variants("query test")
        assert variants == ["query test"]

    @pytest.mark.asyncio
    async def test_respects_n_limit(self):
        """Retorna no máximo n variantes."""
        mock_response = AsyncMock()
        mock_response.content = "\n".join([f"variante {i}" for i in range(10)])
        with patch(
            "vectora.services.utils.load_llm",
            return_value=AsyncMock(ainvoke=AsyncMock(return_value=mock_response)),
        ):
            variants = await _generate_query_variants("query", n=3)
        assert len(variants) <= 3


# ---------------------------------------------------------------------------
# C2 — rag_expand_query
# ---------------------------------------------------------------------------


class TestRagExpandQuery:
    @pytest.mark.asyncio
    async def test_disabled_returns_empty(self):
        with patch("vectora.nodes.rag_subgraph.settings") as ms:
            ms.rag_multi_query_enabled = False
            result = await rag_expand_query(_state())
        assert result == {}

    @pytest.mark.asyncio
    async def test_no_query_returns_empty(self):
        with patch("vectora.nodes.rag_subgraph.settings") as ms:
            ms.rag_multi_query_enabled = True
            result = await rag_expand_query(_state(messages=[]))
        assert result == {}

    @pytest.mark.asyncio
    async def test_single_variant_returns_empty(self):
        """Se só gerou a original, não há ganho → retorna {}."""
        with (
            patch("vectora.nodes.rag_subgraph.settings") as ms,
            patch(
                "vectora.nodes.rag_subgraph._generate_query_variants",
                new_callable=AsyncMock,
                return_value=["query original"],  # só 1 variant
            ),
        ):
            ms.rag_multi_query_enabled = True
            ms.rag_multi_query_n = 3
            result = await rag_expand_query(_state())
        assert result == {}

    @pytest.mark.asyncio
    async def test_multiple_variants_sets_state(self):
        """Com N variantes, seta rag_query_variants no state."""
        variants = ["query original", "reformulação 1", "reformulação 2"]
        with (
            patch("vectora.nodes.rag_subgraph.settings") as ms,
            patch(
                "vectora.nodes.rag_subgraph._generate_query_variants",
                new_callable=AsyncMock,
                return_value=variants,
            ),
        ):
            ms.rag_multi_query_enabled = True
            ms.rag_multi_query_n = 3
            result = await rag_expand_query(_state())
        assert result.get("rag_query_variants") == variants


# ---------------------------------------------------------------------------
# C3 — rag_retrieve com HyDE (integração)
# ---------------------------------------------------------------------------


class TestRagRetrieveHyDE:
    @pytest.mark.asyncio
    async def test_hyde_triggered_when_score_low(self):
        """HyDE é chamado quando score inicial < rag_hyde_threshold."""
        low_score_docs = [_doc("doc baixo", "s1", score=0.3)]
        hyde_docs = [_doc("hyde resultado", "hyde", score=0.85)]

        from langchain_core.runnables import RunnableConfig

        from vectora.nodes.rag_subgraph import rag_retrieve

        config: RunnableConfig = {"configurable": {}}

        with (
            patch(
                "vectora.nodes.rag_subgraph._call_vector_search_all",
                new_callable=AsyncMock,
                return_value=low_score_docs,
            ),
            patch(
                "vectora.nodes.rag_subgraph._hyde_search",
                new_callable=AsyncMock,
                return_value=hyde_docs,
            ) as mock_hyde,
            patch("vectora.nodes.rag_subgraph.settings") as ms,
        ):
            ms.rag_hyde_enabled = True
            ms.rag_hyde_threshold = 0.5
            ms.rag_multi_query_enabled = False
            result = await rag_retrieve(_state(), config=config)

        mock_hyde.assert_called_once()
        # Deve conter tanto os docs originais quanto os do HyDE
        assert len(result["rag_docs"]) >= 1

    @pytest.mark.asyncio
    async def test_hyde_not_triggered_when_score_high(self):
        """HyDE NÃO é chamado quando score inicial >= rag_hyde_threshold."""
        high_score_docs = [_doc("doc bom", "s1", score=0.8)]

        from langchain_core.runnables import RunnableConfig

        from vectora.nodes.rag_subgraph import rag_retrieve

        config: RunnableConfig = {"configurable": {}}

        with (
            patch(
                "vectora.nodes.rag_subgraph._call_vector_search_all",
                new_callable=AsyncMock,
                return_value=high_score_docs,
            ),
            patch(
                "vectora.nodes.rag_subgraph._hyde_search",
                new_callable=AsyncMock,
            ) as mock_hyde,
            patch("vectora.nodes.rag_subgraph.settings") as ms,
        ):
            ms.rag_hyde_enabled = True
            ms.rag_hyde_threshold = 0.5
            ms.rag_multi_query_enabled = False
            await rag_retrieve(_state(), config=config)

        mock_hyde.assert_not_called()

    @pytest.mark.asyncio
    async def test_hyde_disabled_skips(self):
        """HyDE não é chamado quando rag_hyde_enabled=False."""
        low_score_docs = [_doc("doc", "s1", score=0.1)]

        from langchain_core.runnables import RunnableConfig

        from vectora.nodes.rag_subgraph import rag_retrieve

        config: RunnableConfig = {"configurable": {}}

        with (
            patch(
                "vectora.nodes.rag_subgraph._call_vector_search_all",
                new_callable=AsyncMock,
                return_value=low_score_docs,
            ),
            patch(
                "vectora.nodes.rag_subgraph._hyde_search",
                new_callable=AsyncMock,
            ) as mock_hyde,
            patch("vectora.nodes.rag_subgraph.settings") as ms,
        ):
            ms.rag_hyde_enabled = False
            ms.rag_hyde_threshold = 0.5
            ms.rag_multi_query_enabled = False
            await rag_retrieve(_state(), config=config)

        mock_hyde.assert_not_called()
