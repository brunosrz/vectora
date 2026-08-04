"""`TaskOut` expõe o estado do Kanban (`status`/`block_kind`/`block_reason`)
via API REST, e o endpoint de desbloqueio reseta uma task bloqueada para
"ready", limpando o motivo do bloqueio.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from fastapi import HTTPException, Request

import backend
from backend.api.handlers import background as bg_api
from backend.scheduling import background_tasks as bg
from backend.scheduling import kanban

_SCHEMA = (
    Path(backend.__file__).parent / "storage" / "migrations" / "sqlite" / "schema.sql"
)


@pytest.fixture
async def db(tmp_path, monkeypatch):
    import aiosqlite

    db_path = str(tmp_path / "bg.db")

    async def _connect() -> Any:
        conn: Any = await aiosqlite.connect(db_path)
        conn.row_factory = lambda c, r: dict(
            zip([col[0] for col in c.description], r, strict=False)
        )
        return conn

    setup = await _connect()
    await setup.executescript(_SCHEMA.read_text(encoding="utf-8"))
    await setup.commit()
    await setup.close()

    monkeypatch.setattr(bg, "_get_db", _connect)
    monkeypatch.setattr(kanban, "_get_db", _connect)
    return db_path


class _FakeRequestImpl:
    class _State:
        user = type("U", (), {"id": "u1"})()

    state = _State()


def _fake_request() -> Request:
    return cast("Request", _FakeRequestImpl())


@pytest.mark.asyncio
async def test_get_tasks_devolve_status_do_kanban(db):
    task = await bg.create_task(
        session_id="s1",
        user_id="u1",
        kind="routine",
        name="A",
        instruction="i",
        trigger_type="interval",
        trigger_config={"cron_expr": "0 9 * * *"},
    )

    saida = await bg_api.get_tasks(_fake_request(), "s1")

    assert len(saida) == 1
    assert saida[0].id == task.id
    # Task recorrente nasce com next_run_at futuro definido — status
    # "scheduled", não "ready" (reservado pra tasks já acionáveis agora,
    # como manual criada direto no board).
    assert saida[0].status == "scheduled"
    assert saida[0].block_kind is None


@pytest.mark.asyncio
async def test_unblock_endpoint_devolve_pra_ready_e_limpa_o_motivo(db):
    task = await bg.create_task(
        session_id="s1",
        user_id="u1",
        kind="routine",
        name="A",
        instruction="i",
        trigger_type="manual",
        trigger_config={},
    )
    await kanban.block_task(task.id, "needs_input", "falta a chave da API")

    saida = await bg_api.unblock_task_endpoint(_fake_request(), "s1", task.id)

    assert saida.status == "ready"
    assert saida.block_kind is None
    assert saida.block_reason is None


@pytest.mark.asyncio
async def test_unblock_endpoint_com_task_de_outra_session_e_404(db):
    """Erro/borda: o mesmo isolamento por `thread_id` que os outros
    endpoints já aplicam (`_require_task`) precisa valer aqui também."""
    task = await bg.create_task(
        session_id="s1",
        user_id="u1",
        kind="routine",
        name="A",
        instruction="i",
        trigger_type="manual",
        trigger_config={},
    )

    with pytest.raises(HTTPException) as exc_info:
        await bg_api.unblock_task_endpoint(_fake_request(), "sessao-errada", task.id)

    assert exc_info.value.status_code == 404
