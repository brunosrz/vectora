"""Tests for vectora/services/text.py"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from vectora.services.text import text_service


class TestTextService:
    def test_split_returns_list(self):
        result = text_service.split("Este é um texto curto.")
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_split_long_text_produces_multiple_chunks(self):
        long_text = "palavra " * 2000
        chunks = text_service.split(long_text)
        assert len(chunks) > 1

    def test_split_empty_string(self):
        result = text_service.split("")
        assert isinstance(result, list)

    def test_count_messages_tokens_returns_int(self):
        msgs = [HumanMessage(content="olá"), AIMessage(content="oi")]
        count = text_service.count_messages_tokens(msgs)
        assert isinstance(count, int)
        assert count > 0

    def test_count_tokens_increases_with_length(self):
        short = [HumanMessage(content="oi")]
        long = [HumanMessage(content="palavra " * 100)]
        assert text_service.count_messages_tokens(
            long
        ) > text_service.count_messages_tokens(short)

    def test_count_empty_messages(self):
        count = text_service.count_messages_tokens([])
        assert count == 0
