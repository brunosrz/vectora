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
from backend.scheduling import background_tasks as bg
from backend.services import agent_factory

_SCHEMA = (
    Path(backend.__file__).parent / "storage" / "migrations" / "sqlite" / "schema.sql"
)


@pytest.fixture
async def db(tmp_path, monkeypatch):
    """Banco SQLite temporário com o schema único aplicado.

    `_get_db` abre uma conexão nova por chamada (igual à produção); todas apontam
    para o mesmo arquivo, então o estado persiste entre operações.
    """
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
    # threads.py (upsert/increment/list de sessions) compartilha o mesmo banco.
    monkeypatch.setattr("backend.api.handlers.threads._get_db", _connect)
    return db_path


class _FakeAgent:
    def __init__(self, result: Any = None, exc: Exception | None = None) -> None:
        self.result = result
        self.exc = exc
        self.calls: list[dict[str, Any]] = []
        self.state_updates: list[dict[str, Any]] = []

    async def ainvoke(self, inp, config=None, context=None) -> Any:
        self.calls.append({"input": inp, "config": config, "context": context})
        if self.exc is not None:
            raise self.exc
        return self.result

    async def aupdate_state(self, config, values) -> Any:
        self.state_updates.append({"config": config, "values": values})
        return None


class _SeqAgent:
    """Agente fake que devolve resultados em sequência (um por ainvoke)."""

    def __init__(self, results: list[Any]) -> None:
        self.results = list(results)
        self.calls: list[dict[str, Any]] = []
        self.state_updates: list[dict[str, Any]] = []

    async def ainvoke(self, inp, config=None, context=None) -> Any:
        self.calls.append({"input": inp, "config": config, "context": context})
        return self.results.pop(0)

    async def aupdate_state(self, config, values) -> Any:
        self.state_updates.append({"config": config, "values": values})
        return None


def _patch_agent(monkeypatch, agent: Any) -> None:
    async def _fake_get_agent(
        user_id: str | None = None,
        model: str = "",
        chat_mode: bool = False,
        workspace_id: str | None = None,
    ) -> Any:
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
# Quota por workspace
# ---------------------------------------------------------------------------


async def test_quota_por_workspace_bloqueia_apos_o_limite_mas_nao_bloqueia_manual(
    db, monkeypatch
):
    monkeypatch.setattr(bg, "MAX_SCHEDULED_TASKS_PER_WORKSPACE", 2)

    await bg.create_task(
        session_id="s",
        user_id="u",
        kind="routine",
        name="t1",
        instruction="i",
        trigger_type="interval",
        trigger_config={"cron_expr": "0 9 * * *"},
        workspace_id="ws-quota",
    )
    await bg.create_task(
        session_id="s",
        user_id="u",
        kind="routine",
        name="t2",
        instruction="i",
        trigger_type="interval",
        trigger_config={"cron_expr": "0 10 * * *"},
        workspace_id="ws-quota",
    )

    with pytest.raises(ValueError, match="limite"):
        await bg.create_task(
            session_id="s",
            user_id="u",
            kind="routine",
            name="t3",
            instruction="i",
            trigger_type="interval",
            trigger_config={"cron_expr": "0 11 * * *"},
            workspace_id="ws-quota",
        )

    # Erro/borda: 'manual' nunca conta pra quota, mesmo workspace já saturado.
    manual = await bg.create_task(
        session_id="s",
        user_id="u",
        kind="routine",
        name="t-manual",
        instruction="i",
        trigger_type="manual",
        workspace_id="ws-quota",
    )
    assert manual.id

    # Outro workspace não compete pela mesma quota.
    other = await bg.create_task(
        session_id="s",
        user_id="u",
        kind="routine",
        name="t-outro-ws",
        instruction="i",
        trigger_type="interval",
        trigger_config={"cron_expr": "0 12 * * *"},
        workspace_id="ws-outro",
    )
    assert other.id


# ---------------------------------------------------------------------------
# Timezone do usuário
# ---------------------------------------------------------------------------


def test_next_run_usa_timezone_do_usuario_nao_utc(monkeypatch):
    """Cron é interpretado no fuso do usuário: "todo dia às 9h" pra alguém em
    GMT-3 dispara às 12h UTC, não às 9h UTC (que seria 6h da manhã pra ele)."""
    from datetime import datetime

    class _FakeSettings:
        user_timezone = "America/Sao_Paulo"

    monkeypatch.setattr(
        "backend.workspace.runtime_settings.runtime_settings", _FakeSettings()
    )

    result = bg._next_run("0 9 * * *")

    assert result is not None
    parsed = datetime.fromisoformat(result)
    # Armazenado em UTC, mas representando 9h em São Paulo (UTC-3).
    assert parsed.hour == 12

    # Erro/borda: timezone inexistente não derruba o agendamento — cai no
    # fuso local com aviso, em vez de propagar ZoneInfoNotFoundError.
    class _BrokenSettings:
        user_timezone = "Marte/Olympus_Mons"

    monkeypatch.setattr(
        "backend.workspace.runtime_settings.runtime_settings", _BrokenSettings()
    )
    fallback = bg._next_run("0 9 * * *")
    assert fallback is not None


