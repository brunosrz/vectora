"""Testes para vectora/services/ignore.py — foco nas funções novas.

Cobre:
- load_vectoraignore_spec: carrega .vectoraignore com pathspec gitwildmatch
- load_ignore_spec: combina .gitignore + .vectoraignore num spec único
- Integração: is_ignored respeita spec combinado
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestLoadVectoraignoreSpec:
    """load_vectoraignore_spec: carrega .vectoraignore como PathSpec."""

    def test_returns_none_when_no_file(self, tmp_path):
        from src.services.ignore import load_vectoraignore_spec

        spec = load_vectoraignore_spec(tmp_path)
        assert spec is None

    def test_loads_simple_pattern(self, tmp_path):
        from src.services.ignore import load_vectoraignore_spec

        (tmp_path / ".vectoraignore").write_text("*.log\n")
        spec = load_vectoraignore_spec(tmp_path)
        assert spec is not None
        assert spec.match_file("error.log")
        assert not spec.match_file("main.py")

    def test_loads_directory_pattern(self, tmp_path):
        from src.services.ignore import load_vectoraignore_spec

        (tmp_path / ".vectoraignore").write_text("tests/fixtures/**\n")
        spec = load_vectoraignore_spec(tmp_path)
        assert spec is not None
        assert spec.match_file("tests/fixtures/data.json")
        assert not spec.match_file("src/main.py")

    def test_ignores_comment_lines(self, tmp_path):
        from src.services.ignore import load_vectoraignore_spec

        (tmp_path / ".vectoraignore").write_text("# comment\n*.generated.py\n")
        spec = load_vectoraignore_spec(tmp_path)
        assert spec is not None
        assert spec.match_file("schema.generated.py")
        assert not spec.match_file("models.py")

    def test_searches_up_to_parent(self, tmp_path):
        from src.services.ignore import load_vectoraignore_spec

        (tmp_path / ".vectoraignore").write_text("*.secret\n")
        subdir = tmp_path / "src" / "core"
        subdir.mkdir(parents=True)

        spec = load_vectoraignore_spec(subdir)
        assert spec is not None
        assert spec.match_file("credentials.secret")

    def test_uses_closest_vectoraignore(self, tmp_path):
        """Quando há dois .vectoraignore em níveis distintos, usa o mais próximo."""
        from src.services.ignore import load_vectoraignore_spec

        (tmp_path / ".vectoraignore").write_text("*.parent\n")
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / ".vectoraignore").write_text("*.child\n")

        spec = load_vectoraignore_spec(subdir)
        assert spec is not None
        # bate padrão do filho
        assert spec.match_file("a.child")
        # NÃO bate padrão do pai (usa apenas o mais próximo)
        assert not spec.match_file("a.parent")


class TestLoadIgnoreSpec:
    """load_ignore_spec: combina .gitignore + .vectoraignore."""

    def test_returns_none_when_neither_exists(self, tmp_path):
        from src.services.ignore import load_ignore_spec

        spec = load_ignore_spec(tmp_path)
        assert spec is None

    def test_uses_gitignore_when_only_that_exists(self, tmp_path):
        from src.services.ignore import load_ignore_spec

        (tmp_path / ".gitignore").write_text("*.pyc\n")
        spec = load_ignore_spec(tmp_path)
        assert spec is not None
        assert spec.match_file("main.pyc")
        assert not spec.match_file("main.py")

    def test_uses_vectoraignore_when_only_that_exists(self, tmp_path):
        from src.services.ignore import load_ignore_spec

        (tmp_path / ".vectoraignore").write_text("data/**\n")
        spec = load_ignore_spec(tmp_path)
        assert spec is not None
        assert spec.match_file("data/dump.json")
        assert not spec.match_file("src/model.py")

    def test_combines_both_specs(self, tmp_path):
        from src.services.ignore import load_ignore_spec

        (tmp_path / ".gitignore").write_text("*.pyc\ndist/\n")
        (tmp_path / ".vectoraignore").write_text("tests/fixtures/**\n*.generated.py\n")
        spec = load_ignore_spec(tmp_path)
        assert spec is not None

        # padrões do .gitignore
        assert spec.match_file("foo.pyc")
        assert spec.match_file("dist/bundle.js")

        # padrões do .vectoraignore
        assert spec.match_file("tests/fixtures/data.json")
        assert spec.match_file("schema.generated.py")

        # arquivo não ignorado por nenhum
        assert not spec.match_file("src/core/models.py")

    def test_gitignore_and_vectoraignore_independent_search(self, tmp_path):
        """Cada arquivo é procurado independentemente na hierarquia."""
        from src.services.ignore import load_ignore_spec

        parent = tmp_path / "proj"
        parent.mkdir()
        (parent / ".gitignore").write_text("*.log\n")

        subdir = parent / "src"
        subdir.mkdir()
        (subdir / ".vectoraignore").write_text("*.secret\n")

        # subdir tem .vectoraignore local; sobe e acha .gitignore no proj/
        spec = load_ignore_spec(subdir)
        assert spec is not None
        assert spec.match_file("error.log")  # do .gitignore em proj/
        assert spec.match_file("key.secret")  # do .vectoraignore em src/


class TestIsIgnoredWithCombinedSpec:
    """Garante que is_ignored funciona com spec combinado de load_ignore_spec."""

    def test_file_ignored_by_vectoraignore(self, tmp_path):
        from src.services.ignore import is_ignored, load_ignore_spec

        (tmp_path / ".vectoraignore").write_text("*.dump\n")
        spec = load_ignore_spec(tmp_path)

        dump_file = tmp_path / "db.dump"
        assert is_ignored(dump_file, tmp_path, spec)

    def test_file_not_ignored(self, tmp_path):
        from src.services.ignore import is_ignored, load_ignore_spec

        (tmp_path / ".vectoraignore").write_text("*.dump\n")
        spec = load_ignore_spec(tmp_path)

        py_file = tmp_path / "main.py"
        assert not is_ignored(py_file, tmp_path, spec)

    def test_always_skip_dirs_still_apply(self, tmp_path):
        """ALWAYS_SKIP_DIRS são bloqueados mesmo sem spec."""
        from src.services.ignore import is_ignored

        node_modules_file = tmp_path / "node_modules" / "pkg" / "index.js"
        assert is_ignored(node_modules_file, tmp_path, None)
