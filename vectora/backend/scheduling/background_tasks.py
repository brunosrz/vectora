"""Tarefas em segundo plano por session — rotina (cron), heartbreak (evento) e manual.

Uma *background task* pertence a uma session do chat (`session_id` = thread_id) e roda
o agente Vectora autonomamente. Cada execução cria uma thread própria (`run_thread_id`),
registrada em `vectora_sessions` para aparecer na sidebar, e uma linha em
`vectora_background_runs` com o resultado.

Triggers:
    interval — cron (`trigger_config={"cron_expr": "..."}`), avaliado pelo BackgroundScheduler.
    webhook  — disparado por `dispatch_webhook_event` quando um evento externo casa o filtro
               (`trigger_config={"provider": "github", "events": ["push", ...], "repo"?: ...}`).
    manual   — disparado sob demanda via `run_task(task, "manual")`.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, tzinfo
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from croniter import croniter

from backend.rbac.subscription import require_pro

logger = logging.getLogger(__name__)

VALID_KINDS = {"routine", "heartbreak", "subagent"}
#: "once" — execução única numa hora futura (``next_run_at`` explícito, sem
#: ``cron_expr`` recorrente) — usado por ``schedule_subagent_task``.
VALID_TRIGGERS = {"interval", "once", "webhook", "manual", "subagent"}
VALID_PRIORITIES = {"low", "normal", "high", "urgent"}

#: Limite de tarefas agendadas (não-``manual``) por workspace — evita um
#: workspace acumular centenas de tarefas `interval`/`webhook`/`once` sem
#: controle. Tarefas `manual` (só disparam sob demanda, nunca autônomas)
#: nunca contam pra essa quota.
MAX_SCHEDULED_TASKS_PER_WORKSPACE = 50

#: Tolerância pra disparo atrasado de tarefa recorrente. Além disso, o
#: disparo é pulado e a tarefa reagenda pro próximo horário — evita que
#: voltar de um downtime longo dispare de uma vez tudo que "venceu"
#: enquanto o processo estava parado.
CATCH_UP_GRACE = timedelta(minutes=10)


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------


@dataclass
class BackgroundTask:
    """Tarefa em segundo plano vinculada a uma session do chat."""

    id: str
    session_id: str
    user_id: str
    kind: str
    name: str
    instruction: str
    trigger_type: str
    trigger_config: dict[str, Any] = field(default_factory=dict)
    workspace_id: str | None = None
    enabled: bool = True
    last_run_at: str | None = None
    next_run_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    #: Estado do Kanban — lido/escrito via `backend.scheduling.kanban`,
    #: nunca por SQL direto aqui. Default `"todo"` casa com o `DEFAULT` do
    #: schema; `create_task` já promove pra `"ready"` antes de devolver.
    status: str = "todo"
    block_kind: str | None = None
    block_reason: str | None = None
    #: Perfil de agente customizado — `None` = comportamento padrão do
    #: orchestrator, sem mudança de instrução/modelo/budget.
    agent_profile_id: str | None = None
    #: Sinal visual do card no Kanban — "low" | "normal" | "high" | "urgent".
    #: Não afeta ordem real de claim (`claim_task` é FIFO por status).
    priority: str = "normal"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "kind": self.kind,
            "name": self.name,
            "instruction": self.instruction,
            "trigger_type": self.trigger_type,
            "trigger_config": self.trigger_config,
            "workspace_id": self.workspace_id,
            "enabled": self.enabled,
            "last_run_at": self.last_run_at,
            "next_run_at": self.next_run_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "block_kind": self.block_kind,
            "block_reason": self.block_reason,
            "agent_profile_id": self.agent_profile_id,
            "priority": self.priority,
        }


def _row_to_task(row: dict[str, Any]) -> BackgroundTask:
    cfg_raw = row.get("trigger_config") or "{}"
    try:
        cfg = json.loads(cfg_raw) if isinstance(cfg_raw, str) else dict(cfg_raw)
    except (ValueError, TypeError):
        cfg = {}
    return BackgroundTask(
        id=row["id"],
        session_id=row["session_id"],
        user_id=str(row["user_id"]),
        kind=row["kind"],
        name=row["name"],
        instruction=row["instruction"],
        trigger_type=row["trigger_type"],
        trigger_config=cfg,
        workspace_id=row.get("workspace_id"),
        enabled=bool(row.get("enabled", 1)),
        last_run_at=row.get("last_run_at"),
        next_run_at=row.get("next_run_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        status=row.get("status") or "todo",
        block_kind=row.get("block_kind"),
        block_reason=row.get("block_reason"),
        agent_profile_id=row.get("agent_profile_id"),
        priority=row.get("priority") or "normal",
    )


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------


async def _get_db() -> Any:
    """Conexão aiosqlite com row_factory de dict (injetável em testes)."""
    import aiosqlite

    from backend.settings import settings

    db_path = settings.db_dsn or ":memory:"
    conn: Any = await aiosqlite.connect(db_path)
    conn.row_factory = lambda c, r: dict(
        zip([col[0] for col in c.description], r, strict=False)
    )
    return conn


# ---------------------------------------------------------------------------
# Validação / agendamento
# ---------------------------------------------------------------------------


def _validate(
    kind: str,
    trigger_type: str,
    trigger_config: dict[str, Any],
    priority: str = "normal",
) -> None:
    if kind not in VALID_KINDS:
        msg = f"kind inválido: {kind!r}. Válidos: {sorted(VALID_KINDS)}"
        raise ValueError(msg)
    if trigger_type not in VALID_TRIGGERS:
        msg = f"trigger inválido: {trigger_type!r}. Válidos: {sorted(VALID_TRIGGERS)}"
        raise ValueError(msg)
    if priority not in VALID_PRIORITIES:
        msg = f"priority inválida: {priority!r}. Válidas: {sorted(VALID_PRIORITIES)}"
        raise ValueError(msg)
    if trigger_type == "interval":
        cron = (trigger_config or {}).get("cron_expr")
        if not cron:
            raise ValueError("trigger 'interval' requer trigger_config.cron_expr")
        # croniter levanta se o cron for inválido.
        croniter(cron, datetime.now(UTC))
    if trigger_type == "once" and (trigger_config or {}).get("cron_expr"):
        raise ValueError(
            "trigger 'once' não aceita trigger_config.cron_expr (não é recorrente)"
        )


async def _check_quota(conn: Any, workspace_id: str | None, trigger_type: str) -> None:
    """Levanta ValueError se o workspace já atingiu
    ``MAX_SCHEDULED_TASKS_PER_WORKSPACE`` tarefas não-manuais. Sem
    ``workspace_id`` (tarefas fora de um workspace) ou `trigger_type`
    'manual', não há quota — só recorrência/webhook autônomos contam."""
    if workspace_id is None or trigger_type == "manual":
        return
    cur = await conn.execute(
        "SELECT COUNT(*) AS cnt FROM vectora_background_tasks "
        "WHERE workspace_id = ? AND trigger_type != 'manual'",
        (workspace_id,),
    )
    row = await cur.fetchone()
    count = row["cnt"] if row else 0
    if count >= MAX_SCHEDULED_TASKS_PER_WORKSPACE:
        raise ValueError(
            f"limite de {MAX_SCHEDULED_TASKS_PER_WORKSPACE} tarefas agendadas "
            "por workspace atingido — pause ou remova tarefas existentes antes "
            "de criar novas"
        )


def _user_tzinfo() -> tzinfo:
    """Fuso configurado pelo usuário, ou o local do SO como fallback.

    Timezone inválido/indisponível degrada pro local com aviso (nunca
    lança) — um agendamento no fuso errado é melhor que o backend não
    subir, e o aviso deixa o problema visível no log.
    """
    try:
        from backend.workspace.runtime_settings import runtime_settings

        tz_name = runtime_settings.user_timezone
    except Exception:
        tz_name = ""
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            logger.warning(
                "background_tasks: timezone %r indisponível — usando local", tz_name
            )
    return datetime.now().astimezone().tzinfo or UTC


def _next_run(cron_expr: str | None) -> str | None:
    """Próximo disparo em UTC (formato de armazenamento) a partir do cron.

    O cron é interpretado no fuso do usuário — "0 9 * * 1" significa 9h da
    manhã pra quem escreveu, não 9h UTC. O retorno é sempre convertido pra
    UTC porque é o que `_list_due_interval_tasks` compara.
    """
    if not cron_expr:
        return None
    try:
        now_local = datetime.now(_user_tzinfo())
        nxt = croniter(cron_expr, now_local).get_next(datetime)
        return nxt.astimezone(UTC).isoformat()
    except Exception:
        logger.exception("background_tasks: cron inválido %r", cron_expr)
        return None


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def create_task(
    session_id: str,
    user_id: str,
    kind: str,
    name: str,
    instruction: str,
    trigger_type: str,
    trigger_config: dict[str, Any] | None = None,
    workspace_id: str | None = None,
    next_run_at: str | None = None,
    agent_profile_id: str | None = None,
    priority: str = "normal",
) -> BackgroundTask:
    """Cria uma tarefa. Levanta ValueError em kind/trigger/cron/priority inválidos.

    ``next_run_at`` — override explícito de quando disparar, usado por
    agendamentos de execução única (sem ``cron_expr`` recorrente, ex.
    ``schedule_subagent_task``). Sem isso, ``trigger_type="interval"``
    calcula normalmente a partir de ``trigger_config["cron_expr"]``.
    """
    cfg = trigger_config or {}
    _validate(kind, trigger_type, cfg, priority)
    if trigger_type == "webhook":
        require_pro()
    task_id = str(uuid4())
    if next_run_at is not None:
        next_run = next_run_at
    else:
        next_run = (
            _next_run(cfg.get("cron_expr")) if trigger_type == "interval" else None
        )

    # Task com data de disparo futura nasce em "scheduled" — distingue de
    # "todo" (sem data, esperando promoção por dependência) e de "ready"
    # (acionável agora, ex.: manual criada direto no board).
    status = "scheduled" if next_run is not None else "ready"

    conn = await _get_db()
    try:
        await _check_quota(conn, workspace_id, trigger_type)
        await conn.execute(
            """
            INSERT INTO vectora_background_tasks
              (id, session_id, workspace_id, user_id, kind, name, instruction,
               trigger_type, trigger_config, enabled, next_run_at, status,
               agent_profile_id, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """,
            (
                task_id,
                session_id,
                workspace_id,
                user_id,
                kind,
                name,
                instruction,
                trigger_type,
                json.dumps(cfg),
                next_run,
                status,
                agent_profile_id,
                priority,
            ),
        )
        await conn.commit()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()

    return BackgroundTask(
        id=task_id,
        session_id=session_id,
        user_id=user_id,
        kind=kind,
        name=name,
        instruction=instruction,
        trigger_type=trigger_type,
        trigger_config=cfg,
        workspace_id=workspace_id,
        enabled=True,
        next_run_at=next_run,
        status=status,
        agent_profile_id=agent_profile_id,
        priority=priority,
    )


async def list_tasks(session_id: str) -> list[BackgroundTask]:
    """Lista tarefas de uma session."""
    conn = await _get_db()
    try:
        cur = await conn.execute(
            "SELECT * FROM vectora_background_tasks WHERE session_id = ? "
            "ORDER BY created_at DESC",
            (session_id,),
        )
        rows = await cur.fetchall()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()
    return [_row_to_task(r) for r in rows]


async def get_task(task_id: str) -> BackgroundTask | None:
    """Retorna a tarefa pelo id, ou None."""
    conn = await _get_db()
    try:
        cur = await conn.execute(
            "SELECT * FROM vectora_background_tasks WHERE id = ?",
            (task_id,),
        )
        row = await cur.fetchone()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()
    return _row_to_task(row) if row else None


async def update_task(task_id: str, **updates: Any) -> BackgroundTask | None:
    """Atualiza campos (name, instruction, enabled, trigger_config). Recalcula
    next_run_at quando o cron muda. Retorna a tarefa atualizada ou None."""
    task = await get_task(task_id)
    if task is None:
        return None

    sets: list[str] = []
    args: list[Any] = []
    if "name" in updates and updates["name"] is not None:
        sets.append("name = ?")
        args.append(updates["name"])
    if "instruction" in updates and updates["instruction"] is not None:
        sets.append("instruction = ?")
        args.append(updates["instruction"])
    if "enabled" in updates and updates["enabled"] is not None:
        sets.append("enabled = ?")
        args.append(1 if updates["enabled"] else 0)
    if "trigger_config" in updates and updates["trigger_config"] is not None:
        cfg = updates["trigger_config"]
        _validate(task.kind, task.trigger_type, cfg)
        sets.append("trigger_config = ?")
        args.append(json.dumps(cfg))
        if task.trigger_type == "interval":
            sets.append("next_run_at = ?")
            args.append(_next_run(cfg.get("cron_expr")))
    if "priority" in updates and updates["priority"] is not None:
        priority = updates["priority"]
        if priority not in VALID_PRIORITIES:
            msg = (
                f"priority inválida: {priority!r}. Válidas: {sorted(VALID_PRIORITIES)}"
            )
            raise ValueError(msg)
        sets.append("priority = ?")
        args.append(priority)
    if not sets:
        return task

    sets.append("updated_at = ?")
    args.append(datetime.now(UTC).isoformat())
    args.append(task_id)

    conn = await _get_db()
    try:
        await conn.execute(
            f"UPDATE vectora_background_tasks SET {', '.join(sets)} WHERE id = ?",  # noqa: S608  # nosec B608
            tuple(args),
        )
        await conn.commit()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()

    if "enabled" in updates and updates["enabled"] is not None:
        await _sync_status_with_enabled(task_id, enabled=bool(updates["enabled"]))

    return await get_task(task_id)


async def _sync_status_with_enabled(task_id: str, *, enabled: bool) -> None:
    """Mantém `status` (Kanban) coerente com o toggle `enabled`.

    Desabilitar tira a tarefa do fluxo ativo (`todo`). Reabilitar só devolve
    pra `ready` se não houver um `block_kind` ativo — reabilitar por cima de
    um bloqueio (ex.: budget estourado) fingiria que ele não existe mais.
    """
    try:
        from backend.scheduling import kanban

        if not enabled:
            await kanban.set_status(task_id, "todo")
            return

        estado = await kanban.get_task_status(task_id)
        if estado.get("block_kind"):
            return
        await kanban.set_status(task_id, "ready")
    except Exception:
        # Kanban é camada acessória — falha aqui não pode impedir o toggle,
        # que já foi persistido acima.
        logger.warning(
            "background_tasks: falha ao sincronizar status do kanban", exc_info=True
        )


async def delete_task(task_id: str) -> bool:
    """Remove a tarefa. Retorna False se não existia."""
    conn = await _get_db()
    try:
        cur = await conn.execute(
            "DELETE FROM vectora_background_tasks WHERE id = ?",
            (task_id,),
        )
        await conn.commit()
        return (cur.rowcount or 0) > 0
    finally:
        with contextlib.suppress(Exception):
            await conn.close()


# ---------------------------------------------------------------------------
# Runs (histórico)
# ---------------------------------------------------------------------------


async def _insert_run(
    run_id: str, task: BackgroundTask, run_thread_id: str, trigger_source: str
) -> None:
    conn = await _get_db()
    try:
        await conn.execute(
            """
            INSERT INTO vectora_background_runs
              (id, task_id, session_id, run_thread_id, trigger_source, status)
            VALUES (?, ?, ?, ?, ?, 'running')
            """,
            (run_id, task.id, task.session_id, run_thread_id, trigger_source),
        )
        await conn.commit()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()


async def _finish_run(run_id: str, status: str, summary: str) -> None:
    conn = await _get_db()
    try:
        await conn.execute(
            "UPDATE vectora_background_runs SET status = ?, summary = ?, "
            "finished_at = ? WHERE id = ?",
            (status, summary[:4000], datetime.now(UTC).isoformat(), run_id),
        )
        await conn.commit()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()


async def _mark_run_awaiting(run_id: str, summary: str) -> None:
    """Marca a run como pendente de aprovação humana (HITL).

    Diferente de ``_finish_run``: NÃO grava ``finished_at`` — a run não terminou,
    está esperando resume (approve/reject/edit).
    """
    conn = await _get_db()
    try:
        await conn.execute(
            "UPDATE vectora_background_runs SET status = 'awaiting_approval', "
            "summary = ? WHERE id = ?",
            (summary[:4000], run_id),
        )
        await conn.commit()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()


async def _touch_last_run(task_id: str) -> None:
    conn = await _get_db()
    try:
        await conn.execute(
            "UPDATE vectora_background_tasks SET last_run_at = ? WHERE id = ?",
            (datetime.now(UTC).isoformat(), task_id),
        )
        await conn.commit()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()


async def list_runs(session_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Lista as execuções recentes de uma session."""
    conn = await _get_db()
    try:
        cur = await conn.execute(
            "SELECT * FROM vectora_background_runs WHERE session_id = ? "
            "ORDER BY started_at DESC LIMIT ?",
            (session_id, limit),
        )
        rows = await cur.fetchall()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()
    return list(rows)


# ---------------------------------------------------------------------------
# Delegação de subagente (tool `task`) — vira histórico na aba Tarefas
# ---------------------------------------------------------------------------


async def _get_or_create_subagent_anchor(
    session_id: str, user_id: str, subagent_type: str, workspace_id: str | None
) -> BackgroundTask:
    """Tarefa-âncora ``kind="subagent"`` por (session, subagent_type).

    Cada delegação via ``task()`` (deepagents ``SubAgentMiddleware``) roda
    dentro do mesmo turno, sem persistência própria — a âncora é criada uma
    vez e cada delegação vira um novo ``vectora_background_runs`` sob ela,
    igual a uma tarefa agendada acumulando histórico de execuções.
    """
    for t in await list_tasks(session_id):
        if (
            t.kind == "subagent"
            and t.trigger_config.get("subagent_type") == subagent_type
        ):
            return t
    return await create_task(
        session_id=session_id,
        user_id=user_id,
        kind="subagent",
        name=f"Subagente: {subagent_type}",
        instruction="",
        trigger_type="subagent",
        trigger_config={"subagent_type": subagent_type},
        workspace_id=workspace_id,
    )


async def record_subagent_delegation(
    session_id: str,
    user_id: str,
    subagent_type: str,
    description: str,
    status: str,
    summary: str,
    workspace_id: str | None = None,
) -> None:
    """Registra uma chamada à tool ``task()`` como execução na aba Tarefas.

    Best-effort — falha aqui nunca deve derrubar o stream de chat que a
    disparou (ver ``backend/api/adapters.py::adapt_stream``).
    """
    try:
        task = await _get_or_create_subagent_anchor(
            session_id, user_id, subagent_type, workspace_id
        )
        run_id = str(uuid4())
        await _insert_run(run_id, task, session_id, "subagent")
        await _finish_run(run_id, status, summary or description[:200])
        await _touch_last_run(task.id)
    except Exception:
        logger.exception(
            "record_subagent_delegation: falha ao registrar run subagent=%s",
            subagent_type,
        )


# ---------------------------------------------------------------------------
# Execução do agente
# ---------------------------------------------------------------------------


def _extract_summary(result: Any) -> str:
    """Texto da última mensagem do agente (resumo da run)."""
    try:
        msgs = result.get("messages") if isinstance(result, dict) else None
        if not msgs:
            return ""
        last = msgs[-1]
        content = getattr(last, "content", None)
        if content is None and isinstance(last, dict):
            content = last.get("content")
        if isinstance(content, str):
            return content[:2000]
        if isinstance(content, list):
            parts = [
                str(b.get("text", ""))
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            return "".join(parts)[:2000]
    except Exception:
        logger.debug("background_tasks: falha ao extrair resumo", exc_info=True)
    return ""


def _extract_interrupt(result: Any) -> Any | None:
    """Retorna o payload do 1º interrupt se a run pausou (HITL), senão ``None``.

    O LangGraph devolve ``result["__interrupt__"]`` (lista de ``Interrupt``)
    quando o grafo pausa numa tool sob HumanInTheLoopMiddleware, em vez de
    levantar exceção. O ``.value`` do primeiro interrupt carrega o pedido de
    aprovação (tool + args).
    """
    if not isinstance(result, dict):
        return None
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    first = interrupts[0]
    return getattr(first, "value", first)


def _describe_interrupt(payload: Any) -> str:
    """Descrição curta e humana do que a run está esperando aprovar.

    O payload do HumanInTheLoopMiddleware costuma ser uma lista de pedidos de
    ação (``action``/``tool``/``args``). Extrai os nomes das tools quando
    possível; fallback para ``str`` truncado.
    """
    try:
        items = payload if isinstance(payload, list) else [payload]
        names: list[str] = []
        for it in items:
            if isinstance(it, dict):
                name = (
                    it.get("action")
                    or it.get("tool")
                    or (it.get("action_request") or {}).get("action")
                )
                if name:
                    names.append(str(name))
        if names:
            return "Aguardando aprovação: " + ", ".join(names)
    except Exception:
        logger.debug("background_tasks: falha ao descrever interrupt", exc_info=True)
    return ("Aguardando aprovação: " + str(payload))[:2000]


def _emit_run_event(
    event: str, task: BackgroundTask, run_id: str, run_thread_id: str, summary: str = ""
) -> None:
    """Emite o estado da run no canal SSE de webhooks (consumido pelo painel)."""
    try:
        from backend.api.handlers.webhooks import _emit_sse_event

        _emit_sse_event(
            provider="background",
            event_type=f"background_run.{event}",
            data={
                "task_id": task.id,
                "task_name": task.name,
                "kind": task.kind,
                "session_id": task.session_id,
                "run_id": run_id,
                "run_thread_id": run_thread_id,
                "status": event,
                "summary": summary,
            },
        )
    except Exception:
        logger.debug("background_tasks: falha ao emitir SSE da run", exc_info=True)


async def _worktree_workspace_id(workspace_id: str, task_id: str) -> str:
    """Cria (ou reusa) um worktree isolado para a task e devolve o id do
    workspace efêmero apontando pra ele.

    Só tarefas em segundo plano passam por aqui. A delegação síncrona
    (``task()`` no meio de um turno do orchestrator) roda no workspace
    principal de propósito: ali o agente troca de persona pra um
    especialista dentro do mesmo turno, não é trabalho paralelo — isolar
    criaria um worktree por chamada e as edições ficariam invisíveis pro
    usuário, que está vendo o workspace principal. Paralelismo real, com
    duas runs mexendo em arquivo ao mesmo tempo, só acontece em segundo
    plano — é aqui que o isolamento é necessário.
    """
    from backend.scheduling.delegate import create_task_worktree
    from backend.workspace.workspace import workspace_registry

    worktree_path = await create_task_worktree(workspace_id, task_id)
    ws = workspace_registry.get_or_create(worktree_path)
    return ws.id


async def run_task(
    task: BackgroundTask,
    trigger_source: str,
    payload: dict[str, Any] | None = None,
) -> str | None:
    """Executa o agente para a tarefa. Cria uma thread visível e grava a run.

    Defensiva: nunca propaga exceção — falha vira run com status 'error'. Retorna
    o `run_thread_id` em sucesso, ou None em erro.
    """
    # Corte por budget acontece **antes** de criar a run: barrar depois já
    # teria gasto. A run em andamento nunca é abortada no meio — ver
    # `backend/scheduling/budget.py`.
    try:
        from backend.scheduling.budget import check_budget

        if not await check_budget(task.id):
            logger.info(
                "background_tasks: run de %s barrada por budget estourado", task.id
            )
            return None
    except Exception:
        # Budget é camada acessória: falha aqui não pode impedir a tarefa de
        # rodar, que é a função principal.
        logger.warning("background_tasks: checagem de budget falhou", exc_info=True)

    run_id = str(uuid4())

    # Claim atômico via CAS: pega a task só se ainda estiver `ready` e sem
    # claim — evita duas execuções concorrentes da mesma task (tick do
    # scheduler cruzando com um disparo manual, por exemplo). Como o Kanban
    # é camada acessória, um erro aqui não pode impedir a run de rodar —
    # só a corrida real (claim_task devolvendo `False`) barra.
    try:
        from backend.scheduling.kanban import claim_task

        if not await claim_task(task.id, run_id):
            logger.info(
                "background_tasks: %s já está com claim tomado — pulando run",
                task.id,
            )
            return None
    except Exception:
        logger.warning("background_tasks: claim_task falhou", exc_info=True)

    run_thread_id = f"bg-{task.id}-{int(datetime.now(UTC).timestamp())}"
    await _insert_run(run_id, task, run_thread_id, trigger_source)
    _emit_run_event("started", task, run_id, run_thread_id)

    try:
        from langchain_core.messages import HumanMessage

        from backend.services import agent_factory
        from backend.vtypes.context import ctx_from_config

        prompt = task.instruction
        model_override: str | None = None
        if task.agent_profile_id:
            # Perfil de agente customizado: a instrução da task é o "o
            # quê", a do perfil é o "como" — concatenadas, nunca uma
            # substituindo a outra. Falha ao carregar o perfil (apagado,
            # DB indisponível) degrada pro comportamento padrão da task,
            # nunca derruba a run.
            try:
                from backend.services.agent_profiles import get_profile

                profile = await get_profile(task.agent_profile_id)
                if profile is not None:
                    if profile.instruction_path:
                        try:
                            from pathlib import Path

                            persona = Path(profile.instruction_path).read_text(
                                encoding="utf-8"
                            )
                            prompt = f"{persona}\n\n---\n\n{prompt}"
                        except OSError:
                            logger.warning(
                                "background_tasks: instruction_path do perfil %s "
                                "ilegível",
                                task.agent_profile_id,
                                exc_info=True,
                            )
                    model_override = profile.model_override
            except Exception:
                logger.warning(
                    "background_tasks: falha ao carregar perfil %s da task %s",
                    task.agent_profile_id,
                    task.id,
                    exc_info=True,
                )

        if payload:
            evt = json.dumps(payload, ensure_ascii=False)[:4000]
            prompt = f"{prompt}\n\n## Evento recebido\n```json\n{evt}\n```"

        configurable: dict[str, Any] = {
            "thread_id": run_thread_id,
            "user_id": task.user_id,
            # Default "auto": sem humano no fluxo de fundo, o HITL dinâmico roda
            # sem pausas e a task conclui inteira. Uma task pode configurar um
            # modo que interrompe (trigger_config.permission_mode) — aí a run
            # fica "awaiting_approval" e é retomável via resume_background_run.
            "permission_mode": task.trigger_config.get("permission_mode", "auto"),
            # Identifica a task pro HITL de `kanban_update_status`: uma run
            # que se marca bloqueada (`task_id == background_task_id`) não
            # espera aprovação de si mesma — ver `backend/services/middleware.py`.
            "background_task_id": task.id,
        }
        if task.workspace_id:
            configurable["workspace_id"] = task.workspace_id

        subagent_type = task.trigger_config.get("subagent_type")
        if subagent_type:
            # Agendamento de subagente específico — usa um worktree isolado
            # quando é "coder" e a task tem workspace (evita concorrência
            # com o workspace principal do usuário).
            if subagent_type == "coder" and task.workspace_id:
                configurable["workspace_id"] = await _worktree_workspace_id(
                    task.workspace_id, task.id
                )
            from backend.scheduling.subagent_runner import build_subagent_graph

            agent = await build_subagent_graph(subagent_type)
        else:
            agent = await agent_factory.get_user_agent(
                user_id=task.user_id,
                model=model_override or "",
                workspace_id=task.workspace_id,
            )

        config = {"configurable": configurable, "recursion_limit": 50}
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=prompt)]},
            config=config,
            context=ctx_from_config(config),
        )

        from backend.api.handlers.threads import (
            _increment_message_count,
            _upsert_session,
        )

        label = "Rotina" if task.kind == "routine" else "Heartbreak"
        await _upsert_session(
            run_thread_id,
            title=f"{label}: {task.name}",
            workspace_id=task.workspace_id,
        )
        # message_count>0 faz a thread da run aparecer na sidebar (ListThreads
        # filtra message_count>0). O histórico completo sai do checkpointer via
        # GetHistory (o grafo roda com run_thread_id + checkpointer compartilhado).
        await _increment_message_count(run_thread_id)

        # HITL: se o grafo pausou numa ação destrutiva, a run fica pendente de
        # aprovação (não "done") — o interrupt está salvo no checkpointer e a
        # run é retomável por resume_background_run.
        interrupt_payload = _extract_interrupt(result)
        if interrupt_payload is not None:
            desc = _describe_interrupt(interrupt_payload)
            await _mark_run_awaiting(run_id, desc)
            await _touch_last_run(task.id)
            _emit_run_event("needs_approval", task, run_id, run_thread_id, desc)
            return run_thread_id

        summary = _extract_summary(result)
        await _finish_run(run_id, "done", summary)
        await _touch_last_run(task.id)
        _emit_run_event("done", task, run_id, run_thread_id, summary)
        await report_to_parent_session(task, run_thread_id, summary)
        await _mark_kanban_after_success(task)
        return run_thread_id
    except Exception as exc:
        logger.exception(
            "background_tasks: run falhou",
            extra={"task_id": task.id, "trigger": trigger_source},
        )
        with contextlib.suppress(Exception):
            await _finish_run(run_id, "error", str(exc))
        _emit_run_event("error", task, run_id, run_thread_id, str(exc))
        with contextlib.suppress(Exception):
            from backend.scheduling.kanban import block_task

            # "transient" (não "capability"): é uma falha da própria run,
            # não do orçamento — a taxonomia distingue os dois motivos pro
            # card mostrar o certo.
            await block_task(task.id, "transient", str(exc)[:500])
        return None