def test_next_run_sem_timezone_configurado_usa_local_do_so(monkeypatch):
    class _NoTz:
        user_timezone = ""

    monkeypatch.setattr("backend.workspace.runtime_settings.runtime_settings", _NoTz())
    assert bg._next_run("0 9 * * *") is not None

    # Erro/borda: cron inválido continua retornando None (regressão) — o
    # timezone não pode ter transformado um erro de parse em exceção.
    assert bg._next_run("isso não é cron") is None


# ---------------------------------------------------------------------------
# Catch-up throttle (disparo atrasado)
# ---------------------------------------------------------------------------


def test_is_stale_so_marca_atraso_alem_da_janela_de_tolerancia():
    from datetime import UTC, datetime, timedelta

    now = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)

    # Atrasado muito além da janela (processo ficou horas parado) — pula.
    antigo = (now - timedelta(hours=5)).isoformat()
    assert bg._is_stale(antigo, now) is True

    # Happy path: atraso pequeno (dentro da tolerância) ainda dispara.
    recente = (now - timedelta(minutes=2)).isoformat()
    assert bg._is_stale(recente, now) is False

    # Erro/borda: timestamp ausente ou ilegível nunca é tratado como
    # atrasado — na dúvida executa, não engole a tarefa em silêncio.
    assert bg._is_stale(None, now) is False
    assert bg._is_stale("não é timestamp", now) is False


async def test_tick_pula_interval_atrasada_mas_executa_once_atrasada(db, monkeypatch):
    from datetime import UTC, datetime, timedelta

    executed: list[str] = []

    async def _fake_run_task(task, trigger, payload=None):
        executed.append(task.id)

    monkeypatch.setattr(bg, "run_task", _fake_run_task)

    muito_atrasado = (datetime.now(UTC) - timedelta(hours=6)).isoformat()

    recorrente = await bg.create_task(
        session_id="s",
        user_id="u",
        kind="routine",
        name="diária atrasada",
        instruction="i",
        trigger_type="interval",
        trigger_config={"cron_expr": "0 9 * * *"},
        next_run_at=muito_atrasado,
    )
    unica = await bg.create_task(
        session_id="s",
        user_id="u",
        kind="routine",
        name="única atrasada",
        instruction="i",
        trigger_type="once",
        next_run_at=muito_atrasado,
    )

    await bg.BackgroundScheduler().tick()

    # A recorrente atrasada é pulada e reagendada pro futuro...
    assert recorrente.id not in executed
    reagendada = await bg.get_task(recorrente.id)
    assert reagendada is not None
    assert reagendada.next_run_at is not None
    assert datetime.fromisoformat(reagendada.next_run_at) > datetime.now(UTC)

    # ...mas a execução única atrasada ainda roda (erro/borda: pular aqui
    # perderia uma tarefa que o usuário pediu explicitamente uma vez).
    assert unica.id in executed


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
# Sprint 3.1 — a thread da run aparece na sidebar (ListThreads)
# ---------------------------------------------------------------------------


async def test_run_task_incrementa_message_count_da_thread(db, monkeypatch):
    """A run bem-sucedida chama _increment_message_count(run_thread_id) — é o
    que faz ListThreads (filtra message_count>0) mostrá-la na sidebar. Antes a
    thread era gravada com message_count=0 e nunca aparecia.

    Testa o wiring com mock (o caminho real de I/O de sessão publica eventos
    que não isolam por event-loop nos testes; ListThreads+increment reais têm
    cobertura própria em test_threads_*)."""
    agent = _FakeAgent(result={"messages": [{"content": "feito"}]})
    _patch_agent(monkeypatch, agent)

    upserts: list[str] = []
    increments: list[str] = []

    async def _fake_upsert(thread_id, title=None, workspace_id=None, mode=None):
        upserts.append(thread_id)

    async def _fake_increment(thread_id):
        increments.append(thread_id)

    monkeypatch.setattr("backend.api.handlers.threads._upsert_session", _fake_upsert)
    monkeypatch.setattr(
        "backend.api.handlers.threads._increment_message_count", _fake_increment
    )

    task = await bg.create_task(
        session_id="sess-vis",
        user_id="u",
        kind="routine",
        name="Visível",
        instruction="i",
        trigger_type="manual",
        trigger_config={},
        workspace_id="ws1",
    )

    run_thread_id = await bg.run_task(task, "manual")
    assert run_thread_id is not None
    # A run registrou a thread E incrementou seu message_count (→ listável).
    assert upserts == [run_thread_id]
    assert increments == [run_thread_id]

    # Erro/borda: run que FALHA (agente levanta) nem registra nem incrementa —
    # thread sem conteúdo não polui a sidebar.
    upserts.clear()
    increments.clear()
    _patch_agent(monkeypatch, _FakeAgent(exc=RuntimeError("boom")))
    task2 = await bg.create_task(
        session_id="sess-vis",
        user_id="u",
        kind="routine",
        name="Falha",
        instruction="i",
        trigger_type="manual",
        trigger_config={},
    )
    assert await bg.run_task(task2, "manual") is None
    assert upserts == []
    assert increments == []


