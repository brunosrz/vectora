# vectora-update-server

Cloudflare Workers app que serve manifestos `latest.yml` / `latest-mac.yml` /
`latest-linux.yml` para o `electron-updater` rodando dentro do desktop
Vectora.

Componentes:

- **`src/worker.ts`** — handler HTTP. Rotas:
  - `GET /updates/:channel/:os/:arch/latest.yml` — manifesto principal.
  - `GET /updates/:channel/:os/:arch/:filename` — binário em si (delta
    `.blockmap` ou full).
  - `GET /health` — sanity check.
- **`config.yml`** — phased rollout, channels habilitados, quarantine.
- **`scripts/release.ts`** — sobe novo release: copia binários para R2,
  gera `latest*.yml`, atualiza `config.yml` com versão "stable".

## Variáveis de ambiente

| Var                                         | Descrição                                                                                            |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `R2_BUCKET`                                 | Nome do bucket Cloudflare R2 onde os binários ficam.                                                 |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | Credenciais de leitura.                                                                              |
| `LICENSE_VALIDATE_URL`                      | Edge function Supabase `validate-license` — Worker valida `VECTORA_TOKEN` antes de servir downloads. |
| `KV_NAMESPACE`                              | Namespace KV para guardar `config.yml` runtime + telemetria de update.                               |

## Rollout faseado

`config.yml`:

```yaml
channels:
  latest:
    version: 1.2.0
    rollout_percent: 25 # 25% dos clients recebem este manifest
    previous_stable: 1.1.4 # outros 75% recebem este
  beta:
    version: 1.3.0-beta.2
    rollout_percent: 100
quarantined: [] # versoes bloqueadas por crash report
```

O Worker decide qual versão servir por hash(client_id) % 100 < rollout_percent.

## Telemetria

`POST /telemetry/update-result` recebe `{state: started|completed|failed,
version, os, arch}` do desktop main.ts (D2 setupAutoUpdater); contabiliza
em KV. Se `failed` ultrapassa 3 em 1h para mesma versão → versão entra
em `quarantined` automaticamente (D4 rollback automático).

## Deploy

```bash
pnpm install
pnpm wrangler deploy
```

Domínio em produção: `updates.vectora.company` (via Cloudflare DNS
apontando para Worker).
