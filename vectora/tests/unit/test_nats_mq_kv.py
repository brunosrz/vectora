"""NatsMQ/NatsKV (D3) — mesma interface de RedisMQ/RedisKV, sobre JetStream mockado.

``nats`` (nats-py) não roda contra um servidor real nestes testes — o
cliente/JetStream context são mockados, verificando só o contrato da
interface (mesmo formato que MemoryMQ/RedisMQ e MemoryKV/RedisKV já seguem).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.persistence.kv import NatsKV
from backend.scheduling.mq import NatsMQ, StreamMessage


@pytest.mark.asyncio
async def test_nats_mq_enqueue_publishes_to_jetstream():
    fake_js = MagicMock()
    fake_js.add_stream = AsyncMock()
    fake_js.publish = AsyncMock(return_value=MagicMock(seq=42))
    fake_nc = MagicMock()
    fake_nc.jetstream = MagicMock(return_value=fake_js)

    mq = NatsMQ("nats://127.0.0.1:4222")
    with patch("nats.connect", new=AsyncMock(return_value=fake_nc)):
        msg_id = await mq.enqueue("jobs", {"a": 1})

    assert msg_id == "42"
    fake_js.add_stream.assert_awaited_once()
    fake_js.publish.assert_awaited_once_with(
        "jobs", json.dumps({"a": 1}).encode("utf-8")
    )


@pytest.mark.asyncio
async def test_nats_mq_consume_acks_on_success_and_dispatches_payload():
    fake_msg = MagicMock()
    fake_msg.data = json.dumps({"x": 1}).encode("utf-8")
    fake_msg.reply = "reply-1"
    fake_msg.ack = AsyncMock()

    fake_sub = MagicMock()
    fake_sub.fetch = AsyncMock(side_effect=[[fake_msg], TimeoutError])

    fake_js = MagicMock()
    fake_js.add_stream = AsyncMock()
    fake_js.pull_subscribe = AsyncMock(return_value=fake_sub)
    fake_nc = MagicMock()
    fake_nc.jetstream = MagicMock(return_value=fake_js)

    import asyncio

    received: list[StreamMessage] = []
    stop = asyncio.Event()

    async def handler(msg: StreamMessage) -> None:
        received.append(msg)
        stop.set()

    mq = NatsMQ("nats://127.0.0.1:4222")
    with patch("nats.connect", new=AsyncMock(return_value=fake_nc)):
        await mq.consume("jobs", "g", "c1", handler, stop_event=stop, block_ms=10)

    assert len(received) == 1
    assert received[0].payload == {"x": 1}
    fake_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_nats_kv_get_set_delete_round_trip():
    fake_entry = MagicMock(value=b"valor")
    fake_bucket = MagicMock()
    fake_bucket.get = AsyncMock(return_value=fake_entry)
    fake_bucket.put = AsyncMock()
    fake_bucket.delete = AsyncMock()

    fake_js = MagicMock()
    fake_js.key_value = AsyncMock(return_value=fake_bucket)
    fake_nc = MagicMock()
    fake_nc.jetstream = MagicMock(return_value=fake_js)

    kv = NatsKV("nats://127.0.0.1:4222")
    with patch("nats.connect", new=AsyncMock(return_value=fake_nc)):
        await kv.set("chave", "valor")
        result = await kv.get("chave")
        await kv.delete("chave")

    assert result == "valor"
    fake_bucket.put.assert_awaited_once_with("chave", b"valor")
    fake_bucket.delete.assert_awaited_once_with("chave")


@pytest.mark.asyncio
async def test_nats_kv_get_returns_none_on_miss():
    fake_bucket = MagicMock()
    fake_bucket.get = AsyncMock(side_effect=Exception("key not found"))

    fake_js = MagicMock()
    fake_js.key_value = AsyncMock(return_value=fake_bucket)
    fake_nc = MagicMock()
    fake_nc.jetstream = MagicMock(return_value=fake_js)

    kv = NatsKV("nats://127.0.0.1:4222")
    with patch("nats.connect", new=AsyncMock(return_value=fake_nc)):
        result = await kv.get("nao-existe")

    assert result is None


@pytest.mark.asyncio
async def test_nats_kv_sanitiza_dois_pontos_na_chave():
    """Bug real: `f"partial:{thread_id}"` (usado em native_stream.py/
    threads.py) e `f"watch:{channel}:{workspace_id}"` (file_watcher.py)
    usam `:` como separador — o bucket JetStream KV real rejeita esse
    caractere com `InvalidKeyError` (charset aceito:
    `[-/_=.a-zA-Z0-9]`), então todo save de preview parcial de streaming
    falhava silenciosamente (só um WARNING no log). A chave chega
    sanitizada no `put`/`get`/`delete` reais, sem precisar caçar cada
    call-site do resto do backend que usa `:`."""
    fake_entry = MagicMock(value=b"valor")
    fake_bucket = MagicMock()
    fake_bucket.get = AsyncMock(return_value=fake_entry)
    fake_bucket.put = AsyncMock()
    fake_bucket.delete = AsyncMock()

    fake_js = MagicMock()
    fake_js.key_value = AsyncMock(return_value=fake_bucket)
    fake_nc = MagicMock()
    fake_nc.jetstream = MagicMock(return_value=fake_js)

    kv = NatsKV("nats://127.0.0.1:4222")
    thread_id = "ae535959-ec7f-41d6-a423-3c4d188c4b9d"
    with patch("nats.connect", new=AsyncMock(return_value=fake_nc)):
        await kv.set(f"partial:{thread_id}", "conteudo parcial")
        await kv.get(f"partial:{thread_id}")
        await kv.delete(f"partial:{thread_id}")

    expected = f"partial_{thread_id}"
    fake_bucket.put.assert_awaited_once_with(expected, b"conteudo parcial")
    fake_bucket.get.assert_awaited_once_with(expected)
    fake_bucket.delete.assert_awaited_once_with(expected)


@pytest.mark.asyncio
async def test_erro_borda_chave_sem_caractere_invalido_passa_intacta():
    """Chaves já válidas (sem `:` nem outro caractere fora do charset) não
    podem ser alteradas pela sanitização — round-trip continua idêntico."""
    fake_entry = MagicMock(value=b"valor")
    fake_bucket = MagicMock()
    fake_bucket.get = AsyncMock(return_value=fake_entry)
    fake_bucket.put = AsyncMock()

    fake_js = MagicMock()
    fake_js.key_value = AsyncMock(return_value=fake_bucket)
    fake_nc = MagicMock()
    fake_nc.jetstream = MagicMock(return_value=fake_js)

    kv = NatsKV("nats://127.0.0.1:4222")
    with patch("nats.connect", new=AsyncMock(return_value=fake_nc)):
        await kv.set("valida.chave_123/x-y", "valor")
        await kv.get("valida.chave_123/x-y")

    fake_bucket.put.assert_awaited_once_with("valida.chave_123/x-y", b"valor")
    fake_bucket.get.assert_awaited_once_with("valida.chave_123/x-y")
