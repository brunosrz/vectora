# Vectora Deep Engine — Estado Atual e Roadmap

> **Privado.** Auditoria do "motor" do Vectora (agente + grafo + streaming
>
> - persistência + memória + segurança) contra a documentação canônica da
>   LangChain/LangGraph/Deep Agents consultada via MCP `docs-langchain` em
>   junho/2026. Este doc é a fonte de verdade para o que precisa entrar
>   no roadmap pós-E para entregar um **backend robusto, escalável e seguro**
>   usando o melhor dos três frameworks.

---

## Sumário executivo

O Vectora hoje implementa uma versão **funcional** mas **artesanal** do
padrão Deep Agents. O que entregamos no Bloco E é equivalente em
**comportamento** à proposta canônica do `create_deep_agent`, mas é
**não-equivalente em superfície** — perdemos middleware nativo, profiles
por modelo, backends pluggable, streaming v3, structured output,
guardrails prontos e o ecossistema LangSmith.

> **Clarificação importante sobre o Bloco E**: o bloco E está marcado
> ✅ Concluído porque entregou (a) o `agent_factory` consolidado com
> cache versionado por user, (b) a TUI textual (`vectora chat`) e (c)
> os 9 sub-blocos E1–E9 (com E2 ⏳ parcial). **Não** significa que
> migramos para `create_deep_agent`. A dep `deepagents>=0.6.3` está
> instalada (foi adicionada antecipando essa migração), mas
> `grep -r "from deepagents" src/` retorna **0 resultados**. O grafo
> atual usa `langgraph.StateGraph` direto, com nós artesanais para
> orchestrator/coder/search/HITL. O bloco **DE** descrito aqui é
> exatamente o fechamento dessa lacuna: aproveitar o que já fizemos
> em E como base e migrar a superfície para a API canônica.

Esta é a lacuna que separa "um agente que funciona" de "um agente
production-ready que escala". O bloco **DE — Deep Engine** descrito ao
final desse documento fecha cada uma dessas frentes em 14 sub-tarefas
ortogonais.

**Filosofia central a internalizar**:

> "Deep Agents é um **harness** sobre LangChain (componentes) + LangGraph
> (runtime). Não substitui nenhum — adiciona uma camada opinionada de
> filesystem virtual, subagents, planning, skills, memória, sandboxes,
> middleware, HITL e prompt caching com defaults sensatos."

Quando você escreve `create_deep_agent(...)` está obtendo um
`CompiledStateGraph` do LangGraph com middleware da LangChain embutidos
— pode ser composto, estendido, injetado em outro `StateGraph` ou
serializado normalmente. Não há mágica nova; é uma fábrica.

---

## 1. Como o motor está hoje (auditoria por capacidade)

| #   | Capacidade                           | Hoje                                                                       | Canônico (Deep Agents)                                                                                                                       | Status                                              |
| --- | ------------------------------------ | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| 1   | Construção do agente                 | `agent_factory.build_graph()` artesanal em `src/services/agent_factory.py` | `create_deep_agent(model=, tools=, subagents=, middleware=, backend=, memory=, skills=, permissions=, interrupt_on=, response_format=, ...)` | ❌ Custom                                           |
| 2   | Orquestração de subagents            | Funções async (`coder`, `search`) + nós de finalize                        | Subagents como `dict {name, description, prompt, tools, model}` ou `AsyncSubAgent`; harness expõe `task` tool automaticamente                | ⏳ Parcial — comportamento ok, superfície diferente |
| 3   | HITL                                 | Nó `hitl_check` custom + `interrupt()` raw                                 | `HumanInTheLoopMiddleware(interrupt_on={"tool": {"allowed_decisions": [...]}})`                                                              | ❌ Custom                                           |
| 4   | Permission modes (ask/auto/plan/...) | Mapping próprio em `get_interrupt_on()`                                    | `interrupt_on` ou `HumanInTheLoopMiddleware` com `allowed_decisions`                                                                         | ⏳ Diferente                                        |
| 5   | Filesystem virtual                   | `src/tools/fs.py` artesanal + `resolve_within_workspace`                   | `StateBackend` (default), `FilesystemBackend(root_dir=, virtual_mode=True)`, `StoreBackend`, `CompositeBackend`                              | ❌ Custom                                           |
| 6   | Filesystem permissions               | scope-guard manual por tool                                                | `permissions=[FilesystemPermission(...)]` com `first-match-wins`                                                                             | ❌ Custom                                           |
| 7   | Skills (procedural memory)           | `services/skills.py` próprio                                               | `skills=["./skills/"]` + `SKILL.md` frontmatter; carregamento on-demand pelo harness                                                         | ⏳ Comportamento ok, integração ausente             |
| 8   | Memory (long-term)                   | `services/memory.py` com `cohere.AsyncClient` direto + cosine custom       | `memory=["AGENTS.md"]` + `StoreBackend(namespace=lambda rt: (rt.server_info.user.identity,))`                                                | ❌ Custom                                           |
| 9   | Context compression                  | Truncamento manual em alguns nós                                           | `SummarizationMiddleware(model=, trigger=("tokens", 4000), keep=("messages", 20))`                                                           | ❌ Ausente                                          |
| 10  | Prompt caching                       | Ausente                                                                    | Anthropic prompt caching automático via Profile + `cache_control: "ephemeral"`                                                               | ❌ Ausente                                          |
| 11  | Profiles por modelo                  | Ausente                                                                    | `HarnessProfile(excluded_tools=, excluded_middleware=, reasoning_effort=, prompt_cache=)` registrável por provider/modelo                    | ❌ Ausente                                          |
| 12  | Sandboxes                            | Terminal PTY local sem isolamento                                          | `Modal/E2B/Deno/Daytona Sandbox` ou `LocalShellBackend(root_dir=, env=)`; exec tool automática                                               | ❌ Ausente                                          |
| 13  | Interpreters                         | Ausente                                                                    | `eval` tool em QuickJS scoped (programmatic tool calling)                                                                                    | ❌ Ausente                                          |
| 14  | Streaming                            | `astream_events v2` parseado em `src/api/adapters.py`                      | `stream_events(version="v3")` com projeções tipadas: `.messages`, `.tool_calls`, `.subagents`, `.values`, `.output`                          | ⏳ Funciona, mas versão antiga                      |
| 15  | Async subagents                      | Sequencial (`parallel_dispatch` artesanal)                                 | `AsyncSubAgent` + background workers + cancelamento + progress                                                                               | ❌ Ausente                                          |
| 16  | Structured output                    | Ausente                                                                    | `response_format=PydanticModel` → `result["structured_response"]`; auto-seleciona `ProviderStrategy` ou `ToolStrategy`                       | ❌ Ausente                                          |
| 17  | Multi-tenancy                        | Manual via `user_id` em `configurable`                                     | `context_schema=Context` + `rt.server_info.user.identity` (autenticação resolve identidade automática quando deployado)                      | ⏳ Funciona, mas sem auth handler                   |
| 18  | Persistence                          | `AsyncSqliteSaver` ✓                                                       | `AsyncSqliteSaver` / `AsyncPostgresSaver` / Managed (auto)                                                                                   | ✅                                                  |
| 19  | LangGraph Store                      | Ausente (memória via cohere custom)                                        | `InMemoryStore` / `PostgresStore` com semantic search nativo                                                                                 | ❌ Ausente                                          |
| 20  | Time travel / forking                | Ausente                                                                    | `update_state(as_node=...)` + replay de `checkpoint_id`                                                                                      | ❌ Ausente                                          |
| 21  | Fault-tolerance / pending writes     | Implícito (LangGraph default)                                              | LangGraph reinicia do último checkpoint; pending writes não re-executam                                                                      | ✅                                                  |
| 22  | Guardrails (PII)                     | Ausente                                                                    | `PIIMiddleware(pii_type=, strategy=)` para email, credit_card, ip, api_key, etc                                                              | ❌ Ausente                                          |
| 23  | Model retry / fallback               | Implícito (LangChain)                                                      | `ModelRetryMiddleware`, `ModelFallbackMiddleware`, `ToolRetryMiddleware`                                                                     | ❌ Ausente                                          |
| 24  | Cost / call limits                   | Ausente                                                                    | `ModelCallLimitMiddleware(thread_limit=, run_limit=, exit_behavior=)` + `ToolCallLimitMiddleware`                                            | ❌ Ausente                                          |
| 25  | LangSmith tracing                    | Ausente                                                                    | `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY` → traces automáticos                                                                       | ❌ Ausente                                          |
| 26  | LangSmith Engine                     | Ausente                                                                    | Monitora traces, detecta issues, sugere fixes                                                                                                | ❌ Ausente                                          |
| 27  | ACP (Agent Control Protocol)         | Planejado em I4                                                            | `deepagents-acp.server` + `adapter` + `ide-integration`                                                                                      | ⏳ Planejado                                        |
| 28  | Frontend SDK                         | Adapter SSE custom em `chat/src/lib/api/vectora-client.ts`                 | `@langchain/langgraph-sdk` + `useStream` hook + `useStream.subagents`                                                                        | ❌ Custom                                           |

