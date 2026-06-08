# <img src="assets/vectora.svg" width="32" height="32"> Vectora

**Vectora** é um assistente de IA self-hosted para equipes de desenvolvimento — roda inteiramente no seu servidor, integra como sub-agente em qualquer orquestrador compatível com MCP (Claude Code, Claude Desktop, extensões VS Code) e vem com um chat web multi-usuário completo.

No seu núcleo, o Vectora resolve o **problema do abismo de conhecimento**: os LLMs não conhecem sua base de código, sua documentação ou as versões mais recentes da sua stack. O Vectora preenche essa lacuna com RAG híbrido (BM25 + vetores densos + reranker Cohere) — você indexa seus documentos uma vez e toda interação com IA passa a ter contexto completo.

---

## Por que o Vectora?

- **Orchestrator + Agentes Especializados** — O Orchestrator é o agente LLM primário. Responde diretamente para consultas simples e delega com instruções explícitas para os especialistas (search, coder, RAG). Sem hops de roteamento desnecessários.
- **Pipeline RAG híbrido** — Cada recuperação roda BM25 + busca vetorial densa + reranker Cohere. O resultado flui de volta para o Orchestrator para síntese.
- **Mais de 20 ferramentas em 6 categorias** — Web search, busca vetorial, filesystem, terminal (PTY), artifacts, memória — sempre disponíveis.
- **Embeddings curados** — Resultados da busca web passam por um gate de curadoria (reranker Cohere + LLM judge) antes de serem indexados. Sua base de conhecimento nunca é contaminada.
- **Chat web multi-usuário** — Interface Next.js integrada com autenticação, RBAC, workspaces, terminal embarcado, visualizador de diff e painel de planos.
- **Memória persistente entre sessões** — Memória em SQLite com isolamento por usuário.
- **Infraestrutura zero no modo lite** — SQLite + LanceDB. Sem Docker ou Postgres para uso local ou times pequenos.
- **Multi-LLM** — Google Gemini (plano gratuito), Cohere, OpenAI, Anthropic, ou Ollama (totalmente local).

---

## Arquitetura

### Orchestrator + Workers

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

## Início rápido (a partir do código fonte)

```bash
git clone https://github.com/brunosrz/vectora.git
cd vectora

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
```

---

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
```

Servidor MCP remoto via SSE:

```json
{
  "mcpServers": {
    "Vectora": {
      "url": "https://vectora.seudominio.com/mcp/sse"
    }
  }
}
```

---

## Build (SCons)

O sistema de build usa [SCons](https://scons.org/), incluído como
dependência de dev. Funciona direto no PowerShell, cmd, bash ou zsh —
sem dependência de sintaxe shell específica.

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
```

---

## Referência de Ferramentas

| Categoria     | Ferramentas                                                                                                 |
| ------------- | ----------------------------------------------------------------------------------------------------------- |
| **Web**       | `web_search`, `web_fetch`, `web_crawl`, `web_map`, `web_research`, `web_get_research`                       |
| **RAG**       | `vector_search`, `embedding`, `ingest_docs`, `manage_retriever`                                             |
| **Arquivos**  | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal`                                      |
| **Artifacts** | `create_artifact`                                                                                           |
| **Memória**   | `save_memory`, `get_memory`, `delete_memory`                                                                |
| **Git**       | `git_status`, `git_log`, `git_diff`, `git_branch`, `git_checkout`, `git_commit`, `git_push`, `gh_pr_create` |

---

## Stack de Tecnologia

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

Proprietária. Consulte o arquivo [LICENSE](./LICENSE).
