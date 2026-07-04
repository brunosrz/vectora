---
title: Geral
weight: 1
---

**Vectora é open source?**
Não. É software comercial de código fechado — você roda na sua infra, mas o código pertence à Vectora Company. Mesmo modelo do Cursor, Linear ou Notion.

**Preciso de conta pra usar o Free?**
Não. O Free roda 100% local, sem cadastro, sem nenhuma dependência de `services.vectora.company`.

**Quais LLMs são suportados?**
Google Gemini, OpenAI, Anthropic, Cohere, e Ollama (totalmente local). O seletor de modelo só mostra os que têm chave configurada.

**Dá pra usar sem internet?**
Parcialmente. Com Ollama local, o LLM roda offline — mas RAG (Cohere/VoyageAI) e busca web (Tavily) ainda dependem de rede, a menos que você configure alternativas locais.

**Qual a diferença entre o Vectora e um coding assistant tipo Copilot?**
Copilot é autocomplete. Vectora é um agente completo com RAG dedicado, terminal, git, chat web multi-usuário e servidor MCP — pensado pra conhecer o seu projeto de verdade, não só sugerir a próxima linha.

**Existe versão mobile?**
Não. Vectora é desktop (Windows/macOS/Linux) + chat web acessível de qualquer navegador (incluindo mobile, via o servidor rodando numa VPS/servidor da empresa).
