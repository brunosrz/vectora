"""AI Jail — backend.sandbox.worker: protocolo JSON-lines do loop que roda
DENTRO do jail (exec/read_file/write_file)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.sandbox import worker


@pytest.mark.asyncio
async def test_exec_returns_stdout_stderr_exit_code(monkeypatch):
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(b"ok\n", b""))
    proc.returncode = 0
    monkeypatch.setattr(
        worker.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)
    )

    resp = await worker.handle_request(
        {"op": "exec", "id": 1, "command": ["echo", "ok"]}
    )

    assert resp == {"id": 1, "stdout": "ok\n", "stderr": "", "exit_code": 0}


@pytest.mark.asyncio
async def test_exec_nonzero_exit_code_propagated(monkeypatch):
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(b"", b"boom\n"))
    proc.returncode = 2
    monkeypatch.setattr(
        worker.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)
    )

    resp = await worker.handle_request({"op": "exec", "id": 2, "command": ["false"]})

    assert resp["exit_code"] == 2
    assert resp["stderr"] == "boom\n"


@pytest.mark.asyncio
async def test_exec_command_not_found_returns_error_not_exception(monkeypatch):
    async def _raise(*_args, **_kwargs):
        raise FileNotFoundError("nope")

    monkeypatch.setattr(worker.asyncio, "create_subprocess_exec", _raise)

    resp = await worker.handle_request({"op": "exec", "id": 3, "command": ["nope"]})

    assert resp["id"] == 3
    assert "error" in resp


@pytest.mark.asyncio
async def test_write_then_read_file_roundtrip(tmp_path):
    target = tmp_path / "f.txt"

    write_resp = await worker.handle_request(
        {"op": "write_file", "id": 4, "path": str(target), "content": "olá"}
    )
    read_resp = await worker.handle_request(
        {"op": "read_file", "id": 5, "path": str(target)}
    )

    assert write_resp == {"id": 4, "ok": True}
    assert read_resp == {"id": 5, "content": "olá"}


@pytest.mark.asyncio
async def test_read_file_missing_returns_error_not_exception(tmp_path):
    resp = await worker.handle_request(
        {"op": "read_file", "id": 6, "path": str(tmp_path / "missing.txt")}
    )

    assert resp["id"] == 6
    assert "error" in resp


@pytest.mark.asyncio
async def test_unknown_op_returns_error():
    resp = await worker.handle_request({"op": "delete_everything", "id": 7})

    assert resp == {"id": 7, "error": "op desconhecida: 'delete_everything'"}
