"""Tests for the embedding worker circuit breaker (backend/services/background.py)."""

from __future__ import annotations

import pytest

import backend.embedding.background as _bg_mod
from backend.embedding.background import (
    BackgroundEmbeddingWorker,
    _is_rate_limit_error,
    get_worker_pause_state,
)
from backend.embedding.queue import EmbeddingQueueRecord
from backend.storage import factory as _storage_factory
from backend.storage.factory import EmbeddingDimensionMismatchError


@pytest.fixture(autouse=True)
def _reset_worker_singleton():
    original = _bg_mod._worker
    _bg_mod._worker = None
    yield
    _bg_mod._worker = original


class _FakeQueue:
    """Fila mínima que conta chamadas — sem banco."""

    def __init__(self) -> None:
        self.mark_processing_calls = 0
        self.archived_reason: str | None = None

    async def mark_processing(self, queue_id: str) -> None:
        self.mark_processing_calls += 1

    async def archive_pending(self, reason: str) -> int:
        self.archived_reason = reason
        return 7


def _record() -> EmbeddingQueueRecord:
    return EmbeddingQueueRecord(
        queue_id="q1",
        text="conteúdo",
        collection="articles",
        doc_metadata="{}",
        attempt_count=0,
    )


@pytest.mark.parametrize(
    "message",
    [
        "status_code: 429",
        "TooManyRequests",
        "You are using a Trial key, rate limit reached",
        "monthly quota exceeded",
    ],
)
def test_is_rate_limit_error_detects(message: str) -> None:
    assert _is_rate_limit_error(Exception(message))


def test_is_rate_limit_error_ignores_other_errors() -> None:
    assert not _is_rate_limit_error(Exception("connection refused"))


@pytest.mark.asyncio
async def test_trip_breaker_pauses_and_archives() -> None:
    worker = BackgroundEmbeddingWorker()
    _bg_mod._worker = worker  # torna a instância o singleton lido pelo status
    queue = _FakeQueue()

    await worker._trip_rate_limit_breaker(queue)

    assert worker.paused is True
    assert worker.pause_reason is not None
    assert "429" in worker.pause_reason
    assert queue.archived_reason == worker.pause_reason
    # Estado exposto ao endpoint de status.
    paused, reason = get_worker_pause_state()
    assert paused is True
    assert reason == worker.pause_reason


@pytest.mark.asyncio
async def test_trip_breaker_idempotent_across_batch() -> None:
    """Segunda task do mesmo batch não re-arquiva a fila."""
    worker = BackgroundEmbeddingWorker()
    queue = _FakeQueue()

    await worker._trip_rate_limit_breaker(queue)
    queue.archived_reason = None  # marca para detectar re-arquivamento
    await worker._trip_rate_limit_breaker(queue)

    assert queue.archived_reason is None  # não arquivou de novo


