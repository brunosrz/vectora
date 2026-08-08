# Plano de Implementação — Vectora Gateway (Produção)

> Revisado 2026-08-08. Reescrito por inteiro — a versão anterior (revisão
> 2026-06-28) descrevia uma arquitetura pré-migração (Supabase, Worker
> `vectora-gateway` isolado, domínio `vectora.chat` cobrindo tudo). Desde
> então o produto migrou pra um Worker único (`vectora-services`) com D1 no
> lugar do Supabase — ver `documents/history.md` e
> `documents/business-model.md` ("Billing, auth e licenciamento —
> arquitetura atual") pro resumo executivo dessa mudança. Este documento
> reflete o código real em `services/` na data da revisão.

---

## Arquitetura — O que é o gateway e quem faz o quê

```
Bruno (desenvolvedor)
  └── cria UMA vez: OAuth Apps no GitHub/Google/Slack/GitLab, o Worker no Cloudflare

Usuário final do Vectora (instala o .exe)
  └── não configura nada de gateway/OAuth — tudo acontece automaticamente
  └── só conecta sua conta GitHub/Slack/etc. dentro do app Vectora

vectora-services (Worker Cloudflare único — services/src/index.ts)
  └── dispatch por hostname: gateway.vectora.chat + {token}.vectora.chat → gateway;
      qualquer outro host → o app da company (auth/billing/license/gdpr/...)
  └── gateway: recebe conexões WebSocket de backends Vectora
  └── atribui token estável: HMAC-SHA256(fingerprint) → 6 chars (base36)
  └── {token}.vectora.chat é o subdomínio DESSA instalação — qualquer
      request nele (callback OAuth, webhook) é serializado e encaminhado
      pelo WebSocket ativo pro backend local (proxy HTTP genérico, não
      rotas hardcoded por provider)
```

**Um único Worker, dois domínios servidos por ele** (`services/src/index.ts`):

- `gateway.vectora.chat` + `*.vectora.chat` (zona `vectora.chat`, única `[[routes]]` do `wrangler.toml`) → o gateway (device/session relay pro desktop).
- `services.vectora.company` → o mesmo Worker, branch "qualquer outro host": auth/billing/license/gdpr/api-keys/issues/rag-library/registry/telemetry + updates. **Este segundo domínio não tem `[[routes]]` própria no `wrangler.toml`** — a exposição em `services.vectora.company` é configurada como Custom Domain fora deste repo (validar com quem administra o Cloudflare antes de assumir o mecanismo exato).
- O **site** `vectora.company` (marketing/dashboard, TanStack Start) é outro sistema por completo — hospedado no **Vercel** (`company/vercel.json`), não neste Worker.

**Dois tipos de OAuth — não confundir:**

| Tipo                     | Propósito                                   | Provider                        | Callback                                                |
| ------------------------ | ------------------------------------------- | ------------------------------- | ------------------------------------------------------- |
| **Login na company**     | Entrar em vectora.company                   | `services` (D1, sessão própria) | tratado no próprio `services.vectora.company`           |
| **Integração do agente** | Agente acessa GitHub/Drive/Slack do usuário | Provider → gateway → Backend    | `https://{token}.vectora.chat/auth/{provider}/callback` |

A Seção 3 deste plano é sobre o **segundo tipo** — OAuth para que o agente faça chamadas API em nome do usuário.

---

## SEÇÃO 1 — Cloudflare

### 1.1 Worker `vectora-services`

`services/wrangler.toml`: `name = "vectora-services"`, `main = "src/index.ts"`, `compatibility_date = "2025-06-01"`, `nodejs_compat` habilitado.

### 1.2 Rota

Uma única entrada em `[[routes]]`:

```toml
[[routes]]
pattern = "*.vectora.chat/*"
zone_name = "vectora.chat"
```

O wildcard cobre `gateway.vectora.chat` (host fixo do gateway) e qualquer `{token}.vectora.chat` (subdomínio por instalação) — não são duas entradas separadas, é uma única regra que o Worker desambigua internamente (`services/src/gateway/index.ts`, comparando `host` contra `GATEWAY_HOST`).

> Registrar `gateway.vectora.chat` como Custom Domain **em paralelo** a essa rota conflita na API da Cloudflare (comentário explícito no `wrangler.toml`) — não faça as duas coisas.

### 1.3 Bindings do Worker (`services/wrangler.toml`)

| Binding                    | Tipo           | Nome real                                   | Uso                                                               |
| -------------------------- | -------------- | ------------------------------------------- | ----------------------------------------------------------------- |
| `DB`                       | D1             | `vectora-db`                                | Substitui o Postgres do Supabase — sem RLS, autorização em código |
| `R2`                       | R2 bucket      | `vectora-r2`                                | Releases (updates) + exports GDPR                                 |
| `GATEWAY_SESSION`          | Durable Object | classe `GatewaySession`                     | Uma instância por token/instalação, relay WebSocket↔HTTP          |
| `GATEWAY_METRICS`          | KV             | id `f38a1de6…`                              | Estado do OAuth device-flow do gateway (`oauth:{state}` → token)  |
| `KV`                       | KV             | id `0bed7e9f…`                              | Config de canais/rollout/quarentena de updates                    |
| `EMAIL_QUEUE`              | Queue          | `vectora-email` (+ DLQ)                     | Envio de email assíncrono (Resend)                                |
| `JOBS_QUEUE`               | Queue          | `vectora-jobs` (+ DLQ, `max_concurrency=1`) | Jobs em background (ex.: hard-delete GDPR agendado)               |
| `LICENSE_VALIDATE_LIMITER` | Rate limit     | 30 req/min                                  | `POST /license/validate` (endpoint público)                       |

Cron: `0 3 * * *` (diário) dispara o hard-delete de contas GDPR expiradas há 30+ dias.

### 1.4 Secrets no Worker

Executar em `services/` (nomes **sem mudança** em relação à versão anterior deste doc):

```powershell
# 1. HMAC para gerar tokens estáveis por instalação (só o gateway usa)
#    Gerar: python -c "import secrets; print(secrets.token_hex(32))"
pnpm wrangler secret put GATEWAY_HMAC_SECRET

# 2. Segredo compartilhado company ↔ gateway ↔ backend, device flow de licença
pnpm wrangler secret put VECTORA_OAUTH_SECRET

# 3. Prova que o cliente é um build genuíno do Vectora (fixo por produto,
#    embutido no binário Nuitka — não é por usuário)
pnpm wrangler secret put VECTORA_APP_SECRET

# 4. Billing (Stripe internacional + Asaas Brasil)
pnpm wrangler secret put STRIPE_SECRET_KEY
pnpm wrangler secret put STRIPE_WEBHOOK_SECRET
pnpm wrangler secret put STRIPE_PRICE_PRO_USD
pnpm wrangler secret put ASAAS_API_KEY
pnpm wrangler secret put ASAAS_API_URL

# 5. Email, cadastro
pnpm wrangler secret put RESEND_API_KEY
pnpm wrangler secret put TURNSTILE_SECRET_KEY
```

> Não existe `VECTORA_JWT_SECRET` nem nunca existiu como secret de produção real — sessão da company usa **token opaco** (D1, hash SHA-256), não JWT (ver Seção 5).

---

## SEÇÃO 2 — Backend Vectora App

### 2.1 Variáveis de Ambiente do Gateway no Backend

Em `~/.vectora/.env` da instalação (defaults em `backend/settings.py`/`backend/defaults.env`):

```env
GATEWAY_URL=wss://gateway.vectora.chat
GATEWAY_ENABLED=true

# Compartilhado com o Worker para OAuth device flow de licença
VECTORA_OAUTH_SECRET=<mesmo valor do wrangler secret VECTORA_OAUTH_SECRET>

# Embutido no build, não precisa ser configurado manualmente em instalação normal
VECTORA_APP_SECRET=<mesmo valor do wrangler secret VECTORA_APP_SECRET>
```

Outras URLs configuráveis (default já aponta pra produção; útil pra apontar a um `services` local via `wrangler dev` ou self-hosted): `VECTORA_LICENSE_URL`, `VECTORA_LICENSE_CONNECT_URL`, `VECTORA_LICENSE_PORTAL_URL`, `VECTORA_COMPANY_URL`, `VECTORA_GATEWAY_URL` (ver `.env.example`).

### 2.2 Como o Backend Registra com o Gateway

```
Backend                              Gateway (Worker)
  │                                    │
  │  POST /register                    │
  │  Authorization: Bearer <APP_SECRET>│
  │  { fingerprint }                   │
  │ ─────────────────────────────────► │
  │                                    │  timingSafeEqual contra
  │                                    │  env.VECTORA_APP_SECRET
  │                                    │  token = HMAC-SHA256(fingerprint)[:4B] → base36, 6 chars
  │  { token, subdomain, websocket_url }│
  │ ◄───────────────────────────────── │
  │                                    │
  │  WebSocket: wss://gateway.vectora.chat/ws/{token} │
  │ ─────────────────────────────────► │
```

O token é salvo em `~/.vectora/gateway_token` (`backend/services/gateway/token.py`, permissões de arquivo restritas). O `GatewayClient` mantém o WebSocket vivo com backoff exponencial; se cair, o Worker enfileira requests recebidos por até 10 minutos (`QUEUE_TTL_MS`) e reenvia tudo de uma vez na reconexão.

O subdomínio `{token}.vectora.chat` aparece em `GET /gateway/status` no backend para exibir ao usuário no dashboard do app.

**Importante — mecanismo de proxy, não rotas hardcoded**: o Worker não conhece `/auth/github/callback` nem `/webhook/slack` como rotas próprias. Qualquer request em `{token}.vectora.chat/*` (qualquer path, qualquer método) é serializado (`{type:"request", id, method, path, headers, body}`) e mandado pelo WebSocket ativo; o `GatewayClient` no backend Python recebe e refaz a chamada real em `http://localhost:8000{path}`, onde as rotas de fato existem (`backend/api/handlers/oauth.py`, `backend/api/handlers/webhooks.py`). A resposta volta pelo mesmo canal, correlacionada por `id`.

---

## SEÇÃO 3 — OAuth Providers (Integração do Agente)

> **Quem cria:** Bruno (você), uma única vez, como desenvolvedor.
> **Quem usa:** Todos os usuários do Vectora ao conectar suas contas no app.
>
> O callback registrado no cadastro do app no provider é
> `gateway.vectora.chat/auth/{provider}/callback` (aponte pra esse domínio
> fixo no cadastro — é o host "base" da zona `vectora.chat`). Na prática,
> cada instalação resolve seu próprio `redirect_uri` **real** como
> `https://{token}.vectora.chat/auth/{provider}/callback`
> (`backend/api/handlers/oauth.py::_gateway_callback_url`, lê
> `~/.vectora/gateway_token`) — o DNS wildcard `*.vectora.chat` cobre
> qualquer `{token}`, e a maioria dos providers aceita subdomínios do host
> cadastrado como redirect_uri válido (confirmado pra GitHub:
> `docs.github.com/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps`).
> Então o cadastro no provider continua sendo feito **uma única vez** — não
> é preciso recadastrar por instalação. Ordem de resolução real do
> `redirect_uri` por provider: env var explícita (`GITHUB_OAUTH_REDIRECT_URI`
> etc.) → `_gateway_callback_url(provider)` → fallback
> `http://localhost:8080/auth/{provider}/callback` (dev sem gateway conectado).

---

### 3.1 GitHub App — checklist de registro

**Ação manual, uma única vez, feita por você (Bruno) como desenvolvedor.**
GitHub App, não OAuth App clássico — o GitHub recomenda GitHub Apps pra
integrações novas (permissões refinadas, usuário escolhe quais repos
liberar, tokens de curta duração por padrão). O fluxo de autorização de
usuário de um GitHub App usa os MESMOS endpoints
`github.com/login/oauth/authorize` e `login/oauth/access_token` de um
OAuth App clássico, então o código de troca `code → token` em
`backend/api/handlers/oauth.py::_github_cfg`/`github_oauth_callback` não
muda — só o cadastro é diferente. Nenhum `client_id`/`client_secret` vai
hardcoded no código — o app lê
`GITHUB_OAUTH_CLIENT_ID`/`GITHUB_OAUTH_CLIENT_SECRET`/`GITHUB_OAUTH_REDIRECT_URI`
do ambiente, com fallback pro domínio do gateway.

1. **github.com/settings/apps/new** (Developer settings → GitHub Apps →
   New GitHub App — não "OAuth Apps").
2. Preencher:
   ```
   GitHub App name: Vectora
   Homepage URL: https://vectora.company
   Callback URL: https://gateway.vectora.chat/auth/github/callback
   ```
   Marcar **"Request user authorization (OAuth) during installation"** —
   sem isso o app não gera user access token, só installation tokens
   (fluxo server-to-server, não o que o Vectora usa aqui).
3. **Permissions** (Repository permissions): Contents (Read & write),
   Pull requests (Read & write), Issues (Read & write), Metadata
   (Read-only, obrigatório).
4. **Optional features**: desmarcar/desativar a expiração de 8h do user
   access token ("Expire user authorization tokens") — o backend hoje
   guarda o token direto como `GITHUB_TOKEN` (env override) e não
   implementa o fluxo de refresh_token; com a expiração ligada, a conexão
   pararia de funcionar depois de 8h sem aviso.
5. **Gerar o client secret** (seção "Client secrets" na página do app
   criado, botão "Generate a new client secret") — visível só uma vez,
   copiar imediatamente.
6. **Guardar as credenciais** em `~/.vectora/.env` da instalação (ou nas
   envs do backend, se rodando em modo servidor):
   ```env
   GITHUB_OAUTH_CLIENT_ID=<Client ID>
   GITHUB_OAUTH_CLIENT_SECRET=<Client Secret>
   ```
   O `GITHUB_OAUTH_REDIRECT_URI` não precisa ser setado — sem ele, o
   backend resolve o callback sozinho (ver o quadro no topo da Seção 3).
   Só defina a env var pra forçar um callback custom (self-hosted atrás
   de domínio próprio, por exemplo).
7. **Instalar o app** na sua conta/org (botão "Install App" na página do
   app) — sem instalação, o usuário autoriza mas o token não tem acesso a
   nenhum repositório.
8. Repetir o cadastro (OAuth App clássico, não GitHub App) para
   GitLab/Google/Slack se o usuário quiser habilitá-los já — a estrutura
   de `_gitlab_cfg`/`_google_cfg`/`_slack_cfg` é análoga (ver §3.2-3.4
   abaixo).
9. **Teste de validação**: no app Vectora, ir em Configurações →
   Integrações → GitHub → Conectar. Deve redirecionar para o GitHub,
   pedir autorização, e voltar ao app já conectado. Confirmar via
   `GET /auth/github/status` → `{"connected": true, ...}`.

**Scopes solicitados no fluxo pelo backend** (equivalentes às
`oauth_scopes` do registry, mas em GitHub Apps o acesso real é definido
pelas Permissions do passo 3, não pelo parâmetro `scope` da URL de
autorização):

- `repo` — leitura/escrita em repositórios
- `user:email` — email do usuário
- `read:org` — membros de organização

---

### 3.2 Google OAuth (Drive + Gmail)

**Onde:** console.cloud.google.com

1. Criar projeto `Vectora` (ou usar existente)
2. **APIs & Services → Enable APIs:** Google Drive API, Gmail API, People API
3. **OAuth consent screen:**
   - App name: `Vectora`
   - User support email: `bssnem@gmail.com`
   - Developer contact: `bssnem@gmail.com`
   - Scopes: `drive`, `gmail.readonly`, `userinfo.email`, `userinfo.profile`
   - Status: Testing (até 100 usuários sem verificação Google)
4. **Credentials → OAuth 2.0 Client ID:**
   - Application type: Web application
   - Authorized redirect URIs:
     ```
     https://gateway.vectora.chat/auth/google/callback
     http://localhost:8080/auth/google/callback
     ```

**Backend:**

```env
GOOGLE_OAUTH_CLIENT_ID=<Client ID>
GOOGLE_OAUTH_CLIENT_SECRET=<Client Secret>
GOOGLE_OAUTH_REDIRECT_URI=https://gateway.vectora.chat/auth/google/callback
```

> Nota de gap conhecido (ver `documents/gateway-implementation.md` §10):
> `gmail.py`/`gdrive.py` hoje não têm um fluxo `/auth/google/...`
> implementado no backend — só a env var lida diretamente pelas tools. Os
> passos acima cadastram o app; falta a rota Python correspondente.

---

### 3.3 Slack OAuth App

**Onde:** api.slack.com/apps → Create New App → From scratch

1. **OAuth & Permissions → Bot Token Scopes:**
   ```
   chat:write
   channels:read
   users:read
   channels:history
   files:read
   im:read
   ```
2. **Redirect URLs:**
   ```
   https://gateway.vectora.chat/auth/slack/callback
   http://localhost:8080/auth/slack/callback
   ```
3. **Event Subscriptions:**
   - Request URL: `https://gateway.vectora.chat/webhook/slack`
   - Events: `message.channels`, `app_mention`, `message.im`

**Backend:**

```env
SLACK_OAUTH_CLIENT_ID=<Client ID>
SLACK_OAUTH_CLIENT_SECRET=<Client Secret>
SLACK_SIGNING_SECRET=<Signing Secret>
SLACK_REDIRECT_URI=https://gateway.vectora.chat/auth/slack/callback
```

> Na prática, o Connect do Slack (`backend/services/connect/`) roda em
> **Socket Mode** (WebSocket direto com a API do Slack, sem depender do
> callback público acima) — o fluxo OAuth desta seção cobre a tool
> `slack.py` (mensagens avulsas via bot token), não o Connect.

---

### 3.4 GitLab OAuth

**Onde:** gitlab.com/-/profile/applications

```
Name: Vectora
Redirect URI:
  https://gateway.vectora.chat/auth/gitlab/callback
  http://localhost:8080/auth/gitlab/callback
Scopes: api, read_repository, write_repository, read_user
```

**Backend:**

```env
GITLAB_OAUTH_CLIENT_ID=<Application ID>
GITLAB_OAUTH_CLIENT_SECRET=<Secret>
GITLAB_BASE_URL=https://gitlab.com
```

---

## SEÇÃO 4 — Webhooks

> Webhooks de terceiros são configurados para apontar pra
> `https://{token}.vectora.chat/webhook/{provider}` (subdomínio da
> instalação — mesmo mecanismo de proxy da Seção 2.2). O Worker não
> interpreta o payload; só encaminha bytes pro backend local via
> WebSocket, onde `backend/api/handlers/webhooks.py::POST /webhook/{provider}`
> verifica a assinatura própria de cada provider (`X-Hub-Signature-256`
> pro GitHub, `X-Gitlab-Token`, `X-Slack-Signature`, `X-Linear-Signature`,
> `svix-signature` pro Resend) antes de processar.
>
> **Quem configura:** Você (Bruno) como desenvolvedor, uma única vez nos painéis dos providers.
> Usuários finais não mexem nisso.

---

### 4.1 GitHub Webhooks (nível de organização)

**Onde:** github.com/organizations/vectora-company → Settings → Webhooks

```
Payload URL: https://gateway.vectora.chat/webhook/github
Content type: application/json
Secret: <valor de GITHUB_WEBHOOK_SECRET>
Events: Pull requests, Pushes, Issues, Comments
```

> Para webhooks de repositórios individuais de usuários, o backend
> cria via API GitHub em nome do usuário autenticado.

**Backend:**

```env
GITHUB_WEBHOOK_SECRET=<secret>
```

---

### 4.2 GitLab Webhooks

```
URL: https://gateway.vectora.chat/webhook/gitlab
Secret Token: <valor de GITLAB_WEBHOOK_SECRET>
Triggers: Push, Merge requests, Comments
```

**Backend:**

```env
GITLAB_WEBHOOK_SECRET=<token>
```

---

### 4.3 Slack Event Subscriptions

```
Request URL: https://gateway.vectora.chat/webhook/slack
```

> Slack faz challenge de verificação na hora do cadastro — o backend
> precisa responder com `{"challenge": "..."}` (já implementado em
> `webhooks.py`; o Worker só encaminha o request, não intercepta).

---

### 4.4 Linear Webhooks

```
URL: https://gateway.vectora.chat/webhook/linear
Events: Issue, Comment, Cycle, Project
```

**Backend:**

```env
LINEAR_WEBHOOK_SECRET=<secret gerado pelo Linear>
```

---

### 4.5 Resend Webhooks

```
URL: https://gateway.vectora.chat/webhook/resend
Events: email.sent, email.delivered, email.bounced, email.complained
```

**Backend:**

```env
RESEND_WEBHOOK_SECRET=<signing secret Svix>
```

---

## SEÇÃO 5 — `services` (auth/billing/license/GDPR — antiga "Supabase")

> A company (`services.vectora.company`) **não usa Supabase** — todo o
> billing/auth/licenciamento roda no mesmo Worker `vectora-services`,
> persistido em D1 (`vectora-db`, binding `DB`). Sem RLS de banco:
> autorização é código, verificada em cada handler a partir da sessão
> resolvida pelo token Bearer.

### 5.1 Auth (`services/src/auth/`)

- **Sessão**: token opaco de 32 bytes (não JWT — a company é a única
  consumidora, comunicação server-to-server, sem motivo pra carregar
  claims), hash SHA-256 armazenado em D1, TTL 30 dias.
- **Signup**: exige Turnstile (`turnstileToken`), senha mínima 8
  caracteres, hash via PBKDF2-SHA256/WebCrypto nativo (100.000 iterações
  — teto real do runtime `workerd`, não bcrypt/argon2, que não rodam
  nele). Cria user + `VECTORA_TOKEN` (licença, 32 bytes hex) +
  subscription `free` automaticamente. Verificação de email obrigatória
  via fila `EMAIL_QUEUE`/Resend.
- **Login**: email/senha ou magic link.

### 5.2 Billing (`services/src/billing/`)

Dois provedores conforme o país do usuário (`country: "BR"|"INTL"` na
subscription, decidido no signup): **Stripe** para clientes
internacionais, **Asaas** para o Brasil (evita fricções do Stripe com
cartão/boleto BR). `POST /billing/checkout` decide o provider por
`sub.currency === "BRL"`. Webhooks de ambos (`POST /billing/webhooks?provider=stripe|asaas`)
mantêm `subscriptions.status`/`tier` sincronizados; cancelamento sempre
rebaixa pra `free` (o gate `require_pro()` no backend Python
verifica **tier**, não status). Também cobre cupons e presentes.

### 5.3 License (`services/src/license/`)

| Endpoint                                                                 | Auth                              | Propósito                                                                    |
| ------------------------------------------------------------------------ | --------------------------------- | ---------------------------------------------------------------------------- |
| `POST /license/validate`                                                 | Público, rate-limited (30/min IP) | Valida `VECTORA_TOKEN` — `{valid, tier, status, days_remaining, expires_at}` |
| `POST /license/agent-login`                                              | Email + senha                     | Devolve o `VECTORA_TOKEN` recuperável (não rotaciona a cada login)           |
| `POST /license/portal`                                                   | Sessão                            | Portal de pagamento (Stripe/Asaas)                                           |
| `POST /license/rotate`                                                   | Sessão                            | Rotaciona o token manualmente                                                |
| `GET /license/token-status`, `/license/token/reveal`, `/license/history` | Sessão                            | Consulta/histórico                                                           |

### 5.4 GDPR (`services/src/gdpr/`)

`POST /gdpr/export` junta `users`+`subscriptions`+`license_checks`+`api_keys`,
grava em R2 (`exports/{userId}-{ts}.json`), serve via `GET /gdpr/export/*`
com checagem de dono. `POST /gdpr/delete` faz soft-delete + revoga sessão

- email; o cron diário (03:00 UTC) enfileira hard-delete (fila
  `vectora-jobs`) pra contas expiradas há 30+ dias — cancela Stripe/Asaas e
  `DELETE FROM users` (cascade cuida do resto).

---

## SEÇÃO 6 — Hospedagem (Vercel + Cloudflare)

`vectora.company` (o **site**, marketing/dashboard, TanStack Start) e
`services.vectora.company`/`gateway.vectora.chat` (a **API**, Worker
`vectora-services`) são sistemas de hospedagem completamente diferentes,
apesar de compartilharem domínio raiz.

### 6.1 Variáveis de Ambiente no Projeto Vercel `vectora-company` (o site)

| Var                             | Valor                                         | Ambiente                                                                                                  |
| ------------------------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `VITE_GA4_MEASUREMENT_ID`       | `G-K0JK9B2YH2`                                | Production                                                                                                |
| `VITE_GOOGLE_SITE_VERIFICATION` | `i9Af68Fzq4E9N6QEmMHxz8Bp5xpTZXzPyNqG5IeoZbo` | Production                                                                                                |
| `TURNSTILE_SECRET_KEY`          | `<secret key>`                                | Production                                                                                                |
| `VITE_TURNSTILE_SITE_KEY`       | `<site key>`                                  | Production                                                                                                |
| `VITE_SERVICES_URL`/equivalente | `https://services.vectora.company`            | Production — aponta o site pra API real, checar nome exato da env var em `company/` na hora de configurar |

> As vars `SUPABASE_SERVICE_ROLE_KEY`/`VITE_SUPABASE_URL`/`VITE_SUPABASE_KEY`
> da versão anterior deste doc **não existem mais** — não há Supabase.

### 6.2 Docs — Projeto `vectora-docs` (Vercel)

- Install command: `npx --yes pnpm@11 install` (via `docs/vercel.json`)
- Build command: `pnpm build`
- Env vars: `DOCS_URL`, `APP_URL` (ver `docs/.env.example`)

---

## SEÇÃO 7 — Verificação

### 7.1 Gateway online

```powershell
curl https://gateway.vectora.chat/health
# Esperado: 200 OK
```

### 7.2 Wildcard DNS

```powershell
curl https://abc123.vectora.chat/
# Esperado: gateway responde (4xx sem sessão ativa — normal)
```

### 7.3 OAuth device flow (licença)

```powershell
# 1. Backend: POST /license/oauth/init → {state, auth_url}
# 2. Abrir auth_url → logar na company → autorizar
# 3. Backend: GET /license/oauth/poll?state=... → {ok: true}
```

### 7.4 Integração GitHub (agente)

```powershell
# No app Vectora: Configurações → Integrações → GitHub → Conectar
# Redireciona para o GitHub via {token}.vectora.chat, autentica, volta ao app
# Agente consegue clonar repos, criar PRs, etc.
```

### 7.5 Services (auth/billing/license/gdpr)

```powershell
curl https://services.vectora.company/license/validate -X POST -d '{"token":"..."}'
# Esperado: {"valid": true/false, "tier": "free"|"pro", ...}
```

---

## SEÇÃO 8 — Ordem de Execução

```
[ ] 1. Cloudflare: zona vectora.chat com a rota wildcard *.vectora.chat/* → vectora-services
[ ] 2. Worker: wrangler secret put GATEWAY_HMAC_SECRET
[ ] 3. Worker: wrangler secret put VECTORA_OAUTH_SECRET
[ ] 4. Worker: wrangler secret put VECTORA_APP_SECRET
[ ] 5. Worker: wrangler secret put STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET / STRIPE_PRICE_PRO_USD
[ ] 6. Worker: wrangler secret put ASAAS_API_KEY / ASAAS_API_URL
[ ] 7. Worker: wrangler secret put RESEND_API_KEY / TURNSTILE_SECRET_KEY
[ ] 8. Worker: aplicar migrations D1 (services/migrations/)
[ ] 9. Worker: wrangler deploy
[ ] 10. Cloudflare: configurar Custom Domain services.vectora.company → vectora-services (fora do wrangler.toml, validar mecanismo com quem administra o DNS)
[ ] 11. Backend: adicionar VECTORA_APP_SECRET/VECTORA_OAUTH_SECRET ao defaults.env
[ ] 12. Testar: GET /gateway/status no backend → ver subdomínio
[ ] 13. GitHub App: criar em github.com/settings/apps/new (não OAuth App)
[ ] 14. Google OAuth: criar no console.cloud.google.com
[ ] 15. Slack App: criar em api.slack.com/apps
[ ] 16. GitLab App: criar em gitlab.com/-/profile/applications
[ ] 17. Vercel: adicionar env vars no projeto do site (company)
[ ] 18. Testar fluxo OAuth GitHub end-to-end (via app Vectora)
[ ] 19. Testar license device flow
[ ] 20. Testar signup/login/billing (Stripe sandbox + Asaas sandbox)
```

---

## SEÇÃO 9 — Secrets Consolidados

### Worker `vectora-services` (Cloudflare wrangler secrets)

```
GATEWAY_HMAC_SECRET     → interno ao gateway, gera tokens estáveis por instalação
VECTORA_OAUTH_SECRET    → compartilhado com company e backend (device flow)
VECTORA_APP_SECRET      → prova que cliente é Vectora legítimo (fixo por produto)
STRIPE_SECRET_KEY       → billing internacional
STRIPE_WEBHOOK_SECRET   → valida webhooks do Stripe
STRIPE_PRICE_PRO_USD    → price id do plano Pro
ASAAS_API_KEY           → billing Brasil
ASAAS_API_URL           → endpoint da API Asaas (sandbox vs produção)
RESEND_API_KEY          → envio de email (verificação, notificações)
TURNSTILE_SECRET_KEY    → anti-bot no signup
```

### Backend (`~/.vectora/.env`)

```env
VECTORA_APP_SECRET=<mesmo do Worker>
VECTORA_OAUTH_SECRET=<mesmo do Worker>
GATEWAY_URL=wss://gateway.vectora.chat
GATEWAY_ENABLED=true

# OAuth Providers (integração do agente)
GITHUB_OAUTH_CLIENT_ID=
GITHUB_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=https://gateway.vectora.chat/auth/google/callback
SLACK_OAUTH_CLIENT_ID=
SLACK_OAUTH_CLIENT_SECRET=
SLACK_SIGNING_SECRET=
SLACK_REDIRECT_URI=https://gateway.vectora.chat/auth/slack/callback
GITLAB_OAUTH_CLIENT_ID=
GITLAB_OAUTH_CLIENT_SECRET=
GITLAB_BASE_URL=https://gitlab.com

# Webhook Secrets
GITHUB_WEBHOOK_SECRET=
GITLAB_WEBHOOK_SECRET=
SLACK_SIGNING_SECRET=
LINEAR_WEBHOOK_SECRET=
RESEND_WEBHOOK_SECRET=
```

### Vercel (projeto do site `vectora.company`)

```
TURNSTILE_SECRET_KEY=<mesmo do Worker, se o form de signup roda no site>
VITE_TURNSTILE_SITE_KEY=<site key>
```

---

## SEÇÃO 10 — Tool Gateway (roadmap, design apenas)

> Escopo desta seção: arquitetura decidida + pontos de extensão identificados
> no código real. **Não é implementação** — fica para uma sprint futura
> dedicada, quando o volume de tools cobertas justificar o investimento.
> Distinto da Seção 3 (OAuth de integração do agente): a Seção 3 já entrega
> o mecanismo genérico gateway↔backend; o Tool Gateway é uma camada em cima
> disso que resolve um problema de **fricção de setup**, não de mecanismo.

### O problema hoje

Cada tool de integração externa (`backend/tools/slack.py`, `gdrive.py`,
`gmail.py`, `jira.py`, `linear.py`, `notion.py`, `gh.py`) lê sua **própria**
env var (`SLACK_BOT_TOKEN`, `GITHUB_PERSONAL_ACCESS_TOKEN`, etc. — ver
`slack.py::_token()`), e cada uma exige que **Bruno** (não o usuário final)
registre um OAuth App separado no provider correspondente (Seção 3). Isso é
fricção dupla:

1. **Pro operador do Vectora** (Bruno): N providers = N OAuth Apps pra
   manter, N conjuntos de client_id/client_secret, N callbacks.
2. **Pro usuário final**: cada integração nova é um fluxo de conexão
   separado em Integrações, mesmo que várias tools compartilhem o mesmo
   provider (ex.: Slack `slack_send`/`slack_list_channels`/`slack_read` já
   compartilham `SLACK_BOT_TOKEN` — isso já funciona bem; o problema é
   entre _providers diferentes_, não dentro do mesmo).

### O que o Tool Gateway resolve — e o que não resolve

**Resolve**: um usuário que ainda não tem OAuth Apps próprios pode conectar
Slack/GitHub/Google/etc. através de credenciais operadas pela Vectora
(client_id/secret do gateway), reduzindo o fluxo de "criar OAuth App
primeiro" pra "clicar em Conectar". Centraliza _quais_ integrações estão
disponíveis (mesmo catálogo, uma vez, não duplicado por tool).

**Não resolve, e não deve**: substituir BYOK. O princípio fundacional do
produto (`market-and-positioning.md`) é que o usuário sempre pode trazer
suas próprias credenciais — o Tool Gateway é uma opção adicional de setup
mais rápido, nunca a única via. Qualquer tool continua funcionando com a
env var direta (`SLACK_BOT_TOKEN` etc.) configurada manualmente em
Integrações, exatamente como hoje — o gateway só populariza essa mesma env
var por um caminho alternativo (ver fluxo abaixo).

### Arquitetura decidida

Reaproveita a primitiva que a Seção 3 já entrega — `gateway.vectora.chat`
já recebe callbacks OAuth e encaminha pro backend certo via WebSocket
(`GatewaySession` Durable Object, `services/src/gateway/gateway-session.ts`).
O Tool Gateway generaliza isso de "OAuth por provider configurado
individualmente" pra "catálogo de providers com credenciais operadas pela
Vectora, resultado sempre pousando na mesma env var que a tool já lê":

```
Usuário clica "Conectar" no catálogo de integrações (aba Integrações,
já teria uma seção "via Vectora" ao lado de "BYOK")
        │
        ▼
gateway.vectora.chat/auth/{provider}/start
   (usa client_id/secret OPERADOS PELA VECTORA — Seção 3, já registrados
    uma vez por Bruno, reaproveitados por todos os usuários finais)
        │
        ▼
OAuth callback → {token}.vectora.chat/auth/{provider}/callback
        │
        ▼
GatewaySession (Durable Object) encaminha o token via WebSocket pro
backend do usuário (mesmo canal que já existe pra webhooks — Seção 4)
        │
        ▼
Backend grava o token na MESMA env var que a tool já lê hoje
(SLACK_BOT_TOKEN, GITHUB_PERSONAL_ACCESS_TOKEN, ...) via
POST /auth/envs (mesmo mecanismo da aba Integrações) — as tools em
backend/tools/*.py não mudam NADA, continuam lendo a env var de sempre
```

**Ponto de extensão central**: nenhuma tool precisa saber se o token veio
via Tool Gateway ou via BYOK manual — ambos os caminhos convergem na mesma
env var, gravada pelo mesmo `POST /auth/envs`. Isso significa que o Tool
Gateway é **puramente aditivo** na aba Integrações (mais uma forma de
popular a env var), sem exigir refactor de nenhuma tool existente.

### Escopo de providers (fase 1, ao implementar)

Providers que já têm tool própria e leem env var isolada — candidatos
naturais por já terem o "outro lado" pronto: Slack (`SLACK_BOT_TOKEN`),
GitHub (`GITHUB_PERSONAL_ACCESS_TOKEN`, já cobre `gh.py`), Google
(`gmail.py`/`gdrive.py`, hoje sem OAuth implementado — ver nota na Seção
3.2), Linear, Jira, Notion. Não inclui MCP marketplace (já resolvido via
`POST /auth/envs` no fluxo de instalação, sem precisar do Tool Gateway).

### Testes (quando implementado — fora de escopo desta seção)

- Conectar via Tool Gateway grava a mesma env var que a tool já lê — tool
  funciona sem nenhuma mudança de código.
- BYOK continua funcionando em paralelo — desconectar do Tool Gateway não
  apaga uma env var configurada manualmente por cima (BYOK sempre vence,
  nunca é sobrescrito silenciosamente por uma conexão via gateway mais
  antiga).
- Erro/borda: provider sem OAuth App operado pela Vectora ainda configurado
  (client_id vazio) — catálogo mostra a opção "via Vectora" desabilitada
  com mensagem clara, não um botão que falha silenciosamente ao clicar.

### Verificação (quando implementado)

Conectar Slack via Tool Gateway (sem nunca ter configurado `SLACK_BOT_TOKEN`
manualmente), confirmar que `slack_send` funciona sem nenhuma mudança de
código na tool; depois configurar `SLACK_BOT_TOKEN` manualmente por cima e
confirmar que o valor manual vence (BYOK sempre tem prioridade).
