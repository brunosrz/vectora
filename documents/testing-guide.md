# TDD no Vectora — Padrões de Backend e Frontend

Referência normativa para escrever e avaliar testes no monorepo. Complementa
o §18 do CLAUDE.md (filosofia geral). Este documento descreve os padrões
**concretos e já estabelecidos** no codebase — não aspirações abstratas.

Cobre os quatro subprojetos com suíte de testes: `vectora/` (Python + React),
`vectora/frontend/` (Playwright e2e), `services/` (Cloudflare Worker) e
`company/` (site/dashboard).

---

## Filosofia (resumo do §18 CLAUDE.md)

| Princípio                     | O que significa na prática                                                                               |
| ----------------------------- | -------------------------------------------------------------------------------------------------------- |
| **TDD**                       | Teste antes da feature/fix. Bug → reproduzir com teste antes de corrigir                                 |
| **Reconstrução pelos testes** | A suíte completa deve descrever o contrato — sem o código de produção, os testes guiam a reimplementação |
| **Foco no erro**              | Todo teste de caminho feliz tem o par de erro/borda **no mesmo teste/arquivo**                           |
| **Edge cases obrigatórios**   | Vazio, null, limite, duplicado, ordem trocada, payload malformado, concorrência                          |
| **Saída enxuta**              | Apenas falhas e avisos aparecem; sucessos são pontos (reporter `dot`)                                    |

---

## Backend Python (`vectora/tests/`, pytest + asyncio)

### Estrutura de diretório

```
tests/unit/test_<módulo>.py             # sem dependências externas, roda sempre
tests/integration/test_<fluxo>_*.py     # sobe infra local (docker) ou serviços reais
tests/e2e/test_agent_live_runs.py       # fluxo completo com LLM real (marker "live")
tests/stress/test_<coisa>.py            # carga/concorrência, sem APIs externas
```

Arquivo de teste unitário tem no máximo uma responsabilidade: um módulo ou
handler. Se cobre mais de um, divide.

### Markers (`pyproject.toml::[tool.pytest.ini_options]`)

| Marker           | Significado                                                                                    |
| ---------------- | ---------------------------------------------------------------------------------------------- |
| `live`           | Sem mock — chama LLM/Tavily reais. Custa API real; só roda via `scons tests-live`              |
| `storage`        | Integração de storage (Postgres, Redis, Qdrant, SQLite, LanceDB) — sobe docker automaticamente |
| `integration`    | Testes de integração com APIs reais (requer `GOOGLE_API_KEY` + `COHERE_API_KEY`)               |
| `e2e`            | End-to-end com APIs reais                                                                      |
| `stress`         | Carga e concorrência — sem APIs externas, só infra local                                       |
| `browser`        | Sobe Chromium real via Playwright (`playwright install chromium`)                              |
| `frontend_build` | Sobe o backend real servindo `frontend/dist` (`pnpm --dir frontend build` antes)               |
| `electron_dev`   | Sobe o build dev do Electron real (`scons frontend`)                                           |
| `singularity`    | Escape real do sandbox Singularity/Apptainer — requer binário instalado, deselecionado no CI   |
| `lifecycle`      | Testes sequenciais de ciclo de vida (dependem de ordem)                                        |

`-m "not live"` é o filtro padrão do CI para `tests/unit`; `-m "not storage and
not singularity"` é o filtro para `tests/integration`.

### `conftest.py` raiz — watchdog de shutdown travado

`tests/conftest.py` registra `pytest_unconfigure` que força `os._exit()`
depois do summary/coverage serem emitidos. Isso existe porque alguns
recursos (ex.: o `Observer` do watchdog usado no SSE de eventos de
workspace) podem deixar threads não-daemon vivas; sem essa rede, o processo
do pytest imprime "N passed" e nunca sai, travando a CI. Também expõe
utilitários (`_free_port`, `_wait_port_open`) usados para subir o backend
real como subprocesso em `tests/integration` e `tests/e2e`.

### Cabeçalho padrão

```python
"""Testes para backend/api/handlers/context_graph.py.

Cobre: <o que é verificado em uma linha por classe>.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
```

