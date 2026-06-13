# Vectora — Por Trás da Cortina

> **Privado.** Este documento responde "o que move o Vectora": cada
> dependência, onde mora no código, e por que está lá. Use como
> referência interna quando alguém perguntar "como vocês fazem X?".

Tudo aqui foi extraído de `pyproject.toml` + `chat/package.json` em
junho/2026. Caminhos referenciam `src/...` (backend Python) e
`chat/components/...` (chat web TypeScript).

---

## 1. Servidor (Python 3.13+)

| Ingrediente           | Onde mora                          | Para quê                                                           |
| --------------------- | ---------------------------------- | ------------------------------------------------------------------ |
| **FastAPI + Uvicorn** | `src/api/server.py`                | servidor HTTP/SSE/WebSocket; serve a SPA Vite via `StaticFiles`    |
| **Pydantic v2**       | `src/types/*`                      | schemas tipados — mensagens, threads, attachments, eventos SSE     |
| **Pydantic-Settings** | `src/settings.py`                  | hierarquia `defaults.env` → `.env` → `~/.vectora/.env`; falha cedo |
| **httpx**             | `src/services/*`                   | cliente HTTP async (chamadas a LLMs, web tools, license server)    |
| **trio**              | dep transitiva de `asyncssh`/`mcp` | não usamos diretamente; só pra compatibilidade dos SDKs            |

## 2. Agente (LangChain / LangGraph)

| Ingrediente                     | Onde                                                                 | Para quê                                                                                                                                                                       |
| ------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **LangChain core**              | `src/agents/*`, `src/services/utils.py`                              | abstração de `BaseTool`, `BaseMessage`, `BaseChatModel`                                                                                                                        |
| **LangGraph**                   | `src/services/agent_factory.py`                                      | grafo orchestrator → coder/search/rag + HITL via `interrupt()`                                                                                                                 |
| **langgraph-checkpoint-sqlite** | `src/services/checkpoint.py`                                         | persiste estado do grafo por thread em `~/.vectora/data/vectora.db`                                                                                                            |
| **langchain-cohere**            | `src/services/utils.py`, `src/tools/rag.py`                          | `CohereEmbeddings` (RAG, memórias) + `CohereRerank` (re-ranking)                                                                                                               |
| **langchain-ollama**            | `src/services/utils.py`                                              | provider local sem custo                                                                                                                                                       |
| **langchain-tavily**            | `src/tools/web.py`                                                   | busca web + extração de conteúdo de URLs                                                                                                                                       |
| **langchain-mcp-adapters**      | `src/services/plugins.py`                                            | adapta servidores MCP de terceiros como `BaseTool` do agente                                                                                                                   |
| **langchain-text-splitters**    | `src/services/background.py`                                         | chunking de documentos para o RAG                                                                                                                                              |
| **langchain-community**         | **dep instalada, 0 imports hoje** (potencial subutilizado — ver §21) | catálogo **oficial** de conectores 1st-party da LangChain: 100+ document loaders, vector stores, chat histories, retrievers, caches, tools utilitárias                         |
| **deepagents**                  | **dep instalada, 0 imports hoje**                                    | Bloco E entregou TUI textual + `agent_factory` próprio, mas a migração para `create_deep_agent` ficou parcial (E2 marcado ⏳ na auditoria do `deep-engine.md`); reabre em DE-1 |
| **tiktoken**                    | `src/services/text.py`                                               | conta tokens para janelas de contexto, custo, e truncamento                                                                                                                    |

> **LLMs específicos** (Google, OpenAI, Anthropic): hoje o `load_llm()`
> em `src/services/utils.py` usa `init_chat_model` da langchain — não
> precisamos de SDK por provider porque o `init_chat_model` decide por
> string. Bloco F15 vai migrar para SDKs oficiais (`langchain-google-genai`,
> `langchain-openai`, `langchain-anthropic`) para ganhar prompt caching
> e parsers ReAct nativos.

## 3. RAG (Retrieval-Augmented Generation)

Como o RAG funciona, ingrediente por ingrediente:

| Ingrediente          | Onde                                             | Função                                                              |
| -------------------- | ------------------------------------------------ | ------------------------------------------------------------------- |
| **LanceDB**          | `src/tools/rag.py`, `src/services/background.py` | vector store local (embedded, sem servidor); arquivos em `lancedb/` |
| **pyarrow**          | `src/services/background.py`                     | formato colunar que o LanceDB consome para upserts em batch         |
| **rank-bm25**        | `src/nodes/rag_subgraph.py`                      | retrieval esparso (BM25) que combina com o denso para hybrid search |
| **CohereEmbeddings** | (via `langchain-cohere`)                         | `embed-multilingual-v3.0` (1024-dim) — único embedder do projeto    |
| **CohereRerank**     | `src/services/utils.py`                          | re-rank dos top-K após retrieval; eleva precisão @ 5                |

Fluxo: `expand_query → hybrid_retrieve (LanceDB + BM25) → decide → rerank
→ inject_context`. Multi-query expansion via LLM. Score baixo → cai para
busca web (Tavily) como fallback.

