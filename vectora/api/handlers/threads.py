"""Handler do serviço ThreadService — CRUD de threads via REST.

Endpoints (todos POST, padrão ConnectRPC):
    POST /vectora.chat.v1.ThreadService/CreateThread
    POST /vectora.chat.v1.ThreadService/GetThread
    POST /vectora.chat.v1.ThreadService/ListThreads
    POST /vectora.chat.v1.ThreadService/DeleteThread
    POST /vectora.chat.v1.ThreadService/GetHistory

Persiste no mesmo banco SQLite que o chat TUI usa, via AsyncSqliteSaver
+ tabela vectora_sessions.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from vectora.api.schemas import (
    CreateThreadRequest,
    DeleteThreadRequest,
    GetHistoryRequest,
    GetHistoryResponse,
    GetThreadRequest,
    HistoryMessage,
    ListThreadsRequest,
    ListThreadsResponse,
    Thread,
    UpdateThreadRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Lazy DB loader
# ---------------------------------------------------------------------------

_db_conn: Any = None


async def _ensure_schema(db: Any) -> None:
    """Cria a tabela ``vectora_sessions`` se ainda não existir.

    Idempotente. Exportada para que o ``_lifespan`` do server possa chamar
    no startup, garantindo que a tabela exista antes do primeiro request —
    evita race com o ``AsyncSqliteSaver`` do LangGraph que abre o mesmo
    arquivo ``~/.vectora/checkpoints.db``.
    """
    await db.execute("""
        CREATE TABLE IF NOT EXISTS vectora_sessions (
            thread_id     TEXT    PRIMARY KEY,
            user_type     TEXT    NOT NULL DEFAULT 'human',
            created_at    TEXT    NOT NULL,
            last_activity TEXT    NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            extra         TEXT    NOT NULL DEFAULT '{}'
        )
    """)
    await db.commit()


async def _get_db() -> Any:
    """Retorna conexão aiosqlite com o banco de checkpoints/sessões."""
    global _db_conn
    if _db_conn is None:
        from pathlib import Path

        import aiosqlite

        db_path = Path.home() / ".vectora" / "checkpoints.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _db_conn = await aiosqlite.connect(str(db_path))
        await _db_conn.execute("PRAGMA journal_mode=WAL")
        await _ensure_schema(_db_conn)
    return _db_conn


async def ensure_sessions_table() -> None:
    """Cria a tabela ``vectora_sessions`` ao boot (chamada do lifespan)."""
    db = await _get_db()
    await _ensure_schema(db)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_thread(row: tuple) -> Thread:
    """Converte uma linha da tabela vectora_sessions em Thread."""
    thread_id, _, created_at, last_activity, _, extra_json = row
    title = ""
    workspace_id = ""
    try:
        extra = json.loads(extra_json or "{}")
        title = extra.get("title", "")
        workspace_id = extra.get("workspace_id", "")
    except Exception:
        pass
    return Thread(
        id=str(thread_id),
        created_at=created_at,
        updated_at=last_activity,
        title=title,
        workspace_id=workspace_id,
    )


# ---------------------------------------------------------------------------
# _upsert_session — registra/atualiza thread em vectora_sessions
# ---------------------------------------------------------------------------


async def _upsert_session(
    thread_id: str, title: str | None = None, workspace_id: str | None = None
) -> None:
    """Garante que thread_id existe em vectora_sessions (cria ou atualiza).

    Chamado por stream_chat() para que threads criadas via chat normal
    apareçam em ListThreads após reinicialização do servidor.

    O campo extra é mesclado: title e workspace_id só são sobrescritos quando
    fornecidos, preservando os demais dados já gravados.
    """
    db = await _get_db()
    now = datetime.now(UTC).isoformat()

    async with db.execute(
        "SELECT extra FROM vectora_sessions WHERE thread_id = ?",
        (thread_id,),
    ) as cur:
        row = await cur.fetchone()
    extra: dict[str, Any] = {}
    if row:
        try:
            extra = json.loads(row[0] or "{}")
        except Exception:
            extra = {}
    if title is not None:
        extra["title"] = title
    if workspace_id is not None:
        extra["workspace_id"] = workspace_id
    extra_json = json.dumps(extra)

    # ON CONFLICT preserva created_at original; atualiza last_activity e extra.
    await db.execute(
        """
        INSERT INTO vectora_sessions
            (thread_id, created_at, last_activity, message_count, extra)
        VALUES (?, ?, ?, 0, ?)
        ON CONFLICT(thread_id) DO UPDATE SET
            last_activity = excluded.last_activity,
            extra        = excluded.extra
        """,
        (thread_id, now, now, extra_json),
    )
    await db.commit()


# ---------------------------------------------------------------------------
# CreateThread
# ---------------------------------------------------------------------------


@router.post("/vectora.chat.v1.ThreadService/CreateThread")
async def create_thread(_: CreateThreadRequest) -> Thread:
    """Cria uma nova thread vazia e persiste no banco."""
    db = await _get_db()
    thread_id = str(uuid.uuid4())[:8]
    now = datetime.now(UTC).isoformat()
    await db.execute(
        """
        INSERT INTO vectora_sessions (thread_id, created_at, last_activity, extra)
        VALUES (?, ?, ?, '{}')
        """,
        (thread_id, now, now),
    )
    await db.commit()
    return Thread(id=thread_id, created_at=now, updated_at=now, title="")


# ---------------------------------------------------------------------------
# GetThread
# ---------------------------------------------------------------------------


@router.post("/vectora.chat.v1.ThreadService/GetThread")
async def get_thread(request: GetThreadRequest) -> Thread:
    db = await _get_db()
    async with db.execute(
        "SELECT thread_id, user_type, created_at, last_activity, message_count, extra "
        "FROM vectora_sessions WHERE thread_id = ?",
        (request.thread_id,),
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Thread {request.thread_id!r} not found"
        )
    return _row_to_thread(row)


# ---------------------------------------------------------------------------
# ListThreads
# ---------------------------------------------------------------------------


@router.post("/vectora.chat.v1.ThreadService/ListThreads")
async def list_threads(request: ListThreadsRequest) -> ListThreadsResponse:
    limit = max(1, min(request.limit or 50, 200))
    db = await _get_db()
    async with db.execute(
        "SELECT thread_id, user_type, created_at, last_activity, message_count, extra "
        "FROM vectora_sessions ORDER BY last_activity DESC LIMIT ?",
        (limit,),
    ) as cur:
        rows = await cur.fetchall()
    return ListThreadsResponse(threads=[_row_to_thread(r) for r in rows])


# ---------------------------------------------------------------------------
# DeleteThread
# ---------------------------------------------------------------------------


@router.post("/vectora.chat.v1.ThreadService/DeleteThread")
async def delete_thread(request: DeleteThreadRequest) -> dict:
    db = await _get_db()
    await db.execute(
        "DELETE FROM vectora_sessions WHERE thread_id = ?",
        (request.thread_id,),
    )
    await db.commit()
    return {}


# ---------------------------------------------------------------------------
# UpdateThread
# ---------------------------------------------------------------------------


@router.post("/vectora.chat.v1.ThreadService/UpdateThread")
async def update_thread(request: UpdateThreadRequest) -> Thread:
    """Atualiza metadados (title) de uma thread existente."""
    db = await _get_db()
    async with db.execute(
        "SELECT thread_id, user_type, created_at, last_activity, message_count, extra "
        "FROM vectora_sessions WHERE thread_id = ?",
        (request.thread_id,),
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Thread {request.thread_id!r} not found"
        )
    thread = _row_to_thread(row)
    # Merge title no extra existente
    try:
        extra = json.loads(row[5] or "{}")
    except Exception:
        extra = {}
    extra["title"] = request.title
    now = datetime.now(UTC).isoformat()
    await db.execute(
        "UPDATE vectora_sessions SET extra = ?, last_activity = ? WHERE thread_id = ?",
        (json.dumps(extra), now, request.thread_id),
    )
    await db.commit()
    return Thread(
        id=thread.id,
        created_at=thread.created_at,
        updated_at=now,
        title=request.title,
    )


# ---------------------------------------------------------------------------
# GetHistory
# ---------------------------------------------------------------------------


@router.post("/vectora.chat.v1.ThreadService/GetHistory")
async def get_history(request: GetHistoryRequest) -> GetHistoryResponse:
    """Retorna o histórico de mensagens de uma thread via checkpointer LangGraph.

    Reusa o singleton do grafo (mesmo que o handler de chat) — evita rebuild
    do grafo + abertura de uma nova connection SQLite a cada request.
    """
    try:
        from vectora.api.handlers.chat import _get_graph

        graph = await _get_graph()
        config = {"configurable": {"thread_id": request.thread_id}}
        state = await graph.aget_state(config)

        if state is None or not state.values:
            return GetHistoryResponse(messages=[])

        messages_raw = state.values.get("messages", [])
        history: list[HistoryMessage] = []
        for msg in messages_raw:
            role = "assistant"
            if hasattr(msg, "type"):
                role = "human" if msg.type == "human" else "assistant"
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            history.append(HistoryMessage(role=role, content=content))

        return GetHistoryResponse(messages=history)

    except Exception as exc:
        logger.exception("api/threads: erro ao carregar histórico")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