# ---------------------------------------------------------------------------
# Sprint 3.2 — a run reporta o resultado de volta na sessão-mãe
# ---------------------------------------------------------------------------


async def test_run_task_reporta_conclusao_na_sessao_mae(db, monkeypatch):
    """Ao concluir, a run posta uma AIMessage no checkpoint da sessão que criou
    a task (task.session_id) via graph.aupdate_state — o orquestrador principal
    fica sabendo que a tarefa terminou (Hermes/Paperclip)."""
    agent = _FakeAgent(result={"messages": [{"content": "3 arquivos alterados"}]})
    _patch_agent(monkeypatch, agent)

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr("backend.api.handlers.threads._upsert_session", _noop)
    monkeypatch.setattr("backend.api.handlers.threads._increment_message_count", _noop)

    task = await bg.create_task(
        session_id="parent-sess",
        user_id="u",
        kind="routine",
        name="Auditoria",
        instruction="i",
        trigger_type="manual",
        trigger_config={},
    )
    run_thread_id = await bg.run_task(task, "manual")

    assert len(agent.state_updates) == 1
    upd = agent.state_updates[0]
    assert upd["config"]["configurable"]["thread_id"] == "parent-sess"
    msg = upd["values"]["messages"][0]
    assert "Auditoria" in msg.content  # nome da task
    assert "3 arquivos alterados" in msg.content  # resumo
    assert run_thread_id in msg.content  # link pra thread da run


async def test_report_to_parent_session_pula_sem_sessao_mae(db, monkeypatch):
    """Erro/borda: sem session_id (ou session_id == run_thread_id) não reporta
    — não há sessão-mãe distinta pra notificar."""
    agent = _FakeAgent()
    _patch_agent(monkeypatch, agent)

    task_sem = bg.BackgroundTask(
        id="t",
        session_id="",
        user_id="u",
        kind="routine",
        name="X",
        instruction="i",
        trigger_type="manual",
    )
    assert await bg.report_to_parent_session(task_sem, "bg-1", "resumo") is False
    assert agent.state_updates == []

    task_self = bg.BackgroundTask(
        id="t",
        session_id="bg-1",
        user_id="u",
        kind="routine",
        name="X",
        instruction="i",
        trigger_type="manual",
    )
    assert await bg.report_to_parent_session(task_self, "bg-1", "resumo") is False


# ---------------------------------------------------------------------------
# HITL em background — interrupt → awaiting_approval → resume (Sprint 1.3)
# ---------------------------------------------------------------------------


async def test_run_task_interrupt_marks_awaiting_and_resume_completes(db, monkeypatch):
    """Uma run que pausa em HITL fica 'awaiting_approval' (não 'done') e o
    resume_background_run a retoma até concluir. O interrupt é detectado pelo
    ``__interrupt__`` no resultado do ainvoke (LangGraph pausa, não levanta)."""
    from types import SimpleNamespace

    # 1º ainvoke (run_task) pausa; 2º ainvoke (resume) conclui.
    agent = _SeqAgent(
        [
            {"__interrupt__": [SimpleNamespace(value=[{"action": "file_write"}])]},
            {"messages": [{"content": "arquivo escrito"}]},
        ]
    )
    _patch_agent(monkeypatch, agent)

    async def _fake_upsert(thread_id, title=None, workspace_id=None):
        return None

    monkeypatch.setattr("backend.api.handlers.threads._upsert_session", _fake_upsert)

    task = await bg.create_task(
        session_id="sess-hitl",
        user_id="u-hitl",
        kind="routine",
        name="Escreve",
        instruction="Escreva um arquivo",
        trigger_type="manual",
        trigger_config={"permission_mode": "ask"},  # modo que interrompe
        workspace_id="ws-h",
    )

    run_thread_id = await bg.run_task(task, "manual")
    assert run_thread_id is not None  # thread visível mesmo pausada

    runs = await bg.list_runs("sess-hitl")
    assert len(runs) == 1
    assert runs[0]["status"] == "awaiting_approval"
    assert runs[0]["finished_at"] is None  # não terminou — aguarda aprovação
    assert "file_write" in runs[0]["summary"]
    run_id = runs[0]["id"]

    # Resume aprovando → conclui.
    status = await bg.resume_background_run(run_id, "approve")
    assert status == "done"
    assert len(agent.calls) == 2
    from langgraph.types import Command

    assert isinstance(agent.calls[1]["input"], Command)  # resume via Command

    runs2 = await bg.list_runs("sess-hitl")
    assert runs2[0]["status"] == "done"
    assert runs2[0]["summary"] == "arquivo escrito"


async def test_resume_background_run_rejects_unknown_or_finished_run(db, monkeypatch):
    """Erro/borda: resume de run inexistente ou já concluída devolve None sem
    tocar no agente."""
    agent = _SeqAgent([{"messages": [{"content": "x"}]}])
    _patch_agent(monkeypatch, agent)

    async def _fake_upsert(*a, **k):
        return None

    monkeypatch.setattr("backend.api.handlers.threads._upsert_session", _fake_upsert)

    # Run inexistente.
    assert await bg.resume_background_run("nao-existe", "approve") is None

    # Run que concluiu (status 'done') não é retomável.
    task = await bg.create_task(
        session_id="sess-fin",
        user_id="u",
        kind="routine",
        name="Feito",
        instruction="i",
        trigger_type="manual",
        trigger_config={},
    )
    await bg.run_task(task, "manual")  # conclui 'done' (sem interrupt)
    done_run = (await bg.list_runs("sess-fin"))[0]
    assert done_run["status"] == "done"
    assert await bg.resume_background_run(done_run["id"], "approve") is None


