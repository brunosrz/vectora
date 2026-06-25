"""Vectora Tools Package.

Agrupa todas as ferramentas do agente em módulos temáticos:

- web      → web_search, fetch_url
- rag      → embedding, vector_search, ingest_docs, manage_retriever
- fs       → file_read, file_edit, file_write, grep, list_dir, terminal
- memory   → save_memory, get_memory, delete_memory
- mcp      → call_mcp_tool
- native   → time_now, time_parse, hash_text, base64_encode, regex_test,
             json_query, jwt_decode, http_request

Este __init__.py re-exporta tudo para manter compatibilidade retroativa
com qualquer código que importe direto de `tools`.
"""

import logging

from langchain.tools import BaseTool

from backend.settings import settings
from backend.tools.fs import file_edit, file_read, file_write, grep, list_dir, terminal
from backend.tools.git import git_stage, git_unstage
from backend.tools.mcp import call_mcp_tool
from backend.tools.memory import delete_memory, get_memory, save_memory
from backend.tools.native import (
    base64_decode,
    base64_encode,
    hash_text,
    http_request,
    json_query,
    jwt_decode,
    regex_test,
    time_now,
    time_parse,
)
from backend.tools.rag import (
    embedding,
    ingest_docs,
    manage_retriever,
    vector_search,
)
from backend.tools.web import fetch_url, web_search

logger = logging.getLogger(__name__)


def _build_tools_list() -> list[BaseTool]:
    """Constrói lista de ferramentas ativas com base na configuração."""
    tools: list[BaseTool] = []

    # Web (sempre disponível)
    tools.extend([web_search, fetch_url])

    # RAG
    tools.extend([vector_search, embedding, ingest_docs, manage_retriever])

    # Memória persistente
    tools.extend([save_memory, get_memory, delete_memory])

    # Filesystem + Terminal
    tools.extend([file_read, file_edit, file_write, grep, list_dir, terminal])

    # Git stage/unstage (operações de index)
    tools.extend([git_stage, git_unstage])

    # Native utilities
    tools.extend(
        [
            time_now,
            time_parse,
            hash_text,
            base64_encode,
            base64_decode,
            regex_test,
            json_query,
            jwt_decode,
            http_request,
        ]
    )

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
    "base64_decode",
    "base64_encode",
    "call_mcp_tool",
    "delete_memory",
    "embedding",
    "fetch_url",
    "file_edit",
    "file_read",
    "file_write",
    "get_memory",
    "get_tools",
    "git_stage",
    "git_unstage",
    "grep",
    "hash_text",
    "http_request",
    "ingest_docs",
    "json_query",
    "jwt_decode",
    "list_dir",
    "manage_retriever",
    "regex_test",
    "save_memory",
    "terminal",
    "time_now",
    "time_parse",
    "vector_search",
    "web_search",
]
