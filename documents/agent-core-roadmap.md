# Vectora — Núcleo do Agente: Stack, Arquitetura e Roadmap

> Documento canônico consolidado: stack técnico, auditoria da arquitetura
> de agente (deep-agent) e inventário de tools nativas — antes três
> arquivos separados (referência de stack, auditoria de migração deep-agent
> e inventário de tools), unificados aqui.
>
> Contexto atual (ver `history.md` — "O Vectora hoje"): o agente já roda
> sobre `create_deep_agent` (LangGraph + deepagents) como arquitetura
> canônica — não existe mais um "VCR" neural próprio nem um orchestrator
> manual por nós como caminho principal. As seções abaixo auditam o que
> dessa migração já está de fato na superfície canônica do harness versus
> o que ainda é implementação artesanal equivalente em comportamento.

---

## Vectora — Por Trás da Cortina

> **Privado.** Este documento responde "o que move o Vectora": cada
> dependência, onde mora no código, e por que está lá. Use como
> referência interna quando alguém perguntar "como vocês fazem X?".

Tudo aqui foi extraído de `pyproject.toml` + `vectora/frontend/package.json` em
junho/2026. Caminhos referenciam `backend/...` (backend Python) e
`vectora/frontend/components/...` (chat web TypeScript).

---

#### 1. Servidor (Python 3.13+)

| Ingrediente           | Onde mora                          | Para quê                                                           |
| --------------------- | ---------------------------------- | ------------------------------------------------------------------ |
| **FastAPI + Uvicorn** | `backend/api/server.py`            | servidor HTTP/SSE/WebSocket; serve a SPA Vite via `StaticFiles`    |
| **Pydantic v2**       | `backend/types/*`                  | schemas tipados — mensagens, threads, attachments, eventos SSE     |
| **Pydantic-Settings** | `backend/settings.py`              | hierarquia `defaults.env` → `.env` → `~/.vectora/.env`; falha cedo |
| **httpx**             | `backend/services/*`               | cliente HTTP async (chamadas a LLMs, web tools, license server)    |
| **trio**              | dep transitiva de `asyncssh`/`mcp` | não usamos diretamente; só pra compatibilidade dos SDKs            |

#### 2. Agente (LangChain / LangGraph)

| Ingrediente                     | Onde                                                                 | Para quê                                                                                                                                                                              |
| ------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **LangChain core**              | `backend/agents/*`, `backend/services/utils.py`                      | abstração de `BaseTool`, `BaseMessage`, `BaseChatModel`                                                                                                                               |
| **LangGraph**                   | `backend/services/agent_factory.py`                                  | grafo orchestrator → coder/search/rag + HITL via `interrupt()`                                                                                                                        |
| **langgraph-checkpoint-sqlite** | `backend/services/checkpoint.py`                                     | persiste estado do grafo por thread em `~/.vectora/data/vectora.db`                                                                                                                   |
| **langchain-cohere**            | `backend/services/utils.py`, `backend/tools/rag.py`                  | `CohereEmbeddings` (RAG, memórias) + `CohereRerank` (re-ranking)                                                                                                                      |
| **langchain-ollama**            | `backend/services/utils.py`                                          | provider local sem custo                                                                                                                                                              |
| **langchain-tavily**            | `backend/tools/web.py`                                               | busca web + extração de conteúdo de URLs                                                                                                                                              |
| **langchain-mcp-adapters**      | `backend/services/plugins.py`                                        | adapta servidores MCP de terceiros como `BaseTool` do agente                                                                                                                          |
| **langchain-text-splitters**    | `backend/services/background.py`                                     | chunking de documentos para o RAG                                                                                                                                                     |
| **langchain-community**         | **dep instalada, 0 imports hoje** (potencial subutilizado — ver §21) | catálogo **oficial** de conectores 1st-party da LangChain: 100+ document loaders, vector stores, chat histories, retrievers, caches, tools utilitárias                                |
| **deepagents**                  | **dep instalada, 0 imports hoje**                                    | Bloco E entregou TUI textual + `agent_factory` próprio, mas a migração para `create_deep_agent` ficou parcial (E2 marcado ⏳ na auditoria do `agent-core-roadmap.md`); reabre em DE-1 |
| **tiktoken**                    | `backend/services/text.py`                                           | conta tokens para janelas de contexto, custo, e truncamento                                                                                                                           |

> **LLMs específicos** (Google, OpenAI, Anthropic): hoje o `load_llm()`
> em `backend/services/utils.py` usa `init_chat_model` da langchain — não
> precisamos de SDK por provider porque o `init_chat_model` decide por
> string. Bloco F15 vai migrar para SDKs oficiais (`langchain-google-genai`,
> `langchain-openai`, `langchain-anthropic`) para ganhar prompt caching
> e parsers ReAct nativos.

#### 3. RAG (Retrieval-Augmented Generation)

Como o RAG funciona, ingrediente por ingrediente:

| Ingrediente          | Onde                                                     | Função                                                              |
| -------------------- | -------------------------------------------------------- | ------------------------------------------------------------------- |
| **LanceDB**          | `backend/tools/rag.py`, `backend/services/background.py` | vector store local (embedded, sem servidor); arquivos em `lancedb/` |
| **pyarrow**          | `backend/services/background.py`                         | formato colunar que o LanceDB consome para upserts em batch         |
| **rank-bm25**        | `backend/nodes/rag_subgraph.py`                          | retrieval esparso (BM25) que combina com o denso para hybrid search |
| **CohereEmbeddings** | (via `langchain-cohere`)                                 | `embed-multilingual-v3.0` (1024-dim) — único embedder do projeto    |
| **CohereRerank**     | `backend/services/utils.py`                              | re-rank dos top-K após retrieval; eleva precisão @ 5                |

Fluxo: `expand_query → hybrid_retrieve (LanceDB + BM25) → decide → rerank
→ inject_context`. Multi-query expansion via LLM. Score baixo → cai para
busca web (Tavily) como fallback.

#### 4. MCP (Model Context Protocol)

| Ingrediente                      | Onde                                              | Função                                                                                                                                                                            |
| -------------------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **mcp** (SDK oficial)            | (transporte e tipos)                              | tipos, transports stdio/SSE, runtime do servidor MCP                                                                                                                              |
| **`mcp.server.fastmcp.FastMCP`** | `backend/mcp/server.py:37` (`mcp = FastMCP(...)`) | wrapper de alto nível (decorators `@mcp.tool()`); converte funções Python em tool definitions MCP automaticamente. Faz parte do pacote `mcp>=1.27.1` — **não** é uma dep separada |
| **langchain-mcp-adapters**       | `backend/services/plugins.py`                     | Vectora **como cliente** MCP (consome outros servidores MCP como tools)                                                                                                           |

O Vectora pode ser **invocado pelo Claude Desktop** (Vectora como tool MCP
via FastMCP em stdio/SSE) ou pode **chamar outros servidores MCP**
(plugins MCP por usuário virando `BaseTool` do agente).

#### 5. Terminal (PTY persistente)

| Camada          | Ingrediente                                                          | Onde                                                  |
| --------------- | -------------------------------------------------------------------- | ----------------------------------------------------- |
| Backend Unix    | **ptyprocess**                                                       | `backend/services/pty_session.py`                     |
| Backend Windows | **pywinpty**                                                         | (mesmo arquivo, `sys_platform` switch)                |
| Frontend chat   | **@xterm/xterm** + **@xterm/addon-fit** + **@xterm/addon-web-links** | `vectora/frontend/components/terminal/xterm-view.tsx` |
| Frontend TUI    | **textual.widgets.RichLog** (planejado em SX-TUI-3)                  | `backend/ui/components/workbench_panel.py` (a criar)  |
| Transporte      | **WebSocket nativo do FastAPI**                                      | `backend/api/handlers/terminal.py`                    |

> **Por que WebSocket direto** (sem proxy Hono): o `pnpm dev` Hono não
> faz upgrade de WebSocket. O `xterm-view.tsx` fala direto com
> `ws://${VECTORA_API_URL}/vectora.terminal.v1/ws?...&token=`. Cookies
> httpOnly não viajam em WS cross-origin → obtemos token via
> `GET /auth/ws-token` e passamos na query.

#### 6. File System + Editor

| Operação           | Ingrediente                                                                                | Onde                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Ler arquivo        | `pathlib.Path.read_text/bytes`                                                             | `backend/tools/fs.py::file_read`                                                         |
| Escrever (atomic)  | `Path.write_text` + `rename`                                                               | `backend/tools/fs.py::file_write` / `file_edit`                                          |
| Mover para lixeira | **send2trash**                                                                             | `backend/api/handlers/workspaces.py:1138` (DELETE de arquivo)                            |
| Grep               | (Python puro hoje; ripgrep no SX-FS-6)                                                     | `backend/tools/fs.py::grep`                                                              |
| Anti-traversal     | helper `resolve_within_workspace`                                                          | `backend/services/security.py`                                                           |
| Tree (UI)          | endpoint `GET /workspaces/{id}/tree`                                                       | `vectora/frontend/components/workbench/tabs/files-tab.tsx`                               |
| **Editor inline**  | `<textarea>` puro (sem Monaco, sem CodeMirror)                                             | planejado em SX-FS-1 com ETag (`expected_sha256`)                                        |
| Preview PDF        | **pdfjs-dist**                                                                             | `vectora/frontend/components/chat/features/file-preview-grid.tsx` (1ª página, thumbnail) |
| Preview markdown   | **react-markdown** + **remark-gfm** + **react-syntax-highlighter** (Prism + `vscDarkPlus`) | `vectora/frontend/components/chat/message-item.tsx`                                      |

> **Por que não Monaco/CodeMirror**: peso. Monaco ~300KB minified;
> CodeMirror ~100KB. Para o uso atual (edição esporádica, ler-mais-que-escrever),
> `<textarea>` monospace + syntax highlight via Prism resolve. Promover
> para CodeMirror só se houver demanda real (SX-FS-1 deixa porta aberta).

#### 7. Diff

Apenas Git mesmo. Sem `diff-match-patch`, sem `jsdiff`.

| Camada              | Ingrediente                                    | Onde                                                       |
| ------------------- | ---------------------------------------------- | ---------------------------------------------------------- |
| Geração             | **GitPython** (`Repo.git.diff(...)`)           | `backend/tools/git.py::git_diff`                           |
| Parsing             | parser custom de hunks unified                 | `backend/api/handlers/workspaces.py` (`/git/diff/file`)    |
| Render web          | componente custom + `react-syntax-highlighter` | `vectora/frontend/components/workbench/tabs/diff-tab.tsx`  |
| Render TUI          | `DiffWidget` (Textual `Static` + Rich)         | `backend/ui/widgets/diff.py`                               |
| Diff inline em chat | HITL preview                                   | `vectora/frontend/components/chat/features/hitl-panel.tsx` |

#### 8. Git (operações)

| Ingrediente                   | Onde                   | Função                                                                                   |
| ----------------------------- | ---------------------- | ---------------------------------------------------------------------------------------- |
| **GitPython** (`git>=3.1.50`) | `backend/tools/git.py` | 11 tools: status, log, diff, branch, checkout, commit, push, pull, stash, worktree, init |
| **gh CLI** via subprocess     | `backend/tools/gh.py`  | PRs, issues, reviews, releases — confia no `gh auth` do user                             |

#### 9. SSH / Workspaces remotos

| Ingrediente                          | Onde                                      | Função                                             |
| ------------------------------------ | ----------------------------------------- | -------------------------------------------------- |
| **asyncssh**                         | `backend/services/transport/ssh.py`       | conexão async + auth por chave; pool por workspace |
| `gh codespace ssh -c <name>` wrapper | `backend/services/transport/codespace.py` | GitHub Codespaces via tunneling                    |

#### 10. Envs (variáveis de ambiente)

| Camada                | Ingrediente                                | Onde                                                                   |
| --------------------- | ------------------------------------------ | ---------------------------------------------------------------------- |
| Leitura de `.env`     | **python-dotenv**                          | `backend/settings.py`                                                  |
| Validação + tipagem   | **Pydantic-Settings**                      | `backend/settings.py::Settings`                                        |
| Overrides por usuário | coluna `users.env_overrides_json` (SQLite) | `backend/services/auth.py`                                             |
| API CRUD              | `GET/POST/DELETE /auth/envs`               | `backend/api/handlers/auth.py`                                         |
| UI                    | aba "Envs" mascarando o valor (`••••••••`) | `vectora/frontend/components/layout/settings-dialog/tabs/envs-tab.tsx` |

**Hierarquia em runtime**: `system_env ∪ user.env_overrides` (user vence).
Logs nunca printam o valor — só o KEY.

