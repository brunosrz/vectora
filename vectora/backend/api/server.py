"""FastAPI app factory do Vectora API.

Modos:
    chat     — API + StaticFiles da SPA (``chat/dist/``)
    headless — apenas API (sem catch-all SPA)

Schemas request/response vivem em ``src/api/schemas.py`` (Pydantic).

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
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import Response as FastAPIResponse
from fastapi.staticfiles import StaticFiles

from backend.api.handlers.admin import router as admin_router
from backend.api.handlers.artifacts import router as artifacts_router
from backend.api.handlers.auth import router as auth_router
from backend.api.handlers.background import router as background_router
from backend.api.handlers.chat import router as chat_router
from backend.api.handlers.license import router as license_router
from backend.api.handlers.memory import router as memory_router
from backend.api.handlers.oauth import router as oauth_router
from backend.api.handlers.plugins import router as plugins_router
from backend.api.handlers.share import router as share_router
from backend.api.handlers.skills import router as skills_router
from backend.api.handlers.terminal import router as terminal_router
from backend.api.handlers.threads import router as thread_router
from backend.api.handlers.tools import router as tools_router
from backend.api.handlers.v1.classify import router as v1_classify_router
from backend.api.handlers.v1.extract import router as v1_extract_router
from backend.api.handlers.v1.jobs import router as v1_jobs_router
from backend.api.handlers.webhooks import router as webhooks_router
from backend.api.handlers.workspaces import router as workspace_router
from backend.api.handlers.workspaces import view_router as workspace_view_router

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


def _chat_static_root() -> Path | None:
    """Localiza o bundle estático da SPA do chat.

    Resolução em ordem:
      1. Nuitka onefile — ``__compiled__.containing_dir/chat_static``.
      2. Nuitka onefile — ``$NUITKA_ONEFILE_PARENT/chat_static``.
      3. Override via env ``VECTORA_CHAT_STATIC``.
      4. Dev — ``<repo_root>/chat/dist`` (build Vite).

    Retorna ``None`` se nenhuma das localizações tiver um ``index.html``.
    ``VECTORA_SKIP_STATIC=1`` força proxy para o dev server (modo dev).
    """
    if os.environ.get("VECTORA_SKIP_STATIC"):
        return None

    candidates: list[Path] = []

    compiled = getattr(sys, "__compiled__", None)
    if compiled is not None and hasattr(compiled, "containing_dir"):
        candidates.append(Path(compiled.containing_dir) / "chat_static")

    nuitka_parent = os.environ.get("NUITKA_ONEFILE_PARENT")
    if nuitka_parent:
        candidates.append(Path(nuitka_parent) / "chat_static")

    override = os.environ.get("VECTORA_CHAT_STATIC")
    if override:
        candidates.append(Path(override))

    repo_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    candidates.append(repo_dist)

    for c in candidates:
        if (c / "index.html").is_file():
            return c
    return None


async def _stop_background_worker() -> None:
    """Para o background embedding worker se estiver rodando. Idempotente."""
    from backend.services import background as bg

    worker = bg._worker
    if worker is None:
        return
    bg._worker = None
    try:
        await worker.stop(timeout_seconds=5)
        logger.info("api/server: background worker parado")
    except Exception as exc:
        logger.warning("api/server: erro ao parar background worker: %s", exc)


_LICENSE_REVALIDATE_INTERVAL_S = 6 * 60 * 60  # 6h — espelha o TTL do cache


async def _license_revalidation_loop() -> None:
    """Valida a licença no boot e revalida a cada 6h.

    Nunca derruba o servidor: falha vira warning no log e o estado fica
    visível no banner do chat via ``GET /license/status`` (que lê o cache).
    """
    from backend.services.license import LicenseError, validate_license_async

    while True:
        try:
            info = await validate_license_async()
            logger.info(
                "license: tier=%s status=%s days_remaining=%d cached=%s",
                info.tier,
                info.status,
                info.days_remaining,
                info.cached,
            )
        except LicenseError as exc:
            logger.warning("license: %s", exc)
        except Exception as exc:
            logger.warning("license: falha inesperada na validação — %s", exc)
        await asyncio.sleep(_LICENSE_REVALIDATE_INTERVAL_S)


async def _run_jobs_worker(stop_event: asyncio.Event) -> None:
    """Roda o worker da fila de jobs; encerra silenciosamente em erro fatal."""
    try:
        from backend.services.jobs import run_jobs_worker

        await run_jobs_worker(stop_event=stop_event)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("api/server: jobs worker encerrou: %s", exc)


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

    # E.B-13 — LangSmith tracing opt-in (ativado se langsmith_tracing=true + api_key).
    try:
        from backend.services.tracer import enable_langsmith_tracing

        enable_langsmith_tracing()
    except Exception as exc:
        logger.warning("api/server: falha ao configurar LangSmith tracing: %s", exc)

    # MCP sempre-ativo: o MCP é montado em /mcp, mas o Starlette não roda o
    # lifespan de sub-apps montados. Compomos aqui a parte do lifespan do MCP
    # que importa no boot — persistir em ~/.vectora/.env as keys vindas do
    # ambiente (ex.: GOOGLE_API_KEY passada ao `vectora start`).
    try:
        from backend.mcp.env_bootstrap import bootstrap_env_from_mcp

        if bootstrap_env_from_mcp():
            logger.info("api/server: keys do MCP persistidas a partir do ambiente")
    except Exception as exc:
        logger.warning("api/server: bootstrap de env do MCP falhou: %s", exc)

    # C14 — Setup wizard: avisa o operador se ainda não há usuários cadastrados
    try:
        from backend.services.auth import has_users as _has_users

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
        from backend.api.handlers.threads import ensure_sessions_table

        await ensure_sessions_table()
    except Exception as exc:
        logger.warning("api/server: falha ao criar vectora_sessions: %s", exc)

    if _WARMUP_GRAPH:
        from backend.api.handlers.chat import awarm_graph

        await awarm_graph()

    # Validação de licença: uma no boot (não-bloqueante) + revalidação a cada
    # 6h (TTL do cache). O launcher CLI valida antes do uvicorn, mas deploys
    # via docker/uvicorn direto não passam pelo launcher — sem este loop o
    # servidor nunca validava o VECTORA_TOKEN.
    license_task = asyncio.create_task(_license_revalidation_loop())

    # Sincronização de caches entre réplicas (pub/sub via Redis quando
    # REDIS_URL configurado; no modo lite é local e inofensivo).
    try:
        from backend.services.cache_sync import start_cache_sync

        await start_cache_sync()
    except Exception as exc:
        logger.warning("api/server: cache_sync indisponível: %s", exc)

    # Cache de completions LLM (RedisCache/RedisSemanticCache com Redis;
    # InMemoryCache caso contrário), aplicado via set_llm_cache.
    try:
        from backend.services.cache_llm import init_llm_cache

        init_llm_cache()
    except Exception as exc:
        logger.warning("api/server: cache_llm indisponível: %s", exc)

    # Worker que consome a fila de jobs assíncronos da API.
    jobs_stop = asyncio.Event()
    jobs_worker_task: asyncio.Task[None] = asyncio.create_task(
        _run_jobs_worker(jobs_stop)
    )

    # Worker que processa a fila de embeddings (RAG): lê os chunks PENDING e
    # grava os vetores no LanceDB. SEM ele, tudo que `ingest_docs`/
    # `ingest_directory` enfileiram fica "pending" para sempre e o RAG nunca
    # recupera nada (o `_lifespan` parava o worker no shutdown mas nunca o
    # iniciava no startup).
    try:
        from backend.services.background import get_background_worker

        embedding_worker = await get_background_worker()
        await embedding_worker.start()
    except Exception as exc:
        logger.warning("api/server: falha ao iniciar embedding worker: %s", exc)

    # Tarefas em segundo plano: scheduler das tasks 'interval' (cron) por session.
    try:
        from backend.services.background_tasks import get_scheduler

        await get_scheduler().start()
    except Exception as exc:
        logger.warning("api/server: falha ao iniciar background scheduler: %s", exc)

    # Túnel ngrok — expõe /webhook/* para o mundo externo em desenvolvimento.
    # Só ativo quando NGROK_AUTHTOKEN ou ngrok_enabled=true nas settings.
    try:
        from backend.services.ngrok_tunnel import start_tunnel

        _port = int(os.environ.get("VECTORA_PORT", "8080"))
        start_tunnel(_port)
    except Exception as exc:
        logger.warning("api/server: falha ao iniciar túnel ngrok: %s", exc)

    try:
        yield
    finally:
        logger.info("api/server: shutdown — fechando recursos")
        try:
            from backend.services.background_tasks import get_scheduler as _gs

            await _gs().stop()
        except Exception:
            pass
        try:
            from backend.services.ngrok_tunnel import stop_tunnel

            stop_tunnel()
        except Exception:
            pass
        license_task.cancel()
        try:
            from backend.services.cache_sync import stop_cache_sync

            await stop_cache_sync()
        except Exception:
            logger.debug("api/server: erro ao encerrar cache_sync")

        # Para o worker de jobs e fecha a message queue (Redis Streams).
        jobs_stop.set()
        jobs_worker_task.cancel()
        try:
            from backend.services.mq import get_mq

            await get_mq().close()
        except Exception:
            logger.debug("api/server: erro ao fechar message queue")
        from backend.api.handlers.chat import aclose_graph
        from backend.services.pty_registry import pty_registry

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

    ``serve_static=False`` desliga o catch-all que serve a SPA Vite — usado
    em testes para que rotas não-API retornem 404 reais em vez de devolver
    ``index.html`` ou cair no proxy dev.
    """
    from backend.version import __version__

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
    from backend.api.middleware.auth import AuthMiddleware

    app.add_middleware(AuthMiddleware)

    # ── Rate limiting ─────────────────────────────────────────────────────────
    from backend.api.middleware.rate_limit import attach_limiter

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
        else [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
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
    app.include_router(share_router)
    app.include_router(memory_router)
    app.include_router(oauth_router)
    app.include_router(webhooks_router)
    app.include_router(admin_router)
    app.include_router(workspace_router)
    app.include_router(workspace_view_router)
    app.include_router(artifacts_router)
    app.include_router(plugins_router)
    app.include_router(skills_router)
    app.include_router(license_router)
    app.include_router(tools_router)
    app.include_router(terminal_router)
    app.include_router(background_router)
    # REST API v1 — structured output endpoints
    app.include_router(v1_extract_router)
    app.include_router(v1_classify_router)
    # REST API v1 — jobs assíncronos
    app.include_router(v1_jobs_router)

    # ── MCP server (sempre-ativo, montado em /mcp) ────────────────────────────
    # Sobe junto de todo boot do backend (vectora start) reusando a MESMA
    # instância FastMCP — sem processo separado. Agentes externos (Claude
    # Desktop/Code) conectam em /mcp mesmo com a janela do app oculta. Montado
    # ANTES do catch-all da SPA para que /mcp/* não caia no index.html.
    try:
        from backend.mcp.server import mcp_asgi_app

        app.mount("/mcp", mcp_asgi_app())
        logger.info("api/server: MCP montado em /mcp")
    except Exception as exc:
        logger.warning("api/server: falha ao montar MCP em /mcp: %s", exc)

    # ── Discovery Layer — schema das tools (Web UI D1.1) ──────────────────────
    @app.get("/api/tools/schema")
    async def tools_schema() -> dict:
        from backend.nodes.tools import ALL_TOOLS

        tools_data = []
        for t in ALL_TOOLS:
            schema: dict = {}
            try:
                args_schema = getattr(t, "args_schema", None)
                if args_schema is not None and hasattr(
                    args_schema, "model_json_schema"
                ):
                    schema = args_schema.model_json_schema()
            except Exception:
                pass
            tools_data.append(
                {
                    "name": t.name,
                    "description": (t.description or "").split("\n")[0][:200],
                    "args_schema": schema,
                    "render_hint": (getattr(t, "extras", None) or {}).get(
                        "render_hint", "json"
                    ),
                }
            )
        return {"version": "1", "tool_count": len(tools_data), "tools": tools_data}

    # ── Health + Metrics ──────────────────────────────────────────────────────

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/metrics")
    async def metrics() -> list:
        try:
            from backend.services.tracer import tracer

            return await tracer.get_recent(n=50)
        except Exception:
            return []

    if not serve_static:
        return app

    # ── SPA Vite (preferido) ──────────────────────────────────────────────────
    # Em produção (binário Nuitka) ou após `pnpm --dir chat build`, servimos
    # o bundle estático diretamente. O catch-all devolve `index.html` para
    # rotas client-side (TanStack Router resolve no browser).
    chat_static = _chat_static_root()
    if chat_static is not None:
        logger.info("api/server: servindo SPA estática de %s", chat_static)

        # Mount em /assets/ (e diretórios afins gerados pelo Vite) — caminho
        # com extensão tem prioridade; rotas "limpas" caem no catch-all.
        app.mount(
            "/assets",
            StaticFiles(directory=str(chat_static / "assets")),
            name="vite-assets",
        )

        # Arquivos da raiz (favicon, manifest, ícones) servidos sob demanda.
        @app.get("/{filename:path}", include_in_schema=False)
        async def _spa_or_static(request: Request, filename: str) -> FastAPIResponse:
            # Se for arquivo real na raiz do bundle, serve direto.
            candidate = (chat_static / filename).resolve()
            try:
                candidate.relative_to(chat_static.resolve())
            except ValueError:
                # path traversal — bloqueia
                return FastAPIResponse(status_code=404)
            if candidate.is_file():
                return FileResponse(candidate)
            # Caso contrário, devolve index.html — o router client-side
            # processa a rota.
            return FileResponse(chat_static / "index.html")

        return app

    # ── Frontend proxy (fallback dev sem build) ───────────────────────────────
    # Quando `chat/dist/` não existe, encaminhamos qualquer rota não-API para
    # o servidor de dev externo (Vite em :5173 ou Next.js legado em :3000).
    # Configurável via VECTORA_FRONTEND_URL.
    _frontend_url = os.environ.get(
        "VECTORA_FRONTEND_URL", "http://localhost:5173"
    ).rstrip("/")

    proxy_skip_req_headers = frozenset(
        {"host", "connection", "transfer-encoding", "accept-encoding"}
    )
    proxy_skip_resp_headers = frozenset(
        {"transfer-encoding", "connection", "content-encoding", "content-length"}
    )

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
            # Mensagem hardcoded em pt-BR — backend ainda não tem i18n
            # estruturado (ver `src/ui/strings/` futuro, espelhando o CSV
            # de `chat/lib/i18n/strings.csv.ts`). `.encode("utf-8")` evita
            # restrição ASCII-only dos bytes literals do Python.
            return FastAPIResponse(
                content=(
                    "<html><body><h2>Frontend indisponível</h2>"
                    "<p>Rode <code>pnpm --dir chat dev</code> ou faça o build "
                    "com <code>pnpm --dir chat build</code> para gerar "
                    "<code>chat/dist/</code>.</p></body></html>"
                ).encode(),
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
