"""Rich CLI Chat Interface for Vectora - "Rich Gorda" Dashboard.

Professional agent dashboard using Rich components for real-time rendering.
Features advanced layout, status indicators, and audit trails.

Features:
    - Three-panel dashboard (header, body, footer)
    - Real-time status updates for background workers
    - Markdown rendering for AI responses
    - Live audit panel with conversation history
    - Conversation export to markdown files
    - Professional error and success panels
    - Debug Mode with real-time log monitoring (God-Mode dashboard)
"""

import asyncio
import logging
import os
import warnings
from enum import StrEnum
from queue import Queue
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from prompt_toolkit import PromptSession

# Suppress UserWarnings from external libraries in quiet mode
if os.getenv("QUIET_MODE", "true").lower() == "true":
    warnings.filterwarnings("ignore", category=UserWarning)

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph, RunnableConfig
from rich.console import Console
from rich.panel import Panel

from vectora.context import Context
from vectora.graph import build_graph
from vectora.services.checkpoint import Checkpointer
from vectora.services.log_setup import setup_logging, setup_queue_handler
from vectora.services.terminal_stream import (
    register_terminal_output_callback,
    unregister_terminal_output_callback,
)
from vectora.services.utils import async_lifespan
from vectora.state import State
from vectora.ui.commands import handle_command
from vectora.ui.main import (
    AuditPanel,
    ChatMessage,
    LogPanel,
    SeparatorLine,
    SuccessPanel,
    TerminalPanel,
    ToolCallPanel,
    ToolMessagePanel,
    VectoraLayout,
    VectoraStatusPanel,
    WelcomeScreen,
)
from vectora.version import __version__

logger = logging.getLogger(__name__)


class LangGraphEvent(StrEnum):
    """LangGraph astream_events v2 event type strings.

    Using str mixin so comparisons with raw event["event"] strings work
    without unpacking — e.g. ``event_type == LangGraphEvent.CHAT_MODEL_STREAM``.
    """

    CHAT_MODEL_STREAM = "on_chat_model_stream"
    TOOL_START = "on_tool_start"
    TOOL_END = "on_tool_end"
    CHAIN_START = "on_chain_start"
    CHAIN_END = "on_chain_end"
    CHAIN_STREAM = "on_chain_stream"


