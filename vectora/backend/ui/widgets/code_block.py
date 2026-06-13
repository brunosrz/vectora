"""CodeBlockWidget — render_hint: code_block."""

from __future__ import annotations

from textual.widgets import Static


class CodeBlockWidget(Static):
    """Displays a tool result as a syntax-highlighted code block."""

    DEFAULT_CSS = """
    CodeBlockWidget {
        background: $panel;
        border: round $primary-darken-2;
        padding: 0 1;
        margin: 0 0 1 0;
    }
    """

    def __init__(self, tool_name: str, content: str, is_error: bool = False) -> None:
        color = "red" if is_error else "green"
        header = f"[bold {color}]❯ {tool_name}[/bold {color}]"
        body = content[:2000] + ("…" if len(content) > 2000 else "")
        super().__init__(f"{header}\n{body}")
