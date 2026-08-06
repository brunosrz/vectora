---
title: General
weight: 1
---

**Is Vectora open source?**
No. It's commercial, closed-source software — you run it on your infra, but the code belongs to Vectora Company. Same model as Cursor, Linear, or Notion.

**Do I need an account to use Free?**
No. Free runs 100% locally, no signup, no dependency on `services.vectora.company` whatsoever.

**Which LLMs are supported?**
Google Gemini, OpenAI, Anthropic, Cohere, and Ollama (fully local). The model selector only shows the ones with a configured key.

**Can I use it without internet?**
Partially. With local Ollama, the LLM runs offline — but RAG (Cohere/VoyageAI) and web search (Tavily) still depend on the network, unless you configure local alternatives.

**What's the difference between Vectora and a coding assistant like Copilot?**
Copilot is autocomplete. Vectora is a full agent with dedicated RAG, terminal, git, multi-user web chat, and a shared workspace with the agent — built to actually know your project, not just suggest the next line.

**Is there a mobile version?**
No. Vectora is desktop (Windows/macOS/Linux) + a web chat accessible from any browser (including mobile, via the server running on a company VPS/server).
