"""RAG tools: embedding assíncrono, busca vetorial e ingestão de documentos."""

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any, Literal

from langchain.tools import tool
from langchain_core.documents import Document as LCDoc
from langchain_core.runnables import RunnableConfig

from vectora.config.settings import settings
from vectora.services.queue import get_embedding_queue
from vectora.services.text import text_service

try:
    import lancedb
    import pandas as pd
    from langchain_cohere import CohereEmbeddings, CohereRerank
    from pydantic import SecretStr
except ImportError:
    lancedb = None  # type: ignore
    pd = None  # type: ignore
    CohereEmbeddings = None  # type: ignore
    CohereRerank = None  # type: ignore
    SecretStr = None  # type: ignore

logger = logging.getLogger(__name__)


def _parse_metadata(raw: object) -> dict[str, Any]:
    """Desserializa o campo `metadata` de uma linha LanceDB para dict.

    O metadata é gravado como string JSON pelo background worker. Aceita
    também dict já desserializado (defensivo) e devolve {} em qualquer falha.
    """
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError, ValueError:
        return {}


def _is_cohere_quota_error(err: str) -> bool:
    """Retorna True se o erro indica quota/rate-limit do Cohere."""
    err_lower = err.lower()
    return (
        "429" in err
        or "too many requests" in err_lower
        or "rate limit" in err_lower
        or "quota" in err_lower
        or "you are using a trial key" in err_lower
        or "monthly active users" in err_lower
    )


@tool(extras={"render_hint": "queue_badge"})
async def embedding(
    text: str, collection: str = "articles", metadata: dict[str, Any] | None = None
) -> str:
    """Enfileira documento para embedding assíncrono (fire-and-forget).

    Em vez de bloquear esperando Cohere (1-2 segundos por chunk), enfileira o documento
    imediatamente. Um background worker processa a fila e indexa em LanceDB.

    Args:
        text: Texto do documento a indexar
        collection: Nome da coleção LanceDB (articles, wiki, api_docs, knowledge_base)
        metadata: Metadados opcionais (source, author, timestamp, etc)

    Returns:
        JSON com status fire_and_forget + queue_id, ou error
    """
    if not settings.embedding_queue_enabled:
        logger.error("embedding called but queue not enabled")
        return json.dumps(
            {"status": "error", "error": "Embedding queue not configured."}
        )

    _t0 = time.perf_counter()
    try:
        queue = await get_embedding_queue(settings.embedding_queue_dsn)
        queue_id = await queue.enqueue(text, collection, metadata)

        logger.info(
            "embedding_enqueued",
            extra={
                "queue_id": queue_id,
                "collection": collection,
                "text_length": len(text),
            },
        )
        try:
            from vectora.services.tracer import tracer as _tr

            async with _tr.span("embedding_tool", "enqueue") as _s:
                _s.set(queue_id=queue_id, collection=collection, text_len=len(text))
        except Exception:
            pass

        return json.dumps(
            {
                "status": "fire_and_forget",
                "queue_id": queue_id,
                "collection": collection,
                "message": "Document enqueued for async embedding and indexing.",
            }
        )

    except Exception as e:
        err = str(e)
        logger.exception(
            "embedding_enqueue_failed",
            extra={"collection": collection, "text_length": len(text)},
        )
        try:
            from vectora.services.tracer import tracer as _tr

            _tr.record_sync(
                "embedding_tool",
                "enqueue",
                time.perf_counter() - _t0,
                {"collection": collection},
                status="error",
            )
        except Exception:
            pass
        if _is_cohere_quota_error(err):
            return json.dumps(
                {
                    "status": "quota_error",
                    "error": (
                        "**Cohere: quota/rate limit atingido.**\n"
                        "Aguarde alguns minutos ou verifique seu plano em dashboard.cohere.com."
                    ),
                    "collection": collection,
                }
            )
        return json.dumps(
            {
                "status": "error",
                "error": err or "Failed to enqueue embedding",
                "collection": collection,
            }
        )


