"""Rich UI Components for Vectora.

Advanced visual components using Rich for a professional, real-time CLI experience.
Includes layouts, status indicators, panels, and live rendering capabilities.
Features Debug Mode with real-time log panel for production monitoring.
"""

from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Any

from rich.console import Console, Group
from rich.layout import Layout
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from vectora.version import __version__


class VectoraLayout:
    """Professional dashboard layout for Vectora chat."""

    def __init__(self) -> None:
        """Initialize the dashboard layout."""
        self.layout = Layout()
        self._build_layout()

    def _build_layout(self) -> None:
        """Build the three-section layout: header, body, footer."""
        self.layout.split_column(
            Layout(name="header", size=4),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

    def update_header(
        self,
        provider: str = "unset",
        thread_id: int = 1,
        message_count: int = 0,
    ) -> None:
        """Update header with session info."""
        # Logo colors: Indigo (#4F46E5) background, White V, Cyan (#0EA5E9) dot
        header_text = (
            f"[bold white]V[/bold white][bold #0EA5E9]•[/bold #0EA5E9] [bold white]Vectora v{__version__}[/bold white] | "
            f"[#0EA5E9]Provider: {provider}[/#0EA5E9] | "
            f"[#FFFFFF]Thread: {thread_id}[/#FFFFFF] | "
            f"[#FFFFFF]Messages: {message_count}[/#FFFFFF]"
        )
        self.layout["header"].update(
            Panel(header_text, style="on #4F46E5", expand=False)
        )

    def update_body(self, content: str | Panel | Table) -> None:
        """Update main body with chat or content."""
        self.layout["body"].update(content)

    def update_footer(
        self,
        embedding_queue: int = 0,
        rag_status: str = "Ready",
        *,
        worker_active: bool = False,
        cohere_rate_limited: bool = False,
    ) -> None:
        """Update footer with background worker status."""
        worker_indicator = "[green]*[/green]" if worker_active else "[dim]o[/dim]"
        cohere_indicator = (
            " | [bold yellow]⚠ Cohere limited[/bold yellow]"
            if cohere_rate_limited
            else ""
        )
        footer_text = (
            f"{worker_indicator} Background Worker | "
            f"[cyan]Embedding Queue: {embedding_queue}[/cyan] | "
            f"[yellow]RAG: {rag_status}[/yellow]"
            f"{cohere_indicator}"
        )
        self.layout["footer"].update(Panel(footer_text, style="dim", expand=False))

    def render(self) -> Layout:
        """Return the layout for rendering."""
        return self.layout

    def split_with_debug(self, log_queue: Queue) -> Layout:
        """Return layout with debug panel in right sidebar (Debug Mode)."""
        self.layout.split_column(
            Layout(name="main"),
            Layout(name="debug", size=40),
        )
        self.layout["main"].split_column(
            Layout(name="header", size=4),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )
        return self.layout

    def get_main_layout(self) -> Layout:
        """Get the main layout area (for use in split mode)."""
        return self.layout["main"]

    def update_debug_panel(self, log_panel: Panel) -> None:
        """Update debug panel with log data."""
        if "debug" in self.layout.children:
            self.layout["debug"].update(log_panel)


class LogPanel:
    """Real-time log display panel for Debug Mode."""

    def __init__(self, log_queue: Queue, max_lines: int = 20) -> None:
        """Initialize log panel.

        Args:
            log_queue: Queue containing log records
            max_lines: Maximum lines to display (circular buffer)
        """
        self.log_queue = log_queue
        self.max_lines = max_lines
        self.logs: list[tuple[str, str]] = []  # (level, message) tuples

    def _get_log_color(self, level: str) -> str:
        """Get color for log level."""
        level_colors = {
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold red",
        }
        return level_colors.get(level, "white")

    def update_logs(self) -> None:
        """Pull new logs from queue (non-blocking)."""
        while not self.log_queue.empty():
            try:
                record = self.log_queue.get_nowait()
                level = record.levelname
                message = record.getMessage()
                self.logs.append((level, message))

                # Keep only the last N lines
                if len(self.logs) > self.max_lines:
                    self.logs.pop(0)
            except Exception:
                break

    def render(self) -> Panel:
        """Render log panel as styled table."""
        self.update_logs()

        table = Table(show_header=False, box=None, padding=(0, 1))

        if not self.logs:
            table.add_row("[dim]No logs yet...[/dim]")
        else:
            # Show most recent logs at the bottom
            for level, message in self.logs[-self.max_lines :]:
                color = self._get_log_color(level)
                level_badge = f"[{color}][{level:7}][/{color}]"
                table.add_row(f"{level_badge} {message}")

        return Panel(
            table,
            title="[bold cyan][GEAR] DEBUG LOGS[/bold cyan]",
            style="cyan",
            expand=True,
            border_style="cyan",
        )


class VectoraStatusPanel:
    """Real-time status panel for long-running operations."""

    def __init__(self, console: Console) -> None:
        """Initialize status panel."""
        self.console = console

    def thinking(self, message: str = "Thinking...") -> Any:
        """Show a spinner while the model thinks."""
        return self.console.status(
            f"[bold cyan]{message}[/bold cyan]",
            spinner="dots",
            spinner_style="cyan",
        )

    def processing_documents(self, count: int) -> Panel:
        """Show document processing status."""
        table = Table(show_header=False, box=None)
        table.add_row("[cyan]Documents Processed[/cyan]", f"[bold]{count}[/bold]")
        return Panel(table, title="[bold]RAG Pipeline[/bold]", style="green")

    def connection_test(self) -> Any:
        """Show spinner for connection testing."""
        return self.console.status(
            "[bold cyan]Testing connection to LLM...[/bold cyan]",
            spinner="dots",
        )


class ChatMessage:
    """Formatted chat message with styling."""

    def __init__(self, role: str, content: str) -> None:
        """Initialize a chat message."""
        self.role = role
        self.content = content
        self.timestamp = datetime.now()

    def to_panel(self) -> Panel:
        """Render as a styled panel."""
        if self.role.lower() == "user":
            return Panel(
                self.content,
                title="[bold cyan][USER] You: [/bold cyan]",
                style="cyan",
                expand=False,
                border_style="cyan",
            )
        # Render AI response as markdown for better formatting.
        # O role carrega o label correto: "Vectora", "Vectora RAG", etc.
        markdown = Markdown(self.content)
        return Panel(
            markdown,
            title=f"[bold magenta][{self.role}][/bold magenta]",
            style="magenta",
            expand=False,
            border_style="magenta",
        )

    def to_markdown_line(self) -> str:
        """Render as markdown for file export."""
        role_text = "**User**" if self.role.lower() == "user" else "**Vectora**"
        return f"## {role_text}\n\n{self.content}\n\n---\n\n"


class QuotaErrorPanel:
    """Painel estilizado para erros de quota/rate-limit do LLM."""

    _DASHBOARD_URLS: dict[str, str] = {
        "google-genai": "https://aistudio.google.com/plan_information",
        "openai": "https://platform.openai.com/usage",
        "anthropic": "https://console.anthropic.com/settings/usage",
        "cohere": "https://dashboard.cohere.com/",
    }

    @staticmethod
    def render(
        provider: str = "LLM",
        retry_after: int | None = None,
        kind: str = "unknown",
    ) -> Panel:
        """Renderiza aviso de quota como panel Vectora amarelo.

        Args:
            provider: nome do provedor (ex: "google-genai", "openai").
            retry_after: segundos até o limite resetar, se disponível na API.
            kind: "rpm" | "rpd" | "unknown"
        """
        dashboard = QuotaErrorPanel._DASHBOARD_URLS.get(provider, "")
        dashboard_line = f"\n\nVerifique seu uso em: {dashboard}" if dashboard else ""

        if kind == "rpd":
            title_extra = " — Cota Diária"
            body = (
                f"**Limite de cota diária atingido ({provider})**\n\n"
                "Você esgotou a cota diária do provedor. "
                "O limite reseta às **00:00 PT** (meia-noite, horário do Pacífico).\n\n"
                "_Considere aguardar o reset ou fazer upgrade do plano._"
                f"{dashboard_line}"
            )
        elif kind == "rpm" and retry_after:
            title_extra = " — Por Minuto"
            body = (
                f"**Limite por minuto atingido ({provider})**\n\n"
                f"Aguarde **{retry_after}s** e tente novamente. "
                "Sua cota total **não foi consumida**.\n\n"
                "_Dica: envie mensagens com um intervalo de alguns segundos._"
                f"{dashboard_line}"
            )
        else:
            title_extra = ""
            body = (
                f"**Rate limit atingido ({provider})**\n\n"
                "O provedor retornou **429 Too Many Requests**. "
                "Aguarde alguns segundos e tente novamente.\n\n"
                "_Se persistir após horas de inatividade, pode ser cota diária esgotada._"
                f"{dashboard_line}"
            )

        content = Group(Markdown(body))
        return Panel(
            content,
            title=f"[bold yellow][Vectora] Rate Limit (429){title_extra}[/bold yellow]",
            style="yellow",
            expand=False,
            border_style="yellow",
        )


class ToolCallPanel:
    """Painel amarelo para exibir chamadas de tools pelo agente."""

    @staticmethod
    def render(
        tool_name: str,
        tool_args: dict[str, Any] | str | None = None,
        max_len: int = 600,
    ) -> Panel:
        """Renderiza chamada de tool com argumentos.

        Args:
            tool_name: Nome da ferramenta chamada
            tool_args: Argumentos passados (dict ou string)

        Returns:
            Panel amarelo com ícone de ferramenta
        """
        import json

        if isinstance(tool_args, dict):
            try:
                args_repr = json.dumps(tool_args, indent=2, ensure_ascii=False)
            except TypeError, ValueError:
                args_repr = str(tool_args)
        elif tool_args is None:
            args_repr = "{}"
        else:
            args_repr = str(tool_args)

        # Limita tamanho para não poluir o terminal
        if len(args_repr) > max_len:
            args_repr = args_repr[:max_len] + "\n... [truncated]"

        body = f"[bold yellow]{escape(tool_name)}[/bold yellow]\n[dim]{escape(args_repr)}[/dim]"
        return Panel(
            body,
            title="[bold yellow][TOOL CALL][/bold yellow]",
            style="yellow",
            border_style="yellow",
            expand=False,
        )


class ToolMessagePanel:
    """Painel vermelho para exibir respostas (resultados) das tools."""

    @staticmethod
    def render(tool_name: str, content: str, *, is_error: bool = False) -> Panel:
        """Renderiza resposta de tool.

        Args:
            tool_name: Nome da ferramenta que respondeu
            content: Conteúdo da resposta
            is_error: Se True, destaca como erro

        Returns:
            Panel vermelho (canonical para tool messages)
        """
        # Limita tamanho para não poluir o terminal
        max_len = 800
        truncated = content[:max_len] + (
            f"\n... [truncated {len(content) - max_len} chars]"
            if len(content) > max_len
            else ""
        )

        prefix = "[bold red][X] ERROR[/bold red]\n" if is_error else ""
        body = f"{prefix}[red]{escape(truncated)}[/red]"

        return Panel(
            body,
            title=f"[bold red][TOOL RESPONSE][/bold red] [dim]{escape(tool_name)}[/dim]",
            style="red",
            border_style="red",
            expand=False,
        )


class TerminalPanel:
    """Painel verde para exibir comandos de terminal e suas saídas em tempo real."""

    @staticmethod
    def render_command(command: str) -> Panel:
        """Renderiza o comando que vai ser executado.

        Args:
            command: Comando shell

        Returns:
            Panel verde claro com prompt $ comando
        """
        return Panel(
            f"[bold green]$[/bold green] [bright_green]{escape(command)}[/bright_green]",
            title="[bold green][TERMINAL][/bold green]",
            style="green",
            border_style="green",
            expand=False,
        )

    @staticmethod
    def render_line(line: str) -> Text:
        """Renderiza uma linha individual de saída em tempo real.

        Usada pelo callback de streaming para exibir cada linha assim que
        chega do processo, antes do comando terminar.

        Args:
            line: Linha de saída (sem newline)

        Returns:
            Rich Text verde formatado
        """
        from rich.text import Text as _Text

        t = _Text()
        t.append("  │ ", style="dim green")
        t.append(line, style="green")
        return t

    @staticmethod
    def render_output(output: str, *, exit_code: int | None = None) -> Panel:
        """Renderiza a saída do terminal.

        Args:
            output: stdout + stderr combinados
            exit_code: Exit code do processo (None se ainda rodando)

        Returns:
            Panel verde com saída
        """
        # Trunca para não estourar a tela
        max_len = 2000
        truncated = output[:max_len] + (
            f"\n... [truncated {len(output) - max_len} chars]"
            if len(output) > max_len
            else ""
        )

        title_suffix = f" [dim]exit={exit_code}[/dim]" if exit_code is not None else ""

        return Panel(
            f"[green]{escape(truncated) or '(no output)'}[/green]",
            title=f"[bold green][TERMINAL OUTPUT][/bold green]{title_suffix}",
            style="green",
            border_style="green",
            expand=False,
        )


class AuditPanel:
    """Panel for displaying conversation audit and history."""

    def __init__(self, max_visible: int = 5) -> None:
        """Initialize audit panel."""
        self.messages: list[ChatMessage] = []
        self.max_visible = max_visible

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the audit."""
        self.messages.append(ChatMessage(role, content))

    def render(self) -> Panel:
        """Render audit as a table."""
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Role", style="bold")
        table.add_column("Content", style="white")

        # Show only the last N messages
        for i, msg in enumerate(self.messages[-self.max_visible :], 1):
            content_preview = (
                msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            )
            role_emoji = "[USER]" if msg.role.lower() == "user" else "[Vectora]"
            table.add_row(str(i), f"{role_emoji} {msg.role}", content_preview)

        return Panel(
            table,
            title="[bold][LIST] Recent Messages[/bold]",
            style="green",
            expand=False,
        )

    def to_markdown(self) -> str:
        """Export entire audit as markdown."""
        lines = [
            f"# Session Audit - {len(self.messages)} messages\n\n",
            f"*Generated: {datetime.now().isoformat()}*\n\n",
        ]
        lines.extend(msg.to_markdown_line() for msg in self.messages)
        return "".join(lines)

    def save_to_file(self, filepath: Path | None = None) -> Path:
        """Save audit to file."""
        if filepath is None:
            log_dir = Path.home() / ".vectora" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            filepath = (
                log_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            )

        filepath.write_text(self.to_markdown(), encoding="utf-8")
        return filepath


class WelcomeScreen:
    """Welcome and information screen."""

    @staticmethod
    def render(provider: str = "unset", model: str = "unknown") -> Group:
        """Render welcome screen — header + the exact same panel used by /list."""
        from vectora.ui.commands.help import build_commands_panel

        header_text = f"""[bold cyan]Welcome to Vectora![/bold cyan]

[yellow]Provider:[/yellow] {provider}  |  [yellow]Model:[/yellow] {model}

[bold cyan]⌨️  Dicas de Entrada:[/bold cyan]

[bold green]Enter[/bold green]          [dim]Enviar mensagem[/dim]
[bold green]Alt+Enter[/bold green]      [dim]Quebra de linha[/dim]
[bold green]Shift+Enter[/bold green]    [dim]Quebra de linha (alternativa)[/dim]
"""
        header = Panel(
            header_text,
            title="[bold cyan][ROCKET] Vectora Chat[/bold cyan]",
            expand=True,
        )
        return Group(header, build_commands_panel())


class ProgressIndicator:
    """Beautiful progress indicators for long operations."""

    def __init__(self, console: Console) -> None:
        """Initialize progress indicator."""
        self.console = console

    def embedding_progress(self, total: int) -> Progress:
        """Show embedding progress bar."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=self.console,
        )

    def stream_indicator(self) -> Text:
        """Animated streaming indicator."""
        return Text("▌", style="bold cyan")


