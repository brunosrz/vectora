"""Testes para backend/storage/lancedb/index.py.

Cobertura era zero antes destes testes. Foi assim que dois bugs reais
passaram despercebidos: `create_fts_index` chamava
`table.create_fts_index(...)`, método que não existe em `AsyncTable` (só
existe `create_index(column, config=FTS(...))`) — o `try/except` engolia o
`AttributeError` resultante como um warning genérico "falha ao criar FTS",
então nenhum índice FTS jamais foi criado por este caminho (o único
caminho que de fato funciona é o inline em `lancedb_backend.py`, agora
consolidado para usar este helper corrigido).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from backend.storage.lancedb.index import create_fts_index, create_ivf_index


class _FakeTable:
    def __init__(self, name: str = "articles", row_count: int = 0) -> None:
        self.name = name
        self._row_count = row_count
        self.create_index = AsyncMock()

    async def count_rows(self) -> int:
        return self._row_count


class TestCreateIvfIndex:
    async def test_cria_indice_quando_atinge_min_rows(self):
        table = _FakeTable(row_count=15_000)

        created = await create_ivf_index(table, min_rows=10_000)

        assert created is True
        table.create_index.assert_awaited_once()
        assert table.create_index.await_args is not None
        _, kwargs = table.create_index.await_args
        assert kwargs["index_type"] == "IVF_PQ"

    async def test_abaixo_do_minimo_pula_sem_erro(self):
        table = _FakeTable(row_count=100)

        created = await create_ivf_index(table, min_rows=10_000)

        assert created is False
        table.create_index.assert_not_awaited()

    async def test_indice_ja_existente_nao_propaga(self):
        table = _FakeTable(row_count=20_000)
        table.create_index = AsyncMock(side_effect=RuntimeError("index already exists"))

        created = await create_ivf_index(table, min_rows=10_000)

        assert created is False

    async def test_count_rows_falhando_retorna_false_sem_lancar(self):
        class _BoomTable(_FakeTable):
            async def count_rows(self) -> int:
                msg = "storage indisponível"
                raise RuntimeError(msg)

        table = _BoomTable()

        created = await create_ivf_index(table, min_rows=10_000)

        assert created is False


class TestCreateFtsIndex:
    async def test_cria_via_create_index_com_config_fts(self):
        table = _FakeTable()

        created = await create_fts_index(table, "text")

        assert created is True
        table.create_index.assert_awaited_once()
        assert table.create_index.await_args is not None
        args, kwargs = table.create_index.await_args
        assert args[0] == "text"
        assert kwargs["replace"] is False
        assert kwargs["config"].language == "English"
        # Regressão real: o método antigo (table.create_fts_index) não
        # existe em AsyncTable — este teste garante que o caminho certo
        # (table.create_index com config=FTS(...)) é o que é chamado.
        assert not hasattr(table, "create_fts_index")

    async def test_idioma_customizado_repassado_pro_fts_config(self):
        table = _FakeTable()

        await create_fts_index(table, "text", language="Portuguese")

        assert table.create_index.await_args is not None
        _, kwargs = table.create_index.await_args
        assert kwargs["config"].language == "Portuguese"

    async def test_indice_ja_existente_nao_propaga(self):
        table = _FakeTable()
        table.create_index = AsyncMock(side_effect=RuntimeError("FTS already exists"))

        created = await create_fts_index(table, "text")

        assert created is False

    async def test_falha_generica_nao_propaga(self):
        table = _FakeTable()
        table.create_index = AsyncMock(side_effect=RuntimeError("storage indisponível"))

        created = await create_fts_index(table, "text")

        assert created is False
