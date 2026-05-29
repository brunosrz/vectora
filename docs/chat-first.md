# Vectora — Chat-First DLC Plan

> Plano focado no chat web (`chat/`). Tudo que o Vectora Agent desenvolver
> daqui pra frente é pensado **através da lente do chat**: como o usuário vê,
> interage, dispara e consome o agente via UI Next.js.
>
> Quando o usuário fala em "Vectora Agent", refere-se ao backend Python
> (`vectora/`). Quando fala em "Vectora Chat", refere-se à UI Next.js (`chat/`).
> Ambos compõem o produto Vectora.

## Contexto

O chat deixou de ser fork do `chat-langchain` e virou interface oficial do
Vectora. Foundation técnica + polish foram concluídos (Blocos A e B). Daqui
em diante, cada feature nova do agente deve ter contraparte visível na UI —
nenhum recurso é considerado "pronto" até estar consumível pelo chat.

**Princípio cardinal: chat-first significa schema-first.** O backend declara
intenção via `metadata={"render_hint": ...}` nas tools, eventos tipados no
proto, e o chat dispatcha visualmente sem código por tool nova.

---

## Sumário (TOC)

| Bloco | Tema                                                                                      | Status       |
| ----- | ----------------------------------------------------------------------------------------- | ------------ |
| **A** | Chat Foundations                                                                          | ✅ Concluído |
| **B** | Polish, Bugfixes & Infra                                                                  | ✅ Concluído |
| **C** | Authentication & RBAC                                                                     | ✅ Concluído |
| **D** | Reasoning Reveal & Thinking UX                                                            | ✅ Concluído |
| **E** | HITL em Chat                                                                              | ✅ Concluído |
| **F** | File Handling Completo                                                                    | ✅ Concluído |
| **G** | Workspaces + Git Integration                                                              | ✅ Concluído |
| **H** | Slash Commands                                                                            | ✅ Concluído |
| **I** | Conversation Features (search, export, share)                                             | ✅ Concluído |
| **J** | Mobile & PWA                                                                              | ✅ Concluído |
| **K** | Live Metrics Dashboard                                                                    | ✅ Concluído |
| **L** | Settings Architecture                                                                     | ✅ Concluído |
| **M** | Performance, UX Polish & i18n/L10n                                                        | ✅ Concluído |
| **N** | Per-User Memory                                                                           | ✅ Concluído |
| **O** | Workspace Integrations (OAuth + API keys)                                                 | ✅ Concluído |
| **P** | Root Admin Panel (RBAC/ABAC global)                                                       | ✅ Concluído |
| **Q** | Workspace P2 + Auth Onboarding — Trust Folder, Scope Guard Rails, Worktree & Invites      | ⏳ Planejado |
| **R** | UX Polish — Command Bar, Permission Modes, Effort/Meter + i18n/Tema/Idioma & Input Polish | ⏳ Planejado |
| **S** | Connectors & Plugins Manager (cont. de O)                                                 | ⏳ Planejado |

---

## BLOCO A — Chat Foundations [CONCLUÍDO]

Toda a base do chat: backend API (FastAPI + SSE), frontend stack
(Next.js + Hono + Zustand), schema-driven rendering, bundling. Shipping.

| Sub-bloco                            | Entregue                                                                                                                                                                                                                                                  |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A1 — Limpeza do fork                 | `chat/src/` deletado, `chat/lib/api/langgraph-client.ts` removido, deps LangSmith/LangGraph SDK out, package renomeado para `vectora-chat`                                                                                                                |
| A2 — `vectora/api/` (FastAPI+SSE)    | Módulo completo: `server.py`, `handlers/chat.py` + `handlers/threads.py`, `adapters.py` (LangGraph events → SSE), `schemas.py`. Endpoints `StreamChat`, `ResumeChat`, `GetTools`, `Create/Get/List/Delete/Get Thread`/`GetHistory`, `/health`, `/metrics` |
| A3 — Tool metadata schema            | `metadata={"render_hint","category","destructive","icon"}` em todas as 17 tools (`vectora/tools/*.py`); endpoint `GET /tools/schema` expõe                                                                                                                |
| A4 — Hono backend integrado          | `chat/server/index.ts` + `chat/server/routes/{chat,threads,health}.ts` + `chat/app/api/[[...route]]/route.ts` montando no Next.js                                                                                                                         |
| A5 — Tipos TypeScript schema-driven  | `chat/lib/types/render.ts` (`RenderHint`, `ToolCategory`), `events.ts`, `messages.ts`, `tools.ts` — espelham proto                                                                                                                                        |
| A6 — Renderização schema-driven      | `chat/components/chat/tool-call-renderer.tsx` despacha por `render_hint`: `JsonViewer`, `DiffViewer`, `CodeBlockViewer`, `TerminalBlock`, `SearchResultsViewer`, `TableViewer`, `QueueBadge`, `QueueProgress`, `ArtifactCard`                             |
| A7 — SSE Heartbeat                   | MCP server emite `: heartbeat` a cada 25s; FastAPI/SSE usa `X-Accel-Buffering: no`                                                                                                                                                                        |
| A8 — Observabilidade base            | `VectoraTracer` SQLite + `GET /metrics` retornando últimos 50 spans                                                                                                                                                                                       |
| A9 — Subcomando CLI `vectora server` | `mcp` / `chat` / `headless` em `vectora/main.py`, com `chat_static/` bundle pronto pra `make build-chat`                                                                                                                                                  |
| A10 — `tools/schema` autodescoberta  | Frontend pode buscar lista completa de tools com `render_hint` + `args_schema` JSON                                                                                                                                                                       |

---

## BLOCO B — Polish, Bugfixes & Infra Improvements [CONCLUÍDO]

Tudo que foi **além do escopo planejado** durante a implementação do A. Emergiu
de bugs reais, fricção de UX e oportunidades de melhoria descobertas em uso.

### B1 — Modelos reais do Vectora Agent

- `chat/lib/config/deployment-config.ts` substituiu modelos do fork LangChain
  pelos **25 modelos reais** alinhados ao `AVAILABLE_MODELS` Python
  (`vectora/config/settings.py`): 6 Google (Gemini 3.x + 2.5), 12 OpenAI
  (GPT-5.5/5.4/5/4.1 + o3/o4-mini), 3 Anthropic (Claude 4.7/4.6/4.5), 4 Cohere
- Default: `gemini-2.5-flash`

### B2 — Branding completo Vectora

- Favicons gerados: `favicon-16x16.png`, `favicon-32x32.png`,
  `favicon-600x600.png`, `vectora.ico` multi-res (16/32/48/64/128/256)
- `Assistant Icon.svg` + `.png` — fundo navy com gradient + pássaro Vectora
  em azul claro, na escala correta (`translate(70,70) scale(1.8)`)
- Welcome screen: pássaro Vectora ao lado do texto `Vectora` no JetBrains Mono
- Header: ícone pequeno + texto
- Sidebar: 2 links Vectora (GitHub docs + Issues) em vez dos 3 links LangChain
- `app/layout.tsx` Open Graph + meta titles atualizados

### B3 — Pipeline de assets via Python

- `resvg-py` (Rust-backed, zero deps de sistema, Windows-friendly) +
  `Pillow` para multi-res ICO
- Comando one-shot para regenerar tudo a partir de um único SVG fonte

### B4 — React 19 + Next 16 compat

- `React.RefObject<T>` → `React.RefObject<T | null>` em todos os refs
- `useRef<T>()` → `useRef<T | undefined>(undefined)` (React 19 exige initial value)
- `hono/vercel` `handle()` retorna função única, não objeto destructurável
- Removidas referências a `client` (LangGraph SDK), `useCheckpointHistory`,
  `Checkpoint` type, `MODELS["glm-5"]`, `IMAGE_UNSUPPORTED_MODEL_MESSAGE`
- Removida lógica de upload de imagem hardcoded no GLM-5

### B5 — Turborepo + Turbopack

- `chat/package.json`: campo `packageManager: "pnpm@11.2.2"`, scripts com `--turbopack`
- `chat/turbo.json` criado (build/dev/lint/start tasks)
- Renomeado para `vectora-chat`

### B6 — Thinking timer & stream error handling

- `chat/lib/hooks/chat/use-stream-handler.ts`:
  - `thinkingStartTime: Date.now()` capturado na criação da mensagem
  - `isThinking: false` + `thinkingDuration` setados em `catch` (erro real **e** abort)
  - Bloco `finally` defensivo garante encerramento mesmo em paths inesperados

### B7 — Markdown envelope protocol

- Orchestrator envolve toda resposta em ` ``````markdown ... `````` `
  (seis crases) — evita conflito de fence quando a resposta contém blocos
  de código triplos internos
- `chat/lib/utils/string/markdown-envelope.ts`: `stripMarkdownEnvelope()`
  streaming-safe (suporta envelope parcial durante token streaming)
- Aplicado em `message-item.tsx` antes do `ReactMarkdown`
- Regra documentada no `_ORCHESTRATOR_PROMPT` (`vectora/agents/orchestrator.py`)

### B8 — Filtro de tokens de structured-output

- `vectora/api/adapters.py`: `_STRUCTURED_OUTPUT_NODES = {"orchestrator"}`
- Helper `_extract_orchestrator_response()` lê o `AIMessage(content=response)`
  do `Command.update` no `on_chain_end` e emite como `TokenEvent` único

### B9 — Dead code cleanup

- `/generate-title` endpoint legacy removido — usava `truncateTitle` como
  fallback puro
- Imports mortos (LangSmith, VECTORA_API_URL no string-helpers) removidos
- `Checkpoint` type definido localmente em `time-travel-panel.tsx`

### B10 — `.gitignore` fix

- Linha 17: `lib/` → `/lib/` (anchored to root) — desbloqueou commits de
  `chat/lib/**` que estavam silenciosamente ignorados

### B11 — Server lifecycle robusto

- `vectora/api/server.py`: `@asynccontextmanager _lifespan` com:
  - Startup opcional via `VECTORA_WARMUP_GRAPH=1`
  - Shutdown paralelo via `asyncio.gather`: `_stop_background_worker()` +
    `aclose_graph()` rodam simultâneos
  - Timeout total configurável (`VECTORA_SHUTDOWN_TIMEOUT_S`, default 10s)
- `vectora/api/handlers/chat.py`: funções públicas `aclose_graph()` +
  `awarm_graph()` encapsulam o estado privado (`_graph`, `_checkpointer_ctx`)
- `vectora/main.py`: `os._exit(0)` após `uvicorn.run()` — bypass de threads
  não-daemon de libs externas (langsmith, httpx, Cohere rate limiter)

### B12 — Logs auditáveis sem ruído

- `vectora/services/log_setup.py`: `_BackgroundConsoleFilter` expandido
- Silenciados completamente: `langsmith`, `langsmith.client`, `uvicorn.access`, `fastapi`
- `vectora/main.py`: uvicorn `log_level="warning"` + `access_log=False`;
  override via `VECTORA_UVICORN_LOG_LEVEL`

### B13 — GetHistory reusa singleton do grafo

- `vectora/api/handlers/threads.py`: `get_history()` agora chama
  `_get_graph()` em vez de rebuildar via `async with AsyncSqliteSaver` a
  cada request — eliminou o spam de "Building LangGraph"

### B14 — Zustand stale-while-revalidate

- `pnpm add zustand@5.0.13`
- `chat/lib/stores/threads-store.ts`: cache `Record<threadId, {messages, fetchedAt, updatedAt}>`
- `chat/lib/hooks/chat/use-thread-messages.ts`: drop-in replacement de
  `useState<Message[]>`, subscreve apenas ao slice da thread atual
- `chat/components/chat/chat-interface.tsx`: lê cache via
  `useThreadsStore.getState()` (não-reativo) dentro do effect — evita loop
- `chat/app/page.tsx`: `invalidate()` ao deletar thread
- Resultado: trocar para thread já visitada renderiza **instantaneamente**,
  fetch silencioso revalida em background

### B15 — Orchestrator post-RAG synthesis path

- Defesa contra `GraphRecursionError` em loop orchestrator↔rag_subgraph
- Síntese determinística pós-RAG quando última mensagem é `SystemMessage(name="rag_context")`

---

## BLOCO C — Authentication & RBAC [CONCLUÍDO]

**Contexto.** Vectora não é um chatbot comum — opera com acesso real ao
filesystem, terminal, RAG indexado, secrets. Empresas instalam em VPS e
compartilham com a equipe. Sem autenticação, expor o `vectora server`
publicamente é inviável — qualquer pessoa com a URL teria controle total
do servidor.

Segundo eixo: **separação por usuário**. Sessões, threads, workspaces,
secrets, audit trail — tudo escopado por identidade. Auth não é só
"manter intrusos fora"; é a base que permite UX multi-tenant decente
(privacidade, organização, accountability).

**Modelo cardinal:**

- `vectora` CLI local = **root por default** (quem tem acesso ao filesystem do
  servidor já tem controle total — exigir login seria teatro de segurança).
  Pode opcionalmente logar; uma vez logado, a sessão passa a operar como
  esse usuário até `vectora auth logout`.
- `vectora server` (chat | mcp | headless) = **autenticação obrigatória**.
  Sem token válido, retorna 401 em tudo exceto `/health` e `/auth/*`.
- Primeiro acesso ao web = tela de criação de conta; primeiro usuário criado
  vira `root` automaticamente.

### C1 — Identity model (backend)

**Arquivo novo** `vectora/services/auth.py`:

- Pydantic models: `User`, `Session`, `Role`, `Credentials`
- Hash de password: `argon2-cffi` (Argon2id, defaults seguros)
- Tabela SQLite `users(id, email, password_hash, role, env_overrides_json, created_at, last_login_at)` no banco principal (`~/.vectora/checkpoints.db`)
- Tabela `refresh_tokens(token_hash, user_id, expires_at, revoked, created_at)`
- Roles: `root`, `admin`, `member`, `viewer`

