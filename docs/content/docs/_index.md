---
title: Documentação
cascade:
  type: docs
sidebar:
  open: true
---

Vectora é um **agente de IA self-hosted** — roda inteiramente no seu próprio servidor, integra como sub-agente em qualquer orquestrador compatível com MCP (Claude Code, Claude Desktop, extensões VS Code) e vem com um chat web multi-usuário completo.

No seu núcleo, o Vectora fecha o **abismo de conhecimento** entre um LLM e sua base de código, documentação e stack atual: um pipeline de **RAG** híbrido (BM25 + vetores densos + reranker) para recuperação por similaridade, e um **Context Graph** nativo (workspace analisado via tree-sitter + extração por LLM) para contexto estrutural.

## Por onde começar

| Eu quero...                              | Ir para                                        |
| ---------------------------------------- | ---------------------------------------------- |
| Instalar o Vectora                       | [Instalação](./getting-started/installation)   |
| Rodar em 5 minutos                       | [Início rápido](./getting-started/quick-start) |
| Entender o pipeline de RAG               | [RAG & Context Graph](./concepts/rag)          |
| Conectar um cliente MCP (Claude Code...) | [Servidor MCP](./reference/mcp-server)         |
| Ver todos os comandos da CLI             | [Referência de CLI](./reference/cli)           |
| Fazer deploy em um servidor              | [Requisitos](./deployment/requirements)        |
| Entender auth, secrets e BYOK            | [Segurança](./security/authentication)         |
| Usar a API REST                          | [Referência de API](./api-reference/overview)  |

## O que o Vectora é (e não é)

Vectora é **software comercial, código fechado** — não é open source. Você roda na sua própria infraestrutura (seu servidor, sua VPS, seu desktop), mas o código-fonte pertence à Vectora Company. É o mesmo modelo do Cursor, Linear ou Notion: a infra é sua, o código é do fornecedor.

- **Free** roda 100% local, sem conta necessária. Você traz suas próprias chaves de API.
- **Pro** é opcional e cobre trial/billing/licenciamento via `services.vectora.company`, um Worker Cloudflare pequeno — não é um "Vectora Cloud" que hospeda ou executa sua instância por você. Fazer upgrade muda quais recursos ficam disponíveis (stack de storage de alto desempenho, chat web multi-usuário, webhooks, API REST), nunca onde o agente roda.

Veja a [página de preços](https://vectora.company/#pricing) para os planos atuais.