@tool(extras={"render_hint": "search_results"})
async def vector_search(
    query: str, collection: str = "articles", limit: int = 5
) -> str:
    """Busca o banco de dados vetorial LanceDB por documentos similares.

    LanceDB é file-based — nenhum container ou servidor é necessário.

    Args:
        query: String da consulta de busca
        collection: Nome da tabela LanceDB
        limit: Número máximo de resultados a retornar

    Returns:
        JSON com documentos e scores de similaridade
    """
    try:
        if lancedb is None or CohereEmbeddings is None:
            return "LanceDB or Cohere dependencies missing."

        api_key = settings.get_cohere_api_key()
        if not api_key:
            logger.error("vector_search called but COHERE_API_KEY not configured")
            return json.dumps(
                {"status": "failed", "error": "COHERE_API_KEY not configured"}
            )

        # NOTE: do NOT wrap in SecretStr here.
        # langchain-core's get_from_dict_or_env calls str(SecretStr) → "**********",
        # not the actual value, causing a 401 from Cohere.
        embeddings_model = CohereEmbeddings(  # ty: ignore[missing-argument]
            cohere_api_key=api_key,  # ty: ignore[invalid-argument-type]
            model=settings.embedding_model,
        )

        # embed_query → input_type="search_query" (Cohere v3 assimétrico).
        # Os documentos são indexados com embed_documents → "search_document"
        # no background worker. Não trocar por embed_documents aqui.
        query_vector = embeddings_model.embed_query(query)

        db = await lancedb.connect_async(str(settings.lancedb_dir))

        try:
            async with asyncio.timeout(10):
                table = await db.open_table(collection)
        except TimeoutError:
            logger.exception(f"LanceDB open_table timed out for {collection}")
            return json.dumps(
                {"status": "error", "error": "Vector store access timed out"}
            )
        except Exception:
            logger.warning("LanceDB table not found", extra={"collection": collection})
            return json.dumps(
                {
                    "status": "no_results",
                    "message": f"Collection '{collection}' not found or empty",
                }
            )

        try:
            async with asyncio.timeout(10):
                search_results = await (
                    table.vector_search(query_vector).limit(limit).to_pandas()
                )
        except TimeoutError:
            logger.exception(f"vector_search timed out for collection {collection}")
            return json.dumps(
                {"status": "error", "error": "Search timed out after 10s"}
            )

        results = [
            {
                "id": str(row["id"]),
                "score": float(row.get("_distance", 0.0)),
                "content": row["text"],
                "metadata": json.loads(row.get("metadata", "{}")),
            }
            for _, row in search_results.iterrows()
        ]

        # Reranking opcional — melhora precisão
        if results and settings.reranker_type == "cohere" and CohereRerank:
            try:
                reranker = CohereRerank(
                    cohere_api_key=SecretStr(api_key),
                    model=settings.reranker_model,
                    top_n=settings.reranker_top_k,
                )
                docs_to_rerank = [
                    LCDoc(page_content=str(r["content"]), metadata=r["metadata"])
                    for r in results
                ]
                reranked_docs = reranker.compress_documents(docs_to_rerank, query)
                results = [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "relevance_score": doc.metadata.get("relevance_score"),
                    }
                    for doc in reranked_docs
                ]
                logger.info("vector_search_reranked", extra={"top_k": len(results)})
            except Exception as rerank_err:
                logger.warning(f"Reranking failed, using raw results: {rerank_err}")
                for r in results:
                    r["reranking_status"] = "unavailable"

        logger.info(
            "vector_search completed",
            extra={
                "query": query,
                "collection": collection,
                "result_count": len(results),
            },
        )
        try:
            from vectora.services.tracer import tracer as _tr

            async with _tr.span("vector_search_tool", "search") as _s:
                _s.set(
                    collection=collection, n_results=len(results), query_len=len(query)
                )
        except Exception:
            pass

        return json.dumps(
            {
                "status": "success",
                "results": results,
                "query": query,
                "collection": collection,
            }
        )

    except Exception as e:
        err = str(e)
        logger.exception(
            "vector_search_failed", extra={"query": query, "collection": collection}
        )
        if _is_cohere_quota_error(err):
            return json.dumps(
                {
                    "status": "quota_error",
                    "error": (
                        "**Cohere: quota/rate limit atingido.**\n"
                        "Aguarde alguns minutos ou verifique seu plano em dashboard.cohere.com."
                    ),
                }
            )
        return json.dumps({"status": "failed", "error": err or "Vector search failed"})