### C2 — JWT signing e token lifecycle

- `python-jose[cryptography]` ou `pyjwt` para signing
- Algoritmo: HS256 com secret em `~/.vectora/auth.key` (gerado on first run,
  permissão 600), ou Ed25519 para deployments avançados
- **Access token** (~15min): claims `{sub, email, role, exp, iat}`
- **Refresh token** (~7d): opaque, hashed em DB; rotação a cada refresh
- Endpoint `POST /auth/refresh` aceita refresh token e emite novo par
- Logout invalida o refresh token (deleta do DB)

### C3 — Endpoints de auth (proto + REST)

Novo serviço no proto: `AuthService`:

- `SignUp(email, password) → {user, access_token, refresh_token}`
  - Primeiro user da instância vira `root` automaticamente
  - Sub-sequentes vão como `member` por default (admin/root podem promover)
  - Validação: email RFC-compliant, password ≥ 12 chars
- `SignIn(email, password) → {access_token, refresh_token, user}`
- `Refresh(refresh_token) → {access_token, refresh_token}`
- `SignOut(refresh_token)` → invalida
- `Me() → User` (auth required, retorna dados do usuário atual)
- `ChangePassword(old, new)` (auth required)

REST equivalents montados em `vectora/api/handlers/auth.py`:

- `POST /auth/signup`, `/auth/signin`, `/auth/refresh`, `/auth/signout`
- `GET /auth/me`, `POST /auth/change-password`

### C4 — Middleware FastAPI

- `vectora/api/middleware/auth.py` (novo): `get_current_user` dependency
- Aplicado em **todos** os handlers exceto: `/health`, `/auth/*`, `/docs`,
  static files
- Extrai `Authorization: Bearer <token>` ou cookie httpOnly `vectora_access`
- 401 com `WWW-Authenticate: Bearer` se inválido/expirado
- Injeta `request.state.user: User` para handlers consumirem

### C5 — RBAC: permissões por role

| Role     | Pode                                                                                        | Não pode                                             |
| -------- | ------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| `root`   | Tudo (criar/deletar users, mudar roles, deletar threads de outros, full secrets access)     | —                                                    |
| `admin`  | Criar workspaces compartilhados, deletar threads de members, ver audit log completo         | Mudar role de outros, deletar root                   |
| `member` | Threads próprias, workspace próprio, RAG escopado, terminal **apenas em workspace próprio** | Threads de outros, deletar workspaces compartilhados |
| `viewer` | Read-only em workspaces compartilhados (chat sem envio), exportar                           | Enviar mensagens, criar workspaces, qualquer write   |

Implementação:

- `vectora/services/permissions.py` (novo): `check_permission(user, action, resource) → bool`
- Decorator `@require_role("admin")` para handlers
- Thread ownership via coluna `threads.user_id`; permissões consultam
  `user_id == request.user.id OR user.role in {admin, root}`

### C6 — Modo unauthenticated do CLI

- `vectora chat`, `vectora rag`, `vectora workspaces`, `vectora mcp` no
  terminal local não exigem login — assumem root
- Implícito: usuário com shell access no servidor já tem root via filesystem
- Implementação: helper `get_local_user()` retorna `User(role="root", email="local@vectora")`
  quando rodando em modo CLI (não server)
- Override via `VECTORA_AUTH_REQUIRED=true` no env para forçar auth mesmo
  no CLI (deploy paranoico)

### C7 — Modo authenticated do CLI

Novo subcomando `vectora auth`:

- `vectora auth signup` — interativo: email, password (com confirmação),
  hits `POST /auth/signup` do servidor configurado em `~/.vectora/config.toml`
- `vectora auth login` — interativo: email + password → guarda tokens
- `vectora auth logout` — invalida refresh token no server + limpa local
- `vectora auth whoami` — mostra usuário ativo + role + servidor
- `vectora auth refresh` — força rotação (debug)

Storage local:

1. **Primeira opção**: keyring do OS via `keyring` package
   - Windows: Credential Manager
   - macOS: Keychain
   - Linux: Secret Service (gnome-keyring/kwallet)
2. **Fallback**: `~/.vectora/auth.json` com permissão `0600`
3. Estrutura: `{"server_url": "...", "user_id": "...", "email": "...",
"access_token": "...", "refresh_token": "...", "expires_at": "..."}`

Quando logado, **todos** os comandos do CLI (incluindo `vectora chat`)
passam a usar o token — root local é sobrescrito pela identidade autenticada.
`vectora auth logout` volta pra root local.

### C8 — Frontend: tela de login/signup

- Rota `/auth/signin`, `/auth/signup` em `chat/app/auth/`
- Detecta primeiro acesso: `GET /auth/has-users` retorna `{exists: false}`
  → redirect automático para `/auth/signup`
- Após primeiro signup, fluxo padrão exige `/auth/signin`
- Token storage:
  - **Cookie `httpOnly` + `SameSite=Strict`** para access_token
    (Next.js middleware) — primário, mais seguro contra XSS
  - Refresh token em cookie similar, vida mais longa
  - Refresh automático: middleware Next.js intercepta 401, tenta refresh,
    retry uma vez antes de redirecionar para `/auth/signin`
- Formulário com validação client-side (Zod) + server errors inline
- Componente shadcn `Form` + `Input` + `Button` (já tem `chat/components/ui/`)

### C9 — Frontend: indicador de usuário ativo + dropdown

- `chat/components/layout/user-menu.tsx` (novo): avatar redondo com inicial
  do email no header, à esquerda do "New Chat"
- Click → dropdown: nome, email, role badge, "Settings", "Logout"
- Logout → `POST /auth/signout` + clear cookies + redirect `/auth/signin`
- Settings → modal completo (M1 do plano), aba "Account" + aba "Envs" (C10)
- Zustand store `chat/lib/stores/auth-store.ts`:
  `{ user, isAuthenticated, hydrate(), logout() }`
- Persiste user data (não token) em sessionStorage para evitar flash de
  "loading" no header

### C10 — Secrets/Envs por usuário

**Conceito.** Cada user pode sobrescrever variáveis de ambiente do agente
quando o agente roda em request dele. Mesclagem em runtime:

```python
effective_env = {**system_env, **user.env_overrides}
```

Permite ex.: root deixar `GH_TOKEN` vazio → cada usuário configura o seu,
trabalha em suas próprias branches/PRs (G6).

**UI** (Settings → "Envs"):

- Tabela: `KEY` | `VALUE` (sempre `••••••••`) | action (Edit / Delete)
- Botão "Add env var" → form: key + value
- Indicador visual: "Inherited from root" / "Custom (yours)"
- Reset: remove o override do user (volta a herdar do system)

**Backend storage**:

- Default: SQLite + libsodium (PyNaCl `SecretBox`)
- Chave de criptografia derivada do password do user via PBKDF2/scrypt
  (re-derivada no signin e mantida em memory por dentro do session)
- Logout = chave descarregada; envs ficam ilegíveis até próximo signin
- Trade-off: troca de password obriga re-criptografar todos os envs
  (`POST /auth/change-password` faz isso atomicamente)

### C11 — Provider de keystore: KeePassXC `.kdbx` embarcado

**Decisão arquitetural.** Vectora é self-hosted, single-binary friendly —
nada de daemons externos. KeePassXC é GUI, mas o **formato `.kdbx`** é
padrão aberto e o Python tem `pykeepass` que lê/escreve `.kdbx` direto,
sem precisar do KeePassXC instalado.

Mesmo padrão do SQLite (checkpointer) e LanceDB (vector store):
**um arquivo no disco, sem serviço**.

**Por que `.kdbx`** em vez do PyNaCl interno (C10):

- Formato auditável e padronizado (KDBX4: AES-256-CBC + ChaCha20 + Argon2id KDF)
- Usuário pode abrir o `.kdbx` no KeePassXC desktop / mobile (KeePass2Android,
  Strongbox iOS) para ver/editar fora do Vectora se quiser
- Mesma chave protege múltiplas entries — não há "uma chave por env var"
- `pykeepass` é maduro, em produção desde 2018, pure-Python, sem deps nativas

**Layout** (`~/.vectora/secrets/`):

```
~/.vectora/secrets/
├── system.kdbx           # envs do root/sistema (criado on first run)
└── users/
    ├── <user_id_1>.kdbx  # envs por usuário
    ├── <user_id_2>.kdbx
    └── ...
```

**Lifecycle**:

- Master password do `.kdbx` derivado do password do user (PBKDF2 a partir
  do mesmo password de login → não precisa de senha extra)
- Login bem-sucedido → handle do `.kdbx` aberto em memory, mantido na session
- Logout → handle descarregado; arquivo `.kdbx` segue criptografado em repouso
- Change password (C9) → re-criptografa `.kdbx` com nova chave (atomic via tempfile + rename)

**Config** (`~/.vectora/secrets.toml`):

```toml
provider = "keepass"   # default. Reservado: "internal" (PyNaCl puro, sem .kdbx)

[keepass]
dir = "~/.vectora/secrets"   # path base — override pra montar em volume diferente
kdf_iterations = 60          # Argon2id rounds (default seguro)
```

**Módulo** `vectora/services/secrets/`:

- `base.py`: Protocol `SecretsProvider` — `get(user, key)`, `set(user, key, value)`, `list(user)`, `delete(user, key)`, `unlock(user, password)`, `lock(user)`
- `keepass.py`: implementação via `pykeepass.PyKeePass`; cria `<user_id>.kdbx`
  na primeira chamada de `unlock()` para um user novo
- `internal.py`: fallback PyNaCl (SQLite + SecretBox) — útil para testes
  unitários e ambientes ultraminimalistas

**Vantagens operacionais**:

- Backup trivial: copiar a pasta `~/.vectora/secrets/`
- Migração entre máquinas: mover os `.kdbx` (a senha de cada user mantém a chave)
- Auditoria offline: admin pode abrir `system.kdbx` no KeePassXC desktop
  para inspecionar entries de sistema (read-only se quiser)

**Trade-off conhecido**: cada user adiciona um `.kdbx`. Para 100+ users isso
ainda é file system trivial (cada `.kdbx` típico tem ~10KB). Se virar
problema, futura otimização: shared `.kdbx` com groups por user_id —
mas adiciona complexidade que não justifica em hoje.

### Dependência adicional (`pyproject.toml`)

```toml
pykeepass = ">=4.1"
```

### C12 — Audit log

- Tabela `audit(id, user_id, action, target_type, target_id, timestamp, ip, user_agent, success, metadata_json)`
- Eventos rastreados:
  - Auth: `signup`, `signin`, `signin_failed`, `signout`, `change_password`,
    `refresh_token_rotation`
  - Threads: `thread_create`, `thread_delete`
  - Workspaces: `workspace_create`, `workspace_delete`, `workspace_switch`
  - Tools destrutivas: `tool_call` quando `tool.metadata.destructive=True`
    (terminal, file_write, db_migrate, manage_retriever delete, etc.)
- Endpoint `GET /audit` — admin/root only — filtros: `user_id`, `action`,
  `date_range`, `success`
- UI: aba "Audit" em Settings (admin/root only)

### C13 — Rate limiting

- `slowapi` (FastAPI-friendly) ou implementação custom com sliding window
- Limits por user_id em endpoints sensíveis:
  - `/auth/signin`: 5/min por email (failure-based, sucesso reseta)
  - `/auth/signup`: 3/hour por IP (anti-spam)
  - `/auth/change-password`: 3/hour por user
  - `StreamChat`: 60/min por user (gera carga LLM real)
- Lockout: 10 falhas de login em 1h bloqueia o email por 1h
- Storage: in-memory (single-server) ou Redis (multi-server) — `~/.vectora/config.toml`

### C14 — Setup wizard server-side

- Primeira run de `vectora server chat` sem usuários → log especial:
  ```
  ✨ Vectora aguardando setup. Abra http://localhost:8080 e crie o
     primeiro usuário (esse vira root automaticamente).
  ```
- `/auth/signup` aceita signup sem auth APENAS enquanto não houver users
- Após o primeiro signup, signup público é restrito (config
  `allow_public_signup: bool = False` no `~/.vectora/config.toml`)
- Root pode criar users adicionais via API: `POST /admin/users` (admin/root only)

### Dependências novas (`pyproject.toml`)

```toml
argon2-cffi = ">=23.1"        # password hashing
python-jose = { version = ">=3.3", extras = ["cryptography"] }  # JWT
pynacl = ">=1.5"              # secrets crypto
slowapi = ">=0.1.9"           # rate limiting
keyring = ">=25.0"            # OS keyring no CLI

# Secrets keystore (C11):
pykeepass = ">=4.1"           # KeePassXC .kdbx embarcado, pure-Python
```

### Arquivos críticos (Bloco C)

