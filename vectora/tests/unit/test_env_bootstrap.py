"""Testes para backend/mcp/env_bootstrap.py.

Cobre: LLM_PROVIDER vindo do ambiente MCP vai pro app_settings (SQLite via
runtime_settings), nunca pro .env — só segredos (API keys) vão pro .env.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def _isolated_runtime_settings(tmp_path: Path, monkeypatch):
    from backend.workspace import runtime_settings as rs_module
    from backend.workspace.runtime_settings import RuntimeSettings

    fresh = RuntimeSettings(path=tmp_path / "checkpoints.db")
    monkeypatch.setattr(rs_module, "runtime_settings", fresh)
    return fresh


@pytest.fixture
def _isolated_env_file(tmp_path: Path, monkeypatch):
    import backend.mcp.env_bootstrap as eb

    env_file = tmp_path / ".env"
    monkeypatch.setattr(eb, "_ENV_FILE", env_file)
    return env_file


class TestBootstrapLlmProviderFromMcp:
    def test_persiste_provider_do_ambiente_em_app_settings(
        self, monkeypatch, _isolated_runtime_settings
    ):
        from backend.mcp.env_bootstrap import _bootstrap_llm_provider_from_mcp

        monkeypatch.setenv("LLM_PROVIDER", "cohere")
        result = _bootstrap_llm_provider_from_mcp()

        assert result is True
        assert _isolated_runtime_settings.get("active_provider") == "cohere"

    def test_sem_llm_provider_no_ambiente_nao_faz_nada(
        self, monkeypatch, _isolated_runtime_settings
    ):
        from backend.mcp.env_bootstrap import _bootstrap_llm_provider_from_mcp

        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        assert _bootstrap_llm_provider_from_mcp() is False
        assert _isolated_runtime_settings.get("active_provider") is None

    def test_nao_sobrescreve_provider_ja_configurado(
        self, monkeypatch, _isolated_runtime_settings
    ):
        from backend.mcp.env_bootstrap import _bootstrap_llm_provider_from_mcp

        _isolated_runtime_settings.set("active_provider", "openai")
        monkeypatch.setenv("LLM_PROVIDER", "cohere")

        result = _bootstrap_llm_provider_from_mcp()

        assert result is False
        assert _isolated_runtime_settings.get("active_provider") == "openai"


class TestBootstrapEnvFromMcpDoesNotWriteLlmProviderToEnvFile:
    def test_llm_provider_nao_vai_pro_env_file(
        self, monkeypatch, _isolated_runtime_settings, _isolated_env_file
    ):
        from backend.mcp.env_bootstrap import bootstrap_env_from_mcp

        monkeypatch.setenv("LLM_PROVIDER", "cohere")
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("COHERE_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)

        result = bootstrap_env_from_mcp()

        assert result is True
        assert _isolated_runtime_settings.get("active_provider") == "cohere"
        # LLM_PROVIDER não é segredo — nunca escrito no .env, mesmo quando o
        # arquivo é criado por outra key reconhecida (aqui não há nenhuma).
        assert not _isolated_env_file.exists()

    def test_secret_key_ainda_vai_pro_env_file(
        self, monkeypatch, _isolated_runtime_settings, _isolated_env_file
    ):
        from backend.mcp.env_bootstrap import bootstrap_env_from_mcp

        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.setenv("COHERE_API_KEY", "sk-test-123")
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)

        result = bootstrap_env_from_mcp()

        assert result is True
        content = _isolated_env_file.read_text(encoding="utf-8")
        assert "COHERE_API_KEY=sk-test-123" in content
        assert "LLM_PROVIDER" not in content