async def test_resume_background_run_reject_and_edit_decisions(db, monkeypatch):
    """decision='reject' e decision='edit:<json>' montam o Command(resume=...)
    correto (action distinta dos demais); ambos concluem no fake agent."""
    from langgraph.types import Command

    task_reject = await bg.create_task(
        session_id="sess-reject",
        user_id="u",
        kind="routine",
        name="R",
        instruction="i",
        trigger_type="manual",
        trigger_config={"permission_mode": "ask"},
    )
    run_id_reject = "run-reject"
    await bg._insert_run(run_id_reject, task_reject, "bg-reject", "manual")
    await bg._mark_run_awaiting(run_id_reject, "aguardando terminal")

    agent = _SeqAgent([{"messages": [{"content": "rejeitado"}]}])
    _patch_agent(monkeypatch, agent)
    status = await bg.resume_background_run(run_id_reject, "reject")
    assert status == "done"
    assert isinstance(agent.calls[0]["input"], Command)
    assert agent.calls[0]["input"].resume == {"action": "reject"}

    task_edit = await bg.create_task(
        session_id="sess-edit",
        user_id="u",
        kind="routine",
        name="E",
        instruction="i",
        trigger_type="manual",
        trigger_config={"permission_mode": "ask"},
    )
    run_id_edit = "run-edit"
    await bg._insert_run(run_id_edit, task_edit, "bg-edit", "manual")
    await bg._mark_run_awaiting(run_id_edit, "aguardando terminal")

    agent2 = _SeqAgent([{"messages": [{"content": "editado"}]}])
    _patch_agent(monkeypatch, agent2)
    status2 = await bg.resume_background_run(run_id_edit, 'edit:{"cmd": "ls"}')
    assert status2 == "done"
    assert agent2.calls[0]["input"].resume == {"action": "edit", "args": {"cmd": "ls"}}


async def test_resume_background_run_invalid_decision_marks_error(db, monkeypatch):
    """Erro/borda: decision desconhecida levanta ValueError, capturado pelo
    except geral — a run vira 'error' (não fica presa em awaiting_approval) e
    o resume devolve None."""
    task = await bg.create_task(
        session_id="sess-bad-decision",
        user_id="u",
        kind="routine",
        name="X",
        instruction="i",
        trigger_type="manual",
        trigger_config={"permission_mode": "ask"},
    )
    run_id = "run-bad-decision"
    await bg._insert_run(run_id, task, "bg-bad", "manual")
    await bg._mark_run_awaiting(run_id, "aguardando terminal")

    agent = _SeqAgent([{"messages": [{"content": "nunca chega"}]}])
    _patch_agent(monkeypatch, agent)

    status = await bg.resume_background_run(run_id, "banana")
    assert status is None
    assert agent.calls == []  # nem chegou a invocar o agente

    run = await bg._get_run(run_id)
    assert run is not None
    assert run["status"] == "error"
    assert "decision inválida" in run["summary"]


async def test_resume_background_run_repauses_same_turn(db, monkeypatch):
    """Se o resume dispara OUTRA ação destrutiva no mesmo turno, a run continua
    'awaiting_approval' (não vira 'done') — retomável de novo."""
    from types import SimpleNamespace

    task = await bg.create_task(
        session_id="sess-repause",
        user_id="u",
        kind="routine",
        name="Y",
        instruction="i",
        trigger_type="manual",
        trigger_config={"permission_mode": "ask"},
    )
    run_id = "run-repause"
    await bg._insert_run(run_id, task, "bg-repause", "manual")
    await bg._mark_run_awaiting(run_id, "aguardando terminal")

    agent = _SeqAgent(
        [{"__interrupt__": [SimpleNamespace(value=[{"action": "terminal"}])]}]
    )
    _patch_agent(monkeypatch, agent)

    status = await bg.resume_background_run(run_id, "approve")
    assert status == "awaiting_approval"

    run = await bg._get_run(run_id)
    assert run is not None
    assert run["status"] == "awaiting_approval"
    assert "terminal" in run["summary"]


async def test_resume_background_run_ainvoke_exception_marks_error(db, monkeypatch):
    """Erro/borda: exceção do agent.ainvoke durante o resume marca a run como
    'error' (não fica presa em awaiting_approval) e devolve None."""
    task = await bg.create_task(
        session_id="sess-resume-exc",
        user_id="u",
        kind="routine",
        name="Z",
        instruction="i",
        trigger_type="manual",
        trigger_config={"permission_mode": "ask"},
    )
    run_id = "run-resume-exc"
    await bg._insert_run(run_id, task, "bg-resume-exc", "manual")
    await bg._mark_run_awaiting(run_id, "aguardando terminal")

    agent = _FakeAgent(exc=RuntimeError("modelo indisponível"))
    _patch_agent(monkeypatch, agent)

    status = await bg.resume_background_run(run_id, "approve")
    assert status is None

    run = await bg._get_run(run_id)
    assert run is not None
    assert run["status"] == "error"
    assert "modelo indisponível" in run["summary"]


