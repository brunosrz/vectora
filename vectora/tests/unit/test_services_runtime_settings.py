"""Tests for src/services/runtime_settings.py"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from backend.workspace.runtime_settings import RuntimeSettings

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_settings_path(tmp_path: Path) -> Path:
    """Retorna um caminho temporário para settings.json (ainda não existe)."""
    return tmp_path / "settings.json"


@pytest.fixture
def rs(tmp_settings_path: Path) -> RuntimeSettings:
    """RuntimeSettings apontando para arquivo temporário."""
    return RuntimeSettings(path=tmp_settings_path)


# ---------------------------------------------------------------------------
# Defaults sem arquivo
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_no_file_uses_defaults(self, tmp_settings_path: Path) -> None:
        assert not tmp_settings_path.exists()
        rs = RuntimeSettings(path=tmp_settings_path)
        assert rs.active_provider == "google-genai"
        assert rs.active_model == "gemini-2.5-flash"

    def test_get_unknown_key_returns_default(self, rs: RuntimeSettings) -> None:
        assert rs.get("chave_inexistente", "fallback") == "fallback"

    def test_get_unknown_key_no_default_returns_none(self, rs: RuntimeSettings) -> None:
        assert rs.get("chave_inexistente") is None


# ---------------------------------------------------------------------------
# Persistência: salvar e recarregar
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_set_creates_file(
        self, rs: RuntimeSettings, tmp_settings_path: Path
    ) -> None:
        rs.set("test_key", "test_value")
        assert tmp_settings_path.exists()

    def test_save_and_reload(self, tmp_settings_path: Path) -> None:
        rs1 = RuntimeSettings(path=tmp_settings_path)
        rs1.set("my_key", "my_value")

        rs2 = RuntimeSettings(path=tmp_settings_path)
        assert rs2.get("my_key") == "my_value"

    def test_multiple_keys_persisted(self, tmp_settings_path: Path) -> None:
        rs = RuntimeSettings(path=tmp_settings_path)
        rs.set("k1", "v1")
        rs.set("k2", 42)

        rs2 = RuntimeSettings(path=tmp_settings_path)
        assert rs2.get("k1") == "v1"
        assert rs2.get("k2") == 42

    def test_overwrite_key(self, rs: RuntimeSettings) -> None:
        rs.set("key", "first")
        rs.set("key", "second")
        assert rs.get("key") == "second"


# ---------------------------------------------------------------------------
# set_active_model
# ---------------------------------------------------------------------------


class TestSetActiveModel:
    def test_set_active_model_updates_provider(self, rs: RuntimeSettings) -> None:
        rs.set_active_model("openai", "gpt-4o")
        assert rs.active_provider == "openai"

    def test_set_active_model_updates_model(self, rs: RuntimeSettings) -> None:
        rs.set_active_model("anthropic", "claude-sonnet-4-5")
        assert rs.active_model == "claude-sonnet-4-5"

    def test_set_active_model_cohere(self, rs: RuntimeSettings) -> None:
        rs.set_active_model("cohere", "command-a-03-2025")
        assert rs.active_provider == "cohere"
        assert rs.active_model == "command-a-03-2025"

    def test_set_active_model_persists(self, tmp_settings_path: Path) -> None:
        rs1 = RuntimeSettings(path=tmp_settings_path)
        rs1.set_active_model("openai", "gpt-4o")

        rs2 = RuntimeSettings(path=tmp_settings_path)
        assert rs2.active_provider == "openai"
        assert rs2.active_model == "gpt-4o"


# ---------------------------------------------------------------------------
# Tolerância a falhas
# ---------------------------------------------------------------------------


class TestFaultTolerance:
    def test_corrupt_json_falls_back_to_defaults(self, tmp_settings_path: Path) -> None:
        tmp_settings_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_settings_path.write_text("{ invalid json !!!}", encoding="utf-8")

        rs = RuntimeSettings(path=tmp_settings_path)
        # Não deve levantar exceção — usa defaults
        assert rs.active_provider == "google-genai"
        assert rs.active_model == "gemini-2.5-flash"

    def test_empty_file_falls_back_to_defaults(self, tmp_settings_path: Path) -> None:
        tmp_settings_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_settings_path.write_text("", encoding="utf-8")

        rs = RuntimeSettings(path=tmp_settings_path)
        assert rs.active_provider == "google-genai"

    def test_partial_file_uses_defaults_for_missing_keys(
        self, tmp_settings_path: Path
    ) -> None:
        tmp_settings_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_settings_path.write_text(
            json.dumps({"active_provider": "openai"}), encoding="utf-8"
        )

        rs = RuntimeSettings(path=tmp_settings_path)
        assert rs.active_provider == "openai"
        assert rs.active_model == "gemini-2.5-flash"  # fallback to default


# ---------------------------------------------------------------------------
# fallback_order (Parte A3)
# ---------------------------------------------------------------------------


class TestFallbackOrder:
    def test_default_empty(self, rs: RuntimeSettings) -> None:
        assert rs.fallback_order == []

    def test_set_and_get_roundtrip(self, rs: RuntimeSettings) -> None:
        rs.set_fallback_order(["openai:gpt-4o", "google-genai:gemini-2.5-flash"])
        assert rs.fallback_order == [
            "openai:gpt-4o",
            "google-genai:gemini-2.5-flash",
        ]

    def test_preserves_order(self, rs: RuntimeSettings) -> None:
        rs.set_fallback_order(["cohere:command-a", "openai:gpt-4o"])
        assert rs.fallback_order == ["cohere:command-a", "openai:gpt-4o"]

    def test_filters_empty_and_blank(self, rs: RuntimeSettings) -> None:
        rs.set_fallback_order(["openai:gpt-4o", "", "   ", "cohere:command-a"])
        assert rs.fallback_order == ["openai:gpt-4o", "cohere:command-a"]

    def test_trims_whitespace(self, rs: RuntimeSettings) -> None:
        rs.set_fallback_order(["  openai:gpt-4o  "])
        assert rs.fallback_order == ["openai:gpt-4o"]

    def test_set_empty_clears(self, rs: RuntimeSettings) -> None:
        rs.set_fallback_order(["openai:gpt-4o"])
        rs.set_fallback_order([])
        assert rs.fallback_order == []

    def test_persists_to_disk(self, tmp_settings_path: Path) -> None:
        rs = RuntimeSettings(path=tmp_settings_path)
        rs.set_fallback_order(["openai:gpt-4o"])
        rs2 = RuntimeSettings(path=tmp_settings_path)
        assert rs2.fallback_order == ["openai:gpt-4o"]

    def test_invalid_type_in_file_returns_empty(self, tmp_settings_path: Path) -> None:
        tmp_settings_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_settings_path.write_text(
            json.dumps({"llm_fallback_order": "not-a-list"}), encoding="utf-8"
        )
        rs = RuntimeSettings(path=tmp_settings_path)
        assert rs.fallback_order == []

    def test_overwrite_replaces(self, rs: RuntimeSettings) -> None:
        rs.set_fallback_order(["openai:gpt-4o", "cohere:command-a"])
        rs.set_fallback_order(["google-genai:gemini-2.5-flash"])
        assert rs.fallback_order == ["google-genai:gemini-2.5-flash"]

    def test_entries_are_strings(self, rs: RuntimeSettings) -> None:
        rs.set_fallback_order(["openai:gpt-4o"])
        assert all(isinstance(x, str) for x in rs.fallback_order)


# ---------------------------------------------------------------------------
# reload()
# ---------------------------------------------------------------------------


class TestReload:
    def test_reload_picks_up_external_changes(self, tmp_settings_path: Path) -> None:
        rs = RuntimeSettings(path=tmp_settings_path)
        rs.set("key", "original")

        # Modificar arquivo externamente
        data = json.loads(tmp_settings_path.read_text(encoding="utf-8"))
        data["key"] = "updated"
        tmp_settings_path.write_text(json.dumps(data), encoding="utf-8")

        # Antes do reload — valor antigo em memória
        assert rs.get("key") == "original"

        rs.reload()
        assert rs.get("key") == "updated"


class TestRagSettings:
    """rag_settings: defaults + merge + persistência (aba de memória)."""

    def test_defaults(self, rs) -> None:
        s = rs.rag_settings
        assert s["reranker_enabled"] is True
        assert s["reranker_top_k"] == 5
        assert s["rerank_provider"] == "auto"
        assert s["embed_provider"] == "auto"
        assert s["ingest_file_types"] == []

    def test_set_merges_partial(self, rs) -> None:
        rs.set_rag_settings(reranker_enabled=False, reranker_top_k=12)
        s = rs.rag_settings
        assert s["reranker_enabled"] is False
        assert s["reranker_top_k"] == 12
        # Campos não informados mantêm o default.
        assert s["rerank_provider"] == "auto"

    def test_set_ignores_none(self, rs) -> None:
        rs.set_rag_settings(reranker_top_k=8)
        rs.set_rag_settings(reranker_top_k=None, rerank_provider="voyage")
        s = rs.rag_settings
        assert s["reranker_top_k"] == 8  # não sobrescrito por None
        assert s["rerank_provider"] == "voyage"

    def test_persists_across_reload(self, tmp_settings_path) -> None:
        from backend.workspace.runtime_settings import RuntimeSettings

        rs1 = RuntimeSettings(path=tmp_settings_path)
        rs1.set_rag_settings(reranker_top_k=20, ingest_file_types=["code"])
        rs2 = RuntimeSettings(path=tmp_settings_path)
        assert rs2.rag_settings["reranker_top_k"] == 20
        assert rs2.rag_settings["ingest_file_types"] == ["code"]
