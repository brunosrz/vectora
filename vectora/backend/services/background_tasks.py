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
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from croniter import croniter

logger = logging.getLogger(__name__)

VALID_KINDS = {"routine", "heartbreak"}
VALID_TRIGGERS = {"interval", "webhook", "manual"}


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


def _validate(kind: str, trigger_type: str, trigger_config: dict[str, Any]) -> None:
    if kind not in VALID_KINDS:
        msg = f"kind inválido: {kind!r}. Válidos: {sorted(VALID_KINDS)}"
        raise ValueError(msg)
    if trigger_type not in VALID_TRIGGERS:
        msg = f"trigger inválido: {trigger_type!r}. Válidos: {sorted(VALID_TRIGGERS)}"
        raise ValueError(msg)
    if trigger_type == "interval":
        cron = (trigger_config or {}).get("cron_expr")
        if not cron:
            raise ValueError("trigger 'interval' requer trigger_config.cron_expr")
        # croniter levanta se o cron for inválido.
        croniter(cron, datetime.now(UTC))


def _next_run(cron_expr: str | None) -> str | None:
    if not cron_expr:
        return None
    try:
        return croniter(cron_expr, datetime.now(UTC)).get_next(datetime).isoformat()
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
) -> BackgroundTask:
    """Cria uma tarefa. Levanta ValueError em kind/trigger/cron inválidos."""
    cfg = trigger_config or {}
    _validate(kind, trigger_type, cfg)
    task_id = str(uuid4())
    next_run = _next_run(cfg.get("cron_expr")) if trigger_type == "interval" else None

    conn = await _get_db()
    try:
        await conn.execute(
            """
            INSERT INTO vectora_background_tasks
              (id, session_id, workspace_id, user_id, kind, name, instruction,
               trigger_type, trigger_config, enabled, next_run_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
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
    return await get_task(task_id)


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


async def run_task(
    task: BackgroundTask,
    trigger_source: str,
    payload: dict[str, Any] | None = None,
) -> str | None:
    """Executa o agente para a tarefa. Cria uma thread visível e grava a run.

    Defensiva: nunca propaga exceção — falha vira run com status 'error'. Retorna
    o `run_thread_id` em sucesso, ou None em erro.
    """
    run_id = str(uuid4())
    run_thread_id = f"bg-{task.id}-{int(datetime.now(UTC).timestamp())}"
    await _insert_run(run_id, task, run_thread_id, trigger_source)
    _emit_run_event("started", task, run_id, run_thread_id)

    try:
        from langchain_core.messages import HumanMessage

        from backend.services import agent_factory
        from backend.vtypes.context import ctx_from_config

        prompt = task.instruction
        if payload:
            evt = json.dumps(payload, ensure_ascii=False)[:4000]
            prompt = f"{prompt}\n\n## Evento recebido\n```json\n{evt}\n```"

        configurable: dict[str, Any] = {
            "thread_id": run_thread_id,
            "user_id": task.user_id,
            # Sem humano para responder HITL: auto-aprova edições, mas ainda
            # interrompe em ações destrutivas (a thread fica na sidebar para o
            # usuário retomar).
            "permission_mode": "auto",
        }
        if task.workspace_id:
            configurable["workspace_id"] = task.workspace_id
        config = {"configurable": configurable, "recursion_limit": 50}

        agent = await agent_factory.get_user_agent(user_id=task.user_id)
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=prompt)]},
            config=config,
            context=ctx_from_config(config),
        )
        summary = _extract_summary(result)

        from backend.api.handlers.threads import _upsert_session

        label = "Rotina" if task.kind == "routine" else "Heartbreak"
        await _upsert_session(
            run_thread_id,
            title=f"{label}: {task.name}",
            workspace_id=task.workspace_id,
        )

        await _finish_run(run_id, "done", summary)
        await _touch_last_run(task.id)
        _emit_run_event("done", task, run_id, run_thread_id, summary)
        return run_thread_id
    except Exception as exc:
        logger.exception(
            "background_tasks: run falhou",
            extra={"task_id": task.id, "trigger": trigger_source},
        )
        with contextlib.suppress(Exception):
            await _finish_run(run_id, "error", str(exc))
        _emit_run_event("error", task, run_id, run_thread_id, str(exc))
        return None


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
    return any(e == event_type or e == base for e in events)


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
# Scheduler (interval)
# ---------------------------------------------------------------------------


async def _list_due_interval_tasks() -> list[BackgroundTask]:
    now = datetime.now(UTC).isoformat()
    conn = await _get_db()
    try:
        cur = await conn.execute(
            "SELECT * FROM vectora_background_tasks "
            "WHERE enabled = 1 AND trigger_type = 'interval' "
            "AND next_run_at IS NOT NULL AND next_run_at <= ?",
            (now,),
        )
        rows = await cur.fetchall()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()
    return [_row_to_task(r) for r in rows]


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
        """Executa as interval tasks vencidas e reagenda cada uma."""
        for task in await _list_due_interval_tasks():
            await run_task(task, "interval")
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