| Sub     | Arquivos chat                                                                                                  | Arquivos vectora (Python)                                                                                              |
| ------- | -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| C1-C2   | —                                                                                                              | `vectora/services/auth.py` (novo), tabelas em `vectora/services/session.py`                                            |
| C3      | —                                                                                                              | `vectora/api/protos/.../auth.proto` (novo), `vectora/api/handlers/auth.py` (novo), `vectora/api/schemas.py` (+ models) |
| C4      | —                                                                                                              | `vectora/api/middleware/auth.py` (novo), `vectora/api/server.py` (registrar middleware)                                |
| C5      | —                                                                                                              | `vectora/services/permissions.py` (novo), `vectora/state.py` (+ user_id em threads)                                    |
| C6-C7   | —                                                                                                              | `vectora/main.py` (subcomando `auth`), `vectora/cli/auth.py` (novo)                                                    |
| C8      | `chat/app/auth/signin/page.tsx`, `chat/app/auth/signup/page.tsx`, `chat/middleware.ts` (refresh) — todos novos | `/auth/has-users` endpoint                                                                                             |
| C9      | `chat/components/layout/user-menu.tsx`, `chat/lib/stores/auth-store.ts` — novos                                | —                                                                                                                      |
| C10-C11 | `chat/components/layout/settings-dialog/envs-tab.tsx` (novo)                                                   | `vectora/services/secrets/{base,internal,keepass}.py` (novos), dep `pykeepass>=4.1`                                    |
| C12     | `chat/components/layout/settings-dialog/audit-tab.tsx` (novo, admin)                                           | `vectora/api/handlers/audit.py` (novo), tabela `audit`                                                                 |
| C13     | —                                                                                                              | `vectora/api/middleware/rate_limit.py` (novo)                                                                          |
| C14     | first-run banner no `/auth/signup`                                                                             | `vectora/main.py` (banner log)                                                                                         |

### Verificação

- `vectora server chat` em VPS fresh → primeira visita web mostra signup
- Após signup, root criado; logout → signin com credenciais corretas
- Criar segundo user (member) via root; member tenta ver thread do root → 403
- `vectora auth login` no CLI → `vectora chat` opera como esse user
- `vectora auth logout` → próximo `vectora chat` volta a operar como root local
- Configurar `GH_TOKEN` em env_overrides de um user → request desse user
  vê o token no env do agente; outro user não
- Audit log: `signin_failed` aparece após password errada; `tool_call`
  para `file_write` aparece quando tool roda
- Rate limit: 6º signin attempt em <1min retorna 429
- Vaultwarden opt-in: configurar `secrets.toml` → secrets agora persistem lá

---

## BLOCO D — Reasoning Reveal & Thinking UX

**Contexto.** Hoje o usuário vê só a resposta final. O `OrchestratorDecision`
carrega `reason`, `delegate_to`, `task_query` — sinais ricos do raciocínio que
estão sendo descartados. Modelos modernos (Claude, GPT-5, Gemini 3) tornaram
o "thinking visible" parte da experiência esperada.

### D1 — Reason field como bloco "Thinking" colapsável

- Backend: `vectora/api/adapters.py` emite novo `ThinkingEvent` contendo
  `reason` extraído do `OrchestratorDecision` no `on_chain_end` do orchestrator
- Frontend: novo render hint `thinking` ou campo dedicado em `Message`:
  `thinking?: string`
- Componente colapsado por padrão acima da resposta — clica e expande
- Ícone de "raciocínio" (lucide `brain` ou `sparkles`)

### D2 — Stream de progresso semântico

Hoje o frontend mostra apenas "Thinking..." genérico. Substituir por:

- `Routing: search` — quando orchestrator decide delegate
- `Searching the web…` — quando search_agent inicia
- `Synthesizing 5 documents…` — quando RAG injeta contexto
- `Generating image with nano-banana…` — após Bloco I do roadmap principal

Implementação: o `NodeEvent` já carrega `node` + `status`; mapear cada nome
em `chat/lib/constants/node-labels.ts`.

### D3 — Per-node duration badges

- `NodeEvent` já carrega `duration_ms` quando `status="finished"`
- Badge sutil ao lado da resposta: `orchestrator 800ms · search 2.1s · rag 350ms`

### D4 — Dev mode toggle

- `?dev=1` na URL ou setting hidden ativa exibição de:
  - `delegate_to`, `task_query` (decisão completa do orchestrator)
  - `routing_decision` do state
  - Tool args completos sem truncamento
- Default: off (UX limpa para usuário final)

**Arquivos críticos:** `vectora/api/adapters.py`, `vectora/api/schemas.py` (+ProtoEvent), `chat/lib/types/events.ts`, `chat/lib/types/messages.ts`, `chat/components/chat/message-item.tsx` (Thinking block + NodeBadges), `chat/lib/constants/node-labels.ts` (novo)

---

## BLOCO E — HITL em Chat

**Contexto.** O agente Python implementa HITL via `interrupt_before` do
LangGraph. Este bloco define como o chat web apresenta a pausa e coleta a
decisão do usuário.

### E1 — Backend HITL emitido como SSE

- `interrupt_before=["coder_tools"]` no `build_graph()`
- `HITLEvent` no proto: `tool_name`, `args_json`, `interrupt_id`, `diff_preview` (opcional)
- `vectora/api/adapters.py` detecta interrupt e emite `HITLEvent` no stream

### E2 — Painel de aprovação no chat

- Modal/inline card aparece quando `HITLEvent` chega
- 4 ações alinhadas com Deep Agents:
  - **Approve** — continua com args originais
  - **Edit** — abre editor JSON dos args
  - **Reject** — cancela; envia feedback ao agente
  - **Respond** — envia mensagem humana como resultado da tool
- `ResumeChat({thread_id, interrupt_id, decision})` retoma o stream

### E3 — Diff preview para tools de filesystem

- Para `file_edit`/`file_write`: backend gera diff e injeta em `diff_preview`
- Chat renderiza com `DiffViewer` (já existe) **antes** dos botões de ação

### E4 — Configuração por tipo de tool

- Setting na UI: "Confirmar antes de…" → checkboxes por tool category
  (filesystem, terminal, rag-destructive, paid-generation)
- Persistido por user (C10) em `~/.vectora/config.toml`, lido pelo `vectora/graph.py`

**Arquivos críticos:** `vectora/api/protos/.../chat.proto` (HITLEvent), `vectora/graph.py` (interrupt_before), `vectora/api/adapters.py`, `chat/components/chat/features/hitl-panel.tsx` (novo), `chat/lib/hooks/chat/use-stream-handler.ts` (resume on event)

---

## BLOCO F — File Handling Completo

**Contexto.** Welcome screen tem botão de attach + drag-and-drop básico, mas
o pipeline downstream não está completo.

### F1 — Multimodal LLM call com attachments

- Atualizar `StreamChatRequest` no proto: `attachments: list[Attachment]`
- `vectora/api/handlers/chat.py` converte para `HumanMessage(content=[{"type": "image_url", ...}])`
- Suporte a image, PDF, código (texto inline truncado a N kB)

### F2 — PDF preview no input

- Chat: ao anexar PDF, render primeira página via `pdf.js` (cliente-side)
- Botão "Adicionar ao RAG" abre `ingest_docs` com o arquivo

### F3 — Drag-and-drop pra indexar

- Arrastar arquivo na sidebar → confirma "Adicionar ao RAG do workspace ativo"
- Streaming de progresso via `queue_progress` render hint (já existe)

### F4 — Code attachment com syntax highlight

- Detecta extensão, injeta em `CodeBlockViewer` (já existe)

**Arquivos críticos:** `vectora/api/protos/.../chat.proto`, `vectora/api/handlers/chat.py`, `chat/components/chat/features/file-preview-grid.tsx` (extend), `chat/lib/utils/files/pdf-preview.ts` (novo)

---

## BLOCO G — Workspaces + Git Integration

**Contexto.** Workspaces (do roadmap principal) trazem isolamento por
projeto. Para devs, "projeto" é quase sempre **repositório git** — e a UX
do Vectora precisa tratar isso como cidadão de primeira classe: selecionar
pasta existente, criar pasta nova, **ou clonar repositório**. Cada user
pode trabalhar no mesmo repo em sua própria worktree/branch usando seu
próprio `GH_TOKEN` (C10).

### G1 — Workspace selector no header

- Dropdown à esquerda do "New Chat", mostra workspace ativo + lista
- Click → switch via `WorkspaceService.SetActive(workspace_id)` no backend
- Estado em Zustand store: `workspaces-store.ts` (cache `list` + `active_id`)

### G2 — Criar workspace: 3 modos

- **Existente**: file picker → selecionar pasta local
- **Novo**: input nome + path destino → `mkdir -p` e inicializa
- **Clone**: input git URL + path → `git clone` em background (usa `GH_TOKEN`
  do user)
- Modal único com tabs no header, fluxo guiado
- Workspace ID = `sha256(abspath(cwd))[:8]` como definido no roadmap principal

### G3 — Git tools no Vectora Agent

Novo módulo `vectora/tools/git.py`:

| Tool                                    | render_hint  | destructive           | HITL                    |
| --------------------------------------- | ------------ | --------------------- | ----------------------- |
| `git_status`                            | `diff`       | false                 | não                     |
| `git_log(n=10, branch?)`                | `table`      | false                 | não                     |
| `git_diff(ref?)`                        | `diff`       | false                 | não                     |
| `git_branch(action, name?)`             | `table`      | parcial (delete=true) | em delete               |
| `git_checkout(ref)`                     | `code_block` | true                  | sim (perde uncommitted) |
| `git_commit(message, files=None)`       | `code_block` | true                  | **sim** (sempre)        |
| `git_worktree(action, name?, branch?)`  | `table`      | true (em remove)      | em remove               |
| `git_push(remote, branch, force=False)` | `code_block` | true                  | **sim**                 |
| `git_pull(remote, branch)`              | `code_block` | true (pode mergear)   | sim                     |
| `git_stash(action, name?)`              | `code_block` | parcial               | em pop/drop             |

Tools gh CLI (em `vectora/tools/gh.py`):
| Tool | render_hint |
|------|-------------|
| `gh_pr_create(title, body, base, draft=False)` | `code_block` |
| `gh_pr_list(state="open")` | `table` |
| `gh_pr_view(pr_number)` | `code_block` |
| `gh_pr_review(pr_number, verdict, body)` | `diff` |
| `gh_pr_merge(pr_number, method="squash")` | `code_block` (destructive) |
| `gh_issue_create(title, body, labels=[])` | `code_block` |
| `gh_issue_list(state, labels=[])` | `table` |
| `gh_issue_view(issue_number)` | `code_block` |
| `gh_issue_comment(issue_number, body)` | `code_block` |

Deps: `gitpython>=3.1` para operações locais; `gh` CLI via `subprocess` para GitHub.

### G4 — Training do orchestrator pra git workflows

System prompt enriquecido com regras git-aware:

```
## Git workflow

Quando o workspace tem repositório git, prefira workflows seguros:

- ANTES de modificações grandes, sempre crie uma worktree:
  `git_worktree create feature-X` — evita conflitos com main
- Commit messages SEMPRE seguem semantic commits:
  feat:/fix:/refactor:/docs:/test:/chore:
- Pull request: primeiro push da branch, depois `gh_pr_create`
- Code review: use `gh_pr_review` com verdict approve/request_changes/comment
- Issues abertas: liste com `gh_issue_list` antes de iniciar feature nova
  para evitar trabalho duplicado
- Para hotfix em produção: branch a partir de main, commit isolado, PR direto

Nunca:
- Force push em main/master sem confirmação explícita do usuário
- Commit "wip" ou mensagens vagas — sempre escreva o porquê
- Misturar refactor + feature no mesmo commit
```

### G5 — Git status no UI

- Badge discreto no header (à direita do workspace selector): branch atual
  · ahead/behind indicator · dirty dot
  `🌿 feature-auth · ↑2 ↓0 · ●` (● = dirty)
- Click → painel inline com `git_status` formatado
- Polling leve: 5s quando aba ativa, pausa quando inativa
- Endpoint backend: `GET /workspaces/{id}/git/status` (cached por 2s)

### G6 — Per-user Git authentication

Caso de uso: empresa instala Vectora; cada dev tem seu próprio `GH_TOKEN`
configurado nos envs (C10). Ao invés do root deixar token no system env
(que vazaria entre users), root deixa `GH_TOKEN` vazio e cada user
configura o próprio.

- Tools git usam `os.environ` final = `system_env + user.env_overrides`
- Convenção opcional de branch naming: `<role>/<user_short>/<task>` ex:
  `feat/bruno/auth-jwt` — configurável em `~/.vectora/config.toml`
- `gh_pr_create` injeta `Co-Authored-By` apenas se user explicitamente
  habilitar — default desligado (nunca creditar Vectora em commits sem
  consentimento)

### G7 — Workspace = repo git (auto-detecção)

- Se `workspace.cwd` contém `.git`, ativa "git mode" automaticamente
- `WorkspaceInfo` retornado pela API ganha campos:
  ```
  is_git_repo: bool
  git_remote: str | None
  git_default_branch: str | None
  git_current_branch: str | None
  ```
- Manifest do workspace (do roadmap principal) ganha seção "Git State"
  no MANIFEST.md

### G8 — Worktree management na UI

- Tool `git_worktree create <name>` cria em `~/.vectora/worktrees/<workspace>/<name>`
- Cada thread pode estar associada a uma worktree do mesmo repo
  (`thread.metadata.worktree`)
- Header mostra: `Workspace: vectora · Worktree: feat-multimodal`
- Selector secundário para trocar worktree sem trocar workspace
- Útil para múltiplas features paralelas sem conflict de checkout

### G9 — PR review workflow guiado

- Quando user pergunta "review PR #123": orchestrator delega para
  agente novo `pr_reviewer` (ou subagente do coder) que:
  1. `gh_pr_view 123` — pega contexto
  2. `git_diff origin/main...PR_BRANCH` — analisa mudanças
  3. Avalia: segurança, testes, style, breaking changes
  4. Sugere `gh_pr_review` com verdict + comentários inline
- UI: render especial pra resultado — mostra diff lado-a-lado com
  comentários da AI inline (similar ao GitHub PR review)

### Dependências novas (`pyproject.toml`)

```toml
gitpython = ">=3.1"
# `gh` CLI binary — requisito de sistema, não Python
```

### Arquivos críticos (Bloco G)