#### 11. Auth + Segurança (servidor)

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

#### 12. Vault de secrets (KeePassXC nativo)

| Ingrediente     | Onde                                                                            | Função                                                    |
| --------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------- |
| **pykeepass**   | `backend/services/secrets/keepass.py`                                           | abre/lê/escreve arquivos `.kdbx` com AES-256              |
| Layout          | `~/.vectora/secrets/system.kdbx` + `~/.vectora/secrets/users/<user_id>.kdbx`    | um vault por usuário                                      |
| Master key      | derivada via **PBKDF2-SHA256** (200k iter, salt=`user_id`) do password de login | sem master extra para o user — vault destrava com o login |
| Compatibilidade | KeePassXC (desktop) · KeePass2Android · Strongbox (iOS)                         | auditoria offline em qualquer cliente padrão              |

#### 13. Criptografia ponta-a-ponta (a verdade nua e crua)

**Não temos E2E no sentido SaaS clássico.** Vou explicar exatamente o que
temos e por quê.

##### O que protegemos

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

##### O que NÃO protegemos

- **Conteúdo das conversas em repouso**: o checkpointer SQLite do
  LangGraph guarda mensagens em **claro**. Quem tem acesso ao disco do
  servidor lê. Mitigação: o servidor é **do próprio usuário** (self-hosted)
  ou de uma empresa que confia no operador.
- **Conteúdo no servidor durante processamento**: o servidor precisa do
  texto cru para chamar o LLM e indexar no RAG. Não há como
  processar conteúdo cifrado sem comprometer funcionalidade
  (homomorfismo é inviável para LLMs hoje).

##### Por que isso é OK

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

#### 14. Chat web (TypeScript)

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
| Componentes (shadcn/ui)  | `vectora/frontend/components/ui/*.tsx`                                                                                          | wrappers tipados sobre Radix, copiados (não NPM)                      |
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

#### 15. TUI textual (terminal nativo)

| Ingrediente        | Onde                                        | Função                                                                |
| ------------------ | ------------------------------------------- | --------------------------------------------------------------------- |
| **textual**        | `backend/ui/app.py`, `backend/ui/widgets/*` | framework declarativo Python para TUIs ricas                          |
| **rich**           | dep do `textual`; também direto             | rendering colorido inline (`[bold]...[/]`)                            |
| **prompt-toolkit** | (legado do CLI rich antigo)                 | candidato a remover após SX-TUI-1 (a TUI nova usa só `textual.Input`) |

#### 16. Persistência local (SQLite)

| Ingrediente                     | Para quê                                                          |
| ------------------------------- | ----------------------------------------------------------------- |
| **aiosqlite**                   | driver async em `backend/services/{auth,session,queue,tracer}.py` |
| **SQLAlchemy 2.0**              | usado em fronts isoladas; maioria do código fala SQL puro         |
| **langgraph-checkpoint-sqlite** | persiste checkpoints do grafo por thread                          |

Bancos: `~/.vectora/data/vectora.db` (auth, sessions, audit, threads),
`~/.vectora/data/embedding_queue.db` (fila de indexação),
`~/.vectora/data/traces.db` (observabilidade).

#### 17. Build / Distribuição

| Ingrediente                                  | Função                                                                                                      |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **Nuitka**                                   | compila o entrypoint `backend/launcher.py` em executável **onefile** com SPA Vite embutida (`chat_static/`) |
| **scons**                                    | task runner (`SConstruct`): `dev`, `build-chat`, `build-nuitka`, `release-{win,mac,linux}`, `tests`, `lint` |
| **electron-builder** + **electron-updater**  | wrap o binário Nuitka em `.msi`/`.dmg`/`.AppImage`/`.deb`/`.rpm`                                            |
| **Cloudflare Workers** (no `update-server/`) | serve `latest.yml` para electron-updater com phased rollout                                                 |

#### 18. Qualidade

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

#### 19. Pacotes secundários / utilitários

| Ingrediente  | Função                                               |
| ------------ | ---------------------------------------------------- |
| **pandas**   | manipulação tabular em alguns nós de RAG e em testes |
| **pathspec** | parsing de `.gitignore` em ferramentas de tree/grep  |

#### 20. Dependências fantasma (alvos de limpeza)

Listadas no `pyproject.toml` mas **sem nenhum `import` no `backend/`** (grep
limpo em junho/2026):

- `dotfiles`
- `ast-serialize`
- `librt`

Provavelmente sobraram de experimentações abandonadas. Removê-las
reduz vector de typo-squatting + 3 deps de menos para o uv resolver.

> **Não confundir** com `langchain-community` e `deepagents`, que também
> estão sem imports hoje mas **não são fantasma** — são bibliotecas
> oficiais legítimas cuja adoção foi planejada e ainda não foi
> implementada. Ver §21 (catálogo community) e `agent-core-roadmap.md` DE-1
> (migração para `create_deep_agent`).

---

#### 21. Catálogo `langchain-community` — o que dá pra adotar

`langchain-community` é o **pacote oficial 1st-party** da LangChain com
100+ integrações pequenas (chat histories, document loaders, chat
loaders, vector stores extras, retrievers, caches, tools utilitárias).
Hoje a dep está instalada **e não usamos nada** — não é fantasma, é
subutilização.

> **Regra de adoção**: quando um integrante específico já tem pacote
> dedicado (ex.: `langchain-cohere`, `langchain-tavily`, `langchain-qdrant`),
> use o dedicado. Para o resto, `langchain-community` é a casa correta.

##### 21.1 Chat loaders — habilita ingestão de conversas externas como contexto

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

##### 21.2 Document loaders — fontes além de filesystem

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

##### 21.3 Chat message histories — alternativa exportável ao checkpointer

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

##### 21.4 Tools utilitárias — sem precisar de API key

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

##### 21.5 Toolkits — pacotes de ferramentas relacionadas

| Toolkit                       | Uso                                                                                                                               |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `SQLDatabaseToolkit`          | agente conversa com SQLite/Postgres/MySQL/MSSQL do user — **power feature**                                                       |
| `GmailToolkit`, `O365Toolkit` | ler/enviar email/calendário (OAuth pelo vault)                                                                                    |
| `JiraToolkit`                 | criar/comentar issues                                                                                                             |
| `FileManagementToolkit`       | read/write/list/copy/move/delete (referência; não substitui `backend/tools/fs.py` por falta de anti-traversal e permission rules) |

`SQLDatabaseToolkit` é particularmente forte: user conecta seu Postgres,
o agente lê schema automaticamente, gera SQL com validação,
sanitiza e executa. Caso de uso "BI conversacional" pronto.

##### 21.6 Retrievers — formaliza nosso hybrid

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
em `backend/nodes/rag_subgraph.py` por `EnsembleRetriever` + `ContextualCompressionRetriever(CohereRerank)`. Mesmo comportamento, ~60% menos código.

##### 21.7 Caches — local e distribuído

| Cache            | Uso                                                                                               |
| ---------------- | ------------------------------------------------------------------------------------------------- |
| `SQLiteCache`    | drop-in para LLM completion cache local (`set_llm_cache(...)`) — reduz custo em prompts repetidos |
| `LocalFileCache` | mesma ideia, formato arquivo                                                                      |
| `InMemoryCache`  | dev/testes                                                                                        |
| `RedisCache`     | distribuído (Bloco G)                                                                             |

Adoção imediata recomendada: `SQLiteCache` em
`~/.vectora/data/llm_cache.db` opt-in via setting. Bloco G migra para
Redis.

##### 21.8 Embeddings — alternativas locais ao Cohere

| Embeddings              | Uso                                                        |
| ----------------------- | ---------------------------------------------------------- |
| `HuggingFaceEmbeddings` | modelos locais (BGE, MiniLM, e5) via sentence-transformers |
| `FastEmbedEmbeddings`   | implementação ONNX rápida da Qdrant                        |
| `OllamaEmbeddings`      | embeddings via Ollama (mesma instalação local)             |
| `LlamaCppEmbeddings`    | quantizado local                                           |
| `GPT4AllEmbeddings`     | modelos GPT4All                                            |

**Tier free**: trocar `CohereEmbeddings` por `FastEmbedEmbeddings(model="BAAI/bge-small-en-v1.5")` quando o user não tem `COHERE_API_KEY`. Sem custo, sem rede,
qualidade aceitável (~85% do Cohere multilingual em benchmarks PT-BR).

##### 21.9 SQL utilities

| Utility                         | Uso                                                                                                             |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `SQLDatabase`                   | conector universal (SQLite/Postgres/MySQL/MSSQL/Oracle) com schema introspection — base do `SQLDatabaseToolkit` |
| `SQLDatabaseChain` (deprecated) | substituído pelo toolkit acima                                                                                  |

`SQLDatabase` é especialmente útil porque já temos SQLAlchemy 2.0 como
dep — conectar agente a "qualquer base SQL do user" custa ~20 linhas.

##### 21.10 O que NÃO adotar do community

Para registro, deps que existem mas **não fazem sentido pro Vectora**:

- `Chroma`, `FAISS` — já temos LanceDB (melhor performance + multimodal).
- `OpenAIEmbeddings` (community) — preferimos Cohere multilingual.
- `LLMs` (TextCompletion) — deprecados pela LangChain.
- Chains legadas (`ConversationalRetrievalChain`, `LLMChain`,
  `RetrievalQA`) — substituídas por `create_agent` + middleware.

##### 21.11 Roadmap de adoção (proposta)

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

#### Apêndice — quando alguém perguntar…

##### "Como vocês emulam o terminal?"

PTY real do OS (`ptyprocess` Unix / `pywinpty` Windows) ligado a um
WebSocket que fala com `xterm.js` no browser ou `RichLog` na TUI.
Sessão persistente — fecha a aba, reabre, comando ainda rodando.

##### "E o file system no chat?"

Endpoints REST tipados (`GET /workspaces/{id}/tree`, `GET /file`,
`POST /fs/file`) consumidos por um `<Tree>` custom em React. Atomic
writes server-side. Anti-traversal por `resolve_within_workspace`.
Lixeira via `send2trash` (não `rm -rf`).

##### "E o Diff? Só Git?"

Só Git. `GitPython` gera o diff unified, um parser nosso transforma em
hunks, e renderizamos com Tailwind classes (verde/vermelho) ou no
Textual com `Static` + cores Rich. Não usamos `diff-match-patch` nem
`jsdiff`.

##### "Como abrimos e editamos arquivos?"

Read: `pathlib`. Write: `Path.write_text` + `os.replace` (atomic).
Edit (substituição cirúrgica): `file_edit` tool faz `find/replace`
com validação. Editor inline no chat: `<textarea>` monospace
(SX-FS-1 vai adicionar ETag para evitar overwrite concorrente).
Sem Monaco, sem CodeMirror — peso não justifica o uso atual.

##### "Como salvamos as envs?"

Três camadas: `defaults.env` (in-package) → `.env` (project) →
`~/.vectora/.env` (user global). Por-usuário: coluna JSON
`users.env_overrides_json` no SQLite. Em runtime: merge das três

- overrides do user. Mascaradas na UI; nunca em logs. Pydantic-Settings
  valida tudo no boot — falha imediata em vez de NoneType mais tarde.

##### "Como lidam com auth?"

- Senha: Argon2id (`argon2-cffi`).
- Sessão: JWT HS256 (`python-jose`) — access 15min, refresh 7d com rotação.
- Storage local do CLI: `keyring` do OS.
- Rate limit: `slowapi` por IP/user/email.
- Cookies httpOnly + SameSite=Lax + Secure (atrás de TLS).
- Audit log de tudo destrutivo.

##### "Têm E2E encryption?"

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

##### "Por que não monorepo via Turborepo / pnpm workspaces?"

`vectora/frontend/` tem `pnpm-workspace.yaml` + `turbo.json` legados do fork
inicial. Hoje rodamos `pnpm --dir vectora/frontend ...` direto. Limpar isso é
chore de housekeeping baixa prioridade.

##### "Por que TanStack Router em vez de React Router?"

Type-safe routing por arquivo, integração nativa com TanStack Query,
e zero ginástica para code-splitting. Bloco D documentou a migração de
Next.js para Vite + TanStack para eliminar o sidecar Node.js do
instalador desktop.

---

## Vectora Deep Engine — Estado Atual e Roadmap

> **Privado.** Auditoria do "motor" do Vectora (agente + grafo + streaming
>
> - persistência + memória + segurança) contra a documentação canônica da
>   LangChain/LangGraph/Deep Agents consultada via MCP `docs-langchain` em
>   junho/2026. Este doc é a fonte de verdade para o que precisa entrar
>   no roadmap pós-E para entregar um **backend robusto, escalável e seguro**
>   usando o melhor dos três frameworks.

