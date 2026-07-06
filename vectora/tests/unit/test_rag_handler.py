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


class TestRagSearch:
    """POST /rag/search — busca direta do usuário, mesma vector_search do agente."""

    @pytest.mark.asyncio
    async def test_search_with_explicit_collection_returns_sorted_results(self):
        import json

        from backend.api.handlers import rag as handler
        from backend.api.handlers.rag import RagSearchBody
        from backend.tools.rag import vector_search

        raw = json.dumps(
            {
                "status": "success",
                "results": [
                    {"content": "b", "score": 0.9},
                    {"content": "a", "score": 0.1},
                ],
            }
        )
        with patch.object(vector_search, "coroutine", AsyncMock(return_value=raw)):
            out = await handler.search_rag(
                RagSearchBody(query="oi", collection="articles", limit=5)
            )

        assert out["query"] == "oi"
        assert [r["content"] for r in out["results"]] == ["a", "b"]
        assert all(r["collection"] == "articles" for r in out["results"])

    @pytest.mark.asyncio
    async def test_search_without_collection_or_workspace_falls_back_to_articles(self):
        from backend.api.handlers import rag as handler
        from backend.api.handlers.rag import RagSearchBody
        from backend.tools.rag import vector_search

        mocked = AsyncMock(return_value='{"status": "no_results", "results": []}')
        with patch.object(vector_search, "coroutine", mocked):
            out = await handler.search_rag(RagSearchBody(query="oi"))

        mocked.assert_awaited_once_with(query="oi", collection="articles", limit=5)
        assert out["results"] == []

    @pytest.mark.asyncio
    async def test_search_with_workspace_but_nothing_indexed_returns_empty(self):
        """Edge — workspace sem nenhuma coleção indexada não deve chamar vector_search."""
        from backend.api.handlers import rag as handler
        from backend.api.handlers.rag import RagSearchBody
        from backend.tools.rag import vector_search

        with (
            patch.object(
                handler,
                "get_workspace_rag_summary",
                AsyncMock(return_value={"collections": []}),
            ),
            patch.object(vector_search, "coroutine", AsyncMock()) as mocked,
        ):
            out = await handler.search_rag(
                RagSearchBody(query="oi", workspace_id="ws-vazio")
            )

        mocked.assert_not_awaited()
        assert out == {"results": []}


class TestRagCollectionsRealLanceDB:
    """LanceDB é embedded (file-based, sem rede) — roda contra dados reais,
    validando o FORMATO do retorno (chaves/tipos), não conteúdo fixo.

    Mantém as classes TestRagCollections/TestWorkspaceRagSummary acima (que
    mockam `_connect_lancedb`) — esta é a 2ª passada, sem mock nenhum de
    storage, só a instância Cohere/embedding continua fora do escopo (RAG
    handler nunca chama embedding pra listar/gerenciar coleções).
    """

    @pytest.mark.asyncio
    async def test_list_collections_shape_with_real_table(self, tmp_path):
        import lancedb
        import pyarrow as pa

        from backend.api.handlers import rag as handler
        from backend.settings import settings

        db = await lancedb.connect_async(str(tmp_path))
        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("text", pa.string()),
                pa.field("metadata", pa.string()),
            ]
        )
        table = await db.create_table("articles", schema=schema)
        await table.add(
            [{"id": "1", "text": "conteudo", "metadata": '{"workspace_id": "ws-1"}'}]
        )

        with patch.object(settings, "lancedb_dir", tmp_path):
            out = await handler.list_collections()

        assert isinstance(out, dict)
        assert isinstance(out["collections"], list)
        assert len(out["collections"]) == 1
        collection = out["collections"][0]
        assert isinstance(collection["name"], str)
        assert isinstance(collection["count"], int)

    @pytest.mark.asyncio
    async def test_workspace_summary_shape_with_real_table(self, tmp_path):
        import lancedb
        import pyarrow as pa

        from backend.api.handlers import rag as handler
        from backend.settings import settings

        db = await lancedb.connect_async(str(tmp_path))
        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("text", pa.string()),
                pa.field("metadata", pa.string()),
            ]
        )
        table = await db.create_table("articles", schema=schema)
        await table.add(
            [
                {"id": "1", "text": "a", "metadata": '{"workspace_id": "ws-real"}'},
                {"id": "2", "text": "b", "metadata": '{"workspace_id": "outro"}'},
            ]
        )

        with patch.object(settings, "lancedb_dir", tmp_path):
            out = await handler.get_workspace_rag_summary("ws-real")

        assert isinstance(out, dict)
        assert isinstance(out["collections"], list)
        for entry in out["collections"]:
            assert set(entry.keys()) == {"name", "count"}
            assert isinstance(entry["name"], str)
            assert isinstance(entry["count"], int)
        # workspace_id filtra corretamente: só a linha de "ws-real" conta.
        assert out["collections"][0]["count"] == 1
