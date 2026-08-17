"""Utility Functions and Multi-Provider LLM Loading.

``load_native_llm()`` resolve o provider ativo (env > runtime_settings >
defaults) e devolve o ``ChatClient`` nativo do provider — Google Gemini,
OpenAI, Anthropic, Cohere, Ollama e OpenRouter — via
``backend/llm/fallback_chat_client.load_chat_client``.

Inclui o async context manager de ciclo de vida da aplicação.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from backend.llm.base import ChatClient


# provider canônico (underscore) → (env var do modelo, modelo default).
# A UI/LLM_PROVIDER pode usar hífen ("google-genai"); normalizamos p/ underscore.
_PROVIDER_SPEC: dict[str, tuple[str, str]] = {
    "google_genai": ("GOOGLE_MODEL", "gemini-2.5-flash"),
    "openai": ("OPENAI_MODEL", "gpt-4o"),
    "anthropic": ("ANTHROPIC_MODEL", "claude-opus-4-1"),
    "cohere": ("COHERE_CHAT_MODEL", "command-a-03-2025"),
    "ollama": ("OLLAMA_MODEL", "gpt-oss:20b"),
    "openrouter": ("OPENROUTER_MODEL", "openrouter/auto"),
    "nine_router": ("NINE_ROUTER_MODEL", ""),
}


def load_native_llm(model_id: str = "") -> ChatClient:
    """Carrega o ``ChatClient`` nativo do provider ativo.

    Mesma resolução de provider/modelo que o antigo ``load_llm`` (env >
    runtime_settings > defaults), mas devolve um ``ChatClient``
    (``backend/llm/base.py``) em vez de ``BaseChatModel``. ``model_id``
    (opcional, formato ``"provider:model"``) sobrepõe o provider/modelo
    padrão — usado pela troca de modelo por request.
    """
    import os

    from backend.workspace.runtime_settings import runtime_settings

    if model_id:
        prov, _sep, name = model_id.partition(":")
        provider = prov.replace("-", "_")
        spec = _PROVIDER_SPEC.get(provider)
        env_var = spec[0] if spec else ""
        model_name = (
            name
            or (os.getenv(env_var) if env_var else None)
            or (spec[1] if spec else "")
        )
    else:
        provider = (
            os.getenv("LLM_PROVIDER") or runtime_settings.active_provider
        ).replace("-", "_")
        spec = _PROVIDER_SPEC.get(provider)
        if spec is None:
            msg = (
                f"LLM_PROVIDER desconhecido: {provider!r}. Suportados: "
                "google_genai, openai, anthropic, cohere, ollama, openrouter"
            )
            raise ValueError(msg)
        env_var, default_model = spec
        active = (
            runtime_settings.active_model
            if runtime_settings.active_provider.replace("-", "_") == provider
            else ""
        )
        model_name = os.getenv(env_var) or active or default_model

    if not model_name and provider == "nine_router":
        from backend.settings import settings

        model_name = settings.nine_router_default_model or ""

    if not model_name:
        msg = f"Modelo de LLM não resolvido para provider {provider!r}."
        raise ValueError(msg)

    mid = f"{provider}:{model_name}"
    from backend.llm.fallback_chat_client import load_chat_client

    return load_chat_client(mid)


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

    from backend.embedding.background import get_background_worker

    _log = logging.getLogger(__name__)

    worker = await get_background_worker()
    await worker.start()
    _log.info("BackgroundEmbeddingWorker iniciado via async_lifespan")

    try:
        yield
    finally:
        await worker.stop()
        _log.info("BackgroundEmbeddingWorker parado via async_lifespan")
