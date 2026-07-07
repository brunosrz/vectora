---
title: Servidor MCP
weight: 5
---

O servidor MCP do Vectora é **sempre-ativo**: sobe junto com `vectora start`, montado em `/mcp` no mesmo processo FastAPI (via `FastMCP`, transporte SSE) — não existe um processo MCP separado nem uma porta dedicada.

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

As mesmas tools nativas do agente (arquivos, git, terminal, RAG, web) — sujeitas às mesmas políticas de ABAC/tool policy que valem no chat. Um cliente externo conectando via MCP não ganha nenhum privilégio a mais do que um usuário teria no chat web.

## Vectora como cliente MCP

Além de servidor, o Vectora consome MCP servers de terceiros — configurados em **Configurações → Ambiente → Plugins**, com suporte a transporte `stdio`, `sse` e `http`. Veja [Usando as configurações](../../guides/using-settings).

## Segurança

Toda tool call via MCP passa pelo mesmo mecanismo de HITL e ABAC do chat — não é um canal de bypass.