## 4. MCP (Model Context Protocol)

| Ingrediente                      | Onde                                          | Função                                                                                                                                                                            |
| -------------------------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **mcp** (SDK oficial)            | (transporte e tipos)                          | tipos, transports stdio/SSE, runtime do servidor MCP                                                                                                                              |
| **`mcp.server.fastmcp.FastMCP`** | `src/mcp/server.py:37` (`mcp = FastMCP(...)`) | wrapper de alto nível (decorators `@mcp.tool()`); converte funções Python em tool definitions MCP automaticamente. Faz parte do pacote `mcp>=1.27.1` — **não** é uma dep separada |
| **langchain-mcp-adapters**       | `src/services/plugins.py`                     | Vectora **como cliente** MCP (consome outros servidores MCP como tools)                                                                                                           |

O Vectora pode ser **invocado pelo Claude Desktop** (Vectora como tool MCP
via FastMCP em stdio/SSE) ou pode **chamar outros servidores MCP**
(plugins MCP por usuário virando `BaseTool` do agente).

## 5. Terminal (PTY persistente)

| Camada          | Ingrediente                                                          | Onde                                             |
| --------------- | -------------------------------------------------------------------- | ------------------------------------------------ |
| Backend Unix    | **ptyprocess**                                                       | `src/services/pty_session.py`                    |
| Backend Windows | **pywinpty**                                                         | (mesmo arquivo, `sys_platform` switch)           |
| Frontend chat   | **@xterm/xterm** + **@xterm/addon-fit** + **@xterm/addon-web-links** | `chat/components/terminal/xterm-view.tsx`        |
| Frontend TUI    | **textual.widgets.RichLog** (planejado em SX-TUI-3)                  | `src/ui/components/workbench_panel.py` (a criar) |
| Transporte      | **WebSocket nativo do FastAPI**                                      | `src/api/handlers/terminal.py`                   |

> **Por que WebSocket direto** (sem proxy Hono): o `pnpm dev` Hono não
> faz upgrade de WebSocket. O `xterm-view.tsx` fala direto com
> `ws://${VECTORA_API_URL}/vectora.terminal.v1/ws?...&token=`. Cookies
> httpOnly não viajam em WS cross-origin → obtemos token via
> `GET /auth/ws-token` e passamos na query.

## 6. File System + Editor

| Operação           | Ingrediente                                                                                | Onde                                                                         |
| ------------------ | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Ler arquivo        | `pathlib.Path.read_text/bytes`                                                             | `src/tools/fs.py::file_read`                                                 |
| Escrever (atomic)  | `Path.write_text` + `rename`                                                               | `src/tools/fs.py::file_write` / `file_edit`                                  |
| Mover para lixeira | **send2trash**                                                                             | `src/api/handlers/workspaces.py:1138` (DELETE de arquivo)                    |
| Grep               | (Python puro hoje; ripgrep no SX-FS-6)                                                     | `src/tools/fs.py::grep`                                                      |
| Anti-traversal     | helper `resolve_within_workspace`                                                          | `src/services/security.py`                                                   |
| Tree (UI)          | endpoint `GET /workspaces/{id}/tree`                                                       | `chat/components/workbench/tabs/files-tab.tsx`                               |
| **Editor inline**  | `<textarea>` puro (sem Monaco, sem CodeMirror)                                             | planejado em SX-FS-1 com ETag (`expected_sha256`)                            |
| Preview PDF        | **pdfjs-dist**                                                                             | `chat/components/chat/features/file-preview-grid.tsx` (1ª página, thumbnail) |
| Preview markdown   | **react-markdown** + **remark-gfm** + **react-syntax-highlighter** (Prism + `vscDarkPlus`) | `chat/components/chat/message-item.tsx`                                      |

> **Por que não Monaco/CodeMirror**: peso. Monaco ~300KB minified;
> CodeMirror ~100KB. Para o uso atual (edição esporádica, ler-mais-que-escrever),
> `<textarea>` monospace + syntax highlight via Prism resolve. Promover
> para CodeMirror só se houver demanda real (SX-FS-1 deixa porta aberta).

## 7. Diff

Apenas Git mesmo. Sem `diff-match-patch`, sem `jsdiff`.

| Camada              | Ingrediente                                    | Onde                                                |
| ------------------- | ---------------------------------------------- | --------------------------------------------------- |
| Geração             | **GitPython** (`Repo.git.diff(...)`)           | `src/tools/git.py::git_diff`                        |
| Parsing             | parser custom de hunks unified                 | `src/api/handlers/workspaces.py` (`/git/diff/file`) |
| Render web          | componente custom + `react-syntax-highlighter` | `chat/components/workbench/tabs/diff-tab.tsx`       |
| Render TUI          | `DiffWidget` (Textual `Static` + Rich)         | `src/ui/widgets/diff.py`                            |
| Diff inline em chat | HITL preview                                   | `chat/components/chat/features/hitl-panel.tsx`      |

## 8. Git (operações)

