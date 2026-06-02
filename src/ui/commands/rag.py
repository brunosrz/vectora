"""/rag command — RAG pipeline status panel and ingest."""

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.panel import Panel
from rich.table import Table

from src.config.settings import settings

logger = logging.getLogger(__name__)

# D5: canonical collections — each has a distinct semantic purpose
# so RAG search stays precise and avoids cross-contamination
CANONICAL_COLLECTIONS: dict[str, str] = {
    "code": "Source code (.py, .ts, .js, .go, .rs…)",
    "docs": "Documentation (.md, .rst, .txt, .pdf…)",
    "web": "Fetched web pages and articles",
    "notes": "Personal notes and scratch files",
}

# File-extension → collection heuristic
_EXT_TO_COLLECTION: dict[str, str] = {
    ".py": "code",
    ".ts": "code",
    ".tsx": "code",
    ".js": "code",
    ".jsx": "code",
    ".go": "code",
    ".rs": "code",
    ".java": "code",
    ".c": "code",
    ".cpp": "code",
    ".h": "code",
    ".sh": "code",
    ".md": "docs",
    ".rst": "docs",
    ".txt": "docs",
    ".pdf": "docs",
    ".ipynb": "docs",
    ".html": "web",
    ".htm": "web",
}


def _guess_collection(path: str, glob_pattern: str) -> str:
    """Infere a coleção mais adequada baseada no caminho e padrão glob.

    Prioriza: --collection explícito (não chega aqui) > extensão do padrão glob
    > nome do diretório (docs/, notes/).
    Retorna "code" como fallback razoável para projetos Python.
    """
    # Tenta inferir pela extensão do padrão (ex: **/*.md → docs)
    if glob_pattern:
        ext = Path(glob_pattern.lstrip("*").replace("*", "")).suffix
        if ext in _EXT_TO_COLLECTION:
            return _EXT_TO_COLLECTION[ext]

    # Tenta inferir pelo nome do diretório
    path_lower = path.lower()
    if any(part in path_lower for part in ("doc", "wiki", "readme", "notes")):
        return "docs"
    if any(part in path_lower for part in ("note", "scratch", "journal")):
        return "notes"

    return "code"  # default para projetos Python


async def handle_rag_add(raw_args: str, console: Any) -> None:
    """Handle /rag add <path> [--collection X] [--pattern Y].

    Indexa um diretório no LanceDB chamando ingest_docs diretamente.
    """
    import shlex

    from rich.progress import Progress, SpinnerColumn, TextColumn

    try:
        parts = shlex.split(raw_args)
    except ValueError:
        parts = raw_args.split()

    if not parts:
        console.print(
            "[red]Uso:[/red] /rag add <path> [--collection <nome>] [--pattern <glob>]\n"
            "[dim]Exemplos:[/dim]\n"
            "  /rag add .\n"
            "  /rag add src/agents\n"
            "  /rag add docs/ --collection wiki --pattern '**/*.md'"
        )
        return

    directory_path = parts[0]
    explicit_collection: str | None = None
    glob_pattern = "**/*.py"

    i = 1
    while i < len(parts):
        if parts[i] == "--collection" and i + 1 < len(parts):
            explicit_collection = parts[i + 1]
            i += 2
        elif parts[i] == "--pattern" and i + 1 < len(parts):
            glob_pattern = parts[i + 1]
            i += 2
        else:
            i += 1

    # D5: se não especificou --collection, inferir pela extensão/caminho
    collection = explicit_collection or _guess_collection(directory_path, glob_pattern)

    console.print(
        f"[cyan]Indexando[/cyan] [bold]{directory_path}[/bold] "
        f"[dim](collection={collection}, pattern={glob_pattern})[/dim]"
    )

    try:
        import json

        from src.tools.rag import ingest_docs

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Processando arquivos...", total=None)
            result_str = await ingest_docs.ainvoke(
                {
                    "directory_path": directory_path,
                    "collection": collection,
                    "glob_pattern": glob_pattern,
                }
            )

        try:
            data = json.loads(result_str) if isinstance(result_str, str) else result_str
        except Exception:
            console.print(f"[yellow]{result_str}[/yellow]")
            return

        status = data.get("status", "unknown")
        if status == "completed":
            skipped = data.get("skipped_ignored", 0)
            ingest_fails = data.get("failed", 0)
            skipped_note = (
                f"  Ignorados (__pycache__, .gitignore…): [dim]{skipped}[/dim]\n"
                if skipped > 0
                else "  Ignorados (.gitignore, .vectoraignore): [dim]0[/dim]\n"
            )
            fail_hint = (
                "\n[dim]  → /rag failed para ver erros · /rag retry para reprocessar[/dim]\n"
                if ingest_fails > 0
                else ""
            )
            console.print(
                Panel(
                    f"[green]✓ Indexação concluída[/green]\n\n"
                    f"  Arquivos:  [bold]{data.get('total_files', 0)}[/bold]\n"
                    f"  Chunks:    [bold]{data.get('total_chunks', 0)}[/bold]\n"
                    f"  Enfileirados: [green]{data.get('indexed', 0)}[/green]\n"
                    f"  Falhas ao ler/chunkar: [red]{ingest_fails}[/red]{fail_hint}"
                    f"{skipped_note}"
                    f"\n[dim]Use /rag para acompanhar o progresso do worker.[/dim]",
                    title=f"[bold cyan]RAG — {directory_path}[/bold cyan]",
                    border_style="cyan",
                )
            )
        elif status == "no_files":
            console.print(
                Panel(
                    f"[yellow]Nenhum arquivo encontrado[/yellow]\n"
                    f"{data.get('message', '')}",
                    title="[bold yellow]RAG — Sem arquivos[/bold yellow]",
                    border_style="yellow",
                )
            )
        else:
            console.print(f"[yellow]{result_str}[/yellow]")

    except Exception as e:
        console.print(f"[red]Erro ao indexar:[/red] {e}")


