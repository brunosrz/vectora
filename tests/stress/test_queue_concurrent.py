"""Stress test 1 — EmbeddingQueue: enqueue concorrente.

Dispara N coroutines simultâneas de enqueue() contra uma única fila SQLite
e verifica que:
  - todos os queue_ids são únicos (sem colisão de UUID)
  - nenhuma escrita é perdida (count_pending == N)
  - o tempo total permanece dentro do budget aceitável

Testa: WAL mode, busy_timeout, Index(status) e ausência de deadlock sob
carga de escrita paralela — o mesmo padrão do BackgroundEmbeddingWorker +
ingest_docs rodando ao mesmo tempo em produção.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from src.services.queue import EmbeddingQueue


@pytest.mark.stress
@pytest.mark.asyncio
async def test_queue_concurrent_enqueue(tmp_path):
    """100 enqueues simultâneos — sem perda, sem colisão, dentro do budget."""
    N = 100
    db_path = tmp_path / "stress_queue.db"
    queue = EmbeddingQueue(f"sqlite+aiosqlite:///{db_path}")
    await queue.init()

    texts = [f"documento de stress número {i}" for i in range(N)]

    t0 = time.perf_counter()
    queue_ids = await asyncio.gather(
        *[queue.enqueue(text, "stress_collection") for text in texts]
    )
    elapsed = time.perf_counter() - t0

    # Todos os IDs devem ser únicos
    assert len(set(queue_ids)) == N, "Colisão de queue_id detectada"

    # Nenhuma escrita pode ter sido perdida
    pending = await queue.count_pending()
    assert pending == N, f"Esperado {N} pendentes, encontrado {pending}"

    # Budget: 100 escritas SQLite locais devem completar em menos de 10 s
    assert elapsed < 10.0, f"Tempo excessivo: {elapsed:.2f}s para {N} enqueues"
