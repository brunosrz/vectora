"""Tests for vectora/agents/_identity.py"""

from __future__ import annotations

from vectora.agents._identity import VECTORA_IDENTITY


def test_identity_is_string():
    assert isinstance(VECTORA_IDENTITY, str)
    assert len(VECTORA_IDENTITY) > 200


def test_identity_contains_stack():
    assert "LangChain" in VECTORA_IDENTITY
    assert "LangGraph" in VECTORA_IDENTITY
    assert "FastMCP" in VECTORA_IDENTITY
    assert "LanceDB" in VECTORA_IDENTITY


def test_identity_contains_license_and_repo():
    assert "Apache 2.0" in VECTORA_IDENTITY
    assert "github.com" in VECTORA_IDENTITY


def test_identity_mentions_cohere():
    assert "Cohere" in VECTORA_IDENTITY


def test_identity_describes_agents():
    assert "Supervisor" in VECTORA_IDENTITY
    assert "Direct" in VECTORA_IDENTITY
    assert "Search" in VECTORA_IDENTITY
    assert "Coder" in VECTORA_IDENTITY
