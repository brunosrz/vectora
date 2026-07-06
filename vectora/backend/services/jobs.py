"""Fila de jobs assíncronos sobre ``get_mq()`` (``RedisMQ`` ou ``MemoryMQ``).

Dois streams por job:

- ``jobs`` — fila de trabalho; ``run_jobs_worker`` consome e despacha por
  ``kind`` para o handler registrado em ``register_job``.
- ``jobs:events:<request_id>`` — eventos de progresso/resultado; ``stream_job_events``
  consome e devolve ao cliente (SSE).

Cada handler publica eventos com ``publish_event`` e encerra com um evento
terminal (``done`` ou ``error``). Se o handler levantar exceção, o worker publica
``error`` no lugar.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import socket
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

JOBS_STREAM = "jobs"
JOBS_GROUP = "jobs-workers"
_TERMINAL = frozenset({"done", "error"})

#: Handler de job — recebe (request_id, payload) e publica eventos.
JobHandler = Callable[[str, dict], Awaitable[None]]

_handlers: dict[str, JobHandler] = {}


def register_job(kind: str, handler: JobHandler) -> None:
    """Registra um handler para um ``kind`` de job (idempotente por kind)."""
    _handlers[kind] = handler


def registered_kinds() -> list[str]:
    """Lista os kinds de job registrados (para o painel/healthcheck)."""
    return sorted(_handlers)


def _events_stream(request_id: str) -> str:
    return f"jobs:events:{request_id}"


async def submit_job(kind: str, payload: dict | None = None) -> str:
    """Enfileira um job e retorna o ``request_id`` para acompanhamento."""
    from backend.scheduling.mq import get_mq

    request_id = uuid.uuid4().hex
    mq = await get_mq()
    await mq.enqueue(
        JOBS_STREAM,
        {"request_id": request_id, "kind": kind, "payload": payload or {}},
    )
    logger.debug("jobs: submetido kind=%s request_id=%s", kind, request_id)
    return request_id


async def publish_event(request_id: str, status: str, data: dict | None = None) -> None:
    """Publica um evento de progresso/resultado no stream do ``request_id``."""
    from backend.scheduling.mq import get_mq

    mq = await get_mq()
    await mq.enqueue(_events_stream(request_id), {"status": status, **(data or {})})


async def stream_job_events(
    request_id: str, *, idle_timeout: float = 30.0
) -> AsyncIterator[dict]:
    """Itera os eventos de um job até um evento terminal (``done``/``error``).

    Encerra após ``idle_timeout`` segundos sem novos eventos (proteção contra
    jobs travados / clientes pendurados).
    """
    from backend.scheduling.mq import get_mq

    mq = await get_mq()
    out: asyncio.Queue[dict] = asyncio.Queue()
    stop = asyncio.Event()

    async def _handler(msg: Any) -> None:
        await out.put(msg.payload)
        if msg.payload.get("status") in _TERMINAL:
            stop.set()

    task = asyncio.create_task(
        mq.consume(
            _events_stream(request_id),
            group=f"sse-{request_id}",
            consumer="sse",
            handler=_handler,
            stop_event=stop,
            block_ms=1000,
        )
    )
    try:
        while True:
            try:
                async with asyncio.timeout(idle_timeout):
                    event = await out.get()
            except TimeoutError:
                break
            yield event
            if event.get("status") in _TERMINAL:
                break
    finally:
        stop.set()
        task.cancel()
        with contextlib.suppress(Exception, asyncio.CancelledError):
            await task


async def run_jobs_worker(*, stop_event: asyncio.Event | None = None) -> None:
    """Worker que consome ``jobs`` e despacha por ``kind``.

    Todos os workers compartilham o consumer group ``jobs-workers``, então cada
    job é entregue a um único worker. O nome do consumidor é único por processo
    para o redelivery do Redis funcionar.
    """
    from backend.scheduling.mq import get_mq

    consumer = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"

    async def _handler(msg: Any) -> None:
        payload = msg.payload
        request_id = payload.get("request_id", "")
        kind = payload.get("kind", "")
        handler = _handlers.get(kind)
        if handler is None:
            await publish_event(
                request_id, "error", {"error": f"kind desconhecido: {kind}"}
            )
            return
        try:
            await handler(request_id, payload.get("payload", {}))
        except Exception as exc:
            logger.exception("jobs: handler kind=%s falhou", kind)
            await publish_event(request_id, "error", {"error": str(exc)})

    logger.info("jobs: worker iniciado (consumer=%s)", consumer)
    mq = await get_mq()
    await mq.consume(
        JOBS_STREAM,
        group=JOBS_GROUP,
        consumer=consumer,
        handler=_handler,
        stop_event=stop_event,
        block_ms=1000,
    )
