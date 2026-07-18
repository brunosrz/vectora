"""adapt_stream registra delegação de subagente (tool `task`) na aba Tarefas.

O deepagents (SubAgentMiddleware) expõe `task(subagent_type=, description=)`
como uma tool comum — o adaptador intercepta seu on_tool_start/on_tool_end
via observação de eventos (sem tocar o pacote deepagents vendorizado) e
persiste via `backend.scheduling.background_tasks.record_subagent_delegation`.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.api.adapters import adapt_stream


@pytest.fixture(autouse=True)
def _isolated(_no_thread_persistence):
    pass


def _parse(sse: str) -> dict:
    assert sse.startswith("data: ")
    return json.loads(sse[len("data: ") :].strip())


async def _agen(events):
    for ev in events:
        yield ev


def _task_start(
    subagent_type: str, description: str, run_id: str = "run-task-1"
) -> dict:
    return {
        "event": "on_tool_start",
        "name": "task",
        "run_id": run_id,
        "data": {"input": {"subagent_type": subagent_type, "description": description}},
    }


def _task_end(
    output: str = "feito", *, is_error: bool = False, run_id: str = "run-task-1"
) -> dict:
    out = (
        SimpleNamespace(content="erro na delegação", status="error")
        if is_error
        else output
    )
    return {
        "event": "on_tool_end",
        "name": "task",
        "run_id": run_id,
        "data": {"output": out},
    }


@pytest.mark.asyncio
async def test_delegation_recorded_with_user_id(monkeypatch):
    """on_tool_end de `task` com user_id registra a delegação."""
    mock_record = AsyncMock()
    monkeypatch.setattr(
        "backend.scheduling.background_tasks.record_subagent_delegation", mock_record
    )

    events = [
        _task_start("coder", "Crie um arquivo X"),
        _task_end("Arquivo criado com sucesso"),
    ]
    _ = [_parse(s) async for s in adapt_stream(_agen(events), "tid", user_id="u1")]

    mock_record.assert_awaited_once()
    assert mock_record.await_args is not None
    kwargs = mock_record.await_args.kwargs
    assert kwargs["session_id"] == "tid"
    assert kwargs["user_id"] == "u1"
    assert kwargs["subagent_type"] == "coder"
    assert kwargs["description"] == "Crie um arquivo X"
    assert kwargs["status"] == "done"


@pytest.mark.asyncio
async def test_delegation_marks_failed_status_on_tool_error(monkeypatch):
    """Erro/borda: resultado de erro da tool vira status='failed'."""
    mock_record = AsyncMock()
    monkeypatch.setattr(
        "backend.scheduling.background_tasks.record_subagent_delegation", mock_record
    )

    events = [
        _task_start("search", "Pesquise X"),
        _task_end(is_error=True),
    ]
    _ = [_parse(s) async for s in adapt_stream(_agen(events), "tid", user_id="u1")]

    assert mock_record.await_args is not None
    kwargs = mock_record.await_args.kwargs
    assert kwargs["status"] == "error"


@pytest.mark.asyncio
async def test_delegation_skipped_without_user_id(monkeypatch):
    """Erro/borda: sem user_id (sessão anônima/CLI), não tenta persistir."""
    mock_record = AsyncMock()
    monkeypatch.setattr(
        "backend.scheduling.background_tasks.record_subagent_delegation", mock_record
    )

    events = [_task_start("coder", "x"), _task_end("ok")]
    _ = [_parse(s) async for s in adapt_stream(_agen(events), "tid")]

    mock_record.assert_not_awaited()


@pytest.mark.asyncio
async def test_delegation_failure_never_breaks_the_stream(monkeypatch):
    """Erro/borda: falha ao registrar não deve impedir o stream de completar."""
    monkeypatch.setattr(
        "backend.scheduling.background_tasks.record_subagent_delegation",
        AsyncMock(side_effect=RuntimeError("db indisponível")),
    )

    events = [_task_start("coder", "x"), _task_end("ok")]
    out = [_parse(s) async for s in adapt_stream(_agen(events), "tid", user_id="u1")]

    # O stream não deve abortar: eventos de tool_call/tool_result normais saem.
    types = [e["type"] for e in out]
    assert "tool_call" in types
    assert "tool_result" in types


@pytest.mark.asyncio
async def test_non_task_tools_do_not_trigger_delegation(monkeypatch):
    """Tools normais (não `task`) não devem disparar o registro de subagente."""
    mock_record = AsyncMock()
    monkeypatch.setattr(
        "backend.scheduling.background_tasks.record_subagent_delegation", mock_record
    )

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
    _ = [_parse(s) async for s in adapt_stream(_agen(events), "tid", user_id="u1")]

    mock_record.assert_not_awaited()
