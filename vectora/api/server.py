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

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vectora.api.handlers.admin import router as admin_router
from vectora.api.handlers.auth import router as auth_router
from vectora.api.handlers.chat import router as chat_router
from vectora.api.handlers.memory import router as memory_router
from vectora.api.handlers.oauth import router as oauth_router
from vectora.api.handlers.threads import router as thread_router

logger = logging.getLogger(__name__)

# Pasta onde o `make build-chat` deposita o build Next.js
_CHAT_STATIC_DIR = Path(__file__).parent.parent / "chat_static"


# Tempo máximo total para o shutdown — depois disso, `os._exit` em main.py
# encerra o processo de qualquer jeito. Configurável via env.
_SHUTDOWN_TIMEOUT_S = float(os.environ.get("VECTORA_SHUTDOWN_TIMEOUT_S", "10"))

# Pré-aquecer o grafo no startup. Reduz latência da 1ª request (~3-5s) em troca
# de inicialização mais lenta. Default desligado (dev-friendly).
_WARMUP_GRAPH = os.environ.get("VECTORA_WARMUP_GRAPH", "0").lower() in {
    "1",
    "true",
    "yes",
}


async def _stop_background_worker() -> None:
    """Para o background embedding worker se estiver rodando. Idempotente."""
    from vectora.services import background as bg

    worker = bg._worker
    if worker is None:
        return
    bg._worker = None
    try:
        await worker.stop(timeout_seconds=5)
        logger.info("api/server: background worker parado")
    except Exception as exc:
        logger.warning("api/server: erro ao parar background worker: %s", exc)


@asynccontextmanager
async def _lifespan(app: FastAPI):  # type: ignore[return]  # noqa: ANN202
    """Startup / shutdown da aplicação.

    **Startup**: opcionalmente pré-aquece o grafo (``VECTORA_WARMUP_GRAPH=1``).

    **Shutdown**: fecha recursos async-with longos (background worker primeiro,
    depois checkpointer SQLite) **em paralelo**, com timeout global. Recursos
    independentes não precisam esperar uns aos outros.

    O hard-exit final (``os._exit(0)`` em ``main.py``) cobre o caso de threads
    não-daemon de libs externas (langsmith, httpx, cohere) que ignoram cancel.
    """
    logger.info("api/server: startup")

    # C14 — Setup wizard: avisa o operador se ainda não há usuários cadastrados
    try:
        from vectora.services.auth import has_users as _has_users

        if not await _has_users():
            logger.warning(
                "\n\n"
                "  ✨  Vectora aguardando setup inicial.\n"
                "      Abra o chat no browser e crie o primeiro usuário.\n"
                "      O primeiro usuário se torna root automaticamente.\n"
            )
    except Exception:
        pass  # Não bloqueia o startup se o DB ainda não estiver criado

    if _WARMUP_GRAPH:
        from vectora.api.handlers.chat import awarm_graph

        await awarm_graph()

    try:
        yield
    finally:
        logger.info("api/server: shutdown — fechando recursos")
        from vectora.api.handlers.chat import aclose_graph

        # Ordem lógica: parar workers que podem estar usando o grafo ANTES de
        # fechar o checkpointer. Mas como ambos têm `try/except` internos e são
        # independentes na prática, rodamos em paralelo via `gather` para
        # encurtar o tempo total de shutdown.
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    _stop_background_worker(),
                    aclose_graph(),
                    return_exceptions=True,
                ),
                timeout=_SHUTDOWN_TIMEOUT_S,
            )
        except TimeoutError:
            logger.warning(
                "api/server: shutdown excedeu %.1fs — hard-exit cuidará do resto",
                _SHUTDOWN_TIMEOUT_S,
            )


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

    # ── Auth middleware ───────────────────────────────────────────────────────
    from vectora.api.middleware.auth import AuthMiddleware

    app.add_middleware(AuthMiddleware)

    # ── Rate limiting ─────────────────────────────────────────────────────────
    from vectora.api.middleware.rate_limit import attach_limiter

    attach_limiter(app)

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Permite que o frontend Next.js (localhost:3000 em dev) chame a API.
    # Em produção, restringir CORS_ORIGINS ao domínio real do frontend.
    # Com allow_credentials=True, allow_origins não pode ser "*" — precisamos
    # de origens explícitas quando cookies httpOnly são usados.
    _cors_origins_env = os.environ.get("VECTORA_CORS_ORIGINS", "")
    _cors_origins = (
        [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
        if _cors_origins_env
        else ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(thread_router)
    app.include_router(memory_router)
    app.include_router(oauth_router)
    app.include_router(admin_router)

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
