"""Handler /rag — settings de RAG + listagem/limpeza de coleções."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


class TestRagSettingsEndpoints:
    @pytest.mark.asyncio
    async def test_get_returns_runtime_settings(self, tmp_path):
        from backend.api.handlers import rag as handler
        from backend.services.runtime_settings import RuntimeSettings

        rs = RuntimeSettings(path=tmp_path / "settings.json")
        # O handler importa runtime_settings localmente; patcha o módulo origem.
        with patch("backend.services.runtime_settings.runtime_settings", rs):
            out = await handler.get_rag_settings()
        assert out["reranker_enabled"] is True
        assert out["reranker_top_k"] == 5

    @pytest.mark.asyncio
    async def test_patch_updates_and_returns(self, tmp_path):
        from backend.api.handlers import rag as handler
        from backend.api.handlers.rag import RagSettingsBody
        from backend.services.runtime_settings import RuntimeSettings

        rs = RuntimeSettings(path=tmp_path / "settings.json")
        with patch("backend.services.runtime_settings.runtime_settings", rs):
            out = await handler.patch_rag_settings(
                RagSettingsBody(reranker_enabled=False, reranker_top_k=9)
            )
        assert out["reranker_enabled"] is False
        assert out["reranker_top_k"] == 9


class TestRagCollections:
    @pytest.mark.asyncio
    async def test_list_empty_when_lancedb_unavailable(self):
        from backend.api.handlers import rag as handler

        with patch.object(handler, "_connect_lancedb", AsyncMock(return_value=None)):
            out = await handler.list_collections()
        assert out == {"collections": []}

    @pytest.mark.asyncio
    async def test_delete_raises_503_when_unavailable(self):
        from fastapi import HTTPException

        from backend.api.handlers import rag as handler

        with patch.object(handler, "_connect_lancedb", AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc:
                await handler.delete_collection("articles")
        assert exc.value.status_code == 503
