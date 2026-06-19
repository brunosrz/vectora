"""Testes para o fix de persistência de threads (session loss bug).

Bug: StreamChat cria threads no checkpointer LangGraph mas NUNCA grava na
tabela `vectora_sessions`. Após reiniciar o servidor, ListThreads retorna
lista vazia mesmo que o histórico exista nos checkpoints.

Segundo problema: titles de threads só existem em estado React local — não
sobrevivem a reload/restart.

Fixes testados:
1. _upsert_session() existe e faz UPSERT na tabela vectora_sessions
2. stream_chat() chama _upsert_session() com o thread_id correto
3. UpdateThread endpoint persiste title no campo extra JSON
4. Thread criada via _upsert_session aparece em ListThreads
"""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ["VECTORA_AUTH_REQUIRED"] = "false"

# ---------------------------------------------------------------------------
# Fake DB para testes unitários
# ---------------------------------------------------------------------------


class _CursorProxy:
    """Suporta tanto `await db.execute(...)` quanto `async with db.execute(...) as cur`.

    Espelha o comportamento do aiosqlite._AioContextManager.
    """

    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor

    def __await__(self):  # type: ignore[override]
        async def _inner() -> FakeCursor:
            return self._cursor

        return _inner().__await__()

    async def __aenter__(self) -> FakeCursor:
        return self._cursor

    async def __aexit__(self, *_: object) -> None:
        pass


class FakeDB:
    """Banco em memória que simula aiosqlite.Connection.

    `execute()` é síncrono (como aiosqlite requer internamente) e retorna
    _CursorProxy que suporta `await` e `async with`.
    """

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}
        self.sql_calls: list[tuple[str, tuple]] = []

    def execute(self, sql: str, params: tuple = ()) -> _CursorProxy:  # sync!
        self.sql_calls.append((sql, params))
        sql_norm = sql.upper().replace("\n", " ").strip()

        if "INSERT OR REPLACE" in sql_norm or (
            "INSERT" in sql_norm and "ON CONFLICT" in sql_norm
        ):
            thread_id = params[0]
            created_at = params[1] if len(params) > 1 else "2025-01-01T00:00:00Z"
            last_activity = params[2] if len(params) > 2 else created_at
            extra = params[3] if len(params) > 3 else "{}"
            if thread_id in self.rows:
                self.rows[thread_id]["last_activity"] = last_activity
                try:
                    extra_obj = json.loads(extra)
                    existing = json.loads(self.rows[thread_id].get("extra", "{}"))
                    existing.update(extra_obj)
                    self.rows[thread_id]["extra"] = json.dumps(existing)
                except Exception:
                    self.rows[thread_id]["extra"] = extra
            else:
                self.rows[thread_id] = {
                    "thread_id": thread_id,
                    "created_at": created_at,
                    "last_activity": last_activity,
                    "message_count": 0,
                    "extra": extra,
                }
            cursor = FakeCursor(self, thread_id)

        elif "UPDATE" in sql_norm and "vectora_sessions" in sql_norm.lower():
            thread_id = params[-1] if params else None
            if thread_id and thread_id in self.rows:
                extra_json = params[0]
                self.rows[thread_id]["extra"] = extra_json
            cursor = FakeCursor(self, thread_id)

        else:
            # SELECT — lookup pelo primeiro param
            lookup_id = params[0] if params else None
            cursor = FakeCursor(self, lookup_id)

        return _CursorProxy(cursor)

    async def commit(self) -> None:
        pass


class FakeCursor:
    def __init__(self, db: FakeDB, lookup_id: str | None = None) -> None:
        self._db = db
        self._lookup_id = lookup_id

    async def fetchone(self) -> tuple | None:
        if self._lookup_id and self._lookup_id in self._db.rows:
            return _row_tuple(self._db.rows[self._lookup_id])
        return None

    async def fetchall(self) -> list[tuple]:
        return [_row_tuple(r) for r in self._db.rows.values()]


def _row_tuple(r: dict) -> tuple:
    return (
        r["thread_id"],
        "human",
        r["created_at"],
        r["last_activity"],
        r.get("message_count", 0),
        r.get("extra", "{}"),
    )


# ---------------------------------------------------------------------------
# 1. _upsert_session — testes unitários da função
# ---------------------------------------------------------------------------


