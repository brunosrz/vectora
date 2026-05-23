"""Rich CLI Chat Interface for Vectora.

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
from langgraph.types import Command
from rich.console import Console
from rich.panel import Panel

from vectora.context import Context
from vectora.graph import build_graph
from vectora.services.log_setup import (
    set_console_log_level,
    setup_logging,
    setup_queue_handler,
)
from vectora.services.runtime_settings import runtime_settings
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
    HITLPanel,
    LogPanel,
    QuotaErrorPanel,
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
            "workspace_id": getattr(context, "workspace_id", None),
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


def _suspend(status_ctx: Any) -> None:
    try:
        if status_ctx is not None and hasattr(status_ctx, "stop"):
            status_ctx.stop()
    except Exception:
        pass


def _resume(status_ctx: Any) -> None:
    try:
        if status_ctx is not None and hasattr(status_ctx, "start"):
            status_ctx.start()
    except Exception:
        pass


def _render_tool_event_start(
    tool_name: str, tool_input: object, status_ctx: Any, verbosity: int = 0
) -> None:
    """Render tool-call start according to verbosity level.

    Level 0 — silent.
    Level 1 — one-line "[→ tool_name]" indicator.
    Level 2 — compact panel: tool name only, no args.
    Level 3 — panel with truncated args (≤ 200 chars).
    Level 4+ — panel with full args (≤ 600 chars, same as before).
    Terminal always gets special green treatment when verbosity ≥ 1.
    """
    if verbosity == 0:
        # Register terminal streaming silently so output still works
        if _is_terminal_tool(tool_name):
            if verbosity >= 1:
                pass
            register_terminal_output_callback(lambda line: None)
        return

    _suspend(status_ctx)

    if _is_terminal_tool(tool_name):
        command = ""
        if isinstance(tool_input, dict):
            command = str(tool_input.get("command", ""))  # ty: ignore[no-matching-overload]
        else:
            command = str(tool_input)

        if verbosity == 1:
            console.print("[dim green]→ terminal[/dim green]")
        else:
            console.print(TerminalPanel.render_command(command))

        def _stream_line(line: str) -> None:
            if verbosity >= 2:
                console.print(TerminalPanel.render_line(line))

        register_terminal_output_callback(_stream_line)
    elif verbosity == 1:
        console.print(f"[dim yellow]→ {tool_name}[/dim yellow]")
    elif verbosity == 2:
        console.print(ToolCallPanel.render(tool_name, None))
    elif verbosity == 3:
        args_obj = tool_input if isinstance(tool_input, dict) else {"input": tool_input}
        console.print(ToolCallPanel.render(tool_name, args_obj, max_len=200))  # ty: ignore[call-arg]
    else:
        args_obj = tool_input if isinstance(tool_input, dict) else {"input": tool_input}
        console.print(ToolCallPanel.render(tool_name, args_obj))  # ty: ignore[invalid-argument-type]

    _resume(status_ctx)


def _render_tool_event_end(
    tool_name: str, tool_output: object, status_ctx: Any, verbosity: int = 0
) -> None:
    """Render tool-call end according to verbosity level.

    Level 0 — silent.
    Level 1 — one-line "✓ tool_name" or "✗ tool_name" indicator.
    Level 2 — compact panel: status only, no content.
    Level 3 — panel with response truncated to 200 chars.
    Level 4+ — panel with full response (≤ 800 chars).
    """
    if hasattr(tool_output, "content"):
        output_str = str(tool_output.content)
    else:
        output_str = str(tool_output)

    is_error = output_str.lower().startswith(("erro", "error"))

    if verbosity == 0:
        if _is_terminal_tool(tool_name):
            unregister_terminal_output_callback()
        return

    _suspend(status_ctx)

    if _is_terminal_tool(tool_name):
        unregister_terminal_output_callback()
        if verbosity == 1:
            icon = "✗" if is_error else "✓"
            color = "red" if is_error else "green"
            console.print(f"[{color}]{icon} terminal done[/{color}]")
        elif verbosity == 2:
            icon = "✗ ERROR" if is_error else "✓ done"
            color = "red" if is_error else "green"
            console.print(f"[{color}][TERMINAL] {icon}[/{color}]")
        elif is_error:
            console.print(TerminalPanel.render_output(output_str))
        else:
            console.print(
                Panel(
                    "[green]✓ Command completed[/green]",
                    title="[bold green][TERMINAL DONE][/bold green]",
                    style="green",
                    border_style="green",
                    expand=False,
                )
            )
    elif verbosity == 1:
        icon = "✗" if is_error else "✓"
        color = "red" if is_error else "dim green"
        console.print(f"[{color}]{icon} {tool_name}[/{color}]")
    elif verbosity == 2:
        status = "ERROR" if is_error else "ok"
        color = "red" if is_error else "green"
        console.print(
            Panel(
                f"[{color}]{status}[/{color}]",
                title=f"[bold red][TOOL RESPONSE][/bold red] [dim]{tool_name}[/dim]"
                if is_error
                else f"[bold green][TOOL RESPONSE][/bold green] [dim]{tool_name}[/dim]",
                expand=False,
                border_style="red" if is_error else "green",
            )
        )
    elif verbosity == 3:
        truncated = output_str[:200] + ("…" if len(output_str) > 200 else "")
        console.print(ToolMessagePanel.render(tool_name, truncated, is_error=is_error))
    else:
        console.print(ToolMessagePanel.render(tool_name, output_str, is_error=is_error))

    _resume(status_ctx)


_AGENT_LABELS: dict[str, str] = {
    "respond": "Vectora",
    "rag": "Vectora RAG",
    "coder": "Vectora Coder",
    "search": "Vectora Search",
}

# Nós internos do RAG e da curadoria web que emitem tokens de LLMs utilitários
# (judge de curadoria, reranker) — esses tokens NÃO devem aparecer no chat.
_RAG_INTERNAL_NODES: frozenset[str] = frozenset(
    {
        "rag_retrieve",
        "rag_decide_node",
        "_rag_decide_node",
        "rag_websearch",
        "rag_rerank",
        "rag_inject",
        "process_retrieval",  # curation judge no loop de search
    }
)


def _extract_text_chunk(chunk: Any) -> str:
    """Extrai texto de um chunk de CHAT_MODEL_STREAM."""
    content = chunk.content if hasattr(chunk, "content") else None
    if not content:
        return ""
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts)
    if isinstance(content, dict) and "text" in content:
        return content["text"]
    return str(content)


def _handle_stream_event(
    event: dict,
    *,
    response_content: str,
    routing_decision: str,
    orchestrator_delegated: bool,
    status_ctx: Any,
    verbosity: int,
) -> tuple[str, str, bool]:
    """Processa um evento individual do astream_events.

    Retorna (response_content, routing_decision, orchestrator_delegated) atualizados.
    Extraído de _process_user_turn para ser reutilizado no loop de HITL resume.
    """
    event_type = event.get("event")
    event_name = event.get("name", "")
    node = event.get("metadata", {}).get("langgraph_node", "")

    # Streaming do conteúdo da IA.
    # Filtra duas categorias de tokens que NÃO devem aparecer no chat:
    #   1. Nós internos do RAG / curadoria (judge, reranker) — os tokens
    #      JSON do CurationDecision vazariam como lixo no painel.
    #   2. Primeira invocação do orchestrator — tokens do JSON de
    #      roteamento (OrchestratorDecision) gerados pelo structured output.
    if event_type == LangGraphEvent.CHAT_MODEL_STREAM:
        if node in _RAG_INTERNAL_NODES:
            # Nó utilitário interno — descartar silenciosamente
            pass
        elif node == "orchestrator" and not orchestrator_delegated:
            # Primeira invocação do orchestrator: JSON de roteamento — descartar
            pass
        else:
            chunk = event.get("data", {}).get("chunk")
            if chunk:
                response_content += _extract_text_chunk(chunk)

    # CHAIN_END do orchestrator: captura routing_decision e resposta.
    elif event_type == LangGraphEvent.CHAIN_END and event_name == "orchestrator":
        raw_output = event.get("data", {}).get("output", {})
        if hasattr(raw_output, "update") and isinstance(raw_output.update, dict):
            output = raw_output.update
        elif isinstance(raw_output, dict):
            output = raw_output
        else:
            output = {}

        if output:
            rd = output.get("routing_decision", "respond")
            if rd and rd != "respond":
                routing_decision = rd
                orchestrator_delegated = True
            elif rd == "respond":
                # Sempre "respond" → garante label correto mesmo após delegação
                routing_decision = "respond"
                # Captura a AIMessage do orchestrator.
                # Remove o guard `if not response_content` para que a síntese
                # pós-coder/search SOBREPONHA o streaming acumulado dos sub-agents.
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

    # Tool chamada: AMARELO (ou VERDE se terminal)
    elif event_type == LangGraphEvent.TOOL_START:
        tool_input = event.get("data", {}).get("input")
        _render_tool_event_start(event_name, tool_input, status_ctx, verbosity)

    # Tool retornou: VERMELHO (ou VERDE se terminal)
    elif event_type == LangGraphEvent.TOOL_END:
        tool_output = event.get("data", {}).get("output")
        _render_tool_event_end(event_name, tool_output, status_ctx, verbosity)

    # Fallback: captura AIMessage de nós legacy (call_llm, call_llm_debug)
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

    return response_content, routing_decision, orchestrator_delegated


async def _ask_hitl_decision(pending: list[dict], status_ctx: Any) -> dict:
    """Exibe o HITLPanel e lê a decisão do usuário (approve / reject).

    Pausa o spinner, renderiza o painel de confirmação, lê input inline
    e retoma o spinner antes de retornar.
    """
    _suspend(status_ctx)
    console.print(HITLPanel.render(pending))

    try:
        from prompt_toolkit import PromptSession  # type: ignore[attr-defined]
        from prompt_toolkit.patch_stdout import patch_stdout as _pso

        _ps = PromptSession("> ")  # type: ignore[type-arg]

        def _read() -> str:
            with _pso():
                return _ps.prompt()

        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, _read)
    except Exception:
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, input, "")

    answer = answer.strip().lower()
    _resume(status_ctx)

    # Qualquer input vazio, "s", "y", "sim", "yes" → aprovação
    if answer in ("", "s", "y", "sim", "yes"):
        return {"action": "approve"}
    return {"action": "reject"}


async def _process_user_turn(
    user_input: str,
    graph: CompiledStateGraph[State, Context, State, State],  # ty: ignore[invalid-type-arguments]
    config: RunnableConfig,
    audit: AuditPanel,
    status_panel: VectoraStatusPanel,
    verbosity: int = 0,
) -> str:
    """Process a single user turn e retorna a resposta do AI.

    Suporta HITL: quando o grafo pausa (interrupt() em hitl_check), exibe
    o painel de confirmação, lê a decisão do usuário e retoma o grafo com
    Command(resume=decision). O loop continua até o grafo terminar.

    Exibe eventos visuais ao longo do processamento:
    - Tool calls em AMARELO (ToolCallPanel)
    - Tool responses em VERMELHO (ToolMessagePanel)
    - Terminal commands/outputs em VERDE (TerminalPanel)
    - Confirmações HITL em AMARELO (HITLPanel)
    - Resposta final do LLM em magenta (ChatMessage)
    """
    import contextlib

    audit.add_message("User", user_input)
    console.print(ChatMessage("User", user_input).to_panel())

    response_content = ""
    routing_decision = "respond"
    _orchestrator_delegated = False

    # Usamos status_ctx manualmente para poder suspender/retomar o spinner
    # quando exibimos panels de tool (evita conflito visual com Live render)
    status_ctx = status_panel.thinking("Processing your message...")
    status_ctx.__enter__()

    # Entrada inicial para o grafo — após o primeiro turno, pode ser
    # Command(resume=...) quando retomando de um interrupt HITL
    graph_input: Any = {"messages": [HumanMessage(user_input)]}

    try:
        # Loop de execução + HITL: roda até o grafo terminar sem interrupt
        while True:
            # recursion_limit: 50 — defesa em profundidade (ver A6.2)
            async for event in graph.astream_events(
                graph_input,
                config={**config, "recursion_limit": 50},
                version="v2",
            ):
                response_content, routing_decision, _orchestrator_delegated = (
                    _handle_stream_event(
                        event,
                        response_content=response_content,
                        routing_decision=routing_decision,
                        orchestrator_delegated=_orchestrator_delegated,
                        status_ctx=status_ctx,
                        verbosity=verbosity,
                    )
                )

            # ── Verifica se o grafo pausou em um interrupt HITL ──────────────
            state = await graph.aget_state({**config, "recursion_limit": 50})
            interrupts = [
                intr for task in (state.tasks or []) for intr in (task.interrupts or ())
            ]

            if not interrupts:
                # Sem interrupt — turno finalizado normalmente
                break

            # Há pelo menos um interrupt HITL pendente
            payload: list[dict] = interrupts[0].value  # lista de {name, args, id}
            decision = await _ask_hitl_decision(payload, status_ctx)

            # Retoma o grafo com a decisão do usuário
            graph_input = Command(resume=decision)

    finally:
        with contextlib.suppress(Exception):
            status_ctx.__exit__(None, None, None)

    if response_content:
        # Marcador de quota: "quota rate limit:30:rpm" ou "quota rate limit:0:rpd"
        _stripped = response_content.strip()
        _is_quota_marker = _stripped.startswith("quota rate limit")
        if _is_quota_marker:
            import re

            try:
                from vectora.config.settings import settings

                _provider = settings.llm_provider or "LLM"
            except Exception:
                _provider = "LLM"
            # Formato: "quota rate limit:<segundos>:<kind>"
            _m = re.search(r"quota rate limit:(\d+):(\w+)", _stripped)
            _retry_after = int(_m.group(1)) if _m and int(_m.group(1)) > 0 else None
            _kind = _m.group(2) if _m else "unknown"
            console.print(QuotaErrorPanel.render(_provider, _retry_after, _kind))
        else:
            label = _AGENT_LABELS.get(routing_decision, "Vectora")
            console.print(ChatMessage(label, response_content).to_panel())
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
    """Chat loop with dashboard layout and live rendering."""
    from vectora.ui.commands import _load_debug_config

    verbosity: int = _load_debug_config()
    log_queue: Queue | None = None
    log_panel_obj: LogPanel | None = None

    def _apply_verbosity_logging(v: int) -> None:
        """Ajusta nível do console handler conforme verbosity.

        verbosity 0  → CRITICAL  (silencia tudo — console limpo para o usuário)
        verbosity 1+ → WARNING
        verbosity 2+ → INFO
        verbosity 4+ → DEBUG
        """
        if v == 0:
            set_console_log_level(logging.CRITICAL)
        elif v == 1:
            set_console_log_level(logging.WARNING)
        elif v >= 4:
            set_console_log_level(logging.DEBUG)
        else:
            set_console_log_level(logging.INFO)

    # Aplica imediatamente — antes de qualquer log aparecer na tela
    _apply_verbosity_logging(verbosity)

    def _setup_full_debug() -> None:
        """Set up live log panel (verbosity 5 only)."""
        nonlocal log_queue, log_panel_obj
        log_queue = Queue()
        setup_queue_handler(log_queue)
        log_panel_obj = LogPanel(log_queue, max_lines=15)
        logger.info("🔧 Full debug panel active")

    def _teardown_full_debug() -> None:
        """Remove live log panel."""
        nonlocal log_queue, log_panel_obj
        if log_queue is not None:
            try:
                while not log_queue.empty():
                    log_queue.get_nowait()
            except Exception:
                pass
        log_queue = None
        log_panel_obj = None

    # Initialize dashboard
    layout = VectoraLayout()

    # Set up full debug panel only at verbosity 5
    if verbosity >= 5:
        _setup_full_debug()
        assert log_queue is not None  # noqa: S101
        layout.split_with_debug(log_queue)

    status_panel = VectoraStatusPanel(console)
    audit = AuditPanel(max_visible=3)
    # Injetar contexto no configurable para que os nós possam acessá-lo
    config = RunnableConfig(
        configurable={
            "thread_id": context.thread_id,
            "context": context,
            "workspace_id": getattr(context, "workspace_id", None),
        }
    )
    # Track current thread_id to detect session changes
    current_thread_id = context.thread_id

    # Load prior messages
    message_count = await _load_prior_messages(graph, context, audit)

    # Update header and body based on mode
    debug_label = f" | [cyan]🔧 v={verbosity}[/cyan]" if verbosity > 0 else ""
    if verbosity >= 5:
        main_layout = layout.get_main_layout()
        main_layout["header"].update(
            Panel(
                f"[bold cyan][ROCKET] Vectora v{__version__}[/bold cyan] | "
                f"[yellow]Provider: {provider}[/yellow] | "
                f"[magenta]Thread: {context.thread_id}[/magenta] | "
                f"[green]Messages: {message_count}[/green]{debug_label}",
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
                old_verbosity = verbosity
                should_exit, context, verbosity = await handle_command(
                    user_input, config, console, context, verbosity
                )
                if should_exit:
                    console.print("\n[yellow][WAVE] Goodbye![/yellow]")
                    break

                # Atualiza nível de log do console quando verbosity muda
                if verbosity != old_verbosity:
                    _apply_verbosity_logging(verbosity)

                # Handle verbosity level 5 (full debug panel) transitions
                if verbosity >= 5 and log_queue is None:
                    _setup_full_debug()
                    assert log_queue is not None  # noqa: S101
                    layout.split_with_debug(log_queue)
                elif verbosity < 5 and log_queue is not None:
                    _teardown_full_debug()
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
                            "workspace_id": getattr(context, "workspace_id", None),
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
            await _process_user_turn(
                user_input, graph, config, audit, status_panel, verbosity
            )

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
            debug_label = f" | [cyan]🔧 v={verbosity}[/cyan]" if verbosity > 0 else ""
            if verbosity >= 5:
                main_layout = layout.get_main_layout()
                main_layout["header"].update(
                    Panel(
                        f"[bold cyan][ROCKET] Vectora v{__version__}[/bold cyan] | "
                        f"[yellow]Provider: {provider}[/yellow] | "
                        f"[magenta]Thread: {context.thread_id}[/magenta] | "
                        f"[green]Messages: {len(audit.messages)}[/green]{debug_label}",
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


async def _resolve_startup_session(
    settings: Any,
    *,
    force_new: bool = False,
    session_id: str | None = None,
) -> str:
    """Resolve which thread_id to use on startup based on the current directory.

    Priority:
    1. ``session_id`` explicit override (--session CLI flag) — use it if it exists.
    2. ``force_new`` (--new CLI flag) — always create a fresh session.
    3. Last session for cwd stored in runtime_settings — resume if still in DB.
    4. Fallback — create a new session and associate it with cwd.
    """
    from pathlib import Path

    from vectora.services.session import SessionService

    cwd = str(Path.cwd())

    try:
        session_service = SessionService(settings)
        await session_service.initialize()

        # ── 1. Explicit --session override ────────────────────────────────────
        if session_id is not None:
            existing = {s["thread_id"] for s in await session_service.list_all()}
            if session_id in existing:
                logger.info(
                    "Resuming explicit session",
                    extra={"thread_id": session_id},
                )
                return session_id
            logger.warning(
                "Session %s not found — creating a new session instead.", session_id
            )

        # ── 2. --new: skip resume, create fresh ───────────────────────────────
        if not force_new:
            last_id = runtime_settings.get_session_for_dir(cwd)
            if last_id is not None:
                existing = {s["thread_id"] for s in await session_service.list_all()}
                if last_id in existing:
                    logger.info(
                        "Resuming session for directory",
                        extra={"thread_id": last_id, "cwd": cwd},
                    )
                    return last_id

        # ── 3/4. Create a new session ─────────────────────────────────────────
        new_id = await session_service.create(working_directory=cwd)
        runtime_settings.set_session_for_dir(cwd, new_id)
        logger.info(
            "New session created for directory",
            extra={"thread_id": new_id, "cwd": cwd},
        )
        return new_id

    except Exception as e:
        logger.warning("Session resolution failed (%s) — using fallback session.", e)
        return "000001"


async def run_chat(
    settings: Any | None = None,
    *,
    force_new: bool = False,
    session_id: str | None = None,
) -> None:
    """Run the chat dashboard.

    Args:
        settings: Settings instance. If None, loads fresh from config.
        force_new: If True, always create a new session (--new flag).
        session_id: If given, resume this specific session ID (--session flag).
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

        thread_id = await _resolve_startup_session(
            settings,
            force_new=force_new,
            session_id=session_id,
        )
        # Determina workspace ativo para isolamento por projeto (B5)
        from pathlib import Path as _Path

        from vectora.services.workspace import workspace_registry as _ws_registry

        _ws = _ws_registry.get_or_create(str(_Path.cwd()))
        context = Context(user_type="default", thread_id=thread_id, workspace_id=_ws.id)

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