**Resumo numérico**:

- ✅ implementado canonicamente: 2
- ⏳ comportamento ok / superfície diferente: 6
- ❌ ausente ou custom-only: 20

Esses 20 itens ❌ são exatamente o que separa o Vectora do estado da arte
no ecossistema LangChain. Cada um tem um sub-bloco DE no roadmap.

---

## 2. Filosofia: framework × runtime × harness

Para tomar decisões certas no roadmap precisamos parar de confundir os
três níveis (a fonte de muita confusão hoje no código):

```
┌─────────────────────────────────────────────────────────┐
│  Deep Agents (HARNESS — opinionado, "agent factory")    │
│  - create_deep_agent + middleware + subagents + skills  │
│  - filesystem virtual + backends + sandboxes            │
│  - prompt caching + context compression                 │
├─────────────────────────────────────────────────────────┤
│  LangChain (FRAMEWORK — componentes reusáveis)          │
│  - BaseChatModel, BaseTool, init_chat_model             │
│  - middleware system (HITL, Summarization, PII, retry)  │
│  - structured output (Provider/Tool strategies)         │
│  - guardrails, prompts, parsers                         │
├─────────────────────────────────────────────────────────┤
│  LangGraph (RUNTIME — execução durável)                 │
│  - StateGraph + nodes + edges + checkpointer            │
│  - BaseStore (long-term memory) + threads + super-steps │
│  - interrupts + time travel + pending writes            │
│  - streaming v3 + subgraphs + namespaces                │
└─────────────────────────────────────────────────────────┘
```

**Regra prática**: ao adicionar capacidade nova,

1. Pergunte: existe **middleware** LangChain pronto? Use.
2. Pergunte: existe **backend** Deep Agents pronto? Use.
3. Pergunte: o LangGraph já oferece **primitiva** (checkpoint, store,
   interrupt)? Use.
4. **Só** se as três respostas forem "não" você escreve código novo.

Hoje nós quebramos essa regra dezenas de vezes — `services/memory.py`,
`services/agent_factory.hitl_check`, `tools/fs.py`,
`services/security.py::resolve_within_workspace`, todos têm equivalente
canônico que dá conta do mesmo problema com menos código, mais features,
e integração com LangSmith de graça.

---

## 3. API canônica de referência

A assinatura do `create_deep_agent` é nosso mapa de capacidades — cada
parâmetro responde a uma decisão arquitetural:

```python
create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict] | None = None,
    *,
    system_prompt: str | SystemMessage | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    subagents: Sequence[SubAgent | CompiledSubAgent | AsyncSubAgent] | None = None,
    skills: list[str] | None = None,
    memory: list[str] | None = None,
    permissions: list[FilesystemPermission] | None = None,
    backend: BackendProtocol | BackendFactory | None = None,
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
    response_format: ResponseFormat[T] | type[T] | dict | None = None,
    state_schema: type[DeepAgentState] | None = None,
    context_schema: type[ContextT] | None = None,
    checkpointer: Checkpointer | None = None,
    store: BaseStore | None = None,
    cache: BaseCache | None = None,
    debug: bool = False,
    name: str | None = None,
) -> CompiledStateGraph
```

Cada um abaixo:

### 3.1 `model`

`"google_genai:gemini-3.5-flash"` (string `provider:model`) ou
`BaseChatModel` já inicializado. O harness chama
`init_chat_model()` automaticamente.

**Hoje**: usamos `load_llm()` próprio em `src/services/utils.py` que
escolhe provider via `Settings.llm_provider`. **Mantemos** — é o ponto
de injeção do tier gate (C7) e da rotação de modelo. Apenas passamos o
resultado para `create_deep_agent(model=instance)`.

### 3.2 `tools`

Lista de `BaseTool`, callables `@tool`, ou `dict` tool descriptors.
Aceita MCP tools via `langchain-mcp-adapters` automaticamente.

**Hoje**: 39 tools registradas em `src/tools/__init__.py::ALL_TOOLS`.
`tool_resolver.resolve_tools(user_id)` aplica ABAC e MCP plugins do user.
**Mantemos** — só passamos o resultado para `tools=`.

### 3.3 `system_prompt`

`str` ou `SystemMessage`. Concatenado com prompts internos do harness
(planning, todos, filesystem). Aceita `cache_control: "ephemeral"` para
Anthropic prompt caching.

**Hoje**: `VECTORA_IDENTITY + ORCHESTRATOR_PROMPT` em
`src/agents/_identity.py` e `src/agents/orchestrator.py`. Sem prompt
caching. **Migrar** para receber o prompt completo e marcar a parte
estática como cacheable (DE-5).

### 3.4 `middleware`

Lista ordenada de `AgentMiddleware`. Hooks em pontos estratégicos:
`before_agent`, `after_agent`, `before_model_call`, `after_model_call`,
`before_tool_call`, `after_tool_call`.

