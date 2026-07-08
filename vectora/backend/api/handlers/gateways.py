"""Gateway dinâmico de LLM local (Ollama) — descoberta e registro de modelos.

Endpoints (exigem auth via middleware):
    GET    /gateways/ollama/models              — descoberta via {base_url}/api/tags
    GET    /gateways/ollama/registered           — modelos registrados pelo usuário
    POST   /gateways/ollama/registered            — registra um modelo (tag)
    DELETE /gateways/ollama/registered/{model_id} — remove

Ollama não exige API key — a UI popula o dropdown consultando /api/tags do
host configurado em vez de digitação livre (evita erro de digitação virar
falha silenciosa no chat). `load_llm("ollama:<tag>")`
(backend/services/utils.py) já resolve qualquer tag dinâmica — este módulo
só cuida de descoberta e persistência da lista escolhida pelo usuário.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gateways", tags=["gateways"])

_DISCOVERY_TIMEOUT_S = 2.5


class OllamaModelInfo(BaseModel):
    name: str
    size: int | None = None
    modified_at: str | None = None


class OllamaDiscoveryResponse(BaseModel):
    reachable: bool
    models: list[OllamaModelInfo]


class RegisteredModel(BaseModel):
    id: str
    tag: str
    created_at: str


class RegisterModelRequest(BaseModel):
    tag: str


async def _get_db() -> Any:
    """Reusa a conexão SQLite do handler de threads (mesmo arquivo
    ~/.vectora/checkpoints.db) em vez de abrir outra."""
    from backend.api.handlers.threads import _get_db as _threads_db

    return await _threads_db()


async def _ensure_ollama_table(db: Any) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS ollama_registered_models (
            id         TEXT PRIMARY KEY,
            tag        TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        )
    """)
    await db.commit()


@router.get("/ollama/models")
async def discover_ollama_models() -> OllamaDiscoveryResponse:
    """Consulta {OLLAMA_BASE_URL}/api/tags. Host fora do ar → reachable=False,
    nunca deixa a exceção subir como 500 (é esperado o host estar desligado)."""
    import httpx

    from backend.settings import settings

    base_url = (settings.ollama_base_url or "http://127.0.0.1:11434").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=_DISCOVERY_TIMEOUT_S) as client:
            resp = await client.get(f"{base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.info("gateways: Ollama em %s inacessível", base_url, exc_info=True)
        return OllamaDiscoveryResponse(reachable=False, models=[])

    models = [
        OllamaModelInfo(
            name=m["name"], size=m.get("size"), modified_at=m.get("modified_at")
        )
        for m in data.get("models", [])
        if m.get("name")
    ]
    return OllamaDiscoveryResponse(reachable=True, models=models)


@router.get("/ollama/registered")
async def list_registered_ollama_models() -> list[RegisteredModel]:
    db = await _get_db()
    await _ensure_ollama_table(db)
    async with db.execute(
        "SELECT id, tag, created_at FROM ollama_registered_models ORDER BY created_at"
    ) as cur:
        rows = await cur.fetchall()
    return [RegisteredModel(id=r[0], tag=r[1], created_at=r[2]) for r in rows]


@router.post("/ollama/registered")
async def register_ollama_model(body: RegisterModelRequest) -> RegisteredModel:
    tag = body.tag.strip()
    if not tag:
        raise HTTPException(status_code=400, detail="tag vazia")

    db = await _get_db()
    await _ensure_ollama_table(db)
    model_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).isoformat()
    try:
        await db.execute(
            "INSERT INTO ollama_registered_models (id, tag, created_at) VALUES (?, ?, ?)",
            (model_id, tag, created_at),
        )
        await db.commit()
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            raise HTTPException(status_code=409, detail="modelo já registrado") from exc
        raise
    return RegisteredModel(id=model_id, tag=tag, created_at=created_at)


@router.delete("/ollama/registered/{model_id}")
async def unregister_ollama_model(model_id: str) -> dict:
    db = await _get_db()
    await _ensure_ollama_table(db)
    await db.execute("DELETE FROM ollama_registered_models WHERE id = ?", (model_id,))
    await db.commit()
    return {"ok": True}
