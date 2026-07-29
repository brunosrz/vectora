"""PROVIDER_API_KEY_ENV — chaves de LLM/search sobrevivem à restauração
pós-.env de projeto (Sprint 11.5: TAVILY_API_KEY tinha precedência
invertida, ausente do dict que `_load_environment_hierarchy` usa pra
restaurar o valor do usuário depois que um `.env` de projeto/repo
esquecido no filesystem sobrescreve tudo)."""

from __future__ import annotations

import os

import pytest

from backend.settings import PROVIDER_API_KEY_ENV, Settings


class TestProviderApiKeyEnvRegistry:
    def test_tavily_registrada_no_dict_de_precedencia(self):
        assert PROVIDER_API_KEY_ENV["tavily"] == "TAVILY_API_KEY"

    def test_todas_as_chaves_conhecidas_ainda_presentes_regressao(self):
        assert PROVIDER_API_KEY_ENV["google-genai"] == "GOOGLE_API_KEY"
        assert PROVIDER_API_KEY_ENV["openai"] == "OPENAI_API_KEY"
        assert PROVIDER_API_KEY_ENV["anthropic"] == "ANTHROPIC_API_KEY"
        assert PROVIDER_API_KEY_ENV["cohere"] == "COHERE_API_KEY"
        assert PROVIDER_API_KEY_ENV["openrouter"] == "OPENROUTER_API_KEY"


@pytest.fixture
def _isolated_env_hierarchy(tmp_path, monkeypatch):
    """Isola `_load_environment_hierarchy`: home do usuário e cwd apontam
    pra diretórios temporários, sem tocar no `.env` real do repo."""
    import backend.settings as settings_mod

    vectora_home = tmp_path / "vectora_home"
    vectora_home.mkdir()
    monkeypatch.setattr(settings_mod, "_default_vectora_home", lambda: vectora_home)

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    for key in PROVIDER_API_KEY_ENV.values():
        if key:
            monkeypatch.delenv(key, raising=False)

    return vectora_home, project_dir


class TestTavilyKeyPrecedence:
    def test_env_de_projeto_nao_vence_env_do_usuario(self, _isolated_env_hierarchy):
        vectora_home, project_dir = _isolated_env_hierarchy
        (vectora_home / ".env").write_text("TAVILY_API_KEY=tvly-user-value\n")
        (project_dir / ".env").write_text("TAVILY_API_KEY=tvly-project-leftover\n")

        Settings()

        assert os.environ["TAVILY_API_KEY"] == "tvly-user-value"

    def test_regressao_google_api_key_continua_restaurada(
        self, _isolated_env_hierarchy
    ):
        vectora_home, project_dir = _isolated_env_hierarchy
        (vectora_home / ".env").write_text("GOOGLE_API_KEY=AIza-user-value\n")
        (project_dir / ".env").write_text("GOOGLE_API_KEY=AIza-project-leftover\n")

        Settings()

        assert os.environ["GOOGLE_API_KEY"] == "AIza-user-value"

    def test_sem_env_de_usuario_projeto_prevalece_borda(self, _isolated_env_hierarchy):
        _vectora_home, project_dir = _isolated_env_hierarchy
        (project_dir / ".env").write_text("TAVILY_API_KEY=tvly-only-project\n")

        Settings()

        assert os.environ["TAVILY_API_KEY"] == "tvly-only-project"
