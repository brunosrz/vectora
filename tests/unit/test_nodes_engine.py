"""Tests for vectora/nodes/engine.py"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from vectora.nodes.engine import (
    _extract_tavily_results,
    _process_tavily_results,
    process_retrieval,
)
from vectora.state import State


class TestExtractTavilyResults:
    def test_dict_with_results_key(self):
        data = {"results": [{"content": "a"}, {"content": "b"}]}
        assert _extract_tavily_results(data, "web_search") == data["results"]

    def test_list_input(self):
        data = [{"content": "x"}]
        assert _extract_tavily_results(data, "web_search") == data

    def test_empty_dict_returns_empty_list(self):
        result = _extract_tavily_results({}, "web_search")
        assert result == []

    def test_invalid_type_returns_none(self):
        result = _extract_tavily_results("invalid", "web_search")  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        assert result is None


class TestProcessTavilyResults:
    @pytest.mark.asyncio
    async def test_formats_and_enqueues(self):
        results = [{"content": "doc content", "title": "Title", "url": "https://a.com"}]
        mock_embedding = AsyncMock()
        mock_embedding.ainvoke.return_value = json.dumps({"queue_id": "qid-1"})

        docs, queue_ids = await _process_tavily_results(
            results, "web_search", mock_embedding
        )

        assert len(docs) == 1
        assert docs[0]["page_content"] == "doc content"
        assert docs[0]["metadata"]["url"] == "https://a.com"
        assert "qid-1" in queue_ids

    @pytest.mark.asyncio
    async def test_skips_empty_content(self):
        results = [{"content": "", "title": "Empty", "url": "https://a.com"}]
        mock_embedding = AsyncMock()

        docs, queue_ids = await _process_tavily_results(
            results, "web_search", mock_embedding
        )

        assert docs == []
        assert queue_ids == []
        mock_embedding.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_embedding_failure_skips_queue_id(self):
        results = [{"content": "valid content", "title": "T", "url": "https://b.com"}]
        mock_embedding = AsyncMock()
        mock_embedding.ainvoke.side_effect = Exception("API error")

        docs, queue_ids = await _process_tavily_results(
            results, "web_search", mock_embedding
        )

        assert len(docs) == 1  # doc ainda formatado
        assert queue_ids == []  # mas sem queue_id

    @pytest.mark.asyncio
    async def test_multiple_results(self):
        results = [
            {"content": "doc 1", "title": "A", "url": "https://a.com"},
            {"content": "doc 2", "title": "B", "url": "https://b.com"},
        ]
        mock_embedding = AsyncMock()
        mock_embedding.ainvoke.return_value = json.dumps({"queue_id": "q1"})

        docs, queue_ids = await _process_tavily_results(
            results, "web_search", mock_embedding
        )

        assert len(docs) == 2
        assert len(queue_ids) == 2


class TestProcessRetrieval:
    def _runtime(self):
        return MagicMock()

    def _tool_msg(self, content: str, name: str = "web_search") -> ToolMessage:
        return ToolMessage(content=content, tool_call_id="t1", name=name)

    @pytest.mark.asyncio
    async def test_empty_messages_returns_empty(self):
        state: State = {"messages": [], "session_metadata": {}}
        result = await process_retrieval(state, self._runtime())
        assert result == {}

    @pytest.mark.asyncio
    async def test_no_tool_messages_returns_empty(self):
        state: State = {
            "messages": [HumanMessage(content="hi"), AIMessage(content="hello")],
            "session_metadata": {},
        }
        result = await process_retrieval(state, self._runtime())
        assert result == {}

    @pytest.mark.asyncio
    async def test_tool_message_wrong_name_skipped(self):
        state: State = {
            "messages": [self._tool_msg('{"results": []}', name="terminal")],
            "session_metadata": {},
        }
        result = await process_retrieval(state, self._runtime())
        assert result == {}

    @pytest.mark.asyncio
    async def test_invalid_json_skipped(self):
        state: State = {
            "messages": [self._tool_msg("not valid json", name="web_search")],
            "session_metadata": {},
        }
        result = await process_retrieval(state, self._runtime())
        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty(self):
        state: State = {
            "messages": [self._tool_msg('{"results": []}', name="web_search")],
            "session_metadata": {},
        }
        result = await process_retrieval(state, self._runtime())
        assert result == {}

    @pytest.mark.asyncio
    async def test_valid_web_search_populates_state(self):
        content = json.dumps(
            [{"content": "article content", "title": "Art", "url": "https://a.com"}]
        )
        state: State = {
            "messages": [self._tool_msg(content, name="web_search")],
            "session_metadata": {},
        }

        mock_resp = json.dumps({"queue_id": "q-abc"})
        with patch("vectora.nodes.engine.embedding") as mock_emb:
            mock_emb.ainvoke = AsyncMock(return_value=mock_resp)
            result = await process_retrieval(state, self._runtime())

        assert "retrieval_results" in result
        assert result.get("web_search_triggered") is True
        assert len(result["retrieval_results"]["web_search"]) == 1

    @pytest.mark.asyncio
    async def test_fetch_url_also_detected(self):
        content = json.dumps(
            [{"content": "fetched page", "title": "Page", "url": "https://b.com"}]
        )
        state: State = {
            "messages": [self._tool_msg(content, name="fetch_url")],
            "session_metadata": {},
        }

        with patch("vectora.nodes.engine.embedding") as mock_emb:
            mock_emb.ainvoke = AsyncMock(return_value=json.dumps({"queue_id": "q2"}))
            result = await process_retrieval(state, self._runtime())

        assert "retrieval_results" in result
        assert "fetch_url" in result["retrieval_results"]

    @pytest.mark.asyncio
    async def test_accumulates_existing_pending_embeds(self):
        content = json.dumps(
            [{"content": "new doc", "title": "T", "url": "https://c.com"}]
        )
        state: State = {
            "messages": [self._tool_msg(content, name="web_search")],
            "session_metadata": {},
            "pending_embeds": ["existing-qid"],
        }

        with patch("vectora.nodes.engine.embedding") as mock_emb:
            mock_emb.ainvoke = AsyncMock(
                return_value=json.dumps({"queue_id": "new-qid"})
            )
            result = await process_retrieval(state, self._runtime())

        assert "existing-qid" in result["pending_embeds"]
        assert "new-qid" in result["pending_embeds"]
