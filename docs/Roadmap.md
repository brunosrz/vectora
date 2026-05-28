# Plano: Roadmap Vectora — Pré vs Pós Deep Agents

## Contexto

Após leitura completa das docs do LangChain, LangGraph, Deep Agents, Tavily, Cohere, MCP Adapters e A2A, este plano define com precisão o que o Vectora pode e deve implementar **agora com LangGraph puro** e o que **só faz sentido após a migração para Deep Agents**.

**Regra cardinal:** Implementar tudo que for possível de forma totalmente funcional antes de ir para Deep Agents. Não usar Deep Agents como muleta. Aprender e dominar com o próprio Vectora.

**Estado atual confirmado:**

- Orchestrator como agente primário LLM (OrchestratorDecision schema)
- 17 tools (fs: 7 + rag: 3 + web: 2 + memory: 3 + mcp: 1 + terminal: 1)
- `langchain-mcp-adapters>=0.1.0` já instalado (não usado ainda)
- `rank-bm25>=0.2.2` já instalado (não usado ainda)
- RAG subgraph com threshold adaptativo (0.7/0.4)
- AsyncSqliteSaver para checkpoints
- Sem HITL, sem parallel execution, sem LangGraph Studio

---

## DIRETIVA PERMANENTE — Sistema de Tipos (Type Safety)

> **Esta diretiva se aplica a todos os blocos, presentes e futuros.**

### Regras Obrigatórias

1. **Centralização em `vectora/types/`**: Todo modelo de dados complexo (estado intermediário, resultado de agente, schema de curadoria, métricas) deve residir em `vectora/types/`. Módulos de domínio (agents/, nodes/, services/) definem lógica — não tipos.

2. **Pydantic como base**: Todos os modelos de dados devem herdar de `pydantic.BaseModel`. TypedDicts são permitidos apenas como anotação de estado LangGraph (onde o próprio framework exige dict-like serialization).

3. **PEP 585 / PEP 604 — Sintaxe moderna obrigatória**:
   - `list[str]` em vez de `List[str]`
   - `str | None` em vez de `Optional[str]`
   - `dict[str, Any]` em vez de `Dict[str, Any]`
   - Zero imports de `typing` para primitivos (`List`, `Dict`, `Optional`, `Tuple`, `Set`) — apenas `Annotated`, `Literal`, `NotRequired`, `TYPE_CHECKING` quando necessários

4. **Contratos de interface**: `state.py` importa os tipos de `vectora/types/`. Os campos de estado que referenciam resultados de agentes usam os modelos Pydantic (`CoderResult | None`, `SearchResult | None`, `SubTask`, etc.) e não `dict | None`.

5. **Lógica pura + decoradores de infra**: Funções de nó implementam apenas a lógica de negócio. Preocupações transversais (tracing, observabilidade, awareness de workspace) são aplicadas via decoradores (`@trace_node`, `@workspace_aware`).

### Estrutura `vectora/types/`

```
vectora/types/
├── __init__.py        # re-export de todos os tipos públicos
├── documents.py       # Document, ArtifactMetadata
├── agents.py          # AgentName, SubTask, OrchestratorDecision,
│                      # CoderResult, SearchResult, ParallelResult, UIMetrics
├── curation.py        # WebResultVerdict, CurationDecision
├── session.py         # SessionMetadata
└── workspace.py       # Workspace (Pydantic)
```

### Estado atual da tipagem (inventário)

| Modelo                                       | Local atual                    | Tipo atual             | Ação                                                                        |
| -------------------------------------------- | ------------------------------ | ---------------------- | --------------------------------------------------------------------------- |
| `OrchestratorDecision`, `SubTask`            | `agents/orchestrator.py`       | Pydantic ✓             | Mover para `types/agents.py`                                                |
| `CoderResult`, `SearchResult`                | `agents/results.py`            | Pydantic ✓             | Mover para `types/agents.py`                                                |
| `WebResultVerdict`, `CurationDecision`       | `nodes/web_curation.py`        | Pydantic ✓             | Mover para `types/curation.py`                                              |
| `Document`, `SessionMetadata`                | `state.py`                     | TypedDict              | Criar Pydantic em `types/`; manter TypedDict em state por compat. LangGraph |
| `ArtifactMetadata`                           | `messages.py`                  | TypedDict              | Criar Pydantic em `types/documents.py`                                      |
| `Workspace`                                  | `services/workspace.py`        | Dataclass              | Migrar para Pydantic em `types/workspace.py`                                |
| `UIMetrics`                                  | `providers/Stream.tsx` (só TS) | —                      | Criar Pydantic em `types/metrics.py`                                        |
| `ParallelResult`                             | (não existe)                   | —                      | Criar em `types/agents.py`                                                  |
| `EmbeddingQueueRecord`                       | `services/queue.py`            | SQLAlchemy ORM         | Manter como ORM (não Pydantic)                                              |
| `Context`, `UserPreferences`, `FeatureFlags` | `context.py`                   | Dataclass frozen+slots | Manter como dataclass (frozen+slots sem equivalente Pydantic trivial)       |

---

## PARTE 1 — PRÉ-DEEP AGENTS

Tudo nesta seção é implementável com **LangGraph + LangChain puros**, sem nenhuma dependência do Deep Agents framework. Organizado por blocos de lançamento (rc3 → rc4 → v0.1.0 → v0.2.x).

---

### BLOCO T — Type System (implementar imediatamente — paralelo ao rc4)

Implementação da diretiva de tipos definida acima. Todos os modelos já implementados migram para `vectora/types/`. Zero breaking changes — os módulos originais re-exportam de `vectora/types/`.

#### T1 — Criar módulos em `vectora/types/`

**`vectora/types/agents.py`** — move de `agents/orchestrator.py` e `agents/results.py`:

```python
AgentName = Literal["coder", "search", "rag"]

class SubTask(BaseModel):
    agent: AgentName
    task_query: str
    reason: str = ""

class OrchestratorDecision(BaseModel):
    action: Literal["respond", "delegate", "parallel"]
    response: str | None = None
    delegate_to: AgentName | None = None
    task_query: str | None = None
    parallel_tasks: list[SubTask] | None = None
    reason: str

class CoderResult(BaseModel):
    summary: str
    files_changed: list[str] = []
    tests_run: bool = False
    success: bool = True
    next_steps: str | None = None

class SearchResult(BaseModel):
    summary: str
    sources: list[str] = []
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    web_search_used: bool = False

class ParallelResult(BaseModel):
    agent: AgentName
    task: str
    response: str
    success: bool = True

class UIMetrics(BaseModel):
    last_node: str | None = None
    last_node_ms: float | None = None
    total_tokens_session: int = 0
    rag_hits: int = 0
    rag_misses: int = 0
    tool_calls: dict[str, int] = {}
    workspace_id: str | None = None
    manifest_version: int = 0
```

**`vectora/types/curation.py`** — move de `nodes/web_curation.py`:

```python
class WebResultVerdict(BaseModel):
    index: int
    keep: bool
    reason: str

class CurationDecision(BaseModel):
    verdicts: list[WebResultVerdict]
```

**`vectora/types/documents.py`** — Pydantic equivalente ao TypedDict de `state.py`:

```python
class Document(BaseModel):
    page_content: str
    metadata: dict[str, Any] = {}
    relevance_score: float | None = None

class ArtifactMetadata(BaseModel):
    title: str
    path: str
    session_id: str
    created_at: str
    content_preview: str | None = None
```

**`vectora/types/session.py`**:

```python
class SessionMetadata(BaseModel):
    thread_id: str
    user_type: str = "human"
    created_at: str
    llm_provider: str = ""
    llm_model: str = ""
    workspace_id: str | None = None
    manifest_version: int = 0
```

**`vectora/types/workspace.py`** — migra de dataclass `services/workspace.py`:

```python
class Workspace(BaseModel):
    id: str
    name: str
    cwd: str
    created_at: str
    bucket_names: list[str] = []
    manifest_version: int = 0
```

**`vectora/types/__init__.py`** — re-export público:

```python
from vectora.types.agents import (AgentName, SubTask, OrchestratorDecision,
    CoderResult, SearchResult, ParallelResult, UIMetrics)
from vectora.types.curation import WebResultVerdict, CurationDecision
from vectora.types.documents import Document, ArtifactMetadata
from vectora.types.session import SessionMetadata
from vectora.types.workspace import Workspace
```

#### T2 — Atualizar módulos consumidores

- **`agents/orchestrator.py`**: remove definições locais de `SubTask`, `OrchestratorDecision`; importa de `vectora.types`
- **`agents/results.py`**: remove definições locais de `CoderResult`, `SearchResult`; importa de `vectora.types`
- **`nodes/web_curation.py`**: remove definições locais de `WebResultVerdict`, `CurationDecision`; importa de `vectora.types`
- **`services/workspace.py`**: substitui `@dataclass` `Workspace` por `from vectora.types import Workspace`; ajusta `asdict()` para `.model_dump()`
- **`messages.py`**: importa `ArtifactMetadata` de `vectora.types`
- **`state.py`**: campos `coder_result`, `search_result`, `parallel_tasks`, `parallel_results` tipados com os modelos Pydantic (usando `| None` para compat. de serialização LangGraph)

#### T3 — Verificação

- `tests/unit/test_types.py` (novo): valida criação, serialização e `model_dump()` de cada modelo
- `uv run pytest tests/unit/ -x -q` — suite completa verde
- `uv run python -c "from vectora.types import *; print('OK')"` — importação limpa

Impacto: `vectora/types/` (5 novos módulos), `agents/orchestrator.py`, `agents/results.py`, `nodes/web_curation.py`, `services/workspace.py`, `messages.py`, `state.py`

---

### BLOCO A — rc3 (Integração de capacidades já na dep tree)

As três deps abaixo já estão em `pyproject.toml` mas não usadas corretamente.

#### A1 — langchain-mcp-adapters: upgrade do MultiServerMCPClient

**O que está hoje:** `vectora/tools/mcp.py` usa implementação customizada de MCP client.
**O que muda:** Usar `MultiServerMCPClient` da biblioteca oficial `langchain-mcp-adapters`.

Ganhos:

- Tool interceptors (logging, retry, autenticação por servidor)
- OAuth nativo para servidores MCP que exigem auth
- Resource loading (blobs de arquivos/dados do servidor MCP)
- Sessões persistentes (`async with client.session(...)`)
- `allowedTools` / `disabledTools` por padrão (filtragem)
- Suporte a `structuredContent` para retorno de dados estruturados

Impacto: `vectora/tools/mcp.py`, `vectora/mcp/server.py` (client-side config)

#### A2 — Cohere `input_type` correto

**O que está hoje:** `input_type` foi removido na rc1 por incompatibilidade com `langchain-cohere==0.5.1`.
**O que muda:** Verificar versão disponível e reativar:

- Embedding (indexação): `input_type="search_document"`
- Query (busca): `input_type="search_query"`

Impacto: `vectora/tools/rag.py` (`embedding`), `vectora/nodes/retrieval.py` (`vector_search`)

#### A3 — Tavily v2: migrar para `langchain-tavily`

**O que está hoje:** `vectora/tools/web.py` usa `TavilyClient` direto via `tavily-python`.
**O que muda:** Migrar para `langchain-tavily` com a nova classe `TavilySearch`.

Novos parâmetros desbloqueados:

- `topic`: "general" | "news" | "finance" — segmenta o tipo de busca
- `time_range`: "day" | "week" | "month" | "year" — filtro temporal
- `include_raw_content`: True — retorna conteúdo completo da página
- `include_images` + `include_image_descriptions` — imagens nos resultados
- `search_depth`: "basic" | "advanced"
- `include_domains` / `exclude_domains` — listas de domínios

Nova tool `tavily_extract` (substitui fetch_url com suporte a múltiplas URLs).

Impacto: `vectora/tools/web.py`, `pyproject.toml` (add `langchain-tavily`, drop `tavily-python`)

#### A4 — LangGraph Studio: configuração local

**O que está hoje:** Nenhum arquivo `langgraph.json`. Debugging via logs.
**O que muda:** Adicionar `langgraph.json` + adaptar `graph.py` para expor o grafo.

```json
{
  "graphs": {
    "vectora": "./vectora/graph.py:build_graph"
  },
  "python_version": "3.14",
  "dependencies": ["."]
}
```

Uso: `langgraph dev` → UI em `http://127.0.0.1:2024` com:

- Visualização de cada nó/edge em tempo real
- Inspeção de state em cada step
- Time-travel debugging (replay de turnos)
- State forking (testar variações de um ponto específico)
- Token + latência por nó

Impacto: criar `langgraph.json`, nenhuma mudança em código

---

### BLOCO A5 — rc3 (Anti-contaminação do RAG via web)

Implementar **após A3** — A3 estabiliza o schema dos resultados Tavily que A5 consome.

#### Contexto — a única superfície de contaminação do Vectora

RAG local é seguro por construção: o usuário escolhe o que indexar (`ingest_docs` numa
pasta `docs/` ou `src/`). O risco mora no **cascading automático das web tools**. Hoje:

- `process_retrieval` (`engine.py`) enfileira **todo** resultado de `web_search`/`fetch_url`
- `rag_websearch` (`rag_subgraph.py`) faz o mesmo no fallback do RAG
- Ambos gravam na **mesma tabela `articles`** usada por `ingest_docs`
- Não há filtro, ranking, nem forma de desfazer

Resultado concreto: buscar "godot ability system" indexa 5 resultados — só 1 é o repo
correto (`github.com/brunosrz/AbilitySystem`). Os outros 4 ("Godot Gameplay Systems"
etc.) contaminam a base permanentemente. O prompt do search agent _avisa_ contra isso,
mas o cascading roda em nós do grafo — é automático, o agent não tem voto.

Bloco A5 resolve em três frentes: **isolamento**, **gate de qualidade** e **reversibilidade**.

#### A5.1 — Bucket dedicado para conteúdo web

Separar fisicamente conteúdo web dos docs curados pelo usuário.

Novas settings (`vectora/config/settings.py`):

- `rag_collection_default: str = "articles"` — docs curados (ingest_docs, embedding manual)
- `rag_collection_web: str = "web_cache"` — conteúdo vindo da web (cascading)

Os dois call-sites de cascading passam a usar `settings.rag_collection_web` em vez do
`"articles"` hardcoded. O background worker já cria a tabela sob demanda — zero mudança
no `_write_to_lancedb`.

Retrieval consulta **ambos** os buckets e mescla os resultados:

- `_call_vector_search` (`rag_subgraph.py`) ganha variante multi-collection
- Resultados web carregam `origin="web_search"` + `relevance_score` no metadata, para
  o reranker e o LLM ponderarem a confiança da fonte
- `rag_inject` exibe a origem no bloco de contexto (curado vs web)

Ganhos imediatos: audit (inspecionar só o bucket web), observabilidade (`/rag` mostra
contagem por bucket) e purge cirúrgico sem tocar nos docs do usuário.

#### A5.2 — Gate de curadoria: Reranker + LLM judge antes de persistir

Novo módulo `vectora/nodes/web_curation.py`. Nenhum resultado web é persistido sem
passar por duas etapas de aprovação:

```
resultados web (N)
  → CohereRerank contra a query/task → relevance_score por resultado
  → descarta score < settings.web_persist_min_score
  → LLM judge (1 call estruturada, batch) avalia os sobreviventes:
      recebe project_context + orchestrator_task → decide keep/discard por doc
  → aprovados → enfileira no bucket web_cache (score + razão no metadata)
  → rejeitados → logados para audit, NÃO persistidos
```

Schemas:

```python
class WebResultVerdict(BaseModel):
    index: int
    keep: bool
    reason: str          # 1 frase — por que é (ir)relevante ao projeto

class CurationDecision(BaseModel):
    verdicts: list[WebResultVerdict]
```

O LLM judge recebe `project_context` (AGENTS.md/CLAUDE.md já carregados pelo orchestrator)

- `orchestrator_task` — assim sabe o que é "o projeto" e distingue o repo do brunosrz
  de um asset aleatório do Godot. O judge roda **sempre** sobre os sobreviventes do
  reranker (1 call em batch, não 1 por doc).

Função pública `curate_and_enqueue(results, query, *, task, project_context, collection)`
substitui os loops de enqueue incondicional em:

- `process_retrieval` / `_process_tavily_results` (`engine.py`)
- `rag_websearch` (`rag_subgraph.py`)

Novas settings:

- `web_curation_enabled: bool = True` — kill-switch
- `web_persist_min_score: float = 0.5` — threshold do reranker no gate

LLM judge: `load_llm().with_structured_output(CurationDecision)`, singleton lazy igual
ao `_get_orchestrator_llm`.

#### A5.3 — Tool `manage_retriever` (remover / atualizar)

Hoje o Vectora só sabe **adicionar** ao RAG. Falta remover — essencial para a
reavaliação: quando o usuário fornece a fonte canônica, o agent precisa apagar o que
foi indexado por engano antes.

Nova tool em `vectora/tools/rag.py`:

```python
@tool
async def manage_retriever(
    action: Literal["list", "delete", "purge"],
    collection: str = "web_cache",
    source: str | None = None,
) -> str
```

- `list` — lista docs indexados (source, title, relevance_score, indexed_at) — audit
- `delete` — apaga por `source` (match de URL): scan da tabela, parse do metadata JSON,
  `await table.delete("id IN (...)")` por `queue_id`
- `purge` — limpa um bucket inteiro (cleanup do legado em `articles`, feito pelo operador)

"Atualizar" = `delete` + `embedding` (documentado como padrão, sem action separada).

Registrar em `ALL_TOOLS` (`nodes/tools.py`) → 15 → **16 tools**. Exposta também no MCP
server (`vectora/mcp/server.py`) — é destrutiva, mas alinhada com `file_write`/`terminal`
já expostos.

Prompts de orchestrator e search ganham a **regra de reavaliação**: ao receber fonte
autoritativa do usuário (repo canônico, doc oficial), reavaliar conteúdo web já indexado
e remover via `manage_retriever` o que agora se sabe estar errado.

#### Decisões de design já fechadas

- **Gate**: reranker filtra + LLM judge avalia **sempre** os sobreviventes (não só borderline)
- **Escopo do RAG**: retrieval pesquisa os dois buckets; resultados web vêm marcados
- **Legado**: conteúdo já misturado em `articles` fica como está; limpeza é manual via
  `manage_retriever purge` (sem migração automática)

#### Impacto

| Arquivo                                              | Mudança                                                        |
| ---------------------------------------------------- | -------------------------------------------------------------- |
| `vectora/config/settings.py`                         | 4 settings novas (2 collections + 2 curation)                  |
| `vectora/nodes/web_curation.py`                      | **novo** — gate rerank + LLM judge                             |
| `vectora/nodes/engine.py`                            | `process_retrieval` usa `curate_and_enqueue`                   |
| `vectora/nodes/rag_subgraph.py`                      | `rag_websearch` usa o gate; `_call_vector_search` multi-bucket |
| `vectora/tools/rag.py`                               | nova tool `manage_retriever`                                   |
| `vectora/nodes/tools.py`                             | registrar `manage_retriever` em ALL_TOOLS (→16)                |
| `vectora/mcp/server.py`                              | expor `manage_retriever`                                       |
| `vectora/agents/orchestrator.py`, `agents/search.py` | regra de reavaliação no prompt                                 |

#### Verificação

- Novo `tests/unit/test_nodes_web_curation.py` — mock do reranker + judge, garante que
  lixo abaixo do threshold ou reprovado pelo judge não é enfileirado
- Atualizar `test_nodes_engine.py` e `test_nodes_rag_subgraph.py` para o gate de curadoria
- `test_nodes_tools.py` — `manage_retriever` registrada, `ALL_TOOLS == 16`
- Manual: buscar "godot ability system" → confirmar que só o resultado relevante entra
  em `web_cache`; `manage_retriever delete` remove uma entrada errada; `articles` intacto

---

### BLOCO A6 — Correção Urgente do RAG (hotfix rc4)

#### Contexto — o incidente

O usuário indexou a documentação XML de um projeto (embedding OK) e pediu uma
resposta via RAG. O Vectora **travou por completo** e morreu com
`GraphRecursionError: Recursion limit of 25`. Os logs revelam uma cadeia de
falhas encadeadas — não um bug, mas **quatro**.

