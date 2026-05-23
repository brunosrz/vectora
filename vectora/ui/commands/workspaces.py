"""Comando /workspaces — lista e gerencia workspaces do Vectora."""

from __future__ import annotations

from typing import Any

from rich.table import Table


def handle_workspaces_command(
    args: str,
    console: Any,
    current_workspace_id: str | None = None,
) -> None:
    """Exibe a lista de workspaces registrados.

    Uso:
      /workspaces                    — lista todos
      /workspaces rename <id> <nome> — renomeia
      /workspaces delete <id>        — remove do registry
    """
    parts = args.strip().split()

    if len(parts) >= 3 and parts[0] == "rename":
        _handle_rename(parts[1], " ".join(parts[2:]), console)
    elif len(parts) == 2 and parts[0] == "delete":
        _handle_delete(parts[1], console, current_workspace_id)
    else:
        _handle_list(console, current_workspace_id)


def _handle_list(
    console: Any,
    current_workspace_id: str | None,
) -> None:
    """Lista todos os workspaces registrados."""
    from rich.panel import Panel

    from vectora.services.workspace import workspace_registry

    workspaces = workspace_registry.list_all()

    if not workspaces:
        console.print(
            Panel(
                "Nenhum workspace registrado ainda.\n"
                "Inicie o Vectora em um diretório de projeto para criar o primeiro.",
                title="[bold cyan]Workspaces[/bold cyan]",
                border_style="blue",
            )
        )
        return

    table = Table(
        title="Workspaces Vectora",
        border_style="blue",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("", width=2)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Nome", style="bold white")
    table.add_column("Diretório")
    table.add_column("Manifest", width=10)

    for ws in sorted(workspaces, key=lambda w: w.created_at or "", reverse=True):
        marker = "[green]●[/green]" if ws.id == current_workspace_id else " "
        if ws.manifest_path().exists():
            manifest_status = f"[green]v{ws.manifest_version}[/green]"
        else:
            manifest_status = "[dim]—[/dim]"
        table.add_row(marker, ws.id, ws.name, ws.cwd, manifest_status)

    console.print(table)
    console.print(
        "[dim]● = workspace ativo  |  "
        "/workspaces rename <id> <nome>  |  "
        "/workspaces delete <id>[/dim]"
    )


def _handle_rename(workspace_id: str, new_name: str, console: Any) -> None:
    """Renomeia um workspace."""
    from vectora.services.workspace import workspace_registry

    if workspace_registry.rename(workspace_id, new_name):
        console.print(
            f"[green]✓[/green] Workspace [cyan]{workspace_id}[/cyan] renomeado para "
            f"[bold]{new_name}[/bold]."
        )
    else:
        console.print(
            f"[red]✗[/red] Workspace [cyan]{workspace_id}[/cyan] não encontrado."
        )


def _handle_delete(
    workspace_id: str, console: Any, current_workspace_id: str | None
) -> None:
    """Remove um workspace do registry (não apaga dados do LanceDB)."""
    if workspace_id == current_workspace_id:
        console.print(
            "[red]✗[/red] Não é possível deletar o workspace ativo da sessão atual."
        )
        return

    from vectora.services.workspace import workspace_registry

    if workspace_registry.delete(workspace_id):
        console.print(
            f"[green]✓[/green] Workspace [cyan]{workspace_id}[/cyan] removido do registry.\n"
            "[dim]Nota: os dados indexados no LanceDB não foram apagados.[/dim]"
        )
    else:
        console.print(
            f"[red]✗[/red] Workspace [cyan]{workspace_id}[/cyan] não encontrado."
        )
