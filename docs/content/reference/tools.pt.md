---
title: Referência de Tools
weight: 3
---

O Vectora vem com **160+ tools nativas**, organizadas por categoria. A filosofia é "batteries included": o que é de alta frequência e utilidade ampla vem embutido, em vez de exigir que você instale um MCP server separado pra cada coisa.

| Categoria         | Ferramentas                                                                                                  |
| ----------------- | ------------------------------------------------------------------------------------------------------------ |
| **Arquivos**      | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal`, `create_artifact`                    |
| **Git**           | 14 operações — status, log, diff, branch, checkout, commit, push, pull, stage/unstage, stash, merge, compare |
| **GitHub**        | `gh_issue_create/list/view/comment`, `gh_pr_create/list/view/merge` (via `gh` CLI)                           |
| **Web**           | `web_search`, `web_fetch` + extração/crawl                                                                   |
| **RAG**           | `vector_search`, `embedding`, `ingest_docs`, `manage_retriever`                                              |
| **Context Graph** | `build_knowledge_graph`, `graph_query`, `graph_explain`, `graph_path`, `graph_update`, `graph_affected`      |
| **Memória**       | `save_memory`, `get_memory`, `delete_memory`                                                                 |
| **Workspace**     | `workspace_list`, `workspace_describe`, `bucket_summary`                                                     |
| **Integrações**   | Jira, Slack, Linear, Google Drive, Gmail, Notion (opcionais, via OAuth/API key por workspace)                |
| **Utilitárias**   | `time_*`, `hash_*`, `base64_*`, `regex_test`, `json_query`, `jwt_decode`, `http_request`                     |
| **MCP**           | `call_mcp_tool` — delega pra MCP servers de terceiros configurados pelo usuário                              |

## Habilitando/desabilitando tools

Administradores controlam quais tools ficam disponíveis pra cada usuário em **Configurações → Administração → Ferramentas**. Cada MCP plugin de terceiro tem seu próprio painel de **Tool Policy** (em **Configurações → Ambiente → Plugins**) pra granularidade por servidor.

## Defensividade

Toda tool tem tratamento de erro interno — uma falha de tool nunca derruba a conversa; ela vira uma observação de erro que o próprio agente vê e pode reagir (tentar de novo, avisar você, escolher outro caminho).

## Veja também

- [Orchestrator & Subagentes](../../concepts/sub-agents) — como coder/search usam esse inventário
- [Usando as configurações](../../guides/using-settings) — aba Ferramentas