---

#### Sumário executivo

O Vectora hoje implementa uma versão **funcional** mas **artesanal** do
padrão Deep Agents. O que entregamos no Bloco E é equivalente em
**comportamento** à proposta canônica do `create_deep_agent`, mas é
**não-equivalente em superfície** — perdemos middleware nativo, profiles
por modelo, backends pluggable, streaming v3, structured output,
guardrails prontos e o ecossistema LangSmith.

> **Clarificação importante sobre o Bloco E**: o bloco E está marcado
> ✅ Concluído porque entregou (a) o `agent_factory` consolidado com
> cache versionado por user, (b) a TUI textual (`vectora chat`) e (c)
> os 9 sub-blocos E1–E9 (com E2 ⏳ parcial). **Não** significa que
> migramos para `create_deep_agent`. A dep `deepagents>=0.6.3` está
> instalada (foi adicionada antecipando essa migração), mas
> `grep -r "from deepagents" backend/` retorna **0 resultados**. O grafo
> atual usa `langgraph.StateGraph` direto, com nós artesanais para
> orchestrator/coder/search/HITL. O bloco **DE** descrito aqui é
> exatamente o fechamento dessa lacuna: aproveitar o que já fizemos
> em E como base e migrar a superfície para a API canônica.

Esta é a lacuna que separa "um agente que funciona" de "um agente
production-ready que escala". O bloco **DE — Deep Engine** descrito ao
final desse documento fecha cada uma dessas frentes em 14 sub-tarefas
ortogonais.

**Filosofia central a internalizar**:

> "Deep Agents é um **harness** sobre LangChain (componentes) + LangGraph
> (runtime). Não substitui nenhum — adiciona uma camada opinionada de
> filesystem virtual, subagents, planning, skills, memória, sandboxes,
> middleware, HITL e prompt caching com defaults sensatos."

Quando você escreve `create_deep_agent(...)` está obtendo um
`CompiledStateGraph` do LangGraph com middleware da LangChain embutidos
— pode ser composto, estendido, injetado em outro `StateGraph` ou
serializado normalmente. Não há mágica nova; é uma fábrica.

---

#### 1. Como o motor está hoje (auditoria por capacidade)

| #   | Capacidade                           | Hoje                                                                           | Canônico (Deep Agents)                                                                                                                       | Status                                              |
| --- | ------------------------------------ | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| 1   | Construção do agente                 | `agent_factory.build_graph()` artesanal em `backend/services/agent_factory.py` | `create_deep_agent(model=, tools=, subagents=, middleware=, backend=, memory=, skills=, permissions=, interrupt_on=, response_format=, ...)` | ❌ Custom                                           |
| 2   | Orquestração de subagents            | Funções async (`coder`, `search`) + nós de finalize                            | Subagents como `dict {name, description, prompt, tools, model}` ou `AsyncSubAgent`; harness expõe `task` tool automaticamente                | ⏳ Parcial — comportamento ok, superfície diferente |
| 3   | HITL                                 | Nó `hitl_check` custom + `interrupt()` raw                                     | `HumanInTheLoopMiddleware(interrupt_on={"tool": {"allowed_decisions": [...]}})`                                                              | ❌ Custom                                           |
| 4   | Permission modes (ask/auto/plan/...) | Mapping próprio em `get_interrupt_on()`                                        | `interrupt_on` ou `HumanInTheLoopMiddleware` com `allowed_decisions`                                                                         | ⏳ Diferente                                        |
| 5   | Filesystem virtual                   | `backend/tools/fs.py` artesanal + `resolve_within_workspace`                   | `StateBackend` (default), `FilesystemBackend(root_dir=, virtual_mode=True)`, `StoreBackend`, `CompositeBackend`                              | ❌ Custom                                           |
| 6   | Filesystem permissions               | scope-guard manual por tool                                                    | `permissions=[FilesystemPermission(...)]` com `first-match-wins`                                                                             | ❌ Custom                                           |
| 7   | Skills (procedural memory)           | `services/skills.py` próprio                                                   | `skills=["./skills/"]` + `SKILL.md` frontmatter; carregamento on-demand pelo harness                                                         | ⏳ Comportamento ok, integração ausente             |
| 8   | Memory (long-term)                   | `services/memory.py` com `cohere.AsyncClient` direto + cosine custom           | `memory=["AGENTS.md"]` + `StoreBackend(namespace=lambda rt: (rt.server_info.user.identity,))`                                                | ❌ Custom                                           |
| 9   | Context compression                  | Truncamento manual em alguns nós                                               | `SummarizationMiddleware(model=, trigger=("tokens", 4000), keep=("messages", 20))`                                                           | ❌ Ausente                                          |
| 10  | Prompt caching                       | Ausente                                                                        | Anthropic prompt caching automático via Profile + `cache_control: "ephemeral"`                                                               | ❌ Ausente                                          |
| 11  | Profiles por modelo                  | Ausente                                                                        | `HarnessProfile(excluded_tools=, excluded_middleware=, reasoning_effort=, prompt_cache=)` registrável por provider/modelo                    | ❌ Ausente                                          |
| 12  | Sandboxes                            | Terminal PTY local sem isolamento                                              | `Modal/E2B/Deno/Daytona Sandbox` ou `LocalShellBackend(root_dir=, env=)`; exec tool automática                                               | ❌ Ausente                                          |
| 13  | Interpreters                         | Ausente                                                                        | `eval` tool em QuickJS scoped (programmatic tool calling)                                                                                    | ❌ Ausente                                          |
| 14  | Streaming                            | `astream_events v2` parseado em `backend/api/adapters.py`                      | `stream_events(version="v3")` com projeções tipadas: `.messages`, `.tool_calls`, `.subagents`, `.values`, `.output`                          | ⏳ Funciona, mas versão antiga                      |
| 15  | Async subagents                      | Sequencial (`parallel_dispatch` artesanal)                                     | `AsyncSubAgent` + background workers + cancelamento + progress                                                                               | ❌ Ausente                                          |
| 16  | Structured output                    | Ausente                                                                        | `response_format=PydanticModel` → `result["structured_response"]`; auto-seleciona `ProviderStrategy` ou `ToolStrategy`                       | ❌ Ausente                                          |
| 17  | Multi-tenancy                        | Manual via `user_id` em `configurable`                                         | `context_schema=Context` + `rt.server_info.user.identity` (autenticação resolve identidade automática quando deployado)                      | ⏳ Funciona, mas sem auth handler                   |
| 18  | Persistence                          | `AsyncSqliteSaver` ✓                                                           | `AsyncSqliteSaver` / `AsyncPostgresSaver` / Managed (auto)                                                                                   | ✅                                                  |
| 19  | LangGraph Store                      | Ausente (memória via cohere custom)                                            | `InMemoryStore` / `PostgresStore` com semantic search nativo                                                                                 | ❌ Ausente                                          |
| 20  | Time travel / forking                | Ausente                                                                        | `update_state(as_node=...)` + replay de `checkpoint_id`                                                                                      | ❌ Ausente                                          |
| 21  | Fault-tolerance / pending writes     | Implícito (LangGraph default)                                                  | LangGraph reinicia do último checkpoint; pending writes não re-executam                                                                      | ✅                                                  |
| 22  | Guardrails (PII)                     | Ausente                                                                        | `PIIMiddleware(pii_type=, strategy=)` para email, credit_card, ip, api_key, etc                                                              | ❌ Ausente                                          |
| 23  | Model retry / fallback               | Implícito (LangChain)                                                          | `ModelRetryMiddleware`, `ModelFallbackMiddleware`, `ToolRetryMiddleware`                                                                     | ❌ Ausente                                          |
| 24  | Cost / call limits                   | Ausente                                                                        | `ModelCallLimitMiddleware(thread_limit=, run_limit=, exit_behavior=)` + `ToolCallLimitMiddleware`                                            | ❌ Ausente                                          |
| 25  | LangSmith tracing                    | Ausente                                                                        | `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY` → traces automáticos                                                                       | ❌ Ausente                                          |
| 26  | LangSmith Engine                     | Ausente                                                                        | Monitora traces, detecta issues, sugere fixes                                                                                                | ❌ Ausente                                          |
| 27  | ACP (Agent Control Protocol)         | Planejado em I4                                                                | `deepagents-acp.server` + `adapter` + `ide-integration`                                                                                      | ⏳ Planejado                                        |
| 28  | Frontend SDK                         | Adapter SSE custom em `vectora/frontend/src/lib/api/vectora-client.ts`         | `@langchain/langgraph-sdk` + `useStream` hook + `useStream.subagents`                                                                        | ❌ Custom                                           |

**Resumo numérico**:

- ✅ implementado canonicamente: 2
- ⏳ comportamento ok / superfície diferente: 6
- ❌ ausente ou custom-only: 20

Esses 20 itens ❌ são exatamente o que separa o Vectora do estado da arte
no ecossistema LangChain. Cada um tem um sub-bloco DE no roadmap.

---

#### 2. Filosofia: framework × runtime × harness

Para tomar decisões certas no roadmap precisamos parar de confundir os
três níveis (a fonte de muita confusão hoje no código):

```
┌─────────────────────────────────────────────────────────┐
│  Deep Agents (HARNESS — opinionado, "agent factory")    │
│  - create_deep_agent + middleware + subagents + skills  │
│  - filesystem virtual + backends + sandboxes            │
│  - prompt caching + context compression                 │
├─────────────────────────────────────────────────────────┤
│  LangChain (FRAMEWORK — componentes reusáveis)          │
│  - BaseChatModel, BaseTool, init_chat_model             │
│  - middleware system (HITL, Summarization, PII, retry)  │
│  - structured output (Provider/Tool strategies)         │
│  - guardrails, prompts, parsers                         │
├─────────────────────────────────────────────────────────┤
│  LangGraph (RUNTIME — execução durável)                 │
│  - StateGraph + nodes + edges + checkpointer            │
│  - BaseStore (long-term memory) + threads + super-steps │
│  - interrupts + time travel + pending writes            │
│  - streaming v3 + subgraphs + namespaces                │
└─────────────────────────────────────────────────────────┘
```

**Regra prática**: ao adicionar capacidade nova,

1. Pergunte: existe **middleware** LangChain pronto? Use.
2. Pergunte: existe **backend** Deep Agents pronto? Use.
3. Pergunte: o LangGraph já oferece **primitiva** (checkpoint, store,
   interrupt)? Use.
4. **Só** se as três respostas forem "não" você escreve código novo.

Hoje nós quebramos essa regra dezenas de vezes — `services/memory.py`,
`services/agent_factory.hitl_check`, `tools/fs.py`,
`services/security.py::resolve_within_workspace`, todos têm equivalente
canônico que dá conta do mesmo problema com menos código, mais features,
e integração com LangSmith de graça.

---

#### 3. API canônica de referência

A assinatura do `create_deep_agent` é nosso mapa de capacidades — cada
parâmetro responde a uma decisão arquitetural:

```python
create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict] | None = None,
    *,
    system_prompt: str | SystemMessage | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    subagents: Sequence[SubAgent | CompiledSubAgent | AsyncSubAgent] | None = None,
    skills: list[str] | None = None,
    memory: list[str] | None = None,
    permissions: list[FilesystemPermission] | None = None,
    backend: BackendProtocol | BackendFactory | None = None,
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
    response_format: ResponseFormat[T] | type[T] | dict | None = None,
    state_schema: type[DeepAgentState] | None = None,
    context_schema: type[ContextT] | None = None,
    checkpointer: Checkpointer | None = None,
    store: BaseStore | None = None,
    cache: BaseCache | None = None,
    debug: bool = False,
    name: str | None = None,
) -> CompiledStateGraph
```

Cada um abaixo:

##### 3.1 `model`

`"google_genai:gemini-3.5-flash"` (string `provider:model`) ou
`BaseChatModel` já inicializado. O harness chama
`init_chat_model()` automaticamente.

**Hoje**: usamos `load_llm()` próprio em `backend/services/utils.py` que
escolhe provider via `Settings.llm_provider`. **Mantemos** — é o ponto
de injeção do tier gate (C7) e da rotação de modelo. Apenas passamos o
resultado para `create_deep_agent(model=instance)`.

##### 3.2 `tools`

Lista de `BaseTool`, callables `@tool`, ou `dict` tool descriptors.
Aceita MCP tools via `langchain-mcp-adapters` automaticamente.

