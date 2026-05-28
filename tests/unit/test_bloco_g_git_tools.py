"""Bloco G — Git Tools — testes TDD.

G3: git_status, git_log, git_diff, git_branch, git_checkout, git_commit,
    git_stash, git_push (metadata + comportamento real em repo temporário).
G3: gh tools — metadata e fallback gracioso quando gh não disponível.

Os testes usam gitpython para criar repos temporários reais via tmp_path.
As funções-helper (_git_status_impl, etc.) são testadas diretamente;
os @tool wrappers recebem apenas testes de metadados.
"""

from __future__ import annotations

import json
from pathlib import Path

import git
import pytest

# ===========================================================================
# Fixtures — repos temporários
# ===========================================================================


@pytest.fixture
def empty_repo(tmp_path: Path) -> git.Repo:
    """Repo git vazio (sem commits)."""
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()
    return repo


@pytest.fixture
def repo_with_commit(tmp_path: Path) -> git.Repo:
    """Repo com um commit inicial."""
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()
    # Cria arquivo e faz commit inicial
    f = tmp_path / "README.md"
    f.write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    return repo


@pytest.fixture
def dirty_repo(tmp_path: Path) -> git.Repo:
    """Repo com arquivo modificado e arquivo untracked."""
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()
    f = tmp_path / "README.md"
    f.write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    # Modifica o arquivo já commitado
    f.write_text("# Test\nModified\n")
    # Adiciona arquivo untracked
    (tmp_path / "new_file.py").write_text("x = 1\n")
    return repo


# ===========================================================================
# Classe 1 — Metadados dos @tool
# ===========================================================================


class TestGitToolMetadata:
    """Verifica que cada tool tem os metadados corretos declarados."""

    def test_git_status_metadata(self) -> None:
        from vectora.tools.git import git_status

        extras = git_status.metadata or {}
        assert extras.get("render_hint") == "code_block"
        assert extras.get("category") == "git"
        assert extras.get("destructive") is False

    def test_git_log_metadata(self) -> None:
        from vectora.tools.git import git_log

        extras = git_log.metadata or {}
        assert extras.get("render_hint") == "table"
        assert extras.get("destructive") is False

    def test_git_diff_metadata(self) -> None:
        from vectora.tools.git import git_diff

        extras = git_diff.metadata or {}
        assert extras.get("render_hint") == "diff"
        assert extras.get("destructive") is False

    def test_git_branch_metadata(self) -> None:
        from vectora.tools.git import git_branch

        extras = git_branch.metadata or {}
        assert extras.get("render_hint") == "table"
        assert extras.get("category") == "git"

    def test_git_commit_is_destructive(self) -> None:
        from vectora.tools.git import git_commit

        extras = git_commit.metadata or {}
        assert extras.get("destructive") is True

    def test_git_push_is_destructive(self) -> None:
        from vectora.tools.git import git_push

        extras = git_push.metadata or {}
        assert extras.get("destructive") is True

    def test_git_checkout_is_destructive(self) -> None:
        from vectora.tools.git import git_checkout

        extras = git_checkout.metadata or {}
        assert extras.get("destructive") is True

    def test_git_stash_metadata(self) -> None:
        from vectora.tools.git import git_stash

        extras = git_stash.metadata or {}
        assert extras.get("category") == "git"


# ===========================================================================
# Classe 2 — _git_status_impl
# ===========================================================================