`from __future__ import annotations` é obrigatório — mantém compatibilidade
com `ty` e evita erros de avaliação tardia de type hints.

### Organização em classes

Agrupa por comportamento, não por arquivo:

```python
class TestHealth:
    def test_returns_ok(self, client): ...

class TestGetTools:
    def test_lista_tools_sem_erro_de_import(self, client): ...
```

A classe é o "contexto" (estado de entrada); os métodos são as variações.
Nomes em `test_<o_que_acontece_quando_X>`.

### Fixtures

Preferir fixtures de escopo `function` (default). `scope="module"` apenas
quando o setup é caro (ex: `TestClient` do FastAPI) e os testes não mudam
estado compartilhado:

```python
@pytest.fixture(scope="module")
def headless_app():
    os.environ["VECTORA_AUTH_REQUIRED"] = "false"
    from backend.api.server import create_app
    return create_app()


@pytest.fixture(scope="module")
def client(headless_app):
    return TestClient(headless_app, raise_server_exceptions=False)
```

Fixtures utilitárias simples ficam como funções normais (não `@fixture`):

```python
def _make_registry(tmp_path: Path) -> tuple[MagicMock, MagicMock]:
    ws = MagicMock()
    ws.cwd = str(tmp_path)
    registry = MagicMock()
    registry.get = MagicMock(return_value=ws)
    return registry, ws
```

### Imports dentro dos testes (lazy)

Imports de `backend.*` ficam **dentro** do corpo do teste ou do método — não
no topo do arquivo. Isso isola falhas de import e evita efeitos colaterais no
nível de módulo:

```python
def test_not_built_when_graph_json_absent(self, tmp_path):
    from backend.api.handlers.context_graph import _status_from_disk
    ...
```

### Mock de dependências externas

**Registry de workspace** — o padrão mais comum no codebase:

```python
with patch("backend.services.workspace.workspace_registry", registry):
    result = _graph_dir("ws1")
```

Sempre patcha `backend.services.workspace.workspace_registry` (onde o objeto
vive), não o caminho do módulo que o importa — funciona mesmo com lazy imports.

**Filesystem** — usar `tmp_path` do pytest, nunca criar arquivos fora dele:

```python
def _write_graph(tmp_path: Path, data: dict) -> Path:
    d = tmp_path / ".vectora" / "graph"
    d.mkdir(parents=True, exist_ok=True)
    (d / "graph.json").write_text(json.dumps(data), encoding="utf-8")
    return d
```

**Request do FastAPI** — mock direto sem TestClient:

```python
def _fake_request(user_id: str = "u1") -> MagicMock:
    req = MagicMock()
    req.state.user = MagicMock()
    req.state.user.id = user_id
    return req
```

**Variáveis de ambiente** — `monkeypatch.setenv` (nunca `os.environ` direta):

```python
def test_uses_custom_host(monkeypatch):
    monkeypatch.setenv("VECTORA_HOST", "0.0.0.0")
    from backend.settings import Settings
    assert Settings().host == "0.0.0.0"
```

### Testes assíncronos

`asyncio_mode = "auto"` no `pyproject.toml` — `async def test_*` roda sem
precisar de `@pytest.mark.asyncio` explícito (o marker ainda aparece em
código legado, mas não é obrigatório em teste novo):

```python
async def test_query_matches_by_label(self, tmp_path):
    from backend.api.handlers.context_graph import QueryRequest, post_query
    ...
    resp = await post_query(_fake_request(), "ws1", QueryRequest(question="auth"))
    assert any(n["id"] == "n_auth" for n in resp.nodes)
```

### Par feliz + erro (obrigatório)

```python
class TestPostExplain:
    async def test_returns_node_and_neighbors(self, tmp_path):
        # caminho feliz — nó existe
        ...
        assert "n_auth" in {n["id"] for n in resp.nodes}

    async def test_raises_404_for_unknown_node(self, tmp_path):
        # caminho de erro — nó inexistente
        with pytest.raises(HTTPException) as exc:
            await post_explain(req, "ws1", ExplainRequest(node_id="ghost"))
        assert exc.value.status_code == 404
```

### O que testar vs. o que não testar

