"""Settings de RAG + gestão de coleções (aba de memória do workbench).

Endpoints (exigem auth via middleware):
    GET    /rag/settings           — settings de RAG em runtime
    PATCH  /rag/settings           — atualiza (reranker on/off, top_k, providers, tipos)
    GET    /rag/collections        — lista as coleções (tabelas LanceDB) e tamanho
    DELETE /rag/collections/{name} — apaga uma coleção inteira

Os settings persistem em ``runtime_settings`` (``~/.vectora/settings.json``) e são
lidos pelo build do reranker/embeddings (``backend/tools/rag.py``).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


class RagSettingsBody(BaseModel):
    reranker_enabled: bool | None = None
    reranker_top_k: int | None = None
    rerank_provider: str | None = None
    embed_provider: str | None = None
    ingest_file_types: list[str] | None = None


@router.get("/settings")
async def get_rag_settings() -> dict[str, Any]:
    from backend.services.runtime_settings import runtime_settings

    return runtime_settings.rag_settings


@router.patch("/settings")
async def patch_rag_settings(body: RagSettingsBody) -> dict[str, Any]:
    from backend.services.runtime_settings import runtime_settings

    return runtime_settings.set_rag_settings(**body.model_dump())


async def _connect_lancedb() -> Any:
    """Conexão LanceDB async, ou None se indisponível/desconfigurado."""
    try:
        import lancedb

        from backend.settings import settings

        if settings.lancedb_dir is None:
            return None
        return await lancedb.connect_async(str(settings.lancedb_dir))
    except Exception:
        logger.warning("rag: falha ao conectar LanceDB", exc_info=True)
        return None


@router.get("/collections")
async def list_collections() -> dict[str, Any]:
    db = await _connect_lancedb()
    if db is None:
        return {"collections": []}
    try:
        names = (await db.list_tables()).tables
    except Exception:
        try:
            names = await db.table_names()
        except Exception:
            logger.warning("rag: falha ao listar coleções", exc_info=True)
            return {"collections": []}

    collections: list[dict[str, Any]] = []
    for name in names:
        count: int | None = None
        try:
            table = await db.open_table(name)
            count = await table.count_rows()
        except Exception:
            count = None
        collections.append({"name": str(name), "count": count})
    return {"collections": collections}


@router.delete("/collections/{name}")
async def delete_collection(name: str) -> dict[str, Any]:
    db = await _connect_lancedb()
    if db is None:
        raise HTTPException(status_code=503, detail="LanceDB indisponível")
    try:
        await db.drop_table(name)
    except Exception as exc:
        logger.warning("rag: falha ao apagar coleção %r", name, exc_info=True)
        raise HTTPException(
            status_code=404, detail=f"Coleção {name!r} não encontrada"
        ) from exc
    return {"status": "deleted", "name": name}
