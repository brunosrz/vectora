"""Testes unitários de `LanceDBBackend.search_text` — mocka `lancedb.connect_async`
pra pegar bug estrutural (nome de parâmetro errado, parsing de forma de
resposta errada) sem depender de um banco LanceDB real em disco."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from backend.storage.vectorstore.lancedb_backend import LanceDBBackend


@pytest.fixture
def backend():
    return LanceDBBackend(lancedb_dir="/tmp/fake-lancedb")


@pytest.fixture
def mock_db():
    db = AsyncMock()
    with patch(
        "backend.storage.vectorstore.lancedb_backend.lancedb.connect_async",
        AsyncMock(return_value=db),
    ):
        yield db


def _fts_query(df: pd.DataFrame) -> MagicMock:
    """Molde da cadeia `table.search(query, query_type="fts").limit(n).to_pandas()`
    — `.search()`/`.limit()` são síncronos, só `.to_pandas()` é async."""
    query_obj = MagicMock()
    query_obj.limit.return_value.to_pandas = AsyncMock(return_value=df)
    return query_obj


class TestLanceDBBackendSearchText:
    @pytest.mark.asyncio
    async def test_search_text_retorna_hits_do_indice_fts(self, backend, mock_db):
        table = AsyncMock()
        table.create_index = AsyncMock()
        df = pd.DataFrame(
            [
                {
                    "id": "doc-1",
                    "_score": 3.5,
                    "text": "erro de autenticação JWT",
                    "metadata": "{}",
                }
            ]
        )
        table.search = MagicMock(return_value=_fts_query(df))
        mock_db.open_table.return_value = table

        hits = await backend.search_text("articles", "JWT", limit=5)

        assert len(hits) == 1
        assert hits[0].id == "doc-1"
        assert hits[0].score == pytest.approx(3.5)
        assert hits[0].content == "erro de autenticação JWT"
        table.create_index.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search_text_colecao_inexistente_retorna_vazio_sem_propagar(
        self, backend, mock_db
    ):
        mock_db.open_table.side_effect = RuntimeError("tabela não existe")

        hits = await backend.search_text("nao-existe", "query", limit=5)

        assert hits == []

    @pytest.mark.asyncio
    async def test_search_text_create_index_falhando_ainda_tenta_buscar(
        self, backend, mock_db
    ):
        """`create_index` falha quando o índice já existe (comportamento
        normal em rodadas subsequentes) — não pode impedir a busca."""
        table = AsyncMock()
        table.create_index = AsyncMock(side_effect=RuntimeError("índice já existe"))
        df = pd.DataFrame(
            [{"id": "doc-1", "_score": 1.0, "text": "conteúdo", "metadata": "{}"}]
        )
        table.search = MagicMock(return_value=_fts_query(df))
        mock_db.open_table.return_value = table

        hits = await backend.search_text("articles", "conteúdo", limit=5)

        assert len(hits) == 1

    @pytest.mark.asyncio
    async def test_search_text_fts_indisponivel_retorna_vazio_sem_propagar(
        self, backend, mock_db
    ):
        table = AsyncMock()
        table.create_index = AsyncMock()
        table.search = MagicMock(side_effect=RuntimeError("FTS não suportado"))
        mock_db.open_table.return_value = table

        hits = await backend.search_text("articles", "query", limit=5)

        assert hits == []


class TestLanceDBBackendListRows:
    """Regressão ao vivo: `list_rows` derrubava o resumo RAG do workspace
    toda vez que uma linha tinha vetor de verdade — `row.get("vector")`
    devolve `numpy.ndarray`, e `array or []` explode com "truth value of
    an array with more than one element is ambiguous"."""

    @pytest.mark.asyncio
    async def test_linha_com_vetor_multi_elemento_nao_lanca(self, backend, mock_db):
        table = AsyncMock()
        df = pd.DataFrame(
            [
                {
                    "id": "doc-1",
                    "vector": np.array([0.1, 0.2, 0.3]),
                    "text": "conteúdo",
                    "metadata": "{}",
                }
            ]
        )
        table.to_pandas = AsyncMock(return_value=df)
        mock_db.open_table = AsyncMock(return_value=table)

        rows = await backend.list_rows("articles")

        assert len(rows) == 1
        assert rows[0].vector == pytest.approx([0.1, 0.2, 0.3])

    @pytest.mark.asyncio
    async def test_linha_sem_vetor_vira_lista_vazia(self, backend, mock_db):
        """Coluna `vector` ausente na linha vem como escalar `NaN` (float)
        do pandas, não `None` — `list(NaN)` também lançaria sem o guard."""
        table = AsyncMock()
        df = pd.DataFrame(
            [
                {
                    "id": "doc-2",
                    "vector": float("nan"),
                    "text": "sem vetor",
                    "metadata": "{}",
                }
            ]
        )
        table.to_pandas = AsyncMock(return_value=df)
        mock_db.open_table = AsyncMock(return_value=table)

        rows = await backend.list_rows("articles")

        assert rows[0].vector == []

    @pytest.mark.asyncio
    async def test_colecao_inexistente_retorna_vazio_sem_propagar(
        self, backend, mock_db
    ):
        mock_db.open_table = AsyncMock(side_effect=RuntimeError("tabela não existe"))

        rows = await backend.list_rows("nao-existe")

        assert rows == []
