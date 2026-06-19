"""Tests — storage/migrations/runner.py (F2) e data_migration.py (F12).

Runner: status / upgrade / downgrade usando SQL inline (sem arquivos .sql).
DataMigration: dry-run em memória.
"""

from __future__ import annotations

import pytest


class TestMigrationRunner:
    """Schema migration runner (F2)."""

    @pytest.fixture
    async def runner_conn(self, tmp_path):
        import aiosqlite

        db_path = str(tmp_path / "test_migrations.db")
        conn = await aiosqlite.connect(db_path)
        conn.row_factory = aiosqlite.Row
        yield conn
        await conn.close()

    @pytest.mark.asyncio
    async def test_status_empty(self, runner_conn):
        from backend.storage.migrations.runner import MigrationRunner

        runner = MigrationRunner(runner_conn)
        statuses = await runner.status()
        # Sem migrations SQL a listar — lista pode estar vazia
        assert isinstance(statuses, list)

    @pytest.mark.asyncio
    async def test_upgrade_noop_when_no_sql(self, runner_conn, tmp_path):
        """upgrade() sem migrations pendentes não levanta exceção."""
        from backend.storage.migrations.runner import MigrationRunner

        runner = MigrationRunner(runner_conn, migrations_dir=tmp_path)
        applied = await runner.upgrade()
        assert isinstance(applied, list)

    @pytest.mark.asyncio
    async def test_schema_migrations_table_created(self, runner_conn, tmp_path):
        """Tabela schema_migrations é criada ao instanciar runner."""
        from backend.storage.migrations.runner import MigrationRunner

        runner = MigrationRunner(runner_conn, migrations_dir=tmp_path)
        await runner.upgrade()  # força criação da tabela

        cur = await runner_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        )
        row = await cur.fetchone()
        assert row is not None


class TestDataMigrationDryRun:
    """Migrações de dados (F12) — apenas dry-run para não precisar de infra."""

    @pytest.mark.asyncio
    async def test_to_postgres_dry_run(self, tmp_path):
        """dry-run retorna contagem sem conectar ao Postgres."""
        import aiosqlite

        from backend.storage.migrations.data_migration import migrate_to_postgres

        db_path = str(tmp_path / "source.db")
        async with aiosqlite.connect(db_path) as conn:
            # Cria tabela de teste
            await conn.execute(
                "CREATE TABLE vectora_users (id TEXT PRIMARY KEY, name TEXT)"
            )
            await conn.execute("INSERT INTO vectora_users VALUES ('u1', 'Alice')")
            await conn.commit()

        result = await migrate_to_postgres(
            sqlite_path=db_path,
            postgres_dsn="postgresql://fake/db",
            dry_run=True,
        )
        assert result["dry_run"] is True
        assert result["total_rows"] >= 1
        assert "vectora_users" in result["tables"]

    @pytest.mark.asyncio
    async def test_to_postgres_dry_run_missing_table(self, tmp_path):
        """Tabela ausente não levanta erro no dry-run."""
        import aiosqlite

        from backend.storage.migrations.data_migration import migrate_to_postgres

        db_path = str(tmp_path / "empty.db")
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute("CREATE TABLE unrelated (id INTEGER)")

        result = await migrate_to_postgres(
            sqlite_path=db_path,
            postgres_dsn="postgresql://fake/db",
            dry_run=True,
        )
        assert result["total_rows"] == 0

    @pytest.mark.asyncio
    async def test_memory_to_langgraph_missing_table(self, tmp_path):
        """Banco sem tabela 'memories' retorna total=0 sem erro."""
        import aiosqlite

        from backend.storage.migrations.data_migration import (
            migrate_memory_to_langgraph,
        )

        db_path = str(tmp_path / "no_memories.db")
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute("CREATE TABLE other (id INTEGER)")

        # dry-run — não precisa de store configurado
        result = await migrate_memory_to_langgraph(
            sqlite_path=db_path,
            dry_run=True,
        )
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_memory_to_langgraph_dry_run(self, tmp_path):
        """dry-run conta registros sem chamar store."""
        import aiosqlite

        from backend.storage.migrations.data_migration import (
            migrate_memory_to_langgraph,
        )

        db_path = str(tmp_path / "memories.db")
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute(
                "CREATE TABLE memories (id TEXT PRIMARY KEY, user_id TEXT, content TEXT)"
            )
            await conn.execute(
                "INSERT INTO memories VALUES ('m1', 'u1', '{\"text\": \"hello\"}')"
            )
            await conn.commit()

        result = await migrate_memory_to_langgraph(
            sqlite_path=db_path,
            dry_run=True,
        )
        assert result["dry_run"] is True
        assert result["total"] == 1
