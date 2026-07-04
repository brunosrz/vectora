# Plano de Implementação — Vectora Relay (Produção)

> Revisado 2026-06-28. Versão corrigida após identificar inconsistências na primeira versão.

---

## Arquitetura — O que é o relay e quem faz o quê

```
Bruno (desenvolvedor)
  └── cria UMA vez: OAuth Apps no GitHub/Google/Slack, Worker no Cloudflare

Usuário final do Vectora (instala o .exe)
  └── não configura nada de relay/OAuth — tudo acontece automaticamente
  └── só conecta sua conta GitHub/Slack dentro do app Vectora

Relay (Cloudflare Worker em relay.vectora.chat)
  └── recebe conexões WebSocket de backends Vectora
  └── atribui token estável: HMAC-SHA256(userId:fingerprint) → abc123
  └── {abc123}.vectora.chat aponta para aquele backend
  └── recebe callbacks OAuth e webhooks, encaminha via WebSocket ao backend certo
```

**Dois tipos de OAuth — não confundir:**

| Tipo                     | Propósito                                   | Provider                 | Callback                                      |
| ------------------------ | ------------------------------------------- | ------------------------ | --------------------------------------------- |
| **Login na company**     | Entrar em vectora.company                   | Supabase → GitHub/Google | `supabase.co/auth/v1/callback`                |
| **Integração do agente** | Agente acessa GitHub/Drive/Slack do usuário | Relay → Backend          | `relay.vectora.chat/auth/{provider}/callback` |

A Seção 3 deste plano é sobre o **segundo tipo** — OAuth para que o agente faça chamadas API em nome do usuário.

---

## SEÇÃO 1 — Cloudflare

### 1.1 Domínio `vectora.chat` no Cloudflare

✅ **Já concluído** — `vectora.chat` está no Cloudflare com NS `beth.ns.cloudflare.com` / `greg.ns.cloudflare.com`.

---

### 1.2 Registros DNS — `vectora.chat`

| Tipo  | Nome    | Conteúdo                                 | Proxy      | TTL  |
| ----- | ------- | ---------------------------------------- | ---------- | ---- |
| CNAME | `relay` | `vectora-relay.bruno-soarxz.workers.dev` | ✅ Proxied | Auto |
| CNAME | `*`     | `vectora-relay.bruno-soarxz.workers.dev` | ✅ Proxied | Auto |

O wildcard `*` captura todos os subdomínios `{token}.vectora.chat` e os proxia para o Worker. Cloudflare emite certificado wildcard automaticamente.

---

### 1.3 Custom Domains no Worker

Cloudflare Dashboard → Workers & Pages → `vectora-relay` → Settings → Domains:

```
Adicionar: relay.vectora.chat
Adicionar: *.vectora.chat
```

Ou via `wrangler.toml`:

```toml
routes = [
  { pattern = "relay.vectora.chat/*", custom_domain = true },
  { pattern = "*.vectora.chat/*",     custom_domain = true }
]
```

Depois: `pnpm wrangler deploy`

---

### 1.4 Secrets no Worker

Executar em `relay/`:

```powershell
# 1. HMAC para gerar tokens estáveis por usuário (só o relay usa)
#    Gerar: python -c "import secrets; print(secrets.token_hex(32))"
pnpm wrangler secret put RELAY_HMAC_SECRET

# 2. Segredo compartilhado company ↔ relay ↔ backend para OAuth device flow de licença
#    Gerar: python -c "import secrets; print(secrets.token_hex(32))"
#    MESMO valor em: company Vercel (RELAY_OAUTH_SECRET) e backend .env (VECTORA_OAUTH_SECRET)
pnpm wrangler secret put VECTORA_OAUTH_SECRET
```

> ⚠️ Não existe `VECTORA_JWT_SECRET` no relay. O relay não valida JWTs de backends
> individuais — cada instalação tem sua própria chave. Autenticação de registro
> é feita via `VECTORA_APP_SECRET` (veja Seção 2.2).

