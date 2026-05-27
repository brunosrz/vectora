"""FastAPI app factory do Vectora API.

Modos:
    chat     — API + static files do frontend compilado (Next.js out/)
    headless — apenas API (sem static files) — para Paperclip e integrações

Endpoints registrados:
    POST /vectora.chat.v1.ChatService/StreamChat
    POST /vectora.chat.v1.ChatService/ResumeChat
    GET  /vectora.chat.v1.ChatService/GetTools
    POST /vectora.chat.v1.ThreadService/CreateThread
    POST /vectora.chat.v1.ThreadService/GetThread
    POST /vectora.chat.v1.ThreadService/ListThreads
    POST /vectora.chat.v1.ThreadService/DeleteThread
    POST /vectora.chat.v1.ThreadService/GetHistory
    GET  /health
    GET  /metrics
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vectora.api.handlers.chat import router as chat_router
from vectora.api.handlers.threads import router as thread_router

logger = logging.getLogger(__name__)

# Pasta onde o `make build-chat` deposita o build Next.js
_CHAT_STATIC_DIR = Path(__file__).parent.parent / "chat_static"


@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ARG001 — assinatura do FastAPI
    """Startup / shutdown da aplicação.

    Responsabilidade principal: fechar recursos async-with longos (checkpointer
    SQLite, background workers) corretamente quando o uvicorn recebe SIGINT,
    para que ``Ctrl+C`` derrube o processo sem deixar threads/conexões penduradas.
    """
    logger.info("api/server: startup")
    try:
        yield
    finally:
        logger.info("api/server: shutdown — fechando recursos")

        # 1) Fecha o AsyncSqliteSaver mantido vivo pelo handler de chat
        try:
            from vectora.api.handlers import chat as chat_handler

            if chat_handler._checkpointer_ctx is not None:
                await chat_handler._checkpointer_ctx.__aexit__(None, None, None)
                chat_handler._checkpointer_ctx = None
                chat_handler._graph = None
                logger.info("api/server: checkpointer SQLite fechado")
        except Exception as exc:  # noqa: BLE001
            logger.warning("api/server: erro ao fechar checkpointer: %s", exc)

        # 2) Para o background embedding worker (se rodando)
        try:
            from vectora.services import background as bg

            if bg._worker is not None:
                await bg._worker.stop(timeout_seconds=5)
                bg._worker = None
                logger.info("api/server: background worker parado")
        except Exception as exc:  # noqa: BLE001
            logger.debug("api/server: background worker não estava ativo: %s", exc)


def create_app(*, serve_static: bool = True) -> FastAPI:
    """Cria e configura a aplicação FastAPI do Vectora.

    Args:
        serve_static: Se True, serve o frontend compilado em ``/``.
                      Se False (modo headless), expõe apenas a API.
    """
    from vectora.version import __version__

    app = FastAPI(
        title="Vectora API",
        version=__version__,
        description=(
            "API de chat do Vectora — streaming via SSE, gerenciamento de threads, "
            "autodescoberta de ferramentas."
        ),
        lifespan=_lifespan,
        # Desabilita docs interativas em produção (opcional)
        docs_url="/docs",
        redoc_url=None,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Permite que o frontend Next.js (localhost:3000 em dev) chame a API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Em produção, restringir ao domínio do frontend
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(chat_router)
    app.include_router(thread_router)

    # ── Health + Metrics ──────────────────────────────────────────────────────

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/metrics")
    async def metrics() -> list:
        try:
            from vectora.services.tracer import tracer

            return await tracer.get_recent(n=50)
        except Exception:
            return []

    # ── Static files (frontend compilado) ─────────────────────────────────────
    if serve_static:
        if _CHAT_STATIC_DIR.exists():
            from fastapi.staticfiles import StaticFiles

            # Monta em / — o Next.js static export gera index.html na raiz
            # O router FastAPI tem prioridade sobre os arquivos estáticos.
            app.mount(
                "/",
                StaticFiles(directory=_CHAT_STATIC_DIR, html=True),
                name="chat_static",
            )
            logger.info(
                "api/server: frontend estático disponível em /  (dir=%s)",
                _CHAT_STATIC_DIR,
            )
        else:
            logger.warning(
                "api/server: modo 'chat' mas vectora/chat_static/ não existe. "
                "Execute `make build-chat` para compilar o frontend."
            )

    return app