| Ingrediente                   | Onde               | Função                                                                                   |
| ----------------------------- | ------------------ | ---------------------------------------------------------------------------------------- |
| **GitPython** (`git>=3.1.50`) | `src/tools/git.py` | 11 tools: status, log, diff, branch, checkout, commit, push, pull, stash, worktree, init |
| **gh CLI** via subprocess     | `src/tools/gh.py`  | PRs, issues, reviews, releases — confia no `gh auth` do user                             |

## 9. SSH / Workspaces remotos

| Ingrediente                          | Onde                                  | Função                                             |
| ------------------------------------ | ------------------------------------- | -------------------------------------------------- |
| **asyncssh**                         | `src/services/transport/ssh.py`       | conexão async + auth por chave; pool por workspace |
| `gh codespace ssh -c <name>` wrapper | `src/services/transport/codespace.py` | GitHub Codespaces via tunneling                    |

## 10. Envs (variáveis de ambiente)

| Camada                | Ingrediente                                | Onde                                                       |
| --------------------- | ------------------------------------------ | ---------------------------------------------------------- |
| Leitura de `.env`     | **python-dotenv**                          | `src/settings.py`                                          |
| Validação + tipagem   | **Pydantic-Settings**                      | `src/settings.py::Settings`                                |
| Overrides por usuário | coluna `users.env_overrides_json` (SQLite) | `src/services/auth.py`                                     |
| API CRUD              | `GET/POST/DELETE /auth/envs`               | `src/api/handlers/auth.py`                                 |
| UI                    | aba "Envs" mascarando o valor (`••••••••`) | `chat/components/layout/settings-dialog/tabs/envs-tab.tsx` |

**Hierarquia em runtime**: `system_env ∪ user.env_overrides` (user vence).
Logs nunca printam o valor — só o KEY.

## 11. Auth + Segurança (servidor)

| Ingrediente                      | Função                                                                                     |
| -------------------------------- | ------------------------------------------------------------------------------------------ |
| **argon2-cffi**                  | hash de senhas (Argon2id, defaults da `argon2.PasswordHasher`)                             |
| **python-jose[cryptography]**    | JWT HS256 — access token 15min, refresh token opaco 7d rotacionado                         |
| **slowapi**                      | rate limit (sliding window): 5/min `/auth/signin`, 60/min `StreamChat`, etc.               |
| **keyring** (OS)                 | guarda token de sessão do CLI no Credential Manager / Keychain / Secret Service            |
| **pynacl**                       | fallback de encriptação simétrica (XSalsa20-Poly1305) quando keyring/keepass indisponíveis |
| cookies httpOnly + SameSite=Lax  | `Set-Cookie: vectora_access; HttpOnly; SameSite=Lax`                                       |
| `Authorization: Bearer` fallback | quando cookies não estão disponíveis (CLI, API clients)                                    |
| `Depends(get_current_user)`      | default em todos os handlers; whitelist explícita para `/auth/*`, `/health`, `/license/*`  |
| Audit log                        | tabela `audit` (signup, signin, change_password, tool_call destrutivo, …)                  |

## 12. Vault de secrets (KeePassXC nativo)

| Ingrediente     | Onde                                                                            | Função                                                    |
| --------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------- |
| **pykeepass**   | `src/services/secrets/keepass.py`                                               | abre/lê/escreve arquivos `.kdbx` com AES-256              |
| Layout          | `~/.vectora/secrets/system.kdbx` + `~/.vectora/secrets/users/<user_id>.kdbx`    | um vault por usuário                                      |
| Master key      | derivada via **PBKDF2-SHA256** (200k iter, salt=`user_id`) do password de login | sem master extra para o user — vault destrava com o login |
| Compatibilidade | KeePassXC (desktop) · KeePass2Android · Strongbox (iOS)                         | auditoria offline em qualquer cliente padrão              |

## 13. Criptografia ponta-a-ponta (a verdade nua e crua)

**Não temos E2E no sentido SaaS clássico.** Vou explicar exatamente o que
temos e por quê.

### O que protegemos

- **Em trânsito (browser ↔ servidor)**: TLS via nginx/cloudflared/tunnel
  é responsabilidade do deploy. O Vectora **não termina TLS sozinho** —
  recomendamos reverse proxy. Cookies entram com `Secure` quando atrás
  de TLS.
- **Em trânsito (Electron ↔ backend local)**: HTTP em `127.0.0.1` na
  mesma máquina. Não há "rede" entre eles. O OS isola por processo.
- **Em repouso (no servidor)**:
  - Senhas: Argon2id hash (não-reversível).
  - Secrets do usuário: AES-256 dentro do `.kdbx` por usuário.
  - LLM API keys: dentro do `.kdbx` ou em `users.env_overrides_json`
    mascarado (não recomendado, mas suportado).
  - JWT secret: arquivo `~/.vectora/auth.key` com permissão `0600`.

### O que NÃO protegemos

- **Conteúdo das conversas em repouso**: o checkpointer SQLite do
  LangGraph guarda mensagens em **claro**. Quem tem acesso ao disco do
  servidor lê. Mitigação: o servidor é **do próprio usuário** (self-hosted)
  ou de uma empresa que confia no operador.
