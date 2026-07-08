"""Testes do fan-out de PtySession (broadcast pra múltiplos WS no mesmo terminal).

Antes desta mudança, `read()` drenava uma única `asyncio.Queue` — dois
clientes WS abrindo o mesmo `terminal_id` competiam pelos mesmos itens
(round-robin), então o segundo cliente nunca via a saída completa. Agora
cada consumidor chama `subscribe()` e ganha sua própria fila; o read-loop
faz broadcast pra todas.
"""

from __future__ import annotations

import asyncio

import pytest

from backend.services.pty_session import PtySession


class _FakeProc:
    """Simula o backend PTY: devolve os chunks de `outputs` e então EOF."""

    def __init__(self, outputs: list[bytes]) -> None:
        self._outputs = list(outputs)

    def read(self, _n: int) -> bytes:
        if not self._outputs:
            raise EOFError
        return self._outputs.pop(0)


def _make_session(outputs: list[bytes]) -> PtySession:
    proc = _FakeProc(outputs)
    return PtySession(
        terminal_id="term-1", workspace_id="ws-1", thread_id="t1", proc=proc
    )


async def _drain(q: asyncio.Queue[bytes | None]) -> list[bytes]:
    chunks: list[bytes] = []
    while True:
        item = await q.get()
        if item is None:
            return chunks
        chunks.append(item)


@pytest.mark.asyncio
async def test_dois_subscribers_recebem_todos_os_chunks() -> None:
    session = _make_session([b"a", b"b", b"c"])
    q1 = session.subscribe()
    q2 = session.subscribe()

    await session._read_loop()

    assert await _drain(q1) == [b"a", b"b", b"c"]
    assert await _drain(q2) == [b"a", b"b", b"c"]


@pytest.mark.asyncio
async def test_subscriber_tardio_nao_recebe_chunks_anteriores() -> None:
    """subscribe() depois do read-loop já ter rodado não recebe nada — a
    fila é criada vazia, sem replay do histórico (mesma limitação que já
    existia com o leitor único)."""
    session = _make_session([b"a", b"b"])
    q1 = session.subscribe()
    await session._read_loop()
    await _drain(q1)

    q2 = session.subscribe()
    assert q2.empty()


@pytest.mark.asyncio
async def test_unsubscribe_para_de_receber_broadcast() -> None:
    session = _make_session([b"x"])
    q1 = session.subscribe()
    session.unsubscribe(q1)

    await session._read_loop()

    assert q1.empty()


def test_unsubscribe_de_fila_desconhecida_nao_quebra() -> None:
    session = _make_session([])
    q = asyncio.Queue()
    session.unsubscribe(q)  # não deve levantar


@pytest.mark.asyncio
async def test_sem_subscribers_read_loop_nao_quebra() -> None:
    session = _make_session([b"a"])
    await session._read_loop()  # não deve levantar mesmo sem consumidores
