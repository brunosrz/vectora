# TDD no Vectora — Padrões de Backend e Frontend

Referência normativa para escrever e avaliar testes no projeto. Complementa
o §18 do CLAUDE.md (filosofia geral). Este documento descreve os padrões
**concretos e já estabelecidos** no codebase — não aspirações abstratas.

---

## Filosofia (resumo do §18 CLAUDE.md)

| Princípio                     | O que significa na prática                                                                               |
| ----------------------------- | -------------------------------------------------------------------------------------------------------- |
| **TDD**                       | Teste antes da feature/fix. Bug → reproduzir com teste antes de corrigir                                 |
| **Reconstrução pelos testes** | A suíte completa deve descrever o contrato — sem o código de produção, os testes guiam a reimplementação |
| **Foco no erro**              | Todo teste de caminho feliz tem o par de erro/borda **no mesmo arquivo**                                 |
| **Edge cases obrigatórios**   | Vazio, null, limite, duplicado, payload malformado, workspace inexistente                                |
| **Saída enxuta**              | Apenas falhas e avisos aparecem; successos são pontos                                                    |

---

## Backend (pytest + asyncio)

### Estrutura de arquivo

```
tests/unit/test_<módulo>.py
tests/integration/test_<módulo>_integration.py
tests/e2e/test_<fluxo>.py
```

Arquivo de teste unitário tem no máximo uma responsabilidade: um módulo ou
handler. Se cobre mais de um, divide.

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
class TestStatusFromDisk:
    def test_not_built_when_graph_json_absent(self, tmp_path): ...
    def test_done_counts_nodes_and_edges(self, tmp_path): ...
    def test_workspace_missing_raises_404(self): ...
```

A classe é o "contexto" (estado de entrada); os métodos são as variações.
Nomes em `test_<o_que_acontece_quando_X>`.

### Fixtures

Preferir fixtures de escopo `function` (default). `scope="module"` apenas
quando o setup é caro (ex: `TestClient` do FastAPI) e os testes não mudam
estado compartilhado.

```python
@pytest.fixture(scope="module")
def client():
    os.environ["VECTORA_AUTH_REQUIRED"] = "false"
    from backend.api.server import create_app
    app = create_app(serve_static=False)
    from fastapi.testclient import TestClient
    return TestClient(app, raise_server_exceptions=False)
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

```python
@pytest.mark.asyncio
async def test_query_matches_by_label(self, tmp_path):
    from backend.api.handlers.context_graph import QueryRequest, post_query
    ...
    resp = await post_query(_fake_request(), "ws1", QueryRequest(question="auth"))
    assert any(n["id"] == "n_auth" for n in resp.nodes)
```

### Par feliz + erro (obrigatório)

```python
class TestPostExplain:
    @pytest.mark.asyncio
    async def test_returns_node_and_neighbors(self, tmp_path):
        # caminho feliz — nó existe
        ...
        assert "n_auth" in {n["id"] for n in resp.nodes}

    @pytest.mark.asyncio
    async def test_raises_404_for_unknown_node(self, tmp_path):
        # caminho de erro — nó inexistente
        with pytest.raises(HTTPException) as exc:
            await post_explain(req, "ws1", ExplainRequest(node_id="ghost"))
        assert exc.value.status_code == 404
```

### O que testar vs. o que não testar

| Testar                                          | Não testar                                         |
| ----------------------------------------------- | -------------------------------------------------- |
| Funções puras e helpers                         | `__init__.py` vazio                                |
| Lógica de negócio nos services                  | Wiring de DI do FastAPI                            |
| Contratos dos endpoints (status codes, schemas) | Código portado/externo sem lógica própria          |
| Casos de erro e edge cases                      | Implementações que são 100% delegadas ao framework |
| Stores, hooks, utils                            | Routes/handlers que só chamam um service           |

**Código portado de terceiros** (ex: `backend/services/context_graph/extract.py`,
`detect.py`, `export.py`) — a estratégia é testar a **interface pública**
(`pipeline.py::build_workspace_graph`, `cache.py`) que os chama, não cada
linha interna. Atingir 100% nesse código requereria reescrever os testes do
projeto original — fora de escopo. O que garante confiança é o teste
end-to-end do pipeline.

---

## Frontend (vitest + jsdom + Testing Library)

### Estrutura de arquivo

```
components/<área>/__tests__/<componente>.test.tsx
lib/hooks/__tests__/<hook>.test.ts
lib/stores/__tests__/<store>.test.ts
```

### Cabeçalho obrigatório para componentes/hooks com DOM

```typescript
// @vitest-environment jsdom
```

Sem isso o vitest roda em Node e `document`, `window`, `fetch` não existem.

### Importação após os mocks

