"""`reconcile_vectora_sessions` — rede de segurança contra a divergência
entre `vectora_sessions` (o que a sidebar lê) e `sessions.db`/`SessionStore`
(fonte de verdade do motor nativo).

Achado real (2026-09-03): `vectora_sessions` com só 1 linha há semanas
enquanto `sessions.db` tinha dezenas de threads reais, incluindo uma
conversa do dia com 32 mensagens completamente ausente da sidebar. A causa
raiz exata ficou sem confirmação determinística (VECTORA_HOME e o caminho
de upsert de `chat.py` foram descartados por leitura de código), então a
correção é uma reconciliação idempotente que repovoa qualquer divergência
— não depende de saber qual bug específico causou o desalinhamento.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import aiosqlite
import pytest

from backend.api.handlers import threads as th
from backend.persistence.native.session_store import SessionStore
from backend.storage.sqlite.pool import AsyncConnectionPool
from backend.vtypes.message import MessageRole, text_message


@pytest.fixture
async def checkpoints_db() -> AsyncIterator[aiosqlite.Connection]:
    db = await aiosqlite.connect(":memory:")
    await th._ensure_schema(db)
    try:
        yield db
    finally:
        await db.close()


@pytest.fixture
async def session_store(tmp_path) -> AsyncIterator[SessionStore]:
    pool = AsyncConnectionPool(str(tmp_path / "sessions.db"), min_size=1, max_size=2)
    await pool.open()
    store = SessionStore(pool)
    await store.setup()
    try:
        yield store
    finally:
        await pool.close()


@pytest.fixture(autouse=True)
def _wire_stores(
    monkeypatch: pytest.MonkeyPatch,
    checkpoints_db: aiosqlite.Connection,
    session_store: SessionStore,
) -> None:
    async def _fake_get_db() -> aiosqlite.Connection:
        return checkpoints_db

    async def _fake_get_session_store() -> SessionStore:
        return session_store

    monkeypatch.setattr(th, "_get_db", _fake_get_db)
    monkeypatch.setattr(th, "_get_session_store", _fake_get_session_store)


async def _real_thread(
    session_store: SessionStore, thread_id: str, n_messages: int
) -> None:
    await session_store.create_session(thread_id, user_id="alice", mode="code")
    for i in range(n_messages):
        await session_store.append_message(
            thread_id, text_message(MessageRole.USER, f"mensagem {i}")
        )


def _http_request_alice() -> MagicMock:
    request = MagicMock()
    user = MagicMock()
    user.id = "alice"
    request.state = MagicMock(user=user)
    return request


class TestReconcileRepovoaThreadAusente:
    async def test_thread_real_ausente_de_vectora_sessions_e_repovoada(
        self, session_store: SessionStore, checkpoints_db: aiosqlite.Connection
    ) -> None:
        await _real_thread(session_store, "thread-perdida", 32)

        reconciled = await th.reconcile_vectora_sessions()

        assert reconciled == 1
        async with checkpoints_db.execute(
            "SELECT message_count FROM vectora_sessions WHERE thread_id = ?",
            ("thread-perdida",),
        ) as cur:
            row = await cur.fetchone()
        assert row is not None
        assert row[0] == 32

    async def test_thread_repovoada_aparece_em_list_threads(
        self, session_store: SessionStore
    ) -> None:
        await _real_thread(session_store, "thread-perdida", 5)

        await th.reconcile_vectora_sessions()
        result = await th.list_threads(
            th.ListThreadsRequest(limit=50), _http_request_alice()
        )

        assert [t.id for t in result.threads] == ["thread-perdida"]

    async def test_varias_threads_ausentes_todas_repovoadas(
        self, session_store: SessionStore
    ) -> None:
        await _real_thread(session_store, "thread-1", 3)
        await _real_thread(session_store, "thread-2", 7)

        reconciled = await th.reconcile_vectora_sessions()

        assert reconciled == 2


class TestReconcileCorrigeContagemDivergente:
    async def test_message_count_desatualizado_e_corrigido_sem_apagar_extra(
        self, session_store: SessionStore, checkpoints_db: aiosqlite.Connection
    ) -> None:
        await _real_thread(session_store, "thread-1", 10)
        # vectora_sessions já tem a thread, mas com contagem velha (upsert
        # que falhou no meio, ou incremento perdido) e um título já gravado
        # pela UI — a reconciliação corrige a contagem sem tocar no título.
        await th._upsert_session("thread-1", title="Titulo ja existente")
        await checkpoints_db.execute(
            "UPDATE vectora_sessions SET message_count = 1 WHERE thread_id = ?",
            ("thread-1",),
        )
        await checkpoints_db.commit()

        reconciled = await th.reconcile_vectora_sessions()

        assert reconciled == 1
        async with checkpoints_db.execute(
            "SELECT message_count, extra FROM vectora_sessions WHERE thread_id = ?",
            ("thread-1",),
        ) as cur:
            row = await cur.fetchone()
        assert row is not None
        count, extra_json = row
        assert count == 10
        assert json.loads(extra_json)["title"] == "Titulo ja existente"


class TestReconcileNaoMexeEmThreadJaSincronizada:
    async def test_thread_ja_sincronizada_nao_conta_como_reconciliada(
        self, session_store: SessionStore
    ) -> None:
        await _real_thread(session_store, "thread-1", 4)
        await th._upsert_session("thread-1")
        await th._increment_message_count("thread-1")
        await th._increment_message_count("thread-1")
        await th._increment_message_count("thread-1")
        await th._increment_message_count("thread-1")

        reconciled = await th.reconcile_vectora_sessions()

        assert reconciled == 0

    async def test_thread_sem_nenhuma_mensagem_nunca_e_criada(
        self, session_store: SessionStore, checkpoints_db: aiosqlite.Connection
    ) -> None:
        """Erro/borda: thread registrada em SessionStore (via create_session,
        sem nenhuma mensagem anexada) não vira linha fantasma em
        vectora_sessions — reconcile só repovoa conversa real."""
        await session_store.create_session("thread-vazia", user_id="alice")

        reconciled = await th.reconcile_vectora_sessions()

        assert reconciled == 0
        async with checkpoints_db.execute(
            "SELECT COUNT(*) FROM vectora_sessions"
        ) as cur:
            row = await cur.fetchone()
        assert row is not None
        assert row[0] == 0

    async def test_rodar_duas_vezes_seguidas_e_idempotente(
        self, session_store: SessionStore
    ) -> None:
        await _real_thread(session_store, "thread-1", 5)

        first = await th.reconcile_vectora_sessions()
        second = await th.reconcile_vectora_sessions()

        assert first == 1
        assert second == 0