async def _mark_kanban_after_success(task: BackgroundTask) -> None:
    """Fecha o ciclo do Kanban após uma run bem-sucedida.

    Recorrente (`interval`) nunca termina de verdade — volta pra `ready`
    pro próximo disparo, nunca `done` (que seria um estado terminal errado
    pra algo que roda de novo amanhã). Qualquer outro `trigger_type` (
    `manual`/`webhook`/`once`) é execução única: `done` é terminal.
    `recompute_ready()` promove tasks que dependiam desta, quando existirem.
    """
    try:
        from backend.scheduling.kanban import recompute_ready, set_status

        novo_status = "ready" if task.trigger_type == "interval" else "done"
        await set_status(task.id, novo_status)
        await recompute_ready()
    except Exception:
        logger.warning(
            "background_tasks: falha ao atualizar status do kanban pós-run",
            exc_info=True,
        )


async def _get_run(run_id: str) -> dict[str, Any] | None:
    """Uma run de background por id (ou ``None``)."""
    conn = await _get_db()
    try:
        cur = await conn.execute(
            "SELECT id, task_id, session_id, run_thread_id, status, summary "
            "FROM vectora_background_runs WHERE id = ?",
            (run_id,),
        )
        return await cur.fetchone()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()


async def resume_background_run(run_id: str, decision: str = "approve") -> str | None:
    """Retoma uma run de background pausada em HITL (``awaiting_approval``).

    O interrupt está persistido no checkpointer compartilhado sob o
    ``run_thread_id``, então resume o grafo com ``Command(resume=...)`` — mesmo
    mecanismo do ResumeChat do chat síncrono.

    Args:
        run_id: id da run em ``awaiting_approval``.
        decision: ``"approve"`` | ``"reject"`` | ``"edit:<json_dos_args>"``.

    Returns:
        Novo status (``"done"`` ou ``"awaiting_approval"`` se pausou de novo no
        mesmo turno), ou ``None`` se a run não existe/não está pendente ou falha.
    """
    run = await _get_run(run_id)
    if run is None or run.get("status") != "awaiting_approval":
        return None
    run_thread_id = run.get("run_thread_id") or ""
    task = await get_task(run["task_id"])
    if task is None or not run_thread_id:
        return None

    try:
        from langgraph.types import Command

        from backend.services import agent_factory
        from backend.vtypes.context import ctx_from_config

        if decision == "approve":
            resume_value: dict[str, Any] = {"action": "approve"}
        elif decision == "reject":
            resume_value = {"action": "reject"}
        elif decision.startswith("edit:"):
            resume_value = {"action": "edit", "args": json.loads(decision[5:])}
        else:
            raise ValueError(f"decision inválida: {decision!r}")

        mode = task.trigger_config.get("permission_mode", "auto")
        configurable: dict[str, Any] = {
            "thread_id": run_thread_id,
            "user_id": task.user_id,
            "permission_mode": mode,
            "background_task_id": task.id,
        }
        if task.workspace_id:
            configurable["workspace_id"] = task.workspace_id
        config = {"configurable": configurable, "recursion_limit": 50}

        agent = await agent_factory.get_user_agent(
            user_id=task.user_id,
            workspace_id=task.workspace_id,
        )
        result = await agent.ainvoke(
            Command(resume=resume_value),
            config=config,
            context=ctx_from_config(config),
        )

        interrupt_payload = _extract_interrupt(result)
        if interrupt_payload is not None:
            desc = _describe_interrupt(interrupt_payload)
            await _mark_run_awaiting(run_id, desc)
            _emit_run_event("needs_approval", task, run_id, run_thread_id, desc)
            return "awaiting_approval"

        summary = _extract_summary(result)
        await _finish_run(run_id, "done", summary)
        _emit_run_event("done", task, run_id, run_thread_id, summary)
        await report_to_parent_session(task, run_thread_id, summary)
        return "done"
    except Exception as exc:
        logger.exception("background_tasks: resume falhou", extra={"run_id": run_id})
        with contextlib.suppress(Exception):
            await _finish_run(run_id, "error", str(exc))
        return None