@pytest.mark.asyncio
async def test_process_record_rate_limit_trips_breaker_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Em rate limit, não re-tenta 3 vezes — dispara o breaker na 1a falha."""
    worker = BackgroundEmbeddingWorker()
    queue = _FakeQueue()

    async def _raise_429(_text: str) -> list[float]:
        raise Exception("status_code: 429 — Trial key rate limit")

    monkeypatch.setattr(worker, "_generate_embedding", _raise_429)

    await worker._process_record(_record(), queue)

    assert worker.paused is True
    # mark_processing chamado uma única vez (sem o loop de 3 tentativas).
    assert queue.mark_processing_calls == 1
    assert queue.archived_reason is not None


@pytest.mark.asyncio
async def test_get_queue_uses_effective_storage_mode_not_raw_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """storage_mode='complete' configurado + licença Free deve cair pro
    backend local (SQLite/LanceDB) — nunca chamar get_pg_pool()/require_pro().

    Regressão: o worker lia self.config.storage_mode (valor cru) em vez de
    get_effective_storage_mode() (valor pós-licença), então uma instalação
    com storage_mode='complete' configurado mas sem licença Pro entrava num
    loop de erro 402 a cada ciclo do worker.
    """
    worker = BackgroundEmbeddingWorker()
    worker.config.storage_mode = "complete"
    worker.config.postgres_dsn = "postgresql://fake/db"

    monkeypatch.setattr(
        "backend.services.license.get_effective_storage_mode",
        lambda: "lite",
    )

    postgres_queue_called = False

    class _FakePostgresQueueDB:
        def __init__(self) -> None:
            nonlocal postgres_queue_called
            postgres_queue_called = True

        async def _ensure_table(self) -> None:
            pass

    monkeypatch.setattr("backend.embedding.queue.PostgresQueueDB", _FakePostgresQueueDB)

    sqlite_queue_called = False

    async def _fake_get_embedding_queue(_dsn: str) -> object:
        nonlocal sqlite_queue_called
        sqlite_queue_called = True
        return _FakeQueue()

    monkeypatch.setattr(_bg_mod, "get_embedding_queue", _fake_get_embedding_queue)

    await worker._get_queue()

    assert sqlite_queue_called is True
    assert postgres_queue_called is False


class _FakeVectorStoreBackend:
    """Backend nativo mínimo — só registra as chamadas de upsert."""

    def __init__(self) -> None:
        self.upserted: list[tuple[str, list]] = []

    async def upsert(self, collection: str, rows: list) -> None:
        self.upserted.append((collection, rows))


async def _cleanup_dim_meta(collection: str) -> None:
    db = await _storage_factory._embedding_meta_db()
    await _storage_factory._ensure_embedding_meta_table(db)
    await db.execute(
        "DELETE FROM embedding_index_meta WHERE collection = ?", (collection,)
    )
    await db.commit()


class TestWriteToVectorStore:
    """`_write_to_vector_store` escreve no backend nativo com guard de
    dimensão prévio — a checagem que antes só rodava dentro do wrapper
    LangChain (`get_langchain_vector_store`, removido) precisa continuar
    protegendo o caminho de escrita real (nativo)."""

    @pytest.mark.asyncio
    async def test_write_upserts_after_dimension_check_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        collection = "test-write-vs-happy"
        await _cleanup_dim_meta(collection)
        try:
            fake_backend = _FakeVectorStoreBackend()
            monkeypatch.setattr(
                _storage_factory,
                "get_vector_store_backend",
                lambda: _fake_get(fake_backend),
            )

            worker = BackgroundEmbeddingWorker()
            record = EmbeddingQueueRecord(
                queue_id="q1",
                text="conteúdo",
                collection=collection,
                doc_metadata='{"workspace_id": "w1"}',
                attempt_count=0,
            )

            await worker._write_to_vector_store(record, [0.1, 0.2, 0.3])

            assert len(fake_backend.upserted) == 1
            written_collection, rows = fake_backend.upserted[0]
            assert written_collection == collection
            assert rows[0].id == "q1"
            assert rows[0].vector == [0.1, 0.2, 0.3]
        finally:
            await _cleanup_dim_meta(collection)

    @pytest.mark.asyncio
    async def test_write_raises_on_dimension_mismatch_without_upserting(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Coleção já indexada com 1024 dims — vetor novo de 3 dims deve
        levantar antes de qualquer escrita (nunca corromper a coleção)."""
        collection = "test-write-vs-mismatch"
        await _cleanup_dim_meta(collection)
        try:
            await _storage_factory._check_embedding_dimension(
                collection, 1024, provider="cohere"
            )

            fake_backend = _FakeVectorStoreBackend()
            monkeypatch.setattr(
                _storage_factory,
                "get_vector_store_backend",
                lambda: _fake_get(fake_backend),
            )

            worker = BackgroundEmbeddingWorker()
            record = EmbeddingQueueRecord(
                queue_id="q2",
                text="conteúdo",
                collection=collection,
                doc_metadata="{}",
                attempt_count=0,
            )

            with pytest.raises(EmbeddingDimensionMismatchError):
                await worker._write_to_vector_store(record, [0.1, 0.2, 0.3])

            assert fake_backend.upserted == []
        finally:
            await _cleanup_dim_meta(collection)


async def _fake_get(backend: _FakeVectorStoreBackend) -> _FakeVectorStoreBackend:
    return backend


class TestGenerateEmbedding:
    """`_generate_embedding` delega pra `_build_lc_embeddings()` — antes era
    `CohereEmbeddings` hardcoded, sem o fallback multi-provider que a
    indexação de verdade precisa ter (mesmo padrão de `_write_to_vector_store`)."""

    @pytest.mark.asyncio
    async def test_delega_para_build_lc_embeddings(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _FakeEmb:
            async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
                assert texts == ["conteúdo"]
                return [[0.1, 0.2, 0.3]]

        monkeypatch.setattr(_storage_factory, "_build_lc_embeddings", _FakeEmb)

        worker = BackgroundEmbeddingWorker()
        vetor = await worker._generate_embedding("conteúdo")

        assert vetor == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_sem_provider_configurado_levanta_value_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_storage_factory, "_build_lc_embeddings", lambda: None)

        worker = BackgroundEmbeddingWorker()
        with pytest.raises(ValueError, match="Nenhum provider"):
            await worker._generate_embedding("conteúdo")
