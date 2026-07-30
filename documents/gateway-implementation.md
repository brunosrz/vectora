# Plano de Implementação — Vectora Gateway (Produção)

> Revisado 2026-06-28. Versão corrigida após identificar inconsistências na primeira versão.

---

## Arquitetura — O que é o gateway e quem faz o quê

```
Bruno (desenvolvedor)
  └── cria UMA vez: OAuth Apps no GitHub/Google/Slack, Worker no Cloudflare

Usuário final do Vectora (instala o .exe)
  └── não configura nada de gateway/OAuth — tudo acontece automaticamente
  └── só conecta sua conta GitHub/Slack dentro do app Vectora

Gateway (Cloudflare Worker em gateway.vectora.chat)
  └── recebe conexões WebSocket de backends Vectora
  └── atribui token estável: HMAC-SHA256(fingerprint) → abc123
  └── {abc123}.vectora.chat aponta para aquele backend
  └── recebe callbacks OAuth e webhooks, encaminha via WebSocket ao backend certo
```

**Dois tipos de OAuth — não confundir:**

| Tipo                     | Propósito                                   | Provider                 | Callback                                        |
| ------------------------ | ------------------------------------------- | ------------------------ | ----------------------------------------------- |
| **Login na company**     | Entrar em vectora.company                   | Supabase → GitHub/Google | `supabase.co/auth/v1/callback`                  |
| **Integração do agente** | Agente acessa GitHub/Drive/Slack do usuário | Gateway → Backend        | `gateway.vectora.chat/auth/{provider}/callback` |

A Seção 3 deste plano é sobre o **segundo tipo** — OAuth para que o agente faça chamadas API em nome do usuário.

---

## SEÇÃO 1 — Cloudflare

### 1.1 Domínio `vectora.chat` no Cloudflare

✅ **Já concluído** — `vectora.chat` está no Cloudflare com NS `beth.ns.cloudflare.com` / `greg.ns.cloudflare.com`.

---

### 1.2 Registros DNS — `vectora.chat`

| Tipo  | Nome      | Conteúdo                                   | Proxy      | TTL  |
| ----- | --------- | ------------------------------------------ | ---------- | ---- |
| CNAME | `gateway` | `vectora-gateway.bruno-soarxz.workers.dev` | ✅ Proxied | Auto |
| CNAME | `*`       | `vectora-gateway.bruno-soarxz.workers.dev` | ✅ Proxied | Auto |

O wildcard `*` captura todos os subdomínios `{token}.vectora.chat` e os proxia para o Worker. Cloudflare emite certificado wildcard automaticamente.

---

### 1.3 Custom Domains no Worker

Cloudflare Dashboard → Workers & Pages → `vectora-gateway` → Settings → Domains:

```
Adicionar: gateway.vectora.chat
Adicionar: *.vectora.chat
```

Ou via `wrangler.toml`:

```toml
routes = [
  { pattern = "gateway.vectora.chat/*", custom_domain = true },
  { pattern = "*.vectora.chat/*",     custom_domain = true }
]
```

Depois: `pnpm wrangler deploy`

---

### 1.4 Secrets no Worker

Executar em `gateway/`:

```powershell
# 1. HMAC para gerar tokens estáveis por usuário (só o gateway usa)
#    Gerar: python -c "import secrets; print(secrets.token_hex(32))"
pnpm wrangler secret put GATEWAY_HMAC_SECRET

# 2. Segredo compartilhado company ↔ gateway ↔ backend para OAuth device flow de licença
#    Gerar: python -c "import secrets; print(secrets.token_hex(32))"
#    MESMO valor em: company Vercel (GATEWAY_OAUTH_SECRET) e backend .env (VECTORA_OAUTH_SECRET)
pnpm wrangler secret put VECTORA_OAUTH_SECRET
```

> ⚠️ Não existe `VECTORA_JWT_SECRET` no gateway. O gateway não valida JWTs de backends
> individuais — cada instalação tem sua própria chave. Autenticação de registro
> é feita via `VECTORA_APP_SECRET` (veja Seção 2.2).

---

### 1.5 KV Namespace