**Hoje**: 39 tools registradas em `backend/tools/__init__.py::ALL_TOOLS`.
`tool_resolver.resolve_tools(user_id)` aplica ABAC e MCP plugins do user.
**Mantemos** — só passamos o resultado para `tools=`.

##### 3.3 `system_prompt`

`str` ou `SystemMessage`. Concatenado com prompts internos do harness
(planning, todos, filesystem). Aceita `cache_control: "ephemeral"` para
Anthropic prompt caching.

**Hoje**: `VECTORA_IDENTITY + ORCHESTRATOR_PROMPT` em
`backend/agents/_identity.py` e `backend/agents/orchestrator.py`. Sem prompt
caching. **Migrar** para receber o prompt completo e marcar a parte
estática como cacheable (DE-5).

##### 3.4 `middleware`

Lista ordenada de `AgentMiddleware`. Hooks em pontos estratégicos:
`before_agent`, `after_agent`, `before_model_call`, `after_model_call`,
`before_tool_call`, `after_tool_call`.

**Built-ins disponíveis** (todos `provider-agnostic`):

| Middleware                  | Função                                           | Status no Vectora                    |
| --------------------------- | ------------------------------------------------ | ------------------------------------ |
| `SummarizationMiddleware`   | Comprime histórico quando perto do limite        | ❌ Ausente                           |
| `HumanInTheLoopMiddleware`  | Pausa antes de tools sensíveis (`interrupt_on=`) | ❌ Custom                            |
| `ModelCallLimitMiddleware`  | Limita chamadas ao modelo por thread/run         | ❌ Ausente                           |
| `ToolCallLimitMiddleware`   | Limita tools globalmente ou por nome             | ❌ Ausente                           |
| `ModelFallbackMiddleware`   | Fallback a outro modelo se primário falhar       | ❌ Ausente                           |
| `ModelRetryMiddleware`      | Retry exponencial em falhas de modelo            | ❌ Ausente                           |
| `ToolRetryMiddleware`       | Retry de tools falhando                          | ❌ Ausente                           |
| `PIIMiddleware`             | Detecta + redact/mask/block PII                  | ❌ Ausente                           |
| `TodoListMiddleware`        | Equipa agente com planning de tasks              | ⏳ Implementamos write_todos próprio |
| `LLMToolSelectorMiddleware` | LLM filtra tools antes do main model             | ❌ Ausente                           |
| `LLMToolEmulatorMiddleware` | Emula tools com LLM (testes)                     | ❌ Ausente                           |
| `ContextEditingMiddleware`  | Trim/clear de tool uses no histórico             | ❌ Ausente                           |
| `ShellMiddleware`           | Shell session persistente                        | ⏳ Temos PTY próprio                 |
| `FileSearchMiddleware`      | Glob + Grep sobre filesystem                     | ⏳ Temos tools próprias              |
| `FilesystemMiddleware`      | Filesystem para context + memory                 | ⏳ Temos tools próprias              |
| `SubagentMiddleware`        | Spawn de subagents                               | ⏳ Custom                            |

**Adoção mínima recomendada** (DE-2):
`HumanInTheLoopMiddleware` + `SummarizationMiddleware` + `PIIMiddleware`

- `ModelCallLimitMiddleware` + `ToolCallLimitMiddleware` + `ModelRetryMiddleware`.

##### 3.5 `subagents`

Lista de `dict {name, description, prompt, tools, model}` ou
`CompiledSubAgent` ou `AsyncSubAgent`. O harness expõe automaticamente a
tool `task(subagent_type=, description=, ...)` ao supervisor.

```python
subagents=[
    {
        "name": "coder",
        "description": "Edits code, runs tests, validates with git",
        "prompt": CODER_PROMPT,
        "tools": [file_read, file_edit, file_write, terminal, git_*],
        "model": None,  # herda do supervisor
    },
    {
        "name": "search",
        "description": "Web search + RAG over local docs",
        "prompt": SEARCH_PROMPT,
        "tools": [web_search, web_fetch, search_memory],
    },
]
```

**Hoje**: `coder` e `search` são funções async em `backend/agents/{coder,search}.py`
invocadas via grafo manual. **Migrar** para dicts (DE-1 + DE-10).

##### 3.6 `skills`

Lista de paths para diretórios. O harness lê `SKILL.md` (frontmatter
YAML com `name` + `description`) no startup, expõe descrições no system
prompt, e carrega o corpo on-demand quando o LLM decide invocar.

```python
skills=["./skills/", "/memories/user-skills/"]
```

**Hoje**: `services/skills.py` próprio com staging + git clone. Continua
útil para CRUD; o que falta é **integrar** com `skills=` do create_deep_agent
em vez de mantermos um sistema separado.

##### 3.7 `memory`

Lista de paths para arquivos de memória (tipicamente `AGENTS.md`,
`/memories/preferences.md`). Carregados no system prompt no startup.
Quando combinados com `StoreBackend(namespace=lambda rt: ...)` viram
memória persistente por user/agent/org.

```python
memory=["/memories/AGENTS.md", "/memories/preferences.md"]
backend=CompositeBackend(
    default=StateBackend(),
    routes={
        "/memories/": StoreBackend(
            namespace=lambda rt: (rt.server_info.user.identity,),
        ),
    },
)
```

**Hoje**: `services/memory.py` artesanal com `cohere.AsyncClient` direto
(violação do princípio "use SDK oficial"). Sem AGENTS.md por user.
**Migrar** para `memory=` + `StoreBackend` (DE-4).

##### 3.8 `permissions`

Lista de `FilesystemPermission(operations=, paths=, mode=)`. Evaluation
**first-match-wins, default allow**.

```python
permissions=[
    {"operations": ["write"], "paths": [".env", "**/credentials*", "**/.git/**"], "mode": "deny"},
    {"operations": ["read"], "paths": [".env*"], "mode": "deny"},
    {"operations": ["read", "write"], "paths": ["/workspace/**"], "mode": "allow"},
]
```

**Hoje**: `resolve_within_workspace()` em `backend/services/security.py` faz
anti-traversal mas não tem regras declarativas. **Substituir** (DE-3).

##### 3.9 `backend`

`BackendProtocol` ou `BackendFactory` (callable que recebe `Runtime` e
retorna backend). Determina onde os arquivos vivem:

| Backend                                              | Escopo             | Persistência               |
| ---------------------------------------------------- | ------------------ | -------------------------- |
| `StateBackend()`                                     | Thread             | via checkpointer           |
| `FilesystemBackend(root_dir=, virtual_mode=True)`    | Local disk         | permanente                 |
| `StoreBackend(namespace=)`                           | Cross-thread       | via BaseStore              |
| `ContextHubBackend("agent-id")`                      | LangSmith Hub      | permanente                 |
| `LocalShellBackend(root_dir=, env=)`                 | Local + shell exec | permanente                 |
| `Modal/E2B/Daytona/Deno Sandbox`                     | Container isolado  | per-session ou persistente |
| `CompositeBackend(default=, routes={"/path/": ...})` | Roteamento         | varia                      |

**Hoje**: nenhum. Filesystem é `pathlib.Path` direto via tools.
**Migrar** para `CompositeBackend` com rotas claras (DE-3):

```python
backend=lambda rt: CompositeBackend(
    default=StateBackend(rt),  # scratch do agente
    routes={
        "/workspace/": FilesystemBackend(
            root_dir=workspace_root(rt),
            virtual_mode=True,
        ),
        "/memories/": StoreBackend(
            rt,
            namespace=lambda rt: (rt.server_info.user.identity,),
        ),
        "/skills/": StoreBackend(
            rt,
            namespace=lambda rt: ("vectora",),
        ),
    },
)
```

##### 3.10 `interrupt_on`

`dict[str, bool | InterruptOnConfig]`. Quando o agente decide chamar
tool em `interrupt_on`, o grafo pausa via `interrupt()` antes da execução.
Cliente retoma com `Command(resume={"decisions": [{"type": "approve"}]})`
ou `"edit"` ou `"reject"`.

**Hoje**: temos lógica equivalente em `hitl_check`. **Substituir** pelo
`HumanInTheLoopMiddleware` que entrega o mesmo + `allowed_decisions` +
integração nativa com o frontend SDK (DE-2).

##### 3.11 `response_format`

Schema (`Pydantic BaseModel`, `dataclass`, `TypedDict`, ou JSON Schema).
LangChain auto-seleciona:

- `ProviderStrategy` se modelo suporta structured output nativo
  (OpenAI, Anthropic, Gemini, xAI Grok)
- `ToolStrategy` (tool calling forçado) para os demais

Resultado em `result["structured_response"]` validado.

**Hoje**: Ausente. Quando o agente precisa retornar dados estruturados,
parseamos JSON do texto manualmente. **Adicionar** (DE-7) — habilita
flows como `extract_contact_info`, `classify_intent`,
`generate_workspace_config` sem regex.

##### 3.12 `state_schema` / `context_schema`

`state_schema`: extensão do `DeepAgentState` (TypedDict com `messages`,
`todos`, `files`, ...). Útil para campos customizados.

`context_schema`: dataclass com dados **per-run** que tools/middleware
leem via `runtime.context`. Default seria:

```python
@dataclass
class VectoraContext:
    user_id: str
    workspace_id: str | None = None
    permission_mode: Literal["ask", "auto", "plan", "accept_edits", "bypass"] = "ask"
    org_id: str | None = None
    locale: Literal["en", "es", "pt-BR"] = "pt-BR"
```

**Hoje**: passamos `user_id` e `permission_mode` em `configurable`
manualmente. **Migrar** para `context_schema` tipado (DE-1).

##### 3.13 `checkpointer` / `store`

`checkpointer`: `BaseCheckpointSaver`. Default: `InMemorySaver`. Vectora
usa `AsyncSqliteSaver` apontando para `~/.vectora/data/vectora.db`.

`store`: `BaseStore`. Para long-term memory cross-thread. Vectora não usa
hoje (memória via cohere custom).

**Hoje**: checkpointer ✅. Store ❌.
**Migrar** memória para `InMemoryStore` (dev) ou `AsyncPostgresStore` (prod)
com `index={"embed": CohereEmbeddings, "dims": 1024}` para semantic
search nativo, substituindo `services/memory.py` (DE-4).

##### 3.14 `cache`

`BaseCache` (LangChain). LLM responses cache. Vectora não usa.
**Adicionar** opt-in via `InMemoryCache` (dev) ou `RedisCache` (prod)
no Bloco G.

---

#### 4. HarnessProfile — defaults por modelo

Profiles são **bundles declarativos** de configuração que o
`create_deep_agent` aplica automaticamente quando você passa o `model=`
correspondente.

```python
from deepagents import HarnessProfile, register_harness_profile

register_harness_profile(
    "anthropic:claude-sonnet-4-6",
    HarnessProfile(
        excluded_tools=frozenset(),  # mostra todas as filesystem tools
        prompt_cache=True,           # cache_control: ephemeral no system
        reasoning_effort="high",     # passado ao Anthropic
        max_tool_iterations=50,
    ),
)

register_harness_profile(
    "google_genai:gemini-2.5-flash",
    HarnessProfile(
        excluded_tools=frozenset({"glob"}),  # Gemini é ruim em glob
        prompt_cache=False,                  # Gemini ainda não tem
        max_tool_iterations=30,
    ),
)

register_harness_profile(
    "ollama:llama3",
    HarnessProfile(
        # Modelos locais menores: esconde tools complexas
        excluded_tools=frozenset({"task", "write_todos"}),
        max_tool_iterations=15,
    ),
)
```

**Por que importa**: cada modelo tem capacidades diferentes (prompt
caching, multimodal, structured output nativo, reasoning effort). Hoje
temos um único caminho para todos. **Adicionar** (DE-5).

---

#### 5. Streaming v3 — projeções tipadas e subagents

LangGraph 1.1+ introduziu o formato `version="v2"` (StreamPart unificado)
e `version="v3"` no Deep Agents (projeções tipadas).

**Hoje**: `astream_events(version="v2")` em `backend/api/adapters.py`. Nós
mesmos branchamos por tipo de evento. Funciona, mas:

- Tokens, tool calls e values vêm misturados → adapter complexo.
- Subagents não têm projeção própria → não sabemos
  facilmente "qual subagent gerou esse token".

**Canônico (v3)**:

```python
stream = agent.stream_events(input, version="v3")

# 4 projeções independentes
for message in stream.messages:        # tokens do supervisor
    yield SSE("token", message.text)

for tool_call in stream.tool_calls:    # tool calls do supervisor
    yield SSE("tool_call", {
        "name": tool_call.tool_name,
        "input": tool_call.input,
        "completed": tool_call.completed,
        "error": tool_call.error,
    })

for subagent in stream.subagents:      # cada delegação ganha handle
    yield SSE("subagent_started", {
        "name": subagent.name,
        "path": subagent.path,
        "status": subagent.status,
    })
    for msg in subagent.messages:
        yield SSE("subagent_token", {
            "name": subagent.name,
            "text": msg.text,
        })
    for tc in subagent.tool_calls:
        yield SSE("subagent_tool_call", {
            "name": subagent.name,
            "tool": tc.tool_name,
            "input": tc.input,
        })

for value in stream.values:            # snapshots de state
    yield SSE("state", value)
```

Status do subagent ∈ `{started, running, completed, failed, interrupted}`.
Frontend pode renderizar **cada subagent num bloco separado** com seu
próprio thinking + tool calls + tokens.

**Migrar** o adapter (DE-6).

---

#### 6. Memory: a abordagem que dispensa código próprio

A documentação canônica trata memória como **arquivos num filesystem**,
não como tabela. Isso é radicalmente diferente do nosso `services/memory.py`.

**Dimensões**:

| Dimensão   | Pergunta                | Opções                                                         |
| ---------- | ----------------------- | -------------------------------------------------------------- |
| Duração    | Quanto tempo dura?      | Short-term (thread) ou long-term (cross-thread)                |
| Tipo       | Que tipo de informação? | Episódica (passado), procedural (skills), semântica (fatos)    |
| Escopo     | Quem vê?                | User, agent, org                                               |
| Update     | Quando escreve?         | Hot-path (durante conversa) ou background (consolidation cron) |
| Retrieval  | Como lê?                | Loaded into prompt vs on-demand (skills)                       |
| Permission | Pode escrever?          | Read-write vs read-only (policies)                             |

**Padrão recomendado para Vectora**:

```python
backend=lambda rt: CompositeBackend(
    default=StateBackend(rt),
    routes={
        "/memories/": StoreBackend(             # semântica per-user
            rt,
            namespace=lambda rt: (
                rt.server_info.assistant_id,
                rt.server_info.user.identity,
            ),
        ),
        "/skills/": StoreBackend(               # procedural per-user
            rt,
            namespace=lambda rt: (rt.server_info.user.identity,),
        ),
        "/policies/": StoreBackend(             # org-wide read-only
            rt,
            namespace=lambda rt: (rt.context.org_id,),
        ),
        "/workspace/": FilesystemBackend(       # código do user
            root_dir=workspace_root(rt),
            virtual_mode=True,
        ),
    },
),
memory=["/memories/AGENTS.md"],
skills=["/skills/"],
permissions=[
    {"operations": ["write"], "paths": ["/policies/**"], "mode": "deny"},
],
```

**Episodic memory** (passado conversacional): já temos via
checkpointer SQLite. Para tornar **searchable**, expor uma tool wrapper:

```python
@tool
async def search_past_conversations(query: str, runtime: ToolRuntime) -> str:
    """Search this user's past conversations for context."""
    user_id = runtime.server_info.user.identity
    threads = await client.threads.search(
        metadata={"user_id": user_id},
        limit=5,
    )
    # ... retorna histórico relevante
```

**Background consolidation** (sleep-time compute): segundo agente
deep_agent dedicado que roda em cron, lê conversas recentes via
`search_recent_conversations`, sintetiza, e atualiza `/memories/AGENTS.md`
do user. Cadência ~6h (chat ativo) ou nightly (uso esporádico). Match
crítico: cron-interval = lookback-window do tool. (DE-13)

---

#### 7. Multi-tenancy e segurança

##### 7.1 Identidade

Em produção, **toda invocação carrega 2 parâmetros**:

```python
agent.invoke(
    {"messages": [{"role": "user", "content": "..."}]},
    config={"configurable": {"thread_id": str(uuid7())}},  # conversation
    context=VectoraContext(user_id=user.id, workspace_id=ws.id),  # per-run
)
```

`thread_id` é estável (mesma conversa). `context` muda por run (pode mudar
workspace mid-conversation por exemplo).

**Auto-resolução de identidade**: ao deployar em LangSmith ou
implementar `custom_auth` no `langgraph.json`, `rt.server_info.user.identity`
vira o `user_id` autenticado. Sem isso, passamos manualmente via `context`.

##### 7.2 Authorization

LangSmith Deployments expõe `auth_handlers` que:

- Etiquetam recursos com `owner: user_id`.
- Retornam filtros para listagens (user só vê seus threads/assistants).
- Negam com HTTP 403 quando não autorizado.

**Vectora hoje**: B1 (auth/RBAC) faz isso manualmente em handlers
FastAPI. **Migrar** para o padrão LangGraph quando deploy em LangSmith
ou re-aproveitar a infra de auth handlers do `langgraph` standalone.

##### 7.3 Credenciais por user (Agent Auth)

Quando o agente chama APIs externas em nome do user (GitHub, Slack,
Google Drive, etc), o padrão canônico é **Agent Auth** — OAuth managed
da LangChain:

```python
from langchain_auth import Client
auth_client = Client()

@tool
async def github_action(query: str, runtime: ToolRuntime):
    auth_result = await auth_client.authenticate(
        provider="github",
        scopes=["repo", "read:org"],
        user_id=runtime.server_info.user.identity,
    )
    # use auth_result.token
```

Na primeira chamada, o agente interrompe execução e mostra OAuth consent
URL. Após o user autenticar, o agente resume com token válido.
Refresh automático.

**Vectora hoje**: GitHub OAuth manual em B6 + tokens no vault KeePass.
Funciona; reabrir consideração quando Agent Auth ficar GA estável.

##### 7.4 Sandboxes (DE-11)

Para workspaces **untrusted** ou execução de código gerado, hoje rodamos
em PTY local (zero isolamento). Canonicamente:

- `Modal/E2B/Daytona/Deno` sandbox backend → execução isolada.
- `execute` tool aparece automaticamente quando sandbox detectado.
- Pode-se rodar **agent fora**, **sandbox dentro** (modelo decoupled).
  Vectora já segue esse padrão — só falta plugar o backend certo.

Sandbox + git worktree por user (já em I1) = isolamento real para
multi-tenant code execution.

---

#### 8. Guardrails (DE-8)

Defesa em camadas via middleware. Ordem importa (cada um pode
short-circuit).

```python
middleware=[
    # Camada 1: filtro determinístico de input
    ContentFilterMiddleware(banned_keywords=["...", "..."]),

    # Camada 2: PII em ambos os sentidos
    PIIMiddleware("email", strategy="redact", apply_to_input=True),
    PIIMiddleware("email", strategy="redact", apply_to_output=True),
    PIIMiddleware("api_key", detector=r"sk-[a-zA-Z0-9]{32}", strategy="block"),
    PIIMiddleware("credit_card", strategy="mask"),

    # Camada 3: budgets de custo
    ModelCallLimitMiddleware(thread_limit=100, run_limit=20, exit_behavior="end"),
    ToolCallLimitMiddleware(tool_name="terminal", thread_limit=10),
    ToolCallLimitMiddleware(tool_name="web_search", run_limit=5),

    # Camada 4: resiliência
    ModelRetryMiddleware(max_attempts=3, exponential_backoff=True),
    ToolRetryMiddleware(max_attempts=2),
    ModelFallbackMiddleware(
        primary="anthropic:claude-sonnet-4-6",
        fallback="openai:gpt-5.4",
    ),

    # Camada 5: HITL — sempre o último gate
    HumanInTheLoopMiddleware(interrupt_on={
        "file_write": {"allowed_decisions": ["approve", "edit", "reject"]},
        "terminal": {"allowed_decisions": ["approve", "reject"]},
        "git_push": True,
    }),

    # Camada 6: summarization — para janelas longas
    SummarizationMiddleware(
        model="anthropic:claude-haiku-4",
        trigger=("fraction", 0.8),
        keep=("messages", 30),
    ),

    # Camada 7: custom safety guardrail (after_agent)
    SafetyOutputGuardrail(),  # LLM-based check da resposta final
]
```

**Custom guardrails** via `@before_agent` ou `@after_agent`:

```python
from langchain.agents.middleware import before_agent, hook_config

@before_agent(can_jump_to=["end"])
def block_prompt_injection(state, runtime):
    first_msg = state["messages"][0]
    if contains_injection_signature(first_msg.content):
        return {
            "messages": [{
                "role": "assistant",
                "content": "Pedido bloqueado por motivo de segurança."
            }],
            "jump_to": "end",
        }
    return None
```

---

#### 9. Persistence avançada (DE-14)

LangGraph já entrega persistence, mas estamos usando ~30% do que é
possível.

##### 9.1 Time travel

```python
# Listar histórico do thread
history = list(graph.get_state_history(config))

# Encontrar checkpoint antes de um node específico
before_coder = next(s for s in history if s.next == ("coder",))

# Replay a partir desse checkpoint
graph.invoke(None, config={
    "configurable": {
        "thread_id": config["configurable"]["thread_id"],
        "checkpoint_id": before_coder.config["configurable"]["checkpoint_id"],
    },
})
```

**Use case Vectora**: rewind (SX-FS-3) — implementação canônica trivial.

##### 9.2 Update state (edit + regenerate)

```python
# User edita a 3ª mensagem
graph.update_state(
    config={"configurable": {"thread_id": tid, "checkpoint_id": cid_before_msg3}},
    values={"messages": [HumanMessage(content="versão editada")]},
    as_node="__start__",  # treats update como input
)
# Próximo invoke regenera daquele ponto
```

**Use case Vectora**: I4 (edit message + regenerate) + I5 (fork from here)
do Bloco B5 — implementação canônica em 10 linhas.

##### 9.3 Pending writes recovery

Quando um node falha mid-super-step, LangGraph já persiste os writes dos
nodes que **completaram** no mesmo super-step. No resume, esses não
re-executam. Isso é **automático** — só precisamos confiar.

**Use case Vectora**: se `parallel_dispatch` chama coder + search + rag
e search falha, no resume coder/rag não re-executam. Já temos! Só não
estávamos documentando.

##### 9.4 Subgraph checkpointer scoping

Importante para HITL aninhado: ao colocar um agente compilado como
node de outro StateGraph (padrão recomendado para workflows custom),
pode-se escolher entre:

- **Per-thread checkpointing**: subgraph compartilha thread com pai.
- **Per-invocation checkpointing**: cada call do subgraph é
  independente.

Decisão fica em `.compile(checkpointer=...)` do subgraph.

---

#### 10. ACP — Agent Control Protocol (DE-12, já em I4)

Padrão open para clientes (IDEs, CLIs, outros agentes) chamarem agentes
remotos como ferramentas.

```
[Claude Desktop] ──ACP──> [Vectora] ──MCP/tools──> [Postgres/GitHub/...]
```

3 componentes da lib:

- `deepagents-acp.server` — Vectora expõe `/acp/v1` autenticado.
- `deepagents-acp.adapter` — Vectora consome outros agentes ACP como
  subagent.
- `deepagents-acp.ide-integration` — conector VSCode/JetBrains nativo.

Bloco I4 já mapeia. Implementação concreta em DE-12 + J7 (REST público).

---

#### 11. Frontend canônico (`@langchain/langgraph-sdk`)

A docs `deepagents/frontend/*` cobre `useStream`, `useStream(subagent)`,
`useArtifacts`, `useInterrupts`, `useThreadHistory`. Substitui nosso
`vectora-client.ts` artesanal por uma surface consistente com toda a
comunidade LangChain.

```ts
const { messages, status, interrupt, submit, stop } = useStream({
  apiUrl: "/v1/agent",
  apiKey: token,
  threadId,
  assistantId: "vectora",
  context: { user_id, workspace_id, permission_mode },
});

const subagentStream = useStream.subagents();
// renderizar cada subagent em bloco separado

const onApprove = () =>
  submit(Command((resume = { decisions: [{ type: "approve" }] })));
const onReject = () =>
  submit(Command((resume = { decisions: [{ type: "reject" }] })));
const onEdit = (newArgs) =>
  submit(Command((resume = { decisions: [{ type: "edit", args: newArgs }] })));
```

Vale migrar quando o Bloco D (Vite SPA) estabilizar, junto com a Etapa
DE-6 (streaming v3).

---

#### 12. Observabilidade — LangSmith (DE-9)

