"""/traces command — exibe spans do VectoraTracer (observabilidade interna).

Uso:
    /traces                → últimos 30 spans de todas as sessões
    /traces --session <id> → spans de uma sessão específica
    /traces --node <nome>  → filtra por nó (orchestrator, invoke_llm, rag_retrieve…)
    /traces --clear        → apaga todos os spans (reset do banco de traces)
"""

from __future__ import annotations

import logging
from typing import Any

from rich.panel import Panel
from rich.table import Table

from vectora.services.tracer import tracer

logger = logging.getLogger(__name__)

# Largura máxima do campo metadata no painel
_META_MAX = 55


async def handle_traces_command(args: str, console: Any, context: Any) -> None:
    """Exibe spans recentes do VectoraTracer.

    Args:
        args: Argumentos após /traces
        console: Rich console para output
        context: Contexto atual (usado para session_id padrão)
    """

    parts = args.strip().split()
    session_filter: int | None = None
    node_filter: str | None = None
    do_clear = False

    i = 0
    while i < len(parts):
        tok = parts[i]
        if tok in ("--session", "-s") and i + 1 < len(parts):
            try:
                session_filter = int(parts[i + 1])
            except ValueError:
                console.print(f"[red]session_id inválido: {parts[i + 1]}[/red]")
                return
            i += 2
        elif tok in ("--node", "-n") and i + 1 < len(parts):
            node_filter = parts[i + 1]
            i += 2
        elif tok in ("--clear", "-c"):
            do_clear = True
            i += 1
        else:
            i += 1

    # ── clear ──────────────────────────────────────────────────────────────
    if do_clear:
        removed = await tracer.clear_all()
        console.print(
            f"[green]✓ {removed} span(s) apagado(s) do banco de traces.[/green]"
        )
        return

    # ── fetch spans ────────────────────────────────────────────────────────
    if session_filter is not None:
        spans = await tracer.get_session(session_filter, limit=50)
    else:
        spans = await tracer.get_recent(n=30)

    if node_filter:
        spans = [s for s in spans if s.get("node", "").startswith(node_filter)]

    if not spans:
        hint = ""
        if session_filter:
            hint = f" para session {session_filter}"
        elif node_filter:
            hint = f" com node '{node_filter}'"
        console.print(
            Panel(
                f"[dim]Nenhum span encontrado{hint}.[/dim]\n"
                "[dim]Os spans são gravados automaticamente durante as conversas.[/dim]",
                title="[bold cyan]Traces[/bold cyan]",
                border_style="cyan",
            )
        )
        return

    # ── renderizar tabela ──────────────────────────────────────────────────
    table = Table(
        show_lines=True,
        border_style="cyan",
        title=f"Últimos {len(spans)} span(s)"
        + (f" · session {session_filter}" if session_filter else "")
        + (f" · node={node_filter}" if node_filter else ""),
    )
    table.add_column("node", style="bold cyan", width=18)
    table.add_column("event", style="dim", width=10)
    table.add_column("ms", justify="right", width=7)
    table.add_column("status", width=7)
    table.add_column("in/out", justify="right", width=10)
    table.add_column("session", justify="center", width=8)
    table.add_column("metadata", style="dim", max_width=_META_MAX)

    for sp in spans:
        node = str(sp.get("node", ""))[:18]
        event = str(sp.get("event", ""))[:10]
        dur = sp.get("duration_ms")
        dur_str = f"{dur:.0f}" if dur is not None else "—"
        status = str(sp.get("status", "ok"))
        status_fmt = (
            f"[red]{status}[/red]"
            if status not in ("ok", "success")
            else f"[green]{status}[/green]"
        )
        in_tok = sp.get("in_tokens")
        out_tok = sp.get("out_tokens")
        tok_str = (
            f"{in_tok}/{out_tok}"
            if in_tok is not None and out_tok is not None
            else ("—" if in_tok is None and out_tok is None else f"{in_tok or '—'}/—")
        )
        sess = str(sp.get("session_id") or "—")

        import json as _json

        meta_raw = sp.get("metadata", "{}")
        try:
            meta_dict = _json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
            meta_str = ", ".join(f"{k}={v}" for k, v in meta_dict.items())
        except Exception:
            meta_str = str(meta_raw)
        meta_str = meta_str[:_META_MAX]

        table.add_row(node, event, dur_str, status_fmt, tok_str, sess, meta_str)

    # ── sumário agregado ───────────────────────────────────────────────────
    node_stats: dict[str, list[float]] = {}
    for sp in spans:
        n = sp.get("node", "?")
        d = sp.get("duration_ms")
        if d is not None:
            node_stats.setdefault(n, []).append(float(d))

    summary_lines = []
    for n, durations in sorted(node_stats.items()):
        avg = sum(durations) / len(durations)
        summary_lines.append(
            f"  [cyan]{n}[/cyan]: {len(durations)}x  avg [bold]{avg:.0f}ms[/bold]"
        )

    footer = (
        "\n[bold]Por nó:[/bold]\n" + "\n".join(summary_lines) if summary_lines else ""
    )
    hint_txt = "\n[dim]Use /traces --session <id> · --node <n> · --clear[/dim]"
    console.print(
        Panel(
            table,
            title="[bold cyan]Traces — Observabilidade[/bold cyan]",
            border_style="cyan",
            subtitle=footer + hint_txt if footer else hint_txt,
            expand=False,
        )
    )


# Backward-compat alias
_handle_traces_command = handle_traces_command
