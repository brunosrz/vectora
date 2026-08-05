---
title: Introdução
weight: 1
---

## O que é o Vectora

Vectora é um **agente de IA self-hosted** para equipes de desenvolvimento. Ele roda inteiramente no seu servidor — sua VPS, sua máquina local, o servidor da sua empresa — e resolve o problema que a maioria dos assistentes de IA ignora: **fazer o agente conhecer de verdade o seu projeto**, não só gerar código genérico.

Isso acontece por dois caminhos que trabalham juntos:

- **RAG híbrido** — indexação de código, documentos e decisões passadas com busca por palavra-chave (BM25) + busca vetorial densa + reranking, para que o agente responda com base no que foi indexado, não no que ele "acha" que é verdade.
- **Context Graph nativo** — um grafo de conhecimento do workspace (funções, classes, conceitos e como se relacionam), construído via parsing AST (tree-sitter) e extração semântica por LLM. Complementa o RAG com contexto estrutural que embeddings sozinhos não capturam.

## Arquitetura em uma imagem

```text
Você (CLI / Chat Web / MCP client)
        │
        ▼
   Orchestrator (create_deep_agent — LangGraph + deepagents)
        │
   ┌────┴────┐
   ▼         ▼
 coder     search      ← subagentes especializados
   │         │
   └────┬────┘
        ▼
  70+ tools nativas (arquivos, git, terminal, RAG, web, integrações)
        │
        ▼
  SQLite + LanceDB (lite, default)  ou  Postgres + Qdrant + Redis (complete)
```

O **orchestrator** é o supervisor: responde direto quando a pergunta é simples, ou delega para um subagente especializado (`coder` para operações de arquivo/git/terminal, `search` para busca web e RAG) via middleware human-in-the-loop (HITL) que pausa antes de ações destrutivas para você aprovar.

## Os quatro jeitos de usar

O mesmo backend atende quatro superfícies diferentes, ao mesmo tempo:

1. **Chat web** — interface React multi-usuário, com workbench (arquivos, git, terminal, RAG, Context Graph) — veja [Usando o chat](../guides/using-the-chat) e [Usando a workbench](../guides/using-the-workbench).
2. **CLI** — `vectora start`, `vectora config`, `vectora storage` — veja a [referência de CLI](../reference/cli).
3. **MCP server** — montado em `/mcp` no mesmo processo, sempre ativo. Conecte Claude Code, Claude Desktop ou qualquer cliente MCP — veja [Servidor MCP](../reference/mcp-server).
4. **API REST interna** — o mesmo conjunto de endpoints que o frontend usa (chat, RAG, gateways, settings), disponível pra automações contra a sua própria instância — veja [Integração Self-Hosted](../api-reference/self-hosted-integration).

## Free vs. Pro

Vectora é **software comercial de código fechado** — você roda na sua infraestrutura, mas o código pertence à Vectora Company (mesmo modelo do Cursor, Linear, Notion).

- **Free** — 100% local, sem conta, sem nenhuma dependência da Vectora Company. Você traz suas próprias chaves de API (LLM, Cohere/Voyage para embeddings, Tavily para busca web). Storage lite (SQLite + LanceDB).
- **Pro** — opcional, cobre trial/billing/licenciamento via `services.vectora.company` (um Worker Cloudflare pequeno, não um "Vectora Cloud" que hospeda sua instância). Desbloqueia chat web multi-usuário, storage complete (Postgres + Qdrant + Redis), webhooks e a API REST com rate limit maior.

Veja [preços atualizados](https://vectora.company/#pricing).

## Próximo passo

→ [Instalação](../installation)
