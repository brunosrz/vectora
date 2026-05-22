# MVP Scope — Vectora v0.1.0

Registro técnico completo de tudo implementado no Vectora v0.1.0. Serve como referência para o time e como checklist de release.

**Versão:** 0.1.0rc3
**Status:** 🟡 Feature-complete, em polimento final (rc2 — não publicada)

---

## 1. Arquitetura do Grafo (LangGraph)

### Topologia

```
START
  └─► orchestrator  ─────────────────────────────── Command(goto=...)
        ├─► [respond]      ──► END
        ├─► [search]       ──► search_tools ──► process_retrieval ──► search ──► END
        ├─► [coder]        ──► coder_tools ──► coder ──► END
        └─► [rag_subgraph] ──► rag_subgraph ──► orchestrator (síntese) ──► END
```

### Nós

| Nó                  | Tipo               | Função                                                                |
| ------------------- | ------------------ | --------------------------------------------------------------------- |
| `orchestrator`      | Custom (LLM)       | Agente primário — responde inline ou delega com task_query explícita  |
| `search`            | Custom             | Pesquisa web + RAG                                                    |
| `search_tools`      | DiagnosticToolNode | web_search, fetch_url, vector_search                                  |
| `process_retrieval` | Custom             | Cascading automático web → LanceDB                                    |
| `coder`             | Custom             | Filesystem, terminal, git                                             |
| `coder_tools`       | DiagnosticToolNode | Ferramentas de fs + create_artifact                                   |
| `rag_subgraph`      | CompiledStateGraph | Pipeline RAG completo (nó atômico); injeta contexto via SystemMessage |

### Edges

- `START → orchestrator` (determinístico)
- `orchestrator → {END, search, coder, rag_subgraph}` (`add_conditional_edges` via `_orchestrator_route`)
- `rag_subgraph → orchestrator` (síntese inline — orchestrator vê contexto RAG e responde)
- `search ↔ search_tools → process_retrieval → search` (cascading loop)
- `coder ↔ coder_tools` (`tools_condition` loop)

### Compilação

`build_graph(checkpointer)` em `graph.py`:

- `StateGraph(state_schema=State, context_schema=Context, input_schema=State, output_schema=State)`
- Compila com `checkpointer=AsyncSqliteSaver`
- Checkpointer serializa o `State` completo entre turnos (persistência multi-session)

---

## 2. State & Context

### State (TypedDict, `state.py`)

```python
class State(TypedDict):
    messages:           Annotated[Sequence[BaseMessage], add_messages]
    session_metadata:   SessionMetadata
    routing_decision:   NotRequired[Literal["direct","coder","search","tools","rag"] | None]
    retrieval_results:  NotRequired[dict[str, list[Document]] | None]
    rag_query:          NotRequired[str | None]
    rag_docs:           NotRequired[list[Document] | None]
    pending_embeds:     NotRequired[list[str] | None]   # queue_ids fire-and-forget
    web_search_triggered: NotRequired[bool | None]
    selected_rag_source:  NotRequired[str | None]
    summarized_history:   NotRequired[str | None]
```

- `messages` usa o reducer `add_messages` do LangChain (append inteligente, substituição por `id`)
- Todos os campos opcionais usam `NotRequired` (Python 3.11+) para compatibilidade com `total=True`
- `Document` é um `TypedDict` próprio com `page_content`, `metadata`, `relevance_score: float | None`

### SessionMetadata (TypedDict, total=False)

```python
class SessionMetadata(TypedDict, total=False):
    thread_id:    int
    user_type:    str
    created_at:   str       # ISO 8601
    llm_provider: str
    llm_model:    str
```

### Context (dataclass frozen, `context.py`)

```python
@dataclass(frozen=True, slots=True)
class Context:
    user_type:       str
    thread_id:       str | int
    user_id:         str = "default"
    correlation_id:  str | None      # UUID auto-gerado em __post_init__
    conversation_id: str | None
    created_at:      str | None      # ISO timestamp auto-setado
    preferences:     UserPreferences
    features:        FeatureFlags
```

- `UserPreferences`: `language`, `max_search_results=10`, `min_score_threshold=0.5`, `preferred_model`
- `FeatureFlags`: `enable_web_search`, `enable_url_fetch`, `enable_database`, `enable_rag`, `enable_mcp`
- Imutável por design — injetado via `RunnableConfig["configurable"]`

---

## 3. Orchestrator & Roteamento

O Orchestrator é o agente primário do sistema. Ele usa **LLM structured output** (`OrchestratorDecision`) para decidir entre responder inline ou delegar a um sub-agente com uma instrução clara.

### `OrchestratorDecision` (Pydantic)

```python
class OrchestratorDecision(BaseModel):
    action: Literal["respond", "delegate"]
    response: str | None = None          # resposta completa quando action=="respond"
    delegate_to: Literal["coder", "search", "rag"] | None = None
    task_query: str | None = None        # instrução focada para o sub-agente (1–3 frases)
    reason: str                          # uma frase para log/debug
```

### `orchestrator(state: State) -> Command`

Fluxo de execução:

1. Carrega project context (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md` do cwd) na primeira mensagem da sessão — persiste em `state["project_context"]`
2. Monta `_build_context_block(state, session_id)` com session metadata (incluindo `Session ID:`) e histórico de artifacts
3. Chama LLM com `.bind_tools(ALL_TOOLS).with_structured_output(OrchestratorDecision)` para obter decisão estruturada
4. **`action="respond"`**: cria `AIMessage`, injeta em `messages`, roteia para `END`
5. **`action="delegate"`**: escreve `orchestrator_task = task_query` no state, roteia para `coder` / `search` / `rag_subgraph`
6. Fallback (LLM call falha): responde inline com mensagem de erro

Sub-agentes (`coder`, `search`) leem `state["orchestrator_task"]` e injetam como diretiva no topo do system prompt, priorizando sobre o histórico bruto.

### Self-Awareness (`agents/_identity.py`)

`VECTORA_IDENTITY` — string constante importada por todos os agents:

- Identidade: open-source Python, GitHub brunosrz/vectora, Apache 2.0
- Stack declarada: LangChain, LangGraph, FastMCP, LanceDB, Cohere, Tavily
- Arquitetura: multi-agent stateful com orchestrator + specialization
- Capacidades: RAG local, busca web, fs/terminal, memória persistente, embedding assíncrono, MCP, multi-sessão, artifacts
- Comandos disponíveis: `/list`, `/tools`, `/debug`, `/new`, `/session`, `/model`, `/rag`, `/help`

### Self-Awareness (`agents/_identity.py`)

`VECTORA_IDENTITY` — string constante importada por todos os agents:

- Identidade: open-source Python, GitHub brunosrz/vectora, Apache 2.0
- Stack declarada: LangChain, LangGraph, FastMCP, LanceDB, Cohere, Tavily
- Arquitetura: multi-agent stateful com orchestrator + specialization
- Capacidades: RAG local, busca web, fs/terminal, memória persistente, embedding assíncrono, MCP, multi-sessão
- Comandos disponíveis: `/list`, `/tools`, `/debug`, `/new`, `/session`, `/model`, `/rag`, `/help`

---

## 4. Agents

### Orchestrator Agent (`agents/orchestrator.py`)

- **Papel**: Agente primário — responde inline para perguntas simples, sintetiza contexto RAG, cria artifacts explicitamente via `create_artifact`, delega tarefas complexas a sub-agentes com instrução clara
- **LLM**: Singleton lazy-loaded `_orchestrator_llm` via `_get_orchestrator_llm() -> Runnable`; usa `.bind_tools(ALL_TOOLS).with_structured_output(OrchestratorDecision)`
- **Tools disponíveis**: `ALL_TOOLS` (15 tools, incluindo `create_artifact`, `save_memory`, `get_memory`, `delete_memory`)
- **System prompt**: `_ORCHESTRATOR_PROMPT` — VECTORA_IDENTITY + regras de delegação + instruções de síntese RAG + uso correto de `create_artifact` (passar `session_id` do context block)
- **Project context**: `_load_project_context()` escaneia cwd recursivamente por `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` na primeira mensagem; resultado persiste em `state["project_context"]`

### Search Agent (`agents/search.py`)

- **Papel**: Pesquisa web em tempo real, busca vetorial, construção passiva da base de conhecimento
- **LLM**: Singleton lazy-loaded `_search_llm`
- **Tools bindadas**: `SEARCH_TOOLS` (`web_search`, `fetch_url`, `vector_search`, `embedding` se RAG habilitado)
- **System prompt**: Estratégia RAG-first → web fallback; `process_retrieval` faz cascading automático (não chamar `embedding` manualmente); citar fontes
- **Invocação**: `invoke_llm(_get_search_llm(), state, system_prompt=SYSTEM_PROMPT)`

### Coder Agent (`agents/coder.py`)

- **Papel**: Operações de filesystem, terminal, git, geração e edição de código
- **LLM**: Singleton lazy-loaded `_coder_llm`
- **Tools bindadas**: `[*FS_TOOLS, *MEMORY_TOOLS]` (condicionado por `settings.enable_file_operations`)
- **System prompt**: Git liberado sem confirmação; destrutivos bloqueados pela tool; proatividade (executar testes, usar grep para navegar, edições cirúrgicas)
- **Invocação**: `invoke_llm(_get_coder_llm(), state, system_prompt=SYSTEM_PROMPT)`

---

## 5. Nodes Base (`nodes/base.py`)

### `sanitize_for_gemini(messages) -> list`

Gemini exige alternância estrita `Human → AI`. O sanitizador:

1. Remove blocos `AIMessage(tool_calls=[...])` no início da janela
2. Remove `ToolMessage`s consequentes órfãos
3. Garante que a sequência comece com `HumanMessage` ou `AIMessage` limpa

### `build_messages(state, system_prompt="") -> list[BaseMessage]`

Pipeline de construção do prompt final:

1. **Sliding window** via `trim_messages(max_context_tokens)` com `text_service.count_messages_tokens` como `token_counter`
2. **Fallback anti-vazio**: Se `trim_messages` remover toda HumanMessage, retoma das últimas mensagens
3. **Sanitização Gemini**: `sanitize_for_gemini(trimmed)`
4. **System prompt do agent**: Injetado como `SystemMessage` no topo
5. **RAG context**: Se `state["rag_docs"]`, injeta bloco `## Contexto Recuperado (RAG)` como `SystemMessage`
6. **Retrieval results legado**: Se `state["retrieval_results"]`, injeta bloco `## USE O CONTEXTO ABAIXO`
7. **Memórias**: Se `thread_id` disponível, carrega todas memórias de `MemoryStore` e injeta como `SystemMessage`

### `invoke_llm(llm, state, system_prompt="") -> dict`

1. `build_messages(state, system_prompt)`
2. `llm.astream(messages)` — coleta chunks acumulando `content` e `tool_calls`
3. Trata `RESOURCE_EXHAUSTED` / HTTP 429 com mensagem de fallback `"⚠️ Quota da API atingida"`
4. Retorna `{"messages": [AIMessage(content=..., tool_calls=[...])]}`

---

## 6. RAG Subgraph (`nodes/rag_subgraph.py`)

### Topologia Interna

```
START → rag_retrieve → _rag_decide_node ─────────────────────────────► END
                            │
                            ├─► rag_inject    (score ≥ 0.7)
                            ├─► rag_rerank    (0.4 ≤ score < 0.7) → rag_inject
                            └─► rag_websearch (score < 0.4)        → rag_inject
```

### Thresholds

```python
_SCORE_HIGH = 0.7   # Alta confiança → inject direto
_SCORE_LOW  = 0.4   # Confiança mediana → rerank antes de injetar
                    # Abaixo de 0.4 → fallback web
```

### Nós

**`rag_retrieve`**

- Extrai query da última `HumanMessage` via `_extract_query()`
- Chama `_call_vector_search(query)` diretamente (sem passar por ToolNode)
- Retorna `{rag_query, rag_docs: list[Document]}`

**`_rag_decide_node`**

- Nó pivot — não altera estado, retorna `{}`
- Necessário para que `add_conditional_edges` funcione com LangGraph

**`_route_after_decide`** (função de roteamento)

- Calcula `score = _best_score(rag_docs)` (max `relevance_score` dos docs)
- Retorna `"rag_inject"` | `"rag_rerank"` | `"rag_websearch"`

**`rag_rerank`**

- Instancia `CohereRerank(top_n=3, model=settings.reranker_model)`
- Converte `Document[]` para `LCDoc[]` e chama `compress_documents(docs, query)`
- Retorna `{rag_docs: list[Document]}` reordenado
- Fallback silencioso: em caso de exceção (sem API key, quota, etc), retorna `{}`

**`rag_websearch`**

- Chama `_call_web_search(query)` → lista de resultados brutos
- Filtra resultados com `content` vazio
- Converte cada resultado em `Document(page_content, metadata={source, title, url, origin})`
- **Cascading**: Chama `_enqueue_for_embedding(content, collection)` para cada resultado (fire-and-forget)
- Combina com `state["rag_docs"]` existentes
- Retorna `{rag_docs, web_search_triggered=True, pending_embeds=[queue_ids]}`

**`rag_inject`**

- Formata até 5 docs (truncados a 800 chars cada) como bloco Markdown
- Injeta score e fonte quando disponíveis
- Retorna `{"messages": [SystemMessage("## Contexto Recuperado (RAG)...")]}`

### Helpers Privados

- `_extract_query(state) -> str` — extrai texto da última `HumanMessage`; retorna `""` se não houver
- `_best_score(docs) -> float` — max de `relevance_score`, ignorando `None`; retorna `0.0` se vazio
- `_call_vector_search(query, collection, limit) -> list[Document]` — chamada direta sem ToolNode; retorna `[]` em erro
- `_call_web_search(query) -> list[dict]` — invoca `web_search.invoke()` síncrono; retorna `[]` em erro
- `_enqueue_for_embedding(text, collection, metadata) -> str | None` — chama `embedding.ainvoke()`; retorna `queue_id` ou `None`

---

## 7. Process Retrieval (`nodes/engine.py`)

### `process_retrieval(state, runtime) -> dict`

Cascading automático: qualquer `ToolMessage` de `web_search` ou `fetch_url` engatilha embedding fire-and-forget.

**Algoritmo**:

1. Itera `state["messages"]` em ordem reversa, parando no primeiro não-`ToolMessage`
2. Para cada `ToolMessage` com `name in ("web_search", "fetch_url")`:
   - Parse `json.loads(msg.content)` (tratando `str | Any`)
   - Extrai lista de resultados via `_extract_tavily_results(data, tool_name)`
   - Para cada resultado: formata `Document(page_content, metadata={title, url, source})`
   - Chama `embedding_tool.ainvoke({"text", "collection", "metadata"})` → captura `queue_id`
3. Acumula em `state["retrieval_results"]` e `state["pending_embeds"]`
4. Seta `state["web_search_triggered"] = True`

**Retorno**: `{retrieval_results, pending_embeds, web_search_triggered}` ou `{}` se nada novo

---

## 8. DiagnosticToolNode (`nodes/debug.py`)

Wrapper sobre `ToolNode` com logging detalhado para cada invocação de ferramenta:

- Log de entrada: lista de `tool_calls` pendentes
- Log de saída: conteúdo de cada `ToolMessage` retornada
- Rastreia exceções por ferramenta individualmente
- Mantém interface idêntica ao `ToolNode` (transparente para o grafo)

---

## 9. Tool Groups (`nodes/tools.py`)

```python
SEARCH_TOOLS  = [web_search, fetch_url, vector_search] + [embedding] (se enable_rag)
FS_TOOLS      = [file_read, file_edit, file_write, grep, list_dir, terminal, create_artifact]
MEMORY_TOOLS  = [save_memory, get_memory, delete_memory]
RAG_TOOLS     = [vector_search] + [embedding, ingest_docs] (se enable_rag)
ALL_TOOLS     = union deduplicated por name  # 15 tools no total
```

Tool nodes pré-instanciados via `DiagnosticToolNode(tools=ALL_TOOLS)`: `search_tools_node`, `coder_tools_node`

---

## 10. Ferramentas (15)

### Web — `tools/web.py`

**`web_search(query) -> str`**

- Provider: Tavily API (`search_depth="advanced"`, `max_results=5`)
- Guard: `enable_web_search` + `TAVILY_API_KEY`
- Retorna JSON array `[{url, title, content, ...}]`

**`fetch_url(url) -> str`**

- Provider: Tavily Extract API
- Valida esquema `http://` ou `https://`
- Retorna texto puro extraído da página

### RAG — `tools/rag.py`

**`embedding(text, collection="articles", metadata=None) -> str`**

- Guard: `enable_rag` + `embedding_queue_enabled`
- Chama `get_embedding_queue(dsn).enqueue(text, collection, metadata)` → UUID
- Retorna `{"status": "fire_and_forget", "queue_id", "collection"}`

**`vector_search(query, collection="articles", limit=5) -> str`**

- Guard: `enable_rag` + dependências lancedb/cohere
- `CohereEmbeddings(embed-multilingual-v3.0).embed_query(query)` → vetor 1024-dim
- `lancedb.connect_async(lancedb_dir)` → `table.vector_search(vector).limit(limit).to_pandas()`
- Timeout 10s por operação (via `asyncio.timeout`)
- Reranking opcional: se `reranker_type="cohere"` e `CohereRerank` disponível
- Retorna `{"status": "success", "results": [{id, score, content, metadata}]}`
- Erros: `"no_results"` (collection não existe), `"error"` (timeout), `"failed"` (exceção)

**`ingest_docs(directory_path, collection="articles", glob_pattern="**/\*.md") -> str`\*\*

- Guards: `enable_file_operations` + `is_safe_file_path`
- Carrega `.gitignore` spec via `load_gitignore_spec()` — respeita `__pycache__`, `.venv`, `node_modules`, etc
- Infere `suffix_filter` do glob pattern
- Chunking via `text_service.split(text)` (tiktoken `cl100k_base`, 512 tokens, 50 overlap)
- `embedding.ainvoke(chunk)` fire-and-forget para cada chunk
- Retorna `{"status": "completed", "total_files", "total_chunks", "indexed", "failed", "skipped_ignored"}`

### Filesystem — `tools/fs.py`

**`file_read(file_path) -> str`**

- `is_safe_file_path()`: rejeita `..`, extensões perigosas (`.exe`, `.sh`, `.bat`, etc)
- Leitura UTF-8

**`file_edit(file_path, old_text, new_text, replace_all=False) -> str`**

- Guard: `enable_file_operations` + `is_safe_file_path`
- Se `old_text=""` e arquivo não existe: cria
- `replace(old_text, new_text, count=1)` ou `replace_all` para todas ocorrências

**`file_write(file_path, content) -> str`**

- Guard: `enable_file_operations` + `is_safe_file_path`
- `mkdir(parents=True, exist_ok=True)` antes de escrever
- Retorna path + tamanho em bytes

**`grep(pattern, path=".") -> str`**

- Guard: `enable_file_operations` + `is_safe_regex_pattern` (anti-ReDoS)
- Respeita `.gitignore` via `is_ignored()`
- `re.search(pattern, line)` linha a linha
- Retorna `arquivo:linha:conteúdo` (máx 100 resultados)

**`list_dir(path=".", recursive=False) -> str`**

- Guard: `enable_file_operations`
- Respeita `.gitignore`
- `iterdir()` ou `rglob("*")` se `recursive=True`
- Formato: `[DIR] nome` / `[FILE] nome`; máx 500 itens

**`create_artifact(artifact_type, title, content, session_id="000000") -> str`**

- Guard: `title` e `content` não podem ser vazios; `artifact_type` deve estar em `_VALID_ARTIFACT_TYPES`
- Tipos aceitos: `plan`, `spec`, `task_list`, `overview`, `guide`, `architecture`, `implementation`
- `_artifact_slug(title)` — kebab-case unicode-aware, max 50 chars, fallback `"artifact"`
- Salva em `~/.vectora/artifacts/{session_id}/{slug}.md` (ou `{slug}-1.md`, `{slug}-2.md` para colisões)
- Retorna JSON: `{path, title, artifact_type, session_id, created_at}`
- Erro retornado como JSON: `{error: "..."}`

**`terminal(command) -> str`** (async)

- Normaliza comandos Unix → Windows (`mkdir -p` → `mkdir`)
- Guard: `is_safe_shell_command()` — blacklist-only: `rm -rf`, `mkfs`, `dd if=/dev/zero`, `fork bomb`, `sudo rm/mkfs/dd/shred`
- `asyncio.create_subprocess_shell` (não bloqueia event loop)
- Timeout 30s; stdout + stderr capturados em paralelo
- `emit_terminal_line(line)` para streaming em tempo real na UI

### Memory — `tools/memory.py`

**`save_memory(key, content, metadata=None, ttl_days=None) -> str`**

- `MemoryStore.save(user_id="default_user", key, content, metadata, ttl_days)`
- Retorna `{"status": "saved", "memory_id", "key", "expires_in_days"}`

**`get_memory(key=None) -> str`**

- Com `key`: retorna `{"status": "found", "content", "metadata", "updated_at"}`
- Sem `key`: retorna todas as memórias ativas `{"status": "success", "count", "memories"}`
- Não encontrado: `{"status": "not_found"}`

**`delete_memory(key) -> str`**

- Retorna `{"status": "deleted"}` ou `{"status": "not_found"}`

### MCP — `tools/mcp.py`

**`call_mcp_tool(tool_name, arguments) -> str`**

- Guard: `enable_mcp` + `mcp_server_url`
- `MultiServerMCPClient` singleton lazy-loaded com cache de tools
- `astream_events({tool_name, arguments})` com timeout `mcp_timeout`
- Compatível com qualquer MCP server externo (Claude, LangChain, custom)

---

## 11. Embedding Queue (`services/queue.py`)

### `EmbeddingQueueRecord` (SQLAlchemy ORM)

```
id, queue_id (UUID unique), text, collection, doc_metadata (JSON)
status: pending | processing | success | failed | dlq
error_message, dlq_reason, attempt_count
created_at, processed_at, updated_at
```

### `EmbeddingQueue`

- `init()`: Cria engine async, tabelas, ativa `PRAGMA journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=30000`
- `enqueue(text, collection, metadata) -> queue_id`: INSERT + retorna UUID
- `get_pending(limit) -> list`: `status="pending"` e `attempt_count < 3`
- `count_pending() -> int`: `pending + processing`
- `get_stats() -> dict`: Contagem por status (`pending`, `processing`, `success`, `failed`, `dlq`)
- `mark_processing(queue_id)`: status → `"processing"` + `attempt_count += 1`
- `mark_success(queue_id)`: status → `"success"` + `processed_at`
- `mark_failed(queue_id, error_message)`: status → `"failed"`
- `mark_dlq(queue_id, reason)`: status → `"dlq"` após esgotar retries
- `get_failed() -> list`: `status in ("failed", "dlq")`
- `reconcile()`: Move `status="processing"` com `updated_at > 2 min` de volta para `"pending"` (recovery de crash)
- `close()`: `engine.dispose()`

### Concorrência

- `connect_args={"timeout": 30}`: aguarda WAL lock até 30s
- WAL mode: leituras e escritas simultâneas sem blocking
- `asyncio.Lock` com double-check para singleton `_queue`

### `get_embedding_queue(db_url: str | None) -> EmbeddingQueue`

- Levanta `ValueError` imediatamente se `db_url is None`
- Singleton global com asyncio.Lock (double-check pattern)

---

## 12. Background Embedding Worker (`services/background.py`)

### `BackgroundEmbeddingWorker`

**Loop principal** (polling interval: 5s):

1. `queue.get_pending(limit=10)`
2. Processa em paralelo via `asyncio.Semaphore(5)`
3. Antes de cada embedding: `await _rate_limiter.acquire()` — token bucket para Cohere
4. Para cada registro: `_generate_embedding()` → `_write_to_lancedb()`
5. `mark_success()` ou `mark_failed()` / `mark_dlq()` após 3 tentativas

**`CohereRateLimiter` (token bucket)**:

- `calls_per_minute` configurável via `settings.cohere_calls_per_minute` (default: 90 — 10% abaixo do limite trial de 100/min)
- `asyncio.Lock` serializa aquisições entre os workers paralelos
- Expõe `throttle_count` e `avg_wait_s` para o dashboard `/rag`

**Retry com exponential backoff**:

- Attempt 1: imediato
- Attempt 2: +1s
- Attempt 3: +2s
- Attempt 4: +4s → `mark_dlq(reason=traceback)` com stack trace completo

**LanceDB write serialization**: `asyncio.Semaphore(1)` para evitar race condition em parallel writes

**Startup**: `_reconcile_startup()` — chama `queue.reconcile()` para recuperar jobs travados de crashes anteriores

**Singleton**: `get_background_worker()` com `asyncio.Lock`

**Counters**: `processed_count`, `failed_count` (expostos no dashboard `/rag`)

---

## 13. Embedding Service (`services/embedding.py`)

### `EmbeddingService`

- Gerencia ciclo de vida do LanceDB (lazy-load, `connect_async`)
- Gerencia `CohereEmbeddings` (modelo configurável via Settings)
- Integra com `EmbeddingQueue` para fire-and-forget
- `IgnoreValidator`: evita embeddar secrets, chaves de API, tokens (regex-based)
- `health_check()`: liveness probe para MCP server
- `clear_collection(collection)`: drop + recria tabela no LanceDB
- `search(query, collection, limit)`: semantic search com retry interno

---

## 14. Memory Store (`services/memory.py`)

### `MemoryStore`

**Schema SQLite**:

```sql
CREATE TABLE memories (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  key TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata TEXT,           -- JSON
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  expires_at TIMESTAMP,    -- NULL = nunca expira
  UNIQUE(user_id, key)
)
CREATE INDEX idx_user_key ON memories(user_id, key)
CREATE INDEX idx_expires_at ON memories(expires_at)
```

**Métodos**:

- `save(user_id, key, content, metadata, ttl_days)`: `INSERT OR REPLACE` — upsert por `(user_id, key)`
- `get(user_id, key) -> dict | None`: Valida `expires_at > now`
- `get_all(user_id) -> list`: Ativas, ordenadas por `updated_at DESC`
- `delete(user_id, key) -> bool`: Retorna `True` se linha existia
- `cleanup_expired() -> int`: `DELETE WHERE expires_at < now`

**Singleton**: `get_memory_store(db_dsn)` lazy-loaded

---

## 15. Security (`services/security.py`)

### `is_safe_file_path(path, allowed_dirs=None) -> bool`

- Rejeita `".."` na string (traversal)
- Rejeita extensões executáveis: `.exe`, `.sh`, `.bat`, `.cmd`, `.com`, `.pif`
- Se `allowed_dirs`: resolve path e valida `relative_to(allowed_dir)`

### `is_safe_regex_pattern(pattern) -> bool`

- Blacklist de padrões ReDoS: `(.*)*`, `(.+)+`, `(a|a)*`, e variações
- `try: re.compile(pattern)` — rejeita regex inválido

### `is_safe_shell_command(command) -> bool`

- **Modelo blacklist-only**: permite tudo exceto explicitamente bloqueado
- **Bloqueados**: `rm -rf`, `mkfs`, `dd if=/dev/zero`, fork bomb (`:(){ :|:& };:`), `sudo rm`, `sudo mkfs`, `sudo dd`, `sudo shred`, `shred`

---

## 16. Text Service (`services/text.py`)

### `TextService`

- `encoding_name`: `"cl100k_base"` (GPT-4 compat, sem HuggingFace)
- `chunk_size`: 512 tokens; `chunk_overlap`: 50 tokens
- `_splitter`: `RecursiveCharacterTextSplitter.from_tiktoken_encoder()`
- `split(text) -> list[str]`: chunks respeitando token boundary
- `count_tokens(text) -> int`
- `count_messages_tokens(messages) -> int`: multimodal-safe (text content apenas)

**Singleton via Settings**: `text_service = _build()` — garante mesma contagem entre `ingest_docs` e `trim_messages`

---

## 17. Telemetry Service (`services/telemetry.py`)

### `TelemetryService`

**Logging dual-output**:

- Console: `TextFormatter` — `[LEVEL] logger | thread=N | mensagem`
- File: `JSONFormatter` — JSON Lines com `{timestamp, level, logger, message, thread_id, model, routing_decision, ...}`
- `RotatingFileHandler`: 10 MB por arquivo, 5 backups
- Quiet mode: suprime `langchain`, `langgraph`, `google` loggers

**Audit trail**:

- `log_chat_message(session_id, role, content, metadata)`: acumula em `session_messages`
- `export_session_audit(session_id) -> path`: exporta Markdown com histórico completo

**Debug dump**:

- `export_debug_dump() -> path`: gera `.tar.gz` com `INFO.json` (plataforma, versão, provider), logs JSON, databases

**Correlation**:

- `start_correlation(session_id) -> correlation_id`: UUID para rastreamento por request

---

## 18. Session Service (`services/session.py`)

### `SessionService`

- `initialize()`: Inicializa `AsyncSqliteSaver` (LangGraph checkpointer)
- `create(user_type) -> thread_id`: Novo ID de thread
- `switch(thread_id) -> bool`: Ativa sessão (carrega do checkpointer)
- `list_all() -> list[dict]`: Todas as sessões, ordenadas por `last_activity DESC`
- `get_runnable_config(thread_id) -> RunnableConfig`: `{"configurable": {"thread_id": ...}}`
- `delete(thread_id) -> bool`
- `get_history(thread_id, limit=50) -> list[dict]`: Histórico de mensagens
- `update_activity(thread_id)`: Atualiza `last_activity` + incrementa `message_count`
- `shutdown()`: Fecha conexão com banco

---

## 19. Checkpointer (`services/checkpoint.py`)

```python
async with Checkpointer(db_dsn) as checkpointer:
    # checkpointer = AsyncSqliteSaver
    values = await checkpointer.aget(config)
```

- Async context manager sobre `AsyncSqliteSaver.from_conn_string()`
- Ativa WAL mode na conexão
- Usado pelo `AgentManager` para compilar o grafo com persistência

---

## 20. Settings (`config/settings.py`)

### `Settings` (Pydantic BaseSettings)

**LLM**:

- `llm_provider`: `"google-genai"` | `"openai"` | `"anthropic"` | `"ollama"`
- `google_model`: `"gemini-2.5-flash-lite"` | `openai_model` | `anthropic_model` | `ollama_model`
- `ollama_base_url`

**Runtime**:

- `debug_mode`, `log_level: "INFO"`, `quiet_mode`
- `max_context_tokens: 8000`

**Roaming Profile Pattern** — tudo em `~/.vectora/`:

- `vectora_home`, `data_dir`, `logs_dir`, `keys_dir`
- `db_file`, `embedding_queue_file`, `lancedb_dir`
- `db_dsn`: `"sqlite:///..."` (aiosqlite)
- `embedding_queue_dsn`: `"sqlite+aiosqlite:///..."` (SQLAlchemy)

**Feature Flags**:

- `enable_rag: True`, `enable_web_search: True`, `enable_file_operations: True`, `enable_mcp: False`
- `embedding_queue_enabled: True`

**Embeddings (Cohere)**:

- `embedding_model: "embed-multilingual-v3.0"` (1024 dims)
- `reranker_type: "cohere"`, `reranker_model: "rerank-multilingual-v3.0"`, `reranker_top_k: 5`
- `tiktoken_encoding: "cl100k_base"`, `chunk_size: 512`, `chunk_overlap: 50`
- `cohere_calls_per_minute: 90` — rate limit do BackgroundEmbeddingWorker (trial: 100/min; buffer de 10%)

**Hierarquia de configuração** (crescente):

1. `defaults.env` (embarcado no pacote)
2. `~/.vectora/.env` (global do usuário)
3. `.env` (projeto local) ← maior precedência

**Métodos públicos**:

- `get_llm_provider()`, `get_llm_model()`, `get_llm_api_key()`
- `get_cohere_api_key()`
- `get_available_providers()`: detecta providers pelas API keys presentes no ambiente
- `set_model(provider, model)`
- `_initialize_derived_paths()`: deriva todos os paths a partir de `vectora_home`

**Singleton**: `settings = get_settings()` module-level

---

## 21. MCP Server (`mcp/server.py`)

**13 tools** via `@mcp.tool()` com descrições otimizadas para LLM tool selection:

| Tool                       | Timeout | Função                       |
| -------------------------- | ------- | ---------------------------- |
| `web_search_tool`          | 30s     | Tavily search                |
| `fetch_url_tool`           | 30s     | Tavily extract               |
| `vector_search_tool`       | 20s     | LanceDB semantic search      |
| `embedding_tool`           | 60s     | Fire-and-forget queue        |
| `ingest_docs_tool`         | 120s    | Batch ingestion              |
| `file_read_tool`           | 10s     | Leitura de arquivo           |
| `file_edit_tool`           | 15s     | Edição cirúrgica             |
| `file_write_tool`          | 15s     | Criação/sobrescrita          |
| `grep_tool`                | 20s     | Regex search                 |
| `list_dir_tool`            | 10s     | Listagem de diretório        |
| `terminal_tool`            | 60s     | Shell async                  |
| `call_mcp_tool_tool`       | 45s     | Bridge MCP→MCP               |
| `delegate_task_to_vectora` | 300s    | A2A — executa grafo completo |

**4 resources** via `@mcp.resource()`:

| Resource URI                           | Conteúdo                                           |
| -------------------------------------- | -------------------------------------------------- |
| `vectora://thread/{thread_id}/context` | Resumo da thread atual                             |
| `vectora://thread/{thread_id}/history` | Últimas 5 mensagens                                |
| `vectora://status`                     | Status do servidor (versão, provider, RAG enabled) |
| `vectora://collections`                | Lista de coleções LanceDB disponíveis              |

**Transports**:

- `stdio` (default): JSON-RPC local — Claude Code, Claude Desktop
- `sse` (via `MCP_TRANSPORT=sse`): HTTP/SSE — Paperclip, multi-agent, Docker

**`delegate_task_to_vectora`**: Executa o grafo LangGraph completo como sub-agente via `AgentManager.chat()`, com `thread_id` por cliente para isolamento total de sessão.

---

## 22. Agent Manager (`agent.py`)

### `AgentManager`

DI hub e ponto de acesso de alto nível para todas as funcionalidades:

- Inicializa: `TelemetryService`, `SessionService`, `EmbeddingService`
- Compila o grafo via `build_graph(checkpointer)` + `AsyncSqliteSaver`
- `chat(user_input, session_id) -> str`: Executa LangGraph (`graph.ainvoke`)
- `switch_model(provider, model)`, `get_available_models()`
- `create_session()`, `switch_session()`, `list_sessions()`
- `search_vectors()`, `queue_document_for_embedding()`
- `validate_file_edit()`, `validate_command()`
- `export_session_audit()`, `get_debug_dump()`
- `initialize()` / `shutdown()`: lifecycle completo (workers, databases, LanceDB)

---

## 23. CLI & Interface (`ui/`)

- `chat.py`: TUI com Rich `Live` + `prompt_toolkit` — painéis coloridos por tipo de mensagem
- `commands.py`: Dispatcher de `/` commands (`/debug`, `/model`, `/new`, `/session`, `/tools`, `/rag`, `/help`)
- `main.py`: Componentes Rich (panels, layouts, progress bars, widgets)
- `vectora setup`: Wizard interativo com seleção de provider, input seguro de API key, teste de conectividade
- Prompt multiline: `Alt+Enter` / `Shift+Enter`
- Debug mode: `/debug` toggle, persiste em `~/.vectora/chat_config.json`
- Visual feedback: tool calls (amarelo), responses (vermelho/verde), terminal (verde)

---

## 24. Testing

- **Padrão KISS 1:1**: 1 arquivo de teste por arquivo fonte, estrutura flat em `tests/`
- **197 testes** passando (unit + integration), 4 skipped (e2e reais)
- **Cobertura ≥ 70%** em todos os arquivos com teste dedicado
- **`pytest-asyncio`** com `asyncio_mode = "auto"`
- **ruff** — `All checks passed`
- **ty** — 81 erros residuais: incompatibilidade LangGraph/ty (`TypedDictLikeV1` + campos `Annotated`) + stubs ausentes de Cohere, SQLAlchemy, LanceDB, Rich, Textual — nenhum acionável sem upstream fix

---

## 25. CI/CD & Deployment

- **GitHub Actions** (`runner.yml`): lint (ruff), build (`compileall`), unit/stress/integration/e2e tests, security (safety), docker build+push (GHCR), deploy VPS (SSH+SCP), publish PyPI
- **GHCR**: `ghcr.io/brunosrz/vectora:latest` — autenticado via `GHCR_TOKEN` (PAT, não GITHUB_TOKEN)
- **PyPI**: `vectora-agent` — Trusted Publishing OIDC (sem token armazenado)
- **Todos os jobs**: `environment: Production` — necessário para acessar secrets do ambiente
- **Dockerfile** multi-stage: builder (uv + venv) → runtime (só `.venv` + source, sem uv)
- **docker-compose.yml**: `ghcr.io/brunosrz/vectora:latest`, volume `vectora-data`, porta `8000`
- **Pre-commit hooks**: `uv-lock`, trim whitespace, ruff lint, ruff format, Prettier (markdown), validate TOML/YAML/JSON
- **Semantic versioning**: `version.py` via `importlib.metadata.version("vectora-agent")`

---

## 26. Integrações Externas

| Serviço           | Uso                                                                             | Obrigatório                  |
| ----------------- | ------------------------------------------------------------------------------- | ---------------------------- |
| **Google Gemini** | LLM principal (free tier)                                                       | Um dos quatro                |
| **OpenAI**        | LLM alternativo                                                                 | Um dos quatro                |
| **Anthropic**     | LLM alternativo                                                                 | Um dos quatro                |
| **Ollama**        | LLM local                                                                       | Um dos quatro                |
| **Cohere**        | Embeddings (`embed-multilingual-v3.0`) + Reranking (`rerank-multilingual-v3.0`) | Sim (para RAG)               |
| **Tavily**        | Web search + URL fetch                                                          | Não (RAG ainda funciona sem) |
| **LanceDB**       | Vector store local (file-based)                                                 | Sim (para RAG)               |
| **LangSmith**     | Tracing opcional                                                                | Não                          |

---

## 27. Checklist de Release

### Core

- [x] 14 ferramentas implementadas e testadas
- [x] Orchestrator + 3 workers especializados (direct / search / coder)
- [x] RAG subgraph com 5 nós e threshold adaptativo
- [x] Cascading embeddings (web → LanceDB fire-and-forget)
- [x] Background worker com retry exponencial + DLQ
- [x] Persistência SQLite + LanceDB
- [x] MCP Server (stdio + SSE) com 13 tools + 4 resources
- [x] Memory cross-session (TTL opcional)
- [x] Security: path traversal, ReDoS, command blacklist

### Qualidade

- [x] `ruff check` — 0 erros
- [x] `ty check` — 81 erros residuais não acionáveis
- [x] `pytest tests/ --cov` — 197 testes, ≥70% por arquivo testado
- [x] Pre-commit hooks passando
- [ ] Release notes escritas
- [ ] Git tag `v0.1.0` criada

### Publicação

- [ ] `uv build` — wheel gerado sem erros (verifica `defaults.env` dentro do `.whl`)
- [ ] GHCR push — `ghcr.io/brunosrz/vectora:latest` (via `[deploy]` no commit)
- [ ] PyPI publish — `vectora-agent` via Trusted Publishing (setup único em pypi.org/manage/account/publishing/)
- [ ] GitHub Release criada com changelog e tag `v0.1.0`