| Testar                                          | Não testar                                 |
| ----------------------------------------------- | ------------------------------------------ |
| Funções puras e helpers                         | `__init__.py` vazio                        |
| Lógica de negócio nos services                  | Wiring de DI do FastAPI                    |
| Contratos dos endpoints (status codes, schemas) | Código portado/externo sem lógica própria  |
| Casos de erro e edge cases                      | Implementações 100% delegadas ao framework |
| Stores, hooks, utils                            | Routes/handlers que só chamam um service   |

**Código portado de terceiros** (ex: os módulos de extração/detecção sob
`backend/services/context_graph/`, derivados de graphify) — a estratégia é
testar a **interface pública** (`pipeline.py::build_workspace_graph`,
`cache.py`) que os chama, não cada linha interna. Atingir 100% nesse código
requereria reescrever os testes do projeto original — fora de escopo. O que
garante confiança é o teste end-to-end do pipeline.

---

## Frontend do produto (`vectora/frontend/`, vitest + jsdom + Testing Library)

### Estrutura de arquivo

```
components/<área>/__tests__/<componente>.test.tsx
lib/hooks/<área>/__tests__/<hook>.test.ts
lib/stores/__tests__/<store>.test.ts
electron/src/__tests__/<módulo>.test.ts    # funções puras do processo main
```

### Cabeçalho obrigatório para componentes/hooks com DOM

```typescript
// @vitest-environment jsdom
```

Sem isso o vitest roda em Node e `document`, `window`, `fetch` não existem.

### Importação após os mocks

Todos os `vi.mock(...)` devem vir **antes** do `import` do módulo testado.
O vitest iça (hoists) os mocks mas a ordem de leitura importa para clareza:

```typescript
// 1. mocks
vi.mock("@/lib/stores/workspaces-store", () => ({ ... }));
vi.mock("@/lib/hooks/use-context-graph", () => ({ ... }));

// 2. import do módulo testado — depois dos mocks
import { ContextGraphTab } from "@/components/workbench/tabs/context-graph-tab";
```

### Mock do Paraglide (`m`)

Padrão universal — retorna o nome da chave como string, sem precisar
compilar o Paraglide:

```typescript
vi.mock("@/lib/paraglide/messages", () => ({
  m: new Proxy(
    {},
    {
      get:
        (_t, prop) =>
        (..._args: unknown[]) =>
          String(prop),
    },
  ),
}));
```

Com isso `m.graph_not_built()` retorna `"graph_not_built"` — testável com
`screen.getByText("graph_not_built")`.

### Mock de stores Zustand

```typescript
vi.mock("@/lib/stores/workspaces-store", () => ({
  useWorkspacesStore: (sel: (s: { active_id: string }) => unknown) =>
    sel({ active_id: "ws1" }),
}));
```

Simula apenas os campos que o componente usa. Não mockar o store inteiro.

### Mock de hooks

Quando o componente depende de um hook complexo (com fetch, efeitos, polling),
mocka o hook inteiro em vez de mockar o fetch interno:

```typescript
const mockBuild = vi.fn();
const mockUseContextGraph = vi.fn();

vi.mock("@/lib/hooks/use-context-graph", () => ({
  useContextGraph: (...args: unknown[]) => mockUseContextGraph(...args),
}));

function setup(overrides = {}) {
  mockUseContextGraph.mockReturnValue({
    status: { status: "not_built" },
    report: null,
    loading: false,
    build: mockBuild,
    ...overrides,
  });
}
```

### Mock de `fetch` global

```typescript
const FETCH_MOCK = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", FETCH_MOCK);
  FETCH_MOCK.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function mockOk(body: object): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
```

### `act()` para atualizações assíncronas de estado

```typescript
const { result } = renderHook(() => useContextGraph("ws1"));
await act(async () => {});

await act(async () => {
  fireEvent.click(btn);
});

await act(async () => {
  await result.current.build({ model: "gpt-4o" });
});
```

Omitir o `act` não falha o teste mas gera warnings no console — inaceitável.

### cleanup e isolamento entre testes

```typescript
afterEach(() => {
  cleanup(); // desmonta DOM do React
  vi.clearAllMocks(); // reseta call counts e implementações
});
```

### Organização dos testes de componente

