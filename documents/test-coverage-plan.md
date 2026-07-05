# Vectora — Plano de Cobertura de Testes (Integração Real + Contrato de Erro)

> Levantamento atual (agent de exploração, contagem de arquivos + leitura de
> amostra em cada diretório): **304 arquivos de teste** no monorepo, mas a
> distribuição é desbalanceada — a maioria é unitária com mock pesado, e
> quase nada exercita frontend e backend **de verdade**, na mesma chamada.
> Este documento planeja o reequilíbrio: ~300 testes novos de integração real
> (sem mock de rede entre as camadas que estão sendo testadas) e um contrato
> de erro HTTP único, hoje inexistente no backend Python.

---

## 1. Estado atual (levantado, não estimado)

| Subprojeto                    | Arquivos | Padrão                                                                                                |
| ----------------------------- | -------- | ----------------------------------------------------------------------------------------------------- |
| `vectora/tests/unit`          | 138      | Unitário, mock pesado de serviços/LLM                                                                 |
| `vectora/tests/integration`   | 5        | Real (SQLite/Postgres/Redis/Qdrant reais ou containers Docker) — mas só 5 arquivos pra todo o backend |
| `vectora/tests/e2e`           | 2        | Playwright real (`playwright.config.ts`), backend rodando de verdade em `127.0.0.1:8080`              |
| `vectora/tests/stress`        | 4        | Carga                                                                                                 |
| `vectora/frontend` (vitest)   | 101      | Componente/hook, `fetch`/APIs sempre mockadas                                                         |
| `services/tests`              | 25       | Real (`cloudflare:test`, D1 em memória de verdade, `worker.fetch(...)`)                               |
| `company/src/**/*.test.ts(x)` | 31       | Componente, `servicesFetch` sempre mockado — zero chamada real ao `services/`                         |

**Os dois padrões "real" que já existem e devem ser o molde**:
`vectora/tests/integration/test_api_background.py` (SQLite real a partir de
`tmp_path`, roda migrations de verdade) e `services/tests/index.test.ts`
(`worker.fetch(req, env, ctx)` contra D1 real via `cloudflare:test`). Nenhum
teste hoje conecta **duas camadas de verdade ao mesmo tempo** (frontend
chamando um backend real rodando, ou `company` chamando um `services` real
rodando) — os 2 specs de `vectora/tests/e2e/` são a única exceção, e cobrem
só streaming e recuperação de sessão.

## 2. Contrato de erro — hoje não existe

`backend/api/` não tem exception handler global. Toda rota levanta
`HTTPException(status_code=..., detail=...)` isoladamente — `detail` é uma
string livre, às vezes em português, às vezes em inglês, sem `code` máquina-
legível. O único formato estruturado que existe é `ErrorEvent` (`backend/api/
schemas.py`), e é exclusivo de eventos SSE de streaming — não se aplica a uma
resposta HTTP de erro comum (ex.: 401 de rota REST, 404 de recurso).

**Contrato proposto**, aplicado via `@app.exception_handler(HTTPException)`
em `backend/api/server.py`:

```json
{ "error": { "code": "AUTH_REQUIRED", "message": "Não autenticado." } }
```

- `code`: string estável em `SCREAMING_SNAKE_CASE`, um enum por família de
  erro (`AUTH_REQUIRED`, `FORBIDDEN`, `NOT_FOUND`, `VALIDATION_ERROR`,
  `CONFLICT`, `RATE_LIMITED`, `INTERNAL`) — é o que o frontend passa a
  dispatchar sobre, em vez de fazer `if (detail.includes(...))` (padrão
  frágil que hoje aparece em alguns pontos do cliente).
- `message`: a mesma string humana que já existe hoje (sem quebrar nada
  visualmente).
- Volume adicional: cada `HTTPException(...)` do código atual ganha um
  `code=` explícito (kwarg novo em uma subclasse `ApiError(HTTPException)`
  que o handler sabe desembrulhar; `HTTPException` cru sem `code` cai em
  `INTERNAL` por default, nunca quebra rota que não foi tocada ainda).
