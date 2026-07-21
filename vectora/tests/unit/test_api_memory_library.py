"""TDD — Memory Library (handler HTTP).

GET  /rag-library/catalog — lista buckets publicados
POST /rag-library/install — baixa e instala um bucket como coleção LanceDB
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.api.handlers.memory_library import (
    InstallRequest,
    get_catalog,
    post_install,
)
from backend.services.memory_library import MemoryLibraryError


@pytest.mark.asyncio
async def test_get_catalog_returns_entries_from_service(monkeypatch):
    from backend.api.handlers import memory_library

    monkeypatch.setattr(
        memory_library,
        "_list_catalog",
        AsyncMock(return_value=[{"id": "b1", "name": "Bucket 1", "verified": True}]),
    )

    result = await get_catalog()

    assert result == [{"id": "b1", "name": "Bucket 1", "verified": True}]


@pytest.mark.asyncio
async def test_get_catalog_degrades_to_empty_list_on_service_failure(monkeypatch):
    from backend.api.handlers import memory_library

    monkeypatch.setattr(memory_library, "_list_catalog", AsyncMock(return_value=[]))

    result = await get_catalog()

    assert result == []


@pytest.mark.asyncio
async def test_post_install_returns_collection_on_success(monkeypatch):
    from backend.api.handlers import memory_library

    monkeypatch.setattr(
        memory_library,
        "download_memory_bucket",
        AsyncMock(return_value="shared_b1"),
    )

    result = await post_install(InstallRequest(bucket_id="b1"))

    assert result == {"status": "installed", "collection": "shared_b1"}


@pytest.mark.asyncio
async def test_post_install_incompatible_embed_model_returns_error_not_exception(
    monkeypatch,
):
    from backend.api.handlers import memory_library

    monkeypatch.setattr(
        memory_library,
        "download_memory_bucket",
        AsyncMock(side_effect=MemoryLibraryError("embedder incompatível")),
    )

    result = await post_install(InstallRequest(bucket_id="b1"))

    assert result["status"] == "error"
    assert "embedder" in result["error"]
