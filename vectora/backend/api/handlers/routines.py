"""Handler REST de rotinas agendadas (Modo Rotina).

Endpoints:
    GET    /routines           — lista rotinas do usuário autenticado
    POST   /routines           — cria uma nova rotina
    PATCH  /routines/{id}      — atualiza (habilita/desabilita/renomeia)
    DELETE /routines/{id}      — remove rotina
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

if TYPE_CHECKING:
    from backend.services.routines import Routine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/routines", tags=["routines"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class RoutineOut(BaseModel):
    id: str
    user_id: int
    name: str
    instruction: str
    cron_expr: str
    workspace_id: str | None
    enabled: bool
    last_run_at: str | None
    next_run_at: str | None
    created_at: str
    updated_at: str


class CreateRoutineRequest(BaseModel):
    name: str
    instruction: str
    cron_expr: str
    workspace_id: str | None = None


class UpdateRoutineRequest(BaseModel):
    name: str | None = None
    instruction: str | None = None
    cron_expr: str | None = None
    enabled: bool | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_id(request: Request) -> int:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return int(user.id)


def _to_out(r: Routine) -> RoutineOut:
    return RoutineOut(
        id=r.id,
        user_id=r.user_id,
        name=r.name,
        instruction=r.instruction,
        cron_expr=r.cron_expr,
        workspace_id=r.workspace_id,
        enabled=r.enabled,
        last_run_at=r.last_run_at.isoformat() if r.last_run_at else None,
        next_run_at=r.next_run_at.isoformat() if r.next_run_at else None,
        created_at=r.created_at.isoformat(),
        updated_at=r.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[RoutineOut])
async def get_routines(request: Request) -> list[RoutineOut]:
    from backend.services.routines import list_routines

    uid = _user_id(request)
    routines = await list_routines(user_id=uid)
    return [_to_out(r) for r in routines]


@router.post("", response_model=RoutineOut, status_code=201)
async def post_routine(request: Request, body: CreateRoutineRequest) -> RoutineOut:
    from backend.services.routines import create_routine

    uid = _user_id(request)
    try:
        routine = await create_routine(
            user_id=uid,
            name=body.name,
            instruction=body.instruction,
            cron_expr=body.cron_expr,
            workspace_id=body.workspace_id,
        )
    except Exception as exc:
        logger.exception("routines: falha ao criar")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(routine)


@router.patch("/{routine_id}", response_model=RoutineOut)
async def patch_routine(
    request: Request, routine_id: str, body: UpdateRoutineRequest
) -> RoutineOut:
    from backend.services.routines import update_routine

    uid = _user_id(request)
    routine = await update_routine(
        routine_id=routine_id,
        user_id=uid,
        enabled=body.enabled,
        name=body.name,
        instruction=body.instruction,
        cron_expr=body.cron_expr,
    )
    if routine is None:
        raise HTTPException(status_code=404, detail="Rotina não encontrada")
    return _to_out(routine)


@router.delete("/{routine_id}", status_code=204)
async def delete_routine_endpoint(request: Request, routine_id: str) -> None:
    from backend.services.routines import delete_routine

    uid = _user_id(request)
    deleted = await delete_routine(routine_id=routine_id, user_id=uid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rotina não encontrada")