**Built-ins disponíveis** (todos `provider-agnostic`):

| Middleware                  | Função                                           | Status no Vectora                    |
| --------------------------- | ------------------------------------------------ | ------------------------------------ |
| `SummarizationMiddleware`   | Comprime histórico quando perto do limite        | ❌ Ausente                           |
| `HumanInTheLoopMiddleware`  | Pausa antes de tools sensíveis (`interrupt_on=`) | ❌ Custom                            |
| `ModelCallLimitMiddleware`  | Limita chamadas ao modelo por thread/run         | ❌ Ausente                           |
| `ToolCallLimitMiddleware`   | Limita tools globalmente ou por nome             | ❌ Ausente                           |
| `ModelFallbackMiddleware`   | Fallback a outro modelo se primário falhar       | ❌ Ausente                           |
| `ModelRetryMiddleware`      | Retry exponencial em falhas de modelo            | ❌ Ausente                           |
| `ToolRetryMiddleware`       | Retry de tools falhando                          | ❌ Ausente                           |
| `PIIMiddleware`             | Detecta + redact/mask/block PII                  | ❌ Ausente                           |
| `TodoListMiddleware`        | Equipa agente com planning de tasks              | ⏳ Implementamos write_todos próprio |
| `LLMToolSelectorMiddleware` | LLM filtra tools antes do main model             | ❌ Ausente                           |
| `LLMToolEmulatorMiddleware` | Emula tools com LLM (testes)                     | ❌ Ausente                           |
| `ContextEditingMiddleware`  | Trim/clear de tool uses no histórico             | ❌ Ausente                           |
| `ShellMiddleware`           | Shell session persistente                        | ⏳ Temos PTY próprio                 |
| `FileSearchMiddleware`      | Glob + Grep sobre filesystem                     | ⏳ Temos tools próprias              |
| `FilesystemMiddleware`      | Filesystem para context + memory                 | ⏳ Temos tools próprias              |
| `SubagentMiddleware`        | Spawn de subagents                               | ⏳ Custom                            |

**Adoção mínima recomendada** (DE-2):
`HumanInTheLoopMiddleware` + `SummarizationMiddleware` + `PIIMiddleware`

- `ModelCallLimitMiddleware` + `ToolCallLimitMiddleware` + `ModelRetryMiddleware`.

### 3.5 `subagents`

Lista de `dict {name, description, prompt, tools, model}` ou
`CompiledSubAgent` ou `AsyncSubAgent`. O harness expõe automaticamente a
tool `task(subagent_type=, description=, ...)` ao supervisor.

```python
subagents=[
    {
        "name": "coder",
        "description": "Edits code, runs tests, validates with git",
        "prompt": CODER_PROMPT,
        "tools": [file_read, file_edit, file_write, terminal, git_*],
        "model": None,  # herda do supervisor
    },
    {
        "name": "search",
        "description": "Web search + RAG over local docs",
        "prompt": SEARCH_PROMPT,
        "tools": [web_search, web_fetch, search_memory],
    },
]
```

**Hoje**: `coder` e `search` são funções async em `src/agents/{coder,search}.py`
invocadas via grafo manual. **Migrar** para dicts (DE-1 + DE-10).

### 3.6 `skills`

Lista de paths para diretórios. O harness lê `SKILL.md` (frontmatter
YAML com `name` + `description`) no startup, expõe descrições no system
prompt, e carrega o corpo on-demand quando o LLM decide invocar.

```python
skills=["./skills/", "/memories/user-skills/"]
```

**Hoje**: `services/skills.py` próprio com staging + git clone. Continua
útil para CRUD; o que falta é **integrar** com `skills=` do create_deep_agent
em vez de mantermos um sistema separado.

### 3.7 `memory`

Lista de paths para arquivos de memória (tipicamente `AGENTS.md`,
`/memories/preferences.md`). Carregados no system prompt no startup.
Quando combinados com `StoreBackend(namespace=lambda rt: ...)` viram
memória persistente por user/agent/org.

```python
memory=["/memories/AGENTS.md", "/memories/preferences.md"]
backend=CompositeBackend(
    default=StateBackend(),
    routes={
        "/memories/": StoreBackend(
            namespace=lambda rt: (rt.server_info.user.identity,),
        ),
    },
)
```

**Hoje**: `services/memory.py` artesanal com `cohere.AsyncClient` direto
(violação do princípio "use SDK oficial"). Sem AGENTS.md por user.
**Migrar** para `memory=` + `StoreBackend` (DE-4).

### 3.8 `permissions`

Lista de `FilesystemPermission(operations=, paths=, mode=)`. Evaluation
**first-match-wins, default allow**.

```python
permissions=[
    {"operations": ["write"], "paths": [".env", "**/credentials*", "**/.git/**"], "mode": "deny"},
    {"operations": ["read"], "paths": [".env*"], "mode": "deny"},
    {"operations": ["read", "write"], "paths": ["/workspace/**"], "mode": "allow"},
]
```

**Hoje**: `resolve_within_workspace()` em `src/services/security.py` faz
anti-traversal mas não tem regras declarativas. **Substituir** (DE-3).

### 3.9 `backend`

`BackendProtocol` ou `BackendFactory` (callable que recebe `Runtime` e
retorna backend). Determina onde os arquivos vivem:

| Backend                                              | Escopo             | Persistência               |
| ---------------------------------------------------- | ------------------ | -------------------------- |
| `StateBackend()`                                     | Thread             | via checkpointer           |
| `FilesystemBackend(root_dir=, virtual_mode=True)`    | Local disk         | permanente                 |
| `StoreBackend(namespace=)`                           | Cross-thread       | via BaseStore              |
| `ContextHubBackend("agent-id")`                      | LangSmith Hub      | permanente                 |
| `LocalShellBackend(root_dir=, env=)`                 | Local + shell exec | permanente                 |
| `Modal/E2B/Daytona/Deno Sandbox`                     | Container isolado  | per-session ou persistente |
| `CompositeBackend(default=, routes={"/path/": ...})` | Roteamento         | varia                      |

**Hoje**: nenhum. Filesystem é `pathlib.Path` direto via tools.
**Migrar** para `CompositeBackend` com rotas claras (DE-3):

```python
backend=lambda rt: CompositeBackend(
    default=StateBackend(rt),  # scratch do agente
    routes={
        "/workspace/": FilesystemBackend(
            root_dir=workspace_root(rt),
            virtual_mode=True,
        ),
        "/memories/": StoreBackend(
            rt,
            namespace=lambda rt: (rt.server_info.user.identity,),
        ),
        "/skills/": StoreBackend(
            rt,
            namespace=lambda rt: ("vectora-agent",),
        ),
    },
)
```

### 3.10 `interrupt_on`

`dict[str, bool | InterruptOnConfig]`. Quando o agente decide chamar
tool em `interrupt_on`, o grafo pausa via `interrupt()` antes da execução.
Cliente retoma com `Command(resume={"decisions": [{"type": "approve"}]})`
ou `"edit"` ou `"reject"`.