async def test_resume_background_run_reporta_conclusao_na_sessao_mae(db, monkeypatch):
    """report_to_parent_session também é chamado a partir do resume (não só de
    run_task) — a sessão-mãe recebe o aviso de conclusão pós-aprovação."""
    task = await bg.create_task(
        session_id="parent-resume",
        user_id="u",
        kind="routine",
        name="Aprovada",
        instruction="i",
        trigger_type="manual",
        trigger_config={"permission_mode": "ask"},
    )
    run_id = "run-report-resume"
    await bg._insert_run(run_id, task, "bg-report-resume", "manual")
    await bg._mark_run_awaiting(run_id, "aguardando terminal")

    agent = _SeqAgent([{"messages": [{"content": "ação concluída"}]}])
    _patch_agent(monkeypatch, agent)

    status = await bg.resume_background_run(run_id, "approve")
    assert status == "done"
    assert len(agent.state_updates) == 1
    upd = agent.state_updates[0]
    assert upd["config"]["configurable"]["thread_id"] == "parent-resume"
    assert "ação concluída" in upd["values"]["messages"][0].content


async def test_describe_interrupt_non_list_payload_and_internal_exception():
    """Erro/borda: payload que não é lista/dict cai no fallback str truncado;
    um item cujo 'action_request' não é dict dispara o except interno (e
    também cai no mesmo fallback, sem propagar)."""
    assert bg._describe_interrupt("motivo qualquer") == (
        "Aguardando aprovação: motivo qualquer"
    )

    # action_request não-dict: `"oops".get(...)` estoura AttributeError,
    # capturado pelo except interno de _describe_interrupt.
    payload = [{"action_request": "oops"}]
    desc = bg._describe_interrupt(payload)
    assert desc.startswith("Aguardando aprovação: ")
    assert "oops" in desc


async def test_report_to_parent_session_tolera_falha_do_aupdate_state(db, monkeypatch):
    """Erro/borda: aupdate_state falhando (ex.: sessão-mãe corrompida) não deve
    propagar — report_to_parent_session é best-effort e devolve False."""

    class _BoomAgent:
        async def aupdate_state(self, config, values):
            raise RuntimeError("checkpoint indisponível")

    _patch_agent(monkeypatch, _BoomAgent())

    task = bg.BackgroundTask(
        id="t-boom",
        session_id="parent-boom",
        user_id="u",
        kind="routine",
        name="X",
        instruction="i",
        trigger_type="manual",
    )
    ok = await bg.report_to_parent_session(task, "bg-boom", "resumo")
    assert ok is False


# ---------------------------------------------------------------------------
# Sprint 3.3 — tools do orquestrador: listar/consultar tasks e runs
# ---------------------------------------------------------------------------


async def test_orchestrator_tools_list_status_result(db, monkeypatch):
    """list_background_tasks/get_task_status/get_task_result devolvem o estado
    das tasks e runs da sessão — o orquestrador principal fica sabendo o que
    está rodando/terminou. Erro/borda: task/run inexistente devolve erro
    tipado, não exceção (§11)."""
    import json as _json

    # Hermético: invocar tools via .ainvoke dispara callbacks do LangChain que
    # sondam o ambiente via `git describe` (langsmith) — desligado aqui para não
    # depender do git ambiente nem da ordem do suite.
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")

    from backend.tools.background import (
        get_task_result,
        get_task_status,
        list_background_tasks,
    )

    task = await bg.create_task(
        session_id="sess-tools",
        user_id="u",
        kind="routine",
        name="Diária",
        instruction="i",
        trigger_type="manual",
        trigger_config={},
    )
    # Registra uma run concluída manualmente (sem invocar o agente).
    run_id = "run-xyz"
    await bg._insert_run(run_id, task, "sess-tools", "manual")
    await bg._finish_run(run_id, "done", "3 itens processados")

    from langchain_core.runnables import RunnableConfig

    cfg: RunnableConfig = {"configurable": {"thread_id": "sess-tools", "user_id": "u"}}

    listed = _json.loads(await list_background_tasks.ainvoke({}, config=cfg))
    assert listed["status"] == "ok"
    assert len(listed["tasks"]) == 1
    assert listed["tasks"][0]["task_id"] == task.id
    assert listed["tasks"][0]["last_run"]["status"] == "done"

    status = _json.loads(
        await get_task_status.ainvoke({"task_id": task.id}, config=cfg)
    )
    assert status["status"] == "ok"
    assert any(r["run_id"] == run_id for r in status["runs"])

    result = _json.loads(await get_task_result.ainvoke({"run_id": run_id}, config=cfg))
    assert result["status"] == "ok"
    assert result["summary"] == "3 itens processados"

    # Erro/borda: ids inexistentes → erro tipado.
    bad_status = _json.loads(
        await get_task_status.ainvoke({"task_id": "nope"}, config=cfg)
    )
    assert bad_status["status"] == "error"
    bad_result = _json.loads(
        await get_task_result.ainvoke({"run_id": "nope"}, config=cfg)
    )
    assert bad_result["status"] == "error"