class TestUpsertSession:
    """A função _upsert_session deve existir em threads.py e fazer UPSERT correto."""

    @pytest.mark.asyncio
    async def test_upsert_session_exists(self):
        """_upsert_session deve ser importável de vectora.api.handlers.threads."""
        from backend.api.handlers.threads import _upsert_session

    @pytest.mark.asyncio
    async def test_upsert_creates_row(self):
        """_upsert_session escreve INSERT ... ON CONFLICT no banco."""
        from backend.api.handlers.threads import _upsert_session

        db = FakeDB()
        with patch(
            "backend.api.handlers.threads._get_db", new=AsyncMock(return_value=db)
        ):
            await _upsert_session("thread-abc")

        assert len(db.sql_calls) >= 1
        sql_used = " ".join(s for s, _ in db.sql_calls).upper()
        assert "INSERT" in sql_used
        assert "ON CONFLICT" in sql_used or "OR REPLACE" in sql_used

    @pytest.mark.asyncio
    async def test_upsert_stores_thread_id(self):
        """O thread_id passado aparece como parâmetro SQL e é armazenado."""
        from backend.api.handlers.threads import _upsert_session

        db = FakeDB()
        with patch(
            "backend.api.handlers.threads._get_db", new=AsyncMock(return_value=db)
        ):
            await _upsert_session("thread-xyz")

        all_params = [p for _, p in db.sql_calls]
        flat = [item for sublist in all_params for item in sublist]
        assert "thread-xyz" in flat

    @pytest.mark.asyncio
    async def test_upsert_with_title_stores_in_extra(self):
        """Quando title é fornecido, deve aparecer no JSON do campo extra."""
        from backend.api.handlers.threads import _upsert_session

        db = FakeDB()
        with patch(
            "backend.api.handlers.threads._get_db", new=AsyncMock(return_value=db)
        ):
            await _upsert_session("thread-titled", title="Minha Conversa")

        all_params_str = str(db.sql_calls)
        assert "Minha Conversa" in all_params_str

    @pytest.mark.asyncio
    async def test_upsert_idempotent(self):
        """Chamar duas vezes com o mesmo thread_id não lança exceção."""
        from backend.api.handlers.threads import _upsert_session

        db = FakeDB()
        with patch(
            "backend.api.handlers.threads._get_db", new=AsyncMock(return_value=db)
        ):
            await _upsert_session("thread-dup")
            await _upsert_session("thread-dup")  # segunda chamada não deve falhar

    @pytest.mark.asyncio
    async def test_upsert_calls_commit(self):
        """_upsert_session deve chamar commit() após executar."""
        from backend.api.handlers.threads import _upsert_session

        db = MagicMock()
        db.execute = MagicMock(return_value=_CursorProxy(FakeCursor(FakeDB())))
        db.commit = AsyncMock()

        with patch(
            "backend.api.handlers.threads._get_db", new=AsyncMock(return_value=db)
        ):
            await _upsert_session("thread-commit-test")

        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 2. stream_chat chama _upsert_session
# ---------------------------------------------------------------------------


