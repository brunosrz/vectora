"""Tests for src/tools/fs.py"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from langchain_core.runnables import RunnableConfig

from backend.vtypes import Workspace

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def trusted_ws(tmp_path, monkeypatch):
    """Workspace confiável apontando para tmp_path + config para as tools.

    As tools de fs confinam toda operação ao workspace ativo (Q4). Os testes
    registram um workspace confiável em tmp_path e passam seu id no config para
    que leituras/escritas ocorram dentro da pasta de teste.
    """
    from backend.workspace import workspace as ws_mod

    ws = Workspace(
        id="testws",
        name="testws",
        cwd=str(tmp_path),
        created_at="2024-01-01T00:00:00+00:00",
        trusted=True,
    )
    monkeypatch.setattr(
        ws_mod.workspace_registry,
        "get",
        lambda wid: ws if wid == "testws" else None,
    )
    monkeypatch.setattr(
        ws_mod.workspace_registry,
        "get_or_create",
        lambda cwd=None: ws,
    )
    return {"configurable": {"workspace_id": "testws"}}


# ---------------------------------------------------------------------------
# file_read
# ---------------------------------------------------------------------------


class TestFileRead:
    def test_reads_existing_file(self, tmp_path, trusted_ws):
        from backend.tools.fs import file_read

        f = tmp_path / "hello.txt"
        f.write_text("conteudo do arquivo", encoding="utf-8")
        result = file_read.invoke({"file_path": str(f)}, config=trusted_ws)
        assert result == "conteudo do arquivo"

    def test_file_not_found(self, tmp_path, trusted_ws):
        from backend.tools.fs import file_read

        result = file_read.invoke(
            {"file_path": str(tmp_path / "nao_existe.txt")}, config=trusted_ws
        )
        assert "not found" in result.lower() or "error" in result.lower()

    def test_blocked_path(self, tmp_path, trusted_ws):
        from backend.tools.fs import file_read

        outside = tmp_path.parent / "fora_do_workspace.txt"
        result = file_read.invoke({"file_path": str(outside)}, config=trusted_ws)
        assert "fora do workspace" in result.lower() or "error" in result.lower()


# ---------------------------------------------------------------------------
# file_write
# ---------------------------------------------------------------------------


class TestFileWrite:
    def test_creates_new_file(self, tmp_path, trusted_ws):
        from backend.tools.fs import file_write

        dest = tmp_path / "novo.txt"
        result = file_write.invoke(
            {"file_path": str(dest), "content": "ola mundo"}, config=trusted_ws
        )
        assert "ok" in result.lower() or "written" in result.lower()
        assert dest.read_text(encoding="utf-8") == "ola mundo"

    def test_overwrites_existing_file(self, tmp_path, trusted_ws):
        from backend.tools.fs import file_write

        dest = tmp_path / "existente.txt"
        dest.write_text("velho", encoding="utf-8")
        file_write.invoke(
            {"file_path": str(dest), "content": "novo"}, config=trusted_ws
        )
        assert dest.read_text(encoding="utf-8") == "novo"

    def test_creates_parent_dirs(self, tmp_path, trusted_ws):
        from backend.tools.fs import file_write

        dest = tmp_path / "sub" / "dir" / "arquivo.txt"
        file_write.invoke({"file_path": str(dest), "content": "x"}, config=trusted_ws)
        assert dest.exists()

    def test_blocked_path(self, tmp_path, trusted_ws):
        from backend.tools.fs import file_write

        outside = tmp_path.parent / "evil.txt"
        result = file_write.invoke(
            {"file_path": str(outside), "content": "x"}, config=trusted_ws
        )
        assert "fora do workspace" in result.lower() or "error" in result.lower()

    def test_requires_trust(self, tmp_path, monkeypatch):
        from backend.tools.fs import file_write
        from backend.workspace import workspace as ws_mod

        untrusted = Workspace(
            id="untrusted",
            name="untrusted",
            cwd=str(tmp_path),
            created_at="2024-01-01T00:00:00+00:00",
            trusted=False,
        )
        monkeypatch.setattr(
            ws_mod.workspace_registry,
            "get",
            lambda wid: untrusted if wid == "untrusted" else None,
        )
        monkeypatch.setattr(
            ws_mod.workspace_registry, "get_or_create", lambda cwd=None: untrusted
        )
        cfg = {"configurable": {"workspace_id": "untrusted"}}
        result = file_write.invoke(
            {"file_path": str(tmp_path / "x.txt"), "content": "x"},
            config=cfg,  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        )
        assert "confi" in result.lower()  # "não é confiável" / "confiança"


# ---------------------------------------------------------------------------
# file_edit
# ---------------------------------------------------------------------------


class TestFileEdit:
    def test_replaces_text(self, tmp_path, trusted_ws):
        from backend.tools.fs import file_edit

        f = tmp_path / "code.py"
        f.write_text("foo = 1\nbar = 2\n", encoding="utf-8")
        result = file_edit.invoke(
            {"file_path": str(f), "old_text": "foo = 1", "new_text": "foo = 99"},
            config=trusted_ws,
        )
        assert "ok" in result.lower()
        assert "foo = 99" in f.read_text(encoding="utf-8")

    def test_replace_all(self, tmp_path, trusted_ws):
        from backend.tools.fs import file_edit

        f = tmp_path / "rep.txt"
        f.write_text("a a a", encoding="utf-8")
        file_edit.invoke(
            {
                "file_path": str(f),
                "old_text": "a",
                "new_text": "b",
                "replace_all": True,
            },
            config=trusted_ws,
        )
        assert f.read_text(encoding="utf-8") == "b b b"

    def test_creates_file_when_old_text_empty(self, tmp_path, trusted_ws):
        from backend.tools.fs import file_edit

        dest = tmp_path / "new.txt"
        result = file_edit.invoke(
            {"file_path": str(dest), "old_text": "", "new_text": "criado"},
            config=trusted_ws,
        )
        assert "ok" in result.lower() or "created" in result.lower()
        assert dest.read_text(encoding="utf-8") == "criado"

    def test_text_not_found(self, tmp_path, trusted_ws):
        from backend.tools.fs import file_edit

        f = tmp_path / "f.txt"
        f.write_text("abc", encoding="utf-8")
        result = file_edit.invoke(
            {"file_path": str(f), "old_text": "xyz", "new_text": "nope"},
            config=trusted_ws,
        )
        assert "not found" in result.lower() or "error" in result.lower()


# ---------------------------------------------------------------------------
# grep
# ---------------------------------------------------------------------------


class TestGrep:
    def test_finds_pattern_in_file(self, tmp_path, trusted_ws):
        from backend.tools.fs import grep

        f = tmp_path / "backend.py"
        f.write_text("def foo():\n    pass\n", encoding="utf-8")
        result = grep.invoke(
            {"pattern": "def foo", "path": str(tmp_path)}, config=trusted_ws
        )
        assert "def foo" in result

    def test_no_match_returns_message(self, tmp_path, trusted_ws):
        from backend.tools.fs import grep

        f = tmp_path / "empty.py"
        f.write_text("nothing here", encoding="utf-8")
        result = grep.invoke(
            {"pattern": "xyz_not_present", "path": str(tmp_path)}, config=trusted_ws
        )
        assert "no matches" in result.lower()

    def test_invalid_pattern(self, trusted_ws):
        from backend.tools.fs import grep

        with patch("backend.tools.fs.is_safe_regex_pattern", return_value=False):
            result = grep.invoke(
                {"pattern": "[invalid", "path": "."}, config=trusted_ws
            )
        assert "invalid" in result.lower() or "error" in result.lower()


# ---------------------------------------------------------------------------
# list_dir
# ---------------------------------------------------------------------------


class TestListDir:
    def test_lists_files(self, tmp_path, trusted_ws):
        from backend.tools.fs import list_dir

        (tmp_path / "a.txt").write_text("x")
        (tmp_path / "b.txt").write_text("y")
        result = list_dir.invoke({"path": str(tmp_path)}, config=trusted_ws)
        assert "a.txt" in result
        assert "b.txt" in result

    def test_recursive(self, tmp_path, trusted_ws):
        from backend.tools.fs import list_dir

        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.txt").write_text("z")
        result = list_dir.invoke(
            {"path": str(tmp_path), "recursive": True}, config=trusted_ws
        )
        assert "deep.txt" in result

    def test_nonexistent_dir(self, tmp_path, trusted_ws):
        from backend.tools.fs import list_dir

        result = list_dir.invoke({"path": str(tmp_path / "nope")}, config=trusted_ws)
        assert "not found" in result.lower() or "error" in result.lower()


# ---------------------------------------------------------------------------
# create_artifact
# ---------------------------------------------------------------------------


def _cfg(thread_id: str) -> RunnableConfig:
    """RunnableConfig mínimo — thread_id vem do config (injetado pelo
    LangGraph em produção via configurable["thread_id"]), nunca de um
    kwarg que dependeria do modelo "lembrar" de passar o ID certo."""
    return cast("RunnableConfig", {"configurable": {"thread_id": thread_id}})


class TestCreateArtifact:
    def test_creates_file_and_returns_json(self, tmp_path, monkeypatch):
        from backend.tools.fs import create_artifact

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = create_artifact.invoke(
            {
                "artifact_type": "plan",
                "title": "Plano de Implementacao Auth",
                "content": "# Auth\n\nPasso 1: definir schema\nPasso 2: implementar JWT",
            },
            config=_cfg("042731"),
        )
        data = json.loads(result)
        assert "path" in data
        assert data["artifact_type"] == "plan"
        assert data["session_id"] == "042731"
        assert data["title"] == "Plano de Implementacao Auth"
        assert Path(data["path"]).exists()
        content = Path(data["path"]).read_text(encoding="utf-8")
        assert "Auth" in content

    def test_saved_under_session_dir(self, tmp_path, monkeypatch):
        from backend.tools.fs import create_artifact

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = create_artifact.invoke(
            {
                "artifact_type": "spec",
                "title": "API de Pagamentos",
                "content": "Spec content",
            },
            config=_cfg("000001"),
        )
        data = json.loads(result)
        artifact_path = Path(data["path"])
        # deve estar em .src/artifacts/000001/
        assert "000001" in str(artifact_path)
        assert artifact_path.suffix == ".md"

    def test_no_overwrite_collision(self, tmp_path, monkeypatch):
        from backend.tools.fs import create_artifact

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        kwargs = {
            "artifact_type": "guide",
            "title": "Setup Guide",
            "content": "Content",
        }
        cfg = _cfg("999999")
        r1 = json.loads(create_artifact.invoke(kwargs, config=cfg))
        r2 = json.loads(create_artifact.invoke(kwargs, config=cfg))
        assert r1["path"] != r2["path"]
        assert Path(r1["path"]).exists()
        assert Path(r2["path"]).exists()

    def test_invalid_type_returns_error(self, tmp_path, monkeypatch):
        from backend.tools.fs import create_artifact

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = create_artifact.invoke(
            {
                "artifact_type": "invalid_type",
                "title": "Titulo",
                "content": "Conteudo",
            },
            config=_cfg("000000"),
        )
        data = json.loads(result)
        assert "error" in data

    def test_empty_title_returns_error(self, tmp_path, monkeypatch):
        from backend.tools.fs import create_artifact

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = create_artifact.invoke(
            {
                "artifact_type": "plan",
                "title": "   ",
                "content": "Conteudo",
            },
            config=_cfg("000000"),
        )
        data = json.loads(result)
        assert "error" in data

    def test_empty_content_returns_error(self, tmp_path, monkeypatch):
        from backend.tools.fs import create_artifact

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = create_artifact.invoke(
            {
                "artifact_type": "plan",
                "title": "Titulo valido",
                "content": "",
            },
            config=_cfg("000000"),
        )
        data = json.loads(result)
        assert "error" in data

    def test_all_valid_types_accepted(self, tmp_path, monkeypatch):
        from backend.tools.fs import _VALID_ARTIFACT_TYPES, create_artifact

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        for artifact_type in _VALID_ARTIFACT_TYPES:
            result = create_artifact.invoke(
                {
                    "artifact_type": artifact_type,
                    "title": f"Teste {artifact_type}",
                    "content": "Conteudo de teste",
                },
                config=_cfg("000000"),
            )
            data = json.loads(result)
            assert "error" not in data, f"tipo '{artifact_type}' falhou: {data}"

    def test_missing_thread_id_returns_error_instead_of_silent_default(
        self, tmp_path, monkeypatch
    ):
        """Regressão: session_id="000000" como default oculto fazia o artifact
        cair num diretório errado sempre que o config não trazia o thread_id
        real (ex.: modelo "esquecia" de passar o parâmetro, já que dependia
        dele lembrar de um valor visto só no texto do prompt) — o painel
        Plano da UI, que busca pelo threadId real, mostrava "Sem planos"
        mesmo com o Vectora confirmando que salvou. Agora falha alto (erro
        explícito) em vez de salvar silenciosamente no lugar errado."""
        from backend.tools.fs import create_artifact

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = create_artifact.invoke(
            {
                "artifact_type": "overview",
                "title": "Visao Geral",
                "content": "Conteudo",
            },
            config={"configurable": {}},
        )
        data = json.loads(result)
        assert "error" in data


# ---------------------------------------------------------------------------
# _artifact_slug (helper interno)
# ---------------------------------------------------------------------------


class TestArtifactSlug:
    def test_basic_slug(self):
        from backend.tools.fs import _artifact_slug

        slug = _artifact_slug("Plano de Implementacao")
        assert slug == "plano-de-implementacao"

    def test_max_length(self):
        from backend.tools.fs import _artifact_slug

        long_title = "a" * 100
        assert len(_artifact_slug(long_title)) <= 50

    def test_empty_falls_back(self):
        from backend.tools.fs import _artifact_slug

        assert _artifact_slug("") == "artifact"
        assert _artifact_slug("   !@#  ") == "artifact"

    def test_spaces_become_hyphens(self):
        from backend.tools.fs import _artifact_slug

        assert _artifact_slug("hello world") == "hello-world"

    def test_no_consecutive_hyphens(self):
        from backend.tools.fs import _artifact_slug

        slug = _artifact_slug("a  b   c")
        assert "--" not in slug


# ---------------------------------------------------------------------------
# Hooks pós-escrita + auto-commit (Trilha B) — vectora.toml [hooks]/[agent]
# ---------------------------------------------------------------------------


class TestPostWriteHooksAndAutoCommit:
    def test_file_write_runs_post_write_hook(self, tmp_path, trusted_ws):
        """[hooks] post_file_write roda com {file} substituído pelo path real."""
        from backend.tools.fs import file_write

        marker = tmp_path / "hook-ran.txt"
        (tmp_path / "vectora.toml").write_text(
            "[hooks]\npost_file_write = [\"python -c \\\"open(r'{file}' + '.marker', 'w').close()\\\"\"]\n",
            encoding="utf-8",
        )

        dest = tmp_path / "novo.txt"
        file_write.invoke({"file_path": str(dest), "content": "ola"}, config=trusted_ws)

        marker_file = Path(str(dest) + ".marker")
        assert marker_file.exists()

    def test_file_write_without_config_does_not_run_hooks(self, tmp_path, trusted_ws):
        """Sem vectora.toml (ou sem seções configuradas), nenhum hook roda — edge."""
        from backend.tools.fs import file_write

        dest = tmp_path / "sem-config.txt"
        result = file_write.invoke(
            {"file_path": str(dest), "content": "ola"}, config=trusted_ws
        )
        assert "ok" in result.lower() or "written" in result.lower()

    def test_file_edit_auto_commit_creates_git_commit(self, tmp_path, trusted_ws):
        """agent.auto_commit=true faz file_edit gerar um commit git automático."""
        import git

        from backend.tools.fs import file_edit

        repo = git.Repo.init(tmp_path)
        repo.config_writer().set_value("user", "name", "Test").release()
        repo.config_writer().set_value("user", "email", "t@t.com").release()

        target = tmp_path / "arquivo.py"
        target.write_text("x = 1\n", encoding="utf-8")
        repo.index.add(["arquivo.py"])
        repo.index.commit("initial")

        (tmp_path / "vectora.toml").write_text(
            "[agent]\nauto_commit = true\n", encoding="utf-8"
        )

        file_edit.invoke(
            {
                "file_path": str(target),
                "old_text": "x = 1",
                "new_text": "x = 2",
            },
            config=trusted_ws,
        )

        latest = next(repo.iter_commits())
        assert "arquivo.py" in str(latest.message)
        assert repo.is_dirty() is False

    def test_file_edit_auto_commit_disabled_by_default_leaves_changes_uncommitted(
        self, tmp_path, trusted_ws
    ):
        """Edge — sem auto_commit=true (default), a edição NÃO vira commit."""
        import git

        from backend.tools.fs import file_edit

        repo = git.Repo.init(tmp_path)
        repo.config_writer().set_value("user", "name", "Test").release()
        repo.config_writer().set_value("user", "email", "t@t.com").release()

        target = tmp_path / "arquivo.py"
        target.write_text("x = 1\n", encoding="utf-8")
        repo.index.add(["arquivo.py"])
        repo.index.commit("initial")

        file_edit.invoke(
            {
                "file_path": str(target),
                "old_text": "x = 1",
                "new_text": "x = 2",
            },
            config=trusted_ws,
        )

        assert repo.is_dirty() is True
