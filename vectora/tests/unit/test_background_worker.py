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