@tool(extras={"render_hint": "queue_progress"})
async def ingest_docs(
    directory_path: str,
    collection: str = "articles",
    glob_pattern: str = "**/*.py",
    config: RunnableConfig | None = None,
) -> str:
    """Indexa um diretório inteiro de arquivos no banco vetorial (LanceDB).

    Use quando o usuário pedir para:
    - "fazer embedding de uma pasta" / "indexar uma pasta"
    - "adicionar arquivos ao RAG" / "rag add <pasta>"
    - Indexar código-fonte Python, documentação ou qualquer conjunto de arquivos

    NUNCA chamar via terminal — esta é uma tool nativa, não um comando de shell.
    Respeita automaticamente .gitignore e .vectoraignore — __pycache__, .venv,
    node_modules e demais entradas de ambos os arquivos são ignorados.
    Crie um .vectoraignore na raiz do projeto para controle granular do RAG
    (mesmo formato do .gitignore, ex: "tests/fixtures/**", "*.generated.py").

    Args:
        directory_path: Caminho da pasta (ex: ".", "vectora/agents", "docs/")
        collection: Coleção LanceDB de destino (default: "articles")
        glob_pattern: Filtro de arquivos:
            - "**/*.py"  → arquivos Python (default — projetos Python)
            - "**/*.md"  → Markdown / documentação
            - "**/*"     → todos os arquivos de texto

    Returns:
        JSON com total_files, total_chunks, indexed (enfileirados), failed
    """
    from pathlib import Path

    from vectora.services.ignore import is_ignored, load_ignore_spec
    from vectora.services.security import is_safe_file_path

    if not is_safe_file_path(directory_path):
        return f"Access denied: {directory_path} is outside allowed directory"

    path = Path(directory_path).resolve()
    if not path.is_dir():
        return f"Not a directory: {directory_path}"

    # Carrega specs combinadas (.gitignore + .vectoraignore) uma vez para todo o diretório
    spec = load_ignore_spec(path)

    # Usa o glob_pattern diretamente no rglob para que o Python filtre por extensão
    # de forma nativa — ex: "**/*.py" → rglob("*.py") retorna apenas arquivos .py,
    # nunca .pyc nem qualquer outro sufixo.  Depois aplica is_ignored em TODOS os
    # candidatos, garantindo que __pycache__, .venv e demais dirs hardcoded em
    # ALWAYS_SKIP_DIRS sejam contabilizados corretamente em skipped_ignored.
    stripped_glob = glob_pattern
    while stripped_glob.startswith("**/"):
        stripped_glob = stripped_glob[3:]

    all_matching = sorted(f for f in path.rglob(stripped_glob) if f.is_file())
    files_to_ingest: list[Path] = []
    skipped_ignored = 0

    for f in all_matching:
        if is_ignored(f, path, spec):
            skipped_ignored += 1
            logger.debug(
                "ingest_docs: arquivo ignorado por .gitignore/.vectoraignore/ALWAYS_SKIP",
                extra={"file": str(f)},
            )
        else:
            files_to_ingest.append(f)

    if not files_to_ingest:
        return json.dumps(
            {
                "status": "no_files",
                "message": f"Nenhum arquivo encontrado em '{directory_path}' com padrão '{glob_pattern}' (após filtrar .gitignore, .vectoraignore)",
                "skipped_ignored": skipped_ignored,
            }
        )

    # Splitter vem do TextService — fonte única de verdade para chunking.
    # Encoding, chunk_size e chunk_overlap são definidos em Settings e
    # compartilhados com o token_counter do trim_messages em engine.py.
    success_count = 0
    fail_count = 0
    total_chunks = 0

    for file_path in files_to_ingest:
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning(
                "ingest_docs: falha ao ler arquivo",
                extra={"file": str(file_path), "error": str(e)},
            )
            fail_count += 1
            continue

        chunks = text_service.split(text)
        total_chunks += len(chunks)

        for chunk_text in chunks:
            # workspace_id injetado no metadata para isolamento por projeto (B5)
            _workspace_id = (
                (config.get("configurable") or {}).get("workspace_id")
                if config is not None
                else None
            )
            chunk_metadata: dict[str, Any] = {
                "source": str(file_path),
                "source_dir": directory_path,
                "ingested_at": datetime.now(UTC).isoformat(),
            }
            if _workspace_id:
                chunk_metadata["workspace_id"] = _workspace_id

            try:
                res = await embedding.ainvoke(
                    {
                        "text": chunk_text,
                        "collection": collection,
                        "metadata": chunk_metadata,
                    }
                )
                data = json.loads(res) if isinstance(res, str) else res
                if isinstance(data, dict) and data.get("status") == "fire_and_forget":
                    success_count += 1
                elif isinstance(data, dict) and data.get("status") == "quota_error":
                    # Cohere quota hit — abort early and surface the error
                    logger.warning(
                        "ingest_docs: quota Cohere atingida, abortando",
                        extra={"file": str(file_path)},
                    )
                    return json.dumps(
                        {
                            "status": "quota_error",
                            "error": (
                                "**Cohere: quota/rate limit atingido.**\n"
                                "Aguarde alguns minutos ou verifique seu plano em dashboard.cohere.com."
                            ),
                            "indexed_before_error": success_count,
                            "collection": collection,
                        }
                    )
                else:
                    fail_count += 1
            except Exception as chunk_err:
                logger.warning(
                    "ingest_docs: falha ao enfileirar chunk",
                    extra={"file": str(file_path), "error": str(chunk_err)},
                )
                fail_count += 1

    logger.info(
        "ingest_docs_completed",
        extra={
            "collection": collection,
            "total_files": len(files_to_ingest),
            "total_chunks": total_chunks,
            "success": success_count,
            "fail": fail_count,
            "skipped_ignored": skipped_ignored,
        },
    )

    return json.dumps(
        {
            "status": "completed",
            "total_files": len(files_to_ingest),
            "total_chunks": total_chunks,
            "indexed": success_count,
            "failed": fail_count,
            "skipped_ignored": skipped_ignored,
            "collection": collection,
        }
    )


