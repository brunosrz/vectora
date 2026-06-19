"""Vectora CLI — ponto de entrada unificado.

vectora                 imprime o help (descobre a CLI de configuração)
vectora start           sobe backend + MCP + SPA (fullstack)
vectora start --headless  sobe sem janela (bandeja + backend + MCP)

Configuração (operacional, para VPS via SSH):
  vectora config                 mostra ~/.vectora/settings.json
  vectora config --set K=V       edita uma chave de settings
  vectora config keys            wizard de API keys + LLM provider
  vectora config docker [up|down|status]
  vectora config qdrant <url> [--api-key KEY]
  vectora config redis <url>
  vectora storage <ação>         migrations, diagnóstico, backup/restore
  vectora auth <ação>            signup | login | logout | whoami | refresh
  vectora traces                 spans de observabilidade
  vectora sessions               lista as sessões salvas
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import os
import socket
import sys
from pathlib import Path


def _find_free_port(preferred: int | None = None) -> int:
    """Devolve uma porta TCP livre em 127.0.0.1.

    Se ``preferred`` for fornecida e estiver disponível, é retornada como está;
    caso contrário (ou se já estiver ocupada), o SO escolhe uma porta efêmera.
    """
    if preferred is not None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", preferred))
                return preferred
            except OSError:
                pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


# Configure UTF-8 on Windows before any output
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Project root no sys.path (necessário ao rodar como script direto). Usa
# parent.parent (raiz), não parent (pacote src/), para não sombrear pacotes de
# terceiros com o mesmo nome (ex.: src/mcp/ sombrearia o pacote `mcp`).
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.services.log_setup import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    from backend.version import __version__

    parser = argparse.ArgumentParser(
        prog="vectora",
        description="Vectora — workspace de IA com RAG e MCP nativos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""exemplos:
  vectora                              imprime este help
  vectora start                        sobe backend + MCP + SPA (fullstack)
  vectora start --headless             sobe sem janela (bandeja + backend + MCP)
  vectora start --port 9000            porta custom
  vectora config                       mostra a configuração atual
  vectora config --set verbosity=2
  vectora config keys                  wizard de API keys + LLM provider
  vectora config docker up             sobe Postgres + Redis + Qdrant local
  vectora config qdrant https://… --api-key KEY
  vectora config redis redis://…
  vectora storage info                 status dos backends de dados
  vectora auth login                   autentica no servidor configurado
  vectora traces                       mostra os últimos 50 spans
  vectora sessions                     lista as sessões salvas
""",
    )

    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"vectora {__version__}",
    )

    sub = parser.add_subparsers(dest="command", metavar="subcommand")

    # ── start — backend + MCP + SPA (fullstack/headless) ──────────────────────
    start_p = sub.add_parser(
        "start",
        help="Sobe o Vectora completo (backend + MCP + SPA)",
        description=(
            "Sobe o backend completo (FastAPI + /mcp) servindo a SPA via uvicorn.\n\n"
            "  vectora start              -> fullstack (janela quando há desktop)\n"
            "  vectora start --headless   -> só bandeja + backend + MCP, sem janela\n\n"
            "Em host sem display (VPS/Docker), roda como servidor puro."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    start_p.add_argument(
        "--headless",
        action="store_true",
        help="Não abre janela — mantém backend + MCP + bandeja ativos.",
    )
    start_p.add_argument("--host", default="0.0.0.0", help="Host de escuta")  # noqa: S104  # nosec B104
    start_p.add_argument("--port", type=int, default=None, help="Porta (default: 8080)")
    start_p.add_argument(
        "--ssl-certfile",
        metavar="PEM",
        default=None,
        help=(
            "Certificado TLS (PEM fullchain) — sobe em https://. Também via env "
            "SSL_CERTFILE. Necessário para Secure Context ao acessar via IP de LAN."
        ),
    )
    start_p.add_argument(
        "--ssl-keyfile",
        metavar="PEM",
        default=None,
        help="Chave privada TLS correspondente. Também via env SSL_KEYFILE.",
    )

    # ── config — settings + keys/docker/qdrant/redis ──────────────────────────
    config_p = sub.add_parser(
        "config",
        help="Configuração do aplicativo (settings, keys, docker, qdrant, redis)",
        description=(
            "Sem ação, mostra ou edita ~/.vectora/settings.json.\n"
            "Com ação:\n"
            "  keys                 wizard de API keys + LLM provider\n"
            "  docker [up|down|status]  infra local (Postgres, Redis, Qdrant)\n"
            "  qdrant <url> [--api-key KEY]  testa e persiste Qdrant\n"
            "  redis <url>          testa e persiste Redis"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    config_p.add_argument(
        "config_action",
        nargs="?",
        default=None,
        choices=["keys", "docker", "qdrant", "redis"],
        help="Ação de configuração (sem ação = mostra/edita settings).",
    )
    config_p.add_argument(
        "config_arg",
        nargs="?",
        default=None,
        help="Argumento da ação: up|down|status (docker) ou URL (qdrant/redis).",
    )
    config_p.add_argument(
        "--api-key",
        dest="api_key",
        default=None,
        help="[qdrant] API key opcional.",
    )
    config_p.add_argument(
        "--set",
        metavar="KEY=VALUE",
        action="append",
        dest="set_values",
        help=(
            "Edita uma chave de settings. Repetível. "
            "Chaves: active_provider, active_model, verbosity."
        ),
    )

    # ── traces ────────────────────────────────────────────────────────────────
    traces_p = sub.add_parser(
        "traces",
        help="Spans internos de observabilidade",
        description="Mostra spans do trace store SQLite em ~/.vectora/traces.db.",
    )
    traces_p.add_argument(
        "--session", "-s", metavar="ID", default=None, help="Filtra por session ID"
    )
    traces_p.add_argument(
        "--last", "-n", type=int, default=50, metavar="N", help="Quantos spans (50)"
    )
    traces_p.add_argument(
        "--json", action="store_true", dest="as_json", help="Saída como JSONL"
    )
    traces_p.add_argument(
        "--clear", action="store_true", help="Apaga todos os spans (ou só --session)"
    )

    # ── sessions ──────────────────────────────────────────────────────────────
    sub.add_parser(
        "sessions",
        help="Lista todas as sessões salvas",
        description="Mostra sessões com ID, data, contagem de mensagens e diretório.",
    )

    # ── storage ───────────────────────────────────────────────────────────────
    storage_p = sub.add_parser(
        "storage",
        help="Storage: migrations, diagnóstico, backup/restore, wizard BaaS",
        description=(
            "Comandos de storage:\n"
            "  info               status de saúde de todos os backends\n"
            "  up / down          sobe/para Postgres+pgvector, Redis e Qdrant\n"
            "  test <DSN>         testa conectividade a um banco\n"
            "  wizard             configura o backend interativamente (BaaS)\n"
            "  migrate status|upgrade|downgrade\n"
            "  backup / restore <arquivo>"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    storage_p.add_argument(
        "action",
        nargs="?",
        choices=[
            "info",
            "up",
            "down",
            "test",
            "wizard",
            "migrate",
            "backup",
            "restore",
        ],
        default="info",
        help="Ação de storage (default: info)",
    )
    storage_p.add_argument(
        "subaction",
        nargs="?",
        default=None,
        help="Sub-ação: status/upgrade/downgrade (migrate), DSN (test), arquivo (restore)",
    )
    storage_p.add_argument(
        "version", nargs="?", default=None, help="Versão alvo para downgrade (ex: 0002)"
    )
    storage_p.add_argument(
        "--db", metavar="PATH", default=None, help="Caminho do SQLite (settings.db_dsn)"
    )
    storage_p.add_argument(
        "--output", metavar="FILE", default=None, help="Arquivo de saída do backup"
    )

    # ── auth ──────────────────────────────────────────────────────────────────
    auth_p = sub.add_parser(
        "auth",
        help="Autenticação no servidor Vectora",
        description=(
            "Comandos de autenticação:\n"
            "  signup | login | logout | whoami | refresh\n\n"
            "Sem login, o CLI opera como root local (acesso via filesystem)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    auth_p.add_argument(
        "action",
        nargs="?",
        choices=["signup", "login", "logout", "whoami", "refresh"],
        help="Ação de autenticação.",
    )

    return parser


# ---------------------------------------------------------------------------
# start — backend + MCP + SPA via uvicorn
# ---------------------------------------------------------------------------


def _run_start(args: argparse.Namespace) -> None:
    """``vectora start`` — sobe FastAPI (+ /mcp) servindo a SPA via uvicorn.

    Em ``--headless`` registra ``VECTORA_HEADLESS=1`` para a bandeja/Electron
    decidirem não abrir janela; o servidor em si é idêntico.
    """
    import uvicorn

    from backend.api.server import create_app

    if args.headless:
        os.environ["VECTORA_HEADLESS"] = "1"

    # Precedência da porta: --port > VECTORA_PORT (env do Electron) > 8080.
    port = args.port or int(os.environ.get("VECTORA_PORT") or 0) or 8080
    uvicorn_log_level = os.environ.get("VECTORA_UVICORN_LOG_LEVEL", "warning")

    # TLS opcional — CLI tem prioridade; settings (env SSL_CERTFILE/SSL_KEYFILE
    # ou ~/.vectora/.env) é o fallback. Com cert+key o uvicorn serve https://,
    # necessário para Secure Context (crypto.randomUUID etc.) via IP de LAN.
    ssl_certfile = args.ssl_certfile
    ssl_keyfile = args.ssl_keyfile
    if not ssl_certfile or not ssl_keyfile:
        try:
            from backend.settings import settings as _settings

            ssl_certfile = ssl_certfile or _settings.ssl_certfile
            ssl_keyfile = ssl_keyfile or _settings.ssl_keyfile
        except Exception:
            pass
    if bool(ssl_certfile) != bool(ssl_keyfile):
        print(
            "❌ TLS requer certificado E chave: informe --ssl-certfile e "
            "--ssl-keyfile (ou SSL_CERTFILE/SSL_KEYFILE)."
        )
        sys.exit(1)
    use_tls = bool(ssl_certfile and ssl_keyfile)

    # Transporte desktop é IPC real: sob VECTORA_DESKTOP=1 (Electron) o backend
    # não expõe porta TCP ao SO. Em Linux/macOS usa unix socket; no Windows usa
    # named pipe (ipc_pipe_win). Web/VPS mantém TCP (servidor de rede, por design).
    uds_path: str | None = None
    if os.environ.get("VECTORA_DESKTOP") and sys.platform != "win32":
        sock_dir = Path.home() / ".vectora"
        sock_dir.mkdir(parents=True, exist_ok=True)
        uds_path = str(sock_dir / "vectora.sock")
        with contextlib.suppress(FileNotFoundError):
            Path(uds_path).unlink()

    app = create_app()
    scheme = "https" if use_tls else "http"
    if uds_path:
        logger.info("Iniciando Vectora via unix socket %s (desktop IPC)", uds_path)
        config = uvicorn.Config(
            app,
            uds=uds_path,
            log_level=uvicorn_log_level,
            access_log=False,
            ssl_certfile=ssl_certfile,
            ssl_keyfile=ssl_keyfile,
        )
    else:
        logger.info(
            "Iniciando Vectora em %s://%s:%d (%s)",
            scheme,
            args.host,
            port,
            "headless" if args.headless else "fullstack",
        )
        config = uvicorn.Config(
            app,
            host=args.host,
            port=port,
            log_level=uvicorn_log_level,
            access_log=False,
            ssl_certfile=ssl_certfile,
            ssl_keyfile=ssl_keyfile,
        )
    server = uvicorn.Server(config)

    # Windows + VECTORA_DESKTOP: named pipe em vez de TCP — nenhuma porta TCP é
    # exposta ao SO. O Electron conecta via \\.\pipe\vectora-<pid>, lido de stdout.
    if sys.platform == "win32" and os.environ.get("VECTORA_DESKTOP"):
        from backend.services.ipc_pipe_win import PIPE_ENV_VAR, pipe_name, serve_pipe

        _pipe = pipe_name()
        os.environ[PIPE_ENV_VAR] = _pipe
        print(f"{PIPE_ENV_VAR}={_pipe}", flush=True)

        async def _run_win() -> None:
            pipe_task = asyncio.create_task(serve_pipe(_pipe, "127.0.0.1", port))
            try:
                await server.serve()
            finally:
                pipe_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await pipe_task

        asyncio.run(_run_win())
        return

    # Sobe o servidor e, quando há display, a bandeja do sistema (Python). Sem
    # display (VPS/Docker) ou sem pystray, degrada para servidor puro. A bandeja
    # bloqueia a main thread até "Sair"; o servidor roda em thread de fundo.
    from backend.services.tray import run_server_with_tray

    run_server_with_tray(server, f"{scheme}://localhost:{port}", headless=args.headless)

    # Retorno do tray/servidor = shutdown concluído. No Windows, threads
    # não-daemon de libs externas (langsmith, httpx, SQLite do tracer, Cohere
    # rate limiter) mantêm o interpreter vivo; os._exit ignora-as e libera o
    # terminal. Os recursos críticos já foram fechados no lifespan.
    logger.info("Vectora: encerrando processo")
    os._exit(0)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run() -> None:
    """Ponto de entrada síncrono — comando ``vectora``."""
    parser = _build_parser()
    args = parser.parse_args()

    command = getattr(args, "command", None)

    if command is None:
        parser.print_help()
        return

    if command == "start":
        _run_start(args)
        return

    if command == "config":
        from backend.cli.config import run_config

        run_config(args)
        return

    if command == "traces":
        from backend.cli.traces import run_traces

        run_traces(args)
        return

    if command == "sessions":
        from backend.cli.sessions import run_sessions

        run_sessions()
        return

    if command == "storage":
        from backend.cli.storage import run_storage

        run_storage(args)
        return

    if command == "auth":
        from backend.auth import (
            cmd_login,
            cmd_logout,
            cmd_refresh,
            cmd_signup,
            cmd_whoami,
        )

        action = getattr(args, "action", None)
        handlers = {
            "signup": cmd_signup,
            "login": cmd_login,
            "logout": cmd_logout,
            "whoami": cmd_whoami,
            "refresh": cmd_refresh,
        }
        handler = handlers.get(action or "")
        if handler is None:
            print(
                "Uso: vectora auth <ação>\n"
                "Ações: signup | login | logout | whoami | refresh\n"
                "Exemplo: vectora auth login"
            )
            sys.exit(1)
        sys.exit(handler(args))

    parser.print_help()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        run()