Adicionar **3 env vars** habilita observabilidade end-to-end zero-config:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls_...
LANGCHAIN_PROJECT=vectora-prod  # opcional
```

Cada `agent.invoke` vira um trace navegável com:

- Cada LLM call (prompt + tokens in/out + custo).
- Cada tool call (args + resultado + duração).
- Cada subagent expansão.
- Cada interrupt (com decisão do user).
- Cada middleware hook.

**LangSmith Engine**: opt-in que monitora traces, detecta padrões
problemáticos (timeouts, error rates, latência p95), e sugere fixes
(prompt tweaks, middleware ajustes).

**Para Vectora**: integrar como opt-in via `Settings.langsmith_api_key`.
Quando ausente, traces ficam só local (`VectoraTracer` SQLite — A1).
Quando presente, espelhamos para LangSmith. **Sem PII** — config separada
de `LANGCHAIN_TRACING_V2` para evitar acidente.

---

#### 13. Bloco DE — Deep Engine (roadmap)

> **Quando rodar**: depois de Bloco F (storage) e antes de Bloco H/I
> (deep agents 1+2 já presumem esse refactor). Pode rodar em paralelo
> com System Experience (TUI/UX) já que SX é cliente do agente, não
> do harness.

##### DE-1 — `agent_factory` → `create_deep_agent`

Refactor cirúrgico:

```python
# backend/services/agent_factory.py (novo)

async def get_user_agent(user_id: str) -> CompiledStateGraph:
    cache_key = (
        user_id,
        llm_version(),
        tools_version(user_id),
        policy_version(user_id),
        skills_version(user_id),
    )
    if cached := _agent_cache.get(cache_key):
        return cached

    agent = create_deep_agent(
        model=load_llm(),
        tools=resolve_tools(user_id),
        subagents=_subagent_specs(user_id),
        system_prompt=VECTORA_IDENTITY + ORCHESTRATOR_PROMPT,
        middleware=_middleware_stack(user_id),
        backend=_backend_factory(user_id),
        memory=["/memories/AGENTS.md"],
        skills=["/skills/"],
        permissions=_permissions(user_id),
        interrupt_on={},  # gerenciado pelo HumanInTheLoopMiddleware
        context_schema=VectoraContext,
        checkpointer=await get_checkpointer(),
        store=await get_store(),
        name="vectora-supervisor",
    )

    _agent_cache[cache_key] = agent
    return agent
```

Deletar: `build_graph`, `hitl_check`, `_hitl_route`, `_resolve_pre_interrupt`,
`_apply_hitl_edit`, `parallel_dispatch`, todas as `*_finalize`.

##### DE-2 — Middleware nativo

`backend/services/middleware.py` (novo) com `_middleware_stack(user_id)`
montando a stack canônica (HITL + Summarization + ModelCallLimit +
ToolCallLimit + PII + ModelRetry + ModelFallback).

Map de `permission_mode → interrupt_on` movido para construção do
`HumanInTheLoopMiddleware`:

```python
def _hitl_middleware(permission_mode: str) -> HumanInTheLoopMiddleware:
    match permission_mode:
        case "bypass" | "auto":
            return HumanInTheLoopMiddleware(interrupt_on={})
        case "accept_edits":
            return HumanInTheLoopMiddleware(interrupt_on={
                "terminal": {"allowed_decisions": ["approve", "edit", "reject"]},
            })
        case "plan":
            # Recusa toda destrutiva
            return HumanInTheLoopMiddleware(interrupt_on={
                tool: {"allowed_decisions": ["reject"]}
                for tool in DESTRUCTIVE_TOOLS
            })
        case _:  # ask, default
            return HumanInTheLoopMiddleware(interrupt_on={
                tool: {"allowed_decisions": ["approve", "edit", "reject"]}
                for tool in DESTRUCTIVE_TOOLS
            })
