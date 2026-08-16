"""Registry de servidores MCP por usuário.

Cada usuário tem sua própria lista de servidores MCP (plugins), persistida em
``~/.vectora/mcp/<user_id>.json``. As tools desses servidores entram no
toolset via ``VectoraMCPClient`` (``backend/tools/mcp.py``). O isolamento por
arquivo garante que um usuário não veja os plugins de outro.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, create_model

from backend.tools.langchain_bridge import as_langchain_tool
from backend.tools.mcp import VectoraMCPClient
from backend.tools.registry import ToolExtras, ToolSpec

logger = logging.getLogger(__name__)

_HEALTH_TIMEOUT_S = 10

#: Contador de versão por usuário — bumpado a cada add/remove. Permite invalidar
#: caches downstream (tools MCP resolvidas, LLM bindado) sem reiniciar.
_versions: dict[str, int] = {}

#: Cache das tools MCP resolvidas: user_id -> (version, tools).
_mcp_tools_cache: dict[str, tuple[int, list]] = {}


def _plugins_dir() -> Path:
    """Diretório base dos arquivos de plugins por usuário."""
    return Path.home() / ".vectora" / "mcp"


def tools_version(user_id: str) -> int:
    """Versão atual da configuração MCP do usuário (muda em add/remove)."""
    return _versions.get(user_id, 0)


def _bump_version(user_id: str) -> None:
    _versions[user_id] = _versions.get(user_id, 0) + 1
    # Avisa as demais réplicas — no modo lite é um no-op local.
    import json

    from backend.persistence.kv import publish_soon

    publish_soon(
        "vectora:tools",
        json.dumps({"user_id": user_id, "version": _versions[user_id]}),
    )


def apply_remote_version(user_id: str, version: int) -> None:
    """Aplica um bump de versão vindo de outra réplica (via cache_sync).

    Avança a versão local e descarta o cache de tools do usuário — o LLM
    bindado (``llm_tools._bound_cache``) é invalidado por consequência, pois
    sua chave inclui esta versão.
    """
    if version <= _versions.get(user_id, 0):
        return
    _versions[user_id] = version
    _mcp_tools_cache.pop(user_id, None)


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------


class McpServer(BaseModel):
    name: str
    transport: str = "stdio"  # stdio | sse | http
    command: str = ""  # usado por stdio
    args: list[str] = []
    url: str = ""  # usado por sse/http


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


def _user_file(user_id: str) -> Path:
    safe = user_id.replace("/", "_").replace("\\", "_") or "local"
    return _plugins_dir() / f"{safe}.json"


def list_servers(user_id: str) -> list[McpServer]:
    """Lista os servidores MCP do usuário."""
    path = _user_file(user_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("plugins: arquivo inválido para %s", user_id)
        return []
    out: list[McpServer] = []
    for item in data.get("servers", []):
        try:
            out.append(McpServer(**item))
        except Exception:
            logger.debug("plugins: servidor inválido ignorado: %s", item)
    return out


def _save(user_id: str, servers: list[McpServer]) -> None:
    path = _user_file(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"servers": [s.model_dump() for s in servers]}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def add_server(user_id: str, server: McpServer) -> McpServer:
    """Adiciona ou atualiza (por nome) um servidor MCP do usuário."""
    servers = [s for s in list_servers(user_id) if s.name != server.name]
    servers.append(server)
    _save(user_id, servers)
    _bump_version(user_id)
    return server


def remove_server(user_id: str, name: str) -> bool:
    """Remove um servidor pelo nome. Retorna True se existia."""
    servers = list_servers(user_id)
    remaining = [s for s in servers if s.name != name]
    if len(remaining) == len(servers):
        return False
    _save(user_id, remaining)
    _bump_version(user_id)
    return True


# ---------------------------------------------------------------------------
# Conexão / health-check
# ---------------------------------------------------------------------------


def build_connection(server: McpServer) -> dict:
    """Monta o dict de conexão no formato aceito por
    ``VectoraMCPClient.connect`` (``backend/tools/mcp.py``)."""
    if server.transport == "stdio":
        return {
            "transport": "stdio",
            "command": server.command,
            "args": list(server.args),
        }
    if server.transport == "sse":
        return {"transport": "sse", "url": server.url}
    # "http" → streamable_http moderno
    return {"transport": "streamable_http", "url": server.url}


async def health_check(server: McpServer) -> dict:
    """Tenta conectar ao servidor e listar suas tools.

    Retorna ``{ok, tools, error}``. Nunca lança — falhas viram ``ok=False``.
    Conecta em modo ``strict``: a primeira falha (servidor não sobe, timeout,
    etc.) propaga pro ``except`` em vez de virar silenciosamente "0 tools".
    """
    client = VectoraMCPClient()
    try:
        async with asyncio.timeout(_HEALTH_TIMEOUT_S):
            await client.connect({server.name: build_connection(server)}, strict=True)
        return {"ok": True, "tools": sorted(client.tools()), "error": ""}
    except Exception as exc:
        return {"ok": False, "tools": [], "error": str(exc)}
    finally:
        await client.aclose()


_JSON_SCHEMA_TYPES: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _args_model_from_input_schema(
    tool_name: str, input_schema: dict | None
) -> type[BaseModel]:
    """Constrói um ``BaseModel`` dinâmico a partir do JSON Schema que um
    servidor MCP publica em ``Tool.inputSchema`` — mapeamento raso (tipos
    primitivos + array/object), o suficiente pro schema que o LLM recebe
    pra chamar a tool remota."""
    properties: dict[str, Any] = (input_schema or {}).get("properties", {}) or {}
    required = set((input_schema or {}).get("required", []) or [])
    fields: dict[str, Any] = {}
    for prop_name, prop_schema in properties.items():
        py_type = _JSON_SCHEMA_TYPES.get((prop_schema or {}).get("type", ""), Any)
        if prop_name in required:
            fields[prop_name] = (py_type, ...)
        else:
            fields[prop_name] = (py_type | None, (prop_schema or {}).get("default"))
    return create_model(f"{tool_name}Args", **fields)


def _remote_tool_spec(server_name: str, connection: dict, mcp_tool: Any) -> ToolSpec:
    """Empacota uma ``mcp.types.Tool`` remota como ``ToolSpec`` nativa —
    cada invocação abre uma conexão nova, isolada, só com o servidor dono da
    tool (nenhum estado de sessão é mantido entre chamadas)."""
    tool_name = mcp_tool.name

    async def _handler(**kwargs: Any) -> str:
        client = VectoraMCPClient()
        try:
            async with asyncio.timeout(_HEALTH_TIMEOUT_S):
                await client.connect({server_name: connection}, strict=True)
                return await client.call_tool(tool_name, kwargs)
        except TimeoutError:
            return f"Erro: tool MCP '{tool_name}' excedeu {_HEALTH_TIMEOUT_S}s."
        except Exception as exc:
            logger.exception(
                "plugins: falha ao invocar tool MCP remota", extra={"tool": tool_name}
            )
            return f"Erro ao invocar tool MCP '{tool_name}': {exc}"
        finally:
            await client.aclose()

    _handler.__name__ = tool_name

    return ToolSpec(
        name=tool_name,
        description=mcp_tool.description or "",
        args_model=_args_model_from_input_schema(tool_name, mcp_tool.inputSchema),
        handler=_handler,
        extras=ToolExtras(render_hint="json", category="mcp", icon="share-2"),
        needs_ctx=False,
    )


async def get_user_mcp_tools(user_id: str) -> list:
    """Carrega as tools (``BaseTool``, via ``as_langchain_tool``) dos
    servidores MCP do usuário.

    Cacheado por ``(user_id, version)`` — só reconecta quando o usuário muda
    seus servidores. Sem servidores configurados → lista vazia. Falha de um
    servidor degrada para os que responderam (``VectoraMCPClient.connect``
    é tolerante por padrão); uma exceção ao listar todas ainda vira lista
    vazia + log, nunca propaga.
    """
    version = tools_version(user_id)
    cached = _mcp_tools_cache.get(user_id)
    if cached is not None and cached[0] == version:
        return cached[1]

    servers = list_servers(user_id)
    if not servers:
        _mcp_tools_cache[user_id] = (version, [])
        return []

    connections = {s.name: build_connection(s) for s in servers}
    client = VectoraMCPClient()
    try:
        async with asyncio.timeout(_HEALTH_TIMEOUT_S):
            await client.connect(connections)
        remote_tools = client.tools()
        tools_by_server = client.tools_by_server()
    except Exception:
        logger.warning("plugins: falha ao carregar tools MCP de %s", user_id)
        remote_tools, tools_by_server = {}, {}
    finally:
        await client.aclose()

    tools = [
        as_langchain_tool(
            _remote_tool_spec(
                tools_by_server[name], connections[tools_by_server[name]], t
            )
        )
        for name, t in remote_tools.items()
    ]

    _mcp_tools_cache[user_id] = (version, tools)
    return tools
