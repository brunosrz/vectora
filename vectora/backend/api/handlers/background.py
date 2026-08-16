"""Handler REST de tarefas em segundo plano — scoped por session do chat.

Rotina (cron), Heartbreak (evento/webhook) e disparo manual vivem dentro de uma
session (`thread_id`), pois é a session que guarda config + workspace + histórico.

Endpoints (todos exigem autenticação):
    GET    /sessions/{thread_id}/background/tasks            — lista tasks da session
    POST   /sessions/{thread_id}/background/tasks            — cria task
    PATCH  /sessions/{thread_id}/background/tasks/{task_id}  — atualiza/habilita
    DELETE /sessions/{thread_id}/background/tasks/{task_id}  — remove
    POST   /sessions/{thread_id}/background/tasks/{task_id}/run — dispara manual
    GET    /sessions/{thread_id}/background/runs             — histórico de execuções
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

if TYPE_CHECKING:
    from backend.scheduling.background_tasks import BackgroundTask

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions/{thread_id}/background", tags=["background"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TaskDependencyOut(BaseModel):
    id: str
    name: str
    status: str


class TaskOut(BaseModel):
    id: str
    session_id: str
    workspace_id: str | None
    kind: str
    name: str
    instruction: str
    trigger_type: str
    trigger_config: dict[str, Any]
    enabled: bool
    last_run_at: str | None
    next_run_at: str | None
    status: str
    block_kind: str | None = None
    block_reason: str | None = None
    #: `workspace_id` já é o "tenant" do card; `agent_profile_id` é o
    #: "assignee".
    agent_profile_id: str | None = None
    priority: str = "normal"
    #: Pais diretos em `vectora_task_links`, com status atual — fonte real
    #: do contador N/M do editor de dependência no card (antes o frontend
    #: declarava `blocked_by` mas nada preenchia).
    dependencies: list[TaskDependencyOut] = []


class CreateTaskRequest(BaseModel):
    kind: str
    name: str
    instruction: str
    trigger_type: str
    trigger_config: dict[str, Any] = {}
    workspace_id: str | None = None
    priority: str = "normal"


class UpdateTaskRequest(BaseModel):
    name: str | None = None
    instruction: str | None = None
    enabled: bool | None = None
    trigger_config: dict[str, Any] | None = None
    #: Transição manual de status (drag-and-drop no board) — validada contra
    #: `kanban.MANUAL_TRANSITIONS`, nunca um `UPDATE` direto.
    status: str | None = None
    priority: str | None = None


class BulkTaskActionRequest(BaseModel):
    task_ids: list[str]
    action: str


class BulkTaskResult(BaseModel):
    task_id: str
    ok: bool
    error: str | None = None


class RunOut(BaseModel):
    id: str
    task_id: str
    run_thread_id: str | None
    trigger_source: str
    status: str
    summary: str | None
    started_at: str
    finished_at: str | None


class CommentOut(BaseModel):
    id: str
    task_id: str
    user_id: str
    body: str
    created_at: str


class CreateCommentRequest(BaseModel):
    body: str


class TaskEventOut(BaseModel):
    id: str
    task_id: str
    from_status: str | None
    to_status: str
    block_kind: str | None
    block_reason: str | None
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_id(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return str(user.id)


async def _to_out(t: BackgroundTask) -> TaskOut:
    from backend.scheduling.kanban import get_dependencies

    deps = await get_dependencies(t.id)
    return TaskOut(
        id=t.id,
        session_id=t.session_id,
        workspace_id=t.workspace_id,
        kind=t.kind,
        name=t.name,
        instruction=t.instruction,
        trigger_type=t.trigger_type,
        trigger_config=t.trigger_config,
        enabled=t.enabled,
        last_run_at=t.last_run_at,
        next_run_at=t.next_run_at,
        status=t.status,
        block_kind=t.block_kind,
        block_reason=t.block_reason,
        agent_profile_id=t.agent_profile_id,
        priority=t.priority,
        dependencies=[TaskDependencyOut(**d) for d in deps],
    )


async def _require_task(thread_id: str, task_id: str) -> BackgroundTask:
    """Carrega a task garantindo que pertence à session da URL."""
    from backend.scheduling.background_tasks import get_task

    task = await get_task(task_id)
    if task is None or task.session_id != thread_id:
        raise HTTPException(status_code=404, detail="Task não encontrada")
    return task


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/tasks", response_model=list[TaskOut])
async def get_tasks(request: Request, thread_id: str) -> list[TaskOut]:
    from backend.scheduling.background_tasks import list_tasks

    _user_id(request)
    return [await _to_out(t) for t in await list_tasks(thread_id)]


@router.post("/tasks", response_model=TaskOut, status_code=201)
async def post_task(
    request: Request, thread_id: str, body: CreateTaskRequest
) -> TaskOut:
    from backend.scheduling.background_tasks import create_task

    uid = _user_id(request)
    if body.workspace_id:
        from backend.api.handlers.workspaces import require_workspace_access

        require_workspace_access(body.workspace_id, request)
    try:
        task = await create_task(
            session_id=thread_id,
            user_id=uid,
            kind=body.kind,
            name=body.name,
            instruction=body.instruction,
            trigger_type=body.trigger_type,
            trigger_config=body.trigger_config,
            workspace_id=body.workspace_id,
            priority=body.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("background: falha ao criar task")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return await _to_out(task)


#: Ações suportadas por `PATCH /tasks/bulk`. Só "archive" nesta leva — outras
#: ações em lote (ex.: cancelar) entram quando o produto pedir.
_BULK_ACTIONS = {"archive"}


@router.patch("/tasks/bulk", response_model=list[BulkTaskResult])
async def bulk_tasks_endpoint(
    request: Request, thread_id: str, body: BulkTaskActionRequest
) -> list[BulkTaskResult]:
    """Ação em lote da barra de seleção múltipla do Kanban.

    Cada `task_id` roda isolado (try/except por item): uma falha (id
    inexistente, task de outra session) não aborta os demais — a resposta
    reporta sucesso/erro por-item em vez de tudo-ou-nada.
    """
    from backend.scheduling import kanban

    _user_id(request)
    if body.action not in _BULK_ACTIONS:
        raise HTTPException(
            status_code=400, detail=f"ação {body.action!r} não suportada"
        )

    results: list[BulkTaskResult] = []
    for task_id in body.task_ids:
        try:
            await _require_task(thread_id, task_id)
            await kanban.set_status(task_id, "archived")
            results.append(BulkTaskResult(task_id=task_id, ok=True))
        except HTTPException as exc:
            results.append(
                BulkTaskResult(task_id=task_id, ok=False, error=str(exc.detail))
            )
        except Exception as exc:
            logger.exception(
                "background: falha ao aplicar ação em lote",
                extra={"task_id": task_id, "action": body.action},
            )
            results.append(BulkTaskResult(task_id=task_id, ok=False, error=str(exc)))
    return results


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def patch_task(
    request: Request, thread_id: str, task_id: str, body: UpdateTaskRequest
) -> TaskOut:
    from backend.scheduling import kanban
    from backend.scheduling.background_tasks import update_task

    _user_id(request)
    await _require_task(thread_id, task_id)
    if body.status is not None:
        try:
            await kanban.manual_transition(task_id, body.status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        updated = await update_task(
            task_id,
            name=body.name,
            instruction=body.instruction,
            enabled=body.enabled,
            trigger_config=body.trigger_config,
            priority=body.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Task não encontrada")
    return await _to_out(updated)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task_endpoint(request: Request, thread_id: str, task_id: str) -> None:
    from backend.scheduling.background_tasks import delete_task

    _user_id(request)
    await _require_task(thread_id, task_id)
    await delete_task(task_id)


@router.post("/tasks/{task_id}/unblock", response_model=TaskOut)
async def unblock_task_endpoint(
    request: Request, thread_id: str, task_id: str
) -> TaskOut:
    """Botão "Desbloquear" do Kanban — limpa `block_kind`/`block_reason` e
    devolve a tarefa pra `ready`, competindo pelo claim de novo."""
    from backend.scheduling.background_tasks import get_task
    from backend.scheduling.kanban import unblock_task

    _user_id(request)
    await _require_task(thread_id, task_id)
    await unblock_task(task_id)
    updated = await get_task(task_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Task não encontrada")
    return await _to_out(updated)


@router.post("/tasks/{task_id}/run", status_code=202)
async def run_task_endpoint(
    request: Request,
    thread_id: str,
    task_id: str,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    from backend.scheduling.background_tasks import run_task

    _user_id(request)
    task = await _require_task(thread_id, task_id)
    background_tasks.add_task(run_task, task, "manual")
    return {"status": "queued", "task_id": task_id}


class ResumeRunRequest(BaseModel):
    decision: str = "approve"  # "approve" | "reject" | "edit:<json_dos_args>"


@router.post("/runs/{run_id}/resume", status_code=202)
async def resume_run_endpoint(
    request: Request,
    thread_id: str,
    run_id: str,
    body: ResumeRunRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Retoma (approve/reject/edit) OU cancela (``decision="cancel"``) uma run
    pausada em HITL (``awaiting_approval``).

    O resume roda em background (invoca o agente); o novo status chega via o
    evento SSE ``background_run.done``/``needs_approval`` e no ``GET /runs``. O
    cancelamento é síncrono (só marca 'cancelled').
    """
    from backend.scheduling.background_tasks import (
        _get_run,
        cancel_background_run,
        resume_background_run,
    )

    _user_id(request)
    run = await _get_run(run_id)
    if run is None or run.get("session_id") != thread_id:
        raise HTTPException(status_code=404, detail="Run não encontrada")
    if run.get("status") != "awaiting_approval":
        raise HTTPException(status_code=409, detail="Run não está aguardando aprovação")
    if body.decision == "cancel":
        await cancel_background_run(run_id)
        return {"status": "cancelled", "run_id": run_id}
    background_tasks.add_task(resume_background_run, run_id, body.decision)
    return {"status": "queued", "run_id": run_id}


