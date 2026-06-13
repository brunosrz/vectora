# <img src="assets/vectora.svg" width="32" height="32"> Vectora

**Vectora** é um assistente de IA self-hosted para equipes de desenvolvimento — roda inteiramente no seu servidor, integra como sub-agente em qualquer orquestrador compatível com MCP (Claude Code, Claude Desktop, extensões VS Code) e vem com um chat web multi-usuário completo.

No seu núcleo, o Vectora resolve o **problema do abismo de conhecimento**: os LLMs não conhecem sua base de código, sua documentação ou as versões mais recentes da sua stack. O Vectora preenche essa lacuna com RAG híbrido (BM25 + vetores densos + reranker Cohere) — você indexa seus documentos uma vez e toda interação com IA passa a ter contexto completo.

---

## Por que o Vectora?

<<<<<<< HEAD

- **Orchestrator + Specialized Agents**: The Orchestrator is the primary LLM agent — it answers directly for simple queries and crafts explicit task instructions for specialists (search, coder). No wasted routing hops.
- **RAG-native subgraph**: Every document query goes through a full retrieve → score → rerank → inject pipeline. Results flow back to the Orchestrator for synthesis.
- **16 tools across 5 categories**: Web search, vector search, file system, artifacts, memory — always available across all agents.
- **Cascading embeddings**: Web search results land in an isolated `web_cache` collection and pass a curation gate (Cohere reranker + LLM judge) before being embedded — your curated knowledge base is never contaminated by unreviewed web results.
- **Sub-agent architecture**: Runs as an MCP server. Claude Code delegates complex tasks to Vectora; Vectora reasons, routes, and responds.
- **Persistent memory**: Cross-session memory in SQLite. Vectora remembers your preferences, project context, and decisions.
- **Zero infra**: SQLite + LanceDB. No Docker required for local use.
- # **Multi-LLM**: Google Gemini (free tier), Cohere (free tier), OpenAI, Anthropic, or Ollama (fully local).
- **Orchestrator + Agentes Especializados** — O Orchestrator é o agente LLM primário. Responde diretamente para consultas simples e delega com instruções explícitas para os especialistas (search, coder, RAG). Sem hops de roteamento desnecessários.
- **Pipeline RAG híbrido** — Cada recuperação roda BM25 + busca vetorial densa + reranker Cohere. O resultado flui de volta para o Orchestrator para síntese.
- **Mais de 20 ferramentas em 6 categorias** — Web search, busca vetorial, filesystem, terminal (PTY), artifacts, memória — sempre disponíveis.
- **Embeddings curados** — Resultados da busca web passam por um gate de curadoria (reranker Cohere + LLM judge) antes de serem indexados. Sua base de conhecimento nunca é contaminada.
- **Chat web multi-usuário** — Interface Next.js integrada com autenticação, RBAC, workspaces, terminal embarcado, visualizador de diff e painel de planos.
- **Memória persistente entre sessões** — Memória em SQLite com isolamento por usuário.
- **Infraestrutura zero no modo lite** — SQLite + LanceDB. Sem Docker ou Postgres para uso local ou times pequenos.
- **Multi-LLM** — Google Gemini (plano gratuito), Cohere, OpenAI, Anthropic, ou Ollama (totalmente local).
  > > > > > > > dev

---

## Arquitetura

### Orchestrator + Workers

<<<<<<< HEAD
Every message enters through a single entry point and is routed by the **Orchestrator** to the right specialized agent:

```
START
  └─► orchestrator (responds inline OR delegates with task_query)
        ├─► [respond]      → END
        ├─► [search]       → search → search_tools → process_retrieval ↻ → END
        ├─► [coder]        → coder → coder_tools ↻ → END
        └─► [rag_subgraph] → rag_subgraph → orchestrator (synthesis) → END
```

| Agent            | Responsibility                                                                       | Tools                                                                          |
| ---------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| **orchestrator** | Primary LLM agent — responds directly OR delegates with an explicit task description | `create_artifact`, `save_memory`, `get_memory`, `delete_memory`                |
| **search**       | Web research, real-time info, builds knowledge base via cascading embeddings         | `web_search`, `fetch_url`, `vector_search`                                     |
| **coder**        | File operations, terminal commands, code generation                                  | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal`         |
| **rag**          | Retrieval pipeline — retrieve → score → rerank/websearch → inject → orchestrator     | `vector_search`, `embedding`, `ingest_docs`, `manage_retriever` (via subgraph) |

### RAG Subgraph

When the orchestrator routes to `rag`, a dedicated subgraph runs the full retrieval pipeline before synthesis:

```
rag_retrieve (vector_search)
  └─► rag_decide (score threshold)
        ├─► rag_inject     (score ≥ 0.7 — high confidence, inject directly)
        ├─► rag_rerank     (score 0.4–0.7 — rerank with Cohere before inject)
        └─► rag_websearch  (score < 0.4 — fall back to web + auto-embed results)