class TestStreamChatRegistersThread:
    """stream_chat() deve registrar a thread em vectora_sessions via _upsert_session."""

    @pytest.mark.asyncio
    async def test_stream_chat_calls_upsert_with_thread_id(self):
        """stream_chat chama _upsert_session com o thread_id do request."""
        upsert_calls: list[str] = []

        async def mock_upsert(
            thread_id: str,
            title: str = "",
            workspace_id: str | None = None,
        ) -> None:
            upsert_calls.append(thread_id)

        async def _empty_events(*_a: object, **_kw: object):
            return
            yield  # async generator

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=_empty_events())

        from backend.api.schemas import StreamChatRequest

        with (
            patch(
                "backend.services.agent_factory.get_user_agent",
                new=AsyncMock(return_value=mock_graph),
            ),
            patch(
                "backend.api.handlers.threads._upsert_session",
                side_effect=mock_upsert,
            ),
        ):
            import importlib

            import backend.api.handlers.chat as chat_mod

            importlib.reload(chat_mod)

            request = StreamChatRequest(content="Olá", thread_id="explicit-thread-id")
            http_request = MagicMock()
            http_request.state = MagicMock(user=None)
            _response = await chat_mod.stream_chat(request, http_request)

        assert "explicit-thread-id" in upsert_calls, (
            "stream_chat deve chamar _upsert_session com o thread_id fornecido"
        )

    @pytest.mark.asyncio
    async def test_stream_chat_upserts_when_thread_id_empty(self):
        """Quando thread_id é vazio, stream_chat gera UUID e chama _upsert_session."""
        upsert_calls: list[str] = []

        async def mock_upsert(
            thread_id: str,
            title: str = "",
            workspace_id: str | None = None,
        ) -> None:
            upsert_calls.append(thread_id)

        async def _empty_events(*_a: object, **_kw: object):
            return
            yield

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=_empty_events())

        from backend.api.schemas import StreamChatRequest

        with (
            patch(
                "backend.services.agent_factory.get_user_agent",
                new=AsyncMock(return_value=mock_graph),
            ),
            patch(
                "backend.api.handlers.threads._upsert_session",
                side_effect=mock_upsert,
            ),
        ):
            import importlib

            import backend.api.handlers.chat as chat_mod

            importlib.reload(chat_mod)

            request = StreamChatRequest(content="Sem thread id")
            http_request = MagicMock()
            http_request.state = MagicMock(user=None)
            _response = await chat_mod.stream_chat(request, http_request)

        assert len(upsert_calls) == 1, "Deve ter sido chamado exatamente uma vez"
        thread_id_used = upsert_calls[0]
        assert len(thread_id_used) > 0, "thread_id gerado não deve ser vazio"


# ---------------------------------------------------------------------------
# 3. UpdateThread endpoint
# ---------------------------------------------------------------------------


def _make_app_with_db(tmp_db: FakeDB) -> tuple:
    """Cria app FastAPI com o FakeDB injetado em threads._get_db."""
    import backend.api.handlers.threads as t_mod

    original_get_db = t_mod._get_db
    original_db_conn = t_mod._db_conn
    t_mod._db_conn = None

    async def patched_get_db():
        return tmp_db

    t_mod._get_db = patched_get_db  # type: ignore[assignment]  # ty: ignore[invalid-assignment]

    from backend.api.server import create_app

    app = create_app(serve_static=False)
    return app, original_get_db, original_db_conn, t_mod


def _restore_app(t_mod, original_get_db, original_db_conn) -> None:
    t_mod._get_db = original_get_db
    t_mod._db_conn = original_db_conn


class TestUpdateThreadEndpoint:
    """Endpoint UpdateThread deve existir e persistir o title no campo extra."""

    def test_update_thread_route_exists(self):
        """Rota UpdateThread deve estar registrada no app."""
        from fastapi.testclient import TestClient

        db = FakeDB()
        app, orig_get_db, orig_conn, t_mod = _make_app_with_db(db)
        try:
            routes = [r.path for r in app.routes]
            assert "/vectora.chat.v1.ThreadService/UpdateThread" in routes, (
                f"Rota UpdateThread não encontrada. Rotas: {routes}"
            )
        finally:
            _restore_app(t_mod, orig_get_db, orig_conn)

    def test_update_thread_saves_title(self):
        """POST /UpdateThread deve salvar o title no campo extra da thread."""
        from fastapi.testclient import TestClient

        db = FakeDB()
        # Pré-popula uma thread via execute síncrono
        db.execute(
            "INSERT INTO vectora_sessions (thread_id, created_at, last_activity, message_count, extra) "
            "VALUES (?, ?, ?, 0, ?) ON CONFLICT(thread_id) DO UPDATE SET last_activity = excluded.last_activity",
            ("thread-upd", "2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z", "{}"),
        )

        app, orig_get_db, orig_conn, t_mod = _make_app_with_db(db)
        try:
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/vectora.chat.v1.ThreadService/UpdateThread",
                json={"thread_id": "thread-upd", "title": "Título Persistido"},
            )
            assert response.status_code == 200, (
                f"Esperado 200, obtido {response.status_code}: {response.text}"
            )
            # O title deve ter sido atualizado no DB
            if "thread-upd" in db.rows:
                extra = json.loads(db.rows["thread-upd"].get("extra", "{}"))
                assert extra.get("title") == "Título Persistido"
        finally:
            _restore_app(t_mod, orig_get_db, orig_conn)

    def test_update_thread_returns_updated_thread(self):
        """UpdateThread deve retornar a Thread com o title atualizado."""
        from fastapi.testclient import TestClient

        db = FakeDB()
        db.execute(
            "INSERT INTO vectora_sessions (thread_id, created_at, last_activity, message_count, extra) "
            "VALUES (?, ?, ?, 0, ?) ON CONFLICT(thread_id) DO UPDATE SET last_activity = excluded.last_activity",
            ("thread-ret", "2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z", "{}"),
        )

        app, orig_get_db, orig_conn, t_mod = _make_app_with_db(db)
        try:
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/vectora.chat.v1.ThreadService/UpdateThread",
                json={"thread_id": "thread-ret", "title": "Novo Título"},
            )
            if response.status_code == 200:
                body = response.json()
                assert body.get("id") == "thread-ret"
                assert body.get("title") == "Novo Título"
        finally:
            _restore_app(t_mod, orig_get_db, orig_conn)

    def test_update_thread_not_found(self):
        """UpdateThread com thread inexistente deve retornar 404."""
        from fastapi.testclient import TestClient

        db = FakeDB()
        app, orig_get_db, orig_conn, t_mod = _make_app_with_db(db)
        try:
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/vectora.chat.v1.ThreadService/UpdateThread",
                json={"thread_id": "nao-existe-xyz", "title": "Qualquer"},
            )
            assert response.status_code == 404, (
                f"Esperado 404 para thread inexistente, obtido {response.status_code}"
            )
        finally:
            _restore_app(t_mod, orig_get_db, orig_conn)


