"""Tool `terminal`: streaming real via `_drain_terminal_output` + stdin interativo.

Detecta "processo vivo mas sem output novo há alguns segundos"
(provavelmente esperando input) e devolve o controle ao agente, que pode
responder via `terminal(stdin_input=...)` no mesmo processo em vez de
travar a chamada de tool inteira.
"""

from __future__ import annotations

import sys

import pytest

from backend.tools.context import ctx_from_config
from backend.tools.fs import _pending_terminal, terminal


def _config(thread_id: str = "t1") -> dict:
    return {"configurable": {"thread_id": thread_id, "workspace_id": None}}


@pytest.fixture(autouse=True)
def _clear_pending():
    _pending_terminal.clear()
    yield
    _pending_terminal.clear()


@pytest.mark.asyncio
async def test_terminal_command_idle_waiting_input_then_resumed_via_stdin(monkeypatch):
    """Comando que fica esperando input registra pendência e é retomado com stdin_input."""
    monkeypatch.setattr("backend.tools.fs._IDLE_TIMEOUT", 0.1)
    monkeypatch.setattr("backend.tools.fs._HARD_TIMEOUT", 5.0)

    script = (
        "import sys; print('pronto'); sys.stdout.flush(); "
        "resp = input(); print('recebido:' + resp)"
    )
    command = f'{sys.executable} -c "{script}"'

    result = await terminal(command=command, ctx=ctx_from_config(_config("t1")))

    assert "esperando input" in result
    assert "t1" in _pending_terminal

    resumed = await terminal(stdin_input="ola", ctx=ctx_from_config(_config("t1")))

    assert "recebido:ola" in resumed
    assert "t1" not in _pending_terminal


@pytest.mark.asyncio
async def test_terminal_stdin_input_without_pending_process_returns_error():
    """stdin_input sem nenhum comando pendente na thread é um erro claro, não um crash."""
    result = await terminal(
        stdin_input="ola", ctx=ctx_from_config(_config("sem-pendencia"))
    )

    assert result.startswith("Error:")
    assert "sem-pendencia" not in _pending_terminal


@pytest.mark.asyncio
async def test_terminal_without_command_or_stdin_input_returns_error():
    result = await terminal(ctx=ctx_from_config(_config("t2")))

    assert result.startswith("Error:")