| Sub | Arquivos chat                                                                                  | Arquivos vectora (Python)                                                                         |
| --- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| G1  | `chat/components/layout/workspace-selector.tsx`, `chat/lib/stores/workspaces-store.ts` (novos) | `vectora/api/protos/.../workspace.proto` (novo serviço)                                           |
| G2  | `chat/components/layout/workspace-create-modal.tsx` (novo, 3 tabs)                             | `vectora/api/handlers/workspaces.py` (novo, `Create/Clone`)                                       |
| G3  | —                                                                                              | `vectora/tools/git.py` (novo), `vectora/tools/gh.py` (novo), `vectora/nodes/tools.py` (registrar) |
| G4  | —                                                                                              | `vectora/agents/orchestrator.py` (prompt expansion)                                               |
| G5  | `chat/components/layout/git-status-badge.tsx` (novo)                                           | `/workspaces/{id}/git/status` endpoint                                                            |
| G6  | aviso na UI de Envs (C10)                                                                      | merge logic em `vectora/services/auth.py`                                                         |
| G7  | extends `WorkspaceInfo` consumer                                                               | `vectora/services/workspace.py` (auto-detect git)                                                 |
| G8  | secondary worktree selector                                                                    | `git_worktree` tool + storage em `~/.vectora/worktrees/`                                          |
| G9  | `chat/components/chat/features/pr-review-view.tsx` (novo render especial)                      | `vectora/agents/pr_reviewer.py` (novo, opcional separar do coder)                                 |

### Verificação

- `vectora chat` numa pasta sem git → workspace selector mostra "Clone" tab
- Clonar `github.com/brunosrz/vectora` → pasta criada, workspace ativo
- Badge no header mostra `🌿 main · ↑0 ↓0 · ○`
- Mensagem: "abra uma branch feat-test e faça commit do README" →
  HITL antes do commit → approve → commit aparece em `git_log`
- User B faz signin, configura seu `GH_TOKEN`, abre PR → PR aparece com
  authorship dele (root nunca vê o token dele)
- Worktree: criar 2 worktrees do mesmo repo, abrir 2 threads em paralelo
  trabalhando em features diferentes — sem conflitos
- PR review: dar PR URL → agente roda análise → resultado com diff + comentários

---

## BLOCO H — Slash Commands

**Contexto.** TUI tem comandos `/rag`, `/workspaces`, `/models`. No web, zero.
Slash commands tornam ações de power-user descobríveis e rápidas.

### H1 — Autocomplete inline com `/`

- Ao digitar `/` no início do input, popup mostra lista filtrada
- Cada comando: nome + descrição + arg preview

### H2 — Comandos implementados

| Comando              | Ação                                  | Endpoint backend                     |
| -------------------- | ------------------------------------- | ------------------------------------ |
| `/rag add <path>`    | Indexa pasta/arquivo                  | `ingest_docs` tool via thread        |
| `/rag list`          | Mostra panel `/rag` inline            | `GET /rag/stats` (novo)              |
| `/workspace <name>`  | Switch workspace                      | `WorkspaceService.SetActive`         |
| `/clone <git-url>`   | Clona repo como workspace novo        | G2                                   |
| `/branch <name>`     | Cria/switch branch no workspace ativo | `git_branch` tool                    |
| `/pr <title>`        | Cria PR da branch atual               | `gh_pr_create`                       |
| `/model <name>`      | Quick switch modelo da thread         | client-side (atualiza `agentConfig`) |
| `/clear`             | Limpa thread atual (mantém ID)        | `DeleteThread` + `CreateThread`      |
| `/export [md\|json]` | Download conversa                     | client-side                          |
| `/share`             | Cria URL read-only                    | `POST /threads/{id}/share` (novo)    |
| `/auth logout`       | Logout                                | C9                                   |
| `/help`              | Lista todos os comandos               | client-side                          |

### H3 — Histórico de comandos

- `↑`/`↓` no input com `/` digitado navega histórico
- Persiste em `localStorage` (por user_id quando autenticado)

**Arquivos críticos:** `chat/components/chat/features/slash-commands.tsx` (novo), `chat/lib/constants/slash-commands.ts` (registry), `chat/components/chat/chat-input.tsx` (hook into onChange), `vectora/api/handlers/share.py` (novo endpoint)

---

## BLOCO I — Conversation Features

### I1 — Search dentro da thread + global

- Search bar no topo de cada thread (search messages)
- Search global na sidebar (já tem o input, mas só filtra título)
- Backend: novo endpoint `POST /threads/search` com query + scope (`current` | `all`)
- Respeita ownership (C5): users só veem suas próprias threads ou threads compartilhadas

### I2 — Export

- `.md` via `/export md` ou botão no menu da thread
- `.json` (formato completo com metadata, tool_calls)
- Render formatado com timestamps, roles, tool calls inline

### I3 — Share (read-only URL)

- `POST /threads/{id}/share` → retorna `share_token`
- Rota pública `/share/{token}` no chat — renderiza thread em modo read-only
- Storage backend: tabela `shared_threads(token, thread_id, expires_at, created_by)`
- Apenas owner ou admin pode share; rotas públicas não precisam auth

### I4 — Edit message + regenerate

- Botão `Edit` em mensagens do usuário (parcialmente implementado)
- Editar → submit → drop mensagens posteriores → re-stream
- Botão `Regenerate` em respostas (já tem) — polish: confirmação + animação

### I5 — Branching (Fork from here)

- Botão em qualquer mensagem
- Cria nova thread copiando histórico até aquela mensagem
- Útil para "e se eu tivesse perguntado X em vez de Y"

**Arquivos críticos:** `chat/components/chat/features/thread-search.tsx` (novo), `chat/lib/utils/export/` (novo módulo), `chat/app/share/[token]/page.tsx` (novo), `vectora/api/handlers/share.py` (novo)

---

## BLOCO J — Mobile & PWA

### J1 — Sidebar responsiva

- Drawer pattern: ícone hamburger no mobile, sidebar como sheet overlay
- `<768px`: sidebar escondida por default
- `chat/components/layout/sidebar.tsx`: usar shadcn `Sheet` em mobile

### J2 — PWA manifest + service worker

- `chat/public/manifest.json` + `service-worker.js`
- Instalável como app, ícones já existem (`favicon-600x600.png`)
- Offline: cache do shell + última thread visualizada

### J3 — Touch-optimized

- Tap targets ≥ 44×44px
- Swipe pra arquivar/deletar thread
- Long-press = menu de contexto da mensagem

### J4 — Mobile keyboard

- Auto-resize textarea respeita keyboard visível
- Send button maior em mobile
- "Done" button no iOS keyboard

**Arquivos críticos:** `chat/components/layout/sidebar.tsx`, `chat/public/manifest.json` (novo), `chat/public/service-worker.js` (novo), `chat/app/layout.tsx` (link manifest), `chat/components/chat/chat-input.tsx`

---

## BLOCO K — Live Metrics Dashboard

**Contexto.** Backend tem `VectoraTracer` + `/metrics`. Frontend não usa.

### K1 — Floating metrics widget

- Bottom-right corner, colapsado por default
- Expande: latência por nó atual, tokens (in/out), tool_calls do turno,
  hit rate RAG da sessão
- Lê `UIMetricsEvent` do SSE stream

### K2 — Per-message metric badges

- Ao final de cada AI message: badges discretos
  `⏱ 2.3s · 🪙 1.4k in / 320 out · 🛠 3 tools · 📚 2 RAG hits`

### K3 — Session totals

- Header pequeno do topo: `Tokens nesta sessão: 12.4k · ~$0.04`
- Estimativa de custo via `MODELS[id].pricing` (novo campo)

### K4 — Graph visualization (avançado)

- Aba "Graph" tab no header (escondida em mobile)
- Embeda `@xyflow/react` com topologia do grafo
- Highlight do nó ativo em tempo real (extrai `langgraph_node` do metadata)
- Per-node duration overlay

**Arquivos críticos:** `chat/components/chat/features/metrics-widget.tsx` (novo), `chat/lib/stores/metrics-store.ts` (novo Zustand), `chat/components/chat/features/graph-view.tsx` (novo, depende de `@xyflow/react`), `chat/lib/config/deployment-config.ts` (pricing field)

---

## BLOCO L — Settings Architecture [CONCLUÍDO]

**Contexto.** O `AgentSettings` atual tem Agent Type e Recursion Limit (itens
a remover) e o Model Selector (que já existe no chat input). O componente
ficou vazio de propósito. Em paralelo, o UserMenu tem "Configurações" como
botão morto (TODO). Este bloco define onde cada coisa vive — a arquitetura
de settings que N (memória) e O (integrações) precisam para existir.

### Arquitetura de Settings

```
⚙️ Header → "Chat Settings" (escopo: sessão/chat atual)
  ┌────────────────────────────────────┐
  │ Chat Settings                      │
  ├────────────────────────────────────┤
  │ FERRAMENTAS                        │
  │  □ Mostrar tool calls no chat      │
  │  □ Confirmar ações destrutivas     │
  │    (filesystem, terminal, RAG)     │
  │                                    │
  │ RESPOSTA                           │
  │  ○ Concisa  ● Normal  ○ Detalhada  │
  │                                    │
  │ ──────────────────────────────     │
  │ ⌨ Atalhos de teclado               │
  └────────────────────────────────────┘

Avatar → Configurações → Settings Dialog (escopo: usuário)
  Abas: [Conta] [Memória] [Integrações] [Envs] [Preferências]
  [Root/Admin] + aba [Administração]

  Conta:        email atual, botão mudar senha
  Memória:      lista de memórias salvas (N1) — placeholder inicialmente
  Integrações:  GitHub, OpenAI, Anthropic, etc. (O1) — placeholder inicialmente
  Envs:         tabela de env var overrides do user (C10)
  Preferências: tema (dark/light), limite de histórico, idioma
  Administração (root/admin):
    - Controle global de agents/tools habilitados
    - RBAC/ABAC por usuário (quais workspaces acessa, nível de permissão)
    - Métricas de uso por usuário
    - Configurações globais do servidor
```

### L1 — Redesign do Agent Settings → "Chat Settings"

**Remover:** Agent Type, Recursion Limit
**Adicionar:**

- Toggle "Mostrar tool calls" (persiste por user em localStorage)
- Toggle "Confirmar ações destrutivas" (HITL E4 antecipado como toggle simples)
- Selector verbosity: Concisa / Normal / Detalhada (persiste por user)
  **Manter:** View Keyboard Shortcuts

Arquivo: `chat/components/layout/agent-settings.tsx` (modificar)
Store: `chat/lib/stores/settings-store.ts` (novo Zustand, persiste por user_id)

### L2 — Settings Dialog completo (UserMenu → Configurações)

Novo módulo `chat/components/layout/settings-dialog/`:

```
settings-dialog/
├── index.tsx           (Dialog raiz com tabs, abre do UserMenu)
├── tabs/
│   ├── conta-tab.tsx   (email, change password)
│   ├── memoria-tab.tsx (placeholder → N2 depois)
│   ├── integracoes-tab.tsx (placeholder com cards → O depois)
│   ├── envs-tab.tsx    (C10 — env vars por user)
│   └── preferencias-tab.tsx (tema, histórico limit)
└── admin/
    └── admin-tab.tsx   (root/admin only — P1 depois)
```

UserMenu: o botão "Configurações" abre este dialog.
Zustand: `chat/lib/stores/settings-store.ts` — persiste `{ showToolCalls, requireHitl, verbosity, historyLimit, theme }` no localStorage **prefixado por user_id**.

### L3 — Tema (dark/light/system)

- Toggle no tab Preferências
- `chat/components/providers/theme-provider.tsx` (novo)
- Persiste em `localStorage["theme-{user_id}"]`

### L4 — System prompt custom (Preferências avançadas)

- Campo textarea "Instrução personalizada" → prefixado ao system prompt
- Persistido por user em `~/.vectora/config.toml` via endpoint `PATCH /auth/preferences`

**Arquivos críticos:**

- `chat/components/layout/agent-settings.tsx` — simplificar para Chat Settings
- `chat/components/layout/user-menu.tsx` — ligar "Configurações" ao novo dialog
- `chat/components/layout/settings-dialog/` — novo módulo completo
- `chat/lib/stores/settings-store.ts` — novo Zustand store
- `chat/components/providers/theme-provider.tsx` — novo

**Verificação:**

- ⚙️ abre "Chat Settings" sem Agent Type/Recursion Limit; toggles funcionam
- Avatar → Configurações abre dialog com abas; aba Conta mostra email do user
- Aba Preferências: toggle tema dark→light funciona imediatamente
- Aba Envs: add/edit/delete env vars do user (testar com `GH_TOKEN`)
- Aba Memória: mostra placeholder "Em breve" (N2)
- Aba Integrações: mostra cards placeholder (O)
- Root: aba Administração aparece; non-root: aba não aparece

---

## BLOCO M — Performance, UX Polish & i18n/L10n [CONCLUÍDO parcial — i18n em andamento]

### ── M1–M5: Performance & UX Polish [CONCLUÍDO] ──────────────────────────────

**Objetivo:** Garantir fluidez visual e responsividade da interface independente do volume de mensagens e velocidade de streaming.

### M1 — Virtualização de threads longas

- `@tanstack/react-virtual` v3 integrado em `chat/components/chat/message-list.tsx`
- Ativa somente acima de 50 mensagens (`VIRTUALIZE_THRESHOLD = 50`) — abaixo disso, renderização direta é igualmente rápida e mais simples
- `measureElement` via ResizeObserver mede alturas reais incluindo conteúdo de streaming: sem jitter de scroll com mensagens que crescem dinamicamente
- `overscan: 4` pré-renderiza itens fora da viewport para rolagem suave
- Scroll para último item: `virtualizer.scrollToIndex(messages.length - 1, { align: "end" })`
- Posicionamento: `position: absolute + transform: translateY(${vItem.start}px)` por item

### M2 — Token-by-token rendering smoothness

