"""MCP tool: invoca ferramentas de outros servidores via Model Context Protocol.

Usa o `MultiServerMCPClient` oficial da biblioteca `langchain-mcp-adapters`.
O cliente carrega tools LangChain-compatíveis de servidores MCP externos
configurados em settings (`mcp_server_url` e/ou `mcp_command`).

Ganhos sobre a implementação antiga (client customizado, quebrado):
- `get_tools()` devolve `BaseTool` prontos — sem parsing manual de JSON-RPC
- `tool_interceptors` para logging/observabilidade de cada chamada externa
- Suporte nativo a stdio, SSE e streamable_http
- Sessões persistentes via `async with client.session(...)`
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING, Any

from langchain.tools import tool

from src.settings import settings

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except ImportError:
    MultiServerMCPClient = None  # type: ignore[assignment,misc]  # ty: ignore[invalid-assignment]

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

# Cache global — reutiliza cliente e tools entre chamadas.
# Protegido por lock para evitar race condition em inicialização concorrente.
_mcp_client: Any | None = None
_mcp_tools_by_name: dict[str, Any] | None = None
_mcp_lock: asyncio.Lock = asyncio.Lock()


# ---------------------------------------------------------------------------
# Interceptor — observabilidade de tools de servidores MCP externos
# ---------------------------------------------------------------------------


async def _logging_interceptor(
    request: Any,
    handler: Callable[[Any], Awaitable[Any]],
) -> Any:
    """Loga cada chamada a tools de servidores MCP externos.

    Satisfaz o Protocol `ToolCallInterceptor` (callable async). Nunca altera
    request/result — só registra timing e nome para auditoria. Falhas de log
    jamais quebram a chamada da tool.
    """
    name = getattr(request, "name", "?")
    server = getattr(request, "server_name", "?")
    t0 = time.perf_counter()
    logger.info("mcp_external_tool_call", extra={"tool": name, "server": server})
    try:
        result = await handler(request)
    except Exception:
        logger.exception("mcp_external_tool_failed", extra={"tool": name})
        raise
    logger.debug(
        "mcp_external_tool_done",
        extra={"tool": name, "elapsed_s": round(time.perf_counter() - t0, 3)},
    )
    return result


# ---------------------------------------------------------------------------
# Configuração de conexões
# ---------------------------------------------------------------------------


def _build_connections() -> dict[str, dict[str, Any]]:
    """Monta o dict de conexões a partir das settings.

    Formato exigido pelo MultiServerMCPClient 0.2.x: cada servidor é um dict
    com `transport` ("stdio" | "sse" | "streamable_http") + campos específicos.
    """
    connections: dict[str, dict[str, Any]] = {}

    if settings.mcp_server_url:
        # URL → transport HTTP. mcp_transport_type "http" mapeia para o
        # streamable_http moderno; "sse" mantém o legado SSE.
        transport = "sse" if settings.mcp_transport_type == "sse" else "streamable_http"
        connections["default"] = {
            "transport": transport,
            "url": settings.mcp_server_url,
        }

    if settings.mcp_command:
        connections["local"] = {
            "transport": "stdio",
            "command": settings.mcp_command,
            "args": settings.mcp_command_args or [],
        }

    return connections


async def _get_mcp_client() -> Any | None:
    """Obtém ou cria a instância global do MultiServerMCPClient."""
    global _mcp_client

    if _mcp_client is not None:
        return _mcp_client

    if MultiServerMCPClient is None:
        logger.warning("langchain-mcp-adapters não instalado")
        return None

    connections = _build_connections()
    if not connections:
        logger.debug("Nenhum servidor MCP configurado (mcp_server_url/mcp_command)")
        return None

    async with _mcp_lock:
        if _mcp_client is not None:  # double-check após o lock
            return _mcp_client
        try:
            _mcp_client = MultiServerMCPClient(
                connections,  # ty: ignore[invalid-argument-type]
                tool_interceptors=[_logging_interceptor],
            )
            logger.info(
                "MCP client inicializado",
                extra={"servers": list(connections.keys())},
            )
        except Exception:
            logger.exception("Falha ao inicializar MCP client")
            _mcp_client = None

    return _mcp_client


async def _get_mcp_tools() -> dict[str, Any]:
    """Carrega as tools de todos os servidores MCP configurados.

    Returns:
        Dict {tool_name: BaseTool}. Vazio se nenhum servidor disponível.
    """
    global _mcp_tools_by_name

    if _mcp_tools_by_name is not None:
        return _mcp_tools_by_name

    client = await _get_mcp_client()
    if client is None:
        return {}

    try:
        tools = await client.get_tools()
        _mcp_tools_by_name = {t.name: t for t in tools}
        logger.info("MCP tools carregadas", extra={"count": len(_mcp_tools_by_name)})
    except Exception:
        logger.exception("Falha ao listar MCP tools")
        _mcp_tools_by_name = {}

    return _mcp_tools_by_name


@tool(
    extras={
        "render_hint": "json",
        "category": "mcp",
        "destructive": False,
        "icon": "share-2",
    }
)
async def call_mcp_tool(tool_name: str, arguments: str) -> str:
    """Invoca uma ferramenta de outro servidor MCP via Model Context Protocol.

    Use para encadear capacidades de servidores MCP externos registrados em
    settings (`mcp_server_url` ou `mcp_command`).

    Args:
        tool_name: Nome da ferramenta no servidor MCP
        arguments: Argumentos em formato JSON string (ex: '{"query": "x"}')

    Returns:
        Resposta da ferramenta MCP, ou mensagem de erro descritiva
    """
    if MultiServerMCPClient is None:
        return "MCP indisponível. Instale: pip install langchain-mcp-adapters"

    if not settings.enable_mcp:
        return "MCP desabilitado. Defina ENABLE_MCP=true para usar servidores externos."

    try:
        args_dict: dict[str, Any] = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError as e:
        return f"Erro: 'arguments' deve ser JSON válido — {e}"

    tools = await _get_mcp_tools()
    if not tools:
        return (
            "Nenhuma tool MCP disponível. Verifique mcp_server_url / mcp_command "
            "nas configurações."
        )

    target = tools.get(tool_name)
    if target is None:
        return (
            f"Tool MCP '{tool_name}' não encontrada. "
            f"Disponíveis: {', '.join(sorted(tools))}"
        )

    logger.info("call_mcp_tool", extra={"tool": tool_name})

    try:
        async with asyncio.timeout(settings.mcp_timeout):
            result = await target.ainvoke(args_dict)
        return str(result)
    except TimeoutError:
        logger.warning("call_mcp_tool timeout", extra={"tool": tool_name})
        return f"Erro: tool MCP '{tool_name}' excedeu {settings.mcp_timeout}s."
    except Exception as e:
        logger.exception("call_mcp_tool_failed", extra={"tool": tool_name})
        return f"Erro ao invocar tool MCP '{tool_name}': {e!s}"
