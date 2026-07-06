"""adapt_stream emite output do terminal em tempo real (não só no on_tool_end).

A tool `terminal` já chamava `emit_terminal_line()` a cada linha, mas nada
registrava um callback — o output só chegava ao frontend no ToolResultEvent
final. `adapt_stream` agora registra um callback e corre uma fila de linhas
em paralelo ao consumo de eventos do LangGraph (que fica parado durante
toda a execução da tool, sem emitir nada novo).
"""

from __future__ import annotations

import asyncio
import json

import pytest

from backend.api.adapters import adapt_stream
from backend.services.terminal_stream import emit_terminal_line


def _parse(sse: str) -> dict:
    assert sse.startswith("data: ")
    return json.loads(sse[len("data: ") :].strip())


async def _slow_agen(events, delay: float):
    """Simula o graph ficando parado enquanto a tool `terminal` roda."""
    for ev in events:
        await asyncio.sleep(delay)
        yield ev


async def _collect(gen):
    return [_parse(s) async for s in gen]


@pytest.mark.asyncio
async def test_terminal_lines_emitted_while_graph_is_idle():
    """Linhas emitidas via emit_terminal_line chegam ANTES do próximo evento
    do graph, mesmo que o graph não produza nada por um tempo."""

    events = [
        {
            "event": "on_tool_start",
            "name": "terminal",
            "run_id": "r1",
            "data": {"input": {"command": "npm install"}},
        },
        {
            "event": "on_tool_end",
            "name": "terminal",
            "run_id": "r1",
            "data": {"output": "instalado"},
        },
    ]

    gen = adapt_stream(_slow_agen(events, delay=0.2), "tid")

    async def _emit_lines_soon():
        await asyncio.sleep(0.02)
        emit_terminal_line("added 42 packages")
        await asyncio.sleep(0.02)
        emit_terminal_line("audited 100 packages")

    emit_task = asyncio.create_task(_emit_lines_soon())
    out = await _collect(gen)
    await emit_task

    types = [e["type"] for e in out]
    terminal_lines = [e for e in out if e["type"] == "terminal_line"]

    assert [e["line"] for e in terminal_lines] == [
        "added 42 packages",
        "audited 100 packages",
    ]
    # As duas linhas chegam ANTES do tool_result (que só sai no on_tool_end,
    # 0.2s+0.2s depois) — prova que não esperaram o graph avançar.
    assert types.index(terminal_lines[0]["type"]) < types.index("tool_result")
    assert types.index(terminal_lines[1]["type"]) < types.index("tool_result")


@pytest.mark.asyncio
async def test_no_terminal_lines_when_none_emitted():
    """Erro/borda: sem chamada a emit_terminal_line, não gera terminal_line."""
    events = [
        {
            "event": "on_tool_start",
            "name": "file_read",
            "run_id": "r1",
            "data": {"input": {"path": "x.py"}},
        },
        {
            "event": "on_tool_end",
            "name": "file_read",
            "run_id": "r1",
            "data": {"output": "conteudo"},
        },
    ]
    out = await _collect(adapt_stream(_slow_agen(events, delay=0.0), "tid"))
    assert not [e for e in out if e["type"] == "terminal_line"]


@pytest.mark.asyncio
async def test_terminal_callback_unregistered_after_stream_ends():
    """Erro/borda: callback não deve vazar entre streams — o próximo adapt_stream
    não deve receber linhas de uma emissão tardia do stream anterior."""
    events = [{"event": "on_chain_end", "name": "x", "data": {}}]
    await _collect(adapt_stream(_slow_agen(events, delay=0.0), "tid1"))

    # Emissão tardia após o primeiro stream terminar — não deve quebrar nada
    # nem ser entregue a ninguém (callback já foi desregistrado).
    emit_terminal_line("linha orfa")

    out2 = await _collect(adapt_stream(_slow_agen(events, delay=0.0), "tid2"))
    assert not [e for e in out2 if e["type"] == "terminal_line"]
