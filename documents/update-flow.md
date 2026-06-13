# Vectora — Fluxo de Atualização (changelog-antes, aprovação manual, backup + rollback)

> **Status:** proposta de design — aguardando aprovação antes de implementar.
> Nenhum código deste documento foi escrito ainda.

## 1. Objetivo e princípios

O usuário precisa **ver o que muda e aprovar ANTES** de qualquer atualização ser
aplicada — o oposto do Chrome (que só mostra o changelog depois de já ter
instalado e não dá como reverter).

Princípios inegociáveis:

1. **Nada automático.** Nenhum download/instalação sem clique explícito.
2. **Changelog primeiro.** As notas da versão nova aparecem _antes_ do download,
   e o usuário aprova as mudanças.
3. **Backup antes de instalar.** Snapshot dos dados do usuário antes de aplicar.
4. **Rollback real.** Voltar para a versão anterior + restaurar o backup.

## 2. Estado atual (o que existe e o que falta)

| Componente                | Hoje                                                                                            | Gap                                                            |
| ------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `desktop/src/main.ts`     | `autoDownload=true`, `autoInstallOnAppQuit=true`; tray só mostra "aplicar" **depois** de baixar | Inverter para manual; buscar changelog antes; backup; rollback |
| `desktop/src/preload.ts`  | bridge de IPC (update-status read-only)                                                         | Adicionar approve/download/install/rollback                    |
| `update-server/worker.ts` | serve `latest.yml` + binários + telemetria; rollout/quarantine                                  | Endpoint de **changelog** por versão                           |
| `update-server` (scripts) | `config.yml` e `scripts/release.ts` citados no README **não existem**                           | Criar release.ts + schema de config                            |
| chat (renderer)           | recebe `vectora:update-status` mas sem UI dedicada                                              | Banner + modal de changelog + progresso + tela de rollback     |
| `CHANGELOG.md`            | —                                                                                               | Fonte das notas por versão                                     |

## 3. Arquitetura

```
   CI (tag v*)                Cloudflare Worker (R2 + KV)            Desktop (Electron)
 ┌─────────────┐   release   ┌───────────────────────────┐  feed  ┌────────────────────┐
 │ build nativo│ ──────────► │ R2: binários + changelog  │ ◄───── │ electron-updater   │
 │ + changelog │             │ KV: config.yml (rollout)  │        │ (autoDownload=OFF) │
 └─────────────┘             └───────────────────────────┘        └─────────┬──────────┘
                                                                            │ IPC
                                                                  ┌─────────▼──────────┐
                                                                  │ chat (renderer):   │
                                                                  │ banner+changelog+  │
                                                                  │ progresso+rollback │
                                                                  └────────────────────┘
```

### Sequência (caminho feliz)

```
1. App liga → 30s depois: autoUpdater.checkForUpdates()  (sem baixar nada)
2. update-available(vNova) → main BUSCA o changelog vAtual→vNova no worker
3. main → renderer: "vectora:update-available" { from, to, notesMarkdown }
4. Renderer mostra BANNER discreto "Atualização vNova disponível — Ver novidades"
5. Usuário abre o modal → lê o changelog renderizado
6. Usuário clica "Aprovar e baixar" → renderer → main "update-approve-download"
7. main: autoUpdater.downloadUpdate() → progresso → renderer (barra)
8. download pronto → renderer mostra "Instalar agora (faz backup)" / "Depois"
9. Usuário clica instalar → main faz BACKUP dos dados → autoUpdater.quitAndInstall()
10. App reinicia na vNova. Telemetria: completed.
```

Em nenhum ponto antes do passo 6 algo é baixado; antes do passo 9, nada é
instalado.

## 4. Contratos

### 4.1 Worker — novos/ajustados endpoints

```
GET /updates/:channel/:os/:arch/latest.yml      (existe) — manifesto electron-updater
GET /updates/:channel/:os/:arch/:version/:file  (existe) — binário/blockmap
POST /telemetry/update-result                   (existe) — estados de update
GET /changelog/:channel/:version?from=<vAtual>  (NOVO)   — notas acumuladas
```

`GET /changelog` retorna JSON:

```json
{
  "target": "1.4.0",
  "from": "1.2.0",
  "mandatory": false,
  "entries": [
    {
      "version": "1.4.0",
      "date": "2026-06-10",
      "notes": "## Novidades\n- ..."
    },
    { "version": "1.3.0", "date": "2026-05-22", "notes": "## ...\n- ..." }
  ]
}
```

As notas (`notes`) são markdown, renderizadas no modal. `mandatory` permite
marcar updates de segurança (ainda exigem clique, mas a UI deixa claro).

### 4.2 `config.yml` (em KV, schema)