Agrupa por **estado do componente**, não por elemento de DOM:

```typescript
describe("ContextGraphTab", () => {
  describe("estado not_built", () => {
    it("exibe mensagem graph_not_built", () => { ... });
    it("clicar no botão chama build()", async () => { ... });
  });

  describe("estado error", () => {
    it("exibe a mensagem de erro", () => { ... });
  });
});
```

### Seletores preferidos

| Preferir                                         | Evitar                                                             |
| ------------------------------------------------ | ------------------------------------------------------------------ |
| `screen.getByText("graph_not_built")`            | `container.querySelector(".some-class")`                           |
| `screen.getByRole("button", { name: /build/i })` | `screen.getByTestId(...)` (só quando não há alternativa semântica) |

`data-testid` é adicionado no componente **somente** quando não há forma
semântica de selecionar o elemento.

### e2e de frontend — Playwright (`vectora/frontend/e2e/`)

Distinto do vitest: usa `@playwright/test`, roda contra o app real (backend +
SPA servida), não jsdom. Arquivos `*.spec.ts` (não `*.test.ts`) — o
`vitest.config.ts` exclui `e2e/**` explicitamente para as duas suítes não
colidirem. Config em `playwright.config.ts`; `global-setup.ts` prepara o
ambiente (usuário/sessão) antes da suíte. Cobre fluxos como streaming de
chat, workflow de git, recuperação de sessão e abas do workbench — um
arquivo por fluxo (`streaming.spec.ts`, `git-workflow.spec.ts`,
`workbench-tabs.spec.ts` etc.). Roda via `pnpm test:e2e`, fora do `scons
tests` (que só cobre a suíte vitest do frontend).

---

## `services/` — Cloudflare Worker (gateway + updates), vitest + Workers pool

`services/vitest.config.ts` declara dois `projects`:

- **`workers`** (`tests/**/*.test.ts`, exceto `tests/scripts/**`) — roda no
  runtime real `workerd` via `@cloudflare/vitest-pool-workers`, com bindings
  simulados (`kvNamespaces`, `r2Buckets`, `d1Databases`, `durableObjects`,
  filas) configurados contra `wrangler.test.toml` (não o `wrangler.toml` de
  produção). Cobertura usa provider `istanbul` — o coverage nativo v8 do
  vitest não instrumenta `workerd`.
- **`node`** (`tests/scripts/**/*.test.ts`) — CLI Node puro (ex.: script de
  release), roda no pool default do Node porque não usa nenhuma API do
  Worker; rodar no pool `workerd` quebraria o teardown (`fs`/`child_process`
  reais não existem no isolate sandboxed).

Segredos/credenciais de teste são fixados como bindings estáticos no config
(nunca lidos do `.env` real) para manter a suíte hermética — variáveis como
`TURNSTILE_SECRET_KEY` ficam vazias de propósito para desligar a checagem
externa durante os testes.

```typescript
describe("hashPassword/verifyPassword", () => {
  it("hashes in the self-describing pbkdf2$iter$salt$hash format and verifies the same password", async () => {
    const hash = await hashPassword("correct horse battery staple");
    expect(hash).toMatch(/^pbkdf2\$100000\$[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+$/);
  });

  it("rejects a wrong password, a malformed hash, and an unsupported algorithm tag", async () => {
    ...
  });
});
```

Nomenclatura em inglês nas descrições é aceita neste subprojeto (segue o
padrão já estabelecido nos testes de `services/`); Python e o frontend do
produto usam descrições em português.

Rodar: `pnpm --dir services run test`.

---

## `company/` — site/dashboard, vitest + jsdom + Testing Library

Mesmo empilhamento do frontend do produto (vitest + jsdom + React Testing
Library), mas projeto separado com seu próprio `vitest.config.ts`
(`environment: "jsdom"`, plugin `@vitejs/plugin-react`). Padrão de mock de
dependência de servidor (TanStack Start `server/fns/*`):

