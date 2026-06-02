"""Tests para o view_router de src/api/handlers/workspaces.py.

Cobre os endpoints adicionados em T6/T7 (Workbench):
- GET /workspaces/{id}/tree            — lista dirs/files filtrando ruído.
- GET /workspaces/{id}/file            — texto truncado, detecção de binário.
- GET /workspaces/{id}/git/diff        — resumo (vazio em pastas não-git).
- GET /workspaces/{id}/git/diff/file   — hunks (vazio quando sem mudanças).

Os endpoints reusam ``services.security.resolve_within_workspace`` (Q4),
então qualquer path fora do workspace devolve resposta vazia em vez de
listar/ler.
"""

from __future__ import annotations

import pytest

from src.types import Workspace

# ---------------------------------------------------------------------------
# Fixture — workspace confiável apontando para tmp_path
# ---------------------------------------------------------------------------


@pytest.fixture
def trusted_ws(tmp_path, monkeypatch):
    """Registra um workspace confiável em tmp_path no registry.

    Devolve uma tupla ``(workspace_id, tmp_path)`` para os testes montarem
    arquivos dentro de tmp_path e chamarem os endpoints com o id certo.
    """
    from src.services import workspace as ws_mod

    ws = Workspace(
        id="vws",
        name="vws",
        cwd=str(tmp_path),
        created_at="2024-01-01T00:00:00+00:00",
        trusted=True,
    )
    monkeypatch.setattr(
        ws_mod.workspace_registry,
        "get",
        lambda wid: ws if wid == "vws" else None,
    )
    return "vws", tmp_path


# ---------------------------------------------------------------------------
# /workspaces/{id}/tree
# ---------------------------------------------------------------------------


class TestWorkspaceTree:
    @pytest.mark.asyncio
    async def test_lists_root_when_path_empty(self, trusted_ws):
        from src.api.handlers.workspaces import workspace_tree

        wsid, root = trusted_ws
        (root / "a.txt").write_text("a", encoding="utf-8")
        (root / "sub").mkdir()

        resp = await workspace_tree(workspace_id=wsid, path="")
        names = {e.name for e in resp.entries}
        assert "a.txt" in names
        assert "sub" in names

    @pytest.mark.asyncio
    async def test_lists_subdir(self, trusted_ws):
        from src.api.handlers.workspaces import workspace_tree

        wsid, root = trusted_ws
        (root / "sub").mkdir()
        (root / "sub" / "inside.txt").write_text("x", encoding="utf-8")

        resp = await workspace_tree(workspace_id=wsid, path="sub")
        names = [e.name for e in resp.entries]
        assert "inside.txt" in names

    @pytest.mark.asyncio
    async def test_filters_noisy_dirs(self, trusted_ws):
        """`.git`, `node_modules`, `.venv`, `__pycache__` não aparecem."""
        from src.api.handlers.workspaces import workspace_tree

        wsid, root = trusted_ws
        for noisy in (".git", "node_modules", ".venv", "__pycache__", ".next"):
            (root / noisy).mkdir()
        (root / "src").mkdir()

        resp = await workspace_tree(workspace_id=wsid, path="")
        names = {e.name for e in resp.entries}
        assert "src" in names
        for noisy in (".git", "node_modules", ".venv", "__pycache__", ".next"):
            assert noisy not in names

    @pytest.mark.asyncio
    async def test_marks_dirs_and_files(self, trusted_ws):
        from src.api.handlers.workspaces import workspace_tree

        wsid, root = trusted_ws
        (root / "data").mkdir()
        (root / "x.md").write_text("x", encoding="utf-8")

        resp = await workspace_tree(workspace_id=wsid, path="")
        kinds = {e.name: e.kind for e in resp.entries}
        assert kinds["data"] == "dir"
        assert kinds["x.md"] == "file"

    @pytest.mark.asyncio
    async def test_returns_empty_for_traversal_attempt(self, trusted_ws):
        """`..` resolve fora do workspace → guard rail bloqueia."""
        from src.api.handlers.workspaces import workspace_tree

        wsid, _ = trusted_ws
        resp = await workspace_tree(workspace_id=wsid, path="..")
        assert resp.entries == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_workspace(self, trusted_ws):
        from src.api.handlers.workspaces import workspace_tree

        resp = await workspace_tree(workspace_id="nope", path="")
        assert resp.entries == []


# ---------------------------------------------------------------------------
# /workspaces/{id}/file
# ---------------------------------------------------------------------------


