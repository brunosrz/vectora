"""Message queue distribuída — Bloco G (G3), base para a API externa.

Fila de mensagens sobre **Redis Streams** com consumer groups
(``XADD``/``XREADGROUP``/``XACK``): entrega at-least-once, múltiplos
consumidores em réplicas distintas, redelivery de mensagens não-ackadas.

- ``MemoryMQ`` — fallback in-process (modo lite / testes): ``asyncio.Queue``
  por stream; sem redelivery entre processos (não há outros processos).
- ``RedisMQ`` — produção multi-réplica.

Nota: a fila de **embeddings** continua no ``src/services/queue.py`` (SQLite
no lite; Postgres ``SKIP LOCKED`` no complete — já é multi-réplica seguro).
Este módulo é a fundação para consumidores novos: webhooks de saída (Bloco L),
jobs da REST API v1 (Bloco J) e tarefas assíncronas do agente.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

#: Handler de consumo — recebe a mensagem; exceção ⇒ sem ACK (redelivery).
Handler = Callable[["StreamMessage"], Awaitable[None]]


@dataclass(frozen=True)
class StreamMessage:
    """Mensagem entregue ao consumidor."""

    id: str
    payload: dict


class MemoryMQ:
    """Backend in-process — sem persistência nem redelivery cross-process."""

    def __init__(self) -> None:
        self._streams: dict[str, asyncio.Queue[StreamMessage]] = {}

    def _queue(self, stream: str) -> asyncio.Queue[StreamMessage]:
        return self._streams.setdefault(stream, asyncio.Queue())

    async def enqueue(self, stream: str, payload: dict) -> str:
        msg = StreamMessage(id=uuid.uuid4().hex, payload=payload)
        await self._queue(stream).put(msg)
        return msg.id

    async def consume(
        self,
        stream: str,
        group: str,
        consumer: str,
        handler: Handler,
        *,
        stop_event: asyncio.Event | None = None,
        block_ms: int = 5000,
    ) -> None:
        """Consome até ``stop_event`` ser setado (ou para sempre)."""
        queue = self._queue(stream)
        while stop_event is None or not stop_event.is_set():
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=block_ms / 1000)
            except TimeoutError:
                continue
            try:
                await handler(msg)
            except Exception:
                logger.exception("mq[%s]: handler falhou — recolocando", stream)
                await queue.put(msg)
                await asyncio.sleep(1)

    async def close(self) -> None:
        self._streams.clear()


class RedisMQ:
    """Backend Redis Streams com consumer groups (at-least-once)."""

    def __init__(self, url: str, *, maxlen: int = 10_000) -> None:
        import redis.asyncio as aredis

        self._redis = aredis.from_url(url, decode_responses=True)
        self._maxlen = maxlen

    async def enqueue(self, stream: str, payload: dict) -> str:
        msg_id = await self._redis.xadd(
            stream,
            {"payload": json.dumps(payload, ensure_ascii=False)},
            maxlen=self._maxlen,
            approximate=True,
        )
        return str(msg_id)

    async def _ensure_group(self, stream: str, group: str) -> None:
        try:
            await self._redis.xgroup_create(stream, group, id="0", mkstream=True)
        except Exception as exc:  # BUSYGROUP = grupo já existe
            if "BUSYGROUP" not in str(exc):
                raise

    async def consume(
        self,
        stream: str,
        group: str,
        consumer: str,
        handler: Handler,
        *,
        stop_event: asyncio.Event | None = None,
        block_ms: int = 5000,
        count: int = 10,
    ) -> None:
        """Loop de consumo: XREADGROUP → handler → XACK.

        Handler que lança exceção deixa a mensagem pendente no grupo —
        redelivery via ``XAUTOCLAIM`` fica a cargo de um reaper futuro ou de
        outro consumidor com o mesmo nome reiniciado.
        """
        await self._ensure_group(stream, group)
        while stop_event is None or not stop_event.is_set():
            try:
                batches: Any = await self._redis.xreadgroup(
                    group, consumer, {stream: ">"}, count=count, block=block_ms
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("mq[%s]: leitura falhou (%s) — retry em 2s", stream, exc)
                await asyncio.sleep(2)
                continue
            for _stream_name, messages in batches or []:
                for msg_id, fields in messages:
                    try:
                        payload = json.loads(fields.get("payload", "{}"))
                    except json.JSONDecodeError:
                        payload = {}
                    try:
                        await handler(StreamMessage(id=str(msg_id), payload=payload))
                        await self._redis.xack(stream, group, msg_id)
                    except Exception:
                        logger.exception(
                            "mq[%s]: handler falhou para %s (sem ACK)", stream, msg_id
                        )

    async def close(self) -> None:
        import contextlib

        with contextlib.suppress(Exception):
            await self._redis.aclose()


MQ = MemoryMQ | RedisMQ

_mq: MQ | None = None


def get_mq() -> MQ:
    """Singleton da message queue — Redis quando ``settings.redis_url`` setado."""
    global _mq
    if _mq is None:
        from backend.persistence.kv import redis_reachable
        from backend.settings import settings

        url = (settings.redis_url or "").strip()
        if settings.storage_mode == "complete" and url and redis_reachable(url):
            try:
                _mq = RedisMQ(url)
                logger.info("mq: backend Redis Streams")
            except Exception as exc:
                logger.warning("mq: Redis indisponível (%s) — usando memória", exc)
                _mq = MemoryMQ()
        else:
            if settings.storage_mode == "complete" and url:
                logger.info("mq: redis_url configurado mas inacessível — memória")
            _mq = MemoryMQ()
    return _mq


def reset_mq() -> None:
    """Descarta o singleton — usado em testes."""
    global _mq
    _mq = None
