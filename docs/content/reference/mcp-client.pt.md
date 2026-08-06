---
title: MCP Client
weight: 5
---

O Vectora consome servidores MCP de terceiros — não expõe a si mesmo como servidor MCP para outros harnesses. Configure conectores em **Configurações → Ambiente → Plugins**, com suporte a transporte `stdio`, `sse` e `http`.

## Instalando um conector

A tab **Library** do workbench lista um marketplace de conectores MCP com curadoria (`GET /mcp/registry`) — instale/desinstale direto por ali, ou registre um servidor MCP customizado manualmente em **Configurações → Ambiente → Plugins**.

## Como o agente usa

A tool `call_mcp_tool` (`backend/tools/mcp.py`) delega chamadas para qualquer servidor MCP conectado, via `MultiServerMCPClient` (`langchain_mcp_adapters`) — o agente descobre e invoca as tools expostas pelo servidor externo dentro do próprio grafo LangGraph, sujeito ao mesmo `HumanInTheLoopMiddleware`/`permission_mode` que protege qualquer outra tool do chat.

Veja [Usando as configurações](../../guides/using-settings) pra detalhes de configuração por workspace.