- `requestAnimationFrame` batching em `chat/lib/hooks/chat/use-stream-handler.ts`
- Tokens chegam em alta frequência (Gemini Flash pode gerar >200 tokens/s) → acumulados em `pendingTokenBatch: string`
- `scheduleTokenFlush()` agenda um único `setMessages` por frame (~60fps máximo), eliminando layout thrashing
- `flushNow()` chamado imediatamente antes de eventos não-token (tool calls, node events, HITL, erros) para garantir ordenação correta do conteúdo
- Implementado tanto em `processStream` quanto em `processResume`

### M3 — Auto-scroll inteligente

- `shouldAutoScrollRef` rastreia intenção do usuário: `true` quando na base da conversa, `false` quando scrollou para cima
- Detecção de scroll manual: `currentScrollTop < lastScrollTopRef.current` → cancela auto-scroll imediatamente
- Botão flutuante "Voltar ao fim" (`ArrowDown`) aparece quando `showScrollButton === true`, com animação `slideInButton`
- Lógica de carga inicial: `MutationObserver` + polling periódico (100ms) garantem scroll até o fim mesmo enquanto imagens e blocos de código renderizam e mudam a altura da página
- Estabilização: verifica se `scrollHeight` se manteve igual por 5 iterações consecutivas antes de encerrar o auto-scroll inicial

### M4 — Loading skeletons

- Novo componente `chat/components/chat/message-skeleton.tsx`: 6 mensagens alternadas (user/assistant) com `animate-pulse`, simulando uma thread real durante carregamento
- Sidebar: 5 skeleton rows com opacidade gradual (`opacity: 1 - i * 0.12`) substituíram o spinner — sem reflow ao carregar threads
- `ToolCallRenderer`: pulse animation (`h-2.5 rounded-full bg-muted/70 animate-pulse`) enquanto `tool.output == null && isStreaming` — o usuário vê que a tool está em execução mesmo antes do resultado chegar

### M5 — Optimistic UI + retry em erros

- Campo `isError?: boolean` adicionado ao tipo `Message` em `chat/lib/types/messages.ts`
- No `catch` do stream em `chat-interface.tsx`: a mensagem de erro é marcada com `isError = true`
- `MessageItem` renderiza botão "Tentar novamente" (`RefreshCw`) quando `message.isError && onRetry`; o botão dispara `handleRegenerate` para reenviar a última mensagem do usuário
- Props `onRetry` e `isLoadingThread` propagados: `ChatInterface → MessageList → MessageItem`

---

### ── M6–M10: i18n / L10n [EM ANDAMENTO] ───────────────────────────────────────

**Objetivo:** Internacionalizar toda a interface do chat sem dependências externas. Strings em CSV com colunas por idioma — adicionar idioma = adicionar coluna. Inglês como fallback universal.

**Idiomas suportados inicialmente:** English (`en`), Español (`es`), Português Brasil (`pt-BR`)

### M6 — Infraestrutura de traduções (CSV-driven, zero deps)

**Formato:** CSV com colunas `key,en,es,pt-BR` em `chat/lib/i18n/strings.csv.ts`

- Arquivo `.ts` com template literal no formato CSV — sem necessidade de webpack loader nem build step
- Comentários com `#` para separar seções (filtrados no parser)
- Interpolação simples via `{varName}`: `t('time.minutes_ago', { n: 5 })` → `"5 min ago"` / `"hace 5 min"` / `"há 5 min"`
- Para adicionar idioma: adicionar coluna no CSV + atualizar o tipo `Lang`

**Parser** em `chat/lib/i18n/index.tsx`:

- Parser CSV próprio (20 linhas) — lida com valores entre aspas duplas contendo vírgulas
- Executa uma única vez no carregamento do módulo → resultado cacheado como constante `TRANSLATIONS`
- Fallback: `entry[language] ?? entry["en"] ?? key` — nunca quebra com chave inexistente

**Hook `useT()`:**

```ts
const t = useT();
t("header.new_chat"); // → "New Chat" / "Nuevo Chat" / "Novo Chat"
t("time.minutes_ago", { n: 5 }); // → "5 min ago" / "hace 5 min" / "há 5 min"
```

- Subscreve seletivamente ao campo `language` do settings-store: `useSettingsStore(s => s.language)`
- `useCallback([language])` → memoizado, re-cria apenas ao trocar idioma

**`I18nProvider`** em `chat/app/layout.tsx`:

- Atualiza `document.documentElement.lang` via `useEffect` ao trocar idioma
- Sem Context overhead — `useT()` lê diretamente do Zustand store

### M7 — Preferência de idioma no settings-store

Extensão de `chat/lib/stores/settings-store.ts`:

- Campo `language: Lang` — default calculado via `detectLanguage()`:
  1. `localStorage["vectora-settings-*"]` (persistido entre sessões)
  2. `navigator.language` → mapeado para `en`/`es`/`pt-BR`
  3. Fallback: `"en"`
- Persiste junto com as demais preferências por usuário (`partialize` atualizado)
- Ação `setLanguage(v: Lang)` adicionada

### M8 — Seletor de idioma na aba Preferências

Em `chat/components/layout/settings-dialog/tabs/preferencias-tab.tsx`:

- Select com 3 opções: `English`, `Español`, `Português (BR)`
- Labels dos idiomas sempre no próprio idioma (universalmente reconhecíveis)
- Troca instantânea: toda a UI re-renderiza em ≤1 frame pois `useT()` está subscrito ao store

### M9 — Migração dos componentes para `useT()`

~15 arquivos atualizados para usar `useT()` em vez de strings hardcoded:

| Componente                                                    | Strings migradas                                                      |
| ------------------------------------------------------------- | --------------------------------------------------------------------- |
| `components/layout/header.tsx`                                | New Chat, Vectora                                                     |
| `components/layout/sidebar.tsx`                               | Threads, Search, grupos temporais, relative time, empty states, links |
| `components/layout/user-menu.tsx`                             | Menu do usuário, Configurações, Sair                                  |
| `components/layout/agent-settings.tsx`                        | Todas as labels de configuração do chat                               |
| `components/layout/settings-dialog/index.tsx`                 | Título, todas as abas                                                 |
| `components/layout/settings-dialog/tabs/conta-tab.tsx`        | Segurança, roles, labels                                              |
| `components/layout/settings-dialog/tabs/preferencias-tab.tsx` | Todas as labels + seletor de idioma                                   |
| `components/layout/keyboard-shortcuts-dialog.tsx`             | Título                                                                |
| `components/chat/chat-input.tsx`                              | Placeholders, botões Stop/Attach, hints                               |
| `components/chat/message-item.tsx`                            | Copy, Regenerate, Good/Bad, Feedback, Retry, Thinking                 |
| `components/chat/message-list.tsx`                            | Voltar ao fim                                                         |
| `components/chat/features/welcome-screen.tsx`                 | Título principal, placeholder                                         |
| `components/chat/features/hitl-panel.tsx`                     | Aprovar, Editar, Rejeitar, todos labels                               |
| `components/chat/features/voice-input-button.tsx`             | Tooltips                                                              |
| `components/chat/chat-interface.tsx`                          | Mensagens de erro expostas ao usuário                                 |

**Padrão de migração (exemplo):**

```tsx
// Antes (hardcoded PT-BR ou EN misto)
<Button>Tentar novamente</Button>;

// Depois
const t = useT();
<Button>{t("message.retry")}</Button>;
```

**Relative time em `sidebar.tsx`:** `getRelativeTime()` recebe `t` como parâmetro → chamado com `t` do hook dentro do componente. Sem perda de memoização.

### M10 — Cobertura de strings (~185 keys)

O CSV cobre todas as seções da UI:

- Layout & navegação (header, sidebar, user-menu)
- Relative time (just now, minutes, hours, days, weeks, months)
- Chat input (placeholders, botões, hints de teclado)
- Mensagens (copy, regenerate, feedback, retry, thinking, subagent)
- Tool calls (executando…)
- Scroll (voltar ao fim)
- Chat settings (modelo, verbosidade, ferramentas)
- Settings dialog (todas as abas)
- Conta (roles, segurança)
- Preferências (tema, limite, instrução personalizada, idioma)
- HITL panel (aprovar, editar, rejeitar)
- Autenticação (loading)
- Atalhos de teclado

**Arquivos críticos (i18n):**

- `chat/lib/i18n/strings.csv.ts` — CSV com ~185 chaves × 3 idiomas (NOVO)
- `chat/lib/i18n/index.tsx` — parser, `I18nProvider`, `useT()` hook (NOVO)
- `chat/lib/stores/settings-store.ts` — campo `language: Lang` + `setLanguage()`
- `chat/app/layout.tsx` — adicionar `<I18nProvider />`
- `chat/components/layout/settings-dialog/tabs/preferencias-tab.tsx` — seletor de idioma
- ~14 componentes adicionais — `useT()` em vez de strings hardcoded

---

## BLOCO N — Per-User Memory

**Contexto.** O Vectora Agent tem hoje apenas memória global (`memory` tool).
Em contexto corporativo multi-usuário, as memórias precisam ser escopadas por
usuário — o agente aprende sobre Bruno, sobre Maria — e nunca vazar entre eles.
O usuário também precisa poder auditar e editar o que o agente sabe sobre ele.

### N1 — Backend: memória isolada por usuário

- `vectora/tools/memory.py`: todas as operações de memória usam
  `namespace = f"user:{user_id}"` quando rodando com usuário autenticado
  (fallback para namespace global quando CLI local sem auth)
- `vectora/api/handlers/memory.py` (novo): endpoints REST
  - `GET /memory` → lista memórias do user atual (paginado)
  - `DELETE /memory/{memory_id}` → deleta memória específica
  - `PUT /memory/{memory_id}` → edita conteúdo de uma memória
  - `DELETE /memory` → limpa todas as memórias do user
- `vectora/api/server.py`: registrar router
- Middleware de auth já injeta `request.state.user` → handlers usam `user.id`

### N2 — Frontend: aba Memória no Settings Dialog

- `chat/components/layout/settings-dialog/tabs/memoria-tab.tsx`:
  - Lista de memórias do user (fetch `GET /api/memory`)
  - Cada memória: texto truncado + data + botão Editar + botão Deletar
  - Botão "Limpar toda memória" (com confirmação)
  - Inline editor ao clicar Editar (textarea + salvar/cancelar)
  - Empty state: "O Vectora ainda não salvou memórias sobre você"
- Hono proxy: `chat/server/routes/memory.ts` (novo)
- `GET /api/memory` etc. forwarded para `VECTORA_API_URL/memory`

### N3 — Indicador de contexto no chat

- Integrado com HITL (Bloco E) — quando agente carrega memórias na chain,
  emite `NodeEvent` com `node="memory_load"` e `metadata.memories_loaded=N`
- Chat mostra badge discreto "🧠 N memórias carregadas" por mensagem
- Clicável → expande lista das memórias usadas naquela resposta

**Arquivos críticos:**

- `vectora/tools/memory.py` — adicionar `user_id` no namespace
- `vectora/api/handlers/memory.py` — novo router
- `chat/server/routes/memory.ts` — novo proxy Hono
- `chat/components/layout/settings-dialog/tabs/memoria-tab.tsx` — novo
- `chat/components/chat/message-item.tsx` — badge de memórias (N3)

---

## BLOCO O — Workspace Integrations (OAuth + API Keys)

**Contexto.** Vectora é self-hosted e multi-usuário. Cada developer precisa
usar suas próprias credenciais (GitHub token, OpenAI key etc.) sem compartilhar
com o admin ou outros usuários. As API keys ficam no vault KeePassXC do user
(C11). OAuth (GitHub) permite fluxo de autenticação delegada, sem o user
precisar criar e gerenciar tokens manualmente.

### O1 — API Key integrations (simples — apenas API key)

Integrações sem OAuth — user insere a chave, fica no vault KeePass dele.
O agente usa `user.env_overrides` (C10) que já é mergeado no `effective_env`.

| Integração  | Env var               | Onde usar no agente                   |
| ----------- | --------------------- | ------------------------------------- |
| OpenAI      | `OPENAI_API_KEY`      | LLM (GPT-4.x, o3/o4) + embeddings     |
| Anthropic   | `ANTHROPIC_API_KEY`   | LLM (Claude 4.x)                      |
| Cohere      | `COHERE_API_KEY`      | Reranker + LLM (Command)              |
| Tavily      | `TAVILY_API_KEY`      | Web search tool                       |
| Groq        | `GROQ_API_KEY`        | LLM ultrafast (Llama, Mixtral)        |
| HuggingFace | `HUGGINGFACE_API_KEY` | Modelos open source via Inference API |
| Perplexity  | `PERPLEXITY_API_KEY`  | Busca com citações                    |

**UI** (aba Integrações no Settings Dialog):

- Cards por integração: logo + nome + status (✓ Conectado / − Não configurado)
- Click → inline form: input de API key (masked) + botão Salvar/Remover
- Key é salva via `POST /api/auth/envs` (endpoint C10 já existe) com a env var correta
- "Verificar" button: faz chamada de teste (ex: `GET /v1/models` na OpenAI) e mostra ✓/✗

### O2 — GitHub OAuth

**Modelo:** Vectora é registrado como GitHub OAuth App (não GitHub App).
Mais simples que GitHub App — não requer instalação no repositório.

**Fluxo:**

1. User clica "Conectar GitHub" na aba Integrações
2. Redirect para `https://github.com/login/oauth/authorize?client_id=...&scope=repo,user`
3. GitHub redireciona para `vectora server: /auth/github/callback?code=...`
4. Backend troca `code` por `access_token` (POST para GitHub)
5. Token armazenado no KeePass vault do user como `GITHUB_TOKEN`
6. Tools `git_push`, `gh_pr_create` etc. (G3) usam `user.env_overrides["GITHUB_TOKEN"]`

