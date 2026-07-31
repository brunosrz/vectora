"""`HITLEvent.pre_approved` — wiring do Sprint 22 dentro de `adapt_stream`.

O ponto crítico: `pre_approved` é só uma anotação no evento SSE. O
`__interrupt__` já fez o grafo pausar antes deste código rodar — nada aqui
decide se a tool executa.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from backend.api.adapters import adapt_stream


def _parse(sse: str) -> dict:
    assert sse.startswith("data: ")
    return json.loads(sse[len("data: ") :].strip())


async def _agen(events):
    for ev in events:
        yield ev


def _interrupt_event(tool_name: str, args: dict):
    intr = type(
        "Intr", (), {"value": [{"name": tool_name, "args": args, "id": "i1"}]}
    )()
    return {
        "event": "on_chain_stream",
        "name": "hitl_check",
        "run_name": "hitl_check",
        "metadata": {},
        "data": {"chunk": {"__interrupt__": [intr]}},
    }


@pytest.fixture(autouse=True)
def _isolated(_no_thread_persistence):
    pass


@pytest.mark.asyncio
async def test_pre_approved_reflete_o_avaliador(monkeypatch):
    async def _sempre_true(*_a, **_k):
        return True

    monkeypatch.setattr("backend.api.adapters._pre_approved", _sempre_true)

    events = [_interrupt_event("terminal", {"command": "git status"})]
    out = [_parse(s) async for s in adapt_stream(_agen(events), "tid")]

    hitl = next(e for e in out if e["type"] == "hitl")
    assert hitl["pre_approved"] is True


@pytest.mark.asyncio
async def test_falha_no_avaliador_nao_derruba_o_stream(monkeypatch):
    """Erro/borda: `_pre_approved` já degrada sozinho, mas se algo escapar
    (bug futuro) o stream ainda não pode quebrar por causa de uma anotação
    cosmética — HITL é a parte que importa."""
    quebrado = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr("backend.api.adapters._pre_approved", quebrado)

    events = [_interrupt_event("terminal", {"command": "git status"})]
    out = [_parse(s) async for s in adapt_stream(_agen(events), "tid")]

    hitl = next(e for e in out if e["type"] == "hitl")
    assert hitl["pre_approved"] is False


@pytest.mark.asyncio
async def test_pre_approved_nao_afeta_a_emissao_do_evento_hitl():
    """Regressão do invariante central: com ou sem pré-aprovação, o evento
    `hitl` sempre é emitido — o pause já aconteceu no grafo antes disso."""
    events = [_interrupt_event("file_write", {"path": "x.py"})]
    out = [_parse(s) async for s in adapt_stream(_agen(events), "tid")]

    tipos = [e["type"] for e in out]
    assert "hitl" in tipos
