---
title: Connecting MCP Clients
weight: 5
---

Vectora expone un servidor MCP **siempre activo**, montado en `/mcp` en el mismo proceso FastAPI — no hay un proceso MCP separado ni un puerto dedicado. Cualquier cliente MCP (Claude Code, Claude Desktop, Cursor, Zed, o tu propio agente) puede conectarse y delegar tareas a Vectora.

## Configurar en Claude Desktop / Claude Code

Agrega esto a tu archivo de configuración MCP:

```json
{
  "mcpServers": {
    "Vectora": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

En producción, usa la URL HTTPS pública de tu servidor:

```json
{
  "mcpServers": {
    "Vectora": {
      "url": "https://vectora.yourdomain.com/mcp"
    }
  }
}
```

## Qué se expone

25 herramientas nativas quedan disponibles para el cliente externo: archivos, git solo-lectura, Context Graph, RAG, búsqueda, terminal y delegación — ver la lista completa en [Servidor MCP](../../reference/mcp-server).

**Escritura y terminal exigen aprobación por workspace.** A diferencia del chat (que pasa por el `HumanInTheLoopMiddleware`), un cliente MCP llama a las herramientas directo — sin esa aprobación, `file_write`/`file_edit`/`terminal` rechazan la ejecución. Aprueba una vez en **Configuración → Workspace** (o `POST /workspaces/approve-mcp-write`) antes de pedirle al cliente que escriba archivos o ejecute comandos. Las herramientas solo-lectura funcionan sin necesidad de aprobación.

## Agregar servidores MCP de terceros a Vectora

Vectora también es un **cliente** MCP — puedes conectar servidores MCP externos y el agente empieza a usar sus herramientas. Configura esto en **Configuración → Entorno → Plugins**, con soporte para tres transportes:

| Transporte | Uso                                        |
| ----------- | -------------------------------------------- |
| `stdio`     | comando + args, proceso local                |
| `sse`       | URL de servidor remoto vía Server-Sent Events |
| `http`      | URL de servidor remoto vía HTTP               |

Un panel de **Política de Herramientas** por servidor te permite restringir qué herramientas de ese MCP están habilitadas.

## Ver también

- [Servidor MCP (referencia técnica)](../../reference/mcp-server)
- [Usando la configuración](../using-settings) — la pestaña Plugins en detalle
