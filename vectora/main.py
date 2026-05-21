"""Main entry point for Vectora CLI.

Refactored to use Settings + AgentManager (Dependency Injection).
No scattered os.getenv() calls. No complex context objects in configurable.

This is the "brain" that initializes everything with proper dependency injection:
1. Load Settings (fail-fast on validation errors)
2. Initialize AgentManager (which injects all services)
3. Run the CLI (thin UI layer)

Simple, testable, maintainable.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Configure UTF-8 on Windows before any output
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Add vectora to path for imports
vectora_dir = Path(__file__).parent
if str(vectora_dir) not in sys.path:
    sys.path.insert(0, str(vectora_dir))

# Setup logging early (before importing rest of app)
from vectora.services.log_setup import setup_logging

setup_logging()

logger = logging.getLogger(__name__)


async def main() -> None:
    """Main entry point for Vectora CLI.

    Initialization sequence:
    1. Load Settings (with validation)
    2. Initialize AgentManager
    3. Run CLI dashboard
    """
    try:
        logger.info("Starting Vectora CLI...")

        # ====================================================================
        # STEP 1: Load Settings (Single Source of Truth)
        # ====================================================================
        from vectora.config.settings import Settings

        try:
            settings = Settings()
            logger.info(
                "Settings loaded successfully",
                extra={
                    "provider": settings.get_llm_provider(),
                    "version": settings.version,
                },
            )
        except Exception as e:
            logger.critical(
                "Failed to initialize Settings. Configuration error:",
                extra={"error": str(e)},
            )
            print(
                f"\n❌ Configuration Error:\n{e}\n\n"
                "Please check your environment variables or ~/.vectora/.env file."
            )
            sys.exit(1)

        # ====================================================================
        # STEP 2: Initialize SessionService
        # ====================================================================
        from vectora.services.session import SessionService

        try:
            session_service = SessionService(settings)
            await session_service.initialize()
            logger.info("SessionService initialized successfully")
        except Exception as e:
            logger.critical(
                "Failed to initialize SessionService",
                extra={"error": str(e)},
            )
            print(f"\n❌ Initialization Error:\n{e}")
            sys.exit(1)

        # ====================================================================
        # STEP 3: Validate LLM Configuration
        # ====================================================================
        available_providers = settings.get_available_providers()
        if not available_providers:
            logger.warning("No LLM providers configured. Running setup wizard...")
            from vectora.ui.setup_wizard import run_setup

            await run_setup()
            settings = Settings()

        # ====================================================================
        # STEP 4: Run CLI Dashboard
        # ====================================================================
        from vectora.ui.chat import run_chat

        await run_chat(settings=settings)

    except KeyboardInterrupt:
        logger.info("Chat interrupted by user")
        print("\n\nGoodbye! 👋")
        sys.exit(0)
    except Exception as e:
        logger.exception("Unexpected error in main loop")
        print(f"\n❌ Unexpected Error:\n{e}")
        sys.exit(1)
    finally:
        logger.info("Vectora CLI shutdown")


def run() -> None:
    """Synchronous entry point (called by `vectora` CLI command).

    This wrapper converts the async main() to sync for the CLI.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋")
        sys.exit(0)


# ---------------------------------------------------------------------------
# vectora traces — CLI de observabilidade interna
# ---------------------------------------------------------------------------


async def _traces_main(
    session: int | None = None,
    last: int = 50,
    as_json: bool = False,
    clear: bool = False,
) -> None:
    """Lê e exibe spans do tracer SQLite local."""
    from vectora.services.tracer import tracer

    if clear:
        if session is not None:
            removed = await tracer.clear_session(session)
            print(f"Removidos {removed} spans da session {session}.")
        else:
            removed = await tracer.clear_all()
            print(f"Removidos {removed} spans.")
        return

    if session is not None:
        spans = await tracer.get_session(session, limit=last)
    else:
        spans = await tracer.get_recent(n=last)

    if not spans:
        print("Nenhum span encontrado. Execute o Vectora para gerar traces.")
        return

    if as_json:
        for s in spans:
            print(__import__("json").dumps(s))
        return

    from rich.console import Console
    from rich.table import Table

    console = Console()
    title = (
        f"Vectora Traces — session {session}"
        if session
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

    for s in reversed(spans):  # mais antigo primeiro
        ts = s.get("started_at", "")[:19].replace("T", " ")
        node = s.get("node", "")
        event = s.get("event", "")
        status = s.get("status", "ok")
        dur = s.get("duration_ms")
        dur_str = f"{dur:.1f}" if dur is not None else "—"
        in_t = str(s.get("in_tokens") or "—")
        out_t = str(s.get("out_tokens") or "—")
        sess = str(s.get("session_id") or "—")
        meta_raw = s.get("metadata", "{}")
        try:
            meta = (
                __import__("json").loads(meta_raw)
                if isinstance(meta_raw, str)
                else meta_raw
            )
            meta_str = ", ".join(f"{k}={v}" for k, v in meta.items() if v is not None)[
                :80
            ]
        except Exception:
            meta_str = str(meta_raw)[:80]

        color = status_color.get(status, "red")
        table.add_row(
            ts,
            node,
            event,
            f"[{color}]{status}[/{color}]",
            dur_str,
            in_t,
            out_t,
            sess,
            meta_str,
        )

    console.print(table)
    console.print(f"[dim]{len(spans)} span(s) exibidos.[/dim]")


def run_traces() -> None:
    """Entry point: vectora traces [--session N] [--last N] [--json] [--clear]"""
    import argparse

    parser = argparse.ArgumentParser(
        prog="vectora traces",
        description="Exibe spans de observabilidade interna do Vectora.",
    )
    parser.add_argument(
        "--session", "-s", type=int, default=None, help="Filtrar por session_id"
    )
    parser.add_argument(
        "--last",
        "-n",
        type=int,
        default=50,
        help="Número de spans a exibir (default: 50)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Saída em JSONL (uma linha por span)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Apaga todos os spans (ou da --session especificada)",
    )
    args = parser.parse_args()

    import contextlib

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(
            _traces_main(
                session=args.session,
                last=args.last,
                as_json=args.as_json,
                clear=args.clear,
            )
        )


if __name__ == "__main__":
    run()