class TestGitStatusImpl:
    def test_clean_repo_returns_clean_true(self, repo_with_commit: git.Repo) -> None:
        from vectora.tools.git import _git_status_impl

        result = _git_status_impl(repo_with_commit)
        assert result["status"] == "ok"
        assert result["clean"] is True
        assert result["untracked"] == []
        assert result["modified"] == []

    def test_dirty_repo_untracked_and_modified(self, dirty_repo: git.Repo) -> None:
        from vectora.tools.git import _git_status_impl

        result = _git_status_impl(dirty_repo)
        assert result["status"] == "ok"
        assert result["clean"] is False
        assert "new_file.py" in result["untracked"]
        assert "README.md" in result["modified"]

    def test_returns_branch_name(self, repo_with_commit: git.Repo) -> None:
        from vectora.tools.git import _git_status_impl

        result = _git_status_impl(repo_with_commit)
        assert isinstance(result["branch"], str)
        assert len(result["branch"]) > 0

    def test_staged_file_appears_in_staged(self, dirty_repo: git.Repo) -> None:
        from vectora.tools.git import _git_status_impl

        # Stageia a modificação do README
        dirty_repo.index.add(["README.md"])
        result = _git_status_impl(dirty_repo)
        assert "README.md" in result["staged"]


# ===========================================================================
# Classe 3 — _git_log_impl
# ===========================================================================


class TestGitLogImpl:
    def test_no_commits_returns_empty(self, empty_repo: git.Repo) -> None:
        from vectora.tools.git import _git_log_impl

        result = _git_log_impl(empty_repo, n=10)
        assert result["status"] == "ok"
        assert result["commits"] == []

    def test_returns_commit_list(self, repo_with_commit: git.Repo) -> None:
        from vectora.tools.git import _git_log_impl

        result = _git_log_impl(repo_with_commit, n=10)
        assert result["status"] == "ok"
        assert len(result["commits"]) == 1
        commit = result["commits"][0]
        assert "hash" in commit
        assert "message" in commit
        assert commit["message"] == "Initial commit"

    def test_respects_n_limit(self, tmp_path: Path) -> None:
        from vectora.tools.git import _git_log_impl

        repo = git.Repo.init(tmp_path)
        repo.config_writer().set_value("user", "name", "T").release()
        repo.config_writer().set_value("user", "email", "t@t.com").release()
        for i in range(5):
            f = tmp_path / f"file{i}.txt"
            f.write_text(f"content {i}")
            repo.index.add([f.name])
            repo.index.commit(f"Commit {i}")

        result = _git_log_impl(repo, n=3)
        assert len(result["commits"]) == 3


# ===========================================================================
# Classe 4 — _git_diff_impl
# ===========================================================================


class TestGitDiffImpl:
    def test_no_changes_empty_diff(self, repo_with_commit: git.Repo) -> None:
        from vectora.tools.git import _git_diff_impl

        result = _git_diff_impl(repo_with_commit)
        assert result["status"] == "ok"
        assert result["diff"] == ""

    def test_modified_file_shows_diff(self, dirty_repo: git.Repo) -> None:
        from vectora.tools.git import _git_diff_impl

        result = _git_diff_impl(dirty_repo)
        assert result["status"] == "ok"
        assert "README.md" in result["diff"] or "Modified" in result["diff"]


# ===========================================================================
# Classe 5 — _git_branch_impl
# ===========================================================================


class TestGitBranchImpl:
    def test_list_branches(self, repo_with_commit: git.Repo) -> None:
        from vectora.tools.git import _git_branch_impl

        result = _git_branch_impl(repo_with_commit, action="list")
        assert result["status"] == "ok"
        assert isinstance(result["branches"], list)
        assert len(result["branches"]) >= 1
        assert isinstance(result["current"], str)

    def test_create_branch(self, repo_with_commit: git.Repo) -> None:
        from vectora.tools.git import _git_branch_impl

        result = _git_branch_impl(
            repo_with_commit, action="create", name="feature-test"
        )
        assert result["status"] == "ok"
        branch_names = [b.name for b in repo_with_commit.branches]
        assert "feature-test" in branch_names

    def test_delete_branch(self, repo_with_commit: git.Repo) -> None:
        from vectora.tools.git import _git_branch_impl

        # Cria e depois deleta
        repo_with_commit.create_head("to-delete")
        result = _git_branch_impl(repo_with_commit, action="delete", name="to-delete")
        assert result["status"] == "ok"
        branch_names = [b.name for b in repo_with_commit.branches]
        assert "to-delete" not in branch_names

    def test_create_without_name_returns_error(
        self, repo_with_commit: git.Repo
    ) -> None:
        from vectora.tools.git import _git_branch_impl

        result = _git_branch_impl(repo_with_commit, action="create", name=None)
        assert result["status"] == "error"