class SafeConsole(Console):
    """Console wrapper that gracefully handles Unicode encoding errors on Windows."""

    def print(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """Print with fallback to plain text if encoding fails."""
        try:
            super().print(*args, **kwargs)  # type: ignore[arg-type]
        except UnicodeEncodeError:
            # Fallback: print plain text without rich formatting using UTF-8 binary output
            if args:
                import re
                import sys
                from io import StringIO

                # Try to render the renderable to plain text
                try:
                    # Create a temporary non-file console to extract text
                    temp_buffer = StringIO()
                    temp_console = Console(
                        file=temp_buffer,
                        force_terminal=False,
                        width=120,
                    )
                    temp_console.print(args[0], **kwargs)
                    text = temp_buffer.getvalue().rstrip("\n")
                except Exception:
                    # If that fails, just convert to string
                    text = str(args[0])

                # Remove rich markup tags for cleaner output
                text = re.sub(r"\[/?[^\]]*\]", "", text)
                # Write directly to stdout buffer with UTF-8 encoding
                # This bypasses the console's cp1252 encoding on Windows
                if text:
                    sys.stdout.buffer.write(
                        (text + "\n").encode("utf-8", errors="replace")
                    )


# Configure console for Windows compatibility
import sys

console = SafeConsole()


async def _export_audit(
    audit_panel: AuditPanel,
) -> None:
    """Display and save final message audit with rich formatting."""
    try:
        # Clear terminal
        import os

        os.system("cls" if os.name == "nt" else "clear")  # noqa: S605 ASYNC221

        try:
            console.print("\n")
            console.print(SeparatorLine.render("[LIST] SESSION AUDIT"))

            # Display audit messages using chat format
            for msg in audit_panel.messages:
                console.print(msg.to_panel())

            # Save to file
            audit_file = audit_panel.save_to_file()
            console.print(
                f"\n[green][OK] Audit saved to[/green] [dim]{audit_file}[/dim]"
            )
        except UnicodeEncodeError:
            # Fallback for Windows encoding issues - print without rich formatting
            print("\n=== SESSION AUDIT ===\n")
            for msg in audit_panel.messages:
                print(f"[{msg.role}]")
                print(msg.content)
                print("-" * 40)
            # Save to file
            audit_file = audit_panel.save_to_file()
            print(f"\nAudit saved to {audit_file}")

    except Exception as e:
        logger.warning(f"Audit failed: {e}")


async def _load_prior_messages(
    graph: CompiledStateGraph[State, Context, State, State],  # ty: ignore[invalid-type-arguments]
    context: Context,
    audit: AuditPanel,
) -> int:
    """Load prior messages from checkpointer into audit and display them."""
    config = RunnableConfig(
        configurable={
            "thread_id": context.thread_id,
            "context": context,
        }
    )
    try:
        state = await graph.aget_state(config)
        prior_messages = state.values.get("messages", [])
        for msg in prior_messages:
            role = "User" if isinstance(msg, HumanMessage) else "Vectora"
            audit.add_message(role, msg.content)
            # Display the message to the user
            console.print(ChatMessage(role, msg.content).to_panel())
        return len(prior_messages)
    except Exception as e:
        logger.warning(f"Could not load prior messages: {e}")
        return 0


def _is_terminal_tool(tool_name: str) -> bool:
    """Verifica se a tool é o terminal (precisa de UX especial verde)."""
    return tool_name.lower() in {"terminal", "terminal_tool"}


def _render_tool_event_start(
    tool_name: str, tool_input: object, status_ctx: Any
) -> None:
    """Exibe um evento de início de tool no console.

    Suspende o spinner momentaneamente para não embaralhar o panel.
    Terminal recebe tratamento verde especial; outras tools ficam amarelas.
    """
    try:
        if status_ctx is not None and hasattr(status_ctx, "stop"):
            status_ctx.stop()
    except Exception:
        pass

    if _is_terminal_tool(tool_name):
        # Comando shell em verde
        command = ""
        if isinstance(tool_input, dict):
            command = str(tool_input.get("command", ""))  # ty: ignore[no-matching-overload]
        else:
            command = str(tool_input)
        console.print(TerminalPanel.render_command(command))

        # Registra callback de streaming: cada linha chega em tempo real
        def _stream_line(line: str) -> None:
            console.print(TerminalPanel.render_line(line))

        register_terminal_output_callback(_stream_line)
    else:
        # Tool genérica em amarelo
        args_obj = tool_input if isinstance(tool_input, dict) else {"input": tool_input}
        console.print(ToolCallPanel.render(tool_name, args_obj))  # ty: ignore[invalid-argument-type]

    try:
        if status_ctx is not None and hasattr(status_ctx, "start"):
            status_ctx.start()
    except Exception:
        pass


def _render_tool_event_end(
    tool_name: str, tool_output: object, status_ctx: Any
) -> None:
    """Exibe um evento de fim de tool no console.

    Suspende o spinner momentaneamente para não embaralhar o panel.
    Terminal recebe tratamento verde; demais tools ficam vermelhas.
    """
    try:
        if status_ctx is not None and hasattr(status_ctx, "stop"):
            status_ctx.stop()
    except Exception:
        pass

    # Extrai conteúdo de string ou ToolMessage
    if hasattr(tool_output, "content"):
        output_str = str(tool_output.content)
    else:
        output_str = str(tool_output)

    is_error = output_str.lower().startswith(("erro", "error"))

    if _is_terminal_tool(tool_name):
        # Desregistra o callback de streaming — processo terminou
        unregister_terminal_output_callback()

        # Extrai exit code do output se presente (formato "[exit=N]" não existe
        # no output real, mas o returncode pode estar no log; exibe apenas
        # um painel compacto de conclusão — a saída já foi exibida linha a linha)
        is_error = output_str.lower().startswith(("erro", "error"))
        if is_error:
            # Erros aparecem completos para o usuário saber o que falhou
            console.print(TerminalPanel.render_output(output_str))
        else:
            # Sucesso: painel mínimo para não duplicar o que já foi streamado
            from rich.panel import Panel as _Panel

            console.print(
                _Panel(
                    "[green]✓ Command completed[/green]",
                    title="[bold green][TERMINAL DONE][/bold green]",
                    style="green",
                    border_style="green",
                    expand=False,
                )
            )
    else:
        # Resposta de tool genérica em vermelho
        console.print(ToolMessagePanel.render(tool_name, output_str, is_error=is_error))

    try:
        if status_ctx is not None and hasattr(status_ctx, "start"):
            status_ctx.start()
    except Exception:
        pass


async def _process_user_turn(
    user_input: str,
    graph: CompiledStateGraph[State, Context, State, State],  # ty: ignore[invalid-type-arguments]
    config: RunnableConfig,
    audit: AuditPanel,
    status_panel: VectoraStatusPanel,
) -> str:
    """Process a single user turn and return AI response.

    Exibe eventos visuais ao longo do processamento:
    - Tool calls em AMARELO (ToolCallPanel)
    - Tool responses em VERMELHO (ToolMessagePanel)
    - Terminal commands/outputs em VERDE (TerminalPanel)
    - Resposta final do LLM em magenta (ChatMessage)
    """
    audit.add_message("User", user_input)
    console.print(ChatMessage("User", user_input).to_panel())

    response_content = ""
    # Usamos status_ctx manualmente para poder suspender/retomar o spinner
    # quando exibimos panels de tool (evita conflito visual com Live render)
    status_ctx = status_panel.thinking("Processing your message...")
    status_ctx.__enter__()
    try:
        async for event in graph.astream_events(
            {"messages": [HumanMessage(user_input)]},
            config=config,
            version="v2",
        ):
            event_type = event.get("event")
            event_name = event.get("name", "")

            # Streaming do conteúdo da IA
            if event_type == LangGraphEvent.CHAT_MODEL_STREAM:
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and "text" in item:
                                response_content += item["text"]
                            elif isinstance(item, str):
                                response_content += item
                            else:
                                response_content += str(item)
                    elif isinstance(content, dict) and "text" in content:
                        response_content += content["text"]
                    else:
                        response_content += str(content)

            # Tool chamada: AMARELO (ou VERDE se terminal)
            elif event_type == LangGraphEvent.TOOL_START:
                tool_input = event.get("data", {}).get("input")
                _render_tool_event_start(event_name, tool_input, status_ctx)

            # Tool retornou: VERMELHO (ou VERDE se terminal)
            elif event_type == LangGraphEvent.TOOL_END:
                tool_output = event.get("data", {}).get("output")
                _render_tool_event_end(event_name, tool_output, status_ctx)

            # Captura AIMessage retornado diretamente pelo nó (sem streaming).
            # Acontece quando call_llm captura internamente um erro de quota/rate-limit
            # e retorna um AIMessage de fallback — nenhum CHAT_MODEL_STREAM é emitido.
            elif event_type == LangGraphEvent.CHAIN_END and event_name in (
                "call_llm",
                "call_llm_debug",
            ):
                if not response_content:
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict):
                        msgs = output.get("messages", [])
                        for msg in msgs:
                            if (
                                isinstance(msg, AIMessage)
                                and msg.content
                                and not getattr(msg, "tool_calls", None)
                            ):
                                c = msg.content
                                response_content = c if isinstance(c, str) else str(c)
                                break
    finally:
        import contextlib

        with contextlib.suppress(Exception):
            status_ctx.__exit__(None, None, None)

    if response_content:
        console.print(ChatMessage("Vectora", response_content).to_panel())
        audit.add_message("Vectora", response_content)

    return response_content


