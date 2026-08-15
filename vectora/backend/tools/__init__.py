"""Vectora Tools Package.

Agrupa todas as ferramentas do agente em módulos temáticos:

- web      → web_search, fetch_url
- rag      → embedding, vector_search, ingest_docs, manage_retriever
- fs       → file_read, file_edit, file_write, grep, list_dir, terminal
- memory   → save_memory, get_memory, delete_memory
- mcp      → call_mcp_tool
- browser  → browser_navigate, browser_screenshot, browser_click, browser_scroll,
             browser_fill, browser_read_dom, browser_start, browser_stop,
             browser_restart, browser_logs
- native   → time_now, time_parse, hash_text, base64_encode, regex_test,
             json_query, jwt_decode, http_request

Este __init__.py re-exporta tudo para manter compatibilidade retroativa
com qualquer código que importe direto de `tools`.
"""

from __future__ import annotations

import logging

from langchain.tools import BaseTool

from backend.settings import settings
from backend.tools import browser as _browser_module
from backend.tools import fs as _fs_module
from backend.tools import git as _git_module
from backend.tools.github import github_fetch_pr_diff, github_post_pr_comment
from backend.tools.langchain_bridge import as_langchain_tool
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
from backend.tools.registry import TOOL_REGISTRY
from backend.tools.web import fetch_url, web_search

logger = logging.getLogger(__name__)


def _bridge(name: str) -> BaseTool:
    """Envolve uma tool nativa (`@vtool`, ``backend/tools/registry.py``) num
    adapter compatível — mesmo padrão de ``backend/nodes/tools.py``,
    necessário aqui porque este módulo ainda expõe ``TOOLS``/``TOOLS_BY_NAME``
    tipados como ``BaseTool`` para compatibilidade retroativa."""
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        msg = f"tool nativa '{name}' não registrada — módulo não importado?"
        raise RuntimeError(msg)
    return as_langchain_tool(spec)


file_read = _bridge("file_read")
file_edit = _bridge("file_edit")
file_write = _bridge("file_write")
grep = _bridge("grep")
list_dir = _bridge("list_dir")
terminal = _bridge("terminal")
git_stage = _bridge("git_stage")
git_unstage = _bridge("git_unstage")
browser_navigate = _bridge("browser_navigate")
browser_screenshot = _bridge("browser_screenshot")
browser_click = _bridge("browser_click")
browser_scroll = _bridge("browser_scroll")
browser_fill = _bridge("browser_fill")
browser_read_dom = _bridge("browser_read_dom")


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

    # GitHub API (saída de rede — modelo de referência PR review via webhook)
    tools.extend([github_fetch_pr_diff, github_post_pr_comment])

    # Browser: navegação livre + automação sobre a página atual
    tools.extend(
        [
            browser_navigate,
            browser_screenshot,
            browser_click,
            browser_scroll,
            browser_fill,
            browser_read_dom,
        ]
    )

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
    "browser_click",
    "browser_fill",
    "browser_navigate",
    "browser_read_dom",
    "browser_screenshot",
    "browser_scroll",
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
    "github_fetch_pr_diff",
    "github_post_pr_comment",
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
