# Storage — Modo Lite (SQLite + LanceDB)

O modo **lite** é o default do Vectora. Usa SQLite para dados relacionais e
LanceDB para busca vetorial — sem dependências externas (zero Docker, zero
servidor).

---

## SQLite — Pool de conexões (`src/storage/sqlite/pool.py`)

### Motivação

O `AsyncSqliteSaver` do LangGraph abre uma nova conexão por `from_conn_string()`
a cada request. Para workloads com múltiplas threads simultâneas isso gera
contenção de locks no SQLite. O `AsyncConnectionPool` mantém conexões abertas
e as reutiliza, reduzindo o overhead de abertura e garantindo que os PRAGMAs
de hardening sejam aplicados de forma consistente.

### PRAGMAs aplicados a toda conexão

| PRAGMA         | Valor       | Motivo                                                 |
| -------------- | ----------- | ------------------------------------------------------ |
| `journal_mode` | `WAL`       | Leitores simultâneos não bloqueiam o escritor          |
| `busy_timeout` | `30000`     | Espera até 30 s antes de retornar `SQLITE_BUSY`        |
| `synchronous`  | `NORMAL`    | fsync só em checkpoints WAL — mais rápido que `FULL`   |
| `temp_store`   | `MEMORY`    | Tabelas temporárias em RAM                             |
| `mmap_size`    | `268435456` | 256 MiB de memória mapeada — reduz syscalls de leitura |
| `foreign_keys` | `ON`        | Integridade referencial ativada                        |

### Uso

```python
from src.storage.sqlite.pool import AsyncConnectionPool

# Pool reutilizável no ciclo de vida da aplicação
pool = AsyncConnectionPool("data/vectora.db", min_size=1, max_size=8)
await pool.open()

async with pool.acquire() as conn:
    row = await conn.execute_fetchone("SELECT * FROM spans WHERE session_id=?", (42,))

await pool.close()

# Ou como context manager
async with AsyncConnectionPool.from_path("data/vectora.db") as pool:
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO …")
```

### Parâmetros

| Parâmetro  | Default | Descrição                             |
| ---------- | ------- | ------------------------------------- |
| `min_size` | 1       | Conexões abertas no `open()`          |
| `max_size` | 8       | Limite máximo de conexões simultâneas |

---

## LanceDB — Cache de conexões e índices

### Motivação

Cada chamada a `lancedb.connect_async(path)` recarrega metadados do diretório
Lance. Para o Vectora, que acessa as mesmas coleções repetidamente, um cache
processo-local elimina esse overhead.

### Módulos

#### `src/storage/lancedb/connection.py` — `LanceDBConnectionCache`

Cache singleton de objetos `AsyncConnection`. Uma conexão por path.

```python
from src.storage.lancedb.connection import get_lancedb

db = await get_lancedb()                      # usa settings.lancedb_dir
db = await get_lancedb("/data/my-lancedb")    # path explícito

table = await db.open_table("articles")
results = await table.search(query_vec).limit(10).to_list()
```

#### `src/storage/lancedb/index.py` — `create_ivf_index`, `create_fts_index`

Criação on-demand de índices IVF_PQ e FTS (Full-Text Search).

```python
from src.storage.lancedb.index import create_ivf_index, create_fts_index

table = await db.open_table("articles")

# Índice vetorial IVF_PQ (criado só se a tabela tem >= 10 000 linhas)
await create_ivf_index(table)

# Índice FTS para busca lexical
await create_fts_index(table, text_column="text")
```

**Parâmetros IVF_PQ:**

| Parâmetro         | Default | Descrição                                       |
| ----------------- | ------- | ----------------------------------------------- |
| `num_partitions`  | 256     | Clusters IVF — aumentar para coleções maiores   |
| `num_sub_vectors` | 16      | Sub-vetores PQ — controla qualidade vs. memória |
| `min_rows`        | 10 000  | Mínimo de linhas para criar o índice            |

#### `src/storage/lancedb/optimize.py` — `optimize_table`, `schedule_optimize`

Compactação de fragmentos e remoção de versões antigas.

```python
from src.storage.lancedb.optimize import optimize_table, schedule_optimize

# Otimização única
await optimize_table(table)

# Otimização periódica em background (cada hora)
task = schedule_optimize(table, interval_s=3600)

# Para cancelar:
task.cancel()
```

---

## Quando usar cada índice

| Cenário                             | Índice                                 |
| ----------------------------------- | -------------------------------------- |
| Busca semântica (embeddings)        | IVF_PQ                                 |
| Busca por palavra-chave exata       | FTS                                    |
| Busca híbrida (semântica + lexical) | Ambos (reranking manual ou via Cohere) |
| Coleção < 10 000 vetores            | Nenhum (linear scan é mais rápido)     |

---

## Próximos passos (F2+)

- **F2** — Schema versioning com `storage/migrations/` e `runner.py`
- **F3** — Protocols tipados e factories unificadas
- **F4** — Integração do `AsyncConnectionPool` com `AsyncSqliteSaver`
- **F5** — `SqliteStore` para LangGraph BaseStore (memórias do agente)
- **F6** — `LanceDB` como `VectorStore` do LangChain
