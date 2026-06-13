"""Tests para src/agents/results.py — schemas CoderResult e SearchResult."""

from __future__ import annotations

import pytest

from backend.types import CoderResult, SearchResult

# ---------------------------------------------------------------------------
# CoderResult
# ---------------------------------------------------------------------------


def test_coder_result_defaults():
    """Campos opcionais têm defaults corretos."""
    r = CoderResult(summary="Fiz X")
    assert r.summary == "Fiz X"
    assert r.files_changed == []
    assert r.tests_run is False
    assert r.success is True
    assert r.next_steps is None


def test_coder_result_full():
    """Todos os campos preenchidos corretamente."""
    r = CoderResult(
        summary="Implementei Y",
        files_changed=["src/foo.py", "tests/test_foo.py"],
        tests_run=True,
        success=True,
        next_steps="Fazer deploy",
    )
    assert r.files_changed == ["src/foo.py", "tests/test_foo.py"]
    assert r.tests_run is True
    assert r.next_steps == "Fazer deploy"


def test_coder_result_failure():
    """success=False é aceito."""
    r = CoderResult(summary="Erro ao compilar", success=False)
    assert r.success is False


def test_coder_result_model_dump():
    """model_dump() produz dict serializável."""
    r = CoderResult(summary="ok", files_changed=["a.py"])
    d = r.model_dump()
    assert isinstance(d, dict)
    assert d["summary"] == "ok"
    assert d["files_changed"] == ["a.py"]


# ---------------------------------------------------------------------------
# SearchResult
# ---------------------------------------------------------------------------


def test_search_result_defaults():
    """Campos opcionais têm defaults corretos."""
    r = SearchResult(summary="Encontrei X")
    assert r.summary == "Encontrei X"
    assert r.sources == []
    assert r.confidence == pytest.approx(0.7)
    assert r.web_search_used is False


def test_search_result_full():
    """Todos os campos preenchidos corretamente."""
    r = SearchResult(
        summary="Pesquisa sobre LangGraph",
        sources=["https://langchain.com", "https://docs.rs"],
        confidence=0.9,
        web_search_used=True,
    )
    assert len(r.sources) == 2
    assert r.confidence == pytest.approx(0.9)
    assert r.web_search_used is True


def test_search_result_confidence_bounds():
    """confidence deve estar entre 0.0 e 1.0."""
    with pytest.raises((ValueError, Exception)):
        SearchResult(summary="x", confidence=1.5)
    with pytest.raises((ValueError, Exception)):
        SearchResult(summary="x", confidence=-0.1)


def test_search_result_model_dump():
    """model_dump() produz dict serializável."""
    r = SearchResult(summary="encontrei", sources=["https://a.com"])
    d = r.model_dump()
    assert isinstance(d, dict)
    assert d["web_search_used"] is False
    assert "a.com" in d["sources"][0]
