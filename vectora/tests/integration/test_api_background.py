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
    CreateLinkRequest,
    CreateTaskRequest,
    ResumeRunRequest,
    UpdateTaskRequest,
    add_link_endpoint,
    approve_review_endpoint,
    delete_task_endpoint,
    get_runs,
    get_tasks,
    patch_task,
    post_task,
    remove_link_endpoint,
    resume_run_endpoint,
    run_task_endpoint,
)
from backend.engine.hitl import ApprovalGate
from backend.persistence.native.session_store import SessionStore
from backend.scheduling import background_tasks as bg
from backend.services import agent_factory
from backend.services.agent_factory import NativeAgent
from backend.storage.sqlite.pool import AsyncConnectionPool
from backend.tools.registry import ToolRegistry
from backend.vtypes.message import VMessageChunk

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


class _ScriptedChatClient:
    """Cliente de chat fake — devolve um único turno de texto puro (sem
    tool call), suficiente pra exercitar o handler REST ponta a ponta."""

    def __init__(self, texto: str) -> None:
        self._texto = texto

    async def astream(self, messages, *, tools=None, temperature=None, max_tokens=None):
        yield VMessageChunk(delta_text=self._texto)


def _patch_native_engine(
    monkeypatch, *, session_store: SessionStore, texto: str
) -> None:
    """Substitui as dependências que `run_task`/`resume_background_run`
    resolvem via `agent_factory` (motor nativo) + `FallbackChatClient` —
    mesmo padrão de `tests/unit/test_services_background.py`."""
    native_agent = NativeAgent(
        tool_registry=ToolRegistry(),
        subagent_catalog={},
        system_prompt="system prompt de teste",
    )

    async def _fake_get_native_agent(
        user_id: str | None = None,
        chat_mode: bool = False,
        workspace_id: str | None = None,
    ) -> NativeAgent:
        return native_agent

    async def _fake_get_session_store() -> SessionStore:
        return session_store

    approval_gate = ApprovalGate(session_store)

    async def _fake_get_approval_gate() -> ApprovalGate:
        return approval_gate

    async def _fake_get_store() -> None:
        return None

    monkeypatch.setattr(agent_factory, "get_native_agent", _fake_get_native_agent)
    monkeypatch.setattr(agent_factory, "get_session_store", _fake_get_session_store)
    monkeypatch.setattr(agent_factory, "get_approval_gate", _fake_get_approval_gate)
    monkeypatch.setattr(agent_factory, "get_store", _fake_get_store)
    monkeypatch.setattr(
        bg, "FallbackChatClient", lambda primary_model_id="": _ScriptedChatClient(texto)
    )


@pytest.fixture
async def native_session_store(tmp_path):
    """``SessionStore`` real (sqlite à parte do banco de tasks/runs) — a
    mesma infraestrutura que ``agent_factory.get_session_store()`` devolve
    em produção, isolada por teste."""
    pool = AsyncConnectionPool(
        str(tmp_path / "native-sessions.db"), min_size=1, max_size=2
    )
    await pool.open()
    store = SessionStore(pool)
    await store.setup()
    try:
        yield store
    finally:
        await pool.close()


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


async def test_post_task_aceita_agent_profile_id_do_formulario_de_criacao(db):
    """``create_task`` (backend/scheduling/background_tasks.py) já suporta
    ``agent_profile_id`` — só o schema HTTP não expõe o campo, então o
    formulário de nova tarefa (Sprint 4 Fase 2, campo "assignee") não tinha
    como setar isso na criação. Regressão: sem o campo no schema, o assignee
    sempre volta ``None`` mesmo pedindo um perfil real."""
    out = await post_task(
        _req(),
        "thread-1",
        CreateTaskRequest(
            kind="routine",
            name="Com assignee",
            instruction="Faça algo",
            trigger_type="manual",
            agent_profile_id="perfil-1",
        ),
    )
    assert out.agent_profile_id == "perfil-1"

    # Erro/borda: omitir o campo continua criando sem assignee (default None).
    sem_assignee = await post_task(
        _req(),
        "thread-1",
        CreateTaskRequest(
            kind="routine",
            name="Sem assignee",
            instruction="Faça algo",
            trigger_type="manual",
        ),
    )
    assert sem_assignee.agent_profile_id is None


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


