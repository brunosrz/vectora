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

| Bloco | Tema                                          | Status                                       |
| ----- | --------------------------------------------- | -------------------------------------------- |
| **A** | Chat Foundations                              | ✅ Concluído                                 |
| **B** | Polish, Bugfixes & Infra                      | ✅ Concluído                                 |
| **C** | **Authentication & RBAC**                     | 🎯 **Prioridade atual**                      |
| **D** | Reasoning Reveal & Thinking UX                | ⏳ Próximo                                   |
| **E** | HITL em Chat                                  | ⏳ Bloqueado por `interrupt_before` no graph |
| **F** | File Handling Completo                        | ⏳ Independente                              |
| **G** | Workspaces + Git Integration                  | ⏳ Junto com workspaces do backend           |
| **H** | Slash Commands                                | ⏳ Power-user                                |
| **I** | Conversation Features (search, export, share) | ⏳ Power-user                                |
| **J** | Mobile & PWA                                  | ⏳ Pré-mobile native                         |
| **K** | Live Metrics Dashboard                        | ⏳ Observabilidade                           |
| **L** | Settings & Customization                      | ⏳ Continuous                                |
| **M** | Performance & UX Polish                       | ⏳ Continuous                                |

**Ordem sugerida pós-conclusão de C:**
`C → D → F → G → E → L → H → I → J → K → M`

C é prioridade pois desbloqueia uso multi-usuário em VPS corporativa — sem
auth, o `vectora server` não pode ser exposto publicamente.

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

## BLOCO C — Authentication & RBAC 🎯 [PRIORIDADE ATUAL]

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

# Opcional (gated):
httpx = "*"                   # já presente — usado pelo Vaultwarden client
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
| C10-C11 | `chat/components/layout/settings-dialog/envs-tab.tsx` (novo)                                                   | `vectora/services/secrets/{base,internal,vaultwarden}.py` (novos)                                                      |
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

## BLOCO L — Settings & Customization

### N1 — Settings panel completo

- Hoje: dialog mínimo via `AgentSettings`
- Expandir com abas:
  - **Account** — email, password change (C9)
  - **Envs** — env vars do user (C10)
  - **Audit** — admin/root only (C12)
  - **Modelos** — selector por kind (LLM, TTS, ASR, Image, Embedding, Reranker)
  - **Workspace** — workspace ativo + criar/deletar
  - **Aparência** — tema, font size, density
  - **Comportamento** — HITL configuration (E4), verbosity, system prompt custom
  - **Privacy** — clear all threads, export all data, LangSmith on/off

### N2 — Tema (dark/light/system)

- Hoje: dark hardcoded
- Toggle via shadcn theme provider
- Persist em `localStorage` + sync com `prefers-color-scheme`

### N3 — System prompt custom por workspace

- Field em `Workspace` no backend: `custom_system_prompt: str | None`
- Editor markdown no settings → injetado no `_load_session_context` do orchestrator

### N4 — Verbosity slider (terse / normal / verbose)

- 0-5 escala que mapeia pra system prompt do orchestrator
- 0: respostas de 1 frase; 5: respostas longas com fontes

**Arquivos críticos:** `chat/components/layout/settings-dialog/` (novo módulo), `chat/lib/stores/settings-store.ts` (novo Zustand), `chat/components/providers/theme-provider.tsx` (novo)

---

## BLOCO M — Performance & UX Polish

### M1 — Virtualização de threads longas

- `@tanstack/react-virtual` para `MessageList` quando > 50 mensagens
- Mantém scroll position ao trocar threads
- Mensagem ativa (streaming) sempre renderizada

### M2 — Token-by-token rendering smoothness

- Buffer de N ms (ex: 16ms = 1 frame) antes de re-renderizar
- Evita layout thrashing em streams rápidos do Gemini Flash

### M3 — Auto-scroll inteligente

- Hoje: scroll force-to-bottom no novo token
- Detecta se usuário scrollou pra cima → para de auto-scrollar; mostra botão
  "Voltar pro fim"

### M4 — Loading skeletons

- Sidebar threads loading: skeleton 5 rows
- Message history loading: skeleton de 2-3 messages
- Tool result pendente: pulse animation no ToolCallRenderer

### M5 — Optimistic UI para envio

- User message aparece **imediatamente** ao apertar Enter (antes do POST)
- Erro no envio → mostra retry inline

**Arquivos críticos:** `chat/components/chat/message-list.tsx` (virtualização), `chat/lib/hooks/chat/use-auto-scroll.ts` (extend), `chat/components/ui/skeleton.tsx` (já existe shadcn — usar)

---

## Ordem de implementação sugerida

```
[CONCLUÍDOS]
  Bloco A — Chat Foundations
  Bloco B — Polish, Bugfixes & Infra

[v0.1-chat — PRIORIDADE: desbloqueio multi-usuário]
  Bloco C — Authentication & RBAC
  (sem isso, vectora server não pode ser exposto publicamente)

[v0.2-chat — UX imediato]
  Bloco D (reasoning reveal) → Bloco F (file handling)

[v0.3-chat — projeto-first]
  Bloco G (workspaces + git) ← depende do backend de workspaces (B5-B7 roadmap principal)
  Bloco E (HITL) ← depende de interrupt_before no graph

[v0.4-chat — power-user]
  Bloco H (slash commands) → Bloco I (search/export/share) → Bloco L (settings)

[v0.5-chat — mobile + observability]
  Bloco J (mobile/PWA) → Bloco K (metrics dashboard)

[contínuo]
  Bloco M — Performance & UX Polish (aplicar incrementalmente)
```

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
  Vaultwarden opt-in via config → secrets migram pra ele
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
