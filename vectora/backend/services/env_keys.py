"""Aplicação em runtime de API keys de LLM/search — fonte única compartilhada.

Evita a duplicação que causava o bug: `PATCH /admin/api-keys` e `POST /envs`
tinham cada um sua própria cópia da lógica "grava no .env + atualiza
os.environ + atualiza settings", e só a primeira estava correta — a
segunda gravava só no banco por-usuário, nunca chegando em `os.environ`.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

#: Env vars de LLM/search conhecidas pelo Vectora — qualquer uma delas
#: setada via `/envs` (não só via `/admin/api-keys`) precisa valer
#: imediatamente na próxima chamada ao provider, sem restart.
KNOWN_LLM_ENV_KEYS: frozenset[str] = frozenset(
    {
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "COHERE_API_KEY",
        "TAVILY_API_KEY",
        "OPENROUTER_API_KEY",
    }
)


def default_env_file() -> Path:
    """``~/.vectora/.env`` — mesmo arquivo que `PATCH /admin/api-keys` já usa."""
    p = Path.home() / ".vectora" / ".env"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def apply_llm_env_key(env_file: Path, env_var: str, value: str) -> None:
    """Persiste ``env_var=value`` em ``env_file``, ``os.environ`` e ``settings``.

    Nunca loga o valor — só o nome da env var (padrão de auditoria já usado
    em `patch_api_keys`). ``value`` vazia limpa a key (mesmo comportamento
    de `patch_api_keys`, que aceita string vazia pra "esquecer" uma key).
    """
    from backend.cli.keys import upsert_env_key

    v = value.strip()
    upsert_env_key(env_file, env_var, v)
    os.environ[env_var] = v

    try:
        from backend.settings import settings

        attr = env_var.lower()
        if hasattr(settings, attr):
            object.__setattr__(settings, attr, v or None)
    except Exception:
        logger.exception("env_keys: falha ao atualizar settings.%s", env_var.lower())
