"""``vectora traces`` — visualização dos spans de observabilidade (SQLite)."""

from __future__ import annotations

import argparse
import asyncio
import contextlib


async def _run_traces_async(args: argparse.Namespace) -> None:
    """Implementa ``vectora traces`` — lê do trace store em ~/.vectora/traces.db."""
    from backend.services.tracer import tracer

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


def run_traces(args: argparse.Namespace) -> None:
    """Entry point síncrono de ``vectora traces``."""
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_run_traces_async(args))