@tool(extras={"render_hint": "table"})
async def manage_retriever(
    action: Literal["list", "delete", "purge"],
    collection: str = "web_cache",
    source: str | None = None,
) -> str:
    """Gerencia documentos indexados no RAG — listar, remover ou limpar.

    Use para CORRIGIR a base de conhecimento. O Vectora indexa conteúdo web
    automaticamente (após curadoria). Quando uma fonte se revela errada — por
    exemplo, o usuário fornece depois o repositório ou doc canônico — use esta
    tool para remover o que foi indexado por engano. Indexar é só metade do
    trabalho; poder desfazer é o que mantém o RAG confiável.

    Args:
        action:
            - "list": lista os documentos da coleção (source, title, score)
            - "delete": remove documentos cujo source/url/title contém `source`
            - "purge": apaga a coleção inteira — use com cuidado
        collection: coleção LanceDB alvo (default: "web_cache", o bucket web).
            Use "articles" para o bucket de docs curados pelo usuário.
        source: para action="delete", trecho da URL/source/título a remover
            (ex: "godot-gameplay-systems"). Obrigatório quando action="delete".

    Returns:
        JSON com o resultado da operação
    """
    if lancedb is None:
        return json.dumps({"status": "error", "error": "LanceDB não instalado."})
    if settings.lancedb_dir is None:
        return json.dumps({"status": "error", "error": "lancedb_dir não configurado."})
    if action == "delete" and not source:
        return json.dumps(
            {
                "status": "error",
                "error": "Param 'source' é obrigatório para action='delete'.",
            }
        )

    try:
        db = await lancedb.connect_async(str(settings.lancedb_dir))
    except Exception as e:
        return json.dumps(
            {"status": "error", "error": f"Falha ao conectar LanceDB: {e}"}
        )

    # purge — apaga a coleção inteira
    if action == "purge":
        try:
            await db.drop_table(collection)
            logger.info("manage_retriever_purge", extra={"collection": collection})
            return json.dumps({"status": "purged", "collection": collection})
        except Exception as e:
            return json.dumps(
                {"status": "error", "error": f"Falha ao apagar '{collection}': {e}"}
            )

    # list / delete — abrem a tabela e escaneiam os metadados
    try:
        async with asyncio.timeout(10):
            table = await db.open_table(collection)
    except Exception:
        return json.dumps(
            {
                "status": "no_results",
                "message": f"Coleção '{collection}' não encontrada ou vazia",
            }
        )

    try:
        async with asyncio.timeout(15):
            df = await table.to_pandas()
    except Exception as e:
        return json.dumps(
            {"status": "error", "error": f"Falha ao ler '{collection}': {e}"}
        )

    # Parse do metadata vetorizado — uma passada pandas (.map), sem iterrows()
    # (iterrows é notoriamente lento; .map roda em C sobre a Series inteira).
    if "metadata" not in df.columns or "id" not in df.columns:
        return json.dumps(
            {
                "status": "no_results",
                "message": f"Coleção '{collection}' sem schema id/metadata",
            }
        )
    ids = df["id"].astype(str)
    meta = df["metadata"].map(_parse_metadata)

    if action == "list":
        items = [
            {
                "id": doc_id,
                "source": m.get("source") or m.get("url", ""),
                "title": m.get("title", ""),
                "origin": m.get("origin", ""),
                "relevance_score": m.get("relevance_score"),
                "indexed_at": m.get("indexed_at", ""),
            }
            for doc_id, m in zip(ids, meta, strict=False)
        ]
        return json.dumps(
            {
                "status": "success",
                "collection": collection,
                "count": len(items),
                "documents": items,
            }
        )

    # action == "delete" — 'source' já validado no início da função.
    # Match por substring via máscara booleana vetorizada sobre o DataFrame.
    needle = (source or "").lower()

    def _meta_matches(m: dict[str, Any]) -> bool:
        return (
            needle in str(m.get("source", "")).lower()
            or needle in str(m.get("url", "")).lower()
            or needle in str(m.get("title", "")).lower()
        )

    matched = ids[meta.map(_meta_matches)].tolist()
    if not matched:
        return json.dumps(
            {
                "status": "no_match",
                "collection": collection,
                "message": f"Nenhum documento com source contendo '{source}'",
            }
        )

    try:
        # queue_ids são UUIDs — sem aspas/escape a tratar no predicado SQL.
        id_list = ", ".join(f"'{i}'" for i in matched)
        await table.delete(f"id IN ({id_list})")
        logger.info(
            "manage_retriever_delete",
            extra={"collection": collection, "deleted": len(matched)},
        )
        return json.dumps(
            {
                "status": "deleted",
                "collection": collection,
                "deleted": len(matched),
                "ids": matched,
            }
        )
    except Exception as e:
        return json.dumps({"status": "error", "error": f"Falha ao deletar: {e}"})