```

##### DE-3 — Backends pluggable

`backend/services/backends.py` (novo) com `_backend_factory(user_id)`
retornando `CompositeBackend` com 4 rotas (default + workspace + memories

- skills). Substitui `resolve_within_workspace` + tools `fs.py` manuais.

`permissions=` para `.env`, `.git/`, `credentials*` deny-write.

##### DE-4 — Memory como filesystem

- Remove `services/memory.py` artesanal.
- Substitui por `memory=["/memories/AGENTS.md"]`.
- `StoreBackend(namespace=lambda rt: (rt.server_info.user.identity,))`
  com `index={"embed": CohereEmbeddings, "dims": 1024}` para semantic
  search nativo.
- Migration: copia tabela `memories` antiga para o novo store.

##### DE-5 — HarnessProfile por modelo

`backend/services/profiles.py` (já planejado em H5). Registra um profile por
modelo principal usado (Anthropic, OpenAI, Gemini, Cohere, Ollama).
Cobre prompt caching, reasoning effort, excluded tools.

##### DE-6 — Streaming v3 + subagents projection

Refactor de `backend/api/adapters.py`:

- Trocar `astream_events(version="v2")` → `stream_events(version="v3")`.
- Expor projections separadas no SSE:
  `{type: "supervisor_token", ...}`,
  `{type: "subagent_started", name, path}`,
  `{type: "subagent_token", name, text}`,
  `{type: "subagent_tool_call", name, tool, input}`,
  `{type: "subagent_completed", name, output}`.

Frontend (Bloco D já preparou Vite) renderiza cada subagent em bloco
próprio.

##### DE-7 — Structured output

Adicionar `response_format=` opcional ao `/v1/chat/stream` e expor
endpoints especializados:

- `POST /v1/extract` `{schema, text}` → JSON validado.
- `POST /v1/classify` `{labels, text}` → label + confidence.
- `POST /v1/generate-config` `{type, hints}` → dict tipado.

Auto-detecta `ProviderStrategy` (Anthropic/OpenAI/Gemini) ou
`ToolStrategy` (fallback).

##### DE-8 — Guardrails

Stack defensiva canônica (PII + ContentFilter + custom safety
guardrails) em `_middleware_stack(user_id)`. Configurável por tier
no admin panel (B7).

##### DE-9 — LangSmith tracing opt-in

`Settings.langsmith_api_key` (env `VECTORA_LANGSMITH_KEY`). Quando set:

- Espelha traces para LangSmith.
- Habilita LangSmith Engine.
- Adiciona link "Ver trace" em cada mensagem na UI (link público
  controlado).

Sem set: comportamento atual (`VectoraTracer` SQLite local).

##### DE-10 — Async subagents (paralelismo real)

Substituir `parallel_dispatch` por subagents async-first do deepagents.
Quando o supervisor chama `task(subagent_type=...)` 3× em paralelo, os
3 subagents rodam concorrentes em event loops separados.

Cancelamento via `subagent.cancel()`. Progress via `get_stream_writer`
dentro de tools dos subagents.

##### DE-11 — Sandbox backend

Para workspaces **untrusted** (clonados de URL pública ou marked não-
trusted no B2):

- Backend = `ModalSandbox()` ou `E2BSandbox()` por workspace.
- `execute` tool automática (substitui nossa `terminal` quando sandbox).
- HITL desnecessário dentro de sandbox (isolamento já é o gate).

Plano F (storage) deve cobrir o caso lite (sem sandbox), DE-11 cobre o
pro com sandbox managed.

##### DE-12 — ACP server público

Bloco I4 + J7 já mapeiam. DE-12 confirma o caminho:
`/v1/acp` → `deepagents-acp.server` mount → autenticado via OAuth2
client credentials (J1).

##### DE-13 — Background memory consolidation

Segundo deep agent (`consolidation_agent`) em `langgraph.json` com cron
`0 */6 * * *`. Lê conversas das últimas 6h via
`search_recent_conversations`, sintetiza, atualiza
`/memories/AGENTS.md` do user. Self-hosted: usa SCons ou systemd timer.

##### DE-14 — Time travel + edit/regenerate via update_state

Endpoints REST:

- `GET /v1/threads/{tid}/checkpoints` → lista (já temos SX-FS-3 que pede).
- `POST /v1/threads/{tid}/rewind {checkpoint_id}` → cria novo run no
  checkpoint anterior.
- `POST /v1/threads/{tid}/messages/{mid}/edit {content}` → `update_state`
  - invoke novo.
- `POST /v1/threads/{tid}/fork {from_checkpoint_id}` → cria novo thread
  copiando histórico até o checkpoint.

Tudo 10–30 linhas cada — LangGraph já entrega a primitiva.

---

#### 14. Arquivos críticos (Bloco DE)

| Sub   | Arquivos                                                                                                                                  |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| DE-1  | `backend/services/agent_factory.py` (rewrite), deletar `build_graph` interno; `backend/services/context.py` (novo, `VectoraContext`)      |
| DE-2  | `backend/services/middleware.py` (novo); deletar `hitl_check`, `_resolve_pre_interrupt`, `_apply_hitl_edit`                               |
| DE-3  | `backend/services/backends.py` (novo); deprecate `backend/services/security.py::resolve_within_workspace`; refactor `backend/tools/fs.py` |
| DE-4  | deletar `backend/services/memory.py`; refactor `backend/tools/memory.py` para usar store nativo; migration script                         |
| DE-5  | `backend/services/profiles.py` (novo); registra profile por modelo no startup                                                             |
| DE-6  | `backend/api/adapters.py` (refactor v2→v3), `backend/api/node_labels.py` (extensão p/ subagent paths)                                     |
| DE-7  | `backend/api/handlers/{extract,classify}.py` (novos); `backend/api/handlers/chat.py` (`response_format` opcional)                         |
| DE-8  | `backend/services/guardrails.py` (novo); `vectora/frontend/src/components/admin/guardrails-panel.tsx` (UI)                                |
| DE-9  | `backend/services/telemetry/langsmith.py` (novo); env `VECTORA_LANGSMITH_KEY`                                                             |
| DE-10 | `backend/services/agent_factory.py` (subagents como `AsyncSubAgent`)                                                                      |
| DE-11 | `backend/services/sandboxes/{modal,e2b}.py` (novos); reuso de I1 (sandbox + worktree)                                                     |
| DE-12 | `backend/api/handlers/v1/acp.py` (mount); `pyproject.toml` (+`deepagents-acp`)                                                            |
| DE-13 | `backend/agents/consolidation.py` (novo); `langgraph.json`; cron via SCons                                                                |
| DE-14 | `backend/api/handlers/threads.py` (+checkpoints, rewind, edit, fork); `backend/services/checkpoint.py` (helpers)                          |

---

#### 15. Dependências (atualizar `pyproject.toml`)

```toml
# Faixas abertas (princípio 5 do plano mestre)
dependencies = [
  # já existe
  "langchain>=1.3.1",
  "langchain-core>=1.4.0",
  "langgraph>=1.2.1",
  "langgraph-checkpoint-sqlite>=3.1.0",
  "deepagents>=0.6.3",
  # Adicionar
  "langchain-anthropic>=0.4.0",   # prompt caching nativo
  "langchain-openai>=0.4.0",      # ProviderStrategy nativa
  "langchain-google-genai>=2.2.0",
  "langgraph-checkpoint-postgres>=3.0.0",  # opt-in pro tier
  "langgraph-store-sqlite>=0.2.0",         # store local
  "langgraph-store-postgres>=0.2.0",       # store pro
  "deepagents-acp>=0.3.0",        # ACP (DE-12)
  # Opcionais quando tier=pro
  "langsmith>=0.5.0",             # já temos via langchain
]
```

Remover (deps fantasma confirmadas em `documents/agent-core-roadmap.md`):

- `dotfiles`, `ast-serialize`, `librt`.

---

#### 16. Verificação (end-to-end do Bloco DE)

- `from deepagents import create_deep_agent` é o único builder de agente
  no `backend/`. `grep -r "StateGraph(" backend/` deve retornar **0 ocorrências**
  no agente principal (apenas subgraphs auxiliares se houver).
- `agent.invoke({...}, context=VectoraContext(...))` funciona; tools
  leem `runtime.context.user_id`.
- HITL via `HumanInTheLoopMiddleware`: `interrupt()` raw removido.
  Approve/Edit/Reject em todos os 5 modos preservam comportamento dos
  29 testes do E6.
- Memória: `/memories/AGENTS.md` por user; cross-thread persistente;
  semantic search funciona via `store.search(namespace, query=...)`.
- Streaming v3: cliente JS consome `stream.subagents` e renderiza cada
  subagent em bloco. Latência first-token ≤ atual.
- Structured output: `POST /v1/extract` retorna Pydantic validado.
- Guardrails: tentar enviar email com `sk-...` no body → PIIMiddleware
  bloqueia com `[REDACTED_API_KEY]`.
- LangSmith: setar `VECTORA_LANGSMITH_KEY=...` → próxima invocation
  aparece no dashboard em <30s.
- Time travel: clicar "Voltar até aqui" na 3ª mensagem → 4ª+ apagadas,
  nova resposta gerada do mesmo checkpoint.
- ACP: Claude Desktop → "Add ACP server" → URL Vectora → tools do
  Vectora aparecem disponíveis para o Claude.

---

#### 17. Princípios cardinais (para internalizar)

1. **Antes de escrever código, procure middleware/backend/primitiva já
   pronto.** Toda capacidade nova começa por uma consulta à docs
   (`docs-langchain` MCP). Reescrever é violação de princípio.

2. **Composability > complexity.** `create_deep_agent` retorna um
   `CompiledStateGraph` normal. Pode-se compor num `StateGraph` maior
   (router de intents, fan-out, workflow custom). Nunca há razão para
   reimplementar o `agent loop`.

3. **Backends decidem onde dados vivem; middleware decide o que acontece
   neles; permissions decidem quem pode tocar.** Manter os 3 separados —
   confundir um com o outro foi a fonte do código artesanal atual.

4. **Streaming v3 sempre, v2 nunca.** Adapter v2 sofre na hora de
   distinguir supervisor de subagent.

5. **Multi-tenancy é `(thread_id, context)` + auth handler.** Nunca
   embutir `user_id` em prompts ou tools manuais — sempre via
   `runtime.context` ou `runtime.server_info.user.identity`.

6. **Long-term memory é filesystem, não tabela.** Tudo via `StoreBackend`

   - `memory=["AGENTS.md"]`. Semantic search nativa.

7. **LangSmith é a observabilidade default.** Não temos motivo para
   manter `VectoraTracer` SQLite quando deploy estiver em prod — vira
   fallback local.

8. **Profiles antes de hardcode por provider.** Se você está escrevendo
   `if model.startswith("anthropic:")` em algum lugar, isso é um profile
   esperando para nascer.

9. **HITL é middleware, não nó do grafo.** A diferença é que middleware
   se compõe e é serializável; nó custom não.

10. **Sandbox > scope-guard.** Quando a tarefa é "isolar execução
    potencialmente perigosa", a resposta é "sandbox backend", não "regex
    de path mais esperta".

---

#### 18. Referência cruzada com o plano mestre

| Sub-bloco DE | Substitui / complementa                         | Habilita              |
| ------------ | ----------------------------------------------- | --------------------- |
| DE-1         | reescreve metade de E1/E2/E5                    | toda a stack DE       |
| DE-2         | substitui E4 (HITL)                             | DE-8 (guardrails)     |
| DE-3         | substitui parte de SX-FS-1..19 (backend)        | DE-4, DE-11           |
| DE-4         | substitui C1 (memory)                           | DE-13 (consolidação)  |
| DE-5         | substitui H5 (profiles parcial)                 | prompt caching H3     |
| DE-6         | substitui E3 (adapters)                         | frontend SDK          |
| DE-7         | nova capability                                 | uso em B5 (export), J |
| DE-8         | nova camada                                     | compliance K          |
| DE-9         | substitui A1 tracer parcial                     | M (observability)     |
| DE-10        | substitui I3 (async parcial)                    | H/I full              |
| DE-11        | substitui I1 (sandbox parcial)                  | multi-tenant pro      |
| DE-12        | substitui I4/J7 (ACP)                           | IDE integrations N7   |
| DE-13        | substitui H2 (AGENTS.md memory parcial)         | personalização        |
| DE-14        | substitui SX-FS-3 (rewind via langgraph nativo) | I4/I5 do B5           |

Bloco DE é **upstream** de quase tudo que vem depois — vale priorizá-lo
no momento em que houver bandwidth para um refactor de 2–4 semanas.

---

#### 19. Quando NÃO migrar (riscos e contra-indicações)

- **Se Bloco F (storage) ainda não estabilizou**, segurar DE até lá.
  Backends pluggable dependem de Postgres/Qdrant configuráveis.
- **Se contexto E2E (testes integrados com APIs reais) está
  quebrado**, consertar primeiro. Refactor sem rede de segurança é
  receita para regressão silenciosa.
- **Se a base de testes do agente ainda passa por mocks ad-hoc** do
  `build_graph`, criar suite de paridade primeiro: gravar fixtures de
  comportamento esperado (input → mensagens emitidas → tool calls)
  rodando no agente atual, e usar como golden test após o refactor.
- **Se Bloco D (Vite) ainda mostra instabilidade** em mobile/Electron,
  refactorar primeiro o backend pode fragilizar duas frentes ao mesmo
  tempo.

Padrão recomendado: DE entra **em paralelo** com System Experience
(que é cliente), mas **depois** de F+G (storage+cache estabilizados),
com release behind feature flag (`VECTORA_USE_DEEP_ENGINE=1`) por 1–2
versões antes de virar default.

---

## Vectora — Tools Nativas (Batteries Included)

> Filosofia de tooling: torne **nativo** o que outros agentes deixam
> para o user instalar via MCP. Reduz fricção, garante qualidade,
> elimina "tenho que instalar 10 plugins antes de começar".
>
> Documento pareado com `extensibility-roadmap.md` — este define
> o que está dentro do Vectora; aquele define como o user instala
> qualquer outro MCP do ecossistema.

---

#### A filosofia "Sublime vs vim+plugins"

Vim ganha em flexibilidade. Sublime Text ganha em produtividade de
saída-da-caixa. Para 90% dos usuários, **Sublime venceu**. Não porque
seja superior tecnicamente — porque eliminou a etapa "instale 30
plugins antes de escrever sua primeira linha".

Claude Code e Cursor caíram na mesma armadilha do vim:

> _"Para fazer browser automation, instale o MCP playwright. Para
> consultar PostgreSQL, instale o MCP postgres. Para gerar PDF, instale
> o MCP pdf. Para ler Excel, instale o MCP excel. Etc."_

Cada install é fricção. Cada server externo é mais um ponto de falha,
uma versão para acompanhar, uma vulnerabilidade potencial. **Vectora
inverte:** o que é alta-frequência + utilidade-ampla + estabilidade
vem nativo. O que é vendor-específico ou nicho fica na MCP Library.

---

#### Critério de inclusão como tool nativa

Uma tool entra no binário Vectora **se e somente se** cumpre os 4:

1. **Alta frequência:** > 20% dos workflows reais provavelmente usam
2. **Utilidade ampla:** serve dev, PM, marketing, design — não só 1 persona
3. **Estável:** API/CLI/biblioteca não muda toda semana
4. **Sem dependência vendor-específica:** não exige conta paga em SaaS
   específico

Tudo que falha em pelo menos 1 critério vira **plugin DLC Tier 2C**
ou **MCP de terceiro** (via MCP Library).

---

#### Inventário de tools nativas

##### Já implementadas (Vectora atual)

| Tool          | Categoria   | Status | Backend                                   |
| ------------- | ----------- | ------ | ----------------------------------------- |
| `fs_read`     | File System | ✅     | stdlib                                    |
| `fs_write`    | File System | ✅     | stdlib                                    |
| `fs_edit`     | File System | ✅     | stdlib + difflib                          |
| `fs_grep`     | File System | ✅     | ripgrep wrap                              |
| `fs_glob`     | File System | ✅     | pathlib                                   |
| `fs_tree`     | File System | ✅     | stdlib                                    |
| `git_*`       | Git         | ✅     | subprocess gitpython                      |
| `gh_*`        | GitHub      | ✅     | `gh` CLI wrap                             |
| `web_search`  | Web         | ✅     | Tavily v2 via langchain-tavily            |
| `web_fetch`   | Web         | ✅     | httpx                                     |
| `rag_search`  | RAG         | ✅     | LanceDB/Qdrant + Cohere rerank            |
| `rag_add`     | RAG         | ✅     | embedding queue                           |
| `workspace_*` | Workspace   | ✅     | LangGraph store + filesystem              |
| `memory_*`    | Memory      | ✅     | LangGraph SqliteStore/PostgresStore       |
| `mcp_call`    | MCP         | ✅     | mcp-client (delegação para MCPs externos) |
| `terminal`    | Terminal    | ✅     | PTY (xterm.js no chat)                    |
| `skill_*`     | Skills      | ✅     | skill resolver                            |

##### A adicionar — Onda 1 (pré-lançamento, crítico)

| Tool           | Categoria | Backend Python            | Justificativa                                                      |
| -------------- | --------- | ------------------------- | ------------------------------------------------------------------ |
| `time_*`       | Time/Date | `datetime`, `zoneinfo`    | Trivial e usado constantemente                                     |
| `http_request` | Network   | `httpx`                   | REST client genérico — alternativa explícita a "fetch with method" |
| `hash_*`       | Crypto    | `hashlib`                 | SHA/MD5/etc. para uso quotidiano                                   |
| `jwt_decode`   | Crypto    | `PyJWT`                   | Debug de auth é uso comum                                          |
| `base64_*`     | Encoding  | stdlib                    | Trivial mas frequente                                              |
| `regex_test`   | Util      | stdlib                    | Validar regex sem leave-and-test no chat                           |
| `json_*`       | Util      | stdlib + `jq`-like via py | Manipulação de JSON sem REPL                                       |

##### A adicionar — Onda 2 (pós-lançamento Q3, alta demanda)

| Tool                  | Categoria | Backend                   | Justificativa                                 |
| --------------------- | --------- | ------------------------- | --------------------------------------------- |
| `browser_screenshot`  | Browser   | Playwright                | QA + scraping + verificação visual            |
| `browser_navigate`    | Browser   | Playwright                | Multi-step browser automation                 |
| `browser_fill_form`   | Browser   | Playwright                | Auth flows, smoke tests                       |
| `browser_extract`     | Browser   | Playwright + Cheerio      | Scraping estruturado                          |
| `db_query`            | Database  | sqlalchemy + drivers      | PostgreSQL/MySQL/SQLite/SQLServer (read-only) |
| `db_introspect`       | Database  | sqlalchemy reflection     | Lista tables/columns/relations                |
| `db_migrate`          | Database  | alembic wrap (HITL gated) | Apply migration (com aprovação humana)        |
| `code_python`         | Code Exec | subprocess sandbox        | REPL persistente Python (Deep Agents Bloco I) |
| `code_node`           | Code Exec | subprocess sandbox        | REPL persistente Node                         |
| `code_shell`          | Code Exec | (já existe via terminal)  | —                                             |
| `sequential_thinking` | Reasoning | Anthropic MCP spec nativo | Chain-of-thought tool padrão MCP              |

##### A adicionar — Onda 3 (capabilities de output não-código)

| Tool                 | Categoria     | Backend                | Justificativa                                 |
| -------------------- | ------------- | ---------------------- | --------------------------------------------- |
| `pdf_read`           | Documents     | pypdf                  | PDF é input universal                         |
| `pdf_extract_tables` | Documents     | pdfplumber + camelot   | Tabelas em PDF é uso comum                    |
| `pdf_generate`       | Documents     | reportlab / weasyprint | Gerar PDF a partir de Markdown/HTML           |
| `pdf_merge_split`    | Documents     | pypdf                  | Manipulação básica                            |
| `xlsx_read`          | Office        | openpyxl               | Excel é onipresente em empresas               |
| `xlsx_generate`      | Office        | openpyxl               | Gerar planilha com fórmulas + formatação      |
| `docx_read`          | Office        | python-docx            | Word é onipresente                            |
| `docx_generate`      | Office        | python-docx            | Gerar relatório com formatação                |
| `pptx_generate`      | Office        | python-pptx            | Apresentações para liderança/clientes         |
| `csv_read_write`     | Data          | pandas                 | CSV universal                                 |
| `chart_generate`     | Visualization | matplotlib + plotly    | Retorna asset_id de imagem (alinhado ia-plus) |
| `dashboard_generate` | Visualization | HTML+Chart.js+Tailwind | Dashboard standalone que abre no browser      |
| `diagram_mermaid`    | Visualization | mermaid-cli            | Diagrama via texto                            |
| `diagram_plantuml`   | Visualization | plantuml jar           | UML legacy mas comum                          |
| `diagram_graphviz`   | Visualization | graphviz               | DAGs, fluxogramas                             |

##### A adicionar — Onda 4 (mídia + análise)

| Tool                       | Categoria | Backend           | Justificativa                    |
| -------------------------- | --------- | ----------------- | -------------------------------- |
| `image_resize_crop`        | Image     | Pillow (PIL)      | Manipulação básica sem chamar IA |
| `image_convert_format`     | Image     | Pillow            | PNG ↔ JPEG ↔ WebP                |
| `image_metadata`           | Image     | Pillow + exifread | EXIF, dimensões, etc.            |
| `image_ocr`                | Image     | Tesseract         | OCR sem pagar API                |
| `audio_convert`            | Audio     | FFmpeg wrap       | Formato + sample rate + duration |
| `audio_extract_from_video` | Audio     | FFmpeg wrap       | Preparação para STT              |
| `video_thumbnail`          | Video     | FFmpeg wrap       | Frame extraction                 |
| `archive_zip_tar`          | Files     | stdlib            | Compactar/descompactar           |

##### A adicionar — Onda 5 (infra/devops)

| Tool             | Categoria | Backend      | Justificativa                            |
| ---------------- | --------- | ------------ | ---------------------------------------- |
| `dns_lookup`     | Network   | dnspython    | Debug de DNS é comum                     |
| `port_check`     | Network   | socket       | "Tá ouvindo na porta X?"                 |
| `traceroute`     | Network   | subprocess   | Debug de rede                            |
| `whois`          | Network   | python-whois | Domínio, IP                              |
| `docker_ps_logs` | DevOps    | docker SDK   | Read-only: list, logs, inspect           |
| `kubectl_read`   | DevOps    | kubectl wrap | Read-only: get pods/deployments/services |
| `process_list`   | OS        | psutil       | Lista processos + uso de recursos        |

---

#### O que **fica de fora** das tools nativas (e por quê)

##### Conectores vendor-específicos → Plugins DLC Tier 2C

| Service                            | Por que não nativo                                                                                            |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Notion, Jira, Linear, Figma, Slack | Cada um exige OAuth, manutenção de API mutável, gerenciamento de webhooks. Vira plugin first-party (Tier 2C). |
| Google Workspace                   | Auth pesada, escopos complexos. Plugin DLC.                                                                   |
| Datadog, Sentry, Grafana           | Observability é vertical específico (`documents/observability.md`).                                           |
| Stripe, Shopify, HubSpot           | Commerce/CRM tem ciclo de vida próprio. Plugin DLC.                                                           |
| AWS/GCP/Azure CLIs                 | Auth complexa + risco de custo descontrolado. Plugin (futuro).                                                |

##### MCPs do ecossistema → MCP Library

Tudo que não cabe nativo nem em plugin first-party fica disponível via
MCP Library — user instala sob demanda (`documents/extensibility-roadmap.md`).

##### Capacidades pesadas/regulatórias → fora de escopo

| Capacidade                      | Por quê fora                                                            |
| ------------------------------- | ----------------------------------------------------------------------- |
| Compilação de C++/Rust/Swift    | Vectora não distribui compiladores; user instala se precisar            |
| GPU compute (CUDA, etc.)        | Não temos como portar sem inflar o binário 5×                           |
| Drivers de hardware específicos | Fora do escopo de produtividade                                         |
| Crypto operacional (carteiras)  | Risco regulatório / financeiro                                          |
| Geração de vídeo                | Custo/latência inviáveis (já documentado em `extensibility-roadmap.md`) |

---

#### Render hints novos derivados das tools

Cada tool com output não-trivial precisa de render hint correspondente
em `vectora/frontend/lib/types/render.ts`:

```ts
export type RenderHint =
  | ...existentes...
  | "browser_screenshot"     // imagem com URL + timestamp
  | "db_result"              // tabela + query original + count + duration
  | "pdf_preview"            // primeira página + N pages + download
  | "xlsx_preview"           // primeiras N linhas + count + download
  | "pptx_preview"           // thumbnail dos primeiros slides + download
  | "docx_preview"           // primeiro parágrafo + page count + download
  | "dashboard_preview"      // iframe sandboxed + open-in-new-tab
  | "diagram_render"         // SVG inline + source toggle
  | "chart_inline"           // alias de image_preview com hint de source
  | "json_tree"              // JSON colapsível interativo
  | "regex_test"             // teste de regex com match highlights
  | "transcript"             // já em ia-plus
  | "audio_player"           // já em ia-plus
  | "image_preview"          // já em ia-plus
  | "image_grid";            // já em ia-plus
