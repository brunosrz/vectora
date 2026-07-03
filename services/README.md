# vectora-services

Worker único no Cloudflare que substitui os antigos `relay/` e
`update-server/` (unificados nesta fase — ver `documents/` ou o histórico de
commits pra contexto da decisão). Domínios não mudam:

- `relay.vectora.chat` + `{token}.vectora.chat` — proxy WebSocket
  bidirecional de OAuth/webhooks pro app desktop (`src/relay/`). O cliente
  Python do desktop já tem essas URLs hardcoded — não mexer sem atualizar
  os dois lados.
- `update.vectora.company` — distribuição de releases pro `electron-updater`
  e download público de primeira instalação (`src/updates/`).

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

## Bindings (`wrangler.toml`)

- Durable Object `RELAY_SESSION` (classe `RelaySession`).
- KV `RELAY_METRICS` — estado de OAuth device flow do relay.
- R2 `R2` (bucket `vectora-releases`) — instaladores + manifestos.
- KV `KV` — config de canais/rollout/quarentena do updates.
- Secrets (via `wrangler secret put`, não no `.toml`): `VECTORA_JWT_SECRET`,
  `RELAY_HMAC_SECRET`, `VECTORA_OAUTH_SECRET`.

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
