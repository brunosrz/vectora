"""Gateways dinâmicos de LLM (Ollama local, OpenRouter) — descoberta e registro.

Endpoints (exigem auth via middleware):
    GET    /gateways/ollama/models                  — descoberta via {base_url}/api/tags
    GET    /gateways/ollama/registered               — modelos Ollama registrados
    POST   /gateways/ollama/registered                — registra um modelo (tag)
    DELETE /gateways/ollama/registered/{model_id}     — remove

    GET    /gateways/openrouter/status                — key configurada? (mascarada)
    POST   /gateways/openrouter/key                   — valida e salva a key
    DELETE /gateways/openrouter/key                    — remove a key
    GET    /gateways/openrouter/models?q=              — catálogo público (cache ~1h)
    GET    /gateways/openrouter/registered             — modelos OpenRouter registrados
    POST   /gateways/openrouter/registered              — registra um modelo (id)
    DELETE /gateways/openrouter/registered/{model_id}   — remove

Ollama não exige API key — a UI popula o dropdown consultando /api/tags do
host configurado em vez de digitação livre (evita erro de digitação virar
falha silenciosa no chat). OpenRouter exige key (proxy pago multi-provider) —
validada contra /api/v1/auth/key antes de persistir. Em ambos os casos,
`load_llm("ollama:<tag>" | "openrouter:<id>")` (backend/services/utils.py) já
resolve o id dinâmico — este módulo só cuida de descoberta/validação e da
lista de modelos escolhida pelo usuário.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gateways", tags=["gateways"])


async def _get_http_client() -> AsyncIterator[Any]:
    """Dependency do client HTTP usado pelas chamadas de descoberta/catálogo.

    Injeção via FastAPI (`Depends`) em vez de `httpx.AsyncClient()` direto —
    testes trocam o client com `app.dependency_overrides`, resolvido pelo
    próprio FastAPI dentro do mesmo contexto async da request. Evita a classe
    de flake de `unittest.mock.patch("httpx.AsyncClient", ...)` em cima do
    `TestClient` (que despacha a app ASGI numa portal/thread própria — o
    patch pode não estar mais em vigor quando o handler roda, dependendo de
    timing do event loop; reproduzido só em CI Linux, nunca localmente).
    """
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        yield client


_DISCOVERY_TIMEOUT_S = 2.5
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_OPENROUTER_CATALOG_TTL_S = 3600


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


# `table` nunca vem de input externo — só os 2 literais definidos abaixo
# (ollama_registered_models / openrouter_registered_models) — f-string é
# segura aqui, sem risco de SQL injection via request.
async def _ensure_registry_table(db: Any, table: str) -> None:
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id         TEXT PRIMARY KEY,
            tag        TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        )
    """)
    await db.commit()


async def _list_registered(table: str) -> list[RegisteredModel]:
    db = await _get_db()
    await _ensure_registry_table(db, table)
    async with db.execute(
        f"SELECT id, tag, created_at FROM {table} ORDER BY created_at"  # noqa: S608  # nosec B608
    ) as cur:
        rows = await cur.fetchall()
    return [RegisteredModel(id=r[0], tag=r[1], created_at=r[2]) for r in rows]


async def _register(table: str, tag: str) -> RegisteredModel:
    tag = tag.strip()
    if not tag:
        raise HTTPException(status_code=400, detail="tag vazia")

    db = await _get_db()
    await _ensure_registry_table(db, table)
    model_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).isoformat()
    try:
        await db.execute(
            f"INSERT INTO {table} (id, tag, created_at) VALUES (?, ?, ?)",  # noqa: S608  # nosec B608
            (model_id, tag, created_at),
        )
        await db.commit()
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            raise HTTPException(status_code=409, detail="modelo já registrado") from exc
        raise
    return RegisteredModel(id=model_id, tag=tag, created_at=created_at)


async def _unregister(table: str, model_id: str) -> None:
    db = await _get_db()
    await _ensure_registry_table(db, table)
    await db.execute(f"DELETE FROM {table} WHERE id = ?", (model_id,))  # noqa: S608  # nosec B608
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
    return await _list_registered("ollama_registered_models")


@router.post("/ollama/registered")
async def register_ollama_model(body: RegisterModelRequest) -> RegisteredModel:
    return await _register("ollama_registered_models", body.tag)


