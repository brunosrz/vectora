"""Shared constants, provider maps, and utility functions for command handlers.

All command modules import from here to avoid duplication.
"""

import logging
import os
from pathlib import Path
from typing import Any

from vectora.config.settings import settings
from vectora.services.runtime_settings import runtime_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Available models by provider
# ---------------------------------------------------------------------------

AVAILABLE_MODELS: dict[str, list[str]] = {
    "google-genai": [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "o3",
        "o4-mini",
    ],
    "anthropic": [
        "claude-sonnet-4-5",
        "claude-opus-4-5",
        "claude-haiku-4-5",
    ],
    "cohere": [
        "command-a-03-2025",
        "command-r-plus-08-2024",
        "command-r-08-2024",
        "command-r7b-12-2024",
    ],
}


def get_available_models(provider: str | None = None) -> dict[str, list[str]]:
    """Get available models for a provider or all providers."""
    if provider:
        return {provider: AVAILABLE_MODELS.get(provider, [])}
    return AVAILABLE_MODELS


# ---------------------------------------------------------------------------
# Provider metadata maps
# ---------------------------------------------------------------------------

#: Variável de ambiente da API key por provider (None = sem chave necessária)
PROVIDER_API_KEY_ENV: dict[str, str | None] = {
    "google-genai": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "ollama": None,
    "cohere": "COHERE_API_KEY",
}

#: Variável de ambiente do modelo por provider
PROVIDER_MODEL_ENV: dict[str, str] = {
    "google-genai": "GOOGLE_MODEL",
    "openai": "OPENAI_MODEL",
    "anthropic": "ANTHROPIC_MODEL",
    "ollama": "OLLAMA_MODEL",
    "cohere": "COHERE_CHAT_MODEL",
}

#: Nome de exibição por provider
PROVIDER_DISPLAY: dict[str, str] = {
    "google-genai": "Google Gemini",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "ollama": "Ollama",
    "cohere": "Cohere",
}

#: URL para obter API key por provider
PROVIDER_KEY_URL: dict[str, str] = {
    "google-genai": "https://aistudio.google.com/app/apikey",
    "openai": "https://platform.openai.com/api-keys",
    "anthropic": "https://console.anthropic.com/",
    "cohere": "https://dashboard.cohere.com/api-keys",
}

#: Cor Rich por provider
PROVIDER_COLOR: dict[str, str] = {
    "google-genai": "cyan",
    "openai": "green",
    "anthropic": "magenta",
    "ollama": "yellow",
    "cohere": "blue",
}


# ---------------------------------------------------------------------------
# Provider utilities
# ---------------------------------------------------------------------------


def find_provider_for_model(model: str) -> str | None:
    """Retorna o provider que possui o modelo, ou None se não encontrado."""
    for provider, models in AVAILABLE_MODELS.items():
        if model in models:
            return provider
    return None


def has_api_key(provider: str) -> bool:
    """Retorna True se a API key do provider está configurada no ambiente."""
    key_env = PROVIDER_API_KEY_ENV.get(provider)
    if key_env is None:
        return True  # Ollama não precisa de chave
    return bool(os.environ.get(key_env))


def reset_llm_singletons() -> None:
    """Zera singletons de LLM dos agentes para forçar recriação com novo provider/model."""
    try:
        import vectora.agents.coder as _c
        import vectora.agents.orchestrator as _o
        import vectora.agents.search as _s

        _o._orchestrator_llm = None
        _c._coder_llm = None
        _s._search_llm = None
        logger.debug("LLM singletons resetados")
    except Exception as e:
        logger.warning("Erro ao resetar LLM singletons: %s", e)


def save_api_key_to_env(key_env: str, key: str) -> None:
    """Persiste a API key em ~/.vectora/.env (criando ou atualizando a linha)."""
    env_file = Path.home() / ".vectora" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    found = False
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key_env}="):
                lines.append(f"{key_env}={key}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{key_env}={key}")

    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("API key salva em ~/.vectora/.env (%s)", key_env)


def apply_model_change(provider: str, model: str) -> None:
    """Aplica a troca de provider/model: settings.json + os.environ + singletons LLM."""
    # 1. Persiste em settings.json
    runtime_settings.set_active_model(provider, model)

    # 2. Atualiza os.environ (efeito imediato para load_llm())
    os.environ["LLM_PROVIDER"] = provider
    if env_var := PROVIDER_MODEL_ENV.get(provider):
        os.environ[env_var] = model

    # 3. Atualiza o singleton Settings em memória
    try:
        settings.llm_provider = provider  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
        settings.set_model(provider, model)
    except Exception as e:
        logger.warning("Erro ao atualizar settings singleton: %s", e)

    # 4. Reseta singletons dos agentes → próxima chamada cria novo LLM
    reset_llm_singletons()
    logger.info("Model aplicado: provider=%s model=%s", provider, model)


# ---------------------------------------------------------------------------
# Backward-compat aliases (used by code that imported private names)
# ---------------------------------------------------------------------------

_PROVIDER_API_KEY_ENV = PROVIDER_API_KEY_ENV
_PROVIDER_MODEL_ENV = PROVIDER_MODEL_ENV
_PROVIDER_DISPLAY = PROVIDER_DISPLAY
_PROVIDER_KEY_URL = PROVIDER_KEY_URL
_PROVIDER_COLOR = PROVIDER_COLOR
_find_provider_for_model = find_provider_for_model
_has_api_key = has_api_key
_reset_llm_singletons = reset_llm_singletons
_save_api_key_to_env = save_api_key_to_env
_apply_model_change = apply_model_change
