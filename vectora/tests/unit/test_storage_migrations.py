"""Tests — storage/migrations/runner.py e data_migration.py.

Runner SQLite: usa as migrations em storage/migrations/sqlite/*.sql.
DataMigration: dry-run em memória.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestMigrationRunner:
    """Schema migration runner — arquivo único (sqlite/schema.sql)."""

    @pytest.fixture
    async def runner_conn(self, tmp_path):
        import aiosqlite

        db_path = str(tmp_path / "test_migrations.db")
        conn = await aiosqlite.connect(db_path)
        conn.row_factory = aiosqlite.Row
        yield conn
        await conn.close()

    @pytest.fixture
    async def raw_conn(self, tmp_path):
        """Conexão sem row_factory — simula o contexto de produção (server.py)."""
        import aiosqlite

        db_path = str(tmp_path / "test_migrations_raw.db")
        conn = await aiosqlite.connect(db_path)
        yield conn
        await conn.close()

    @pytest.mark.asyncio
    async def test_status_pending_on_empty_db(self, runner_conn):
        """status() mostra applied=False num banco vazio."""
        from backend.storage.migrations.runner import MigrationRunner

        runner = MigrationRunner(runner_conn)
        status = await runner.status()
        assert status.applied is False
        assert status.applied_at is None
        assert status.checksum

    @pytest.mark.asyncio
    async def test_status_shows_applied_after_upgrade(self, runner_conn):
        """status() mostra applied=True e drift=False após upgrade() rodar."""
        from backend.storage.migrations.runner import MigrationRunner

        runner = MigrationRunner(runner_conn)
        await runner.upgrade()
        status = await runner.status()
        assert status.applied is True
        assert status.drift is False
        assert status.applied_at is not None

    @pytest.mark.asyncio
    async def test_upgrade_applies_schema_and_returns_true(self, runner_conn):
        """upgrade() aplica o schema.sql inteiro e retorna True na 1ª chamada."""
        from backend.storage.migrations.runner import MigrationRunner

        runner = MigrationRunner(runner_conn)
        applied = await runner.upgrade()
        assert applied is True

    @pytest.mark.asyncio
    async def test_upgrade_idempotent(self, runner_conn):
        """Segunda chamada a upgrade() é no-op (checksum já bate) — retorna False."""
        from backend.storage.migrations.runner import MigrationRunner

        runner = MigrationRunner(runner_conn)
        await runner.upgrade()
        second = await runner.upgrade()
        assert second is False

    @pytest.mark.asyncio
    async def test_schema_migrations_table_created(self, runner_conn):
        """Tabela de controle schema_migrations é criada ao instanciar runner."""
        from backend.storage.migrations.runner import MigrationRunner

        runner = MigrationRunner(runner_conn)
        await runner.upgrade()  # força criação da tabela

        cur = await runner_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        )
        row = await cur.fetchone()
        assert row is not None

    @pytest.mark.asyncio
    async def test_upgrade_without_row_factory(self, raw_conn):
        """upgrade() funciona com conexão sem row_factory (caso de produção)."""
        from backend.storage.migrations.runner import MigrationRunner

        runner = MigrationRunner(raw_conn)
        applied = await runner.upgrade()
        assert applied is True
        second = await runner.upgrade()
        assert second is False

    @pytest.mark.asyncio
    async def test_colunas_do_kanban_chegam_em_banco_ja_populado(
        self, runner_conn, monkeypatch
    ):
        """`CREATE TABLE IF NOT EXISTS` é no-op quando a tabela já existe sem
        as colunas `status`/`block_kind`/`claim_lock`/`budget_cents` etc —
        os `ALTER TABLE` correspondentes precisam rodar mesmo assim, senão o
        tick do scheduler falha com `sqlite3.OperationalError: no such
        column: status` contra um banco com o schema antigo de
        `vectora_background_tasks`."""
        from backend.storage.migrations.runner import MigrationRunner

        # Simula o shape "pré-kanban": só as colunas que existiam antes.
        await runner_conn.executescript(
            """
            CREATE TABLE vectora_background_tasks (
                id             TEXT PRIMARY KEY,
                session_id     TEXT NOT NULL,
                workspace_id   TEXT,
                user_id        TEXT NOT NULL,
                kind           TEXT NOT NULL,
                name           TEXT NOT NULL,
                instruction    TEXT NOT NULL,
                trigger_type   TEXT NOT NULL,
                trigger_config TEXT NOT NULL DEFAULT '{}',
                enabled        INTEGER NOT NULL DEFAULT 1,
                last_run_at    TEXT,
                next_run_at    TEXT,
                created_at     TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE vectora_background_runs (
                id             TEXT PRIMARY KEY,
                task_id        TEXT NOT NULL,
                session_id     TEXT NOT NULL,
                run_thread_id  TEXT,
                trigger_source TEXT NOT NULL,
                status         TEXT NOT NULL DEFAULT 'running',
                summary        TEXT,
                started_at     TEXT NOT NULL DEFAULT (datetime('now')),
                finished_at    TEXT
            );
            """
        )
        await runner_conn.commit()

        assert await MigrationRunner(runner_conn).upgrade() is True

        cur = await runner_conn.execute("PRAGMA table_info(vectora_background_tasks)")
        cols = {row[1] for row in await cur.fetchall()}
        assert {
            "status",
            "block_kind",
            "block_reason",
            "claim_lock",
            "claim_expires_at",
            "budget_cents",
        } <= cols

        cur = await runner_conn.execute("PRAGMA table_info(vectora_background_runs)")
        cols = {row[1] for row in await cur.fetchall()}
        assert {"tokens_used", "estimated_cost_cents"} <= cols

        # Erro/borda: release_stale_claims do scheduler roda sem lançar
        # contra o schema migrado.
        from backend.scheduling import kanban

        async def _get_db():
            return runner_conn

        monkeypatch.setattr(kanban, "_get_db", _get_db)
        assert await kanban.release_stale_claims() == 0

    @pytest.mark.asyncio
    async def test_vectora_sessions_table_created(self, runner_conn):
        """O schema cria a tabela vectora_sessions."""
        from backend.storage.migrations.runner import MigrationRunner

        await MigrationRunner(runner_conn).upgrade()
        cur = await runner_conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='vectora_sessions'"
        )
        assert await cur.fetchone() is not None

    @pytest.mark.asyncio
    async def test_vectora_sessions_has_extra_column(self, runner_conn):
        """vectora_sessions tem a coluna extra (onde mode/title/workspace vivem)."""
        from backend.storage.migrations.runner import MigrationRunner

        await MigrationRunner(runner_conn).upgrade()
        cur = await runner_conn.execute("PRAGMA table_info(vectora_sessions)")
        cols = {row[1] for row in await cur.fetchall()}
        assert "extra" in cols
        assert "thread_id" in cols

    @pytest.mark.asyncio
    async def test_reapply_after_content_change_updates_checksum(
        self, runner_conn, tmp_path
    ):
        """Editar o schema.sql muda o checksum: upgrade() reaplica e status() reflete."""
        from backend.storage.migrations.runner import MigrationRunner

        original = (
            Path(__file__).resolve().parents[2]
            / "backend"
            / "storage"
            / "migrations"
            / "sqlite"
            / "schema.sql"
        ).read_text(encoding="utf-8")

        edited_file = tmp_path / "schema_edited.sql"
        edited_file.write_text(
            original
            + "\nCREATE TABLE IF NOT EXISTS _test_marker (id INTEGER PRIMARY KEY);\n",
            encoding="utf-8",
        )

        runner = MigrationRunner(runner_conn, schema_file=edited_file)
        first = await runner.upgrade()
        assert first is True

        cur = await runner_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='_test_marker'"
        )
        assert await cur.fetchone() is not None

        status = await runner.status()
        assert status.applied is True
        assert status.drift is False

    @pytest.mark.asyncio
    async def test_alter_add_column_skips_existing_column(self, runner_conn):
        """ALTER TABLE ... ADD COLUMN não falha quando a coluna já existe."""
        from backend.storage.migrations.runner import MigrationRunner

        runner = MigrationRunner(runner_conn)
        await runner.upgrade()

        # Reaplicar manualmente o statement ALTER de uma coluna já criada pelo
        # CREATE TABLE não deve levantar "duplicate column name".
        await runner._execute_statement(
            "ALTER TABLE vectora_sessions ADD COLUMN extra TEXT"
        )

    @pytest.mark.asyncio
    async def test_upgrade_from_old_versioned_control_table(self, runner_conn):
        """Um `schema_migrations` no formato antigo versionado (version, name,
        applied_at, checksum) — sem coluna `id` — não pode fazer apply()
        quebrar com "no such column: id"."""
        from backend.storage.migrations.runner import MigrationRunner

        await runner_conn.executescript("""
            CREATE TABLE schema_migrations (
                version    TEXT PRIMARY KEY,
                name       TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                checksum   TEXT NOT NULL
            );
            INSERT INTO schema_migrations VALUES
                ('0001', 'auth', '2026-07-13T13:31:47+00:00', 'deadbeef');
        """)
        await runner_conn.commit()

        runner = MigrationRunner(runner_conn)
        applied = await runner.apply()
        assert applied is True

        status = await runner.status()
        assert status.applied is True
        assert status.drift is False


class TestDataMigrationDryRun:
    """Migrações de dados — apenas dry-run para não precisar de infra."""

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