**Backend** (`vectora/api/handlers/oauth.py` novo):

- `GET /auth/github` → redirect para GitHub OAuth
- `GET /auth/github/callback` → troca code por token, salva no vault, redirect chat
- `DELETE /auth/github` → revoga e remove token
- `GET /auth/github/status` → `{connected: bool, username: str | None}`

**Configuração** (`~/.vectora/config.toml`):

```toml
[integrations.github]
client_id = "..."
client_secret = "..."   # armazenado em system.kdbx (root)
redirect_uri = "http://localhost:8080/auth/github/callback"
```

**Frontend:**

- Card GitHub: status badge + botão "Conectar" (redirect) ou "Desconectar"
- Após OAuth: mostra avatar + username do GitHub conectado
- `chat/server/routes/oauth.ts` (novo): proxy para endpoints OAuth

### O3 — Google OAuth (futuramente)

Mesmo padrão de O2, mas com scopes Google Drive + Gmail.
`GOOGLE_ACCESS_TOKEN` no vault → `drive_read`, `drive_write` tools.

### O4 — Notion OAuth (futuramente)

API Token (simples, como O1) ou OAuth App.
`NOTION_API_KEY` → tool `notion_search` para RAG de knowledge bases.

### O5 — Linear OAuth (futuramente)

`LINEAR_API_KEY` (simples, como O1) → tools `linear_issue_create`, `linear_issue_list`.

**Arquivos críticos:**

- `vectora/api/handlers/oauth.py` — novo (GitHub OAuth flow)
- `vectora/services/secrets/keepass.py` — já existe, usar para armazenar tokens
- `chat/components/layout/settings-dialog/tabs/integracoes-tab.tsx` — cards com status
- `chat/server/routes/oauth.ts` — proxy Hono para OAuth endpoints
- `vectora/tools/git.py`, `vectora/tools/gh.py` — já planejados em G3

**Verificação O1:**

- User insere `OPENAI_API_KEY` → salvo via `/api/auth/envs` → chat usa GPT-4.x com tokens do user
- User B não vê key do User A (isolamento via vault)
- Root não tem o token do user: `GET /auth/envs` de outro user retorna 403

**Verificação O2:**

- Fresh install, registrar Vectora como GitHub OAuth App no github.com/settings/developers
- Click "Conectar GitHub" → redirect para GitHub → authorize → retorna ao chat com status "Conectado como @brunosrz"
- Pedir pro agente fazer um commit → usa GITHUB_TOKEN do user → PR criado no name dele

---

## BLOCO P — Root Admin Panel (RBAC/ABAC Global)

**Contexto.** O root do Vectora precisa de uma visão administrativa para
gerenciar quem acessa o quê. Isso vai além das permissões básicas do Bloco C
(roles) — permite controle fino de quais agents/tools cada user pode usar,
quais workspaces acessa e com que nível.

### P1 — Aba Administração no Settings Dialog (root/admin only)

Sub-abas dentro de Administração:

**Usuários:**

- Tabela: email | role | último acesso | status
- Click → drawer com detalhes: mudar role, resetar senha, ver workspaces, ver envs (masked)
- Botão "Convidar usuário" → gera link de signup válido por 24h

**Agents & Tools:**

- Checklist de agents disponíveis: quais estão habilitados globalmente
- Por agent: quais tools estão habilitadas
- ABAC: override por usuário ("User X não pode usar terminal")
- Persistido em `~/.vectora/config.toml` → lido pelo `vectora/graph.py` ao buildar graph

**Workspaces:**

- Lista de todos os workspaces no servidor
- Assign: `user_id → workspace_id → role` (owner, writer, reader)
- Tabela: Workspace | Usuários com acesso | Tools liberadas

**Sistema:**

- Versão do Vectora Agent + chat
- Status dos serviços (LanceDB, SQLite, MCP servers ativos)
- Métricas de uso: requests/min, tokens/user/day, top tools usadas
- Configurações globais: `allow_public_signup`, `default_model`, `max_recursion`

### P2 — Backend: endpoints de admin

- `GET /admin/users` → lista usuários com stats (já existe como `GET /auth/users`)
- `POST /admin/users/{id}/tools` → override de tools por user
- `GET /admin/workspaces` → todos os workspaces com assignees
- `POST /admin/workspaces/{id}/assign` → atribuir user a workspace
- `GET /admin/system` → versão, health, métricas
- `PATCH /admin/config` → atualizar `allow_public_signup`, `default_model` etc.

**Arquivos críticos:**

- `chat/components/layout/settings-dialog/admin/admin-tab.tsx` — novo
- `chat/components/layout/settings-dialog/admin/users-panel.tsx` — novo
- `chat/components/layout/settings-dialog/admin/tools-panel.tsx` — novo
- `vectora/api/handlers/admin.py` — novo router (todos os endpoints exigem root/admin)
- `vectora/services/permissions.py` — ampliar com `can_override_tools(user, target_user_id)`

---

## BLOCO Q — Workspace P2 + Auth Onboarding: Trust Folder, Scope Guard Rails, Worktree & Invites

