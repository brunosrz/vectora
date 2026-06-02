# Vectora — Plano Mestre (rev. junho/2026)

> Plano consolidado do produto **Vectora** (backend `src/` + chat `chat/`)
> mais o ecossistema da **Vectora Company** (site, billing, marketing).
>
> **Reorganização** desta revisão: tudo o que foi entregue até T.13 está
> condensado nos **blocos A–C**. As fases pendentes do produto ocupam
> **D–J** (distribuição, deep agents, storage, cache, REST API). O hardening
> profissional fica em **K–N** (billing/SDK/observability/IDE). A
> **Vectora Company** ocupa **O–S** (legal, site, docs, suporte, marketing).
>
> Fora de escopo deste plano (mantidos como documentos separados em
> `docs/oem.md` e `docs/pitch_deck.md`): **OEM**, **Vectora Cloud**, **Data
> Store**. São iniciativas pós-lançamento e não entram no roadmap atual.

---

## Sumário (TOC)

| Bloco | Tema                                                                                                                          | Status       |
| ----- | ----------------------------------------------------------------------------------------------------------------------------- | ------------ |
| **A** | UX & Chat Foundation — base do chat, polish, reasoning/HITL, file handling, i18n, mobile                                      | ✅ Concluído |
| **B** | Security & Workflow — auth/RBAC, workspaces+git, slash commands, conversation, admin, OAuth                                   | ✅ Concluído |
| **C** | Power Features — plugins MCP, skills, terminal/workbench, memória, settings, workspaces remotos, license gate, OXC            | ✅ Concluído |
| **D** | Distribuição Comercial — Nuitka launcher + frontend bundle + Electron + instaladores assinados + auto-update                  | ⏳ Planejado |
| **E** | Deep Agents — refactor para `create_deep_agent` + TUI textual                                                                 | ⏳ Planejado |
| **F** | Storage Infrastructure — hardening lite + schema versioning + langgraph.{checkpoint,store} + LanceDB/Qdrant/Postgres + BaaS   | ⏳ Planejado |
| **G** | Cache Distribuído — Redis (KV + LLM bind invalidation + usage + rate-limit + langchain-redis)                                 | ⏳ Planejado |
| **H** | Deep Agents 1 — skills nativas, AGENTS.md, prompt cache, compressão, 6 web tools full                                         | ⏳ Planejado |
| **I** | Deep Agents 2 — sandbox + worktree, interpreters, async subagents, ACP, remote backends                                       | ⏳ Planejado |
| **J** | REST API v1 — OAuth2 client credentials + OpenAI-compat + ACP público                                                         | ⏳ Planejado |
| **K** | Billing & License Infra — Supabase + Stripe + Asaas (PIX/boleto) + tier enforcement + banners                                 | ⏳ Planejado |
| **L** | SDKs & API Ecosystem — Python/TS SDKs, webhooks, GitHub Actions, OpenAPI polish                                               | ⏳ Planejado |
| **M** | Observability & Reliability — OpenTelemetry, Sentry, health probes, SLOs, backup/DR                                           | ⏳ Planejado |
| **N** | Distribution Hardening & IDE Integrations — signing pipeline, auto-update, Docker, distros, VS Code/JetBrains/Zed/Neovim, n8n | ⏳ Planejado |
| **O** | Vectora Company: Identidade & Legal — CNPJ/MEI, marca, domínios, termos, emails                                               | ⏳ Planejado |
| **P** | Vectora Company: Site `vectora.company` — landing, signup, dashboard, pricing, FAQ                                            | ⏳ Planejado |
| **Q** | Vectora Company: Docs `docs.vectora.company` — guides, reference, self-hosting, changelog                                     | ⏳ Planejado |
| **R** | Vectora Company: Suporte & Comunidade — WhatsApp, email, GitHub Issues, status page, beta                                     | ⏳ Planejado |
| **S** | Vectora Company: Marketing & Lançamento — PyPI 1.0 + Docker oficial + kit influencers + canais + cronograma                   | ⏳ Planejado |

**Ordem sugerida de implementação:**
`D → E → F → G → H → I → J → K → L → M → N → O → P → Q → R → S`

Blocos D–J podem rodar em **paralelo parcial** (E↔F são independentes;
H/I dependem de E; J depende de F). Blocos K–N podem rodar em paralelo
parcial após D estar pronto. O–S são sequenciais (legal precede site
precede docs precede suporte precede marketing).

---

## Diretrizes (vinculantes para todo PR)

### 1. Comentários em código são documentação, não diário

Comentários descrevem **o que o código faz** e invariantes que precisa
preservar.

**Proibido:** identificadores de planejamento (`Bloco T`, `T10.4`),
justificativa histórica (`antes era X`), "por quê" estratégico
(`para alinhar ao roadmap`), TODOs sem dono.

**Esperado:** invariantes não-óbvios, restrições que o tipo não
captura, mapeamentos sutis a APIs externas, pegadinhas que travariam
o leitor.

Refactor imediato ao editar: comentário com referência de bloco →
reescrever no diff.

### 2. Strings de UI sempre via i18n — nada hardcoded

Qualquer string visível no chat passa por `useT()` e existe em
`chat/lib/i18n/strings.csv.ts` nas 3 línguas (`en`, `es`, `pt-BR`).
Adicionar string nova = adicionar 3 colunas no CSV. Mesma regra
vale para `src/ui/` (rich/textual).

### 3. TDD + type hints obrigatórios

- **TDD**: bug → teste primeiro; feature → 1 happy + 1 erro.
- **Python**: `Any` só com justificativa; `uv run ty check src
tests` em verde.
- **TypeScript estrito**: `pnpm tsc --noEmit` verde.
- **OXC**: `pnpm --dir chat exec oxlint` verde no pre-commit.

### 4. Nomes referenciam o presente

Sem `LegacyFoo`, `NewFoo`, `FooV2`. Quando renomeamos, renomeamos
por completo.

### 5. Integrações sempre via SDK oficial mais recente

Toda LLM, embedding, vector store, cache e rerank entra via
`langchain-<provider>` ou o SDK oficial **na última versão estável**.
Nada de imports deprecados.

### 6. Chat-first significa schema-first

Backend declara intenção via `metadata={"render_hint": ...}` nas
tools e eventos tipados no proto. O chat dispatcha visualmente
sem código por tool nova.

### 7. Auth-first para tudo server

Qualquer endpoint novo no `src/api/` considera permissões.
`Depends(get_current_user)` é o default. Rotas públicas
(`/auth/*`, `/health`, `/license/*`, `/docs`) são whitelist
explícita.

### 8. Backend é fonte de verdade

Cache cliente é stale-while-revalidate. Reload sempre vai ao
backend. Nunca persistir state crítico só em localStorage.

---

## BLOCO A — UX & Chat Foundation [CONCLUÍDO]

> Resumo condensado dos blocos antigos **A, B, D, E, F (+F.2/F.3/F.4),
> M (+M6–M10), J (+J.2), K (+K.2), L, R (+R6–R10)**. Tudo que toca a
> experiência visual e a fundação do chat web.

### A1 — Chat Foundations & Schema-Driven Rendering

Base completa do chat: backend FastAPI + SSE (`src/api/server.py`,
`handlers/chat.py`, `handlers/threads.py`, `adapters.py`,
`schemas.py`), proto Connect-RPC (`StreamChat`, `ResumeChat`,
`GetTools`, `Create/Get/List/Delete Thread`, `GetHistory`, `/health`,
`/metrics`). Frontend Next.js 16 + Hono (`chat/server/index.ts` +
rotas em `chat/server/routes/`) montado no App Router via
`chat/app/api/[[...route]]/route.ts`. Stack: React 19 + Turbopack +
Zustand 5 + shadcn/ui + Tailwind.

Tools com `metadata={"render_hint", "category", "destructive",
"icon"}` em todas as 17 tools (`src/tools/*.py`). Endpoint
`GET /tools/schema` expõe registry para o frontend. Dispatcher em
`chat/components/chat/tool-call-renderer.tsx` decide componente por
`render_hint`: `JsonViewer`, `DiffViewer`, `CodeBlockViewer`,
`TerminalBlock`, `SearchResultsViewer`, `TableViewer`, `QueueBadge`,
`QueueProgress`, `ArtifactCard`. Adicionar render hint novo = 1 linha
no `RenderHint` type + 1 componente + entry no dispatcher.

SSE heartbeat (`: heartbeat` a cada 25s) + `X-Accel-Buffering: no`
para nginx-friendly streaming. Observabilidade: `VectoraTracer`
SQLite + `GET /metrics` (últimos 50 spans).

### A2 — Polish, Branding & Models Registry

Migração completa do fork `chat-langchain`: `chat/src/` deletado,
deps LangSmith out, package renomeado `vectora-chat`. Modelos reais
sincronizados com `AVAILABLE_MODELS` Python — 25 modelos em
`chat/lib/config/deployment-config.ts` (6 Google Gemini 3.x+2.5, 12
OpenAI 5.5/5.4/5/4.1+o3/o4-mini, 3 Anthropic Claude 4.7/4.6/4.5, 4
Cohere). Default `gemini-2.5-flash`.

Branding: favicons multi-res, `Assistant Icon.svg` com pássaro
Vectora navy+azul-claro, welcome screen, header, sidebar, Open Graph.
Pipeline via `resvg-py` + Pillow (zero deps de sistema, Windows
friendly).

React 19 + Next 16 compat: `RefObject<T | null>`,
`useRef<T | undefined>(undefined)`, `hono/vercel handle()` retorna
função única. Turborepo 11.2.2 + Turbopack `--turbopack`.

Bug-fixes estruturais: thinking timer + stream error handling com
`finally` defensivo; markdown envelope protocol (6 backticks +
`stripMarkdownEnvelope()` streaming-safe); filtro de tokens de
structured-output no `adapters.py`; dead code cleanup; server
lifecycle robusto (`_lifespan` + `asyncio.gather` shutdown +
`VECTORA_SHUTDOWN_TIMEOUT_S` + `os._exit(0)`). Logs auditáveis:
`_BackgroundConsoleFilter` silencia langsmith/uvicorn.access/fastapi.

### A3 — Reasoning Reveal + Thinking UX + HITL + Permission Modes

**Reasoning**: backend emite `ThinkingEvent` no `on_chain_end` do
orchestrator com `reason`, `delegate_to`, `task_query`. Frontend:
`Message.thinking?: string` + bloco colapsado acima da resposta.
Stream de progresso semântico via `chat/lib/constants/node-labels.ts`
("Routing: search", "Synthesizing 5 documents…"). Per-node duration
badges. Dev mode (`?dev=1`) expõe decisão completa.

**HITL** (`interrupt_before` no LangGraph): `HITLEvent` no proto com
`tool_name`, `args_json`, `interrupt_id`, `diff_preview`. 4 ações:
**Approve**, **Edit** (JSON editor), **Reject** (com feedback),
**Respond** (mensagem humana como resultado). `ResumeChat({thread_id,
interrupt_id, decision})` retoma. Diff preview para
`file_edit`/`file_write` via `DiffViewer`. Configuração por categoria
de tool em Settings → Chat. Default seguro: `requireHitl: true`.

**5 modos de permissão** (R2) consumidos em `vectora/graph.py` via
`interrupt_before` dinâmico:

- **Solicitar permissões** — HITL em toda destrutiva
- **Aceitar edições** — auto-aprova `file_edit`/`file_write`
- **Modo de planejamento** — plan-only, recusa destrutivas
- **Modo automático** — auto-aprova dentro do workspace confiável
- **Ignorar permissões** — full-auto (ainda bounded por scope guard)

Chip "Modo" no command-bar + atalho ⇧Ctrl M. Persistido por user.

### A4 — File Handling Completo + Safe Roots + Paste-as-File

**Multimodal & ingestão** (`StreamChatRequest.attachments`):
`HumanMessage(content=[{"type": "image_url", ...}])` em
`handlers/chat.py`. Suporte image, PDF, código (texto inline até
N kB). PDF preview via `pdf.js` client-side. Drag-and-drop na
sidebar → "Adicionar ao RAG" com streaming `queue_progress`.

**MAX_INPUT_CHARS removido** (herdado do chat-langchain):
eliminado de `chat/lib/constants/features.ts`. `LARGE_PASTE_THRESHOLD
= 4000` chars: paste > threshold vira `pasted-<ts>.txt` attachment
(padrão ChatGPT) via `chat-interface.tsx::handleInputPaste`. Removido
`maxLength` no textarea.

**Safe Roots** (cap de path por admin):

- Modelo `SafeRoot` (`src/types/safe_root.py`): `id` (sha256[:8]),
  `path`, `label`, `created_by`, `builtin`.
- `SafeRootRegistry` (`src/services/safe_roots.py`) singleton com
  persistência em `~/.vectora/safe_roots.json`. Auto-popula
  `~/Documents/vectora` como builtin (não-removível).
- `BrowseDir` valida path contra registry; 403 quando user comum
  tenta escapar; default = safe-root mais próximo do `$HOME`.
- API admin (`/admin/safe-roots/*`, `require_admin`): GET/POST/PATCH/
  DELETE; builtin nunca removível.
- Frontend: aba "Pastas Seguras" em Admin com CRUD. Path editável
  no trust dialog (Input + Enter + "Ir"), erro 403 inline. Sidebar
  ganha grupo "PASTAS" colapsável (workspaces ativos + safe-roots).

### A5 — i18n CSV-Driven, Theme & Idioma

Sistema CSV puro em `chat/lib/i18n/strings.csv.ts` — 3 colunas
`en`, `es`, `pt-BR` (~440 chaves). Parser próprio (~20 linhas),
cache constante `TRANSLATIONS`, interpolação `{varName}`. Hook
`useT()` subscreve só ao slice `language` do settings-store.
`I18nProvider` em `chat/app/layout.tsx` atualiza
`document.documentElement.lang`. Detecção automática:
`localStorage` → `navigator.language` → `"en"`.

Tema dark/light/system via `theme-provider.tsx` (next-themes).
Chat Settings e Preferências ambos têm seletor de tema + idioma.
Persistido por user em `vectora-settings-{user_id}`.

Cobertura: header, sidebar ("Sessions/Sessões"), user-menu,
chat-input, message-item, settings-dialog, HITL panel, welcome
state, atalhos de teclado, error toasts. Empty states, tooltips,
aria-label, placeholders — todos via `t()`. Rename Threads →
Sessions feito nos **valores** do CSV (chaves preservadas).

### A6 — Mobile, PWA & Touch

**LAN/Tailscale**: `next.config.mjs` com `allowedDevOrigins`
expandido (`100.*`, RFC1918 ranges) + override
`NEXT_DEV_ALLOWED_ORIGINS`. Login mobile funciona — `Set-Cookie`
sem `Secure` em HTTP, sem `Domain`.

**PWA**: `chat/public/manifest.json` (standalone, theme `#0a0e1a`,
ícones 32/600), `chat/public/service-worker.js` (cache-first shell

- assets versionados, network-first HTML, bypass APIs/WS). Registro
  em `app/layout.tsx` com guard `NODE_ENV === "production"`.

**Sidebar mobile**: `<768px` vira `Sheet` (shadcn) ativado por
hamburger. Workbench mobile: `Sheet` overlay com swipe-down.

**Touch polish**: olho da senha com `onPointerDown + preventDefault

- onTouchStart` fallback; tap targets ≥ 44×44px; auto-resize
  textarea respeita keyboard.

### A7 — Live Metrics + Usage Popover + Performance

**`GET /auth/usage`** enriquecido com 3 janelas: `context` (used/
window/model), `five_hour` (used/limit/resets), `weekly` (used/
limit/resets). Janela de contexto vem de `MODELS[id].context_window`;
janelas 5h/semanal do `services/rate_limit.py`.

**`usage-popover.tsx`** estilo Claude Code: barras horizontais
semafóricas (verde <60%, amarelo 60–85%, vermelho >85%) via
`getUsageColor()` em `chat/lib/utils/usage.ts`. Formatador
`formatTokens(n)` ("1.2k", "174.2k", "1.0M"). Chip clicável no
command-bar substitui o `context-meter` text-only deprecated.

Per-message badges em `message-item.tsx`: `⏱ 2.3s · 🪙 1.4k in /
320 out · 🛠 3 tools · 📚 2 RAG hits`. Hook `useUsage()` com SWR
30s + on-focus + after-response.

**Performance** (M1–M5):

- `@tanstack/react-virtual` em `message-list.tsx` acima de 50
  mensagens; `overscan: 4`; `measureElement` via ResizeObserver.
- `requestAnimationFrame` batching em `use-stream-handler.ts`
  (tokens acumulados em `pendingTokenBatch`, único `setMessages`
  por frame ~60fps); reset robusto de `flushScheduled` em
  `try/catch/finally/abort`.
- Auto-scroll inteligente: `shouldAutoScrollRef`, botão flutuante
  "Voltar ao fim", `MutationObserver` + estabilização de
  `scrollHeight` no load inicial.
- Loading skeletons; optimistic retry (`Message.isError` + botão
  RefreshCw); thread otimista (`addOptimisticThread()` antes do
  streaming, substituição sem flash).

### A8 — Settings Architecture, Command Bar, Plus Menu & Unified Input

**Settings** (`chat/components/layout/settings-dialog/`): 8 tabs —
Conta, Preferências, Memória, Integrações, Plugins, Skills, Envs,
Administração. Store: `settings-store.ts` com `persist` +
`partialize` chave por user_id.

**Chat Settings** (`agent-settings.tsx`): Mostrar tool calls,
Confirmar destrutivas (default `true`), Verbosity (Concisa/Normal/
Detalhada), tema, idioma. Agent Type e Recursion Limit legados
removidos.

**Command bar** (`features/command-bar.tsx`): chip `Local`/
`<hostname>` (não mais "Server"), workspace selector com badge
SSH/Codespace, branch (eleva `git-status-badge.tsx`), worktree,
botão "novo".

**Plus menu** (`features/plus-menu.tsx`): popover de anexos —
Adicionar arquivos/fotos (Ctrl+U), Adicionar pasta (trust dialog),
Comandos de barra (autocomplete), Conectores → deep-link
Integrações, Adicionar plugins → Plugins.

**Reasoning effort**: dropdown duplo Modelos (⇧Ctrl I) + Esforço
(⇧Ctrl E, Baixa/Média/Alto/Max) → `reasoning_effort` no
configurable. Modo rápido toggle desliga thinking.

**Welcome unificado** (F.2): `welcome-screen.tsx` deletado.
`ChatInterface` renderiza **sempre** `chat-input.tsx`. Header
condicional (`empty-state-header.tsx`) "O que posso fazer por você?"
acima do mesmo input quando `messages.length === 0`. Plus-menu,
command-bar, model selector e context-meter disponíveis desde
o primeiro carregamento. Drop hint expandido via prop. Bubble AI
com `pb-3` + `mt-2` no footer (sem buraco).

---

## BLOCO B — Security, Workspaces & Conversation [CONCLUÍDO]

> Resumo condensado dos blocos antigos **C, G (+G.2), H, I, O, P, Q
> (+Q1–Q8)**. Tudo que toca segurança, RBAC, workspaces, git, slash
> commands, busca/export/share, integrações OAuth e painel admin.

### B1 — Authentication, RBAC & Vault (KeePassXC)

**Identity model** (`src/services/auth.py`): `User`, `Session`,
`Role`, `Credentials`. Password hash via `argon2-cffi` (Argon2id,
defaults seguros). Tabela `users(id, email, password_hash, role,
env_overrides_json, created_at, last_login_at, name)` no SQLite
principal (`~/.vectora/data/vectora.db`). Tabela `refresh_tokens
(token_hash, user_id, expires_at, revoked, created_at)`.

**Roles**: `root`, `admin`, `member`, `viewer`. RBAC em
`src/services/permissions.py`: `check_permission(user, action,
resource) → bool`. Decorator `@require_role("admin")`. Thread
ownership via `threads.user_id` (member só vê próprias; admin/root
veem todas).

**JWT** (HS256, secret em `~/.vectora/auth.key` perm 600): access
token 15min, refresh token opaco 7d rotacionado. Endpoints
(`api/handlers/auth.py`): `POST /auth/signup`, `/signin`, `/refresh`,
`/signout`, `GET /me`, `PATCH /me`, `POST /change-password`,
`GET /users`, `GET /audit`, `GET /usage`, `GET /envs`, `POST /envs`,
`DELETE /envs/{key}`.

**Middleware** (`src/api/middleware/auth.py`): `get_current_user`
dependency injetada em todos os handlers exceto whitelist
(`/auth/*`, `/health`, `/license/*`, `/docs`). 401 com
`WWW-Authenticate: Bearer` em falha. Cookie httpOnly `vectora_access`
ou `Authorization: Bearer`.

**CLI**: `vectora` local = root por default. `vectora auth
signup|login|logout|whoami|refresh` para modo authenticated. Storage:
keyring do OS (Windows Credential Manager, macOS Keychain, Secret
Service) com fallback `~/.vectora/auth.json` 0600.

**Frontend**: tela `/auth/signup` (primeiro acesso vira root via
`/auth/has-users`), `/auth/signin` (sem link "criar conta"
incondicional), invite flow `?invite=<token>` com `/auth/invite/{token}`
validation. `auth-provider.tsx` faz roteamento correto. UserMenu
dropdown (avatar redondo) → Settings → Logout. Store
`auth-store.ts`: `{user, isAuthenticated, hydrate(), logout()}`.

**Secrets vault — KeePassXC `.kdbx` por usuário** (C11):

- Layout `~/.vectora/secrets/`: `system.kdbx` (root) +
  `users/<user_id>.kdbx` (um por usuário).
- Master password derivada do password de login via PBKDF2-SHA256
  (200k iter, salt = user_id). Handle aberto na sessão; descarregado
  no logout.
- Provider `pykeepass>=4.1` em `src/services/secrets/keepass.py`
  (Protocol `SecretsProvider`: `get/set/list/delete/unlock/lock`).
  Fallback PyNaCl em `internal.py`. SSH keys em `ssh_keys.py`.
- Compatível com KeePassXC desktop / KeePass2Android / Strongbox iOS
  para auditoria offline.
- Change password re-criptografa `.kdbx` atomicamente (tempfile +
  rename).

**Envs por usuário** (C10): `effective_env = {**system_env,
**user.env_overrides}` mergeado em runtime. Tabela mascarada na aba
Envs do Settings: KEY | `••••••••` | Edit/Delete. Backend
`POST/GET/DELETE /auth/envs` já operacional.

**Audit log** (C12): tabela `audit(id, user_id, action, target_type,
target_id, timestamp, ip, user_agent, success, metadata_json)`.
Eventos: `signup`, `signin`, `signin_failed`, `signout`,
`change_password`, `refresh_token_rotation`, `thread_create/delete`,
`workspace_create/delete/switch`, `tool_call` (quando
`tool.metadata.destructive=True`). Endpoint `GET /audit` admin-only

- aba "Audit" no Settings.

**Rate limiting** (C13): `slowapi` com sliding window.
`/auth/signin`: 5/min por email (lockout 10 falhas em 1h);
`/auth/signup`: 3/hour por IP; `/auth/change-password`: 3/hour por
user; `StreamChat`: 60/min por user. Endpoint `GET /auth/usage`
reflete contadores 5h + semanal.

**Convites** (Q8): tabela `invites(token_hash PK, email, role,
created_by, expires_at, used_at)` no DB principal. Funções
`create_invite(role, email?, ttl_hours=24)`, `validate_invite(token)`,
`consume_invite(token, user_id)` em `services/auth.py`. Endpoints
admin `/admin/invites` (POST/GET/DELETE). Signup público fechado
após primeiro user; só permite via `invite_token` válido. UI no
painel `UsersPanel` admin com dialog "Convidar usuário" + lista de
pendentes.

**Onboarding pós-setup** (Q7): primeiro acesso sem usuários →
redirect direto para `/auth/signup` (setup root). Com usuários
existentes → tela de login sem opção de criar conta pública.

### B2 — Workspaces P1+P2: Trust Folder, Scope Guard Rails

**Workspace model** (`src/types/workspace.py`): `id` (sha256[:8] do
`abspath(cwd)`), `name`, `cwd`, `is_git_repo`, `git_remote`,
`git_current_branch`, `git_default_branch`, `trusted: bool`,
`trusted_at`, `trusted_by`, `transport: Literal["local","ssh",
"codespace"]`, `remote_host`, `remote_path`, `ssh_key_id`,
`codespace_name`.

**Registry** (`src/services/workspace.py`): singleton com persistência
JSON em `~/.vectora/workspaces.json`. APIs `list/get/create/trust/
git_init/set_active/create_remote`. `_migrate` legado set
`transport="local"`.

**WorkspaceService backend** (`src/api/handlers/workspaces.py`),
Connect-style sob `/vectora.workspace.v1.WorkspaceService/`:

- `GET ListWorkspaces` — lista do user
- `GET GetActiveWorkspace`
- `POST SetActiveWorkspace` `{workspace_id}`
- `POST CreateWorkspace` `{path, trust, git_init}`
- `POST TrustWorkspace` `{workspace_id}`
- `POST GitInitWorkspace` `{workspace_id}`
- `GET BrowseDir?path=` (respeita safe-roots, ver A4)
- `GET ListSafeRoots`
- `GET Codespaces`
- `POST TestSsh`
- `POST CreateRemoteWorkspace`
- `GET ListWorktrees?workspace_id=` / `POST CreateWorktree`

