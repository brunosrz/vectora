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

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response as FastAPIResponse

from src.api.handlers.admin import router as admin_router
from src.api.handlers.artifacts import router as artifacts_router
from src.api.handlers.auth import router as auth_router
from src.api.handlers.chat import router as chat_router
from src.api.handlers.memory import router as memory_router
from src.api.handlers.oauth import router as oauth_router
from src.api.handlers.plugins import router as plugins_router
from src.api.handlers.terminal import router as terminal_router
from src.api.handlers.threads import router as thread_router
from src.api.handlers.tools import router as tools_router
from src.api.handlers.workspaces import router as workspace_router
from src.api.handlers.workspaces import view_router as workspace_view_router

logger = logging.getLogger(__name__)

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
    from src.services import background as bg

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
        from src.services.auth import has_users as _has_users

        if not await _has_users():
            logger.warning(
                "\n\n"
                "  ✨  Vectora aguardando setup inicial.\n"
                "      Abra o chat no browser e crie o primeiro usuário.\n"
                "      O primeiro usuário se torna root automaticamente.\n"
            )
    except Exception:
        pass  # Não bloqueia o startup se o DB ainda não estiver criado

    # Garante que a tabela vectora_sessions existe antes do primeiro request.
    # Evita race com AsyncSqliteSaver do LangGraph (mesmo arquivo .db) que
    # podia fazer o CREATE TABLE silenciar e get_thread/list_threads
    # retornarem 500 "no such table" até o servidor reiniciar.
    try:
        from src.api.handlers.threads import ensure_sessions_table

        await ensure_sessions_table()
    except Exception as exc:
        logger.warning("api/server: falha ao criar vectora_sessions: %s", exc)

    if _WARMUP_GRAPH:
        from src.api.handlers.chat import awarm_graph

        await awarm_graph()

    try:
        yield
    finally:
        logger.info("api/server: shutdown — fechando recursos")
        from src.api.handlers.chat import aclose_graph
        from src.services.pty_registry import pty_registry

        # Encerra PTYs ANTES do hard-exit em main.py — evita processos órfãos.
        try:
            pty_registry.close_all()
        except Exception:
            logger.debug("api/server: erro ao encerrar PTYs")

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


def create_app(serve_static: bool = True) -> FastAPI:
    """Cria e configura a aplicação FastAPI do Vectora.

    ``serve_static=False`` desliga o catch-all que faz proxy do frontend Next.js
    — usado em testes para que rotas não-API retornem 404 reais em vez de cair
    no proxy.
    """
    from src.version import __version__

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
    from src.api.middleware.auth import AuthMiddleware

    app.add_middleware(AuthMiddleware)

    # ── Rate limiting ─────────────────────────────────────────────────────────
    from src.api.middleware.rate_limit import attach_limiter

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
    app.include_router(workspace_router)
    app.include_router(workspace_view_router)
    app.include_router(artifacts_router)
    app.include_router(plugins_router)
    app.include_router(tools_router)
    app.include_router(terminal_router)

    # ── Health + Metrics ──────────────────────────────────────────────────────

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/metrics")
    async def metrics() -> list:
        try:
            from src.services.tracer import tracer

            return await tracer.get_recent(n=50)
        except Exception:
            return []

    # ── Frontend proxy (catch-all) ────────────────────────────────────────────
    # Encaminha qualquer rota não-API para o servidor Next.js.
    # DEVE ser registrado por último para não sobrepor endpoints reais.
    # Configurável via VECTORA_FRONTEND_URL (padrão: http://localhost:3000).
    _frontend_url = os.environ.get(
        "VECTORA_FRONTEND_URL", "http://localhost:3000"
    ).rstrip("/")

    # Headers de request que não devem ser encaminhados ao upstream
    proxy_skip_req_headers = frozenset(
        {"host", "connection", "transfer-encoding", "accept-encoding"}
    )
    # Headers de resposta gerenciados pelo FastAPI/Starlette — não encaminhar
    # para evitar conflitos (ex: content-length incorreto após descompressão)
    proxy_skip_resp_headers = frozenset(
        {"transfer-encoding", "connection", "content-encoding", "content-length"}
    )

    if not serve_static:
        return app

    @app.api_route("/{path:path}", methods=["GET", "HEAD"])
    async def _frontend_proxy(request: Request, path: str) -> FastAPIResponse:
        """Proxy reverso: encaminha requests não-API para o Next.js frontend.

        Notas importantes:
        - accept-encoding é suprimido para o upstream receber conteúdo plain
          (sem gzip), evitando mismatch de content-length na resposta.
        - content-length é omitido da resposta — FastAPI recalcula com base
          no conteúdo já descomprimido pelo httpx.
        - Endpoints SSE/streaming do Next.js dev (ex: /_next/webpack-hmr)
          são redirecionados direto para o frontend, sem buffer.
        """
        target = f"{_frontend_url}/{path}"
        if request.url.query:
            target = f"{target}?{request.url.query}"

        fwd_headers = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in proxy_skip_req_headers
        }
        # Pede conteúdo sem compressão — httpx decodifica gzip mas não atualiza
        # content-length, causando leitura truncada no browser.
        fwd_headers["accept-encoding"] = "identity"

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                upstream = await client.request(
                    method=request.method,
                    url=target,
                    headers=fwd_headers,
                    content=await request.body(),
                )
            resp_headers = {
                k: v
                for k, v in upstream.headers.items()
                if k.lower() not in proxy_skip_resp_headers
            }
            return FastAPIResponse(
                content=upstream.content,
                status_code=upstream.status_code,
                headers=resp_headers,
                media_type=upstream.headers.get("content-type"),
            )
        except httpx.ConnectError:
            logger.warning("frontend_proxy: frontend indisponível em %s", _frontend_url)
            return FastAPIResponse(
                content=(
                    b"<html><body><h2>Frontend indispon\xedvel</h2>"
                    b"<p>Certifique-se que o servidor Next.js est\xe1 rodando.</p></body></html>"
                ),
                status_code=502,
                media_type="text/html; charset=utf-8",
            )
        except Exception as exc:
            logger.warning("frontend_proxy: erro ao encaminhar /%s: %s", path, exc)
            return FastAPIResponse(
                content=b'{"detail":"Erro no proxy do frontend"}',
                status_code=502,
                media_type="application/json",
            )

    return app
