---
title: Servidor MCP
weight: 5
---

El servidor MCP de Vectora está **siempre activo**: se inicia con cada arranque del backend (`vectora start`/`vectora web`), montado en `/mcp` en el mismo proceso FastAPI (SDK `mcp`, transporte SSE) — no hay un proceso MCP separado ni un puerto dedicado.

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

En producción, usa la URL HTTPS pública de tu servidor: `https://vectora.yourdomain.com/mcp`.

Ver la guía [Conectando clientes MCP](../../guides/mcp-clients) para instrucciones completas.

## Qué se expone

25 herramientas de lectura y escritura: archivos (`file_read`/`file_edit`/`file_write`), búsqueda (`grep`, `list_dir`, `vector_search`, `web_search`, `fetch_url`), RAG (`embedding`, `ingest_docs`, `manage_retriever`), workspace (`workspace_describe`/`workspace_list`/`bucket_summary`), git solo-lectura (`git_status`/`git_diff`/`git_log`), Context Graph (`graph_query`/`graph_explain`/`graph_path`/`graph_affected`), `terminal`, delegación (`delegate_task_to_vectora`) y métricas (`vectora_metrics`).

## Seguridad: aprobación de escritura por workspace

**Un cliente MCP autenticado no pasa por el grafo LangGraph** — `file_write`, `file_edit` y `terminal` llaman a la herramienta interna directo, fuera del `HumanInTheLoopMiddleware`/`permission_mode` que protege el chat. Para cerrar esto sin introducir fricción por llamada (el punto del MCP es operar sin pausar en cada herramienta), estas 3 herramientas exigen una **aprobación persistida por workspace**:

- Sin aprobación: `file_write_tool`/`file_edit_tool`/`terminal_tool` rechazan con un mensaje claro — nada se ejecuta.
- Aprobar una vez: `POST /workspaces/approve-mcp-write` libera las 3 herramientas para ese workspace hasta que se revoque.
- Las herramientas solo-lectura (archivos, git, Context Graph, búsqueda, RAG) **nunca** pasan por esta compuerta — no necesitan aprobación.

Cada llamada a las 3 herramientas con compuerta (aprobada o rechazada) genera un log estructurado (`mcp_write_call`) para auditoría.

## Vectora como cliente MCP

Además de ser servidor, Vectora también consume servidores MCP de terceros — configurados en **Configuración → Entorno → Plugins**, con soporte para transportes `stdio`, `sse` y `http`. Ver [Usando la configuración](../../guides/using-settings).
