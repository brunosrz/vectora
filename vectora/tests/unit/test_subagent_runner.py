"""Testes para backend/scheduling/subagent_runner.py.

Cobre: resolução de spec por SOUL e paridade entre `SUBAGENT_TYPES` (literal
estático, evita ciclo de import) e o catálogo real. A montagem do agente
isolado por SOUL (execução agendada, `trigger_config.subagent_type`) é
responsabilidade de `backend/scheduling/background_tasks.py::run_task`
(motor nativo) — coberta em `tests/unit/test_services_background.py`.
"""

from __future__ import annotations

import pytest

from backend.scheduling.subagent_runner import SUBAGENT_TYPES, _spec_for


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
