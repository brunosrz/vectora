"""Tests do Bloco Q backend — workspace trust, git init, worktree e handlers.

Cobre lacunas de teste:
    Q2 — trust/is_trusted no WorkspaceRegistry
    Q3 — git_init_repo (idempotente)
    Q5 — git_worktree (add/list/remove)
    Q1 — handlers do WorkspaceService (Browse/Create/Trust/SetActive)

O registry é isolado do disco via instância fresca com _save no-op; as operações
git rodam em repositórios temporários e worktrees redirecionadas para tmp_path.
"""

from __future__ import annotations

from types import SimpleNamespace

import git
import pytest

from vectora.services.workspace import WorkspaceRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def reg(monkeypatch):
    """Registry isolado: não toca ~/.vectora/workspaces.json."""
    r = WorkspaceRegistry()
    r._loaded = True
    monkeypatch.setattr(r, "_save", lambda: None)
    monkeypatch.setattr("vectora.services.workspace.workspace_registry", r)
    return r


def _req(user=None):
    """Request fake com .state.user, suficiente para os handlers."""
    return SimpleNamespace(state=SimpleNamespace(user=user))


# ---------------------------------------------------------------------------
# Q2 — trust no registry
# ---------------------------------------------------------------------------


class TestTrust:
    def test_added_folder_starts_untrusted(self, reg, tmp_path):
        # Pasta diferente do cwd do processo → não confiada por padrão
        sub = tmp_path / "sub"
        sub.mkdir()
        ws = reg.get_or_create(str(sub))
        assert ws.trusted is False

    def test_trust_marks_trusted(self, reg, tmp_path):
        ws = reg.get_or_create(str(tmp_path))
        assert reg.trust(ws.id, "user1") is True
        assert reg.get(ws.id).trusted is True
        assert reg.get(ws.id).trusted_by == "user1"
        assert reg.get(ws.id).trusted_at is not None

    def test_trust_unknown_returns_false(self, reg):
        assert reg.trust("naoexiste", "user1") is False

    def test_is_trusted(self, reg, tmp_path):
        ws = reg.get_or_create(str(tmp_path))
        assert reg.is_trusted(ws.id) is False
        reg.trust(ws.id)
        assert reg.is_trusted(ws.id) is True

    def test_create_with_trust(self, reg, tmp_path):
        ws = reg.create(str(tmp_path), trust=True, user_id="u")
        assert ws.trusted is True


class TestSessionWorkspace:
    def test_creates_folder_under_documents(self, reg, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "vectora.services.workspace._session_workspaces_root",
            lambda: tmp_path / "docs",
        )
        ws = reg.get_or_create_session_workspace("thread123", "u")
        assert (tmp_path / "docs" / "thread123").is_dir()
        assert ws.cwd.endswith("thread123")

    def test_session_workspace_is_trusted(self, reg, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "vectora.services.workspace._session_workspaces_root",
            lambda: tmp_path / "docs",
        )
        ws = reg.get_or_create_session_workspace("thread123", "u")
        assert ws.trusted is True

    def test_session_workspace_is_idempotent(self, reg, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "vectora.services.workspace._session_workspaces_root",
            lambda: tmp_path / "docs",
        )
        a = reg.get_or_create_session_workspace("thread123")
        b = reg.get_or_create_session_workspace("thread123")
        assert a.id == b.id


# ---------------------------------------------------------------------------
# Q3 — git_init_repo
# ---------------------------------------------------------------------------


class TestGitInit:
    def test_init_empty_dir(self, tmp_path):
        from vectora.tools.git import git_init_repo

        result = git_init_repo(str(tmp_path))
        assert result["status"] == "ok"
        assert (tmp_path / ".git").exists()

    def test_init_is_idempotent(self, tmp_path):
        from vectora.tools.git import git_init_repo

        git_init_repo(str(tmp_path))
        again = git_init_repo(str(tmp_path))
        assert again["status"] == "already"

    def test_detect_reflects_init(self, tmp_path):
        from vectora.tools.git import detect_git_info, git_init_repo

        assert detect_git_info(str(tmp_path)).get("is_git_repo") is False
        git_init_repo(str(tmp_path))
        assert detect_git_info(str(tmp_path)).get("is_git_repo") is True