- `frontend/lib/api/vectora-client.ts`: novo parser único de erro de
  resposta não-2xx, substituindo os parses ad-hoc espalhados por hook.

Essa mudança é pré-requisito de boa parte dos testes de "caminho de erro" da
seção 4 — sem `code` estável, testar "o erro certo apareceu" vira comparar
string livre, frágil por design.

## 3. Onde os testes de integração real vão morar

Nenhum diretório novo greenfield — expande os três padrões reais que já
existem, em vez de inventar um quarto:

- **`vectora/tests/integration/`**: `TestClient` (FastAPI) real + SQLite real
  (não mockado) por módulo de rota (`auth`, `chat`, `workspaces`, `rag`,
  `admin` quando aplicável, `git`, `mcp`). Roda migrations reais em
  `tmp_path`, mesmo padrão de `test_api_background.py`.
- **`services/tests/`**: expande os specs existentes por família de rota
  (`admin`, `billing`, `auth`, `gifts`, `coupons`) com os casos de borda que
  o plano de RBAC (`rustling-hatching-summit.md`) já cobriu parcialmente —
  aqui é aprofundar, não recriar.
- **`vectora/tests/e2e/`** e um `company/tests-e2e/` novo (Playwright,
  mesma dependência já presente em `devDependencies` da raiz do frontend,
  só falta o `playwright.config.ts` equivalente em `company/`): fluxos que
  exigem duas camadas rodando de verdade ao mesmo tempo — chat completo
  (frontend real → backend real, sem mock de LLM quando a chave existir no
  ambiente de CI, com skip automático quando não existir, mesmo padrão já
  usado em `test_mcp_tools.py`), e em `company/` o fluxo signup → checkout
  (Stripe test mode) → dashboard → admin.

## 4. Distribuição das ~300 novas

| Bloco                                                                                     | Qtde aprox. | Onde                                      |
| ----------------------------------------------------------------------------------------- | ----------- | ----------------------------------------- |
| Backend real (rota completa via `TestClient`, por handler)                                | 120         | `vectora/tests/integration/`              |
| `services/` — aprofundamento de casos de borda (RBAC, cupom, presente, plano)             | 60          | `services/tests/`                         |
| Contrato de erro (todo handler novo/tocado, 400/401/403/404/409/422/500 → mesmo envelope) | 40          | Ambos acima, mesmo arquivo do teste feliz |
| Playwright `vectora/tests/e2e/` (chat, workbench, RAG fim-a-fim)                          | 40          | `vectora/tests/e2e/`                      |
| Playwright `company/` novo (signup, checkout, admin, gift redemption)                     | 40          | `company/tests-e2e/` (novo)               |

Total: 300. O par feliz/erro exigido pelo CLAUDE.md (§18) entra **no mesmo
teste** de cada bloco, não em arquivos separados — os 40 "contrato de erro"
da tabela acima são o piso mínimo de cobertura de borda que ainda não existe
hoje nos handlers mais críticos (auth, billing, admin), não uma contagem à
parte de tudo que precisa de par erro.

## 5. Ordem de execução (cada item é um sprint com commit próprio)

1. Contrato de erro no backend Python (`ApiError` + handler + migração dos
   `HTTPException` mais usados: auth, billing-adjacent, workspaces).
2. Parser único de erro no `vectora-client.ts` + ajuste dos hooks que hoje
   fazem parse ad-hoc.
3. `vectora/tests/integration/` — expandir por handler, na ordem de
   criticidade: `auth` → `chat` → `workspaces` → `rag` → `git`.
4. `services/tests/` — aprofundar RBAC/billing/coupons/gifts.
5. Playwright `vectora/tests/e2e/` novos specs.
6. Playwright `company/` — setup do zero (`playwright.config.ts`,
   `tests-e2e/`) + specs de signup/checkout/admin.

## 6. Fora de escopo aqui

- Testes de carga/stress (já cobertos por `vectora/tests/stress/`, não faz
  parte da queixa de "muito mock, pouca integração real").
- Reescrever os 138 unitários existentes — eles continuam válidos como
  primeira linha de defesa; o problema é a ausência de uma segunda camada
  real, não a existência da primeira.
