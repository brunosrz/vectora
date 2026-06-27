"""Informações de modelos LLM para o frontend (model selector).

Endpoint (exige auth via middleware):
    GET /models/providers — providers de LLM com credencial configurada.

O frontend usa isto para esconder do model selector os modelos cujo provider não
tem API key (ex.: sem chave OpenAI/Anthropic, GPT/Claude não aparecem).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/providers")
async def get_configured_providers() -> dict:
    """Lista os providers de LLM com credencial configurada."""
    from backend.settings import settings

    return {"providers": settings.configured_llm_providers()}