**Hoje**: temos lógica equivalente em `hitl_check`. **Substituir** pelo
`HumanInTheLoopMiddleware` que entrega o mesmo + `allowed_decisions` +
integração nativa com o frontend SDK (DE-2).

### 3.11 `response_format`

Schema (`Pydantic BaseModel`, `dataclass`, `TypedDict`, ou JSON Schema).
LangChain auto-seleciona:

- `ProviderStrategy` se modelo suporta structured output nativo
  (OpenAI, Anthropic, Gemini, xAI Grok)
- `ToolStrategy` (tool calling forçado) para os demais

Resultado em `result["structured_response"]` validado.

**Hoje**: Ausente. Quando o agente precisa retornar dados estruturados,
parseamos JSON do texto manualmente. **Adicionar** (DE-7) — habilita
flows como `extract_contact_info`, `classify_intent`,
`generate_workspace_config` sem regex.

### 3.12 `state_schema` / `context_schema`

`state_schema`: extensão do `DeepAgentState` (TypedDict com `messages`,
`todos`, `files`, ...). Útil para campos customizados.

`context_schema`: dataclass com dados **per-run** que tools/middleware
leem via `runtime.context`. Default seria:

```python
@dataclass
class VectoraContext:
    user_id: str
    workspace_id: str | None = None
    permission_mode: Literal["ask", "auto", "plan", "accept_edits", "bypass"] = "ask"
    org_id: str | None = None
    locale: Literal["en", "es", "pt-BR"] = "pt-BR"
```

**Hoje**: passamos `user_id` e `permission_mode` em `configurable`
manualmente. **Migrar** para `context_schema` tipado (DE-1).

### 3.13 `checkpointer` / `store`

`checkpointer`: `BaseCheckpointSaver`. Default: `InMemorySaver`. Vectora
usa `AsyncSqliteSaver` apontando para `~/.vectora/data/vectora.db`.

`store`: `BaseStore`. Para long-term memory cross-thread. Vectora não usa
hoje (memória via cohere custom).

**Hoje**: checkpointer ✅. Store ❌.
**Migrar** memória para `InMemoryStore` (dev) ou `AsyncPostgresStore` (prod)
com `index={"embed": CohereEmbeddings, "dims": 1024}` para semantic
search nativo, substituindo `services/memory.py` (DE-4).

### 3.14 `cache`

`BaseCache` (LangChain). LLM responses cache. Vectora não usa.
**Adicionar** opt-in via `InMemoryCache` (dev) ou `RedisCache` (prod)
no Bloco G.

---

## 4. HarnessProfile — defaults por modelo

Profiles são **bundles declarativos** de configuração que o
`create_deep_agent` aplica automaticamente quando você passa o `model=`
correspondente.

```python
from deepagents import HarnessProfile, register_harness_profile

register_harness_profile(
    "anthropic:claude-sonnet-4-6",
    HarnessProfile(
        excluded_tools=frozenset(),  # mostra todas as filesystem tools
        prompt_cache=True,           # cache_control: ephemeral no system
        reasoning_effort="high",     # passado ao Anthropic
        max_tool_iterations=50,
    ),
)

register_harness_profile(
    "google_genai:gemini-2.5-flash",
    HarnessProfile(
        excluded_tools=frozenset({"glob"}),  # Gemini é ruim em glob
        prompt_cache=False,                  # Gemini ainda não tem
        max_tool_iterations=30,
    ),
)

register_harness_profile(
    "ollama:llama3",
    HarnessProfile(
        # Modelos locais menores: esconde tools complexas
        excluded_tools=frozenset({"task", "write_todos"}),
        max_tool_iterations=15,
    ),
)
```

**Por que importa**: cada modelo tem capacidades diferentes (prompt
caching, multimodal, structured output nativo, reasoning effort). Hoje
temos um único caminho para todos. **Adicionar** (DE-5).

---

## 5. Streaming v3 — projeções tipadas e subagents

LangGraph 1.1+ introduziu o formato `version="v2"` (StreamPart unificado)
e `version="v3"` no Deep Agents (projeções tipadas).

**Hoje**: `astream_events(version="v2")` em `src/api/adapters.py`. Nós
mesmos branchamos por tipo de evento. Funciona, mas:

- Tokens, tool calls e values vêm misturados → adapter complexo.
- Subagents não têm projeção própria → não sabemos
  facilmente "qual subagent gerou esse token".

**Canônico (v3)**:

```python
stream = agent.stream_events(input, version="v3")

# 4 projeções independentes
for message in stream.messages:        # tokens do supervisor
    yield SSE("token", message.text)

for tool_call in stream.tool_calls:    # tool calls do supervisor
    yield SSE("tool_call", {
        "name": tool_call.tool_name,
        "input": tool_call.input,
        "completed": tool_call.completed,
        "error": tool_call.error,
    })

for subagent in stream.subagents:      # cada delegação ganha handle
    yield SSE("subagent_started", {
        "name": subagent.name,
        "path": subagent.path,
        "status": subagent.status,
    })
    for msg in subagent.messages:
        yield SSE("subagent_token", {
            "name": subagent.name,
            "text": msg.text,
        })
    for tc in subagent.tool_calls:
        yield SSE("subagent_tool_call", {
            "name": subagent.name,
            "tool": tc.tool_name,
            "input": tc.input,
        })

for value in stream.values:            # snapshots de state
    yield SSE("state", value)
```

Status do subagent ∈ `{started, running, completed, failed, interrupted}`.
Frontend pode renderizar **cada subagent num bloco separado** com seu
próprio thinking + tool calls + tokens.

**Migrar** o adapter (DE-6).

---

## 6. Memory: a abordagem que dispensa código próprio

A documentação canônica trata memória como **arquivos num filesystem**,
não como tabela. Isso é radicalmente diferente do nosso `services/memory.py`.

**Dimensões**:

| Dimensão   | Pergunta                | Opções                                                         |
| ---------- | ----------------------- | -------------------------------------------------------------- |
| Duração    | Quanto tempo dura?      | Short-term (thread) ou long-term (cross-thread)                |
| Tipo       | Que tipo de informação? | Episódica (passado), procedural (skills), semântica (fatos)    |
| Escopo     | Quem vê?                | User, agent, org                                               |
| Update     | Quando escreve?         | Hot-path (durante conversa) ou background (consolidation cron) |
| Retrieval  | Como lê?                | Loaded into prompt vs on-demand (skills)                       |
| Permission | Pode escrever?          | Read-write vs read-only (policies)                             |

**Padrão recomendado para Vectora**:

```python
backend=lambda rt: CompositeBackend(
    default=StateBackend(rt),
    routes={
        "/memories/": StoreBackend(             # semântica per-user
            rt,
            namespace=lambda rt: (
                rt.server_info.assistant_id,
                rt.server_info.user.identity,
            ),
        ),
        "/skills/": StoreBackend(               # procedural per-user
            rt,
            namespace=lambda rt: (rt.server_info.user.identity,),
        ),
        "/policies/": StoreBackend(             # org-wide read-only
            rt,
            namespace=lambda rt: (rt.context.org_id,),
        ),
        "/workspace/": FilesystemBackend(       # código do user
            root_dir=workspace_root(rt),
            virtual_mode=True,
        ),
    },
),
memory=["/memories/AGENTS.md"],
skills=["/skills/"],
permissions=[
    {"operations": ["write"], "paths": ["/policies/**"], "mode": "deny"},
],
```

**Episodic memory** (passado conversacional): já temos via
checkpointer SQLite. Para tornar **searchable**, expor uma tool wrapper:

```python
@tool
async def search_past_conversations(query: str, runtime: ToolRuntime) -> str:
    """Search this user's past conversations for context."""
    user_id = runtime.server_info.user.identity
    threads = await client.threads.search(
        metadata={"user_id": user_id},
        limit=5,
    )
    # ... retorna histórico relevante
```

**Background consolidation** (sleep-time compute): segundo agente
deep_agent dedicado que roda em cron, lê conversas recentes via
`search_recent_conversations`, sintetiza, e atualiza `/memories/AGENTS.md`
do user. Cadência ~6h (chat ativo) ou nightly (uso esporádico). Match
crítico: cron-interval = lookback-window do tool. (DE-13)

---

## 7. Multi-tenancy e segurança

### 7.1 Identidade

Em produção, **toda invocação carrega 2 parâmetros**:

```python
agent.invoke(
    {"messages": [{"role": "user", "content": "..."}]},
    config={"configurable": {"thread_id": str(uuid7())}},  # conversation
    context=VectoraContext(user_id=user.id, workspace_id=ws.id),  # per-run
)
```

`thread_id` é estável (mesma conversa). `context` muda por run (pode mudar
workspace mid-conversation por exemplo).

**Auto-resolução de identidade**: ao deployar em LangSmith ou
implementar `custom_auth` no `langgraph.json`, `rt.server_info.user.identity`
vira o `user_id` autenticado. Sem isso, passamos manualmente via `context`.

### 7.2 Authorization

LangSmith Deployments expõe `auth_handlers` que:

- Etiquetam recursos com `owner: user_id`.
- Retornam filtros para listagens (user só vê seus threads/assistants).
- Negam com HTTP 403 quando não autorizado.

**Vectora hoje**: B1 (auth/RBAC) faz isso manualmente em handlers
FastAPI. **Migrar** para o padrão LangGraph quando deploy em LangSmith
ou re-aproveitar a infra de auth handlers do `langgraph` standalone.

### 7.3 Credenciais por user (Agent Auth)

Quando o agente chama APIs externas em nome do user (GitHub, Slack,
Google Drive, etc), o padrão canônico é **Agent Auth** — OAuth managed
da LangChain:

```python
from langchain_auth import Client
auth_client = Client()

@tool
async def github_action(query: str, runtime: ToolRuntime):
    auth_result = await auth_client.authenticate(
        provider="github",
        scopes=["repo", "read:org"],
        user_id=runtime.server_info.user.identity,
    )
    # use auth_result.token
```

Na primeira chamada, o agente interrompe execução e mostra OAuth consent
URL. Após o user autenticar, o agente resume com token válido.
Refresh automático.

**Vectora hoje**: GitHub OAuth manual em B6 + tokens no vault KeePass.
Funciona; reabrir consideração quando Agent Auth ficar GA estável.

### 7.4 Sandboxes (DE-11)

Para workspaces **untrusted** ou execução de código gerado, hoje rodamos
em PTY local (zero isolamento). Canonicamente:

- `Modal/E2B/Daytona/Deno` sandbox backend → execução isolada.
- `execute` tool aparece automaticamente quando sandbox detectado.
- Pode-se rodar **agent fora**, **sandbox dentro** (modelo decoupled).
  Vectora já segue esse padrão — só falta plugar o backend certo.

Sandbox + git worktree por user (já em I1) = isolamento real para
multi-tenant code execution.

---

## 8. Guardrails (DE-8)

Defesa em camadas via middleware. Ordem importa (cada um pode
short-circuit).

```python
middleware=[
    # Camada 1: filtro determinístico de input
    ContentFilterMiddleware(banned_keywords=["...", "..."]),

    # Camada 2: PII em ambos os sentidos
    PIIMiddleware("email", strategy="redact", apply_to_input=True),
    PIIMiddleware("email", strategy="redact", apply_to_output=True),
    PIIMiddleware("api_key", detector=r"sk-[a-zA-Z0-9]{32}", strategy="block"),
    PIIMiddleware("credit_card", strategy="mask"),

    # Camada 3: budgets de custo
    ModelCallLimitMiddleware(thread_limit=100, run_limit=20, exit_behavior="end"),
    ToolCallLimitMiddleware(tool_name="terminal", thread_limit=10),
    ToolCallLimitMiddleware(tool_name="web_search", run_limit=5),

    # Camada 4: resiliência
    ModelRetryMiddleware(max_attempts=3, exponential_backoff=True),
    ToolRetryMiddleware(max_attempts=2),
    ModelFallbackMiddleware(
        primary="anthropic:claude-sonnet-4-6",
        fallback="openai:gpt-5.4",
    ),

    # Camada 5: HITL — sempre o último gate
    HumanInTheLoopMiddleware(interrupt_on={
        "file_write": {"allowed_decisions": ["approve", "edit", "reject"]},
        "terminal": {"allowed_decisions": ["approve", "reject"]},
        "git_push": True,
    }),

    # Camada 6: summarization — para janelas longas
    SummarizationMiddleware(
        model="anthropic:claude-haiku-4",
        trigger=("fraction", 0.8),
        keep=("messages", 30),
    ),

    # Camada 7: custom safety guardrail (after_agent)
    SafetyOutputGuardrail(),  # LLM-based check da resposta final
]
```

**Custom guardrails** via `@before_agent` ou `@after_agent`:

```python
from langchain.agents.middleware import before_agent, hook_config

@before_agent(can_jump_to=["end"])
def block_prompt_injection(state, runtime):
    first_msg = state["messages"][0]
    if contains_injection_signature(first_msg.content):
        return {
            "messages": [{
                "role": "assistant",
                "content": "Pedido bloqueado por motivo de segurança."
            }],
            "jump_to": "end",
        }
    return None
```

---

## 9. Persistence avançada (DE-14)

LangGraph já entrega persistence, mas estamos usando ~30% do que é
possível.

### 9.1 Time travel

```python
# Listar histórico do thread
history = list(graph.get_state_history(config))

# Encontrar checkpoint antes de um node específico
before_coder = next(s for s in history if s.next == ("coder",))

# Replay a partir desse checkpoint
graph.invoke(None, config={
    "configurable": {
        "thread_id": config["configurable"]["thread_id"],
        "checkpoint_id": before_coder.config["configurable"]["checkpoint_id"],
    },
})
```