async def cancel_background_run(run_id: str) -> str | None:
    """Cancela uma run pendente de aprovação (ou rodando) — status 'cancelled'.

    A run cancelada não é retomável. Retorna ``"cancelled"`` em sucesso, ou
    ``None`` se a run não existe ou já terminou (done/error/cancelled).
    """
    run = await _get_run(run_id)
    if run is None or run.get("status") not in ("awaiting_approval", "running"):
        return None
    await _finish_run(
        run_id, "cancelled", run.get("summary") or "Cancelada pelo usuário."
    )
    return "cancelled"


async def report_to_parent_session(
    task: BackgroundTask, run_thread_id: str, summary: str
) -> bool:
    """Posta o resultado da run COMO MENSAGEM na sessão-mãe (Hermes/Paperclip).

    Anexa uma ``AIMessage`` ao checkpoint da sessão que criou a task
    (``task.session_id``) via ``graph.aupdate_state`` — o reducer de mensagens
    do LangGraph acrescenta ao histórico, então o próximo turno do orquestrador
    principal VÊ que a tarefa terminou (com resumo + link pra thread da run).

    Best-effort: falha aqui nunca deve derrubar a conclusão da run. Retorna
    ``True`` se reportou, ``False`` se pulou (sem sessão-mãe) ou falhou.
    """
    if not task.session_id or task.session_id == run_thread_id:
        return False
    try:
        from langchain_core.messages import AIMessage

        from backend.services import agent_factory

        graph = await agent_factory.get_user_agent(
            user_id=task.user_id,
            workspace_id=task.workspace_id,
        )
        text = (
            f"🔔 Tarefa em segundo plano concluída — **{task.name}**\n\n"
            f"{summary or '(sem resumo)'}\n\n"
            f"_Histórico completo na thread `{run_thread_id}`._"
        )
        await graph.aupdate_state(
            {"configurable": {"thread_id": task.session_id}},
            {"messages": [AIMessage(content=text)]},
        )
        return True
    except Exception:
        logger.exception(
            "background_tasks: falha ao reportar à sessão-mãe",
            extra={"task_id": task.id, "session_id": task.session_id},
        )
        return False