- **Conteúdo no servidor durante processamento**: o servidor precisa do
  texto cru para chamar o LLM e indexar no RAG. Não há como
  processar conteúdo cifrado sem comprometer funcionalidade
  (homomorfismo é inviável para LLMs hoje).

### Por que isso é OK

Vectora é **self-hosted**. O argumento de venda é:
**seus dados ficam no seu servidor**. E2E faz sentido quando você
não confia no provedor (modelo SaaS). Quando você **é** o provedor
(VPS própria, máquina pessoal, servidor da empresa), E2E vira teatro
criptográfico — o servidor precisa ver os dados para fazer o trabalho.

> Se um usuário acessa Vectora hospedado na VPS dele a partir de casa:
> os dados são protegidos por TLS no caminho, hash forte de senha,
> JWT assinado, vault AES-256 para secrets. **Não** há criptografia
> tal que o operador da VPS (= ele mesmo) não consiga ler suas próprias
> conversas. Esse não é o threat model.

## 14. Chat web (TypeScript)

| Camada                   | Ingrediente                                                                                                                     | Função                                                                |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Bundler                  | **Vite 8** + **@vitejs/plugin-react**                                                                                           | dev server <300ms HMR + build de SPA                                  |
| PWA                      | **vite-plugin-pwa**                                                                                                             | service worker, manifest, cache-first shell                           |
| Linguagem                | **TypeScript 6**                                                                                                                | tipagem estrita                                                       |
| Framework UI             | **React 19**                                                                                                                    | base                                                                  |
| Routing                  | **@tanstack/react-router** + **@tanstack/router-plugin**                                                                        | file-based, type-safe, code-splitting automático                      |
| Data fetching            | **@tanstack/react-query**                                                                                                       | cache stale-while-revalidate, on-focus refetch                        |
| Lista virtualizada       | **@tanstack/react-virtual**                                                                                                     | message list com 500+ mensagens sem freeze                            |
| State                    | **zustand** + middleware `persist`                                                                                              | stores por feature (auth, workspaces, threads, workbench, settings)   |
| Estilo                   | **tailwindcss 4** + **@tailwindcss/typography** + **tailwindcss-animate** + **tw-animate-css** + **autoprefixer** + **postcss** | utility-first, atomic                                                 |
| Primitivos UI            | ~25 **@radix-ui/react-** packages                                                                                               | dialog, dropdown, popover, select, slider, tabs, toast, tooltip, etc. |
| Componentes (shadcn/ui)  | `chat/components/ui/*.tsx`                                                                                                      | wrappers tipados sobre Radix, copiados (não NPM)                      |
| Ícones                   | **lucide-react**                                                                                                                | ~1.3k ícones SVG tree-shakeable                                       |
| Fonte                    | **geist**                                                                                                                       | Vercel Geist Sans + Mono                                              |
| Toast                    | **sonner**                                                                                                                      | sistema central de feedback (UX-7)                                    |
| Command palette          | **cmdk**                                                                                                                        | base para ⌘K (UX-48)                                                  |
| Carousel                 | **embla-carousel-react**                                                                                                        | ainda não usado; reservado para showcase                              |
| Drawer mobile            | **vaul**                                                                                                                        | bottom sheet iOS-style                                                |
| OTP input                | **input-otp**                                                                                                                   | reservado para 2FA futuro                                             |
| Day picker               | **react-day-picker**                                                                                                            | calendário para filtros de threads                                    |
| Resizable splits         | **react-resizable-panels**                                                                                                      | divisórias arrastáveis (chat + workbench)                             |
| Markdown                 | **react-markdown** + **remark-gfm**                                                                                             | GFM (tables, task lists, autolinks)                                   |
| Syntax highlight         | **react-syntax-highlighter** (Prism)                                                                                            | tema `vscDarkPlus`                                                    |
| Forms                    | **react-hook-form** + **@hookform/resolvers**                                                                                   | controle de form sem re-render                                        |
| Validação                | **zod**                                                                                                                         | schemas do form + parse de payloads SSE                               |
| Charts                   | **recharts**                                                                                                                    | reservado para Settings → Admin → Sistema (métricas)                  |
| Datas                    | **date-fns**                                                                                                                    | formatação locale-aware                                               |
| Cookies                  | **js-cookie**                                                                                                                   | leitura no client (cookies httpOnly do server não são acessíveis)     |
| Tema (light/dark/system) | **next-themes**                                                                                                                 | persistência + system-aware                                           |
| Class helpers            | **clsx** + **tailwind-merge** + **class-variance-authority**                                                                    | merge de className idiomático para Tailwind                           |
| PDF preview              | **pdfjs-dist**                                                                                                                  | 1ª página como thumbnail no upload                                    |
| Terminal                 | **@xterm/xterm** + addons                                                                                                       | já citado em §5                                                       |

## 15. TUI textual (terminal nativo)