**Use case Vectora**: rewind (SX-FS-3) — implementação canônica trivial.

### 9.2 Update state (edit + regenerate)

```python
# User edita a 3ª mensagem
graph.update_state(
    config={"configurable": {"thread_id": tid, "checkpoint_id": cid_before_msg3}},
    values={"messages": [HumanMessage(content="versão editada")]},
    as_node="__start__",  # treats update como input
)
# Próximo invoke regenera daquele ponto
```

**Use case Vectora**: I4 (edit message + regenerate) + I5 (fork from here)
do Bloco B5 — implementação canônica em 10 linhas.

### 9.3 Pending writes recovery

Quando um node falha mid-super-step, LangGraph já persiste os writes dos
nodes que **completaram** no mesmo super-step. No resume, esses não
re-executam. Isso é **automático** — só precisamos confiar.

**Use case Vectora**: se `parallel_dispatch` chama coder + search + rag
e search falha, no resume coder/rag não re-executam. Já temos! Só não
estávamos documentando.

### 9.4 Subgraph checkpointer scoping

Importante para HITL aninhado: ao colocar um agente compilado como
node de outro StateGraph (padrão recomendado para workflows custom),
pode-se escolher entre:

- **Per-thread checkpointing**: subgraph compartilha thread com pai.
- **Per-invocation checkpointing**: cada call do subgraph é
  independente.

Decisão fica em `.compile(checkpointer=...)` do subgraph.

---

## 10. ACP — Agent Control Protocol (DE-12, já em I4)

Padrão open para clientes (IDEs, CLIs, outros agentes) chamarem agentes
remotos como ferramentas.

```
[Claude Desktop] ──ACP──> [Vectora] ──MCP/tools──> [Postgres/GitHub/...]
```

3 componentes da lib:

- `deepagents-acp.server` — Vectora expõe `/acp/v1` autenticado.
- `deepagents-acp.adapter` — Vectora consome outros agentes ACP como
  subagent.
- `deepagents-acp.ide-integration` — conector VSCode/JetBrains nativo.

Bloco I4 já mapeia. Implementação concreta em DE-12 + J7 (REST público).

---

## 11. Frontend canônico (`@langchain/langgraph-sdk`)

A docs `deepagents/frontend/*` cobre `useStream`, `useStream(subagent)`,
`useArtifacts`, `useInterrupts`, `useThreadHistory`. Substitui nosso
`vectora-client.ts` artesanal por uma surface consistente com toda a
comunidade LangChain.

```ts
const { messages, status, interrupt, submit, stop } = useStream({
  apiUrl: "/v1/agent",
  apiKey: token,
  threadId,
  assistantId: "vectora",
  context: { user_id, workspace_id, permission_mode },
});

const subagentStream = useStream.subagents();
// renderizar cada subagent em bloco separado

const onApprove = () =>
  submit(Command((resume = { decisions: [{ type: "approve" }] })));
const onReject = () =>
  submit(Command((resume = { decisions: [{ type: "reject" }] })));
const onEdit = (newArgs) =>
  submit(Command((resume = { decisions: [{ type: "edit", args: newArgs }] })));
```

Vale migrar quando o Bloco D (Vite SPA) estabilizar, junto com a Etapa
DE-6 (streaming v3).

---

## 12. Observabilidade — LangSmith (DE-9)

Adicionar **3 env vars** habilita observabilidade end-to-end zero-config:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls_...
LANGCHAIN_PROJECT=vectora-prod  # opcional
```

Cada `agent.invoke` vira um trace navegável com:

- Cada LLM call (prompt + tokens in/out + custo).
- Cada tool call (args + resultado + duração).
- Cada subagent expansão.
- Cada interrupt (com decisão do user).
- Cada middleware hook.

**LangSmith Engine**: opt-in que monitora traces, detecta padrões
problemáticos (timeouts, error rates, latência p95), e sugere fixes
(prompt tweaks, middleware ajustes).

**Para Vectora**: integrar como opt-in via `Settings.langsmith_api_key`.
Quando ausente, traces ficam só local (`VectoraTracer` SQLite — A1).
Quando presente, espelhamos para LangSmith. **Sem PII** — config separada
de `LANGCHAIN_TRACING_V2` para evitar acidente.

---

## 13. Bloco DE — Deep Engine (roadmap)

> **Quando rodar**: depois de Bloco F (storage) e antes de Bloco H/I
> (deep agents 1+2 já presumem esse refactor). Pode rodar em paralelo
> com System Experience (TUI/UX) já que SX é cliente do agente, não
> do harness.

### DE-1 — `agent_factory` → `create_deep_agent`

Refactor cirúrgico:

```python
# src/services/agent_factory.py (novo)

async def get_user_agent(user_id: str) -> CompiledStateGraph:
    cache_key = (
        user_id,
        llm_version(),
        tools_version(user_id),
        policy_version(user_id),
        skills_version(user_id),
    )
    if cached := _agent_cache.get(cache_key):
        return cached

    agent = create_deep_agent(
        model=load_llm(),
        tools=resolve_tools(user_id),
        subagents=_subagent_specs(user_id),
        system_prompt=VECTORA_IDENTITY + ORCHESTRATOR_PROMPT,
        middleware=_middleware_stack(user_id),
        backend=_backend_factory(user_id),
        memory=["/memories/AGENTS.md"],
        skills=["/skills/"],
        permissions=_permissions(user_id),
        interrupt_on={},  # gerenciado pelo HumanInTheLoopMiddleware
        context_schema=VectoraContext,
        checkpointer=await get_checkpointer(),
        store=await get_store(),
        name="vectora-supervisor",
    )

    _agent_cache[cache_key] = agent
    return agent
```

Deletar: `build_graph`, `hitl_check`, `_hitl_route`, `_resolve_pre_interrupt`,
`_apply_hitl_edit`, `parallel_dispatch`, todas as `*_finalize`.

### DE-2 — Middleware nativo

`src/services/middleware.py` (novo) com `_middleware_stack(user_id)`
montando a stack canônica (HITL + Summarization + ModelCallLimit +
ToolCallLimit + PII + ModelRetry + ModelFallback).

Map de `permission_mode → interrupt_on` movido para construção do
`HumanInTheLoopMiddleware`:

```python
def _hitl_middleware(permission_mode: str) -> HumanInTheLoopMiddleware:
    match permission_mode:
        case "bypass" | "auto":
            return HumanInTheLoopMiddleware(interrupt_on={})
        case "accept_edits":
            return HumanInTheLoopMiddleware(interrupt_on={
                "terminal": {"allowed_decisions": ["approve", "edit", "reject"]},
            })
        case "plan":
            # Recusa toda destrutiva
            return HumanInTheLoopMiddleware(interrupt_on={
                tool: {"allowed_decisions": ["reject"]}
                for tool in DESTRUCTIVE_TOOLS
            })
        case _:  # ask, default
            return HumanInTheLoopMiddleware(interrupt_on={
                tool: {"allowed_decisions": ["approve", "edit", "reject"]}
                for tool in DESTRUCTIVE_TOOLS
            })
