"""``vectora config`` — configuração do aplicativo.

Sem ação, mostra/edita ``~/.vectora/settings.json``. Com ação, despacha para o
fluxo correspondente:

  - ``config keys``               — wizard de API keys + LLM provider
  - ``config docker [up|down|status]`` — infra local via Docker
  - ``config qdrant <url> [--api-key]`` — testa e persiste Qdrant
  - ``config redis <url>``        — testa e persiste Redis
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _show_or_set(args: argparse.Namespace) -> None:
    """``vectora config`` (sem ação) — mostra ou edita settings.json."""
    from rich.console import Console
    from rich.table import Table

    from backend.services.runtime_settings import runtime_settings

    set_values = getattr(args, "set_values", None)
    if set_values:
        allowed_keys = {"active_provider", "active_model"}
        for kv in set_values:
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
            runtime_settings.set(key, value)
            print(f"✓ {key} = {value!r}")
        return

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
        "last_session_by_dir": "Session per directory mapping",
    }

    for key in ("active_provider", "active_model"):
        value = runtime_settings.get(key)
        table.add_row(key, str(value), descriptions.get(key, ""))

    mapping = runtime_settings.last_session_by_dir
    if mapping:
        summary = f"{len(mapping)} director{'y' if len(mapping) == 1 else 'ies'}"
        table.add_row(
            "last_session_by_dir", summary, descriptions["last_session_by_dir"]
        )

    console.print(table)
    console.print(f"\n[dim]File: {Path.home() / '.vectora' / 'settings.json'}[/dim]")


def run_config(args: argparse.Namespace) -> None:
    """Despacha ``vectora config [ação]``."""
    action = getattr(args, "config_action", None)

    if action is None:
        _show_or_set(args)
        return

    if action == "keys":
        from backend.cli.keys import run_keys

        run_keys()
        return

    if action == "docker":
        from backend.cli.infra import run_docker

        run_docker(getattr(args, "config_arg", None) or "status")
        return

    if action == "qdrant":
        from backend.cli.infra import run_qdrant

        run_qdrant(
            getattr(args, "config_arg", None) or "",
            getattr(args, "api_key", None),
        )
        return

    if action == "redis":
        from backend.cli.infra import run_redis

        run_redis(getattr(args, "config_arg", None) or "")
        return

    print(f"❌ Ação de config desconhecida: {action!r}")
    sys.exit(1)