**Scope guard rails** (Q4): helper central
`src/services/security.py::resolve_within_workspace(path,
workspace_root) -> Path | None` — resolve absoluto e garante
`resolved.is_relative_to(workspace_root)`. Substitui o antigo
`allowed_dirs=["."]`. Aplicado em **todas** as tools de `fs.py` e
`git.py`. **`terminal`**: `create_subprocess_shell(command,
cwd=workspace_root)` — comandos rodam dentro da pasta. Mantém
blacklist `is_safe_shell_command`. Workspace `trusted=False` →
read-only (recusa write/terminal/git destrutivos com mensagem
pedindo trust).

**Auto-detect git** (G7): se `workspace.cwd` contém `.git`, ativa
"git mode" no `WorkspaceInfo` (`is_git_repo`, `git_remote`,
`git_default_branch`, `git_current_branch`).

**`git init` automático** (Q3): `git_init_repo(cwd)` em
`src/tools/git.py` (via `git.Repo.init`). Tool `git_init`
(`render_hint: code_block`). No `CreateWorkspace` com
`git_init=True`, se `is_git_repo=False` roda e re-detecta. UI
oferece no momento do trust.

**Frontend**: `workspace-selector.tsx` no header (chip + dropdown
Workspaces + "Adicionar pasta"); `workspace-trust-dialog.tsx`
(directory browser via `BrowseDir`, checkbox "Inicializar git").
Store `workspaces-store.ts` com cache stale-while-revalidate
hidratado no boot. `agentConfig.workspace_id` propagado na request.

**Workspaces remotos** (G.2): ver C6 abaixo (tabs SSH/Codespace
no trust dialog, `TransportBackend` Protocol).

### B3 — Git Integration + gh CLI + Worktrees

**Tools git** (`src/tools/git.py`):
| Tool | render_hint | destructive | HITL |
| --------------------------------------- | ------------ | ----------- | ----------- |
| `git_status` | `diff` | false | não |
| `git_log(n=10, branch?)` | `table` | false | não |
| `git_diff(ref?)` | `diff` | false | não |
| `git_branch(action, name?)` | `table` | em delete | em delete |
| `git_checkout(ref)` | `code_block` | true | sim |
| `git_commit(message, files=None)` | `code_block` | true | **sim** |
| `git_worktree(action, name?, branch?)` | `table` | em remove | em remove |
| `git_push(remote, branch, force=False)` | `code_block` | true | **sim** |
| `git_pull(remote, branch)` | `code_block` | true | sim |
| `git_stash(action, name?)` | `code_block` | em pop/drop | em pop/drop |
| `git_init` | `code_block` | false | não |

**Tools gh CLI** (`src/tools/gh.py`): `gh_pr_create(title, body,
base, draft)`, `gh_pr_list`, `gh_pr_view`, `gh_pr_review(pr_number,
verdict, body)`, `gh_pr_merge(pr_number, method="squash")` destrutivo,
`gh_issue_create/list/view/comment`. Render hints alinhados:
`code_block`/`table`/`diff` conforme natureza.

**Per-user Git auth** (G6): tools git lêem `effective_env`
(`system_env + user.env_overrides`). `gh` CLI usa `GITHUB_TOKEN` do
user via vault (B1) ou OAuth (B7). `Co-Authored-By` desligado por
default (opt-in explícito do user).

**Git status badge** (G5): header mostra `🌿 feature-auth · ↑2 ↓0 ·
●`. Click → painel inline com `git_status`. Polling 5s quando aba
ativa, pausa quando inativa. Endpoint `GET /workspaces/{id}/git/
status` cached 2s.

**Worktrees** (G8 + Q5): `git_worktree create <name>` em
`~/.vectora/worktrees/<workspace_id>/<name>` via `git worktree add`.
`thread.metadata.worktree` associa thread ↔ worktree (tools confinam
ao path da worktree). Endpoint `ListWorktrees`/`CreateWorktree`.
Frontend: secondary selector ao lado do workspace.

**PR review workflow** (G9): subagente `pr_reviewer` (delegado pelo
orchestrator) executa `gh_pr_view → git_diff origin/main...BRANCH →
gh_pr_review`. Render especial em `pr-review-view.tsx` (diff
lado-a-lado com comentários AI inline).

**Orchestrator git-aware** (G4): system prompt enriquecido com regras
(semantic commits, worktree antes de mudanças grandes, never force
push em main, `gh_issue_list` antes de feature nova).

### B4 — Slash Commands

**Autocomplete inline** com `/`: popup `slash-command-menu.tsx`
filtrado em tempo real. Cada comando: nome + descrição + arg
preview. `↑`/`↓` navega histórico (persistido em `localStorage` por
user_id).

**Registry** (`chat/lib/constants/slash-commands.ts`):

| Comando              | Ação                     | Endpoint                   |
| -------------------- | ------------------------ | -------------------------- |
| `/rag add <path>`    | Indexa pasta/arquivo     | `ingest_docs`              |
| `/rag list`          | Stats do RAG             | `GET /rag/stats`           |
| `/workspace <name>`  | Switch workspace         | `SetActive`                |
| `/clone <git-url>`   | Clona repo como ws       | G2                         |
| `/branch <name>`     | Cria/switch branch       | `git_branch`               |
| `/pr <title>`        | PR da branch atual       | `gh_pr_create`             |
| `/model <name>`      | Quick switch modelo      | client-side                |
| `/clear`             | Limpa thread (mantém ID) | DeleteThread+Create        |
| `/export [md\|json]` | Download conversa        | client-side                |
| `/share`             | URL read-only            | `POST /threads/{id}/share` |
| `/auth logout`       | Logout                   | B1                         |
| `/help`              | Lista comandos           | client-side                |

**Backend** (`src/api/handlers/share.py`): novo endpoint
`POST /threads/{id}/share` → `share_token`, tabela
`shared_threads(token, thread_id, expires_at, created_by)`.

### B5 — Conversation Features: Search, Export, Share, Edit, Branch

**Search dentro da thread + global** (I1): search bar no topo de
cada thread; search global na sidebar. Backend `POST /threads/search`
com query + scope (`current` | `all`). Respeita ownership (B1).

**Export** (I2): `.md` via `/export md` ou botão no menu da thread
(`chat/lib/utils/export/`); `.json` formato completo com metadata +
tool_calls. Render formatado com timestamps, roles, tool calls
inline.

**Share read-only** (I3): `POST /threads/{id}/share` → `share_token`.
Rota pública `/share/{token}` em `chat/app/share/[token]/page.tsx`
renderiza read-only. Storage backend `shared_threads`. Apenas owner
ou admin pode share.

**Edit message + regenerate** (I4): botão `Edit` em mensagens do
user; editar → submit → drop posteriores → re-stream. Botão
`Regenerate` em respostas (com confirmação + animação).

**Branching "Fork from here"** (I5): botão em qualquer mensagem.
Cria nova thread copiando histórico até aquela mensagem (útil para
"e se eu tivesse perguntado X em vez de Y").

### B6 — Workspace Integrations (OAuth GitHub + API Keys)

**API Key integrations** (O1) — user insere chave, vai no vault dele:
| Integração | Env var | Uso no agente |
| ----------- | --------------------- | --------------------------- |
| OpenAI | `OPENAI_API_KEY` | LLM + embeddings fallback |
| Anthropic | `ANTHROPIC_API_KEY` | Claude 4.x |
| Cohere | `COHERE_API_KEY` | Reranker + LLM + embeddings |
| Tavily | `TAVILY_API_KEY` | Web search |
| Groq | `GROQ_API_KEY` | LLM ultrafast |
| HuggingFace | `HUGGINGFACE_API_KEY` | Inference API |
| Perplexity | `PERPLEXITY_API_KEY` | Busca com citações |

Aba "Integrações" do Settings: cards com logo + status (✓/−) +
form inline (key masked + Salvar/Remover) + botão "Verificar" que
faz chamada de teste. Salva via `POST /api/auth/envs`.

**GitHub OAuth** (O2 — OAuth App):

- `GET /auth/github` → redirect GitHub OAuth (`scope=repo,user`)
- `GET /auth/github/callback?code=...` → troca por token, salva
  como `GITHUB_TOKEN` no vault, redirect chat
- `DELETE /auth/github` → revoga e remove
- `GET /auth/github/status` → `{connected, username}`
- Config (`~/.vectora/config.toml`): `[integrations.github]`
  com `client_id`, `client_secret` (em `system.kdbx`), `redirect_uri`.

Tools `git_push`, `gh_pr_create` usam `effective_env["GITHUB_TOKEN"]`
do user. Card GitHub no Settings: status badge + "Conectar"/"Desconectar"

- avatar+username pós-OAuth.

**Google / Notion / Linear OAuth** (O3–O5, futuro pós-S):
mesmo padrão; tokens no vault, scopes apropriados. Tools
`drive_*`, `notion_*`, `linear_*` consomem.

### B7 — Root Admin Panel (RBAC/ABAC Global)

Aba "Administração" no Settings (root/admin only). Sub-abas:

**Usuários** (`UsersPanel` inline em `admin-tab.tsx`):

- Tabela: email | role | último acesso | status
- Drawer com detalhes: mudar role, resetar senha, ver workspaces,
  ver envs (masked)
- Botão "Convidar usuário" (B1 — gera link 24h)

**Ferramentas** (`tool-policy-panel.tsx`):

- Checklist global de agents/tools habilitados
- ABAC: override por user ("X não pode usar terminal")
- Persistido em `~/.vectora/config.toml` + tabela
  `~/.vectora/tools/<user_id>.json`
- `tool_policy.is_allowed(user_id, name)` consultado no
  `tool_resolver` (ver C2)

**Workspaces**:

- Lista de todos os workspaces do servidor
- Assign: `user_id → workspace_id → role` (owner, writer, reader)

**Sistema**:

- Versão Vectora + chat
- Status dos serviços (LanceDB, SQLite, MCP servers)
- Métricas: requests/min, tokens/user/day, top tools

**Configuração** (`ConfigPanel`):

- `allow_public_signup` toggle
- `default_model` — **`<Select>`** com `getAllowedModels()` (não
  mais Input de texto)
- `max_recursion`

**Backend** (`src/api/handlers/admin.py`):

- `GET /admin/users` (lista com stats)
- `POST /admin/users/{id}/tools` (override de tools)
- `GET /admin/workspaces` (todos com assignees)
- `POST /admin/workspaces/{id}/assign`
- `GET /admin/system` (versão, health, métricas)
- `PATCH /admin/config`
- `POST/GET/DELETE /admin/invites`
- `GET/POST/PATCH/DELETE /admin/safe-roots` (A4)

`require_admin` em todos. Proxy Hono em `chat/server/routes/admin.ts`.

---

## BLOCO C — Power Features, Plugins, Terminal & Distribution Foundation [CONCLUÍDO]

> Resumo condensado dos blocos antigos **N, S (+S1–S8), T (T1–T11+T.X),
> T.12 (parte) + T.13, G.2 (workspaces remotos)**. Tudo que dá poder
> ao usuário avançado e a base da distribuição comercial.

### C1 — Per-User Memory

Memória escopada por usuário (`vectora/tools/memory.py`): operações
usam `namespace = f"user:{user_id}"` quando autenticado (fallback
global no CLI sem auth). Endpoints REST (`src/api/handlers/memory.py`):

- `GET /memory` — lista paginada do user
- `DELETE /memory/{memory_id}` — deleta específica
- `PUT /memory/{memory_id}` — edita conteúdo
- `DELETE /memory` — limpa todas

Frontend `memoria-tab.tsx`: lista de memórias do user (truncadas

- data + Editar inline + Deletar); botão "Limpar toda memória" com
  confirmação; empty state. Proxy Hono `chat/server/routes/memory.ts`.
  Badge "🧠 N memórias carregadas" por mensagem quando agente carrega
  contexto (via `NodeEvent.metadata.memories_loaded`), clicável para
  expandir lista.

### C2 — MCP Plugins Manager + Tool Policy (ABAC)

**MCP registry por usuário** (S2): `src/services/plugins.py` —
`McpServer` Pydantic (name, transport `stdio|sse|http`, command,
args, url). Persistência `~/.vectora/mcp/<user_id>.json`. APIs:
`list_servers`, `add_server`, `remove_server` (com `_bump_version`
para invalidar caches downstream), `health_check`, `build_connection`,
`get_user_mcp_tools` (async, cached por `(user_id, version)`).

Endpoints (`src/api/handlers/plugins.py`, auth required):

- `GET /plugins` — lista do user
- `POST /plugins` — add/update (validação por transport)
- `DELETE /plugins/{name}` — remove
- `POST /plugins/{name}/verify` — health-check (conecta + lista tools)

Frontend `plugins-tab.tsx`: tabela add/list/remove/verify com
toggle por transport. Proxy Hono `chat/server/routes/plugins.ts`.

**Tool Policy ABAC** (S5): `src/services/tool_policy.py` com
persistência `~/.vectora/tools/<user_id>.json` (`{disabled: [names]}`).
APIs `is_allowed(user_id, name)`, `get_disabled`, `set_disabled`
(bump de versão). Admin endpoints `/admin/users/{id}/tools` (B7) +
self-service `GET/PUT /tools/policy`. Frontend `tool-policy-panel.tsx`
no Admin + seção self no Settings.

**Tool Resolver + user-aware nodes** (S4+S6): novo
`src/services/tool_resolver.py::resolve_tools(user_id)` =
`[t for t in ALL_TOOLS if tool_policy.is_allowed(user_id, t.name)]

- await plugins.get_user_mcp_tools(user_id)`. Cache em
`dict[(user_id, version) -> list[BaseTool]]`. Versão derivada de
`tools_version(user_id)` (S2/S4).

Agents (`orchestrator`, `coder`, `search`) aceitam
`config: RunnableConfig`, extraem `user_id` de
`config.configurable`, fazem `bind_tools(resolve_tools(user_id))`
com cache `dict[(user_id, version) -> bound LLM]`. Fallback para
`ALL_TOOLS` quando CLI/local. `DiagnosticToolNode` em
`src/nodes/debug.py` é subclasse dinâmica que resolve tools por
user no `ainvoke`. Grafo singleton; rebind no próximo request após
bump.

**`/tools/schema` por user** (S7): reflete o user autenticado —
`ALL_TOOLS` menos desabilitadas + MCP do user. Frontend já consome
sem mudança.

### C3 — Skills Manager (S8 — `langchain-skills` style)

**Registry por usuário** (`src/services/skills.py`): `~/.vectora/
skills/<user_id>/index.json` + `<skill_id>/` (uma pasta por skill
com `SKILL.md`). Modelo `Skill` (`src/types/skill.py`): `id, name,
description, source, path, installed_at, installed_by`.

**Instalação**: aceita git URL (`git clone --depth 1`) ou path
local (cópia recursiva via `shutil.copytree`). Valida `SKILL.md`
com frontmatter YAML mínimo (`name` + `description` obrigatórios).
Staging em `.staging/` antes do move para slug do nome.
`_bump_version(user_id)` invalida caches downstream (agent_factory
no Bloco E).

**Endpoints** (`src/api/handlers/skills.py`):

- `GET /skills` — lista do user
- `POST /skills` — install (`{source}`)
- `DELETE /skills/{skill_id}` — remove
- `POST /skills/{skill_id}/verify` — revalida SKILL.md

Frontend `skills-tab.tsx`: lista (nome/descrição/source truncados),
input install (URL ou path, Enter ou +), botões verify/remove com
feedback inline (CheckCircle2/XCircle). Proxy Hono
`chat/server/routes/skills.ts`. 12 chaves i18n `skills.*`.

`list_skill_paths(user_id) -> list[Path]` consumido pelo
`agent_factory` no Bloco E para montar `skills=[...]` do Deep Agent.

### C4 — Embedded Terminal (PTY persistente)

**PTY cross-platform** (T1): `src/services/pty_session.py` —
classe `PtySession` que abre shell (`pwsh`/`cmd` Win, `$SHELL`/`bash`
Unix) em PTY via `pywinpty` (Win) ou `ptyprocess` (Unix). API:
`write(data)`, `resize(cols, rows)`, `read()` (async via thread/
executor → fila asyncio), `close()`.

`src/services/pty_registry.py`: `dict[terminal_id → PtySession]`
com `create(thread_id, workspace_id, shell?)`, `get`, `close`,
`close_all`. Múltiplos terminais por sessão (split). Cleanup no
`_lifespan` chama `pty_registry.close_all()` antes do `os._exit(0)`.

**WebSocket endpoint** (T2): `src/api/handlers/terminal.py` —
`@router.websocket("/vectora.terminal.v1/ws")` (query `thread_id`,
`workspace_id`, `terminal_id?`, `token`). Valida auth + `trusted` →
cria/recupera `PtySession` → bombeia bytes PTY↔WS. Mensagens de
controle JSON para `resize`. Browser abre `ws://${VECTORA_API_URL}/
vectora.terminal.v1/ws?...&token=` direto (proxy Hono não faz upgrade
WS no App Router).

A tool `terminal` injeta comandos no mesmo PTY quando há terminal
aberto na sessão (modo "persistente"); senão mantém o efêmero atual
(modo fallback `subprocess`). Streaming reaproveita `terminal_stream.py`.

**Frontend** (T3): `chat/components/terminal/` —

- `terminal-panel.tsx` — container do split direito; `PanelGroup`
  vertical aninhado para múltiplos PTYs.
- `xterm-view.tsx` — wrapper client-only do `@xterm/xterm`
  (+ `addon-fit`, `addon-web-links`) via `dynamic(import,
{ ssr: false })`; `term.onData → ws.send`; `ws.onmessage →
term.write`; `ResizeObserver → fit()` + envia `resize`.

Workspace **não-confiável** → painel mostra aviso e não abre o PTY.
i18n `terminal.*` em 3 línguas. Status (conectado/encerrado) +
reconexão automática leve.

### C5 — Workbench Multi-Tab (Terminal · Files · Diff · Plan) + SWR

**Workbench shell** (T5): rename `terminals-store.ts` →
`workbench-store.ts`. Novo `chat/components/workbench/workbench-panel.tsx`
com barra de abas (Terminal · Arquivos · Diff · Plano). Botão único
`PanelRight` no header substitui o flutuante anterior. Atalho ⌃⇧E
cicla; ⌃⇧T/F/D/P por aba. Mobile (`<768px`) vira `Sheet` overlay.

**Aba Arquivos** (T6):

- Backend: `GET /workspaces/{id}/tree?path=&depth=1` (reusa
  `resolve_within_workspace` Q4), `GET /workspaces/{id}/file?path=`
  (truncamento N kB, binário retorna `kind: "binary"`). Ignora
  `.git/`, `node_modules/`, `.venv/`.
- Frontend `files-tab.tsx`: árvore lazy-expanded com filtro/busca;
  viewer inline read-only via `CodeBlockViewer` por extensão; click
  abre arquivo. Pin de arquivo (T10.2) persiste em LocalStorage
  por `(threadId, workspace_id)`.

**Aba Diff** (T7):

- Backend: `GET /workspaces/{id}/git/diff?ref=HEAD` reusa
  `tools/git.py`. Retorna `[{path, status, additions, deletions,
hunks}]`.
- Frontend `diff-tab.tsx`: cabeçalho com `+N -M`, lista de arquivos
  com expand inline (lazy load hunk), reusa `DiffViewer`. Workspace
  não-git → estado vazio explicativo.

**Aba Plano** (T8):

- Backend: `GET /artifacts?session_id=` lê
  `~/.vectora/artifacts/<session_id>/*.md`, retorna
  `ArtifactMetadata[]` (reuso de `src/types/documents.py`).
- Frontend `plan-tab.tsx`: cards (título/tipo/timestamp) + markdown
  completo lateral ao clicar. SSE `tool_call=create_artifact` →
  invalidate.

**T.X — PanelGroup árvore estável**: `app/session/[threadId]/page.tsx`
renderiza sempre 3 filhos do PanelGroup; visibilidade via
`collapsible + collapsedSize={0}` e `disabled={!showWorkbench}`.
Conteúdo do `<Panel>` condicional **dentro** (`{showWorkbench ?
<WorkbenchPanel /> : null}`). IDs estáveis. Corrige
`Symbol.iterator` runtime error.

**T10 — QoL**:

- T10.1 — chips de status na barra de abas (qtd PTYs, `+N -M`
  modificados, qtd artifacts).
- T10.2 — pin de arquivo persistido.
- T10.3 — SWR padronizado.
- T10.4 — empty states acionáveis (Diff vazio → atalho
  `git_log`; Plan vazio → "Pedir ao Vectora um plano para…").
- T10.5 — atalhos ⌃⇧T/F/D/P.
- T10.6 — i18n `workbench.*`.

**T11 — Persistência e cache do Workbench**:

- T11.1 — Zustand `persist` + `partialize` do "chassi" (`panelOpen`,
  `activeTabByThread`, `byThread` metadados, `activeByThread`,
  `splitSize`, `pinnedFiles`). Chave `vectora-workbench-{user_id}`.
  PTYs reabrem reconnect WS; se servidor reiniciou → WS responde
  `4404` e front fecha aba.
- T11.2–4 — slices `files`/`diff`/`plan` no store (volátil, SWR-style),
  refactor das tabs para consumir; LRU implícito.
- T11.5 — invalidação por SSE em `use-stream-handler.ts`: case
  `tool_call` → `create_artifact` invalida plan;
  `file_write|file_edit|terminal|git_commit|git_checkout` invalida
  files+diff do workspace.
- T11.6 — `chat/lib/hooks/workbench/use-swr.ts` (~30 linhas):
  encapsula "lê do store → render imediato → refetch se stale →
  escreve no store".

### C6 — Workspaces Remotos: SSH + GitHub Codespaces

**Workspace.transport** (G.2.1): `Literal["local", "ssh", "codespace"]`

- `remote_host`, `remote_path`, `ssh_key_id`, `codespace_name` no
  modelo. `_migrate` set `transport="local"` para workspaces antigos.

**TransportBackend Protocol** (G.2.2): `src/services/transport/`

- `__init__.py` — Protocol com `list_dir`, `read_file`, `write_file`,
  `run(cmd, cwd, timeout)`, `open_pty`, `close`.
- `local.py` — default (pathlib + asyncio.create_subprocess_exec +
  `pty_session.PtySession`).
- `ssh.py` — `asyncssh>=2.18` async-native; lazy connect, pool 1
  por workspace; `_parse_host()` extrai `user@host:port`; lê chave
  do vault via `services/secrets/ssh_keys.py`; `run()` usa
  `cd ... && cmd` com `shlex.quote`.
- `codespace.py` — wraps `gh codespace list/start/ssh -c <name>`;
  herda de `SshTransport` apontando para `localhost:<porta_efêmera>`.
- `factory.py` — `get_transport(workspace)` com cache por
  `workspace.id`.

**Refactor tools** (G.2.3): `fs.py` (`file_read/edit/write`, `grep`,
`list_dir`), `git.py` adicionaram `_require_local(config)` que
retorna erro `{status: "remote_unsupported"}` para non-local.
`terminal` checa `transport != "local"` e roteia para
`get_transport(ws).run()`. PTY remoto explicitamente rejeitado no
WS layer com mensagem ("interactive PTY remote = future work").

**SSH keys no vault** (G.2.4): `src/services/secrets/ssh_keys.py`
em `~/.vectora/ssh-keys/<user_id>/<key_id>` (chmod 0700/0600);
`key_id = sha256[:12]` do conteúdo. APIs: `add_ssh_key`,
`list_ssh_keys`, `remove_ssh_key`, `get_ssh_key_bytes` (async).
Endpoints `/auth/ssh-keys` GET/POST(multipart)/DELETE em
`handlers/auth.py`.

**Codespaces via `gh` CLI** (G.2.5): `list_codespaces()` wraps
`gh codespace list --json name,repository,state,gitStatus`.
`ensure_started(name)` roda `gh codespace start`. `CodespaceTransport`
spawn `gh codespace ssh -c <name> -- bash -lc <cmd>` por run.
Endpoints `GET /workspaces/codespaces`, `POST /workspaces/test-ssh`,
`POST /workspaces/create-remote`.

**Trust dialog tabs** (G.2.6): `workspace-trust-dialog.tsx` ganha
3 tabs (Local/SSH/Codespace) só em `mode="trust"` (ingest segue
Local-only). Tab SSH: host + path + select de chave + upload de
key + botão "Testar conexão" com feedback inline. Tab Codespace:
loading, lista com `state`, click cria. Estado limpo no abrir. i18n
12 chaves `workspace.ssh_*` + `workspace.codespaces_*` + `workspace.
tab_local`.

**Badge no header** (G.2.7): `workspace-selector.tsx` exibe ícone
`Server` (sky) para SSH ou `Cloud` (violet) para Codespace ao lado
do nome, com tooltip mostrando `remote_host`/`codespace_name`.
Mesma lógica no dropdown (substitui `FolderGit2`/`FolderOpen` quando
non-local). i18n `workspace.transport.ssh` + `.codespace`.

### C7 — License Gate (Plus/Pro) + Status Endpoint (T.12.1+T.12.7)