@router.delete("/ollama/registered/{model_id}")
async def unregister_ollama_model(model_id: str) -> dict:
    await _unregister("ollama_registered_models", model_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# OpenRouter — key (validada contra /auth/key), catálogo público, registro
# ---------------------------------------------------------------------------


class OpenRouterStatus(BaseModel):
    configured: bool
    masked: str


class OpenRouterKeyRequest(BaseModel):
    api_key: str


class OpenRouterModelInfo(BaseModel):
    id: str
    name: str
    context_length: int | None = None


class OpenRouterCatalogResponse(BaseModel):
    models: list[OpenRouterModelInfo]


def _env_file() -> Path:
    p = Path.home() / ".vectora" / ".env"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 10:
        return "•" * len(value)
    return f"{value[:6]}•••{value[-4:]}"


def _remove_env_key(env_file: Path, key: str) -> None:
    if not env_file.exists():
        return
    lines = [
        line
        for line in env_file.read_text(encoding="utf-8").splitlines()
        if not line.startswith(f"{key}=")
    ]
    env_file.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


@router.get("/openrouter/status")
async def get_openrouter_status() -> OpenRouterStatus:
    import os

    raw = os.environ.get("OPENROUTER_API_KEY", "").strip()
    return OpenRouterStatus(configured=bool(raw), masked=_mask_key(raw))


@router.post("/openrouter/key")
async def set_openrouter_key(body: OpenRouterKeyRequest) -> OpenRouterStatus:
    """Valida a key contra GET /auth/key antes de persistir — nunca salva uma
    key que a própria OpenRouter rejeita."""
    import os

    import httpx

    from backend.cli.keys import upsert_env_key

    api_key = body.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="key vazia")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{_OPENROUTER_BASE_URL}/auth/key",
                headers={"Authorization": f"Bearer {api_key}"},
            )
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Erro ao validar key na OpenRouter: {exc}"
        ) from exc

    if resp.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Key rejeitada pela OpenRouter (HTTP {resp.status_code})",
        )

    upsert_env_key(_env_file(), "OPENROUTER_API_KEY", api_key)
    os.environ["OPENROUTER_API_KEY"] = api_key
    from backend.settings import settings

    object.__setattr__(settings, "openrouter_api_key", api_key)

    return OpenRouterStatus(configured=True, masked=_mask_key(api_key))


@router.delete("/openrouter/key")
async def clear_openrouter_key() -> OpenRouterStatus:
    import os

    from backend.settings import settings

    _remove_env_key(_env_file(), "OPENROUTER_API_KEY")
    os.environ.pop("OPENROUTER_API_KEY", None)
    object.__setattr__(settings, "openrouter_api_key", None)
    return OpenRouterStatus(configured=False, masked="")


# `fetched_at` usa `-inf`, não `0.0`, como sentinela de "nunca buscado":
# `time.monotonic()` não conta a partir de zero, reflete o uptime da
# máquina — numa VM efêmera de CI recém-bootada, `now` pode ser menor que
# `_OPENROUTER_CATALOG_TTL_S`, e `0.0` faria `now - fetched_at > TTL` dar
# falso (cache "resetado" pareceria recém-buscado, pulando o fetch e
# devolvendo lista vazia direto). `-inf` garante `now - fetched_at == +inf`
# sempre, não importa o uptime da máquina.
_catalog_cache: dict[str, Any] = {"fetched_at": float("-inf"), "models": []}


@router.get("/openrouter/models")
async def discover_openrouter_models(
    client: Annotated[Any, Depends(_get_http_client)], q: str = ""
) -> OpenRouterCatalogResponse:
    """Catálogo público de modelos da OpenRouter (não exige key). Cacheado em
    memória por _OPENROUTER_CATALOG_TTL_S — a lista muda pouco e evita bater
    na API a cada tecla digitada na busca do frontend."""
    now = time.monotonic()
    if now - _catalog_cache["fetched_at"] > _OPENROUTER_CATALOG_TTL_S:
        try:
            resp = await client.get(f"{_OPENROUTER_BASE_URL}/models")
            resp.raise_for_status()
            data = resp.json()
            _catalog_cache["models"] = [
                OpenRouterModelInfo(
                    id=m["id"],
                    name=m.get("name", m["id"]),
                    context_length=m.get("context_length"),
                )
                for m in data.get("data", [])
                if m.get("id")
            ]
            _catalog_cache["fetched_at"] = now
        except Exception:
            logger.warning(
                "gateways: falha ao buscar catálogo OpenRouter", exc_info=True
            )
            if not _catalog_cache["models"]:
                return OpenRouterCatalogResponse(models=[])

    models: list[OpenRouterModelInfo] = _catalog_cache["models"]
    if q.strip():
        needle = q.strip().lower()
        models = [
            m for m in models if needle in m.id.lower() or needle in m.name.lower()
        ]
    return OpenRouterCatalogResponse(models=models[:100])


@router.get("/openrouter/registered")
async def list_registered_openrouter_models() -> list[RegisteredModel]:
    return await _list_registered("openrouter_registered_models")


@router.post("/openrouter/registered")
async def register_openrouter_model(body: RegisterModelRequest) -> RegisteredModel:
    return await _register("openrouter_registered_models", body.tag)


@router.delete("/openrouter/registered/{model_id}")
async def unregister_openrouter_model(model_id: str) -> dict:
    await _unregister("openrouter_registered_models", model_id)
    return {"ok": True}
