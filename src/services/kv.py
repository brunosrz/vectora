"""KV distribuído + pub/sub — Bloco G (G1).

Abstração mínima de chave/valor com publish/subscribe para sincronizar caches
in-memory entre réplicas do backend:

- ``MemoryKV`` — default (modo lite / single-process). Pub/sub despacha para
  os subscribers do próprio processo; ``get/set`` usam um dict com TTL.
- ``RedisKV`` — ativado quando ``settings.redis_url`` está configurado. Usa
  ``redis.asyncio``; um reader task único atende todas as inscrições.

Os caches locais (``llm_tools._bound_cache``, ``plugins._mcp_tools_cache``,
``workspace._active``…) continuam sendo o L1 — o KV serve de invalidador L2
via pub/sub (ver ``cache_sync.py``), não de storage primário.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

#: Callback de subscription — recebe o payload (str) publicado no canal.
Subscriber = Callable[[str], None] | Callable[[str], Awaitable[None]]


async def _dispatch(callback: Subscriber, payload: str) -> None:
    try:
        result = callback(payload)
        if inspect.isawaitable(result):
            await result
    except Exception:
        logger.exception("kv: subscriber falhou (payload descartado)")


class MemoryKV:
    """Backend in-memory — válido apenas para single-process (modo lite)."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float | None]] = {}
        self._subs: dict[str, list[Subscriber]] = {}

    async def get(self, key: str) -> str | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        value, expires = entry
        if expires is not None and time.monotonic() > expires:
            self._data.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, *, ttl_s: float | None = None) -> None:
        expires = time.monotonic() + ttl_s if ttl_s else None
        self._data[key] = (value, expires)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def publish(self, channel: str, payload: str) -> None:
        for callback in self._subs.get(channel, []):
            await _dispatch(callback, payload)

    def subscribe(self, channel: str, callback: Subscriber) -> None:
        self._subs.setdefault(channel, []).append(callback)

    async def start(self) -> None:  # paridade de interface com RedisKV
        return None

    async def close(self) -> None:
        self._data.clear()
        self._subs.clear()


class RedisKV:
    """Backend Redis — multi-réplica. Um único reader task de pub/sub."""

    def __init__(self, url: str) -> None:
        import redis.asyncio as aredis

        self._redis = aredis.from_url(url, decode_responses=True)
        self._subs: dict[str, list[Subscriber]] = {}
        self._pubsub: Any = None
        self._reader: asyncio.Task | None = None

    async def get(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def set(self, key: str, value: str, *, ttl_s: float | None = None) -> None:
        await self._redis.set(key, value, ex=int(ttl_s) if ttl_s else None)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def publish(self, channel: str, payload: str) -> None:
        await self._redis.publish(channel, payload)

    def subscribe(self, channel: str, callback: Subscriber) -> None:
        self._subs.setdefault(channel, []).append(callback)

    async def start(self) -> None:
        """Inscreve nos canais registrados e inicia o reader task."""
        if not self._subs or self._reader is not None:
            return
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(*self._subs.keys())
        self._reader = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        try:
            async for message in self._pubsub.listen():
                if message.get("type") != "message":
                    continue
                channel = str(message.get("channel", ""))
                payload = str(message.get("data", ""))
                for callback in self._subs.get(channel, []):
                    await _dispatch(callback, payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("kv: reader pub/sub encerrou com erro: %s", exc)

    async def close(self) -> None:
        if self._reader is not None:
            self._reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader
            self._reader = None
        if self._pubsub is not None:
            with contextlib.suppress(Exception):
                await self._pubsub.aclose()
        with contextlib.suppress(Exception):
            await self._redis.aclose()


KV = MemoryKV | RedisKV

_kv: KV | None = None


def get_kv() -> KV:
    """Singleton do KV — Redis quando ``settings.redis_url`` está setado."""
    global _kv
    if _kv is None:
        from src.settings import settings

        url = (settings.redis_url or "").strip()
        if url:
            try:
                _kv = RedisKV(url)
                logger.info("kv: backend Redis (%s)", url.split("@")[-1])
            except Exception as exc:
                logger.warning("kv: Redis indisponível (%s) — usando memória", exc)
                _kv = MemoryKV()
        else:
            _kv = MemoryKV()
    return _kv


def reset_kv() -> None:
    """Descarta o singleton — usado em testes."""
    global _kv
    _kv = None


def publish_soon(channel: str, payload: str) -> None:
    """Publica sem bloquear, a partir de código síncrono.

    Os bumps de versão (plugins/tool_policy/workspace) são funções sync; este
    helper agenda o publish no event loop corrente. Sem loop (CLI puro), o
    publish é um no-op — nesse modo não há outras réplicas para avisar.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(get_kv().publish(channel, payload))
