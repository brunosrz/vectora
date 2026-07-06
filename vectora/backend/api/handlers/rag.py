"""Settings de RAG + gestão de coleções (aba de memória do workbench).

Endpoints (exigem auth via middleware):
    GET    /rag/settings             — settings de RAG em runtime
    PATCH  /rag/settings             — atualiza (reranker on/off, top_k, providers, tipos)
    GET    /rag/collections          — lista as coleções (tabelas LanceDB) e tamanho
    DELETE /rag/collections/{name}   — apaga uma coleção inteira
    GET    /rag/workspace-summary    — o que já está indexado num workspace específico
    POST   /rag/search               — busca direta do usuário (thin wrapper sobre vector_search)

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
    from backend.workspace.runtime_settings import runtime_settings

    return runtime_settings.rag_settings


@router.patch("/settings")
async def patch_rag_settings(body: RagSettingsBody) -> dict[str, Any]:
    from backend.workspace.runtime_settings import runtime_settings

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


@router.get("/workspace-summary")
async def get_workspace_rag_summary(workspace_id: str) -> dict[str, Any]:
    """O que já está indexado NESTE workspace, por coleção.

    RAG é escopo de workspace (persiste no LanceDB entre sessões), não de
    thread — sem este endpoint, a aba Memória do workbench só via
    `ragCitations` da thread atual (evento de streaming) e mostrava "vazio"
    numa sessão nova mesmo com o workspace já indexado antes. `workspace_id`
    vive dentro do JSON de `metadata` de cada linha (não é coluna própria do
    LanceDB), então a contagem exige ler o metadata de cada linha — mesmo
    custo já pago por `manage_retriever(action="list")` em `tools/rag.py`.
    """
    from backend.tools.rag import _parse_metadata

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

    summary: list[dict[str, Any]] = []
    for name in names:
        try:
            table = await db.open_table(str(name))
            df = await table.to_pandas()
        except Exception:
            # Coleção corrompida/sem tabela não deve derrubar as demais.
            logger.warning(
                "rag: falha ao ler coleção %r pro resumo do workspace",
                name,
                exc_info=True,
            )
            continue
        if "metadata" not in df.columns:
            continue
        meta = df["metadata"].map(_parse_metadata)
        count = sum(1 for m in meta if m.get("workspace_id") == workspace_id)
        if count > 0:
            summary.append({"name": str(name), "count": count})
    return {"collections": summary}


class RagSearchBody(BaseModel):
    query: str
    workspace_id: str | None = None
    collection: str | None = None
    limit: int = 5


@router.post("/search")
async def search_rag(body: RagSearchBody) -> dict[str, Any]:
    """Busca direta do usuário na base RAG — mesma `vector_search` que o agente usa.

    Sem `collection`, busca em toda coleção indexada com o `workspace_id`
    dado (via `/rag/workspace-summary`); resultados de todas as coleções
    são combinados e ordenados por score.
    """
    import json as _json

    from backend.tools.rag import vector_search

    collections: list[str]
    if body.collection:
        collections = [body.collection]
    elif body.workspace_id:
        summary = await get_workspace_rag_summary(body.workspace_id)
        collections = [c["name"] for c in summary["collections"]]
    else:
        collections = ["articles"]

    if not collections:
        return {"results": []}

    all_results: list[dict[str, Any]] = []
    for collection in collections:
        raw = await vector_search.ainvoke(
            {"query": body.query, "collection": collection, "limit": body.limit}
        )
        try:
            parsed = _json.loads(raw)
        except ValueError:
            continue
        for r in parsed.get("results", []):
            r["collection"] = collection
            all_results.append(r)

    all_results.sort(
        key=lambda r: r.get("relevance_score") or -r.get("score", 0), reverse=True
    )
    return {"results": all_results[: body.limit], "query": body.query}


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