| Ingrediente        | Onde                                | Função                                                                |
| ------------------ | ----------------------------------- | --------------------------------------------------------------------- |
| **textual**        | `src/ui/app.py`, `src/ui/widgets/*` | framework declarativo Python para TUIs ricas                          |
| **rich**           | dep do `textual`; também direto     | rendering colorido inline (`[bold]...[/]`)                            |
| **prompt-toolkit** | (legado do CLI rich antigo)         | candidato a remover após SX-TUI-1 (a TUI nova usa só `textual.Input`) |

## 16. Persistência local (SQLite)

| Ingrediente                     | Para quê                                                      |
| ------------------------------- | ------------------------------------------------------------- |
| **aiosqlite**                   | driver async em `src/services/{auth,session,queue,tracer}.py` |
| **SQLAlchemy 2.0**              | usado em fronts isoladas; maioria do código fala SQL puro     |
| **langgraph-checkpoint-sqlite** | persiste checkpoints do grafo por thread                      |

Bancos: `~/.vectora/data/vectora.db` (auth, sessions, audit, threads),
`~/.vectora/data/embedding_queue.db` (fila de indexação),
`~/.vectora/data/traces.db` (observabilidade).

## 17. Build / Distribuição

| Ingrediente                                  | Função                                                                                                      |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **Nuitka**                                   | compila o entrypoint `src/launcher.py` em executável **onefile** com SPA Vite embutida (`chat_static/`)     |
| **scons**                                    | task runner (`SConstruct`): `dev`, `build-chat`, `build-nuitka`, `release-{win,mac,linux}`, `tests`, `lint` |
| **electron-builder** + **electron-updater**  | wrap o binário Nuitka em `.msi`/`.dmg`/`.AppImage`/`.deb`/`.rpm`                                            |
| **Cloudflare Workers** (no `update-server/`) | serve `latest.yml` para electron-updater com phased rollout                                                 |

## 18. Qualidade

| Ingrediente                     | Função                                                                                                             |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **ruff**                        | lint + format Python (substitui flake8 + black + isort)                                                            |
| **ty** (Astral)                 | type checker Python — mais rápido que pyright, mesmo padrão                                                        |
| **mypy** + **pyright**          | fallback / segunda opinião                                                                                         |
| **bandit**                      | security scan Python (SQL injection, weak crypto, hardcoded secrets)                                               |
| **oxlint** (Oxc)                | lint TypeScript escrito em Rust (~50× mais rápido que ESLint)                                                      |
| **typescript** (`tsc --noEmit`) | type check                                                                                                         |
| **vitest**                      | testes do chat (mais rápido e DX melhor que jest)                                                                  |
| **pytest** + add-ons            | testes Python: `pytest-asyncio` · `pytest-cov` · `pytest-timeout` (120s) · `pytest-rerunfailures` · `pytest-order` |
| **coverage**                    | report HTML em `htmlcov/`                                                                                          |

## 19. Pacotes secundários / utilitários

| Ingrediente  | Função                                               |
| ------------ | ---------------------------------------------------- |
| **pandas**   | manipulação tabular em alguns nós de RAG e em testes |
| **pathspec** | parsing de `.gitignore` em ferramentas de tree/grep  |

## 20. Dependências fantasma (alvos de limpeza)

Listadas no `pyproject.toml` mas **sem nenhum `import` no `src/`** (grep
limpo em junho/2026):

- `dotfiles`
- `ast-serialize`
- `librt`

Provavelmente sobraram de experimentações abandonadas. Removê-las
reduz vector de typo-squatting + 3 deps de menos para o uv resolver.

> **Não confundir** com `langchain-community` e `deepagents`, que também
> estão sem imports hoje mas **não são fantasma** — são bibliotecas
> oficiais legítimas cuja adoção foi planejada e ainda não foi
> implementada. Ver §21 (catálogo community) e `deep-engine.md` DE-1
> (migração para `create_deep_agent`).

---

## 21. Catálogo `langchain-community` — o que dá pra adotar

`langchain-community` é o **pacote oficial 1st-party** da LangChain com
100+ integrações pequenas (chat histories, document loaders, chat
loaders, vector stores extras, retrievers, caches, tools utilitárias).
Hoje a dep está instalada **e não usamos nada** — não é fantasma, é
subutilização.

> **Regra de adoção**: quando um integrante específico já tem pacote
> dedicado (ex.: `langchain-cohere`, `langchain-tavily`, `langchain-qdrant`),
> use o dedicado. Para o resto, `langchain-community` é a casa correta.

### 21.1 Chat loaders — habilita ingestão de conversas externas como contexto

Permite o user exportar histórico de outros apps e jogar no RAG para o
agente **aprender o estilo de conversa, contexto e relacionamentos**.

| Loader                        | Uso no Vectora                                                    |
| ----------------------------- | ----------------------------------------------------------------- |
| `WhatsAppChatLoader`          | user exporta chat (.zip) → indexa no RAG → agente lembra contexto |
| `TelegramChatLoader`          | idem para Telegram (exportação JSON)                              |
| `SlackChatLoader`             | export de canal/DM → ingestão                                     |
| `DiscordChatLoader`           | export de canal                                                   |
| `IMessageChatLoader`          | `chat.db` do macOS                                                |
| `FacebookMessengerChatLoader` | export Facebook                                                   |
| `LangSmithRunChatLoader`      | reusa traces do LangSmith como contexto                           |

