"""D2 — carga: duas sessões/workspaces escrevendo checkpoints ao mesmo tempo.

Valida que ``busy_timeout`` (WAL + 30s, aplicado por todo
``AsyncConnectionPool`` — ``backend/storage/sqlite/pool.py``) absorve o caso
comum de contenção — dois pools distintos apontando pro MESMO
``checkpoints.db``, escrevendo checkpoints via ``VectoraSqliteSaver``
(``backend/persistence/native/sqlite_checkpointer.py``) simultaneamente —
sem lançar "database is locked". Não é reescrita de arquitetura (avaliada e
descartada no plano — só validação de que o hardening já existente é
suficiente pro perfil de uso atual).
"""

from __future__ import annotations

import asyncio

import pytest

from backend.persistence.native.sqlite_checkpointer import VectoraSqliteSaver
from backend.storage.sqlite.pool import AsyncConnectionPool


async def _open_hardened(
    db_path: str,
) -> tuple[VectoraSqliteSaver, AsyncConnectionPool]:
    """Réplica do que agent_factory._ensure_infra faz: abre o pool (PRAGMAs de
    hardening aplicados por conexão) e o checkpointer nativo por cima."""
    pool = AsyncConnectionPool(db_path, min_size=1, max_size=4)
    await pool.open()
    saver = VectoraSqliteSaver(pool)
    await saver.setup()
    return saver, pool


async def _write_checkpoints(saver: VectoraSqliteSaver, thread_id: str, n: int) -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata

    for i in range(n):
        config: RunnableConfig = {
            "configurable": {"thread_id": thread_id, "checkpoint_ns": ""}
        }
        checkpoint: Checkpoint = {
            "v": 1,
            "id": f"{thread_id}-{i}",
            "ts": "2026-01-01T00:00:00+00:00",
            "channel_values": {"count": i},
            "channel_versions": {},
            "versions_seen": {},
            "updated_channels": [],
        }
        metadata: CheckpointMetadata = {"source": "loop", "step": i}
        await saver.aput(config, checkpoint, metadata, {})


@pytest.mark.asyncio
async def test_two_concurrent_sessions_write_same_db_without_locking_errors(tmp_path):
    """2 'workspaces' (pools separados) gravando no mesmo checkpoints.db."""
    db_path = str(tmp_path / "checkpoints.db")

    saver_a, pool_a = await _open_hardened(db_path)
    saver_b, pool_b = await _open_hardened(db_path)

    try:
        await asyncio.gather(
            _write_checkpoints(saver_a, "workspace-a", 20),
            _write_checkpoints(saver_b, "workspace-b", 20),
        )
    finally:
        await pool_a.close()
        await pool_b.close()

    # Confirma que ambas as threads persistiram — sem escrita perdida por
    # contenção silenciosa.
    saver_c, pool_c = await _open_hardened(db_path)
    try:
        state_a = [
            c
            async for c in saver_c.alist({"configurable": {"thread_id": "workspace-a"}})
        ]
        state_b = [
            c
            async for c in saver_c.alist({"configurable": {"thread_id": "workspace-b"}})
        ]
    finally:
        await pool_c.close()

    assert len(state_a) == 20
    assert len(state_b) == 20


@pytest.mark.asyncio
async def test_hardened_connection_has_busy_timeout_and_wal(tmp_path):
    """Confirma os PRAGMAs de fato aplicados na conexão — não só inferidos por
    ausência de "database is locked" nos testes de concorrência acima."""
    db_path = str(tmp_path / "checkpoints.db")
    _saver, pool = await _open_hardened(db_path)
    try:
        async with pool.acquire() as conn:
            cur = await conn.execute("PRAGMA busy_timeout")
            row = await cur.fetchone()
            assert row is not None
            assert row[0] == 30000

            cur = await conn.execute("PRAGMA journal_mode")
            row = await cur.fetchone()
            assert row is not None
            assert row[0].lower() == "wal"
    finally:
        await pool.close()


@pytest.mark.asyncio
async def test_three_concurrent_sessions_same_thread_no_exception(tmp_path):
    """Edge — 3 pools concorrentes na MESMA thread (pior caso de contenção)."""
    db_path = str(tmp_path / "checkpoints.db")
    savers = []
    try:
        for _ in range(3):
            saver, pool = await _open_hardened(db_path)
            savers.append((saver, pool))

        await asyncio.gather(
            *(_write_checkpoints(saver, "shared-thread", 10) for saver, _ in savers)
        )
    finally:
        for _saver, pool in savers:
            await pool.close()