# ---------------------------------------------------------------------------
# Q5 — git_worktree
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_with_commit(tmp_path, monkeypatch):
    """Repo git temporário com um commit + worktrees redirecionadas a tmp_path."""
    repo = git.Repo.init(tmp_path)
    cw = repo.config_writer()
    cw.set_value("user", "name", "Test")
    cw.set_value("user", "email", "test@example.com")
    cw.release()
    (tmp_path / "file.txt").write_text("hello", encoding="utf-8")
    repo.index.add(["file.txt"])
    repo.index.commit("init")

    monkeypatch.setattr(
        "vectora.tools.git._worktrees_root",
        lambda wid: tmp_path / "_wt" / wid,
    )
    return repo


class TestWorktree:
    def test_add_creates_worktree(self, repo_with_commit):
        from vectora.tools.git import _git_worktree_impl

        result = _git_worktree_impl(
            repo_with_commit, "ws1", action="add", name="feat-x", branch="feat-x"
        )
        assert result["status"] == "ok"
        assert result["name"] == "feat-x"

    def test_list_includes_added_worktree(self, repo_with_commit):
        from vectora.tools.git import _git_worktree_impl

        _git_worktree_impl(
            repo_with_commit, "ws1", action="add", name="feat-y", branch="feat-y"
        )
        listed = _git_worktree_impl(repo_with_commit, "ws1", action="list")
        assert listed["status"] == "ok"
        paths = " ".join(w.get("path", "") for w in listed["worktrees"])
        assert "feat-y" in paths

    def test_add_without_name_errors(self, repo_with_commit):
        from vectora.tools.git import _git_worktree_impl

        result = _git_worktree_impl(repo_with_commit, "ws1", action="add")
        assert result["status"] == "error"

    def test_unknown_action_errors(self, repo_with_commit):
        from vectora.tools.git import _git_worktree_impl

        result = _git_worktree_impl(repo_with_commit, "ws1", action="bogus")
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Q1 — handlers do WorkspaceService
# ---------------------------------------------------------------------------


class TestWorkspaceHandlers:
    @pytest.mark.asyncio
    async def test_create_then_list(self, reg, tmp_path):
        from vectora.api.handlers.workspaces import (
            CreateWorkspaceRequest,
            create_workspace,
            list_workspaces,
        )

        body = CreateWorkspaceRequest(path=str(tmp_path), trust=True)
        created = await create_workspace(_req(), body)
        assert created.status == "ok"
        assert created.workspace is not None
        assert created.workspace.trusted is True

        listing = await list_workspaces(_req())
        ids = {w.id for w in listing.workspaces}
        assert created.workspace.id in ids
        assert listing.active_id == created.workspace.id

    @pytest.mark.asyncio
    async def test_create_nonexistent_path(self, reg, tmp_path):
        from vectora.api.handlers.workspaces import (
            CreateWorkspaceRequest,
            create_workspace,
        )

        body = CreateWorkspaceRequest(path=str(tmp_path / "nao_existe"))
        result = await create_workspace(_req(), body)
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_trust_handler(self, reg, tmp_path):
        from vectora.api.handlers.workspaces import (
            TrustRequest,
            trust_workspace,
        )

        ws = reg.get_or_create(str(tmp_path))
        result = await trust_workspace(_req(), TrustRequest(workspace_id=ws.id))
        assert result.status == "ok"
        assert result.workspace is not None
        assert result.workspace.trusted is True

    @pytest.mark.asyncio
    async def test_set_active_unknown(self, reg):
        from vectora.api.handlers.workspaces import (
            SetActiveRequest,
            set_active_workspace,
        )

        result = await set_active_workspace(
            _req(), SetActiveRequest(workspace_id="naoexiste")
        )
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_browse_lists_subdirs(self, tmp_path):
        from vectora.api.handlers.workspaces import browse_dir

        (tmp_path / "alpha").mkdir()
        (tmp_path / "beta").mkdir()
        (tmp_path / "file.txt").write_text("x", encoding="utf-8")

        result = await browse_dir(path=str(tmp_path))
        names = {e.name for e in result.entries}
        assert "alpha" in names
        assert "beta" in names
        # Arquivos não entram — só diretórios
        assert "file.txt" not in names
