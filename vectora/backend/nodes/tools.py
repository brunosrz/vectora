"""Catálogo de tools do agente, agrupadas por categoria.

Todos os agentes recebem ALL_TOOLS — a diferença entre eles é o treinamento
(system prompt) e o contexto, não as ferramentas disponíveis.

As listas parciais (SEARCH_TOOLS, FS_TOOLS, etc.) são mantidas como referência
semântica pra montar `SOUL_CATALOG` (backend/agents/souls.py) mas ALL_TOOLS é
a lista canônica consumida pelo agente principal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.tools.background import (
    approve_task_action,
    create_background_task,
    delete_background_task,
    get_task_result,
    get_task_status,
    list_background_tasks,
    run_background_task_now,
    schedule_subagent_task,
    schedule_task,
    toggle_background_task,
)
from backend.tools.browser import (
    browser_click,
    browser_drag,
    browser_fill,
    browser_fill_form,
    browser_logs,
    browser_navigate,
    browser_read_dom,
    browser_restart,
    browser_screenshot,
    browser_scroll,
    browser_start,
    browser_stop,
    browser_upload_file,
    browser_wait_for,
)
from backend.tools.browser_devtools import (
    browser_analyze_trace,
    browser_clear_console,
    browser_close_tab,
    browser_compare_heap_snapshots,
    browser_emulate,
    browser_evaluate,
    browser_get_network_request,
    browser_lighthouse_audit,
    browser_list_console_messages,
    browser_list_network_requests,
    browser_list_tabs,
    browser_new_tab,
    browser_screencast_start,
    browser_screencast_stop,
    browser_select_tab,
    browser_set_dialog_policy,
    browser_snapshot,
    browser_start_trace,
    browser_stop_trace,
    browser_take_heap_snapshot,
)
from backend.tools.computer_use import computer_use
from backend.tools.context_graph import (
    build_knowledge_graph,
    graph_affected,
    graph_cancel_build,
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
    git_check_hooks,
    git_checkout,
    git_cherry_pick,
    git_commit,
    git_compare,
    git_diff,
    git_discard,
    git_fetch,
    git_init,
    git_log,
    git_merge,
    git_pull,
    git_push,
    git_reorder,
    git_resolve_conflict,
    git_revert,
    git_squash,
    git_stage,
    git_stash,
    git_status,
    git_unstage,
    git_worktree,
)
from backend.tools.gmail import gmail_list, gmail_read
from backend.tools.homeassistant import (
    ha_call_service,
    ha_get_state,
    ha_list_entities,
    ha_list_services,
)
from backend.tools.jira import jira_create_issue, jira_list_issues, jira_transition
from backend.tools.kanban import kanban_create, kanban_list, kanban_update_status
from backend.tools.learning import (
    install_learned_skill,
    learn_from_session,
    save_learned_fact,
)
from backend.tools.library import (
    delete_skill,
    install_mcp_from_registry,
    install_memory_bucket,
    install_skill_from_catalog,
    list_mcp_catalog,
    list_memory_bucket_catalog,
    list_skills_catalog,
    publish_memory_bucket_tool,
    publish_skill_tool,
    save_mcp_env_var,
    uninstall_mcp,
    verify_skill,
)
from backend.tools.linear import (
    linear_create_issue,
    linear_list_issues,
    linear_update_issue,
)
from backend.tools.mcp import call_mcp_tool
from backend.tools.media import (
    analyze_video,
    generate_image,
    generate_video,
    text_to_speech,
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
from backend.tools.terminal_sessions import close_terminal, list_terminals
from backend.tools.thinking import sequential_thinking
from backend.tools.web import fetch_url, web_crawl, web_map, web_search
from backend.tools.workspace import (
    bucket_summary,
    get_workbench_context,
    workspace_describe,
    workspace_list,
)

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

# ---------------------------------------------------------------------------
# Grupos semânticos (referência — não são usados diretamente pelos agentes)
# ---------------------------------------------------------------------------

#: Ferramentas de busca e pesquisa
SEARCH_TOOLS: list[BaseTool] = [
    web_search,
    fetch_url,
    web_crawl,
    web_map,
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
    list_terminals,
    close_terminal,
]

#: Ferramentas de browser: navegação livre + automação + dev server
BROWSER_TOOLS: list[BaseTool] = [
    browser_navigate,
    browser_screenshot,
    browser_click,
    browser_scroll,
    browser_fill,
    browser_read_dom,
    browser_wait_for,
    browser_drag,
    browser_upload_file,
    browser_fill_form,
    browser_start,
    browser_stop,
    browser_restart,
    browser_logs,
    browser_list_tabs,
    browser_new_tab,
    browser_close_tab,
    browser_select_tab,
    browser_list_console_messages,
    browser_clear_console,
    browser_list_network_requests,
    browser_get_network_request,
    browser_evaluate,
    browser_snapshot,
    browser_set_dialog_policy,
    browser_emulate,
    browser_start_trace,
    browser_stop_trace,
    browser_analyze_trace,
    browser_take_heap_snapshot,
    browser_compare_heap_snapshots,
    browser_screencast_start,
    browser_screencast_stop,
    browser_lighthouse_audit,
]

#: Ferramentas de memória (C4: search_memory adicionado; Remember: learning loop)
MEMORY_TOOLS: list[BaseTool] = [
    save_memory,
    get_memory,
    delete_memory,
    search_memory,
    learn_from_session,
    install_learned_skill,
    save_learned_fact,
]

#: Ferramentas da Library: auto-instalar MCP/Skills/Memory Library, invocar
#: MCP externo já conectado
LIBRARY_TOOLS: list[BaseTool] = [
    call_mcp_tool,
    list_mcp_catalog,
    list_skills_catalog,
    list_memory_bucket_catalog,
    install_mcp_from_registry,
    install_skill_from_catalog,
    install_memory_bucket,
    uninstall_mcp,
    delete_skill,
    verify_skill,
    publish_memory_bucket_tool,
    publish_skill_tool,
    save_mcp_env_var,
]

#: Ferramentas de workspace e manifests (B6)
WORKSPACE_TOOLS: list[BaseTool] = [
    workspace_describe,
    workspace_list,
    bucket_summary,
    get_workbench_context,
    create_background_task,
    schedule_task,
    schedule_subagent_task,
    list_background_tasks,
    get_task_status,
    get_task_result,
    approve_task_action,
    toggle_background_task,
    delete_background_task,
    run_background_task_now,
    kanban_list,
    kanban_create,
    kanban_update_status,
]

#: Ferramentas do Context Graph (grafo de conhecimento do workspace)
GRAPH_TOOLS: list[BaseTool] = [
    build_knowledge_graph,
    graph_query,
    graph_explain,
    graph_path,
    graph_affected,
    graph_update,
    graph_cancel_build,
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
    git_discard,
    git_squash,
    git_reorder,
    git_cherry_pick,
    git_fetch,
    git_merge,
    git_revert,
    git_compare,
    git_resolve_conflict,
    git_check_hooks,
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
    web_crawl,
    web_map,
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
    list_terminals,
    close_terminal,
    browser_navigate,
    browser_screenshot,
    browser_click,
    browser_scroll,
    browser_fill,
    browser_read_dom,
    browser_wait_for,
    browser_drag,
    browser_upload_file,
    browser_fill_form,
    browser_start,
    browser_stop,
    browser_restart,
    browser_logs,
    browser_list_tabs,
    browser_new_tab,
    browser_close_tab,
    browser_select_tab,
    browser_list_console_messages,
    browser_clear_console,
    browser_list_network_requests,
    browser_get_network_request,
    browser_evaluate,
    browser_snapshot,
    browser_set_dialog_policy,
    browser_emulate,
    browser_start_trace,
    browser_stop_trace,
    browser_analyze_trace,
    browser_take_heap_snapshot,
    browser_compare_heap_snapshots,
    browser_screencast_start,
    browser_screencast_stop,
    browser_lighthouse_audit,
    save_memory,
    get_memory,
    delete_memory,
    search_memory,
    learn_from_session,
    install_learned_skill,
    save_learned_fact,
    call_mcp_tool,
    list_mcp_catalog,
    list_skills_catalog,
    list_memory_bucket_catalog,
    install_mcp_from_registry,
    install_skill_from_catalog,
    install_memory_bucket,
    uninstall_mcp,
    delete_skill,
    verify_skill,
    publish_memory_bucket_tool,
    publish_skill_tool,
    save_mcp_env_var,
    workspace_describe,
    workspace_list,
    bucket_summary,
    get_workbench_context,
    create_background_task,
    schedule_task,
    schedule_subagent_task,
    list_background_tasks,
    get_task_status,
    get_task_result,
    approve_task_action,
    toggle_background_task,
    delete_background_task,
    run_background_task_now,
    kanban_list,
    kanban_create,
    kanban_update_status,
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
    git_discard,
    git_squash,
    git_reorder,
    git_cherry_pick,
    git_fetch,
    git_merge,
    git_revert,
    git_compare,
    git_resolve_conflict,
    git_check_hooks,
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
    graph_cancel_build,
    sequential_thinking,
    # Mídia (imagem/voz pelo provider ativo)
    generate_image,
    text_to_speech,
    generate_video,
    analyze_video,
    # Casa conectada (Home Assistant)
    ha_list_entities,
    ha_get_state,
    ha_list_services,
    ha_call_service,
    # Controle de tela do desktop (opt-in, sempre HITL)
    computer_use,
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
    web_crawl,
    web_map,
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
]
