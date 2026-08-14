"""``SessionStore`` — persistência simplificada de sessões/mensagens sobre
``aiosqlite``.

Para o motor de conversa nativo, substitui o schema de checkpoint do
LangGraph (``VectoraSqliteSaver``, ``sqlite_checkpointer.py``) por um
schema append-only simples: ``sessions`` + ``messages`` +
``pending_approvals``. O protocolo de checkpoint (``channel_versions``,
``pending_writes``, ``checkpoint_id`` por superstep) existe pra reconstituir
um grafo multi-nó em qualquer superstep — sem grafo declarativo, isso é peso
morto que o loop nativo não precisa carregar.

O que o Vectora precisa e o schema minimalista do Hermes não modela
sobrevive por outro caminho, mais simples que branch de checkpoint:

- **Fork de conversa** (editar mensagem/regenerar) via ``parent_message_id``
  — a mensagem nova aponta pro ponto da cadeia de onde diverge; mensagens
  da branch anterior nunca são apagadas, só deixam de ser ``is_branch_head``.
- **HITL sobrevivendo a restart** via ``pending_approvals`` — persistido
  IMEDIATA e SINCRONAMENTE antes de qualquer espera, nunca só em memória
  de processo.

Coexiste com ``VectoraSqliteSaver`` até o loop de conversa nativo existir
e cortar o dispatch pro motor nativo — sem consumidor de produção ainda.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from backend.vtypes.message import VMessage

if TYPE_CHECKING:
    from backend.storage.sqlite.pool import AsyncConnectionPool

_SETUP_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    thread_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    workspace_id TEXT,
    parent_thread_id TEXT,
    mode TEXT NOT NULL,
    permission_mode TEXT NOT NULL DEFAULT 'ask',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL REFERENCES sessions(thread_id),
    parent_message_id INTEGER,
    role TEXT NOT NULL,
    content_json TEXT NOT NULL,
    tool_calls_json TEXT,
    tool_call_id TEXT,
    name TEXT,
    is_branch_head INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_messages_thread ON messages(thread_id, id);
CREATE TABLE IF NOT EXISTS pending_approvals (
    thread_id TEXT PRIMARY KEY REFERENCES sessions(thread_id),
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
    _id, _parent, role, content_json, tool_calls_json, tool_call_id, name = row
    data = {
        "role": role,
        "content": json.loads(content_json),
        "tool_calls": json.loads(tool_calls_json) if tool_calls_json else [],
        "tool_call_id": tool_call_id,
        "name": name,
        "finish_reason": None,
        "is_error": False,
    }
    return VMessage.from_dict(data)


class SessionStore:
    """Persistência async sobre um ``AsyncConnectionPool`` (aiosqlite) com os
    PRAGMAs de hardening já aplicados por conexão — mesmo pool usado por
    ``VectoraSqliteSaver``."""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool
        self._is_setup = False

    async def setup(self) -> None:
        """Cria as tabelas se não existirem. Idempotente — chamado
        automaticamente por todo método público antes de qualquer query."""
        if self._is_setup:
            return
        async with self._pool.acquire() as conn:
            await conn.executescript(_SETUP_SQL)
            await conn.commit()
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
                "INSERT OR IGNORE INTO sessions (thread_id, user_id, workspace_id, "
                "parent_thread_id, mode, permission_mode, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    thread_id,
                    user_id,
                    workspace_id,
                    parent_thread_id,
                    mode,
                    permission_mode,
                    agora,
                    agora,
                ),
            )
            await conn.commit()

    async def append_message(
        self, thread_id: str, msg: VMessage, *, parent_message_id: int | None = None
    ) -> int:
        """Persiste `msg` e devolve o `id` gerado. A mensagem nova vira a
        ponta ativa da branch (`is_branch_head`); se `parent_message_id`
        aponta pra um nó no meio da cadeia (fork — editar/regenerar), a
        branch divergente anterior nunca é apagada, só deixa de ser a
        ponta ativa dessa thread."""
        await self.setup()
        agora = _now()
        role, content_json, tool_calls_json, tool_call_id, name = _message_to_row(msg)
        async with self._pool.acquire() as conn:
            cur = await conn.execute(
                "INSERT INTO messages (thread_id, parent_message_id, role, "
                "content_json, tool_calls_json, tool_call_id, name, is_branch_head, "
                "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)",
                (
                    thread_id,
                    parent_message_id,
                    role,
                    content_json,
                    tool_calls_json,
                    tool_call_id,
                    name,
                    agora,
                ),
            )
            new_id = cur.lastrowid
            if new_id is None:
                erro = "INSERT em `messages` não gerou lastrowid"
                raise RuntimeError(erro)
            await conn.execute(
                "UPDATE messages SET is_branch_head = 0 "
                "WHERE thread_id = ? AND id != ?",
                (thread_id, new_id),
            )
            await conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE thread_id = ?",
                (agora, thread_id),
            )
            await conn.commit()
        return int(new_id)

    async def get_branch_head_id(self, thread_id: str) -> int | None:
        """`id` da mensagem que é a ponta ativa da branch, ou `None` se a
        thread ainda não tem mensagem nenhuma — usado pelo caller (loop de
        conversa nativo) pra encadear `parent_message_id` ao persistir a
        próxima mensagem, sem precisar reler o histórico inteiro só pra
        descobrir o último `id`."""
        await self.setup()
        async with self._pool.acquire() as conn:
            cur = await conn.execute(
                "SELECT id FROM messages WHERE thread_id = ? "
                "AND is_branch_head = 1 ORDER BY id DESC LIMIT 1",
                (thread_id,),
            )
            row = await cur.fetchone()
        return row[0] if row is not None else None

    async def get_history(
        self, thread_id: str, *, up_to_message_id: int | None = None
    ) -> list[VMessage]:
        """Reconstrói a cadeia de mensagens seguindo `parent_message_id` a
        partir da ponta ativa (ou de `up_to_message_id`, pra reler uma
        branch antiga sem apagar o que veio depois) até a raiz — reload/
        resume acontece por reconstrução da persistência, nunca por estado
        mantido só em memória (invariante do loop nativo)."""
        await self.setup()
        async with self._pool.acquire() as conn:
            if up_to_message_id is not None:
                start_id: int | None = up_to_message_id
            else:
                cur = await conn.execute(
                    "SELECT id FROM messages WHERE thread_id = ? "
                    "AND is_branch_head = 1 ORDER BY id DESC LIMIT 1",
                    (thread_id,),
                )
                row = await cur.fetchone()
                start_id = row[0] if row is not None else None

            cadeia: list[Any] = []
            current_id = start_id
            while current_id is not None:
                cur = await conn.execute(
                    "SELECT id, parent_message_id, role, content_json, "
                    "tool_calls_json, tool_call_id, name FROM messages "
                    "WHERE thread_id = ? AND id = ?",
                    (thread_id, current_id),
                )
                row = await cur.fetchone()
                if row is None:
                    break
                cadeia.append(row)
                current_id = row[1]

        cadeia.reverse()
        return [_row_to_message(row) for row in cadeia]

    async def set_branch_head(self, thread_id: str, message_id: int) -> None:
        """Marca `message_id` como a ponta ativa da thread — fork explícito
        (editar mensagem/regenerar) sem apagar nenhuma mensagem existente."""
        await self.setup()
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE messages SET is_branch_head = 0 WHERE thread_id = ?",
                (thread_id,),
            )
            await conn.execute(
                "UPDATE messages SET is_branch_head = 1 WHERE thread_id = ? AND id = ?",
                (thread_id, message_id),
            )
            await conn.commit()

    async def get_pending_approval(self, thread_id: str) -> dict[str, Any] | None:
        await self.setup()
        async with self._pool.acquire() as conn:
            cur = await conn.execute(
                "SELECT interrupt_id, tool_name, tool_call_id, args_json, "
                "reasoning, created_at FROM pending_approvals WHERE thread_id = ?",
                (thread_id,),
            )
            row = await cur.fetchone()
        if row is None:
            return None
        interrupt_id, tool_name, tool_call_id, args_json, reasoning, created_at = row
        return {
            "interrupt_id": interrupt_id,
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "args": json.loads(args_json),
            "reasoning": reasoning,
            "created_at": created_at,
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
        """Persiste IMEDIATA e SINCRONAMENTE a aprovação pendente, antes de
        qualquer espera — HITL sobrevive a restart do backend porque o
        estado nunca vive só em memória."""
        await self.setup()
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO pending_approvals (thread_id, "
                "interrupt_id, tool_name, tool_call_id, args_json, reasoning, "
                "created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    thread_id,
                    interrupt_id,
                    tool_name,
                    tool_call_id,
                    json.dumps(args, ensure_ascii=False),
                    reasoning,
                    _now(),
                ),
            )
            await conn.commit()

    async def clear_pending_approval(self, thread_id: str) -> None:
        await self.setup()
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM pending_approvals WHERE thread_id = ?", (thread_id,)
            )
            await conn.commit()
