"""Handler do serviço ThreadService — CRUD de threads via REST.

Endpoints (todos POST, padrão ConnectRPC):
    POST /vectora.chat.v1.ThreadService/CreateThread
    POST /vectora.chat.v1.ThreadService/GetThread
    POST /vectora.chat.v1.ThreadService/ListThreads
    POST /vectora.chat.v1.ThreadService/DeleteThread
    POST /vectora.chat.v1.ThreadService/GetHistory

Endpoints REST de rewind (A.2):
    GET  /threads/{thread_id}/checkpoints  — lista checkpoints de turno
    POST /threads/{thread_id}/rewind       — restaura workspace para checkpoint

Persiste no mesmo banco SQLite que o chat TUI usa, via AsyncSqliteSaver
+ tabelas vectora_sessions / vectora_checkpoint_artifacts.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from src.api.schemas import (
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


def _user_id(request: Request) -> str:
    """Extrai o user_id do request autenticado, ou 'local' em modo CLI."""
    user = getattr(request.state, "user", None)
    if user is not None and getattr(user, "id", None):
        return str(user.id)
    return "local"


# ---------------------------------------------------------------------------
# Lazy DB loader
# ---------------------------------------------------------------------------

_db_conn: Any = None


async def _ensure_schema(db: Any) -> None:
    """Cria as tabelas do banco de checkpoints/sessões se não existirem.

    Idempotente. Exportada para que o ``_lifespan`` do server possa chamar
    no startup, garantindo que as tabelas existam antes do primeiro request —
    evita race com o ``AsyncSqliteSaver`` do LangGraph que abre o mesmo
    arquivo ``~/.vectora/checkpoints.db``.

    Tabelas gerenciadas:
    - ``vectora_sessions`` — metadados de cada thread/sessão.
    - ``vectora_checkpoint_artifacts`` — metadados dos snapshots de rewind (A.2).
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
    await db.execute("""
        CREATE TABLE IF NOT EXISTS vectora_checkpoint_artifacts (
            id              TEXT PRIMARY KEY,
            thread_id       TEXT NOT NULL,
            checkpoint_id   TEXT NOT NULL,
            strategy        TEXT NOT NULL DEFAULT 'git',
            git_sha         TEXT,
            snapshot_path   TEXT,
            files_touched   TEXT NOT NULL DEFAULT '[]',
            created_at      TEXT NOT NULL
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
async def create_thread(body: CreateThreadRequest, http_request: Request) -> Thread:
    """Cria uma nova thread e a associa ao workspace escolhido pelo usuário.

    Quando `workspace_id` vem vazio, a thread nasce sem workspace — o
    backend cria e atribui o workspace dedicado da sessão
    (`~/Documents/vectora/<thread_id>`) na primeira mensagem, em
    `chat.py::_resolve_workspace_id`.
    """
    db = await _get_db()
    thread_id = str(uuid.uuid4())[:8]
    now = datetime.now(UTC).isoformat()

    workspace_id = body.workspace_id
    if workspace_id:
        from src.services.workspace import workspace_registry

        if workspace_registry.get(workspace_id) is not None:
            workspace_registry.set_active(workspace_id, _user_id(http_request))
        else:
            workspace_id = ""

    extra = json.dumps({"workspace_id": workspace_id} if workspace_id else {})
    await db.execute(
        """
        INSERT INTO vectora_sessions (thread_id, created_at, last_activity, extra)
        VALUES (?, ?, ?, ?)
        """,
        (thread_id, now, now, extra),
    )
    await db.commit()
    return Thread(
        id=thread_id,
        created_at=now,
        updated_at=now,
        title="",
        workspace_id=workspace_id,
    )


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
        from src.graph import get_user_agent

        graph = await get_user_agent()
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


# ---------------------------------------------------------------------------
# Rewind — A.2b: schema + endpoints REST
# ---------------------------------------------------------------------------


class CheckpointArtifact(BaseModel):
    """Metadados de um snapshot de rewind gravado para uma thread."""

    id: str
    thread_id: str
    checkpoint_id: str
    strategy: str
    git_sha: str | None
    snapshot_path: str | None
    files_touched: list[str]
    created_at: str


class CheckpointsResponse(BaseModel):
    checkpoints: list[CheckpointArtifact]


class RewindRequest(BaseModel):
    checkpoint_id: str


class RewindResponse(BaseModel):
    status: str
    message: str = ""


@router.get("/threads/{thread_id}/checkpoints", response_model=CheckpointsResponse)
async def list_thread_checkpoints(thread_id: str) -> CheckpointsResponse:
    """Lista os checkpoints de rewind gravados para uma thread.

    Retorna apenas artefatos com ``strategy='git'`` ou ``strategy='snapshot'``
    associados a turnos completos (gravados pelo orchestrator após cada turno).
    A filtragem por ``kind='turn'`` via metadados LangGraph é feita pelo
    orchestrator ao gravar — aqui lemos apenas o que está em
    ``vectora_checkpoint_artifacts``.
    """
    db = await _get_db()
    async with db.execute(
        "SELECT id, thread_id, checkpoint_id, strategy, git_sha, snapshot_path, "
        "files_touched, created_at "
        "FROM vectora_checkpoint_artifacts "
        "WHERE thread_id = ? ORDER BY created_at DESC",
        (thread_id,),
    ) as cur:
        rows = await cur.fetchall()

    return CheckpointsResponse(
        checkpoints=[
            CheckpointArtifact(
                id=r[0],
                thread_id=r[1],
                checkpoint_id=r[2],
                strategy=r[3],
                git_sha=r[4],
                snapshot_path=r[5],
                files_touched=json.loads(r[6] or "[]"),
                created_at=r[7],
            )
            for r in rows
        ]
    )


@router.post("/threads/{thread_id}/rewind", response_model=RewindResponse)
async def rewind_thread(
    thread_id: str,
    body: RewindRequest,
    workspace_id: Annotated[str, Query()] = "",
) -> RewindResponse:
    """Restaura o workspace para o estado do checkpoint indicado.

    Requer que o ``workspace_id`` seja passado via query param (ou seja
    encontrado no banco pela thread) e que o workspace seja um repositório git.
    O mutex do workspace é adquirido durante a restauração — bloqueia escritas
    concorrentes de tools. Retorna 409 se o workspace estiver ocupado.

    Passos:
    1. Busca o artefato pelo ``checkpoint_id`` na tabela.
    2. Obtém o workspace via registry.
    3. Adquire ``acquire_workspace_lock(workspace_id, thread_id)``.
    4. Chama ``restore_git_checkpoint(repo, git_sha)``.
    """
    db = await _get_db()
    async with db.execute(
        "SELECT id, git_sha, snapshot_path, strategy "
        "FROM vectora_checkpoint_artifacts "
        "WHERE thread_id = ? AND checkpoint_id = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (thread_id, body.checkpoint_id),
    ) as cur:
        row = await cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Checkpoint {body.checkpoint_id!r} não encontrado para a thread.",
        )

    _artifact_id, git_sha, _snapshot_path, strategy = row

    # Resolve workspace: query param > banco
    wid = workspace_id or ""
    if not wid:
        async with db.execute(
            "SELECT extra FROM vectora_sessions WHERE thread_id = ?",
            (thread_id,),
        ) as cur2:
            session_row = await cur2.fetchone()
        if session_row:
            try:
                wid = json.loads(session_row[0] or "{}").get("workspace_id", "")
            except Exception:
                wid = ""

    if not wid:
        raise HTTPException(
            status_code=422,
            detail="workspace_id é obrigatório para o rewind (passe via query param).",
        )

    from src.services.workspace import (
        WorkspaceLockTimeoutError,
        acquire_workspace_lock,
        workspace_registry,
    )

    ws = workspace_registry.get(wid)
    if ws is None:
        raise HTTPException(
            status_code=404, detail=f"Workspace {wid!r} não encontrado."
        )

    if strategy == "git":
        if not git_sha:
            raise HTTPException(
                status_code=422, detail="Artefato de checkpoint sem git_sha."
            )
        try:
            import git as gitpy

            repo = gitpy.Repo(ws.cwd, search_parent_directories=True)
        except Exception as exc:
            raise HTTPException(
                status_code=422, detail=f"Não é um repositório git: {exc}"
            ) from exc

        try:
            async with acquire_workspace_lock(wid, thread_id, timeout=5.0):
                from src.services.checkpoint import restore_git_checkpoint

                result = restore_git_checkpoint(repo, git_sha)
        except WorkspaceLockTimeoutError as lock_exc:
            raise HTTPException(
                status_code=409,
                detail="Workspace ocupado por outra operação — tente novamente em instantes.",
            ) from lock_exc
        if result["status"] != "ok":
            raise HTTPException(
                status_code=500, detail=result.get("message", "Falha no restore.")
            )
    elif strategy == "snapshot":
        if not _snapshot_path:
            raise HTTPException(
                status_code=422,
                detail="Artefato de checkpoint sem snapshot_path.",
            )
        try:
            async with acquire_workspace_lock(wid, thread_id, timeout=5.0):
                from src.services.checkpoint import restore_snapshot_checkpoint

                result = restore_snapshot_checkpoint(_snapshot_path, ws.cwd)
        except WorkspaceLockTimeoutError as lock_exc:
            raise HTTPException(
                status_code=409,
                detail="Workspace ocupado por outra operação — tente novamente em instantes.",
            ) from lock_exc
        if result["status"] != "ok":
            raise HTTPException(
                status_code=500, detail=result.get("message", "Falha no restore.")
            )
    else:
        raise HTTPException(
            status_code=422,
            detail=f"Estratégia de checkpoint {strategy!r} ainda não suportada pelo rewind.",
        )

    return RewindResponse(status="ok")


# ---------------------------------------------------------------------------
# C.27 — Activity endpoint: arquivos tocados + resumo de tool calls
# ---------------------------------------------------------------------------


class ActivityResponse(BaseModel):
    files_touched: list[str]
    tool_call_counts: dict[str, int]
    turn_count: int


@router.get("/threads/{thread_id}/activity", response_model=ActivityResponse)
async def thread_activity(thread_id: str) -> ActivityResponse:
    """Retorna um resumo da atividade da thread: arquivos modificados e
    contagem de tool calls agrupados por nome.

    Consolida ``files_touched`` de todos os checkpoints de turno da thread.
    """
    db = await _get_db()

    # Coleta files_touched de todos os checkpoints da thread
    async with db.execute(
        "SELECT files_touched FROM vectora_checkpoint_artifacts WHERE thread_id = ?",
        (thread_id,),
    ) as cur:
        ft_rows = await cur.fetchall()

    all_files: list[str] = []
    for (ft_json,) in ft_rows:
        try:
            all_files.extend(json.loads(ft_json or "[]"))
        except Exception:
            pass
    unique_files = sorted(set(all_files))

    # Contagem de turnos (número de checkpoints)
    async with db.execute(
        "SELECT COUNT(*) FROM vectora_checkpoint_artifacts WHERE thread_id = ?",
        (thread_id,),
    ) as cur:
        turn_count_row = await cur.fetchone()
    turn_count: int = turn_count_row[0] if turn_count_row else 0

    # tool_call_counts: derivado de files_touched por convenção (sem acesso ao
    # grafo LangGraph aqui). Expandir em iterações futuras via VectoraTracer.
    return ActivityResponse(
        files_touched=unique_files,
        tool_call_counts={},
        turn_count=turn_count,
    )
