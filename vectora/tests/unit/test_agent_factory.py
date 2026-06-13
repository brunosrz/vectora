"""Testes unitários do agent_factory — Bloco E."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def reset_factory():
    """Garante estado limpo do factory entre testes."""
    import backend.graph as af

    # Estado original
    orig_graph = af._graph
    orig_ctx = af._checkpointer_ctx
    orig_tracker = dict(af._version_tracker)

    yield

    # Restaura sem fechar recursos reais (evita efeitos colaterais)
    af._graph = orig_graph
    af._checkpointer_ctx = orig_ctx
    af._version_tracker = orig_tracker


# ---------------------------------------------------------------------------
# get_user_agent — caching
# ---------------------------------------------------------------------------


async def test_get_user_agent_singleton():
    """Chamadas repetidas devem retornar o mesmo grafo."""
    import backend.graph as af

    fake_graph = MagicMock(name="compiled_graph")
    af._graph = fake_graph

    r1 = await af.get_user_agent("user1")
    r2 = await af.get_user_agent("user2")

    assert r1 is r2 is fake_graph


async def test_get_user_agent_none_user_id():
    """user_id=None deve funcionar sem erro."""
    import backend.graph as af

    af._graph = MagicMock()
    result = await af.get_user_agent(None)
    assert result is af._graph


async def test_get_user_agent_calls_build_when_none():
    """Primeira chamada (grafo=None) deve chamar _build_graph."""
    import backend.graph as af

    af._graph = None
    af._checkpointer_ctx = None

    fake_graph = MagicMock(name="fresh_graph")

    async def mock_build():
        af._graph = fake_graph
        af._checkpointer_ctx = MagicMock()

    with patch.object(af, "_build_graph_async", new=mock_build):
        result = await af.get_user_agent("user1")

    assert result is fake_graph


# ---------------------------------------------------------------------------
# aclose — lifecycle
# ---------------------------------------------------------------------------


async def test_aclose_idempotent():
    """aclose() chamado múltiplas vezes não deve levantar exceção."""
    import backend.graph as af

    af._graph = None
    af._checkpointer_ctx = None

    await af.aclose()
    await af.aclose()


async def test_aclose_clears_state():
    """aclose() deve limpar _graph, _checkpointer_ctx e _version_tracker."""
    import backend.graph as af

    fake_ctx = MagicMock()
    fake_ctx.__aexit__ = AsyncMock(return_value=None)

    af._graph = MagicMock()
    af._checkpointer_ctx = fake_ctx
    af._version_tracker["u1"] = (1, 2, 3)

    await af.aclose()

    assert af._graph is None
    assert af._checkpointer_ctx is None
    assert af._version_tracker == {}
    fake_ctx.__aexit__.assert_called_once_with(None, None, None)


async def test_aclose_handles_ctx_error():
    """aclose() deve silenciar erros do __aexit__ do checkpointer."""
    import backend.graph as af

    fake_ctx = MagicMock()
    fake_ctx.__aexit__ = AsyncMock(side_effect=RuntimeError("db error"))
    af._checkpointer_ctx = fake_ctx

    # Não deve propagar
    await af.aclose()
    assert af._graph is None


# ---------------------------------------------------------------------------
# awarm — startup
# ---------------------------------------------------------------------------


async def test_awarm_does_not_raise_on_error():
    """awarm() deve silenciar erros de inicialização."""
    import backend.graph as af

    with patch.object(af, "get_user_agent", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = RuntimeError("db locked")
        await af.awarm()  # não deve propagar


# ---------------------------------------------------------------------------
# _track_versions — invalidação de cache LLM
# ---------------------------------------------------------------------------


async def test_version_tracker_registers_first_version():
    """_track_versions deve registrar a versão na primeira chamada sem invalidar."""
    import backend.graph as af

    af._version_tracker.clear()

    with (
        patch("backend.graph.tools_version", return_value=3),
        patch("backend.graph.tool_policy") as mock_policy,
        patch("backend.graph.skills_version", return_value=5),
        patch("backend.graph._invalidate_llm_cache") as mock_inv,
    ):
        mock_policy.policy_version.return_value = 7
        af._track_versions("u1")

    assert af._version_tracker["u1"] == (3, 7, 5)
    mock_inv.assert_not_called()


async def test_version_tracker_invalidates_on_change():
    """_track_versions deve chamar _invalidate_llm_cache quando versão muda."""
    import backend.graph as af

    af._version_tracker["u1"] = (3, 7, 5)

    with (
        patch("backend.graph.tools_version", return_value=4),
        patch("backend.graph.tool_policy") as mock_policy,
        patch("backend.graph.skills_version", return_value=5),
        patch("backend.graph._invalidate_llm_cache") as mock_inv,
    ):
        mock_policy.policy_version.return_value = 7
        af._track_versions("u1")

    mock_inv.assert_called_once_with("u1")
    assert af._version_tracker["u1"] == (4, 7, 5)


async def test_version_tracker_invalidates_on_skills_change():
    """Skills version mudando deve invalidar o cache do LLM."""
    import backend.graph as af

    af._version_tracker["u1"] = (3, 7, 5)

    with (
        patch("backend.graph.tools_version", return_value=3),
        patch("backend.graph.tool_policy") as mock_policy,
        patch("backend.graph.skills_version", return_value=6),
        patch("backend.graph._invalidate_llm_cache") as mock_inv,
    ):
        mock_policy.policy_version.return_value = 7
        af._track_versions("u1")

    mock_inv.assert_called_once_with("u1")
    assert af._version_tracker["u1"] == (3, 7, 6)


# ---------------------------------------------------------------------------
# _invalidate_llm_cache
# ---------------------------------------------------------------------------


async def test_invalidate_removes_only_target_user():
    """_invalidate_llm_cache deve remover apenas as entradas do usuário alvo."""
    import backend.graph as af
    from backend.services import llm_tools

    llm_tools._bound_cache[("u1", 1, 1)] = "llm_u1_a"
    llm_tools._bound_cache[("u1", 2, 1)] = "llm_u1_b"
    llm_tools._bound_cache[("u2", 1, 1)] = "llm_u2_a"

    af._invalidate_llm_cache("u1")

    assert ("u1", 1, 1) not in llm_tools._bound_cache
    assert ("u1", 2, 1) not in llm_tools._bound_cache
    assert ("u2", 1, 1) in llm_tools._bound_cache

    # Cleanup
    llm_tools._bound_cache.pop(("u2", 1, 1), None)
