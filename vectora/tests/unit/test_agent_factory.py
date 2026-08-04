"""Testes para agent_factory.py — cache de grafos por sessão e ParallelToolNode."""

from __future__ import annotations

import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# HarnessProfile / cache de grafos por sessão (user_id, model)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_agent_creates_graph_per_user():
    """get_user_agent com user_id cria entrada em _graphs_by_user."""
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
        # Chave de cache inclui workspace_id (string vazia quando não há
        # workspace ativo pro usuário).
        assert ("user-1", "__default__", "") in af._graphs_by_user


@pytest.mark.asyncio
async def test_get_user_agent_isolates_users():
    """Dois user_ids diferentes geram entradas isoladas no cache."""
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
    """Mesma (user_id, model) não reconstrói o grafo (cache hit)."""
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
    """Sem user_id usa cache global _graphs (fallback)."""
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
        # Chave global também carrega o workspace ("" quando não há um
        # workspace_id explícito e não há user_id pra resolver o ativo).
        assert "__default__::ws=" in af._graphs
        assert not af._graphs_by_user


# ---------------------------------------------------------------------------
# HITL dinâmico — permission_mode NÃO entra na chave de cache (um grafo só)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_agent_one_graph_serves_all_permission_modes():
    """HITL dinâmico: o grafo é o mesmo para qualquer modo (o modo é lido do
    runtime.context por request, não compilado).

    Antes cada permission_mode com interrupt_on distinto tinha grafo próprio
    cacheado; agora get_user_agent nem aceita permission_mode e compila um único
    grafo por (user, model, chat_mode). Trocar o modo na appbar não recompila.
    """
    fake_graph = MagicMock(name="graph")
    build_mock = AsyncMock(return_value=fake_graph)

    with (
        patch("backend.services.agent_factory._build_graph_async", new=build_mock),
        patch("backend.services.agent_factory._track_versions"),
    ):
        import backend.services.agent_factory as af

        af._graphs_by_user.clear()
        af._graphs.clear()

        g1 = await af.get_user_agent(user_id="user-1", model="")
        g2 = await af.get_user_agent(user_id="user-1", model="")

        assert g1 is g2
        assert build_mock.call_count == 1
        # _build_graph_async recebe (model, chat_mode, user_id, workspace_id)
        # — sem permission_mode (assinatura reduzida no HITL dinâmico).
        assert len(build_mock.call_args_list[0].args) == 4


@pytest.mark.asyncio
async def test_get_user_agent_rejects_permission_mode_kwarg():
    """Erro/borda: permission_mode foi removido da assinatura — passá-lo agora
    é TypeError (protege contra caller legado ressurgir silenciosamente)."""
    import backend.services.agent_factory as af

    with pytest.raises(TypeError):
        await af.get_user_agent(user_id="user-2", permission_mode="plan")  # ty: ignore[unknown-argument]


# ---------------------------------------------------------------------------
# ParallelToolNode — execução paralela de tools de tipos diferentes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parallel_tool_node_runs_tools_concurrently():
    """Tools de tipos diferentes acionam asyncio.gather."""
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
    """Tools do mesmo tipo não acionam asyncio.gather — delega para super."""
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
        with contextlib.suppress(Exception):
            await node.arun(data)

    gather_mock.assert_not_called()


@pytest.mark.asyncio
async def test_parallel_tool_node_empty_tool_calls_delegates():
    """Sem tool_calls, asyncio.gather não é chamado — delega para super."""
    from backend.nodes.parallel_tools import ParallelToolNode

    node = ParallelToolNode(tools=[])

    data: dict[str, list[object]] = {"tool_calls": []}

    gather_mock = AsyncMock()
    with patch("backend.nodes.parallel_tools.asyncio.gather", gather_mock):
        with contextlib.suppress(Exception):
            await node.arun(data)

    gather_mock.assert_not_called()


@pytest.mark.asyncio
async def test_parallel_tool_node_unknown_tool_returns_error():
    """Tool desconhecida retorna dict com chave 'error' (defensivo, não lança)."""
    from backend.nodes.parallel_tools import ParallelToolNode

    node = ParallelToolNode(tools=[])

    result = await node._run_tool({"name": "nao_existe", "args": {}})
    assert "error" in result
    assert "nao_existe" in result["error"]
