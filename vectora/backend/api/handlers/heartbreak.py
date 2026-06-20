"""Handler REST do Modo Heartbreak — sessões de escuta contínua.

Endpoints:
    POST   /heartbreak/sessions           — cria sessão
    DELETE /heartbreak/sessions/{id}      — encerra sessão
    GET    /heartbreak/sessions           — lista sessões ativas do usuário
    POST   /heartbreak/trigger/{id}       — envia evento à sessão (webhook)
    GET    /heartbreak/sessions/{id}/log  — contagem de execuções (simples)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

if TYPE_CHECKING:
    from backend.services.heartbreak import HeartbreakSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/heartbreak", tags=["heartbreak"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SessionOut(BaseModel):
    id: str
    user_id: int
    instruction: str
    workspace_id: str | None
    status: str
    run_count: int
    trigger_count: int
    created_at: str


class CreateSessionRequest(BaseModel):
    instruction: str
    workspace_id: str | None = None
    trigger_type: str = "webhook"
    trigger_config: dict[str, Any] = {}


class TriggerRequest(BaseModel):
    payload: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_id(request: Request) -> int:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return int(user.id)


def _to_out(s: HeartbreakSession) -> SessionOut:
    return SessionOut(
        id=s.id,
        user_id=s.user_id,
        instruction=s.instruction,
        workspace_id=s.workspace_id,
        status=s.status,
        run_count=s.run_count,
        trigger_count=len(s.triggers),
        created_at=s.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/sessions", response_model=SessionOut, status_code=201)
async def create_session(request: Request, body: CreateSessionRequest) -> SessionOut:
    from backend.services.heartbreak import get_manager

    uid = _user_id(request)
    mgr = get_manager()
    session = mgr.create(
        user_id=uid,
        instruction=body.instruction,
        workspace_id=body.workspace_id,
    )
    try:
        session.register_trigger(body.trigger_type, body.trigger_config)
    except ValueError as exc:
        mgr.stop(session.id)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(session)


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(request: Request) -> list[SessionOut]:
    from backend.services.heartbreak import get_manager

    uid = _user_id(request)
    return [_to_out(s) for s in get_manager().list_active(user_id=uid)]


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(request: Request, session_id: str) -> None:
    from backend.services.heartbreak import get_manager

    uid = _user_id(request)
    mgr = get_manager()
    session = mgr.get(session_id)
    if session is None or session.user_id != uid:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    mgr.stop(session_id)


@router.post("/trigger/{session_id}", status_code=202)
async def trigger_session(
    request: Request,
    session_id: str,
    body: TriggerRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    from backend.services.heartbreak import get_manager

    mgr = get_manager()
    session = mgr.get(session_id)
    if session is None or session.status != "active":
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    background_tasks.add_task(session.send_event, body.payload)
    return {"status": "queued", "session_id": session_id}


@router.get("/sessions/{session_id}/log")
async def session_log(request: Request, session_id: str) -> dict[str, Any]:
    from backend.services.heartbreak import get_manager

    uid = _user_id(request)
    session = get_manager().get(session_id)
    if session is None or session.user_id != uid:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    return {
        "session_id": session_id,
        "run_count": session.run_count,
        "status": session.status,
    }
