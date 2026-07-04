<!-- markdownlint-disable MD033 MD041 -->

# Vectora — Monorepo

Monorepo da Vectora. Cada produto vive em sua própria pasta, com toolchain e
lockfile independentes. O que conecta tudo é o **GitHub Actions** (um workflow
por projeto, gated por path) e o **pre-commit** compartilhado na raiz.

## Estrutura

| Pasta                             | Projeto                                                                                                               | Stack                            | Deploy                               |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------- | -------------------------------- | ------------------------------------ |
| [`vectora/`](vectora/README.md)   | App Vectora (assistente de IA self-hosted)                                                                            | Python (uv) + Vite + Electron    | Docker (GHCR) + instaladores nativos |
| [`company/`](company/README.md)   | Site institucional                                                                                                    | TanStack Start + Vite (pnpm)     | Vercel → **vectora.company**         |
| [`docs/`](docs/README.md)         | Documentação                                                                                                          | Docusaurus (pnpm)                | Vercel → **docs.vectora.company**    |
| [`services/`](services/README.md) | Relay (OAuth/webhooks pro desktop) + updates (distribuição de releases) — era `relay/` + `update-server/`, unificados | Hono + Cloudflare Workers (pnpm) | Cloudflare (wrangler)                |
| `documents/`                      | Notas de design/planejamento (markdown interno)                                                                       | —                                | não publicado                        |

> O app em si (backend Python, frontend Vite, casca Electron) fica todo dentro
> de `vectora/` — veja [vectora/README.md](vectora/README.md) para detalhes de
> arquitetura, build e CLI.

## CI/CD (`.github/workflows/`)

Um workflow por projeto, **gated por path** (`on.push/pull_request.paths`): uma
mudança só no `vectora/` não dispara o build/deploy de `company`, `docs` etc.

| Workflow       | Dispara em              | Faz                                                                                                                      |
| -------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `vectora.yml`  | `vectora/**`, tags `v*` | lint • security • build • testes (unit/stress/integration/e2e) • Docker push (GHCR) • release nativo (Nuitka + Electron) |
| `company.yml`  | `company/**`            | lint/typecheck/test/build • deploy Vercel (master)                                                                       |
| `docs.yml`     | `docs/**`               | typecheck/build • deploy Vercel (master)                                                                                 |
| `services.yml` | `services/**`           | install/typecheck/test • deploy Cloudflare (master)                                                                      |
| `codeql.yml`   | master + agenda         | análise CodeQL (Python + Actions)                                                                                        |
| `triage.yml`   | issues                  | label `needs-triage` + boas-vindas                                                                                       |

### Secrets esperados

| Secret                                                                                                                                     | Usado por                                        |
| ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------ |
| `GOOGLE_API_KEY`, `COHERE_API_KEY`, `TAVILY_API_KEY`                                                                                       | testes do vectora                                |
| `GHCR_TOKEN`                                                                                                                               | push da imagem Docker (fallback: `GITHUB_TOKEN`) |
| `WIN_CERTIFICATE_BASE64`, `WIN_CERTIFICATE_PASSWORD`, `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID`, `VECTORA_RELEASES_TOKEN` | assinatura/publicação dos instaladores nativos   |
| `VERCEL_TOKEN`, `VERCEL_ORG_ID`                                                                                                            | deploy Vercel (company + docs)                   |
| `VERCEL_PROJECT_ID_COMPANY`, `VERCEL_PROJECT_ID_DOCS`                                                                                      | projeto Vercel de cada site                      |
| `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`                                                                                            | deploy do services                               |

## Desenvolvimento

Cada projeto é independente — entre na pasta e use o gerenciador dele:

```bash
# App Vectora (Python + Vite + Electron)
cd vectora && uv sync && uv run vectora start

# Site institucional
cd company && pnpm install && pnpm dev

# Docs
cd docs && pnpm install && pnpm dev

# Services (relay + updates)
cd services && pnpm install && pnpm dev
```

### Pre-commit (raiz)

O `.pre-commit-config.yaml` na raiz cobre todos os projetos (ruff/ty/bandit no
`vectora/`, prettier/oxlint/tsc no frontend, actionlint nos workflows):

```bash
pre-commit install
pre-commit run --all-files
```

## Licença

Proprietária. Consulte [LICENSE](./LICENSE).