```

### DE-3 — Backends pluggable

`src/services/backends.py` (novo) com `_backend_factory(user_id)`
retornando `CompositeBackend` com 4 rotas (default + workspace + memories

- skills). Substitui `resolve_within_workspace` + tools `fs.py` manuais.

`permissions=` para `.env`, `.git/`, `credentials*` deny-write.

### DE-4 — Memory como filesystem

- Remove `services/memory.py` artesanal.
- Substitui por `memory=["/memories/AGENTS.md"]`.
- `StoreBackend(namespace=lambda rt: (rt.server_info.user.identity,))`
  com `index={"embed": CohereEmbeddings, "dims": 1024}` para semantic
  search nativo.
- Migration: copia tabela `memories` antiga para o novo store.

### DE-5 — HarnessProfile por modelo

`src/services/profiles.py` (já planejado em H5). Registra um profile por
modelo principal usado (Anthropic, OpenAI, Gemini, Cohere, Ollama).
Cobre prompt caching, reasoning effort, excluded tools.

### DE-6 — Streaming v3 + subagents projection

Refactor de `src/api/adapters.py`:

- Trocar `astream_events(version="v2")` → `stream_events(version="v3")`.
- Expor projections separadas no SSE:
  `{type: "supervisor_token", ...}`,
  `{type: "subagent_started", name, path}`,
  `{type: "subagent_token", name, text}`,
  `{type: "subagent_tool_call", name, tool, input}`,
  `{type: "subagent_completed", name, output}`.

Frontend (Bloco D já preparou Vite) renderiza cada subagent em bloco
próprio.

### DE-7 — Structured output

Adicionar `response_format=` opcional ao `/v1/chat/stream` e expor
endpoints especializados:

- `POST /v1/extract` `{schema, text}` → JSON validado.
- `POST /v1/classify` `{labels, text}` → label + confidence.
- `POST /v1/generate-config` `{type, hints}` → dict tipado.

Auto-detecta `ProviderStrategy` (Anthropic/OpenAI/Gemini) ou
`ToolStrategy` (fallback).

### DE-8 — Guardrails

Stack defensiva canônica (PII + ContentFilter + custom safety
guardrails) em `_middleware_stack(user_id)`. Configurável por tier
no admin panel (B7).

### DE-9 — LangSmith tracing opt-in

`Settings.langsmith_api_key` (env `VECTORA_LANGSMITH_KEY`). Quando set:

- Espelha traces para LangSmith.
- Habilita LangSmith Engine.
- Adiciona link "Ver trace" em cada mensagem na UI (link público
  controlado).

Sem set: comportamento atual (`VectoraTracer` SQLite local).

### DE-10 — Async subagents (paralelismo real)

Substituir `parallel_dispatch` por subagents async-first do deepagents.
Quando o supervisor chama `task(subagent_type=...)` 3× em paralelo, os
3 subagents rodam concorrentes em event loops separados.

Cancelamento via `subagent.cancel()`. Progress via `get_stream_writer`
dentro de tools dos subagents.

### DE-11 — Sandbox backend

Para workspaces **untrusted** (clonados de URL pública ou marked não-
trusted no B2):

- Backend = `ModalSandbox()` ou `E2BSandbox()` por workspace.
- `execute` tool automática (substitui nossa `terminal` quando sandbox).
- HITL desnecessário dentro de sandbox (isolamento já é o gate).

Plano F (storage) deve cobrir o caso lite (sem sandbox), DE-11 cobre o
pro com sandbox managed.

### DE-12 — ACP server público

Bloco I4 + J7 já mapeiam. DE-12 confirma o caminho:
`/v1/acp` → `deepagents-acp.server` mount → autenticado via OAuth2
client credentials (J1).

### DE-13 — Background memory consolidation

Segundo deep agent (`consolidation_agent`) em `langgraph.json` com cron
`0 */6 * * *`. Lê conversas das últimas 6h via
`search_recent_conversations`, sintetiza, atualiza
`/memories/AGENTS.md` do user. Self-hosted: usa SCons ou systemd timer.

### DE-14 — Time travel + edit/regenerate via update_state

Endpoints REST:

- `GET /v1/threads/{tid}/checkpoints` → lista (já temos SX-FS-3 que pede).
- `POST /v1/threads/{tid}/rewind {checkpoint_id}` → cria novo run no
  checkpoint anterior.
- `POST /v1/threads/{tid}/messages/{mid}/edit {content}` → `update_state`
  - invoke novo.
- `POST /v1/threads/{tid}/fork {from_checkpoint_id}` → cria novo thread
  copiando histórico até o checkpoint.

Tudo 10–30 linhas cada — LangGraph já entrega a primitiva.

---

## 14. Arquivos críticos (Bloco DE)

| Sub   | Arquivos                                                                                                                      |
| ----- | ----------------------------------------------------------------------------------------------------------------------------- |
| DE-1  | `src/services/agent_factory.py` (rewrite), deletar `build_graph` interno; `src/services/context.py` (novo, `VectoraContext`)  |
| DE-2  | `src/services/middleware.py` (novo); deletar `hitl_check`, `_resolve_pre_interrupt`, `_apply_hitl_edit`                       |
| DE-3  | `src/services/backends.py` (novo); deprecate `src/services/security.py::resolve_within_workspace`; refactor `src/tools/fs.py` |
| DE-4  | deletar `src/services/memory.py`; refactor `src/tools/memory.py` para usar store nativo; migration script                     |
| DE-5  | `src/services/profiles.py` (novo); registra profile por modelo no startup                                                     |
| DE-6  | `src/api/adapters.py` (refactor v2→v3), `src/api/node_labels.py` (extensão p/ subagent paths)                                 |
| DE-7  | `src/api/handlers/{extract,classify}.py` (novos); `src/api/handlers/chat.py` (`response_format` opcional)                     |
| DE-8  | `src/services/guardrails.py` (novo); `chat/src/components/admin/guardrails-panel.tsx` (UI)                                    |
| DE-9  | `src/services/telemetry/langsmith.py` (novo); env `VECTORA_LANGSMITH_KEY`                                                     |
| DE-10 | `src/services/agent_factory.py` (subagents como `AsyncSubAgent`)                                                              |
| DE-11 | `src/services/sandboxes/{modal,e2b}.py` (novos); reuso de I1 (sandbox + worktree)                                             |
| DE-12 | `src/api/handlers/v1/acp.py` (mount); `pyproject.toml` (+`deepagents-acp`)                                                    |
| DE-13 | `src/agents/consolidation.py` (novo); `langgraph.json`; cron via SCons                                                        |
| DE-14 | `src/api/handlers/threads.py` (+checkpoints, rewind, edit, fork); `src/services/checkpoint.py` (helpers)                      |

---

## 15. Dependências (atualizar `pyproject.toml`)

```toml
# Faixas abertas (princípio 5 do plano mestre)
dependencies = [
  # já existe
  "langchain>=1.3.1",
  "langchain-core>=1.4.0",
  "langgraph>=1.2.1",
  "langgraph-checkpoint-sqlite>=3.1.0",
  "deepagents>=0.6.3",
  # Adicionar
  "langchain-anthropic>=0.4.0",   # prompt caching nativo
  "langchain-openai>=0.4.0",      # ProviderStrategy nativa
  "langchain-google-genai>=2.2.0",
  "langgraph-checkpoint-postgres>=3.0.0",  # opt-in pro tier
  "langgraph-store-sqlite>=0.2.0",         # store local
  "langgraph-store-postgres>=0.2.0",       # store pro
  "deepagents-acp>=0.3.0",        # ACP (DE-12)
  # Opcionais quando tier=pro
  "langsmith>=0.5.0",             # já temos via langchain
]
```

Remover (deps fantasma confirmadas em `docs/tech.md`):

- `dotfiles`, `ast-serialize`, `librt`.

---

## 16. Verificação (end-to-end do Bloco DE)

- `from deepagents import create_deep_agent` é o único builder de agente
  no `src/`. `grep -r "StateGraph(" src/` deve retornar **0 ocorrências**
  no agente principal (apenas subgraphs auxiliares se houver).
- `agent.invoke({...}, context=VectoraContext(...))` funciona; tools
  leem `runtime.context.user_id`.
- HITL via `HumanInTheLoopMiddleware`: `interrupt()` raw removido.
  Approve/Edit/Reject em todos os 5 modos preservam comportamento dos
  29 testes do E6.
- Memória: `/memories/AGENTS.md` por user; cross-thread persistente;
  semantic search funciona via `store.search(namespace, query=...)`.
- Streaming v3: cliente JS consome `stream.subagents` e renderiza cada
  subagent em bloco. Latência first-token ≤ atual.
- Structured output: `POST /v1/extract` retorna Pydantic validado.
- Guardrails: tentar enviar email com `sk-...` no body → PIIMiddleware
  bloqueia com `[REDACTED_API_KEY]`.
- LangSmith: setar `VECTORA_LANGSMITH_KEY=...` → próxima invocation
  aparece no dashboard em <30s.
- Time travel: clicar "Voltar até aqui" na 3ª mensagem → 4ª+ apagadas,
  nova resposta gerada do mesmo checkpoint.
- ACP: Claude Desktop → "Add ACP server" → URL Vectora → tools do
  Vectora aparecem disponíveis para o Claude.

---

## 17. Princípios cardinais (para internalizar)

1. **Antes de escrever código, procure middleware/backend/primitiva já
   pronto.** Toda capacidade nova começa por uma consulta à docs
   (`docs-langchain` MCP). Reescrever é violação de princípio.

2. **Composability > complexity.** `create_deep_agent` retorna um
   `CompiledStateGraph` normal. Pode-se compor num `StateGraph` maior
   (router de intents, fan-out, workflow custom). Nunca há razão para
   reimplementar o `agent loop`.

3. **Backends decidem onde dados vivem; middleware decide o que acontece
   neles; permissions decidem quem pode tocar.** Manter os 3 separados —
   confundir um com o outro foi a fonte do código artesanal atual.

4. **Streaming v3 sempre, v2 nunca.** Adapter v2 sofre na hora de
   distinguir supervisor de subagent.

5. **Multi-tenancy é `(thread_id, context)` + auth handler.** Nunca
   embutir `user_id` em prompts ou tools manuais — sempre via
   `runtime.context` ou `runtime.server_info.user.identity`.

6. **Long-term memory é filesystem, não tabela.** Tudo via `StoreBackend`

   - `memory=["AGENTS.md"]`. Semantic search nativa.

7. **LangSmith é a observabilidade default.** Não temos motivo para
   manter `VectoraTracer` SQLite quando deploy estiver em prod — vira
   fallback local.

8. **Profiles antes de hardcode por provider.** Se você está escrevendo
   `if model.startswith("anthropic:")` em algum lugar, isso é um profile
   esperando para nascer.

9. **HITL é middleware, não nó do grafo.** A diferença é que middleware
   se compõe e é serializável; nó custom não.

10. **Sandbox > scope-guard.** Quando a tarefa é "isolar execução
    potencialmente perigosa", a resposta é "sandbox backend", não "regex
    de path mais esperta".

---

## 18. Referência cruzada com o plano mestre

| Sub-bloco DE | Substitui / complementa                         | Habilita              |
| ------------ | ----------------------------------------------- | --------------------- |
| DE-1         | reescreve metade de E1/E2/E5                    | toda a stack DE       |
| DE-2         | substitui E4 (HITL)                             | DE-8 (guardrails)     |
| DE-3         | substitui parte de SX-FS-1..19 (backend)        | DE-4, DE-11           |
| DE-4         | substitui C1 (memory)                           | DE-13 (consolidação)  |
| DE-5         | substitui H5 (profiles parcial)                 | prompt caching H3     |
| DE-6         | substitui E3 (adapters)                         | frontend SDK          |
| DE-7         | nova capability                                 | uso em B5 (export), J |
| DE-8         | nova camada                                     | compliance K          |
| DE-9         | substitui A1 tracer parcial                     | M (observability)     |
| DE-10        | substitui I3 (async parcial)                    | H/I full              |
| DE-11        | substitui I1 (sandbox parcial)                  | multi-tenant pro      |
| DE-12        | substitui I4/J7 (ACP)                           | IDE integrations N7   |
| DE-13        | substitui H2 (AGENTS.md memory parcial)         | personalização        |
| DE-14        | substitui SX-FS-3 (rewind via langgraph nativo) | I4/I5 do B5           |

Bloco DE é **upstream** de quase tudo que vem depois — vale priorizá-lo
no momento em que houver bandwidth para um refactor de 2–4 semanas.

---

## 19. Quando NÃO migrar (riscos e contra-indicações)

- **Se Bloco F (storage) ainda não estabilizou**, segurar DE até lá.
  Backends pluggable dependem de Postgres/Qdrant configuráveis.
- **Se contexto E2E (testes integrados com APIs reais) está
  quebrado**, consertar primeiro. Refactor sem rede de segurança é
  receita para regressão silenciosa.
- **Se a base de testes do agente ainda passa por mocks ad-hoc** do
  `build_graph`, criar suite de paridade primeiro: gravar fixtures de
  comportamento esperado (input → mensagens emitidas → tool calls)
  rodando no agente atual, e usar como golden test após o refactor.
- **Se Bloco D (Vite) ainda mostra instabilidade** em mobile/Electron,
  refactorar primeiro o backend pode fragilizar duas frentes ao mesmo
  tempo.

Padrão recomendado: DE entra **em paralelo** com System Experience
(que é cliente), mas **depois** de F+G (storage+cache estabilizados),
com release behind feature flag (`VECTORA_USE_DEEP_ENGINE=1`) por 1–2
versões antes de virar default.