> **Contexto.** A seleção de workspace **não funciona hoje**. O frontend tem
> `workspaces-store.ts` e a rota Hono `chat/server/routes/workspaces.ts`, mas
> elas dão proxy para `/vectora.workspace.v1.WorkspaceService/*` — endpoints
> que **não existem no backend** (`vectora/api/handlers/` não tem
> `workspaces.py`). Não há componente de seleção (`workspace-selector.tsx`
> ausente). E o conceito de "workspace" na prática é apenas o `cwd` do processo
> onde o `vectora` foi iniciado.
>
> Pior: os **guard rails de escopo são fracos**. `vectora/tools/fs.py` usa
> `is_safe_file_path(path, allowed_dirs=["."])` — onde `.` é o cwd do
> _processo_, não a pasta escolhida — e a tool `terminal` roda
> `asyncio.create_subprocess_shell(command)` **sem `cwd=`**, herdando o
> diretório do servidor sem nenhuma confinação. Não há `git_init` nem
> `git_worktree` em `vectora/tools/git.py` (G8 nunca foi implementado de fato).
>
> **Objetivo do Bloco Q:** transformar workspace num conceito de primeira classe
> com o modelo _trust folder_ (como editores/IDEs modernos): o usuário escolhe
> uma pasta, ela é apresentada como pasta confiável, e **a partir daí o Vectora
> só pode ler/escrever/rodar comandos/usar git dentro dela** (guard rails de
> escopo reais). Se a pasta não for um repositório git, oferece `git init`.
> Isso é o que torna seguro o Vectora editar arquivos e rodar comandos. Inclui
> worktrees para features paralelas.
>
> **Adendo (auth onboarding).** Em uso real, a tela de login expõe "Criar conta"
> mesmo quando já existe usuário, e o primeiro acesso cai no login em vez de ir
> direto ao setup do root. O backend já fecha o signup público
> (`/auth/signup` → 403 após o 1º usuário), mas o frontend não roteia
> corretamente e **não há sistema de convites** (o Bloco P1 planejou "Convidar
> usuário" mas nunca implementou). Q7–Q8 fecham esse gap: roteamento de
> onboarding correto + signup por convite com token expirável emitido por
> root/admin.

### Q1 — `WorkspaceService` backend (o handler que falta)

Novo `vectora/api/handlers/workspaces.py` + registro em `vectora/api/server.py`
(`app.include_router(workspace_router)`), espelhando os paths que o frontend já
chama (Connect-style POST/GET sob `/vectora.workspace.v1.WorkspaceService/`):

| Endpoint                    | Ação                                                                         |
| --------------------------- | ---------------------------------------------------------------------------- |
| `GET  …/ListWorkspaces`     | lista todos os workspaces do registry (escopado por user quando autenticado) |
| `GET  …/GetActiveWorkspace` | workspace ativo da sessão atual                                              |
| `POST …/SetActiveWorkspace` | troca o workspace ativo `{workspace_id}`                                     |
| `POST …/CreateWorkspace`    | registra pasta `{path, trust: bool, git_init: bool}`                         |
| `POST …/TrustWorkspace`     | marca workspace como confiável `{workspace_id}`                              |
| `POST …/GitInitWorkspace`   | roda `git init` na pasta `{workspace_id}`                                    |
| `GET  …/BrowseDir`          | **directory browser** (Q6): lista subpastas de `{path}`                      |

Reusa o `workspace_registry` singleton (`vectora/services/workspace.py`) e
`detect_git_info()` (`vectora/tools/git.py:593`). Auth: `Depends(get_current_user)`
no modo server; root local no CLI (C6).

### Q2 — Estado de "trust" no modelo Workspace

Estende `vectora/types/workspace.py` (`Workspace` Pydantic) com:

- `trusted: bool = False` — pasta confirmada como confiável pelo usuário
- `trusted_at: str | None` — timestamp ISO da confirmação
- `trusted_by: str | None` — user_id que confiou (multi-tenant)

`WorkspaceRegistry` ganha `trust(workspace_id, user_id)` + persistência no
`~/.vectora/workspaces.json`. **Regra cardinal:** tools de escrita/terminal/git
só executam em workspace `trusted=True`. Workspace não-confiável → modo
read-only (somente `file_read`, `grep`, `list`).

### Q3 — `git init` automático para pastas sem repositório

- Nova helper `git_init_repo(cwd) -> dict` em `vectora/tools/git.py` (usa
  `git.Repo.init(cwd)`), e tool `git_init` exposta ao agente
  (render_hint `code_block`, destructive `false`).
- No fluxo de criação de workspace (Q1 `CreateWorkspace` com `git_init=True`):
  se `detect_git_info()` retorna `is_git_repo=False`, roda `git init` e
  re-detecta. Atualiza `is_git_repo`/`git_current_branch` no registry.
- UI (Q6) mostra: "Esta pasta não é um repositório git. Inicializar?" no
  momento do trust.

### Q4 — Scope Guard Rails (confinação real ao workspace ativo)

O coração da segurança. Hoje `allowed_dirs=["."]` e terminal sem `cwd`. Mudar para:

- **Novo helper central** em `vectora/services/security.py`:
  `resolve_within_workspace(path, workspace_root) -> Path | None` — resolve o
  path absoluto e garante `resolved.is_relative_to(workspace_root)`; retorna
  `None` se escapar (bloqueia `..`, symlinks para fora, paths absolutos
  externos). Substitui o atual `allowed_dirs=["."]`.
- **`vectora/tools/fs.py`**: `file_read`, `file_write`, `file_edit`, `grep`,
  `list`, `terminal` passam a resolver o workspace ativo via config
  (`configurable.workspace_id` → `workspace.cwd`, mesmo padrão de
  `_resolve_workspace` em `git.py:35`) e validar contra `workspace_root`.
- **`terminal`**: `create_subprocess_shell(command, cwd=workspace_root, …)` —
  comandos rodam **dentro** da pasta. Mantém a blacklist atual
  (`is_safe_shell_command`).
- Workspace não-`trusted` → tools destrutivas retornam erro pedindo trust.
- Mensagem de erro clara quando um path escapa: `"Path fora do workspace
'{root}'. O Vectora só pode acessar arquivos dentro da pasta confiável."`

### Q5 — Git Worktree (G8 real)

- Helpers + tool `git_worktree(action, name?, branch?)` em
  `vectora/tools/git.py` (`add`/`list`/`remove`); worktrees em
  `~/.vectora/worktrees/<workspace_id>/<name>` (via `git worktree add`).
- `thread.metadata.worktree` associa thread ↔ worktree; quando setado, as
  tools de Q4 confinam ao path da worktree em vez do root principal.
- Endpoint `…/ListWorktrees` + `…/CreateWorktree` no WorkspaceService (Q1).

### Q6 — Workspace selector + trust UI (frontend)

- **Novo** `chat/components/layout/workspace-selector.tsx` — o chip de pasta
  (espelha o chip `vectora` da print 1), à esquerda no header. Dropdown:
  lista de workspaces + "Adicionar pasta…".
- **Novo** `chat/components/layout/workspace-trust-dialog.tsx` — fluxo trust
  folder: directory browser (consome `…/BrowseDir`), confirmação "Confio nesta
  pasta" (explica os guard rails), checkbox "Inicializar git se necessário".
- **Novo** `chat/server/routes/` já tem `workspaces.ts` — estender com
  `/browse`, `/create`, `/trust`, `/git-init`, `/worktrees`.
- `workspaces-store.ts` ganha `trusted` no `WorkspaceInfo` + ações
  `trust()`, `create()`, `browse()`.
- Hidrata o store no boot (`chat/app/page.tsx` / provider) e seta
  `agentConfig.workspace_id` na request (já consumido em
  `chat/lib/...` → `chat.py:242`).

### Q7 — Onboarding de auth: roteamento de primeiro acesso & signup público fechado

Corrige o fluxo de entrada **sem novo backend** (reusa `GET /auth/has-users`,
que já existe e retorna `HasUsersResponse(exists)`).

- **`chat/components/providers/auth-provider.tsx`**: quando não autenticado,
  antes de redirecionar para `/auth/signin`, consultar `GET /api/auth/has-users`.
  Se `exists=false` → `router.replace("/auth/signup")` (setup do root). Se
  `exists=true` → `router.replace("/auth/signin?from=…")` (comportamento atual).
- **`chat/app/auth/signin/page.tsx`**: **remover** o link incondicional
  "Primeiro acesso? Criar conta". No mount, checar `has-users`; se `false`,
  redirecionar para `/auth/signup`. Com usuários existentes, a tela de login
  nunca oferece criação pública.
- **`chat/app/auth/signup/page.tsx`**: manter o redirect para signin quando
  `has-users=true` **e** não houver convite válido (ver Q8). Sem convite,
  signup só é permitido no primeiro acesso.
- **i18n**: rever strings de auth em `chat/lib/i18n/strings.csv.ts` — remover/
  ajustar a chave do link "criar conta"; adicionar texto de setup do root.

### Q8 — Signup por convite (link com token)

Implementa o "Convidar usuário" do P1 (nunca construído). Token opaco expirável,
no padrão dos `refresh_tokens` (hash SHA-256 no DB, nunca em claro).

**Backend — `vectora/services/auth.py`:**

- Nova tabela `invites(token_hash PK, email, role, created_by, expires_at,
used_at, created_at)` em `_ensure_schema()`.
- `create_invite(created_by, role="member", email=None, ttl_hours=24) -> str`
  (gera token via `secrets.token_hex`, persiste hash; reusa `_hash_refresh_token`
  ou novo `_hash_token`).
- `validate_invite(token) -> dict | None` (não usado, não expirado; retorna
  role/email).
- `consume_invite(token, user_id)` (seta `used_at`; idempotente/atômico).
- `list_invites()` / `revoke_invite(token)` para o painel admin.
- `signup(email, password, *, role=None)`: aceitar `role` opcional (quando vindo
  de convite), mantendo a regra "1º usuário = root".

**Backend — `vectora/api/handlers/auth.py` + `vectora/api/schemas.py`:**

- `SignupRequest` ganha `invite_token: str = ""`.
- `signup_endpoint`: lógica em camadas —
  (1) `has_users()==False` → permite (root, como hoje);
  (2) `invite_token` válido → permite com a role do convite e **consome** o convite;
  (3) caso contrário → 403 (como hoje).
- `GET /auth/invite/{token}` (público): valida e retorna `{valid, email?, role}`
  para a página de signup pré-preencher/verificar.

**Backend — `vectora/api/handlers/admin.py`:**

- `POST /admin/invites` (`require_admin`) → body `{role, email?, ttl_hours}` →
  retorna `{token, url, expires_at}` (URL = `<frontend>/auth/signup?invite=<token>`).
- `GET /admin/invites` (`require_admin`) → lista convites pendentes.
- `DELETE /admin/invites/{token}` (`require_admin`) → revoga.

**Frontend:**

- **`chat/app/auth/signup/page.tsx`**: ler `?invite=<token>` da URL. Se presente,
  validar via `GET /api/auth/invite/{token}`; em modo convite, **permitir** signup
  mesmo com `has-users=true`, enviar `invite_token` no POST e exibir contexto
  ("Convite para função: member"). Token inválido/expirado + usuários existentes →
  redirecionar para signin com aviso.
- **`chat/components/layout/settings-dialog/admin/users-panel.tsx`**: botão
  "Convidar usuário" → dialog (select de role + email opcional + TTL) →
  `POST /api/admin/invites` → mostra link copiável. Lista de convites pendentes
  com botão revogar.
- **Proxies Hono**: `chat/server/routes/auth.ts` (+ `GET /invite/:token`) e a rota
  admin (+ `/admin/invites` GET/POST/DELETE).
- **i18n**: novas chaves para o dialog de convite + mensagens de convite
  inválido/expirado.

### Arquivos críticos (Bloco Q)

| Sub | Arquivos chat                                                                                                                        | Arquivos vectora (Python)                                                                                                                                                                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Q1  | `chat/server/routes/workspaces.ts` (estende)                                                                                         | `vectora/api/handlers/workspaces.py` (novo), `vectora/api/server.py` (registrar)                                                                                                                       |
| Q2  | `chat/lib/stores/workspaces-store.ts` (+`trusted`)                                                                                   | `vectora/types/workspace.py`, `vectora/services/workspace.py` (`trust()`)                                                                                                                              |
| Q3  | —                                                                                                                                    | `vectora/tools/git.py` (`git_init_repo` + tool)                                                                                                                                                        |
| Q4  | —                                                                                                                                    | `vectora/services/security.py` (`resolve_within_workspace`), `vectora/tools/fs.py` (todas as tools + `terminal` com `cwd=`)                                                                            |
| Q5  | secondary worktree selector no header                                                                                                | `vectora/tools/git.py` (`git_worktree`), `vectora/state.py` (`thread.metadata.worktree`)                                                                                                               |
| Q6  | `workspace-selector.tsx`, `workspace-trust-dialog.tsx` (novos)                                                                       | `…/BrowseDir` endpoint                                                                                                                                                                                 |
| Q7  | `auth-provider.tsx`, `auth/signin/page.tsx`, `auth/signup/page.tsx`, `i18n/strings.csv.ts`                                           | — (reusa `/auth/has-users`)                                                                                                                                                                            |
| Q8  | `auth/signup/page.tsx` (modo convite), `admin/users-panel.tsx`, `server/routes/auth.ts` (+`/invite`), rota admin (+`/admin/invites`) | `services/auth.py` (tabela `invites` + funções), `api/handlers/auth.py` (+`invite_token`, `GET /auth/invite/{token}`), `api/handlers/admin.py` (+`/admin/invites`), `api/schemas.py` (+`invite_token`) |

### Verificação (Bloco Q)

- `vectora server chat` → header mostra chip da pasta; clicar → "Adicionar
  pasta" abre directory browser; navegar e selecionar pasta sem git
- Diálogo de trust explica guard rails + oferece `git init`; confirmar →
  workspace `trusted=True`, `git init` rodado, branch detectada
- Pedir ao agente "crie README.md e rode `ls`" → arquivo criado **dentro** da
  pasta, `ls` roda com `cwd` = pasta
- Pedir "leia C:\Windows\system32\drivers\etc\hosts" (fora do workspace) →
  bloqueado com mensagem de escopo
- Workspace não-confiável → tentativa de `file_write` retorna pedido de trust
- Criar worktree `feat-x` → aparece em `~/.vectora/worktrees/…`; abrir thread
  associada confina as tools à worktree
- **(Q7)** Fresh install (sem usuários) → abrir `/` redireciona **direto** para
  criar conta (setup root); a tela de login não aparece
- **(Q7)** Com usuário existente → `/` cai em login; tela de login **não** mostra
  "criar conta"
- **(Q8)** Root abre Admin → "Convidar usuário" (role member, TTL 24h) → recebe
  link copiável
- **(Q8)** Abrir o link `/auth/signup?invite=<token>` em janela anônima → cria
  conta como member; reabrir o mesmo link → recusado (consumido/expirado)
- **(Q8)** `POST /auth/signup` sem convite e com usuários existentes → 403
  (inalterado)

---

## BLOCO R — UX Polish: Command Bar, Permission Modes & Effort/Meter

> **Contexto.** Continuação direta do Bloco M (UX polish). As prints enviadas
> pelo usuário (interface do Claude Code desktop) são a **referência visual**
> para a área de input do Vectora Chat. Hoje o `chat/components/chat/chat-input.tsx`
> tem só textarea + anexo + voz + (model selector via `agent-settings`). O
> objetivo é adotar o layout da referência: uma **command bar** rica com barra
> de contexto (pasta/branch/worktree), seletor de modo de permissão, menu `+`,
> seletor de modelo+esforço e medidor de contexto/uso. Decisões confirmadas com
> o usuário: adotar os 5 modos da print; medidor reflete tokens da thread +
> rate limit do user.
>
> **Adendo (polish & i18n descoberto em uso).** Em uso real apareceram regressões
> de polish e cobertura de i18n que entram como R6–R10: várias strings estão
> **hardcoded** (welcome "What can I help with?", sidebar "Threads/Today/Search",
> header "New Chat", placeholder legado "Ask me anything about LangChain…") apesar
> das chaves já existirem em `strings.csv.ts`; **"Threads" deve virar
> "Sessions/Sessões"**; o **Chat Settings** não permite trocar tema nem idioma
> (idioma não tem seletor em lugar nenhum); o toggle **"Confirmar ações
> destrutivas" tem default inseguro `false`** (deveria ser `true`/fallback); a
> **área de input** tem fundo cinza (`bg-card`) no container e no seletor de
> modelo que o usuário quer remover; a aba **Envs** é só placeholder (apesar do
> backend `/auth/envs` + proxy Hono já existirem); e o **Modelo padrão** em Admin →
> Config é um input de texto que deveria ser o mesmo seletor de modelo do input.
> **Regra cardinal:** todo texto de UI (componentes, páginas, diálogos) passa por
> i18n — nada de string hardcoded.

### R1 — Top context bar (print 1)

Barra de chips acima do textarea, espelhando `Local · vectora · dev · worktree`:

- **`Local`** — indicador de execução (local CLI root vs server autenticado);
  lê `auth-store` (C9). Tooltip explica o perímetro.
- **Chip de pasta** — reusa `workspace-selector.tsx` (Q6).
- **Chip de branch** — reusa/eleva `git-status-badge.tsx` (G5) para um switcher
  de branch (`git_branch`/`git_checkout`).
- **Chip de worktree** — seletor de worktree (Q5).
- **Botão "novo"** — atalho para adicionar pasta (Q6).
- Componente novo: `chat/components/chat/features/command-bar.tsx`.

### R2 — Seletor de Modo de Permissão (print 2 — 5 modos)

Chip "Modo" (estilo "Ignorar permissões" amarelo) → dropdown com 5 modos,
mapeando para o HITL existente (Bloco E) + guard rails (Q4):

| Modo                     | Comportamento                                                            |
| ------------------------ | ------------------------------------------------------------------------ |
| **Solicitar permissões** | HITL em toda tool destrutiva (filesystem/terminal/git/paga)              |
| **Aceitar edições**      | auto-aprova `file_edit`/`file_write`; confirma terminal + git destrutivo |
| **Modo de planejamento** | agente planeja e propõe, **não executa** tools destrutivas (plan-only)   |
| **Modo automático**      | auto-aprova tudo **dentro** do workspace confiável (Q4 ainda confina)    |
| **Ignorar permissões**   | full-auto, sem HITL (ainda bounded pelo escopo Q4)                       |

- Persistido por user no `settings-store.ts` (campo `permissionMode`).
- Backend: enviado em `agentConfig` → `configurable.permission_mode`; consumido
  por `vectora/graph.py` (mapeia para `interrupt_before` dinâmico) e
  pelo adapter HITL (Bloco E).
- Atalho de teclado ⇧Ctrl M (registrar em `keyboard-shortcuts-dialog.tsx`).

### R3 — Menu `+` de anexos (print 3)

Substitui o botão de anexo único por um menu popover:

- **Adicionar arquivos ou fotos** (Ctrl+U) — fluxo de attach atual (Bloco F).
- **Adicionar pasta** — abre o trust dialog (Q6).
- **Comandos de barra** — abre o autocomplete de slash commands (Bloco H).
- **Conectores** → submenu (Bloco S).
- **Adicionar plugins…** → MCP servers (Bloco S).
- Componente novo: `chat/components/chat/features/plus-menu.tsx`.

### R4 — Modelos + Esforço (print 4)

Eleva o model selector atual para um dropdown duplo:

- **Modelos** (⇧Ctrl I) — quick switch (já existe em `agent-settings.tsx` /
  `deployment-config.ts`); marca o ativo.
- **Esforço** (⇧Ctrl E): Baixa / Média / Alto / Max — mapeia para
  `reasoning_effort`/thinking budget do modelo (campo novo em `agentConfig`,
  consumido em `chat.py` → `configurable`). Para modelos sem thinking, cai
  para verbosity (Bloco L).
- **Modo rápido** toggle — desliga reasoning/thinking para latência mínima.
- Persistido por thread em `agentConfig`.

### R5 — Medidor de contexto + uso do plano (print 5)

Rodapé do command bar:

- **Janela de contexto** `164.8k / 200.0k (82%)` — tokens da thread atual vs
  `MODELS[id].context_window` (campo novo em `deployment-config.ts`). Soma
  via `UIMetricsEvent`/`metrics-store` (Bloco K).
- **Uso do plano** — rate limits do usuário (Bloco C13): req/min consumidas,
  janela de reset. Endpoint `GET /auth/usage` (novo, lê o estado do
  `rate_limit` middleware).
- Status inferior: `<modelo> · <esforço>` (espelha "Sonnet 4.6 · Médio").
- Componentes: `chat/components/chat/features/context-meter.tsx` (novo),
  `chat/lib/stores/metrics-store.ts` (Bloco K, criar se ainda não existe).

### R6 — Cobertura i18n completa & rename Threads → Sessions

Todas as strings de UI passam por `useT()` (`chat/lib/i18n/index.tsx`); as chaves
**já existem** em `chat/lib/i18n/strings.csv.ts` — falta cablear os componentes.

- **`chat/components/layout/sidebar.tsx`**: maior ofensor. Substituir literais
  por `t('sidebar.title')`, `t('sidebar.search_placeholder')`,
  `t('sidebar.group.today|yesterday|last_7_days|older')`,
  `t('sidebar.new_conversation')`, `t('sidebar.no_results*')`,
  `t('sidebar.documentation*')`, `t('sidebar.feedback')`/`t('sidebar.report_issue')`.
  `getRelativeTime()` passa a retornar via `t('time.*', { n })` (recebe `t` como
  argumento ou vira hook interno).
- **`chat/components/layout/header.tsx`**: `"New Chat"` → `t('header.new_chat')`.
- **`chat/components/chat/features/welcome-screen.tsx`**: `"What can I help
with?"` → `t('welcome.title')`; placeholder → `t('input.placeholder')` /
  `t('input.initializing')`; `"Drop files here"` → `t('welcome.drop_files')`;
  tooltip de anexo → `t('input.attach_files')`; `"Stop"`/`"Stopping..."`.
- **`chat/components/chat/chat-input.tsx`**: corrigir o placeholder legado
  **`"Ask me anything about LangChain..."`** → `t('input.placeholder')`;
  `"Type your next message..."` → `t('input.loading_placeholder')`;
  `"Initializing..."`, `"Queued"`, `"Stop"`, e o help text Enter/Shift+Enter
  (`t('input.send_hint')` / `t('input.new_line_hint')`).
- **`chat/components/layout/agent-settings.tsx`**: título/descrição, labels e
  toggles → chaves `settings.chat.*`; `VERBOSITY_OPTIONS` usa
  `t('settings.chat.verbosity.*')`.
- **Rename Threads → Sessions/Sessões**: alterar os **valores** (não as chaves)
  no CSV — `sidebar.title` → `Sessions,Sesiones,Sessões`; ajustar o "thread/
  threads" remanescente em `sidebar.search_placeholder`,
  `sidebar.no_conversations_hint` e afins para "session/sessão".

### R7 — Tema & Idioma no Chat Settings + default seguro de HITL

- **`chat/components/layout/agent-settings.tsx`**: adicionar seletor de **Tema**
  (reusa `THEME_OPTIONS` + `useTheme()` do next-themes — mesmo padrão de
  `preferencias-tab.tsx:handleThemeChange`, que sincroniza `setTheme` do store +
  `setNextTheme`) e seletor de **Idioma** (reusa `SUPPORTED_LANGS` +
  `setLanguage` do `settings-store.ts`). Strings via `prefs.theme*` /
  `prefs.language*`.
- **`chat/components/layout/settings-dialog/tabs/preferencias-tab.tsx`**:
  acrescentar o seletor de **Idioma** que falta (hoje só tem Tema), para
  consistência — mesmas chaves `prefs.language*`.
- **`chat/lib/stores/settings-store.ts`**: `DEFAULTS.requireHitl: true`
  (confirmar ações destrutivas é o fallback seguro). Persistência existente
  preserva a escolha do usuário; só muda o default de instalações novas.

### R8 — Polish imediato da área de input (fundo cinza)

Correção visual independente do redesign maior de R1/R4 (que depois absorve isto).

- **`chat/components/chat/features/welcome-screen.tsx`**: remover o fundo cinza
  do container do input (`bg-card` → transparente/sutil, mantendo apenas a borda/
  ring) e garantir o seletor de modelo **sem fundo** (já `bg-transparent`; remover
  `hover:bg-muted/50` se ainda destoar).
- **`chat/components/chat/chat-input.tsx`**: aplicar a mesma limpeza
  (`bg-card/95` e camadas de `bg-card/*` → transparente/sutil) para consistência
  entre o estado welcome e o estado de conversa.

### R9 — Aba Envs funcional (backend já existe)

`envs-tab.tsx` hoje é só placeholder. Backend completo já existe:
`vectora/api/handlers/auth.py` (`GET/POST/DELETE /auth/envs`, valores mascarados)
e proxy Hono `chat/server/routes/auth.ts` (`/envs` GET/POST + `/envs/:key` DELETE).

- **`chat/components/layout/settings-dialog/tabs/envs-tab.tsx`**: construir UI —
  listar (`GET /api/auth/envs` → `{envs: masked, keys}`), adicionar via form
  key/value (`POST /api/auth/envs`), remover (`DELETE /api/auth/envs/{key}`).
  Mostra valores mascarados; labels/mensagens via i18n (novas chaves `envs.*`).

### R10 — Admin → Config: seletor de modelo padrão

- **`chat/components/layout/settings-dialog/admin/admin-tab.tsx`** (`ConfigPanel`):
  trocar o `<Input>` de texto de "Modelo padrão" pelo **mesmo `<Select>`** de
  modelo usado no `welcome-screen`/`agent-settings`, reusando `getAllowedModels()`
  e `getModelDisplayName()` (`chat/lib/config/deployment-config.ts`). Mantém o
  PATCH `/api/admin/config` (`default_model`).

> **Nota de correção ao Q8 (Bloco Q).** O painel de usuários do admin é o
> `UsersPanel` **inline** em `settings-dialog/admin/admin-tab.tsx` — não existe
> `users-panel.tsx`. O botão "Convidar usuário" (Q8) deve ser adicionado nesse
> `UsersPanel`. A funcionalidade de convite (front + back) permanece escopo do
> Bloco Q/Q8; R apenas aponta o arquivo correto.

### Arquivos críticos (Bloco R)

| Sub | Arquivos chat                                                                                                            | Arquivos vectora (Python)                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| R1  | `command-bar.tsx` (novo), `git-status-badge.tsx` (eleva p/ switcher)                                                     | —                                                                                          |
| R2  | `permission-mode-menu.tsx` (novo), `settings-store.ts` (+`permissionMode`)                                               | `vectora/graph.py` (interrupt_before dinâmico), `vectora/api/adapters.py`                  |
| R3  | `plus-menu.tsx` (novo), `chat-input.tsx` (integra)                                                                       | —                                                                                          |
| R4  | `agent-settings.tsx` (esforço/fast mode), `deployment-config.ts` (+`context_window`)                                     | `vectora/api/handlers/chat.py` (`reasoning_effort` no configurable)                        |
| R5  | `context-meter.tsx` (novo), `metrics-store.ts`                                                                           | `vectora/api/handlers/auth.py` (`GET /auth/usage`), `vectora/api/middleware/rate_limit.py` |
| R6  | `sidebar.tsx`, `header.tsx`, `welcome-screen.tsx`, `chat-input.tsx`, `agent-settings.tsx`, `i18n/strings.csv.ts`         | —                                                                                          |
| R7  | `agent-settings.tsx` (tema+idioma), `preferencias-tab.tsx` (+idioma), `settings-store.ts` (`requireHitl` default `true`) | —                                                                                          |
| R8  | `welcome-screen.tsx`, `chat-input.tsx` (remover `bg-card`)                                                               | —                                                                                          |
| R9  | `settings-dialog/tabs/envs-tab.tsx` (UI add/list/delete)                                                                 | — (backend `/auth/envs` + proxy Hono já existem)                                           |
| R10 | `settings-dialog/admin/admin-tab.tsx` (`ConfigPanel` → model `<Select>`), `deployment-config.ts` (reuso)                 | —                                                                                          |

### Verificação (Bloco R)

- Command bar mostra `Local · <pasta> · <branch> · <worktree>` e atualiza ao
  trocar workspace/branch
- Trocar modo para "Modo de planejamento" → agente propõe mas não executa
  terminal; "Solicitar permissões" → HITL aparece antes de `file_write`
- Menu `+` abre com 5 itens; "Adicionar pasta" abre trust dialog (Q6)
- Trocar Esforço para "Alto" → próxima resposta usa mais thinking; "Modo
  rápido" → resposta sem reasoning
- Medidor mostra tokens da thread crescendo e % da janela; painel de uso mostra
  rate limit do user com tempo de reset
- **(R6)** Trocar idioma para EN/ES/PT → sidebar (título "Sessions/Sessões",
  busca, grupos "Today/Hoje", tempos relativos), header ("New Chat"), welcome
  ("What can I help with?") e Chat Settings traduzem **sem** strings hardcoded;
  o placeholder legado "Ask me anything about LangChain…" some
- **(R7)** Chat Settings permite trocar **Tema** (claro/escuro/sistema) e
  **Idioma** e o efeito é imediato; instalação nova já vem com "Confirmar ações
  destrutivas" **ligado**
- **(R8)** Área de input (welcome e conversa) **sem** fundo cinza no container e
  no seletor de modelo
- **(R9)** Settings → Envs: adicionar `OPENAI_API_KEY=…` → aparece mascarado na
  lista; deletar remove; persiste no backend (`/auth/envs`)
- **(R10)** Admin → Config: "Modelo padrão" é um **seletor** com os modelos
  permitidos (não input de texto) e salva via `/admin/config`

---

## BLOCO S — Connectors & Plugins Manager

> **Contexto.** Continuação direta do Bloco O (integrações). As entradas
> **"Conectores"** e **"Adicionar plugins…"** do menu `+` (print 3) precisam de
> destino. Vectora já fala MCP (`vectora/tools/mcp.py`,
> `langchain-mcp-adapters`) e tem OAuth/API-keys (Bloco O). O Bloco S dá a UI
> para gerenciar **conectores** (integrações O1/O2 já planejadas) e **plugins
> MCP** (servidores MCP externos plugáveis) a partir do chat.

### S1 — Connectors submenu (do menu `+` → "Conectores")

- Reusa os cards de integração da aba Integrações (Bloco O,
  `settings-dialog/tabs/integracoes-tab.tsx`): GitHub OAuth, OpenAI, Anthropic,
  Cohere, Tavily, etc. — status ✓/− + conectar/desconectar.
- Atalho a partir do `+` abre direto essa aba (deep-link no settings dialog).

### S2 — Plugins MCP (do menu `+` → "Adicionar plugins…")

- **Novo** `chat/components/layout/settings-dialog/tabs/plugins-tab.tsx`:
  lista de MCP servers configurados (nome, transporte stdio/sse/http, status),
  add/edit/remove. Form: comando/URL + env vars (do vault do user, Bloco C11).
- **Backend** `vectora/api/handlers/plugins.py` (novo): CRUD de configs MCP
  por user, persistido em `~/.vectora/mcp_servers.json` (ou por-user). Reusa
  `MultiServerMCPClient` (`vectora/tools/mcp.py`) para health-check.
- As tools dos MCP servers conectados entram no grafo via o registro de tools
  existente; aparecem no `GET /tools/schema` (A10) e renderizam schema-driven.

### S3 — Connector/plugin status na command bar

- Indicador discreto (contagem de conectores ativos) acessível pelo menu `+`.

### Arquivos críticos (Bloco S)

| Sub | Arquivos chat                                                                         | Arquivos vectora (Python)                                                |
| --- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| S1  | `plus-menu.tsx` (deep-link), `integracoes-tab.tsx` (reusa)                            | — (Bloco O)                                                              |
| S2  | `settings-dialog/tabs/plugins-tab.tsx` (novo), `chat/server/routes/plugins.ts` (novo) | `vectora/api/handlers/plugins.py` (novo), `vectora/tools/mcp.py` (reusa) |
| S3  | `command-bar.tsx` (indicador)                                                         | —                                                                        |

### Verificação (Bloco S)

- `+` → "Conectores" abre a aba Integrações com cards e status
- `+` → "Adicionar plugins…" abre aba Plugins; adicionar um MCP server stdio →
  health-check ✓ → suas tools aparecem em `/tools/schema` e ficam usáveis no chat
- User B não vê os plugins/conectores de User A (isolamento por user)

---

## Princípios de implementação

1. **Schema-first sempre.** Novo recurso no agente Python = novo `metadata=`
   na tool / novo evento no proto. Frontend nunca tem switch hardcoded por nome.

2. **Auth-first para tudo server.** Após Bloco C: qualquer endpoint novo,
   handler novo, ferramenta nova considera permissões. `Depends(get_current_user)`
   é o default.

3. **Zustand para state cacheável.** Threads (✓), workspaces, settings, auth,
   metrics — qualquer estado que deve sobreviver a unmount/remount de
   componentes vai pro store. Local state só para coisas efêmeras (input
   draft, modal aberto/fechado).

4. **Render hints permitem extensão sem código TS.** Adicionar render hint =
   1 linha no `RenderHint` type + 1 componente + registrar no dispatcher.

5. **Backend é fonte de verdade.** Cache cliente é stale-while-revalidate;
   reload sempre vai ao backend. Nunca persistir state crítico só no
   localStorage.

6. **Streaming-safe em tudo.** Helpers como `stripMarkdownEnvelope` (B7) já
   suportam estado parcial. Novos helpers de transformação seguem o padrão.

7. **HITL é opt-in por categoria, não global.** Usuário escolhe o que
   confirmar; default protege apenas tools verdadeiramente destrutivas.

8. **Mobile não é afterthought.** Cada bloco novo declara comportamento
   `<768px` no design.

9. **Secrets nunca aparecem em logs.** PyNaCl + audit log mascarado.
   Tokens, env vars sensíveis (`*_TOKEN`, `*_KEY`, `*_SECRET`) sempre `••••`.

10. **CLI root local é design feature, não bug.** Quem tem shell no servidor
    tem root no Vectora — exigir login ali seria teatro. Server endpoints
    são o perímetro de segurança.

---

## Verificação end-to-end por bloco

- **C**: setup wizard fresh → signup → root criado; second user member;
  member tenta ler thread de root → 403; rate limit 6º signin attempt → 429;
  user customiza GH_TOKEN próprio → comandos git usam dele; admin vê audit;
  KeePassXC kdbx criado em ~/.vectora/secrets/users/<user_id>.kdbx no signin; abrir no KeePassXC desktop confirma encriptação correta
- **D**: enviar pergunta complexa → ver `Thinking` colapsado com reason →
  expandir → ver decisão de routing
- **E**: pedir `terminal ls` → modal HITL aparece → Approve → resultado renderiza
- **F**: arrastar PDF no input → preview da 1ª página → enviar → LLM responde sobre conteúdo
- **G**: criar workspace clonando repo → badge git no header → mensagem
  "abra branch e commite" → HITL → commit feito → PR criado com `gh_pr_create`
- **H**: digitar `/clone github.com/...` → workspace novo aparece;
  `/pr "feat: auth"` → PR criado da branch atual
- **I**: `/export md` → download .md formatado; `/share` → URL pública renderiza
  thread read-only (sem auth)
- **J**: abrir em mobile viewport → sidebar é drawer → instalar como PWA →
  funciona offline (shell)
- **K**: enviar mensagem → widget mostra latência em tempo real → badge final
  aparece com tokens e custo estimado
- **L**: trocar tema dark→light → instantâneo; trocar modelo LLM →
  próxima resposta usa o novo
- **M**: thread com 200+ mensagens → scroll smooth, nenhum lag; usuário
  scrolla pra cima → auto-scroll para
