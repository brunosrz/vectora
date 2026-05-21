"""Fixtures mínimas compartilhadas — KISS."""

from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from vectora.state import Document, State


@pytest.fixture
def state() -> State:
    return {
        "messages": [HumanMessage(content="test query")],
        "session_metadata": {},
    }


@pytest.fixture
def doc() -> Document:
    return Document(
        page_content="conteúdo de teste",
        metadata={"source": "http://example.com"},
        relevance_score=0.8,
    )
