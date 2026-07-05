"""Handler de skills — gestão de capacidades reutilizáveis por usuário (S8).

Endpoints (todos exigem autenticação via middleware):
    GET    /skills                 — lista skills instaladas
    POST   /skills                 — instala skill (body: {source})
    DELETE /skills/{skill_id}      — remove skill
    POST   /skills/{skill_id}/verify — revalida SKILL.md (após edição manual)

O user_id vem de ``request.state.user`` (CLI/root → ``"local"``). Skills são
isoladas por usuário (cada um tem sua pasta ``~/.vectora/skills/<id>/``).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from backend.workspace.skills import (
    InstallSkillRequest,
    install_skill,
    list_skills,
    remove_skill,
    verify_skill,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skills", tags=["skills"])


def _user_id(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user is not None and getattr(user, "id", None):
        return str(user.id)
    return "local"


@router.get("")
async def list_user_skills(request: Request) -> dict:
    """Lista as skills instaladas para o usuário autenticado."""
    skills = list_skills(_user_id(request))
    return {"skills": [s.model_dump() for s in skills], "total": len(skills)}


@router.post("")
async def install_user_skill(request: Request, body: InstallSkillRequest) -> dict:
    """Instala uma skill (git URL ou path local)."""
    try:
        skill = install_skill(_user_id(request), body.source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "skill": skill.model_dump()}


@router.delete("/{skill_id}")
async def delete_user_skill(request: Request, skill_id: str) -> dict:
    """Remove uma skill instalada."""
    removed = remove_skill(_user_id(request), skill_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Skill não encontrada.")
    return {"status": "removed", "id": skill_id}


@router.post("/{skill_id}/verify")
async def verify_user_skill(request: Request, skill_id: str) -> dict:
    """Revalida o SKILL.md da skill (útil após edição manual no disco)."""
    return verify_skill(_user_id(request), skill_id)