async def test_list_background_tasks_sem_session_id_e_task_sem_run(db, monkeypatch):
    """Erro/borda: config sem thread_id → erro tipado (sem exceção). Task que
    nunca rodou aparece com last_run=None (não quebra o dict de latest_by_task)."""
    import json as _json

    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")

    from langchain_core.runnables import RunnableConfig

    from backend.tools.background import list_background_tasks

    sem_thread: RunnableConfig = {"configurable": {"user_id": "u"}}
    out_sem = _json.loads(await list_background_tasks.ainvoke({}, config=sem_thread))
    assert out_sem["status"] == "error"

    await bg.create_task(
        session_id="sess-no-run",
        user_id="u",
        kind="routine",
        name="Nunca rodou",
        instruction="i",
        trigger_type="manual",
        trigger_config={},
    )
    cfg: RunnableConfig = {"configurable": {"thread_id": "sess-no-run", "user_id": "u"}}
    out = _json.loads(await list_background_tasks.ainvoke({}, config=cfg))
    assert out["status"] == "ok"
    assert len(out["tasks"]) == 1
    assert out["tasks"][0]["last_run"] is None


# ---------------------------------------------------------------------------
# Sprint 3.4 — intervenção: cancelar / aprovar via tool do orquestrador
# ---------------------------------------------------------------------------


async def test_cancel_and_approve_task_action(db, monkeypatch):
    """cancel_background_run encerra uma run pendente; a tool approve_task_action
    (decision='cancel') faz o mesmo pelo orquestrador. Erro/borda: cancelar uma
    run já concluída → None / erro tipado."""
    import json as _json

    from langchain_core.runnables import RunnableConfig

    from backend.tools.background import approve_task_action

    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")

    task = await bg.create_task(
        session_id="sess-cancel",
        user_id="u",
        kind="routine",
        name="Perigosa",
        instruction="i",
        trigger_type="manual",
        trigger_config={"permission_mode": "ask"},
    )
    run_id = "run-await"
    await bg._insert_run(run_id, task, "sess-cancel", "manual")
    await bg._mark_run_awaiting(run_id, "aguardando terminal")

    cfg: RunnableConfig = {"configurable": {"thread_id": "sess-cancel", "user_id": "u"}}
    out = _json.loads(
        await approve_task_action.ainvoke(
            {"run_id": run_id, "decision": "cancel"}, config=cfg
        )
    )
    assert out["status"] == "ok"
    assert out["run_status"] == "cancelled"

    run = await bg._get_run(run_id)
    assert run is not None
    assert run["status"] == "cancelled"

    # Erro/borda: cancelar de novo (já não está pendente) → None / erro tipado.
    assert await bg.cancel_background_run(run_id) is None
    out2 = _json.loads(
        await approve_task_action.ainvoke(
            {"run_id": run_id, "decision": "cancel"}, config=cfg
        )
    )
    assert out2["status"] == "error"


async def test_approve_task_action_approve_reject_edit(db, monkeypatch):
    """approve_task_action delega approve/reject/edit para resume_background_run
    (só 'cancel' tinha cobertura via tool até aqui)."""
    import json as _json

    from langchain_core.runnables import RunnableConfig

    from backend.tools.background import approve_task_action

    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")

    task = await bg.create_task(
        session_id="sess-approve-tool",
        user_id="u",
        kind="routine",
        name="Perigosa",
        instruction="i",
        trigger_type="manual",
        trigger_config={"permission_mode": "ask"},
    )
    cfg: RunnableConfig = {
        "configurable": {"thread_id": "sess-approve-tool", "user_id": "u"}
    }

    run_approve = "run-tool-approve"
    await bg._insert_run(run_approve, task, "sess-approve-tool", "manual")
    await bg._mark_run_awaiting(run_approve, "aguardando terminal")
    agent = _SeqAgent([{"messages": [{"content": "ok"}]}])
    _patch_agent(monkeypatch, agent)
    out_approve = _json.loads(
        await approve_task_action.ainvoke(
            {"run_id": run_approve, "decision": "approve"}, config=cfg
        )
    )
    assert out_approve == {"status": "ok", "run_status": "done"}

    run_reject = "run-tool-reject"
    await bg._insert_run(run_reject, task, "sess-approve-tool", "manual")
    await bg._mark_run_awaiting(run_reject, "aguardando terminal")
    agent2 = _SeqAgent([{"messages": [{"content": "recusado"}]}])
    _patch_agent(monkeypatch, agent2)
    out_reject = _json.loads(
        await approve_task_action.ainvoke(
            {"run_id": run_reject, "decision": "reject"}, config=cfg
        )
    )
    assert out_reject == {"status": "ok", "run_status": "done"}
    assert agent2.calls[0]["input"].resume == {"action": "reject"}

    run_edit = "run-tool-edit"
    await bg._insert_run(run_edit, task, "sess-approve-tool", "manual")
    await bg._mark_run_awaiting(run_edit, "aguardando terminal")
    agent3 = _SeqAgent([{"messages": [{"content": "editado"}]}])
    _patch_agent(monkeypatch, agent3)
    out_edit = _json.loads(
        await approve_task_action.ainvoke(
            {"run_id": run_edit, "decision": 'edit:{"path": "x"}'}, config=cfg
        )
    )
    assert out_edit == {"status": "ok", "run_status": "done"}
    assert agent3.calls[0]["input"].resume == {"action": "edit", "args": {"path": "x"}}


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
    # Força o vencimento (next_run_at no passado, mas dentro da janela de
    # catch-up — passado remoto seria pulado como disparo obsoleto).
    from datetime import UTC as _UTC
    from datetime import datetime as _dt
    from datetime import timedelta as _td

    vencido = (_dt.now(_UTC) - _td(minutes=1)).isoformat()
    await bg._set_next_run(due.id, vencido)

    disabled = await bg.create_task(
        session_id="s",
        user_id="u",
        kind="routine",
        name="off",
        instruction="i",
        trigger_type="interval",
        trigger_config={"cron_expr": "* * * * *"},
    )
    await bg._set_next_run(disabled.id, vencido)
    await bg.update_task(disabled.id, enabled=False)

    await bg.get_scheduler().tick()

    assert fired == [due.id]  # só a vencida e habilitada roda
    # Reagendou para o futuro.
    rescheduled = await bg.get_task(due.id)
    assert rescheduled is not None
    assert rescheduled.next_run_at != vencido


