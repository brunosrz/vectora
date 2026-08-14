"""``PostgresSessionStore`` — persistência simplificada de sessões/mensagens
sobre ``asyncpg``.

Mesma semântica/contrato de ``SessionStore``
(``backend/persistence/native/session_store.py``) — só os tipos de coluna e
a sintaxe SQL mudam (``$1``/``$2`` de placeholder, ``BIGSERIAL``,
``ON CONFLICT``). Ver a docstring de ``session_store.py`` pra fork via
``parent_message_id`` e o invariante de HITL sobrevivendo a restart via
``pending_approvals``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from backend.vtypes.message import VMessage

if TYPE_CHECKING:
    import asyncpg

_SETUP_SQL = """
CREATE TABLE IF NOT EXISTS vectora_sessions (
    thread_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    workspace_id TEXT,
    parent_thread_id TEXT,
    mode TEXT NOT NULL,
    permission_mode TEXT NOT NULL DEFAULT 'ask',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vectora_messages (
    id BIGSERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES vectora_sessions(thread_id),
    parent_message_id BIGINT,
    role TEXT NOT NULL,
    content_json TEXT NOT NULL,
    tool_calls_json TEXT,
    tool_call_id TEXT,
    name TEXT,
    is_branch_head BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_vectora_messages_thread
    ON vectora_messages(thread_id, id);
CREATE TABLE IF NOT EXISTS vectora_pending_approvals (
    thread_id TEXT PRIMARY KEY REFERENCES vectora_sessions(thread_id),
    interrupt_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_call_id TEXT NOT NULL,
    args_json TEXT NOT NULL,
    reasoning TEXT,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _message_to_row(
    msg: VMessage,
) -> tuple[str, str, str | None, str | None, str | None]:
    data = msg.to_dict()
    content_json = json.dumps(data["content"], ensure_ascii=False)
    tool_calls_json = (
        json.dumps(data["tool_calls"], ensure_ascii=False)
        if data["tool_calls"]
        else None
    )
    return (
        data["role"],
        content_json,
        tool_calls_json,
        data["tool_call_id"],
        data["name"],
    )


def _row_to_message(row: Any) -> VMessage:
    data = {
        "role": row["role"],
        "content": json.loads(row["content_json"]),
        "tool_calls": (
            json.loads(row["tool_calls_json"]) if row["tool_calls_json"] else []
        ),
        "tool_call_id": row["tool_call_id"],
        "name": row["name"],
        "finish_reason": None,
        "is_error": False,
    }
    return VMessage.from_dict(data)


class PostgresSessionStore:
    """Persistência async sobre um ``asyncpg.Pool`` compartilhado (mesmo pool
    de ``backend.storage.factory.get_pg_pool()``)."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._is_setup = False

    async def setup(self) -> None:
        if self._is_setup:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(_SETUP_SQL)
        self._is_setup = True

    async def create_session(
        self,
        thread_id: str,
        *,
        user_id: str,
        workspace_id: str | None = None,
        parent_thread_id: str | None = None,
        mode: str = "chat",
        permission_mode: str = "ask",
    ) -> None:
        await self.setup()
        agora = _now()
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO vectora_sessions (thread_id, user_id, workspace_id, "
                "parent_thread_id, mode, permission_mode, created_at, updated_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8) "
                "ON CONFLICT (thread_id) DO NOTHING",
                thread_id,
                user_id,
                workspace_id,
                parent_thread_id,
                mode,
                permission_mode,
                agora,
                agora,
            )

    async def append_message(
        self, thread_id: str, msg: VMessage, *, parent_message_id: int | None = None
    ) -> int:
        """Persiste `msg` e devolve o `id` gerado — mesmo invariante de fork
        de `SessionStore.append_message` (a mensagem nova vira a ponta ativa
        da branch, sem apagar nenhuma mensagem existente)."""
        await self.setup()
        agora = _now()
        role, content_json, tool_calls_json, tool_call_id, name = _message_to_row(msg)
        async with self._pool.acquire() as conn, conn.transaction():
            new_id = await conn.fetchval(
                "INSERT INTO vectora_messages (thread_id, parent_message_id, role, "
                "content_json, tool_calls_json, tool_call_id, name, is_branch_head, "
                "created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, $8) "
                "RETURNING id",
                thread_id,
                parent_message_id,
                role,
                content_json,
                tool_calls_json,
                tool_call_id,
                name,
                agora,
            )
            await conn.execute(
                "UPDATE vectora_messages SET is_branch_head = FALSE "
                "WHERE thread_id = $1 AND id != $2",
                thread_id,
                new_id,
            )
            await conn.execute(
                "UPDATE vectora_sessions SET updated_at = $1 WHERE thread_id = $2",
                agora,
                thread_id,
            )
        return int(new_id)

    async def get_branch_head_id(self, thread_id: str) -> int | None:
        """`id` da ponta ativa da branch, ou `None` se a thread ainda não
        tem mensagem — mesmo papel de `SessionStore.get_branch_head_id`."""
        await self.setup()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM vectora_messages WHERE thread_id = $1 "
                "AND is_branch_head = TRUE ORDER BY id DESC LIMIT 1",
                thread_id,
            )
        return row["id"] if row is not None else None

    async def get_history(
        self, thread_id: str, *, up_to_message_id: int | None = None
    ) -> list[VMessage]:
        """Reconstrói a cadeia seguindo `parent_message_id` — mesmo
        invariante de `SessionStore.get_history` (reload/resume por
        reconstrução, nunca por estado só em memória)."""
        await self.setup()
        async with self._pool.acquire() as conn:
            if up_to_message_id is not None:
                start_id: int | None = up_to_message_id
            else:
                row = await conn.fetchrow(
                    "SELECT id FROM vectora_messages WHERE thread_id = $1 "
                    "AND is_branch_head = TRUE ORDER BY id DESC LIMIT 1",
                    thread_id,
                )
                start_id = row["id"] if row is not None else None

            cadeia: list[Any] = []
            current_id = start_id
            while current_id is not None:
                row = await conn.fetchrow(
                    "SELECT id, parent_message_id, role, content_json, "
                    "tool_calls_json, tool_call_id, name FROM vectora_messages "
                    "WHERE thread_id = $1 AND id = $2",
                    thread_id,
                    current_id,
                )
                if row is None:
                    break
                cadeia.append(row)
                current_id = row["parent_message_id"]

        cadeia.reverse()
        return [_row_to_message(row) for row in cadeia]

    async def set_branch_head(self, thread_id: str, message_id: int) -> None:
        await self.setup()
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(
                "UPDATE vectora_messages SET is_branch_head = FALSE "
                "WHERE thread_id = $1",
                thread_id,
            )
            await conn.execute(
                "UPDATE vectora_messages SET is_branch_head = TRUE "
                "WHERE thread_id = $1 AND id = $2",
                thread_id,
                message_id,
            )

    async def get_pending_approval(self, thread_id: str) -> dict[str, Any] | None:
        await self.setup()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT interrupt_id, tool_name, tool_call_id, args_json, "
                "reasoning, created_at FROM vectora_pending_approvals "
                "WHERE thread_id = $1",
                thread_id,
            )
        if row is None:
            return None
        return {
            "interrupt_id": row["interrupt_id"],
            "tool_name": row["tool_name"],
            "tool_call_id": row["tool_call_id"],
            "args": json.loads(row["args_json"]),
            "reasoning": row["reasoning"],
            "created_at": row["created_at"],
        }

    async def put_pending_approval(
        self,
        thread_id: str,
        *,
        interrupt_id: str,
        tool_name: str,
        tool_call_id: str,
        args: dict[str, Any],
        reasoning: str | None = None,
    ) -> None:
        await self.setup()
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO vectora_pending_approvals (thread_id, interrupt_id, "
                "tool_name, tool_call_id, args_json, reasoning, created_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7) "
                "ON CONFLICT (thread_id) DO UPDATE SET "
                "interrupt_id = EXCLUDED.interrupt_id, "
                "tool_name = EXCLUDED.tool_name, "
                "tool_call_id = EXCLUDED.tool_call_id, "
                "args_json = EXCLUDED.args_json, "
                "reasoning = EXCLUDED.reasoning, "
                "created_at = EXCLUDED.created_at",
                thread_id,
                interrupt_id,
                tool_name,
                tool_call_id,
                json.dumps(args, ensure_ascii=False),
                reasoning,
                _now(),
            )

    async def clear_pending_approval(self, thread_id: str) -> None:
        await self.setup()
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM vectora_pending_approvals WHERE thread_id = $1",
                thread_id,
            )
