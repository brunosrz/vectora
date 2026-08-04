"""GET /skills/catalog — catálogo curado de skills do registry remoto,
distinto de GET /skills (que lista as instaladas)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.api.handlers import skills as skills_handler


@pytest.mark.asyncio
async def test_get_skills_catalog_returns_remote_entries(monkeypatch):
    monkeypatch.setattr(
        skills_handler.registry_client,
        "fetch_catalog",
        AsyncMock(return_value=[{"id": "s1", "name": "Skill 1"}]),
    )

    result = await skills_handler.get_skills_catalog()

    assert result == {"entries": [{"id": "s1", "name": "Skill 1"}], "total": 1}


@pytest.mark.asyncio
async def test_get_skills_catalog_empty_is_not_error(monkeypatch):
    monkeypatch.setattr(
        skills_handler.registry_client, "fetch_catalog", AsyncMock(return_value=[])
    )

    result = await skills_handler.get_skills_catalog()

    assert result == {"entries": [], "total": 0}
