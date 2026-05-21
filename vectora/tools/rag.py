"""RAG tools: embedding assíncrono, busca vetorial e ingestão de documentos."""

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

from langchain.tools import tool
from langchain_core.documents import Document as LCDoc

from vectora.config.settings import settings
from vectora.services.queue import get_embedding_queue
from vectora.services.text import text_service

try:
    import lancedb
    from langchain_cohere import CohereEmbeddings, CohereRerank
    from pydantic import SecretStr
except ImportError:
    lancedb = None  # type: ignore
    CohereEmbeddings = None  # type: ignore
    CohereRerank = None  # type: ignore
    SecretStr = None  # type: ignore

logger = logging.getLogger(__name__)


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


@tool
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
    if not settings.enable_rag:
        logger.warning("embedding tool called but RAG disabled")
        return json.dumps(
            {
                "status": "error",
                "error": "RAG is disabled. Enable ENABLE_RAG=true to use this tool.",
            }
        )

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
                        "**⚠️ Cohere: quota/rate limit atingido.**\n"
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


@tool
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
    if not settings.enable_rag:
        logger.warning("vector_search tool called but RAG disabled")
        return "RAG is disabled. Enable ENABLE_RAG=true to use this tool."

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
                        "relevance_score": getattr(doc, "relevance_score", None),
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
                        "**⚠️ Cohere: quota/rate limit atingido.**\n"
                        "Aguarde alguns minutos ou verifique seu plano em dashboard.cohere.com."
                    ),
                }
            )
        return json.dumps({"status": "failed", "error": err or "Vector search failed"})


@tool
async def ingest_docs(
    directory_path: str,
    collection: str = "articles",
    glob_pattern: str = "**/*.py",
) -> str:
    """Indexa um diretório inteiro de arquivos no banco vetorial (LanceDB).

    Use quando o usuário pedir para:
    - "fazer embedding de uma pasta" / "indexar uma pasta"
    - "adicionar arquivos ao RAG" / "rag add <pasta>"
    - Indexar código-fonte Python, documentação ou qualquer conjunto de arquivos

    NUNCA chamar via terminal — esta é uma tool nativa, não um comando de shell.
    Respeita automaticamente o .gitignore — __pycache__, .venv, node_modules
    e demais entradas do .gitignore são ignorados automaticamente.

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

    from vectora.services.gitignore import is_ignored, load_gitignore_spec
    from vectora.services.security import is_safe_file_path

    if not settings.enable_file_operations:
        return "File operations are disabled."

    if not is_safe_file_path(directory_path):
        return f"Access denied: {directory_path} is outside allowed directory"

    path = Path(directory_path).resolve()
    if not path.is_dir():
        return f"Not a directory: {directory_path}"

    # Carrega spec do .gitignore uma vez para todo o diretório
    spec = load_gitignore_spec(path)

    # Extrai o sufixo do glob_pattern (ex: **/*.md → .md) para filtrar por extensão
    # Se o padrão não tiver extensão definida, aceita todos os arquivos
    suffix_filter: str | None = None
    if "." in glob_pattern.rsplit("/", maxsplit=1)[-1]:
        suffix_filter = "." + glob_pattern.rsplit(".", 1)[-1]

    # Varre o diretório respeitando .gitignore
    raw_files = sorted(path.rglob("*"))
    files_to_ingest: list[Path] = []
    skipped_ignored = 0

    for f in raw_files:
        if not f.is_file():
            continue
        if suffix_filter and f.suffix != suffix_filter:
            continue
        if is_ignored(f, path, spec):
            skipped_ignored += 1
            logger.debug(
                "ingest_docs: arquivo ignorado por .gitignore",
                extra={"file": str(f)},
            )
            continue
        files_to_ingest.append(f)

    if not files_to_ingest:
        return json.dumps(
            {
                "status": "no_files",
                "message": f"Nenhum arquivo encontrado em '{directory_path}' com padrão '{glob_pattern}' (após filtrar .gitignore)",
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
            chunk_metadata = {
                "source": str(file_path),
                "source_dir": directory_path,
                "ingested_at": datetime.now(UTC).isoformat(),
            }

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
                                "**⚠️ Cohere: quota/rate limit atingido.**\n"
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