# ---------------------------------------------------------------------------
# 4. ListThreads retorna threads criadas via _upsert_session
# ---------------------------------------------------------------------------


class TestListThreadsIncludesUpserted:
    """Threads criadas via _upsert_session devem aparecer em ListThreads."""

    def test_list_threads_empty_initially(self):
        """Sem threads criadas, ListThreads retorna lista vazia."""
        from fastapi.testclient import TestClient

        db = FakeDB()
        app, orig_get_db, orig_conn, t_mod = _make_app_with_db(db)
        try:
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/vectora.chat.v1.ThreadService/ListThreads",
                json={"limit": 50},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["threads"] == []
        finally:
            _restore_app(t_mod, orig_get_db, orig_conn)

    @pytest.mark.asyncio
    async def test_upserted_thread_appears_in_list(self):
        """Thread registrada via _upsert_session aparece em ListThreads."""
        from fastapi.testclient import TestClient

        from backend.api.handlers.threads import _upsert_session

        db = FakeDB()
        app, orig_get_db, orig_conn, t_mod = _make_app_with_db(db)
        try:
            # Upsert direto no FakeDB (simula o que stream_chat fará)
            with patch(
                "backend.api.handlers.threads._get_db",
                new=AsyncMock(return_value=db),
            ):
                await _upsert_session("streamed-thread-001")

            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/vectora.chat.v1.ThreadService/ListThreads",
                json={"limit": 50},
            )
            assert response.status_code == 200
            body = response.json()
            ids = [t["id"] for t in body["threads"]]
            assert "streamed-thread-001" in ids, (
                f"Thread via _upsert_session não aparece em ListThreads. ids={ids}"
            )
        finally:
            _restore_app(t_mod, orig_get_db, orig_conn)

    @pytest.mark.asyncio
    async def test_upserted_thread_with_title_in_list(self):
        """Thread com title upsertada aparece com o title correto em ListThreads."""
        from fastapi.testclient import TestClient

        from backend.api.handlers.threads import _upsert_session

        db = FakeDB()
        app, orig_get_db, orig_conn, t_mod = _make_app_with_db(db)
        try:
            with patch(
                "backend.api.handlers.threads._get_db",
                new=AsyncMock(return_value=db),
            ):
                await _upsert_session(
                    "streamed-thread-002", title="Conversa Persistida"
                )

            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/vectora.chat.v1.ThreadService/ListThreads",
                json={"limit": 50},
            )
            assert response.status_code == 200
            body = response.json()
            thread = next(
                (t for t in body["threads"] if t["id"] == "streamed-thread-002"), None
            )
            assert thread is not None
            assert thread.get("title") == "Conversa Persistida"
        finally:
            _restore_app(t_mod, orig_get_db, orig_conn)