# ---------------------------------------------------------------------------
# Webhook → IA
# ---------------------------------------------------------------------------


async def test_dispatch_webhook_matches_provider_and_event(db, monkeypatch):
    fired: list[tuple[str, str]] = []

    async def _fake_run(task, trigger_source, payload=None):
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


# ---------------------------------------------------------------------------
# Delegação de subagente (tool `task`) → histórico na aba Tarefas
# ---------------------------------------------------------------------------


async def test_record_subagent_delegation_creates_anchor_and_run(db):
    await bg.record_subagent_delegation(
        session_id="s1",
        user_id="u1",
        subagent_type="coder",
        description="Crie um arquivo X",
        status="done",
        summary="Arquivo criado.",
        workspace_id="ws1",
    )

    tasks = await bg.list_tasks("s1")
    assert len(tasks) == 1
    anchor = tasks[0]
    assert anchor.kind == "subagent"
    assert anchor.name == "Subagente: coder"
    assert anchor.trigger_config == {"subagent_type": "coder"}

    runs = await bg.list_runs("s1")
    assert len(runs) == 1
    assert runs[0]["task_id"] == anchor.id
    assert runs[0]["trigger_source"] == "subagent"
    assert runs[0]["status"] == "done"
    assert runs[0]["summary"] == "Arquivo criado."


async def test_record_subagent_delegation_reuses_anchor_across_calls(db):
    """Segunda delegação do mesmo subagente na mesma thread não duplica a âncora."""
    await bg.record_subagent_delegation(
        session_id="s1",
        user_id="u1",
        subagent_type="search",
        description="Pesquise X",
        status="done",
        summary="ok",
    )
    await bg.record_subagent_delegation(
        session_id="s1",
        user_id="u1",
        subagent_type="search",
        description="Pesquise Y",
        status="error",
        summary="erro de rede",
    )

    tasks = await bg.list_tasks("s1")
    assert len(tasks) == 1  # âncora única, reusada

    runs = await bg.list_runs("s1")
    assert len(runs) == 2
    assert {r["status"] for r in runs} == {"done", "error"}


async def test_record_subagent_delegation_tolerates_db_failure(db, monkeypatch):
    """Erro/borda: falha ao persistir nunca deve propagar (best-effort)."""

    async def _boom() -> None:
        raise RuntimeError("db indisponível")

    monkeypatch.setattr(bg, "_get_db", _boom)

    # Não levanta — apenas loga e segue.
    await bg.record_subagent_delegation(
        session_id="s1",
        user_id="u1",
        subagent_type="coder",
        description="x",
        status="done",
        summary="y",
    )


# ---------------------------------------------------------------------------
# Sprint 23 — Kanban ligado à execução real (status/claim/block)
# ---------------------------------------------------------------------------


async def test_create_task_status_inicial_e_ready_nao_todo(db):
    """Regressão do bug real: antes deste sprint toda tarefa nascia com o
    DEFAULT 'todo' do schema e nunca saía de lá — o board ficava sempre
    vazio. `enabled=True` (o default de `create_task`) precisa nascer
    "ready" pra competir pelo claim desde a primeira run."""
    task = await bg.create_task(
        session_id="s1",
        user_id="u1",
        kind="routine",
        name="A",
        instruction="i",
        trigger_type="interval",
        trigger_config={"cron_expr": "0 9 * * *"},
    )
    assert task.status == "ready"

    # Erro/borda: o dataclass devolvido por create_task precisa bater com o
    # que foi de fato persistido — não só o valor em memória.
    persistida = await bg.get_task(task.id)
    assert persistida is not None
    assert persistida.status == "ready"


