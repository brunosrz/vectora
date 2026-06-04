"""Launcher Vectora — entry-point único do binário comercial.

O Launcher tem dois modos de operação:

1. **Binário completo** (Nuitka onefile distribuído via instaladores
   nativos Win/macOS/Linux): valida ``VECTORA_TOKEN`` contra a edge
   function Supabase ``validate-license``, exporta ``VECTORA_TIER`` no
   ambiente e delega para ``src.main:run``.

2. **CLI mirror PyPI** (``vectora-cli`` no PyPI, livre): pula gate de
   licença, expõe **apenas** os subcomandos CLI do agente (``chat``
   textual, ``rag``, ``setup``, ``traces``, ``sessions``, ``config``).
   Subcomandos que exigem servidor web ou Electron (``server chat``,
   ``server headless``) retornam erro explicativo pedindo o instalador
   nativo. Ativado por ``VECTORA_CLI_ONLY=1`` ou via subcomando
   ``vectora --cli-only`` (detecção pelo nome do pacote).

**Modo dev**: ``VECTORA_LICENSE_BYPASS=1`` pula o gate independente do
modo (uso interno).
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger("src.launcher")


def _print_error(message: str) -> None:
    """Imprime erro em stderr com formato consistente."""
    sys.stderr.write(f"\n[Vectora] {message}\n\n")
    sys.stderr.flush()


_SERVER_SUBCOMMANDS = {"server", "headless"}


def _is_cli_only_mode() -> bool:
    """Detecta se estamos rodando como ``vectora-cli`` (PyPI mirror)."""
    return os.getenv("VECTORA_CLI_ONLY", "").strip() == "1"


def _reject_server_in_cli_only() -> int:
    """No modo CLI mirror, recusa subcomandos que requerem o desktop."""
    args = sys.argv[1:]
    if not args:
        return 0
    if args[0] in _SERVER_SUBCOMMANDS:
        _print_error(
            "Este pacote (vectora-cli) só expõe o CLI textual.\n"
            "Para chat web, MCP server e desktop, baixe o instalador\n"
            "nativo em https://vectora.company/download."
        )
        return 5
    return 0


def main() -> int:
    """Entry-point do binário Vectora compilado."""
    if _is_cli_only_mode():
        rc = _reject_server_in_cli_only()
        if rc != 0:
            return rc
        logger.info("launcher: cli-only mode (PyPI mirror), license bypass")
        from src.main import run as cli_run

        cli_run()
        return 0

    # Lazy import para que o gate de licença execute antes de carregar
    # FastAPI, LangGraph, vector stores etc. — boot mais rápido em erro.
    from src.services.license import LicenseError, validate_license_sync

    try:
        info = validate_license_sync()
    except LicenseError as exc:
        _print_error(str(exc))
        return 2
    except Exception as exc:
        _print_error(
            f"Falha inesperada validando licença: {exc}. "
            "Suporte: https://vectora.company/support."
        )
        return 3

    os.environ["VECTORA_TIER"] = info.tier
    logger.info(
        "license: tier=%s status=%s days_remaining=%d cached=%s",
        info.tier,
        info.status,
        info.days_remaining,
        info.cached,
    )

    if info.status == "expired":
        _print_error(
            "Licença Vectora expirada. Renove em https://vectora.company/pricing."
        )
        return 4

    # Aviso visível (não-bloqueante) quando faltam <=7 dias.
    if info.days_remaining <= 7 and info.status == "trial":
        sys.stderr.write(
            f"\n[Vectora] Trial expira em {info.days_remaining} dia(s). "
            "Renove em https://vectora.company/pricing.\n\n"
        )

    # Após a migração para Vite SPA (Bloco D), o FastAPI serve `chat/dist/`
    # diretamente via StaticFiles (ver src/api/server.py::_chat_static_root).
    # Não há mais sidecar Node.js — o launcher só precisa delegar ao CLI.
    from src.main import run as cli_run

    cli_run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
