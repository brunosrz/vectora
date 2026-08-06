"""Testes para backend/scheduling/subagent_runner.py.

Cobre: resolução de spec por SOUL, montagem do grafo isolado (sem
`subagents=`, checkpointer/store/middleware compartilhados com o agente
principal), e paridade entre `SUBAGENT_TYPES` (literal estático, evita
ciclo de import) e o catálogo real.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.scheduling.subagent_runner import (
    SUBAGENT_TYPES,
    _spec_for,
    build_subagent_graph,
)


def test_subagent_types_bate_com_o_catalogo_real():
    """SUBAGENT_TYPES é um literal estático (evita ciclo de import
    nodes.tools -> background -> subagent_runner -> souls -> nodes.tools) —
    esse teste é o que garante que ele nunca fica desatualizado."""
    from backend.agents.souls import SOUL_CATALOG

    assert set(SUBAGENT_TYPES) == set(SOUL_CATALOG)
    assert "coder" in SUBAGENT_TYPES
    assert "search" in SUBAGENT_TYPES


def test_spec_for_coder_retorna_soul_do_coder():
    from backend.agents.souls import SOUL_CATALOG

    assert _spec_for("coder") is SOUL_CATALOG["coder"]


def test_spec_for_search_retorna_soul_do_search():
    from backend.agents.souls import SOUL_CATALOG

    assert _spec_for("search") is SOUL_CATALOG["search"]


def test_spec_for_tipo_invalido_levanta_value_error():
    with pytest.raises(ValueError, match="subagent_type inválido"):
        _spec_for("orchestrator")


@pytest.mark.asyncio
async def test_build_subagent_graph_monta_grafo_sem_subagents_param():
    fake_checkpointer = MagicMock()
    fake_store = MagicMock()
    fake_graph = MagicMock()
    fake_middleware = [MagicMock()]

    with (
        patch(
            "backend.services.agent_factory.get_checkpointer",
            new=AsyncMock(return_value=fake_checkpointer),
        ),
        patch(
            "backend.services.agent_factory.get_store",
            new=AsyncMock(return_value=fake_store),
        ),
        patch(
            "backend.services.middleware.build_middleware_stack",
            return_value=fake_middleware,
        ),
        patch("deepagents.create_deep_agent", return_value=fake_graph) as mock_create,
    ):
        result = await build_subagent_graph("coder")

        assert result is fake_graph
        _, kwargs = mock_create.call_args
        assert "subagents" not in kwargs
        assert kwargs["checkpointer"] is fake_checkpointer
        assert kwargs["store"] is fake_store
        assert kwargs["middleware"] is fake_middleware
        assert kwargs["name"] == "vectora-subagent-coder"


@pytest.mark.asyncio
async def test_build_subagent_graph_tipo_invalido_propaga_erro():
    with pytest.raises(ValueError, match="subagent_type inválido"):
        await build_subagent_graph("orchestrator")
