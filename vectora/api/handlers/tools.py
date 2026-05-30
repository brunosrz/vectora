"""Handler de política de tools do usuário autenticado (Bloco S, S5).

Endpoints (exigem auth via middleware):
    GET /tools/policy   — tools desabilitadas do usuário + lista de built-ins
    PUT /tools/policy   — define as tools desabilitadas do usuário

O controle administrativo (override por outro usuário) vive em
``handlers/admin.py`` (``/admin/users/{id}/tools``).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from vectora.services import tool_policy

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolPolicyBody(BaseModel):
    disabled: list[str] = []


def _user_id(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user is not None and getattr(user, "id", None):
        return str(user.id)
    return "local"


def _all_tool_names() -> list[str]:
    from vectora.nodes.tools import ALL_TOOLS

    return [t.name for t in ALL_TOOLS]


@router.get("/policy")
async def get_policy(request: Request) -> dict:
    """Política de tools do usuário atual."""
    uid = _user_id(request)
    return {
        "disabled": tool_policy.get_disabled(uid),
        "available": _all_tool_names(),
    }


@router.put("/policy")
async def put_policy(request: Request, body: ToolPolicyBody) -> dict:
    """Define as tools desabilitadas do usuário atual."""
    valid = set(_all_tool_names())
    unknown = [n for n in body.disabled if n not in valid]
    if unknown:
        raise HTTPException(
            status_code=400, detail=f"Tools desconhecidas: {sorted(unknown)}"
        )
    tool_policy.set_disabled(_user_id(request), body.disabled)
    return {"status": "ok", "disabled": tool_policy.get_disabled(_user_id(request))}
