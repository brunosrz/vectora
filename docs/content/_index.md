---
title: Vectora Docs
layout: hextra-home
---

{{< hextra/hero-badge >}}
<span>Self-hosted AI agent</span>
{{< /hextra/hero-badge >}}

{{< hextra/hero-headline >}}
Vectora
{{< /hextra/hero-headline >}}

{{< hextra/hero-subtitle >}}
Um agente de IA self-hosted com RAG híbrido, Context Graph nativo,
servidor MCP sempre-ativo e chat web multi-usuário — tudo rodando no seu próprio servidor.
{{< /hextra/hero-subtitle >}}

{{< hextra/hero-button text="Começar" link="docs/getting-started/introduction" >}}

<div class="hx-mt-6"></div>

{{< hextra/feature-grid >}}
{{< hextra/feature-card title="RAG híbrido" subtitle="BM25 + busca vetorial densa + reranker (Cohere/VoyageAI) em cada recuperação, sintetizado de volta pelo orchestrator." >}}
{{< hextra/feature-card title="Context Graph nativo" subtitle="Analisa o workspace com tree-sitter (Python/JS/TS/Go/Rust/Java/C/C++) + extração por LLM, gerando um grafo de conhecimento navegável — não só embeddings." >}}
{{< hextra/feature-card title="Arquitetura deep-agent" subtitle="Construído sobre create_deep_agent (LangGraph + deepagents) — um supervisor delegando para os subagentes coder e search, com middleware HITL para ações destrutivas." >}}
{{< hextra/feature-card title="MCP sempre-ativo" subtitle="O servidor MCP é montado em /mcp no mesmo processo FastAPI — sem processo separado, sem porta separada. Conecte Claude Code, Claude Desktop ou qualquer cliente MCP." >}}
{{< hextra/feature-card title="Zero infra por padrão" subtitle="O modo lite roda em SQLite + LanceDB — sem Docker, sem Postgres. O modo complete (Postgres + Qdrant + Redis) existe quando você precisar escalar." >}}
{{< hextra/feature-card title="Multi-LLM, sem lock-in" subtitle="Google Gemini, OpenAI, Anthropic, Cohere, ou Ollama totalmente local. O seletor de modelo só lista providers com chave de API configurada." >}}
{{< /hextra/feature-grid >}}