Sub-bloco proposto: **SX-RAG-2 — Chat history ingestion** (entra junto
de SX-FS-\* na frente System Experience). Endpoint
`POST /v1/rag/import-chat {source, content}` aceita os formatos suportados.

### 21.2 Document loaders — fontes além de filesystem

Hoje só indexamos arquivos locais. Community traz:

| Loader                                    | Uso                                                |
| ----------------------------------------- | -------------------------------------------------- |
| `GitLoader`                               | indexa repo inteiro como Documents (1 por arquivo) |
| `GitHubIssuesLoader`                      | issues + PRs de um repo                            |
| `NotionDBLoader`, `NotionDirectoryLoader` | bancos Notion via API ou export local              |
| `ConfluenceLoader`                        | wikis corporativos                                 |
| `JiraLoader`                              | issues Jira                                        |
| `PyMuPDFLoader`                           | PDF extractor rápido (texto + metadata)            |
| `PyPDFLoader`, `PyPDFium2Loader`          | alternativas PDF                                   |
| `UnstructuredPDFLoader`                   | PDFs complexos (OCR, tabelas) via `unstructured`   |
| `RecursiveUrlLoader`, `SitemapLoader`     | crawl de docs públicas                             |
| `WebBaseLoader`, `BSHTMLLoader`           | scraping HTML                                      |
| `YoutubeLoader`                           | transcrição de vídeos (idiomas configuráveis)      |
| `RSSFeedLoader`, `SubstackLoader`         | feeds                                              |
| `GoogleDriveLoader`, `OneDriveLoader`     | cloud drives                                       |
| `S3FileLoader`, `S3DirectoryLoader`       | S3 buckets                                         |
| `GCSFileLoader`                           | Google Cloud Storage                               |
| `EverNoteLoader`, `ObsidianLoader`        | notas pessoais                                     |
| `BibtexLoader`                            | bibliografia acadêmica                             |
| `CSVLoader`, `JSONLoader`                 | dados estruturados                                 |

Sub-bloco proposto: **SX-RAG-3 — Conector zoo** com gates de
configuração (cada loader vira opção no `POST /v1/rag/ingest` quando o
user tiver as credenciais correspondentes no vault).

### 21.3 Chat message histories — alternativa exportável ao checkpointer

Checkpointer LangGraph guarda **o estado do grafo inteiro** (tools,
todos, files, etc). Para um "histórico de mensagens limpo, exportável,
auditável independente do agente", `langchain-community` tem:

| Backend                          | Quando usar                              |
| -------------------------------- | ---------------------------------------- |
| `SQLChatMessageHistory`          | mesmo SQLite que usamos hoje (modo lite) |
| `PostgresChatMessageHistory`     | Postgres (Bloco F completo)              |
| `RedisChatMessageHistory`        | quando G estiver montado                 |
| `MongoDBChatMessageHistory`      | clientes Mongo enterprise                |
| `FileChatMessageHistory`         | dev/debug; 1 arquivo JSON por thread     |
| `DynamoDBChatMessageHistory`     | deploy AWS                               |
| `UpstashRedisChatMessageHistory` | serverless Redis                         |

**Uso prático**: feature "exportar conversa" (B5/I2) fica trivial —
instancia `SQLChatMessageHistory(session_id=thread_id, connection=...)`
e itera. Sem precisar deserializar o checkpoint.

### 21.4 Tools utilitárias — sem precisar de API key

| Tool                                                 | Uso                                                 |
| ---------------------------------------------------- | --------------------------------------------------- |
| `DuckDuckGoSearchRun` / `DuckDuckGoSearchAPIWrapper` | fallback **gratuito** quando o user não tem Tavily  |
| `WikipediaQueryRun`                                  | conhecimento factual zero-config                    |
| `ArxivQueryRun`                                      | papers acadêmicos                                   |
| `PubMedQueryRun`                                     | medicina                                            |
| `StackExchangeAPIWrapper`                            | Q&A técnico                                         |
| `WolframAlphaQueryRun`                               | computação simbólica + dados (free tier limitado)   |
| `OpenWeatherMapAPIWrapper`                           | clima                                               |
| `YouTubeSearchTool`                                  | busca de vídeos                                     |
| `RequestsGetTool` / `RequestsPostTool` etc           | HTTP genérico tipado                                |
| `GraphQLAPIWrapper`                                  | GraphQL para queries arbitrárias                    |
| `ShellTool` / `BashProcess`                          | fallback do terminal (não usar — temos PTY próprio) |

**Plus tier zero-config** = `DuckDuckGo + Wikipedia + Arxiv` instalados
de fábrica sem precisar configurar nenhum provider. Substitui hoje
`web_search` precisar de `TAVILY_API_KEY`.

### 21.5 Toolkits — pacotes de ferramentas relacionadas

