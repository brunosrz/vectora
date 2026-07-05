"""Handler /rag — settings de RAG + listagem/limpeza de coleções."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


class TestRagSettingsEndpoints:
    @pytest.mark.asyncio
    async def test_get_returns_runtime_settings(self, tmp_path):
        from backend.api.handlers import rag as handler
        from backend.workspace.runtime_settings import RuntimeSettings

        rs = RuntimeSettings(path=tmp_path / "settings.json")
        # O handler importa runtime_settings localmente; patcha o módulo origem.
        with patch("backend.workspace.runtime_settings.runtime_settings", rs):
            out = await handler.get_rag_settings()
        assert out["reranker_enabled"] is True
        assert out["reranker_top_k"] == 5

    @pytest.mark.asyncio
    async def test_patch_updates_and_returns(self, tmp_path):
        from backend.api.handlers import rag as handler
        from backend.api.handlers.rag import RagSettingsBody
        from backend.workspace.runtime_settings import RuntimeSettings

        rs = RuntimeSettings(path=tmp_path / "settings.json")
        with patch("backend.workspace.runtime_settings.runtime_settings", rs):
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


class TestWorkspaceRagSummary:
    """GET /rag/workspace-summary — RAG é escopo de workspace, não de thread.

    Devolve o que já está indexado NAQUELE workspace, direto do LanceDB,
    contando linhas por coleção cujo metadata.workspace_id bate — independente
    de thread ou de qualquer evento de streaming em andamento.
    """

    @pytest.mark.asyncio
    async def test_empty_when_lancedb_unavailable(self):
        from backend.api.handlers import rag as handler

        with patch.object(handler, "_connect_lancedb", AsyncMock(return_value=None)):
            out = await handler.get_workspace_rag_summary("ws-1")
        assert out == {"collections": []}

    @pytest.mark.asyncio
    async def test_counts_only_rows_matching_workspace_id(self):
        import pandas as pd

        from backend.api.handlers import rag as handler

        df = pd.DataFrame(
            {
                "id": ["1", "2", "3"],
                "metadata": [
                    '{"workspace_id": "ws-1", "source": "a.md"}',
                    '{"workspace_id": "ws-2", "source": "b.md"}',
                    '{"workspace_id": "ws-1", "source": "c.md"}',
                ],
            }
        )
        fake_table = AsyncMock()
        fake_table.to_pandas = AsyncMock(return_value=df)
        fake_db = AsyncMock()
        fake_db.list_tables = AsyncMock(
            return_value=type("T", (), {"tables": ["articles"]})()
        )
        fake_db.open_table = AsyncMock(return_value=fake_table)

        with patch.object(handler, "_connect_lancedb", AsyncMock(return_value=fake_db)):
            out = await handler.get_workspace_rag_summary("ws-1")

        assert out == {"collections": [{"name": "articles", "count": 2}]}

    @pytest.mark.asyncio
    async def test_omits_collections_with_zero_matches(self):
        import pandas as pd

        from backend.api.handlers import rag as handler

        df = pd.DataFrame({"id": ["1"], "metadata": ['{"workspace_id": "ws-other"}']})
        fake_table = AsyncMock()
        fake_table.to_pandas = AsyncMock(return_value=df)
        fake_db = AsyncMock()
        fake_db.list_tables = AsyncMock(
            return_value=type("T", (), {"tables": ["web_cache"]})()
        )
        fake_db.open_table = AsyncMock(return_value=fake_table)

        with patch.object(handler, "_connect_lancedb", AsyncMock(return_value=fake_db)):
            out = await handler.get_workspace_rag_summary("ws-1")

        assert out == {"collections": []}

    @pytest.mark.asyncio
    async def test_tolerates_one_broken_collection_and_still_reports_others(self):
        """Edge — uma coleção corrompida/sem schema não deve derrubar as demais."""
        import pandas as pd

        from backend.api.handlers import rag as handler

        good_df = pd.DataFrame({"id": ["1"], "metadata": ['{"workspace_id": "ws-1"}']})

        async def _open_table(name: str):
            if name == "broken":
                raise RuntimeError("tabela corrompida")
            table = AsyncMock()
            table.to_pandas = AsyncMock(return_value=good_df)
            return table

        fake_db = AsyncMock()
        fake_db.list_tables = AsyncMock(
            return_value=type("T", (), {"tables": ["broken", "articles"]})()
        )
        fake_db.open_table = _open_table

        with patch.object(handler, "_connect_lancedb", AsyncMock(return_value=fake_db)):
            out = await handler.get_workspace_rag_summary("ws-1")

        assert out == {"collections": [{"name": "articles", "count": 1}]}