# ---------------------------------------------------------------------------
# Webhook → IA
# ---------------------------------------------------------------------------


def _event_matches(event_type: str, events: list[str]) -> bool:
    """Casa o evento recebido contra os eventos configurados na task.

    Sem filtro (`events` vazio) casa tudo. Casa por igualdade exata ou pelo
    prefixo antes do ponto (ex.: configurado 'pull_request' casa
    'pull_request.opened').
    """
    if not events:
        return True
    base = event_type.split(".", 1)[0]
    return any(e in (event_type, base) for e in events)


async def dispatch_webhook_event(
    provider: str, event_type: str, payload: dict[str, Any]
) -> int:
    """Dispara as tasks 'webhook' habilitadas cujo filtro casa. Retorna quantas.

    Ponte webhook→IA: chamada por `receive_webhook` após persistir o evento.
    """
    conn = await _get_db()
    try:
        cur = await conn.execute(
            "SELECT * FROM vectora_background_tasks "
            "WHERE enabled = 1 AND trigger_type = 'webhook'",
        )
        rows = await cur.fetchall()
    except Exception:
        logger.exception("background_tasks: falha ao listar webhook tasks")
        return 0
    finally:
        with contextlib.suppress(Exception):
            await conn.close()

    fired = 0
    for row in rows:
        task = _row_to_task(row)
        cfg = task.trigger_config
        want_provider = cfg.get("provider")
        if want_provider and want_provider != provider:
            continue
        if not _event_matches(event_type, list(cfg.get("events") or [])):
            continue
        await run_task(task, "webhook", payload=payload)
        fired += 1
    return fired