```

---

#### Implementação: estrutura proposta

```
backend/
├── tools/
│   ├── __init__.py            # ALL_TOOLS registry
│   ├── fs.py                  # File system (já existe)
│   ├── git.py                 # Git/GitHub (já existe)
│   ├── web.py                 # Web/Tavily (já existe)
│   ├── rag.py                 # RAG (já existe)
│   ├── memory.py              # Memory (já existe)
│   ├── mcp.py                 # MCP client (já existe)
│   ├── terminal.py            # Terminal/PTY (já existe)
│   ├── time.py                # NOVO Onda 1
│   ├── http.py                # NOVO Onda 1
│   ├── crypto.py              # NOVO Onda 1 (hash, jwt, base64)
│   ├── util.py                # NOVO Onda 1 (regex, json)
│   ├── browser/               # NOVO Onda 2
│   │   ├── __init__.py
│   │   ├── playwright.py
│   │   └── scraping.py
│   ├── database/              # NOVO Onda 2
│   │   ├── __init__.py
│   │   ├── query.py
│   │   ├── introspect.py
│   │   └── migrate.py
│   ├── code_exec/             # NOVO Onda 2 (alinhado Deep Agents)
│   │   ├── __init__.py
│   │   ├── python.py
│   │   └── node.py
│   ├── pdf.py                 # NOVO Onda 3
│   ├── office/                # NOVO Onda 3
│   │   ├── __init__.py
│   │   ├── xlsx.py
│   │   ├── docx.py
│   │   ├── pptx.py
│   │   └── csv.py
│   ├── viz/                   # NOVO Onda 3
│   │   ├── __init__.py
│   │   ├── chart.py
│   │   ├── dashboard.py
│   │   └── diagram.py
│   ├── media/                 # NOVO Onda 4 (compartilha com ia-plus)
│   │   ├── __init__.py
│   │   ├── image.py
│   │   ├── audio.py
│   │   └── video.py
│   └── infra/                 # NOVO Onda 5
│       ├── __init__.py
│       ├── network.py
│       ├── docker.py
│       └── k8s.py
```

Cada tool herda da base com:

- Metadata padronizada (`render_hint`, `category`, `destructive`, `icon`,
  `cost_estimate`, `requires_internet`, `requires_filesystem`)
- HITL automático se `destructive=True`
- Logging estruturado
- Tier gating via `services/tool_resolver.py`

---

#### Impacto no tamanho do binário

Preocupação legítima: cada tool nativa adiciona peso ao Nuitka onefile.

Estimativa por onda:

| Onda | Tamanho extra Python deps | Notas                                                         |
| ---- | ------------------------- | ------------------------------------------------------------- |
| 1    | ~2 MB                     | stdlib + httpx + PyJWT                                        |
| 2    | ~120 MB ⚠️                | Playwright drivers (~80 MB) + alembic + drivers DB            |
| 3    | ~40 MB                    | reportlab + openpyxl + python-docx + python-pptx + matplotlib |
| 4    | ~50 MB                    | Pillow + Tesseract + FFmpeg estático ⚠️                       |
| 5    | ~10 MB                    | dnspython + psutil + docker SDK                               |

**Total estimado: ~220 MB extras** — Vectora hoje sai em ~150 MB, ficaria
~370 MB. Aceitável para desktop install, **pesado para Docker base
image** e **alto demais para Termux Android**.

##### Estratégia de mitigação

**Modular install via Nuitka onefile com extensões lazy-loaded:**

```
vectora-base.exe       (150 MB)  — core + Ondas 1 e 5
vectora-pack-office    (40 MB)   — Onda 3
vectora-pack-browser   (80 MB)   — Onda 2 (Playwright)
vectora-pack-media     (50 MB)   — Onda 4
vectora-pack-data      (40 MB)   — Onda 2 (DB drivers + alembic)
```

Comportamento:

- Instalação default baixa `vectora-base` apenas
- Primeira chamada a tool de pack não-instalado dispara prompt:
  _"Esta ferramenta requer o pack 'browser' (80 MB). Instalar agora?"_
- Download in-place (sem reboot do Vectora)
- Verificação de assinatura GPG por pack

**Resultado:** binário base leve, capabilities full disponíveis sob
demanda, sem inflar usuários que não precisam.

---

#### Comparação honesta com concorrentes

| Tool nativa proposta       |  Vectora  |      Claude Code      | Cursor |  Aider   | Continue |
| -------------------------- | :-------: | :-------------------: | :----: | :------: | :------: |
| File system completo       |    ✅     |          ✅           |   ✅   |    ✅    |    ✅    |
| Git/GitHub                 |    ✅     |          ✅           |   ✅   |    ✅    | Parcial  |
| Terminal persistente       |    ✅     |          ✅           |   ✅   |    ❌    |    ❌    |
| RAG sobre projeto          |    ✅     |        Parcial        |   ✅   | Repo-map |    ✅    |
| Browser automation         | 🔄 Onda 2 |       MCP ext.        |   ❌   |    ❌    |    ❌    |
| Database query             | 🔄 Onda 2 |       MCP ext.        |   ❌   |    ❌    |    ❌    |
| Code REPL sandboxado       | 🔄 Onda 2 |          ❌           |   ❌   |    ❌    |    ❌    |
| PDF gen/read               | 🔄 Onda 3 |       MCP ext.        |   ❌   |    ❌    |    ❌    |
| Excel gen/read             | 🔄 Onda 3 |       MCP ext.        |   ❌   |    ❌    |    ❌    |
| PowerPoint gen             | 🔄 Onda 3 |          ❌           |   ❌   |    ❌    |    ❌    |
| Word gen/read              | 🔄 Onda 3 |       MCP ext.        |   ❌   |    ❌    |    ❌    |
| Charts/Plotly              | 🔄 Onda 3 |          ❌           |   ❌   |    ❌    |    ❌    |
| Mermaid/PlantUML/Graphviz  | 🔄 Onda 3 |          ❌           |   ❌   |    ❌    |    ❌    |
| OCR Tesseract              | 🔄 Onda 4 |          ❌           |   ❌   |    ❌    |    ❌    |
| Image manipulação básica   | 🔄 Onda 4 |          ❌           |   ❌   |    ❌    |    ❌    |
| Audio convert (FFmpeg)     | 🔄 Onda 4 |          ❌           |   ❌   |    ❌    |    ❌    |
| Time/timezone tools        | 🔄 Onda 1 |          ❌           |   ❌   |    ❌    |    ❌    |
| JWT decode / hash / base64 | 🔄 Onda 1 |          ❌           |   ❌   |    ❌    |    ❌    |
| Sequential thinking        | 🔄 Onda 2 | ✅ extension thinking |   ❌   |    ❌    |    ❌    |
| Docker/k8s read-only       | 🔄 Onda 5 |       MCP ext.        |   ❌   |    ❌    |    ❌    |

**Diferencial competitivo claro:** Vectora oferece batteries-included
em escala que nenhum concorrente match.

---

#### Cronograma de implementação

```
Pré-lançamento (próximos 3 meses)
  Onda 1: Time, HTTP, Crypto, Util — ~1 sprint (1 semana)

Pós-lançamento Q1
  Onda 5: Infra (DNS, ports, Docker, k8s) — ~1 sprint
  Beta program (documents/launch-and-distribution.md) para Onda 2/3

Pós-lançamento Q2
  Onda 2: Browser + DB + Code REPL — ~3 sprints
   (browser é o mais pesado; DB inclui HITL para migrate)

Pós-lançamento Q3
  Onda 3: Office (PDF, Excel, Word, PowerPoint, Charts, Diagrams) — ~3 sprints

Pós-lançamento Q4
  Onda 4: Media (Image, Audio, Video, OCR) — ~2 sprints
   (alinhado com sprints M5/M6 de ia-plus)
```

---

#### Princípios cardinais

1. **Nativo > MCP quando frequência justifica.** Não criar plugin para o
   que 80% dos users vai querer no dia 1.

2. **Plugin DLC > nativo quando vendor-específico.** Notion não vira
   nativo nunca — a API muda demais, requer OAuth, etc.

3. **MCP Library > plugin quando vertical.** Para nichos onde Vectora
   não compete, ecossistema cobre.

4. **Tudo é tool, nada é mágica.** Toda capability passa pelo mesmo
   pipeline de tool calling, com mesmo render hint, mesma rastreabilidade.

5. **HITL para destrutivo.** Migrate de schema, delete de arquivo, send
   email — sempre passa por aprovação humana (configurável).

6. **Modularidade no install, não no código.** Tools agrupadas em packs
   instaláveis sob demanda para não inflar o binário base.

7. **Sandbox por padrão para code execution.** REPL Python/Node roda em
   container isolado; FS access mediado; network gated.

8. **Cost estimate antes de operações caras.** Toda tool que custa
   ($) declara estimate; HITL gate por threshold configurável.
