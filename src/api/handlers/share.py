"""Handler de compartilhamento de threads (leitura pública).

Endpoints:
    POST /threads/share         — autenticado, cria token de acesso público
    GET  /threads/share/{token} — público, retorna conversa somente-leitura
    DELETE /threads/share/{token} — autenticado, revoga token

O token é um UUID armazenado na tabela ``shared_threads`` do mesmo banco
SQLite usado pelas threads (``~/.vectora/checkpoints.db``).
"""

from __future__ import annotations

import json
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import (
    CreateShareRequest,
    CreateShareResponse,
    HistoryMessage,
    SharedThread,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/threads", tags=["share"])


# ---------------------------------------------------------------------------
# DB helpers (reusa conexão do handler de threads)
# ---------------------------------------------------------------------------


async def _get_db() -> Any:
    from src.api.handlers.threads import _get_db as _threads_db

    return await _threads_db()


async def _ensure_share_table(db: Any) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS shared_threads (
            token       TEXT PRIMARY KEY,
            thread_id   TEXT NOT NULL,
            created_by  TEXT NOT NULL DEFAULT '',
            created_at  TEXT NOT NULL,
            expires_at  TEXT NOT NULL
        )
    """)
    await db.commit()


# ---------------------------------------------------------------------------
# POST /threads/share — cria token (autenticado)
# ---------------------------------------------------------------------------


@router.post("/share")
async def create_share(
    request: Request, body: CreateShareRequest
) -> CreateShareResponse:
    user = getattr(request.state, "user", None)
    user_id = user.id if user else "local"

    db = await _get_db()
    await _ensure_share_table(db)

    token = secrets.token_urlsafe(24)
    now = datetime.now(UTC)
    expires_at = (now + timedelta(hours=max(1, min(body.ttl_hours, 720)))).isoformat()

    await db.execute(
        "INSERT INTO shared_threads (token, thread_id, created_by, created_at, expires_at) VALUES (?,?,?,?,?)",
        (token, body.thread_id, user_id, now.isoformat(), expires_at),
    )
    await db.commit()

    base_url = str(request.base_url).rstrip("/")
    return CreateShareResponse(
        token=token,
        url=f"{base_url}/share/{token}",
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# GET /threads/share/{token} — leitura pública
# ---------------------------------------------------------------------------


@router.get("/share/{token}")
async def get_shared_thread(token: str) -> SharedThread:
    db = await _get_db()
    await _ensure_share_table(db)

    async with db.execute(
        "SELECT thread_id, created_at, expires_at FROM shared_threads WHERE token = ?",
        (token,),
    ) as cur:
        row = await cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Share token not found")

    thread_id, created_at, expires_at = row

    now = datetime.now(UTC).isoformat()
    if expires_at < now:
        raise HTTPException(status_code=404, detail="Share token expired")

    # Obtém título da thread
    title = ""
    async with db.execute(
        "SELECT extra FROM vectora_sessions WHERE thread_id = ?",
        (thread_id,),
    ) as cur:
        session_row = await cur.fetchone()
    if session_row:
        try:
            extra = json.loads(session_row[0] or "{}")
            title = extra.get("title", "")
        except Exception:
            pass

    # Busca histórico via grafo LangGraph
    messages: list[HistoryMessage] = []
    try:
        from src.api.handlers.chat import _get_graph

        graph = await _get_graph()
        config = {"configurable": {"thread_id": thread_id}}
        state = await graph.aget_state(config)
        if state and state.values:
            for msg in state.values.get("messages", []):
                role = "assistant"
                if hasattr(msg, "type"):
                    role = "human" if msg.type == "human" else "assistant"
                content = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )
                messages.append(HistoryMessage(role=role, content=content))
    except Exception:
        logger.debug("share: não foi possível carregar histórico do grafo")

    return SharedThread(
        thread_id=thread_id,
        title=title,
        messages=messages,
        created_at=created_at,
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# DELETE /threads/share/{token} — revoga token (autenticado)
# ---------------------------------------------------------------------------


@router.delete("/share/{token}")
async def delete_share(token: str, request: Request) -> dict:
    user = getattr(request.state, "user", None)
    user_id = user.id if user else "local"

    db = await _get_db()
    await _ensure_share_table(db)

    async with db.execute(
        "SELECT created_by FROM shared_threads WHERE token = ?",
        (token,),
    ) as cur:
        row = await cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Share token not found")

    # Apenas o criador ou admin pode revogar
    role = getattr(user, "role", "member") if user else "local"
    if row[0] != user_id and role not in ("root", "admin"):
        raise HTTPException(status_code=403, detail="Não autorizado")

    await db.execute("DELETE FROM shared_threads WHERE token = ?", (token,))
    await db.commit()
    return {}
