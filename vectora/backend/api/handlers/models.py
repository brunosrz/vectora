"""Informações de modelos LLM para o frontend (model selector).

Endpoint (exige auth via middleware):
    GET /models/providers — providers de LLM com credencial configurada +
    modelos dinâmicos registrados (provider routing — Ollama e OpenRouter).

O frontend usa isto para esconder do model selector os modelos cujo provider não
tem API key (ex.: sem chave OpenAI/Anthropic, GPT/Claude não aparecem) e para
mesclar os modelos Ollama/OpenRouter que o usuário registrou (backend/api/
handlers/provider_routing.py) no catálogo estático de deployment-config.ts.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/providers")
async def get_configured_providers() -> dict:
    """Providers de LLM com credencial configurada + modelos dinâmicos."""
    from backend.api.handlers.provider_routing import (
        list_registered_ollama_models,
        list_registered_openrouter_models,
    )
    from backend.settings import TOOL_CALLING_INCOMPATIBLE_MODELS, settings

    dynamic_models = [
        {"id": f"ollama:{m.tag}", "label": m.tag}
        for m in await list_registered_ollama_models()
    ] + [
        {"id": f"openrouter:{m.tag}", "label": m.tag}
        for m in await list_registered_openrouter_models()
    ]
    return {
        "providers": settings.configured_llm_providers(),
        "dynamic_models": dynamic_models,
        "tool_incompatible_models": sorted(TOOL_CALLING_INCOMPATIBLE_MODELS),
    }