Todos os `vi.mock(...)` devem vir **antes** do `import` do módulo testado.
O vitest iça (hoists) os mocks mas a order de leitura importa para clareza:

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
    getHtmlUrl: vi.fn(() => "/workspaces/ws1/context-graph/html"),
    fetchStatus: vi.fn(),
    ...overrides,
  });
}
```

### Mock de `fetch` global

Para testes de hooks que fazem chamadas HTTP:

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

Qualquer interação que dispara setState (efeito, clique, await) deve estar
dentro de `act`:

```typescript
// montar e aguardar efeitos iniciais
const { result } = renderHook(() => useContextGraph("ws1"));
await act(async () => {});

// interação do usuário
await act(async () => {
  fireEvent.click(btn);
});

// chamada assíncrona do hook
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

`cleanup()` é do `@testing-library/react`. `vi.clearAllMocks()` limpa
`.mock.calls` sem remover a implementação (use `vi.resetAllMocks()` se
quiser resetar também a implementação).

### Organização dos testes de componente

Agrupa por **estado do componente**, não por elemento de DOM:

```typescript
describe("ContextGraphTab", () => {
  describe("estado not_built", () => {
    it("exibe mensagem graph_not_built", () => { ... });
    it("botão está habilitado", () => { ... });
    it("clicar no botão chama build()", async () => { ... });
  });

  describe("estado running", () => {
    it("exibe spinner", () => { ... });
    it("botão está desabilitado", () => { ... });
  });

  describe("estado error", () => {
    it("exibe a mensagem de erro", () => { ... });
    it("exibe mensagem genérica se error é null", () => { ... });
  });
});
```

### Seletores preferidos

| Preferir                                         | Evitar                                                             |
| ------------------------------------------------ | ------------------------------------------------------------------ |
| `screen.getByText("graph_not_built")`            | `container.querySelector(".some-class")`                           |
| `screen.getByRole("button", { name: /build/i })` | `screen.getByTestId(...)` (só quando não há alternativa semântica) |
| `document.querySelector("[data-testid='x']")`    | Seletores por class ou tag genérica                                |

Atributos `data-testid` são adicionados no componente **somente** quando não
há forma semântica de selecionar o elemento.

### Par feliz + erro nos hooks

```typescript
it("busca status ao montar com workspaceId válido", async () => {
  FETCH_MOCK.mockResolvedValueOnce(mockOk({ status: "not_built" }));
  const { result } = renderHook(() => useContextGraph("ws1"));
  await act(async () => {});
  expect(result.current.status.status).toBe("not_built");
});

it("fetch com erro de rede não quebra o hook", async () => {
  FETCH_MOCK.mockRejectedValueOnce(new Error("offline"));
  const { result } = renderHook(() => useContextGraph("ws1"));
  await act(async () => {});
  expect(result.current.status.status).toBe("unknown"); // fallback
});
```

---

## Cobertura — o que medir e o que ignorar

O `vitest.config.ts` e o `pyproject.toml` já configuram os `exclude` corretos.
Regra geral:

| Incluir na cobertura      | Excluir da cobertura                             |
| ------------------------- | ------------------------------------------------ |
| `lib/**`, `components/**` | `lib/paraglide/**` (gerado)                      |
| `backend/`, `tests/`      | Código portado de terceiros (graphify internals) |
| Hooks, stores, utils      | Wiring de rotas (`src/routes/**`)                |
| Services, handlers        | Providers de contexto React                      |

**Código portado** (`backend/services/context_graph/extract.py` etc.) tem
baixa cobertura por design — é código de terceiros adaptado. O que garante
confiança é o teste da interface pública (`pipeline.py`, `tools/context_graph.py`,
`handlers/context_graph.py`) com casos felizes e de erro.

**Meta de cobertura** não é 100% global — é "zero arquivos próprios com 0%
e zero caminhos críticos sem par de erro". O `scons coverage` mostra o
relatório; `skipFull: true` oculta os já completos para focar no gap.

---

## Comandos de referência

```powershell
# Backend — rodar uma suíte específica
cd vectora
uv run pytest tests/unit/test_context_graph_api.py -q --tb=short

# Backend — cobertura de um módulo
uv run pytest tests/unit/test_context_graph_api.py --cov=backend.api.handlers.context_graph --cov-report=term-missing

# Frontend — rodar um teste específico
cd vectora/frontend
pnpm exec vitest run lib/hooks/__tests__/use-context-graph.test.ts

# Frontend — cobertura (só do arquivo)
pnpm exec vitest run --coverage lib/hooks/__tests__/use-context-graph.test.ts

# Suíte completa
cd vectora
scons tests      # vitest + pytest, sem cobertura
scons coverage   # com cobertura
```
