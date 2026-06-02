# Distribuição comercial (Bloco T.12)

> Visão geral de como o Vectora é empacotado e entregue para clientes pagos.

## Arquitetura

```
desktop/ (Electron shell, T.12.5)
└── vectora-core (binário Nuitka, T.12.4)
    ├── FastAPI + LangGraph + agent (backend)
    ├── chat/out/ (frontend Next.js, T.12.2 — bundleado como data dir)
    └── recursos (skills, templates, icons)
```

Cliente final recebe **um** instalador (`.msi`/`.dmg`/`.AppImage`).
Sem pip, sem npm, sem dependências externas.

## Componentes implementados

| Sub                           | Status      | Onde está                                                                                                                                            |
| ----------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| T.12.1 — Launcher único       | ✅          | `src/launcher.py` (faz gate de licença e delega para `src/main`)                                                                                     |
| T.12.2 — Bundle do frontend   | ✅ config   | `build/nuitka.toml` (`include_data_dirs = ["chat/out=chat_static"]`); o FastAPI já tem `serve_static=True`                                           |
| T.12.3 — Desacopla PyPI/NPM   | ⏳ pendente | Mudança em `.github/workflows/runner.yml` — remover `publish-pypi`/`publish-npm`, adicionar `release-binary` apontando para GitHub Releases privadas |
| T.12.4 — Nuitka core          | ✅ config   | `build/nuitka.toml` (onefile + plugins + data dirs). Build: `uv run nuitka --config-file=build/nuitka.toml src/launcher.py`                          |
| T.12.5 — Wrapper Electron     | ✅ skeleton | `desktop/src/main.ts` — spawn do Nuitka, BrowserWindow, tree-kill no quit, autoUpdater                                                               |
| T.12.6 — Instaladores nativos | ✅ config   | `desktop/electron-builder.yml` (Win NSIS/MSI + macOS DMG notarized + Linux AppImage/deb/rpm). Secrets de signing vêm do CI                           |
| T.12.7 — Licenciamento        | ✅          | `src/services/license.py` (validação remota + cache 6h/48h offline), `src/launcher.py` (gate), `src/api/handlers/license.py` (`GET /license/status`) |

## Fluxo de release (CI)

1. Push em `main` → GitHub Actions `runner.yml` é disparado.
2. Matrix por OS (Windows/macOS/Linux):
   1. `pnpm --dir chat install --frozen-lockfile`
   2. `pnpm --dir chat build`
   3. `pnpm --dir chat exec next export` → `chat/out/`
   4. **T.13.6**: `pnpm --dir chat exec oxc-minify chat/out/` (~30–40% redução)
   5. `uv sync --frozen`
   6. `uv run nuitka --config-file=build/nuitka.toml src/launcher.py` → `dist-nuitka/`
   7. `pnpm --dir desktop install && pnpm --dir desktop dist:<os>` → `desktop/dist-electron/`
3. Assinatura:
   - **Win**: cert EV (Azure Trusted Signing) via `CSC_LINK`/`CSC_KEY_PASSWORD`.
   - **macOS**: Apple Developer ID via `APPLE_ID`/`APPLE_APP_SPECIFIC_PASSWORD`/`APPLE_TEAM_ID` + notarize.
   - **Linux**: sem assinatura.
4. Upload para repo `brunosrz/vectora-releases` (privado) com `gh release create`.
5. Manifesto `latest.yml` (electron-builder gera) usado pelo autoUpdater.

## Licenciamento (T.12.7)

O Launcher (`src/launcher.py`) valida `VECTORA_TOKEN` antes de qualquer
subprocesso:

1. Lê `VECTORA_TOKEN` do ambiente (no Electron, vem injetado pelo
   instalador ou pelo `Settings → Licença`).
2. POST para `${VECTORA_LICENSE_URL}` (default: edge function Supabase
   `validate-license`).
3. Cache local em `~/.vectora/license_cache.json` — TTL 6h normal,
   48h em modo offline graceful.
4. Exporta `VECTORA_TIER=plus|pro` para o backend — camada storage (V) e
   cache (W) usam isso para recusar backends Pro quando `tier=plus`.

**Status endpoint** (`GET /license/status`) é público (sem auth) — usado
pelo trial banner no chat (E2 company) para mostrar amarelo ≤7d, vermelho
bloqueante quando expirado.

### Modos de bypass

- `VECTORA_LICENSE_BYPASS=1` — pula o gate inteiro. Uso **interno** apenas
  (CI, dev). Não documentar em produção.
- `VECTORA_LICENSE_URL=<custom>` — aponta para mock/staging.

## Setup do dev (sem build comercial)

Dev local não precisa do Launcher — `pnpm --dir chat dev` + `uv run vectora
server chat` continuam sendo o caminho. Para testar o Launcher localmente:

```bash
export VECTORA_LICENSE_BYPASS=1
uv run python -m src.launcher server chat
```

Para testar o Electron:

```bash
cd desktop
pnpm install
pnpm build
# Aponta para um binário Nuitka existente em ../dist-nuitka:
pnpm start
```

## Próximos passos (fora deste bloco)

- Stripe Customer Portal — `desktop` Settings → "Gerenciar assinatura" abre
  `create-portal` edge function via `shell.openExternal()`. Depende de B6
  do `docs/company.md`.
- Mirror PyPI somente-leitura do CLI Plus (sem frontend nem Electron) por
  compatibilidade com early adopters — resolve conflito com I1 da company.
- ACP server (Y4) integrado ao auto-update channel `acp-beta`.