---

### 1.5 KV Namespace

- **ID:** `ae857e96bdf94823a10629562fb28184`
- **Binding:** `RELAY_METRICS`
- **Status:** ✅ Configurado no `wrangler.toml`
- **Uso:** `oauth:{state}` → token temporário (TTL 5min) para device flow de licença

---

### 1.6 Durable Objects

- **Classe:** `RelaySession`
- **Binding:** `RELAY_SESSION`
- **Migration:** `v1` com `new_sqlite_classes` (free plan)
- **Status:** ✅ Configurado e deployed

---

## SEÇÃO 2 — Backend Vectora App

### 2.1 Variáveis de Ambiente do Relay no Backend

Em `~/.vectora/.env` da instalação:

```env
RELAY_URL=wss://relay.vectora.chat
RELAY_ENABLED=true

# Compartilhado com relay para OAuth device flow de licença
VECTORA_OAUTH_SECRET=<mesmo valor do wrangler secret VECTORA_OAUTH_SECRET>
```

---

### 2.2 Como o Backend Registra com o Relay

O relay recebe qualquer backend Vectora legítimo. A autenticação de registro funciona assim:

```
Backend                              Relay
  │                                    │
  │  POST /register                    │
  │  { userId, fingerprint,            │
  │    app_secret: VECTORA_APP_SECRET }│
  │ ─────────────────────────────────► │
  │                                    │  verifica VECTORA_APP_SECRET
  │                                    │  (valor fixo, shipado com o app)
  │                                    │  gera token = HMAC(userId:fingerprint)
  │  { token, subdomain, ws_url }      │
  │ ◄───────────────────────────────── │
  │                                    │
  │  WebSocket: wss://relay.../ws/token│
  │ ─────────────────────────────────► │
```

`VECTORA_APP_SECRET` é um secret fixo definido por você (Bruno) que vai
embutido no executável do Vectora. Prova que o cliente é software Vectora legítimo
— não é por usuário, é por produto.

```powershell
# Adicionar ao relay:
pnpm wrangler secret put VECTORA_APP_SECRET
# Usar o mesmo valor em: vectora/backend/defaults.env → VECTORA_APP_SECRET
```

O subdomínio `{token}.vectora.chat` aparece em `GET /relay/status` no backend
para exibir ao usuário no dashboard do app.

---

## SEÇÃO 3 — OAuth Providers (Integração do Agente)

> **Quem cria:** Bruno (você), uma única vez, como desenvolvedor.
> **Quem usa:** Todos os usuários do Vectora ao conectar suas contas no app.
>
> O callback sempre vai para `relay.vectora.chat/auth/{provider}/callback`.
> O relay usa o parâmetro `state` para saber qual backend encaminhar.
> Não há `{token}` na URL — um único app OAuth atende todos os usuários.

---

### 3.1 GitHub OAuth App

**Onde:** github.com/settings/developers → OAuth Apps → New OAuth App

```
Application name: Vectora
Homepage URL: https://vectora.company
Authorization callback URL: https://relay.vectora.chat/auth/github/callback
```

> Não usar GitHub App (mais complexo). OAuth App simples é suficiente.

**Scopes solicitados no fluxo pelo backend:**

- `repo` — leitura/escrita em repositórios
- `user:email` — email do usuário
- `read:org` — membros de organização

**Backend (`~/.vectora/.env`):**

```env
GITHUB_OAUTH_CLIENT_ID=<Client ID>
GITHUB_OAUTH_CLIENT_SECRET=<Client Secret>
```

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
     https://relay.vectora.chat/auth/google/callback
     http://localhost:8080/auth/google/callback
     ```

**Backend:**

```env
GOOGLE_OAUTH_CLIENT_ID=<Client ID>
GOOGLE_OAUTH_CLIENT_SECRET=<Client Secret>
GOOGLE_OAUTH_REDIRECT_URI=https://relay.vectora.chat/auth/google/callback
```

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
   https://relay.vectora.chat/auth/slack/callback
   http://localhost:8080/auth/slack/callback
   ```
