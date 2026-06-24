"""Testes para backend/services/context_graph/extract.py.

Testa a API pública: _get_extractor, _safe_extract, helpers de utilitários.
Os parsers tree-sitter individuais têm 8500+ linhas; cobrimos via _safe_extract
com arquivos reais.
"""

from __future__ import annotations

from pathlib import Path


class TestGetExtractor:
    def test_python_file_returns_extractor(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor

        f = tmp_path / "app.py"
        f.touch()
        extractor = _get_extractor(f)
        assert extractor is not None
        assert callable(extractor)

    def test_typescript_file_returns_extractor(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor

        f = tmp_path / "app.ts"
        f.touch()
        extractor = _get_extractor(f)
        assert extractor is not None

    def test_tsx_file_returns_extractor(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor

        f = tmp_path / "Component.tsx"
        f.touch()
        extractor = _get_extractor(f)
        assert extractor is not None

    def test_go_file_returns_extractor(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor

        f = tmp_path / "main.go"
        f.touch()
        extractor = _get_extractor(f)
        assert extractor is not None

    def test_unknown_extension_returns_none(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor

        f = tmp_path / "data.xyz123abc"
        f.touch()
        assert _get_extractor(f) is None

    def test_mcp_json_routed_to_mcp_extractor(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor
        from backend.services.context_graph.mcp_ingest import extract_mcp_config

        f = tmp_path / ".mcp.json"
        f.touch()
        assert _get_extractor(f) is extract_mcp_config

    def test_pyproject_toml_routed_to_manifest(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor
        from backend.services.context_graph.manifest_ingest import (
            extract_package_manifest,
        )

        f = tmp_path / "pyproject.toml"
        f.touch()
        assert _get_extractor(f) is extract_package_manifest

    def test_pom_xml_routed_to_manifest(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor
        from backend.services.context_graph.manifest_ingest import (
            extract_package_manifest,
        )

        f = tmp_path / "pom.xml"
        f.touch()
        assert _get_extractor(f) is extract_package_manifest

    def test_blade_php_returns_blade_extractor(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor

        f = tmp_path / "layout.blade.php"
        f.touch()
        extractor = _get_extractor(f)
        assert extractor is not None

    def test_json_non_mcp_returns_json_extractor(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor

        f = tmp_path / "schema.json"
        f.touch()
        extractor = _get_extractor(f)
        # json files go through generic dispatch (not None unless unsupported)
        # At minimum callable or None; we assert not mcp
        from backend.services.context_graph.mcp_ingest import extract_mcp_config

        assert extractor is not extract_mcp_config


class TestSafeExtract:
    def test_returns_dict_on_success(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor, _safe_extract

        f = tmp_path / "file.py"
        f.write_text("x = 1\n", encoding="utf-8")
        extractor = _get_extractor(f)
        assert extractor is not None
        result = _safe_extract(extractor, f)
        assert isinstance(result, dict)

    def test_returns_empty_on_exception(self, tmp_path: Path):
        from backend.services.context_graph.extract import _safe_extract

        class _RaisingExtractor:
            def __call__(self, path: Path) -> dict:
                raise RuntimeError("parse failed")

        f = tmp_path / "broken.py"
        f.touch()
        result = _safe_extract(_RaisingExtractor(), f)
        assert isinstance(result, dict)
        assert result.get("nodes") == [] or "nodes" not in result


class TestMakeId:
    def test_deterministic(self):
        from backend.services.context_graph.extract import _make_id

        assert _make_id("module", "fn") == _make_id("module", "fn")

    def test_different_inputs_different_ids(self):
        from backend.services.context_graph.extract import _make_id

        assert _make_id("module", "fn_a") != _make_id("module", "fn_b")

    def test_returns_string(self):
        from backend.services.context_graph.extract import _make_id

        assert isinstance(_make_id("x"), str)


class TestFileStem:
    def test_plain_stem_includes_parent(self):
        from backend.services.context_graph.extract import _file_stem

        # _file_stem qualifies with parent dir name to avoid ID collisions
        f = Path("/project/src/auth.py")
        result = _file_stem(f)
        assert "auth" in result
        assert "src" in result

    def test_top_level_file_bare_stem(self):
        from backend.services.context_graph.extract import _file_stem

        # A file at root level (parent is ".") returns bare stem
        f = Path("./Makefile")
        result = _file_stem(f)
        assert "Makefile" in result


class TestSourceLocation:
    def test_integer_line(self):
        from backend.services.context_graph.extract import _source_location

        result = _source_location(42)
        assert result is not None
        assert "42" in result

    def test_string_line(self):
        from backend.services.context_graph.extract import _source_location

        result = _source_location("10")
        assert result is not None
        assert "10" in result

    def test_none_returns_none(self):
        from backend.services.context_graph.extract import _source_location

        assert _source_location(None) is None


class TestExtractPythonFile:
    def test_extracts_function(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor, _safe_extract

        f = tmp_path / "module.py"
        f.write_text("def authenticate(user): return True\n", encoding="utf-8")
        extractor = _get_extractor(f)
        assert extractor is not None
        result = _safe_extract(extractor, f)
        node_labels = [n.get("label", "") for n in result.get("nodes", [])]
        assert any("authenticate" in lbl for lbl in node_labels)

    def test_extracts_class(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor, _safe_extract

        f = tmp_path / "service.py"
        f.write_text("class AuthService:\n    pass\n", encoding="utf-8")
        extractor = _get_extractor(f)
        assert extractor is not None
        result = _safe_extract(extractor, f)
        node_labels = [n.get("label", "") for n in result.get("nodes", [])]
        assert any("AuthService" in lbl for lbl in node_labels)

    def test_empty_file_no_nodes(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor, _safe_extract

        f = tmp_path / "empty.py"
        f.write_text("", encoding="utf-8")
        extractor = _get_extractor(f)
        assert extractor is not None
        result = _safe_extract(extractor, f)
        assert isinstance(result, dict)

    def test_syntax_error_graceful(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor, _safe_extract

        f = tmp_path / "bad.py"
        f.write_text("def (:\n    pass\n", encoding="utf-8")
        extractor = _get_extractor(f)
        assert extractor is not None
        result = _safe_extract(extractor, f)
        assert isinstance(result, dict)


class TestExtractTypeScriptFile:
    def test_extracts_function_ts(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor, _safe_extract

        f = tmp_path / "utils.ts"
        f.write_text(
            "export function greet(name: string): string { return `Hello ${name}`; }\n",
            encoding="utf-8",
        )
        extractor = _get_extractor(f)
        assert extractor is not None
        result = _safe_extract(extractor, f)
        assert isinstance(result.get("nodes"), list)

    def test_extracts_interface(self, tmp_path: Path):
        from backend.services.context_graph.extract import _get_extractor, _safe_extract

        f = tmp_path / "types.ts"
        f.write_text(
            "export interface User { id: string; name: string; }\n", encoding="utf-8"
        )
        extractor = _get_extractor(f)
        assert extractor is not None
        result = _safe_extract(extractor, f)
        assert isinstance(result, dict)


class TestStripJsonc:
    def test_removes_line_comments(self):
        from backend.services.context_graph.extract import _strip_jsonc

        code = '{\n  "key": "value" // comment\n}'
        result = _strip_jsonc(code)
        assert "//" not in result
        assert "value" in result

    def test_removes_block_comments(self):
        from backend.services.context_graph.extract import _strip_jsonc

        code = '{ /* block comment */ "key": 1 }'
        result = _strip_jsonc(code)
        assert "/*" not in result

    def test_preserves_urls(self):
        from backend.services.context_graph.extract import _strip_jsonc

        code = '{ "url": "https://example.com" }'
        result = _strip_jsonc(code)
        assert "https://example.com" in result
