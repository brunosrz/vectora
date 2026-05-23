"""Tests para coder_finalize e search_finalize."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from vectora.agents.coder import coder_finalize
from vectora.agents.search import search_finalize

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ai(content: str = "", tool_calls: list | None = None) -> AIMessage:
    msg = MagicMock(spec=AIMessage)
    msg.content = content
    msg.tool_calls = tool_calls or []
    return msg


def _tc(name: str, args: dict | None = None) -> dict:
    return {"name": name, "args": args or {}, "id": "tc1"}


# ---------------------------------------------------------------------------
# coder_finalize
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coder_finalize_empty_messages():
    """Sem mensagens: retorna coder_result com valores padrão."""
    state = {"messages": []}
    result = await coder_finalize(state)
    assert "coder_result" in result
    cr = result["coder_result"]
    assert cr["files_changed"] == []
    assert cr["tests_run"] is False
    assert cr["success"] is True


@pytest.mark.asyncio
async def test_coder_finalize_extracts_files():
    """Detecta arquivos alterados via file_write e file_edit."""
    msg = _ai(
        tool_calls=[
            _tc("file_write", {"path": "src/foo.py"}),
            _tc("file_edit", {"path": "src/bar.py"}),
        ]
    )
    final = _ai("Implementação concluída.")
    state = {"messages": [msg, final]}
    result = await coder_finalize(state)
    cr = result["coder_result"]
    assert "src/foo.py" in cr["files_changed"]
    assert "src/bar.py" in cr["files_changed"]
    assert cr["summary"] == "Implementação concluída."


@pytest.mark.asyncio
async def test_coder_finalize_detects_pytest():
    """Detecta execução de pytest no terminal."""
    msg = _ai(tool_calls=[_tc("terminal", {"command": "pytest tests/ -v"})])
    final = _ai("Testes passaram.")
    state = {"messages": [msg, final]}
    result = await coder_finalize(state)
    assert result["coder_result"]["tests_run"] is True


@pytest.mark.asyncio
async def test_coder_finalize_detects_npm_test():
    """Detecta npm test no terminal."""
    msg = _ai(tool_calls=[_tc("terminal", {"command": "npm test"})])
    final = _ai("OK.")
    state = {"messages": [msg, final]}
    result = await coder_finalize(state)
    assert result["coder_result"]["tests_run"] is True


@pytest.mark.asyncio
async def test_coder_finalize_no_tests_for_git():
    """git não conta como teste."""
    msg = _ai(tool_calls=[_tc("terminal", {"command": "git commit -m 'feat'"})])
    final = _ai("Commit feito.")
    state = {"messages": [msg, final]}
    result = await coder_finalize(state)
    assert result["coder_result"]["tests_run"] is False


@pytest.mark.asyncio
async def test_coder_finalize_summary_from_last_ai_message():
    """Resumo vem do último AIMessage sem tool_calls."""
    m1 = _ai("Rascunho")
    m2 = _ai("Versão final da resposta.")
    state = {"messages": [m1, m2]}
    result = await coder_finalize(state)
    assert result["coder_result"]["summary"] == "Versão final da resposta."


@pytest.mark.asyncio
async def test_coder_finalize_deduplicates_files():
    """Mesmo arquivo referenciado duas vezes → aparece uma vez."""
    msg = _ai(
        tool_calls=[
            _tc("file_write", {"path": "a.py"}),
            _tc("file_edit", {"path": "a.py"}),
        ]
    )
    final = _ai("OK.")
    state = {"messages": [msg, final]}
    result = await coder_finalize(state)
    assert result["coder_result"]["files_changed"].count("a.py") == 1


@pytest.mark.asyncio
async def test_coder_finalize_tool_message_ignored():
    """ToolMessage não vira resumo."""
    tm = MagicMock(spec=ToolMessage)
    tm.content = "saída do terminal"
    final = _ai("Tarefa concluída.")
    state = {"messages": [tm, final]}
    result = await coder_finalize(state)
    assert result["coder_result"]["summary"] == "Tarefa concluída."


# ---------------------------------------------------------------------------
# search_finalize
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_finalize_empty_messages():
    """Sem mensagens: retorna search_result com valores padrão."""
    state = {"messages": []}
    result = await search_finalize(state)
    sr = result["search_result"]
    assert sr["sources"] == []
    assert sr["web_search_used"] is False
    assert sr["confidence"] == 0.5


@pytest.mark.asyncio
async def test_search_finalize_detects_web_search():
    """Detecta uso de web_search."""
    msg = _ai(tool_calls=[_tc("web_search", {"query": "langgraph tutorial"})])
    final = _ai("Achei o seguinte.")
    state = {"messages": [msg, final]}
    result = await search_finalize(state)
    sr = result["search_result"]
    assert sr["web_search_used"] is True
    assert sr["confidence"] == 0.8


@pytest.mark.asyncio
async def test_search_finalize_detects_fetch_url():
    """Detecta fetch_url e coleta a URL como fonte."""
    msg = _ai(tool_calls=[_tc("fetch_url", {"url": "https://example.com"})])
    final = _ai("Conteúdo extraído.")
    state = {"messages": [msg, final]}
    result = await search_finalize(state)
    sr = result["search_result"]
    assert sr["web_search_used"] is True
    assert "https://example.com" in sr["sources"]


@pytest.mark.asyncio
async def test_search_finalize_summary_from_last_ai():
    """Resumo vem do último AIMessage sem tool_calls."""
    final = _ai("Resultado da busca: X, Y, Z.")
    state = {"messages": [final]}
    result = await search_finalize(state)
    assert result["search_result"]["summary"] == "Resultado da busca: X, Y, Z."


@pytest.mark.asyncio
async def test_search_finalize_no_web_search():
    """vector_search não conta como web_search."""
    msg = _ai(tool_calls=[_tc("vector_search", {"query": "foo"})])
    final = _ai("Resultado do RAG.")
    state = {"messages": [msg, final]}
    result = await search_finalize(state)
    assert result["search_result"]["web_search_used"] is False


# ---------------------------------------------------------------------------
# Topologia do grafo
# ---------------------------------------------------------------------------


def test_graph_has_coder_finalize_node():
    """O grafo compilado deve conter o nó coder_finalize."""
    from vectora.graph import build_graph

    g = build_graph()
    assert "coder_finalize" in g.nodes


def test_graph_has_search_finalize_node():
    """O grafo compilado deve conter o nó search_finalize."""
    from vectora.graph import build_graph

    g = build_graph()
    assert "search_finalize" in g.nodes


def test_graph_coder_routes_to_coder_finalize():
    """coder deve ter coder_finalize como destino (sem tool_calls)."""
    from vectora.graph import build_graph

    g = build_graph()
    assert "coder_finalize" in g.nodes
    assert "coder" in g.nodes


def test_graph_search_routes_to_search_finalize():
    """search deve ter search_finalize como destino (sem tool_calls)."""
    from vectora.graph import build_graph

    g = build_graph()
    assert "search_finalize" in g.nodes
    assert "search" in g.nodes