```typescript
// @vitest-environment jsdom
const { mockGetSession } = vi.hoisted(() => ({ mockGetSession: vi.fn() }));

vi.mock("#/server/fns/auth", () => ({ getSession: mockGetSession }));

describe("useSession", () => {
  it("expõe o usuário autenticado após resolver", async () => {
    mockGetSession.mockResolvedValue({ id: "u1", email: "a@b.com" });
    const { result } = renderHook(() => useSession(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ id: "u1", email: "a@b.com" });
  });

  it("expõe null quando não há sessão (edge — visitante anônimo)", async () => {
    mockGetSession.mockResolvedValue(null);
    ...
  });
});
```

`vi.hoisted` é necessário aqui porque o mock referencia a variável antes de
`vi.mock` ser içado. Rodar: `pnpm --dir company run test` (ou o `lint`/`tsc
--noEmit` equivalentes para type-check).

---

## Cobertura — o que medir e o que ignorar

O `vitest.config.ts` (frontend do produto) e o `pyproject.toml` já
configuram os `exclude` corretos.

| Incluir na cobertura                            | Excluir da cobertura                                                                                  |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `lib/**`, `components/**`, `src/**`, `hooks/**` | `lib/paraglide/**` (gerado)                                                                           |
| `backend/`                                      | Código portado de terceiros (internals de `context_graph`)                                            |
| Hooks, stores, utils                            | Bootstrap/wiring (`src/main.tsx`, `src/router.tsx`, `components/providers/**`, `components/icons/**`) |
| Services, handlers                              | Presets de tema/tipos puros (`lib/theme/**`, `lib/types/**`)                                          |

**Código portado** tem baixa cobertura por design — é código de terceiros
adaptado. O que garante confiança é o teste da interface pública que o
envolve, com casos felizes e de erro.

**Meta de cobertura** não é 100% global — é "zero arquivos próprios com 0%
e zero caminhos críticos sem par de erro". `skipFull: true` no reporter de
texto oculta os arquivos já 100% cobertos para focar no gap (o relatório
HTML mantém tudo).

---

## Comandos de referência

```powershell
# Backend — rodar uma suíte/teste específico
cd vectora
uv run pytest tests/unit/test_context_graph_api.py -q --tb=short
uv run pytest tests/ -k "test_chat" -q --tb=short

# Backend — cobertura de um módulo
uv run pytest tests/unit/test_context_graph_api.py --cov=backend.api.handlers.context_graph --cov-report=term-missing

# Frontend do produto — rodar um teste específico
pnpm --dir vectora/frontend exec vitest run lib/hooks/__tests__/use-context-graph.test.ts

# Frontend do produto — e2e Playwright
pnpm --dir vectora/frontend run test:e2e

# services (Cloudflare Worker)
pnpm --dir services run test

# company
pnpm --dir company run test

# Suíte completa (raiz do monorepo) — vectora (vitest+pytest) + services + company
scons tests             # sem cobertura
scons coverage          # com cobertura (vectora/htmlcov/, frontend/coverage/, services/coverage/)
scons tests-storage     # só tests/integration com marker "storage" (sobe docker)
scons tests-live        # só testes com marker "live" — custa API real, nunca em scons tests
scons lint              # ruff+ty+bandit (vectora) + tsc+oxlint (frontend) + tsc+eslint (company) + tsc (services, docs)
```

### Pipeline de CI (`.github/workflows/vectora.yml`)

Roda sempre — em todo PR contra `master` e em todo push em `master` (merge
de PR), sem gate manual. Só a etapa 7 continua condicionada, agora numa tag
`v*` de verdade (criada pelo merge do PR de release acumulado que
`release-please.yml` mantém) ou disparo manual — não mais `[up-release]`.

1. **lint** — ruff + ty (Python).
2. **security** — bandit + pip-audit (`|| true`, não bloqueia o merge).
3. **frontend** — i18n compile, oxlint, `tsc --noEmit`, `pnpm test` (vitest).
4. **build_verification** — compila o backend (`compileall`) e builda a SPA.
5. **test-unit** — `pytest tests/unit -m "not live" --cov=backend` +
   `pytest tests/stress`.
6. **test-external** — `pytest tests/integration -m "not storage and not
singularity"` + `pytest tests/e2e` (precisam de chaves de API reais via
   secrets do repositório).
7. **release-native** — matriz Linux/macOS/Windows (Nuitka + Electron), só
   numa tag `v*` ou disparo manual.
