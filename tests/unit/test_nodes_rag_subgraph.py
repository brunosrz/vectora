"""Tests for src/nodes/rag_subgraph.py"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from src.nodes.rag_subgraph import (
    _best_score,
    _call_vector_search,
    _call_vector_search_all,
    _call_web_search,
    _extract_query,
    _rag_decide_node,
    _route_after_decide,
    rag_decide,
    rag_inject,
    rag_rerank,
    rag_retrieve,
    rag_websearch,
)
from src.state import Document, State

_SCORE_HIGH = 0.7
_SCORE_LOW = 0.4


def _state(**kw: Any) -> State:
    base: State = {
        "messages": [HumanMessage(content="como funciona o JWT?")],
        "session_metadata": {},
    }
    base.update(kw)  # ty: ignore[invalid-argument-type]
    return base


def _doc(score=0.8, content="doc") -> Document:
    return Document(
        page_content=content, metadata={"source": "test"}, relevance_score=score
    )


class TestExtractQuery:
    def test_extracts_last_human(self):
        s = _state(messages=[HumanMessage(content="a"), HumanMessage(content="b")])
        assert _extract_query(s) == "b"

    def test_empty_messages(self):
        assert _extract_query(_state(messages=[])) == ""

    def test_no_human_message(self):
        from langchain_core.messages import AIMessage

        assert _extract_query(_state(messages=[AIMessage(content="ai")])) == ""


class TestBestScore:
    def test_max_score(self):
        assert _best_score([_doc(0.3), _doc(0.9)]) == pytest.approx(0.9)

    def test_empty(self):
        assert _best_score([]) == 0.0

    def test_none_scores(self):
        assert _best_score([_doc(None), _doc(0.6)]) == pytest.approx(0.6)

    def test_all_none(self):
        assert _best_score([_doc(None)]) == 0.0


class TestRagDecide:
    def test_high_score_inject(self):
        assert rag_decide(_state(rag_docs=[_doc(_SCORE_HIGH)])) == "rag_inject"

    def test_medium_score_rerank(self):
        assert rag_decide(_state(rag_docs=[_doc(0.55)])) == "rag_rerank"

    def test_low_score_routes_to_search(self):
        # score baixo → delega para o search real (rag_pending=True)
        assert rag_decide(_state(rag_docs=[_doc(0.2)])) == "search"

    def test_empty_docs_routes_to_search(self):
        assert rag_decide(_state(rag_docs=[])) == "search"

    def test_exactly_high_threshold(self):
        assert rag_decide(_state(rag_docs=[_doc(_SCORE_HIGH)])) == "rag_inject"

    def test_exactly_low_threshold(self):
        assert rag_decide(_state(rag_docs=[_doc(_SCORE_LOW)])) == "rag_rerank"


class TestRagRetrieve:
    @pytest.mark.asyncio
    async def test_returns_docs(self):
        from langchain_core.runnables import RunnableConfig

        docs = [_doc(0.9, "c1"), _doc(0.7, "c2")]
        config: RunnableConfig = {"configurable": {}}
        with patch(
<<<<<<< HEAD
            "vectora.nodes.rag_subgraph._call_vector_search_all",
=======
            "src.nodes.rag_subgraph._call_vector_search_all",
>>>>>>> dev
            new_callable=AsyncMock,
        ) as m:
            m.return_value = docs
            result = await rag_retrieve(_state(), config=config)
        assert result["rag_query"] == "como funciona o JWT?"
        assert len(result["rag_docs"]) == 2

    @pytest.mark.asyncio
    async def test_empty_query_returns_early(self):
        from langchain_core.runnables import RunnableConfig

        config: RunnableConfig = {"configurable": {}}
        result = await rag_retrieve(_state(messages=[]), config=config)
        assert result["rag_docs"] == []
        assert result["rag_query"] == ""

    @pytest.mark.asyncio
    async def test_no_results(self):
<<<<<<< HEAD
        with patch(
            "vectora.nodes.rag_subgraph._call_vector_search_all",
            new_callable=AsyncMock,
        ) as m:
=======
        from langchain_core.runnables import RunnableConfig

        config: RunnableConfig = {"configurable": {}}
        with (
            patch(
                "src.nodes.rag_subgraph._call_vector_search_all",
                new_callable=AsyncMock,
            ) as m,
            patch("src.nodes.rag_subgraph.settings") as ms,
        ):
>>>>>>> dev
            m.return_value = []
            ms.rag_hyde_enabled = False  # isola teste do HyDE
            ms.rag_multi_query_enabled = False
            result = await rag_retrieve(_state(), config=config)
        assert result["rag_docs"] == []


class TestCallVectorSearchAll:
    @pytest.mark.asyncio
    async def test_merges_all_collections_and_tags_web(self):
<<<<<<< HEAD
        from vectora.config.settings import settings
=======
        from src.settings import settings
>>>>>>> dev

        curated = [_doc(0.9, "curated")]
        web = [Document(page_content="web", metadata={}, relevance_score=0.6)]

        async def fake(query, collection, limit):
            return curated if collection == settings.rag_collection_default else web

        with (
            patch(
<<<<<<< HEAD
                "vectora.nodes.rag_subgraph._list_collections",
                new_callable=AsyncMock,
            ) as mlist,
            patch("vectora.nodes.rag_subgraph._call_vector_search", side_effect=fake),
=======
                "src.nodes.rag_subgraph._list_collections",
                new_callable=AsyncMock,
            ) as mlist,
            patch("src.nodes.rag_subgraph._call_vector_search", side_effect=fake),
>>>>>>> dev
        ):
            mlist.return_value = [
                settings.rag_collection_default,
                settings.rag_collection_web,
            ]
            docs = await _call_vector_search_all("q")

        assert len(docs) == 2
        web_doc = next(d for d in docs if d["page_content"] == "web")
        # docs da coleção web são marcados com origin para ponderar confiança
        assert web_doc["metadata"]["origin"] == "web_search"

    @pytest.mark.asyncio
    async def test_one_collection_failing_does_not_break(self):
<<<<<<< HEAD
        from vectora.config.settings import settings
=======
        from src.settings import settings
>>>>>>> dev

        async def fake(query, collection, limit):
            if collection == settings.rag_collection_default:
                return [_doc(0.8, "curated")]
            raise RuntimeError("coleção indisponível")

        with (
            patch(
<<<<<<< HEAD
                "vectora.nodes.rag_subgraph._list_collections",
                new_callable=AsyncMock,
            ) as mlist,
            patch("vectora.nodes.rag_subgraph._call_vector_search", side_effect=fake),
=======
                "src.nodes.rag_subgraph._list_collections",
                new_callable=AsyncMock,
            ) as mlist,
            patch("src.nodes.rag_subgraph._call_vector_search", side_effect=fake),
>>>>>>> dev
        ):
            mlist.return_value = [
                settings.rag_collection_default,
                settings.rag_collection_web,
            ]
            docs = await _call_vector_search_all("q")
        assert len(docs) == 1

    @pytest.mark.asyncio
    async def test_searches_arbitrary_collections(self):
        """A6.3 — busca coleções fora de articles/web_cache (ex: 'docs', 'code')."""

        async def fake(query, collection, limit):
            return [_doc(0.7, f"from-{collection}")]

        with (
            patch(
<<<<<<< HEAD
                "vectora.nodes.rag_subgraph._list_collections",
                new_callable=AsyncMock,
            ) as mlist,
            patch("vectora.nodes.rag_subgraph._call_vector_search", side_effect=fake),
=======
                "src.nodes.rag_subgraph._list_collections",
                new_callable=AsyncMock,
            ) as mlist,
            patch("src.nodes.rag_subgraph._call_vector_search", side_effect=fake),
>>>>>>> dev
        ):
            mlist.return_value = ["docs", "code", "notes"]
            docs = await _call_vector_search_all("q")

        assert len(docs) == 3
        assert {d["page_content"] for d in docs} == {
            "from-docs",
            "from-code",
            "from-notes",
        }

    @pytest.mark.asyncio
    async def test_no_collections_returns_empty(self):
        with patch(
<<<<<<< HEAD
            "vectora.nodes.rag_subgraph._list_collections",
=======
            "src.nodes.rag_subgraph._list_collections",
>>>>>>> dev
            new_callable=AsyncMock,
        ) as mlist:
            mlist.return_value = []
            docs = await _call_vector_search_all("q")
        assert docs == []


class TestRagWebsearch:
    @pytest.mark.asyncio
    async def test_adds_curated_web_docs(self):
        web = [{"content": "web content", "url": "https://a.com", "title": "A"}]
        web_docs = [
            Document(
                page_content="web content",
                metadata={"url": "https://a.com"},
                relevance_score=None,
            )
        ]
        with patch(
            "src.nodes.rag_subgraph._call_web_search", new_callable=AsyncMock
        ) as m:
            with patch(
<<<<<<< HEAD
                "vectora.nodes.web_curation.curate_and_enqueue",
=======
                "src.nodes.web_curation.curate_and_enqueue",
>>>>>>> dev
                new_callable=AsyncMock,
            ) as mc:
                m.return_value = web
                mc.return_value = (web_docs, ["qid"])
                result = await rag_websearch(_state(rag_query="JWT", rag_docs=[]))
        assert result["web_search_triggered"] is True
        assert len(result["rag_docs"]) == 1
        assert "qid" in result["pending_embeds"]

    @pytest.mark.asyncio
    async def test_no_web_results(self):
        with patch(
            "src.nodes.rag_subgraph._call_web_search", new_callable=AsyncMock
        ) as m:
            m.return_value = []
            result = await rag_websearch(_state(rag_query="test", rag_docs=[]))
        assert result["web_search_triggered"] is True
        assert result.get("pending_embeds") == []

    @pytest.mark.asyncio
    async def test_combines_existing_docs(self):
        existing = [_doc(0.3, "existing")]
        web = [{"content": "web doc", "url": "https://a.com", "title": "A"}]
        web_docs = [Document(page_content="web doc", metadata={}, relevance_score=None)]
        with patch(
            "src.nodes.rag_subgraph._call_web_search", new_callable=AsyncMock
        ) as m:
            with patch(
<<<<<<< HEAD
                "vectora.nodes.web_curation.curate_and_enqueue",
=======
                "src.nodes.web_curation.curate_and_enqueue",
>>>>>>> dev
                new_callable=AsyncMock,
            ) as mc:
                m.return_value = web
                mc.return_value = (web_docs, [])
                result = await rag_websearch(
                    _state(rag_query="test", rag_docs=existing)
                )
        assert len(result["rag_docs"]) == 2

    @pytest.mark.asyncio
    async def test_curation_rejecting_all_persists_nothing(self):
        web = [{"content": "lixo", "url": "https://spam.com", "title": "Spam"}]
        web_docs = [Document(page_content="lixo", metadata={}, relevance_score=None)]
        with patch(
<<<<<<< HEAD
            "vectora.nodes.rag_subgraph._call_web_search", new_callable=AsyncMock
        ) as m:
            with patch(
                "vectora.nodes.web_curation.curate_and_enqueue",
=======
            "src.nodes.rag_subgraph._call_web_search", new_callable=AsyncMock
        ) as m:
            with patch(
                "src.nodes.web_curation.curate_and_enqueue",
>>>>>>> dev
                new_callable=AsyncMock,
            ) as mc:
                m.return_value = web
                mc.return_value = (web_docs, [])  # 0 persistidos
                result = await rag_websearch(_state(rag_query="test", rag_docs=[]))
        assert result["pending_embeds"] == []


class TestRagInject:
    @pytest.mark.asyncio
    async def test_injects_system_message(self):
        docs = [_doc(0.9, "conteúdo JWT")]
        result = await rag_inject(_state(rag_docs=docs, rag_query="JWT"))
        assert "messages" in result
        assert isinstance(result["messages"][0], SystemMessage)
        assert "JWT" in result["messages"][0].content
        assert "conteúdo JWT" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_web_origin_is_tagged(self):
        docs = [
            Document(
                page_content="conteúdo web",
                metadata={"source": "https://a.com", "origin": "web_search"},
                relevance_score=0.8,
            )
        ]
        result = await rag_inject(_state(rag_docs=docs, rag_query="q"))
        assert "web (cache)" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_no_docs_emits_rag_context_marker(self):
        """A6.2 — sem docs, rag_inject ainda emite o marcador rag_context.

        É o sinal determinístico que impede o orchestrator de re-rotear para
        o RAG (loop infinito → GraphRecursionError).
        """
        result = await rag_inject(_state(rag_docs=[], rag_query="JWT"))
        assert "messages" in result
        msg = result["messages"][0]
        assert isinstance(msg, SystemMessage)
        assert msg.name == "rag_context"
        assert "Nenhum documento" in msg.content

    @pytest.mark.asyncio
    async def test_truncates_to_5_docs(self):
        docs = [_doc(0.8, f"doc {i}") for i in range(10)]

        result = await rag_inject(_state(rag_docs=docs, rag_query="test"))
        assert "doc 4" in result["messages"][0].content
        assert "doc 5" not in result["messages"][0].content


class TestResultScore:
    """A6.4 — normalização de score (relevance_score do reranker vs _distance)."""

    def test_relevance_score_used_directly(self):
<<<<<<< HEAD
        from vectora.nodes.rag_subgraph import _result_score
=======
        from src.nodes.rag_subgraph import _result_score
>>>>>>> dev

        assert _result_score({"relevance_score": 0.83}) == pytest.approx(0.83)

    def test_distance_converted_to_similarity_monotonic(self):
<<<<<<< HEAD
        from vectora.nodes.rag_subgraph import _result_score
=======
        from src.nodes.rag_subgraph import _result_score
>>>>>>> dev

        # _distance 0 (match perfeito) → similaridade 1.0
        assert _result_score({"score": 0.0}) == pytest.approx(1.0)
        # monotônico: menor distância → maior similaridade
        near = _result_score({"score": 0.1})
        far = _result_score({"score": 2.0})
        assert near is not None
        assert far is not None
        assert near > far

    def test_relevance_score_takes_precedence(self):
<<<<<<< HEAD
        from vectora.nodes.rag_subgraph import _result_score
=======
        from src.nodes.rag_subgraph import _result_score
>>>>>>> dev

        # com ambos presentes, o relevance_score do reranker vence
        assert _result_score({"relevance_score": 0.9, "score": 0.1}) == pytest.approx(
            0.9
        )

    def test_no_score_returns_none(self):
<<<<<<< HEAD
        from vectora.nodes.rag_subgraph import _result_score
=======
        from src.nodes.rag_subgraph import _result_score
>>>>>>> dev

        assert _result_score({}) is None

    def test_invalid_score_returns_none(self):
<<<<<<< HEAD
        from vectora.nodes.rag_subgraph import _result_score
=======
        from src.nodes.rag_subgraph import _result_score
>>>>>>> dev

        assert _result_score({"score": "nan-string"}) is None


class TestCallVectorSearch:
    @pytest.mark.asyncio
    async def test_returns_empty_on_error_status(self):
        import json
        from unittest.mock import AsyncMock, patch

        mock_vs = AsyncMock(return_value=json.dumps({"status": "error"}))
        with patch("src.nodes.rag_subgraph.vector_search", create=True):
            with patch(
                "src.tools.rag.vector_search",
                new_callable=lambda: type("T", (), {"ainvoke": staticmethod(mock_vs)}),
            ):
                result = await _call_vector_search("test")
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_docs_on_success(self):
        import json
        from unittest.mock import AsyncMock, patch

        payload = json.dumps(
            {"results": [{"content": "hello", "metadata": {}, "score": 0.9}]}
        )
        mock_ainvoke = AsyncMock(return_value=payload)
        with patch("src.tools.rag.vector_search") as mock_vs:
            mock_vs.ainvoke = mock_ainvoke
            result = await _call_vector_search("hello world")
        assert len(result) == 1
        assert result[0]["page_content"] == "hello"

    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self):
        from unittest.mock import AsyncMock, patch

        with patch("src.tools.rag.vector_search") as mock_vs:
            mock_vs.ainvoke = AsyncMock(side_effect=Exception("boom"))
            result = await _call_vector_search("test")
        assert result == []


class TestCallWebSearch:
    @pytest.mark.asyncio
    async def test_returns_list_on_success(self):
        import json
        from unittest.mock import patch

        data = [{"content": "web result", "url": "https://x.com"}]
        with patch("src.tools.web.web_search") as mock_ws:
            mock_ws.invoke = lambda **_: json.dumps(data)
            result = await _call_web_search("query")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self):
        from unittest.mock import patch

        with patch("src.tools.web.web_search") as mock_ws:
            mock_ws.invoke = lambda **_: (_ for _ in ()).throw(Exception("fail"))
            result = await _call_web_search("query")
        assert result == []


class TestRagRerank:
    @pytest.mark.asyncio
    async def test_empty_docs_returns_empty(self):
        result = await rag_rerank(_state(rag_docs=[], rag_query="q"))
        assert result == {}

    @pytest.mark.asyncio
    async def test_no_api_key_returns_empty(self):
        from unittest.mock import patch

        docs = [_doc(0.7, "content")]
        with patch("src.nodes.rag_subgraph.settings") as ms:
            ms.get_cohere_api_key.return_value = None
            result = await rag_rerank(_state(rag_docs=docs, rag_query="test"))
        assert result == {}

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self):
        from unittest.mock import MagicMock, patch

        docs = [_doc(0.7, "content")]
        mock_reranker = MagicMock()
        mock_reranker.compress_documents.side_effect = Exception("Cohere error")
        with patch("src.nodes.rag_subgraph.settings") as ms:
            ms.get_cohere_api_key.return_value = "test-key"
            ms.reranker_model = "rerank-english-v2.0"
            with patch("langchain_cohere.CohereRerank", return_value=mock_reranker):
                result = await rag_rerank(_state(rag_docs=docs, rag_query="test"))
        assert result == {}


class TestRagDecideNode:
    @pytest.mark.asyncio
    async def test_low_score_sets_rag_pending(self):
        # score baixo → seta rag_pending=True para search_finalize rotear para rag_inject
        result = await _rag_decide_node(_state(rag_docs=[_doc(0.2)]))
        assert result == {"rag_pending": True}

    @pytest.mark.asyncio
    async def test_high_score_no_rag_pending(self):
        result = await _rag_decide_node(_state(rag_docs=[_doc(0.9)]))
        assert result == {}

    def test_route_after_decide_delegates_to_rag_decide(self):
        s = _state(rag_docs=[_doc(0.9)])
        assert _route_after_decide(s) == rag_decide(s)
