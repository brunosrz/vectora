"""Stress test 2 — EmbeddingQueue: contenção leitor/escritor.

Simula o padrão de produção onde ingest_docs (escritor) e
BackgroundEmbeddingWorker (leitor) operam na mesma fila SQLite ao mesmo tempo.

  - 50 writers fazem enqueue() em paralelo
  - 10 readers fazem get_pending() em paralelo
  - tudo simultâneo (asyncio.gather de ambos os grupos)

Verifica:
  - readers nunca levantam exceção (sem "database is locked")
  - writers persistem todos os registros (count_pending == N_WRITES)
  - o tempo total está dentro do budget
"""

from __future__ import annotations

import asyncio
import time

import pytest

from backend.embedding.queue import EmbeddingQueue


@pytest.mark.stress
@pytest.mark.asyncio
async def test_queue_reader_writer_contention(tmp_path):
    """50 writers + 10 readers simultâneos — sem deadlock nem perda de dados."""
    N_WRITES = 50
    N_READS = 10

    db_path = tmp_path / "stress_rw.db"
    queue = EmbeddingQueue(f"sqlite+aiosqlite:///{db_path}")
    await queue.init()

    async def writer(i: int) -> str:
        return await queue.enqueue(f"texto do writer {i}", "rw_collection")

    async def reader() -> list:
        return await queue.get_pending(limit=5)

    t0 = time.perf_counter()
    results = await asyncio.gather(
        *[writer(i) for i in range(N_WRITES)],
        *[reader() for _ in range(N_READS)],
        return_exceptions=True,
    )
    elapsed = time.perf_counter() - t0

    # Nenhuma operação pode ter levantado exceção
    errors = [r for r in results if isinstance(r, Exception)]
    assert not errors, f"Exceções durante contenção R/W: {errors}"

    # Todos os registros foram persistidos
    pending = await queue.count_pending()
    assert pending == N_WRITES, f"Esperado {N_WRITES} pendentes, encontrado {pending}"

    # Budget: 50 writes + 10 reads em menos de 10 s
    assert elapsed < 10.0, f"Tempo excessivo: {elapsed:.2f}s"