async def test_approve_review_endpoint_move_para_done(db):
    """Sprint 4 Fase 4a — endpoint dedicado de aprovação, não a transição
    genérica de status (que recusa `review→done` de propósito)."""
    from backend.scheduling.kanban import set_status

    out = await post_task(
        _req(),
        "thread-1",
        CreateTaskRequest(
            kind="routine", name="Revisar", instruction="i", trigger_type="manual"
        ),
    )
    await set_status(out.id, "review")

    approved = await approve_review_endpoint(_req(), "thread-1", out.id)

    assert approved.status == "done"

    # Erro/borda: aprovar de novo (já não está mais em review) → 400, não
    # um sucesso silencioso que reescreve o mesmo status.
    with pytest.raises(HTTPException) as again:
        await approve_review_endpoint(_req(), "thread-1", out.id)
    assert again.value.status_code == 400

    # Erro/borda: task de outra session → 404, mesmo enforcement de posse
    # que os outros endpoints de task já têm.
    with pytest.raises(HTTPException) as wrong_session:
        await approve_review_endpoint(_req(), "thread-B", out.id)
    assert wrong_session.value.status_code == 404


async def test_links_endpoint_adiciona_e_remove_dependencia(db):
    """Sprint 4 Fase 4d — `add_dependency` só era chamada internamente
    pela tool `kanban_decompose` do agente, sem rota HTTP nenhuma."""
    pai = await post_task(
        _req(),
        "thread-1",
        CreateTaskRequest(
            kind="routine", name="Pai", instruction="i", trigger_type="manual"
        ),
    )
    filho = await post_task(
        _req(),
        "thread-1",
        CreateTaskRequest(
            kind="routine", name="Filho", instruction="i", trigger_type="manual"
        ),
    )

    updated = await add_link_endpoint(
        _req(), "thread-1", filho.id, CreateLinkRequest(parent_id=pai.id)
    )
    assert [d.id for d in updated.dependencies] == [pai.id]

    updated = await remove_link_endpoint(_req(), "thread-1", filho.id, pai.id)
    assert updated.dependencies == []


async def test_links_endpoint_recusa_ciclo_com_409(db):
    """Erro/borda: fechar um ciclo pelo HTTP devolve 409 (conflito com o
    estado do grafo de dependências), não 500 nem um vínculo criado."""
    a = await post_task(
        _req(),
        "thread-1",
        CreateTaskRequest(
            kind="routine", name="a", instruction="i", trigger_type="manual"
        ),
    )
    b = await post_task(
        _req(),
        "thread-1",
        CreateTaskRequest(
            kind="routine", name="b", instruction="i", trigger_type="manual"
        ),
    )
    await add_link_endpoint(_req(), "thread-1", b.id, CreateLinkRequest(parent_id=a.id))

    with pytest.raises(HTTPException) as ciclo:
        await add_link_endpoint(
            _req(), "thread-1", a.id, CreateLinkRequest(parent_id=b.id)
        )
    assert ciclo.value.status_code == 409


async def test_links_endpoint_recusa_task_de_outra_session(db):
    """Erro/borda: linkar contra uma task de outra thread vazaria dado
    entre sessions — os dois lados do vínculo precisam pertencer à mesma."""
    out = await post_task(
        _req(),
        "thread-A",
        CreateTaskRequest(
            kind="routine", name="a", instruction="i", trigger_type="manual"
        ),
    )
    outra = await post_task(
        _req(),
        "thread-B",
        CreateTaskRequest(
            kind="routine", name="b", instruction="i", trigger_type="manual"
        ),
    )

    with pytest.raises(HTTPException) as wrong_session:
        await add_link_endpoint(
            _req(), "thread-A", out.id, CreateLinkRequest(parent_id=outra.id)
        )
    assert wrong_session.value.status_code == 404


async def test_manual_run_creates_run_and_registers_thread(
    db, monkeypatch, native_session_store
):
    _patch_native_engine(monkeypatch, session_store=native_session_store, texto="feito")

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


async def test_resume_run_endpoint_cancel_and_approve(
    db, monkeypatch, native_session_store
):
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

    _patch_native_engine(
        monkeypatch, session_store=native_session_store, texto="concluído"
    )
    # `resume_conversation` só age se houver uma aprovação pendente real no
    # SessionStore pro `run_thread_id` — registra a mesma pendência que uma
    # pausa HITL real teria persistido antes do run virar 'awaiting_approval'.
    await native_session_store.create_session(
        "bg-thread-resume-2", user_id=task.user_id
    )
    await native_session_store.put_pending_approval(
        "bg-thread-resume-2",
        interrupt_id="intr-resume-2",
        tool_name="terminal",
        tool_call_id="call-1",
        args={"command": "echo oi"},
    )

    bt = BackgroundTasks()
    resp_approve = await resume_run_endpoint(
        _req(), "thread-resume", run_id_2, ResumeRunRequest(decision="approve"), bt
    )
    assert resp_approve == {"status": "queued", "run_id": run_id_2}

    await bt()  # executa o resume enfileirado (o que o FastAPI faria depois)

    approved = await bg._get_run(run_id_2)
    assert approved is not None
    assert approved["status"] == "done"
