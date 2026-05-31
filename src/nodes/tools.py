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

from src.tools.fs import (
    create_artifact,
    file_edit,
    file_read,
    file_write,
    grep,
    list_dir,
    terminal,
)
from src.tools.gh import (
    gh_issue_comment,
    gh_issue_create,
    gh_issue_list,
    gh_issue_view,
    gh_pr_create,
    gh_pr_list,
    gh_pr_merge,
    gh_pr_view,
)
from src.tools.git import (
    git_branch,
    git_checkout,
    git_commit,
    git_diff,
    git_init,
    git_log,
    git_pull,
    git_push,
    git_stash,
    git_status,
    git_worktree,
)
from src.tools.memory import delete_memory, get_memory, save_memory, search_memory
from src.tools.rag import embedding, ingest_docs, manage_retriever, vector_search
from src.tools.web import fetch_url, web_search
from src.tools.workspace import bucket_summary, workspace_describe, workspace_list

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
    manage_retriever,
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

#: Ferramentas de memória (C4: search_memory adicionado)
MEMORY_TOOLS: list[BaseTool] = [save_memory, get_memory, delete_memory, search_memory]

#: Ferramentas de workspace e manifests (B6)
WORKSPACE_TOOLS: list[BaseTool] = [workspace_describe, workspace_list, bucket_summary]

#: Ferramentas RAG de ingestão e gestão
RAG_TOOLS: list[BaseTool] = [vector_search, embedding, ingest_docs, manage_retriever]

#: Ferramentas git e GitHub CLI (G3)
GIT_TOOLS: list[BaseTool] = [
    git_status,
    git_log,
    git_diff,
    git_branch,
    git_checkout,
    git_commit,
    git_push,
    git_pull,
    git_stash,
    git_init,
    git_worktree,
    gh_pr_list,
    gh_pr_create,
    gh_pr_view,
    gh_pr_merge,
    gh_issue_list,
    gh_issue_create,
    gh_issue_view,
    gh_issue_comment,
]

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
    manage_retriever,
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
    search_memory,
    workspace_describe,
    workspace_list,
    bucket_summary,
    # G3 — Git + GitHub CLI
    git_status,
    git_log,
    git_diff,
    git_branch,
    git_checkout,
    git_commit,
    git_push,
    git_pull,
    git_stash,
    git_init,
    git_worktree,
    gh_pr_list,
    gh_pr_create,
    gh_pr_view,
    gh_pr_merge,
    gh_issue_list,
    gh_issue_create,
    gh_issue_view,
    gh_issue_comment,
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
    "GIT_TOOLS",
    "MEMORY_TOOLS",
    "RAG_TOOLS",
    "SEARCH_TOOLS",
    "WORKSPACE_TOOLS",
    "all_tool_node",
    "coder_tool_node",
    "memory_tool_node",
    "search_tool_node",
]
