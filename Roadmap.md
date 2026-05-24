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

> **Esta diretiva rege a manutenção e evolução da arquitetura de tipos do projeto.**

### Regras Obrigatórias para Evolução

1. **Centralização em `vectora/types/`**: Todo novo modelo de dados (estado intermediário, resultado de agente, métrica, ou schema) deve ser adicionado exclusivamente em `vectora/types/`. Módulos de domínio (`agents/`, `nodes/`, `services/`) contêm apenas lógica de execução — jamais definições de tipos complexos.

2. **Pydantic como padrão**: Todos os modelos de dados devem herdar de `pydantic.BaseModel`. O uso de `TypedDict` é restrito apenas à definição de `State` para compatibilidade estrita com o LangGraph.

3. **Sintaxe moderna (PEP 585 / PEP 604)**:
   - Use `list[str]`, `dict[str, Any]`, `str | None`.
   - É proibido importar coleções básicas (`List`, `Dict`, `Optional`, etc.) do módulo `typing`. Use tipos nativos sempre.

4. **Contratos de Interface**: Mantenha o `state.py` como a camada de "bridge". Campos de estado que representam resultados ou decisões de agentes devem ser obrigatoriamente tipados pelos modelos Pydantic definidos em `vectora/types/`, garantindo a validação no fluxo de execução.

5. **Vectora Chat (TypeScript)**: A mesma rigorosidade se aplica ao frontend. Todos os dados vindos do agente devem ser mapeados em interfaces centralizadas em `chat/src/types/`. Evite `any` a todo custo, utilizando as interfaces definidas para garantir que a UI reflita fielmente o estado do grafo.

6. **Infraestrutura via Decoradores**: A lógica de infraestrutura (tracing, observabilidade, contexto de workspace, HITL) deve ser aplicada de forma transparente via decoradores (`@trace_node`, `@workspace_aware`, etc.), mantendo a lógica de negócio dos nós limpa e legível.

### Estrutura do Catálogo (`vectora/types/`)

A pasta `vectora/types/` é a fonte única da verdade para a estrutura de dados. Ao adicionar novas funcionalidades, siga o arquivo correspondente:

- `agents.py`: Decisões do orquestrador e resultados de agentes.
- `documents.py`: Estruturas de documentos e artifacts.
- `curation.py`: Schemas para julgamento de conteúdo.
- `session.py`: Metadados persistentes de sessão.
- `workspace.py`: Definições de workspaces e estados de projeto.
- `metrics.py`: Schemas para observabilidade via `ui_metrics`.

### Manutenção e Expansão

- **Ao criar uma nova Tool**: Adicione o `metadata={"render_hint": "..."}` ao decorador `@tool` para permitir a autodescoberta pela Web UI (D1.1).
- **Ao modificar nós**: Certifique-se de que o contrato de entrada/saída (via `State`) respeita os tipos Pydantic definidos em `types/`.
- **Linting**: O projeto segue *Strict Typing*. Qualquer novo código deve passar na validação de tipo sem o uso de `Any` explícito, priorizando o uso de `Union` ou `Discriminated Unions` quando a estrutura for variável.

---

## PARTE 1 — PRÉ-DEEP AGENTS

Tudo nesta seção é implementável com **LangGraph + LangChain puros**, sem nenhuma dependência do Deep Agents framework. Organizado por blocos de lançamento (rc3 → rc4 → v0.1.0 → v0.2.x).

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

### BLOCO D — v0.2.x (UI & Observabilidade)

#### D1 — Vectora Web UI (Next.js + Agent Chat UI)

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

#### D4 — Vectora Chat Self-Hosted & Distribuição npm

Com a evolução do Vectora como uma solução de RAG e agentes self-hosted de alta performance, a interface gráfica de chat também precisa seguir o mesmo modelo de implantação autônoma e descentralizada. Para garantir que o chat possa rodar de forma opcional e isolada, a estrutura foi desacoplada fisicamente do backend em Python.

**O que está hoje:** A interface Web (Vectora Web UI) foi originalmente planejada na pasta interna `vectora/web/` como um subdiretório do projeto Python, misturando o ciclo de vida e a publicação do pacote Python com a aplicação Next.js.

**O que muda:** O projeto frontend Next.js é movido para a raiz do repositório, renomeado para a pasta `chat/`. Essa pasta opera de forma totalmente independente e desacoplada do backend Python, permitindo que a interface Web seja publicada e consumida de forma isolada do pacote principal.

##### Empacotamento e Publicação (vectora-chat no npm)

Para disponibilizar o frontend de forma modular para a comunidade e usuários self-hosted, ele é configurado para ser distribuído como um pacote npm autônomo sob a identidade `vectora-chat`:

