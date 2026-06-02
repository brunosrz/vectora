"""Handler de status de licença — consumido pelo trial banner do chat (T.12.7).

Lê o cache local que o Launcher escreveu no boot — sem fazer call remoto a cada
request. ``GET /license/status`` é público (acessível antes do login) para que
a tela de login possa mostrar "Licença expirada — renove em ..." sem confundir
o usuário com 401.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.services.license import read_cached_status

router = APIRouter(prefix="/license", tags=["license"])


@router.get("/status")
async def license_status() -> dict:
    """Devolve o status atual da licença (lido do cache local)."""
    info = read_cached_status()
    if info is None:
        return {
            "configured": False,
            "tier": None,
            "status": "unknown",
            "days_remaining": 0,
            "expires_at": "",
            "cached": False,
        }
    return {"configured": True, **info.to_dict()}