async def test_run_task_recorrente_volta_pra_ready_ao_concluir(db, monkeypatch):
    """Tarefa recorrente nunca termina — `done` seria um estado terminal
    errado pra algo que roda de novo amanhã."""
    from backend.scheduling import kanban

    agent = _FakeAgent(result={"messages": [{"content": "ok"}]})
    _patch_agent(monkeypatch, agent)

    async def _noop_upsert(*_a, **_k) -> None:
        return None

    monkeypatch.setattr("backend.api.handlers.threads._upsert_session", _noop_upsert)

    task = await bg.create_task(
        session_id="s1",
        user_id="u1",
        kind="routine",
        name="Recorrente",
        instruction="i",
        trigger_type="interval",
        trigger_config={"cron_expr": "0 9 * * *"},
    )
    assert (await kanban.get_task_status(task.id))["status"] == "ready"

    await bg.run_task(task, "scheduler")

    estado = await kanban.get_task_status(task.id)
    assert estado["status"] == "ready"


async def test_run_task_unica_vira_done_ao_concluir(db, monkeypatch):
    from backend.scheduling import kanban

    agent = _FakeAgent(result={"messages": [{"content": "ok"}]})
    _patch_agent(monkeypatch, agent)

    async def _noop_upsert(*_a, **_k) -> None:
        return None

    monkeypatch.setattr("backend.api.handlers.threads._upsert_session", _noop_upsert)

    task = await bg.create_task(
        session_id="s1",
        user_id="u1",
        kind="routine",
        name="Única",
        instruction="i",
        trigger_type="manual",
        trigger_config={},
    )

    await bg.run_task(task, "manual")

    estado = await kanban.get_task_status(task.id)
    assert estado["status"] == "done"


async def test_run_task_erro_vira_blocked_transient_em_vez_de_travar_em_running(
    db, monkeypatch
):
    """Erro/borda crítica: sem isso, uma run que lança deixaria o card preso
    em `running` para sempre — o motivo real do incidente que este sprint
    corrige."""
    from backend.scheduling import kanban

    agent = _FakeAgent(exc=RuntimeError("LLM caiu"))
    _patch_agent(monkeypatch, agent)

    task = await bg.create_task(
        session_id="s1",
        user_id="u1",
        kind="routine",
        name="Falha",
        instruction="i",
        trigger_type="manual",
        trigger_config={},
    )

    await bg.run_task(task, "manual")

    estado = await kanban.get_task_status(task.id)
    assert estado["status"] == "blocked"
    assert estado["block_kind"] == "transient"
    assert "LLM caiu" in (estado["block_reason"] or "")


async def test_run_task_nao_duplica_quando_claim_ja_foi_tomado(db, monkeypatch):
    """Erro/borda de corrida: duas chamadas de `run_task` pra mesma task
    (tick do scheduler + disparo manual quase simultâneo) — a segunda não
    cria uma 2ª run."""
    from backend.scheduling import kanban

    agent = _FakeAgent(result={"messages": [{"content": "ok"}]})
    _patch_agent(monkeypatch, agent)

    async def _noop_upsert(*_a, **_k) -> None:
        return None

    monkeypatch.setattr("backend.api.handlers.threads._upsert_session", _noop_upsert)

    task = await bg.create_task(
        session_id="s1",
        user_id="u1",
        kind="routine",
        name="Corrida",
        instruction="i",
        trigger_type="manual",
        trigger_config={},
    )

    # Simula outro worker já tendo pego o claim antes desta chamada.
    assert await kanban.claim_task(task.id, "run-de-outro-worker") is True

    resultado = await bg.run_task(task, "manual")

    assert resultado is None
    assert len(agent.calls) == 0
    runs = await bg.list_runs("s1")
    assert runs == []


async def test_update_task_toggle_sincroniza_status(db):
    from backend.scheduling import kanban

    task = await bg.create_task(
        session_id="s1",
        user_id="u1",
        kind="routine",
        name="Toggle",
        instruction="i",
        trigger_type="manual",
        trigger_config={},
    )
    assert (await kanban.get_task_status(task.id))["status"] == "ready"

    await bg.update_task(task.id, enabled=False)
    assert (await kanban.get_task_status(task.id))["status"] == "todo"

    await bg.update_task(task.id, enabled=True)
    assert (await kanban.get_task_status(task.id))["status"] == "ready"


async def test_update_task_nao_reabilita_por_cima_de_bloqueio_ativo(db):
    """Erro/borda: reabilitar uma tarefa bloqueada (ex.: budget estourado)
    não pode fingir que o bloqueio não existe mais."""
    from backend.scheduling import kanban

    task = await bg.create_task(
        session_id="s1",
        user_id="u1",
        kind="routine",
        name="Bloqueada",
        instruction="i",
        trigger_type="manual",
        trigger_config={},
    )
    await kanban.block_task(task.id, "capability", "orçamento estourado")

    await bg.update_task(task.id, enabled=True)

    estado = await kanban.get_task_status(task.id)
    assert estado["status"] == "blocked"
    assert estado["block_kind"] == "capability"
