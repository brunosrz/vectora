"""Fila de jobs assíncronos (``services/jobs.py``) sobre ``MemoryMQ``."""

from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

from backend.scheduling.mq import reset_mq
from backend.services import jobs


@pytest.fixture(autouse=True)
def _reset():
    reset_mq()  # garante MemoryMQ limpo (sem redis_url nos testes)
    jobs._handlers.clear()
    yield
    reset_mq()
    jobs._handlers.clear()


async def _drain(request_id: str, *, idle: float = 5.0) -> list[dict]:
    return [ev async for ev in jobs.stream_job_events(request_id, idle_timeout=idle)]


async def test_submit_retorna_request_id() -> None:
    rid = await jobs.submit_job("echo", {"a": 1})
    assert isinstance(rid, str) and len(rid) == 32


async def test_job_echo_ponta_a_ponta() -> None:
    async def echo(request_id: str, payload: dict) -> None:
        await jobs.publish_event(request_id, "running", {"received": payload})
        await jobs.publish_event(request_id, "done", {"echo": payload})

    jobs.register_job("echo", echo)
    assert "echo" in jobs.registered_kinds()

    rid = await jobs.submit_job("echo", {"hello": "world"})
    stop = asyncio.Event()
    worker = asyncio.create_task(jobs.run_jobs_worker(stop_event=stop))
    try:
        events = await _drain(rid)
    finally:
        stop.set()
        worker.cancel()

    assert events[0]["status"] == "running"
    assert events[-1] == {"status": "done", "echo": {"hello": "world"}}


async def test_kind_desconhecido_publica_error() -> None:
    rid = await jobs.submit_job("inexistente", {})
    stop = asyncio.Event()
    worker = asyncio.create_task(jobs.run_jobs_worker(stop_event=stop))
    try:
        events = await _drain(rid)
    finally:
        stop.set()
        worker.cancel()

    assert events[-1]["status"] == "error"
    assert "inexistente" in events[-1]["error"]


async def test_handler_excecao_publica_error() -> None:
    async def boom(request_id: str, payload: dict) -> None:
        raise RuntimeError("falhou de propósito")

    jobs.register_job("boom", boom)
    rid = await jobs.submit_job("boom", {})
    stop = asyncio.Event()
    worker = asyncio.create_task(jobs.run_jobs_worker(stop_event=stop))
    try:
        events = await _drain(rid)
    finally:
        stop.set()
        worker.cancel()

    assert events[-1]["status"] == "error"
    assert "falhou de propósito" in events[-1]["error"]


# ---------------------------------------------------------------------------
# POST /v1/jobs (HTTP) — cobre o binding real do FastAPI + o decorator de rate
# limit por tier (backend/api/handlers/v1/jobs.py). Endpoint leve o bastante
# (kind "echo", sem LLM) para testar via TestClient sem mocks pesados.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _jobs_app():
    os.environ["VECTORA_AUTH_REQUIRED"] = "false"
    from backend.api.server import create_app

    return create_app()


@pytest.fixture(scope="module")
def _jobs_client(_jobs_app):
    return TestClient(_jobs_app, raise_server_exceptions=False)


def test_submit_via_http_returns_request_id(_jobs_client: TestClient) -> None:
    # `_reset` (autouse) limpa jobs._handlers entre testes — o registro de
    # "echo" feito na importação de v1/jobs.py só vale até o primeiro teardown.
    # Reregistra aqui para não depender de ordem de execução dos testes.
    async def echo(request_id: str, payload: dict) -> None:
        await jobs.publish_event(request_id, "running", {"received": payload})
        await jobs.publish_event(request_id, "done", {"echo": payload})

    jobs.register_job("echo", echo)

    resp = _jobs_client.post("/v1/jobs", json={"kind": "echo", "payload": {"a": 1}})
    assert resp.status_code == 200
    body = resp.json()
    assert body["kind"] == "echo"
    assert isinstance(body["request_id"], str) and len(body["request_id"]) == 32


def test_submit_via_http_unknown_kind_400(_jobs_client: TestClient) -> None:
    resp = _jobs_client.post("/v1/jobs", json={"kind": "nao-existe", "payload": {}})
    assert resp.status_code == 400
