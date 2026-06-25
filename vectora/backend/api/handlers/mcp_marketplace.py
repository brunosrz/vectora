"""MCP Marketplace — FASE 5.3.

Endpoints REST para descoberta e gerenciamento de MCP servers de terceiros.
O registry embutido lista conectores curados; instalação grava em
~/.vectora/mcp.json que o servidor MCP lê no próximo boot.

Routes (montadas em server.py):
    GET  /mcp/registry  — lista conectores disponíveis
    POST /mcp/install   — adiciona conector ao mcp.json
    POST /mcp/uninstall — remove conector do mcp.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp-marketplace"])


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------


class MCPConnector(BaseModel):
    id: str
    name: str
    description: str
    install_cmd: str = ""
    env_vars: list[str] = []
    homepage: str = ""
    category: str = "general"


class InstallRequest(BaseModel):
    mcp_id: str
    workspace_id: str | None = None


class UninstallRequest(BaseModel):
    mcp_id: str
    workspace_id: str | None = None


# ---------------------------------------------------------------------------
# Registry embutido — subconjunto curado de MCPs populares
# ---------------------------------------------------------------------------

_REGISTRY: list[MCPConnector] = [
    MCPConnector(
        id="brave-search",
        name="Brave Search",
        description="Pesquisa web via Brave Search API com resultados sem rastreamento.",
        install_cmd="npx -y @modelcontextprotocol/server-brave-search",
        env_vars=["BRAVE_API_KEY"],
        homepage="https://github.com/modelcontextprotocol/servers",
        category="web",
    ),
    MCPConnector(
        id="filesystem",
        name="Filesystem",
        description="Acesso seguro ao filesystem local com controle de diretórios permitidos.",
        install_cmd="npx -y @modelcontextprotocol/server-filesystem",
        env_vars=[],
        homepage="https://github.com/modelcontextprotocol/servers",
        category="filesystem",
    ),
    MCPConnector(
        id="github",
        name="GitHub",
        description="Integração com GitHub: PRs, issues, código, actions e mais.",
        install_cmd="npx -y @modelcontextprotocol/server-github",
        env_vars=["GITHUB_PERSONAL_ACCESS_TOKEN"],
        homepage="https://github.com/modelcontextprotocol/servers",
        category="devtools",
    ),
    MCPConnector(
        id="postgres",
        name="PostgreSQL",
        description="Consultas read-only em banco PostgreSQL.",
        install_cmd="npx -y @modelcontextprotocol/server-postgres",
        env_vars=["POSTGRES_CONNECTION_STRING"],
        homepage="https://github.com/modelcontextprotocol/servers",
        category="database",
    ),
    MCPConnector(
        id="slack",
        name="Slack",
        description="Leitura e envio de mensagens no Slack via Bot Token.",
        install_cmd="npx -y @modelcontextprotocol/server-slack",
        env_vars=["SLACK_BOT_TOKEN", "SLACK_TEAM_ID"],
        homepage="https://github.com/modelcontextprotocol/servers",
        category="communication",
    ),
    MCPConnector(
        id="sequential-thinking",
        name="Sequential Thinking",
        description="Raciocínio passo-a-passo estruturado antes de agir.",
        install_cmd="npx -y @modelcontextprotocol/server-sequential-thinking",
        env_vars=[],
        homepage="https://github.com/modelcontextprotocol/servers",
        category="reasoning",
    ),
]


# ---------------------------------------------------------------------------
# Config path (substituível em testes)
# ---------------------------------------------------------------------------


def _config_path() -> Path:
    return Path.home() / ".vectora" / "mcp.json"


# ---------------------------------------------------------------------------
# Lógica de install/uninstall
# ---------------------------------------------------------------------------


def _load_installed() -> dict:
    path = _config_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"mcpServers": {}}


def _save_installed(config: dict) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Handlers (também usados como funções nos testes)
# ---------------------------------------------------------------------------


def list_registry() -> list[MCPConnector]:
    return list(_REGISTRY)


async def install_mcp(req: InstallRequest) -> dict:
    connector = next((c for c in _REGISTRY if c.id == req.mcp_id), None)
    if connector is None:
        return {
            "status": "error",
            "error": f"conector '{req.mcp_id}' não encontrado no registry",
        }

    try:
        config = _load_installed()
        config["mcpServers"][connector.id] = {
            "command": connector.install_cmd.split()[0]
            if connector.install_cmd
            else "npx",
            "args": connector.install_cmd.split()[1:] if connector.install_cmd else [],
            "env": {k: f"${{{k}}}" for k in connector.env_vars},
        }
        _save_installed(config)
        logger.info("mcp_marketplace: instalado %s", connector.id)
        return {"status": "installed", "mcp_id": connector.id}
    except Exception as exc:
        logger.exception("mcp_marketplace: falha ao instalar %s", req.mcp_id)
        return {"status": "error", "error": str(exc)}


async def uninstall_mcp(req: UninstallRequest) -> dict:
    try:
        config = _load_installed()
        if req.mcp_id in config.get("mcpServers", {}):
            del config["mcpServers"][req.mcp_id]
            _save_installed(config)
            logger.info("mcp_marketplace: desinstalado %s", req.mcp_id)
            return {"status": "removed", "mcp_id": req.mcp_id}
        return {"status": "not_found", "mcp_id": req.mcp_id}
    except Exception as exc:
        logger.exception("mcp_marketplace: falha ao desinstalar %s", req.mcp_id)
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# FastAPI routes
# ---------------------------------------------------------------------------


@router.get("/registry", response_model=list[MCPConnector])
async def get_registry() -> list[MCPConnector]:
    return list_registry()


@router.post("/install")
async def post_install(req: InstallRequest) -> dict:
    return await install_mcp(req)


@router.post("/uninstall")
async def post_uninstall(req: UninstallRequest) -> dict:
    return await uninstall_mcp(req)
