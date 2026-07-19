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

from backend.tools.background import (
    approve_task_action,
    create_background_task,
    get_task_result,
    get_task_status,
    list_background_tasks,
)
from backend.tools.browser import (
    browser_click,
    browser_fill,
    browser_read_dom,
    browser_screenshot,
    browser_scroll,
)
from backend.tools.context_graph import (
    build_knowledge_graph,
    graph_affected,
    graph_explain,
    graph_path,
    graph_query,
    graph_update,
)
from backend.tools.fs import (
    create_artifact,
    file_edit,
    file_read,
    file_write,
    grep,
    list_dir,
    terminal,
)
from backend.tools.gdrive import (
    google_drive_list,
    google_drive_read,
    google_drive_search,
)
from backend.tools.gh import (
    gh_issue_comment,
    gh_issue_create,
    gh_issue_list,
    gh_issue_view,
    gh_pr_create,
    gh_pr_list,
    gh_pr_merge,
    gh_pr_view,
)
from backend.tools.git import (
    git_branch,
    git_checkout,
    git_commit,
    git_diff,
    git_init,
    git_log,
    git_pull,
    git_push,
    git_stage,
    git_stash,
    git_status,
    git_unstage,
    git_worktree,
)
from backend.tools.gmail import gmail_list, gmail_read
from backend.tools.jira import jira_create_issue, jira_list_issues, jira_transition
from backend.tools.linear import (
    linear_create_issue,
    linear_list_issues,
    linear_update_issue,
)
from backend.tools.memory import delete_memory, get_memory, save_memory, search_memory
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
from backend.tools.notion import notion_create_page, notion_read_page, notion_search
from backend.tools.rag import embedding, ingest_docs, manage_retriever, vector_search
from backend.tools.slack import slack_list_channels, slack_read, slack_send
from backend.tools.thinking import sequential_thinking
from backend.tools.web import fetch_url, web_search
from backend.tools.workspace import (
    bucket_summary,
    get_workbench_context,
    workspace_describe,
    workspace_list,
)

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

#: Ferramentas de browser automation sobre o preview do workspace (A2)
BROWSER_TOOLS: list[BaseTool] = [
    browser_screenshot,
    browser_click,
    browser_scroll,
    browser_fill,
    browser_read_dom,
]

#: Ferramentas de memória (C4: search_memory adicionado)
MEMORY_TOOLS: list[BaseTool] = [save_memory, get_memory, delete_memory, search_memory]

#: Ferramentas de workspace e manifests (B6)
WORKSPACE_TOOLS: list[BaseTool] = [
    workspace_describe,
    workspace_list,
    bucket_summary,
    get_workbench_context,
    create_background_task,
    list_background_tasks,
    get_task_status,
    get_task_result,
    approve_task_action,
]

#: Ferramentas do Context Graph (grafo de conhecimento do workspace)
GRAPH_TOOLS: list[BaseTool] = [
    build_knowledge_graph,
    graph_query,
    graph_explain,
    graph_path,
    graph_affected,
    graph_update,
]

#: Ferramentas RAG de ingestão e gestão
RAG_TOOLS: list[BaseTool] = [vector_search, embedding, ingest_docs, manage_retriever]

#: Utilitários nativos (sem API externa, exceto http_request)
NATIVE_TOOLS: list[BaseTool] = [
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
    git_stage,
    git_unstage,
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
    browser_screenshot,
    browser_click,
    browser_scroll,
    browser_fill,
    browser_read_dom,
    save_memory,
    get_memory,
    delete_memory,
    search_memory,
    workspace_describe,
    workspace_list,
    bucket_summary,
    get_workbench_context,
    create_background_task,
    list_background_tasks,
    get_task_status,
    get_task_result,
    approve_task_action,
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
    git_stage,
    git_unstage,
    gh_pr_list,
    gh_pr_create,
    gh_pr_view,
    gh_pr_merge,
    gh_issue_list,
    gh_issue_create,
    gh_issue_view,
    gh_issue_comment,
    # Integrações externas (configuradas via OAuth/API key; cada tool degrada
    # para erro tipado quando o provider não está conectado).
    google_drive_list,
    google_drive_read,
    google_drive_search,
    gmail_list,
    gmail_read,
    slack_send,
    slack_list_channels,
    slack_read,
    linear_list_issues,
    linear_create_issue,
    linear_update_issue,
    jira_list_issues,
    jira_create_issue,
    jira_transition,
    notion_search,
    notion_read_page,
    notion_create_page,
    build_knowledge_graph,
    graph_query,
    graph_explain,
    graph_path,
    graph_affected,
    graph_update,
    sequential_thinking,
    # Utilitários nativos
    time_now,
    time_parse,
    hash_text,
    base64_encode,
    base64_decode,
    regex_test,
    json_query,
    jwt_decode,
    http_request,
]:
    _all[_t.name] = _t

ALL_TOOLS: list[BaseTool] = list(_all.values())

# ---------------------------------------------------------------------------
# CHAT_TOOLS — modo Chat (conversacional puro, sem workspace/folders)
# ---------------------------------------------------------------------------
# Sem filesystem/git/terminal/workspace: só conversa, web, RAG (retrieval),
# memória e integrações externas. Usado quando chat_mode=True no agent_factory.

CHAT_TOOLS: list[BaseTool] = [
    web_search,
    fetch_url,
    vector_search,
    save_memory,
    get_memory,
    delete_memory,
    search_memory,
    google_drive_list,
    google_drive_read,
    google_drive_search,
    gmail_list,
    gmail_read,
    slack_send,
    slack_list_channels,
    slack_read,
    linear_list_issues,
    linear_create_issue,
    linear_update_issue,
    jira_list_issues,
    jira_create_issue,
    jira_transition,
    notion_search,
    notion_read_page,
    notion_create_page,
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
    "BROWSER_TOOLS",
    "CHAT_TOOLS",
    "FS_TOOLS",
    "GIT_TOOLS",
    "GRAPH_TOOLS",
    "MEMORY_TOOLS",
    "RAG_TOOLS",
    "SEARCH_TOOLS",
    "WORKSPACE_TOOLS",
    "all_tool_node",
    "coder_tool_node",
    "memory_tool_node",
    "search_tool_node",
]
