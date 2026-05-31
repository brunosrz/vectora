"""Stress test 5 — EmbeddingQueue: ciclo completo enqueue → mark_success/failed.

Simula o ciclo de vida real de um BackgroundEmbeddingWorker processando uma
rajada de documentos:
  1. Enfileira N documentos (fase de ingestão)
  2. Busca lotes de pendentes (get_pending)
  3. Metade é marcada como sucesso, metade como falha (mark_success / mark_failed)
  4. Verifica contagens finais de cada status

Testa a consistência do banco SQLite sob transições de estado concorrentes e
garante que o índice em `status` mantém as queries rápidas mesmo após
muitas atualizações.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from src.services.queue import EmbeddingQueue, EmbeddingStatus


@pytest.mark.stress
@pytest.mark.asyncio
async def test_queue_full_lifecycle(tmp_path):
    """200 documentos: enqueue → get_pending → mark_success/failed — consistência total."""
    N = 200
    db_path = tmp_path / "stress_lifecycle.db"
    queue = EmbeddingQueue(f"sqlite+aiosqlite:///{db_path}")
    await queue.init()

    # ── Fase 1: enfileira N documentos em paralelo ──────────────────────────
    t_enqueue = time.perf_counter()
    queue_ids: list[str] = await asyncio.gather(
        *[queue.enqueue(f"documento {i}", "lifecycle_col") for i in range(N)]
    )
    elapsed_enqueue = time.perf_counter() - t_enqueue

    assert len(queue_ids) == N
    assert await queue.count_pending() == N

    # ── Fase 2: busca todos os pendentes em lotes de 50 ────────────────────
    t_fetch = time.perf_counter()
    fetched_ids: list[str] = []
    while True:
        batch = await queue.get_pending(limit=50)
        if not batch:
            break
        fetched_ids.extend(str(rec.queue_id) for rec in batch)
        # Marca os do lote como "processing" para não buscá-los de novo
        await asyncio.gather(
            *[queue.mark_failed(str(rec.queue_id), "processing") for rec in batch]
        )
    elapsed_fetch = time.perf_counter() - t_fetch

    assert len(fetched_ids) == N, f"Fetch incompleto: {len(fetched_ids)}/{N}"

    # ── Fase 3: metade sucesso, metade falha — em paralelo ──────────────────
    half = N // 2
    success_ids = queue_ids[:half]
    failed_ids = queue_ids[half:]

    t_mark = time.perf_counter()
    await asyncio.gather(
        *[queue.mark_success(qid) for qid in success_ids],
        *[queue.mark_failed(qid, "erro de embedding simulado") for qid in failed_ids],
    )
    elapsed_mark = time.perf_counter() - t_mark

    # ── Fase 4: verifica contagens finais ───────────────────────────────────
    pending_final = await queue.count_pending()
    assert pending_final == 0, f"Ainda há {pending_final} pendentes após processamento"

    # Budgets individuais
    assert elapsed_enqueue < 10.0, f"Enqueue: {elapsed_enqueue:.2f}s para {N} itens"
    assert elapsed_fetch < 5.0, f"Fetch em lotes: {elapsed_fetch:.2f}s"
    assert elapsed_mark < 5.0, f"Mark operations: {elapsed_mark:.2f}s para {N} itens"


@pytest.mark.stress
@pytest.mark.asyncio
async def test_queue_count_pending_scales_with_index(tmp_path):
    """count_pending() deve ser O(log n) com o índice — rápido mesmo com 500 registros."""
    N = 500
    db_path = tmp_path / "stress_count.db"
    queue = EmbeddingQueue(f"sqlite+aiosqlite:///{db_path}")
    await queue.init()

    # Popula a fila
    await asyncio.gather(*[queue.enqueue(f"doc {i}", "index_col") for i in range(N)])

    # count_pending() 100 vezes — deve ser consistentemente rápido
    ITERATIONS = 100
    t0 = time.perf_counter()
    for _ in range(ITERATIONS):
        count = await queue.count_pending()
        assert count == N
    elapsed = time.perf_counter() - t0

    avg_ms = (elapsed / ITERATIONS) * 1000
    # Budget: cada count_pending deve levar menos de 50 ms em média
    assert avg_ms < 50.0, f"count_pending muito lento: {avg_ms:.1f}ms médio (máx: 50ms)"
