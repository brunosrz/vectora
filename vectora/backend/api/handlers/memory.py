"""Handler REST de memórias do usuário.

Endpoints:
    GET    /memory                — lista memórias do usuário autenticado (paginado)
    GET    /memory/{key}          — lê uma memória específica
    PUT    /memory/{key}          — edita conteúdo de uma memória
    DELETE /memory/{key}          — deleta uma memória específica
    DELETE /memory                — limpa todas as memórias do usuário

Todos os endpoints exigem autenticação (injetada via middleware).
O user_id é extraído de ``request.state.user.id``.

Lê e escreve o mesmo LangGraph BaseStore usado pelas memory tools do agente
(``backend/tools/memory.py``), no namespace ``("user", <user_id>, "memories")``
— painel de configurações e agente compartilham as mesmas memórias.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])

# asearch/aput/aget vêm de langgraph.store.base.BaseStore — sem tipo público
# estável para o retorno de asearch importar aqui sem acoplar à implementação
# concreta (InMemoryStore/AsyncSqliteStore).
_LIST_ALL_LIMIT = 1000


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


def _user_id(request: Request) -> str:
    """Extrai o user_id bruto do request autenticado.

    Em modo CLI (root local sem auth), usa ``"local"`` — mesmo default de
    ``backend/tools/memory.py::_user_id_from_config``.
    """
    user = getattr(request.state, "user", None)
    if user is not None and hasattr(user, "id"):
        return str(user.id)
    return "local"


def _namespace(request: Request) -> tuple[str, ...]:
    """Namespace do store — idêntico ao usado pelas memory tools do agente."""
    return ("user", _user_id(request), "memories")


async def _store() -> Any:
    from backend.services.agent_factory import get_store

    return await get_store()


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
        ns = _namespace(request)
        store = await _store()

        existing = await store.aget(ns, body.key)
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Memória '{body.key}' já existe. Use PUT para editar.",
            )

        await store.aput(
            ns,
            body.key,
            {
                "key": body.key,
                "content": body.content,
                "metadata": body.metadata,
                "updated_at": datetime.now(UTC).isoformat(),
            },
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
        ns = _namespace(request)
        store = await _store()
        items = await store.asearch(ns, limit=_LIST_ALL_LIMIT)

        all_mems = [
            {
                "key": item.key,
                "content": item.value.get("content", ""),
                "metadata": item.value.get("metadata") or {},
                "updated_at": item.value.get("updated_at", ""),
            }
            for item in items
        ]
        all_mems.sort(key=lambda m: m["updated_at"], reverse=True)

        page = all_mems[offset : offset + limit]
        return ListMemoriesResponse(
            memories=[MemoryItem(**m) for m in page],
            total=len(all_mems),
        )
    except Exception as exc:
        logger.exception("list_memories failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{key}", response_model=MemoryItem)
async def get_memory_by_key(request: Request, key: str) -> MemoryItem:
    """Retorna uma memória específica pelo key."""
    try:
        ns = _namespace(request)
        store = await _store()
        item = await store.aget(ns, key)
        if item is None:
            raise HTTPException(
                status_code=404, detail=f"Memória '{key}' não encontrada"
            )
        return MemoryItem(
            key=key,
            content=item.value.get("content", ""),
            metadata=item.value.get("metadata") or {},
            updated_at=item.value.get("updated_at", ""),
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
        ns = _namespace(request)
        store = await _store()

        existing = await store.aget(ns, key)
        if existing is None:
            raise HTTPException(
                status_code=404, detail=f"Memória '{key}' não encontrada"
            )

        await store.aput(
            ns,
            key,
            {
                "key": key,
                "content": body.content,
                "metadata": body.metadata or existing.value.get("metadata") or {},
                "updated_at": datetime.now(UTC).isoformat(),
            },
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
        ns = _namespace(request)
        store = await _store()
        existing = await store.aget(ns, key)
        if existing is None:
            raise HTTPException(
                status_code=404, detail=f"Memória '{key}' não encontrada"
            )
        await store.adelete(ns, key)
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
        ns = _namespace(request)
        store = await _store()
        items = await store.asearch(ns, limit=_LIST_ALL_LIMIT)
        count = 0
        for item in items:
            await store.adelete(ns, item.key)
            count += 1
        logger.info("clear_all_memories: %d removidas (namespace=%s)", count, ns)
        return DeleteMemoryResponse(status="cleared", deleted=count)
    except Exception as exc:
        logger.exception("clear_all_memories failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
