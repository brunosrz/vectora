"""Tests for backend/services/background_tasks.py.

Cobre o ciclo de vida das tarefas em segundo plano session-scoped: CRUD, execução
real do agente (run_task), scheduler de interval e a ponte webhook→IA. Cada caminho
feliz tem o par de erro/borda no mesmo teste (CLAUDE.md §18).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import backend
from backend.services import agent_factory
from backend.services import background_tasks as bg

_MIGRATION = (
    Path(backend.__file__).parent
    / "storage"
    / "migrations"
    / "sqlite"
    / "0007_background_tasks.sql"
)


@pytest.fixture
async def db(tmp_path, monkeypatch):
    """Banco SQLite temporário com o schema 0007 aplicado.

    `_get_db` abre uma conexão nova por chamada (igual à produção); todas apontam
    para o mesmo arquivo, então o estado persiste entre operações.
    """
    db_path = str(tmp_path / "bg.db")
    up_sql = _MIGRATION.read_text(encoding="utf-8").split("-- down")[0]

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


class _FakeAgent:
    def __init__(self, result: Any = None, exc: Exception | None = None) -> None:
        self.result = result
        self.exc = exc
        self.calls: list[dict[str, Any]] = []

    async def ainvoke(self, inp, config=None, context=None) -> Any:
        self.calls.append({"input": inp, "config": config, "context": context})
        if self.exc is not None:
            raise self.exc
        return self.result


def _patch_agent(monkeypatch, agent: _FakeAgent) -> None:
    async def _fake_get_agent(user_id: str | None = None, model: str = "") -> Any:
        return agent

    monkeypatch.setattr(agent_factory, "get_user_agent", _fake_get_agent)


# ---------------------------------------------------------------------------
# CRUD + validação
# ---------------------------------------------------------------------------


async def test_create_task_persists_then_validation_rejects_bad_input(db):
    task = await bg.create_task(
        session_id="sess-1",
        user_id="uuid-aaa",
        kind="routine",
        name="Resumo diário",
        instruction="Resuma as mudanças do dia",
        trigger_type="interval",
        trigger_config={"cron_expr": "0 9 * * *"},
        workspace_id="ws1",
    )
    assert task.id
    assert task.next_run_at is not None  # interval agenda o próximo horário
    listed = await bg.list_tasks("sess-1")
    assert [t.id for t in listed] == [task.id]
    got = await bg.get_task(task.id)
    assert got is not None
    assert got.name == "Resumo diário"

    # Erro/borda no mesmo teste: kind/trigger/cron inválidos devem falhar.
    with pytest.raises(ValueError):
        await bg.create_task(
            session_id="sess-1",
            user_id="uuid-aaa",
            kind="invalido",
            name="x",
            instruction="x",
            trigger_type="interval",
            trigger_config={"cron_expr": "0 9 * * *"},
        )
    with pytest.raises(ValueError):
        await bg.create_task(
            session_id="sess-1",
            user_id="uuid-aaa",
            kind="routine",
            name="x",
            instruction="x",
            trigger_type="cosmico",
            trigger_config={},
        )
    with pytest.raises(ValueError):
        await bg.create_task(
            session_id="sess-1",
            user_id="uuid-aaa",
            kind="routine",
            name="x",
            instruction="x",
            trigger_type="interval",
            trigger_config={"cron_expr": "isso não é cron"},
        )


async def test_update_and_delete_roundtrip(db):
    task = await bg.create_task(
        session_id="s",
        user_id="u",
        kind="heartbreak",
        name="orig",
        instruction="i",
        trigger_type="webhook",
        trigger_config={"provider": "github", "events": ["push"]},
    )
    updated = await bg.update_task(task.id, name="novo", enabled=False)
    assert updated is not None
    assert updated.name == "novo"
    assert updated.enabled is False

    # Erro/borda: atualizar task inexistente devolve None; delete idem False.
    assert await bg.update_task("nope") is None
    assert await bg.delete_task(task.id) is True
    assert await bg.delete_task(task.id) is False
    assert await bg.get_task(task.id) is None


# ---------------------------------------------------------------------------
# run_task — execução real do agente
# ---------------------------------------------------------------------------


async def test_run_task_invokes_agent_registers_session_and_records_run(
    db, monkeypatch
):
    agent = _FakeAgent(result={"messages": [{"content": "Tudo certo hoje."}]})
    _patch_agent(monkeypatch, agent)

    upserts: list[dict[str, Any]] = []

    async def _fake_upsert(thread_id, title=None, workspace_id=None):
        upserts.append(
            {"thread_id": thread_id, "title": title, "workspace_id": workspace_id}
        )

    monkeypatch.setattr("backend.api.handlers.threads._upsert_session", _fake_upsert)

    task = await bg.create_task(
        session_id="sess-run",
        user_id="uuid-bbb",
        kind="routine",
        name="Check",
        instruction="Verifique o repo",
        trigger_type="manual",
        trigger_config={},
        workspace_id="ws9",
    )

    run_thread_id = await bg.run_task(task, "manual")

    assert run_thread_id is not None
    assert run_thread_id.startswith(f"bg-{task.id}-")
    assert len(agent.calls) == 1
    # A run criou uma thread visível na sidebar com título e workspace certos.
    assert upserts == [
        {"thread_id": run_thread_id, "title": "Rotina: Check", "workspace_id": "ws9"}
    ]
    runs = await bg.list_runs("sess-run")
    assert len(runs) == 1
    assert runs[0]["status"] == "done"
    assert runs[0]["summary"] == "Tudo certo hoje."
    after = await bg.get_task(task.id)
    assert after is not None
    assert after.last_run_at is not None


async def test_run_task_error_path_records_error_and_skips_session(db, monkeypatch):
    agent = _FakeAgent(exc=RuntimeError("LLM caiu"))
    _patch_agent(monkeypatch, agent)

    called: list[Any] = []

    async def _fake_upsert(*a, **k):
        called.append((a, k))

    monkeypatch.setattr("backend.api.handlers.threads._upsert_session", _fake_upsert)

    task = await bg.create_task(
        session_id="sess-err",
        user_id="u",
        kind="heartbreak",
        name="X",
        instruction="i",
        trigger_type="manual",
        trigger_config={},
    )

    result = await bg.run_task(task, "manual")

    assert result is None  # falha não propaga, vira None
    assert called == []  # não registra thread visível se o agente falhou
    runs = await bg.list_runs("sess-err")
    assert runs[0]["status"] == "error"
    assert "LLM caiu" in runs[0]["summary"]


# ---------------------------------------------------------------------------
# Scheduler (interval)
# ---------------------------------------------------------------------------


async def test_scheduler_runs_due_and_skips_disabled(db, monkeypatch):
    fired: list[str] = []

    async def _fake_run(task, trigger_source, payload=None):
        fired.append(task.id)
        return "bg-x"

    monkeypatch.setattr(bg, "run_task", _fake_run)

    due = await bg.create_task(
        session_id="s",
        user_id="u",
        kind="routine",
        name="due",
        instruction="i",
        trigger_type="interval",
        trigger_config={"cron_expr": "* * * * *"},
    )
    # Força o vencimento (next_run_at no passado).
    await bg._set_next_run(due.id, "2000-01-01T00:00:00+00:00")

    disabled = await bg.create_task(
        session_id="s",
        user_id="u",
        kind="routine",
        name="off",
        instruction="i",
        trigger_type="interval",
        trigger_config={"cron_expr": "* * * * *"},
    )
    await bg._set_next_run(disabled.id, "2000-01-01T00:00:00+00:00")
    await bg.update_task(disabled.id, enabled=False)

    await bg.get_scheduler().tick()

    assert fired == [due.id]  # só a vencida e habilitada roda
    # Reagendou para o futuro.
    rescheduled = await bg.get_task(due.id)
    assert rescheduled is not None
    assert rescheduled.next_run_at != "2000-01-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# Webhook → IA
# ---------------------------------------------------------------------------


async def test_dispatch_webhook_matches_provider_and_event(db, monkeypatch):
    fired: list[tuple[str, str]] = []

    async def _fake_run(task, trigger_source, payload=None):  # noqa: ANN001
        fired.append((task.id, trigger_source))
        return "bg-x"

    monkeypatch.setattr(bg, "run_task", _fake_run)

    task = await bg.create_task(
        session_id="s",
        user_id="u",
        kind="heartbreak",
        name="ci",
        instruction="Analise o push",
        trigger_type="webhook",
        trigger_config={"provider": "github", "events": ["push"]},
    )

    # Casa: github + push.
    assert await bg.dispatch_webhook_event("github", "push", {"x": 1}) == 1
    assert fired == [(task.id, "webhook")]

    fired.clear()
    # Não casa: provider diferente.
    assert await bg.dispatch_webhook_event("gitlab", "push", {}) == 0
    # Não casa: evento fora do filtro.
    assert await bg.dispatch_webhook_event("github", "issues", {}) == 0
    assert fired == []
