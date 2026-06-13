"""DiffWidget — render_hint: diff."""

from __future__ import annotations

from textual.widgets import Static


class DiffWidget(Static):
    """Displays a unified diff with color-coded additions and removals."""

    DEFAULT_CSS = """
    DiffWidget {
        background: $panel;
        border: round $primary-darken-2;
        padding: 0 1;
        margin: 0 0 1 0;
        overflow-x: auto;
    }
    """

    def __init__(self, tool_name: str, content: str) -> None:
        lines: list[str] = []
        for line in content[:3000].splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                lines.append(f"[green]{line}[/green]")
            elif line.startswith("-") and not line.startswith("---"):
                lines.append(f"[red]{line}[/red]")
            elif line.startswith("@@"):
                lines.append(f"[cyan]{line}[/cyan]")
            else:
                lines.append(line)
        body = "\n".join(lines)
        super().__init__(f"[bold]diff[/bold] {tool_name}\n{body}")