```yaml
channels:
  latest:
    version: "1.4.0"
    rollout_percent: 25
    previous_stable: "1.3.0"
  beta:
    version: "1.5.0-beta.1"
    rollout_percent: 100
quarantined: ["1.3.1"] # versões bloqueadas por crash report (rollback automático de servidor)
```

### 4.3 IPC (preload bridge)

| Canal                             | Direção         | Payload                                  |
| --------------------------------- | --------------- | ---------------------------------------- |
| `vectora:update-available`        | main → renderer | `{ from, to, notesMarkdown, mandatory }` |
| `vectora:update-approve-download` | renderer → main | —                                        |
| `vectora:update-progress`         | main → renderer | `{ percent }`                            |
| `vectora:update-downloaded`       | main → renderer | `{ version }`                            |
| `vectora:update-install`          | renderer → main | `{ backup: boolean }`                    |
| `vectora:update-dismiss`          | renderer → main | —                                        |
| `vectora:update-rollback`         | renderer → main | `{ toVersion }`                          |
| `vectora:update-error`            | main → renderer | `{ message }`                            |
| `vectora:backups-list`            | renderer → main | → `Backup[]`                             |

## 5. Backup & Rollback

### Backup (antes de instalar)

- Antes do `quitAndInstall`, zipar a pasta de dados do usuário
  (`%USERPROFILE%\.vectora` no Windows; `~/.vectora` no \*nix) para
  `~/.vectora/backups/pre-update-<vAtual>-<timestamp>.zip`.
- Inclui `vectora.toml`, DB SQLite, settings; **exclui** caches.
- Retenção: manter os últimos **N=5** backups (limpa os mais antigos).

### Rollback (voltar versão)

`electron-updater` não tem downgrade nativo, então:

1. `autoUpdater.allowDowngrade = true`.
2. Apontar o feed para o manifesto da **versão anterior** (o worker mantém os
   binários antigos em R2; `previous_stable` no config).
3. `checkForUpdates → downloadUpdate → quitAndInstall` para a versão alvo.
4. Ao reiniciar na versão antiga, **restaurar** o backup de dados correspondente
   (descompactar o zip de `pre-update-<versão>` sobre `~/.vectora`).

A UI de rollback (em Configurações → Atualizações) lista as versões instaladas
recentemente + os backups disponíveis e oferece "Reverter para vX".

> **Quarantine automático** (servidor): se ≥3 crash-reports da mesma versão em 1h
> (telemetria já existente), o worker move a versão para `quarantined` e passa a
> servir `previous_stable` — isso é rollback _de frota_, complementar ao rollback
> manual do usuário.

## 6. Mudanças por arquivo

- **`update-server/src/worker.ts`** — endpoint `GET /changelog/...`; tipar
  `RuntimeConfig` com `previous_stable`/`mandatory`.
- **`update-server/scripts/release.ts`** _(novo)_ — sobe binários + `latest*.yml`
  para R2, gera `changelog/<versão>.json` a partir do `CHANGELOG.md`, atualiza
  `config.yml` no KV.
- **`update-server/config.yml`** _(novo)_ — seed inicial do schema acima.
- **`desktop/src/main.ts`** — `autoDownload=false`, `autoInstallOnAppQuit=false`;
  no `update-available` buscar changelog e repassar; handlers IPC
  approve/install/rollback; função de backup; downgrade.
- **`desktop/src/preload.ts`** — expor os novos canais no `contextBridge`.
- **chat (renderer)** _(novos componentes)_ — `UpdateBanner`, `ChangelogModal`,
  `UpdateProgress`, e seção "Atualizações" nas configurações (rollback/backups).
- **`CHANGELOG.md`** _(novo)_ — fonte das notas (Keep a Changelog).

## 7. Plano de implementação (fases)

1. **Worker + release.ts + config.yml** — feed de changelog funcionando.
2. **Electron main** — manual + changelog-antes + backup + quitAndInstall.
3. **Preload + UI do chat** — banner, modal de changelog, progresso, instalar.
4. **Rollback** — downgrade + restauração de backup + UI de versões/backups.
5. **Telemetria + testes** — estados (`changelog_viewed`, `approved`, `rolled_back`).

## 8. Decisões em aberto (preciso confirmar)

1. **Fonte do changelog:** mantenho `CHANGELOG.md` no repo (Keep a Changelog) e o
   `release.ts` extrai por versão? (recomendado) Ou notas da GitHub Release?
2. **Rollback inclui restaurar dados** automaticamente, ou só reinstala o binário
   antigo e pergunta se restaura o backup? (recomendo: perguntar)
3. **Escopo do backup:** só config + DB (`~/.vectora`), ou também workspaces?
4. **Canais expostos ao usuário:** só `latest`, ou habilito `beta` opt-in na UI?