async def handle_rag_retry(console: Any) -> None:
    """Handle /rag retry — move failed/DLQ items back to pending."""
    try:
        from src.services.queue import get_embedding_queue

        q = await get_embedding_queue(settings.embedding_queue_dsn)
        retried = await q.retry_failed()

        if retried == 0:
            console.print(
                Panel(
                    "[green]Nenhum item para reprocessar — fila sem falhas.[/green]",
                    title="[bold cyan]RAG — Retry[/bold cyan]",
                    border_style="cyan",
                )
            )
        else:
            console.print(
                Panel(
                    f"[green]✓ {retried} item(s) movidos para [bold]pending[/bold].[/green]\n"
                    "[dim]O worker de embedding vai reprocessá-los em breve.[/dim]\n"
                    "[dim]Use /rag para acompanhar o progresso.[/dim]",
                    title="[bold cyan]RAG — Retry[/bold cyan]",
                    border_style="cyan",
                )
            )
        logger.info("rag_retry: %d items re-enqueued", retried)
    except Exception as e:
        console.print(f"[red]Erro ao reprocessar falhas:[/red] {e}")
        logger.exception("rag_retry_failed")


async def handle_rag_command(args: str, console: Any) -> None:
    """Handle /rag command — full RAG pipeline status panel.

    Subcommands:
        /rag          → full panel (worker + queue + LanceDB)
        /rag add <path> [--collection X] [--pattern Y]  → index folder
        /rag failed   → list last failed items (failed/dlq)
        /rag retry    → move failed/DLQ items back to pending
    """
    from rich.text import Text

    stripped_args = args.strip()
    if stripped_args.lower().startswith("add"):
        add_args = stripped_args[3:].strip()
        await handle_rag_add(add_args, console)
        return

    if stripped_args.lower() == "retry":
        await handle_rag_retry(console)
        return

    args = stripped_args.lower()

    # 1. Worker stats (inclui estado de rate limit do Cohere)
    worker_running = False
    processed_count = 0
    failed_count = 0
    cohere_rate_limited = False
    cohere_rate_limit_count = 0
    cohere_last_429_at: datetime | None = None
    rl_calls_per_minute: int = 90
    rl_throttle_count: int = 0
    rl_avg_wait_s: float = 0.0
    rl_total_throttle_s: float = 0.0
    try:
        from src.services.background import get_background_worker

        worker = await get_background_worker()
        worker_running = worker.running
        processed_count = worker.processed_count
        failed_count = worker.failed_count
        cohere_rate_limited = worker.rate_limit_active
        cohere_rate_limit_count = worker.rate_limit_count
        cohere_last_429_at = worker.last_rate_limit_at
        rl = worker._rate_limiter
        rl_calls_per_minute = rl.calls_per_minute
        rl_throttle_count = rl.throttle_count
        rl_avg_wait_s = rl.avg_wait_s
        rl_total_throttle_s = rl.total_throttle_seconds
    except Exception:
        pass

    # 2. Queue stats
    queue_stats: dict[str, int] = {
        "pending": 0,
        "processing": 0,
        "success": 0,
        "failed": 0,
        "dlq": 0,
    }
    failed_records = []
    try:
        from src.services.queue import get_embedding_queue

        q = await get_embedding_queue(settings.embedding_queue_dsn)
        queue_stats = await q.get_stats()
        if args == "failed":
            failed_records = await q.get_failed(limit=10)
    except Exception:
        pass

    # /rag failed subcommand
    if args == "failed":
        if not failed_records:
            console.print(
                Panel(
                    "[green]Nenhum item com falha na fila.[/green]",
                    title="[bold cyan]RAG — Falhas[/bold cyan]",
                    border_style="cyan",
                )
            )
            return

        table = Table(title="Últimas Falhas / DLQ", style="red", show_lines=True)
        table.add_column("queue_id", style="dim", max_width=12)
        table.add_column("status", style="bold red")
        table.add_column("tentativas", justify="right")
        table.add_column("erro", max_width=60)
        for rec in failed_records:
            err = str(rec.error_message or rec.dlq_reason or "")[:120]
            table.add_row(
                str(rec.queue_id)[:8] + "…",
                str(rec.status),
                str(rec.attempt_count),
                err,
            )
        console.print(Panel(table, border_style="red", expand=False))
        return

    # Full panel
    worker_dot = (
        "[bold green]● Running[/bold green]"
        if worker_running
        else "[dim]○ Stopped[/dim]"
    )
    worker_line = (
        f"{worker_dot}  "
        f"[green]{processed_count}[/green] processados, "
        f"[red]{failed_count}[/red] falharam (sessão atual)"
    )

    queue_table = Table(box=None, show_header=False, padding=(0, 1))
    queue_table.add_column("status", style="dim", width=12)
    queue_table.add_column("count", justify="right", width=7)
    queue_table.add_column("desc", style="dim")
    _q_rows = [
        ("pending", "[yellow]", "aguardando Cohere"),
        ("processing", "[cyan]", "sendo processados agora"),
        ("success", "[green]", "escritos no LanceDB"),
        ("failed", "[red]", "use /rag failed | /rag retry"),
        ("dlq", "[bold red]", "use /rag retry para reprocessar"),
    ]
    for key, color, desc in _q_rows:
        n = queue_stats.get(key, 0)
        queue_table.add_row(key, f"{color}{n}[/]", desc)

    # LanceDB collections — total + breakdown por origem (curado vs web).
    # O breakdown usa pandas para agregar `metadata.origin` numa passada.
    lancedb_lines: list[str] = []
    try:
        import lancedb as _lancedb

        from src.tools.rag import _parse_metadata

        db = await _lancedb.connect_async(str(settings.lancedb_dir))
        names = await db.table_names()
        if names:
            for name in names:
                try:
                    tbl = await db.open_table(name)
                    cnt = await tbl.count_rows()
                    origin_note = ""
                    if cnt:
                        try:
                            df = await tbl.to_pandas()
                            origins = (
                                df["metadata"]
                                .map(_parse_metadata)
                                .map(lambda m: m.get("origin", ""))
                            )
                            web_n = int((origins == "web_search").sum())
                            curated_n = cnt - web_n
                            origin_note = (
                                f"  [dim](curado {curated_n} · web {web_n})[/dim]"
                            )
                        except Exception:
                            origin_note = ""
                    lancedb_lines.append(
                        f"  [bold]{name}[/bold]   {cnt} docs{origin_note}"
                    )
                except Exception:
                    lancedb_lines.append(f"  [bold]{name}[/bold]   (erro ao contar)")
        else:
            lancedb_lines.append("  [dim](sem coleções ainda)[/dim]")
    except Exception as e:
        lancedb_lines.append(f"  [dim]LanceDB indisponível: {e}[/dim]")

    body = (
        f"[bold]Background Worker[/bold]   {worker_line}\n"
        "\n"
        f"[bold]Queue[/bold] ({settings.embedding_queue_file.name if settings.embedding_queue_file else 'N/A'})\n"
    )
    lancedb_section = "\n[bold]LanceDB Collections[/bold]  "
    lancedb_section += f"[dim]({settings.lancedb_dir})[/dim]\n"
    lancedb_section += "\n".join(lancedb_lines)

    # Cohere API status panel
    cohere_table = Table(box=None, show_header=False, padding=(0, 1))
    cohere_table.add_column("label", style="dim", width=20)
    cohere_table.add_column("value")

    # Status: rate limited or OK
    if cohere_rate_limited:
        status_str = "[bold yellow]⚠ Rate Limited[/bold yellow]"
    elif cohere_rate_limit_count > 0:
        status_str = "[green]✓ OK[/green] [dim](recuperado)[/dim]"
    else:
        status_str = "[green]✓ OK[/green]"
    cohere_table.add_row("Status", status_str)

    # Key info (prefix only — nunca expõe a chave completa)
    api_key = (
        settings.get_cohere_api_key()
        if hasattr(settings, "get_cohere_api_key")
        else None
    )
    if api_key:
        key_preview = f"[dim]{api_key[:8]}…[/dim]"
        key_len = len(api_key)
        # Trial keys do Cohere têm prefixo "cohere-" e comprimento ~53
        is_likely_trial = key_len < 60 and api_key.lower().startswith("cohere")
        key_type = (
            "[yellow]Trial[/yellow] [dim](100 calls/min)[/dim]"
            if is_likely_trial
            else "[green]Production[/green]"
        )
        cohere_table.add_row("API Key", f"{key_preview}  {key_type}")
    else:
        cohere_table.add_row("API Key", "[red]não configurada[/red]")

    # Rate limiter (token bucket) stats
    cohere_table.add_row(
        "Rate limit config",
        f"[cyan]{rl_calls_per_minute}[/cyan] [dim]calls/min[/dim]",
    )
    if rl_throttle_count > 0:
        cohere_table.add_row(
            "Throttles (sessão)",
            f"[yellow]{rl_throttle_count}[/yellow]  "
            f"[dim]avg wait {rl_avg_wait_s:.2f}s  "
            f"total {rl_total_throttle_s:.1f}s[/dim]",
        )
    else:
        cohere_table.add_row(
            "Throttles (sessão)", "[green]0[/green] [dim](sem espera)[/dim]"
        )

    # 429s from API (passou pelo rate limiter mas ainda houve burst)
    if cohere_rate_limit_count > 0:
        last_str = ""
        if cohere_last_429_at:
            delta = datetime.now() - cohere_last_429_at
            secs = int(delta.total_seconds())
            last_str = f"  [dim](último: {secs}s atrás)[/dim]"
        cohere_table.add_row(
            "429s da API (sessão)",
            f"[yellow]{cohere_rate_limit_count}[/yellow]{last_str}",
        )
    else:
        cohere_table.add_row("429s da API (sessão)", "[green]0[/green]")

    cohere_border = "yellow" if cohere_rate_limited else "cyan"

    console.print(
        Panel(
            Text.from_markup(body),
            title="[bold cyan]RAG Pipeline Status[/bold cyan]",
            border_style="cyan",
            expand=False,
        )
    )
    console.print(
        Panel(
            queue_table,
            title="[cyan]Embedding Queue[/cyan]",
            border_style="cyan",
            expand=False,
        )
    )
    console.print(
        Panel(
            cohere_table,
            title="[bold cyan]Cohere API[/bold cyan]",
            border_style=cohere_border,
            expand=False,
        )
    )
    console.print(
        Panel(
            Text.from_markup(lancedb_section),
            title="[cyan]LanceDB[/cyan]",
            border_style="cyan",
            expand=False,
        )
    )


# Backward-compat aliases
_handle_rag_add = handle_rag_add
_handle_rag_command = handle_rag_command
