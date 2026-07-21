"""Memory Library — catálogo e instalação de buckets RAG compartilhados.

Endpoints (montados em server.py):
    GET  /rag-library/catalog — lista buckets publicados (id, embed_model,
                                 verified, downloads_count, license, ...)
    POST /rag-library/install — baixa e instala um bucket como coleção
                                 LanceDB isolada (`shared_{bucket_id}`)

Download é sempre grátis (decisão de produto) — sem gate de tier/quota.
Publicação (`publish_memory_bucket`) exige `session_token` de uma conta
vectora.company — não há hoje fluxo de login company↔desktop no backend
local pra obter esse token, então não há endpoint `/rag-library/publish`
aqui ainda (gap documentado, não um stub fingindo funcionar).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.memory_library import MemoryLibraryError, download_memory_bucket
from backend.services.memory_library import list_catalog as _list_catalog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag-library", tags=["memory-library"])


class InstallRequest(BaseModel):
    bucket_id: str


@router.get("/catalog")
async def get_catalog() -> list[dict]:
    return await _list_catalog()


@router.post("/install")
async def post_install(req: InstallRequest) -> dict:
    try:
        collection = await download_memory_bucket(req.bucket_id)
    except MemoryLibraryError as exc:
        return {"status": "error", "error": str(exc)}
    return {"status": "installed", "collection": collection}
