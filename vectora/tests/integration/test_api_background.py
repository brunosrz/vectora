"""Integração handler↔serviço de tarefas em segundo plano.

Exercita os endpoints session-scoped com um usuário de id **UUID** — o cenário
que antes derrubava o backend (`int(user.id)` em routines/heartbreak). Prova que
não há mais crash e que o disparo manual roda o agente, cria a run e registra a
thread.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import BackgroundTasks, HTTPException

import backend
from backend.api.handlers.background import (
    CreateTaskRequest,
    ResumeRunRequest,
    UpdateTaskRequest,
    delete_task_endpoint,
    get_runs,
    get_tasks,
    patch_task,
    post_task,
    resume_run_endpoint,
    run_task_endpoint,
)
from backend.scheduling import background_tasks as bg
from backend.services import agent_factory

_UUID = "aa844f17-7e0e-4b0a-8991-c3aab9bdcc63"
_SCHEMA = (
    Path(backend.__file__).parent / "storage" / "migrations" / "sqlite" / "schema.sql"
)


def _req(uid: str | None = _UUID) -> Any:
    user = SimpleNamespace(id=uid) if uid is not None else None
    return SimpleNamespace(state=SimpleNamespace(user=user))


@pytest.fixture
async def db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "bg.db")
    up_sql = _SCHEMA.read_text(encoding="utf-8")

    import aiosqlite

    async def _connect() -> Any:
        conn: Any = await aiosqlite.connect(db_path)
        conn.row_factory = lambda c, r: dict(
            zip([col[0] for col in c.description], r, strict=False)
        )
        return conn

    setup = await _connect()
    await setup.executescript(up_sql)
    await setup.commit()
    await setup.close()

    monkeypatch.setattr(bg, "_get_db", _connect)
    return db_path


@pytest.fixture(autouse=True)
def _pro_tier_by_default(monkeypatch):
    """Tarefas `webhook` exigem tier pro — este arquivo cobre o handler
    REST, não o gating em si (coberto em test_services_background.py)."""
    monkeypatch.setenv("VECTORA_LICENSE_BYPASS", "1")


async def test_post_task_with_uuid_user_does_not_crash(db):
    out = await post_task(
        _req(),
        "thread-1",
        CreateTaskRequest(
            kind="routine",
            name="Resumo",
            instruction="Resuma o dia",
            trigger_type="interval",
            trigger_config={"cron_expr": "0 9 * * *"},
        ),
    )
    assert out.session_id == "thread-1"
    assert out.id  # criou sem ValueError de int(user.id)

    tasks = await get_tasks(_req(), "thread-1")
    assert [t.id for t in tasks] == [out.id]

    # Erro/borda: sem usuário autenticado → 401; cron inválido → 400.
    with pytest.raises(HTTPException) as no_auth:
        await get_tasks(_req(uid=None), "thread-1")
    assert no_auth.value.status_code == 401

    with pytest.raises(HTTPException) as bad_cron:
        await post_task(
            _req(),
            "thread-1",
            CreateTaskRequest(
                kind="routine",
                name="x",
                instruction="x",
                trigger_type="interval",
                trigger_config={"cron_expr": "nope"},
            ),
        )
    assert bad_cron.value.status_code == 400


async def test_patch_and_delete_enforce_session_scope(db):
    out = await post_task(
        _req(),
        "thread-A",
        CreateTaskRequest(
            kind="heartbreak",
            name="ci",
            instruction="i",
            trigger_type="webhook",
            trigger_config={"provider": "github", "events": ["push"]},
        ),
    )
    updated = await patch_task(
        _req(), "thread-A", out.id, UpdateTaskRequest(enabled=False)
    )
    assert updated.enabled is False

    # Erro/borda: a task não pertence a outra session → 404.
    with pytest.raises(HTTPException) as wrong_session:
        await patch_task(_req(), "thread-B", out.id, UpdateTaskRequest(enabled=True))
    assert wrong_session.value.status_code == 404

    await delete_task_endpoint(_req(), "thread-A", out.id)
    assert await get_tasks(_req(), "thread-A") == []


async def test_manual_run_creates_run_and_registers_thread(db, monkeypatch):
    agent = SimpleNamespace()

    async def _ainvoke(inp, config=None, context=None) -> Any:
        return {"messages": [{"content": "feito"}]}

    agent.ainvoke = _ainvoke

    async def _get_agent(
        user_id: str | None = None,
        model: str = "",
        chat_mode: bool = False,
        workspace_id: str | None = None,
    ) -> Any:
        return agent

    monkeypatch.setattr(agent_factory, "get_user_agent", _get_agent)

    upserts: list[str] = []

    async def _upsert(thread_id, title=None, workspace_id=None):
        upserts.append(thread_id)

    monkeypatch.setattr("backend.api.handlers.threads._upsert_session", _upsert)

    created = await post_task(
        _req(),
        "thread-run",
        CreateTaskRequest(
            kind="routine",
            name="Check",
            instruction="Cheque",
            trigger_type="manual",
            trigger_config={},
        ),
    )

    bt = BackgroundTasks()
    resp = await run_task_endpoint(_req(), "thread-run", created.id, bt)
    assert resp["status"] == "queued"

    # Executa a task enfileirada (o que o FastAPI faria após a resposta).
    await bt()

    runs = await get_runs(_req(), "thread-run")
    assert len(runs) == 1
    assert runs[0].status == "done"
    assert runs[0].run_thread_id is not None
    assert upserts == [runs[0].run_thread_id]

    # Erro/borda: rodar task de outra session → 404.
    with pytest.raises(HTTPException) as wrong:
        await run_task_endpoint(_req(), "outra-thread", created.id, BackgroundTasks())
    assert wrong.value.status_code == 404


async def test_resume_run_endpoint_cancel_and_approve(db, monkeypatch):
    """POST /runs/{id}/resume: cancela sincronamente (decision='cancel') ou
    enfileira o resume (approve/reject) via BackgroundTasks — mesmo padrão do
    disparo manual. Erro/borda: run inexistente → 404; run que não está
    aguardando aprovação → 409."""
    created = await post_task(
        _req(),
        "thread-resume",
        CreateTaskRequest(
            kind="routine",
            name="Perigosa",
            instruction="i",
            trigger_type="manual",
            trigger_config={"permission_mode": "ask"},
        ),
    )

    # Erro/borda: run inexistente → 404.
    with pytest.raises(HTTPException) as not_found:
        await resume_run_endpoint(
            _req(), "thread-resume", "nao-existe", ResumeRunRequest(), BackgroundTasks()
        )
    assert not_found.value.status_code == 404

    task = await bg.get_task(created.id)
    assert task is not None

    # Registra uma run pausada em HITL.
    run_id = "run-http-resume"
    await bg._insert_run(run_id, task, "bg-thread-resume", "manual")

    # Erro/borda: run 'running' (ainda não pausou) → 409.
    with pytest.raises(HTTPException) as not_awaiting:
        await resume_run_endpoint(
            _req(), "thread-resume", run_id, ResumeRunRequest(), BackgroundTasks()
        )
    assert not_awaiting.value.status_code == 409

    await bg._mark_run_awaiting(run_id, "Aguardando aprovação: terminal")

    # decision='cancel' — síncrono, run vira 'cancelled' imediatamente.
    resp_cancel = await resume_run_endpoint(
        _req(),
        "thread-resume",
        run_id,
        ResumeRunRequest(decision="cancel"),
        BackgroundTasks(),
    )
    assert resp_cancel == {"status": "cancelled", "run_id": run_id}
    cancelled = await bg._get_run(run_id)
    assert cancelled is not None
    assert cancelled["status"] == "cancelled"

    # decision='approve' num run pendente — enfileira via BackgroundTasks.
    run_id_2 = "run-http-approve"
    await bg._insert_run(run_id_2, task, "bg-thread-resume-2", "manual")
    await bg._mark_run_awaiting(run_id_2, "Aguardando aprovação: terminal")

    agent = SimpleNamespace()

    async def _ainvoke(inp, config=None, context=None) -> Any:
        return {"messages": [{"content": "concluído"}]}

    agent.ainvoke = _ainvoke

    async def _get_agent(
        user_id: str | None = None,
        model: str = "",
        chat_mode: bool = False,
        workspace_id: str | None = None,
    ) -> Any:
        return agent

    monkeypatch.setattr(agent_factory, "get_user_agent", _get_agent)

    bt = BackgroundTasks()
    resp_approve = await resume_run_endpoint(
        _req(), "thread-resume", run_id_2, ResumeRunRequest(decision="approve"), bt
    )
    assert resp_approve == {"status": "queued", "run_id": run_id_2}

    await bt()  # executa o resume enfileirado (o que o FastAPI faria depois)

    approved = await bg._get_run(run_id_2)
    assert approved is not None
    assert approved["status"] == "done"
