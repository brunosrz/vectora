"""Ingest direto de uma pasta no RAG (sem passar pelo agente).

Compartilha o walk/chunk do ``ingest_docs`` (tool) mas enfileira diretamente
na embedding queue com um ``job_id``, permitindo barra de progresso por pasta.
Usado pelos endpoints REST ``/workspaces/{id}/rag/ingest``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.embedding.queue import get_embedding_queue
from backend.services.ignore import load_ignore_spec, walk_files
from backend.services.security import is_safe_file_path
from backend.services.text import text_service
from backend.settings import settings

logger = logging.getLogger(__name__)

#: Extensões consideradas "código" para o filtro de tipo da UI.
_CODE_EXTS = {
    "py",
    "ts",
    "tsx",
    "js",
    "jsx",
    "mjs",
    "cjs",
    "go",
    "rs",
    "java",
    "c",
    "h",
    "cpp",
    "hpp",
    "cc",
    "cs",
    "rb",
    "php",
    "swift",
    "kt",
    "scala",
    "sh",
    "bash",
    "sql",
    "html",
    "css",
    "scss",
    "vue",
    "svelte",
    "toml",
    "yaml",
    "yml",
    "json",
}


def _matches_file_type(path: Path, file_types: str | list[str]) -> bool:
    """`file_types` aceita os 3 atalhos (`"all"`/`"code"`/`"markdown"`) ou
    uma lista de extensões customizadas (ex. `["xml"]`, sem ponto ou com —
    normalizado) — usada pra indexar só um formato específico, como docs de
    engine que só existem em XML."""
    ext = path.suffix.lstrip(".").lower()
    if isinstance(file_types, list):
        if not file_types:
            return True
        normalized = {t.lstrip(".").lower() for t in file_types}
        return ext in normalized
    if file_types == "markdown":
        return ext in {"md", "markdown", "mdx"}
    if file_types == "code":
        return ext in _CODE_EXTS
    return True  # "all"


async def ingest_directory(
    directory_path: str,
    *,
    file_types: str | list[str] = "all",
    collection: str = "articles",
    workspace_id: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Varre uma pasta, faz chunk e enfileira no RAG agrupado por ``job_id``.

    Respeita ``.gitignore``/``.vectoraignore`` (via ``walk_files``) e filtra
    por tipo de arquivo. Não bloqueia: o worker de embedding processa a fila.

    Returns:
        ``{job_id, total_files, total_chunks, status}``.

    Raises:
        ValueError: caminho fora do escopo seguro ou não é diretório.
    """
    if not is_safe_file_path(directory_path):
        raise ValueError(f"Caminho fora do escopo permitido: {directory_path}")
    path = Path(directory_path).resolve()
    if not path.is_dir():
        raise ValueError(f"Não é um diretório: {directory_path}")

    job = job_id or str(uuid4())
    spec = load_ignore_spec(path)
    all_files, _skipped = walk_files(path, "**/*", spec)
    files = [f for f in all_files if _matches_file_type(f, file_types)]

    if not files:
        return {
            "job_id": job,
            "total_files": 0,
            "total_chunks": 0,
            "status": "no_files",
        }

    queue = await get_embedding_queue(settings.embedding_queue_dsn)
    total_chunks = 0
    for file_path in files:
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            logger.warning("rag_ingest: falha ao ler %s", file_path, exc_info=True)
            continue
        for chunk in text_service.split(text):
            metadata: dict[str, Any] = {
                "source": str(file_path),
                "source_dir": str(path),
                "ingested_at": datetime.now(UTC).isoformat(),
            }
            if workspace_id:
                metadata["workspace_id"] = workspace_id
            try:
                await queue.enqueue(chunk, collection, metadata, job_id=job)
                total_chunks += 1
            except Exception:
                logger.warning(
                    "rag_ingest: falha ao enfileirar chunk de %s",
                    file_path,
                    exc_info=True,
                )

    logger.info(
        "rag_ingest_enqueued",
        extra={"job_id": job, "files": len(files), "chunks": total_chunks},
    )
    return {
        "job_id": job,
        "total_files": len(files),
        "total_chunks": total_chunks,
        "status": "enqueued",
    }