| Toolkit                       | Uso                                                                                                                           |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `SQLDatabaseToolkit`          | agente conversa com SQLite/Postgres/MySQL/MSSQL do user — **power feature**                                                   |
| `GmailToolkit`, `O365Toolkit` | ler/enviar email/calendário (OAuth pelo vault)                                                                                |
| `JiraToolkit`                 | criar/comentar issues                                                                                                         |
| `FileManagementToolkit`       | read/write/list/copy/move/delete (referência; não substitui `src/tools/fs.py` por falta de anti-traversal e permission rules) |

`SQLDatabaseToolkit` é particularmente forte: user conecta seu Postgres,
o agente lê schema automaticamente, gera SQL com validação,
sanitiza e executa. Caso de uso "BI conversacional" pronto.

### 21.6 Retrievers — formaliza nosso hybrid

Hoje fazemos retrieval híbrido manual (LanceDB + BM25). Community tem
patterns canônicos:

| Retriever                              | Uso                                                                                   |
| -------------------------------------- | ------------------------------------------------------------------------------------- |
| `EnsembleRetriever`                    | **substituto canônico** do nosso hybrid manual — recebe N retrievers + pesos, faz RRF |
| `MultiQueryRetriever`                  | já implementamos manual no `rag_subgraph.py`; usar canônico                           |
| `ContextualCompressionRetriever`       | wrapper que aplica `CohereRerank` em cima de outro retriever                          |
| `ParentDocumentRetriever`              | chunks pequenos para retrieval + doc inteiro para o LLM                               |
| `SelfQueryRetriever`                   | LLM gera filtros estruturados a partir da query natural                               |
| `TimeWeightedVectorStoreRetriever`     | privilegia memórias recentes                                                          |
| `MultiVectorRetriever`                 | múltiplas representações por doc (summary + chunks + hypothetical)                    |
| `BM25Retriever`                        | wrapper canônico do `rank-bm25` que já usamos                                         |
| `WikipediaRetriever`, `ArxivRetriever` | retriever direto (não tool — pra usar em chains determinísticas)                      |

Sub-bloco proposto: **Refactor RAG-1** — substituir o pipeline manual
em `src/nodes/rag_subgraph.py` por `EnsembleRetriever` + `ContextualCompressionRetriever(CohereRerank)`. Mesmo comportamento, ~60% menos código.

### 21.7 Caches — local e distribuído

| Cache            | Uso                                                                                               |
| ---------------- | ------------------------------------------------------------------------------------------------- |
| `SQLiteCache`    | drop-in para LLM completion cache local (`set_llm_cache(...)`) — reduz custo em prompts repetidos |
| `LocalFileCache` | mesma ideia, formato arquivo                                                                      |
| `InMemoryCache`  | dev/testes                                                                                        |
| `RedisCache`     | distribuído (Bloco G)                                                                             |

Adoção imediata recomendada: `SQLiteCache` em
`~/.vectora/data/llm_cache.db` opt-in via setting. Bloco G migra para
Redis.

### 21.8 Embeddings — alternativas locais ao Cohere

| Embeddings              | Uso                                                        |
| ----------------------- | ---------------------------------------------------------- |
| `HuggingFaceEmbeddings` | modelos locais (BGE, MiniLM, e5) via sentence-transformers |
| `FastEmbedEmbeddings`   | implementação ONNX rápida da Qdrant                        |
| `OllamaEmbeddings`      | embeddings via Ollama (mesma instalação local)             |
| `LlamaCppEmbeddings`    | quantizado local                                           |
| `GPT4AllEmbeddings`     | modelos GPT4All                                            |

**Tier free**: trocar `CohereEmbeddings` por `FastEmbedEmbeddings(model="BAAI/bge-small-en-v1.5")` quando o user não tem `COHERE_API_KEY`. Sem custo, sem rede,
qualidade aceitável (~85% do Cohere multilingual em benchmarks PT-BR).

### 21.9 SQL utilities

| Utility                         | Uso                                                                                                             |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `SQLDatabase`                   | conector universal (SQLite/Postgres/MySQL/MSSQL/Oracle) com schema introspection — base do `SQLDatabaseToolkit` |
| `SQLDatabaseChain` (deprecated) | substituído pelo toolkit acima                                                                                  |

`SQLDatabase` é especialmente útil porque já temos SQLAlchemy 2.0 como
dep — conectar agente a "qualquer base SQL do user" custa ~20 linhas.

### 21.10 O que NÃO adotar do community

Para registro, deps que existem mas **não fazem sentido pro Vectora**:

- `Chroma`, `FAISS` — já temos LanceDB (melhor performance + multimodal).
- `OpenAIEmbeddings` (community) — preferimos Cohere multilingual.
- `LLMs` (TextCompletion) — deprecados pela LangChain.
- Chains legadas (`ConversationalRetrievalChain`, `LLMChain`,
  `RetrievalQA`) — substituídas por `create_agent` + middleware.

### 21.11 Roadmap de adoção (proposta)

