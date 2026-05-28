"""Handler REST de memórias do usuário — Bloco N.

Endpoints:
    GET    /memory                — lista memórias do usuário autenticado (paginado)
    GET    /memory/{key}          — lê uma memória específica
    PUT    /memory/{key}          — edita conteúdo de uma memória
    DELETE /memory/{key}          — deleta uma memória específica
    DELETE /memory                — limpa todas as memórias do usuário

Todos os endpoints exigem autenticação (injetada via middleware).
O user_id é extraído de ``request.state.user.id``.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MemoryItem(BaseModel):
    key: str
    content: str
    metadata: dict[str, Any] = {}
    updated_at: str = ""


class ListMemoriesResponse(BaseModel):
    memories: list[MemoryItem]
    total: int


class CreateMemoryRequest(BaseModel):
    key: str
    content: str
    metadata: dict[str, Any] = {}


class CreateMemoryResponse(BaseModel):
    status: str
    key: str


class UpdateMemoryRequest(BaseModel):
    content: str
    metadata: dict[str, Any] = {}


class UpdateMemoryResponse(BaseModel):
    status: str
    key: str


class DeleteMemoryResponse(BaseModel):
    status: str
    key: str | None = None
    deleted: int | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_id(request: Request) -> str:
    """Extrai user_id do request autenticado.

    O AuthMiddleware injeta ``request.state.user`` quando o token é válido.
    Em modo CLI (root local sem auth), usa ``"local"`` como namespace.
    """
    user = getattr(request.state, "user", None)
    if user is not None and hasattr(user, "id"):
        return f"user:{user.id}"
    return "user:local"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=CreateMemoryResponse, status_code=201)
async def create_memory(
    request: Request,
    body: CreateMemoryRequest,
) -> CreateMemoryResponse:
    """Cria uma nova memória manualmente (pelo painel de configurações)."""
    try:
        from vectora.services.memory import get_memory_store

        namespace = _get_user_id(request)
        store = await get_memory_store()

        existing = await store.get(namespace, body.key)
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Memória '{body.key}' já existe. Use PUT para editar.",
            )

        await store.save(
            user_id=namespace,
            key=body.key,
            content=body.content,
            metadata=body.metadata,
        )
        return CreateMemoryResponse(status="created", key=body.key)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("create_memory failed: key=%s", body.key)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("", response_model=ListMemoriesResponse)
async def list_memories(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListMemoriesResponse:
    """Lista memórias do usuário autenticado, ordenadas por data de atualização."""
    try:
        from vectora.services.memory import get_memory_store

        namespace = _get_user_id(request)
        store = await get_memory_store()
        all_mems = await store.get_all(namespace)

        # Ordena por updated_at descendente (mais recentes primeiro)
        all_mems.sort(key=lambda m: m.get("updated_at", ""), reverse=True)

        page = all_mems[offset : offset + limit]
        return ListMemoriesResponse(
            memories=[
                MemoryItem(
                    key=m["key"],
                    content=m["content"],
                    metadata=m.get("metadata") or {},
                    updated_at=m.get("updated_at", ""),
                )
                for m in page
            ],
            total=len(all_mems),
        )
    except Exception as exc:
        logger.exception("list_memories failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{key}", response_model=MemoryItem)
async def get_memory_by_key(request: Request, key: str) -> MemoryItem:
    """Retorna uma memória específica pelo key."""
    try:
        from vectora.services.memory import get_memory_store

        namespace = _get_user_id(request)
        store = await get_memory_store()
        mem = await store.get(namespace, key)
        if mem is None:
            raise HTTPException(
                status_code=404, detail=f"Memória '{key}' não encontrada"
            )
        return MemoryItem(
            key=mem["key"],
            content=mem["content"],
            metadata=mem.get("metadata") or {},
            updated_at=mem.get("updated_at", ""),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_memory_by_key failed: key=%s", key)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/{key}", response_model=UpdateMemoryResponse)
async def update_memory(
    request: Request,
    key: str,
    body: UpdateMemoryRequest,
) -> UpdateMemoryResponse:
    """Edita o conteúdo de uma memória existente."""
    try:
        from vectora.services.memory import get_memory_store

        namespace = _get_user_id(request)
        store = await get_memory_store()

        # Verifica se existe antes de salvar
        existing = await store.get(namespace, key)
        if existing is None:
            raise HTTPException(
                status_code=404, detail=f"Memória '{key}' não encontrada"
            )

        await store.save(
            user_id=namespace,
            key=key,
            content=body.content,
            metadata=body.metadata or existing.get("metadata") or {},
        )
        return UpdateMemoryResponse(status="updated", key=key)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("update_memory failed: key=%s", key)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{key}", response_model=DeleteMemoryResponse)
async def delete_memory_by_key(request: Request, key: str) -> DeleteMemoryResponse:
    """Deleta uma memória específica pelo key."""
    try:
        from vectora.services.memory import get_memory_store

        namespace = _get_user_id(request)
        store = await get_memory_store()
        deleted = await store.delete(namespace, key)
        if not deleted:
            raise HTTPException(
                status_code=404, detail=f"Memória '{key}' não encontrada"
            )
        return DeleteMemoryResponse(status="deleted", key=key)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("delete_memory_by_key failed: key=%s", key)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("", response_model=DeleteMemoryResponse)
async def clear_all_memories(request: Request) -> DeleteMemoryResponse:
    """Limpa todas as memórias do usuário autenticado."""
    try:
        from vectora.services.memory import get_memory_store

        namespace = _get_user_id(request)
        store = await get_memory_store()
        all_mems = await store.get_all(namespace)
        count = 0
        for mem in all_mems:
            if await store.delete(namespace, mem["key"]):
                count += 1
        logger.info("clear_all_memories: %d removidas (namespace=%s)", count, namespace)
        return DeleteMemoryResponse(status="cleared", deleted=count)
    except Exception as exc:
        logger.exception("clear_all_memories failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
