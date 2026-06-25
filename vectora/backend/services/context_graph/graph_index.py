"""Índice vetorial dos nós do grafo no LanceDB (GraphRAG).

Indexa nós do grafo de contexto no LanceDB para busca semântica. Chamado pelo
pipeline após to_json (Passo 9). Permite que graph_query use vector_search +
expansão de vizinhança em vez de substring simples (GraphRAG completo).

Fallback silencioso: se LanceDB ou embeddings não estiverem disponíveis,
as funções retornam 0/[] sem quebrar o pipeline.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_COLLECTION = "context_graph_nodes"
_EMBED_BATCH = 64


async def _get_db() -> Any:
    """Retorna conexão LanceDB (reutiliza o settings.lancedb_dir do Vectora)."""
    import lancedb  # type: ignore[import-not-found]

    from backend.settings import settings

    return await lancedb.connect_async(str(settings.lancedb_dir))


async def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Embeda lista de textos em batches usando o mesmo modelo do RAG."""
    from backend.settings import settings

    try:
        from langchain_cohere import CohereEmbeddings  # type: ignore[import-not-found]
    except ImportError:
        return []

    api_key = settings.get_cohere_api_key()
    if not api_key:
        return []

    embeddings_model = CohereEmbeddings(  # type: ignore[call-arg]
        cohere_api_key=api_key,  # type: ignore[arg-type]
        model=settings.embedding_model,
    )

    import asyncio

    all_vectors: list[list[float]] = []
    for i in range(0, len(texts), _EMBED_BATCH):
        batch = texts[i : i + _EMBED_BATCH]
        vectors = await asyncio.to_thread(
            embeddings_model.embed_documents, batch
        )
        all_vectors.extend(vectors)
    return all_vectors


def _node_text(node: dict) -> str:
    """Texto canônico para embedar um nó do grafo."""
    label = node.get("label", node.get("id", ""))
    file_type = node.get("file_type", "")
    source_file = node.get("source_file", "")
    docstring = str(node.get("docstring", ""))[:200]
    parts = [label]
    if file_type:
        parts.append(f"— {file_type}")
    if source_file:
        parts.append(f"em {source_file}")
    if docstring:
        parts.append(f". {docstring}")
    return " ".join(parts)


async def index_graph_nodes(
    workspace_id: str,
    graph_data: dict,
    *,
    collection: str = _COLLECTION,
) -> int:
    """Indexa nós do grafo no LanceDB para busca semântica.

    Retorna número de nós indexados. Retorna 0 silenciosamente se LanceDB ou
    embeddings não estiverem disponíveis.
    """
    nodes: list[dict] = graph_data.get("nodes", [])
    if not nodes:
        return 0

    try:
        texts = [_node_text(n) for n in nodes]
        vectors = await _embed_texts(texts)
        if not vectors or len(vectors) != len(nodes):
            return 0

        rows = [
            {
                "id": str(n.get("id", "")),
                "vector": v,
                "text": t,
                "metadata": json.dumps({
                    "node_id": n.get("id", ""),
                    "workspace_id": workspace_id,
                    "source_file": n.get("source_file", ""),
                    "file_type": n.get("file_type", ""),
                }),
            }
            for n, v, t in zip(nodes, vectors, texts, strict=True)
            if n.get("id")
        ]
        if not rows:
            return 0

        db = await _get_db()
        existing = await db.table_names()
        if collection in existing:
            table = await db.open_table(collection)
            await table.add(rows)
        else:
            await db.create_table(collection, data=rows)

        logger.info(
            "context_graph: indexados %d nós no LanceDB (%s)",
            len(rows),
            collection,
            extra={"workspace_id": workspace_id},
        )
        return len(rows)

    except Exception:
        logger.exception(
            "context_graph: falha ao indexar nós no LanceDB",
            extra={"workspace_id": workspace_id},
        )
        return 0


async def search_graph_nodes(
    question: str,
    workspace_id: str,
    *,
    top_k: int = 10,
    collection: str = _COLLECTION,
) -> list[str]:
    """Busca nós semanticamente similares à questão. Retorna lista de node_ids.

    Retorna [] silenciosamente se LanceDB ou embeddings não estiverem disponíveis.
    """
    try:
        vectors = await _embed_texts([question])
        if not vectors:
            return []

        db = await _get_db()
        existing = await db.table_names()
        if collection not in existing:
            return []

        table = await db.open_table(collection)
        search_results = await (
            table.vector_search(vectors[0]).limit(top_k * 2).to_pandas()
        )

        node_ids: list[str] = []
        for _, row in search_results.iterrows():
            meta_raw = row.get("metadata", "{}")
            try:
                meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
            except (json.JSONDecodeError, TypeError):
                meta = {}
            if meta.get("workspace_id") == workspace_id:
                nid = meta.get("node_id") or str(row.get("id", ""))
                if nid:
                    node_ids.append(nid)
            if len(node_ids) >= top_k:
                break

        return node_ids

    except Exception:
        logger.exception(
            "context_graph: falha na busca vetorial de nós",
            extra={"workspace_id": workspace_id},
        )
        return []


async def purge_graph_index(
    workspace_id: str,
    collection: str = _COLLECTION,
) -> None:
    """Remove todos os nós do workspace do índice vetorial.

    Chamado antes de rebuild completo (update=False) para evitar duplicatas.
    """
    try:
        db = await _get_db()
        existing = await db.table_names()
        if collection not in existing:
            return

        table = await db.open_table(collection)
        await table.delete(f"json_extract(metadata, '$.workspace_id') = '{workspace_id}'")

        logger.info(
            "context_graph: índice purgado para workspace %s",
            workspace_id,
            extra={"workspace_id": workspace_id},
        )
    except Exception:
        logger.exception(
            "context_graph: falha ao purgar índice",
            extra={"workspace_id": workspace_id},
        )
