"""Vectora CLI — Unified entry point.

Usage:
    vectora                                 Start chat (resume last session)
    vectora --new                           Start chat with a new session
    vectora --session 042731                Resume a specific session
    vectora --model gpt-5.5                 Switch to GPT-5.5 (auto-detects openai)
    vectora --model gemini-3.5-flash        Switch to Gemini (auto-detects google-genai)
    vectora --model ollama:llama3.2         Ollama model (prefix required)
    vectora --ollama --model llama3.2       Alias for ollama
    vectora --verbosity 3                   Set verbosity level (persists)
    vectora server mcp --transport stdio    Start MCP server (stdio)
    vectora server mcp --transport sse      Start MCP server (SSE, port 8000)
    vectora server chat                     Start web chat server (FastAPI + UI, port 8080)
    vectora server headless                 Start API only, no UI (port 8080)
    vectora traces [--session] [--last N]   View observability traces
    vectora sessions                        List all sessions
    vectora config [--set KEY=VALUE ...]    Show or edit settings
"""

from __future__ import annotations

import argparse
import asyncio
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

# Add project root to path for imports (needed when running as a script directly)
# Note: must use parent.parent (project root), NOT parent (src/ package dir),
# because inserting the package dir shadows third-party packages with the same name
# (e.g., src/mcp/ would shadow the installed `mcp` package).
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.services.log_setup import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    import argparse

    from src.version import __version__

    parser = argparse.ArgumentParser(
        prog="vectora",
        description="Vectora — Advanced AI Assistant with RAG and MCP capabilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  vectora                              resume last session for this directory
  vectora --new                        start a fresh session
  vectora --session 042731             resume session 042731
  vectora --model gpt-5.5              switch to GPT-5.5 (auto-detects openai)
  vectora --model gemini-3.5-flash     switch to Gemini (auto-detects google-genai)
  vectora --model claude-opus-4-7      switch to Claude (auto-detects anthropic)
  vectora --model command-a-03-2025    switch to Cohere (auto-detects cohere)
  vectora --model ollama:llama3.2      ollama (prefix required — names are arbitrary)
  vectora --ollama --model llama3.2    alias: --ollama sets provider to ollama
  vectora --model gpt-5.5 --new        switch model AND start fresh session
  vectora --verbosity 3                set verbosity 0-5 (persists)
  vectora server mcp --transport stdio  start MCP server (stdio, local)
  vectora server mcp --transport sse   start MCP server (SSE, port 8000)
  vectora server chat                  start web chat (FastAPI + UI, port 8080)
  vectora server headless              start API only (no UI, port 8080)
  vectora traces                       show last 50 traces
  vectora traces --session 042731 --last 100
  vectora traces --clear               delete all traces
  vectora sessions                     list all saved sessions
  vectora config                       show current configuration
  vectora config --set verbosity=2 --set active_model=gpt-5.5
""",
    )

    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"vectora {__version__}",
    )

    # ── Global chat options ──────────────────────────────────────────────────

    parser.add_argument(
        "--model",
        metavar="MODEL",
        help=(
            "LLM model to use. Provider is auto-detected from the model name. "
            "Examples: gpt-5.5, gemini-3.5-flash, claude-opus-4-7, command-a-03-2025. "
            "For Ollama use 'ollama:<model>' or --ollama --model <model>. "
            "Persists to ~/.vectora/settings.json."
        ),
    )
    parser.add_argument(
        "--ollama",
        action="store_true",
        help=(
            "Force provider to Ollama (for local models whose names don't have "
            "a recognisable prefix). Equivalent to --model ollama:<model>."
        ),
    )
    parser.add_argument(
        "--verbosity",
        metavar="N",
        type=int,
        choices=range(6),
        help="Verbosity level 0–5 (0=silent, 3=tool events, 5=debug panel). Persists.",
    )
    parser.add_argument(
        "--session",
        metavar="ID",
        help="Resume a specific session by 6-digit ID (e.g. 042731).",
    )
    parser.add_argument(
        "--new",
        action="store_true",
        help="Force a new session instead of resuming the last one.",
    )
    parser.add_argument(
        "--quit",
        action="store_true",
        help="Automatically quit Vectora after 10 seconds.",
    )

    # ── Subcommands ──────────────────────────────────────────────────────────

    sub = parser.add_subparsers(dest="command", metavar="subcommand")

    # server — MCP (stdio/sse) + chat/headless (FastAPI)
    server_p = sub.add_parser(
        "server",
        help="Start a Vectora server (mcp, chat, or headless)",
        description=(
            "Modos disponíveis:\n"
            "  mcp      — MCP server (stdio ou sse) para Claude Desktop/Code e agentes externos\n"
            "  chat     — FastAPI + frontend web compilado (chat web em http://host:port)\n"
            "  headless — FastAPI sem frontend (integração com Paperclip e terceiros)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    server_p.add_argument(
        "mode",
        nargs="?",
        default=None,
        choices=["mcp", "chat", "headless", "stdio", "sse"],
        help=(
            "Modo do servidor. 'mcp' inicia o MCP server (requer --transport). "
            "'chat' e 'headless' iniciam a API FastAPI."
        ),
    )
    # MCP-specific flags (compatibilidade com uso anterior)
    server_p.add_argument(
        "--mode",
        dest="transport",
        choices=["stdio", "sse"],
        help="[MCP] Transporte: stdio (local) ou sse (remoto). Equivalente a `server mcp --transport`.",
    )
    server_p.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="[MCP] Transporte MCP: stdio (default) ou sse.",
    )
    server_p.add_argument("--host", default="0.0.0.0", help="Host (chat/headless/sse)")  # noqa: S104  # nosec B104
    server_p.add_argument(
        "--port",
        type=int,
        default=None,
        help="Porta (mcp sse=8000, chat/headless=8080)",
    )

    # traces
    traces_p = sub.add_parser(
        "traces",
        help="View internal observability traces",
        description="Display spans from the SQLite trace store at ~/.vectora/traces.db.",
    )
    traces_p.add_argument(
        "--session", "-s", metavar="ID", default=None, help="Filter by session ID"
    )
    traces_p.add_argument(
        "--last",
        "-n",
        type=int,
        default=50,
        metavar="N",
        help="Number of spans to display (default: 50)",
    )
    traces_p.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output as JSONL (one span per line)",
    )
    traces_p.add_argument(
        "--clear",
        action="store_true",
        help="Delete all spans (or only those of --session)",
    )

    # sessions
    sub.add_parser(
        "sessions",
        help="List all saved sessions",
        description="Show all sessions with ID, date, message count and directory.",
    )

    # config
    config_p = sub.add_parser(
        "config",
        help="Show or edit ~/.vectora/settings.json",
        description=(
            "Without --set, prints current configuration. "
            "With --set, updates keys and exits."
        ),
    )
    config_p.add_argument(
        "--set",
        metavar="KEY=VALUE",
        action="append",
        dest="set_values",
        help=(
            "Set a config value. Repeatable. "
            "Keys: active_provider, active_model, verbosity. "
            "Example: --set active_provider=openai --set verbosity=2"
        ),
    )

    # auth — autenticação (login, logout, whoami, etc.)
    auth_p = sub.add_parser(
        "auth",
        help="Gerenciar autenticação no servidor Vectora",
        description=(
            "Comandos de autenticação:\n"
            "  signup   — cria nova conta no servidor configurado\n"
            "  login    — autentica com email + senha\n"
            "  logout   — invalida sessão + limpa tokens locais\n"
            "  whoami   — mostra usuário ativo + role + servidor\n"
            "  refresh  — força rotação dos tokens (debug)\n\n"
            "Sem login, o CLI opera como root local (acesso via filesystem)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    auth_p.add_argument(
        "action",
        nargs="?",
        choices=["signup", "login", "logout", "whoami", "refresh"],
        help="Ação de autenticação a executar.",
    )

    return parser


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Standalone chat helper
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Model → provider resolution
# ---------------------------------------------------------------------------

# Ordered list of (prefix, provider). First match wins.
# Ollama is excluded intentionally — its model names are user-defined and
# arbitrary, so they must be disambiguated via the "ollama:" prefix or --ollama.
_MODEL_PREFIXES: list[tuple[str, str]] = [
    # Google Gemini
    ("gemini-", "google-genai"),
    # OpenAI
    ("gpt-", "openai"),
    ("o1-", "openai"),
    ("o1", "openai"),  # bare "o1"
    ("o3-", "openai"),
    ("o3", "openai"),
    ("o4-", "openai"),
    ("o4", "openai"),
    ("text-", "openai"),
    ("dall-e", "openai"),
    ("whisper-", "openai"),
    # Anthropic
    ("claude-", "anthropic"),
    # Cohere
    ("command-", "cohere"),
    ("embed-", "cohere"),
    ("rerank-", "cohere"),
]


def _detect_provider(model: str) -> str | None:
    """Infer provider from model name prefix.

    Returns provider string or None if the model name is ambiguous
    (e.g. arbitrary Ollama model names).
    """
    m = model.lower()
    for prefix, provider in _MODEL_PREFIXES:
        if m.startswith(prefix):
            return provider
    return None


def _apply_global_overrides(args: argparse.Namespace) -> None:
    """Resolve --model / --ollama / --verbosity and persist to RuntimeSettings."""
    from src.services.runtime_settings import runtime_settings

    model: str | None = getattr(args, "model", None)
    use_ollama: bool = getattr(args, "ollama", False)

    if model is not None:
        # ── Ollama: explicit prefix "ollama:<model>" ──────────────────────────
        if model.startswith("ollama:"):
            provider = "ollama"
            model = model[len("ollama:") :]  # strip prefix

        # ── --ollama flag: provider forced, model name is whatever the user typed
        elif use_ollama:
            provider = "ollama"

        # ── Everything else: detect from model name ───────────────────────────
        else:
            provider = _detect_provider(model)
            if provider is None:
                print(
                    f"❌ Cannot infer provider from model '{model}'.\n"
                    "   For Ollama models use: --model ollama:<model>  or  --ollama --model <model>\n"
                    "   Known prefixes: gemini- (google), gpt-/o1/o3/o4 (openai), "
                    "claude- (anthropic), command- (cohere)"
                )
                sys.exit(1)

        runtime_settings.set_active_model(provider, model)
        logger.info("CLI override: provider=%s model=%s", provider, model)

    elif use_ollama:
        # --ollama without --model: just switch provider, keep current ollama model
        from src.services.runtime_settings import runtime_settings as _rs

        runtime_settings.set_active_model("ollama", _rs.active_model)
        logger.info("CLI override: provider=ollama (model unchanged)")

    if args.verbosity is not None:
        runtime_settings.set_verbosity(args.verbosity)
        logger.info("CLI override: verbosity=%d", args.verbosity)


async def _run_chat_async(args: argparse.Namespace) -> None:
    """Full chat startup — settings, session resolution, UI loop."""
    from src.settings import Settings

    try:
        settings = Settings()
    except Exception as e:
        print(
            f"\n❌ Configuration Error:\n{e}\n\n"
            "Check your environment variables or ~/.vectora/.env file."
        )
        sys.exit(1)

    available_providers = settings.get_available_providers()
    if not available_providers:
        logger.warning("No LLM providers configured — starting setup wizard.")
        from src.ui.setup_wizard import run_setup

        await run_setup()
        settings = Settings()

    from src.ui.chat import run_chat

    await run_chat(
        settings=settings,
        force_new=args.new,
        session_id=args.session,
        quit_after=args.quit,
    )


async def _run_traces_async(args: argparse.Namespace) -> None:
    """traces subcommand — mirrors old run_traces() but async."""
    from src.services.tracer import tracer

    if args.clear:
        if args.session:
            removed = await tracer.clear_session(args.session)
            print(f"Removidos {removed} spans da sessão {args.session}.")
        else:
            removed = await tracer.clear_all()
            print(f"Removidos {removed} spans.")
        return

    spans = (
        await tracer.get_session(args.session, limit=args.last)
        if args.session
        else await tracer.get_recent(n=args.last)
    )

    if not spans:
        print("Nenhum span encontrado. Execute o Vectora para gerar traces.")
        return

    if args.as_json:
        import json

        for s in spans:
            print(json.dumps(s))
        return

    import json

    from rich.console import Console
    from rich.table import Table

    console = Console()
    title = (
        f"Vectora Traces — sessão {args.session}"
        if args.session
        else f"Vectora Traces — últimos {len(spans)}"
    )
    table = Table(title=title, show_lines=False, expand=True)
    table.add_column("Quando", style="dim", width=19)
    table.add_column("Node", style="cyan bold", width=20)
    table.add_column("Event", style="blue", width=14)
    table.add_column("Status", width=8)
    table.add_column("ms", justify="right", width=8)
    table.add_column("in↑", justify="right", width=6)
    table.add_column("out↓", justify="right", width=6)
    table.add_column("Session", justify="right", width=8)
    table.add_column("Metadata", style="dim")

    status_color = {
        "ok": "green",
        "error": "red",
        "timeout": "yellow",
        "quota_error": "magenta",
    }

    for s in reversed(spans):
        ts = s.get("started_at", "")[:19].replace("T", " ")
        status = s.get("status", "ok")
        dur = s.get("duration_ms")
        meta_raw = s.get("metadata", "{}")
        try:
            meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
            meta_str = ", ".join(f"{k}={v}" for k, v in meta.items() if v is not None)[
                :80
            ]
        except Exception:
            meta_str = str(meta_raw)[:80]

        color = status_color.get(status, "red")
        table.add_row(
            ts,
            s.get("node", ""),
            s.get("event", ""),
            f"[{color}]{status}[/{color}]",
            f"{dur:.1f}" if dur is not None else "—",
            str(s.get("in_tokens") or "—"),
            str(s.get("out_tokens") or "—"),
            str(s.get("session_id") or "—"),
            meta_str,
        )

    console.print(table)
    console.print(f"[dim]{len(spans)} span(s) exibidos.[/dim]")


async def _run_sessions_async() -> None:
    """sessions subcommand — list all sessions in a Rich table."""
    from rich.console import Console
    from rich.table import Table

    from src.services.runtime_settings import runtime_settings
    from src.services.session import SessionService
    from src.settings import Settings

    try:
        settings = Settings()
        service = SessionService(settings)
        await service.initialize()
        sessions = await service.list_all()
    except Exception as e:
        print(f"❌ Error listing sessions: {e}")
        sys.exit(1)

    console = Console()

    if not sessions:
        console.print("[dim]No sessions found. Start vectora to create one.[/dim]")
        return

    # Find which session is "active" per directory
    active_ids = set(runtime_settings.last_session_by_dir.values())

    table = Table(
        title=f"Vectora Sessions ({len(sessions)} total)",
        show_lines=False,
        expand=False,
    )
    table.add_column("ID", style="cyan bold", width=8)
    table.add_column("Created", style="dim", width=20)
    table.add_column("Messages", justify="right", width=9)
    table.add_column("Directory", style="dim")

    for s in sorted(sessions, key=lambda x: x.get("created_at", ""), reverse=True):
        tid = str(s.get("thread_id", "?"))
        created = s.get("created_at", "")[:19].replace("T", " ")
        msgs = str(s.get("message_count", 0))
        work_dir = s.get("working_directory") or "—"
        # Shorten long paths
        try:
            work_dir = str(Path(work_dir).relative_to(Path.home()))
            work_dir = f"~/{work_dir}"
        except ValueError:
            pass

        marker = " [bold green]◀ active[/bold green]" if tid in active_ids else ""
        table.add_row(tid, created, msgs, f"{work_dir}{marker}")

    console.print(table)


def _run_config(args: argparse.Namespace) -> None:
    """config subcommand — show or edit settings.json."""
    from rich.console import Console
    from rich.table import Table

    from src.services.runtime_settings import runtime_settings

    if args.set_values:
        allowed_keys = {"active_provider", "active_model", "verbosity"}
        for kv in args.set_values:
            if "=" not in kv:
                print(f"❌ Invalid format '{kv}'. Use KEY=VALUE.")
                sys.exit(1)
            key, _, value = kv.partition("=")
            key = key.strip()
            if key not in allowed_keys:
                print(
                    f"❌ Unknown key '{key}'. Allowed: {', '.join(sorted(allowed_keys))}"
                )
                sys.exit(1)
            # Type coercion
            if key == "verbosity":
                try:
                    value = int(value)  # type: ignore[assignment]
                except ValueError:
                    print(f"❌ verbosity must be an integer 0–5, got '{value}'")
                    sys.exit(1)
            runtime_settings.set(key, value)
            print(f"✓ {key} = {value!r}")
        return

    # Display current config
    console = Console()
    table = Table(
        title="Vectora Configuration  (~/.vectora/settings.json)",
        show_lines=False,
        expand=False,
    )
    table.add_column("Key", style="cyan bold")
    table.add_column("Value")
    table.add_column("Description", style="dim")

    descriptions = {
        "active_provider": "Active LLM provider",
        "active_model": "Active LLM model",
        "verbosity": "Verbosity level (0–5)",
        "last_session_by_dir": "Session per directory mapping",
    }

    for key in ("active_provider", "active_model", "verbosity"):
        value = runtime_settings.get(key)
        desc = descriptions.get(key, "")
        console.print() if False else None  # noop — just for structure
        table.add_row(key, str(value), desc)

    # Show last_session_by_dir as a compact summary
    mapping = runtime_settings.last_session_by_dir
    if mapping:
        summary = f"{len(mapping)} director{'y' if len(mapping) == 1 else 'ies'}"
        table.add_row("last_session_by_dir", summary, "Session per directory mapping")

    console.print(table)
    console.print(f"\n[dim]File: {Path.home() / '.vectora' / 'settings.json'}[/dim]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run() -> None:
    """Synchronous entry point — `vectora` CLI command."""
    import contextlib

    parser = _build_parser()
    args = parser.parse_args()

    command = getattr(args, "command", None)

    # ── server ────────────────────────────────────────────────────────────
    if command == "server":
        mode = getattr(args, "mode", None)
        transport = getattr(args, "transport", "stdio") or "stdio"

        # Compatibilidade retroativa: --mode stdio/sse (flag antigo do MCP)
        # era obrigatório; agora o modo é posicional.
        if mode in ("stdio", "sse"):
            transport = mode
            mode = "mcp"

        # Default: sem modo posicional → mcp (comportamento original)
        if mode is None:
            mode = "mcp"

        if mode == "mcp":
            os.environ["MCP_TRANSPORT"] = transport
            os.environ["MCP_HOST"] = args.host
            os.environ["MCP_PORT"] = str(args.port or 8000)
            from src.mcp.server import run as mcp_run

            mcp_run()
            return

        if mode in ("chat", "headless"):
            import uvicorn

            from src.api.server import create_app

            port = args.port or 8080
            uvicorn_log_level = os.environ.get("VECTORA_UVICORN_LOG_LEVEL", "warning")

            app = create_app()
            logger.info(
                "Iniciando Vectora %s server em http://%s:%d",
                mode,
                args.host,
                port,
            )
            # log_level do uvicorn afeta logs do próprio uvicorn (Started server,
            # Application startup, etc.). Ruído em dev — usar "warning" como
            # padrão e permitir override via env para depuração.
            uvicorn.run(
                app,
                host=args.host,
                port=port,
                log_level=uvicorn_log_level,
                access_log=False,  # access logs já são filtrados via log_setup
            )
            # uvicorn.run() retorna após o lifespan completar o shutdown.
            # No Windows, threads não-daemon de libs externas (langsmith,
            # httpx, SQLite do tracer, Cohere rate limiter) mantêm o
            # interpreter vivo indefinidamente — `os._exit` ignora elas e
            # libera o terminal. Os recursos críticos (checkpointer SQLite,
            # background worker) já foram fechados no lifespan.
            logger.info("Vectora server: encerrando processo")
            os._exit(0)

    # ── traces ────────────────────────────────────────────────────────────────
    if command == "traces":
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(_run_traces_async(args))
        return

    # ── sessions ──────────────────────────────────────────────────────────────
    if command == "sessions":
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(_run_sessions_async())
        return

    # ── config ────────────────────────────────────────────────────────────────
    if command == "config":
        _run_config(args)
        return

    # ── auth ──────────────────────────────────────────────────────────────────
    if command == "auth":
        from src.cli.auth import (
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
                "Ações disponíveis: signup | login | logout | whoami | refresh\n"
                "Exemplo: vectora auth login"
            )
            sys.exit(1)
        sys.exit(handler(args))

    # ── chat (default, no subcommand) ─────────────────────────────────────────
    _apply_global_overrides(args)

    try:
        asyncio.run(_run_chat_async(args))
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋")
        sys.exit(0)


# Keep run_traces as a backward-compat shim (vectora-traces script removed, but
# this function is referenced in tests or external configs that may still exist).
def run_traces() -> None:
    """Backward-compat shim. Use `vectora traces` instead."""
    import argparse
    import contextlib

    parser = argparse.ArgumentParser(prog="vectora traces")
    parser.add_argument("--session", "-s", default=None)
    parser.add_argument("--last", "-n", type=int, default=50)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--clear", action="store_true")
    args = parser.parse_args()

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_run_traces_async(args))


if __name__ == "__main__":
    run()
