"""Utility Functions and Multi-Provider LLM Loading.

Provides LLM factory function supporting Google Gemini, OpenAI, Anthropic, Ollama.
Includes async context managers and environment variable helpers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, cast

from langchain.chat_models import init_chat_model

from vectora.services.env import get_env

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langchain_core.language_models.base import BaseLanguageModel


def _get_env_with_default(name: str, default: str) -> str:
    """Get environment variable with a default value."""
    value = get_env(name, strict=False)
    return value if value is not None else default


def load_llm() -> BaseLanguageModel:
    """Load LLM based on environment configuration.

    Supports multiple providers via LLM_PROVIDER environment variable:
    - google-genai (default): Google Gemini models
    - ollama: Local Ollama instance
    - openai: OpenAI API
    - anthropic: Anthropic Claude API

    Environment variables:
        LLM_PROVIDER: Provider name (default: google-genai)
        GOOGLE_API_KEY: Google API key (for google-genai)
        GOOGLE_MODEL: Model name (default: gemini-2.0-flash)
        OLLAMA_BASE_URL: Ollama URL (default: http://127.0.0.1:11434)
        OLLAMA_MODEL: Model name (default: gpt-oss:20b)
        OPENAI_API_KEY: OpenAI API key
        OPENAI_MODEL: Model name (default: gpt-4o)
        ANTHROPIC_API_KEY: Anthropic API key
        ANTHROPIC_MODEL: Model name (default: claude-opus-4-1)
        LLM_TEMPERATURE: Temperature (default: 0.2)
    """
    provider = _get_env_with_default("LLM_PROVIDER", "google-genai")
    temperature = float(_get_env_with_default("LLM_TEMPERATURE", "0.2"))

    if provider == "google-genai":
        model = cast(
            "BaseLanguageModel",
            init_chat_model(
                model=_get_env_with_default("GOOGLE_MODEL", "gemini-2.5-flash"),
                model_provider="google-genai",
                api_key=get_env("GOOGLE_API_KEY"),
                temperature=temperature,
                configurable_fields="any",
            ),
        )

    elif provider == "ollama":
        model = cast(
            "BaseLanguageModel",
            init_chat_model(
                model=_get_env_with_default("OLLAMA_MODEL", "gpt-oss:20b"),
                model_provider="ollama",
                base_url=_get_env_with_default(
                    "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
                ),
                temperature=temperature,
                configurable_fields="any",
            ),
        )

    elif provider == "openai":
        model = cast(
            "BaseLanguageModel",
            init_chat_model(
                model=_get_env_with_default("OPENAI_MODEL", "gpt-4o"),
                model_provider="openai",
                api_key=get_env("OPENAI_API_KEY"),
                temperature=temperature,
                configurable_fields="any",
            ),
        )

    elif provider == "anthropic":
        model = cast(
            "BaseLanguageModel",
            init_chat_model(
                model=_get_env_with_default("ANTHROPIC_MODEL", "claude-opus-4-1"),
                model_provider="anthropic",
                api_key=get_env("ANTHROPIC_API_KEY"),
                temperature=temperature,
                configurable_fields="any",
            ),
        )

    elif provider == "cohere":
        try:
            from langchain_cohere import ChatCohere
        except ImportError as exc:
            msg = "langchain-cohere não instalado. Execute: uv add langchain-cohere"
            raise ImportError(msg) from exc

        api_key = get_env("COHERE_API_KEY")
        if not api_key:
            msg = "COHERE_API_KEY não configurado. Adicione ao seu .env para usar o provider cohere."
            raise ValueError(msg)

        # NOTE: NÃO usar SecretStr aqui.
        # langchain-core's get_from_dict_or_env chama str(SecretStr) → "**********",
        # o que causa 401 Unauthorized da API do Cohere.
        model = cast(
            "BaseLanguageModel",
            ChatCohere(
                cohere_api_key=api_key,  # ty: ignore[invalid-argument-type]
                model=_get_env_with_default("COHERE_CHAT_MODEL", "command-a-03-2025"),
                temperature=temperature,
            ),
        )

    else:
        msg = (
            f"Unknown LLM_PROVIDER: {provider}. "
            f"Supported: google-genai, ollama, openai, anthropic, cohere"
        )
        raise ValueError(msg)

    if not hasattr(model, "bind_tools"):
        msg = "Model must support bind_tools"
        raise TypeError(msg)
    if not hasattr(model, "invoke"):
        msg = "Model must support invoke"
        raise TypeError(msg)
    if not hasattr(model, "with_config"):
        msg = "Model must support with_config"
        raise TypeError(msg)

    return model


@asynccontextmanager
async def async_lifespan() -> AsyncGenerator[None]:
    """Async context manager for application lifecycle.

    Inicia o BackgroundEmbeddingWorker na entrada e para gracefully na saída.
    O worker lê da fila SQLite e escreve embeddings no LanceDB.

    Sem este lifespan, os documentos enfileirados pela tool `embedding` ficam
    em status "pending" indefinidamente — nada os processa.

    Usage:
        async with async_lifespan():
            # Application runs here
            pass
    """
    import logging

    from vectora.services.background import get_background_worker

    _log = logging.getLogger(__name__)

    worker = await get_background_worker()
    await worker.start()
    _log.info("BackgroundEmbeddingWorker iniciado via async_lifespan")

    try:
        yield
    finally:
        await worker.stop()
        _log.info("BackgroundEmbeddingWorker parado via async_lifespan")
