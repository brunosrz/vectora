---
title: MCP Client
weight: 5
---

Vectora consume servidores MCP de terceros — no se expone a sí mismo como servidor MCP para otros harnesses. Configura conectores en **Configuración → Entorno → Plugins**, con soporte para transportes `stdio`, `sse` y `http`.

## Instalando un conector

La tab **Library** del workbench lista un marketplace de conectores MCP con curación (`GET /mcp/registry`) — instala/desinstala directamente ahí, o registra un servidor MCP personalizado manualmente en **Configuración → Entorno → Plugins**.

## Cómo lo usa el agente

La herramienta `call_mcp_tool` (`backend/tools/mcp.py`) delega llamadas a cualquier servidor MCP conectado, vía `MultiServerMCPClient` (`langchain_mcp_adapters`) — el agente descubre e invoca las herramientas expuestas por el servidor externo dentro del propio grafo LangGraph, sujeto al mismo `HumanInTheLoopMiddleware`/`permission_mode` que protege cualquier otra herramienta del chat.

Ver [Usando la configuración](../../guides/using-settings) para detalles de configuración por workspace.