- **ID:** `ae857e96bdf94823a10629562fb28184`
- **Binding:** `GATEWAY_METRICS`
- **Status:** ✅ Configurado no `wrangler.toml`
- **Uso:** `oauth:{state}` → token temporário (TTL 5min) para device flow de licença

---

### 1.6 Durable Objects

- **Classe:** `GatewaySession`
- **Binding:** `GATEWAY_SESSION`
- **Migration:** `v1` com `new_sqlite_classes` (free plan)
- **Status:** ✅ Configurado e deployed

---

## SEÇÃO 2 — Backend Vectora App

### 2.1 Variáveis de Ambiente do Gateway no Backend

Em `~/.vectora/.env` da instalação:

```env
GATEWAY_URL=wss://gateway.vectora.chat
GATEWAY_ENABLED=true

# Compartilhado com gateway para OAuth device flow de licença
VECTORA_OAUTH_SECRET=<mesmo valor do wrangler secret VECTORA_OAUTH_SECRET>
```

---

### 2.2 Como o Backend Registra com o Gateway

O gateway recebe qualquer backend Vectora legítimo. A autenticação de registro funciona assim:

```
Backend                              Gateway
  │                                    │
  │  POST /register                    │
  │  Authorization: Bearer <APP_SECRET>│
  │  { fingerprint }                   │
  │ ─────────────────────────────────► │
  │                                    │  timingSafeEqual contra
  │                                    │  env.VECTORA_APP_SECRET (fixo,
  │                                    │  shipado com o app — igual pra
  │                                    │  toda instalação)
  │                                    │  gera token = HMAC-SHA256(fingerprint)
  │  { token }                         │
  │ ◄───────────────────────────────── │
  │                                    │
  │  WebSocket: wss://gateway.../ws/token│
  │ ─────────────────────────────────► │
```

`VECTORA_APP_SECRET` é um secret fixo definido por você (Bruno) que vai
embutido no executável do Vectora. Prova que o cliente é software Vectora legítimo
— não é por usuário, é por produto.

```powershell
# Adicionar ao gateway:
pnpm wrangler secret put VECTORA_APP_SECRET
# Usar o mesmo valor em: vectora/backend/defaults.env → VECTORA_APP_SECRET
```

O subdomínio `{token}.vectora.chat` aparece em `GET /gateway/status` no backend
para exibir ao usuário no dashboard do app.

---

## SEÇÃO 3 — OAuth Providers (Integração do Agente)

> **Quem cria:** Bruno (você), uma única vez, como desenvolvedor.
> **Quem usa:** Todos os usuários do Vectora ao conectar suas contas no app.
>
> O callback registrado no provider é `gateway.vectora.chat/auth/{provider}/
callback` (aponte pra esse domínio fixo no cadastro do app). Na prática,
> cada instalação resolve seu próprio `redirect_uri` como
> `https://{token}.vectora.chat/auth/{provider}/callback` — `{token}` é o
> identificador que o `GatewayClient` recebeu ao se registrar
> (`POST /register`, ver Seção 2) e persistiu em `~/.vectora/gateway_token`
> (`backend/api/handlers/oauth.py::_gateway_callback_url`). O DNS wildcard
> `*.vectora.chat` cobre qualquer `{token}`, então o cadastro no provider
> continua sendo feito uma única vez — não é preciso recadastrar por
> instalação.

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
   backend resolve o callback sozinho: usa `https://{token}.vectora.chat/
auth/github/callback` (token da instalação, se o gateway já registrou
   um — GitHub aceita subdomínios do host cadastrado como redirect_uri
   válido, ver `docs.github.com/apps/oauth-apps/building-oauth-apps/
authorizing-oauth-apps`) ou `http://localhost:8080/auth/github/
callback` como último fallback (dev sem gateway conectado). Só defina
   a env var pra forçar um callback custom (self-hosted atrás de domínio
   próprio, por exemplo).
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

> Webhooks chegam em `https://gateway.vectora.chat/webhook/{provider}`.
> O gateway usa o header `X-Gateway-Token` ou o payload para identificar
> o backend destino e encaminha via WebSocket.
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

> Slack faz challenge de verificação na hora do cadastro — gateway precisa
> responder com `{"challenge": "..."}`. Implementar no handler do gateway.

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

