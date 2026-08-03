---
title: Servidor MCP
weight: 5
---

O servidor MCP do Vectora é **sempre-ativo**: sobe junto com todo boot do backend (`vectora start`/`vectora web`), montado em `/mcp` no mesmo processo FastAPI (SDK `mcp`, transporte SSE) — não existe um processo MCP separado nem uma porta dedicada.

## Conectando

```json
{
  "mcpServers": {
    "Vectora": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

Em produção, use a URL HTTPS pública do seu servidor: `https://vectora.seudominio.com/mcp`.

Veja o guia [Conectando Clientes MCP](../../guides/mcp-clients) pra instruções completas.

## O que fica exposto

25 tools de leitura e escrita: arquivo (`file_read`/`file_edit`/`file_write`), busca (`grep`, `list_dir`, `vector_search`, `web_search`, `fetch_url`), RAG (`embedding`, `ingest_docs`, `manage_retriever`), workspace (`workspace_describe`/`workspace_list`/`bucket_summary`), git só-leitura (`git_status`/`git_diff`/`git_log`), Context Graph (`graph_query`/`graph_explain`/`graph_path`/`graph_affected`), `terminal`, delegação (`delegate_task_to_vectora`) e métricas (`vectora_metrics`).

## Segurança: aprovação de escrita por workspace

**Um client MCP autenticado não passa pelo grafo LangGraph** — `file_write`, `file_edit` e `terminal` chamam a tool interna direto, fora do `HumanInTheLoopMiddleware`/`permission_mode` que protege o chat. Para fechar isso sem introduzir fricção por chamada (o ponto do MCP é operar sem pausar a cada tool), essas 3 tools exigem uma **aprovação persistida por workspace**:

- Sem aprovação: `file_write_tool`/`file_edit_tool`/`terminal_tool` recusam com mensagem clara — nada é executado.
- Aprovar uma vez: `POST /workspaces/approve-mcp-write` (ou o toggle em **Configurações → Workspace**) libera as 3 tools pra aquele workspace até ser revogado.
- Tools só-leitura (arquivo, git, Context Graph, busca, RAG) **nunca** passam por esse gate — não precisam de aprovação.

Toda chamada às 3 tools gated (aprovada ou recusada) gera um log estruturado (`mcp_write_call`) para auditoria.

## Vectora como cliente MCP

Além de servidor, o Vectora consome MCP servers de terceiros — configurados em **Configurações → Ambiente → Plugins**, com suporte a transporte `stdio`, `sse` e `http`. Veja [Usando as configurações](../../guides/using-settings).