`src/services/license.py`: validação de `VECTORA_TOKEN` contra
edge function Supabase (configurável via `VECTORA_LICENSE_URL`,
default `https://vectora.company/functions/v1/validate-license`).

- `validate_license_async/sync(token, version) -> LicenseStatusInfo`
- `LicenseStatusInfo` (frozen dataclass): `tier`, `status`,
  `days_remaining`, `expires_at`, `validated_at`, `cached`.
- `LicenseError(RuntimeError)` tipado.
- Cache local `~/.vectora/license_cache.json`:
  - **TTL 6h online** — cache fresco usado sem chamar remoto.
  - **TTL 48h offline graceful** — se chamada remota falhar,
    cache stale (>6h, <48h) ainda devolve com `cached=True`.
  - Após 48h → `LicenseError` com link `vectora.company/dashboard`.
- `VECTORA_LICENSE_BYPASS=1` pula validação (dev/CI only —
  jamais documentar em produção).

`src/launcher.py`: entry-point do binário comercial (T.12.4).

- Valida licença antes de qualquer subprocesso.
- Exporta `VECTORA_TIER=plus|pro` para a camada storage (F) e
  cache (G) saberem quais backends podem subir.
- Banner amarelo quando `days_remaining <= 7` em trial; falha
  imediata em `expired`.
- Delega para `src.main.run` (CLI tradicional chat/mcp/headless/
  desktop).

`src/api/handlers/license.py`: `GET /license/status` público
(prefixo whitelist em `auth.py` middleware) lê cache local que o
Launcher escreveu. Resposta:

```json
{
  "configured": true,
  "tier": "plus",
  "status": "trial",
  "days_remaining": 28,
  "expires_at": "...",
  "validated_at": "...",
  "cached": true
}
```

Testes em `tests/unit/test_services_license.py`: bypass, missing
token, cache fresco, cache stale offline (graceful 48h),
`read_cached_status`.

### C8 — OXC Toolchain (T.13)

`chat/.oxlintrc.json` com plugins `react`, `typescript`, `nextjs`,
`unicorn`, `import`. Categorias `correctness`/`suspicious`/`perf`
em `warn` (não bloqueia repo legado); `style` off (coberto pelo
prettier). `react/jsx-key` em `error`. Plugin name é `nextjs` (não
`next`).

Pre-commit hook `oxlint` antes do `tsc` em `.pre-commit-config.yaml`
(`pnpm --dir chat exec oxlint`, `pass_filenames: false`,
cross-platform). Script `pnpm lint:oxc` em `chat/package.json`.

`docs/oxc-toolchain.md` documenta roadmap:

- `oxc-formatter` aguardando GA (alpha 2026-06) — quando estável,
  promover para hook primário e desligar `prettier`.
- `oxc-minify` no `runner.yml` antes do Nuitka packaging
  (Bloco D) — reduzir `_next/static/*.js` ~30–40%.
- Endurecer categorias para `error` conforme warnings fechadas.

---

## ============================================================================

## ⏳ PRODUTO: blocos D–J (pendentes — distribuição, agents, storage, API)

## ============================================================================

## BLOCO D — Distribuição Comercial: Nuitka + Electron + Instaladores

> **Contexto.** O Launcher (`src/launcher.py`), gate de licença, config
> Nuitka (`build/nuitka.toml`), skeleton Electron (`desktop/src/main.ts`)
> e `electron-builder.yml` já estão prontos do Bloco C7+. Falta: rodar o
> pipeline real, validar build em cada SO da matrix, ligar code signing
> pipeline, fechar canal de updates e remover canais públicos legados.

### D1 — Pipeline Nuitka onefile + bundle do frontend (em CI matrix)

- **GitHub Actions matrix** (`runs-on: [windows-latest, macos-latest,
ubuntu-latest]`):
  1. `pnpm --dir chat install --frozen-lockfile`
  2. `pnpm --dir chat build`
  3. `pnpm --dir chat exec next export` → `chat/out/`
  4. (após N6 abaixo: `pnpm --dir chat exec oxc-minify chat/out/`)
  5. `uv sync --frozen`
  6. `uv run nuitka --config-file=build/nuitka.toml src/launcher.py`
  7. Output: `dist-nuitka/vectora-<os>-<arch>`
- **Validações por SO** (smoke tests):
  - `vectora --version` retorna versão correta.
  - `vectora --help` lista subcomandos.
  - `VECTORA_LICENSE_BYPASS=1 vectora server chat --port 0` sobe
    e responde `GET /health` em <10s.
  - `vectora server mcp --transport stdio` faz handshake.
- **Otimizações**: validar plugins Nuitka específicos por dep com
  ext C (`lancedb`, `pyarrow`, `tantivy`, `pykeepass`, `asyncssh`).
  Ajustar `include_package_data` por SO conforme imports lazy
  falham.

### D2 — Electron shell production-ready (sidecar + reload)

- **Path do binário** (`desktop/src/main.ts::backendPath()`): hoje
  aponta para `resources/vectora-core/`. Adicionar fallback em dev
  (`process.env.VECTORA_CORE_PATH` para apontar para
  `dist-nuitka/`).
- **Health-check robusto**: `waitForBackend` com retry exponencial
  - cap 30s; abrir janela de erro com botão "Reiniciar" se passar
    do timeout (em vez de só morrer).
- **Reload** (Ctrl+R / Cmd+R): bloqueado em prod (devTools off);
  liberado se `process.env.VECTORA_DEV=1`.
- **Crash handler**: `backend.on("exit")` chama Sentry (M2) com
  payload {code, signal, last_logs}.
- **Tray icon** (opcional MVP): mostra status (verde/vermelho/
  amarelo conforme `GET /health/ready`) com menu "Open Vectora",
  "Restart Backend", "Quit".
- **Deep-link** `vectora://`: para magic links (signin pelo browser
  → desktop) e `vectora://workspace/<id>` para abrir workspace
  específico.
- **IPC tipado** (`contextBridge`): expor `vectora.platform`,
  `vectora.openExternal(url)` para Stripe portal handoff (Bloco K).

### D3 — Code Signing Pipeline (Win/macOS/Linux)

- **Windows** — Azure Trusted Signing (EV cert):
  - Secrets em GitHub: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`,
    `AZURE_CLIENT_SECRET`, `AZURE_CERTIFICATE_PROFILE_NAME`,
    `AZURE_ENDPOINT`, `AZURE_CODE_SIGNING_ACCOUNT_NAME`.
  - Action `azure/trusted-signing-action@v0.5+`. SignTool valida
    `signtool.exe verify /pa /v vectora.exe` em smoke test.
- **macOS** — Apple Developer ID + notarização:
  - Secrets: `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`,
    `APPLE_TEAM_ID`, `APPLE_DEVELOPER_ID_CERT` (base64 .p12) +
    `APPLE_DEVELOPER_ID_CERT_PASSWORD`.
  - `electron-builder.yml` já tem `notarize: true` + `hardenedRuntime`
    - `entitlements`. Validar `xcrun stapler validate Vectora.dmg`.
  - Entitlements (`build-resources/entitlements.mac.plist`):
    `com.apple.security.cs.allow-unsigned-executable-memory` (para
    Nuitka), `com.apple.security.cs.allow-jit`,
    `com.apple.security.network.client/server`,
    `com.apple.security.files.user-selected.read-write`.
- **Linux**:
  - AppImage: sem assinatura (mantém).
  - `.deb` / `.rpm`: assinar com GPG do projeto
    (`VECTORA_GPG_KEY`/`VECTORA_GPG_KEY_PASSWORD`). `apt-secure` /
    `dnf` validam.

### D4 — Auto-Update Channel Server (electron-updater)

- **Backend leve** em Cloudflare Workers ou Vercel Edge:
  rota `/updates/<channel>/<os>/<arch>/RELEASES` + `/latest.yml`
  consultada pelo electron-updater. Channels: `latest`, `beta`,
  `alpha`.
- **Storage**: R2 ou Vercel Blob com instaladores assinados.
- **Auth do download**: presigned URLs por `VECTORA_TOKEN` (Bloco
  K) — só quem tem licença válida baixa.
- **Manifesto** (gerado por electron-builder): `latest.yml` +
  `latest-mac.yml` + `latest-linux.yml` com checksums sha512 +
  `releaseDate` + `releaseNotes` (markdown).
- **Delta updates**: `differentialPackage` no electron-builder
  (gera `.blockmap` para downloads incrementais ~80% menores).
- **Rollback**: se nova versão crashar 3x consecutivas no boot,
  electron-updater faz `quitAndRevert` para a versão anterior
  preservada em `~/Library/Application Support/Vectora/old-versions/`.
- **Banner no chat** ("Atualização disponível — v1.2.0"): hook em
  `command-bar.tsx` consumindo `GET /api/updates/status` que faz
  proxy para o manifesto.

### D5 — Instaladores nativos finais (electron-builder)

- **Windows**:
  - NSIS `oneClick: false`, `allowToChangeInstallationDirectory:
true`, shortcut Vectora no menu iniciar.
  - MSI para deploy corporativo (GPO friendly).
  - Per-machine + per-user opt-in no NSIS.
- **macOS**:
  - DMG com background custom (`build-resources/dmg-background.png`),
    layout `Vectora.app` → `/Applications` drag.
  - Universal binary (x64 + arm64) via `--universal` no
    electron-builder.
- **Linux**:
  - AppImage com `--no-sandbox` documentado (alguns kernels
    precisam).
  - `.deb` para Ubuntu/Debian — `Depends: libgtk-3-0, libnotify4,
libnss3, libxss1, libxtst6, xdg-utils, libatspi2.0-0`.
  - `.rpm` para Fedora/RHEL — `Requires` equivalente.

### D6 — License + Stripe Customer Portal handoff

- **Settings → "Gerenciar assinatura"** em `chat/components/layout/
settings-dialog/tabs/conta-tab.tsx`: botão que chama
  `POST /api/license/portal` (proxy Hono) → endpoint backend
  `POST /license/portal` que chama edge function Supabase
  `create-portal` (`docs/company.md` B6) → retorna `url`.
- **Desktop**: `shell.openExternal(url)` abre o Stripe Customer
  Portal no navegador padrão (não dentro do Electron — segurança).
- **Trial banner** (E2 company): hook em `chat/components/layout/
license-banner.tsx`:
  - Sem token configurado → laranja, link "Configure em Settings
    → Envs".
  - Trial ≤ 7 dias → amarelo, "Trial expira em N dias — Assinar".
  - Expirado → vermelho, bloqueia input, "Renovar".
- **Tier enforcement no chat**: feature gates leem
  `VECTORA_TIER` do `GET /license/status` e desabilitam UIs Pro
  quando `tier=plus` (badges "Pro only" nos backends storage/cache
  do Settings → Admin → Storage — ver F9, G).

### D7 — Mirror PyPI somente-leitura do CLI Plus (compat early adopters)

- Pacote `vectora-cli` no PyPI contém **apenas** o CLI Python
  (sem frontend, sem Electron). Reutiliza `src/launcher.py` mas
  pula gate de licença em modo `--cli-only` (acessa **só** CLI
  features — `vectora chat` textual, `vectora rag`, `vectora setup`).
- Para tudo que requer chat web ou desktop, redireciona para
  `https://vectora.company` download nativo.
- `pyproject.toml` separa packages: `vectora-cli` (mirror) vs
  `vectora` (full, GitHub Releases privado).
- **Mensagem clara**: ao rodar `vectora server chat` no PyPI mirror
  → erro explicativo apontando para download nativo.

### Arquivos críticos (Bloco D)

| Sub | Arquivos                                                                                                                                                                                                                            |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | `.github/workflows/runner.yml` (matrix), `build/nuitka.toml` (ajustes por SO), `Dockerfile.build` (Linux build container)                                                                                                           |
| D2  | `desktop/src/main.ts` (retry/crash handler/tray/deep-link), `desktop/src/preload.ts` (contextBridge), `desktop/package.json` (+`electron-updater`, +`@sentry/electron`)                                                             |
| D3  | `.github/workflows/runner.yml` (steps de signing), `desktop/electron-builder.yml` (entitlements path, signing flags), `build-resources/entitlements.mac.plist` (novo)                                                               |
| D4  | `update-server/` (novo repo Cloudflare Workers), `chat/components/chat/features/update-banner.tsx` (novo), `chat/server/routes/updates.ts` (novo)                                                                                   |
| D5  | `desktop/electron-builder.yml` (NSIS oneClick/MSI/DMG layout), `build-resources/dmg-background.png`                                                                                                                                 |
| D6  | `chat/components/layout/settings-dialog/tabs/conta-tab.tsx` (+"Gerenciar assinatura"), `chat/components/layout/license-banner.tsx` (novo), `chat/server/routes/license.ts` (proxy), `src/api/handlers/license.py` (+`POST /portal`) |
| D7  | `pyproject.toml` (split packages), `src/launcher.py` (`--cli-only` mode), CI publish-pypi do `vectora-cli`                                                                                                                          |

### Verificação (Bloco D)

- CI matrix produz 3 binários (Win .msi + .exe NSIS, macOS .dmg
  universal, Linux .AppImage + .deb + .rpm) — todos assinados,
  notarizados (macOS), em <30 min de build.
- Instalar em VM limpa Win/macOS/Linux sem Python/Node — app abre,
  pede `VECTORA_TOKEN`, valida, carrega chat.
- Auto-update: subir `vN+1` no canal `beta` → cliente em `vN`
  recebe banner, baixa delta, reinicia, está em `vN+1`.
- Stripe portal: clicar "Gerenciar assinatura" no desktop abre
  navegador externo no Customer Portal.
- Trial banner muda cor conforme dias restantes; expirado
  bloqueia input.
- PyPI mirror: `pip install vectora-cli` + `vectora chat` funciona;
  `vectora server chat` mostra mensagem redirecionando ao site.

---

## BLOCO E — Deep Agents: Refactor do Harness + TUI Textual

> **Contexto.** Hoje o Vectora tem harness custom sobre LangGraph:
> `src/graph.py` compõe orchestrator + 2 subagents (coder, search) + nó
> `hitl_check` + pipeline RAG achatado + `parallel_dispatch`. Cada agent
> cacheia LLM bindado por user via `services/llm_tools.py`. Tool nodes
> (`DiagnosticToolNode`) já são user-aware (C2). O framework
> `deepagents` da LangChain entrega o mesmo padrão (main agent + subagents
>
> - planning + filesystem virtual + skills + HITL nativo via
>   `interrupt_on`). Adotar reduz código próprio e alinha ao ecossistema.
>
> **Bloco E é APENAS refactor.** Comportamento observável, eventos SSE e
> contratos da API permanecem **idênticos**.

### E1 — `agent_factory` por usuário (núcleo)

`src/services/agent_factory.py`:

```python
async def get_user_agent(user_id) -> DeepAgent:
    # cache por (user_id, llm_version, plugins_version, policy_version,
    #            skills_version)
```

Internamente:

- LLM via `services/utils.load_llm()` (já fala provider/model).
- Tools via `services/tool_resolver.resolve_tools(user_id)` (C2 — built-ins
  permitidas + MCP do user + skills do user).
- `subagents=[coder, search, rag]` (E2).
- `system_prompt = VECTORA_IDENTITY + ORCHESTRATOR_PROMPT` (mantém
  envelope markdown da A2 + identidade).
- `interrupt_on` derivado do `permission_mode` (A3 — ver E4).
- `checkpointer = services.checkpoint.get_checkpointer()` (factory
  da Bloco F).

Substitui `_get_orchestrator_llm()`, `_get_coder_llm()`,
`_get_search_llm()` e `services/llm_tools.get_user_bound_llm()`
(reusado **internamente** pelo DeepAgent quando rebinda).

### E2 — Subagents (coder/search/rag) como dicts DeepAgent

Subagents declarados no formato `deepagents`:

```python
{"name": "coder", "description": "...", "prompt": SYSTEM_PROMPT,
 "tools": resolve_tools(user_id), "model": None}
```

Prompts vêm de `agents/coder.py::SYSTEM_PROMPT`,
`agents/search.py::SYSTEM_PROMPT`,
`agents/_identity.py::VECTORA_IDENTITY` (preservados).

**Pós-processamento** (`coder_finalize`/`search_finalize` em
`graph.py:243-257`) vira **middleware** do DeepAgent — extrai
`CoderResult`/`SearchResult` do histórico e injeta em
`state["coder_result"]`/`state["search_result"]` para o orchestrator
sintetizar.

**RAG subagent**: subagent dedicado que executa o pipeline atual de
`rag_subgraph.py` (expand → retrieve → decide → rerank|search →
inject). Mantém `rag_pending` para o caminho "score baixo → search
real". **Não vira middleware** — preserva arquitetura achatada.

`OrchestratorDecision` schema (`src/types/agents.py`): descontinuado.
DeepAgent já implementa `respond`/`delegate`/`parallel` nativos.
`ThinkingEvent` alimenta-se dos campos equivalentes do harness.
Schemas `CoderResult`/`SearchResult` permanecem para
`*_finalize` middleware.

### E3 — Adapters SSE & node labels

`src/api/adapters.py` mapeia eventos LangGraph do DeepAgent
(`main_agent`, `subagent:coder`, `subagent:search`, `subagent:rag`)
para SSE preservando schemas (`ThinkingEvent`, `TokenEvent`,
`ToolCallEvent`, `HITLEvent`, `NodeEvent`). Adicionar entradas em
`src/api/node_labels.py` para `node_label` legível.

`ThinkingEvent` (A3): extrai do raciocínio do main agent
(callback/middleware do DeepAgent); preserva campos `reason`,
`action`, `delegate_to`, `task_query` que o frontend consome
(`chat/lib/types/messages.ts:38-43`).

**Zustand stale-while-revalidate** (A2 B14) **não muda**.

### E4 — HITL via `interrupt_on` (5 modos preservados)

Substitui o nó `hitl_check`. Mapping `permission_mode` (A3) → config
do DeepAgent:

| Modo (A3)      | `interrupt_on`                                                         |
| -------------- | ---------------------------------------------------------------------- |
| `ask`          | `{"terminal": True, "file_write": True, ...}` (REQUIRE_APPROVAL atual) |
| `accept_edits` | `{"terminal": True}` (file_write auto)                                 |
| `plan`         | `{*: "reject"}` — recusa toda destrutiva (envia ToolMessage)           |
| `auto`         | `{}` filtrado por workspace trust (B2)                                 |
| `bypass`       | `{}` — sem interrupts                                                  |

HITL endpoints (`/ResumeChat`) e `interrupt_id` continuam idênticos
— DeepAgent usa `interrupt` do LangGraph (mesmo mecanismo).

### E5 — Cleanup (sumiço de código legado)

Deletar:

- `src/graph.py` (substituído por `agent_factory.get_user_agent()`)
- `src/agents/{orchestrator,coder,search}.py` — caches LLM e nodes
  vão embora; system prompts viram constantes consumidas pelo
  factory.
- `src/nodes/hitl.py` — `hitl_check` removido (constante
  `REQUIRE_APPROVAL` migra para `agent_factory` como mapping de
  `interrupt_on`).
- `src/nodes/debug.py::DiagnosticToolNode` — DeepAgent tem
  observabilidade; preservar tracing via middleware (logging +
  tracer).

### E6 — Testes (regressão obrigatória)

Que **devem continuar passando**:

- `tests/unit/test_nodes_hitl.py` (rebatizado para validar
  `interrupt_on` por modo).
- `tests/unit/test_api_chat_config.py`
- `tests/unit/test_api_auth.py`
- `tests/unit/test_nodes_debug_dynamic.py` (C2) — resolução por
  user permanece via `tool_resolver`.

Novo `test_agent_factory.py`: monta agent para 2 users, valida que
cada um recebe seu próprio toolset (deny + MCP) e cache é por
`(user_id, versions)`.

E2E: "rode `ls` na pasta" em `permission_mode=ask` → 1 evento HITL
→ approve → execução. `plan` → recusa imediata sem HITL.

### E7 — CLI textual TUI (`vectora chat` rich → textual)

> Mantém os comandos one-shot (`vectora traces`, `vectora sessions`,
> `vectora config`) em `rich`. Só o interativo migra.

