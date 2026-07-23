"""Testes para backend/scheduling/subagent_runner.py.

Cobre: resolução de spec por tipo de subagente e montagem do grafo isolado
(sem `subagents=`, checkpointer/store compartilhados com o agente principal).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.scheduling.subagent_runner import (
    SUBAGENT_TYPES,
    _spec_for,
    build_subagent_graph,
)


def test_subagent_types_cobre_coder_e_search():
    assert SUBAGENT_TYPES == ("coder", "search")


def test_spec_for_coder_retorna_spec_do_coder():
    from backend.agents.coder import SUBAGENT_SPEC as coder_spec

    assert _spec_for("coder") == coder_spec


def test_spec_for_search_retorna_spec_do_search():
    from backend.agents.search import SUBAGENT_SPEC as search_spec

    assert _spec_for("search") == search_spec


def test_spec_for_tipo_invalido_levanta_value_error():
    with pytest.raises(ValueError, match="subagent_type inválido"):
        _spec_for("orchestrator")


@pytest.mark.asyncio
async def test_build_subagent_graph_monta_grafo_sem_subagents_param():
    fake_checkpointer = MagicMock()
    fake_store = MagicMock()
    fake_graph = MagicMock()

    with (
        patch(
            "backend.services.agent_factory.get_checkpointer",
            new=AsyncMock(return_value=fake_checkpointer),
        ),
        patch(
            "backend.services.agent_factory.get_store",
            new=AsyncMock(return_value=fake_store),
        ),
        patch("deepagents.create_deep_agent", return_value=fake_graph) as mock_create,
    ):
        result = await build_subagent_graph("coder")

        assert result is fake_graph
        _, kwargs = mock_create.call_args
        assert "subagents" not in kwargs
        assert kwargs["checkpointer"] is fake_checkpointer
        assert kwargs["store"] is fake_store
        assert kwargs["name"] == "vectora-subagent-coder"


@pytest.mark.asyncio
async def test_build_subagent_graph_tipo_invalido_propaga_erro():
    with pytest.raises(ValueError, match="subagent_type inválido"):
        await build_subagent_graph("orchestrator")