3. **Event Subscriptions:**
   - Request URL: `https://relay.vectora.chat/webhook/slack`
   - Events: `message.channels`, `app_mention`, `message.im`

**Backend:**

```env
SLACK_OAUTH_CLIENT_ID=<Client ID>
SLACK_OAUTH_CLIENT_SECRET=<Client Secret>
SLACK_SIGNING_SECRET=<Signing Secret>
SLACK_REDIRECT_URI=https://relay.vectora.chat/auth/slack/callback
```

---

### 3.4 GitLab OAuth

**Onde:** gitlab.com/-/profile/applications

```
Name: Vectora
Redirect URI:
  https://relay.vectora.chat/auth/gitlab/callback
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

> Webhooks chegam em `https://relay.vectora.chat/webhook/{provider}`.
> O relay usa o header `X-Relay-Token` ou o payload para identificar
> o backend destino e encaminha via WebSocket.
>
> **Quem configura:** Você (Bruno) como desenvolvedor, uma única vez nos painéis dos providers.
> Usuários finais não mexem nisso.

---

### 4.1 GitHub Webhooks (nível de organização)

**Onde:** github.com/organizations/vectora-company → Settings → Webhooks

```
Payload URL: https://relay.vectora.chat/webhook/github
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
URL: https://relay.vectora.chat/webhook/gitlab
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
Request URL: https://relay.vectora.chat/webhook/slack
```

> Slack faz challenge de verificação na hora do cadastro — relay precisa
> responder com `{"challenge": "..."}`. Implementar no handler do relay.

---

### 4.4 Linear Webhooks

```
URL: https://relay.vectora.chat/webhook/linear
Events: Issue, Comment, Cycle, Project
```

**Backend:**

```env
LINEAR_WEBHOOK_SECRET=<secret gerado pelo Linear>
```

---

### 4.5 Resend Webhooks

```
URL: https://relay.vectora.chat/webhook/resend
Events: email.sent, email.delivered, email.bounced, email.complained
```

**Backend:**

```env
RESEND_WEBHOOK_SECRET=<signing secret Svix>
```

---

## SEÇÃO 5 — Supabase (vectora.company)

> O Supabase da `vectora.company` hospeda auth de usuários e edge functions de licença.
> O relay interage com `vectora.company` apenas no OAuth device flow de licença.

### 5.1 Edge Functions Necessárias

| Função             | Chamada por                  | Propósito                |
| ------------------ | ---------------------------- | ------------------------ |
| `validate-license` | Backend (a cada 6h)          | Valida token de licença  |
| `agent-login`      | Backend (`/license/connect`) | Login → token de licença |
| `create-portal`    | Backend (`/license/portal`)  | Portal de pagamento      |

**Auth:** Bearer token (token de licença do usuário).

### 5.2 Tabelas Supabase

| Tabela           | Propósito                    |
| ---------------- | ---------------------------- |
| `tokens`         | Token de licença por user_id |
| `license_checks` | Auditoria de validações      |

---

## SEÇÃO 6 — Vercel (company)

### 6.1 Variáveis de Ambiente no Projeto `vectora-company`

