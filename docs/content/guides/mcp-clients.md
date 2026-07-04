---
title: Conectando Clientes MCP
weight: 5
---

O Vectora expõe um servidor MCP **sempre-ativo**, montado em `/mcp` no mesmo processo FastAPI — não existe um processo MCP separado nem uma porta dedicada. Qualquer cliente MCP (Claude Code, Claude Desktop, Cursor, Zed, ou seu próprio agente) pode se conectar e delegar tarefas pro Vectora.

## Configurar no Claude Desktop / Claude Code

Adicione ao seu arquivo de configuração MCP:

```json
{
  "mcpServers": {
    "Vectora": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

Em produção, use a URL HTTPS pública do seu servidor:

```json
{
  "mcpServers": {
    "Vectora": {
      "url": "https://vectora.seudominio.com/mcp"
    }
  }
}
```

## O que fica exposto

As mesmas tools nativas do agente (arquivos, git, terminal, RAG, web) ficam disponíveis pro cliente externo, sujeitas às mesmas políticas de ABAC e ao mesmo mecanismo de HITL que se aplicam no chat.

## Adicionando MCP servers de terceiros ao Vectora

O Vectora também é **cliente** MCP — você pode conectar servidores MCP externos e o agente passa a usar as tools deles. Configure em **Configurações → Ambiente → Plugins**, com suporte a três transportes:

| Transporte | Uso                                              |
| ---------- | ------------------------------------------------ |
| `stdio`    | comando + args, processo local                   |
| `sse`      | URL de um servidor remoto via Server-Sent Events |
| `http`     | URL de um servidor remoto via HTTP               |

Um painel de **Tool Policy** por servidor deixa você restringir quais tools daquele MCP ficam habilitadas.

## Veja também

- [Servidor MCP (referência técnica)](../../reference/mcp-server)
- [Usando as configurações](../using-settings) — aba Plugins em detalhe
