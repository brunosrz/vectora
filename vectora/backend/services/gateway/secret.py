"""Auto-geração do `VECTORA_APP_SECRET` — sem ele o `GatewayClient` nunca
tenta se registrar (`api/server.py`), então o gateway fica sempre
`never_connected` numa instalação nova. Cada instalação gera o seu próprio
secret (mais seguro que embutir um valor fixo no binário, que seria
idêntico em toda instalação) e persiste em `~/.vectora/.env`, reaproveitando
`upsert_env_key` (mesmo mecanismo já usado por `apply_llm_env_key`).
"""

from __future__ import annotations

import logging
import os
import secrets

logger = logging.getLogger(__name__)

_APP_SECRET_ENV_VAR = "VECTORA_APP_SECRET"  # noqa: S105 # nosec B105 -- nome de env var, nao segredo


def ensure_app_secret() -> str:
    """Retorna o `VECTORA_APP_SECRET` já configurado ou gera um novo.

    Idempotente: se já existe (env ou settings), retorna sem regerar. Só
    gera e persiste quando estiver realmente vazio.
    """
    from backend.cli.keys import upsert_env_key
    from backend.services.env_keys import default_env_file
    from backend.settings import settings

    existing = settings.vectora_app_secret or os.environ.get(_APP_SECRET_ENV_VAR, "")
    if existing:
        return existing

    generated = secrets.token_hex(32)
    env_file = default_env_file()
    upsert_env_key(env_file, _APP_SECRET_ENV_VAR, generated)
    os.environ[_APP_SECRET_ENV_VAR] = generated
    settings.vectora_app_secret = generated
    logger.info("gateway: VECTORA_APP_SECRET gerado e persistido em %s", env_file)
    return generated


__all__ = ["ensure_app_secret"]
