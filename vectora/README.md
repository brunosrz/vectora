# <img src="backend/assets/vectora.png" width="32" height="32"> Vectora

**Vectora** é um assistente de IA self-hosted para equipes de desenvolvimento — roda inteiramente no seu servidor, integra como sub-agente em qualquer orquestrador compatível com MCP (Claude Code, Claude Desktop, extensões VS Code) e vem com um chat web multi-usuário completo.

No seu núcleo, o Vectora resolve o **problema do abismo de conhecimento**: os LLMs não conhecem sua base de código, sua documentação ou as versões mais recentes da sua stack. O Vectora preenche essa lacuna por dois caminhos complementares: **RAG híbrido** (BM25 + vetores densos + reranker Cohere/VoyageAI) para recuperação por similaridade, e o **Context Graph** — um grafo de conhecimento nativo do workspace (funções, classes, conceitos e suas relações, via tree-sitter + extração semântica por LLM) para contexto estrutural.

---

## Por que o Vectora?

- **Deep-agent canônico** — o grafo de execução é montado via `create_deep_agent` (pacote `deepagents`, sobre LangGraph), não um orchestrator manual por nós. Isso dá middleware nativo (HITL configurável por modo de permissão), backends de filesystem pluggable e um supervisor que delega para 2 subagentes especializados com instruções explícitas — sem hops de roteamento desnecessários.
- **Pipeline RAG híbrido** — cada recuperação roda BM25 + busca vetorial densa + reranker antes de voltar para o supervisor sintetizar a resposta.
- **Context Graph nativo** — analisa o workspace (AST via tree-sitter para Python/JS/TS/Go/Rust/Java/C/C++, + extração semântica por LLM) e gera um grafo de conhecimento com god nodes, comunidades e perguntas sugeridas. Configurável por tipo de arquivo (ex.: só markdown, deixando o código para o RAG).
- **70+ ferramentas nativas** — filesystem, git (14 operações), GitHub (`gh`), terminal (PTY real), web, RAG, memória, integrações opcionais (Jira, Slack, Linear, Google Drive, Gmail, Notion) e utilitárias (hash, JWT, regex, HTTP) — sempre disponíveis, sem instalar plugins.
- **Resiliência de provider** — fallback automático de LLM por quota (429 troca de provider sozinho, com aviso visível) e de embeddings/rerank (Cohere↔VoyageAI). O model selector reflete o provider ativo.
- **Embeddings curados** — resultados da busca web passam por um gate de curadoria (reranker + LLM judge) antes de serem indexados. Sua base de conhecimento nunca é contaminada.
- **Chat web multi-usuário** — interface React 19 (Vite + TanStack Router) com autenticação, RBAC, workspaces e a workbench (terminal, git, arquivos, context graph, memória, planos — ver abaixo).
- **Memória persistente entre sessões** — memória isolada por usuário, com checkpointer do LangGraph por thread.
- **Infraestrutura zero no modo lite** — SQLite + LanceDB. Sem Docker ou Postgres para uso local ou times pequenos. O modo **complete** (Postgres + Qdrant + Redis) já existe como caminho alternativo para quem precisa de mais escala.
- **Multi-LLM** — Google Gemini, OpenAI, Anthropic, Cohere, ou Ollama (totalmente local). O model selector lista apenas os providers com API key configurada.

---

## Arquitetura

### Supervisor + Subagentes (`create_deep_agent`)

O agente principal (`backend/services/agent_factory.py`) é construído com `create_deep_agent` do pacote `deepagents` — não um `StateGraph` artesanal. O supervisor responde direto para consultas simples ou delega, via a tool `task`, para um dos 2 subagentes especializados:

| Agente           | Papel                                                            | Ferramentas principais                                                               |
| ---------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **orchestrator** | Supervisor — responde direto OU delega para coder/search         | `create_artifact`, `save_memory`, `get_memory`, `delete_memory`, RAG                 |
| **coder**        | Filesystem, terminal, git — geração e revisão de código          | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal`, tools de git |
| **search**       | Busca web em tempo real + RAG (não há subagente de RAG separado) | `web_search`, `web_fetch`, `vector_search`, `embedding`, `ingest_docs`               |

HITL (Human-in-the-Loop) roda via `HumanInTheLoopMiddleware` nativo do harness, configurável por modo de permissão (perguntar sempre / aceitar edições / autônomo / plano).

### Pipeline de RAG (dentro das tools `search`/`rag`)

| Score   | Caminho                                                                               |
| ------- | ------------------------------------------------------------------------------------- |
| ≥ 0.7   | Injeção direta no contexto — alta confiança                                           |
| 0.4–0.7 | Rerank (Cohere/VoyageAI) → injeção                                                    |
| < 0.4   | Cai para busca web, com os resultados curados (reranker + LLM judge) antes de indexar |

---

## Workbench (painel lateral)

No modo **Code**, o chat vem com um painel lateral multi-aba — a workbench. Cada aba renderiza a partir de dados do backend em tempo real:

| Aba               | O que faz                                                                                                                                                                                                         |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **File System**   | Árvore do workspace; abre arquivos como janelas flutuantes (redimensionáveis, arrastáveis), edita via Monaco Editor, e fixa arquivos ("pin") para manter no contexto.                                             |
| **Git**           | Status (staged/unstaged/untracked), diff por arquivo com hunks, histórico de commits, stash e worktrees.                                                                                                          |
| **Search**        | Busca em todo o workspace (arquivos + conteúdo).                                                                                                                                                                  |
| **Plan**          | Planos, specs e guias gerados pelo agente (`create_artifact`, markdown em `~/.vectora/artifacts/`).                                                                                                               |
| **Segundo plano** | Tarefas em segundo plano da sessão + histórico de execuções.                                                                                                                                                      |
| **Preview**       | Configura targets de run (servidor/comando) e mostra o preview do projeto.                                                                                                                                        |
| **Memory (RAG)**  | Memórias e citações RAG/web indexadas + settings de RAG: reranker on/off + top_k, provider de rerank/embedding (Cohere/Voyage/auto), tipos de arquivo a ingerir, e gestão de coleções (listar/apagar).            |
| **Context Graph** | Constrói e exibe o grafo de conhecimento do workspace (god nodes, conexões, perguntas) + settings: tipos de arquivo a indexar (code/document/paper) e modo (semântico/AST). Build pausável e retomável por quota. |
| **Terminal**      | Shell embarcado real via PTY (`pywinpty`/`ptyprocess`) renderizado com xterm.js, com tema dinâmico sincronizado ao tema da UI.                                                                                    |

Os artefatos do Context Graph e o cache ficam em `.vectora/context-graph/` dentro do workspace; o que estiver no `.vectoraignore` (ignore unificado, vale para context graph, RAG, filesystem e chat) é invisível para o Vectora.

---

## Pré-requisitos

| Requisito        | Notas                                                                                             |
| ---------------- | ------------------------------------------------------------------------------------------------- |
| **Python 3.13**  | Gerenciado pelo [uv](https://docs.astral.sh/uv/) — fixado em 3.13 (Nuitka ainda não suporta 3.14) |
| **Node.js 24+**  | Para o frontend web (`pnpm` obrigatório)                                                          |
| **Chave Cohere** | Embeddings + reranking — [plano gratuito](https://dashboard.cohere.com/api-keys)                  |
| **Chave Tavily** | Busca web — [plano gratuito](https://app.tavily.com/)                                             |
| **Provedor LLM** | Google Gemini, OpenAI, Anthropic, Cohere, ou Ollama                                               |

---

## Início rápido (a partir do código fonte)

```bash
git clone https://github.com/brunosrz/vectora.git
cd vectora/vectora

# Instalar dependências Python
uv sync

# Copiar e preencher suas chaves de API
cp .env.example .env
# Edite o .env: GOOGLE_API_KEY, COHERE_API_KEY, TAVILY_API_KEY

# Instalar dependências do frontend (SPA Vite)
pnpm --dir frontend install

# Terminal 1 — backend completo + MCP (/mcp) + SPA (porta 8080)
uv run vectora start --port 8080
# Terminal 2 — frontend dev (Vite, porta 3000, faz proxy p/ a API)
pnpm --dir frontend dev
```

Abra `http://localhost:3000`. O primeiro usuário a se cadastrar vira administrador root.

### CLI de operação (VPS via SSH)

O frontend cobre toda a configuração, mas em VPS via SSH a CLI Rich expõe o essencial:

```bash
uv run vectora config keys         # wizard de API keys + provider de LLM
uv run vectora config docker up    # sobe Postgres + Redis + Qdrant local
uv run vectora start --headless    # backend + MCP, sem janela (bandeja)
```

---

## Integração MCP

O MCP server sobe **junto** com o Vectora (`vectora start`), montado em `/mcp` no mesmo processo FastAPI (via `FastMCP`, SSE) — não há processo MCP separado. Conecte qualquer cliente MCP (Claude Code/Desktop) à URL `/mcp` do seu Vectora em execução:

```json
{
  "mcpServers": {
    "Vectora": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

Em produção, use a URL pública (HTTPS) do seu servidor: `https://vectora.seudominio.com/mcp`.