def _row_to_run_out(r: dict[str, Any]) -> RunOut:
    return RunOut(
        id=r["id"],
        task_id=r["task_id"],
        run_thread_id=r.get("run_thread_id"),
        trigger_source=r["trigger_source"],
        status=r["status"],
        summary=r.get("summary"),
        started_at=r["started_at"],
        finished_at=r.get("finished_at"),
    )


@router.get("/runs", response_model=list[RunOut])
async def get_runs(request: Request, thread_id: str) -> list[RunOut]:
    from backend.scheduling.background_tasks import list_runs

    _user_id(request)
    rows = await list_runs(thread_id)
    return [_row_to_run_out(r) for r in rows]


@router.get("/tasks/{task_id}/runs", response_model=list[RunOut])
async def get_task_runs(request: Request, thread_id: str, task_id: str) -> list[RunOut]:
    """Histórico de execuções de UMA task — fecha a conexão que faltava
    entre `GET /runs` (existia, só por session) e o card do Kanban."""
    from backend.scheduling.background_tasks import list_runs_for_task

    _user_id(request)
    await _require_task(thread_id, task_id)
    rows = await list_runs_for_task(task_id)
    return [_row_to_run_out(r) for r in rows]


def _row_to_comment_out(r: dict[str, Any]) -> CommentOut:
    return CommentOut(
        id=r["id"],
        task_id=r["task_id"],
        user_id=r["user_id"],
        body=r["body"],
        created_at=r["created_at"],
    )