# ---------------------------------------------------------------------------
# GitHub Issues → Kanban (caminho determinístico, sem LLM)
# ---------------------------------------------------------------------------

#: Corpo da issue truncado ao virar instrução do card — evita instrução
#: gigante numa issue com descrição extensa.
_ISSUE_BODY_MAX_CHARS = 2000

#: Ações do evento `issues` que o sync entende. Qualquer outra (labeled,
#: milestoned, etc.) é ignorada — não vira efeito no board.
_ISSUE_SYNC_ACTIONS = frozenset({"opened", "closed", "reopened", "edited", "assigned"})


async def _find_github_issue_sync_anchor() -> BackgroundTask | None:
    """Task 'webhook' que liga eventos `issues` do GitHub ao Kanban.

    O usuário liga o sync criando (UI/API) uma task com trigger_type='webhook'
    e trigger_config={"provider": "github", "events": [... "issues" ...]} — os
    cards de issue nascem na mesma session/workspace dessa task-âncora. Sem
    task assim (habilitada), o sync está desligado: nenhum card é criado ou
    atualizado a partir de eventos `issues`.
    """
    conn = await _get_db()
    try:
        cur = await conn.execute(
            "SELECT * FROM vectora_background_tasks "
            "WHERE enabled = 1 AND trigger_type = 'webhook'",
        )
        rows = await cur.fetchall()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()
    for row in rows:
        task = _row_to_task(row)
        cfg = task.trigger_config
        if cfg.get("provider") != "github":
            continue
        if _event_matches("issues", list(cfg.get("events") or [])):
            return task
    return None


