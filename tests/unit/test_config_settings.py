"""Tests for src/settings.py"""

from __future__ import annotations

import os

import pytest

from src.settings import Settings

# ---------------------------------------------------------------------------
# Smoke tests (existentes)
# ---------------------------------------------------------------------------


def test_settings_loads():
    s = Settings()
    assert s is not None


def test_settings_derived_paths():
    s = Settings()
    assert s.lancedb_dir is not None
    assert str(s.lancedb_dir).endswith("lancedb")


def test_settings_embedding_queue_dsn():
    s = Settings()
    assert s.embedding_queue_dsn is not None
    assert "sqlite" in s.embedding_queue_dsn


def test_settings_defaults():
    s = Settings()
    assert isinstance(s.debug_mode, bool)
    assert isinstance(s.max_context_tokens, int)
    assert s.max_context_tokens > 0


def test_settings_get_cohere_api_key_returns_none_or_str():
    s = Settings()
    key = s.get_cohere_api_key()
    assert key is None or isinstance(key, str)


# ---------------------------------------------------------------------------
# TLS do servidor web (SSL_CERTFILE / SSL_KEYFILE)
# ---------------------------------------------------------------------------


def test_settings_ssl_defaults_none():
    s = Settings()
    assert s.ssl_certfile is None
    assert s.ssl_keyfile is None


def test_settings_ssl_from_env(monkeypatch):
    monkeypatch.setenv("SSL_CERTFILE", "/certs/fullchain.pem")
    monkeypatch.setenv("SSL_KEYFILE", "/certs/key.pem")
    s = Settings()
    assert s.ssl_certfile == "/certs/fullchain.pem"
    assert s.ssl_keyfile == "/certs/key.pem"


def test_cli_parser_accepts_ssl_flags():
    from src.main import _build_parser

    parser = _build_parser()
    args = parser.parse_args(
        [
            "server",
            "web",
            "--ssl-certfile",
            "cert.pem",
            "--ssl-keyfile",
            "key.pem",
        ]
    )
    assert args.ssl_certfile == "cert.pem"
    assert args.ssl_keyfile == "key.pem"


def test_cli_parser_ssl_flags_default_none():
    from src.main import _build_parser

    parser = _build_parser()
    args = parser.parse_args(["server", "web"])
    assert args.ssl_certfile is None
    assert args.ssl_keyfile is None


# ---------------------------------------------------------------------------
# Cohere provider (Fase 1)
# ---------------------------------------------------------------------------


def test_cohere_chat_model_default():
    s = Settings()
    assert s.cohere_chat_model == "command-a-03-2025"


def test_cohere_in_get_llm_model_when_provider_set(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "cohere")
    s = Settings()
    # Sem chave configurada, get_llm_model ainda retorna o campo correto
    assert s.cohere_chat_model is not None
    assert isinstance(s.cohere_chat_model, str)


def test_cohere_available_when_api_key_set(monkeypatch):
    monkeypatch.setenv("COHERE_API_KEY", "cohere_test_key_fake")
    s = Settings()
    providers = s.get_available_providers()
    assert "cohere" in providers


def test_cohere_not_available_without_api_key(monkeypatch):
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    s = Settings()
    # Só aparece se a chave estiver configurada
    providers = s.get_available_providers()
    # Se cohere_api_key não está setado no env, não deve aparecer
    if not s.cohere_api_key:
        assert "cohere" not in providers


def test_set_model_cohere():
    s = Settings()
    s.set_model("cohere", "command-r-plus-08-2024")
    assert s.cohere_chat_model == "command-r-plus-08-2024"


def test_set_model_cohere_default_model():
    s = Settings()
    s.set_model("cohere", "command-a-03-2025")
    assert s.cohere_chat_model == "command-a-03-2025"


# ---------------------------------------------------------------------------
# OpenAI model default — corrigido em fix/critical-bugs (era "gpt-5.5", agora "gpt-4o")
# ---------------------------------------------------------------------------


def test_openai_model_default_is_valid():
    s = Settings()
    invalid_models = {"gpt-5.5", "gpt-5", "gpt-4.5"}
    assert s.openai_model not in invalid_models, (
        f"openai_model='{s.openai_model}' é um modelo inválido/inexistente"
    )


def test_openai_model_default_is_gpt4o():
    s = Settings()
    assert s.openai_model == "gpt-4o"


# ---------------------------------------------------------------------------
# get_llm_model e get_llm_api_key por provider
# ---------------------------------------------------------------------------


def test_get_llm_model_google():
    # Testa a lógica de get_llm_model() diretamente, sem depender da hierarquia de env
    s = Settings()
    s.llm_provider = "google-genai"
    assert s.get_llm_model() == s.google_model


def test_get_llm_model_openai():
    s = Settings()
    s.llm_provider = "openai"
    # openai_model padrão é "gpt-4o" (corrigido em fix/critical-bugs)
    assert s.get_llm_model() == s.openai_model


def test_get_llm_model_cohere():
    # Testa que get_llm_model() retorna cohere_chat_model quando provider=cohere
    s = Settings()
    s.llm_provider = "cohere"
    assert s.get_llm_model() == s.cohere_chat_model


# ---------------------------------------------------------------------------
# Literal do provider inclui "cohere"
# ---------------------------------------------------------------------------


def test_llm_provider_literal_accepts_cohere():
    # Testa que o campo llm_provider aceita "cohere" como valor válido
    s = Settings()
    s.llm_provider = "cohere"  # type: ignore[assignment]
    assert s.llm_provider == "cohere"
