"""Tests for vectora/state.py"""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from vectora.state import Document, State


def test_document_required_fields():
    doc = Document(page_content="texto", metadata={}, relevance_score=None)
    assert doc["page_content"] == "texto"
    assert doc["metadata"] == {}
    assert doc["relevance_score"] is None


def test_document_with_score():
    doc = Document(page_content="x", metadata={"source": "url"}, relevance_score=0.9)
    assert doc["relevance_score"] == 0.9
    assert doc["metadata"]["source"] == "url"


def test_state_minimal():
    s: State = {"messages": [], "session_metadata": {}}
    assert s["messages"] == []
    assert s["session_metadata"] == {}


def test_state_rag_fields():
    s: State = {
        "messages": [HumanMessage(content="oi")],
        "session_metadata": {},
        "rag_query": "jwt",
        "rag_docs": [],
        "pending_embeds": ["q1", "q2"],
        "web_search_triggered": True,
        "routing_decision": "rag",
    }
    assert s["rag_query"] == "jwt"
    assert s["pending_embeds"] == ["q1", "q2"]
    assert s["web_search_triggered"] is True
    assert s["routing_decision"] == "rag"


def test_state_routing_values():
    for decision in ("direct", "search", "coder", "rag"):
        s: State = {
            "messages": [],
            "session_metadata": {},
            "routing_decision": decision,  # type: ignore[typeddict-item]
        }
        assert s["routing_decision"] == decision