async def find_task_by_github_issue(
    session_id: str, repo: str, issue_number: int
) -> BackgroundTask | None:
    """Card já ligado a essa issue (mesmo `repo`+`issue_number`), se existir.

    Chave de idempotência do sync — reentrega do mesmo webhook (o GitHub
    reenvia quando não recebe 200 a tempo) atualiza o card em vez de duplicar.
    """
    for t in await list_tasks(session_id):
        cfg = t.trigger_config
        if (
            cfg.get("source") == "github_issue"
            and cfg.get("repo") == repo
            and cfg.get("issue_number") == issue_number
        ):
            return t
    return None


async def _upsert_github_issue_card(
    anchor: BackgroundTask,
    existing: BackgroundTask | None,
    title: str,
    body: str,
    cfg: dict[str, Any],
) -> BackgroundTask | None:
    """Cria o card na primeira vez que a issue chega; atualiza numa reentrega."""
    if existing is not None:
        await update_task(existing.id, name=title, instruction=body, trigger_config=cfg)
        return await get_task(existing.id)
    return await create_task(
        session_id=anchor.session_id,
        user_id=anchor.user_id,
        kind="routine",
        name=title,
        instruction=body,
        trigger_type="manual",
        trigger_config=cfg,
        workspace_id=anchor.workspace_id,
    )


