"""ToolNodes especializados por categoria de ferramenta.

Todos os agentes recebem ALL_TOOLS — a diferença entre eles é o treinamento
(system prompt) e o contexto, não as ferramentas disponíveis.

As listas parciais (SEARCH_TOOLS, FS_TOOLS, etc.) são mantidas como referência
semântica mas ALL_TOOLS é a lista canônica usada pelos agentes e ToolNodes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langgraph.prebuilt import ToolNode

from vectora.tools.fs import (
    create_artifact,
    file_edit,
    file_read,
    file_write,
    grep,
    list_dir,
    terminal,
)
from vectora.tools.memory import delete_memory, get_memory, save_memory
from vectora.tools.rag import embedding, ingest_docs, vector_search
from vectora.tools.web import fetch_url, web_search

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Grupos semânticos (referência — não são usados diretamente pelos agentes)
# ---------------------------------------------------------------------------

#: Ferramentas de busca e pesquisa
SEARCH_TOOLS: list[BaseTool] = [
    web_search,
    fetch_url,
    vector_search,
    embedding,
    ingest_docs,
]

#: Ferramentas de filesystem, terminal e artifacts
FS_TOOLS: list[BaseTool] = [
    file_read,
    file_edit,
    file_write,
    grep,
    list_dir,
    terminal,
    create_artifact,
]

#: Ferramentas de memória
MEMORY_TOOLS: list[BaseTool] = [save_memory, get_memory, delete_memory]

#: Ferramentas RAG de ingestão
RAG_TOOLS: list[BaseTool] = [vector_search, embedding, ingest_docs]

# ---------------------------------------------------------------------------
# ALL_TOOLS — lista canônica usada por TODOS os agentes
# ---------------------------------------------------------------------------
# Todos os agentes recebem o mesmo conjunto de ferramentas.
# O comportamento diferenciado vem do system prompt e do contexto, não
# da restrição de acesso às ferramentas.

_all: dict[str, BaseTool] = {}
for _t in [
    web_search,
    fetch_url,
    vector_search,
    embedding,
    ingest_docs,
    file_read,
    file_edit,
    file_write,
    grep,
    list_dir,
    terminal,
    create_artifact,
    save_memory,
    get_memory,
    delete_memory,
]:
    _all[_t.name] = _t

ALL_TOOLS: list[BaseTool] = list(_all.values())

# ---------------------------------------------------------------------------
# ToolNodes — todos usam ALL_TOOLS
# ---------------------------------------------------------------------------

search_tool_node = ToolNode(tools=ALL_TOOLS)
coder_tool_node = ToolNode(tools=ALL_TOOLS)
memory_tool_node = ToolNode(tools=MEMORY_TOOLS)
all_tool_node = ToolNode(tools=ALL_TOOLS)

logger.debug(
    "ToolNodes inicializados (ALL_TOOLS para todos os agentes)",
    extra={
        "total": len(ALL_TOOLS),
        "search_group": len(SEARCH_TOOLS),
        "fs_group": len(FS_TOOLS),
        "memory_group": len(MEMORY_TOOLS),
    },
)

__all__ = [
    "ALL_TOOLS",
    "FS_TOOLS",
    "MEMORY_TOOLS",
    "RAG_TOOLS",
    "SEARCH_TOOLS",
    "all_tool_node",
    "coder_tool_node",
    "memory_tool_node",
    "search_tool_node",
]
