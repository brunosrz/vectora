---
title: MCP Server
weight: 5
---

El servidor MCP de Vectora está **siempre activo**: se inicia con `vectora start`, montado en `/mcp` en el mismo proceso FastAPI (vía `FastMCP`, transporte SSE) — no hay un proceso MCP separado ni un puerto dedicado.

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

Las mismas herramientas nativas del agente (archivos, git, terminal, RAG, web) — sujetas a la misma política ABAC/de herramientas que aplica en el chat. Un cliente externo conectándose vía MCP no obtiene más privilegio del que tendría un usuario en el chat web.

## Vectora como cliente MCP

Además de ser servidor, Vectora también consume servidores MCP de terceros — configurados en **Configuración → Entorno → Plugins**, con soporte para transportes `stdio`, `sse` y `http`. Ver [Usando la configuración](../../guides/using-settings).

## Seguridad

Toda llamada a herramienta vía MCP pasa por el mismo mecanismo HITL y ABAC que el chat — no es un canal de bypass.