async def sync_github_issue_to_kanban(
    action: str, repo: str, issue: dict[str, Any]
) -> BackgroundTask | None:
    """Espelha um evento `issues` do GitHub num card do Kanban — sem LLM no meio.

    `opened` cria (ou atualiza, se a issue já tem card — reentrega de
    webhook) um card `trigger_type='manual'`: fica no board, acionável sob
    demanda, mas nunca dispara sozinho como uma task `webhook`/`interval`
    faria — a ponte webhook→IA (`dispatch_webhook_event`) não vê essas
    tasks. `closed`/`reopened` só movem o card via `kanban.set_status`.
    `edited`/`assigned` atualizam título/instrução sem mudar status.

    Retorna `None` sem efeito quando: não há task-âncora configurada (sync
    desligado), a `action` não é reconhecida, ou o payload não traz
    `issue.number`. Defensiva por fora (`_handle_github` já roda dentro do
    try/except do dispatcher de webhook), mas nunca levanta por si só.
    """
    if action not in _ISSUE_SYNC_ACTIONS:
        return None
    issue_number = issue.get("number")
    if issue_number is None or not repo:
        return None

    anchor = await _find_github_issue_sync_anchor()
    if anchor is None:
        return None

    existing = await find_task_by_github_issue(anchor.session_id, repo, issue_number)
    title = str(issue.get("title") or f"Issue #{issue_number}")
    body = str(issue.get("body") or "")[:_ISSUE_BODY_MAX_CHARS]
    cfg = {
        "source": "github_issue",
        "repo": repo,
        "issue_number": issue_number,
        "html_url": issue.get("html_url") or "",
    }

    if action == "opened":
        return await _upsert_github_issue_card(anchor, existing, title, body, cfg)

    if existing is None:
        return None

    if action in ("closed", "reopened"):
        from backend.scheduling import kanban

        await kanban.set_status(existing.id, "done" if action == "closed" else "ready")
    else:  # edited, assigned
        await update_task(existing.id, name=title, instruction=body)
    return await get_task(existing.id)


# ---------------------------------------------------------------------------
# Alertas de observabilidade → Kanban (caminho determinístico, sem LLM)
#
# Contrato genérico pra qualquer ferramenta de alerta (Sentry, Grafana,
# PagerDuty, etc.) — sem parsing nativo de vendor nenhum. O provider aponta
# seu webhook de saída pra POST /webhook/observability com o payload já no
# formato {title, description, severity, url, external_id} (ver docs/content/
# guides/observability-webhooks.en.md).
# ---------------------------------------------------------------------------

#: Chave de agrupamento das tasks 'webhook' que ligam alertas de
#: observabilidade ao Kanban — mesmo papel do `provider == "github"` em
#: `_find_github_issue_sync_anchor`.
_OBSERVABILITY_PROVIDER = "observability"

#: Marca os cards criados por este sync no `trigger_config.source`, junto da
#: chave de idempotência (`external_id`) — mesmo papel do `"github_issue"`.
_OBSERVABILITY_SOURCE = "observability_alert"

#: `severity` → status inicial do card. `critical`/`high` precisam de
#: atenção imediata (`triage`); `medium`/`low` entram na fila normal
#: (`todo`). Severidade ausente ou desconhecida cai em `todo` — nunca
#: escala sozinha pra `triage` sem o sinal explícito do alertador.
_SEVERITY_TO_STATUS: dict[str, str] = {
    "critical": "triage",
    "high": "triage",
    "medium": "todo",
    "low": "todo",
}


async def _find_observability_sync_anchor() -> BackgroundTask | None:
    """Task 'webhook' que liga alertas de observabilidade ao Kanban.

    Mesmo princípio do `_find_github_issue_sync_anchor`: o usuário liga o
    sync criando uma task com trigger_type='webhook' e
    trigger_config={"provider": "observability"} — os cards de alerta nascem
    na mesma session/workspace dessa task-âncora. Sem task assim
    (habilitada), o sync está desligado.
    """
    conn = await _get_db()
    try:
        cur = await conn.execute(
            "SELECT * FROM vectora_background_tasks "
            "WHERE enabled = 1 AND trigger_type = 'webhook'",
        )
        rows = await cur.fetchall()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()
    for row in rows:
        task = _row_to_task(row)
        if task.trigger_config.get("provider") == _OBSERVABILITY_PROVIDER:
            return task
    return None


