"""Testes de integração — PostgreSQL (asyncpg + migrations + pool).

Requer Postgres rodando (vectora-postgres via docker).
Os fixtures de conftest.py sobem o container automaticamente se Docker estiver
disponível; do contrário, todos os testes são pulados.
"""

from __future__ import annotations

import pytest


class TestPostgresMigrationRunner:
    """PostgresMigrationRunner aplica e rastreia migrations Postgres."""

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_upgrade_applies_pending(self, pg_conn):
        """upgrade() aplica as migrations pendentes e retorna a lista de versões."""
        from backend.storage.migrations.postgres_runner import PostgresMigrationRunner

        runner = PostgresMigrationRunner(pg_conn)
        applied = await runner.upgrade()
        assert isinstance(applied, list)

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_upgrade_idempotent(self, pg_conn):
        """Segunda chamada a upgrade() não re-aplica migrations já aplicadas."""
        from backend.storage.migrations.postgres_runner import PostgresMigrationRunner

        runner = PostgresMigrationRunner(pg_conn)
        await runner.upgrade()
        second = await runner.upgrade()
        assert second == []

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_schema_migrations_table_created(self, pg_conn):
        """Tabela schema_migrations é criada automaticamente."""
        from backend.storage.migrations.postgres_runner import PostgresMigrationRunner

        runner = PostgresMigrationRunner(pg_conn)
        await runner.upgrade()

        row = await pg_conn.fetchrow(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'schema_migrations'"
        )
        assert row is not None

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_status_lists_all_migrations(self, pg_conn):
        """status() retorna MigrationStatus para cada arquivo .sql encontrado."""
        from backend.storage.migrations.postgres_runner import (
            MigrationStatus,
            PostgresMigrationRunner,
        )

        runner = PostgresMigrationRunner(pg_conn)
        await runner.upgrade()
        statuses = await runner.status()

        assert len(statuses) >= 1
        assert all(isinstance(s, MigrationStatus) for s in statuses)
        assert all(s.applied for s in statuses)

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_status_shows_pending_for_new_migration(self, pg_conn, tmp_path):
        """Migration ainda não aplicada aparece como applied=False no status."""
        from backend.storage.migrations.postgres_runner import PostgresMigrationRunner

        sql_file = tmp_path / "0099_test_table.sql"
        sql_file.write_text(
            "-- up\nCREATE TABLE IF NOT EXISTS _test_pg_runner (id TEXT);\n"
            "-- down\nDROP TABLE IF EXISTS _test_pg_runner;\n"
        )

        runner = PostgresMigrationRunner(pg_conn, migrations_dir=tmp_path)
        statuses = await runner.status()
        pending = [s for s in statuses if not s.applied]
        assert len(pending) == 1
        assert pending[0].version == "0099"

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_upgrade_error_noop_on_empty_dir(self, pg_conn, tmp_path):
        """upgrade() em diretório sem .sql retorna lista vazia sem erro."""
        from backend.storage.migrations.postgres_runner import PostgresMigrationRunner

        runner = PostgresMigrationRunner(pg_conn, migrations_dir=tmp_path)
        applied = await runner.upgrade()
        assert applied == []

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_downgrade_reverts_migration(self, pg_conn, tmp_path):
        """downgrade() reverte a migration aplicada e remove do tracking."""
        from backend.storage.migrations.postgres_runner import PostgresMigrationRunner

        sql_file = tmp_path / "0001_temp.sql"
        sql_file.write_text(
            "-- up\nCREATE TABLE IF NOT EXISTS _test_downgrade (id TEXT);\n"
            "-- down\nDROP TABLE IF EXISTS _test_downgrade;\n"
        )

        runner = PostgresMigrationRunner(pg_conn, migrations_dir=tmp_path)
        await runner.upgrade()
        reverted = await runner.downgrade("0001")
        assert "0001" in reverted

        row = await pg_conn.fetchrow(
            "SELECT version FROM schema_migrations WHERE version = '0001'"
        )
        assert row is None


class TestPostgresPool:
    """Pool asyncpg conecta e executa queries básicas."""

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_pool_executes_select(self, pg_pool):
        async with pg_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
        assert result == 1

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_pool_multiple_connections(self, pg_pool):
        """Múltiplas aquisições sequenciais funcionam sem deadlock."""
        for _ in range(3):
            async with pg_pool.acquire() as conn:
                val = await conn.fetchval("SELECT 42")
                assert val == 42

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_get_pg_pool_factory(self, pg_dsn, monkeypatch):
        """get_pg_pool() cria pool e garante schema via migration runner."""
        import backend.settings as _s
        import backend.storage.factory as _fac

        _fac._reset_singletons()
        monkeypatch.setattr(_s.settings, "postgres_dsn", pg_dsn)

        try:
            pool = await _fac.get_pg_pool(dsn=pg_dsn)
            assert pool is not None
            async with pool.acquire() as conn:
                val = await conn.fetchval("SELECT 1")
            assert val == 1
        finally:
            await _fac.close_pg_pool()
            _fac._reset_singletons()

    @pytest.mark.asyncio
    @pytest.mark.storage
    async def test_get_pg_pool_raises_without_dsn(self, monkeypatch):
        """get_pg_pool() levanta RuntimeError quando nenhum DSN está configurado."""
        import backend.settings as _s
        import backend.storage.factory as _fac

        _fac._reset_singletons()
        monkeypatch.setattr(_s.settings, "postgres_dsn", None)
        monkeypatch.setattr(_s.settings, "storage_mode", "complete")

        with pytest.raises(RuntimeError, match="postgres_dsn"):
            await _fac.get_pg_pool()

        _fac._reset_singletons()
