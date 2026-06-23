"""Garante que as tools de integração externa estão registradas no ALL_TOOLS.

Regressão: gdrive/gmail/slack/linear/jira/notion existiam como arquivos mas não
eram importadas em `nodes/tools.py`, então o agente nunca as recebia.
"""

from __future__ import annotations

from backend.nodes.tools import ALL_TOOLS

_INTEGRATION_TOOLS = {
    "google_drive_list",
    "google_drive_read",
    "google_drive_search",
    "gmail_list",
    "gmail_read",
    "slack_send",
    "slack_list_channels",
    "slack_read",
    "linear_list_issues",
    "linear_create_issue",
    "linear_update_issue",
    "jira_list_issues",
    "jira_create_issue",
    "jira_transition",
    "notion_search",
    "notion_read_page",
    "notion_create_page",
}


def test_integration_tools_estao_em_all_tools():
    names = {t.name for t in ALL_TOOLS}
    faltando = _INTEGRATION_TOOLS - names
    assert not faltando, f"tools de integração não registradas: {sorted(faltando)}"


def test_all_tools_sem_nomes_duplicados():
    """Erro/borda: registrar muitas tools não pode introduzir nome duplicado
    (o dict de ToolNode silenciaria a colisão, escondendo a perda de uma tool)."""
    names = [t.name for t in ALL_TOOLS]
    duplicados = {n for n in names if names.count(n) > 1}
    assert not duplicados, f"nomes de tool duplicados: {sorted(duplicados)}"
