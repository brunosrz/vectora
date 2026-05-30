"""Registry de servidores MCP por usuário — Bloco S.

Cada usuário tem sua própria lista de servidores MCP (plugins), persistida em
``~/.vectora/mcp/<user_id>.json``. As tools desses servidores entram no grafo
via o cliente MCP. O isolamento por arquivo garante que um usuário não veja os
plugins de outro.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from pydantic import BaseModel

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except ImportError:
    MultiServerMCPClient = None  # type: ignore[assignment,misc]  # ty: ignore[invalid-assignment]

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
    """Monta o dict de conexão no formato do MultiServerMCPClient."""
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
    """
    if MultiServerMCPClient is None:
        return {
            "ok": False,
            "tools": [],
            "error": "langchain-mcp-adapters não instalado.",
        }
    connections = {server.name: build_connection(server)}
    try:
        client = MultiServerMCPClient(connections)  # ty: ignore[invalid-argument-type]
        async with asyncio.timeout(_HEALTH_TIMEOUT_S):
            tools = await client.get_tools()
        return {"ok": True, "tools": [t.name for t in tools], "error": ""}
    except Exception as exc:
        return {"ok": False, "tools": [], "error": str(exc)}


async def get_user_mcp_tools(user_id: str) -> list:
    """Carrega as tools (BaseTool) dos servidores MCP do usuário.

    Cacheado por ``(user_id, version)`` — só reconecta quando o usuário muda
    seus servidores. Sem servidores ou sem a lib instalada → lista vazia. Falha
    de um servidor degrada para os que responderam (o MultiServerMCPClient é
    tolerante; uma exceção global vira lista vazia + log).
    """
    version = tools_version(user_id)
    cached = _mcp_tools_cache.get(user_id)
    if cached is not None and cached[0] == version:
        return cached[1]

    servers = list_servers(user_id)
    if not servers or MultiServerMCPClient is None:
        _mcp_tools_cache[user_id] = (version, [])
        return []

    connections = {s.name: build_connection(s) for s in servers}
    try:
        client = MultiServerMCPClient(connections)  # ty: ignore[invalid-argument-type]
        async with asyncio.timeout(_HEALTH_TIMEOUT_S):
            tools = await client.get_tools()
    except Exception:
        logger.warning("plugins: falha ao carregar tools MCP de %s", user_id)
        tools = []

    _mcp_tools_cache[user_id] = (version, list(tools))
    return _mcp_tools_cache[user_id][1]
