"""Delegate — worktree isolado por task (Sprint 12).

create_task_worktree/remove_task_worktree reaproveitam _git_worktree_impl
já usado pela tool git_worktree — aqui só cobrimos o wrapper: resolução do
workspace, propagação de erro claro, e idempotência da remoção.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.scheduling.delegate import (
    DelegateError,
    create_task_worktree,
    remove_task_worktree,
)


def _fake_workspace(cwd: str = "/tmp/ws1"):
    ws = MagicMock()
    ws.cwd = cwd
    return ws


@pytest.mark.asyncio
async def test_create_task_worktree_returns_path_on_success():
    with (
        patch("backend.workspace.workspace.workspace_registry") as mock_registry,
        patch("git.Repo") as mock_repo_cls,
        patch("backend.tools.git._git_worktree_impl") as mock_impl,
    ):
        mock_registry.get.return_value = _fake_workspace()
        mock_repo_cls.return_value = MagicMock()
        mock_impl.return_value = {
            "status": "ok",
            "action": "add",
            "path": "/home/user/.vectora/worktrees/ws1/task-42",
        }

        path = await create_task_worktree("ws1", "task-42")

        assert path == "/home/user/.vectora/worktrees/ws1/task-42"
        mock_impl.assert_called_once()
        assert mock_impl.call_args.args[2] == "add"
        assert mock_impl.call_args.kwargs["name"] == "task-42"


@pytest.mark.asyncio
async def test_create_task_worktree_unknown_workspace_raises_clear_error():
    with patch("backend.workspace.workspace.workspace_registry") as mock_registry:
        mock_registry.get.return_value = None

        with pytest.raises(DelegateError, match="não encontrado"):
            await create_task_worktree("ghost-ws", "task-1")


@pytest.mark.asyncio
async def test_create_task_worktree_git_failure_raises_delegate_error():
    # Erro/borda: branch inválida/disco cheio não deixa a task presa num
    # estado inconsistente — propaga como DelegateError com mensagem clara.
    with (
        patch("backend.workspace.workspace.workspace_registry") as mock_registry,
        patch("git.Repo") as mock_repo_cls,
        patch("backend.tools.git._git_worktree_impl") as mock_impl,
    ):
        mock_registry.get.return_value = _fake_workspace()
        mock_repo_cls.return_value = MagicMock()
        mock_impl.return_value = {"status": "error", "message": "disk full"}

        with pytest.raises(DelegateError, match="disk full"):
            await create_task_worktree("ws1", "task-42")


@pytest.mark.asyncio
async def test_remove_task_worktree_is_idempotent_on_missing_worktree():
    # Erro/borda: remover um worktree que já não existe (ou nunca existiu)
    # não levanta exceção — só loga e segue.
    with (
        patch("backend.workspace.workspace.workspace_registry") as mock_registry,
        patch("git.Repo") as mock_repo_cls,
        patch("backend.tools.git._git_worktree_impl") as mock_impl,
    ):
        mock_registry.get.return_value = _fake_workspace()
        mock_repo_cls.return_value = MagicMock()
        mock_impl.return_value = {"status": "error", "message": "not found"}

        await remove_task_worktree("ws1", "task-42")  # não deve levantar


@pytest.mark.asyncio
async def test_workspace_without_git_repo_raises_delegate_error():
    with (
        patch("backend.workspace.workspace.workspace_registry") as mock_registry,
        patch("git.Repo", side_effect=Exception("not a git repository")),
    ):
        mock_registry.get.return_value = _fake_workspace()

        with pytest.raises(DelegateError, match="não é um repositório git"):
            await create_task_worktree("ws1", "task-42")
