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

Las mismas herramientas nativas del agente (archivos, git, terminal, RAG, web) quedan disponibles para el cliente externo, sujetas a las mismas políticas ABAC y al mismo mecanismo HITL que aplican en el chat.

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