1. **Nome do Pacote:** O `package.json` do frontend foi renomeado de `vectora-web` para `vectora-chat` e o sinalizador `"private": true` foi removido para permitir a sua publicação pública.
2. **Distribuição Standalone & NPM:** O chat em Next.js é configurado para compilar em produção de forma independente. O executável global (`bin/vectora-chat.js`) permite iniciar o servidor Next.js em produção (`next start`) com uma única chamada após ser instalado via `npm install -g vectora-chat`.
3. **Distribuição Docker & Compose:** Para implantações em servidores reais (VPS), um `Dockerfile` multi-stage com `output: 'standalone'` foi implementado, e o fluxo CI/CD foi ajustado para buildar a imagem `vectora-chat:latest`.
4. **Infraestrutura com Traefik:** O `docker-compose.traefik.yml` gerencia o tráfego em rede, unificando os dois contêineres sob o mesmo domínio (ex: `chat.seudominio.com`). O front assume o tráfego da raiz e as rotas `/api` e `/sse` são encaminhadas diretamente ao LangGraph (motor Python).

Fluxo de Execução Pública NPM:

```bash
# Instalação global do chat via npm
npm install -g vectora-chat

# Execução direta
vectora-chat
```

Essa arquitetura garante que novos desenvolvedores e empresas possam usar o Vectora Python puro (com MCP e RAG local no terminal) ou subir sua stack completa visual nativamente (NPM ou Docker).

Impacto: `chat/package.json` (renomeação e remoção de private), `.gitignore` da raiz (ajuste de caminhos de exclusão de artefatos).

---

### BLOCO E — v0.2.x (Robustez e qualidade)

#### E1 — Reflection pattern (auto-crítica)

**O que está hoje:** Orchestrator responde inline, sem revisão.
**O que muda:** Nó de reflexão opcional entre resposta do agente e entrega ao usuário.

```
orchestrator → [reflect] → END
               (compara resposta com task_query,
                avalia completude, retorna se necessário)
```

Configurável: ativo apenas para `delegate_to="coder"` e `delegate_to="search"`, não para `respond` inline.

Impacto: novo `vectora/nodes/reflect.py`, `vectora/graph.py`

#### E2 — EmbeddingStatus Enum + índice SQLite

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

#### E3 — DLQ cleanup automático

**O que está hoje:** Items em DLQ acumulam indefinidamente.
**O que muda:** `cleanup_old_records(days=30)` executado na startup do worker.

Impacto: `vectora/services/queue.py`, `vectora/services/background.py`

#### E4 — Background embedding backoff adaptativo

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

### F5 — Sandbox backends para terminal

**Gated:** após F1.

Substitui a blacklist-based security atual por execução em ambiente isolado:

```python
agent = create_deep_agent(
    ...,
    sandbox=ModalSandbox(image="python:3.14-slim"),  # ou DaytonaSandbox / DenoSandbox
)
```

- O terminal roda dentro do sandbox, não na máquina host
- Sem necessidade de blacklist — isolamento por design
- Cada sessão recebe sandbox efêmero
- Suporte a imagens Docker customizadas

---

### F6 — Skills system (SKILL.md)

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

### F7 — ACP Protocol (integração com editores)

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

### F8 — Multi-tenant production server

**Gated:** após F1.

**Implantação em dois passos:**

**Passo 1 — Servidor base** (sem autenticação): Deep Agents sobe o servidor com endpoints de streaming, gerenciamento de threads por usuário, histórico de execução e webhooks. Neste ponto o servidor está funcional mas aberto — adequado para rede interna ou como ponto de partida para adicionar auth.

**Passo 2 — Camada de autenticação**: adicionar JWT/API keys e RBAC (roles por usuário/org). Apenas neste passo o servidor está pronto para exposição pública ou multi-tenant real. Se F8 for declarado "concluído" sem este passo, a entrega é o servidor base sem auth — o que é um estado intermediário, não o estado final.

Inclui sandboxes isoladas por usuário (depende de F5).

Substitui o MCP SSE server atual para cenários multi-tenant.

---

### F9 — LangSmith A2A Protocol

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

### F10 — Background memory consolidation

**Gated:** após F1 + F2 (PostgreSQL).

Agente separado que processa conversas entre sessões. O mecanismo de trigger precisa ser explicitamente definido — "roda após a sessão encerrar" não acontece sozinho:

- **Trigger**: ao encerrar o chat (`run_chat` → finally block), enfileira um job de consolidação via task queue (ex: Celery, arq, ou simple asyncio task com persistência). O job só roda se a sessão tiver pelo menos N mensagens novas desde a última consolidação.
- **O que o agente faz:**
  1. Lê histórico da sessão (PostgreSQL checkpoint via F2)
  2. Extrai preferências, decisões, padrões do usuário (1 LLM call estruturada)
  3. Grava em memória de longo prazo namespaceada (LangGraph Store ou tabela dedicada)