---

## Build (SCons)

O sistema de build usa [SCons](https://scons.org/), incluído como dependência de dev, invocado a partir da **raiz do monorepo** (não desta pasta). Funciona direto no PowerShell, cmd, bash ou zsh — sem dependência de sintaxe shell específica.

### Produto final (do zero ao instalador)

```
scons release          Build completo + instalador nativo para o SO atual
```

Bump de versão, build dos instaladores e publicação no canal de update rodam
só via GitHub Actions, disparados por `[up-release]` na mensagem do commit.

Pipeline executado em sequência (encadeado automaticamente por `release`):

```
build frontend (Vite)  -->  build híbrido do backend  -->  Electron + electron-builder
frontend/dist/               dist/vectora/vectora(.exe)    frontend/dist-electron/
```

O "build híbrido" (`build-hybrid.py`, chamado pelo `scons`) compila **só o pacote `backend/`** em C via `Nuitka --mode=package` (gera `backend.pyd`) e depois usa **PyInstaller** para empacotar o launcher + `backend.pyd` + libs Python num único `vectora.exe`. Compilar só o backend (em vez de onefile puro) evita OOM ao compilar dependências gigantes (`google.genai.types`, LanceDB) para C. O pipeline de CI (GitHub Actions) ainda usa Nuitka onefile direto para as builds nativas de release — os dois caminhos convivem hoje.

### Qualidade

```
scons tests            Suíte completa: pytest tests/ (unit+integration+e2e+stress) + vitest
scons coverage          Mesma suíte com relatório de cobertura
scons lint              ruff + ty + bandit (Python) + tsc + oxlint (TypeScript)
scons tests-storage     Só testes de storage (Postgres/Redis/Qdrant — sobe docker automaticamente)
scons clean             Remove dist/ frontend/dist/ frontend/electron/dist*
scons help              Lista completa com descrições
```

**Nota:** no Windows basta abrir o PowerShell ou cmd na raiz do monorepo e rodar `scons release`. Sem Git bash, sem truques de shell.

### CI/CD

- **GitHub Actions** (`.github/workflows/vectora.yml`) — pipeline única: lint → security scan (bandit + pip-audit) → frontend (oxlint/tsc/vitest) → build verification → testes unit/stress/integration+e2e → release nativo (matriz Linux/macOS/Windows, build híbrido Nuitka + electron-builder). Todo o pipeline (inclusive lint) só roda de verdade com `[up-release]` na mensagem do commit ou `workflow_dispatch` manual — qualquer outro push aparece como "skipped", sem custar minutos.
- **Jenkins** (`Jenkinsfile`, raiz do monorepo) — assume o CI contínuo em todo push/PR (`scons lint && scons tests`); o fluxo de release é um job parametrizado e manual que builda por SO (agentes dedicados Windows/macOS/Linux) e publica os instaladores no worker `services` (R2 + KV) via `services/scripts/release.ts`.

---

## Docker

```bash
cp .env.example .env
# Edite o .env com suas chaves

docker compose up -d
# Chat web: http://localhost:8080
```

`docker-compose.yml` sobe **PostgreSQL** (`pgvector/pgvector:pg16`), **Redis** (`redis-stack-server`, com RediSearch/RedisJSON para o cache LLM distribuído) e **Qdrant** — o backend do Vectora em si **não** roda como container, roda no host e se conecta a esses três serviços quando `STORAGE_MODE=complete`.

VPS com HTTPS (Traefik):

```bash
cp .env.example .env
# Defina VECTORA_DOMAIN e ACME_EMAIL

docker network create traefik-public
docker compose -f docker-compose.yml -f docker-compose.traefik.yml up -d
# Chat web: https://vectora.seudominio.com
```

---

## Referência de CLI

```
vectora [comando] [opções]

Comandos:
  (sem args)           Imprime este help
  start                Backend completo + MCP (/mcp) + SPA (fullstack)
  start --headless     Sobe sem janela (bandeja + backend + MCP)
  config               Mostra/edita settings; subcomandos: keys, docker, qdrant, redis
  storage              Migrations, diagnóstico, backup/restore, wizard BaaS
  sessions             Listar todas as sessões salvas

Opções de start:
  --headless           Não abre janela (mantém backend + MCP + bandeja)
  --host <host>        Host de escuta (padrão: 0.0.0.0)
  --port <n>           Porta (padrão: 8080)
  --ssl-certfile/-keyfile <pem>   TLS (serve em https://)
```

---

## Dados e Persistência

Todos os dados ficam em `~/.vectora/`:

```
~/.vectora/
├── config.toml             # Configuração de runtime (provedores, storage)
├── auth.key                # Chave JWT (gerada automaticamente, perm 600)
├── data/
│   ├── vectora.db          # Usuários, sessões, memórias, checkpoints (SQLite WAL)
│   ├── embedding_queue.db  # Fila de embeddings assíncrona (SQLite)
│   ├── traces.db           # Spans de observabilidade (SQLite)
│   └── lancedb/            # Banco vetorial (LanceDB, modo lite)
├── artifacts/              # Planos, specs, guias (output do create_artifact)
│   └── {session_id}/*.md
├── secrets/
│   ├── system.kdbx         # Vault de segredos do sistema (formato KeePassXC)
│   └── users/{id}.kdbx     # Vault por usuário (chaves de API, SSH)
├── skills/{user_id}/       # Skills instaladas (formato SKILL.md)
├── safe_roots.json         # Caminhos confiáveis configurados pelo admin
├── workspaces.json         # Workspaces registrados
└── license_cache.json      # Cache de validação de licença (TTL 6h / 48h offline)
```

No modo **complete** (`STORAGE_MODE=complete`), checkpointer e sessões vão para PostgreSQL, vetores para Qdrant, e cache/KV para Redis — usuários, auth e settings continuam **sempre** em SQLite, independente do modo.

---

## Referência de Ferramentas

Mais de 70 tools registradas, organizadas por categoria:

| Categoria         | Ferramentas                                                                                                  |
| ----------------- | ------------------------------------------------------------------------------------------------------------ |
| **Arquivos**      | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal`, `create_artifact`                    |
| **Git**           | 14 operações — status, log, diff, branch, checkout, commit, push, pull, stage/unstage, stash, merge, compare |
| **GitHub**        | `gh_issue_create/list/view/comment`, `gh_pr_create/list/view/merge` (via `gh` CLI)                           |
| **Web**           | `web_search`, `web_fetch` + extração/crawl                                                                   |
| **RAG**           | `vector_search`, `embedding`, `ingest_docs`, `manage_retriever`                                              |
| **Context Graph** | `build_knowledge_graph`, `graph_query`, `graph_explain`, `graph_path`, `graph_update`, `graph_affected`      |
| **Memória**       | `save_memory`, `get_memory`, `delete_memory`                                                                 |
| **Workspace**     | `workspace_list`, `workspace_describe`, `bucket_summary`                                                     |
| **Integrações**   | Jira, Slack, Linear, Google Drive, Gmail, Notion (opcionais, via OAuth/API key por workspace)                |
| **Utilitárias**   | `time_*`, `hash_*`, `base64_*`, `regex_test`, `json_query`, `jwt_decode`, `http_request`                     |
| **MCP**           | `call_mcp_tool` — delega para MCP servers de terceiros configurados pelo usuário                             |

---

## Testes

O projeto segue TDD (par caminho-feliz + caminho-de-erro no mesmo teste) — ver `documents/testing-guide.md` no monorepo. Contagem atual (verificada via execução real das suítes):

| Suíte                              | Arquivos | Testes     | Como rodar                                                        |
| ---------------------------------- | -------- | ---------- | ----------------------------------------------------------------- |
| **Backend — unit** (`tests/unit/`) | 137      | 2.387      | `uv run pytest tests/unit -q`                                     |
| **Backend — integration**          | 5        | 47         | `uv run pytest tests/integration -q` (Postgres/Redis/Qdrant/MCP)  |
| **Backend — e2e**                  | 2        | 22         | `uv run pytest tests/e2e -q` (MCP resources/routes reais)         |
| **Backend — stress**               | 4        | 7          | `uv run pytest tests/stress -q` (concorrência, sem APIs externas) |
| **Backend — total**                | **148**  | **2.463**  | `uv run pytest tests -q`                                          |
| **Frontend — vitest**              | 90       | 1.008      | `pnpm --dir frontend exec vitest run`                             |
| **Frontend — Playwright e2e**      | 2        | 4          | `pnpm --dir frontend exec playwright test`                        |
| **Total do produto**               | **240**  | **~3.475** | `scons tests` (raiz do monorepo)                                  |

`scons coverage` roda a mesma suíte com relatório de cobertura (`vectora/htmlcov/index.html` para o backend, `frontend/coverage/index.html` para o frontend).

---

## Stack de Tecnologia

### Backend

| Camada                | Tecnologia                                                                                                                                                                                |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Linguagem             | Python 3.13 / [uv](https://docs.astral.sh/uv/)                                                                                                                                            |
| Servidor              | FastAPI ≥0.138 + Uvicorn — serve API, SSE, WebSocket e a SPA (`StaticFiles`)                                                                                                              |
| Framework de agente   | [LangChain](https://langchain.com/) 1.3 + [LangGraph](https://langchain-ai.github.io/langgraph/) 1.2 + [deepagents](https://github.com/langchain-ai/deepagents) 0.6 (`create_deep_agent`) |
| Providers de LLM      | `langchain-google-genai`, `langchain-openai`, `langchain-anthropic`, `langchain-cohere`, `langchain-ollama`                                                                               |
| Banco vetorial        | [LanceDB](https://lancedb.github.io/lancedb/) (lite, default) / Qdrant (complete)                                                                                                         |
| Embeddings + rerank   | Cohere `embed-multilingual-v3.0` + `rerank-multilingual-v3.0`, com VoyageAI como alternativa                                                                                              |
| Busca web             | Tavily via `langchain-tavily`                                                                                                                                                             |
| Retrieval esparso     | `rank-bm25` (híbrido com busca vetorial densa)                                                                                                                                            |
| Context Graph         | `tree-sitter` (Python/JS/TS/Go/Rust/Java/C/C++/JSON) + `networkx` + `rapidfuzz`                                                                                                           |
| Persistência          | SQLite + `aiosqlite` (WAL) + LangGraph Checkpointer (Postgres via `asyncpg` no modo complete)                                                                                             |
| Cache/KV              | Redis (`redis[hiredis]`, `langchain-redis`) — modo complete                                                                                                                               |
| Terminal              | PTY via `pywinpty` (Windows) / `ptyprocess` (Unix)                                                                                                                                        |
| Protocolo de contexto | [MCP](https://modelcontextprotocol.io/) ≥1.28 via [FastMCP](https://github.com/jlowin/fastmcp), montado em `/mcp`                                                                         |
| Segurança             | `argon2-cffi` (senhas), `pyjwt`, `pynacl`, `pykeepass` (vault KeePassXC), `slowapi` (rate limit)                                                                                          |
| Interface CLI         | [Rich](https://rich.readthedocs.io/)                                                                                                                                                      |
| Build/Distribuição    | Nuitka (compila o backend em C) + PyInstaller (empacota) + Electron + `electron-builder`                                                                                                  |

### Frontend

| Camada             | Tecnologia                                                                                                                            |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| Bundler            | Vite 8 + TypeScript 6                                                                                                                 |
| Framework UI       | React 19                                                                                                                              |
| Routing            | TanStack Router (file-based, type-safe)                                                                                               |
| Data fetching      | TanStack Query                                                                                                                        |
| Estado             | Zustand (20 stores) + `useReducer` para estado local de UI                                                                            |
| Estilo             | Tailwind CSS 4 + Radix UI + shadcn/ui + `lucide-react`                                                                                |
| Editor             | Monaco Editor (`@monaco-editor/react`)                                                                                                |
| Terminal           | `@xterm/xterm` + addons (fit, web-links), tema dinâmico via CSS vars                                                                  |
| Janelas flutuantes | `react-rnd` (arquivos abertos como janelas redimensionáveis/arrastáveis)                                                              |
| Markdown           | `react-markdown` + `remark-gfm` + `react-syntax-highlighter`                                                                          |
| Forms + validação  | React Hook Form + Zod                                                                                                                 |
| i18n               | [Paraglide JS](https://inlang.com/m/gerre34r/library-inlang-paraglideJs) — `m()` de `@/lib/paraglide/messages`, sem strings hardcoded |
| PWA                | `vite-plugin-pwa` (manifest + service worker)                                                                                         |
| Testes             | Vitest + Testing Library (unit/componente) + Playwright (e2e)                                                                         |
| Lint               | oxlint (Oxc, Rust)                                                                                                                    |

---

## Configuração

Chaves de API vão em `~/.vectora/config.toml` (criado pelo `vectora config keys`) ou em um `.env` local:

```env
# Provedor LLM (detectado automaticamente pelas chaves disponíveis)
LLM_PROVIDER=google-genai
GOOGLE_API_KEY=sua_chave_aqui

# Obrigatório: embeddings e reranking RAG
COHERE_API_KEY=sua_chave_aqui

# Obrigatório: busca web e extração de URLs
TAVILY_API_KEY=sua_chave_aqui

# Opcional: rastreamento
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=sua_chave_aqui
```

---

## Licença

Software proprietário — código fechado. Consulte [SECURITY.md](./SECURITY.md) para a política de divulgação de vulnerabilidades e [CONTRIBUTING.md](./CONTRIBUTING.md) para o fluxo de contribuição.
