# OXC toolchain — JS/TS lint do Vectora Chat

> Bloco T.13. Substitui ESLint/Prettier residual por componentes da suite
> OXC (Rust). Ganho: lint ~50–100× mais rápido em CI e local.

## Componentes em uso

| Componente              | Status no Vectora                                                           | Comando                                           |
| ----------------------- | --------------------------------------------------------------------------- | ------------------------------------------------- |
| `oxlint`                | **Ativo** — pre-commit + `pnpm lint:oxc`                                    | `pnpm --dir chat exec oxlint`                     |
| `oxc-resolver`          | Indireto via Turbopack (Next 16)                                            | —                                                 |
| `oxc-formatter`         | **Aguardando GA** — alpha em 2026-06; promover quando estável               | —                                                 |
| `oxc-parser` (API Node) | Sob demanda em scripts                                                      | `import { parseSync } from '@oxc-parser/binding'` |
| `oxc-transformer`       | Sob demanda em scripts                                                      | —                                                 |
| `oxc-minify`            | **Pipeline CI** — após `next build`, antes do empacotamento Nuitka (T.12.6) | `oxc-minify chat/out/`                            |

## Config

- `chat/.oxlintrc.json` — preset com plugins `react`, `typescript`, `nextjs`,
  `unicorn`, `import`. Categorias `correctness`/`suspicious`/`perf` em `warn`
  para não bloquear o repo legado; vão subir para `error` por seção conforme
  o código for sendo migrado.
- Regras-chave em `error`: `react/jsx-key`.
- Plugins desligados: `style` (já coberto pelo prettier do pre-commit).

## Roadmap

1. **T.13.2** — quando `oxc-formatter` ficar estável, promover para hook
   primário e desligar o `prettier` (hoje ainda obrigatório no pre-commit).
2. **T.13.6** — adicionar step `oxc-minify chat/out/` no `runner.yml` antes
   do Nuitka packaging (T.12), reduzindo `_next/static/*.js` ~30–40%.
3. Endurecer o preset (categorias para `error`) conforme as warnings
   pendentes forem fechadas — ver `pnpm lint:oxc` para o backlog atual.