## SEÇÃO 5 — Supabase (vectora.company)

> O Supabase da `vectora.company` hospeda auth de usuários e edge functions de licença.
> O gateway interage com `vectora.company` apenas no OAuth device flow de licença.

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
| `GATEWAY_URL`                   | `https://gateway.vectora.chat`                | Production |
| `GATEWAY_OAUTH_SECRET`          | `<mesmo que wrangler VECTORA_OAUTH_SECRET>`   | Production |
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
# Redireciona para GitHub, autentica, volta ao app
# Agente consegue clonar repos, criar PRs, etc.
```

---

## SEÇÃO 8 — Ordem de Execução

```
[ ] 1. Cloudflare: adicionar registros DNS (gateway + wildcard *)
[ ] 2. Cloudflare: adicionar custom domains ao Worker
[ ] 3. Gateway: wrangler secret put GATEWAY_HMAC_SECRET
[ ] 4. Gateway: wrangler secret put VECTORA_OAUTH_SECRET
[ ] 5. Gateway: wrangler secret put VECTORA_APP_SECRET
[ ] 6. Gateway: implementar handler /register (verificar VECTORA_APP_SECRET)
[ ] 7. Gateway: wrangler deploy com custom domains
[ ] 8. Backend: adicionar VECTORA_APP_SECRET ao defaults.env
[ ] 9. Backend: implementar conexão ao gateway no startup
[ ] 10. Testar: GET /gateway/status no backend → ver subdomínio
[ ] 11. GitHub App: criar em github.com/settings/apps/new (não OAuth App)
[ ] 12. Google OAuth: criar no console.cloud.google.com
[ ] 13. Slack App: criar em api.slack.com/apps
[ ] 14. GitLab App: criar em gitlab.com/-/profile/applications
[ ] 15. Vercel: adicionar env vars na company
[ ] 16. Testar fluxo OAuth GitHub end-to-end (via app Vectora)
[ ] 17. Testar license device flow
```

---

## SEÇÃO 9 — Secrets Consolidados

### Gateway (Cloudflare wrangler secrets)

```
GATEWAY_HMAC_SECRET     → interno ao gateway, gera tokens estáveis por usuário
VECTORA_OAUTH_SECRET  → compartilhado com company e backend (device flow)
VECTORA_APP_SECRET    → prova que cliente é Vectora legítimo (fixo por produto)
```

### Backend (`~/.vectora/.env`)

```env
VECTORA_APP_SECRET=<mesmo do gateway>
VECTORA_OAUTH_SECRET=<mesmo do gateway>
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

### Company (Vercel env vars)

```
GATEWAY_URL=https://gateway.vectora.chat
GATEWAY_OAUTH_SECRET=<mesmo do gateway>
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
registre um OAuth App separado no provider correspondente (Seção 5). Isso é
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
   (usa client_id/secret OPERADOS PELA VECTORA — Seção 5, já registrados
    uma vez por Bruno, reaproveitados por todos os usuários finais)
        │
        ▼
OAuth callback → gateway.vectora.chat/auth/{provider}/callback
        │
        ▼
GatewaySession (Durable Object) encaminha o token via WebSocket pro
backend do usuário (mesmo canal que já existe pra webhooks — Seção 3)
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
(`gmail.py`/`gdrive.py`, hoje sem OAuth implementado — ver nota abaixo),
Linear, Jira, Notion. Não inclui MCP marketplace (Sprint 2 já resolveu isso
via `POST /auth/envs` no fluxo de instalação, sem precisar do Tool Gateway).

**Nota de gap identificado durante a investigação**: `gmail.py`/`gdrive.py`
hoje não têm um fluxo `/auth/google/...` implementado no backend (só a
env var lida diretamente) — isso não é bloqueante para o Tool Gateway (o
design não depende de OAuth já existir por provider), mas é um pré-requisito
de implementação a resolver na sprint que fizer isso de verdade: cada
provider sem OAuth próprio ganha um `backend/api/handlers/oauth_{provider}.py`
seguindo o padrão que a Seção 3 já define para GitHub/Slack/GitLab.

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
