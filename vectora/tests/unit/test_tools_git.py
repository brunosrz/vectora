"""Testes para git_stage / git_unstage e metadados de invalidação das tools git."""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.tools.git import git_stage, git_unstage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ws(tmp_path, monkeypatch):
    """Workspace fake apontando para tmp_path com repo git inicializado."""
    from backend.services import workspace as ws_mod
    from backend.vtypes import Workspace

    ws = Workspace(
        id="ws-git",
        name="ws-git",
        cwd=str(tmp_path),
        created_at="2024-01-01T00:00:00+00:00",
        trusted=True,
    )
    monkeypatch.setattr(
        ws_mod.workspace_registry,
        "get",
        lambda wid: ws if wid == "ws-git" else None,
    )
    return ws


def _make_config(ws_id: str) -> Any:
    return {"configurable": {"workspace_id": ws_id, "thread_id": "t1"}}


# ---------------------------------------------------------------------------
# git_stage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_git_stage_ok(mock_ws):
    """Stageia arquivo existente com sucesso."""
    mock_repo = MagicMock()
    with patch("backend.tools.git.git.Repo", return_value=mock_repo):
        result_raw = await git_stage.ainvoke(
            {"path": "src/main.py", "workspace_id": mock_ws.id},
            config=_make_config(mock_ws.id),
        )
    result = json.loads(result_raw)
    assert result["status"] == "ok"
    assert result["action"] == "stage"
    assert result["path"] == "src/main.py"
    mock_repo.git.add.assert_called_once_with("--", "src/main.py")


@pytest.mark.asyncio
async def test_git_stage_path_vazio(mock_ws):
    """Path vazio deve retornar erro, não propagar exceção."""
    mock_repo = MagicMock()
    with patch("backend.tools.git.git.Repo", return_value=mock_repo):
        result_raw = await git_stage.ainvoke(
            {"path": "", "workspace_id": mock_ws.id},
            config=_make_config(mock_ws.id),
        )
    result = json.loads(result_raw)
    assert result["status"] == "error"
    mock_repo.git.add.assert_not_called()


@pytest.mark.asyncio
async def test_git_stage_git_error(mock_ws):
    """GitCommandError vira resposta de erro, não exceção."""
    import git as gitpy

    mock_repo = MagicMock()
    mock_repo.git.add.side_effect = gitpy.GitCommandError("add", 128)
    with patch("backend.tools.git.git.Repo", return_value=mock_repo):
        result_raw = await git_stage.ainvoke(
            {"path": "missing.py", "workspace_id": mock_ws.id},
            config=_make_config(mock_ws.id),
        )
    result = json.loads(result_raw)
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# git_unstage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_git_unstage_ok(mock_ws):
    """Remove arquivo do stage com sucesso."""
    mock_repo = MagicMock()
    with patch("backend.tools.git.git.Repo", return_value=mock_repo):
        result_raw = await git_unstage.ainvoke(
            {"path": "src/main.py", "workspace_id": mock_ws.id},
            config=_make_config(mock_ws.id),
        )
    result = json.loads(result_raw)
    assert result["status"] == "ok"
    assert result["action"] == "unstage"
    mock_repo.git.reset.assert_called_once_with("HEAD", "--", "src/main.py")


@pytest.mark.asyncio
async def test_git_unstage_path_vazio(mock_ws):
    """Path vazio retorna erro estruturado."""
    mock_repo = MagicMock()
    with patch("backend.tools.git.git.Repo", return_value=mock_repo):
        result_raw = await git_unstage.ainvoke(
            {"path": "", "workspace_id": mock_ws.id},
            config=_make_config(mock_ws.id),
        )
    result = json.loads(result_raw)
    assert result["status"] == "error"
    mock_repo.git.reset.assert_not_called()


@pytest.mark.asyncio
async def test_git_unstage_git_error(mock_ws):
    """GitCommandError vira resposta de erro."""
    import git as gitpy

    mock_repo = MagicMock()
    mock_repo.git.reset.side_effect = gitpy.GitCommandError("reset", 128)
    with patch("backend.tools.git.git.Repo", return_value=mock_repo):
        result_raw = await git_unstage.ainvoke(
            {"path": "staged.py", "workspace_id": mock_ws.id},
            config=_make_config(mock_ws.id),
        )
    result = json.loads(result_raw)
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Metadados de invalidação (contrato "invalidates")
# ---------------------------------------------------------------------------


def test_git_stage_tem_invalidates_diff():
    meta = git_stage.extras or git_stage.metadata or {}
    assert "diff" in meta.get("invalidates", [])


def test_git_unstage_tem_invalidates_diff():
    meta = git_unstage.extras or git_unstage.metadata or {}
    assert "diff" in meta.get("invalidates", [])


def test_git_commit_tem_invalidates_diff():
    from backend.tools.git import git_commit

    meta = git_commit.extras or git_commit.metadata or {}
    assert "diff" in meta.get("invalidates", [])


def test_git_checkout_tem_invalidates_files_e_diff():
    from backend.tools.git import git_checkout

    meta = git_checkout.extras or git_checkout.metadata or {}
    tabs = meta.get("invalidates", [])
    assert "diff" in tabs
    assert "files" in tabs


def test_git_pull_tem_invalidates_files_e_diff():
    from backend.tools.git import git_pull

    meta = git_pull.extras or git_pull.metadata or {}
    tabs = meta.get("invalidates", [])
    assert "diff" in tabs
    assert "files" in tabs