- **`src/ui/textual/app.py`** (novo): `VectoraChatApp(App)` com
  layout split (mensagens à esquerda, painel lateral à direita —
  Terminal · Files · Diff · Plan, mesmo do web). Screens para
  config/RAG/workspaces. Key bindings espelham web (⌃` terminal,
  ⌃⇧F arquivos, etc.).
- **`src/ui/textual/streaming.py`**: handler de `astream_events` v2
  que escreve nos widgets via `call_from_thread`. Compartilha o
  adapter SSE→evento já existente (`src/api/adapters.py`).
- **`src/ui/textual/widgets/`**: um widget por `render_hint`
  (`DiffWidget`, `CodeBlockWidget`, `TableWidget`,
  `TerminalBlockWidget`, `ArtifactCardWidget`, `ThinkingWidget`).
  Reuso direto dos tipos em `chat/lib/types/render.ts`
  (espelhamento).
- **Input**: `textual.widgets.Input` com history + autocomplete
  via `Suggester`. Slash commands B4 ganham suggester nativo.
- **HITL**: modal `ModalScreen` para approve/edit/reject (mesmo
  schema do `HITLEvent`).
- **Comandos in-chat** (`src/ui/commands/*`) portados para "actions"
  do app textual; output flui pelos widgets em vez de
  `Console.print`.
- **Setup wizard** (`src/ui/setup_wizard.py`) vira `Screen` ao
  detectar `~/.vectora/config.toml` ausente.
- **`src/main.py`**: subcomando `chat` instancia `VectoraChatApp`.
  `--legacy` mantém caminho `rich` por 1 versão (rollback rápido).

### Dependências

```toml
deepagents = ">=0.6.3"     # já presente, fixar exato
textual    = ">=0.83"      # NOVO — TUI vectora chat
```

### Arquivos críticos (Bloco E)

| Sub | Arquivos                                                                                                                                                                                          |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E1  | `src/services/agent_factory.py` (novo), `src/api/handlers/chat.py` (chama factory em vez de `_get_graph`)                                                                                         |
| E2  | `src/agents/coder.py`, `src/agents/search.py`, `src/agents/_identity.py` (prompts viram constantes), `src/nodes/rag_subgraph.py` (vira subagent)                                                  |
| E3  | `src/api/adapters.py`, `src/api/node_labels.py`                                                                                                                                                   |
| E4  | `src/services/agent_factory.py` (mapping), remoção de `src/nodes/hitl.py`                                                                                                                         |
| E5  | deletar `src/graph.py`, `src/nodes/hitl.py`, partes de `src/agents/{orchestrator,coder,search}.py`                                                                                                |
| E6  | `tests/unit/test_agent_factory.py` (novo); migrar `test_nodes_hitl.py`                                                                                                                            |
| E7  | `src/ui/textual/{app,streaming}.py` (novos), `src/ui/textual/widgets/*.py` (novos), `src/ui/commands/*` (portar para actions), `src/ui/setup_wizard.py` (vira Screen), `src/main.py` (subcomando) |

### Verificação (Bloco E)

- Mesmas perguntas que hoje produzem `delegate_to=coder|search|rag`
  continuam produzindo mesmo `node_label` na UI.
- HITL: approve/reject/edit terminal funciona em todos os 5 modos.
- MCP por user (C2): user adiciona MCP server → tools aparecem no
  `GetTools` e o agente as chama.
- Workspace por sessão (B2): coder respeita `cwd` do workspace ativo.
- Performance: primeiro request por user paga o bind; subsequentes
  (mesma versão) usam cache (sem rebind do LLM).
- `vectora chat` (textual): split visual igual ao web, atalhos
  funcionam, slash commands com suggester.

---

## BLOCO F — Storage Infrastructure: Lite Hardening + Postgres/Qdrant + BaaS

> **Contexto.** Antes de adicionar backends (Postgres/Qdrant),
> **fortalecemos** o que já existe (SQLite + LanceDB) e construímos uma
> **camada de storage** com abstração única que cobre lite (default) e
> completo (opt-in), schema versioning, pool de conexões, health checks
> e migrations explícitas. Depois plugamos backends novos via os mesmos
> Protocols. Por fim, UI no admin e CLI `vectora storage`.
>
> **Modos:**
>
> - **Lite** = zero infra externa (SQLite + LanceDB + cache memória,
>   default; tier Plus permite).
> - **Completo** = Postgres + Qdrant + Redis para multi-server (tier Pro
>   obrigatório; gate em C7 + D6).
>
> Seleção via `[storage]` em `~/.vectora/config.toml` ou env
> `VECTORA_MODE`/`VECTORA_DATABASE_URL`/`VECTORA_QDRANT_URL`/
> `VECTORA_REDIS_URL`.

### F1 — Hardening do modo lite (SQLite + LanceDB)

- **SQLite pool** (`storage/sqlite/pool.py` novo): `AsyncConnectionPool`
  com `aiosqlite`, `min=1 max=8` por banco. PRAGMAs globais:
  `journal_mode=WAL`, `busy_timeout=30000`, `synchronous=NORMAL`,
  `temp_store=MEMORY`, `mmap_size=268435456`, `foreign_keys=ON`
  (consistência auth/invites/refresh_tokens). Substitui o `_db_conn
= None` espalhado.
- **LanceDB** (`storage/lancedb/{connection,index,optimize}.py`
  novos): cache de conexão por path; `open_table()` cached por
  collection; `vector_column.create_index(num_partitions=…)` IVF on-
  demand acima de N linhas; `optimize()` periódico (compaction) via
  job leve no background worker; **FTS index nativo**
  (`table.create_fts_index("text")`) — significativamente mais rápido
  que BM25 custom em tabelas grandes. Mantém BM25 custom como
  fallback.
- **Concorrência**: integra `busy_timeout` + retries com backoff
  nos 3 bancos (`vectora.db`, `embedding_queue.db`, `traces.db`).
- **Documentação** `docs/storage-lite.md`: VACUUM, WAL checkpoint
  manual, backup hot/cold.

### F2 — Schema versioning (substitui `ALTER … suppress(Exception)`)

- **`storage/migrations/`** com migrations numeradas:
  `0001_create_users.sql`, `0002_add_user_name.sql`, etc. Cada
  arquivo tem `-- up` e `-- down`. Para LanceDB (sem DDL clássico),
  migrations são scripts Python idempotentes (add column via
  `merge_insert`, rebuild index, etc.).
- **Runner** `storage/migrations/runner.py`: tabela
  `schema_migrations(version, applied_at, checksum)` em cada banco.
  No startup do server roda pendentes; checksum garante que arquivo
  não foi alterado depois de aplicado.
- **CLI** `vectora storage migrate` (status / upgrade / downgrade
  por versão alvo). Lite roda auto no startup; completo prefere
  rodar manual antes do deploy.

### F3 — Camada `storage/` (Protocols + factories)

- **`storage/protocols.py`**: `Checkpointer`, `Store`,
  `VectorStore`, `AuthDB`, `SessionDB`, `QueueDB`, `SecretsDB`,
  `TracesDB` — Protocols Python tipados. `health()` em cada.
- **`storage/factory.py`**: lê `[storage]` e devolve a instância
  certa. `get_checkpointer()`, `get_store()`, `get_vector_store(name)`,
  etc. Singleton por backend. Reusa pool de F1.
- Impls iniciais (`storage/sqlite/*`, `storage/lancedb/*`) são wraps
  finos sobre o que já existe — comportamento **idêntico** ao
  pré-F para reversibilidade.

### F4 — Checkpointer via `langgraph.checkpoint.{sqlite,postgres}`

- **Lite** (já é): `AsyncSqliteSaver` apontando para
  `~/.vectora/data/vectora.db` via pool F1.
- **Completo**: `AsyncPostgresSaver`
  (`langgraph-checkpoint-postgres`) com `asyncpg` pool. `Schema`
  configurável; o pacote oficial cuida das próprias migrations
  (`setup()` no boot).
- **Factory**: `get_checkpointer()` devolve um ou outro conforme
  config. `services/checkpoint.py` vira fino wrapper.

### F5 — BaseStore via `langgraph.store.{sqlite,postgres}` (refactor memory)

> Substitui implementação custom de `services/memory.py` (cosine em
> Python puro, embeddings JSON-encoded) pelo `BaseStore` oficial do
> LangGraph — namespace, TTL, semantic search nativos.

- **Lite**: `SqliteStore` com
  `index={"embed": CohereEmbeddings(...), "dims": 1024}` — semantic
  search nativo, persistente.
- **Completo**: `PostgresStore` (`langgraph-store-postgres`) com
  `index` apontando para `CohereEmbeddings` e schema separado do
  checkpointer.
- **API consumida pelos handlers** (`memory.py`) passa a falar
  `store.aget()/aput()/asearch()` em vez do CRUD custom. Namespace
  `user:<id>` continua sendo a chave.
- Migration script `vectora storage migrate memory-to-langgraph`
  copia da tabela `memories` antiga para o novo store preservando
  TTL e metadata.

### F6 — VectorStore via `langchain-community` (LanceDB) e `langchain-qdrant`

Substitui uso direto de `lancedb.connect_async` por integrations
oficiais — recebe hybrid search, retry e tipagem grátis.

- **Lite (LanceDB)**: `langchain_community.vectorstores.LanceDB`
  apontando para cache de conexão de F1. Mesma interface
  (`asimilarity_search`, `aadd_texts`, `aadd_documents`) — substitui
  `vector_search()` artesanal de `tools/rag.py` e write path em
  `services/background.py`.
- **Completo (Qdrant)**: `langchain_qdrant.QdrantVectorStore` com
  **`RetrievalMode.HYBRID`** — denso via `CohereEmbeddings` + esparso
  via `FastEmbedSparse(model_name="Qdrant/bm25")`. Connection via
  `qdrant_client.AsyncQdrantClient(url, api_key)`. URL aceita Qdrant
  local **e** Qdrant Cloud (BaaS) sem branching.
- **Alternativa pgvector**: `langchain_postgres.PGVector` para quem
  prefere consolidar em Postgres — selecionável via `[storage]
vector_backend = "pgvector"`.
- **Hybrid lite**: prioriza FTS index do LanceDB (F1) quando
  disponível; mantém BM25 custom como fallback. Multi-query e
  CohereRerank intactos.
- **Collections**: nomenclatura preserved (`articles`, `web_cache`,
  `search`); `workspace_id` continua em metadata para filtro
  pós-retrieval (B2).

### F7 — Auth/Sessions/Secrets/Audit/Invites/Queue em Postgres

- Dep: `asyncpg>=0.29` (+ opcional `sqlalchemy[asyncio]>=2.0`).
- **Migração de schema**: tabelas com prefixo `vectora_*`. Cada
  service (auth, memory, session, secrets/internal, audit, invites)
  ganha:
  - Impl `sqlite/` (extrai SQL atual).
  - Impl `postgres/` (mesmo SQL, ajuste de placeholders `$1` vs `?`
    e `ON CONFLICT … DO UPDATE`).
- **Compatibilidade**: serviço fala com abstração; só a config muda.

### F8 — Embedding queue em Postgres (multi-worker)

- `services/queue.py` + `services/background.py` migram para tabela
  `vectora_embedding_queue` com `SELECT ... FOR UPDATE SKIP LOCKED`
  — múltiplos workers consumindo sem corrida. No lite continua
  SQLite + lock por arquivo.

### F9 — BaaS recipes (Supabase, Neon, Qdrant Cloud)

> Usuários do modo completo raramente vão querer hospedar
> Postgres/Qdrant próprio. Cada provedor tem **pegadinhas** específicas
> (Supabase pgbouncer transaction mode exige `prepare_threshold=0`,
> Neon precisa `?sslmode=require`, Qdrant Cloud impõe payload limits).

- **`storage/recipes/`**: um arquivo por provedor —
  `supabase.py`, `neon.py`, `qdrant_cloud.py` — com:
  - DSN templates parametrizados (host, project_ref, password, region).
  - Flags específicas (`statement_cache_size=0` para pgbouncer
    transaction, `sslmode=require`, `application_name=vectora`).
  - Validação de versão / extensão (`CREATE EXTENSION IF NOT EXISTS
vector` para pgvector hosted).
  - Smoke test: `recipe.healthcheck()` valida conectividade +
    permissões + extensões.
- **Wizard CLI** (F11) e **UI admin** (F10) usam recipes para
  gerar config certa.

### F10 — UI: aba "Storage" no Admin

> Hoje admin só configura `default_model`/`allow_public_signup`/
> `max_recursion`. Storage é invisível.

- **`chat/components/layout/settings-dialog/admin/storage-panel.tsx`**:
  subaba dentro de Administração com 4 seções:
  - **Checkpointer**: select (SQLite/Postgres) + DSN field + "Testar
    conexão" + status (badge verde/amarelo/vermelho).
  - **Store (memory)**: idem (SqliteStore / PostgresStore /
    InMemoryStore).
  - **Vector store**: select (LanceDB / Qdrant / pgvector) + URL/DSN
    - api_key (masked) + status.
  - **Embedding queue**: idem.
- **Wizard "Connect to BaaS"** (botão no topo de cada seção): abre
  modal com 4-step wizard reusando recipes F9.
- **Backend**: `GET /admin/storage` (status + health),
  `POST /admin/storage/test` (testa DSN sem salvar),
  `PATCH /admin/storage` (aplica + agenda reload).
- **Reload**: trocar backend exige restart — UI mostra banner +
  botão "Aplicar e reiniciar" (`os._exit(0)` controlado).
- **Tier gate**: opções Pro (Postgres/Qdrant/pgvector) ficam
  desabilitadas com badge "Pro only" quando `VECTORA_TIER=plus`.
- i18n `storage.*`.

### F11 — CLI `vectora storage`

> Espelho CLI da F10. Operadores headless precisam configurar storage
> sem subir o frontend.

- `vectora storage info` — backends ativos + health (lite/complete,
  paths, DSN mascarado, último migration, contagem de rows).
- `vectora storage test [--backend <name>]` — healthcheck (DB ping,
  vector query, queue read).
- `vectora storage wizard` — TUI interativa (textual de E7) com
  mesmos passos da UI.
- `vectora storage migrate <to-postgres|to-qdrant|to-pgvector>` —
  F12.
- `vectora storage backup` / `restore` — dump físico simplificado
  (sqlite `.backup`, `pg_dump`, snapshot Qdrant).

### F12 — Migration tool (`vectora storage migrate`)

- **`to-postgres`**: lê SQLite local (3 bancos) → cria schema no
  Postgres (runner F2) → bulk insert via `COPY` em transações.
  Idempotente (skip se tabela alvo tem linhas; `--force`).
- **`to-qdrant`**: lê LanceDB, cria collections no Qdrant com schema
  correto, bulk upsert (`AsyncQdrantClient.upsert` em batches 256).
  Mantém payload fields.
- **`to-pgvector`**: move vectors para `PGVector`.
- **`memory-to-langgraph`** (F5): tabela `memories` custom → novo
  store.
- Logs progressivos via `tqdm`/`textual.ProgressBar`; `--dry-run`
  estima volume.

### F13 — `docker-compose` de referência

- **`deploy/compose.complete.yml`**: `postgres:16` (com `pgvector`
  pré-instalado), `qdrant/qdrant:latest`, `redis:7` (G), `vectora`
  (build do projeto). Volumes nomeados; healthchecks; rede
  dedicada. Templates `.env`.
- **`deploy/compose.lite.yml`**: opcional — só `vectora` contra
  storage embutido. Útil para VPS minimalista.
- **README** `deploy/README.md` cobrindo 3 variantes (lite, complete
  self-hosted, complete BaaS).

### F14 — Tests (parametrizados lite/complete)

- Fixtures `@pytest.fixture(params=["lite","complete"])` em auth,
  memory, sessions, queue, traces, vector store. CI Lite (default)
  roda `params=lite`; CI Complete (job opcional com docker services)
  roda também `params=complete`.
- Tests específicos:
  - `test_storage_pool.py` — pool SQLite concorrente, busy_timeout,
    foreign_keys.
  - `test_storage_lancedb.py` — cache de conexão, FTS index,
    compaction.
  - `test_storage_migrations.py` — runner aplica/reverte; checksum
    detecta alteração.
  - `test_storage_recipes.py` — DSN templates renderizam corretamente.
  - `test_admin_storage.py` — endpoints `GET/PATCH/POST /admin/
storage`.
- Smoke: `vectora storage migrate to-postgres` lite→complete preserva
  rows + sample integrity check.

### F15 — Provedores LLM via SDKs oficiais (consistência + Cohere completo)

Hoje `services/utils.load_llm()` mistura `init_chat_model` com paths
legados, e `tools/memory.py` usa `cohere.AsyncClient` direto
(violação do princípio 5).

- **`langchain-google-genai`** — `ChatGoogleGenerativeAI` Gemini
  2.5/3.x.
- **`langchain-openai`** — `ChatOpenAI` (gpt-5.x, o3, o4-mini) +
  `OpenAIEmbeddings` (fallback).
- **`langchain-anthropic`** — `ChatAnthropic` (Claude 4.5/4.6/4.7) +
  prompt caching automático via `cache_control` (H3).
- **`langchain-cohere` completo**:
  - `ChatCohere` — chat (Command-R+, Command-A). Tool calling
    nativo.
  - `CohereEmbeddings` — `embed-multilingual-v3.0` (1024-dim) —
    único embedding do RAG.
  - `CohereRerank` — `rerank-multilingual-v3.0` — único reranker em
    `services/utils.rerank_documents` + `nodes/rag_subgraph`.
  - `CohereToolsReactAgentOutputParser` — parser ReAct multi-hop
    usado quando modelo é Command-R+ e orchestrator opta pelo fluxo
    ReAct.
  - **Remoção**: `tools/memory.py` (linhas 49, 274) substitui
    `cohere.AsyncClient` por `CohereEmbeddings` + `CohereRerank`.
- `services/utils.load_llm()` vira `match provider:` sobre essas 4
  classes; remove imports diretos espalhados.
- **pyproject** sem version pins fixos (princípio 5): faixas abertas
  `>=` com major estável; CI valida upgrade automático.

### Arquivos críticos (Bloco F)

| Sub | Arquivos                                                                                                                                                                                                                                                                                  |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F1  | `storage/sqlite/pool.py` (novo), `storage/lancedb/{connection,index,optimize}.py` (novos), `docs/storage-lite.md`                                                                                                                                                                         |
| F2  | `storage/migrations/{0001_*,…}.sql` (novos), `storage/migrations/runner.py` (novo), `src/main.py` (subcomando)                                                                                                                                                                            |
| F3  | `storage/{protocols,factory}.py` (novos); wraps finos em `storage/{sqlite,lancedb}/*`                                                                                                                                                                                                     |
| F4  | `storage/{sqlite,postgres}/checkpoint.py`; `src/services/checkpoint.py` (factory wrapper)                                                                                                                                                                                                 |
| F5  | `storage/{sqlite,postgres}/store.py`; `src/services/memory.py` (refactor); `src/api/handlers/memory.py` (idem); migration `memory-to-langgraph`                                                                                                                                           |
| F6  | `storage/lancedb/vector_store.py`, `storage/qdrant/vector_store.py`, `storage/postgres/vector_pgvector.py`; refactor de `src/tools/rag.py`, `src/nodes/rag_subgraph.py`, `src/services/background.py`, `src/mcp/server.py`                                                                |
| F7  | `storage/postgres/{auth,session,secrets,audit,invites}.py` (novos); refactor de `src/services/{auth,session,secrets/internal}.py`                                                                                                                                                         |
| F8  | `storage/postgres/queue.py`; refactor de `src/services/{queue,background}.py`                                                                                                                                                                                                             |
| F9  | `storage/recipes/{supabase,neon,qdrant_cloud}.py` (novos); `tests/unit/test_storage_recipes.py`                                                                                                                                                                                           |
| F10 | `chat/components/layout/settings-dialog/admin/storage-panel.tsx` (novo); `src/api/handlers/admin.py` (+`/admin/storage`); i18n `storage.*`                                                                                                                                                |
| F11 | `src/main.py` (subcomando `storage` info/test/wizard/migrate/backup)                                                                                                                                                                                                                      |
| F12 | `src/services/migrate.py` (novo, helpers bulk insert)                                                                                                                                                                                                                                     |
| F13 | `deploy/compose.{lite,complete}.yml`, `deploy/postgres/init.sql`, `deploy/README.md`                                                                                                                                                                                                      |
| F14 | `tests/unit/test_storage_{pool,lancedb,migrations,recipes}.py`; parametrização de `test_services_{auth,memory,session,queue}.py`                                                                                                                                                          |
| F15 | `src/services/utils.py` (`load_llm` consolidado); `src/tools/memory.py` (remover `cohere.AsyncClient`); `pyproject.toml` (+9 deps: langchain-google-genai/openai/anthropic/cohere/community/postgres/qdrant + langgraph-checkpoint-{sqlite,postgres} + langgraph-store-{sqlite,postgres}) |

### Verificação (Bloco F)

**Lite hardening (F1–F3):**

- `vectora server chat` em pasta vazia: storage cria 3 bancos com
  WAL + foreign_keys ON + busy_timeout 30s; LanceDB índices criados
  sob demanda; FTS index montado quando hybrid acionado.
- `vectora storage migrate status` lista migrations aplicadas com
  checksum; alterar arquivo já aplicado → detecta drift e recusa.

**Backends completos (F4–F8):**

- Trocar `[storage] mode = "complete"` → banner "Restart" → restart
  → todas as operações que funcionavam no lite funcionam idêntico
  só que backed por Postgres + Qdrant.
- Hybrid Qdrant: RAG retorna scores combinados dense + sparse;
  mensurável (precision@5).

**BaaS (F9):**

- Wizard CLI: `vectora storage wizard` → Supabase → cola
  service_role + project_ref → healthcheck verde → config salva
  com `statement_cache_size=0`. Idem Neon (sslmode) e Qdrant Cloud.

**UI/CLI (F10/F11):**

- Admin abre Settings → Storage → vê 4 cards (checkpointer/store/
  vector/queue) com status + DSN mascarado; "Testar" em <2s.
  Wizard BaaS funciona idêntico ao CLI.
- `vectora storage info` (headless): JSON com health + paths +
  counts.

**Migration (F12):**

- `vectora storage migrate to-postgres --dry-run` reporta volume
  sem mover. Sem `--dry-run` move e zero rows perdem; `--force`
  sobrescreve.

---

## BLOCO G — Cache Distribuído: Redis + `langchain-redis`

> **Contexto.** O backend tem 7 caches em memória que travam o Vectora
> em single-process: `llm_tools._bound_cache` (C2), `plugins.
_mcp_tools_cache` + `_versions` (C2), `services/usage.usage_tracker`
> (A7), `services/workspace.workspace_registry._active` (B2),
> `services/session._session_cache`, embedding cache implícito.
> Multi-server exige externalização. Redis também alimenta o rate
> limiter (M).

### G1 — Cache abstrato

- `src/services/cache.py`: Protocol `KVCache` (`get`, `set`, `incr`,
  `delete`, `hset`/`hget`, `zadd`/`zrangebyscore`/
  `zremrangebyscore`).
- Impls: `memory` (dict atual, default) e `redis` (`redis-py>=5.0`
  asyncio).

### G2 — LLM bind cache em Redis (pub/sub de invalidação)

- `services/llm_tools._bound_cache` deixa de armazenar o objeto LLM
  (não serializável); passa a guardar **assinaturas** (versão das
  tools que o bind reflete). LLM em si fica em memória local
  **por processo**. INVALIDAÇÃO via Redis pub/sub (ou polling de
  versão) coordena os processos. Multi-server sem rebind
  desnecessário.

### G3 — MCP tools cache + versions

- `services/plugins._mcp_tools_cache` mantém-se em memória local por
  processo (objetos `BaseTool` não serializam). `_versions` migra
  para Redis hash (`vectora:plugins:version:<user_id>` → int).
  `add_server`/`remove_server` fazem `INCR`.

### G4 — Usage tracker em Redis sorted set

- `services/usage.UsageTracker` migra para sorted set por user
  (`ZADD usage:<user_id> <ts> <id>`; `ZREMRANGEBYSCORE` para janela
  deslizante; `ZCARD` para uso atual). Endpoint `GET /auth/usage`
  (A7) passa a ler de lá. Modo lite continua dict em memória.

### G5 — Workspace active em Redis hash

- `workspace_registry._active` migra para Redis hash
  (`workspace:active` → `user_id → workspace_id`). Persistência ainda
  em JSON (lista de workspaces); ativo é volátil.

### G6 — Rate limit Redis sliding window

- `services/rate_limit.py` substitui `slowapi` em memória por
  contagem Redis (sliding window). Suporta limites por user_id E
  por OAuth client (Bloco J).

### G7 — Cache opcional de embeddings

- `services/cache_embeddings.py`: `hash(text+model) → vector` em
  Redis com TTL longo (24h). Reduz custo de chamadas Cohere
  repetidas no RAG e nas memórias. Lite: ignora.

### G8 — `langchain-redis` para caches semânticos e history

> Caches G2/G7 são `KV{string→bytes}`. Para 3 features de alto valor,
> usar `langchain-redis` em vez de cozinhar à mão:

- **`RedisCache`**: cache global de LLM completions — drop-in em
  `set_llm_cache(...)`. Mata re-chamadas idênticas dentro da janela
  (default 1h, configurável por modelo).
- **`RedisSemanticCache`**: cache **semântico** de respostas — usa
  embedding do prompt para hit fuzzy. Reduz custo quando user
  reformula mesma pergunta. Opt-in (`[cache] semantic = true`);
  compartilha `Embeddings` do Cohere (F15) para gerar índice.
- **`RedisChatMessageHistory`**: histórico de threads alternativo
  ao SQLite/Postgres — útil em multi-réplica para store único de
  history coerente.
- Convive com G1–G7: KV cru continua para usage/plugins/workspace;
  Redis "semântico" só para LLM/embedding.

### G9 — Tests

- Fixtures `fakeredis` para CI sem docker; CI complete usa Redis
  real.

### Arquivos críticos (Bloco G)

| Sub | Arquivos                                                                                                                                             |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| G1  | `src/services/cache.py` (novo, Protocol + impls memory/redis)                                                                                        |
| G2  | `src/services/llm_tools.py` (refactor: caching local + invalidação Redis)                                                                            |
| G3  | `src/services/plugins.py` (versions em Redis)                                                                                                        |
| G4  | `src/services/usage.py` (sorted set Redis)                                                                                                           |
| G5  | `src/services/workspace.py` (active map em Redis)                                                                                                    |
| G6  | `src/services/rate_limit.py` (novo) substitui `src/api/middleware/rate_limit.py`                                                                     |
| G7  | `src/services/cache_embeddings.py` (novo); `src/services/background.py`, `src/tools/rag.py` (consultam)                                              |
| G8  | `src/services/cache_llm.py` (wraps `RedisCache`/`RedisSemanticCache`); `storage/redis/chat_history.py` (novo); `pyproject.toml` (+`langchain-redis`) |
| G9  | `tests/unit/test_cache_*.py` (novos)                                                                                                                 |

### Verificação (Bloco G)

- Rodar 2 instâncias do Vectora atrás de load balancer: trocar
  `permission_mode` numa requisição → próxima requisição em qualquer
  instância reflete (invalidação via Redis).
- Rate limit 60/min compartilhado entre instâncias.
- Cache de embedding: 2ª requisição idêntica não chama Cohere.

---

## BLOCO H — Deep Agents 1: Skills, AGENTS.md, Prompt Cache, Compressão, Web Tools

> **Contexto.** Depende do **Bloco E** consolidado. Aqui ficam features
> que a arquitetura DeepAgent destrava sem rewrites: skills nativas,
> AGENTS.md memory, prompt caching Anthropic, compressão de contexto,
> profiles e suite completa de web tools.

### H1 — Skills nativas (continuação do C3)

`services/skills.py` expõe `list_skill_paths(user_id) -> list[Path]`
consumido pelo `services/agent_factory.py` (E1) ao montar
`create_deep_agent(skills=[...])`. UI mostra "skill carregada" no
Thinking quando agente acessa o `SKILL.md`. `GET /v1/tools/schema`
(J) ganha `skills_loaded` no resumo.

### H2 — AGENTS.md memory (convenção DeepAgent)

Convenção do DeepAgent para "memória de longo prazo" via filesystem
virtual. Integra com `services/memory.py` C1 — o AGENTS.md do user
vira a visão consolidada das memórias salvas; o `save_memory`
continua escrevendo para memory, mas o agente lê o `AGENTS.md` no
boot da conversa.

### H3 — Prompt caching Anthropic

Anthropic prompt cache para `system_prompt` longo (`VECTORA_IDENTITY`

- `ORCHESTRATOR_PROMPT`) — economia significativa em tokens. Config
  no `agent_factory` via `cache_control: ephemeral`.

### H4 — Compressão de contexto

Middleware default do DeepAgent (summarization). Configurar janela
em `agent_factory` via env `VECTORA_CONTEXT_COMPRESSION_THRESHOLD`
(default: 75% da `context_window` do modelo).

### H5 — Profiles (defaults por provider/modelo)

`src/services/profiles.py`: perfil por provider/modelo (defaults
para Anthropic, OpenAI, Google) consumido pelo `agent_factory` —
inclui sugestão de `reasoning_effort`, `temperature`,
`cache_control`, system prompt overrides.

### H6 — Web tools completas via `langchain-tavily`

Hoje `src/tools/web.py` expõe só 2 tools (`web_search`, `fetch_url`).
A integração `langchain-tavily` traz **6 classes** — adicionar
todas mantendo a convenção de naming "web" (provider Tavily fica
transparente).

| Tool nova                            | Classe              | `render_hint`    | `destructive` |
| ------------------------------------ | ------------------- | ---------------- | ------------- |
| `web_search` (existente, polir args) | `TavilySearch`      | `search_results` | false         |
| `web_fetch` (renomeia `fetch_url`)   | `TavilyExtract`     | `code_block`     | false         |
| `web_crawl`                          | `TavilyCrawl`       | `table`          | false         |
| `web_map`                            | `TavilyMap`         | `table`          | false         |
| `web_research`                       | `TavilyResearch`    | `queue_badge`    | false         |
| `web_get_research`                   | `TavilyGetResearch` | `search_results` | false         |

- **Pareamento research/get_research**: `web_research` dispara job
  assíncrono (devolve `request_id` renderizado como `queue_badge`);
  `web_get_research` consulta pelo `request_id` e devolve achados.
  Padrão idêntico ao `queue_progress` do RAG.
- **Convenção**: nomes, args, descrições e `metadata.icon` usam
  **"web"**.
- **Permission**: `web_crawl`, `web_map` e `web_research` consomem
  mais quota — entram no conjunto que `tool_policy` (C2) pode
  desabilitar por user. `web_research` em particular pode rodar
  por minutos — opt-in por workspace.
- **Render**: frontend já tem `SearchResultsViewer`, `TableViewer`,
  `QueueBadge` — zero código novo.

### Arquivos críticos (Bloco H)

| Sub | Arquivos                                                                                                                                                                                                                             |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| H1  | `src/services/skills.py` (C3) + `src/services/agent_factory.py` (E1)                                                                                                                                                                 |
| H2  | `src/services/memory.py` (gera AGENTS.md a partir das memórias)                                                                                                                                                                      |
| H3  | `src/services/agent_factory.py` (config Anthropic cache)                                                                                                                                                                             |
| H4  | `src/services/agent_factory.py` (compressão como middleware)                                                                                                                                                                         |
| H5  | `src/services/profiles.py` (novo)                                                                                                                                                                                                    |
| H6  | `src/tools/web.py` (+`web_crawl`, +`web_map`, +`web_research`, +`web_get_research`; rename `fetch_url`→`web_fetch`), `src/agents/search.py` (registra 4 tools no toolset), `pyproject.toml` (`langchain-tavily` versão mais recente) |

### Verificação (Bloco H)

- Skill instalada via C3 muda comportamento do agente (carregamento
  on-demand do SKILL.md).
- Cache hit visível no `usage_metadata` da Anthropic.
- Pedir "mapeia o domínio brunosrz.dev" → agente chama `web_map`,
  resultado em TableViewer. Idem `web_crawl` em "indexe docs de
  https://example.com até 3 níveis".

---

## BLOCO I — Deep Agents 2: Sandbox + Worktree, Interpreters, Async, ACP, Remote

> **Contexto.** Depende de E (Deep Agents refactor) e H (skills + web).

### I1 — Sandbox + git worktree integrado (workspace isolado por user)

> **Cardinal.** No modo lite (C4) o terminal opera direto no
> filesystem, confinado por `resolve_within_workspace` (B2). No modo
> "sandbox", cada user ganha sandbox isolada que monta
> automaticamente uma **git worktree** do workspace ativo —
> combinando `deepagents.sandboxes` (`LocalSandbox`, `ModalSandbox`,
> `E2BSandbox`) com `git_worktree` (B3). Dois engineers editam o
> mesmo repo sem pisar no outro.

- **Backends**:
  - `LocalSandbox` (default) — namespace POSIX / Job Object Windows;
    rápido e sem custo (já é o que `deepagents` usa).
  - `ModalSandbox` — containers Modal, ideal para workloads pesados.
  - `E2BSandbox` — VM E2B, máximo isolamento para código
    não-confiável.
- **Provisionamento** (`src/services/sandboxes/registry.py`): ao
  abrir chat com `permission_mode in {auto, bypass}` num workspace
  git, cria `git_worktree add ~/.vectora/sandboxes/<user_id>/
<thread_id> <branch=feat/auto/<thread_id>>` e monta sandbox
  apontando ali. Worktree isolada por `(user_id, thread_id)`.
- **Cleanup**: encerrar thread chama `git_worktree remove` + termina
  sandbox. TTL configurável (default: 7 dias inativa).
- **HITL**: tools destrutivas dentro da sandbox **não pedem
  aprovação** por default — isolamento já é a barreira.
  `permission_mode=ask` continua pedindo se operador quiser
  belt-and-suspenders.
- Reuso: `src/tools/git.py::git_worktree` (B3),
  `src/services/security.py::resolve_within_workspace` (B2) — guards
  apontam para path da worktree em vez do workspace original.

### I2 — Interpretadores Python/JS persistentes

`deepagents` expõe `PythonInterpreter`/`JSInterpreter` como tools
stateful (mantêm variáveis entre calls). Substitui parte do uso de
`terminal` para análise/cálculo. Atalho: orchestrator prefere
interpreter quando tarefa é "compute" puro.

### I3 — Async subagents (paralelismo real)

DeepAgent ≥0.7 permite subagents async-first. Substitui o
`parallel_dispatch` artesanal que hoje roda sequencial; paralelismo
real entre coder/search/rag quando orchestrator escolhe `action:
"parallel"`. O `_synthesize_after_parallel` (orchestrator) continua
intacto.

### I4 — ACP — Vectora como servidor e cliente de outros agentes

- **Server** (`deepagents-acp.server`): expõe agent do Vectora via
  endpoint ACP em `/acp/v1` — clientes ACP (Claude Code, dcode,
  IDEs com plugin ACP) podem invocar Vectora como sub-agente.
- **Adapter** (`deepagents-acp.adapter`): permite consumir agentes
  ACP externos como sub-agente. Útil para terceirizar tarefas
  específicas (ex: agente especialista em pentest).
- **IDE integration** (`deepagents-acp.ide-integration`): conector
  bidirecional com VSCode/JetBrains via extensão oficial — user
  invoca Vectora dentro do editor.
- Auth via Bloco J (OAuth2 client credentials) — mesmo mecanismo
  do REST público.

### I5 — Remote backends (filesystem/sandbox remoto)

`deepagents.backends.RemoteFileSystem` (S3, GCS, Azure Blob) como
backend opcional para filesystem virtual do DeepAgent. Útil para
deploys multi-host.

### I6 — `dcode` como TUI alternativo (opt-in)

> O DeepAgent ecosystem traz seu próprio TUI textual
> (`deepagents-code`, aka `dcode`). É um app textual completo já
> alinhado ao DeepAgent harness.

- `vectora chat --dcode` instancia o app `dcode` apontando para o
  `agent_factory.get_user_agent()` (mesma fábrica do E1).
- Não substitui o `vectora chat` próprio (E7) — convive lado a lado.
  Quem prefere UX padrão usa `--dcode`; quem prefere UX customizada
  usa default.
- Reuso: ambos compartilham agent, auth, secrets, tools.

### Arquivos críticos (Bloco I)

| Sub | Arquivos                                                                                                                                                                                                                                 |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| I1  | `src/services/sandboxes/{registry,local,modal,e2b}.py` (novos); `src/tools/sandbox_exec.py` (novo); reuso de `src/tools/git.py::git_worktree`; `src/services/security.py` (resolve para path da worktree); HITL gate por permission_mode |
| I2  | `src/services/interpreters/{python,js}.py` (novos); registra como tools do `agent_factory`                                                                                                                                               |
| I3  | `src/services/agent_factory.py` (subagents async, substituir parallel_dispatch)                                                                                                                                                          |
| I4  | `src/services/acp/server.py` + `src/services/acp/adapter.py` (novos); `src/api/handlers/acp.py` (mount em `/acp/v1`); `pyproject.toml` (+`deepagents-acp`)                                                                               |
| I5  | `storage/protocols.py` (+`RemoteFileSystem`); `storage/backends/{s3,gcs,azure}.py` (novos)                                                                                                                                               |
| I6  | `src/main.py` (subcomando `chat --dcode`); `pyproject.toml` (+`deepagents-code`)                                                                                                                                                         |

---

## BLOCO J — REST API v1 (OAuth2 Client Credentials + OpenAI-compat + ACP)

> **Contexto.** Vectora já fala 4 modos: CLI, Chat (Connect-RPC + SSE),
> MCP (stdio/SSE), Headless. Falta o 5º: **REST público** para
> integradores externos (n8n, Slack/Discord/Telegram bots, soluções
> corporativas, BI). O argumento de venda é que Vectora vira "kit
> completo" — RAG + IA + auth + governança per-user — atrás de uma
> REST limpa.

### J1 — OAuth2 client credentials

- `src/services/oauth_clients.py`: modelo `OAuthClient` (`client_id`,
  `client_secret_hash`, `name`, `owner_user_id`, `scopes`,
  `created_at`, `revoked_at`). Persistido pela camada storage (F) —
  tabela `vectora_oauth_clients` ou JSON no lite.
- **Endpoints** (`src/api/handlers/oauth_clients.py`):
  - `POST /v1/oauth/clients` (auth cookie/JWT — só o dono cria) →
    retorna `{client_id, client_secret}` **uma única vez**.
  - `GET /v1/oauth/clients` — lista os clients do user atual.
  - `DELETE /v1/oauth/clients/{id}` — revoga.
- **Token endpoint** (público):
  - `POST /v1/oauth/token` (`grant_type=client_credentials`,
    `client_id`/`client_secret`, `scope=` opcional).
  - Retorna JWT 1h `{access_token, token_type:"Bearer",
expires_in:3600, scope}`. Claim `sub = owner_user_id`,
    `client_id`, `scopes`.
- **Scopes** iniciais: `chat`, `threads`, `rag.read`, `rag.write`,
  `workspaces.read`, `workspaces.write`, `memory.read`,
  `memory.write`, `tools.read`, `plugins.read`, `plugins.write`,
  `openai-compat`, `acp`.

### J2 — Middleware bearer + scopes

- `src/api/middleware/oauth_bearer.py`: valida `Authorization:
Bearer <jwt>` para `/v1/*`. Resolve `user_id` do JWT do J1 e
  injeta em `request.state.user` (mesmo `User` do B1 — todo o stack
  downstream — `tool_policy`, plugins, workspaces, secrets —
  funciona sem mudança). `request.state.client_id` e
  `request.state.scopes` para gating fino.
- Rate limit do J (G6 Redis) usa `client_id` como chave (não
  user_id) — um user pode ter múltiplos clients com limites
  independentes.
- 401/403 conforme RFC 6749 (`error="invalid_token"`,
  `error="insufficient_scope"`).

### J3 — Endpoints Vectora-nativos sob `/v1`

- **Chat & Threads**:
  - `POST /v1/chat/stream` (SSE — mesma payload do `StreamChat`
    interno, sem mudança).
  - `POST /v1/chat/resume` (HITL).
  - `POST/GET/DELETE /v1/threads(/{id})`, `GET /v1/threads/{id}/history`.
- **RAG**:
  - `POST /v1/rag/ingest` (`{source: "path|url|text", content?,
path?, url?, collection="articles", metadata}`).
  - `GET /v1/rag/search` (`?q=...&collection=articles&k=5`).
  - `GET /v1/rag/collections`; `DELETE /v1/rag/collections/{name}`
    (scope `rag.write`).
- **Workspaces**:
  - `GET/POST /v1/workspaces`, `GET /v1/workspaces/{id}`.
  - `POST /v1/workspaces/{id}/trust`, `POST /v1/workspaces/{id}/git-init`.
  - `GET /v1/workspaces/{id}/worktrees`,
    `POST /v1/workspaces/{id}/worktrees`.
  - `DELETE /v1/workspaces/{id}`.
- **Memory**:
  - `GET/POST /v1/memory`, `GET/PUT/DELETE /v1/memory/{key}`.
- **Tools**:
  - `GET /v1/tools` (toolset efetivo do user/client — built-ins
    minus deny + MCP).
  - `GET/PUT /v1/tools/policy`.
- **Plugins/Skills**:
  - `GET/POST /v1/plugins`, `DELETE /v1/plugins/{name}`,
    `POST /v1/plugins/{name}/verify`.
  - `GET/POST /v1/skills`, `DELETE /v1/skills/{name}`.
- **Headers semânticos** (opcionais):
  `X-Vectora-Workspace-Id` força workspace específico;
  `X-Vectora-Rag-Collection`, `X-Vectora-Permission-Mode`.

### J4 — Compatibilidade OpenAI

- `src/api/handlers/openai_compat.py`:
  - `GET /v1/models` — `{data:[{id, object:"model", ...}],
object:"list"}` a partir de `src/config/settings.py::
AVAILABLE_MODELS`.
  - `POST /v1/chat/completions` — aceita shape OpenAI
    (`{model, messages:[{role,content}], stream, temperature?,
max_tokens?, response_format?}`). Tradutor
    `_translate_openai_to_streamchat()` monta `StreamChatRequest`;
    chama mesmo handler interno; transforma saída de volta: - `stream=true` (SSE): `data:
{choices:[{delta:{content}}]}\n\n` por chunk + `data:
[DONE]\n\n`. - `stream=false`: agrega e devolve
    `{choices:[{message:{content}}], usage, model, ...}` no shape
    `chat.completion`.
  - `POST /v1/embeddings` (opcional v1.1): wrapper sobre Cohere para
    clientes que esperam endpoint OpenAI.
- **Multimodal**: `messages[].content` array com `{type:"image_url"}`
  é mapeado para `Attachment(kind=IMAGE)` do schema interno.

### J5 — OpenAPI / Docs

- FastAPI já gera. Expor:
  - `GET /v1/openapi.json` (público).
  - `GET /v1/docs` (Swagger UI público; "Try it out" requer Bearer
    obtido em `/v1/oauth/token`).
- Documentação curta em `docs/rest-api.md` com exemplos
  OpenAI-compat (curl + n8n HTTP node + Python OpenAI SDK apontando
  `base_url=https://<host>/v1`).

### J6 — Frontend (Settings tab "API")

- `chat/components/layout/settings-dialog/tabs/api-tab.tsx`:
  - Listar OAuth clients do user (nome, criado em, scopes, último
    uso).
  - "Criar client" → modal com nome + scopes → mostra
    `client_secret` UMA VEZ (botão copiar) + warning de que não
    será exibido novamente.
  - Revogar.
  - Link para `/v1/docs`.
- Proxy Hono `chat/server/routes/oauth_clients.ts` (CRUD via
  cookie).
- i18n `api.*`.

### J7 — Endpoint ACP público

- Expõe ACP server (I4) em `/v1/acp/*` sob OAuth2 client credentials
  do J1 — clientes externos (Claude Code, dcode, IDEs) conectam
  usando mesmo `client_id`/`client_secret`. Scope dedicado: `acp`.
- A IDE-integration (I4) aponta para esse endpoint quando user
  conecta editor a servidor Vectora remoto.

### J8 — Tests

- `tests/unit/test_api_v1_oauth.py`: criação de client, token grant,
  scope enforcement, revogação, expiração.
- `tests/unit/test_api_v1_chat.py`: streaming nativo + OpenAI-compat
  (stream e non-stream).
- `tests/unit/test_api_v1_rag.py`: ingest + search com OAuth.
- `tests/unit/test_api_v1_workspaces.py`, `_memory.py`, `_tools.py`,
  `_plugins.py`.
- `tests/unit/test_api_v1_openai_compat.py`: shape OpenAI
  (validação JSON schema dos response objects).

### Arquivos críticos (Bloco J)

| Sub | Arquivos chat                                                                                          | Arquivos vectora                                                                                                                                                                          |
| --- | ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| J1  | —                                                                                                      | `src/services/oauth_clients.py`, `storage/{sqlite,postgres}/oauth_clients.py`, `src/api/handlers/oauth_clients.py` (novos)                                                                |
| J2  | —                                                                                                      | `src/api/middleware/oauth_bearer.py` (novo), `src/api/server.py` (registrar middleware), `src/api/middleware/auth.py` (`/v1/` é público p/ esse middleware — cobertura é do oauth_bearer) |
| J3  | —                                                                                                      | `src/api/handlers/v1/{chat,threads,rag,workspaces,memory,tools,plugins,skills}.py` (delegam aos services internos já existentes)                                                          |
| J4  | —                                                                                                      | `src/api/handlers/openai_compat.py` (novo)                                                                                                                                                |
| J5  | —                                                                                                      | `src/api/server.py` (rotas docs `/v1`), `docs/rest-api.md`                                                                                                                                |
| J6  | `chat/components/layout/settings-dialog/tabs/api-tab.tsx`, `chat/server/routes/oauth_clients.ts`, i18n | —                                                                                                                                                                                         |
| J7  | —                                                                                                      | `src/api/handlers/v1/acp.py` (mount I4 server sob `/v1/acp`); reuso de `src/services/acp/server.py`                                                                                       |
| J8  | —                                                                                                      | `tests/unit/test_api_v1_*.py` (novos)                                                                                                                                                     |

### Verificação (Bloco J)

- `POST /v1/oauth/token` com client creds devolve JWT 1h.
- n8n HTTP node `Authorization: Bearer <token>` em `POST
/v1/chat/stream` → SSE chega no n8n.
- Cliente OpenAI Python apontando `base_url=https://<host>/v1` e
  `api_key=<token>` chama `client.chat.completions.create(...,
stream=True)` e recebe streaming compatível.
- Scope `rag.write` consegue `POST /v1/rag/ingest`; sem o scope → 403.
- Revogar client invalida tokens existentes (token check via
  `client_id`).
- 2 clients do mesmo user têm rate limits independentes (G6 Redis).

---

## ============================================================================

## ⏳ PROFISSIONALIZAÇÃO: blocos K–N (billing, SDK, observability, distribution)

## ============================================================================

## BLOCO K — Billing & License Infra: Supabase + Stripe + Asaas + Tier Enforcement

> **Contexto.** O license gate (C7) valida `VECTORA_TOKEN` contra uma
> edge function. Falta construir a infra completa que emite tokens,
> processa pagamentos, gerencia subscriptions e expõe métricas. O
> público-alvo é misto (Brasil + internacional) — Stripe não cobre
> PIX/boleto bem em recorrência via Customer Portal, então Asaas
> entra como provedor BR-first, mantendo Stripe para USD/cartão
> internacional.

### K1 — Supabase schema + RLS (Backend SaaS)

Migrations em `vectora-company/supabase/migrations/`:

**`profiles`** (estende `auth.users`):

```sql
id uuid PK REFERENCES auth.users(id)
full_name text
company text
country text CHECK (country IN ('BR', 'INTL'))  -- routing K5
created_at timestamptz DEFAULT now()
```

**`tokens`** (VECTORA_TOKEN por usuário):

```sql
id uuid PK DEFAULT gen_random_uuid()
user_id uuid REFERENCES profiles(id) ON DELETE CASCADE
token text NULL              -- raw, exibido UMA vez e apagado
token_hash text UNIQUE NOT NULL  -- SHA-256
created_at timestamptz DEFAULT now()
rotated_at timestamptz
```

**`subscriptions`**:

```sql
id uuid PK
user_id uuid REFERENCES profiles(id) ON DELETE CASCADE
tier text NOT NULL  -- 'plus' | 'pro'
status text NOT NULL  -- 'trialing' | 'active' | 'past_due' | 'canceled' | 'expired'
trial_ends_at timestamptz
current_period_start timestamptz NOT NULL
current_period_end timestamptz NOT NULL
provider text NOT NULL  -- 'stripe' | 'asaas' | 'manual'
provider_sub_id text     -- Stripe sub / Asaas subscription ID
currency text NOT NULL   -- 'BRL' | 'USD'
amount_cents integer NOT NULL
created_at/updated_at timestamptz
```

**`license_checks`** (auditoria):

```sql
id uuid PK
user_id uuid REFERENCES profiles(id)
token_hash text NOT NULL
result text NOT NULL  -- 'valid' | 'invalid' | 'expired' | 'trial'
tier text
ip text
vectora_version text
checked_at timestamptz DEFAULT now()
```

**`payment_events`** (webhook log dedup):

```sql
id uuid PK
provider text NOT NULL
provider_event_id text UNIQUE NOT NULL  -- evita reprocess
event_type text NOT NULL
subscription_id uuid REFERENCES subscriptions(id)
payload jsonb NOT NULL
processed_at timestamptz DEFAULT now()
```

**RLS**: `profiles`, `tokens`, `subscriptions` com policy `own_*`
(auth.uid() = user_id). `license_checks` e `payment_events` sem
policy pública (apenas `service_role` via edge functions).

### K2 — Edge functions (`supabase/functions/`)

- **`on-signup`** (trigger `auth.users INSERT`):
  1. Cria `profiles`.
  2. Gera token `vct_` + 96 hex chars via
     `crypto.getRandomValues(new Uint8Array(48))`. SHA-256 do raw.
  3. Insere em `tokens` (raw para exibição única + hash).
  4. Cria `subscriptions` trial 30 dias Plus.

- **`validate-license`** (chamada pelo Vectora Agent):
  - `POST {token, vectora_version}` → busca por hash, checa
    subscription, computa `days_remaining`, audita em
    `license_checks`.
  - 401 token inválido, 402 expirado, 200 ok com payload completo.
  - Rate limit: 20 validações/hora por token (cache local 6h no
    Agent cobre o caso geral).

- **`get-token`** (reveal único, auth Supabase JWT):
  - `GET` → retorna `token` raw + apaga do banco (apenas hash
    permanece). Segunda chamada → `revealed: false`.

- **`rotate-token`**: invalida anterior + gera novo + apaga após
  reveal.

- **`create-checkout`**: cria sessão Stripe Checkout para INTL ou
  Asaas Checkout para BR. Detecta país via `Accept-Language` + IP.
  Currency `usd` (INTL) ou `brl` (BR).

- **`stripe-webhook`**: processa eventos:
  - `checkout.session.completed` → `status='active'`, atualiza
    tier.
  - `invoice.payment_succeeded` → renova `current_period_end`.
  - `customer.subscription.updated` → atualiza tier (upgrade/
    downgrade).
  - `customer.subscription.deleted` → `status='canceled'`.
  - Dedup via `provider_event_id` em `payment_events`.

- **`asaas-webhook`**: processa eventos
  ([docs.asaas.com](https://docs.asaas.com/docs/payment-events)):
  - `PAYMENT_CREATED` → cobrança nova (nova fatura da subscription).
  - `PAYMENT_CONFIRMED` → pagamento feito, saldo não disponível.
  - `PAYMENT_RECEIVED` → recebido (saldo liberado), renova
    `current_period_end`.
  - `PAYMENT_OVERDUE` → `status='past_due'`, banner amarelo no chat.
  - `SUBSCRIPTION_DELETED` → `status='canceled'`.
  - Dedup via `provider_event_id`.

- **`create-portal`**: roteia para Stripe Customer Portal (INTL) ou
  Asaas dashboard endpoint equivalente (BR — Asaas suporta
  cancelamento e atualização via API, frontend embutido no site).

### K3 — Stripe products & subscriptions (INTL)

- **Produtos**:
  - `vectora_plus_monthly` — $7 USD
  - `vectora_pro_monthly` — $20 USD
- Stripe Checkout aceita `currency: "usd"`, métodos card + Apple
  Pay + Google Pay + Link.
- **Proration automática** em upgrade Plus → Pro (Stripe aplica
  crédito proporcional).
- **Customer Portal** para cancelar/upgrade self-service. Habilitar
  via Stripe Dashboard → "Customer portal".

### K4 — Asaas integration (BR: PIX + Boleto + Cartão recorrente)

> Asaas é o provedor BR-first. Cobertura: PIX (instantâneo + Pix
> Automático recorrente regulado pelo Banco Central — exigência
> 5M BRL net equity para participantes desde 2026-01-01), Boleto
> (mín R$5, máx R$49.999,99), Cartão (recurring nativo).

**API base**: `https://api.asaas.com/v3/` (produção) ou
`https://sandbox.asaas.com/api/v3/` (sandbox). Auth: header
`access_token: $ASAAS_API_KEY`.

**Fluxo subscription** (`docs.asaas.com/docs/creating-a-subscription`):

1. **Customer**: `POST /v3/customers` com `name`, `cpfCnpj`,
   `email` → retorna `id`.
2. **Subscription**: `POST /v3/subscriptions` com `customer`,
   `billingType` (`PIX` | `BOLETO` | `CREDIT_CARD` | `UNDEFINED`
   que deixa user escolher por cobrança), `value`, `nextDueDate`,
   `cycle: "MONTHLY"`, `description: "Vectora Plus"`,
   `externalReference: <user_id>`.
3. **Webhook**: configurar URL via `POST /v3/webhooks` apontando
   para `supabase.co/functions/v1/asaas-webhook` com auth token
   `ASAAS_WEBHOOK_TOKEN`. Eventos: `PAYMENT_CREATED`,
   `PAYMENT_CONFIRMED`, `PAYMENT_RECEIVED`, `PAYMENT_OVERDUE`,
   `SUBSCRIPTION_*`.

**Produtos BR**:

- `vectora_plus_monthly_brl` — R$20
- `vectora_pro_monthly_brl` — R$55

**Cupons** (early adopter): cupons criados no Asaas + Stripe
manualmente (`VECTORA25` 25% off Plus 100 redemptions; `PROEARLY`
~18% off Pro 50 redemptions; ambos `duration: "forever"`).

### K5 — Payment routing (BR via Asaas, INTL via Stripe)

Edge function `create-checkout` decide provider:

- `profiles.country = 'BR'` ou `Accept-Language` contém `pt-BR` ou
  IP geolocate Brasil → **Asaas** (PIX + boleto + cartão BR).
- Caso contrário → **Stripe** (cartão internacional).

Usuário sempre pode override no dashboard ("Pagar via Stripe
internacional" como link secundário em BR).

### K6 — Tier enforcement no Vectora Agent (hooks por backend)

Camada storage (F) e cache (G) consultam `VECTORA_TIER`:

```python
# storage/factory.py
def get_checkpointer():
    backend = settings.checkpointer_backend
    if backend == "postgres" and os.environ["VECTORA_TIER"] == "plus":
        raise LicenseError(
            "Postgres checkpointer requer plano Pro. "
            "Upgrade em https://vectora.company/pricing."
        )
    ...
```

Aplicado em: Postgres checkpointer (F4), Postgres store (F5),
Qdrant/pgvector vector store (F6), Postgres queue (F8), Redis cache
(G). Múltiplos workers simultâneos no uvicorn também gate (>1
worker exige Pro).

Frontend admin storage panel (F10): opções Pro desabilitadas com
badge "Pro only" quando `tier=plus`. Link "Fazer upgrade" abre
Customer Portal via `shell.openExternal()` (D6).

### K7 — License banners frontend (consumindo `/license/status`)

Banner único no header `chat/components/layout/license-banner.tsx`:

- **Sem token configurado** (laranja): `⚠ VECTORA_TOKEN não
configurado. Configure em Configurações → Envs.` Botão
  "Configurar".
- **Trial ≤ 7 dias** (amarelo): `⏳ Trial expira em N dias.
Assine para continuar.` Botão "Assinar".
- **`past_due`** (laranja): `⚠ Pagamento em atraso. Regularize em
vectora.company/dashboard.`
- **Licença expirada** (vermelho, bloqueia input): `❌ Licença
expirada.` Botão "Renovar".

Consome `GET /api/license/status` que faz proxy para
`/license/status` (C7). SWR 5min + after-login + on-focus.

### K8 — Onboarding wizard pós-root (no chat web)

Modal multi-step que aparece no primeiro login do root:

1. **VECTORA_TOKEN**: input + valida via `/api/license/validate`.
   Botão "Pular por agora" → banner laranja persistente.
2. **Provedor de IA**: select (Gemini/OpenAI/Anthropic/Ollama) +
   API Key + Testar conexão → salva via `POST /api/auth/envs`.
3. **Cohere (RAG)**: input + Testar → salva via envs. "Pular" →
   aviso de capacidade reduzida.
4. **Conclusão**: links rápidos para "Adicionar usuários",
   "Criar workspace", "Começar a conversar".

Flag `vectora-onboarding-done-{userId}` em localStorage previne
reabrir.

### K9 — Tests

- **Webhook signature verification** (Stripe HMAC SHA-256 +
  Asaas token bearer): garantir que payload modificado é rejeitado.
- **Webhook idempotency**: dispatch mesmo `provider_event_id` 2x
  → segunda chamada vira no-op (dedup via `payment_events`).
- **Mock providers**: testes unitários sem chamada real à Stripe/
  Asaas — `tests/mocks/stripe.py`, `tests/mocks/asaas.py`.
- **Tier enforcement**: tentar montar Postgres checkpointer com
  `VECTORA_TIER=plus` → `LicenseError`.

### Arquivos críticos (Bloco K)

| Sub | Arquivos chat                                                                                  | Arquivos vectora                                            | Arquivos vectora-company                                                                                                                                     |
| --- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| K1  | —                                                                                              | —                                                           | `vectora-company/supabase/migrations/00{1..5}_*.sql` (novos)                                                                                                 |
| K2  | —                                                                                              | —                                                           | `vectora-company/supabase/functions/{on-signup,validate-license,get-token,rotate-token,create-checkout,stripe-webhook,asaas-webhook,create-portal}/index.ts` |
| K3  | —                                                                                              | —                                                           | docs Stripe products no `vectora-company/docs/stripe.md`                                                                                                     |
| K4  | —                                                                                              | —                                                           | `vectora-company/supabase/functions/_shared/asaas.ts` (cliente Asaas)                                                                                        |
| K5  | —                                                                                              | —                                                           | logic no `create-checkout`                                                                                                                                   |
| K6  | F10 storage panel (badge "Pro only")                                                           | `storage/factory.py` (gate), `src/services/cache.py` (gate) | —                                                                                                                                                            |
| K7  | `chat/components/layout/license-banner.tsx` (novo); proxy Hono `chat/server/routes/license.ts` | `src/api/handlers/license.py` (+`POST /portal`)             | —                                                                                                                                                            |
| K8  | `chat/components/onboarding/setup-wizard.tsx` (novo, multi-step modal)                         | —                                                           | —                                                                                                                                                            |
| K9  | —                                                                                              | `tests/unit/test_license_tier_gate.py` (novo)               | `vectora-company/supabase/functions/__tests__/`                                                                                                              |

### Verificação (Bloco K)

- Signup no site (Supabase Auth) → trigger `on-signup` cria
  `profiles + tokens + subscriptions(trialing 30d)`. Dashboard
  mostra token revelável uma vez.
- `validate-license` com token válido → `{valid:true, tier:"plus",
status:"trialing", days_remaining:30}`.
- BR: signup com `country='BR'` → `create-checkout` retorna
  Asaas Checkout (PIX + Boleto + Cartão). Pagar PIX → webhook
  `PAYMENT_RECEIVED` → `status='active'`.
- INTL: signup com `country='INTL'` → `create-checkout` retorna
  Stripe Checkout → pagar cartão → `checkout.session.completed`
  → `status='active'`.
- Upgrade Plus → Pro: Stripe proration automática; Asaas:
  cancela subscription Plus + cria Pro.
- Tier=plus tenta montar Postgres → `LicenseError` com link de
  upgrade. Tier=pro aceita.
- Trial banner muda cor conforme dias; expirado bloqueia input.
- Onboarding wizard aparece no 1º login root, não reabre depois.

---

## BLOCO L — SDKs & API Ecosystem

> **Contexto.** Bloco J entrega a REST `/v1`. Para tração com
> integradores, precisamos de SDKs oficiais (Python + TypeScript),
> webhooks bem documentados para integração reverse (Vectora →
> sistemas externos), e ferramentas de DX (GitHub Actions, Postman).

### L1 — Python SDK (`vectora-sdk`)

Pacote separado em `sdks/python/`:

- **`VectoraClient`** sync + **`AsyncVectoraClient`** async (httpx
  back-end).
- Auth: `client = VectoraClient(api_key="vct_...", base_url="...")`
  ou via `VECTORA_API_KEY` env.
- Métodos espelham `/v1/*`:
  - `chat.stream(messages, model, ...)` → generator de eventos.
  - `chat.completions.create(...)` → compat OpenAI (alias).
  - `threads.create/list/get/delete/history`.
  - `rag.ingest(source, collection)`, `rag.search(q, k=5)`.
  - `workspaces.list/create/trust`.
  - `memory.list/save/delete`.
  - `tools.list/policy`.
- Retry exponencial em `429`/`5xx` (backoff 0.5s → 16s, 5 tries).
- Streaming SSE parsing via `httpx-sse`.
- Type hints completos via `pydantic` v2.
- Publish: PyPI público (livre, separado do `vectora-cli` mirror
  D7).

### L2 — TypeScript SDK (`@vectora/sdk`)

Pacote em `sdks/typescript/`:

- **Universal** (Node 20+ e browser) via `cross-fetch` ou nativo
  `fetch`.
- Auth: `new VectoraClient({ apiKey: "vct_...", baseUrl: "..." })`.
- Métodos paralelos à L1.
- **SSE parsing** via `eventsource-parser` (sem polyfill DOM).
- Type-safe events: `client.chat.stream({...}).on("token", ...)`.
- Tree-shakeable; sub-imports
  `@vectora/sdk/chat`, `@vectora/sdk/rag`.
- Publish: npm público, dual `cjs`/`esm`.

### L3 — Webhooks (Vectora → sistemas externos)

> Hoje só o `validate-license` é "webhook entrante". Falta o
> reverso: notificar sistemas externos quando eventos relevantes
> ocorrem no Vectora.

**Modelo `Webhook`** (no DB principal):

```python
id: str  # sha256[:12]
user_id: str
url: HttpUrl
secret: str  # HMAC-SHA256 key
events: list[str]  # ["thread.created", "rag.indexed", ...]
active: bool
created_at: str
last_delivery_at: str | None
last_status: int | None
```

**Eventos suportados**:

- `thread.created`, `thread.updated`, `thread.deleted`
- `message.created`, `message.completed`
- `rag.indexed`, `rag.queue_failed`
- `tool.executed` (incluindo destructive)
- `workspace.created`, `workspace.trusted`
- `license.expired`, `license.renewed`
- `plugin.installed`, `skill.installed`

**Delivery**:

- POST `{event, data, timestamp, webhook_id}` ao endpoint.
- Header `X-Vectora-Signature: sha256=<hex>` HMAC do body com
  `secret`.
- Header `X-Vectora-Event: thread.created`.
- Retry exponencial 3x (1s, 5s, 25s) em `4xx`/`5xx`. Após 3 falhas
  → DLQ + email ao user.
- Worker async em `src/services/webhook_dispatcher.py` consome
  fila `vectora_webhook_queue`.

**Endpoints** (`src/api/handlers/webhooks.py`):

- `GET/POST /v1/webhooks` (CRUD).
- `GET /v1/webhooks/{id}/deliveries` (últimas 50 entregas).
- `POST /v1/webhooks/{id}/test` (envia evento fake).

**Frontend**: aba "Webhooks" no Settings → API com lista + form
add/remove + deliveries log.

### L4 — GitHub Actions oficiais (`vectora/setup-action`)

Repositório `vectora-company/setup-action`:

```yaml
- uses: vectora/setup-action@v1
  with:
    api-key: ${{ secrets.VECTORA_API_KEY }}
    version: latest # ou específica
```

Action que:

1. Instala `vectora-cli` no runner.
2. Faz login com `api-key`.
3. Adiciona `vectora` ao PATH.

Action complementar `vectora/chat-action` para rodar prompt
único em CI:

```yaml
- uses: vectora/chat-action@v1
  with:
    prompt: "Resume o diff deste PR e sugira melhorias"
    workspace: ${{ github.workspace }}
```

### L5 — OpenAPI polish + Swagger UI customizado

- Gerar OpenAPI 3.1.0 spec completa via FastAPI; revisar
  descrições, exemplos, error responses.
- Swagger UI customizado (dark theme Vectora, logo,
  `tryItOutEnabled: true`).
- "Authorize" botão flui via `client_credentials` (J1) — UI
  expõe form `client_id`/`client_secret` → busca token via
  `/v1/oauth/token` automaticamente.
- Re-publish `openapi.json` em `docs.vectora.company/openapi.json`
  para uso por geradores de SDK terceiros (OpenAPI Generator,
  swagger-codegen).

### L6 — Postman / Insomnia collections

`sdks/collections/`:

- `vectora-v1.postman_collection.json` — todas as rotas + auth
  helper (`{{base_url}}`, `{{access_token}}` via
  `pre-request script` que faz `/v1/oauth/token`).
- `vectora-v1.insomnia.json` — equivalente.
- Publish em postman.com workspace público "Vectora API" +
  insomnia.rest community library.

### Arquivos críticos (Bloco L)

| Sub | Arquivos                                                                                                                                                                      |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| L1  | `sdks/python/` (novo repo ou subpasta), CI publish PyPI                                                                                                                       |
| L2  | `sdks/typescript/` (novo), CI publish npm                                                                                                                                     |
| L3  | `src/types/webhook.py`, `src/services/webhook_dispatcher.py`, `src/api/handlers/webhooks.py` (novos); `chat/components/layout/settings-dialog/tabs/webhooks-panel.tsx` (novo) |
| L4  | `setup-action/` + `chat-action/` (novos repos em `vectora-company/`)                                                                                                          |
| L5  | `src/api/server.py` (Swagger config), `docs/openapi-spec.md`                                                                                                                  |
| L6  | `sdks/collections/` (novo)                                                                                                                                                    |

### Verificação (Bloco L)

- `pip install vectora-sdk` → cliente Python conecta, chama
  `client.chat.completions.create(...)` com streaming.
- `npm install @vectora/sdk` → cliente TS no Node funciona; no
  browser idem (com CORS).
- Webhook: configurar URL test → criar thread → POST recebido
  com `X-Vectora-Signature` válido.
- GitHub Action: workflow consome `setup-action` → `vectora --version`
  funciona no runner.
- Swagger UI: clicar "Authorize" → input client_id/secret →
  "Try it out" em `POST /v1/chat/stream` recebe SSE.
- Postman collection: importar → Auth helper popula token → POST
  `/v1/threads` cria.

---

## BLOCO M — Observability & Reliability Production-Grade

> **Contexto.** Hoje `VectoraTracer` SQLite + `/metrics` (A1) é base
> básica. Em produção self-hosted ou em vendas para empresas
> precisamos: tracing distribuído, error tracking, structured
> logging, health probes, SLOs públicos, backup/DR.

### M1 — OpenTelemetry (traces + metrics + logs)

- **Instrumentação automática** via `opentelemetry-distro` +
  instrumentations para FastAPI, httpx, sqlalchemy, asyncpg, redis.
- **Custom spans** nos hot paths:
  - `agent.invoke` (root span por request).
  - `tool.execute.<tool_name>`.
  - `rag.retrieve`, `rag.rerank`.
  - `llm.call.<provider>.<model>` (com `tokens_in`, `tokens_out`,
    `cost_usd`).
- **Export**: OTLP via env (`OTEL_EXPORTER_OTLP_ENDPOINT`,
  `OTEL_EXPORTER_OTLP_HEADERS`). Suporta Honeycomb, Datadog,
  Jaeger, Tempo, qualquer collector OTLP.
- **Sampling**: head-based 10% default + tail-sampling para
  errors via `OTEL_TRACES_SAMPLER=parentbased_traceidratio`.
- **Resource attributes**: `service.name=vectora`,
  `service.version`, `deployment.environment`, `vectora.tier`.

### M2 — Sentry (error tracking + performance)

- `sentry-sdk[fastapi]>=2.0` integrado em `src/api/server.py` e
  `desktop/main.ts` (`@sentry/electron`).
- DSN via env `SENTRY_DSN`; opt-out via env vazia (default).
- **Breadcrumbs** automáticos: HTTP requests, SQL queries, tool
  calls.
- **Performance monitoring**: traces sample rate 5% +
  `enable_tracing=True`.
- **PII scrubbing**: filtros para `messages`, `attachments`,
  `tool_args` (regex masking de emails, tokens, paths sensíveis).
- **Release tracking**: `release=vectora@<version>` no init.

### M3 — Structured logging (JSON, correlation IDs)

- `structlog` substitui `logging` em hot paths
  (`src/services/log_setup.py` refactor).
- **Correlation ID** por request: middleware
  `src/api/middleware/correlation.py` extrai
  `X-Correlation-Id` do header ou gera UUID4; injeta em
  `contextvars`; toda log line carrega.
- **Format**: JSON em produção (`LOG_FORMAT=json`), pretty em dev
  (`LOG_FORMAT=console`).
- **Campos padrão**: `timestamp`, `level`, `logger`, `message`,
  `correlation_id`, `user_id`, `thread_id`, `tool_name` (quando
  aplicável).
- Compatível com agregadores (Loki, ELK, Datadog Logs).

### M4 — Health probes (Kubernetes-style)

`src/api/handlers/health.py` expande de `/health` único para 3:

- **`GET /health/live`** — processo está vivo. Retorna 200 se
  Python responde (no DB check). Para liveness probe.
- **`GET /health/ready`** — pronto pra receber tráfego. Checa:
  - DB connection (timeout 2s).
  - Vector store reachable.
  - Cache reachable (se Redis configurado).
  - License cached e válido.
    Retorna 503 se algum falha. Para readiness probe.
- **`GET /health/startup`** — boot completo. Checa que migrations
  rodaram e checkpointer está pronto. Para startup probe.

Documentar em `docs/k8s-deploy.md` com `livenessProbe`/
`readinessProbe`/`startupProbe` YAML.

### M5 — SLOs + Status Page

- **SLOs definidos** em `docs/slos.md`:
  - `/v1/chat/stream` p95 latency < 1s (first token), error rate
    < 0.5%.
  - `/v1/rag/search` p95 < 500ms.
  - `/license/status` p95 < 100ms (cache hit).
  - Uptime mensal ≥ 99.5%.
- **Status page** em `status.vectora.company` via BetterStack ou
  Statuspage.io:
  - Componentes: API REST, Chat SSE, Validate License (Supabase),
    Site, Docs.
  - Incidentes manuais + checks automáticos a cada 1min.
  - Subscribe via email/RSS.
- **Histórico de incidentes** público.

### M6 — Backup automation + restore CLI

- **`vectora backup create [--output <path>]`**:
  - Lite: SQLite `.backup` API (todos os 3 bancos) + LanceDB
    snapshot (cp recursivo do `lancedb/`) + safe_roots.json +
    workspaces.json + KeePassXC vaults. Tar.gz com timestamp.
  - Completo: `pg_dump` + Qdrant snapshot API + Redis `BGSAVE` +
    upload para destino (S3, GCS, local).
- **`vectora backup restore <archive>`**: inversa, com
  confirmação interativa.
- **Agendamento**: cron via `vectora backup schedule daily`
  (escreve crontab user-level ou systemd timer) ou via
  `~/.vectora/config.toml`.
- **Encryption**: opcional via `--encrypt` (passphrase + AES-256-GCM
  via `cryptography`).

### M7 — Disaster recovery playbook

`docs/disaster-recovery.md`:

- Cenários cobertos: corrupção SQLite, Postgres crash, perda total
  do servidor, perda de chave de criptografia KeePassXC,
  comprometimento de `auth.key`.
- Procedimento step-by-step para cada cenário com tempos de RTO
  (Recovery Time Objective) e RPO (Recovery Point Objective)
  esperados.
- **Tests anuais**: `vectora backup restore` em VM staging para
  validar.

### Arquivos críticos (Bloco M)

| Sub | Arquivos                                                                                                                   |
| --- | -------------------------------------------------------------------------------------------------------------------------- |
| M1  | `src/services/telemetry/otel.py` (novo); `pyproject.toml` (+ otel deps); `desktop/src/telemetry.ts`                        |
| M2  | `src/api/server.py` (sentry init), `desktop/src/main.ts` (sentry/electron init), `pyproject.toml` (+`sentry-sdk[fastapi]`) |
| M3  | `src/services/log_setup.py` (refactor structlog), `src/api/middleware/correlation.py` (novo)                               |
| M4  | `src/api/handlers/health.py` (refactor: live/ready/startup), `docs/k8s-deploy.md`                                          |
| M5  | `docs/slos.md`, BetterStack setup (terraform opcional)                                                                     |
| M6  | `src/services/backup.py` (novo), `src/main.py` (subcomando `backup`)                                                       |
| M7  | `docs/disaster-recovery.md`                                                                                                |

### Verificação (Bloco M)

- Trace de um request `/v1/chat/stream` aparece no Honeycomb com
  spans `agent.invoke → tool.execute → llm.call`.
- Bug intencional → Sentry captura com breadcrumbs (HTTP, SQL).
- Log em prod é JSON com `correlation_id`; mesmo ID aparece em
  todas as linhas do request.
- `/health/ready` retorna 503 se Postgres derrubado; volta 200
  após recovery.
- Status page mostra uptime histórico + componentes.
- `vectora backup create` → tar.gz contendo todos os dados;
  `vectora backup restore` em VM nova reconstrói operacional.

---

## BLOCO N — Distribution Hardening & IDE Integrations

> **Contexto.** Bloco D entregou pipeline base de Nuitka + Electron.
> Bloco N expande para canais nativos por OS, multi-arch, integrações
> com editores e workflows. Habilita "instalar via `brew install
vectora`" / `apt install vectora` / VS Code Marketplace.

### N1 — Multi-arch builds (x86_64 + arm64)

- GitHub Actions matrix com `arch: [amd64, arm64]` por OS:
  - Win: cross-compile via Nuitka (`--target=arm64` quando
    suportado) ou self-hosted runner ARM Windows.
  - macOS: nativo arm64 (Apple Silicon runners disponíveis).
    Universal binary via `lipo` ou electron-builder `--universal`.
  - Linux: cross-compile via QEMU + Docker `buildx`.
- Validar boot em cada arch.

### N2 — Code signing pipeline aprofundado

- **Reuse** de D3 (Azure Trusted Signing Win + Apple notarize
  macOS + GPG Linux).
- **Adicionar**:
  - Timestamping com RFC3161 (`http://timestamp.digicert.com`)
    para Windows.
  - macOS notarization staple completo via `xcrun stapler`.
  - Auto-renewal de certificados via Vault/1Password CLI no CI.
- **Verificação automática pós-build**: `signtool verify /pa`,
  `codesign --verify --deep --strict`,
  `gpg --verify .deb.asc .deb`.

### N3 — Auto-update channel server avançado

- **Reuse** de D4 (channel server básico).
- **Adicionar**:
  - **Phased rollout**: novo release vai para 5% dos usuários por
    24h, depois 25%, depois 100%. Configurável via
    `vectora-company/update-server/config.yml`.
  - **A/B channels** (`stable`, `beta`, `nightly`): user escolhe
    no Settings → Avançado.
  - **Telemetria de update**: `update_started`, `update_completed`,
    `update_failed` reportados ao Sentry (M2) anonimizados.
  - **Rollback automático**: se 3+ usuários em 1h reportam
    `update_failed` na mesma versão → channel server marca
    versão como `quarantined` e novos clients param de baixar.

### N4 — Docker images oficiais

- `vectora/vectora:latest`, `vectora/vectora:1.0.0` em Docker Hub
  - GHCR (`ghcr.io/vectora-company/vectora`).
- **Multi-stage Dockerfile**:
  - Stage 1: build do frontend (`node:24-alpine`).
  - Stage 2: build do backend (`python:3.13-slim`).
  - Stage 3: runtime mínimo (Distroless ou
    `python:3.13-slim` com `--no-install-recommends`).
- Variants:
  - `:latest` (default Plus, lite storage).
  - `:pro` (extras: postgres client, qdrant CLI).
- Image scanning via Trivy no CI (block merge se CVE high+).

### N5 — Linux distros (APT/DNF/Flathub/Snap)

- **APT** (`apt install vectora`):
  - Repo `apt.vectora.company` (debian + ubuntu pools).
  - GPG signed packages.
  - `aptly` ou `reprepro` para gerenciar repo.
- **DNF/YUM** (`dnf install vectora`):
  - Repo `rpm.vectora.company` (fedora + rhel + suse).
- **Flathub** (`flatpak install com.vectora.Vectora`):
  - Manifest `com.vectora.Vectora.yml` em
    `flathub/flathub` PR.
  - Sandboxed por design — usar XDG portal para filesystem
    access do agente.
- **Snap Store** (`snap install vectora`):
  - `snap/snapcraft.yaml`.
  - Confinement `classic` (precisa de aprovação) para acessar
    filesystem fora do home.

### N6 — macOS Homebrew tap

- Tap em `github.com/vectora-company/homebrew-tap`.
- Formula `vectora.rb`:
  ```ruby
  class Vectora < Formula
    desc "Self-hosted AI agent with RAG, MCP, multi-user chat"
    homepage "https://vectora.company"
    url "https://github.com/vectora-company/vectora/releases/download/v1.0.0/vectora-macos-universal.tar.gz"
    sha256 "..."
    def install
      bin.install "vectora"
    end
  end
  ```
- `brew install vectora-company/tap/vectora`.

### N7 — IDE plugins (VS Code, JetBrains, Zed, Neovim)

- **VS Code extension** (`vectora.code`):
  - Sidebar com chat panel (webview apontando para
    `http://localhost:8080/?embed=1`).
  - Inline completions via Language Server (LSP) consumindo
    REST API `/v1/chat/stream`.
  - RAG sobre workspace atual via `/v1/rag/search`.
  - Commands: `Vectora: New Chat`, `Vectora: Explain Selection`,
    `Vectora: Run Slash Command`.
  - Publish em VS Code Marketplace + Open VSX.

- **JetBrains plugin** (IntelliJ Platform):
  - Tool Window com chat (JCEF browser apontando para
    `http://localhost:8080/?embed=1`).
  - Actions: `Vectora: Explain` (Cmd+Shift+E), `Vectora: Refactor`.
  - Compatível com IntelliJ IDEA, PyCharm, WebStorm, GoLand.
  - Publish em JetBrains Marketplace.

- **Zed extension** via ACP (I4 / J7):
  - Manifest `extension.toml` apontando para `vectora` como
    ACP-compatible agent.
  - User configura `acp_url=https://vectora.company.local/v1/acp`
    - `api_key` nas settings do Zed.

- **Neovim** (`vectora.nvim`):
  - Plugin Lua que consome `/v1/chat/stream`.
  - Comandos `:VectoraChat`, `:VectoraExplain`, `:VectoraRefactor`.
  - Floating window para chat; `vim.lsp.*` para inline
    completions.

### N8 — Workflow integrations (n8n, Zapier, Make)

- **n8n custom nodes** (`@vectora/n8n-nodes`):
  - `Vectora Chat` — stream completion.
  - `Vectora RAG Search`.
  - `Vectora Tool` — invoca tool específica.
  - Publish via npm + listed em n8n community nodes.
- **Zapier integration** (oficial via Zapier Platform):
  - Triggers: `New Thread`, `Tool Executed`, `RAG Indexed`.
  - Actions: `Send Message`, `Search RAG`, `Ingest Document`.
- **Make.com (Integromat)**: app similar ao Zapier.

### N9 — Claude Code MCP Registry oficial

- Submeter Vectora MCP server ao `modelcontextprotocol/registry`:
  PR em `github.com/modelcontextprotocol/registry` adicionando
  entry `vectora` com `transport: stdio`, `command: vectora server
mcp`, descrição, ícone, link para docs.
- Tornar Vectora descoberta automática em Claude Desktop via
  `MCP Settings → Browse Registry`.

### Arquivos críticos (Bloco N)

| Sub | Arquivos                                                                                                                     |
| --- | ---------------------------------------------------------------------------------------------------------------------------- |
| N1  | `.github/workflows/runner.yml` (matrix arch)                                                                                 |
| N2  | `.github/workflows/runner.yml` (timestamping, staple, verify)                                                                |
| N3  | `update-server/config.yml` (rollout %), `chat/components/layout/settings-dialog/tabs/preferencias-tab.tsx` (+channel select) |
| N4  | `Dockerfile` (multi-stage), `.github/workflows/docker.yml` (publish + scan)                                                  |
| N5  | `packaging/apt/`, `packaging/dnf/`, `packaging/flatpak/com.vectora.Vectora.yml`, `packaging/snap/snapcraft.yaml`             |
| N6  | `vectora-company/homebrew-tap/Formula/vectora.rb`                                                                            |
| N7  | `ide/vscode/` (novo repo), `ide/jetbrains/` (novo), `ide/zed/`, `ide/neovim/vectora.nvim`                                    |
| N8  | `integrations/n8n-nodes/` (novo repo), `integrations/zapier/`, `integrations/make/`                                          |
| N9  | PR no `modelcontextprotocol/registry`                                                                                        |

### Verificação (Bloco N)

- VM Ubuntu limpa: `apt install vectora` → app funciona.
- macOS limpa: `brew install vectora-company/tap/vectora` → CLI
  funciona. Desktop via .dmg homebrew cask.
- VS Code: install extension → sidebar abre, chat funciona.
- Zed: configurar ACP url → "Ask AI" chama Vectora.
- n8n: workflow consome `Vectora Chat` node → resposta streamada
  na execution log.
- Claude Desktop: Browse Registry → vê Vectora, instala com 1
  clique.

---

## ============================================================================

## ⏳ VECTORA COMPANY: blocos O–S (legal, site, docs, suporte, marketing)

## ============================================================================

> **Escopo dos blocos O–S.** Aqui ficam **apenas** as frentes da empresa
> que não são código de produto: pessoa jurídica, marca, contratos,
> site institucional `vectora.company`, documentação pública
> `docs.vectora.company`, suporte/comunidade, kit de lançamento e
> marketing. Tudo que é **backend/chat/billing/storage** já está nos
> blocos D–N. `docs/company.md` continua sendo a fonte sobre wizards e
> processos de distribuição, mas **não** é o plano do site — quem
> implementa o site é P.

## BLOCO O — Vectora Company: Identidade & Legal

> **Contexto.** Antes de vender qualquer coisa, a empresa precisa de
> identidade clara (nome, marca, domínio), termos legais válidos e uma
> estrutura mínima de pessoa jurídica/MEI para emitir cobranças e
> receber pagamentos. Sem isso, nem Stripe nem Asaas podem ser
> integrados em produção (K).

### O1 — Estrutura jurídica (MEI/ME no CNPJ de Bruno Soares)

- **Decisão**: abrir MEI primeiro; migra para ME se faturamento
  ultrapassar R$81k/ano (teto MEI).
- **CNAE sugerido**:
  - 6201-5/01 — Desenvolvimento de programas de computador sob
    encomenda (principal).
  - 6202-3/00 — Desenvolvimento e licenciamento de programas de
    computador não customizáveis (secundário).
- **Conta bancária PJ**: Nubank PJ, Inter PJ ou C6 PJ — zero
  tarifa, abertura digital, integração Stripe via transferência
  internacional.
- **Ação**: abertura via portal do empreendedor (`gov.br/mei`) ou
  contador online (Contabilizei, Agilize). Documentar passo a
  passo em `company/ops/setup-mei.md` para repetibilidade.
- **Inscrição municipal**: se exigida pela prefeitura local, abrir
  para emissão de NFS-e (nota fiscal eletrônica de serviço).

### O2 — Marca e domínios

**Domínio principal já adquirido**: `vectora.company`.

**Subdomínios planejados**:

- `vectora.company` — site institucional (P).
- `docs.vectora.company` — documentação pública (Q).
- `api.vectora.company` — REST API pública (J) com TLS próprio.
- `status.vectora.company` — status page (M5).
- `updates.vectora.company` — channel server auto-update (N3).

**Domínios adicionais a registrar (defensivo)**:

- `vectora.dev` — alternativo técnico se disponível.
- `vectora.com.br` — defesa de marca BR.
- Variantes typo: `vector-a.company`, `vectorra.company` (registrar
  baratos e redirecionar para o principal).

**Marca**:

- Nome: **Vectora**.
- Identidade visual já consolidada: pássaro Vectora navy + azul
  claro, JetBrains Mono como fonte de marca, paleta `#0a0e1a` /
  `#3b82f6`.
- **Registro INPI** (Instituto Nacional da Propriedade Industrial):
  - Classe 9 (software/produtos digitais).
  - Classe 42 (serviços de tecnologia e SaaS).
  - Custo ~R$1.500 por classe, prazo 8–18 meses para concessão.
  - Recomendado em 6 meses após lançamento (quando houver receita
    para justificar).
- **Logo files** centralizados em `company/brand/`: SVG vetorial,
  PNGs multi-res, dark/light variants, favicon kit, social cards
  templates (Open Graph 1200×630).

### O3 — Termos legais (LGPD + GDPR-ready)

Dois documentos obrigatórios para o site (P) e para o billing (K):

**Política de Privacidade** (`vectora.company/privacy`):

- **Dados coletados**: email, nome, logs de validação de token, dados
  de pagamento (via Stripe/Asaas — não armazenamos cartão), IP no
  audit log, user_agent no audit log.
- **Dados que NÃO coletamos**: conteúdo de conversas, arquivos,
  código, embeddings, prompts ou respostas do agente — self-hosted
  significa que os dados ficam no servidor do cliente.
- **Base legal LGPD** (Lei 13.709/2018):
  - Art. 7º, I — consentimento.
  - Art. 7º, V — execução de contrato.
  - Art. 11 (dados sensíveis): não tratamos dados sensíveis.
- **Retenção**:
  - Conta: enquanto a conta existir + 30 dias após cancelamento.
  - Logs de licença: 90 dias.
  - Dados de pagamento: prazo legal de 5 anos (LC 116, Art. 195).
- **DPO** (Data Protection Officer): Bruno Soares com email
  `dpo@vectora.company` (alias para o principal).
- **GDPR (Regulation EU 2016/679)** para usuários europeus: mesmo
  tratamento + direitos adicionais (portabilidade, esquecimento,
  retificação). Implementação de "request data export" e "delete
  account" no dashboard (P3).
- **Cookies**: somente sessão (`vectora_access`,
  `vectora_refresh`) e preferência de idioma (`vectora_lang`). Sem
  cookies de tracking. Banner de cookies dispensado em jurisdições
  que aceitam consent-by-cookie-essencial.

**Termos de Uso / EULA** (`vectora.company/terms`):

- **Licença**: não exclusiva, não transferível, não sublicenciável.
- **Permitido**: uso comercial dentro da organização do licenciado;
  instalação em múltiplos servidores da mesma empresa dentro do
  mesmo plano (`assinatura cobre o operador, não a máquina`).
- **Não permitido**: redistribuição, sublicenciamento, engenharia
  reversa para fins de concorrência, revenda de acesso.
- **Trial**: 30 dias gratuitos do Plus; sem cartão obrigatório no
  trial (K2 `on-signup`).
- **Cancelamento**: a qualquer momento; acesso mantido até o fim
  do período pago.
- **Limitação de responsabilidade**: software "as is"; Vectora
  Company não se responsabiliza por perdas de dados em ambiente
  self-hosted. Aval do usuário para usar backup automation (M6).
- **Reembolso**: 14 dias após primeira cobrança (não trial), sem
  perguntas, processado em 7 dias úteis.
- **Foro**: comarca de São João Batista do Glória/MG ou eletrônico
  via JFMG.

**Cookies Policy** (`vectora.company/cookies`):

- Lista os 3 cookies essenciais + finalidade.
- Sem opt-in necessário (apenas essenciais).
- Botão "Limpar cookies" funcional.

**SLA Contratual** (`vectora.company/sla`) — opcional, só para
clientes Pro/Enterprise:

- Uptime do serviço de validação de licença: ≥ 99.5% mensal.
- Latência p95 `validate-license`: < 500ms.
- Crédito por falha de SLA: 10% do valor mensal por 0.5% abaixo do
  target.

**Acordo de Processamento de Dados (DPA)**: template para clientes
Enterprise que requerem (modelo EU DPA padrão ICC).

**Nota cardinal**: redigir tudo em linguagem clara, não juridiquês.
Versão "tldr" no topo de cada documento. Submeter para revisão de
um advogado especializado em SaaS antes do lançamento (custo
estimado R$2.000–R$5.000).

### O4 — Email, comunicação corporativa e GitHub Organization

**Provedor de email**: Google Workspace (Business Starter ~R$30/
mês por caixa).

**Endereços operacionais**:

- `bruno@vectora.company` — principal pessoal.
- `support@vectora.company` — suporte (alias para R2).
- `billing@vectora.company` — Stripe/Asaas enviam notificações
  fiscais aqui.
- `security@vectora.company` — para CVE reports / responsible
  disclosure.
- `dpo@vectora.company` — alias DPO (LGPD/GDPR).
- `press@vectora.company` — alias para imprensa (S5).
- `legal@vectora.company` — alias para questões contratuais.
- `noreply@vectora.company` — outbound transacional (signup,
  reset, invoices).

**Outbound transacional** via Resend ou Postmark
(`api.vectora.company/emails/*`):

- Templates React Email em `vectora-company/emails/`: welcome,
  trial-ending, invoice-paid, invoice-failed, payment-overdue,
  password-reset, magic-link, invite-pending.
- DKIM/SPF/DMARC configurados em `vectora.company` para evitar
  spam.

**WhatsApp Business**:

- Número Brasil dedicado (pode ser pessoal de Bruno com perfil
  Business).
- Auto-resposta fora do horário (`seg–sex 9h–18h BRT`) com link
  para FAQ e formulário de issues.
- Link `wa.me/55...` em todo o site/footer/docs.

**GitHub Organization** `vectora-company`:

- Repos públicos: `docs` (Q), `examples` (samples de SDK uso),
  `issues` (issues público), `homebrew-tap` (N6), `setup-action`
  (L4), `chat-action` (L4), `mcp-server-vectora` (N9), `oauth-clients`
  (samples L1/L2).
- Repos privados: `vectora` (código principal),
  `vectora-releases` (binários assinados D3),
  `vectora-company/site` (P), `vectora-company/supabase` (K1/K2),
  `vectora-company/update-server` (D4/N3),
  `vectora-company/brand` (assets oficiais),
  `vectora-company/ops` (runbooks, playbooks DR M7,
  setup-mei.md, etc).
- 2FA obrigatório em todos os membros.
- Branch protection em `main` (1 review + status checks verdes).
- Dependabot ativo nos repos públicos.
- Security advisories ativos.

### Verificação (Bloco O)

- MEI/ME aberto com CNPJ ativo; emite NFS-e via prefeitura.
- Conta bancária PJ operacional, recebe transferências.
- `vectora.company` apontando para Vercel (P); subdomínios
  resolvendo (`docs`, `api`, `status`, `updates`).
- Emails `@vectora.company` enviando/recebendo; SPF/DKIM/DMARC
  com status `pass` no `mxtoolbox`.
- Termos, Privacy, Cookies, SLA, DPA redigidos, revisados por
  advogado e publicados.
- GitHub Org criada; repos públicos com README/LICENSE; repos
  privados com branch protection.
- WhatsApp Business com perfil completo + auto-resposta
  configurada.

---

## BLOCO P — Vectora Company: Site `vectora.company`

> **Stack:** Next.js 16 + Tailwind + shadcn/ui + Supabase Auth SSR
>
> - Stripe/Asaas (K). Deploy: Vercel (integração Supabase nativa).
>   Repo separado: `vectora-company/site`.

### P1 — Landing Page (`/`)

Scroll único, seções âncora, mobile-first.

**Hero**:

- Tagline: _"Your AI. Your Data. Your Server."_
- Subtítulo (≤15 palavras): "Self-hosted AI agent com RAG, MCP e
  chat web multi-usuário. Seus dados nunca saem do seu servidor."
- CTAs: "Começar trial grátis — 30 dias" (→ `/signup`) + "Ver
  demo" (âncora `#demo`).
- **Vídeo 1 em loop, sem voz** (mp4 + webm, autoplay muted): chat
  em uso (workspace aberto, agente respondendo, sidebar com
  threads). 720p, ≤2MB com `oxc-minify`-style compression. Loop
  ~30s.

**O que é o Vectora** (texto + vídeos intercalados):
Prosa fluida para devs solo + times tech. 4 vídeos sem voz:

1. Uso do chat (RAG respondendo sobre o projeto).
2. Instalação em VPS (30–60s, `pip install vectora` + `vectora
setup`).
3. Workspace + indexação de docs.
4. Acesso multi-usuário via chat web.

**O que é RAG** (diagrama animado SVG):
Ciclo de vida visual: `Documento → Embedding → Vector Store →
Query → Vector Search → Reranker → LLM → Resposta`. Animação CSS
com `prefers-reduced-motion` respeitado.

**Diagramas de arquitetura** (3 SVGs interativos):

- **Diagrama 1**: Três modos de uso — CLI, MCP (sub-agente), Chat
  Web.
- **Diagrama 2**: Agentes especializados (Orchestrator → RAG /
  Search / Coder).
- **Diagrama 3**: Empresa com Vectora em VPS, time acessando via
  chat, cada dev com workspace e API key própria.

**Pricing** (`#pricing`):

| Feature                     | Plus              | Pro                  |
| --------------------------- | ----------------- | -------------------- |
| Trial gratuito              | 30 dias           | —                    |
| CLI + MCP                   | ✓                 | ✓                    |
| Vectora Chat (web)          | —                 | ✓                    |
| SQLite + LanceDB            | ✓                 | ✓                    |
| PostgreSQL + Qdrant + Redis | —                 | ✓                    |
| Multi-thread (acesso web)   | —                 | ✓                    |
| Webhooks (L3)               | —                 | ✓                    |
| REST API `/v1` (J)          | ✓ (limite 60/min) | ✓ (limite 600/min)   |
| SDKs Python/TS (L1/L2)      | ✓                 | ✓                    |
| ACP server (I4/J7)          | —                 | ✓                    |
| Suporte                     | Email 48h         | Email 24h + WhatsApp |
| **BR**                      | R$20/mês          | R$55/mês             |
| **INTL**                    | $7/mês            | $20/mês              |
|                             | [Começar trial]   | [Assinar Pro]        |

**Comparação visual** "Por que self-hosted?" com 4 cards: Privacidade
(seus dados ficam no seu servidor) · Custo (sem markup de API) ·
Customização (escolha seu LLM) · Soberania (sem vendor lock-in).

**Social proof** (pré-lançamento): "Seja um dos primeiros — trial
grátis, sem cartão." Pós-lançamento: depoimentos reais dos beta
testers (R5).

**Footer**:

- Links: Docs · FAQ · Suporte · Issues · API · Status · Changelog.
- Legal: Privacy · Terms · Cookies · SLA · DPA.
- Social: GitHub · X · LinkedIn · WhatsApp · YouTube.
- "Made with ❤ in Brazil" + CNPJ no rodapé.

### P2 — Auth (`/signup`, `/login`)

**`/signup`**:

- Campos: nome, email, senha, country select (BR/INTL — routing
  K5).
- Supabase Auth → trigger `on-signup` (K2) cria token + trial
  automaticamente.
- Após signup: redirect para `/dashboard?welcome=true`.
- Captcha hCaptcha invisible para anti-spam.

**`/login`**:

- Email + senha.
- "Esqueci a senha" → Supabase Magic Link por email (template em
  `vectora-company/emails/magic-link.tsx`).
- Sem OAuth no MVP (Google pode entrar depois).
- Botão "Voltar ao site" no header.

### P3 — Dashboard (`/dashboard`)

**Sidebar** (esquerda): Token, Licença, Pagamento, API Keys,
Conta, Suporte.

**Seção Token** (rota default):

- "Seu VECTORA_TOKEN":
  ```
  [ Clique para revelar seu token — exibido uma única vez ]
                                              [Rotacionar token]
  ⚠ Copie e guarde. Após fechar, não poderá ser exibido novamente.
     Se perder, use "Rotacionar token".
  ```
- Após reveal: token em fonte mono com botão de cópia. Fecha →
  banner amarelo permanente "Token já revelado — rotacione se
  perder".

**Seção Status da Licença**:

```
Plano: Plus — Trial
──────────────────────────────────────────────
Início:            01/06/2026
Término do trial:  01/07/2026
Dias restantes:    30 dias
Status:            ⏳ Trial ativo

[Assinar Plus — R$20/mês]   [Fazer upgrade para Pro — R$55/mês]
```

Para assinantes ativos:

```
Plano: Pro — Ativo
Próxima cobrança: 01/07/2026 (R$55,00)
Próximo método: Cartão final 4242
[Gerenciar assinatura]   [Cancelar]   [Atualizar método]
```

**Seção Pagamento** (BR via Asaas embed; INTL redirect Stripe Portal):

- BR: form de cartão tokenizado via Asaas SDK (PCI DSS compliant)
  ou seleção PIX/Boleto na próxima cobrança.
- INTL: botão "Gerenciar assinatura" → `shell.openExternal` para
  Stripe Customer Portal (no desktop) ou `window.open` (no site).

**Seção API Keys** (consome `/v1/oauth/clients` J1):

- Lista de OAuth clients (nome, criado em, scopes, último uso).
- Botão "Criar API key" → modal nome + scopes + show secret once.
- Revogar inline.

**Seção Histórico de Validações** (últimas 20 do `license_checks`
K1):

```
01/06/2026 14:32 — ✓ válido (Plus, trial) — Vectora v0.5.0 — IP 200.x.x.x
01/06/2026 08:15 — ✓ válido (Plus, trial) — Vectora v0.5.0 — IP 200.x.x.x
```

**Seção Conta**:

- Editar nome, country, idioma preferido.
- Alterar senha (envia magic link de confirmação).
- "Exportar meus dados" (GDPR Art. 20) → ZIP com profile + tokens
  - subscriptions + license_checks em JSON.
- "Deletar conta" (GDPR Art. 17) → confirmação por email + soft
  delete 30 dias + hard delete + cancela subscription.

**Guia de início rápido** (apenas em `?welcome=true`):

```
1. Revele e copie seu VECTORA_TOKEN acima
2. pip install vectora      (ou baixe o instalador nativo)
3. vectora setup            (cole o token quando solicitado)
4. vectora chat             (começar a usar)
```

### P4 — Pricing dedicado (`/pricing`)

Página completa com tabela comparativa expandida (todas features
de A–N visíveis), FAQ inline de preços (8 perguntas comuns),
calculadora simples ("quantos devs? → preço total estimado"),
CTAs duplos por plano.

Toggle BR/INTL no topo muda a coluna de preço (default detectado
por geo IP).

### P5 — FAQ (`/faq`)

Categorias com accordion:

- **Geral**: o que é, o que significa self-hosted, meus dados
  ficam onde, qual a diferença para ChatGPT/Claude, posso usar
  meus próprios LLMs.
- **Instalação**: requisitos mínimos, Windows/macOS/Linux, VPS vs
  local, Docker, qual cloud usar.
- **Licença & Billing**: trial, como funciona expiração,
  cancelamento, meios de pagamento (cartão BR/INTL, PIX, boleto),
  desconto early adopter, reembolso, NF-e.
- **Técnico**: o que é RAG, diferença Plus/Pro, API keys próprias
  vs Vectora, VECTORA_TOKEN como funciona, MCP integration, ACP.
- **Comercial**: posso usar na empresa, quantos devs por
  assinatura, contrato Enterprise, posso reseller.

Cada resposta com link "Saiba mais" para docs (Q) ou guia
específico.

### P6 — Issues & Suporte (`/issues`, `/support`)

**`/issues`**: formulário (título, descrição, categoria
bug/feature/docs/billing) → submete via GitHub Issues API para
`vectora-company/issues` (repo público) ou Linear/Crisp (privado
para billing).

**`/support`**: 4 canais:

- WhatsApp (link direto).
- Email `support@vectora.company` (formulário inline).
- GitHub Issues (link `/issues`).
- Status page (link `status.vectora.company`).

### P7 — Páginas legais (`/privacy`, `/terms`, `/cookies`, `/sla`, `/dpa`)

Conteúdo conforme O3. Linguagem clara, "tldr" no topo, versionado
(footer mostra "Versão 1.0 — 01/06/2026"; mudanças notificadas
por email aos usuários com diff link).

### P8 — i18n + SEO + Performance

**i18n**: `pt-BR` (default) e `en`. `next-intl` ou Paraglide.
Vídeos sem voz — sem necessidade de versionar por idioma. Diagramas
SVG em inglês (linguagem técnica universal).

**SEO**:

- Open Graph completos por página (titles, descrições, OG image
  1200×630 gerada via `@vercel/og`).
- Twitter Cards summary_large_image.
- `sitemap.xml` + `robots.txt`.
- Schema.org JSON-LD: `SoftwareApplication`, `Organization`,
  `FAQPage` (para `/faq`), `Product` (para `/pricing`).
- Canonical tags + hreflang `pt-BR` ↔ `en`.

**Performance**:

- Lighthouse score ≥ 95 em Performance/Accessibility/Best
  Practices/SEO.
- Imagens via `next/image` AVIF/WebP.
- Vídeos `preload="metadata"` (não autoplay no mobile).
- Font subset (JetBrains Mono Latin + Aeonik se usado).

**Analytics**:

- Plausible self-hosted (sem cookies, GDPR-compliant) em
  `analytics.vectora.company`.
- Events trackeados: signup, trial_started, paid_conversion,
  cancel, video_played, pricing_viewed.

### Estrutura de arquivos (Bloco P)

```
vectora-company/site/
├── app/[locale]/
│   ├── page.tsx               (landing — P1)
│   ├── pricing/page.tsx       (P4)
│   ├── faq/page.tsx           (P5)
│   ├── issues/page.tsx        (P6)
│   ├── support/page.tsx       (P6)
│   ├── privacy/page.tsx       (P7)
│   ├── terms/page.tsx         (P7)
│   ├── cookies/page.tsx       (P7)
│   ├── sla/page.tsx           (P7)
│   ├── dpa/page.tsx           (P7)
│   ├── login/page.tsx         (P2)
│   ├── signup/page.tsx        (P2)
│   └── dashboard/
│       ├── page.tsx           (P3 — Token default)
│       ├── billing/page.tsx
│       ├── api-keys/page.tsx
│       └── account/page.tsx
├── components/
│   ├── landing/
│   │   ├── hero.tsx
│   │   ├── video-section.tsx
│   │   ├── rag-diagram.tsx    (SVG animado)
│   │   ├── arch-diagrams.tsx
│   │   └── pricing-table.tsx
│   ├── dashboard/
│   │   ├── token-reveal.tsx
│   │   ├── license-status.tsx
│   │   ├── license-history.tsx
│   │   ├── api-keys-list.tsx
│   │   └── quick-start.tsx
│   └── shared/footer.tsx, header.tsx, ...
├── lib/
│   ├── supabase/{client,server}.ts
│   ├── stripe/client.ts
│   └── asaas/client.ts
├── messages/{pt-BR,en}.json
└── emails/                    (React Email templates O4)
```

### Verificação (Bloco P)

- Landing carrega com vídeo 1 em loop, sem som. Lighthouse ≥ 95.
- Signup BR → dashboard com token + status trial + opções de
  pagamento Asaas (PIX/Boleto/Cartão).
- Signup INTL → dashboard com Stripe Checkout em USD.
- Token reveal: aparece uma vez; segunda → "já revelado".
- Rotacionar token → novo gerado e exibido uma vez.
- Assinar Plus BR via PIX → webhook `PAYMENT_RECEIVED` → status
  "ativo" sem refresh manual.
- Upgrade Plus→Pro → tier atualizado, crédito proporcional.
- Cancelar via portal → status "canceled", acesso até fim do
  período.
- FAQ, Issues, Support, Legal acessíveis sem auth.
- Trocar locale PT-BR ↔ EN → interface traduzida, URL muda
  (`/pt-BR` ↔ `/en`).
- Exportar dados GDPR → ZIP baixado com JSON completo.
- Deletar conta → confirmação por email + soft delete + hard
  delete em 30d.

---

## BLOCO Q — Vectora Company: Documentação `docs.vectora.company`

> **Stack:** Docusaurus 3 (recomendado) ou Mintlify. Subdomínio
> `docs.vectora.company`. Repo público: `vectora-company/docs`.
> Contribuições da comunidade via PR.

### Q1 — Setup + tema + i18n

- **Docusaurus 3** com `@docusaurus/theme-classic` + customização
  visual alinhada ao site P (paleta navy + azul claro, JetBrains
  Mono).
- **i18n**: `pt-BR` (default) e `en`. Cada página em
  `i18n/en/docusaurus-plugin-content-docs/current/`.
- **Algolia DocSearch** (free para open source docs) — busca
  full-text com facets por seção.
- **Theme switcher** dark/light.
- **Sidebar navegável** com auto-collapse + breadcrumbs no topo.
- **Versionamento de docs** por release major (`/v1.x/...`).

### Q2 — Getting Started

```
docs.vectora.company/getting-started/
├── introduction          (o que é, para quem, diferenças)
├── installation          (pip install + requisitos + native installer)
├── quick-start           (vectora setup + vectora chat em 5 min)
├── vectora-token         (o que é, como obter, configurar)
├── first-workspace       (criar, indexar docs, primeira query)
└── upgrade-from-cli      (devs que já usam CLI Plus migram p/ Pro)
```

Cada página: intro de 1 parágrafo, pré-requisitos, passos
numerados, resultado esperado, troubleshooting.

### Q3 — Guides

```
guides/
├── vps-deploy            (DigitalOcean, Hetzner, Contabo — step by step)
├── team-setup            (multi-user, invites, RBAC)
├── rag-guide             (embedding, indexação, boas práticas)
├── mcp-integration       (usar Vectora como sub-agente via MCP)
├── git-workflows         (workspaces git, worktrees, PRs via agente)
├── api-keys              (configurar OpenAI, Anthropic, Gemini, Cohere)
├── webhooks              (registrar, signing, dedup) [L3]
├── sdk-python            (uso do vectora-sdk Python) [L1]
├── sdk-typescript        (uso do @vectora/sdk) [L2]
├── ide-integration       (VS Code, JetBrains, Zed, Neovim) [N7]
├── github-actions        (setup-action, chat-action) [L4]
├── n8n-workflows         (nós oficiais) [N8]
└── data-migration        (de outros agents/assistants para Vectora)
```

### Q4 — Reference

```
reference/
├── cli                   (todos os subcomandos com flags + exemplos)
├── config                (config.toml — todas as opções)
├── tools                 (todas as 20+ tools do agente com schema)
├── agents                (Orchestrator, RAG, Search, Coder, Deep Agents)
├── rest-api              (endpoints /v1/* completos)
├── mcp-server            (tools + resources expostos)
├── acp-server            (ACP endpoints, manifest) [I4/J7]
└── storage-backends      (SQLite, Postgres, LanceDB, Qdrant, pgvector)
```

REST API reference auto-gerada a partir do OpenAPI 3.1 (L5) via
`redocly` ou `swagger-ui-react` embarcado.

### Q5 — Self-hosting

```
self-hosting/
├── requirements          (hardware mínimo + recomendado por tier)
├── docker                (docker-compose.yml pronto, lite + complete)
├── kubernetes            (Helm chart + manifests YAML)
├── nginx-traefik         (reverse proxy com TLS, WebSocket forward)
├── storage-backends      (escolher SQLite vs Postgres, LanceDB vs Qdrant)
├── monitoring            (OpenTelemetry collectors, Grafana dashboards) [M1]
├── backup-restore        (vectora backup CLI, schedule, DR) [M6/M7]
└── updates               (auto-update no desktop vs manual no server)
```

### Q6 — Changelog público + RSS

Página `/changelog` com:

- Versão e data.
- Novidades (features) com link para docs/guides relacionados.
- Correções (bugfixes).
- Mudanças que quebram compatibilidade (breaking changes) em
  destaque com `migration guide` link.
- RSS feed `docs.vectora.company/changelog/rss.xml` para
  ferramentas como Feedly.
- Webhook (L3) `release.published` para integradores.

### Q7 — Padrões de qualidade + contribuição

**Padrões**:

- Toda página tem: intro 1 parágrafo, pré-requisitos, passos
  numerados, resultado esperado, troubleshooting.
- Exemplos de código com output esperado — não só o comando.
- Screenshots ou GIFs para UI do chat (gerados via Playwright
  scripts em `docs/scripts/screenshots/`).
- Linguagem: PT-BR como primário, EN como tradução.
- Cada bloco do produto implementado → página de referência
  correspondente.

**Contribuição** (`CONTRIBUTING.md`):

- Issues para erros e sugestões de docs (label `docs`).
- PRs bem-vindos para correções e traduções.
- Style guide curto (uso de "você" em PT-BR, "you" em EN, voz
  ativa).
- Bot DCO (Developer Certificate of Origin) para PRs externos.

### Verificação (Bloco Q)

- `docs.vectora.company` resolve corretamente; HTTPS verde.
- Algolia DocSearch funciona; busca por "rag" retorna resultados
  relevantes em ≤300ms.
- Quick-start funciona do zero: usuário novo consegue instalar e
  rodar em 10 min seguindo a doc.
- Todos os comandos CLI documentados com exemplos testados (CI
  roda os exemplos como smoke tests).
- Docker Compose da doc funciona em Ubuntu 24.04 limpo.
- Trocar idioma PT-BR ↔ EN preserva a página atual.
- Changelog RSS válido (passa W3C feed validator).

---

## BLOCO R — Vectora Company: Suporte & Comunidade

### R1 — WhatsApp Business

- Link direto no site, na doc e no chat (Settings → Suporte).
- Horário de atendimento explícito (seg–sex 9h–18h BRT).
- Auto-resposta fora do horário com link para FAQ e issues.
- Templates de mensagem aprovados para outbound (notificação de
  expiração, oferta de upgrade) — opt-in pelo user no dashboard.

### R2 — Email `support@vectora.company`

- Para questões de billing, técnicas e legais.
- SLA: resposta em até 48h úteis (Plus) ou 24h úteis (Pro).
- Integração com ferramenta de ticketing — recomendação: Crisp
  (PT-BR friendly, plan free generoso) ou Freshdesk.
- Templates de resposta para questões comuns (8 templates
  iniciais: trial estendido, refund, license issue, install
  trouble, billing dispute, GDPR request, feature request,
  bug report).
- Macros para resposta rápida com link para docs/guia
  específico.

### R3 — GitHub Issues público

Repositório `vectora-company/issues` (separado do código privado):

- Templates: bug report, feature request, docs improvement.
- Labels: `bug`, `enhancement`, `question`, `docs`, `billing`,
  `good first issue`.
- Triagem semanal por Bruno (rotina recorrente em R7).
- Issue templates puxam form do `.github/ISSUE_TEMPLATE/`.
- Auto-assign para Bruno; auto-label baseado em palavras-chave
  via GitHub Actions.

### R4 — Comunidade (Discord OU GitHub Discussions)

**Decisão MVP**: começar com GitHub Discussions (zero manutenção,
público, pesquisável por SEO). Avaliar Discord pós-lançamento se
volume justificar.

**GitHub Discussions** em `vectora-company/issues/discussions`:

- Categorias: `📣 Announcements`, `💡 Ideas`, `🙋 Q&A`,
  `🎉 Show and tell`, `🐛 Help`.
- Pinned posts: welcome, link para docs, código de conduta.
- Bruno responde Q&A 2x/semana.

**Discord** (pós-lançamento, se atingir 500+ usuários):

- Servidor com canais: `#announcements`, `#general`, `#support`,
  `#show-and-tell`, `#feature-requests`, `#pt-br`, `#en`.
- Bot de boas-vindas (`Vectora Bot`) com link para docs e
  quick-start.
- Webhooks (L3) para postar releases e status em `#announcements`.

### R5 — Programa de beta testers

Antes da campanha de influenciadores (S):

- Recrutar 10–20 beta testers via:
  - Comunidades de dev BR: Discord LangChain BR, grupos Telegram
    Python BR, Slack MLOPS BR, Discord Computaria.
  - Twitter/LinkedIn de Bruno.
  - DM para devs que comentam em posts técnicos relacionados.
- **Acesso Pro gratuito por 6 meses** em troca de feedback
  estruturado.
- **Form de feedback** mensal: NPS, top 3 pontos positivos, top 3
  problemas, "se você fosse pago para promover, o que diria?".
- **Calls 1:1** opcionais com Bruno para casos de uso reais.
- **Depoimentos** públicos coletados (com consent) para o site
  (P1) e kit de imprensa (S5).
- **Hall of Fame** no site: "Primeiros 20 betas — obrigado!" com
  avatar/nome/empresa.

### R6 — Status page (`status.vectora.company`)

- **Tooling**: BetterStack Uptime (free tier suficiente para MVP)
  ou Upptime (self-hosted via GitHub Actions, zero custo).
- **Componentes monitorados**:
  - API REST (`api.vectora.company/v1/health/ready`).
  - Chat SSE (`api.vectora.company/v1/health/live`).
  - Validate License Supabase (`supabase.co/functions/v1/validate-license`).
  - Site (`vectora.company`).
  - Docs (`docs.vectora.company`).
  - Update server (`updates.vectora.company`).
- **Check interval**: 60s.
- **Incidentes manuais**: Bruno pode declarar incident e postar
  updates.
- **Histórico** público (90 dias).
- **Subscribe**: email, RSS, webhook (L3).

### R7 — Knowledge base interna + rotinas

`vectora-company/ops/` (repo privado):

- `runbooks/`: procedimentos para incidentes (DB down, Stripe
  webhook lag, license server hiccup, support ticket overload).
- `macros/`: templates de resposta R2 versionados.
- `weekly-checklist.md`: triagem GitHub Issues, revisão
  WhatsApp, NPS dos betas, status page audit, métricas K6
  reconciliation.
- `monthly-review.md`: MRR, churn, NPS, top requested features,
  decisões de roadmap.

### Verificação (Bloco R)

- WhatsApp Business com perfil completo + auto-resposta + 5
  templates aprovados.
- Email `support@` funcionando, Crisp/Freshdesk configurado, 8
  templates de resposta prontos.
- GitHub Issues público com 3 templates + labels + GH Action de
  auto-assign rodando.
- GitHub Discussions configurada com 5 categorias + welcome post
  pinned.
- 10+ beta testers recrutados, com feedback inicial coletado
  antes de S.
- Status page no ar com 6 componentes monitorados; primeiro
  incidente teste documentado.
- Runbook de "DB down" testado em staging (RTO atingido).

---

## BLOCO S — Vectora Company: Marketing & Lançamento

> **Pré-requisito**: blocos O–R prontos + produto estável (D–N
> entregues + smoke tests passando) + 10+ beta testers com
> depoimentos.

### S1 — Releases oficiais (PyPI 1.0 + Docker Hub + GHCR)

**PyPI** (`vectora-cli` mirror D7):

- Versão `1.0.0` com changelog completo (Q6).
- `README.md` PyPI atualizado: descrição, quickstart, link para
  docs, badges (versão, licença, Python).
- Classifiers corretos:
  - `License :: Other/Proprietary License`.
  - `Topic :: Scientific/Engineering :: Artificial Intelligence`.
  - `Topic :: Software Development :: Libraries :: Python Modules`.
  - `Programming Language :: Python :: 3.13`.

**Docker Hub** + **GHCR** (`vectora/vectora:1.0.0`,
`vectora/vectora:latest`, `vectora/vectora:pro`):

- Multi-arch (amd64 + arm64).
- Image scanning Trivy verde.
- `README.md` no Docker Hub com docker-compose exemplo.

**GitHub Releases** (privado, T.12.3 / D3):

- Release `v1.0.0` com:
  - Binários nativos assinados (Win .msi + .exe NSIS, macOS .dmg
    universal, Linux .AppImage + .deb + .rpm).
  - Checksums SHA-512.
  - Release notes em PT-BR + EN com migration guide se aplicável.
- Auto-update channel `latest` publica para clientes existentes
  (D4).

### S2 — Kit para influenciadores e canais

Um kit por destinatário, enviado com **1–2 semanas de antecedência**:

**Conteúdo do kit (PDF + assets ZIP)**:

- **Licença Pro gratuita por 6 meses** (VECTORA_TOKEN dedicado).
- **Guia de instalação de 1 página** (PDF): do zero ao chat em 5
  min, screenshot por passo.
- **3–5 sugestões de demo** prontas para vídeo/stream:
  1. _"Instalei o Vectora na minha VPS e indexei meu repositório
     em 10 minutos"_.
  2. _"Pedi pro Vectora revisar minha PR e ele fez code review
     completo com sugestões inline"_.
  3. _"Minha equipe usa o Vectora como assistente interno — sem
     enviar uma linha de código para terceiros"_.
  4. _"Deixei o Vectora acessar meu código legado e ele me
     explicou tudo, gerou tests e refatorou"_.
  5. _"Conectei o Vectora ao Claude Code via MCP e agora tenho 2
     agentes trabalhando juntos"_.
- **Pasta de assets** (ZIP): logo (SVG + PNG), screenshots do chat
  (1920×1080 PNG), diagrama de arquitetura, banner para thumbnail
  YouTube (1280×720), GIF curto do chat em uso.
- **Contato direto do Bruno (WhatsApp)** para suporte durante
  produção do conteúdo.
- **Pixel de tracking** opt-in para medir conversões (cupom
  específico do canal: `CANAL2025` rastreado no Stripe/Asaas).

**Lista de canais brasileiros (Fase 1, lançamento BR)**:

- TecMundo
- Loop Infinito
- Código Fonte TV
- Lucas Montano
- Mano Deyvin
- Filipe Deschamps
- Augusto Galego (Dev Eficiente)
- Computaria
- Programador BR
- Outros conforme afinidade.

**Lista de canais internacionais (Fase 2, pós-lançamento BR)**:

- Fireship
- AI Jason
- David Ondrej
- Theo - t3.gg
- Comunidades Reddit: r/selfhosted, r/LocalLLaMA, r/Python,
  r/SaaS.
- Hacker News.

### S3 — Posts de lançamento (redes próprias)

**LinkedIn** (perfil Bruno):

- **Post 1** (T-14): contexto e por que RAG self-hosted importa.
- **Post 2** (T-7): introdução ao Vectora com arquitetura.
- **Post 3** (T-0): lançamento oficial com link + vídeo trailer.
- **Posts diários** (T+1 a T+7): screenshots, casos de uso, citação
  de depoimentos.

**Reddit** (no dia do lançamento):

- `r/selfhosted`: _"I built a self-hosted AI agent with RAG, MCP
  server and multi-user web chat — and it's now available"_.
- `r/LocalLLaMA`: foco no RAG híbrido (BM25 + dense + reranker) e
  Deep Agents.
- `r/Python`: foco na arquitetura técnica (FastAPI + LangGraph +
  Cohere + LanceDB).
- `r/SaaS`: foco no modelo de negócio (self-hosted + license token).

**X / Twitter** (perfil Bruno):

- Thread de lançamento com GIF do chat em uso + 8 tweets sobre
  features.

**Hacker News**:

- _"Show HN: Vectora — self-hosted AI agent with hybrid RAG, MCP
  server and multi-user web chat"_.
- Postar terça/quarta 9h ET (horário de melhor tração HN).

**Indie Hackers**:

- Post detalhado: jornada de construção, números (LOC,
  contributors, tempo), arquitetura.

### S4 — Canal próprio Vectora (YouTube + LinkedIn Video)

Editor de vídeo contratado (~R$2k para o pacote inicial):

1. **Trailer oficial** (60–90s): produto em uso, sem narração
   técnica, música licenciada, visual limpo — serve também como
   hero do site P1.
2. **Tutorial completo** (15–20 min): instalação + configuração +
   primeiro uso + casos de uso básicos.
3. **Demo de caso de uso** (5–10 min por caso): equipe usando o
   chat, code review via agente, RAG sobre documentação técnica
   real.
4. **Behind the scenes** (5 min): história da construção, decisões
   arquiteturais — para criar conexão pessoal.

Publicação simultânea em YouTube + LinkedIn Video + corte vertical
para Shorts/Reels/TikTok.

### S5 — Cronograma de lançamento

```
T-30 dias: R5 — recrutar beta testers (10+ confirmados).
T-21 dias: S2 — enviar kits para influenciadores BR.
T-14 dias: S4 — trailer e tutorial finalizados; S3 post LinkedIn 1.
T-10 dias: P operacional (site no ar); Q operacional (docs no ar).
T-7  dias: S3 LinkedIn post 2; R6 status page com 1 semana de
            uptime histórico.
T-3  dias: smoke tests finais; rotação de equipe para call de guerra.
T-0  dia : 🚀 Lançamento oficial:
            06h BRT — posts LinkedIn 3 + Reddit + HN + Twitter publicados.
            09h BRT — email para mailing list (betas + waitlist).
            12h BRT — trailer no YouTube.
            14h BRT — WhatsApp blast para network próximo.
            Durante o dia — influenciadores publicam (semana do lançamento).
T+1–7   : análise de métricas (S6), resposta a comentários,
            suporte ativo, ajustes hot-fix se necessário.
T+14    : Fase 2 — canais internacionais (Reddit EN, HN repost se
            primeira foi fraca, X intl).
T+30    : retro do lançamento; ajustes de produto e marketing.
```

### S6 — Métricas de sucesso

**Meta conservadora (semana 1)**:

- 500+ instalações (`pip install` no PyPI + downloads de
  instaladores).
- 100+ contas criadas no Supabase.
- 50+ usuários em trial ativo.
- 10+ assinantes pagantes.

**Meta otimista (semana 1)**:

- 2.000+ instalações.
- 500+ contas criadas.
- 200+ trials ativos.
- 50+ assinantes pagantes.

**Indicadores de qualidade**:

- Conversão trial → pago (meta: ≥ 5%).
- Churn nos primeiros 30 dias (meta: ≤ 20%).
- NPS informal via WhatsApp/email nos primeiros betas (meta: ≥ 50).
- Star count no GitHub Issues (proxy de community interest).
- Tráfego orgânico no site (meta: ≥ 5k visits/semana após T+30).

**Dashboard de métricas** (Bruno):

- Plausible Analytics (P8) — tráfego.
- Supabase Dashboard — signups, conversões.
- Stripe/Asaas Dashboards — receita, MRR.
- BetterStack Status Page — uptime.
- Sentry (M2) — error rate.

### S7 — Conteúdo pós-lançamento (semanas 2–8)

Manter tração orgânica após semana de lançamento:

**Série "Casos de uso do Vectora"** (LinkedIn + YouTube + Blog
P optional `/blog`):

- 1 post/vídeo por semana nos primeiros 2 meses.
- Temas:
  1. RAG sobre codebase legado.
  2. Code review automatizado.
  3. Equipe de 3 devs usando como assistente compartilhado.
  4. Vectora + MCP no Claude Code (combo).
  5. Vectora + n8n para automação.
  6. Self-hosting em VPS R$30/mês.
  7. Integração com VS Code via extension N7.
  8. ACP — Vectora como sub-agente em Zed.

**Engajamento em comunidades**:

- Responder issues GitHub em até 24h nos primeiros 30 dias.
- Comentários técnicos nos posts dos influenciadores.
- Post semanal no `r/selfhosted` sobre uso real.

### S8 — Cupons early adopter

Para incentivar conversão rápida:

- **Early adopter Plus**: `VECTORA25` — 25% off (R$15/mês BR ou
  $5/mês INTL) para os primeiros 100 assinantes,
  `duration: "forever"`.
- **Early adopter Pro**: `PROEARLY` — ~18% off (R$45/mês BR ou
  $16/mês INTL) para os primeiros 50 assinantes,
  `duration: "forever"`.
- Cupons criados manualmente no Stripe e Asaas com
  `max_redemptions: 100` / `50`. Lifetime price preserved enquanto
  assinatura ativa (anti-churn incentive).
- Cupons rastreados por canal (S2): kit para Lucas Montano com
  `MONTANO25`, etc.

### S9 — Roadmap público (`/roadmap`)

Página no site (P) com roadmap em linguagem de usuário:

```
✓ Lançado
  → CLI + MCP (Plus)
  → Chat web multi-usuário (Pro)
  → RAG híbrido com reranking
  → HITL, workspaces, git integration
  → Skills + plugins MCP + workspaces remotos
  → REST API v1 + SDKs Python/TS
  → Instaladores nativos Win/macOS/Linux

🚧 Em desenvolvimento
  → Deep Agents 2.0 (paralelismo real)
  → Mais conectores (Notion, Linear, Google Drive)
  → Marketplace de skills
  → Mobile apps (iOS + Android)

📍 Planejado
  → ACP Protocol completo (integração Zed, JetBrains, VS Code)
  → Workflow visual builder
  → Voice mode (input + output)
  → Multi-modal expandido (vídeo, áudio)
```

Updates via blog post + email mensal a usuários ativos. Voting na
seção "Planejado" via emoji reactions (GitHub Discussions ou
Canny.io). Sem datas firmes — apenas ordem aproximada.

### Verificação (Bloco S)

- PyPI `vectora-cli 1.0.0` publicado; `pip install` em VM limpa
  funciona.
- Docker `vectora/vectora:1.0.0` testado em Ubuntu 24.04 + macOS
  Docker Desktop.
- GitHub Release `v1.0.0` privado com 6 binários assinados
  - checksums + release notes bilíngue.
- Kit enviado para todos os canais da lista BR com ≥2 semanas de
  antecedência; pelo menos 5 confirmaram interesse em publicar.
- Posts LinkedIn, Reddit, HN, Twitter agendados/publicados
  conforme cronograma S5.
- Trailer finalizado e aprovado; publicado no YouTube com
  thumbnail customizado.
- Meta conservadora atingida na semana 1 (10 assinantes pagantes
  confirmados em Stripe + Asaas combinados).
- Conteúdo pós-lançamento S7 agendado para 8 semanas (calendário
  editorial em `vectora-company/ops/content-calendar.md`).
- Cupons early adopter ativos e rastreáveis no dashboard.
- `/roadmap` publicado com 4 seções e ≥10 itens.

---

## Princípios da Vectora (cardinais)

1. **Self-hosted é a proposta de valor central.** Toda comunicação,
   doc e marketing reforça: seus dados ficam no seu servidor.
   Nunca armazenamos conversas, código ou arquivos.

2. **Produto primeiro, empresa depois.** Nenhuma frente de
   marketing começa sem produto estável. Influenciadores recebem
   kit só quando produto está no ar e testado.

3. **Suporte pessoal é diferencial.** WhatsApp direto com o
   fundador é vantagem real que empresas grandes não oferecem.

4. **Documentação é produto.** Usuário que não consegue instalar
   com a doc é venda perdida. Doc recebe mesmo cuidado que o
   código.

5. **Preço honesto.** R$20/Plus e R$55/Pro são deliberadamente
   baratos. Estratégia é volume + fidelização, não margem alta em
   poucas contas.

6. **Open source como comunidade, fechado como produto.** Issues
   públicos, docs públicas, changelog público. Código proprietário
   — usuários sabem o que o produto faz porque doc é transparente.

7. **Um fundador, muita alavancagem.** Influenciadores como força
   de marketing, beta testers como QA informal, comunidade como
   suporte L1. Bruno foca em produto e no que só ele pode fazer.

8. **Schema-first / chat-first / auth-first / SDK-first.** As 4
   regras técnicas cardinais herdadas dos blocos A–C continuam
   válidas em D–S.

---

## Verificação end-to-end por bloco (resumo executivo)

- **A**: chat + welcome unificado + i18n + PWA + mobile + usage
  popover + reasoning effort + permission modes — todos funcionando
  no browser e mobile.
- **B**: signup → root → invite → trust folder → git workflow → PR
  via agente → admin panel com 5 sub-abas.
- **C**: MCP plugin add → tool funciona; skill install via git URL;
  PTY persistente; workbench 4 tabs com SWR; SSH/Codespace
  transparente; license validate cached.
- **D**: instalador nativo em VM limpa abre, valida licença, chat
  funciona. Auto-update beta→stable funciona com delta.
- **E**: pergunta complexa → DeepAgent delega coder/search/rag; HITL
  em 5 modos; `vectora chat --legacy` ainda funciona por 1 versão.
- **F**: lite hardening passa; trocar para `complete` → Postgres +
  Qdrant tudo verde no admin storage panel.
- **G**: 2 instâncias atrás de LB — rate limit compartilhado, cache
  invalidação via Redis.
- **H**: skill instalada muda comportamento; cache hit Anthropic
  visível; `web_map` funciona.
- **I**: sandbox + worktree por user funciona; ACP server expõe
  Vectora a Zed.
- **J**: `POST /v1/oauth/token` → JWT → OpenAI SDK Python aponta
  para Vectora.
- **K**: signup → trial → upgrade Plus→Pro via PIX (BR) ou Stripe
  (INTL); tier=plus tentando Postgres → erro.
- **L**: `pip install vectora-sdk` → cliente conecta; webhook chega
  com signature válido.
- **M**: trace OTel no Honeycomb; Sentry captura erro; backup +
  restore em VM staging.
- **N**: `apt install vectora` em Ubuntu funciona; VS Code
  extension instala via Marketplace.
- **O**: CNPJ ativo, conta PJ, domínios + emails operacionais,
  termos publicados.
- **P**: signup → dashboard → token reveal → assinar Plus BR via
  PIX → status ativo sem refresh.
- **Q**: `docs.vectora.company` no ar; quick-start em 10 min
  funciona em VM limpa.
- **R**: status page com 6 componentes, 10+ betas com NPS, WhatsApp
  - email + Issues + Discussions operacionais.
- **S**: PyPI 1.0 + Docker + Release nativo publicados; 5+
  influenciadores BR confirmaram; 10+ pagantes na semana 1.