**Cadeia de falha reconstruída a partir dos logs:**

```
rag_retrieve → vector_search → .to_pandas() → ModuleNotFoundError: pandas
            → "found 0 docs, best_score=0.000"
            → rag_decide vê score 0.0 → rag_websearch (fallback)
            → 5 resultados web injetados em rag_docs
            → rag_inject injeta SystemMessage(name="rag_context")
            → rag_subgraph → orchestrator
            → orchestrator NÃO vê o rag_context → re-decide "rag"
            → rag_subgraph → orchestrator → rag_subgraph → … (×25)
            → GraphRecursionError → crash total
```

#### Bug 1 — `pandas` não é dependência (FATAL para RAG local)

`vector_search` (`rag.py:196`) e `manage_retriever` (`rag.py:526`) chamam
`.to_pandas()` do LanceDB. **`pandas` não está em `pyproject.toml`** — só
`lancedb` e `pyarrow`. No ambiente instalado via `uv tool` o pandas não existe,
então `.to_pandas()` levanta `ModuleNotFoundError`. O `except Exception` externo
de `vector_search` engole o erro e retorna `status="failed"` → o subgrafo lê
0 docs. **Resultado: o RAG local é 100% inacessível.** A documentação que o
usuário indexou nunca seria encontrada.

#### Bug 2 — Loop infinito orchestrator ↔ rag_subgraph (FATAL, a "trava")

`graph.py:111` faz `add_edge("rag_subgraph", "orchestrator")` — após o RAG, o
orchestrator deveria **sintetizar** a resposta. Mas:

- `rag_inject` injeta o contexto como `SystemMessage(name="rag_context")`
  (`rag_subgraph.py:322`).
- `orchestrator._select_context_messages` (`orchestrator.py:243-253`) filtra
  **apenas `HumanMessage` e `AIMessage`** — descarta toda `SystemMessage`.
- Logo o orchestrator **nunca vê o contexto RAG**. Ele só vê a pergunta
  original ("me responda com rag…"), re-decide `delegate→rag`, e volta ao
  subgrafo. Loop até o limite de recursão 25 → crash.

Há ainda um agravante: quando o RAG não acha nada, `rag_inject` retorna `{}`
(`rag_subgraph.py:290-292`) — nem o marcador `rag_context` é emitido, então não
existe sinal algum de que o RAG já rodou.

Consequência silenciosa adicional: **mesmo sem o loop, a síntese RAG está
quebrada** — o orchestrator responde de memória própria, nunca dos docs
recuperados, porque o bloco de contexto é descartado antes de chegar ao LLM.

#### Bug 3 — Modelo de coleções incoerente (RAG não acha o que foi indexado)

Existem **dois vocabulários de coleção que não se falam**:

- `/rag add` (`ui/commands/rag.py`) infere coleção via `_guess_collection` →
  `{code, docs, web, notes}` (constante `CANONICAL_COLLECTIONS`, "D5").
- `_call_vector_search_all` (`rag_subgraph.py:99-101`) busca **apenas**
  `settings.rag_collection_default` (`"articles"`) + `rag_collection_web`
  (`"web_cache"`).

Quem indexa via `/rag add docs/` cai na coleção `"docs"` — que o subgrafo RAG
**nunca consulta**. Os docs ficam órfãos. (No incidente, se o agente usou a
tool `ingest_docs` com o default `collection="articles"`, a coleção bateu por
sorte; via `/rag add` teria sido outro miss garantido.)

#### Bug 4 — Distância tratada como score de similaridade

`vector_search` no caminho **sem rerank** grava `_distance` do LanceDB (L2 —
quanto **menor**, melhor) na chave `"score"` (`rag.py:207`). O
`_call_vector_search` do subgrafo copia isso para `relevance_score`
(`rag_subgraph.py:79`: `r.get("relevance_score") or r.get("score")`). Então
`_best_score` / `rag_decide` interpretam distância como similaridade
(quanto **maior**, melhor) — **lógica invertida**: um match excelente
(distância ~0.1) é roteado para websearch; um match ruim (distância ~0.9) é
injetado direto. Só não morde quando o reranker Cohere funciona (aí vem
`relevance_score` real 0-1). Quando o rerank falha (ex.: quota), o roteamento
vira ruído.

#### Correções

**A6.1 — Declarar `pandas` (e `pyarrow`) como dependências de primeira classe**

A causa-raiz do Bug 1 é uma **dependência implícita**: `vector_search` e
`manage_retriever` usam `.to_pandas()` do LanceDB, mas `pandas` nunca foi
declarado em `pyproject.toml`. A correção é **declarar a dependência** — não
remover o uso de pandas:

- `uv add pandas` → adiciona `pandas` ao bloco `[project] dependencies`.
- `pyarrow>=17.0.0` já está declarado — manter.
- `vector_search` (`rag.py:196`) e `manage_retriever` (`rag.py:526`) ficam como
  estão: `.to_pandas()` passa a funcionar porque a dependência existe no
  ambiente instalado via `uv tool`.

Com pandas/pyarrow agora como deps de primeira classe, adotá-los de forma
**idiomática** nas partes que já manipulam dados tabulares/colunares — em vez
de loops Python sobre dicts:

- `manage_retriever` (`rag.py`) — hoje converte o DataFrame em lista de dicts e
  filtra em loop. Passar a usar o DataFrame de verdade: parse de `metadata`
  vetorizado (`df["metadata"].map(json.loads)`) e o match de `source` do
  `delete` via máscara booleana. Mais limpo e mais rápido em coleções grandes.
- `/rag` panel (`ui/commands/rag.py:334-360`) — hoje só `count_rows()` por
  coleção. Carregar cada tabela com `.to_pandas()` e exibir o breakdown por
  origem (curado vs `origin="web_search"`) — a observabilidade por bucket que o
  A5 previa. É uma agregação que genuinamente pede pandas.
- `background.py:_write_to_lancedb` já monta o schema LanceDB com `pyarrow`
  (`pa.schema`/`pa.field`) — é o padrão de referência; manter.

**A6.2 — Quebrar o loop orchestrator ↔ rag_subgraph**

Dois pontos, ambos necessários:

1. `rag_inject` (`rag_subgraph.py`) passa a **sempre** emitir o
   `SystemMessage(name="rag_context")` — inclusive quando não há docs, com
   conteúdo "nenhum documento relevante encontrado para: {query}". Isso garante
   um marcador determinístico de "o RAG rodou neste turno".

