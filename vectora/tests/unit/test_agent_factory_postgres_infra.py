"""_ensure_infra (backend/services/agent_factory.py) — checkpointer/store Postgres (D1).

Antes desta mudança, TODO checkpointer/store era SQLite mesmo em
storage_mode="complete" com Postgres configurado — Qdrant/Redis já eram
reais nesse modo, mas o estado do agente (thread messages, memória) ficava
preso no SQLite de qualquer forma. Agora "complete" + postgres_dsn usa
AsyncPostgresSaver/AsyncPostgresStore; qualquer falha ao abrir Postgres
degrada pro SQLite (nunca impede a sessão de iniciar).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import agent_factory


@pytest.fixture(autouse=True)
def _reset_infra_singletons():
    agent_factory._checkpointer_ctx = None
    agent_factory._checkpointer = None
    agent_factory._store = None
    agent_factory._store_ctx = None
    yield
    agent_factory._checkpointer_ctx = None
    agent_factory._checkpointer = None
    agent_factory._store = None
    agent_factory._store_ctx = None


def _fake_pg_ctx(instance: object) -> MagicMock:
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=instance)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


@pytest.mark.asyncio
async def test_ensure_infra_uses_postgres_checkpointer_and_store_in_complete_mode():
    fake_checkpointer = MagicMock()
    fake_checkpointer.setup = AsyncMock()
    fake_store = MagicMock()
    fake_store.setup = AsyncMock()

    fake_settings = MagicMock(storage_mode="complete", postgres_dsn="postgresql://x/y")

    with (
        patch("backend.settings.settings", fake_settings),
        patch(
            "langgraph.checkpoint.postgres.aio.AsyncPostgresSaver.from_conn_string",
            return_value=_fake_pg_ctx(fake_checkpointer),
        ),
        patch(
            "langgraph.store.postgres.aio.AsyncPostgresStore.from_conn_string",
            return_value=_fake_pg_ctx(fake_store),
        ),
    ):
        await agent_factory._ensure_infra()

    assert agent_factory._checkpointer is fake_checkpointer
    assert agent_factory._store is fake_store
    fake_checkpointer.setup.assert_awaited_once()
    fake_store.setup.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_infra_falls_back_to_sqlite_when_postgres_fails(tmp_path):
    """Edge — DSN ruim/Postgres fora do ar não impede a sessão de iniciar."""
    fake_settings = MagicMock(
        storage_mode="complete",
        postgres_dsn="postgresql://bad/dsn",
        vectora_home=tmp_path,
    )

    with (
        patch("backend.settings.settings", fake_settings),
        patch(
            "langgraph.checkpoint.postgres.aio.AsyncPostgresSaver.from_conn_string",
            side_effect=RuntimeError("connection refused"),
        ),
        patch(
            "backend.llm.backends.build_store", new=AsyncMock(return_value=MagicMock())
        ),
    ):
        await agent_factory._ensure_infra()

    assert agent_factory._checkpointer is not None
    # AsyncSqliteSaver não tem "setup" chamado por nós (chamado internamente) —
    # o importante é que NÃO seja o mock do Postgres e que não levante exceção.
    assert not hasattr(agent_factory._checkpointer, "setup") or not isinstance(
        agent_factory._checkpointer, MagicMock
    )


@pytest.mark.asyncio
async def test_ensure_infra_uses_sqlite_in_lite_mode(tmp_path):
    """Modo lite (default) nunca tenta abrir Postgres."""
    fake_settings = MagicMock(
        storage_mode="lite", postgres_dsn=None, vectora_home=tmp_path
    )

    with (
        patch("backend.settings.settings", fake_settings),
        patch(
            "backend.llm.backends.build_store", new=AsyncMock(return_value=MagicMock())
        ),
    ):
        await agent_factory._ensure_infra()

    assert agent_factory._checkpointer is not None
    assert agent_factory._store_ctx is None
