# vectora-services

Worker único no Cloudflare que unifica os antigos `relay/` e
`update-server/` com auth/billing/license/GDPR/api-keys/issues/rag-library/
registry — que antes dependiam do Supabase da `company/` (ver
`documents/plan.md` Bloco K para o histórico da migração). Domínios:

- `relay.vectora.chat` + `{token}.vectora.chat` — proxy WebSocket
  bidirecional de OAuth/webhooks pro app desktop (`src/relay/`). O cliente
  Python do desktop já tem essas URLs hardcoded — não mexer sem atualizar
  os dois lados.
- `update.vectora.company` — distribuição de releases pro `electron-updater`
  e download público de primeira instalação (`src/updates/`).
- `services.vectora.company` — auth/billing/license/GDPR/api-keys/issues/
  rag-library/registry, todos montados em `src/index.ts`.

Dispatch por hostname em `src/index.ts`.

## Rotas

**relay** (`relay.vectora.chat`):

- `POST /register` — troca um JWT do backend Python por um token de relay de
  6 caracteres + URL de WebSocket.
- `GET|POST /ws/:token` — upgrade pra WebSocket, vira a sessão ativa da
  Durable Object `RelaySession`.
- `GET /health/:token` — `{connected, queued}`.
- `DELETE /relay/session/:token` — revoga a sessão.
- `POST /oauth/token` / `GET /oauth/token/:state` — device flow de OAuth
  (a company grava o token trocado, o backend consome via polling).

**relay** (`{token}.vectora.chat`, qualquer path): webhooks/callbacks OAuth
de terceiros (GitHub etc.) — encaminhados pro backend local via WebSocket se
conectado, ou enfileirados (TTL 10min) se offline.

**updates** (`update.vectora.company`):

- `GET /updates/:channel/:os/:arch/latest.yml` — manifesto do
  electron-updater (sem token — Free não tem conta).
- `GET /updates/:channel/:os/:arch/:version/:filename` — binário/blockmap.
- `GET /download/:channel/:os/:arch/:ext` — download de primeira instalação
  (sem token, sem rollout — sempre a versão estável do canal).
- `POST /telemetry/update-result` — conta sucesso/falha de update;
  quarentena automática após 3 falhas em 1h.

**services** (`services.vectora.company`) — Hono, um router por
responsabilidade, tudo sobre D1 (sem RLS — autorização é código, em cada
handler):

- `/auth/*` — signup, login, logout, refresh, verificação de email.
- `/profile/*` — dados de perfil da conta.
- `/billing/*` — checkout/portal/webhooks (Stripe INTL + Asaas BR), sessão
  web autenticada por cookie.
- `/license/*` — validação/rotação de `VECTORA_TOKEN`, `agent-login`
  (email+senha → token, usado pelo backend Python), `portal` (mesma lógica
  de `/billing/portal`, mas autenticado pelo token em vez de sessão — é a
  rota que o backend Python chama).
- `/oauth/*` — device flow que conecta a conta vectora.company ao relay.
- `/gdpr/*` — soft-delete + Cron Trigger diário de hard-delete.
- `/api-keys/*`, `/issues/*` — gestão de chaves e tickets de suporte.
- `/rag-library/*` — placeholder (catálogo + download de bancos RAG
  pré-indexados; fora de escopo até depois do lançamento do Vectora).
- `/registry/*` — placeholder do MCP registry centralizado.

## Bindings (`wrangler.toml`)

- Durable Object `RELAY_SESSION` (classe `RelaySession`).
- KV `RELAY_METRICS` — estado de OAuth device flow do relay.
- R2 `R2` (bucket `vectora-releases`) — instaladores + manifestos.
- KV `KV` — config de canais/rollout/quarentena do updates.
- D1 `DB` (`vectora-db`) — users/sessions/tokens/subscriptions/license_checks/
  payment_events/email_verifications/rag_packages (`migrations/`).
- Cron Trigger diário (`[triggers]`) — GDPR hard-delete.
- Secrets (via `wrangler secret put`, não no `.toml`): `VECTORA_JWT_SECRET`,
  `RELAY_HMAC_SECRET`, `VECTORA_OAUTH_SECRET` (relay); `RESEND_API_KEY`
  (email transacional); `TURNSTILE_SECRET_KEY` (anti-bot); `STRIPE_SECRET_KEY`,
  `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_PRO_USD` (billing INTL);
  `ASAAS_API_KEY`, `ASAAS_API_URL` (billing BR).

## Publicar um release

Depois de `scons release-<os>` gerar os instaladores em
`vectora/electron/dist-electron/`:

```powershell
pnpm run release -- --version=X.Y.Z
```

Sobe pra R2 e atualiza o canal `latest` no KV (`scripts/release.ts`).

## Testes

`@cloudflare/vitest-pool-workers` (miniflare real, não mocks manuais) —
`pnpm test`. Alguns testes de Durable Object são pulados no Windows
(`TEST_IS_WINDOWS=1`) por um lock de SQLite do workerd que não libera antes
do cleanup do isolated storage; rodam normalmente em CI (Linux).