2. `orchestrator` (`agents/orchestrator.py`) detecta o modo pós-RAG: se a
   **última** mensagem do estado é `SystemMessage` com `name == "rag_context"`,
   entra num caminho de **síntese pura**:
   - Monta um payload com a pergunta do usuário + o bloco `rag_context` + uma
     instrução de síntese ("responda à pergunta com base SÓ neste contexto; se
     não houver resposta nele, diga isso honestamente").
   - Chama `load_llm()` **simples** — sem `OrchestratorDecision`, sem tools.
   - Retorna `Command(goto=END, …)` com o `AIMessage` sintetizado.

   Como esse caminho vai **sempre** para `END`, é impossível re-rotear para
   `rag` — o loop fica estruturalmente eliminado. Bônus: corrige a síntese RAG
   quebrada (Bug 2, agravante) — agora o LLM responde dos docs recuperados.

3. Defesa em profundidade: em `chat.py:363`, passar
   `config={..., "recursion_limit": 50}` no `astream_events` — não é a
   correção (o loop sumiu em A6.2.2), mas dá folga a cadeias legítimas longas.

**A6.3 — Reconciliar o modelo de coleções**

`_call_vector_search_all` (`rag_subgraph.py`) passa a **descobrir todas as
tabelas** via `await db.table_names()` e buscar em cada uma, em paralelo
(`asyncio.gather`), em vez de só `articles` + `web_cache`. A tabela
`rag_collection_web` continua especial: seus docs recebem
`metadata["origin"]="web_search"`. Assim "indexei → o RAG acha", qualquer que
seja a coleção. `_call_vector_search` ganha tratamento de tabela inexistente
(retorna `[]`). Mantém `retrieval.py` consistente (já usa `_call_vector_search_all`).

**A6.4 — Corrigir distância vs similaridade**

Em `_call_vector_search` (`rag_subgraph.py`), quando o resultado só tem
`_distance` (sem `relevance_score` do reranker), converter para uma
similaridade monotônica e limitada: `score = 1.0 / (1.0 + distance)` — maior =
melhor, em `(0, 1]`. Remover o fallback cru `or r.get("score")`. O reranker
Cohere continua sendo o sinal primário quando disponível; a conversão só evita
que o roteamento de `rag_decide` fique invertido quando o rerank falha.

**A6.5 — Auditoria do RAG e superfícies adjacentes (entregável)**

Varredura focada (não linha-a-linha de todo o repo) para achar bugs da mesma
classe, cobrindo: `tools/rag.py`, `tools/web.py`, `tools/fs.py`,
`nodes/rag_subgraph.py`, `nodes/retrieval.py`, `nodes/engine.py`,
`nodes/web_curation.py`, `agents/orchestrator.py`, `agents/search.py`,
`agents/coder.py`, `graph.py`, `services/queue.py`, `services/background.py`,
`ui/commands/rag.py`. Itens já mapeados a confirmar/tratar:

- Estado transitório (`rag_docs`, `web_search_triggered`, `orchestrator_task`)
  persiste no checkpoint entre turnos — contexto RAG obsoleto pode vazar para o
  turno seguinte. Avaliar reset por turno.
- Loop `search → search_tools → process_retrieval → search`: confirmar
  condição de parada robusta.
- `relevance_score` lido como atributo vs. `metadata` em `rag_rerank` /
  `_rerank` (CohereRerank grava em `doc.metadata`).
  O resultado da auditoria vira uma lista de achados anexada ao final deste bloco.

#### Impacto

| Arquivo                          | Mudança                                                                                                                      |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `pyproject.toml`                 | `uv add pandas` — declarar `pandas` em `dependencies` (A6.1)                                                                 |
| `vectora/tools/rag.py`           | manter `.to_pandas()`; `manage_retriever` filtra via DataFrame vetorizado (A6.1)                                             |
| `vectora/ui/commands/rag.py`     | `/rag` panel: breakdown por origem via pandas (A6.1)                                                                         |
| `vectora/nodes/rag_subgraph.py`  | `rag_inject` sempre emite `rag_context`; `_call_vector_search_all` multi-coleção; conversão distância→score (A6.2/A6.3/A6.4) |
| `vectora/agents/orchestrator.py` | caminho de síntese pós-RAG determinístico → `END` (A6.2)                                                                     |
| `vectora/ui/chat.py`             | `recursion_limit: 50` no config do `astream_events` (A6.2, defesa)                                                           |
| `vectora/nodes/retrieval.py`     | alinhar com `_call_vector_search_all` multi-coleção (A6.3)                                                                   |

#### Verificação

- `pyproject.toml` — confirmar `pandas` em `dependencies` após `uv add pandas`;
  `uv sync` reinstala o ambiente.
- `tests/unit/test_tools_rag.py` — `vector_search` e `manage_retriever` cobertos
  com mock LanceDB expondo `.to_pandas()` retornando um DataFrame real
  (`pandas.DataFrame`), validando o caminho de parsing/filtragem.
- Novo `tests/unit/test_agents_orchestrator.py` (ou ampliar o existente) — com a
  última mensagem sendo `SystemMessage(name="rag_context")`, o orchestrator
  roteia para `END` e nunca para `rag_subgraph` (regressão do loop).
- `tests/unit/test_nodes_rag_subgraph.py` — `rag_inject` emite `rag_context`
  mesmo com `rag_docs` vazio; `_call_vector_search_all` busca em todas as
  coleções descobertas.
- Suite completa verde (baseline atual: 332 passed, 2 skipped).
- Manual: indexar uma pasta de docs XML → perguntar via RAG → confirmar
  resposta sintetizada dos docs, **sem** `GraphRecursionError`, em 1 passada
  pelo subgrafo.

#### Achados da auditoria (A6.5)

- **`relevance_score` atributo vs metadata** — CONFIRMADO OK. Toda leitura
  (`rag_rerank`, `_rerank`, `vector_search`, `manage_retriever`,
  `web_curation`) usa `.metadata.get("relevance_score")` ou `dict.get(...)`.
  Não existe nenhum `getattr(doc, "relevance_score")` no código. Sem bug.
- **Loop `search → search_tools → process_retrieval → search`** — OK. A
  terminação é decidida pelo LLM via `tools_condition` (para quando não há mais
  tool_calls) e o estado muda a cada volta (resultados de tool acumulam). Não é
  um loop determinístico como era o do RAG. `recursion_limit:50` cobre o resto.
- **Estado transitório entre turnos** (`rag_docs`, `web_search_triggered`,
  `orchestrator_task` persistem no checkpoint) — sem impacto após A6.2.
  `rag_subgraph` sobrescreve `rag_docs` quando roda; no caminho normal do
  orchestrator nada lê esses campos. Reset por turno é cosmético, não urgente.
- **Custo de embedding multi-coleção** (A6.3) — `_call_vector_search_all` chama
  `vector_search` por coleção, e cada chamada faz seu próprio `embed_query` no
  Cohere. Para N coleções são N chamadas de embedding por query RAG. Aceitável
  para o uso típico (poucas coleções) e as chamadas são paralelas; otimização
  futura: embeddar a query uma vez e reusar o vetor. Não é bug — fica como
  débito conhecido.
- **Bug fantasma `enable_rag`** — removido. Era config morta herdada de
  `defaults.env` (`ENABLE_RAG`), nunca declarada em `settings.py`. RAG é o
  coração do Vectora e está sempre ligado; todas as referências foram purgadas
  de código, env e testes. (`docs/MVP_SCOPE.md` ainda menciona — doc histórico,
  fora do escopo funcional.)

> Nota: há mudanças **não commitadas** de suporte a `.vectoraignore`
> (`services/ignore.py` renomeado de `gitignore.py`, + `tools/fs.py`,
> `tools/rag.py`, `ui/commands/rag.py`, testes). São independentes do A6 e
> devem ser commitadas em separado.

---

### BLOCO B — rc4 / v0.1.0 stable (Reliability & Control)

#### B1 — Human-in-the-Loop (HITL)

**O que está hoje:** `terminal`, `file_edit`, `file_write` executam sem confirmação.
**O que muda:** LangGraph `interrupt_before` + `Command` API para pausar antes de ações destrutivas.

Configuração:

```python
compiled = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["coder_tools"],  # pausa antes do ToolNode
)
```

Fluxo:

1. Orchestrator delega para coder
2. Coder gera tool_calls (file_edit/terminal)
3. Graph pausa → UI exibe "Confirmar?" com diff
4. Usuário: ✅ approve / ✏️ edit args / ❌ reject / 💬 respond
5. `Command(resume=decision)` retoma execução

Decisões disponíveis (alinhadas com Deep Agents HITL para migração futura):

- `approve` — executa com args originais
- `edit` — modifica args antes de executar
- `reject` — cancela, feedback para o agente
- `respond` — mensagem humana vira resultado da tool

Configurável por tipo de tool:

```python
INTERRUPT_ON: dict[str, bool] = {
    "terminal": True,
    "file_write": True,
    "file_edit": False,  # edições cirúrgicas não precisam confirmação
    "file_read": False,
}
```

Impacto: `vectora/graph.py` (compile params), `vectora/ui/chat.py` (nova UI de confirmação), `vectora/state.py` (campo `pending_interrupt`), novo `vectora/nodes/hitl.py`

#### B2 — Structured outputs dos sub-agentes

**O que está hoje:** Coder e search retornam texto livre como AIMessage.
**O que muda:** Sub-agentes retornam JSON estruturado para o orchestrator via `response_format`.

```python
class CoderResult(BaseModel):
    summary: str          # o que foi feito (1-2 frases)
    files_changed: list[str]
    tests_run: bool
    success: bool
    next_steps: str | None

class SearchResult(BaseModel):
    summary: str
    sources: list[str]
    confidence: float     # 0.0-1.0
    web_search_used: bool
```

Orchestrator lê resultado estruturado e pode tomar decisão informada (ex: se `success=False` → delegar novamente com correção).

Impacto: `vectora/agents/coder.py`, `vectora/agents/search.py`, `vectora/agents/orchestrator.py`

#### B3 — ToolRuntime injection (substituir global singletons)

**O que está hoje:** Tools acessam estado global via singletons (`get_memory_store()`, `get_embedding_queue()`).
**O que muda:** Tools recebem contexto via `ToolRuntime` (LangChain nativo):

```python
@tool
async def save_memory(key: str, content: str, runtime: ToolRuntime) -> str:
    user_id = runtime.context.user_id  # isolamento por sessão
    store = runtime.store              # LangGraph Store
    await store.aput((user_id, "memories"), key, {"content": content})
    return json.dumps({"status": "saved"})
```

Benefícios:

- Elimina singletons globais
- Torna tools testáveis sem mock complexo
- Alinha com padrão Deep Agents (mesma API)
- Isolamento por usuário automático

Impacto: `vectora/tools/memory.py`, `vectora/tools/rag.py`, `vectora/tools/fs.py` (parcial)

---

### BLOCO B4–B7 — Expansão do agent RAG: workspaces, manifests, auto-conhecimento

#### Contexto — o que falta no agent RAG hoje

O Bloco A5 deu ao agent RAG o poder de **curar** o que entra (reranker + LLM
judge + bucket isolado). Falta a outra ponta: depois que algo é indexado, o
Vectora não **sabe** que está lá até alguém perguntar e o vector search achar.
Resultado prático:

- O usuário pede algo conectado ao conteúdo recém-indexado e o Vectora responde
  de memória própria — nunca dispara o RAG porque "não sabe que sabe".
- Indexar `docs/godot/` numa pasta e `docs/vectora/` em outra mistura tudo na
  mesma tabela global — não há noção de "este projeto vs aquele". Quando a
  pergunta é "o que sabe sobre ability system?", o RAG pesquisa em **toda** a
  base, retornando lixo de outros projetos.
- A primeira mensagem de cada sessão não carrega o estado da base — o
  orchestrator não recebe "você tem 3 workspaces, o ativo é vectora com 240
  docs sobre X". Sem isso ele não sabe quando vale rotear pro RAG.

Quatro frentes coordenadas: **auto-conhecimento por batch (B4)**, **workspaces
por folder (B5)**, **manifests legíveis (B6)** e **contexto de workspace
garantido no startup (B7)**. Cada uma sozinha tem ganho marginal; juntas viram
o pilar do RAG "que se conhece".

#### Princípios arquiteturais (sustentam todos os 4 blocos)

1. **Manifest é Contexto (System), Memória é Tool.** Mistura entre os dois faz
   o prompt explodir em poucos turnos. O manifest do workspace ativo —
   compacto, ~500 tokens — entra como SystemMessage estática. Memória
   episódica (preferências, decisões, fatos da conversa) permanece **só**
   como tool (`get_memory`, `save_memory`), e o orchestrator decide quando
   consultar via `OrchestratorDecision`. Tokens economizados ficam pra
   resposta, não pra contexto inerte.

2. **Workspace é metadado, não tabela.** Quatro tabelas fixas (`code`,
   `docs`, `web_cache`, `system`) com coluna obrigatória `workspace_id`.
   Filtro via `where="workspace_id == '<id>'"` no LanceDB. Abrir uma pasta
   nova não cria tabela — apenas adiciona linhas com novo `workspace_id`.
   Manutenção, audit e escalabilidade brutalmente mais simples que dezenas
   de tabelas dinâmicas.

3. **Toda curadoria é assíncrona.** `ingest_docs` enfileira docs como `raw`
   e retorna **imediatamente**. O `BackgroundEmbeddingWorker` faz embed +
   reranker + LLM judge + curator (sumarização do manifest) em background,
   com status visível no `/rag` panel. O usuário nunca espera — pode
   continuar conversando enquanto o agente "estuda" o material.

#### B4 — RAG curator: gate assíncrono + atualização do manifest

Hoje o `BackgroundEmbeddingWorker` (`services/background.py:255-296`) drena a
fila e fica em `_poll_interval` adaptativo (5s→30s). Quando bate idle, o RAG
está mecanicamente atualizado mas o Vectora não tem nenhum sumário do que
foi adicionado, nem o gate de curadoria (A5) está nesse fluxo.

Princípio: **ingest é fire-and-forget; curadoria é background com status
visível**. `ingest_docs` enfileira `status="raw"` e retorna em <100ms — sem
LLM, sem reranker no hot path.

Pipeline expandido no worker:

```
raw → embedded → curated → indexed → summarized
 │       │         │         │           │
 │       │         │         │           └─ curator: 1 LLM call por flush
 │       │         │         │              atualiza MANIFEST.md
 │       │         │         └─ LanceDB write (idempotente via queue_id)
 │       │         └─ LLM judge (A5): keep/discard contra project_context
 │       └─ Cohere embed + reranker score (A5)
 └─ ingest_docs apenas enfileira (sem nenhum custo de LLM)
```

Mudanças:

- **Status expandido na fila** (`services/queue.py`): além de
  `pending/processing/success/failed/dlq`, novos estados `raw`, `embedded`,
  `curated`, `indexed`, `summarized`. Cada um é um checkpoint do pipeline.
  Falha em qualquer ponto vai pra `failed` com `last_stage` no metadata.

- **Hook de pós-batch** no worker. Após drenar a fila e entrar em idle
  (linha 265 `if not pending`), e existirem docs `indexed` desde o último
  flush, e passaram-se ≥30s desde o último doc, dispara o **curator**.
  Single flush cobre todo o batch — ingestar 1000 arquivos = 1 LLM call de
  síntese, não 1000.

- **`vectora/agents/rag.py`** (hoje só wrapper, vira o agent completo). Nova
  função `async def curate_workspace_knowledge(workspace_id: str) -> str`:
  1. Lê via LanceDB `where="workspace_id == '<id>' AND indexed_at > <last>'"`
     os docs novos por bucket.
  2. Chama `_get_synthesis_llm()` com prompt: "Você acabou de receber estes
     N docs no workspace X (bucket Y). Resuma em 2-4 parágrafos o que esses
     docs adicionam ao conhecimento do projeto. Foque no que é novo."
  3. Atualiza `MANIFEST.md` (workspace) e `buckets/<bucket>.md` (bucket).
  4. Chama `WorkspaceRegistry.bump_version(workspace_id)` — sinal in-memory
     que o orchestrator usa pra invalidar o cache do contexto (sem I/O por
     turno; ver B7 para o esquema completo de invalidação).
  5. Marca docs como `summarized` na fila.

- **Reentrância**: `asyncio.Lock` por workspace — curator não roda em
  paralelo pro mesmo workspace.

- **Status visível na TUI**: `/rag` panel mostra contagem por estado
  (`raw: 12, embedded: 8, curated: 5, indexed: 100, summarized: 100`).
  `VectoraStatusPanel` no footer indica quando o curator está rodando
  ("Curating workspace knowledge…"). Usuário sabe que algo está em
  background, mas o chat não trava.

- **Sem mexer em memória episódica**: o curator escreve **só** no manifest.
  `save_memory`/`get_memory` continuam intocadas — são tools do orchestrator
  pra fatos da conversa, não pra resumo da base. Decisão de design
  consciente (princípio 1 do bloco).

Impacto: `vectora/services/background.py` (pipeline estendido + hook),
`vectora/services/queue.py` (novos status), `vectora/agents/rag.py` (curator),
`vectora/ui/commands/rag.py` (status panel expandido),
`vectora/ui/main.py` (indicador no footer).

#### B5 — Workspaces por folder via metadado `workspace_id`

Sessions são efêmeras (uma por conversa). Workspaces são **persistentes por
projeto** — mesmo projeto, várias sessions, mesmo conhecimento.

Mudanças:

- **`vectora/services/workspace.py`** (novo) — `WorkspaceRegistry` singleton:

  ```python
  @dataclass
  class Workspace:
      id: str                 # sha256(abspath(cwd))[:8]
      name: str               # basename(cwd) — editável
      cwd: str                # abspath
      created_at: datetime
      bucket_names: list[str] # ["code", "docs", "notes"]
      manifest_version: int   # monotônico, bumped pelo curator (B4)
                              # → orchestrator usa pra invalidar cache sem I/O (B7)
  ```

  Persistido em `~/.vectora/workspaces.json`. API:
  `get_or_create(cwd) → Workspace`, `list_all() → list[Workspace]`,
  `delete(workspace_id)`, `rename(workspace_id, new_name)`,
  `bump_version(workspace_id)` (chamado pelo curator).

- **Schema LanceDB**: quatro tabelas **fixas** — `code`, `docs`, `web_cache`,
  `system`. Cada uma ganha coluna obrigatória `workspace_id: string`:

  ```python
  pa.schema([
      pa.field("id", pa.string()),               # queue_id
      pa.field("workspace_id", pa.string()),     # novo — sempre presente
      pa.field("vector", pa.list_(pa.float32(), 1024)),
      pa.field("text", pa.string()),
      pa.field("metadata", pa.string()),         # JSON com bucket, source, etc.
  ])
  ```

  Globais (não-pertencentes a workspace): usam `workspace_id="__global__"`.
  `web_cache` é compartilhado entre workspaces por padrão (web é web), mas a
  busca pode opcionalmente filtrar por workspace pra resultados curados na
  sessão daquele projeto.

- **`_call_vector_search_all`** (`nodes/rag_subgraph.py:131-169`) ganha
  parâmetro `workspace_id: str | None = None`. Quando passado, faz:

  ```python
  table.search(vector).where(f"workspace_id == '{wid}' OR workspace_id == '__global__'").limit(N)
  ```

  Quando `None` (ex: busca cross-workspace explícita), sem filtro.
  Performance é nativa do LanceDB — filtros `where` rodam sobre coluna
  indexada, não scan full.

- **Migração leve**: docs antigos sem `workspace_id` (das tabelas
  `articles`/`web_cache` pré-B5) recebem `workspace_id="__legacy__"` num
  script de migração one-shot (`vectora/scripts/migrate_to_workspaces.py`).
  Acessíveis via filtro explícito, não poluem buscas normais.

- **Determinação automática do workspace ativo**: na inicialização do chat
  (`ui/chat.py`), `WorkspaceRegistry.get_or_create(os.getcwd())` retorna o
  workspace; ID vai pro `Context` e propaga via `RunnableConfig.configurable`
  pro estado. Tools de RAG lêem esse ID e operam dentro dele.

- **`ingest_docs` / `embedding`** (`tools/rag.py`) ganham awareness de
  workspace: o `workspace_id` ativo é injetado automaticamente no metadata
  do doc antes de enfileirar. Override explícito
  (`workspace_id="__global__"`) ainda funciona pra docs cross-projeto.

- **`/rag` panel** (`ui/commands/rag.py:334-360`): mostra header com
  workspace ativo (nome + ID) + breakdown filtrado por `workspace_id`:

  ```
  Workspace: vectora (a3f2c1) — C:\Users\Machi\Desktop\vectora
    code:       187 docs
    docs:       53 docs
    web_cache:  12 docs (deste workspace) + 340 (global)
  ```

- **Novo comando `/workspaces`**: lista, renomeia, troca workspace ativo
  (troca o filtro sem sair do chat — útil pra cross-project queries).

Vantagens vs naming dinâmico de tabelas:

- **4 tabelas grandes** > 400 tabelas pequenas. Indexação, vacuum,
  estatísticas — tudo mais simples.
- **Cross-workspace queries triviais**: remover o `where` clause.
- **Schema evolution centralizado**: adicionar uma coluna = 4 ALTER, não
  N por workspace.
- **Audit nativo**: `SELECT workspace_id, COUNT(*) FROM code GROUP BY 1`
  responde "quanto cada workspace tem".

Impacto: `vectora/services/workspace.py` (novo),
`vectora/services/background.py` (schema com workspace_id),
`vectora/nodes/rag_subgraph.py` (filtro where),
`vectora/tools/rag.py` (inject workspace_id), `vectora/ui/commands/rag.py`,
`vectora/ui/commands/workspaces.py` (novo), `vectora/context.py`,
`vectora/ui/chat.py`, `vectora/scripts/migrate_to_workspaces.py` (novo).

#### B6 — Manifests (READMEs) por workspace e por bucket

O manifest é a fonte de verdade do "o que tem dentro" — lido pelo LLM como
contexto, renderizado no `/rag` panel, e atualizado pelo curator (B4).

Formato confirmado: **Markdown com YAML frontmatter** (Jekyll-style).

Estrutura no disco:

```
~/.vectora/workspaces/<workspace_id>/
├── MANIFEST.md           # visão geral do workspace
└── buckets/
    ├── code.md           # resumo do bucket "code"
    ├── docs.md
    └── notes.md
```

Exemplo `MANIFEST.md`:

```markdown
---
workspace_id: a3f2c1
name: vectora
cwd: C:\Users\Machi\Desktop\vectora
created_at: 2026-05-22T14:30:00Z
last_updated: 2026-05-22T15:45:12Z
buckets:
  - name: code
    table: ws_a3f2c1__code
    doc_count: 187
    last_indexed: 2026-05-22T15:45:12Z
  - name: docs
    table: ws_a3f2c1__docs
    doc_count: 53
    last_indexed: 2026-05-22T15:30:01Z
---

# Workspace: vectora

Agente de IA open-source baseado em LangGraph com RAG nativo. Sub-agentes
(orchestrator/search/coder) + subgraph RAG adaptativo.

## Conhecimento indexado

**code** (187 docs) — Implementação completa: `vectora/agents/` (orchestrator,
coder, search, rag), `vectora/nodes/` (rag_subgraph, tools), `vectora/tools/`
(rag, fs, web, memory, mcp), `vectora/services/` (background worker,
embedding queue, memory store).

**docs** (53 docs) — README, AGENTS.md, MVP_SCOPE, release notes, plano de
roadmap, docs de arquitetura interna do A5 e A6.

## Tópicos cobertos

- Arquitetura orchestrator + workers + RAG subgraph
- Curadoria de conteúdo web (reranker + LLM judge)
- Background embedding com rate limiting
- ...
```

Tools novas (`vectora/tools/workspace.py`, novo módulo):

- `workspace_describe(workspace_id: str | None = None) -> str` — retorna o
  `MANIFEST.md` renderizado. `None` = workspace ativo.
- `workspace_list() -> str` — lista compacta de todos os workspaces (id, name,
  cwd, doc_count total).
- `bucket_summary(bucket: str, workspace_id: str | None = None) -> str` —
  resumo de 1 bucket específico (`buckets/<bucket>.md`).

Essas 3 tools entram em `ALL_TOOLS` → **16 → 19 tools**. Disponíveis pra todos
os agents e expostas no MCP server. O orchestrator usa `workspace_describe`
para responder "o que você sabe sobre X?" sem precisar disparar RAG quando o
manifest já tem a resposta.

Atualização: feita pelo curator do B4. O LLM gera o novo MANIFEST.md inteiro
(idempotente) ou só os campos do bucket alterado. Frontmatter sempre
regenerado a partir do estado real do LanceDB (doc_count via `count_rows()`).

Impacto: `vectora/services/workspace.py` (extendido com manifest I/O),
`vectora/tools/workspace.py` (novo), `vectora/nodes/tools.py` (registra +3),
`vectora/mcp/server.py` (expõe +3).

#### B7 — Contexto de workspace garantido no startup (AGENTS.md + manifest)

Hoje `_load_project_context` (`agents/orchestrator.py:339-387`) escaneia
AGENTS.md/CLAUDE.md/GEMINI.md uma vez por sessão e injeta como SystemMessage.
O manifest do workspace **não entra**. Resultado: o LLM não sabe que existe
um workspace com 240 docs sobre X, e nunca rota pro RAG quando deveria.

Princípio reiterado: **manifest é contexto; memória é tool**. Esta seção
adiciona o manifest ao contexto estático. Memória episódica permanece
acessível só via `get_memory` — o orchestrator decide quando consultar.

Mudanças:

- **`_load_project_context` vira `_load_session_context`** e devolve bloco
  estruturado com 2 seções (sem memória):

  ```
  ## Contexto do Projeto
  <AGENTS.md/CLAUDE.md/GEMINI.md concatenados — como já funciona hoje>

  ## Workspace Ativo: <name> (<id>)
  <conteúdo prose de MANIFEST.md do workspace, sem frontmatter>

  Ferramentas disponíveis para este workspace:
  - vector_search (filtrado automaticamente para workspace_id == '<id>')
  - workspace_describe, bucket_summary (detalhes do manifest)
  - get_memory (consulte memórias episódicas se a pergunta sugerir)
  ```

  A última linha é o **dica explícita** pro orchestrator: a memória existe,
  mas é tool — não tá injetada no prompt.

- **Tamanho controlado**: manifest é truncado a ~800 tokens. Se exceder, só
  o frontmatter + parágrafo de introdução entram; detalhes por bucket ficam
  acessíveis via `bucket_summary` (tool). Garante que o contexto estático
  não cresce indefinidamente.

- **Carregamento**: 1x por sessão (cache em `state["project_context"]` via
  checkpoint). Invalidação por **versão em memória**, sem I/O por turno:
  - `WorkspaceRegistry` mantém `manifest_version: int` em memória por
    workspace (incrementado pelo curator quando reescreve o manifest).
    Persistido em `~/.vectora/workspaces.json` no save normal — não há save
    extra por invalidação.
  - O orchestrator armazena `state["session_metadata"]["manifest_version"]`
    no checkpoint quando carrega o contexto.
  - A cada turno, comparação **em memória pura**:
    `registry.get_workspace(wid).manifest_version != state[...]["manifest_version"]`
    → recarrega. Sem `os.stat`, sem leitura do `.updated_at`, sem I/O.
  - Curator (B4): no fim da síntese, `registry.bump_version(workspace_id)`.
    Próximo turno do orchestrator percebe o gap e recarrega.

  Vantagem prática: 99% dos turnos não fazem nenhuma checagem de filesystem
  — só comparação de inteiro. Recarga só acontece quando o curator
  efetivamente atualizou algo.

- **Garantia de injeção**: o bloco é a **primeira** SystemMessage da
  conversa, antes de tudo. Mesmo que o usuário mande `/new`, o próximo turno
  recarrega. Mesmo que a quota do LLM bata erro, a próxima tentativa
  reinjeta. Não há caminho onde o LLM perca o conhecimento de workspace.

- **Memória episódica fica como está**: `save_memory`/`get_memory`
  (`tools/memory.py`) continuam funcionando exatamente como hoje, mas o
  namespace muda de `session_<thread_id>` para `workspace_<workspace_id>`
  quando há workspace ativo. Assim memórias seguem o projeto, não a sessão
  (você abre uma sessão nova no mesmo projeto e as memórias estão lá).
  Memórias antigas em `session_<thread_id>` permanecem consultáveis via
  fallback de query (dual lookup).

Impacto: `vectora/agents/orchestrator.py` (renomeia e estende
`_load_session_context` — só adiciona manifest, não memória),
`vectora/tools/memory.py` (namespace por workspace_id, fallback dual),
`vectora/services/workspace.py` (manifest read API consumida aqui).

#### Decisões de design já fechadas (confirmadas com usuário + revisão sênior)

- **Manifest format**: Markdown com YAML frontmatter (Jekyll-style)
- **LanceDB layout**: 4 tabelas fixas (`code`, `docs`, `web_cache`, `system`)
  com coluna `workspace_id` filtrada via `where=`. **Não** nomeia tabelas
  dinamicamente (refatoração que evita 400 tabelas pequenas no longo prazo).
- **Manifest é Context, Memória é Tool**: manifest do workspace ativo entra
  como SystemMessage; `save_memory`/`get_memory` permanecem só como tools.
  Não há injeção de "top 5 memories" no startup — economia de tokens.
- **Gate de curadoria é assíncrono**: `ingest_docs` enfileira `raw` e
  retorna em <100ms. Reranker + LLM judge + curator rodam em background no
  worker, com status visível na TUI.
- **Curator granularity**: por batch com debounce de 30s. Ingestar 1000
  arquivos = 1 LLM call de síntese, não 1000.
- **Workspace ID**: `sha256(abspath(cwd))[:8]` — determinístico, estável.
- **Workspaces globais**: `workspace_id="__global__"` para docs não-pertencentes
  a workspace específico. `__legacy__` pra docs pré-B5 (migração).

#### Verificação

- Novo `tests/unit/test_services_workspace.py` — registry I/O, derivação de
  ID, naming de tabelas, edge case de cwd inexistente.
- Novo `tests/unit/test_agents_rag_curator.py` — mock do LLM de síntese,
  garante 1 call por flush (não N), debounce respeitado, manifest atualizado.
- Novo `tests/unit/test_tools_workspace.py` — `workspace_describe` lê
  MANIFEST.md, `bucket_summary` lê arquivo correto, `workspace_list` formata.
- Atualizar `test_nodes_rag_subgraph.py` — `_call_vector_search_all` com
  `workspace_id` filtra por prefix correto.
- Atualizar `test_agents_orchestrator.py` — `_load_session_context` inclui
  as 3 seções, invalidação por `project_context_stale`.
- Manual end-to-end:
  1. `cd ~/projetos/godot-ability-system && vectora` → cria workspace novo
  2. `/rag add docs/` → retorna **imediatamente** (status `raw` na fila),
     usuário continua conversando enquanto worker processa em background
  3. `/rag` panel mostra contagem evoluindo: raw → embedded → curated →
     indexed → summarized
  4. Aguarda ~30s após indexed (debounce) → MANIFEST.md aparece em
     `~/.vectora/workspaces/<id>/MANIFEST.md` automaticamente
  5. `/workspaces` → lista mostra o novo workspace com doc_count
  6. Nova mensagem: "o que você sabe sobre este projeto?" → orchestrator
     responde direto do manifest (já injetado no contexto), sem disparar RAG
  7. Nova mensagem: "lembra do que decidimos sobre validação?" → orchestrator
     identifica que precisa de memória episódica e dispara `get_memory`
     (não tá no contexto, é tool)
  8. `cd ~/projetos/vectora && vectora` → outro workspace, isolado
  9. Pergunta sobre ability system aqui não retorna lixo do workspace de
     Godot — busca usa `where="workspace_id == '<id_vectora>'"`

#### Ordem de implementação dentro do bloco

B5 (workspaces) → B6 (manifests) → B7 (context loading) → B4 (curator).
Curator vem por último porque depende dos 3 primeiros para ter o que ler e
onde escrever. B5 e B6 podem ser PRs separados.

---

### BLOCO C — v0.2.x (RAG & Memory avançados)

#### C1 — Hybrid RAG (Dense + Sparse BM25)

**O que está hoje:** Apenas busca densa (Cohere embeddings).
**O que já temos:** `rank-bm25>=0.2.2` na dep tree — não usado.
**O que muda:** Adicionar busca esparsa BM25 e fusão via Reciprocal Rank Fusion (RRF).

Pipeline:

```
query
  ├─► dense search (Cohere embeddings → LanceDB)  → ranked_dense
  └─► sparse search (BM25 → LanceDB FTS)          → ranked_sparse
                                                        ↓
                                               RRF merge
                                                        ↓
                                          top-K unified results
                                                        ↓
                                          CohereRerank (final)
```

Impacto: `vectora/nodes/retrieval.py`, `vectora/nodes/rag_subgraph.py`, `vectora/services/embedding.py`

#### C2 — Multi-query retrieval

**O que está hoje:** Uma única query para vector search.
**O que muda:** Gerar N variantes da query antes de buscar, fazer union dos resultados.

```python
async def _generate_query_variants(query: str, n: int = 3) -> list[str]:
    """LLM gera N reformulações da query para melhorar recall."""
    ...

# Executar em paralelo
results = await asyncio.gather(*[
    _call_vector_search(variant) for variant in variants
])
# Deduplicate + rerank
```

Impacto: `vectora/nodes/rag_subgraph.py` (novo nó `rag_multi_query`)

#### C3 — HyDE (Hypothetical Document Embedding)

**O que está hoje:** Query embedding direta.
**O que muda:** Para queries complexas ou abstratas, gerar um "documento hipotético" que responderia a query, embeddar esse documento, usar o vetor resultante para busca.

HyDE melhora recall para perguntas "o que é X?", "como funciona Y?" onde a query tem pouca sobreposição lexical com os documentos.

Impacto: `vectora/nodes/rag_subgraph.py` (condicional — ativado quando score < threshold)

#### C4 — LangGraph Store para memória namespaceada

**O que está hoje:** `MemoryStore` customizado com SQLite, user_id="default_user" hardcoded.
**O que muda:** Migrar para LangGraph `InMemoryStore` → `AsyncPostgresSaver`-compatible Store.

```python
store = InMemoryStore(index={"embed": cohere_embeddings, "dims": 1024})

# Em tools:
namespace = (session_id, "memories")
await store.aput(namespace, key, {"content": content})
memories = await store.asearch(namespace, query=current_query, limit=5)
```

Busca semântica em memórias (não só exata). Isolamento por session_id automático.

Impacto: `vectora/tools/memory.py`, `vectora/state.py`, `vectora/ui/chat.py`

#### C5 — Parallel agent execution

**O que está hoje:** Orchestrator delega para um agente de cada vez.
**O que muda:** Quando orchestrator identifica subtasks independentes, dispara múltiplos agentes em paralelo.

```python
# OrchestratorDecision expandido:
class OrchestratorDecision(BaseModel):
    action: Literal["respond", "delegate", "parallel"]
    parallel_tasks: list[SubTask] | None  # para action="parallel"

# Em graph.py:
if decision.action == "parallel":
    results = await asyncio.gather(
        coder(state_with_coder_task),
        search(state_with_search_task),
    )
```

Impacto: `vectora/agents/orchestrator.py`, `vectora/graph.py`, `vectora/state.py`

---

### BLOCO D — Vectora Chat (fork → stack TypeScript própria)

#### Contexto — o que foi forkado

O `chat/` é um fork do [chat-langchain](https://github.com/langchain-ai/chat-langchain). O projeto original era um assistente de documentação da LangChain com:

- **Backend Python** (`chat/src/`): LangGraph + FastAPI + LangSmith, deployado na LangGraph Cloud
  - `src/agent/docs_graph.py` — agente docs (busca Mintlify, Pylon KB, link check)
  - `src/api/` — FastAPI com auth customizada, rotas LangSmith, geração de título
  - `src/middleware/` — guardrails, retry, fallback de modelos
  - `src/tools/` — Mintlify search, Pylon, pricing, link check, Redis cache
- **Frontend Next.js** (`chat/frontend/`): `@langchain/langgraph-sdk` conectado ao LangGraph Server
  - Autenticação via Bearer token + X-Auth-Key
  - Streaming via SDK oficial (`/threads/{id}/runs`)
  - LangSmith feedback no browser

**O que muda:** todo o backend Python é removido. O chat recebe um backend TypeScript com **Hono** (integrado ao Next.js como route handler — mesmo processo, mesma porta) que se conecta ao **Vectora Agent** via ConnectRPC. O `vectora/api/` é um **módulo novo** do agente (não existe hoje), criado neste bloco.

---

#### D1 — Limpeza: remover o backend Python do fork

**O que vai:**

```
chat/src/              # todo o backend Python (agent, api, middleware, tools, prompts, utils)
chat/pyproject.toml    # dependências Python do chat-langchain
chat/langgraph.json    # config LangGraph Cloud
chat/tests/            # testes Python do chat-langchain
```

**O que vai no frontend (libs incompatíveis):**

```
chat/lib/api/langgraph-client.ts              # SDK LangGraph (substituído pelo Hono proxy)
chat/lib/api/langsmith.ts                     # LangSmith no browser (sem LangSmith no frontend)
chat/lib/hooks/threads/use-checkpoint-history.ts  # LangGraph-specific
```

**`package.json`** — remover:

- `@langchain/langgraph-sdk` — substituído por ConnectRPC client

**O que fica intacto:** todos os componentes React, hooks de UI, Radix UI, sistema de temas, shadcn/ui, utils — a UI não muda estruturalmente.

**Impacto:** remoção de `chat/src/`, `chat/pyproject.toml`, `chat/langgraph.json`, `chat/tests/`, 3 arquivos TS no frontend

---

#### D2 — `vectora/api/` — Novo módulo do agente (ConnectRPC + FastAPI)

**Este módulo não existe hoje.** Cria a camada de API pública que expõe o grafo LangGraph via ConnectRPC server-streaming. É o "servidor" que o chat consome.

**Proto service** (`vectora/api/protos/vectora/chat/v1/chat.proto`):

```proto
service ChatService {
  rpc StreamChat(StreamChatRequest) returns (stream StreamChatEvent);
  rpc ResumeChat(ResumeChatRequest) returns (stream StreamChatEvent);
  rpc GetTools(GetToolsRequest)     returns (GetToolsResponse);
}

service ThreadService {
  rpc CreateThread(CreateThreadRequest)   returns (Thread);
  rpc GetThread(GetThreadRequest)         returns (Thread);
  rpc ListThreads(ListThreadsRequest)     returns (ListThreadsResponse);
  rpc DeleteThread(DeleteThreadRequest)   returns (DeleteThreadResponse);
  rpc GetHistory(GetHistoryRequest)       returns (GetHistoryResponse);
}
```

**Eventos de streaming** (oneof em `StreamChatEvent`):

| Evento            | Campos                                                             | Quando                 |
| ----------------- | ------------------------------------------------------------------ | ---------------------- |
| `ThreadEvent`     | `thread_id`                                                        | Primeiro evento        |
| `TokenEvent`      | `content`, `node`                                                  | Chunk de texto do LLM  |
| `ToolCallEvent`   | `tool_name`, `args_json`, `render_hint`, `category`, `destructive` | Tool invocada          |
| `ToolResultEvent` | `tool_call_id`, `content_json`, `is_error`                         | Resultado              |
| `NodeEvent`       | `node`, `status`, `duration_ms`                                    | Nó iniciou/terminou    |
| `HITLEvent`       | `tool_name`, `args_json`, `interrupt_id`                           | Pausa HITL             |
| `UIMetricsEvent`  | `last_node_ms`, `rag_hits`, `rag_misses`, `tool_calls`             | Métricas em tempo real |
| `DoneEvent`       | `thread_id`, `run_id`                                              | Fim da execução        |
| `ErrorEvent`      | `message`, `code`                                                  | Erro                   |

**Estrutura:**

```
vectora/api/
├── __init__.py
├── protos/vectora/chat/v1/chat.proto
├── gen/                    # stubs buf — build-time, NÃO commitado
├── handlers/
│   ├── chat.py             # ChatServiceHandler: wraps graph.astream_events
│   └── threads.py          # ThreadServiceHandler: wraps AsyncSqliteSaver
├── adapters.py             # LangGraph event → StreamChatEvent proto
├── schemas.py              # Pydantic extras (/health, /metrics)
└── server.py               # FastAPI app factory + /api/tools/schema
```

**`vectora/main.py`** — novo subcomando `vectora server`:

```
vectora server mcp       # MCP stdio/SSE (porta 8000)
vectora server chat      # FastAPI + ConnectRPC + static files do chat
vectora server headless  # FastAPI + ConnectRPC sem UI
```

**Makefile** (raiz do projeto):

```makefile
gen-proto:
    cd vectora/api/protos && buf generate
    # → stubs Python em vectora/api/gen/
    # → stubs TypeScript em chat/lib/gen/

build-chat:
    cd chat && pnpm install && pnpm build
    rm -rf vectora/chat_static && mkdir -p vectora/chat_static
    cp -r chat/out/* vectora/chat_static/
```

**Deps Python:** `fastapi>=0.115`, `uvicorn[standard]>=0.34`, `connectrpc>=0.1`, `grpcio>=1.73`, `grpcio-tools>=1.73`

**Bundling no wheel:**

```toml
# pyproject.toml
[tool.hatch.build.targets.wheel]
include = ["vectora/**", "vectora/chat_static/**"]
```

**Impacto:** `vectora/api/` (novo módulo completo), `vectora/main.py` (+subcomando), `pyproject.toml` (+5 deps), `Makefile` (novo), `buf.yaml`/`buf.gen.yaml` (novo)

---

#### D3 — Schema no agente: `metadata=` em cada `@tool`

**Problema:** sem schema, o chat não sabe como renderizar cada tool call. Com schema, um único componente `<ToolCall>` adapta o renderer baseado em `render_hint` que vem no evento SSE — sem código TS por tool.

**Solução:** campo `metadata=` já suportado pelo decorator `@tool` do LangChain. O `ChatServiceHandler` lê e propaga no `ToolCallEvent`.

**Catálogo completo** (aplicado em `vectora/tools/*.py`):

| Tool               | render_hint       | category     | destructive | icon             |
| ------------------ | ----------------- | ------------ | ----------- | ---------------- |
| `file_read`        | `code_block`      | `filesystem` | false       | `file-text`      |
| `file_edit`        | `diff`            | `filesystem` | true        | `file-edit`      |
| `file_write`       | `code_block`      | `filesystem` | true        | `file-plus`      |
| `grep`             | `table`           | `filesystem` | false       | `search`         |
| `list_dir`         | `table`           | `filesystem` | false       | `folder`         |
| `terminal`         | `terminal_output` | `filesystem` | true        | `terminal`       |
| `web_search`       | `search_results`  | `web`        | false       | `globe`          |
| `fetch_url`        | `code_block`      | `web`        | false       | `link`           |
| `vector_search`    | `search_results`  | `rag`        | false       | `database`       |
| `embedding`        | `queue_badge`     | `rag`        | false       | `layers`         |
| `ingest_docs`      | `queue_progress`  | `rag`        | false       | `upload`         |
| `manage_retriever` | `table`           | `rag`        | true        | `settings`       |
| `create_artifact`  | `artifact`        | `artifacts`  | false       | `file-code`      |
| `save_memory`      | `json`            | `memory`     | false       | `bookmark`       |
| `get_memory`       | `json`            | `memory`     | false       | `bookmark-check` |
| `delete_memory`    | `json`            | `memory`     | true        | `bookmark-x`     |
| `search_memory`    | `search_results`  | `memory`     | false       | `search-check`   |

**Endpoint de descoberta** (`vectora/api/server.py`):

```python
@app.get("/api/tools/schema")
async def tools_schema():
    return {"tools": [
        {"name": t.name, "render_hint": (t.metadata or {}).get("render_hint", "json"),
         "category": (t.metadata or {}).get("category", "general"),
         "destructive": (t.metadata or {}).get("destructive", False),
         "icon": (t.metadata or {}).get("icon", "tool"),
         "args_schema": t.args_schema.model_json_schema() if t.args_schema else {}}
        for t in ALL_TOOLS
    ]}
```

**Impacto:** `vectora/tools/*.py` (adicionar `metadata=` em cada `@tool`), `vectora/api/server.py` (endpoint), `vectora/api/handlers/chat.py` (propagar campos no `ToolCallEvent`)

---

#### D4 — Backend TypeScript: Hono integrado ao Next.js

**Arquitetura:** Hono montado como handler catch-all do App Router. Chat e API no mesmo processo, mesma porta — sem CORS, sem servidor separado.

```
chat/app/api/[[...route]]/route.ts   ← mount do Hono app
chat/server/
├── index.ts                         # Hono app factory
├── routes/
│   ├── chat.ts                      # proxy ConnectRPC → vectora/api (SSE)
│   ├── threads.ts                   # CRUD threads via ConnectRPC
│   └── health.ts                    # /health + /metrics
└── lib/
    ├── connect-client.ts            # ConnectRPC transport → vectora agent
    └── proto-adapter.ts             # StreamChatEvent → SSE para o browser
```

**`server/index.ts`:**

```typescript
import { Hono } from "hono";
import { chatRoutes } from "./routes/chat";
import { threadRoutes } from "./routes/threads";

const app = new Hono().basePath("/api");
app.route("/chat", chatRoutes);
app.route("/threads", threadRoutes);
app.get("/health", (c) => c.json({ status: "ok" }));
export default app;
```

**`app/api/[[...route]]/route.ts`:**

```typescript
import { handle } from "hono/vercel";
import app from "@/server";
export const { GET, POST, DELETE } = handle(app);
```

**`server/routes/chat.ts`** — stream proxy:

```typescript
chatRoutes.post("/stream", async (c) => {
  const { thread_id, content, config } = await c.req.json();
  const stream = connectClient.streamChat({ thread_id, content, config });
  return streamSSE(c, async (sse) => {
    for await (const event of stream)
      await sse.writeSSE({ data: JSON.stringify(event) });
  });
});
```

**Deps TypeScript:** `hono>=4.7`, `@hono/node-server`, `hono/vercel`

**Impacto:** `chat/server/` (novo), `chat/app/api/[[...route]]/route.ts` (novo), `chat/package.json` (+hono)

---

#### D5 — `chat/lib/types/` — Módulo de tipos TypeScript

Espelha o proto + os metadados do agente. Permite componentes genéricos sem enumeração hardcoded de tools.

```
chat/lib/types/
├── index.ts        # re-exports
├── events.ts       # StreamEvent — union discriminada por "type"
├── messages.ts     # MessageSchema — unified message type
├── tools.ts        # ToolSchema, ToolCallSchema, ToolResultSchema
├── render.ts       # RenderHint, ToolCategory
└── thread.ts       # Thread, HistoryMessage
```

**`types/render.ts`:**

```typescript
export type RenderHint =
  | "diff"
  | "code_block"
  | "terminal_output"
  | "search_results"
  | "table"
  | "queue_progress"
  | "queue_badge"
  | "artifact"
  | "json";

export type ToolCategory =
  | "filesystem"
  | "web"
  | "rag"
  | "memory"
  | "artifacts";
```

**`types/events.ts`:**

```typescript
export type StreamEvent =
  | { type: "thread"; thread_id: string }
  | { type: "token"; content: string; node: string }
  | {
      type: "tool_call";
      tool_name: string;
      tool_call_id: string;
      args_json: string;
      render_hint: RenderHint;
      category: ToolCategory;
      destructive: boolean;
    }
  | {
      type: "tool_result";
      tool_call_id: string;
      content_json: string;
      is_error: boolean;
    }
  | {
      type: "node";
      node: string;
      status: "started" | "finished";
      duration_ms: number;
    }
  | { type: "hitl"; tool_name: string; args_json: string; interrupt_id: string }
  | {
      type: "ui_metrics";
      last_node: string;
      last_node_ms: number;
      rag_hits: number;
      rag_misses: number;
      tool_calls: Record<string, number>;
    }
  | { type: "done"; thread_id: string; run_id: string }
  | { type: "error"; message: string; code: string };
```

**Impacto:** `chat/lib/types/` (novo módulo), `chat/lib/gen/` (stubs ConnectRPC gerados pelo buf)

---

#### D6 — Arquitetura de componentes: schema-driven, sem explosão

**Princípio:** papel (`role`) determina cor/layout da mensagem; `render_hint` determina como o conteúdo da tool é exibido. Um `<Message>` e um `<ToolCall>` — sem componente por tipo.

```tsx
// components/message/Message.tsx
const roleStyles = {
  human: "bg-muted ml-auto max-w-[80%]",
  ai: "bg-background",
  tool: "bg-muted/50 font-mono text-sm border-l-2",
  system: "hidden",
};

export function Message({ msg }: { msg: MessageSchema }) {
  return (
    <div className={cn("rounded-lg p-3", roleStyles[msg.role])}>
      {msg.tool_calls?.map((tc) => (
        <ToolCall key={tc.tool_call_id} call={tc} />
      ))}
      <MarkdownContent content={msg.content} />
    </div>
  );
}
```

```tsx
// components/tool-call/ToolCall.tsx
const RENDERERS: Record<
  RenderHint,
  React.ComponentType<{ call: ToolCallSchema }>
> = {
  diff: DiffViewer, // react-diff-viewer-continued
  code_block: CodeBlock, // react-syntax-highlighter
  terminal_output: TerminalBlock, // styled pre dark
  search_results: SearchResults, // cards com score + fonte
  table: DataTable, // tabela paginada
  queue_progress: QueueProgress, // barra de progresso
  queue_badge: QueueBadge, // badge com status
  artifact: ArtifactCard, // card com ícone + download
  json: JsonViewer, // fallback universal
};

export function ToolCall({ call }: { call: ToolCallSchema }) {
  const Renderer = RENDERERS[call.render_hint] ?? RENDERERS.json;
  return (
    <div
      className={cn(
        "border rounded",
        call.destructive && "border-destructive/50",
      )}
    >
      <ToolCallHeader
        name={call.tool_name}
        category={call.category}
        icon={call.icon}
      />
      <Renderer call={call} />
    </div>
  );
}
```

**`useToolSchema`** — carregado via SWR na inicialização, cacheia por 60s:

```typescript
export function useToolSchema() {
  return useSWR<{ tools: ToolSchema[] }>("/api/tools/schema", fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 60_000,
  });
}
// render_hint vem no evento SSE; schema enriquece com icon e category
```

**Adicionar nova tool no agente com `metadata={"render_hint":"table"}` → funciona no chat sem nenhuma linha de TypeScript nova.**

**Impacto:** `chat/components/message/Message.tsx` (reescrito), `chat/components/tool-call/ToolCall.tsx` (reescrito), `chat/lib/hooks/use-tool-schema.ts` (novo)

---

#### D7 — SSE Heartbeat no MCP server

**O que está hoje:** Conexões SSE fechadas silenciosamente por firewalls (30–60s timeout).
**O que muda:** Heartbeat de 25s no MCP server SSE.

```python
async def _heartbeat():
    while True:
        await asyncio.sleep(25)
        yield ": heartbeat\n\n"
```

Impacto: `vectora/mcp/server.py` (SSE mode)

---

#### D8 — Observabilidade: métricas básicas por nó

**O que está hoje:** LangSmith tracing (opcional), logs estruturados.
**O que muda:** Métricas internas sem deps externas — latência por nó, contagem de tool calls, hit rate RAG, taxa HITL. Expostos via `/rag` na TUI e `UIMetricsEvent` no stream do chat.

Impacto: `vectora/services/tracer.py`, `vectora/ui/commands/debug.py`

---

#### D1 — `vectora/api/` — FastAPI + ConnectRPC

**O que muda:** Criar `vectora/api/` como a camada de API pública do Vectora. Expõe o grafo LangGraph via ConnectRPC (server-streaming RPC), gerencia threads via REST/RPC e serve o frontend compilado. Substitui o acesso direto ao `langgraph dev`.

**Três modos de servidor** (todos via `vectora server <modo>`):

| Modo       | Porta default | O que serve                                                               |
| ---------- | ------------- | ------------------------------------------------------------------------- |
| `mcp`      | 8000          | MCP server existente (`vectora/mcp/server.py`) — sem mudanças             |
| `chat`     | 8080          | FastAPI + ConnectRPC + static files do chat frontend                      |
| `headless` | 8080          | FastAPI + ConnectRPC só (sem static files) — para Paperclip e integrações |

---

##### D1.1 — Proto service design

**Arquivo:** `vectora/api/protos/vectora/chat/v1/chat.proto`

```proto
syntax = "proto3";
package vectora.chat.v1;

// Streaming de chat (server-streaming RPC)
service ChatService {
  rpc StreamChat(StreamChatRequest)  returns (stream StreamChatEvent);
  rpc ResumeChat(ResumeChatRequest) returns (stream StreamChatEvent);
  rpc GetTools(GetToolsRequest)     returns (GetToolsResponse);
}

// Gerenciamento de threads (checkpointer wrapper)
service ThreadService {
  rpc CreateThread(CreateThreadRequest)   returns (Thread);
  rpc GetThread(GetThreadRequest)         returns (Thread);
  rpc ListThreads(ListThreadsRequest)     returns (ListThreadsResponse);
  rpc DeleteThread(DeleteThreadRequest)   returns (DeleteThreadResponse);
  rpc GetHistory(GetHistoryRequest)       returns (GetHistoryResponse);
}

// ── request/response ─────────────────────────────────────────────

message StreamChatRequest {
  string thread_id       = 1;  // vazio = auto-criar
  string content         = 2;  // mensagem do usuário
  ChatConfig config      = 3;
}

message ChatConfig {
  string model           = 1;
  string llm_provider    = 2;
  int32  recursion_limit = 3;
  string workspace_id    = 4;
}

message ResumeChatRequest {
  string thread_id    = 1;
  string interrupt_id = 2;
  string decision     = 3;  // "approve" | "reject" | "edit:<json>"
}

// ── eventos de streaming ─────────────────────────────────────────

message StreamChatEvent {
  oneof event {
    ThreadEvent    thread     = 1;   // thread_id criado (1º evento)
    TokenEvent     token      = 2;   // chunk de texto do LLM
    ToolCallEvent  tool_call  = 3;   // tool foi invocada
    ToolResultEvent tool_result = 4; // resultado da tool
    NodeEvent      node       = 5;   // nó do grafo iniciou/terminou
    UIMetricsEvent ui_metrics = 6;   // métricas para MetricsPanel
    HITLEvent      hitl       = 7;   // pausa aguardando aprovação humana
    ErrorEvent     error      = 8;
    DoneEvent      done       = 9;
  }
}

message ThreadEvent     { string thread_id = 1; }
message TokenEvent      { string content = 1; string node = 2; }
message ToolCallEvent   { string tool_name = 1; string tool_call_id = 2;
                          string args_json = 3; string render_hint = 4; }
message ToolResultEvent { string tool_call_id = 1; string content_json = 2;
                          bool is_error = 3; }
message NodeEvent       { string node = 1; string status = 2;
                          int64 duration_ms = 3; }  // status: started|finished
message UIMetricsEvent  { string last_node = 1; int64 last_node_ms = 2;
                          int64 rag_hits = 3; int64 rag_misses = 4;
                          map<string, int64> tool_calls = 5; }
message HITLEvent       { string tool_name = 1; string args_json = 2;
                          string interrupt_id = 3; }
message ErrorEvent      { string message = 1; string code = 2; }
message DoneEvent       { string thread_id = 1; string run_id = 2; }

// ── thread management ────────────────────────────────────────────

message Thread          { string id = 1; string created_at = 2;
                          string updated_at = 3; string title = 4; }
message HistoryMessage  { string role = 1; string content = 2;
                          string created_at = 3; }
message CreateThreadRequest  {}
message GetThreadRequest     { string thread_id = 1; }
message ListThreadsRequest   { int32 limit = 1; }
message ListThreadsResponse  { repeated Thread threads = 1; }
message DeleteThreadRequest  { string thread_id = 1; }
message DeleteThreadResponse {}
message GetHistoryRequest    { string thread_id = 1; }
message GetHistoryResponse   { repeated HistoryMessage messages = 1; }

// ── tools schema ─────────────────────────────────────────────────

message GetToolsRequest  {}
message GetToolsResponse { repeated ToolSchema tools = 1; }
message ToolSchema       { string name = 1; string description = 2;
                           string render_hint = 3; string args_schema_json = 4; }
```

---

##### D1.2 — Estrutura `vectora/api/`

```
vectora/api/
├── __init__.py
├── protos/
│   └── vectora/chat/v1/
│       └── chat.proto
├── gen/                        # gerado por buf (commitar NÃO — build-time)
│   └── vectora_chat_v1/
│       ├── chat_pb2.py
│       ├── chat_pb2_grpc.py
│       └── chat_connect.py     # ConnectRPC servicer base classes
├── handlers/
│   ├── __init__.py
│   ├── chat.py                 # ChatServiceHandler (wraps graph.astream_events)
│   └── threads.py              # ThreadServiceHandler (wraps AsyncSqliteSaver)
├── adapters.py                 # LangGraph event → StreamChatEvent proto
├── schemas.py                  # Pydantic models extras (REST /health, /metrics)
└── server.py                   # FastAPI app factory
```

**`vectora/api/server.py`:**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from connectrpc.asgi import ConnectMiddleware
from pathlib import Path

from .handlers.chat import ChatServiceHandler
from .handlers.threads import ThreadServiceHandler

def create_app(serve_static: bool = True) -> FastAPI:
    app = FastAPI(title="Vectora API", version="0.1.0")

    # ConnectRPC services montados via middleware ASGI
    app.add_middleware(ConnectMiddleware, services=[
        ChatServiceHandler(),
        ThreadServiceHandler(),
    ])

    @app.get("/health")
    async def health(): return {"status": "ok", "version": settings.version}

    @app.get("/metrics")
    async def metrics(): return await tracer.get_recent(n=50)

    if serve_static:
        static = Path(__file__).parent.parent / "chat_static"
        if static.exists():
            app.mount("/", StaticFiles(directory=static, html=True), name="chat")

    return app
```

**`vectora/api/handlers/chat.py`:**

```python
class ChatServiceHandler:
    async def stream_chat(self, request, context):
        thread_id = request.thread_id or str(uuid4())
        yield StreamChatEvent(thread=ThreadEvent(thread_id=thread_id))

        async for event in graph.astream_events(
            {"messages": [HumanMessage(request.content)]},
            config={"configurable": {"thread_id": thread_id}, "recursion_limit": 50},
            version="v2",
        ):
            proto_event = adapters.langgraph_to_proto(event)
            if proto_event:
                yield proto_event

        yield StreamChatEvent(done=DoneEvent(thread_id=thread_id))
```

---

##### D1.3 — Codegen Makefile

**`Makefile` na raiz do projeto:**

```makefile
.PHONY: gen-proto build-chat

# Gera Python stubs + TypeScript clients a partir dos .proto
gen-proto:
    cd vectora/api/protos && buf generate
    @echo "✓ Stubs Python em vectora/api/gen/"
    @echo "✓ Clients TypeScript em chat/frontend/lib/gen/"

# Build do Next.js frontend + copia para vectora/chat_static/
build-chat:
    cd chat/frontend && pnpm install && pnpm build
    rm -rf vectora/chat_static
    mkdir -p vectora/chat_static
    cp -r chat/frontend/out/* vectora/chat_static/
    @echo "✓ Frontend compilado em vectora/chat_static/"
```

**`vectora/api/protos/buf.yaml`:**

```yaml
version: v2
modules:
  - path: .
```

**`vectora/api/protos/buf.gen.yaml`:**

```yaml
version: v2
plugins:
  - plugin: buf.build/protocolbuffers/python
    out: ../gen
  - plugin: buf.build/grpc/python
    out: ../gen
  - plugin: buf.build/connectrpc/python
    out: ../gen
  # TypeScript para o frontend
  - plugin: buf.build/bufbuild/es
    out: ../../../chat/frontend/lib/gen
  - plugin: buf.build/connectrpc/es
    out: ../../../chat/frontend/lib/gen
```

---

##### D1.4 — CLI: `vectora server`

**`vectora/main.py`** — novo subcomando:

```python
@app.command("server")
def server_cmd(
    mode: Annotated[str, typer.Argument(help="mcp | chat | headless")] = "chat",
    host: str = "0.0.0.0",
    port: int = 8080,
):
    """Inicia um servidor Vectora.

    Modos:
      mcp      — MCP server (ferramentas para IAs externas), porta 8000
      chat     — FastAPI + ConnectRPC + frontend compilado, porta 8080
      headless — FastAPI + ConnectRPC sem UI (para Paperclip/integrações)
    """
    if mode == "mcp":
        from vectora.mcp.server import run
        run()
    elif mode in ("chat", "headless"):
        import uvicorn
        from vectora.api.server import create_app
        serve_static = (mode == "chat")
        uvicorn.run(create_app(serve_static=serve_static), host=host, port=port)
    else:
        raise typer.BadParameter(f"modo desconhecido: {mode}")
```

---

##### D1.5 — Novas deps Python

```toml
# pyproject.toml — adicionar
[project.dependencies]
fastapi = ">=0.115"
uvicorn = { version = ">=0.34", extras = ["standard"] }
connectrpc = ">=0.1"          # ConnectRPC ASGI
grpcio = ">=1.73"
grpcio-tools = ">=1.73"
```

---

#### D2 — Frontend Migration (`chat/frontend/`)

**O que muda:** Substituir `@langchain/langgraph-sdk` por clientes ConnectRPC gerados. Todos os componentes de UI ficam intactos — apenas a camada de rede é trocada.

---

##### D2.1 — Deps: remover LangGraph SDK, adicionar ConnectRPC

```json
// chat/frontend/package.json — remover:
"@langchain/langgraph-sdk": "...",
"langsmith": "...",

// adicionar:
"@connectrpc/connect": "^2.0",
"@connectrpc/connect-web": "^2.0",
"@bufbuild/protobuf": "^2.0"
```

---

##### D2.2 — Cliente ConnectRPC

**Novo `chat/frontend/lib/api/vectora-client.ts`** (substitui `langgraph-client.ts`):

```typescript
import { createClient } from "@connectrpc/connect";
import { createConnectTransport } from "@connectrpc/connect-web";
import {
  ChatService,
  ThreadService,
} from "@/lib/gen/vectora/chat/v1/chat_connect";

const VECTORA_API_URL =
  process.env.NEXT_PUBLIC_VECTORA_API_URL ?? "http://localhost:8080";

const transport = createConnectTransport({
  baseUrl: VECTORA_API_URL,
});

export const chatClient = createClient(ChatService, transport);
export const threadClient = createClient(ThreadService, transport);
```

---

##### D2.3 — Hook de streaming

**Novo `chat/frontend/lib/hooks/chat/use-stream-handler.ts`** (substitui 873 linhas do LangGraph SDK):

```typescript
export function useStreamHandler() {
  const streamChat = useCallback(
    async (threadId: string, content: string, config: ChatConfig) => {
      for await (const event of chatClient.streamChat({
        threadId,
        content,
        config,
      })) {
        switch (event.event.case) {
          case "thread":
            onThreadCreated(event.event.value.threadId);
            break;
          case "token":
            appendToken(event.event.value.content);
            break;
          case "toolCall":
            addToolCall(event.event.value);
            break;
          case "toolResult":
            updateToolResult(event.event.value);
            break;
          case "hitl":
            showHITLPanel(event.event.value);
            break;
          case "uiMetrics":
            updateMetrics(event.event.value);
            break;
          case "done":
            finalize(event.event.value);
            break;
          case "error":
            handleError(event.event.value);
            break;
        }
      }
    },
    [],
  );
  return { streamChat };
}
```

---

##### D2.4 — Thread management

**Novo `chat/frontend/lib/hooks/threads/use-threads.ts`** (substitui LangGraph SDK threads):

```typescript
export function useThreads() {
  const createThread = () => threadClient.createThread({});
  const listThreads = () => threadClient.listThreads({ limit: 50 });
  const deleteThread = (id: string) =>
    threadClient.deleteThread({ threadId: id });
  const getHistory = (id: string) => threadClient.getHistory({ threadId: id });
  // ...
}
```

---

##### D2.5 — Static export (Next.js)

**`chat/frontend/next.config.ts`** — adicionar `output: 'export'`:

```typescript
const config: NextConfig = {
  output: "export", // ← static files em /out/
  // ...resto da config
};
```

Remove dependência de Node.js runtime no end-user. O `vectora server chat` serve os arquivos estáticos diretamente via FastAPI `StaticFiles`.

**Remover** (não compatíveis com static export):

- `chat/frontend/app/api/tools/schema/route.ts` (proxy server-side → não necessário, browser chama FastAPI direto)

**Atualizar** `chat/frontend/.env.example`:

```env
# URL do servidor Vectora (vectora server chat / headless)
NEXT_PUBLIC_VECTORA_API_URL=http://localhost:8080

# Removidos (não mais necessários):
# NEXT_PUBLIC_LANGGRAPH_API_URL
# LANGSMITH_API_KEY
```

---

#### D3 — Unificação e Distribuição

**O que muda:** Distribuição unificada via `uv tool install vectora-agent`. End-user não precisa de Node.js.

---

##### D3.1 — Limpeza da pasta `chat/`

Deletar (não pertencem ao Vectora):

- `chat/src/` — backend Python do chat-langchain (docs_agent, guardrails, etc.)
- `chat/langgraph.json` — deployment config LangGraph Cloud
- `chat/pyproject.toml` — deps Python do chat-langchain

Manter:

- `chat/frontend/` — o frontend Next.js (nossa UI)

---

##### D3.2 — Bundling no pacote Python

**`pyproject.toml`:**

```toml
[tool.hatch.build.targets.wheel]
include = [
  "vectora/**",
  "vectora/chat_static/**",  # ← Next.js compilado
]

[tool.uv.build]
include-package-data = true
```

**`MANIFEST.in`:**

```
recursive-include vectora/chat_static *
```

Fluxo de release:

```
make gen-proto   # gera stubs Python + TypeScript
make build-chat  # npm build → vectora/chat_static/
uv build         # inclui chat_static no wheel
uv publish       # versão final disponível em PyPI
```

---

##### D3.3 — Observabilidade integrada

O `VectoraTracer` é integrado ao ConnectRPC handler:

- Cada `StreamChat` abre um span `tracer.span("api", "stream_chat", session_id)`
- `NodeEvent` atualiza `ui_metrics` em tempo real
- `/metrics` REST endpoint expõe `get_recent(n=50)` para dashboards externos
- `vectora server headless` é a interface para Paperclip: sem frontend, só API ConnectRPC

---

#### D4 — Deletar referências ao `langgraph dev`

Arquivos a remover/atualizar:

| Arquivo                                                     | Ação                                                                 |
| ----------------------------------------------------------- | -------------------------------------------------------------------- |
| `langgraph.json` (raiz do projeto)                          | Deletar — era para `langgraph dev`, substituído por `vectora server` |
| `vectora/web/`                                              | Já renomeado para `chat/` — remover qualquer referência obsoleta     |
| `chat/frontend/lib/api/langgraph-client.ts`                 | Deletar (substituído por `vectora-client.ts`)                        |
| `chat/frontend/lib/api/langsmith.ts`                        | Deletar (sem LangSmith no novo stack)                                |
| `chat/frontend/lib/hooks/threads/use-checkpoint-history.ts` | Deletar (LangGraph-specific)                                         |

Dependências Python a remover de `pyproject.toml`:

- Nenhuma necessária imediatamente — `langgraph` permanece (grafo continua usando LangGraph); apenas o `langgraph dev` é abandonado

---

#### Verificação completa do Bloco D

1. `make gen-proto` → arquivos Python em `vectora/api/gen/`, TypeScript em `chat/frontend/lib/gen/`
2. `uv run vectora server chat` → inicia em `localhost:8080`
3. `curl localhost:8080/health` → `{"status": "ok"}`
4. `cd chat/frontend && pnpm dev` → chat disponível em `localhost:3000`, chama `localhost:8080`
5. Enviar mensagem → recebe `ThreadEvent` → `TokenEvent`s → `DoneEvent` via ConnectRPC streaming
6. HITL: tool destrutiva → `HITLEvent` chega no frontend → painel de aprovação → `ResumeChat`
7. `make build-chat` → gera `vectora/chat_static/`
8. `uv run vectora server chat` → `localhost:8080` serve tanto a API quanto o frontend (um único servidor)
9. `uv tool install vectora-agent` (após publish) → usuário sem Node.js consegue usar o chat web
10. `uv run vectora server headless` → só API ConnectRPC, sem static files → Paperclip conecta aqui
11. `uv run vectora server mcp` → MCP server intacto na 8000, sem mudanças
12. `uv run pytest tests/unit/test_api_chat.py tests/unit/test_api_threads.py -q` → verde

---

#### Arquivos críticos do Bloco D

| Arquivo                                              | Tipo              | Mudança                                    |
| ---------------------------------------------------- | ----------------- | ------------------------------------------ |
| `vectora/api/__init__.py`                            | novo              | pacote                                     |
| `vectora/api/protos/vectora/chat/v1/chat.proto`      | novo              | definição dos serviços                     |
| `vectora/api/gen/`                                   | novo (build-time) | stubs gerados pelo buf                     |
| `vectora/api/handlers/chat.py`                       | novo              | ChatServiceHandler                         |
| `vectora/api/handlers/threads.py`                    | novo              | ThreadServiceHandler                       |
| `vectora/api/adapters.py`                            | novo              | LangGraph event → proto                    |
| `vectora/api/server.py`                              | novo              | FastAPI app factory                        |
| `vectora/main.py`                                    | atualizado        | subcomando `server mcp/chat/headless`      |
| `pyproject.toml`                                     | atualizado        | +fastapi, +uvicorn, +connectrpc, +grpcio   |
| `Makefile`                                           | novo              | `gen-proto`, `build-chat`                  |
| `buf.yaml` / `buf.gen.yaml`                          | novo              | configuração buf                           |
| `chat/src/`                                          | deletado          | backend do chat-langchain                  |
| `chat/langgraph.json`                                | deletado          | LangGraph Cloud config                     |
| `chat/frontend/lib/api/vectora-client.ts`            | novo              | ConnectRPC transport                       |
| `chat/frontend/lib/api/langgraph-client.ts`          | deletado          | substituído                                |
| `chat/frontend/lib/hooks/chat/use-stream-handler.ts` | reescrito         | ConnectRPC streaming                       |
| `chat/frontend/lib/hooks/threads/use-threads.ts`     | reescrito         | ConnectRPC threads                         |
| `chat/frontend/lib/gen/`                             | novo (build-time) | stubs TypeScript gerados                   |
| `chat/frontend/next.config.ts`                       | atualizado        | `output: 'export'`                         |
| `langgraph.json` (raiz)                              | deletado          | `vectora server` substitui `langgraph dev` |
| `vectora/chat_static/`                               | novo (build-time) | Next.js compilado bundled no package       |
| `tests/unit/test_api_chat.py`                        | novo              | testa StreamChat handler                   |
| `tests/unit/test_api_threads.py`                     | novo              | testa ThreadService                        |

---

**O que está hoje:** TUI Rich exclusiva. Sem interface web de nenhum tipo.

**O que muda:** Web UI completa em Next.js hospedada em `vectora/web/` — projeto
separado do pacote Python, com lifecycle próprio (`npm`/`pnpm`).

---

##### Contexto — por que um projeto separado?

A TUI em `vectora/ui/` é ótima para desenvolvedores no terminal. A Web UI serve
um caso de uso diferente: demonstrações, compartilhamento de sessão por URL,
depuração visual do grafo, e acesso via browser sem instalar Python. São stacks
diferentes (Python/Rich vs Node/React) e devem coexistir, não se substituir.

`vectora/web/` é um projeto Next.js **independente** — tem seu próprio
`package.json`, `node_modules`, e roda no `localhost:3000`. Ele se conecta ao
backend LangGraph via `langgraph dev` (porta 2024) ou `langgraph serve`.

---

##### Arquitetura de conexão

```
Browser (localhost:3000)
  ↓  HTTP + SSE streaming
Next.js App (vectora/web/)
  ↓  NEXT_PUBLIC_API_URL=http://localhost:2024
LangGraph Dev Server (langgraph dev)
  ↓  carrega grafo via langgraph.json
vectora.graph:build_graph()
  ↓  AsyncSqliteSaver para checkpoints
~/.vectora/checkpoints.db
```

O Agent Chat UI da LangChain usa `@langchain/langgraph-sdk` (TypeScript) para se
comunicar com qualquer servidor LangGraph compatível. O SDK detecta automaticamente
o schema de `messages` (que o Vectora já expõe em `state.py`) e renderiza a UI.

---

##### Estrutura do projeto `vectora/web/`

Criado via `npx create-agent-chat-app`, com a estrutura de frontend apenas
(sem o `apps/agents/` do monorepo — o backend é o Vectora Python existente):

```
vectora/web/
├── package.json              # Node project — independente do pyproject.toml
├── pnpm-lock.yaml
├── next.config.mjs
├── tailwind.config.js        # Tema Vectora (cores customizadas)
├── tsconfig.json
├── postcss.config.mjs
├── .env.example              # Template de variáveis
├── .env.local                # ← NÃO commitado (.gitignore)
│     NEXT_PUBLIC_API_URL=http://localhost:2024
│     NEXT_PUBLIC_ASSISTANT_ID=vectora
│     # NEXT_PUBLIC_AUTH_SCHEME=   (opcional — deixar vazio p/ dev local)
│
├── public/
│   ├── logo.svg              # Logo Vectora
│   └── favicon.ico
│
└── src/
    ├── app/
    │   ├── layout.tsx        # Metadata: title="Vectora Chat"
    │   ├── page.tsx          # Redireciona para /chat
    │   └── chat/
    │       └── page.tsx      # Página principal do chat
    ├── components/
    │   ├── Header.tsx        # Logo + nome "Vectora"
    │   ├── ChatWindow.tsx    # Chat thread com streaming SSE
    │   ├── ToolCallCard.tsx  # Renderiza tool calls inline
    │   ├── HITLPanel.tsx     # Painel de aprovação (HITL B1 — futuro)
    │   └── ui/               # shadcn/ui components
    ├── hooks/
    │   ├── useStream.ts      # Hook de streaming SSE via langgraph-sdk
    │   └── useThread.ts      # Gestão de thread_id (sessão)
    └── lib/
        ├── client.ts         # LangGraphClient init com NEXT_PUBLIC_API_URL
        └── utils.ts
```

---

##### Pré-requisitos no Python (já existem)

- ✅ `langgraph.json` — aponta para `vectora.graph:build_graph` com `python_version: "3.12"`
- ✅ `state.py` — campo `messages: Annotated[Sequence[BaseMessage], add_messages]` (obrigatório pelo Agent Chat UI)
- ✅ `graph.py:build_graph()` — sem parâmetros obrigatórios, compatível com `langgraph dev`

O `langgraph dev` inicia o servidor em `localhost:2024` e expõe:

- `POST /runs/stream` — endpoint de streaming que o Agent Chat UI consome
- `GET /assistants` — lista grafos disponíveis
- `GET /threads/{thread_id}/history` — time-travel

---

##### Customizações Vectora

**Tema** (`tailwind.config.js`):

```js
colors: {
  brand: "#4F46E5";
} // cor indigo do Vectora
```

**Cabeçalho** (`Header.tsx`):

```tsx
<Image src="/logo.svg" alt="Vectora" /> <span>Vectora Chat</span>
```

**Metadata** (`layout.tsx`):

```tsx
export const metadata = {
  title: "Vectora Chat",
  description: "Vectora AI Agent",
};
```

**Renders customizados de tool calls** (`ToolCallCard.tsx`):

- `vector_search` → exibe resultados com relevance_score e fonte
- `web_search` → exibe snippets com link
- `file_read` / `file_edit` → exibe diff do arquivo
- `terminal` → exibe output como bloco de código
- `embedding` / `ingest_docs` → exibe progresso da fila

---

##### Setup inicial (uma vez)

```bash
# 1. Criar projeto com template oficial da LangChain
cd vectora
npx create-agent-chat-app web   # cria vectora/web/ com monorepo apps/web + apps/agents
# Remover apps/agents/ — o backend é o Vectora Python
rm -rf web/apps/agents

# 2. Mover o Next.js para a raiz de web/ (ou adaptar o monorepo)
# Estrutura final: vectora/web/ aponta para o frontend Next.js

# 3. Instalar com pnpm
cd web
pnpm install
```

##### Fluxo de desenvolvimento (dois terminais)

```bash
# Terminal 1 — backend LangGraph
langgraph dev          # porta 2024

# Terminal 2 — frontend Next.js
cd vectora/web
pnpm dev               # porta 3000
```

Acesse http://localhost:3000 → chat com streaming, tool calls visíveis,
time-travel por turno.

---

##### Features habilitadas pelo Agent Chat UI

| Feature                       | Disponível  | Dependência                                 |
| ----------------------------- | ----------- | ------------------------------------------- |
| Chat streaming (SSE)          | ✅ Imediato | `langgraph dev` + `messages` no state       |
| Tool calls inline             | ✅ Imediato | tool_calls nos AIMessages                   |
| Time-travel (replay)          | ✅ Imediato | checkpoints do `langgraph dev`              |
| State forking                 | ✅ Imediato | `langgraph dev`                             |
| Discovery Layer (auto-render) | ✅ D1.1     | `metadata={"render_hint":"..."}` nas tools  |
| Generative UI Engine          | ✅ D1.2     | `ui_component` no JSON de output das tools  |
| Live Graph Visualization      | ✅ D1.3     | `@xyflow/react` + `/assistants/vectora` API |
| State-Sync Observability      | ✅ D1.5     | `ui_metrics` no `state.py`                  |
| Mobile-first layout           | ✅ D1.6     | `shadcn/ui` + breakpoints Tailwind          |
| HITL (approve/reject)         | 🔄 Com B1   | `interrupt_before` no compile()             |
| Multi-sessão por URL          | ✅ Imediato | thread_id no params da URL                  |

---

##### Arquivo `.gitignore` (adições)

```gitignore
vectora/web/node_modules/
vectora/web/.next/
vectora/web/.env.local
vectora/web/out/
```

---

##### `.env.example` (commitado)

```env
# URL do servidor LangGraph (langgraph dev ou langgraph serve)
NEXT_PUBLIC_API_URL=http://localhost:2024

# Nome do grafo em langgraph.json (campo "graphs": {"vectora": ...})
NEXT_PUBLIC_ASSISTANT_ID=vectora

# Auth scheme — deixar vazio para dev local sem autenticação
# NEXT_PUBLIC_AUTH_SCHEME=langsmith-api-key
# LANGSMITH_API_KEY=sk_...
```

---

##### Integração com `langgraph-nextjs-api-passthrough` (produção)

Para expor a web UI publicamente sem vazar a URL interna do LangGraph:

```typescript
// src/app/api/langgraph/[...proxy]/route.ts
import { initApiPassthrough } from "@langchain/langgraph-sdk/api-passthrough";

export const { GET, POST, DELETE, PATCH } = initApiPassthrough({
  langgraphApiUrl: process.env.LANGGRAPH_API_URL, // server-side only
});
```

`.env.local` em produção:

```env
NEXT_PUBLIC_API_URL=https://meu-dominio.com/api/langgraph  # proxy Next.js
LANGGRAPH_API_URL=http://internal:2024                      # backend real
```

---

##### Impacto

| Arquivo/Pasta              | Tipo       | Mudança                                                                       |
| -------------------------- | ---------- | ----------------------------------------------------------------------------- |
| `vectora/web/`             | **novo**   | Projeto Next.js completo                                                      |
| `vectora/web/package.json` | **novo**   | `@langchain/langgraph-sdk`, `next`, `tailwindcss`, `shadcn/ui` — via **pnpm** |
| `vectora/web/.env.example` | **novo**   | Template de variáveis                                                         |
| `vectora/web/src/`         | **novo**   | Componentes React + hooks                                                     |
| `.gitignore`               | modificado | Adicionar `vectora/web/node_modules/`, `.next/`, `.env.local`                 |
| `langgraph.json`           | existente  | Nenhuma mudança necessária — já configurado                                   |
| `vectora/graph.py`         | existente  | Nenhuma mudança — `build_graph()` já compatível                               |

**Python backend:** Zero mudanças. O `langgraph dev` já sabe carregar o grafo.

---

---

##### D1.1 — Tool Discovery Layer 2.0 (Decorator-based, Auto-documented)

**Problema:** Cada vez que uma nova tool é adicionada ao `ALL_TOOLS` Python, o
desenvolvedor precisaria abrir o código React para registrar um novo `ToolCallCard`.
Com 18+ tools e crescendo, isso vira débito técnico em escala.

**Solução refinada: render_hint autodocumentado via `metadata` no próprio decorator.**
A tool declara como quer ser exibida **no mesmo lugar onde é definida** — sem dicionário
de mapeamento separado. A lógica de "onde essa tool pertence" fica junto com o código.

```python
# vectora/tools/rag.py
@tool(metadata={"render_hint": "search_results"})
async def vector_search(query: str, collection: str = "articles") -> str:
    """Realiza busca semântica no LanceDB com reranking Cohere."""
    ...

@tool(metadata={"render_hint": "queue_progress"})
async def ingest_docs(docs_pattern: str, collection: str = "articles") -> str:
    """Indexa pasta de documentos em batch."""
    ...

# vectora/tools/fs.py
@tool(metadata={"render_hint": "diff"})
async def file_edit(file_path: str, old_text: str, new_text: str) -> str:
    """Edita arquivo substituindo texto exato."""
    ...

@tool(metadata={"render_hint": "code_block"})
async def file_read(file_path: str) -> str:
    """Lê conteúdo de arquivo."""
    ...

@tool(metadata={"render_hint": "terminal_output"})
async def terminal(command: str) -> str:
    """Executa comando shell."""
    ...
```

**Catálogo completo de render_hints:**

| render_hint       | Tool(s)                   | Componente React                        |
| ----------------- | ------------------------- | --------------------------------------- |
| `search_results`  | `vector_search`           | Cards com score barra, fonte e trecho   |
| `web_results`     | `web_search`, `fetch_url` | Cards com favicon, URL e snippet        |
| `diff`            | `file_edit`               | Unified diff com cores (red/green)      |
| `code_block`      | `file_read`               | Syntax highlight por extensão           |
| `terminal_output` | `terminal`                | Fundo preto, monospace, scrollable      |
| `queue_progress`  | `ingest_docs`             | Barra de progresso + contagem N/total   |
| `queue_badge`     | `embedding`               | Badge com queue_id + status             |
| `table`           | `manage_retriever`        | Tabela paginada com source, score, date |
| `json`            | qualquer tool nova        | JSON expandível (fallback automático)   |

**Endpoint autodescoberta** (lido pelo frontend na inicialização):

```python
# vectora/mcp/server.py — novo @mcp.resource ou FastAPI route
@app.get("/api/tools/schema")
async def get_tools_schema():
    from vectora.nodes.tools import ALL_TOOLS
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "args_schema": t.args_schema.schema() if t.args_schema else {},
                "render_hint": (t.metadata or {}).get("render_hint", "json"),
            }
            for t in ALL_TOOLS
        ]
    }
```

**Frontend** (`useToolSchema.ts` hook):

```typescript
// Busca schema uma vez na inicialização, cacheia em memória
const { data: toolSchema } = useSWR("/api/tools/schema", fetcher, {
  revalidateOnFocus: false,
  dedupingInterval: 60_000,
});
// ToolCallCard usa: toolSchema[toolName]?.render_hint ?? 'json'
```

Adicionar nova tool ao Vectora Python = apenas incluir `metadata={"render_hint": "..."}`.
**Zero mudanças no React** para tools com hints conhecidos.

**Impacto:**

- `vectora/tools/*.py` — adicionar `metadata={"render_hint": "..."}` em cada `@tool`
- `vectora/mcp/server.py` — endpoint `/api/tools/schema` lê `t.metadata`
- `vectora/web/src/hooks/useToolSchema.ts` — hook SWR que cacheia o schema
- `vectora/web/src/components/ToolCallCard.tsx` — dispatch por `render_hint`

---

##### D1.2 — Generative UI Engine (Python controla a UI)

**Problema:** O Agent Chat UI renderiza o JSON de output das tools como texto expandível.
Ver `{"status": "success", "diff": "+line\n-line"}` é correto mas sem impacto visual.

**Solução:** As tools retornam um campo opcional `ui_component` no JSON de output.
O React checa esse campo e delega a renderização ao componente correspondente.
**Python decide como a saída quer ser exibida — sem hardcode no TypeScript.**

```python
# vectora/tools/fs.py — file_edit retorna diff formatado para UI
async def file_edit(file_path: str, old_text: str, new_text: str) -> str:
    # ... lógica de edição ...
    diff = _generate_unified_diff(old_text, new_text, file_path)
    return json.dumps({
        "status": "success",
        "file": file_path,
        "lines_changed": diff_stats["changed"],
        # Generative UI hint — React renderiza componente de diff bonito
        "ui_component": "file_diff",
        "data": {"diff": diff, "file_path": file_path, "language": _detect_lang(file_path)},
    })
```

```typescript
// vectora/web/src/components/ToolCallCard.tsx
interface ToolOutput {
  ui_component?: string  // nome do componente React a renderizar
  data?: Record<string, unknown>  // props do componente
  [key: string]: unknown  // outros campos padrão
}

export function ToolCallCard({ toolName, output }: Props) {
  const parsed: ToolOutput = JSON.parse(output)

  // Generative UI: se a tool declara o componente, use-o
  if (parsed.ui_component && parsed.data) {
    const Component = UI_COMPONENTS[parsed.ui_component]
    if (Component) return <Component {...parsed.data} />
  }

  // Fallback: render_hint do schema ou JSON expandível
  const hint = toolSchema[toolName]?.render_hint ?? 'json'
  return <StaticCard hint={hint} data={parsed} />
}

// Registro de componentes (cresce independentemente do backend)
const UI_COMPONENTS: Record<string, React.ComponentType<any>> = {
  'file_diff': FileDiffViewer,      // diff com syntax highlight
  'search_table': SearchResultsTable, // tabela com score visual
  'terminal_session': TerminalBlock,  // terminal interativo (futuro)
}
```

**Hierarquia de renderização:**

1. `ui_component` no output (Generative UI, máxima flexibilidade)
2. `render_hint` no schema (Discovery Layer, padrão por tipo de tool)
3. JSON expandível (fallback universal)

**Streaming de outputs grandes:** O `useStream.ts` suporta `partial_output` do
LangGraph — um diff grande aparece linha a linha enquanto a tool escreve, não
em um bloco só no final. Isso exige que as tools retornem via `yield` ou o
LangGraph streame os chunks nativamente (já suportado pelo SDK).

**Impacto:**

- `vectora/tools/fs.py` — `file_edit` retorna `ui_component: "file_diff"`
- `vectora/tools/rag.py` — `vector_search` retorna `ui_component: "search_table"`
- `vectora/tools/web.py` — `web_search` retorna `ui_component: "web_results"`
- `vectora/web/src/components/ToolCallCard.tsx` — hierarquia de renderização
- `vectora/web/src/components/FileDiffViewer.tsx` — **novo** componente de diff
- `vectora/web/src/components/SearchResultsTable.tsx` — **novo** tabela com scores

---

##### D1.3 — Live Graph Visualization (Debugging Visual)

**Problema:** Mesmo com tool calls visíveis, é difícil saber "em qual nó do grafo
o agente está agora" durante uma execução. O LangGraph Studio existe para isso,
mas requer janela separada e contexto diferente.

**Solução:** Embedar a visualização do grafo diretamente na Web UI como uma aba
opcional. O LangGraph já expõe a topologia via API — o frontend a consome e
destaca o nó ativo em tempo real via SSE.

```
┌─────────────────────────────────────┐
│ Vectora Chat  [Chat] [Graph] [Logs] │  ← tabs
├─────────────────────────────────────┤
│  Tab "Graph":                       │
│                                     │
│  START → [orchestrator] → [search] →│  ← nó atual destacado em laranja
│              ↓                      │
│           [coder] → [hitl_check]    │
│              ↓                      │
│           END                       │
│                                     │
│  Nó atual: search (347ms)           │
│  Próximo:  search_finalize          │
└─────────────────────────────────────┘
```

**Como funciona:**

1. **Topologia** — `GET localhost:2024/assistants/vectora` retorna o grafo serializado
   (nós + edges). O frontend carrega uma vez e monta o grafo com `@xyflow/react`
   (React Flow — a mesma lib usada pelo LangGraph Studio, open-source).

2. **Nó ativo** — o stream SSE emite eventos `metadata` com `langgraph_node` a cada
   step. O hook `useStream.ts` extrai esse campo e o expõe como `activeNode`.
   O componente GraphView destaca o nó correspondente em tempo real.

3. **Latência inline** — quando o nó termina, `ui_metrics.last_node_ms` (D1.2)
   aparece como badge no nó do grafo. Debugging visual de latência por nó.

```typescript
// vectora/web/src/components/GraphView.tsx
import ReactFlow, { Node, Edge } from '@xyflow/react'

export function GraphView({ graphSchema, activeNode, metrics }) {
  const nodes: Node[] = graphSchema.nodes.map(n => ({
    id: n.id,
    data: { label: n.id, ms: metrics[n.id]?.avg_ms },
    style: n.id === activeNode ? { border: '2px solid orange' } : {},
  }))
  const edges: Edge[] = graphSchema.edges.map(e => ({
    id: `${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
  }))
  return <ReactFlow nodes={nodes} edges={edges} fitView />
}
```

**Dependência adicional:** `@xyflow/react` (React Flow) — pacote leve (~150KB),
MIT license, usado pela LangChain/LangSmith internamente.

**Mobile:** A aba "Graph" é hidden em viewports < 768px (não faz sentido em tela
pequena). Em mobile, apenas as abas "Chat" e "Logs" ficam visíveis.

**Impacto:**

- `vectora/web/package.json` — adicionar `@xyflow/react`
- `vectora/web/src/components/GraphView.tsx` — **novo** visualizador de grafo
- `vectora/web/src/hooks/useStream.ts` — extrair `langgraph_node` do metadata
- `vectora/web/src/app/chat/page.tsx` — tabs: Chat | Graph | Logs

---

##### D1.5 — State-Sync Observability (`ui_metrics` no State)

**Problema:** Hoje o `VectoraTracer` grava spans em SQLite. A TUI lê via `/traces`.
A Web UI teria que reimplementar a lógica de agregação em TypeScript ou fazer
polling de um endpoint separado — duplicação.

**Solução:** Campo `ui_metrics` em `state.py` atualizado pelos nós principais.
Um dicionário serializável que ambas as interfaces consomem diretamente:

```python
# vectora/state.py — campo novo
ui_metrics: UIMetrics | None = None

@dataclass
class UIMetrics:
    last_node: str                    # nó que acabou de rodar
    last_node_ms: float               # latência desse nó
    total_tokens_session: int         # tokens acumulados na sessão
    rag_hits: int                     # buscas RAG que retornaram docs
    rag_misses: int                   # fallbacks para web
    tool_calls: dict[str, int]        # {tool_name: count} nesta sessão
    workspace_id: str | None          # workspace ativo
    manifest_version: int             # para detectar invalidação de cache
```

Cada nó que já usa `tracer.span()` também atualiza `ui_metrics` no retorno
(`Command(update={"ui_metrics": updated_metrics})`). O orchestrator já é o nó
central — ele agrega as métricas de cada delegação.

**TUI:** `/traces` e o status panel já funcionam via `VectoraTracer` (SQLite).
`ui_metrics` é um complemento leve — dados da **sessão atual** sem I/O extra.

**Web UI:** O Agent Chat UI transmite o state inteiro a cada step via SSE. O
campo `ui_metrics` aparece como um objeto tipado. Um componente `MetricsPanel.tsx`
na sidebar exibe latência, tokens e hit rate do RAG em tempo real, **sem polling**.

**Impacto:**

- `vectora/state.py` — adicionar `UIMetrics` dataclass + campo opcional no State
- `vectora/agents/orchestrator.py` — atualiza `ui_metrics` após cada delegação
- `vectora/web/src/components/MetricsPanel.tsx` — **novo** — sidebar com métricas
- `vectora/web/src/hooks/useStream.ts` — extrai `ui_metrics` do state stream

---

##### D1.6 — Mobile-First com shadcn/ui

**Razão:** O Vectora é o agente de desenvolvimento do usuário. Checar status de
um workspace ou enviar uma instrução rápida via celular enquanto longe do PC é
um caso de uso real e valioso.

**O que muda na Web UI:**

- Todos os componentes usam `shadcn/ui` (Radix UI + Tailwind) — acessível por
  padrão e responsivo.
- Layout com breakpoints: sidebar de métricas colapsa em mobile, chat ocupa
  tela cheia.
- `MetricsPanel` no mobile: barra de ícones condensada no topo (latência, tokens,
  workspace ativo) — sem sidebar flutuante que corta a tela.
- Input de texto: `textarea` com auto-resize e suporte a `Enter` para enviar
  (com `Shift+Enter` para nova linha) — consistente com a TUI.
- `ToolCallCard` em mobile: cards colapsados por padrão, expandem ao tap.

```tsx
// layout base — responsivo
<div className="flex h-screen flex-col md:flex-row">
  <aside className="hidden md:flex w-64 ...">
    {" "}
    {/* sidebar: só desktop */}
    <MetricsPanel />
  </aside>
  <main className="flex-1 overflow-y-auto">
    <ChatWindow />
    <div className="md:hidden">
      {" "}
      {/* metrics condensado: só mobile */}
      <MetricsBadges />
    </div>
  </main>
</div>
```

---

##### D1.7 — Heartbeat Adaptativo (evolução do D2)

O D2 fixou o heartbeat em 25s. Com a Web UI, faz sentido torná-lo adaptativo:

| Estado do Grafo                             | Intervalo Heartbeat | Razão                                |
| ------------------------------------------- | ------------------- | ------------------------------------ |
| `interrupt_before` (HITL pausado)           | 60s                 | Sem streaming, aguardando humano     |
| Nó leve em execução (`orchestrator` decide) | 15s                 | Curto, resposta rápida               |
| Nó pesado (`web_search`, `embedding`)       | 10s                 | Longo, keepalive mais frequente      |
| Idle (aguardando próxima mensagem)          | 60s                 | Sem processamento, economiza conexão |

Implementação: o orchestrator pode injetar `ui_metrics.current_stage` no state
a cada step. O SSE middleware lê esse campo e ajusta o intervalo do ping.
**Isso é uma melhoria futura** — o D2 atual (25s fixo) já resolve o problema
de firewalls. O adaptativo entra em `v0.3.x` ou junto com o deploy em produção.

---

##### Verificação completa

1. `langgraph dev` inicia sem erros → `Graph API running at localhost:2024`
2. `cd vectora/web && pnpm dev` → `ready at localhost:3000`
3. **Discovery Layer:** `GET localhost:2024/api/tools/schema` → JSON com 18+ tools,
   cada uma com `render_hint` extraído do `metadata` do decorator
4. Acessar `localhost:3000` → UI carrega com logo Vectora, sidebar MetricsPanel
5. Enviar mensagem → resposta streamed em tempo real; MetricsPanel atualiza ao vivo
6. **Generative UI:** Tool call `file_edit` → `ToolCallCard` exibe diff colorido
   (FileDiffViewer) porque o output contém `"ui_component": "file_diff"`
7. Tool call `web_search` → cards com favicon, URL clicável e snippet (web_results)
8. Tool call `terminal` → fundo preto, monospace, scrollable (terminal_output)
9. **Live Graph:** Aba "Graph" mostra topologia do Vectora; nó `search` destaca em
   laranja durante execução com latência em ms no badge
10. **State-Sync:** `ui_metrics.rag_hits` incrementa após query RAG bem-sucedida;
    `ui_metrics.tool_calls["web_search"]` sobe após cada busca
11. Clicar em turno anterior → replay do estado (time-travel LangGraph)
12. **Mobile:** Viewport < 768px → sidebar colapsa, tabs "Chat" e "Logs" visíveis,
    ToolCallCards colapsados por padrão (expandem ao tap)
13. `/traces` na TUI ainda funciona — as duas UIs coexistem sem conflito
14. **Auto-discovery de nova tool:** Adicionar nova `@tool(metadata={"render_hint":"table"})`
    no Python → na próxima inicialização do frontend, o schema é atualizado e o
    card correto é exibido sem nenhuma mudança no TypeScript

#### D2 — SSE Heartbeat

**O que está hoje:** Conexões SSE Docker fechadas silenciosamente por firewalls (30-60s timeout).
**O que muda:** Heartbeat de 25s no MCP server SSE.

```python
async def _heartbeat(writer: AsyncGenerator):
    while True:
        await asyncio.sleep(25)
        yield ": heartbeat\n\n"
```

Impacto: `vectora/mcp/server.py` (SSE mode)

#### D3 — Observabilidade: métricas básicas por nó

**O que está hoje:** LangSmith tracing (opcional), logs estruturados.
**O que muda:** Métricas internas sem deps externas:

- Latência por nó (orchestrator, search, coder, rag_subgraph)
- Contagem de tool calls por tipo
- Hit rate RAG (score distribution)
- Taxa de HITL approvals vs rejects

Expostos via `/rag` status no TUI e endpoint `/metrics` no MCP server.

Impacto: `vectora/services/tracer.py`, `vectora/ui/commands/debug.py`

---

### BLOCO E — v0.2.x (Robustez e qualidade)

#### E1 — EmbeddingStatus Enum + índice SQLite

**O que está hoje:** Magic strings "pending"/"processing"/"success"/"failed"/"dlq" em `queue.py`.
**O que muda:**

```python
class EmbeddingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    DLQ = "dlq"
```

- Índice: `Index("ix_queue_status", EmbeddingQueueRecord.status)` para queries O(log n).

Impacto: `vectora/services/queue.py`

#### E2 — DLQ cleanup automático

**O que está hoje:** Items em DLQ acumulam indefinidamente.
**O que muda:** `cleanup_old_records(days=30)` executado na startup do worker.

Impacto: `vectora/services/queue.py`, `vectora/services/background.py`

#### E3 — Background embedding backoff adaptativo

**O que está hoje:** Polling fixo a cada 5s mesmo quando fila vazia.
**O que muda:** Backoff exponencial quando fila vazia (5s → 10s → 30s, máx 60s). Reset ao encontrar items.

Impacto: `vectora/services/background.py`

---

## PARTE 2 — PÓS-DEEP AGENTS

Tudo nesta seção **requer a migração para o framework Deep Agents**. A migração é uma reescrita de `build_graph()` → `create_deep_agent()`.

**Arquitetura plugável:** SQLite + LanceDB permanecem como default self-hosted (roda em 4 núcleos / 8GB RAM). PostgreSQL, Qdrant e Redis são backends **opcionais** para deploys em escala — sem breaking change para o usuário padrão. Nenhum dos três é uma substituição obrigatória; são camadas que o operador ativa via config quando o volume ou os requisitos de concorrência justificam.

**Por que Deep Agents muda o jogo:**

- Framework opinionado sobre padrões de agentes de longa duração
- Sandbox backends (Modal, Daytona, Deno) para execução isolada — substitui blacklist
- Skills (SKILL.md) com progressive disclosure — não emulável nativamente no LangGraph
- HITL built-in com `interrupt_on` declarativo
- Multi-tenant server pronto (threads, RBAC, webhooks, streaming)
- ACP protocol para integração com editores (Zed, JetBrains, VS Code)
- CompiledSubAgent: LangGraph graph compilado rodando como subagente

---

### F1 — Migração para `create_deep_agent()`

Substitui `build_graph(checkpointer)` por:

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="google_genai:gemini-2.5-flash",
    tools=[web_search, vector_search, ...],  # tools customizadas do Vectora
    system_prompt=_ORCHESTRATOR_PROMPT,
    subagents=[coder_subagent, search_subagent],
    skills=["~/.vectora/skills/"],
    memory=["~/.vectora/memory/vectora.md"],
    checkpointer=checkpointer,
)
```

O que é absorvido pelo harness (não precisa mais manter):

- Loop de tool calls
- Compressão de contexto (automática a 85% da janela)
- Sistema de HITL (`interrupt_on`)
- Gestão de subagentes
- Permissões declarativas do filesystem

---

### F2 — PostgreSQL como checkpointer (opcional)

**Gated:** só implementar após F1.

```python
from langgraph.checkpoint.postgres import AsyncPostgresSaver

async with AsyncPostgresSaver.from_conn_string(POSTGRES_URL) as checkpointer:
    agent = create_deep_agent(..., checkpointer=checkpointer)
```

**Default continua sendo SQLite** (`AsyncSqliteSaver`) — sem breaking change. PostgreSQL é ativado via `CHECKPOINT_BACKEND=postgres` + `POSTGRES_URL` na config. A API do grafo não muda. SQLite permanece para embedding queue e memory (independentes do checkpointer).

Benefícios quando ativo: concurrent writes, connection pool, production-grade durability.

---

### F3 — Qdrant como vector store (opcional)

**Gated:** só implementar após F1.

```python
from qdrant_client import AsyncQdrantClient
from langchain_qdrant import QdrantVectorStore
```

**Default continua sendo LanceDB** — sem breaking change. Qdrant é ativado via `VECTOR_BACKEND=qdrant` + `QDRANT_URL` na config. A interface de `vector_search`/`embedding` não muda para o usuário. Ganhos quando ativo: melhor performance em escala, UI web própria, filtros avançados por metadata, sparse vectors nativos (BM42).

Impacto: `vectora/services/embedding.py`, `vectora/tools/rag.py` (abstração de provider via config)

---

### F4 — Redis como cache distribuído (opcional)

**Gated:** só implementar após F1.

**Default sem Redis** — cada camada tem fallback local (sem cache de embedding, sem LLM cache, checkpointer direto). Redis é ativado via `CACHE_BACKEND=redis` + `REDIS_URL` na config. Quando ativo, adiciona três camadas:

1. **Embedding cache**: evitar re-embeddar textos já vistos (hash → vector)
2. **LLM response cache**: respostas para queries idênticas
3. **Session state cache**: checkpoints quentes antes de descer para PostgreSQL (só relevante com F2)

```python
from langchain_redis import RedisCache
set_llm_cache(RedisCache(redis_url=REDIS_URL))
```

---

### F5 — Skills system (SKILL.md)

**Gated:** após F1.

Sistema de capacidades especializadas com progressive disclosure:

```
~/.vectora/skills/
├── python-debugging/
│   └── SKILL.md    # "Use when debugging Python errors"
├── git-workflow/
│   └── SKILL.md    # "Use when working with git"
└── code-review/
    └── SKILL.md
```

Cada skill é carregada sob demanda apenas quando relevante → economiza tokens. Skills podem ter scripts executáveis, docs de referência, templates.

---

### F6 — ACP Protocol (integração com editores)

**Gated:** após F1.

```bash
pip install deepagents-acp
```

Expõe o agente Vectora como servidor ACP, integrável nativamente com:

- Zed (suporte nativo)
- JetBrains (PyCharm, WebStorm, IntelliJ)
- VS Code (via plugin vscode-acp)
- Neovim

Diferença de MCP: MCP é agentes chamando ferramentas externas. ACP é editores controlando agentes.

---

### F7 — Multi-tenant production server

**Gated:** após F1.

**Implantação em dois passos:**

**Passo 1 — Servidor base** (sem autenticação): Deep Agents sobe o servidor com endpoints de streaming, gerenciamento de threads por usuário, histórico de execução e webhooks. Neste ponto o servidor está funcional mas aberto — adequado para rede interna ou como ponto de partida para adicionar auth.

**Passo 2 — Camada de autenticação**: adicionar JWT/API keys e RBAC (roles por usuário/org). Apenas neste passo o servidor está pronto para exposição pública ou multi-tenant real. Se F8 for declarado "concluído" sem este passo, a entrega é o servidor base sem auth — o que é um estado intermediário, não o estado final.

Inclui sandboxes isoladas por usuário (depende de F5).

Substitui o MCP SSE server atual para cenários multi-tenant.

---

### F8 — LangSmith A2A Protocol

**Gated:** após F1 + dois pré-requisitos concretos:

1. **`assistant_id` registrado no LangSmith** — o Vectora precisa estar deployado como assistant no LangSmith e ter um ID atribuído. Sem isso o endpoint `/a2a/{assistant_id}` não existe.
2. **Endpoint `/a2a/` ativamente exposto** — o servidor (F8) precisa estar rodando e o LangSmith precisa conhecer sua URL para rotear chamadas A2A.

Apenas quando esses dois pré-requisitos estiverem ativos o F9 pode ser implementado:

```
POST /a2a/{vectora_id}  ← outro agente chama Vectora como sub-agente
GET  /a2a/{vectora_id}/tasks/{task_id}  ← status assíncrono
```

`contextId` (thread de conversa) e `taskId` (requisição individual) mapeados automaticamente para LangSmith traces.

---

### F9 — Background memory consolidation

**Gated:** após F1 + F2 (PostgreSQL).

Agente separado que processa conversas entre sessões. O mecanismo de trigger precisa ser explicitamente definido — "roda após a sessão encerrar" não acontece sozinho:

- **Trigger**: ao encerrar o chat (`run_chat` → finally block), enfileira um job de consolidação via task queue (ex: Celery, arq, ou simple asyncio task com persistência). O job só roda se a sessão tiver pelo menos N mensagens novas desde a última consolidação.
- **O que o agente faz:**
  1. Lê histórico da sessão (PostgreSQL checkpoint via F2)
  2. Extrai preferências, decisões, padrões do usuário (1 LLM call estruturada)
  3. Grava em memória de longo prazo namespaceada (LangGraph Store ou tabela dedicada)
- **Não bloqueia o usuário** — o chat encerra normalmente; a consolidação roda de forma assíncrona. O usuário pode abrir uma nova sessão imediatamente.
- **Idempotente**: re-rodar para a mesma sessão sobrescreve, não duplica.

Sem o mecanismo de trigger implementado, F9 é apenas código morto — o agente existe mas nunca é chamado.

---

### BLOCO G — Agentes de Domínio

**Gated:** após F1.

Com Deep Agents, adicionar um novo domínio passa a ser ainda mais simples — o harness absorve o loop de tool calls, HITL e gestão de subagentes. Cada domínio novo é:

1. **`vectora/tools/<domain>.py`** — tools com `@tool(metadata={"render_hint": "..."})` registradas em `ALL_TOOLS`
2. **Subagente Deep Agents** — `system_prompt` especializado + tools habilitadas por domínio (não mais ALL_TOOLS para todos)
3. **`vectora/types/agents.py`** — `AgentName` expandido + `<Domain>Result(BaseModel)`
4. **Orquestrador atualizado** — nova regra de delegação + síntese pós-domínio

**`AgentName` expandido:**

```python
AgentName = Literal["coder", "search", "rag", "git", "office", "database", "communication"]
```

**Regras adicionadas ao prompt do orchestrator:**

- **git** → operações git (commit, branch, push, PR, diff, log, code review)
- **office** → criar/ler documentos (Word, Excel, PowerPoint, PDF)
- **database** → queries SQL, inspeção de schema, análise exploratória, migrações
- **communication** → enviar mensagens Slack, e-mail, criar tickets

**HITL automático (Deep Agents):** `db_migrate`, `git_commit`, `git_push`, `email_send` declarados em `interrupt_on` — sem código extra.

---

#### G1 — Git Agent

**Novas tools** (`vectora/tools/git.py`):

| Tool                                     | render_hint  | Descrição                               |
| ---------------------------------------- | ------------ | --------------------------------------- |
| `git_status()`                           | `diff`       | Arquivos modificados, staged, untracked |
| `git_log(n, branch)`                     | `code_block` | Histórico de commits                    |
| `git_diff(ref)`                          | `diff`       | Diff contra ref ou working tree         |
| `git_commit(message, files)`             | `code_block` | Stage seletivo + commit (HITL)          |
| `git_branch(action, name)`               | `code_block` | list / create / checkout / delete       |
| `gh_pr_create(title, body, base)`        | `code_block` | Criar PR via `gh` CLI                   |
| `gh_pr_list(state)`                      | `table`      | Listar PRs abertos/fechados             |
| `gh_pr_review(pr_number, verdict, body)` | `diff`       | Approve / request_changes / comment     |

**Implementação:** `gitpython>=3.1` para operações locais; `gh` CLI via `subprocess` para GitHub.

**`GitResult`** (`types/agents.py`):

```python
class GitResult(BaseModel):
    summary: str
    branch: str | None = None
    commits_created: list[str] = []
    pr_url: str | None = None
    files_changed: list[str] = []
    success: bool = True
```

**Deps:** `gitpython>=3.1`

---

#### G2 — Office Agent

**Novas tools** (`vectora/tools/office.py`):

| Tool                                           | render_hint  | Descrição                          |
| ---------------------------------------------- | ------------ | ---------------------------------- |
| `docx_create(title, content, output_path)`     | `json`       | Cria .docx com Markdown convertido |
| `docx_read(file_path)`                         | `code_block` | Extrai texto de .docx              |
| `xlsx_create(title, data_json, output_path)`   | `json`       | Cria planilha de JSON              |
| `xlsx_read(file_path, sheet)`                  | `table`      | Lê planilha como texto tabular     |
| `pptx_create(title, slides_json, output_path)` | `json`       | Cria apresentação de JSON          |
| `pdf_read(file_path, pages)`                   | `code_block` | Extrai texto de PDF                |

**`OfficeResult`** (`types/agents.py`):

```python
class OfficeResult(BaseModel):
    summary: str
    files_created: list[str] = []
    files_read: list[str] = []
    success: bool = True
```

**Deps:** `python-docx>=1.1`, `openpyxl>=3.1`, `python-pptx>=1.0`, `pdfplumber>=0.11`

---

#### G3 — Database Agent

**Novas tools** (`vectora/tools/database.py`):

| Tool                               | render_hint  | Descrição                                      |
| ---------------------------------- | ------------ | ---------------------------------------------- |
| `db_query(query, conn, read_only)` | `table`      | SELECT; DDL requer `read_only=False` + HITL    |
| `db_schema(table, conn)`           | `table`      | Descreve schema (colunas, tipos, índices)      |
| `db_migrate(script, conn)`         | `code_block` | DDL/DML (HITL automático via Deep Agents)      |
| `db_analyze(table, conn)`          | `table`      | Estatísticas descritivas, distribuições, nulos |

**Connection default:** `settings.database_url` (SQLite, PostgreSQL, MySQL).

**`DatabaseResult`** (`types/agents.py`):

```python
class DatabaseResult(BaseModel):
    summary: str
    rows_affected: int = 0
    query_executed: str | None = None
    schema_changed: bool = False
    success: bool = True
```

**Deps:** `langchain-community>=0.3` (já inclui `SQLDatabase`), `sqlalchemy>=2.0` (já presente)

---

#### G4 — Communication Agent

**Abordagem MCP-first:** conecta a servidores MCP (Slack, Gmail, Linear, Jira) via `MultiServerMCPClient`. Fallback com tools nativas quando MCP não está configurado.

**Configuração MCP** (`~/.vectora/mcp_servers.json` — opcional):

```json
{
  "slack": {
    "command": "npx",
    "args": ["@modelcontextprotocol/server-slack"],
    "env": { "SLACK_BOT_TOKEN": "xoxb-..." }
  },
  "gmail": {
    "command": "npx",
    "args": ["@modelcontextprotocol/server-gmail"],
    "env": { "GMAIL_CREDENTIALS": "~/.vectora/gmail-credentials.json" }
  },
  "linear": {
    "command": "npx",
    "args": ["@linear/mcp-server"],
    "env": { "LINEAR_API_KEY": "lin_api_..." }
  }
}
```

**Fallback tools nativas** (`vectora/tools/communication.py`):

| Tool                                   | render_hint | Dep                   | Env                               |
| -------------------------------------- | ----------- | --------------------- | --------------------------------- |
| `slack_message(channel, text)`         | `json`      | `slack-sdk>=3.27`     | `SLACK_BOT_TOKEN`                 |
| `email_send(to, subject, body)`        | `json`      | stdlib `smtplib`      | `SMTP_HOST/USER/PASSWORD`         |
| `ticket_create(title, body, platform)` | `json`      | `httpx` (já presente) | `LINEAR_API_KEY` / `GITHUB_TOKEN` |

**`CommunicationResult`** (`types/agents.py`):

```python
class CommunicationResult(BaseModel):
    summary: str
    messages_sent: int = 0
    tickets_created: list[str] = []
    recipients: list[str] = []
    success: bool = True
```

**Deps:** `slack-sdk>=3.27` (opcional, se não usar MCP)

---

#### Ordem dentro do bloco

G1 (Git) → G3 (Database) → G2 (Office) → G4 (Communication)

Git e Database têm utilidade imediata para desenvolvedores e deps mínimas. Office e Communication têm mais deps externas e integração MCP mais complexa.

#### Verificação

- `tests/unit/test_agents_git.py`, `test_agents_office.py`, `test_agents_database.py`, `test_agents_communication.py`
- `tests/unit/test_graph.py` — expected nodes expandido com novos agentes
- Manual: `"faça commit das minhas alterações com mensagem X"` → git agent → síntese orchestrator

---

### BLOCO H — App Desktop (v0.5.x — pós-Deep Agents)

#### Contexto — o que falta hoje

Vectora tem três frentes funcionando: CLI/TUI (`vectora chat`), MCP server (`vectora server mcp`) e Chat Web (`vectora server chat` + Next.js — Bloco D). Falta o **app desktop nativo**:

- Tray icon persistente (rodando em background)
- Notificações nativas do OS (HITL pendente, tarefa longa concluída)
- Janela dedicada sem aba de browser
- Drag-and-drop de arquivos para indexação
- **Path real pra mobile (Android/iOS)** — Flet permite reusar o mesmo código

Também serve para legitimar o pitch: hoje somos honestamente CLI + Web. Desktop é o próximo passo natural.

#### Princípio Arquitetural — dois modos no mesmo binário

| Modo                               | Quando usar                        | Stack                                                      |
| ---------------------------------- | ---------------------------------- | ---------------------------------------------------------- |
| **Embedded** (default ao instalar) | Solo dev, offline-first            | Agent in-process + SQLite + LanceDB                        |
| **Connected** (config explícita)   | Time compartilhando knowledge base | ConnectRPC → `vectora server` remoto + PG + Redis + Qdrant |

Mesmo binário, mesma UI. Troca de modo via tela de configurações — não exige reinstalar nada. A única diferença é o transporte: chamada in-process vs ConnectRPC. Toda a renderização de mensagens, tool calls, HITL é idêntica.

---

#### H1 — Framework: Flet

Flet é Python sobre Flutter — escolha alinhada com a stack do Vectora:

- **Async-native** — `async def main(page)`, compatível com `asyncio`/LangGraph sem wrapper
- **UI moderna** — Material 3, dark mode nativo, animações fluidas
- **Multi-target via `flet build`** — `windows`, `macos`, `linux`, `apk` (Android), `ipa` (iOS)
- **Hot reload** em dev
- **Reatividade nativa** — controla mudanças via `page.update()`, sem virtual DOM nem state management externo

Trade-off: bundle inclui Flutter runtime (~50MB no `.exe`/`.app` final). Aceito porque é o único caminho realista para mobile nativo sem reescrever a UI em Kotlin/Swift.

Alternativas descartadas:

- **CustomTkinter** — sync por padrão (wrap asyncio dá fricção), estética datada, zero path pra mobile
- **PyQt/PySide** — licença, complexidade, sem mobile sem reescrever
- **Tauri** — exigiria reescrever a UI em TypeScript (duplicação do chat web)

---

#### H2 — Estrutura `vectora/desktop/`

```
vectora/desktop/
├── __init__.py
├── app.py                  # entry — ft.app(target=main)
├── views/
│   ├── chat.py             # tela principal — chat + sidebar
│   ├── settings.py         # config: modo, server URL, model, theme
│   ├── workspaces.py       # /workspaces (lista + switch ativo)
│   ├── rag.py              # /rag panel (buckets, ingest, manage)
│   └── traces.py           # observabilidade (latência por nó, hit rate)
├── components/
│   ├── message.py          # Message (cor/layout por role)
│   ├── tool_call.py        # ToolCall (dispatch por render_hint)
│   ├── hitl_panel.py       # painel de aprovação HITL
│   ├── status_bar.py       # workspace + modelo + métricas
│   └── tray.py             # system tray + menu
├── client/
│   ├── adapter.py          # Protocol comum (interface única)
│   ├── embedded.py         # in-process — chama build_graph() direto
│   └── connected.py        # ConnectRPC client — fala com vectora server
└── config.py               # ~/.vectora/desktop.json
```

**Entry point novo** (`vectora/main.py`):

```
vectora desktop   # abre o app
```

---

#### H3 — Modo Embedded — agent in-process

Quando `mode="embedded"` (default):

- App inicia `BackgroundEmbeddingWorker` + `AsyncSqliteSaver` no startup
- `EmbeddedClient` chama `build_graph().astream_events()` diretamente — sem rede, sem porta exposta
- Reusa `~/.vectora/` (mesmo diretório do CLI) — sessões, memórias, LanceDB compartilhados com a TUI

Características:

- **Zero latência** de rede
- **Offline-first** (exceto LLM calls — Ollama resolve isso completamente)
- **Instalador único** — `.exe`/`.app`/AppImage com tudo dentro
- **Sem porta exposta** — nada para firewall reclamar

---

#### H4 — Modo Connected — ConnectRPC contra servidor remoto

Quando `mode="connected"`:

- Tela de config pede `server_url` (ex: `https://vectora.empresa.com`)
- `ConnectedClient` reusa o stub Python ConnectRPC gerado em D2
- Auth via Bearer token (opcional, configurado na mesma tela)
- Health check inicial — `GET /health` → status visível na status bar
- Se servidor cai, app continua aberto e mostra "Disconnected" — não crasha

**Caso de uso real:** empresa monta `vectora server headless` numa VPS com PG + Redis + Qdrant indexando o monorepo inteiro. Devs instalam o desktop e apontam — todos compartilham o mesmo knowledge base curado, sem cada um precisar indexar localmente.

---

#### H5 — UI: o schema-driven rendering do D6 é portado

A grande vantagem de termos `metadata=` nas tools (D3) e o `StreamChatEvent` tipado (D2) é que o desktop renderiza tool calls **com o mesmo schema** do chat web — só muda o framework de UI:

```python
# vectora/desktop/components/tool_call.py
RENDERERS: dict[str, Callable[[ToolCallEvent], ft.Control]] = {
    "diff":            diff_viewer,         # ft.Container + syntax highlight
    "code_block":      code_block,
    "terminal_output": terminal_block,
    "search_results":  search_results,
    "table":           data_table,
    "queue_progress":  queue_progress,
    "queue_badge":     queue_badge,
    "artifact":        artifact_card,
    "json":            json_viewer,
}

def tool_call(call: ToolCallEvent) -> ft.Control:
    renderer = RENDERERS.get(call.render_hint, json_viewer)
    return ft.Container(
        content=renderer(call),
        border=ft.border.all(1, ft.colors.RED if call.destructive else ft.colors.OUTLINE),
        padding=8,
    )
```

**Princípio:** uma nova tool com `metadata={"render_hint":"table"}` aparece corretamente no desktop **sem mudar nada na UI**. Schema é a fonte da verdade — desktop e web só implementam renderers; o agente decide qual usar.

---

#### H6 — Notificações + tray + background

Features que diferenciam o desktop do chat web:

- **System tray** — ícone Vectora persistente (`flet.Tray`); menu com `Abrir` / `Pausar agent` / `Sair`
- **Notificações nativas** — `page.show_notification()` para HITL pendente, `ingest_docs` concluído, erro de quota
- **Background mode** — fechar a janela esconde mas não termina; agent embedded continua processando fila
- **File drag-and-drop** — arrastar arquivos para o chat → `ingest_docs` automático (com confirmação se workspace não estiver definido)
- **Global hotkey** (futuro) — `Cmd/Ctrl+Shift+V` chama o Vectora de qualquer lugar

---

#### H7 — Mobile (Android/iOS) — não-P0, viabilidade preservada

Bloco H foca em desktop. Mobile é **roadmap futuro**, mas Flet desbloqueia o path sem reescrita:

- `flet build apk` → Android nativo
- `flet build ipa` → iOS nativo (requer macOS para assinar)

**Mobile força modo connected:** LanceDB e o background worker têm requisitos nativos que não rodam confortavelmente em mobile. App mobile é **cliente leve obrigatoriamente connected** apontando para um `vectora server` (VPS pessoal, doméstico, ou da empresa).

Isso será explicitado no pitch: desktop tem dois modos; mobile só connected.

---

#### H8 — Distribuição

| Plataforma       | Comando              | Artefato                            |
| ---------------- | -------------------- | ----------------------------------- |
| Windows          | `flet build windows` | `.exe` standalone (~80MB com agent) |
| macOS            | `flet build macos`   | `.app` bundle                       |
| Linux            | `flet build linux`   | AppImage                            |
| (futuro) Android | `flet build apk`     | `.apk`                              |
| (futuro) iOS     | `flet build ipa`     | `.ipa`                              |

**Canais:**

- GitHub Releases — binários pré-compilados (CI matrix por OS)
- Homebrew Cask: `brew install --cask vectora`
- Winget: `winget install vectora`
- Flatpak (Linux) — opcional

**Auto-update:** `flet.Page.client_storage` guarda versão atual; periodicamente checa `GET /releases/latest` no GitHub; popup oferece atualizar. Sem dep extra.

---

#### Dependências novas

```toml
flet>=0.25                  # framework
flet-runtime>=0.25          # runtime standalone
```

Não introduz dep no path padrão (`uv tool install vectora-agent`) — vai num extra:

```bash
uv tool install "vectora-agent[desktop]"
```

#### Verificação

- `uv run python -m vectora.desktop` → janela Flet abre, modo embedded ativo
- Configurações → "Modo: Connected" + URL → reconecta sem reiniciar
- Tool call `file_edit` em chat → DiffViewer Flet renderiza diff com cores
- HITL → notificação OS + dialog modal → `Approve`/`Reject` resume execução
- Drag arquivo `.md` na janela → `ingest_docs` enfileira (toast confirmação)
- `flet build windows` em CI → `.exe` < 100MB
- Tray: fechar janela → ícone permanece; click → reabre

---

#### Comparativo CLI vs Web vs Desktop (vai para o pitch)

| Característica      | CLI (TUI)         | Web (chat)                            | Desktop (Flet)                                 |
| ------------------- | ----------------- | ------------------------------------- | ---------------------------------------------- |
| Plataforma          | terminal          | qualquer browser                      | Win / macOS / Linux (+ Android/iOS roadmap)    |
| Instalação          | `uv tool install` | servidor + browser                    | instalador nativo                              |
| Dependência runtime | Python + uv       | Vectora Agent rodando + Node.js (dev) | nenhuma (embedded) ou agent remoto (connected) |
| Modo offline        | ✅                | ✅ (agent local)                      | ✅ (embedded)                                  |
| Notificações        | beep terminal     | toast browser                         | nativas do OS                                  |
| Tray icon           | ❌                | ❌                                    | ✅                                             |
| Background mode     | sessão tmux       | aba aberta                            | ✅ nativo                                      |
| Drag-and-drop       | ❌                | parcial                               | nativo                                         |
| Mobile              | ❌                | responsivo                            | nativo (roadmap H7)                            |
| Audio I/O (TTS/STT) | ❌ planejado      | ❌ planejado                          | ❌ planejado                                   |
| Auto-update         | uv                | recarregar                            | popup nativo                                   |

---

#### Comparativo de stacks (também para o pitch — honesto sobre trade-offs)

|                   | Stack Econômica (default)   | Stack Alto Desempenho (opt-in)           |
| ----------------- | --------------------------- | ---------------------------------------- |
| Checkpoint        | SQLite (`AsyncSqliteSaver`) | PostgreSQL (`AsyncPostgresSaver` — F2)   |
| Vector store      | LanceDB (file-based)        | Qdrant (`QdrantVectorStore` — F3)        |
| Cache             | sem cache                   | Redis (embedding + LLM — F4)             |
| Requisitos        | 4 cores / 8GB RAM           | 8+ cores / 16GB+ RAM + serviços externos |
| Concurrent writes | limitado                    | nativo                                   |
| Escalabilidade    | single-user                 | multi-tenant (F7)                        |
| Custo             | $0                          | infra paga                               |
| Setup             | `uv tool install`           | docker-compose + config                  |

A stack alto desempenho é **gated atrás do F1 (Deep Agents)** e ativada via config — sem breaking change pro usuário default.

---

## Ordem de implementação sugerida

```
[CONCLUÍDO]
  rc3:  A1 → A2 → A3 → A4 → A5 → A6 (hotfixes RAG)
  rc4:  D1 (vectora/api FastAPI+ConnectRPC) → D2 (frontend migration, remove LangGraph SDK) → D3 (cleanup+bundling) → D4 (delete langgraph.json)

[PRÓXIMOS]
  rc4:  types/ (Pydantic types system) → E1 (EmbeddingStatus enum) → E2 (DLQ cleanup) → E3 (backoff) → B1 (HITL)
  v0.1.0: B2 (structured outputs) → B3 (ToolRuntime)
           → B5 (workspaces por folder) → B6 (manifests) → B7 (context loading) → B4 (RAG curator)
  v0.2.0: C1 (Hybrid RAG) → C2 (multi-query) → C4 (Store memory) → C5 (parallel)
  v0.3.0: F1 (Deep Agents migration) → F5 (skills) → F6 (ACP)
           → G1 (Git) → G3 (Database) → G2 (Office) → G4 (Communication)
  v0.4.0: F2 (PostgreSQL) + F3 (Qdrant) + F4 (Redis) → F7 (multi-tenant)
  v0.5.0: H1–H6 (Desktop app — Flet, embedded + connected)
           → H8 (distribuição: brew/winget/AppImage)
  v0.6.0: F8 (A2A) → F9 (memory consolidation)
  v0.7.0: H7 (Mobile via flet build apk/ipa — connected only)
```

---

## O que o Deep Agents NÃO muda (Vectora continua dono)

- Sistema de RAG (subgraph adaptativo com thresholds) — Deep Agents não tem isso
- Background embedding worker com rate limiting — customização do Vectora
- MCP server (stdio + SSE) como sub-agente externo — Deep Agents foca em ACP, não MCP server
- create_artifact tool — conceito original do Vectora
- Session per directory — UX específica do Vectora
- Setup wizard multi-LLM — não existe no Deep Agents
- Verbosity 0-5 — TUI customizada do Vectora

---

## Arquivos críticos por bloco

| Bloco     | Arquivos impactados                                                                                                                                                                                                                                                    |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A1        | `vectora/tools/mcp.py`, `vectora/mcp/server.py`                                                                                                                                                                                                                        |
| A2        | `vectora/tools/rag.py`, `vectora/nodes/retrieval.py`                                                                                                                                                                                                                   |
| A3        | `vectora/tools/web.py`, `pyproject.toml`                                                                                                                                                                                                                               |
| A4        | `langgraph.json` (novo)                                                                                                                                                                                                                                                |
| A5        | `vectora/nodes/web_curation.py` (novo), `vectora/nodes/engine.py`, `vectora/nodes/rag_subgraph.py`, `vectora/tools/rag.py`, `vectora/nodes/tools.py`, `vectora/config/settings.py`, `vectora/mcp/server.py`                                                            |
| B1        | `vectora/graph.py`, `vectora/ui/chat.py`, `vectora/nodes/hitl.py` (novo)                                                                                                                                                                                               |
| B2        | `vectora/agents/coder.py`, `vectora/agents/search.py`, `vectora/agents/orchestrator.py`                                                                                                                                                                                |
| B3        | `vectora/tools/memory.py`, `vectora/tools/rag.py`                                                                                                                                                                                                                      |
| B4        | `vectora/services/background.py` (hook pós-batch), `vectora/agents/rag.py` (curator), `vectora/services/memory.py`                                                                                                                                                     |
| B5        | `vectora/services/workspace.py` (novo), `vectora/nodes/rag_subgraph.py`, `vectora/tools/rag.py`, `vectora/ui/commands/workspaces.py` (novo), `vectora/ui/commands/rag.py`, `vectora/context.py`, `vectora/ui/chat.py`                                                  |
| B6        | `vectora/tools/workspace.py` (novo), `vectora/services/workspace.py` (manifest I/O), `vectora/nodes/tools.py`, `vectora/mcp/server.py`                                                                                                                                 |
| B7        | `vectora/agents/orchestrator.py` (`_load_session_context`), `vectora/tools/memory.py` (namespace), `vectora/services/workspace.py` (manifest read)                                                                                                                     |
| C1        | `vectora/nodes/retrieval.py`, `vectora/nodes/rag_subgraph.py`                                                                                                                                                                                                          |
| C2        | `vectora/nodes/rag_subgraph.py`                                                                                                                                                                                                                                        |
| C4        | `vectora/tools/memory.py`, `vectora/state.py`                                                                                                                                                                                                                          |
| C5        | `vectora/agents/orchestrator.py`, `vectora/graph.py`                                                                                                                                                                                                                   |
| types/    | `vectora/types/__init__.py`, `types/agents.py`, `types/documents.py`, `types/curation.py`, `types/session.py`, `types/workspace.py` (novos); `state.py`, `agents/orchestrator.py`, `agents/results.py`, `nodes/web_curation.py`, `services/workspace.py` (atualizados) |
| D1        | `chat/src/` (deletado), `chat/pyproject.toml` (deletado), `chat/langgraph.json` (deletado), `chat/lib/api/langgraph-client.ts` (deletado), `chat/package.json` (-sdk)                                                                                                  |
| D2        | `vectora/api/` (novo módulo completo), `vectora/main.py` (+server), `pyproject.toml` (+fastapi/connectrpc/grpcio), `Makefile` (novo), `buf.yaml` (novo)                                                                                                                |
| D3        | `vectora/tools/*.py` (metadata= em cada @tool), `vectora/api/server.py` (/tools/schema)                                                                                                                                                                                |
| D4        | `chat/server/` (novo), `chat/app/api/[[...route]]/route.ts` (novo), `chat/package.json` (+hono)                                                                                                                                                                        |
| D5        | `chat/lib/types/` (novo módulo), `chat/lib/gen/` (build-time)                                                                                                                                                                                                          |
| D6        | `chat/components/message/Message.tsx` (reescrito), `chat/components/tool-call/ToolCall.tsx` (reescrito), `chat/lib/hooks/use-tool-schema.ts` (novo)                                                                                                                    |
| D7        | `vectora/mcp/server.py` (SSE heartbeat)                                                                                                                                                                                                                                |
| D8        | `vectora/services/tracer.py`, `vectora/ui/commands/debug.py`                                                                                                                                                                                                           |
| E1-E3     | `vectora/services/queue.py`, `vectora/services/background.py`                                                                                                                                                                                                          |
| G1        | `vectora/tools/git.py` (novo), `vectora/agents/git.py` (novo), `vectora/graph.py`, `vectora/types/agents.py`, `vectora/nodes/tools.py`, `pyproject.toml`                                                                                                               |
| G2        | `vectora/tools/office.py` (novo), `vectora/agents/office.py` (novo), `vectora/graph.py`, `vectora/types/agents.py`, `vectora/nodes/tools.py`, `pyproject.toml`                                                                                                         |
| G3        | `vectora/tools/database.py` (novo), `vectora/agents/database.py` (novo), `vectora/config/settings.py` (`database_url`), `vectora/graph.py`, `vectora/types/agents.py`, `vectora/nodes/tools.py`                                                                        |
| G4        | `vectora/tools/communication.py` (novo), `vectora/agents/communication.py` (novo), `vectora/graph.py`, `vectora/types/agents.py`, `vectora/nodes/tools.py`                                                                                                             |
| G (todos) | `vectora/agents/orchestrator.py` (regras + sínteses), `vectora/state.py` (4 novos campos result)                                                                                                                                                                       |
| H1        | `pyproject.toml` (extra `[desktop]` — flet, flet-runtime)                                                                                                                                                                                                              |
| H2        | `vectora/desktop/` (novo módulo: `app.py`, `views/`, `components/`, `client/`, `config.py`), `vectora/main.py` (+`desktop` subcomando)                                                                                                                                 |
| H3        | `vectora/desktop/client/embedded.py` (in-process — reusa `build_graph`)                                                                                                                                                                                                |
| H4        | `vectora/desktop/client/connected.py` (ConnectRPC stub gerado em D2)                                                                                                                                                                                                   |
| H5        | `vectora/desktop/components/tool_call.py` (RENDERERS por `render_hint`)                                                                                                                                                                                                |
| H6        | `vectora/desktop/components/tray.py`, `vectora/desktop/components/hitl_panel.py`                                                                                                                                                                                       |
| H7        | `flet build apk/ipa` (CI matrix mobile — futuro)                                                                                                                                                                                                                       |
| H8        | `.github/workflows/release-desktop.yml` (CI matrix Windows/macOS/Linux)                                                                                                                                                                                                |
| F1        | `vectora/graph.py` (rewrite), `pyproject.toml` (add deepagents)                                                                                                                                                                                                        |
| F2-F4     | `pyproject.toml`, `vectora/services/checkpoint.py`, `vectora/services/embedding.py`                                                                                                                                                                                    |
