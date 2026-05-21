"""Tests for vectora/nodes/base.py"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from vectora.nodes.base import build_messages, invoke_llm, sanitize_for_gemini
from vectora.state import Document, State

# ---------------------------------------------------------------------------
# sanitize_for_gemini
# ---------------------------------------------------------------------------


class TestSanitizeForGemini:
    def test_starts_with_human_message_unchanged(self):
        msgs = [HumanMessage(content="oi"), AIMessage(content="olá")]
        result = sanitize_for_gemini(msgs)
        assert result[0] == msgs[0]

    def test_removes_orphan_ai_with_tool_calls(self):
        ai = AIMessage(content="", tool_calls=[{"name": "t", "id": "1", "args": {}}])
        tool = ToolMessage(content="result", tool_call_id="1")
        human = HumanMessage(content="depois")
        result = sanitize_for_gemini([ai, tool, human])
        assert result[0] == human

    def test_empty_list_returns_empty(self):
        assert sanitize_for_gemini([]) == []

    def test_valid_ai_without_tool_calls_preserved(self):
        ai = AIMessage(content="resposta")
        result = sanitize_for_gemini([ai])
        assert result[0] == ai

    def test_removes_leading_tool_message(self):
        tool = ToolMessage(content="orphan", tool_call_id="x")
        human = HumanMessage(content="real")
        result = sanitize_for_gemini([tool, human])
        assert result[0] == human


# ---------------------------------------------------------------------------
# build_messages
# ---------------------------------------------------------------------------


class TestBuildMessages:
    @pytest.mark.asyncio
    async def test_returns_list_with_system_message(self):
        state: State = {
            "messages": [HumanMessage(content="oi")],
            "session_metadata": {"thread_id": 1},
        }
        with patch("vectora.nodes.base.get_memory_store") as mock_store:
            store = AsyncMock()
            store.get_all.return_value = []
            mock_store.return_value = store
            msgs = await build_messages(state, system_prompt="Você é Vectora.")

        assert isinstance(msgs[0], SystemMessage)
        assert "Vectora" in msgs[0].content

    @pytest.mark.asyncio
    async def test_system_prompt_injected(self):
        state: State = {
            "messages": [HumanMessage(content="test")],
            "session_metadata": {},
        }
        with patch("vectora.nodes.base.get_memory_store") as mock_store:
            store = AsyncMock()
            store.get_all.return_value = []
            mock_store.return_value = store
            msgs = await build_messages(state, system_prompt="PROMPT_TESTE")

        assert msgs[0].content.startswith("PROMPT_TESTE")

    @pytest.mark.asyncio
    async def test_rag_docs_appended_to_system(self):
        docs = [Document(page_content="contexto rag", metadata={}, relevance_score=0.9)]
        state: State = {
            "messages": [HumanMessage(content="query")],
            "session_metadata": {},
            "rag_docs": docs,
        }
        with patch("vectora.nodes.base.get_memory_store") as mock_store:
            store = AsyncMock()
            store.get_all.return_value = []
            mock_store.return_value = store
            msgs = await build_messages(state, system_prompt="BASE")

        assert "contexto rag" in msgs[0].content


# ---------------------------------------------------------------------------
# invoke_llm
# ---------------------------------------------------------------------------


class TestInvokeLlm:
    @pytest.mark.asyncio
    async def test_returns_ai_message(self):
        state: State = {
            "messages": [HumanMessage(content="oi")],
            "session_metadata": {},
        }

        async def fake_astream(msgs):  # type: ignore[return]
            chunk = MagicMock()
            chunk.content = "resposta"
            chunk.tool_calls = []
            yield chunk

        llm = MagicMock()
        llm.astream = fake_astream

        with patch("vectora.nodes.base.get_memory_store") as mock_store:
            store = AsyncMock()
            store.get_all.return_value = []
            mock_store.return_value = store
            result = await invoke_llm(llm, state, system_prompt="prompt")

        assert "messages" in result
        assert isinstance(result["messages"][0], AIMessage)
        assert result["messages"][0].content == "resposta"

    @pytest.mark.asyncio
    async def test_quota_exhausted_returns_error_message(self):
        state: State = {
            "messages": [HumanMessage(content="oi")],
            "session_metadata": {},
        }

        async def fake_astream_error(msgs):
            raise Exception("RESOURCE_EXHAUSTED quota exceeded")
            yield  # make it a generator

        llm = MagicMock()
        llm.astream = fake_astream_error

        with patch("vectora.nodes.base.get_memory_store") as mock_store:
            store = AsyncMock()
            store.get_all.return_value = []
            mock_store.return_value = store
            result = await invoke_llm(llm, state, system_prompt="")

        assert (
            "Quota" in result["messages"][0].content
            or "quota" in result["messages"][0].content.lower()
        )
