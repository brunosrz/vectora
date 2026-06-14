"""Jobs assíncronos da API — ``POST /v1/jobs`` + ``GET /v1/jobs/{id}/events`` (SSE).

``POST`` enfileira um job de um ``kind`` registrado e devolve ``request_id``;
``GET .../events`` faz streaming dos eventos até ``done``/``error``. Registra o
kind ``echo``, que ecoa o payload de volta.

Exemplo:
    POST /v1/jobs  {"kind": "echo", "payload": {"hello": "world"}}
    → {"request_id": "ab12…", "kind": "echo"}
    GET  /v1/jobs/ab12…/events   (SSE)
    → data: {"status": "running", "received": {"hello": "world"}}
    → data: {"status": "done", "echo": {"hello": "world"}}
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.services.jobs import (
    publish_event,
    register_job,
    registered_kinds,
    stream_job_events,
    submit_job,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class SubmitJobRequest(BaseModel):
    """Payload para submeter um job assíncrono."""

    kind: str = Field(..., description="Tipo de job registrado (ex.: 'echo').")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Dados do job, específicos do kind."
    )


class SubmitJobResponse(BaseModel):
    """Resposta com o id de acompanhamento."""

    request_id: str = Field(..., description="Id para streaming via /events.")
    kind: str


# Kind built-in: echo — devolve o payload recebido.
async def _echo_handler(request_id: str, payload: dict) -> None:
    await publish_event(request_id, "running", {"received": payload})
    await publish_event(request_id, "done", {"echo": payload})


register_job("echo", _echo_handler)


@router.post("/v1/jobs", response_model=SubmitJobResponse)
async def submit(req: SubmitJobRequest) -> SubmitJobResponse:
    """Enfileira um job e devolve o ``request_id`` para acompanhamento."""
    if req.kind not in registered_kinds():
        raise HTTPException(
            status_code=400,
            detail=f"kind desconhecido: {req.kind!r}. Disponíveis: {registered_kinds()}",
        )
    request_id = await submit_job(req.kind, req.payload)
    return SubmitJobResponse(request_id=request_id, kind=req.kind)


@router.get("/v1/jobs/{request_id}/events")
async def events(request_id: str) -> StreamingResponse:
    """Streaming SSE dos eventos do job até ``done``/``error`` (ou idle timeout)."""

    async def _gen() -> AsyncIterator[str]:
        async for event in stream_job_events(request_id):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