def _make_prompt_session() -> PromptSession:  # type: ignore[type-arg]
    """Cria e retorna uma PromptSession configurada com key bindings customizados.

    Separado de _read_multiline_input() para permitir criação única por sessão de chat,
    evitando re-instanciar key bindings e histórico de prompt a cada mensagem enviada.
    """
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings

    bindings = KeyBindings()

    @bindings.add("m-enter")  # Alt+Enter
    def _(event: object) -> None:
        """Insere quebra de linha quando Alt+Enter é pressionado."""
        event.current_buffer.insert_text("\n")  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]

    @bindings.add("s-enter")  # Shift+Enter
    def _(event: object) -> None:
        """Insere quebra de linha quando Shift+Enter é pressionado."""
        event.current_buffer.insert_text("\n")  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]

    return PromptSession("You: ", multiline=False, key_bindings=bindings)


# Sessão única — criada na primeira chamada e reutilizada durante todo o chat.
# Preserva histórico de input (seta ↑) e evita re-instanciar bindings a cada turno.
_prompt_session: PromptSession | None = None  # type: ignore[type-arg]


async def _read_multiline_input() -> str:
    """Lê input do usuário com suporte para multilinha via Alt+Enter.

    Comportamento:
    - Enter: envia a mensagem
    - Alt+Enter / Shift+Enter: adiciona quebra de linha
    - Qualquer output de log emitido enquanto o prompt está ativo (ex: background
      worker) é interceptado por patch_stdout() e impresso acima da linha de input,
      sem corromper o cursor do prompt_toolkit.

    Returns:
        String com input do usuário (pode conter quebras de linha).
    """
    global _prompt_session
    try:
        from prompt_toolkit.patch_stdout import patch_stdout

        if _prompt_session is None:
            _prompt_session = _make_prompt_session()

        session = _prompt_session

        def _prompt() -> str:
            # patch_stdout() redireciona qualquer escrita em sys.stdout/stderr
            # (incluindo logging.StreamHandler) para ser impressa acima do prompt,
            # impedindo que warnings do worker de background corrompam a linha de input.
            with patch_stdout():
                return session.prompt()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _prompt)

    except ImportError:
        # Fallback se prompt_toolkit não estiver disponível
        logger.debug("prompt_toolkit not available, using basic input")
        loop = asyncio.get_event_loop()
        sys.stdout.write("\033[1;36mYou: \033[0m")
        sys.stdout.flush()
        user_line = await loop.run_in_executor(None, sys.stdin.readline)
        return user_line.rstrip("\n")
    except Exception as e:
        # Log unexpected errors from prompt_toolkit initialization
        logger.debug(
            "Error in multiline input, falling back to basic input",
            extra={"error": type(e).__name__, "error_msg": str(e)},
        )
        loop = asyncio.get_event_loop()
        sys.stdout.write("\033[1;36mYou: \033[0m")
        sys.stdout.flush()
        user_line = await loop.run_in_executor(None, sys.stdin.readline)
        return user_line.rstrip("\n")