```

Results are injected as a `SystemMessage` into context. The Orchestrator then synthesizes the final answer inline, without a separate agent hop.

### Artifact Tool

Agents explicitly call `create_artifact` to persist structured documents (plans, specs, guides, architecture decisions) to `~/.vectora/artifacts/{session_id}/` as Markdown files. The tool returns structured metadata (path, title, type, session_id, timestamp) that the Orchestrator can reference in future turns.

### Web Content Anti-contamination

After any `web_search` or `fetch_url` call, `process_retrieval` routes results through a curation gate before embedding:

1. **Cohere reranker** scores each candidate against the current query — items below `web_persist_min_score` are discarded.
2. **LLM judge** evaluates survivors against the project context and current task, returning a `keep/discard` verdict per document.

# Approved content is embedded into a dedicated `web_cache` collection, isolated from `articles` (user-curated content). The `/rag` panel shows the breakdown per collection, and `manage_retriever` lets you audit or remove cached web content at any time.

| Agente           | Responsabilidade                                            | Ferramentas                                                            |
| ---------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------- |
| **orchestrator** | Agente LLM primário — responde direto OU delega             | `create_artifact`, `save_memory`, `get_memory`, `delete_memory`        |
| **search**       | Pesquisa web em tempo real, embeddings curados              | `web_search`, `web_fetch`, `web_crawl`, `web_map`, `vector_search`     |
| **coder**        | Operações de arquivo, terminal, geração de código           | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal` |
| **rag**          | Retrieve → score → rerank/websearch → inject → orchestrator | `vector_search`, `embedding`, `ingest_docs`, `manage_retriever`        |

### RAG Subgraph

| Score   | Caminho                                                              |
| ------- | -------------------------------------------------------------------- |
| ≥ 0.7   | `rag_inject` direto — alta confiança                                 |
| 0.4–0.7 | `rag_rerank` → `rag_inject`                                          |
| < 0.4   | `search` (com `rag_pending=True`) → `search_finalize` → `rag_inject` |

> > > > > > > dev

---

## Pré-requisitos

