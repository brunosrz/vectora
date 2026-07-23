"""Tools de auto-instalação da Library: MCP/Skills/Memory Library.

Cobre `install_mcp_from_registry`, `install_skill_from_catalog` e
`install_memory_bucket` — happy path e erro/borda de cada uma, reaproveitando
a mesma lógica `_impl` que os handlers HTTP já expõem, sem duplicar.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from backend.tools.library import (
    install_mcp_from_registry,
    install_memory_bucket,
    install_skill_from_catalog,
)


def _config(user_id: str = "local") -> dict:
    return {"configurable": {"user_id": user_id}}


# ---------------------------------------------------------------------------
# install_mcp_from_registry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_install_mcp_from_registry_installs_connector_without_env_vars(
    monkeypatch,
):
    from backend.api.handlers import mcp_marketplace

    connector = mcp_marketplace.MCPConnector(
        id="filesystem",
        name="Filesystem",
        description="d",
        install_cmd="npx -y @modelcontextprotocol/server-filesystem",
        env_vars=[],
        vectora_verified=True,
    )
    monkeypatch.setattr(
        mcp_marketplace,
        "list_registry",
        AsyncMock(return_value=[connector]),
    )
    monkeypatch.setattr(
        mcp_marketplace,
        "install_mcp",
        AsyncMock(return_value={"status": "installed", "mcp_id": "filesystem"}),
    )

    result = json.loads(
        await install_mcp_from_registry.ainvoke(
            {"connector_id": "filesystem", "config": _config()}
        )
    )

    assert result == {"status": "installed", "mcp_id": "filesystem"}


@pytest.mark.asyncio
async def test_install_mcp_from_registry_missing_env_vars_does_not_install(
    monkeypatch,
):
    from backend.api.handlers import mcp_marketplace

    connector = mcp_marketplace.MCPConnector(
        id="brave-search",
        name="Brave Search",
        description="d",
        install_cmd="npx -y @modelcontextprotocol/server-brave-search",
        env_vars=["BRAVE_API_KEY_DOES_NOT_EXIST_XYZ"],
    )
    monkeypatch.setattr(
        mcp_marketplace, "list_registry", AsyncMock(return_value=[connector])
    )
    install_spy = AsyncMock()
    monkeypatch.setattr(mcp_marketplace, "install_mcp", install_spy)
    monkeypatch.delenv("BRAVE_API_KEY_DOES_NOT_EXIST_XYZ", raising=False)

    result = json.loads(
        await install_mcp_from_registry.ainvoke(
            {"connector_id": "brave-search", "config": _config()}
        )
    )

    assert result["status"] == "error"
    assert result["missing_env_vars"] == ["BRAVE_API_KEY_DOES_NOT_EXIST_XYZ"]
    install_spy.assert_not_called()


@pytest.mark.asyncio
async def test_install_mcp_from_registry_unknown_connector_returns_error(monkeypatch):
    from backend.api.handlers import mcp_marketplace

    monkeypatch.setattr(mcp_marketplace, "list_registry", AsyncMock(return_value=[]))

    result = json.loads(
        await install_mcp_from_registry.ainvoke(
            {"connector_id": "does-not-exist", "config": _config()}
        )
    )

    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# install_skill_from_catalog
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_install_skill_from_catalog_installs_skill(monkeypatch):
    from backend.services import registry_client
    from backend.workspace import skills as skills_mod

    monkeypatch.setattr(
        registry_client,
        "fetch_catalog",
        AsyncMock(
            return_value=[
                {
                    "id": "pdf-extract",
                    "name": "PDF Extract",
                    "source": "https://github.com/example/pdf-extract-skill",
                }
            ]
        ),
    )

    class _FakeSkill:
        id = "pdf-extract"

    monkeypatch.setattr(
        skills_mod, "install_skill", lambda user_id, source: _FakeSkill()
    )

    result = json.loads(
        await install_skill_from_catalog.ainvoke(
            {"skill_id": "pdf-extract", "config": _config()}
        )
    )

    assert result == {"status": "installed", "skill_id": "pdf-extract"}


@pytest.mark.asyncio
async def test_install_skill_from_catalog_unknown_skill_returns_error(monkeypatch):
    from backend.services import registry_client

    monkeypatch.setattr(registry_client, "fetch_catalog", AsyncMock(return_value=[]))

    result = json.loads(
        await install_skill_from_catalog.ainvoke(
            {"skill_id": "does-not-exist", "config": _config()}
        )
    )

    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# install_memory_bucket
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_install_memory_bucket_installs_collection(monkeypatch):
    from backend.services import memory_library

    monkeypatch.setattr(
        memory_library,
        "download_memory_bucket",
        AsyncMock(return_value="shared_docs-2024"),
    )

    result = json.loads(await install_memory_bucket.ainvoke({"bucket_id": "docs-2024"}))

    assert result == {"status": "installed", "collection": "shared_docs-2024"}


@pytest.mark.asyncio
async def test_install_memory_bucket_error_returns_status_error_not_raised(
    monkeypatch,
):
    from backend.services import memory_library

    async def _boom(bucket_id: str) -> str:
        raise memory_library.MemoryLibraryError("embed_model incompatível")

    monkeypatch.setattr(memory_library, "download_memory_bucket", _boom)

    result = json.loads(await install_memory_bucket.ainvoke({"bucket_id": "docs-2024"}))

    assert result["status"] == "error"
    assert "embed_model incompatível" in result["error"]