async def find_task_by_observability_alert(
    session_id: str, external_id: str
) -> BackgroundTask | None:
    """Card já ligado a esse `external_id`, se existir.

    Chave de idempotência do sync — reentrega do mesmo alerta (retry do
    alertador, at-least-once delivery) atualiza o card em vez de duplicar.
    """
    for t in await list_tasks(session_id):
        cfg = t.trigger_config
        if (
            cfg.get("source") == _OBSERVABILITY_SOURCE
            and cfg.get("external_id") == external_id
        ):
            return t
    return None


async def sync_observability_alert_to_kanban(
    alert: dict[str, Any],
) -> BackgroundTask | None:
    """Espelha um alerta de observabilidade genérico num card do Kanban.

    Determinístico, sem LLM no meio — mesmo caminho de
    `sync_github_issue_to_kanban`. `severity` decide o status inicial via
    `_SEVERITY_TO_STATUS`. Reentrega do mesmo `alert["external_id"]`
    atualiza nome/descrição/status do card existente em vez de duplicar.

    Retorna `None` sem efeito quando não há task-âncora configurada (sync
    desligado). Espera `alert` já validado (`title`/`external_id`
    presentes) — quem chama (`receive_observability_webhook`) valida antes.
    """
    anchor = await _find_observability_sync_anchor()
    if anchor is None:
        return None

    from backend.scheduling import kanban

    external_id = str(alert["external_id"])
    title = str(alert["title"])
    description = str(alert.get("description") or "")[:_ISSUE_BODY_MAX_CHARS]
    severity = str(alert.get("severity") or "").lower()
    status = _SEVERITY_TO_STATUS.get(severity, "todo")
    cfg = {
        "source": _OBSERVABILITY_SOURCE,
        "external_id": external_id,
        "severity": severity,
        "url": str(alert.get("url") or ""),
    }

    existing = await find_task_by_observability_alert(anchor.session_id, external_id)
    if existing is not None:
        await update_task(
            existing.id, name=title, instruction=description, trigger_config=cfg
        )
        await kanban.set_status(existing.id, status)
        return await get_task(existing.id)

    task = await create_task(
        session_id=anchor.session_id,
        user_id=anchor.user_id,
        kind="routine",
        name=title,
        instruction=description,
        trigger_type="manual",
        trigger_config=cfg,
        workspace_id=anchor.workspace_id,
    )
    await kanban.set_status(task.id, status)
    return await get_task(task.id)


# ---------------------------------------------------------------------------
# Scheduler (interval)
# ---------------------------------------------------------------------------


async def _list_due_interval_tasks() -> list[BackgroundTask]:
    now = datetime.now(UTC).isoformat()
    conn = await _get_db()
    try:
        cur = await conn.execute(
            "SELECT * FROM vectora_background_tasks "
            "WHERE enabled = 1 AND trigger_type IN ('interval', 'once') "
            "AND next_run_at IS NOT NULL AND next_run_at <= ?",
            (now,),
        )
        rows = await cur.fetchall()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()
    return [_row_to_task(r) for r in rows]


def _is_stale(next_run_at: str | None, now: datetime) -> bool:
    """True se o disparo agendado ficou pra trás além da janela de tolerância.

    Timestamp ausente/ilegível nunca é considerado atrasado — na dúvida
    executa, é melhor um disparo a mais que engolir a tarefa em silêncio.
    """
    if not next_run_at:
        return False
    try:
        scheduled = datetime.fromisoformat(next_run_at)
    except ValueError:
        return False
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=UTC)
    return scheduled < now - CATCH_UP_GRACE


async def _set_next_run(task_id: str, next_run: str | None) -> None:
    conn = await _get_db()
    try:
        await conn.execute(
            "UPDATE vectora_background_tasks SET next_run_at = ? WHERE id = ?",
            (next_run, task_id),
        )
        await conn.commit()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()


class BackgroundScheduler:
    """Loop asyncio que dispara tasks 'interval' vencidas (tick de 60s)."""

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("BackgroundScheduler iniciado")

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("BackgroundScheduler parado")

    async def _loop(self) -> None:
        try:
            while self._running:
                with contextlib.suppress(Exception):
                    await self.tick()
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass

    async def tick(self) -> None:
        """Executa as interval/once tasks vencidas.

        "interval" reagenda pelo cron; "once" (execução única) só desabilita
        a task depois de rodar — nunca refira sozinha.

        Recorrente atrasada além de ``CATCH_UP_GRACE`` (processo ficou horas
        parado) pula pro próximo horário em vez de disparar retroativamente:
        um "resumo diário das 9h" não deve rodar às 15h só porque a máquina
        estava desligada. "once" nunca é pulada — é uma tarefa que o usuário
        pediu uma vez, atrasar não a torna indesejada.
        """
        # Claims expirados voltam pra `ready` antes de qualquer disparo:
        # worker que morreu sem liberar deixaria o card preso em `running`.
        try:
            from backend.scheduling.kanban import (
                recompute_ready,
                release_stale_claims,
            )

            await release_stale_claims()
            await recompute_ready()
        except Exception:
            # Kanban é camada acessória — falha aqui não pode impedir o
            # disparo das tarefas agendadas, que é a função principal do tick.
            logger.warning("background_tasks: tick do kanban falhou", exc_info=True)

        now = datetime.now(UTC)
        for task in await _list_due_interval_tasks():
            if task.trigger_type == "interval" and _is_stale(task.next_run_at, now):
                logger.info(
                    "background_tasks: pulando disparo atrasado de %s "
                    "(agendado pra %s) — reagendando pro próximo horário",
                    task.id,
                    task.next_run_at,
                )
                await _set_next_run(
                    task.id, _next_run(task.trigger_config.get("cron_expr"))
                )
                continue
            await run_task(task, task.trigger_type)
            if task.trigger_type == "once":
                await update_task(task.id, enabled=False)
            else:
                await _set_next_run(
                    task.id, _next_run(task.trigger_config.get("cron_expr"))
                )


_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    """Singleton do BackgroundScheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler
