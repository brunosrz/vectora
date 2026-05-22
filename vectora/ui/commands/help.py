"""/help, /tools, /list commands."""

import logging
from typing import Any

from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)


async def handle_tools_command(console: Any) -> None:
    """List all available tools in Vectora."""
    try:
        from vectora.tools import TOOLS

        table = Table(title="Available Tools", style="cyan")
        table.add_column("Tool Name", style="bold green")
        table.add_column("Description", style="dim")

        for tool in TOOLS:
            description = ""
            if hasattr(tool, "description"):
                description = tool.description
            elif hasattr(tool, "docstring"):
                doc = tool.docstring or ""
                description = doc.split("\n")[0] if doc else ""

            table.add_row(tool.name, description)

        console.print(Panel(table, style="cyan", expand=False))
        logger.info("Tools listed: %d available", len(TOOLS))
    except Exception as e:
        console.print(f"[red]Error listing tools: {e}[/red]")
        logger.exception("Failed to list tools")


_COMMANDS_TEXT = """
[bold cyan]Available Commands:[/bold cyan]

[bold]/model[/bold]
  List available models for current provider
  Usage: [dim]/model[/dim]

[bold]/model <model_name>[/bold]
  Switch to a different model
  Usage: [dim]/model gemini-3.5-flash[/dim]

[bold]/debug[/bold]
  Toggle debug mode (shows logs from all components)
  Usage: [dim]/debug[/dim]

[bold]/debug true|false[/bold]
  Enable or disable debug mode
  Usage: [dim]/debug true[/dim] or [dim]/debug false[/dim]

[bold]/tools[/bold] or [bold]/tool[/bold]
  List all available tools
  Usage: [dim]/tools[/dim]

[bold]/rag[/bold]
  Painel completo do pipeline RAG: worker status, fila de embedding, coleções LanceDB
  Usage: [dim]/rag[/dim]

[bold]/rag add <path>[/bold]
  Indexa uma pasta inteira no LanceDB (embedding em batch)
  Coleções canônicas: [bold]code[/bold], [bold]docs[/bold], [bold]web[/bold], [bold]notes[/bold] (auto-detectado pelo padrão)
  Usage: [dim]/rag add vectora/agents[/dim]
         [dim]/rag add . --collection code[/dim]
         [dim]/rag add docs/ --pattern "**/*.md" --collection docs[/dim]

[bold]/rag failed[/bold]
  Lista os últimos itens que falharam no embedding (failed/DLQ)
  Usage: [dim]/rag failed[/dim]

[bold]/rag retry[/bold]
  Move itens failed/DLQ de volta para pending para nova tentativa
  Usage: [dim]/rag retry[/dim]

[bold]/new[/bold]
  Create a new chat session
  Usage: [dim]/new[/dim]

[bold]/sessions[/bold]
  List all available sessions
  Usage: [dim]/sessions[/dim]

[bold]/session <id>[/bold]
  Switch to a specific session by ID
  Usage: [dim]/session 1[/dim]

[bold]/list[/bold]
  Show this list of all available commands
  Usage: [dim]/list[/dim]

[bold]/quit[/bold], [bold]/sair[/bold], [bold]/q[/bold]
  Exit the chat

[bold]/help[/bold]
  Show basic help message
"""


def build_commands_panel() -> Panel:
    """Return the commands list as a Rich Panel (without printing)."""
    return Panel(_COMMANDS_TEXT, title="Commands", style="cyan", expand=False)


def display_command_list(console: Any) -> None:
    """Display all available commands in Vectora."""
    console.print(build_commands_panel())


def display_help(console: Any) -> None:
    """Display basic help message pointing to /list for full commands."""
    help_text = """
[bold cyan]Welcome to Vectora Chat![/bold cyan]

Type your message to chat, or use these commands:

[bold]/list[/bold] - Show all available commands
[bold]/help[/bold] - Show this message
[bold]/quit[/bold] - Exit the chat
[bold]/new[/bold] - Create new session
[bold]/tools[/bold] - List available tools
[bold]/debug[/bold] - Toggle debug mode
[bold]/rag[/bold] - Painel do pipeline RAG (queue + LanceDB)
[bold]/rag add <path>[/bold] - Indexa pasta no LanceDB (coleções: code, docs, web, notes)
[bold]/rag retry[/bold] - Reprocessa embeddings que falharam (failed/DLQ)

For complete command reference, type [bold]/list[/bold]
"""
    console.print(Panel(help_text, title="Help", style="cyan", expand=False))


# Backward-compat aliases
_handle_tools_command = handle_tools_command
_display_command_list = display_command_list
_display_help = display_help
