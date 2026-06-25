"""Testes das tools do Context Graph.

Cobre: graph_query, graph_explain, graph_path — caminho feliz + erros.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.runnables import RunnableConfig

SAMPLE_GRAPH = {
    "nodes": [
        {"id": "node_auth", "label": "AuthService", "type": "class"},
        {"id": "node_login", "label": "login", "type": "function"},
        {"id": "node_token", "label": "Token", "type": "class"},
    ],
    "edges": [
        {
            "source": "node_auth",
            "target": "node_login",
            "label": "calls",
            "type": "calls",
        },
        {
            "source": "node_login",
            "target": "node_token",
            "label": "creates",
            "type": "creates",
        },
    ],
}


def _make_ws(tmp_path: Path) -> tuple[MagicMock, Path]:
    graph_dir = tmp_path / ".vectora" / "graph"
    graph_dir.mkdir(parents=True)
    graph_file = graph_dir / "graph.json"
    graph_file.write_text(json.dumps(SAMPLE_GRAPH), encoding="utf-8")
    ws = MagicMock()
    ws.cwd = str(tmp_path)
    return ws, graph_file


def _config(workspace_id: str) -> RunnableConfig:
    return cast("RunnableConfig", {"configurable": {"workspace_id": workspace_id}})


def _patch_registry(ws_mock):
    registry = MagicMock()
    registry.get = MagicMock(return_value=ws_mock)
    return patch("backend.services.workspace.workspace_registry", registry)


# ---------------------------------------------------------------------------
# graph_query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graph_query_found(tmp_path):
    from backend.tools.context_graph import graph_query

    ws, _ = _make_ws(tmp_path)
    with _patch_registry(ws):
        result = await graph_query.ainvoke({"question": "auth"}, config=_config("ws1"))
    assert "AuthService" in result or "auth" in result.lower()
    assert "Encontrei" in result


@pytest.mark.asyncio
async def test_graph_query_not_found(tmp_path):
    from backend.tools.context_graph import graph_query

    ws, _ = _make_ws(tmp_path)
    with _patch_registry(ws):
        result = await graph_query.ainvoke(
            {"question": "zzznomatch123"}, config=_config("ws1")
        )
    assert "Nenhum nó" in result or "not found" in result.lower()


@pytest.mark.asyncio
async def test_graph_query_no_workspace():
    from backend.tools.context_graph import graph_query

    with _patch_registry(None):
        result = await graph_query.ainvoke(
            {"question": "auth"}, config=cast("RunnableConfig", {"configurable": {}})
        )
    assert "Erro" in result or "workspace" in result.lower()


@pytest.mark.asyncio
async def test_graph_query_no_graph_file(tmp_path):
    from backend.tools.context_graph import graph_query

    ws = MagicMock()
    ws.cwd = str(tmp_path)
    with _patch_registry(ws):
        result = await graph_query.ainvoke({"question": "auth"}, config=_config("ws1"))
    assert "build_knowledge_graph" in result or "não encontrado" in result.lower()


# ---------------------------------------------------------------------------
# graph_explain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graph_explain_found(tmp_path):
    from backend.tools.context_graph import graph_explain

    ws, _ = _make_ws(tmp_path)
    with _patch_registry(ws):
        result = await graph_explain.ainvoke(
            {"node_id": "node_auth"}, config=_config("ws1")
        )
    assert "AuthService" in result


@pytest.mark.asyncio
async def test_graph_explain_not_found(tmp_path):
    from backend.tools.context_graph import graph_explain

    ws, _ = _make_ws(tmp_path)
    with _patch_registry(ws):
        result = await graph_explain.ainvoke(
            {"node_id": "nonexistent_node_xyz"}, config=_config("ws1")
        )
    assert "não encontrado" in result.lower() or "not found" in result.lower()


# ---------------------------------------------------------------------------
# graph_path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graph_path_found(tmp_path):
    from backend.tools.context_graph import graph_path

    ws, _ = _make_ws(tmp_path)
    with _patch_registry(ws):
        result = await graph_path.ainvoke(
            {"source": "node_auth", "target": "node_token"}, config=_config("ws1")
        )
    assert "Caminho" in result or "→" in result


@pytest.mark.asyncio
async def test_graph_path_no_path(tmp_path):
    from backend.tools.context_graph import graph_path

    ws, graph_file = _make_ws(tmp_path)
    disconnected = {
        "nodes": [
            {"id": "a", "label": "A", "type": "class"},
            {"id": "b", "label": "B", "type": "class"},
        ],
        "edges": [],
    }
    graph_file.write_text(json.dumps(disconnected), encoding="utf-8")
    with _patch_registry(ws):
        result = await graph_path.ainvoke(
            {"source": "a", "target": "b"}, config=_config("ws1")
        )
    assert (
        "Caminho" in result
        or "não existe" in result.lower()
        or "não encontrado" in result.lower()
    )


@pytest.mark.asyncio
async def test_graph_path_nonexistent_node(tmp_path):
    from backend.tools.context_graph import graph_path

    ws, _ = _make_ws(tmp_path)
    with _patch_registry(ws):
        result = await graph_path.ainvoke(
            {"source": "node_auth", "target": "NOTANODE999"}, config=_config("ws1")
        )
    assert "não encontrado" in result.lower() or "not found" in result.lower()


# ---------------------------------------------------------------------------
# build_knowledge_graph — sem workspace ativo
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_knowledge_graph_no_workspace():
    from backend.tools.context_graph import build_knowledge_graph

    result = await build_knowledge_graph.ainvoke(
        {}, config=cast("RunnableConfig", {"configurable": {}})
    )
    assert "Erro" in result or "workspace" in result.lower()


@pytest.mark.asyncio
async def test_build_knowledge_graph_success(tmp_path):
    from backend.tools.context_graph import build_knowledge_graph

    ws, _ = _make_ws(tmp_path)
    result_mock = MagicMock()
    result_mock.error = None
    result_mock.node_count = 10
    result_mock.edge_count = 15
    result_mock.god_nodes = ["AuthService"]
    result_mock.suggested_questions = ["What does AuthService do?"]
    result_mock.report_path = tmp_path / "report.md"
    with (
        _patch_registry(ws),
        patch(
            "backend.services.context_graph.pipeline.build_workspace_graph",
            new_callable=AsyncMock,
            return_value=result_mock,
        ),
    ):
        result = await build_knowledge_graph.ainvoke(
            {"model": "", "mode": "semantic"}, config=_config("ws1")
        )
    assert "10" in result
    assert "15" in result


# ---------------------------------------------------------------------------
# graph_affected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graph_affected_seed_not_found(tmp_path):
    from backend.tools.context_graph import graph_affected

    ws, _ = _make_ws(tmp_path)
    with _patch_registry(ws):
        result = await graph_affected.ainvoke(
            {"node_query": "xyz_nonexistent_99"}, config=_config("ws1")
        )
    assert len(result) > 0


@pytest.mark.asyncio
async def test_graph_affected_seed_found(tmp_path):
    from backend.tools.context_graph import graph_affected

    ws, _ = _make_ws(tmp_path)
    with _patch_registry(ws):
        result = await graph_affected.ainvoke(
            {"node_query": "node_token"}, config=_config("ws1")
        )
    assert len(result) > 0


# ---------------------------------------------------------------------------
# graph_update — rebuild incremental
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graph_update_calls_pipeline_with_update_true(tmp_path):
    from backend.tools.context_graph import graph_update

    ws, _ = _make_ws(tmp_path)
    result_mock = MagicMock()
    result_mock.error = None
    result_mock.node_count = 5
    result_mock.edge_count = 8
    result_mock.god_nodes = []
    result_mock.suggested_questions = []
    result_mock.report_path = tmp_path / "report.md"
    with (
        _patch_registry(ws),
        patch(
            "backend.services.context_graph.pipeline.build_workspace_graph",
            new_callable=AsyncMock,
            return_value=result_mock,
        ) as mock_build,
    ):
        result = await graph_update.ainvoke({"model": ""}, config=_config("ws1"))
    mock_build.assert_called_once()
    assert mock_build.call_args.kwargs.get("update") is True
    assert "5" in result or "atualizado" in result.lower()
