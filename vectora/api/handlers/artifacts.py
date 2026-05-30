"""Handler de artifacts — lista planos/specs/guias gravados pelo agente.

Reusa ``ArtifactMetadata`` (``vectora/types/documents.py``) e o layout em
disco produzido por ``create_artifact`` (``vectora/tools/fs.py``):

    ~/.vectora/artifacts/<session_id>/<slug>.md
"""

from __future__ import annotations

import logging
from datetime import UTC
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from vectora.types.documents import ArtifactMetadata

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


class ListArtifactsResponse(BaseModel):
    artifacts: list[ArtifactMetadata]


class ArtifactContent(BaseModel):
    title: str
    slug: str
    session_id: str
    created_at: str
    content: str


def _artifacts_dir(session_id: str) -> Path:
    """Pasta de artifacts da sessão. Sanitiza o session_id (sem traversal)."""
    safe = session_id.replace("/", "").replace("\\", "").replace("..", "")
    return Path.home() / ".vectora" / "artifacts" / safe


def _read_preview(path: Path, limit: int = 200) -> str | None:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return f.read(limit + 1)[:limit]
    except OSError:
        return None


@router.get("/", response_model=ListArtifactsResponse)
async def list_artifacts(
    session_id: Annotated[str, Query()] = "",
) -> ListArtifactsResponse:
    """Lista os artifacts da sessão, mais novos primeiro."""
    if not session_id:
        return ListArtifactsResponse(artifacts=[])

    base = _artifacts_dir(session_id)
    if not base.exists() or not base.is_dir():
        return ListArtifactsResponse(artifacts=[])

    items: list[ArtifactMetadata] = []
    try:
        files = sorted(
            (p for p in base.glob("*.md") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        files = []

    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        title = path.stem.replace("-", " ").strip() or path.stem
        items.append(
            ArtifactMetadata(
                title=title,
                path=str(path),
                session_id=session_id,
                created_at=_format_mtime(stat.st_mtime),
                content_preview=_read_preview(path),
            )
        )
    return ListArtifactsResponse(artifacts=items)


@router.get("/{slug}", response_model=ArtifactContent)
async def get_artifact(
    slug: str,
    session_id: Annotated[str, Query()],
) -> ArtifactContent:
    """Devolve o markdown completo de um artifact."""
    base = _artifacts_dir(session_id)
    safe_slug = slug.replace("/", "").replace("\\", "").replace("..", "")
    path = base / f"{safe_slug}.md"

    if not path.exists() or not path.is_file():
        return ArtifactContent(
            title=safe_slug,
            slug=safe_slug,
            session_id=session_id,
            created_at="",
            content="",
        )

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        created = _format_mtime(path.stat().st_mtime)
    except OSError:
        content = ""
        created = ""

    return ArtifactContent(
        title=safe_slug.replace("-", " ").strip() or safe_slug,
        slug=safe_slug,
        session_id=session_id,
        created_at=created,
        content=content,
    )


def _format_mtime(ts: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(ts, tz=UTC).isoformat()
