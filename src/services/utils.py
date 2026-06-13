"""Utility Functions and Multi-Provider LLM Loading.

Provides LLM factory function supporting Google Gemini, OpenAI, Anthropic,
Cohere and Ollama via seus SDKs oficiais LangChain:
    google-genai  → langchain-google-genai  (ChatGoogleGenerativeAI)
    openai        → langchain-openai        (ChatOpenAI)
    anthropic     → langchain-anthropic     (ChatAnthropic, prompt caching)
    cohere        → langchain-cohere        (ChatCohere, CohereEmbeddings,
                                             CohereRerank)
    ollama        → langchain-ollama        (ChatOllama, via init_chat_model)

Inclui async context managers e helpers de variáveis de ambiente.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, cast

from src.services.env import get_env

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langchain_core.language_models.base import BaseLanguageModel


def _get_env_with_default(name: str, default: str) -> str:
    """Get environment variable with a default value."""
    value = get_env(name, strict=False)
    return value if value is not None else default


def load_llm() -> BaseLanguageModel:
    """Carrega o LLM de acordo com as configurações de ambiente.

    A precedência é: variáveis de ambiente > ``~/.vectora/settings.json``
    (runtime_settings) > defaults.

    Provedores suportados (``LLM_PROVIDER``):
        google-genai  — Google Gemini (padrão)
        openai        — OpenAI Chat
        anthropic     — Anthropic Claude, com prompt caching habilitado
        cohere        — Cohere Command
        ollama        — Ollama local

    Variáveis de ambiente:
        LLM_PROVIDER          — provider (google-genai | openai | anthropic |
                                 cohere | ollama)
        GOOGLE_API_KEY        — chave Google Gemini
        GOOGLE_MODEL          — modelo (default: gemini-2.5-flash)
        OPENAI_API_KEY        — chave OpenAI
        OPENAI_MODEL          — modelo (default: gpt-4o)
        ANTHROPIC_API_KEY     — chave Anthropic
        ANTHROPIC_MODEL       — modelo (default: claude-opus-4-1)
        ANTHROPIC_PROMPT_CACHE — habilita prompt caching (default: true)
        COHERE_API_KEY        — chave Cohere
        COHERE_CHAT_MODEL     — modelo (default: command-a-03-2025)
        OLLAMA_BASE_URL       — URL do servidor Ollama (default:
                                 http://127.0.0.1:11434)
        OLLAMA_MODEL          — modelo (default: gpt-oss:20b)
        LLM_TEMPERATURE       — temperatura (default: 0.2)
    """
    import os

    from src.services.runtime_settings import runtime_settings

    provider = os.getenv("LLM_PROVIDER") or runtime_settings.active_provider
    temperature = float(_get_env_with_default("LLM_TEMPERATURE", "0.2"))

    def _active_model(p: str, default: str) -> str:
        """Retorna active_model se o provider ativo bater; caso contrário, o default."""
        if runtime_settings.active_provider == p:
            return runtime_settings.active_model or default
        return default

    model: BaseLanguageModel

    match provider:
        case "google-genai":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
            except ImportError as exc:
                msg = "langchain-google-genai não instalado. Execute: uv add langchain-google-genai"
                raise ImportError(msg) from exc

            model = cast(
                "BaseLanguageModel",
                ChatGoogleGenerativeAI(
                    model=os.getenv("GOOGLE_MODEL")
                    or _active_model("google-genai", "gemini-2.5-flash"),
                    google_api_key=get_env("GOOGLE_API_KEY"),  # type: ignore[arg-type]
                    temperature=temperature,
                ),
            )

        case "openai":
            try:
                from langchain_openai import ChatOpenAI
            except ImportError as exc:
                msg = "langchain-openai não instalado. Execute: uv add langchain-openai"
                raise ImportError(msg) from exc

            model = cast(
                "BaseLanguageModel",
                ChatOpenAI(
                    model=os.getenv("OPENAI_MODEL")
                    or _active_model("openai", "gpt-4o"),
                    api_key=get_env("OPENAI_API_KEY"),  # ty: ignore[invalid-argument-type]
                    temperature=temperature,
                ),
            )

        case "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
            except ImportError as exc:
                msg = "langchain-anthropic não instalado. Execute: uv add langchain-anthropic"
                raise ImportError(msg) from exc

            # Prompt caching habilitado por padrão (reduz custo em ~90% para
            # system prompts longos reutilizados). Desabilitar com
            # ANTHROPIC_PROMPT_CACHE=false para depuração.
            prompt_cache = os.getenv("ANTHROPIC_PROMPT_CACHE", "true").lower() not in {
                "false",
                "0",
                "no",
            }
            betas = ["prompt-caching-2024-07-31"] if prompt_cache else []

            # ChatAnthropic stubs usam model_name mas o campo aceita model em runtime.
            # api_key aceita str mas stubs exigem SecretStr — ambos são supprimidos.
            model = cast(
                "BaseLanguageModel",
                ChatAnthropic(  # ty: ignore[missing-argument]
                    model=os.getenv("ANTHROPIC_MODEL")  # ty: ignore[unknown-argument]
                    or _active_model("anthropic", "claude-opus-4-1"),
                    api_key=get_env("ANTHROPIC_API_KEY"),  # ty: ignore[invalid-argument-type]
                    temperature=temperature,
                    betas=betas,
                ),
            )

        case "cohere":
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
                    model=os.getenv("COHERE_CHAT_MODEL")
                    or _active_model("cohere", "command-a-03-2025"),
                    temperature=temperature,
                ),
            )

        case "ollama":
            from langchain.chat_models import init_chat_model

            model = cast(
                "BaseLanguageModel",
                init_chat_model(
                    model=os.getenv("OLLAMA_MODEL")
                    or _active_model("ollama", "gpt-oss:20b"),
                    model_provider="ollama",
                    base_url=_get_env_with_default(
                        "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
                    ),
                    temperature=temperature,
                    configurable_fields=["model"],
                ),
            )

        case _:
            msg = (
                f"LLM_PROVIDER desconhecido: {provider!r}. "
                "Suportados: google-genai, openai, anthropic, cohere, ollama"
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

    from src.services.background import get_background_worker

    _log = logging.getLogger(__name__)

    worker = await get_background_worker()
    await worker.start()
    _log.info("BackgroundEmbeddingWorker iniciado via async_lifespan")

    try:
        yield
    finally:
        await worker.stop()
        _log.info("BackgroundEmbeddingWorker parado via async_lifespan")
