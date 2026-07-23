"""Tools de auto-instalação da Library: MCP marketplace, catálogo de Skills e
Memory Library — mesma lógica que os handlers HTTP já usam (`_impl`
reaproveitado, nunca duplicado). Todas exigem aprovação humana
(`_REQUIRE_APPROVAL`, `backend/services/middleware.py`): instalar é uma
mudança persistente no ambiente do usuário.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from backend.services.env import get_env

logger = logging.getLogger(__name__)


def _user_id(config: RunnableConfig | None) -> str:
    configurable = (config or {}).get("configurable") or {}
    return str(configurable.get("user_id", "local"))


@tool(
    extras={
        "invalidates": ["mcp"],
        "destructive": True,
        "category": "library",
        "icon": "puzzle",
    }
)
async def install_mcp_from_registry(
    connector_id: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Instala um conector MCP do registry (curados + registry oficial de
    MCP) — mesma lista que a aba Library mostra. Se o conector exigir
    variáveis de ambiente ainda não configuradas, não instala e lista o que
    falta em vez de instalar incompleto.

    Args:
        connector_id: id do conector, como aparece em `GET /mcp/registry`.
    """
    try:
        from backend.api.handlers.mcp_marketplace import (
            InstallRequest,
            install_mcp,
            list_registry,
        )

        registry = await list_registry()
        connector = next((c for c in registry if c.id == connector_id), None)
        if connector is None:
            return json.dumps(
                {
                    "status": "error",
                    "error": f"conector '{connector_id}' não encontrado no registry",
                }
            )

        missing = [v for v in connector.env_vars if not get_env(v, strict=False)]
        if missing:
            return json.dumps(
                {
                    "status": "error",
                    "error": "variáveis de ambiente ausentes para instalar",
                    "missing_env_vars": missing,
                }
            )

        user_id = _user_id(config)
        result = await install_mcp(InstallRequest(mcp_id=connector_id), user_id)
        return json.dumps(result)
    except Exception as exc:
        logger.exception(
            "install_mcp_from_registry failed", extra={"connector_id": connector_id}
        )
        return json.dumps({"status": "error", "error": str(exc)})


@tool(
    extras={
        "invalidates": ["skills"],
        "destructive": True,
        "category": "library",
        "icon": "sparkles",
    }
)
async def install_skill_from_catalog(
    skill_id: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Instala uma skill curada do catálogo remoto (`GET /skills/catalog`) —
    distinto de escrever uma skill nova via `install_learned_skill`.

    Args:
        skill_id: id da skill no catálogo.
    """
    try:
        from backend.services import registry_client
        from backend.workspace.skills import install_skill

        entries = await registry_client.fetch_catalog("skills")
        entry = next((e for e in entries if e.get("id") == skill_id), None)
        if entry is None:
            return json.dumps(
                {
                    "status": "error",
                    "error": f"skill '{skill_id}' não encontrada no catálogo",
                }
            )

        user_id = _user_id(config)
        skill = install_skill(user_id, entry["source"])
        return json.dumps({"status": "installed", "skill_id": skill.id})
    except Exception as exc:
        logger.exception(
            "install_skill_from_catalog failed", extra={"skill_id": skill_id}
        )
        return json.dumps({"status": "error", "error": str(exc)})


@tool(
    extras={
        "invalidates": ["memory"],
        "destructive": True,
        "category": "library",
        "icon": "database",
    }
)
async def install_memory_bucket(bucket_id: str) -> str:
    """Baixa e instala um bucket da Vectora Memory Library como coleção
    LanceDB isolada (`shared_{bucket_id}`) — mesmo fluxo de
    `POST /rag-library/install`.

    Args:
        bucket_id: id do bucket, como aparece em `GET /rag-library/catalog`.
    """
    from backend.services.memory_library import (
        MemoryLibraryError,
        download_memory_bucket,
    )

    try:
        collection = await download_memory_bucket(bucket_id)
        return json.dumps({"status": "installed", "collection": collection})
    except MemoryLibraryError as exc:
        return json.dumps({"status": "error", "error": str(exc)})
    except Exception as exc:
        logger.exception("install_memory_bucket failed", extra={"bucket_id": bucket_id})
        return json.dumps({"status": "error", "error": str(exc)})
