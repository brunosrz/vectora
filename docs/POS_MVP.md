# Roadmap Pós-MVP

Evolução estratégica do Vectora de um **agente multi-especialista local** para um **orquestrador de Deep Agents** escalável, com infra de produção e auto-correção.

O pré-requisito absoluto para qualquer item desta lista é que o **v0.1.0 esteja estável em produção**. Não construir sobre areia.

---

## ✅ Shipped em v0.1.0 (era v0.2)

Estes itens foram antecipados e implementados no MVP:

- ✅ Supervisor com routing inteligente (`agents/supervisor.py`)
- ✅ Search Agent — RAG + web search + cascading embeddings (`agents/search.py`)
- ✅ Coder Agent — filesystem + terminal (`agents/coder.py`)
- ✅ Direct Agent — síntese + memória (`agents/direct.py`)
- ✅ RAG subgraph com threshold adaptativo (retrieve → rerank/websearch → inject)
- ✅ Cascading automático: web_search → LanceDB fire-and-forget
- ✅ Tools distribuídas por agente (SEARCH_TOOLS / FS_TOOLS / MEMORY_TOOLS)

---

## v0.2 — Infra de Produção

Esta versão torna o Vectora apto para produção real com múltiplos usuários simultâneos e observabilidade de nível enterprise.

### Infra Escalável

- [ ] **PostgreSQL** como alternativa ao SQLite (connection pool, concurrent writes, `AsyncPostgresSaver` do LangGraph)
- [ ] **Qdrant Cloud** como alternativa ao LanceDB (vector store gerenciado, escalável)
- [ ] **Valkey/Redis** como cache distribuído (embeddings, respostas frequentes)
- [ ] Migrações automáticas SQLite → PostgreSQL

### Observabilidade Production-Grade

- [ ] Prometheus metrics — latência, tokens/call, taxa de erro por ferramenta, fila de embedding
- [ ] Jaeger distributed tracing — trace completo de cada delegação A2A
- [ ] LangSmith com `client_thread_id` nos metadados — identifica qual agente Paperclip causou cada trace
- [ ] Alert system — Slack/Discord para erros críticos (DLQ cheio, embedding worker morto)

### Débitos Técnicos Prioritários

- [ ] **`thread_id: str` nativo** — Hoje usa `hash(s) & 0xFFFFFFFF`. Em larga escala, colisões são inevitáveis. Migrar para `str` nativo no LangGraph Checkpointer.
- [ ] **SSE Heartbeat** — Conexões ociosas fechadas silenciosamente por firewalls (30–60s). Adicionar `heartbeat_interval = 25s`.
- [ ] **Streaming de tokens** — `delegate()` hoje bloqueia até o LangGraph finalizar. Migrar para `astream_events`.

---

## v0.3 — Memory & Human-in-the-Loop

Esta versão adiciona **consciência temporal** e **controle humano** antes de ações destrutivas.

### Human-in-the-Loop (HITL)

LangGraph suporta `interrupt_before` — o grafo pausa e aguarda confirmação humana:

- [ ] Antes de `file_edit` / `file_write` em produção
- [ ] Antes de `terminal` com comandos de mutação (git push, rm, deploy)
- [ ] Antes de `ingest_docs` em coleções críticas
- [ ] CLI exibe Rich Panel de confirmação antes de prosseguir

### Long-Term Memory Aprimorada

- [ ] User profile persistente — preferências, estilo de código, projetos ativos
- [ ] Consolidação automática — memórias antigas resumidas para evitar overflow
- [ ] Memórias contextuais — recuperadas automaticamente com base no assunto da conversa
- [ ] TTL inteligente — memórias expiram por uso, não apenas por tempo

### Execução Paralela de Sub-Agentes

- [ ] `asyncio.gather` para tarefas independentes — supervisor despacha search + coder em paralelo quando não há dependência entre eles

---

## v0.4 — Deep Agents e Self-Correction

O ponto alto do roadmap: **agentes que se auto-criticam** e **corrigem respostas fracas** antes de entregar ao usuário.

### Reflection Pattern

```
call_llm → [resposta fraca?] → critique_node → call_llm (nova tentativa)
         → [resposta ok?]   → END
```

Critérios de qualidade: coerência, completude, fundamentação em fontes, tom adequado. O agente recebe a crítica como nova instrução: _"Sua resposta anterior foi incompleta porque X. Tente novamente com foco em Y."_

### Supervisor com LLM Full

- [ ] Hoje o supervisor usa regex + keyword fallback. Migrar para LLM call com structured output para casos ambíguos.
- [ ] Roteamento multi-hop — supervisor pode re-rotear após worker completar (ex: search completa busca → direct sintetiza).

### Streaming de Respostas

- [ ] CLI exibe tokens em tempo real (streaming token-by-token via `astream_events`)
- [ ] MCP SSE envia eventos incrementais para o Paperclip
- [ ] Cancelamento mid-stream suportado

---

## Plugins & Ecossistema (v0.3+)

- [ ] **VSCode Extension** — Usar Vectora inline no editor sem sair do contexto de código
- [ ] **ACP Protocol Server** — Agent Client Protocol para Zed/Neovim
- [ ] **Plugin oficial Paperclip** — `integrations/paperclip/plugin/` com API de alto nível
- [ ] **Vectora Asset Library** — Buckets de embeddings pré-treinados (Next.js docs, FastAPI, etc.)
- [ ] **Gemini CLI Plugin** — Usar Vectora como ferramenta dentro do Gemini CLI

---

## Roadmap Resumido

```
v0.1.0 ── MVP ──────────────────────────────────────────────┐
          Supervisor + 3 Workers + RAG Subgraph              │
          14 tools, cascading embeddings, MCP server         │
                                                             │
v0.2   ── Infra de Produção ─────────────────────────────── │
          PostgreSQL + Qdrant + Observabilidade              │
          Prometheus + Jaeger + streaming tokens             │
                                                             │
v0.3   ── Memory & HITL ────────────────────────────────── │
          Human-in-the-loop + Long-term memory              │
          Execução paralela de sub-agentes                   │
                                                             │
v0.4   ── Deep Agents ─────────────────────────────────── │
          Reflection + Self-correction                       │
          Supervisor com LLM full + multi-hop routing        │
                                                             │
v1.0   ── Plugins & Ecossistema ──────────────────────────┘
          VSCode + ACP + Asset Library + Gemini CLI
```
