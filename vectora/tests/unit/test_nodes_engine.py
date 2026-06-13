"""Tests for src/nodes/engine.py"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from backend.nodes.engine import _extract_tavily_results, process_retrieval
from backend.state import Document, State


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


class TestProcessRetrieval:
    """process_retrieval passa resultados web pelo gate de curadoria (A5)."""

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
    async def test_fetch_url_not_cascaded(self):
        # fetch_url não entra no cascading — o usuário escolheu a URL
        # explicitamente (intenção de leitura, não de indexação).
        content = json.dumps(
            [{"content": "fetched page", "title": "Page", "url": "https://b.com"}]
        )
        state: State = {
            "messages": [self._tool_msg(content, name="fetch_url")],
            "session_metadata": {},
        }
        result = await process_retrieval(state, self._runtime())
        assert result == {}

    @pytest.mark.asyncio
    async def test_valid_web_search_runs_curation(self):
        content = json.dumps(
            [{"content": "article content", "title": "Art", "url": "https://a.com"}]
        )
        state: State = {
            "messages": [
                HumanMessage(content="pesquisa X"),
                self._tool_msg(content, name="web_search"),
            ],
            "session_metadata": {},
        }
        docs = [
            Document(
                page_content="article content",
                metadata={"url": "https://a.com"},
                relevance_score=None,
            )
        ]
        with patch(
            "backend.nodes.engine.curate_and_enqueue", new_callable=AsyncMock
        ) as mock_curate:
            mock_curate.return_value = (docs, ["q-abc"])
            result = await process_retrieval(state, self._runtime())

        assert result.get("web_search_triggered") is True
        assert len(result["retrieval_results"]["web_search"]) == 1
        assert "q-abc" in result["pending_embeds"]
        # O gate recebe a query do usuário para julgar relevância.
        assert mock_curate.await_args is not None
        assert mock_curate.await_args.args[1] == "pesquisa X"

    @pytest.mark.asyncio
    async def test_curation_rejecting_everything_persists_nothing(self):
        content = json.dumps(
            [{"content": "lixo", "title": "Spam", "url": "https://spam.com"}]
        )
        state: State = {
            "messages": [self._tool_msg(content, name="web_search")],
            "session_metadata": {},
        }
        docs = [Document(page_content="lixo", metadata={}, relevance_score=None)]
        with patch(
            "backend.nodes.engine.curate_and_enqueue", new_callable=AsyncMock
        ) as mock_curate:
            # Curadoria devolve docs para contexto imediato, mas 0 persistidos.
            mock_curate.return_value = (docs, [])
            result = await process_retrieval(state, self._runtime())

        assert result.get("web_search_triggered") is True
        assert "pending_embeds" not in result or result["pending_embeds"] == []

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
        docs = [Document(page_content="new doc", metadata={}, relevance_score=None)]
        with patch(
            "backend.nodes.engine.curate_and_enqueue", new_callable=AsyncMock
        ) as mock_curate:
            mock_curate.return_value = (docs, ["new-qid"])
            result = await process_retrieval(state, self._runtime())

        assert "existing-qid" in result["pending_embeds"]
        assert "new-qid" in result["pending_embeds"]
