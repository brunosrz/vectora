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
    from backend.vtypes import Workspace
    from backend.workspace import workspace as ws_mod

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
# git_stage / git_unstage — repo real (sem mock de git.Repo)
#
# Os testes acima mockam git.Repo pra cobrir os caminhos de erro sem custo
# de I/O; estes validam contra um repositório de verdade (git é um binário
# local, sem rede) — a asserção é sobre o ESTADO do index (repo.index.entries/
# repo.is_dirty()), não sobre uma string fixa de retorno.
# ---------------------------------------------------------------------------


@pytest.fixture
def real_repo_ws(tmp_path, monkeypatch):
    """Workspace apontando pra um repo git real com um commit inicial."""
    import git as gitpy

    from backend.vtypes import Workspace
    from backend.workspace import workspace as ws_mod

    repo = gitpy.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test").release()
    repo.config_writer().set_value("user", "email", "t@t.com").release()
    (tmp_path / "README.md").write_text("# repo\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("initial")

    ws = Workspace(
        id="ws-real-git",
        name="ws-real-git",
        cwd=str(tmp_path),
        created_at="2024-01-01T00:00:00+00:00",
        trusted=True,
    )
    monkeypatch.setattr(
        ws_mod.workspace_registry,
        "get",
        lambda wid: ws if wid == "ws-real-git" else None,
    )
    return ws, repo, tmp_path


@pytest.mark.asyncio
async def test_git_stage_real_repo_adds_to_index(real_repo_ws):
    ws, repo, root = real_repo_ws
    (root / "novo.py").write_text("x = 1\n", encoding="utf-8")

    result_raw = await git_stage.ainvoke(
        {"path": "novo.py", "workspace_id": ws.id}, config=_make_config(ws.id)
    )
    result = json.loads(result_raw)

    assert result["status"] == "ok"
    staged_paths = {entry[0] for entry in repo.index.entries}
    assert "novo.py" in staged_paths


@pytest.mark.asyncio
async def test_git_unstage_real_repo_removes_from_index(real_repo_ws):
    ws, repo, root = real_repo_ws
    (root / "novo.py").write_text("x = 1\n", encoding="utf-8")
    repo.index.add(["novo.py"])
    assert "novo.py" in {entry[0] for entry in repo.index.entries}

    result_raw = await git_unstage.ainvoke(
        {"path": "novo.py", "workspace_id": ws.id}, config=_make_config(ws.id)
    )
    result = json.loads(result_raw)

    assert result["status"] == "ok"
    # git reset HEAD tira do index mas mantém o arquivo como untracked/modified.
    assert repo.is_dirty(untracked_files=True)


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


# ---------------------------------------------------------------------------
# GitCommandNotFound — git não instalado no sistema
#
# Além de git.GitCommandError, as tools precisam sobreviver a
# git.GitCommandNotFound (executável git ausente do PATH) — caso comum numa
# máquina limpa. Antes de _safe_call existir, os `_git_*_impl` só tratavam
# GitCommandError e deixavam essa exceção escapar direto pro chamador da tool.
# ---------------------------------------------------------------------------


class TestGitCommandNotFound:
    @pytest.mark.asyncio
    async def test_git_diff_com_git_nao_instalado_nao_propaga(self, mock_ws):
        import git as gitpy

        mock_repo = MagicMock()
        mock_repo.git.diff.side_effect = gitpy.GitCommandNotFound(
            "git", FileNotFoundError("git não encontrado")
        )
        with patch("backend.tools.git.git.Repo", return_value=mock_repo):
            from backend.tools.git import git_diff

            result_raw = await git_diff.ainvoke(
                {"workspace_id": mock_ws.id}, config=_make_config(mock_ws.id)
            )
        result = json.loads(result_raw)
        assert result["status"] == "git_not_found"

    @pytest.mark.asyncio
    async def test_git_log_com_git_nao_instalado_nao_propaga(self, mock_ws):
        import git as gitpy

        mock_repo = MagicMock()
        mock_repo.iter_commits.side_effect = gitpy.GitCommandNotFound(
            "git", FileNotFoundError("git não encontrado")
        )
        with patch("backend.tools.git.git.Repo", return_value=mock_repo):
            from backend.tools.git import git_log

            result_raw = await git_log.ainvoke(
                {"workspace_id": mock_ws.id}, config=_make_config(mock_ws.id)
            )
        result = json.loads(result_raw)
        assert result["status"] == "git_not_found"

    def test_safe_call_converte_git_command_not_found(self):
        import git as gitpy

        from backend.tools.git import _safe_call

        def _boom():
            raise gitpy.GitCommandNotFound("git", FileNotFoundError("sumiu"))

        result = _safe_call(_boom)
        assert result["status"] == "git_not_found"

    def test_safe_call_converte_excecao_generica(self):
        from backend.tools.git import _safe_call

        def _boom():
            raise RuntimeError("algo inesperado")

        result = _safe_call(_boom)
        assert result["status"] == "error"
        assert "algo inesperado" in result["message"]

    def test_safe_call_repassa_resultado_de_sucesso(self):
        from backend.tools.git import _safe_call

        result = _safe_call(lambda: {"status": "ok", "value": 42})
        assert result == {"status": "ok", "value": 42}
