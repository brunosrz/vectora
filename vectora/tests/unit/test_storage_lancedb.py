"""Tests — storage/lancedb/ (F1) e get_vector_store (F3/F6).

Modo "lite" usa diretório temporário; modo "complete" (Qdrant) é skippado
sem qdrant_url configurado.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def reset_storage_singletons():
    import backend.storage.factory as _fac

    _fac._reset_singletons()
    yield
    _fac._reset_singletons()


class TestLanceDBConnection:
    """Cache de conexão LanceDB (F1)."""

    @pytest.mark.asyncio
    async def test_connection_returns_db(self, tmp_path):
        from backend.storage.lancedb.connection import get_lancedb

        db = await get_lancedb(str(tmp_path))
        assert db is not None

    @pytest.mark.asyncio
    async def test_connection_singleton(self, tmp_path):
        from backend.storage.lancedb.connection import get_lancedb

        db1 = await get_lancedb(str(tmp_path))
        db2 = await get_lancedb(str(tmp_path))
        assert db1 is db2


class TestGetVectorStore:
    """get_vector_store abre AsyncTable existente ou retorna None (F3/F6)."""

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent(self, tmp_path):
        """Tabela inexistente retorna None — comportamento documentado."""
        from backend.storage.factory import get_vector_store

        tbl = await get_vector_store("articles", path=str(tmp_path / "lancedb"))
        assert tbl is None

    @pytest.mark.asyncio
    async def test_returns_table_when_exists(self, tmp_path):
        """Tabela existente é retornada como AsyncTable."""
        import lancedb
        import pyarrow as pa

        from backend.storage.factory import get_vector_store

        lancedb_path = str(tmp_path / "lancedb")

        # Cria a tabela primeiro via lancedb diretamente
        db = await lancedb.connect_async(lancedb_path)
        schema = pa.schema([pa.field("id", pa.string()), pa.field("text", pa.string())])
        await db.create_table("articles", schema=schema)

        tbl = await get_vector_store("articles", path=lancedb_path)
        assert tbl is not None

    @pytest.mark.asyncio
    async def test_get_lancedb_connection_caches(self, tmp_path):
        """Duas chamadas com mesmo path retornam mesma conexão LanceDB."""
        from backend.storage.lancedb.connection import get_lancedb

        db1 = await get_lancedb(str(tmp_path / "db1"))
        db2 = await get_lancedb(str(tmp_path / "db1"))
        assert db1 is db2

    @pytest.mark.asyncio
    async def test_tabela_existente_agenda_otimizacao_periodica_uma_vez(self, tmp_path):
        """`optimize_table`/`schedule_optimize` existiam mas nunca eram
        chamados em lugar nenhum do app — nenhuma tabela LanceDB recebia
        compactação periódica. O primeiro `get_vector_store` bem-sucedido
        de uma coleção agenda a task; chamadas seguintes reusam a mesma
        (não agenda duas vezes)."""
        import lancedb
        import pyarrow as pa

        import backend.storage.factory as _fac
        from backend.storage.factory import get_vector_store

        lancedb_path = str(tmp_path / "lancedb")
        db = await lancedb.connect_async(lancedb_path)
        schema = pa.schema([pa.field("id", pa.string()), pa.field("text", pa.string())])
        await db.create_table("articles", schema=schema)

        await get_vector_store("articles", path=lancedb_path)
        cache_key = f"{lancedb_path}::articles"
        assert cache_key in _fac._optimize_tasks
        task = _fac._optimize_tasks[cache_key]
        assert not task.done()

        await get_vector_store("articles", path=lancedb_path)
        assert _fac._optimize_tasks[cache_key] is task

    @pytest.mark.asyncio
    async def test_tabela_inexistente_nao_agenda_otimizacao(self, tmp_path):
        """Erro/borda: `table is None` (coleção ainda não criada) não deve
        tentar agendar otimização de uma tabela que não existe."""
        import backend.storage.factory as _fac
        from backend.storage.factory import get_vector_store

        lancedb_path = str(tmp_path / "lancedb")
        tbl = await get_vector_store("nao-existe", path=lancedb_path)

        assert tbl is None
        assert _fac._optimize_tasks == {}
