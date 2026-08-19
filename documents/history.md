# Arquitetura e decisões do produto

Este documento descreve o que o Vectora **é hoje**: a arquitetura atual, as
decisões que a produziram e por que alternativas anteriores foram
descartadas. Não é um changelog nem um relato cronológico — é referência de
produto.

## Identidade

O Vectora é um produto **local-first** de engenharia de contexto: motor de
conversa nativo + tools de fs/git/web/RAG + skills por harness + memória
persistente, rodando embarcado no desktop do usuário. Não é um clone de
Claude Code/Gemini CLI/Codex, não depende de cloud obrigatória, não expõe um
"agente principal" competindo por espaço de CLI de código.

## Motor de conversa

Loop nativo (`backend/engine/conversation_loop.py::run_conversation`) — um
`while` imperativo que relê o histórico via `SessionStore` a cada volta,
chama o `ChatClient` em streaming, executa as tool calls e repete. Sem
`StateGraph`/LangGraph, sem deepagents, sem orchestrator declarativo por nós.

- Tools resolvidas por nome no `TOOL_REGISTRY` (`backend/tools/registry.py`).
- Subagents (coder, search) via `backend/engine/subagents.py`.
- HITL via `should_require_approval` (`backend/engine/hitl.py`).
- Providers de LLM via Protocol `ChatClient` nativo (`backend/llm/base.py`,
  `backend/llm/<provider>/client.py`) — sem `BaseChatModel` do LangChain, sem
  `langchain-openai`/`langchain-anthropic`/`langchain-google-genai`. Todos os
  providers, incluindo o roteador `nine_router`, usam client HTTP nativo.

Motivo da migração para fora de LangChain/LangGraph/deepagents: bugs
silenciosos e não reportados no streaming (`astream` descartando
`delta.tool_calls` em produção por várias revisões antes de ser detectado) e
uma superfície de abstração maior do que o produto precisa. A troca foi
validada primeiro em escopo menor (OpenRouter, Ollama, Tavily saíram de
integrações via LangChain para clientes HTTP nativos, sem regressão) antes de
cobrir o núcleo agêntico inteiro.

## Storage

Dois modos, nenhum banco obrigatório:

- **`lite`** (default) — SQLite (`aiosqlite`) + LanceDB para vetores. Zero
  infraestrutura externa.
- **`complete`** — PostgreSQL (`asyncpg`) + Qdrant + Redis, para quem já tem
  essa infra.

Usuários, autenticação e settings ficam sempre em SQLite, local, independente
do modo escolhido.

## Desktop e backend são uma moeda só

O backend Python sempre roda; o frontend React pode estar visível (janela
Electron) ou oculto (headless/bandeja) — é um modo de operação, não dois
produtos. No app desktop (`VECTORA_DESKTOP=1`) a comunicação com o backend é
por IPC (named pipe/unix socket), nunca TCP. O modo servidor (web/VPS) é a
única superfície TCP, por design.

## MCP é client, não server

O Vectora consome servidores MCP externos (`backend/tools/mcp.py`,
marketplace de conectores). Um servidor MCP embutido (montado no mesmo
processo FastAPI, invocável por Claude Desktop e outros harnesses) chegou a
existir e foi removido: sem autenticação real e com risco de canibalização —
dava para assinar o plano pago só para acessar o RAG via outro harness, sem
nunca abrir o resto do workspace, que é o diferencial real do produto.
Reintroduzir isso é proibido (ver `CLAUDE.md`, regra 16).

## Sem API pública

Uma API REST `/v1` (extract/classify/jobs) chegou a existir e foi removida
antes do lançamento — sem autenticação de terceiros real, sem SDKs, sem
tração. Permanece como visão OEM de longo prazo, não como fundação técnica
atual.

## Modelo de negócio

Free é 100% local, sem conta. Pro é opcional e cobre trial/billing/
licenciamento, servido por `services.vectora.company` (Worker Cloudflare
próprio, sem RLS — autorização é código, em cada handler). Não existe um
"Vectora Cloud" rodando o desktop de terceiros em container.

## `services/`

Unifica o Worker `gateway` (OAuth/webhooks do desktop) com o `updates`
(distribuição de releases) e as rotas de auth/billing/license/GDPR/api-keys
que antes dependiam do Supabase.

## RAG library

Catálogo de RAG pré-indexado, publicável pela comunidade — hoje existe como
placeholder mínimo (`services/src/rag-library/`, catálogo + download), sob um
nome ainda a definir. Fora do escopo de curto prazo: entra em
desenvolvimento só depois do lançamento do Vectora.

## Contexto histórico (condensado)

O produto passou por três reescritas antes da arquitetura atual:

1. **Zyris Rag / Vectora V1** — agente em Go puro (Bubbletea, BadgerDB,
   Chromem-Go, Gin, Langchaingo, MCP/ACP, Llama.cpp gerenciado). Descartado
   por excesso de escopo: stack de LLM/embedding/reranker totalmente aberta,
   installer próprio para Llama.cpp em vez de conectar via HTTP a uma
   instalação existente, banco vetorial imaturo, e concorrência direta com
   Claude Code/Gemini CLI/Codex sem estrutura de empresa por trás.
2. **Vectora V2** — SDKs oficiais no lugar do Langchaingo, stack fechada em
   Gemini & Voyage, backend em nuvem obrigatório (SaaS com planos Free/Plus/
   Pro/Team) para viabilizar distribuição via GPT Store. Descartado porque um
   backend pago obrigatório inviabiliza a frente open source do projeto e é
   trivialmente removível via fork.
3. **Vectora V3** — voltou para tudo embarcado (Milvus, Postgres embarcado) e
   introduziu a ideia de um "VCR" (Vectora Cognitive Runtime): uma LM própria,
   treinada do zero, para decidir tool calls e montar contexto antes da LLM
   principal agir. Essa peça não avançou — treinar e manter um modelo próprio
   é um projeto de pesquisa em si, com custo que competia com o tempo de
   construir o produto. O que sobreviveu da V3 foi o princípio local-first
   (sem cloud obrigatória, sem vendor lock-in) e a ideia de preparar contexto
   antes da LLM agir — hoje implementada como engenharia de contexto
   determinística (tools de fs/git/web/rag, skills por harness, memória via
   Redis/SQLite), não como rede neural própria.

A arquitetura atual (motor nativo, storage lite/complete, MCP client-only,
Free/Pro sem SaaS obrigatório) é o resultado dessas três iterações — não um
ponto de partida arbitrário.