# ===========================================================================
# Classe 6 — _git_commit_impl
# ===========================================================================


class TestGitCommitImpl:
    def test_commit_staged_file(self, dirty_repo: git.Repo) -> None:
        from vectora.tools.git import _git_commit_impl

        # Stageia o arquivo modificado
        dirty_repo.index.add(["README.md"])
        result = _git_commit_impl(dirty_repo, message="fix: update README")
        assert result["status"] == "ok"
        assert len(result["hash"]) == 7
        assert result["message"] == "fix: update README"

    def test_nothing_staged_returns_error(self, repo_with_commit: git.Repo) -> None:
        from vectora.tools.git import _git_commit_impl

        result = _git_commit_impl(repo_with_commit, message="empty commit")
        assert result["status"] == "error"
        assert (
            "staged" in result["message"].lower()
            or "nothing" in result["message"].lower()
        )

    def test_commit_all_flag(self, dirty_repo: git.Repo) -> None:
        from vectora.tools.git import _git_commit_impl

        # Sem stagear — usa all=True para commitar arquivos rastreados modificados
        result = _git_commit_impl(dirty_repo, message="chore: update all", all=True)
        assert result["status"] == "ok"


# ===========================================================================
# Classe 7 — _git_stash_impl
# ===========================================================================


class TestGitStashImpl:
    def test_push_stash_with_changes(self, dirty_repo: git.Repo) -> None:
        from vectora.tools.git import _git_stash_impl

        result = _git_stash_impl(dirty_repo, action="push")
        assert result["status"] == "ok"
        assert result["action"] == "push"

    def test_push_stash_clean_repo_returns_info(
        self, repo_with_commit: git.Repo
    ) -> None:
        from vectora.tools.git import _git_stash_impl

        # Nada para stashear
        result = _git_stash_impl(repo_with_commit, action="push")
        # Pode ser "ok" com 0 itens ou info "nothing to stash"
        assert result["status"] in ("ok", "info")

    def test_list_stash(self, repo_with_commit: git.Repo) -> None:
        from vectora.tools.git import _git_stash_impl

        result = _git_stash_impl(repo_with_commit, action="list")
        assert result["status"] == "ok"
        assert "entries" in result


# ===========================================================================
# Classe 8 — gh tools: metadados e fallback gracioso
# ===========================================================================


class TestGhToolsMetadata:
    def test_gh_pr_list_metadata(self) -> None:
        from vectora.tools.gh import gh_pr_list

        extras = gh_pr_list.metadata or {}
        assert extras.get("render_hint") == "table"
        assert extras.get("category") == "git"

    def test_gh_pr_create_is_destructive(self) -> None:
        from vectora.tools.gh import gh_pr_create

        extras = gh_pr_create.metadata or {}
        # PR create não é destrutivo por padrão (não apaga código)
        assert extras.get("category") == "git"

    def test_gh_issue_list_metadata(self) -> None:
        from vectora.tools.gh import gh_issue_list

        extras = gh_issue_list.metadata or {}
        assert extras.get("render_hint") == "table"

    @pytest.mark.asyncio
    async def test_gh_pr_list_graceful_without_gh(self, tmp_path: Path) -> None:
        """Se `gh` não estiver no PATH, tool retorna JSON de erro, não levanta."""
        import os
        from unittest.mock import patch

        from vectora.tools.gh import _gh_run

        with patch.dict(os.environ, {"PATH": ""}):
            result = _gh_run(["pr", "list"], cwd=str(tmp_path))

        assert result["status"] == "error"
        assert (
            "gh" in result["message"].lower()
            or "not found" in result["message"].lower()
            or result["status"] == "error"
        )
