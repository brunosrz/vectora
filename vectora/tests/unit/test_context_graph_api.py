"""Testes para backend/api/handlers/context_graph.py.

Cobre helpers (_graph_dir, _status_from_disk, _require_graph_json) e
os endpoints assíncronos (query, explain, path, status) via chamada direta
das funções com request mockado — sem TestClient para evitar dependência de
toda a stack FastAPI.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_registry(tmp_path: Path) -> tuple[MagicMock, MagicMock]:
    ws = MagicMock()
    ws.cwd = str(tmp_path)
    registry = MagicMock()
    registry.get = MagicMock(return_value=ws)
    return registry, ws


def _write_graph(tmp_path: Path, data: dict) -> Path:
    d = tmp_path / ".vectora" / "graph"
    d.mkdir(parents=True, exist_ok=True)
    (d / "graph.json").write_text(json.dumps(data), encoding="utf-8")
    return d


def _fake_request(user_id: str = "u1") -> MagicMock:
    req = MagicMock()
    req.state.user = MagicMock()
    req.state.user.id = user_id
    return req


# ---------------------------------------------------------------------------
# _graph_dir
# ---------------------------------------------------------------------------


class TestGraphDir:
    def test_workspace_not_found_returns_none(self):
        from backend.api.handlers.context_graph import _graph_dir

        registry = MagicMock()
        registry.get = MagicMock(return_value=None)
        with patch("backend.services.workspace.workspace_registry", registry):
            assert _graph_dir("nonexistent") is None

    def test_workspace_found_returns_expected_path(self, tmp_path):
        from backend.api.handlers.context_graph import _graph_dir

        registry, _ = _make_registry(tmp_path)
        with patch("backend.services.workspace.workspace_registry", registry):
            result = _graph_dir("ws1")
        assert result == tmp_path / ".vectora" / "graph"


# ---------------------------------------------------------------------------
# _status_from_disk
# ---------------------------------------------------------------------------


class TestStatusFromDisk:
    def test_not_built_when_graph_json_absent(self, tmp_path):
        from backend.api.handlers.context_graph import _status_from_disk

        registry, _ = _make_registry(tmp_path)
        with patch("backend.services.workspace.workspace_registry", registry):
            s = _status_from_disk("ws1")
        assert s.status == "not_built"

    def test_done_counts_nodes_and_edges(self, tmp_path):
        from backend.api.handlers.context_graph import _status_from_disk

        _write_graph(
            tmp_path,
            {
                "nodes": [{"id": "a"}, {"id": "b"}],
                "edges": [{"source": "a", "target": "b"}],
            },
        )
        registry, _ = _make_registry(tmp_path)
        with patch("backend.services.workspace.workspace_registry", registry):
            s = _status_from_disk("ws1")
        assert s.status == "done"
        assert s.node_count == 2
        assert s.edge_count == 1

    def test_workspace_missing_raises_404(self):
        from fastapi import HTTPException

        from backend.api.handlers.context_graph import _status_from_disk

        registry = MagicMock()
        registry.get = MagicMock(return_value=None)
        with patch("backend.services.workspace.workspace_registry", registry):
            with pytest.raises(HTTPException) as exc:
                _status_from_disk("no-ws")
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# _require_graph_json
# ---------------------------------------------------------------------------


class TestRequireGraphJson:
    def test_raises_404_when_file_missing(self, tmp_path):
        from fastapi import HTTPException

        from backend.api.handlers.context_graph import _require_graph_json

        registry, _ = _make_registry(tmp_path)
        with patch("backend.services.workspace.workspace_registry", registry):
            with pytest.raises(HTTPException) as exc:
                _require_graph_json("ws1")
        assert exc.value.status_code == 404

    def test_returns_parsed_data(self, tmp_path):
        from backend.api.handlers.context_graph import _require_graph_json

        _write_graph(tmp_path, {"nodes": [{"id": "x"}], "edges": []})
        registry, _ = _make_registry(tmp_path)
        with patch("backend.services.workspace.workspace_registry", registry):
            data = _require_graph_json("ws1")
        assert data["nodes"][0]["id"] == "x"


# ---------------------------------------------------------------------------
# get_status — leitura de _active_builds
# ---------------------------------------------------------------------------


class TestGetStatus:
    @pytest.mark.asyncio
    async def test_running_from_active_builds(self, tmp_path):
        from backend.api.handlers.context_graph import _active_builds, get_status

        registry, _ = _make_registry(tmp_path)
        _active_builds["__test_running__"] = "running"
        with patch("backend.services.workspace.workspace_registry", registry):
            s = await get_status(_fake_request(), "__test_running__")
        del _active_builds["__test_running__"]
        assert s.status == "running"

    @pytest.mark.asyncio
    async def test_error_from_active_builds(self, tmp_path):
        from backend.api.handlers.context_graph import _active_builds, get_status

        registry, _ = _make_registry(tmp_path)
        _active_builds["__test_err__"] = "error:Pipeline falhou"
        with patch("backend.services.workspace.workspace_registry", registry):
            s = await get_status(_fake_request(), "__test_err__")
        del _active_builds["__test_err__"]
        assert s.status == "error"
        assert "Pipeline falhou" in (s.error or "")

    @pytest.mark.asyncio
    async def test_done_parses_counts(self, tmp_path):
        from backend.api.handlers.context_graph import _active_builds, get_status

        registry, _ = _make_registry(tmp_path)
        _active_builds["__test_done__"] = "done:10:25"
        with patch("backend.services.workspace.workspace_registry", registry):
            s = await get_status(_fake_request(), "__test_done__")
        del _active_builds["__test_done__"]
        assert s.status == "done"
        assert s.node_count == 10
        assert s.edge_count == 25

    @pytest.mark.asyncio
    async def test_falls_back_to_disk_when_not_in_builds(self, tmp_path):
        from backend.api.handlers.context_graph import _active_builds, get_status

        _active_builds.pop("__test_fallback__", None)
        _write_graph(
            tmp_path,
            {"nodes": [{"id": "a"}], "edges": []},
        )
        registry, _ = _make_registry(tmp_path)
        with patch("backend.services.workspace.workspace_registry", registry):
            s = await get_status(_fake_request(), "__test_fallback__")
        assert s.status == "done"


# ---------------------------------------------------------------------------
# post_query
# ---------------------------------------------------------------------------


SAMPLE_DATA = {
    "nodes": [
        {"id": "n_auth", "label": "AuthService", "type": "class"},
        {"id": "n_login", "label": "login", "type": "function"},
        {"id": "n_token", "label": "Token", "type": "class"},
    ],
    "edges": [
        {"source": "n_auth", "target": "n_login", "label": "calls"},
        {"source": "n_login", "target": "n_token", "label": "returns"},
    ],
}


class TestPostQuery:
    @pytest.mark.asyncio
    async def test_matches_by_label(self, tmp_path):
        from backend.api.handlers.context_graph import QueryRequest, post_query

        _write_graph(tmp_path, SAMPLE_DATA)
        registry, _ = _make_registry(tmp_path)
        with patch("backend.services.workspace.workspace_registry", registry):
            resp = await post_query(
                _fake_request(), "ws1", QueryRequest(question="auth")
            )
        assert any(n["id"] == "n_auth" for n in resp.nodes)
        assert "1" in resp.answer

    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self, tmp_path):
        from backend.api.handlers.context_graph import QueryRequest, post_query

        _write_graph(tmp_path, SAMPLE_DATA)
        registry, _ = _make_registry(tmp_path)
        with patch("backend.services.workspace.workspace_registry", registry):
            resp = await post_query(
                _fake_request(), "ws1", QueryRequest(question="zzznothingmatches")
            )
        assert resp.nodes == []

    @pytest.mark.asyncio
    async def test_includes_neighborhood_edges(self, tmp_path):
        from backend.api.handlers.context_graph import QueryRequest, post_query

        _write_graph(tmp_path, SAMPLE_DATA)
        registry, _ = _make_registry(tmp_path)
        with patch("backend.services.workspace.workspace_registry", registry):
            resp = await post_query(
                _fake_request(), "ws1", QueryRequest(question="auth", top_k=5)
            )
        assert len(resp.edges) >= 1


# ---------------------------------------------------------------------------
# post_explain
# ---------------------------------------------------------------------------


class TestPostExplain:
    @pytest.mark.asyncio
    async def test_returns_node_and_neighbors(self, tmp_path):
        from backend.api.handlers.context_graph import ExplainRequest, post_explain

        _write_graph(tmp_path, SAMPLE_DATA)
        registry, _ = _make_registry(tmp_path)
        with patch("backend.services.workspace.workspace_registry", registry):
            resp = await post_explain(
                _fake_request(), "ws1", ExplainRequest(node_id="n_auth")
            )
        ids = {n["id"] for n in resp.nodes}
        assert "n_auth" in ids
        assert "n_login" in ids

    @pytest.mark.asyncio
    async def test_raises_404_for_unknown_node(self, tmp_path):
        from fastapi import HTTPException

        from backend.api.handlers.context_graph import ExplainRequest, post_explain

        _write_graph(tmp_path, SAMPLE_DATA)
        registry, _ = _make_registry(tmp_path)
        with patch("backend.services.workspace.workspace_registry", registry):
            with pytest.raises(HTTPException) as exc:
                await post_explain(
                    _fake_request(), "ws1", ExplainRequest(node_id="ghost")
                )
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# post_path
# ---------------------------------------------------------------------------


class TestPostPath:
    @pytest.mark.asyncio
    async def test_returns_path_between_nodes(self, tmp_path):
        from backend.api.handlers.context_graph import PathRequest, post_path

        _write_graph(tmp_path, SAMPLE_DATA)
        registry, _ = _make_registry(tmp_path)
        with patch("backend.services.workspace.workspace_registry", registry):
            resp = await post_path(
                _fake_request(), "ws1", PathRequest(source="n_auth", target="n_token")
            )
        ids = {n["id"] for n in resp.nodes}
        assert "n_auth" in ids
        assert "n_token" in ids
        assert "n_auth" in resp.answer

    @pytest.mark.asyncio
    async def test_raises_404_when_no_path(self, tmp_path):
        from fastapi import HTTPException

        from backend.api.handlers.context_graph import PathRequest, post_path

        _write_graph(
            tmp_path,
            {
                "nodes": [{"id": "a"}, {"id": "b"}],
                "edges": [],
            },
        )
        registry, _ = _make_registry(tmp_path)
        with patch("backend.services.workspace.workspace_registry", registry):
            with pytest.raises(HTTPException) as exc:
                await post_path(
                    _fake_request(), "ws1", PathRequest(source="a", target="b")
                )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_404_for_unknown_source(self, tmp_path):
        from fastapi import HTTPException

        from backend.api.handlers.context_graph import PathRequest, post_path

        _write_graph(tmp_path, SAMPLE_DATA)
        registry, _ = _make_registry(tmp_path)
        with patch("backend.services.workspace.workspace_registry", registry):
            with pytest.raises(HTTPException) as exc:
                await post_path(
                    _fake_request(), "ws1", PathRequest(source="ghost", target="n_auth")
                )
        assert exc.value.status_code == 404