| Prioridade     | Sub-bloco    | O que                                                                                              |
| -------------- | ------------ | -------------------------------------------------------------------------------------------------- |
| 1 (Bloco G)    | **GC-1**     | `SQLiteCache` opt-in para LLM completions                                                          |
| 2 (Bloco F)    | **FC-1**     | `SQLChatMessageHistory` paralelo ao checkpointer (export limpo)                                    |
| 3 (Bloco H)    | **HC-1**     | `EnsembleRetriever` + `ContextualCompressionRetriever(CohereRerank)` substitui pipeline RAG manual |
| 4 (SX-RAG-2)   | **SX-RAG-2** | Chat loaders (WhatsApp, Telegram, Slack, Discord, iMessage)                                        |
| 5 (SX-RAG-3)   | **SX-RAG-3** | Document loaders (GitLoader, NotionDBLoader, ConfluenceLoader, YoutubeLoader, RecursiveUrlLoader)  |
| 6 (Tools H6+)  | **HC-2**     | `DuckDuckGoSearchRun` como fallback gratuito do Tavily                                             |
| 7 (Tools H6+)  | **HC-3**     | `WikipediaQueryRun` + `ArxivQueryRun` + `StackExchangeAPIWrapper` zero-config                      |
| 8 (Bloco K?)   | **KC-1**     | `SQLDatabaseToolkit` — habilita "BI conversacional" como feature Pro                               |
| 9 (Tier free)  | **HC-4**     | `FastEmbedEmbeddings` fallback quando user não tem Cohere                                          |
| 10 (Bloco H6+) | **HC-5**     | `GmailToolkit` / `O365Toolkit` (junto com OAuth de B6)                                             |

---

## Apêndice — quando alguém perguntar…

### "Como vocês emulam o terminal?"

PTY real do OS (`ptyprocess` Unix / `pywinpty` Windows) ligado a um
WebSocket que fala com `xterm.js` no browser ou `RichLog` na TUI.
Sessão persistente — fecha a aba, reabre, comando ainda rodando.

### "E o file system no chat?"

Endpoints REST tipados (`GET /workspaces/{id}/tree`, `GET /file`,
`POST /fs/file`) consumidos por um `<Tree>` custom em React. Atomic
writes server-side. Anti-traversal por `resolve_within_workspace`.
Lixeira via `send2trash` (não `rm -rf`).

### "E o Diff? Só Git?"

Só Git. `GitPython` gera o diff unified, um parser nosso transforma em
hunks, e renderizamos com Tailwind classes (verde/vermelho) ou no
Textual com `Static` + cores Rich. Não usamos `diff-match-patch` nem
`jsdiff`.

### "Como abrimos e editamos arquivos?"

Read: `pathlib`. Write: `Path.write_text` + `os.replace` (atomic).
Edit (substituição cirúrgica): `file_edit` tool faz `find/replace`
com validação. Editor inline no chat: `<textarea>` monospace
(SX-FS-1 vai adicionar ETag para evitar overwrite concorrente).
Sem Monaco, sem CodeMirror — peso não justifica o uso atual.

### "Como salvamos as envs?"

Três camadas: `defaults.env` (in-package) → `.env` (project) →
`~/.vectora/.env` (user global). Por-usuário: coluna JSON
`users.env_overrides_json` no SQLite. Em runtime: merge das três

- overrides do user. Mascaradas na UI; nunca em logs. Pydantic-Settings
  valida tudo no boot — falha imediata em vez de NoneType mais tarde.

### "Como lidam com auth?"

- Senha: Argon2id (`argon2-cffi`).
- Sessão: JWT HS256 (`python-jose`) — access 15min, refresh 7d com rotação.
- Storage local do CLI: `keyring` do OS.
- Rate limit: `slowapi` por IP/user/email.
- Cookies httpOnly + SameSite=Lax + Secure (atrás de TLS).
- Audit log de tudo destrutivo.

### "Têm E2E encryption?"

Não no sentido SaaS clássico — e isso é proposital. O modelo é
self-hosted: o servidor é seu. O que temos:

- TLS no transporte (responsabilidade do deploy).
- Argon2id para senhas.
- AES-256 (`pykeepass`) para vault de secrets do user.
- Master key derivada via PBKDF2-SHA256 do password de login.
- JWT secret em arquivo `0600`.

O servidor precisa ver o conteúdo para chamar LLMs e indexar no RAG.
Quem opera o servidor (= você) tem acesso a tudo. Esse é o trade-off
do self-hosted — a alternativa é confiar num provedor SaaS.

### "Por que não monorepo via Turborepo / pnpm workspaces?"

`chat/` tem `pnpm-workspace.yaml` + `turbo.json` legados do fork
inicial. Hoje rodamos `pnpm --dir chat ...` direto. Limpar isso é
chore de housekeeping baixa prioridade.

### "Por que TanStack Router em vez de React Router?"

Type-safe routing por arquivo, integração nativa com TanStack Query,
e zero ginástica para code-splitting. Bloco D documentou a migração de
Next.js para Vite + TanStack para eliminar o sidecar Node.js do
instalador desktop.