| Requisito        | Notas                                                                            |
| ---------------- | -------------------------------------------------------------------------------- |
| **Python 3.13+** | Gerenciado pelo [uv](https://docs.astral.sh/uv/)                                 |
| **Node.js 22+**  | Para o chat web (`pnpm` obrigatório)                                             |
| **Chave Cohere** | Embeddings + reranking — [plano gratuito](https://dashboard.cohere.com/api-keys) |
| **Chave Tavily** | Busca web — [plano gratuito](https://app.tavily.com/)                            |
| **Provedor LLM** | Google Gemini (gratuito), OpenAI, Anthropic, Cohere, ou Ollama                   |

---

<<<<<<< HEAD

## Installation

### Option 1: UV — Local install (recommended)

Install Vectora globally with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install vectora-agent
```

On first run, the setup wizard will ask for your API keys and write them to `~/.vectora/.env`.

```bash
vectora        # starts chat (wizard runs automatically if no keys found)
```

To connect Vectora as an MCP sub-agent for Claude Code or Claude Desktop, add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "Vectora": {
      "command": "vectora",
      "args": ["mcp-server"]
    }
  }
}
```

### Option 2: Docker — VPS / remote MCP server

Use this when you want Vectora running on a server and accessible from multiple machines or orchestrators via SSE.

**Local (no domain):**

```bash
cp .env.example .env
# Edit .env with your API keys

docker compose up -d
# SSE endpoint: http://localhost:8000/sse
```

**VPS with Traefik (HTTPS + domain):**

```bash
cp .env.example .env
# Edit .env with your API keys, VECTORA_DOMAIN and ACME_EMAIL

# Create the shared Traefik network if it doesn't exist yet
docker network create traefik-public

docker compose -f docker-compose.yml -f docker-compose.traefik.yml up -d
# SSE endpoint: https://vectora.yourdomain.com/sse
```

To connect from Claude Code or any MCP-compatible orchestrator:

```json
{
  "mcpServers": {
    "Vectora": {
      "url": "https://vectora.yourdomain.com/sse"
    }
  }
}
```

### Option 3: From Source

=======

## Início rápido (a partir do código fonte)

> > > > > > > dev

```bash
git clone https://github.com/brunosrz/vectora.git
cd vectora

<<<<<<< HEAD
uv sync

cp .env.example .env
# Edit .env with your API keys

uv run vectora
=======
# Instalar dependências Python
uv sync

# Copiar e preencher suas chaves de API
cp .env.example .env
# Edite o .env: GOOGLE_API_KEY, COHERE_API_KEY, TAVILY_API_KEY

# Instalar dependências do chat web
pnpm --dir chat install

# Iniciar backend (porta 8080) + chat web (porta 3000) simultaneamente
scons dev
```

Abra `http://localhost:3000`. O primeiro usuário a se cadastrar vira administrador root.

### Somente CLI (sem chat web)

```bash
# Chat textual interativo
uv run vectora chat

# Servidor MCP (stdio — para Claude Code / Claude Desktop)
uv run vectora server mcp --transport stdio

# Somente API — sem Next.js, sem proxy de frontend
uv run vectora server headless --port 8080
>>>>>>> dev
```

---

<<<<<<< HEAD

## CLI Reference

````
vectora [options]              Start chat (resume last session for this directory)
vectora mcp-server             Start MCP server (stdio)
vectora traces                 View observability traces
vectora sessions               List all saved sessions
vectora config                 Show current configuration
vectora config --set KEY=VALUE Edit a setting

Options:
  --model MODEL        Switch LLM model (provider auto-detected). Persists.
  --ollama             Force Ollama provider (for arbitrary local model names)
  --session ID         Resume a specific session by 6-digit ID
  --new                Force a new session
  --verbosity N        Verbosity level 0–5 (0=silent, 5=debug panel). Persists.
  --version            Show version
=======
## Integração MCP

Adicione ao `.mcp.json` do seu projeto ou `~/.claude/mcp.json` globalmente:

```json
{
  "mcpServers": {
    "Vectora": {
      "command": "uv",
      "args": ["run", "vectora", "server", "mcp", "--transport", "stdio"]
    }
  }
}
````

Servidor MCP remoto via SSE:

```json
{
  "mcpServers": {
    "Vectora": {
      "url": "https://vectora.seudominio.com/mcp/sse"
    }
  }
}
>>>>>>> dev
```

---

## Build (SCons)

<<<<<<< HEAD
| Command | Description |
| --------------- | -------------------------------------------------------------- |
| `/help` | Show quick help |
| `/list` | Show all commands |
| `/tools` | List available tools |
| `/model` | List or switch models |
| `/debug [0-5]` | Set verbosity level (tool calls, routing decisions, log panel) |
| `/new` | Start a new session |
| `/sessions` | List all sessions |
| `/session <id>` | Switch to a specific session |
| `/quit` | Exit |
=======
O sistema de build usa [SCons](https://scons.org/), incluído como
dependência de dev. Funciona direto no PowerShell, cmd, bash ou zsh —
sem dependência de sintaxe shell específica.

> > > > > > > dev

### Produto final (do zero ao instalador)

```
scons release          Build completo + instalador nativo para o SO atual
scons release-win      Instalador Windows (.msi + .exe NSIS)
scons release-mac      Instalador macOS (.dmg universal x64+arm64)
scons release-linux    Instaladores Linux (.AppImage + .deb + .rpm)
```

Pipeline executado em sequência:

```
build-chat (1-2 min)  -->  build-nuitka (10-30 min)  -->  build-desktop  -->  package
chat/out/                  dist-nuitka/vectora.exe      desktop/dist/        desktop/dist-electron/
```

### Passos individuais

```
scons build-chat       Build Next.js + export estático -> chat/out/
scons build-nuitka     Binário Nuitka onefile -> dist-nuitka/  (10-30 min na 1ª vez)
scons build-desktop    TypeScript Electron -> desktop/dist/
scons package          electron-builder -> desktop/dist-electron/
scons install-desktop  pnpm install em desktop/
```

### Desenvolvimento

```
scons dev              Backend (8080) + Next.js dev (3000), Ctrl+C encerra ambos
scons dev-backend      Apenas backend
scons dev-chat         Apenas Next.js dev
```

### Qualidade

```
scons test             pytest tests/unit/
scons lint             ruff + ty + tsc + oxlint
scons clean            Remove dist-nuitka/ chat/out/ desktop/dist*
scons help             Lista completa com descrições
```

**Nota:** no Windows basta abrir o PowerShell ou cmd na raiz do projeto e
rodar `scons release-win`. Sem Git bash, sem truques de shell.

---

## Docker

<<<<<<< HEAD
16 tools across 5 categories, always available to all agents:

| Category      | Tools                                                                  | Primary Agent         |
| ------------- | ---------------------------------------------------------------------- | --------------------- |
| **Web**       | `web_search`, `fetch_url`                                              | search                |
| **RAG**       | `vector_search`, `embedding`, `ingest_docs`, `manage_retriever`        | search / RAG subgraph |
| **Files**     | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal` | coder                 |
| **Artifacts** | `create_artifact`                                                      | orchestrator          |
| **Memory**    | `save_memory`, `get_memory`, `delete_memory`                           | orchestrator / coder  |

=======

```bash
cp .env.example .env
# Edite o .env com suas chaves

docker compose up -d
# Chat web: http://localhost:8080
```

VPS com HTTPS (Traefik):

```bash
cp .env.example .env
# Defina VECTORA_DOMAIN e ACME_EMAIL

docker network create traefik-public
docker compose -f docker-compose.yml -f docker-compose.traefik.yml up -d
# Chat web: https://vectora.seudominio.com
```

> > > > > > > dev

---

## Referência de CLI

```
vectora [comando] [opções]

Comandos:
  (padrão) / chat      Chat textual interativo (retoma a última sessão)
  server chat          FastAPI + chat web (serve Next.js embutido ou faz proxy para o dev server)
  server mcp           Servidor MCP (transporte stdio ou SSE)
  server headless      FastAPI somente — sem chat, sem proxy (para integrações de API pura)
  setup                Wizard de configuração inicial interativo
  license              Exibir ou gerenciar status da licença
  auth                 Login / logout / whoami
  traces               Ver rastros internos de observabilidade
  sessions             Listar todas as sessões salvas
  config               Exibir ou editar configurações

Opções globais:
  --model <nome>       Trocar provedor/modelo LLM (ex: gemini-2.5-flash)
  --new                Forçar nova sessão de conversa
  --session <id>       Retomar sessão específica
  --verbosity <0-5>    Nível de detalhe da saída
  --port <n>           Porta para comandos de servidor (padrão: 8080)
```

---

## Dados e Persistência

Todos os dados ficam em `~/.vectora/`:

```
~/.vectora/
<<<<<<< HEAD
├── .env                    # API keys (secrets — never commit)
├── settings.json           # Runtime preferences (provider, model, verbosity)
├── data/
│   ├── vectora.db          # Sessions, memories, LangGraph checkpoints (SQLite)
│   ├── embedding_queue.db  # Async embedding queue (SQLite)
│   ├── traces.db           # Internal observability spans (SQLite)
│   └── lancedb/            # Vector store for RAG (LanceDB)
├── artifacts/              # Auto-detected plans, specs, guides
│   └── {session_id}/
│       └── *.md
├── keys/                   # Reserved for future key management
└── logs/
    ├── vectora.jsonl       # Structured JSON logs
    └── session_*.md        # Exported session audit trails
=======
├── config.toml             # Configuração de runtime (provedores, storage)
├── auth.key                # Chave JWT (gerada automaticamente, perm 600)
├── data/
│   ├── vectora.db          # Usuários, sessões, memórias, checkpoints (SQLite WAL)
│   ├── embedding_queue.db  # Fila de embeddings assíncrona (SQLite)
│   ├── traces.db           # Spans de observabilidade (SQLite)
│   └── lancedb/            # Banco vetorial (LanceDB)
├── artifacts/              # Planos, specs, guias (output do create_artifact)
│   └── {session_id}/*.md
├── secrets/
│   ├── system.kdbx         # Vault de segredos do sistema (formato KeePassXC)
│   └── users/{id}.kdbx     # Vault por usuário (chaves de API, SSH)
├── skills/{user_id}/       # Skills instaladas (formato SKILL.md)
├── safe_roots.json         # Caminhos confiáveis configurados pelo admin
├── workspaces.json         # Workspaces registrados
└── license_cache.json      # Cache de validação de licença (TTL 6h / 48h offline)
>>>>>>> dev
```

**Separation of concerns:**

- `~/.vectora/.env` — secrets (API keys). Never versioned.
- `~/.vectora/settings.json` — non-secret runtime preferences (active provider, model, verbosity, last session per directory). Managed by `vectora config`.

---

## Referência de Ferramentas

<<<<<<< HEAD
| Layer | Technology |
| ---------------- | ------------------------------------------------------------------------------------------------------ |
| Language | Python 3.14+ managed by [uv](https://github.com/astral-sh/uv) |
| Agent Framework | [LangChain](https://langchain.com/) + [LangGraph](https://langchain-ai.github.io/langgraph/) |
| Agent Pattern | Orchestrator + Specialized Workers (search / coder) + RAG Subgraph |
| Vector Store | [LanceDB](https://lancedb.github.io/lancedb/) — file-based, zero-config |
| Embeddings | [Cohere](https://cohere.com/) — `embed-multilingual-v3.0` + `rerank-multilingual-v3.0` |
| Persistence | SQLite via `aiosqlite` + LangGraph Checkpointer |
| Context Protocol | [MCP](https://modelcontextprotocol.io/) via [FastMCP](https://github.com/jlowin/fastmcp) |
| Terminal UI | [Rich](https://rich.readthedocs.io/) + [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/) |
| Observability | [LangSmith](https://smith.langchain.com/) (optional) |
=======
| Categoria | Ferramentas |
| ------------- | ----------------------------------------------------------------------------------------------------------- |
| **Web** | `web_search`, `web_fetch`, `web_crawl`, `web_map`, `web_research`, `web_get_research` |
| **RAG** | `vector_search`, `embedding`, `ingest_docs`, `manage_retriever` |
| **Arquivos** | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal` |
| **Artifacts** | `create_artifact` |
| **Memória** | `save_memory`, `get_memory`, `delete_memory` |
| **Git** | `git_status`, `git_log`, `git_diff`, `git_branch`, `git_checkout`, `git_commit`, `git_push`, `gh_pr_create` |

> > > > > > > dev

---

## Stack de Tecnologia

<<<<<<< HEAD
API keys go in `~/.vectora/.env` (created by the setup wizard) or a project-local `.env`:

````env
# LLM Provider (auto-detected from available keys if not set)
=======
| Camada             | Tecnologia                                                                                             |
| ------------------ | ------------------------------------------------------------------------------------------------------ |
| Linguagem          | Python 3.13+ / [uv](https://docs.astral.sh/uv/)                                                        |
| Framework de agent | [LangChain](https://langchain.com/) + [LangGraph](https://langchain-ai.github.io/langgraph/)           |
| Banco vetorial     | [LanceDB](https://lancedb.github.io/lancedb/) (lite) / Qdrant (pro)                                    |
| Embeddings         | Cohere `embed-multilingual-v3.0` + `rerank-multilingual-v3.0`                                          |
| Persistência       | SQLite + `aiosqlite` (WAL) + LangGraph Checkpointer                                                    |
| Chat web           | Next.js 16 + Hono + Zustand + shadcn/ui + Tailwind                                                     |
| Terminal           | PTY via `pywinpty` (Win) / `ptyprocess` (Unix) + xterm.js                                              |
| Protocolo contexto | [MCP](https://modelcontextprotocol.io/) via [FastMCP](https://github.com/jlowin/fastmcp)               |
| Interface CLI      | [Rich](https://rich.readthedocs.io/) + [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/) |

---

## Configuração

Chaves de API vão em `~/.vectora/config.toml` (criado pelo `vectora setup`) ou em um `.env` local:

```env
# Provedor LLM (detectado automaticamente pelas chaves disponíveis)
>>>>>>> dev
LLM_PROVIDER=google-genai
GOOGLE_API_KEY=sua_chave_aqui

# Obrigatório: embeddings e reranking RAG
COHERE_API_KEY=sua_chave_aqui

# Obrigatório: busca web e extração de URLs
TAVILY_API_KEY=sua_chave_aqui

# Opcional: rastreamento
LANGSMITH_TRACING=false
<<<<<<< HEAD
LANGSMITH_API_KEY=your_key_here
LANGSMITH_PROJECT=vectora
=======
LANGSMITH_API_KEY=sua_chave_aqui
>>>>>>> dev
````

Runtime preferences (model, verbosity, session history) are managed in `~/.vectora/settings.json` via `vectora config` or the `/model` and `/debug` chat commands — no need to touch `.env` for these.

---

## Licença

<<<<<<< HEAD
Apache 2.0. See [LICENSE](./LICENSE).

# <!-- mcp-name: io.github.brunosrz/vectora -->

Proprietária. Consulte o arquivo [LICENSE](./LICENSE).

> > > > > > > dev