def _row_to_event_out(r: dict[str, Any]) -> TaskEventOut:
    return TaskEventOut(
        id=r["id"],
        task_id=r["task_id"],
        from_status=r.get("from_status"),
        to_status=r["to_status"],
        block_kind=r.get("block_kind"),
        block_reason=r.get("block_reason"),
        created_at=r["created_at"],
    )


@router.post("/tasks/{task_id}/comments", response_model=CommentOut, status_code=201)
async def post_comment_endpoint(
    request: Request, thread_id: str, task_id: str, body: CreateCommentRequest
) -> CommentOut:
    from backend.scheduling.kanban import add_comment

    uid = _user_id(request)
    await _require_task(thread_id, task_id)
    try:
        comment = await add_comment(task_id, uid, body.body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("background: falha ao criar comentário")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _row_to_comment_out(comment)


@router.get("/tasks/{task_id}/comments", response_model=list[CommentOut])
async def get_comments_endpoint(
    request: Request, thread_id: str, task_id: str
) -> list[CommentOut]:
    from backend.scheduling.kanban import list_comments

    _user_id(request)
    await _require_task(thread_id, task_id)
    rows = await list_comments(task_id)
    return [_row_to_comment_out(r) for r in rows]


@router.get("/tasks/{task_id}/events", response_model=list[TaskEventOut])
async def get_events_endpoint(
    request: Request, thread_id: str, task_id: str
) -> list[TaskEventOut]:
    """Timeline de transições de status do card — `vectora_task_events`,
    gravada por `kanban._record_task_event` em cada transição."""
    from backend.scheduling.kanban import list_events

    _user_id(request)
    await _require_task(thread_id, task_id)
    rows = await list_events(task_id)
    return [_row_to_event_out(r) for r in rows]