class TestWorkspaceFile:
    @pytest.mark.asyncio
    async def test_reads_text_file(self, trusted_ws):
        from src.api.handlers.workspaces import workspace_file

        wsid, root = trusted_ws
        (root / "hello.txt").write_text("olá mundo\n", encoding="utf-8")

        resp = await workspace_file(workspace_id=wsid, path="hello.txt")
        assert resp.kind == "text"
        assert resp.content == "olá mundo\n"
        assert resp.truncated is False

    @pytest.mark.asyncio
    async def test_detects_binary_file(self, trusted_ws):
        """Byte nulo nos primeiros 8 kB → kind=binary, sem conteúdo."""
        from src.api.handlers.workspaces import workspace_file

        wsid, root = trusted_ws
        (root / "data.bin").write_bytes(b"\x00\x01\x02\xff" * 100)

        resp = await workspace_file(workspace_id=wsid, path="data.bin")
        assert resp.kind == "binary"
        assert resp.content is None
        assert resp.size > 0

    @pytest.mark.asyncio
    async def test_truncates_large_text(self, trusted_ws):
        """Arquivos acima de 256 kB são truncados (campo `truncated=True`)."""
        from src.api.handlers.workspaces import workspace_file

        wsid, root = trusted_ws
        # 300 kB de "a"
        (root / "big.txt").write_text("a" * (300 * 1024), encoding="utf-8")

        resp = await workspace_file(workspace_id=wsid, path="big.txt")
        assert resp.kind == "text"
        assert resp.truncated is True
        assert resp.content is not None
        assert len(resp.content) == 256 * 1024

    @pytest.mark.asyncio
    async def test_returns_empty_for_missing_file(self, trusted_ws):
        from src.api.handlers.workspaces import workspace_file

        wsid, _ = trusted_ws
        resp = await workspace_file(workspace_id=wsid, path="nao-existe.txt")
        assert resp.content is None
        assert resp.size == 0

    @pytest.mark.asyncio
    async def test_blocks_traversal(self, trusted_ws):
        """Path `..` ou absoluto fora do workspace é bloqueado."""
        from src.api.handlers.workspaces import workspace_file

        wsid, root = trusted_ws
        # Cria arquivo IRMÃO ao workspace (acima dele)
        outside = root.parent / "fora.txt"
        outside.write_text("segredo", encoding="utf-8")

        resp = await workspace_file(workspace_id=wsid, path="../fora.txt")
        # Resolver bloqueia (resolve_within_workspace devolve None) →
        # handler responde como "arquivo não encontrado".
        assert resp.content is None or "segredo" not in (resp.content or "")


# ---------------------------------------------------------------------------
# /workspaces/{id}/git/diff
# ---------------------------------------------------------------------------


class TestWorkspaceGitDiff:
    @pytest.mark.asyncio
    async def test_returns_empty_for_non_git_workspace(self, trusted_ws):
        from src.api.handlers.workspaces import workspace_git_diff

        wsid, _ = trusted_ws
        resp = await workspace_git_diff(workspace_id=wsid)
        assert resp.is_git_repo is False
        assert resp.files == []
        assert resp.total_additions == 0
        assert resp.total_deletions == 0

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_workspace(self, trusted_ws):
        from src.api.handlers.workspaces import workspace_git_diff

        resp = await workspace_git_diff(workspace_id="nope")
        assert resp.is_git_repo is False
        assert resp.files == []


class TestWorkspaceGitDiffFile:
    @pytest.mark.asyncio
    async def test_returns_empty_hunks_for_non_git_workspace(self, trusted_ws):
        from src.api.handlers.workspaces import workspace_git_diff_file

        wsid, _ = trusted_ws
        resp = await workspace_git_diff_file(workspace_id=wsid, path="x.md")
        assert resp.hunks == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_workspace(self, trusted_ws):
        from src.api.handlers.workspaces import workspace_git_diff_file

        resp = await workspace_git_diff_file(workspace_id="nope", path="x.md")
        assert resp.hunks == []


# ---------------------------------------------------------------------------
# Parser interno _parse_unified_diff (T7)
# ---------------------------------------------------------------------------


class TestParseUnifiedDiff:
    def test_splits_hunks_by_at_at_header(self):
        from src.api.handlers.workspaces import _parse_unified_diff

        diff = (
            "@@ -1,3 +1,3 @@\n"
            " linha 1\n"
            "-velha\n"
            "+nova\n"
            " linha 3\n"
            "@@ -10,2 +10,2 @@\n"
            "-outra velha\n"
            "+outra nova\n"
        )
        hunks = _parse_unified_diff(diff)
        assert len(hunks) == 2
        assert hunks[0].header == "@@ -1,3 +1,3 @@"
        assert "-velha" in hunks[0].lines
        assert "+nova" in hunks[0].lines
        assert hunks[1].header == "@@ -10,2 +10,2 @@"

    def test_returns_empty_for_empty_diff(self):
        from src.api.handlers.workspaces import _parse_unified_diff

        assert _parse_unified_diff("") == []

    def test_ignores_lines_before_first_hunk(self):
        """Headers `diff --git` / `index` antes do primeiro `@@` são descartados."""
        from src.api.handlers.workspaces import _parse_unified_diff

        diff = (
            "diff --git a/x b/x\n"
            "index abc..def 100644\n"
            "--- a/x\n"
            "+++ b/x\n"
            "@@ -1 +1 @@\n"
            "-velha\n"
            "+nova\n"
        )
        hunks = _parse_unified_diff(diff)
        assert len(hunks) == 1
        assert "-velha" in hunks[0].lines