| Var                             | Valor                                         | Ambiente   |
| ------------------------------- | --------------------------------------------- | ---------- |
| `RELAY_URL`                     | `https://relay.vectora.chat`                  | Production |
| `RELAY_OAUTH_SECRET`            | `<mesmo que wrangler VECTORA_OAUTH_SECRET>`   | Production |
| `VITE_GA4_MEASUREMENT_ID`       | `G-K0JK9B2YH2`                                | Production |
| `VITE_GOOGLE_SITE_VERIFICATION` | `i9Af68Fzq4E9N6QEmMHxz8Bp5xpTZXzPyNqG5IeoZbo` | Production |
| `RESEND_API_KEY`                | `<chave do Resend>`                           | Production |
| `SUPABASE_SERVICE_ROLE_KEY`     | `<service role key>`                          | Production |
| `VITE_SUPABASE_URL`             | `https://lqclwumwslecrcfibrvn.supabase.co`    | Production |
| `VITE_SUPABASE_KEY`             | `<publishable key>`                           | Production |
| `TURNSTILE_SECRET_KEY`          | `<secret key>`                                | Production |
| `VITE_TURNSTILE_SITE_KEY`       | `<site key>`                                  | Production |

### 6.2 Docs — Projeto `vectora-docs`

- Install command: `npx --yes pnpm@11 install` (via `docs/vercel.json`)
- Build command: `pnpm build`
- Env vars: `DOCS_URL`, `APP_URL` (ver `docs/.env.example`)

---

## SEÇÃO 7 — Verificação

### 7.1 Relay online

```powershell
curl https://relay.vectora.chat/health
# Esperado: 200 OK
```

### 7.2 Wildcard DNS

```powershell
curl https://abc123.vectora.chat/
# Esperado: relay responde (4xx sem sessão ativa — normal)
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
# Redireciona para GitHub, autentica, volta ao app
# Agente consegue clonar repos, criar PRs, etc.
```

---

## SEÇÃO 8 — Ordem de Execução

```
[ ] 1. Cloudflare: adicionar registros DNS (relay + wildcard *)
[ ] 2. Cloudflare: adicionar custom domains ao Worker
[ ] 3. Relay: wrangler secret put RELAY_HMAC_SECRET
[ ] 4. Relay: wrangler secret put VECTORA_OAUTH_SECRET
[ ] 5. Relay: wrangler secret put VECTORA_APP_SECRET
[ ] 6. Relay: implementar handler /register (verificar VECTORA_APP_SECRET)
[ ] 7. Relay: wrangler deploy com custom domains
[ ] 8. Backend: adicionar VECTORA_APP_SECRET ao defaults.env
[ ] 9. Backend: implementar conexão ao relay no startup
[ ] 10. Testar: GET /relay/status no backend → ver subdomínio
[ ] 11. GitHub OAuth App: criar em github.com/settings/developers
[ ] 12. Google OAuth: criar no console.cloud.google.com
[ ] 13. Slack App: criar em api.slack.com/apps
[ ] 14. GitLab App: criar em gitlab.com/-/profile/applications
[ ] 15. Vercel: adicionar env vars na company
[ ] 16. Testar fluxo OAuth GitHub end-to-end (via app Vectora)
[ ] 17. Testar license device flow
```

---

## SEÇÃO 9 — Secrets Consolidados

### Relay (Cloudflare wrangler secrets)

```
RELAY_HMAC_SECRET     → interno ao relay, gera tokens estáveis por usuário
VECTORA_OAUTH_SECRET  → compartilhado com company e backend (device flow)
VECTORA_APP_SECRET    → prova que cliente é Vectora legítimo (fixo por produto)
```

### Backend (`~/.vectora/.env`)

```env
VECTORA_APP_SECRET=<mesmo do relay>
VECTORA_OAUTH_SECRET=<mesmo do relay>
RELAY_URL=wss://relay.vectora.chat
RELAY_ENABLED=true

# OAuth Providers (integração do agente)
GITHUB_OAUTH_CLIENT_ID=
GITHUB_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=https://relay.vectora.chat/auth/google/callback
SLACK_OAUTH_CLIENT_ID=
SLACK_OAUTH_CLIENT_SECRET=
SLACK_SIGNING_SECRET=
SLACK_REDIRECT_URI=https://relay.vectora.chat/auth/slack/callback
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

### Company (Vercel env vars)

```
RELAY_URL=https://relay.vectora.chat
RELAY_OAUTH_SECRET=<mesmo do relay>
```
