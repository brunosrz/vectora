"""Vectora Tools Package.

Agrupa todas as ferramentas do agente em módulos temáticos:

- web      → web_search, fetch_url
- rag      → embedding, vector_search, ingest_docs
- fs       → file_read, file_edit, file_write, grep, list_dir, terminal
- memory   → save_memory, get_memory, delete_memory
- mcp      → call_mcp_tool

Este __init__.py re-exporta tudo para manter compatibilidade retroativa
com qualquer código que importe direto de `tools`.
"""

import logging

from langchain.tools import BaseTool

from vectora.config.settings import settings
from vectora.tools.fs import file_edit, file_read, file_write, grep, list_dir, terminal
from vectora.tools.mcp import call_mcp_tool
from vectora.tools.memory import delete_memory, get_memory, save_memory
from vectora.tools.rag import embedding, ingest_docs, vector_search
from vectora.tools.web import fetch_url, web_search

logger = logging.getLogger(__name__)


def _build_tools_list() -> list[BaseTool]:
    """Constrói lista de ferramentas ativas com base na configuração."""
    tools: list[BaseTool] = []

    # Web (sempre disponível)
    tools.extend([web_search, fetch_url])

    # RAG
    tools.extend([vector_search])
    if settings.enable_rag:
        tools.extend([embedding, ingest_docs])

    # Memória persistente
    tools.extend([save_memory, get_memory, delete_memory])

    # Filesystem + Terminal
    if settings.enable_file_operations:
        tools.extend([file_read, file_edit, file_write, grep, list_dir, terminal])

    # MCP
    if settings.enable_mcp:
        tools.append(call_mcp_tool)

    logger.info("Tools initialized", extra={"count": len(tools)})
    return tools


def get_tools() -> list[BaseTool]:
    """Retorna lista de ferramentas ativas."""
    return _build_tools_list()


# Singletons usados pelo grafo e pelos nós
TOOLS: list[BaseTool] = _build_tools_list()
TOOLS_BY_NAME: dict[str, BaseTool] = {t.name: t for t in TOOLS}

__all__ = [
    "TOOLS",
    "TOOLS_BY_NAME",
    "call_mcp_tool",
    "delete_memory",
    "embedding",
    "fetch_url",
    "file_edit",
    "file_read",
    "file_write",
    "get_memory",
    "get_tools",
    "grep",
    "ingest_docs",
    "list_dir",
    "save_memory",
    "terminal",
    "vector_search",
    "web_search",
]