async def chat_loop(
    graph: CompiledStateGraph[State, Context, State, State],  # ty: ignore[invalid-type-arguments]
    checkpointer: AsyncSqliteSaver,
    context: Context,
    provider: str = "unset",
) -> None:
    """Rich Gorda chat loop with dashboard layout and live rendering."""
    # Initialize Debug Mode (load from persistent config)
    from vectora.ui.commands import _load_debug_config

    debug_mode = _load_debug_config()
    log_queue: Queue | None = None
    log_panel_obj: LogPanel | None = None

    def _setup_debug_mode() -> None:
        """Set up debug mode components (queue and panel)."""
        nonlocal log_queue, log_panel_obj
        log_queue = Queue()
        setup_queue_handler(log_queue)
        log_panel_obj = LogPanel(log_queue, max_lines=15)
        logger.info("🔧 Debug Mode enabled - God-Mode dashboard active")

    def _teardown_debug_mode() -> None:
        """Clean up debug mode components."""
        nonlocal log_queue, log_panel_obj
        if log_queue is not None:
            # Drain the queue to prevent lingering handler
            try:
                while not log_queue.empty():
                    log_queue.get_nowait()
            except Exception:
                pass
        log_queue = None
        log_panel_obj = None
        logger.info("Debug Mode disabled")

    # Initialize dashboard
    layout = VectoraLayout()

    # Set up debug mode if enabled
    if debug_mode:
        _setup_debug_mode()
        assert log_queue is not None  # noqa: S101
        layout.split_with_debug(log_queue)

    status_panel = VectoraStatusPanel(console)
    audit = AuditPanel(max_visible=3)
    # Injetar contexto no configurable para que os nós possam acessá-lo
    config = RunnableConfig(
        configurable={
            "thread_id": context.thread_id,
            "context": context,
        }
    )
    # Track current thread_id to detect session changes
    current_thread_id = context.thread_id

    # Load prior messages
    message_count = await _load_prior_messages(graph, context, audit)

    # Update header and body based on mode
    if debug_mode:
        main_layout = layout.get_main_layout()
        main_layout["header"].update(
            Panel(
                f"[bold cyan][ROCKET] Vectora v{__version__}[/bold cyan] | "
                f"[yellow]Provider: {provider}[/yellow] | "
                f"[magenta]Thread: {context.thread_id}[/magenta] | "
                f"[green]Messages: {message_count}[/green] | "
                f"[cyan]🔧 DEBUG MODE[/cyan]",
                style="blue",
                expand=False,
            )
        )
        main_layout["body"].update(WelcomeScreen.render(provider=provider))
        main_layout["footer"].update(
            Panel(
                "[green]*[/green] Background Worker | "
                "[cyan]Embedding Queue: 0[/cyan] | "
                "[yellow]RAG: Ready[/yellow]",
                style="dim",
                expand=False,
            )
        )
    else:
        layout.update_header(provider=provider, message_count=message_count)
        layout.update_body(WelcomeScreen.render(provider=provider))
        layout.update_footer()

    console.print(layout.render())
    console.print()

    # Display prior messages on screen
    if message_count > 0:
        for msg in audit.messages:
            console.print(msg.to_panel())

    # Main chat loop
    while True:
        try:
            user_input = await _read_multiline_input()

            # Handle system commands (/, /model, /help, etc)
            if user_input.startswith("/"):
                should_exit, context, debug_mode = await handle_command(
                    user_input, config, console, context, debug_mode
                )
                if should_exit:
                    console.print("\n[yellow][WAVE] Goodbye![/yellow]")
                    break

                # Handle debug mode changes
                old_debug_mode = log_queue is not None
                if debug_mode and not old_debug_mode:
                    # Debug mode was enabled
                    _setup_debug_mode()
                    assert log_queue is not None  # noqa: S101
                    layout.split_with_debug(log_queue)
                elif not debug_mode and old_debug_mode:
                    # Debug mode was disabled
                    _teardown_debug_mode()
                    layout = VectoraLayout()
                    layout.update_header(
                        provider=provider, message_count=len(audit.messages)
                    )
                    layout.update_body(audit.render())
                    layout.update_footer(embedding_queue=0, worker_active=True)
                    console.print(layout.render())

                # If context changed (new session), reset audit and update config
                if context.thread_id != current_thread_id:
                    old_thread_id = current_thread_id
                    current_thread_id = context.thread_id
                    audit = AuditPanel(max_visible=3)
                    config = RunnableConfig(
                        configurable={
                            "thread_id": context.thread_id,
                            "context": context,
                        }
                    )
                    console.print(
                        SuccessPanel.render(
                            f"Switched to session {context.thread_id} "
                            f"(from {old_thread_id})",
                            title="Session Switched",
                        )
                    )
                    console.print()
                    # Show welcome screen for the new session
                    console.print(WelcomeScreen.render(provider=provider))
                    logger.info(
                        f"Session switched: {old_thread_id} → {context.thread_id}"
                    )
                continue

            if not user_input.strip():
                continue

            # Process turn
            await _process_user_turn(user_input, graph, config, audit, status_panel)

            # Read real queue depth for footer display
            queue_depth = 0
            cohere_limited = False
            try:
                from vectora.config.settings import settings as _settings
                from vectora.services.background import get_background_worker
                from vectora.services.queue import get_embedding_queue

                if _settings.embedding_queue_enabled:
                    _q = await get_embedding_queue(_settings.embedding_queue_dsn)
                    queue_depth = await _q.count_pending()
                _bgw = await get_background_worker()
                cohere_limited = _bgw.rate_limit_active
            except Exception:
                pass

            # Update display
            if debug_mode:
                main_layout = layout.get_main_layout()
                main_layout["header"].update(
                    Panel(
                        f"[bold cyan][ROCKET] Vectora v{__version__}[/bold cyan] | "
                        f"[yellow]Provider: {provider}[/yellow] | "
                        f"[magenta]Thread: {context.thread_id}[/magenta] | "
                        f"[green]Messages: {len(audit.messages)}[/green] | "
                        f"[cyan]🔧 DEBUG MODE[/cyan]",
                        style="blue",
                        expand=False,
                    )
                )
                main_layout["body"].update(audit.render())
                cohere_footer_note = (
                    " | [bold yellow]⚠ Cohere limited[/bold yellow]"
                    if cohere_limited
                    else ""
                )
                main_layout["footer"].update(
                    Panel(
                        "[green]*[/green] Background Worker | "
                        f"[cyan]Embedding Queue: {queue_depth}[/cyan] | "
                        f"[yellow]RAG: Ready[/yellow]{cohere_footer_note}",
                        style="dim",
                        expand=False,
                    )
                )
                # Update debug panel with latest logs
                if log_panel_obj:
                    layout.update_debug_panel(log_panel_obj.render())
                console.print(layout.render())
            else:
                layout.update_header(
                    provider=provider, message_count=len(audit.messages)
                )
                layout.update_footer(
                    embedding_queue=queue_depth,
                    worker_active=True,
                    cohere_rate_limited=cohere_limited,
                )
                console.print(SeparatorLine.render())

        except KeyboardInterrupt:
            logger.info("Chat interrupted by user")
            console.print("\n[yellow][!] Chat interrupted[/yellow]")
            break
        except Exception as e:
            logger.exception("Chat error")
            console.print(
                Panel(
                    f"[red]{e!s}[/red]",
                    title="[bold red][X] Error[/bold red]",
                    style="red",
                )
            )

    # Export audit on exit
    await _export_audit(audit)