class ErrorPanel:
    """Professional error display."""

    @staticmethod
    def render(error: Exception | str, title: str = "Error") -> Panel:
        """Render error as styled panel."""
        error_text = str(error)
        return Panel(
            f"[red]{escape(error_text)}[/red]",
            title=f"[bold red][X] {escape(title)}[/bold red]",
            style="red",
            expand=False,
            border_style="red",
        )


class SuccessPanel:
    """Professional success display."""

    @staticmethod
    def render(message: str, title: str = "Success") -> Panel:
        """Render success as styled panel."""
        return Panel(
            f"[green]{escape(message)}[/green]",
            title=f"[bold green][OK] {escape(title)}[/bold green]",
            style="green",
            expand=False,
            border_style="green",
        )


class HITLPanel:
    """Painel laranja de confirmação HITL (Human-in-the-Loop).

    Exibido quando o coder tenta executar uma ação destrutiva
    (terminal ou file_write) antes de pedir aprovação do usuário.
    """

    @staticmethod
    def render(pending: list[dict]) -> Panel:
        """Renderiza o painel de confirmação HITL.

        Args:
            pending: lista de {name, args, id} das tools aguardando aprovação.
        """
        import json

        lines: list[str] = []
        for tc in pending:
            name = tc.get("name", "unknown")
            args = tc.get("args", {})

            if name in ("terminal", "terminal_tool"):
                cmd = args.get("command", str(args))
                if len(cmd) > 300:
                    cmd = cmd[:300] + "…"
                lines.append(f"[bold yellow]$ {escape(cmd)}[/bold yellow]")

            elif name in ("file_write", "file_write_tool"):
                path = args.get("path", args.get("file_path", "?"))
                content = str(args.get("content", ""))
                preview = content[:200] + ("…" if len(content) > 200 else "")
                lines.append(
                    f"[bold yellow]escrever:[/bold yellow] [white]{escape(str(path))}[/white]\n"
                    f"[dim]{escape(preview)}[/dim]"
                )

            else:
                try:
                    args_str = json.dumps(args, ensure_ascii=False)[:200]
                except Exception:
                    args_str = str(args)[:200]
                lines.append(
                    f"[bold yellow]{escape(name)}[/bold yellow] "
                    f"[dim]{escape(args_str)}[/dim]"
                )

        body = "\n\n".join(lines)
        body += (
            "\n\n[bold]Executar? [[green]S[/green]/[red]n[/red]][/bold]  "
            "[dim](Enter = confirmar)[/dim]"
        )

        return Panel(
            body,
            title="[bold yellow]⚠  HITL — Confirmação necessária[/bold yellow]",
            style="yellow",
            border_style="yellow",
            expand=False,
        )


class SeparatorLine:
    """Visual separator between sections."""

    @staticmethod
    def render(title: str = "") -> Rule:
        """Render a separator line."""
        return Rule(f"[bold]{title}[/bold]" if title else "", style="dim")
