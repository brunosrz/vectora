"""Testes para agent_factory.py — DE-5 (cache por sessão) e DE-12 (ParallelToolNode)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# DE-5 — HarnessProfile / cache de grafos por sessão (user_id, model)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_agent_creates_graph_per_user():
    """get_user_agent com user_id cria entrada em _graphs_by_user (DE-5)."""
    fake_graph = MagicMock()

    with (
        patch(
            "backend.services.agent_factory._build_graph_async",
            new=AsyncMock(return_value=fake_graph),
        ),
        patch("backend.services.agent_factory._track_versions"),
    ):
        import backend.services.agent_factory as af

        af._graphs_by_user.clear()
        af._graphs.clear()

        graph = await af.get_user_agent(user_id="user-1", model="")
        assert graph is fake_graph
        assert ("user-1", "__default__") in af._graphs_by_user


@pytest.mark.asyncio
async def test_get_user_agent_isolates_users():
    """Dois user_ids diferentes geram entradas isoladas no cache (DE-5)."""
    fake_graph_1 = MagicMock(name="graph-user1")
    fake_graph_2 = MagicMock(name="graph-user2")
    graphs_seq = [fake_graph_1, fake_graph_2]

    with (
        patch(
            "backend.services.agent_factory._build_graph_async",
            new=AsyncMock(side_effect=graphs_seq),
        ),
        patch("backend.services.agent_factory._track_versions"),
    ):
        import backend.services.agent_factory as af

        af._graphs_by_user.clear()
        af._graphs.clear()

        g1 = await af.get_user_agent(user_id="user-A", model="")
        g2 = await af.get_user_agent(user_id="user-B", model="")

        assert g1 is fake_graph_1
        assert g2 is fake_graph_2
        assert g1 is not g2


@pytest.mark.asyncio
async def test_get_user_agent_same_user_reuses_graph():
    """Mesma (user_id, model) não reconstrói o grafo (cache hit) (DE-5)."""
    fake_graph = MagicMock()
    build_mock = AsyncMock(return_value=fake_graph)

    with (
        patch("backend.services.agent_factory._build_graph_async", new=build_mock),
        patch("backend.services.agent_factory._track_versions"),
    ):
        import backend.services.agent_factory as af

        af._graphs_by_user.clear()
        af._graphs.clear()

        g1 = await af.get_user_agent(user_id="user-X", model="")
        g2 = await af.get_user_agent(user_id="user-X", model="")

        assert g1 is g2
        assert build_mock.call_count == 1


@pytest.mark.asyncio
async def test_get_user_agent_no_user_id_uses_global_cache():
    """Sem user_id usa cache global _graphs (DE-5 fallback)."""
    fake_graph = MagicMock()

    with patch(
        "backend.services.agent_factory._build_graph_async",
        new=AsyncMock(return_value=fake_graph),
    ):
        import backend.services.agent_factory as af

        af._graphs_by_user.clear()
        af._graphs.clear()

        graph = await af.get_user_agent(user_id=None, model="")
        assert graph is fake_graph
        assert "__default__" in af._graphs
        assert not af._graphs_by_user


# ---------------------------------------------------------------------------
# DE-12 — ParallelToolNode — execução paralela de tools de tipos diferentes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parallel_tool_node_runs_tools_concurrently():
    """Tools de tipos diferentes acionam asyncio.gather (DE-12)."""
    from langchain_core.tools import tool as lc_tool

    from backend.nodes.parallel_tools import ParallelToolNode

    @lc_tool
    async def tool_a(query: str = "") -> str:
        """Tool A."""
        return "result_a"

    @lc_tool
    async def tool_b(query: str = "") -> str:
        """Tool B."""
        return "result_b"

    node = ParallelToolNode(tools=[tool_a, tool_b])

    data = {
        "tool_calls": [
            {"name": "tool_a", "args": {"query": "x"}},
            {"name": "tool_b", "args": {"query": "y"}},
        ]
    }

    with patch(
        "backend.nodes.parallel_tools.asyncio.gather", wraps=asyncio.gather
    ) as gather_spy:
        result = await node.arun(data)

    # Verifica que gather foi chamado com return_exceptions=True (assinatura do ParallelToolNode)
    parallel_calls = [
        c
        for c in gather_spy.call_args_list
        if c.kwargs.get("return_exceptions") is True
    ]
    assert len(parallel_calls) == 1
    assert result is not None


@pytest.mark.asyncio
async def test_parallel_tool_node_same_type_not_parallelized():
    """Tools do mesmo tipo não acionam asyncio.gather — delega para super (DE-12)."""
    from langchain_core.tools import tool as lc_tool

    from backend.nodes.parallel_tools import ParallelToolNode

    @lc_tool
    async def tool_a(query: str = "") -> str:
        """Tool A."""
        return "ok"

    node = ParallelToolNode(tools=[tool_a])

    data = {
        "tool_calls": [
            {"name": "tool_a", "args": {}},
            {"name": "tool_a", "args": {}},
        ]
    }

    gather_mock = AsyncMock()
    with patch("backend.nodes.parallel_tools.asyncio.gather", gather_mock):
        try:
            await node.arun(data)
        except Exception:
            pass

    gather_mock.assert_not_called()


@pytest.mark.asyncio
async def test_parallel_tool_node_empty_tool_calls_delegates():
    """Sem tool_calls, asyncio.gather não é chamado — delega para super (DE-12)."""
    from backend.nodes.parallel_tools import ParallelToolNode

    node = ParallelToolNode(tools=[])

    data: dict[str, list[object]] = {"tool_calls": []}

    gather_mock = AsyncMock()
    with patch("backend.nodes.parallel_tools.asyncio.gather", gather_mock):
        try:
            await node.arun(data)
        except Exception:
            pass

    gather_mock.assert_not_called()


@pytest.mark.asyncio
async def test_parallel_tool_node_unknown_tool_returns_error():
    """Tool desconhecida retorna dict com chave 'error' (DE-12 — defensive)."""
    from backend.nodes.parallel_tools import ParallelToolNode

    node = ParallelToolNode(tools=[])

    result = await node._run_tool({"name": "nao_existe", "args": {}})
    assert "error" in result
    assert "nao_existe" in result["error"]