async def run_chat(settings: Any | None = None) -> None:
    """Run chat with Rich Gorda dashboard.

    Args:
        settings: Settings instance. If None, loads fresh from config.
    """
    from vectora.config.settings import Settings as SettingsClass

    if settings is None:
        setup_logging()
        settings = SettingsClass()

    logger.info("Chat started")

    # Display startup info
    startup_panel = Panel(
        "[bold cyan]Initializing Vectora...[/bold cyan]\n"
        "[dim]Using injected AgentManager and settings[/dim]",
        style="blue",
        expand=False,
    )
    console.print(startup_panel)

    async with async_lifespan():
        console.print("[green][*][/green] System initialized successfully\n")

        # Get LLM provider from settings
        provider = settings.get_llm_provider() if settings else "unset"

        context = Context(user_type="default", thread_id=1)

        try:
            # For now, still use legacy graph/checkpointer from agent
            # TODO Week 2: Replace with agent.chat() method
            from vectora.services.checkpoint import Checkpointer

            async with Checkpointer(settings.db_dsn) as checkpointer:
                graph = build_graph(checkpointer)
                await chat_loop(graph, checkpointer, context, provider=provider)
        except Exception as e:
            error_panel = Panel(
                f"[red]Critical error: {e!s}[/red]",
                title="[bold red][X] Fatal Error[/bold red]",
                style="red",
            )
            console.print(error_panel)
            logger.exception("Critical chat error")
        finally:
            logger.info("Chat ended")


if __name__ == "__main__":
    asyncio.run(run_chat())