- **Não bloqueia o usuário** — o chat encerra normalmente; a consolidação roda de forma assíncrona. O usuário pode abrir uma nova sessão imediatamente.
- **Idempotente**: re-rodar para a mesma sessão sobrescreve, não duplica.

Sem o mecanismo de trigger implementado, F10 é apenas código morto — o agente existe mas nunca é chamado.

---

## Ordem de implementação sugerida

```
rc3:  A1 (MCP adapters) → A2 (Cohere input_type) → A3 (Tavily v2) → A4 (Studio)
      → A5 (anti-contaminação RAG: bucket web + gate reranker/judge + manage_retriever)
rc4:  E2 (EmbeddingStatus enum) → E3 (DLQ cleanup) → E4 (backoff) → B1 (HITL)
v0.1.0 stable: B2 (structured outputs) → B3 (ToolRuntime)
                → B5 (workspaces por folder) → B6 (manifests) → B7 (context loading) → B4 (RAG curator)
v0.2.0: C1 (Hybrid RAG) → C2 (multi-query) → C4 (Store memory) → C5 (parallel)
v0.2.1: D1 (Web UI) → D2 (SSE heartbeat) → D3 (métricas) → E1 (reflection)
v0.3.0: F1 (Deep Agents migration) → F5 (sandbox) → F6 (skills) → F7 (ACP)
v0.4.0: F2 (PostgreSQL) + F3 (Qdrant) + F4 (Redis) → F8 (multi-tenant)
v0.5.0: F9 (A2A) → F10 (memory consolidation)
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

| Bloco | Arquivos impactados                                                                                                                                                                                                   |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A1    | `vectora/tools/mcp.py`, `vectora/mcp/server.py`                                                                                                                                                                       |
| A2    | `vectora/tools/rag.py`, `vectora/nodes/retrieval.py`                                                                                                                                                                  |
| A3    | `vectora/tools/web.py`, `pyproject.toml`                                                                                                                                                                              |
| A4    | `langgraph.json` (novo)                                                                                                                                                                                               |
| A5    | `vectora/nodes/web_curation.py` (novo), `vectora/nodes/engine.py`, `vectora/nodes/rag_subgraph.py`, `vectora/tools/rag.py`, `vectora/nodes/tools.py`, `vectora/config/settings.py`, `vectora/mcp/server.py`           |
| B1    | `vectora/graph.py`, `vectora/ui/chat.py`, `vectora/nodes/hitl.py` (novo)                                                                                                                                              |
| B2    | `vectora/agents/coder.py`, `vectora/agents/search.py`, `vectora/agents/orchestrator.py`                                                                                                                               |
| B3    | `vectora/tools/memory.py`, `vectora/tools/rag.py`                                                                                                                                                                     |
| B4    | `vectora/services/background.py` (hook pós-batch), `vectora/agents/rag.py` (curator), `vectora/services/memory.py`                                                                                                    |
| B5    | `vectora/services/workspace.py` (novo), `vectora/nodes/rag_subgraph.py`, `vectora/tools/rag.py`, `vectora/ui/commands/workspaces.py` (novo), `vectora/ui/commands/rag.py`, `vectora/context.py`, `vectora/ui/chat.py` |
| B6    | `vectora/tools/workspace.py` (novo), `vectora/services/workspace.py` (manifest I/O), `vectora/nodes/tools.py`, `vectora/mcp/server.py`                                                                                |
| B7    | `vectora/agents/orchestrator.py` (`_load_session_context`), `vectora/tools/memory.py` (namespace), `vectora/services/workspace.py` (manifest read)                                                                    |
| C1    | `vectora/nodes/retrieval.py`, `vectora/nodes/rag_subgraph.py`                                                                                                                                                         |
| C2    | `vectora/nodes/rag_subgraph.py`                                                                                                                                                                                       |
| C4    | `vectora/tools/memory.py`, `vectora/state.py`                                                                                                                                                                         |
| C5    | `vectora/agents/orchestrator.py`, `vectora/graph.py`                                                                                                                                                                  |
| E1    | `vectora/nodes/reflect.py` (novo), `vectora/graph.py`                                                                                                                                                                 |
| E2-E4 | `vectora/services/queue.py`, `vectora/services/background.py`                                                                                                                                                         |
| F1    | `vectora/graph.py` (rewrite), `pyproject.toml` (add deepagents)                                                                                                                                                       |
| F2-F4 | `pyproject.toml`, `vectora/services/checkpoint.py`, `vectora/services/embedding.py`                                                                                                                                   |
