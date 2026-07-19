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


class CreateTaskRequest(BaseModel):
    kind: str
    name: str
    instruction: str
    trigger_type: str
    trigger_config: dict[str, Any] = {}
    workspace_id: str | None = None


class UpdateTaskRequest(BaseModel):
    name: str | None = None
    instruction: str | None = None
    enabled: bool | None = None
    trigger_config: dict[str, Any] | None = None


class RunOut(BaseModel):
    id: str
    task_id: str
    run_thread_id: str | None
    trigger_source: str
    status: str
    summary: str | None
    started_at: str
    finished_at: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_id(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return str(user.id)


def _to_out(t: BackgroundTask) -> TaskOut:
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
    return [_to_out(t) for t in await list_tasks(thread_id)]


@router.post("/tasks", response_model=TaskOut, status_code=201)
async def post_task(
    request: Request, thread_id: str, body: CreateTaskRequest
) -> TaskOut:
    from backend.scheduling.background_tasks import create_task

    uid = _user_id(request)
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
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("background: falha ao criar task")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _to_out(task)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def patch_task(
    request: Request, thread_id: str, task_id: str, body: UpdateTaskRequest
) -> TaskOut:
    from backend.scheduling.background_tasks import update_task

    _user_id(request)
    await _require_task(thread_id, task_id)
    try:
        updated = await update_task(
            task_id,
            name=body.name,
            instruction=body.instruction,
            enabled=body.enabled,
            trigger_config=body.trigger_config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Task não encontrada")
    return _to_out(updated)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task_endpoint(request: Request, thread_id: str, task_id: str) -> None:
    from backend.scheduling.background_tasks import delete_task

    _user_id(request)
    await _require_task(thread_id, task_id)
    await delete_task(task_id)


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
    """Retoma uma run pausada em HITL (``awaiting_approval``).

    O resume roda em background (invoca o agente); o novo status chega via o
    evento SSE ``background_run.done``/``needs_approval`` e no ``GET /runs``.
    """
    from backend.scheduling.background_tasks import _get_run, resume_background_run

    _user_id(request)
    run = await _get_run(run_id)
    if run is None or run.get("session_id") != thread_id:
        raise HTTPException(status_code=404, detail="Run não encontrada")
    if run.get("status") != "awaiting_approval":
        raise HTTPException(status_code=409, detail="Run não está aguardando aprovação")
    background_tasks.add_task(resume_background_run, run_id, body.decision)
    return {"status": "queued", "run_id": run_id}


@router.get("/runs", response_model=list[RunOut])
async def get_runs(request: Request, thread_id: str) -> list[RunOut]:
    from backend.scheduling.background_tasks import list_runs

    _user_id(request)
    rows = await list_runs(thread_id)
    return [
        RunOut(
            id=r["id"],
            task_id=r["task_id"],
            run_thread_id=r.get("run_thread_id"),
            trigger_source=r["trigger_source"],
            status=r["status"],
            summary=r.get("summary"),
            started_at=r["started_at"],
            finished_at=r.get("finished_at"),
        )
        for r in rows
    ]
