# Storage — Modo Lite (SQLite + LanceDB)

O modo **lite** é o default do Vectora. Usa SQLite para dados relacionais e
LanceDB para busca vetorial — sem dependências externas (zero Docker, zero
servidor). O modo **complete** (Postgres + Qdrant + Redis) é a alternativa
para quem já tem essa infra; usuários/auth/settings ficam sempre em SQLite,
independente do modo.

---

## SQLite — Pool de conexões (`backend/storage/sqlite/pool.py`)

### Motivação

Abrir uma nova conexão SQLite por request gera contenção de locks em
workloads com múltiplas threads simultâneas. O `AsyncConnectionPool` mantém
conexões abertas e as reutiliza, reduzindo o overhead de abertura e
garantindo que os PRAGMAs de hardening sejam aplicados de forma consistente.

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
from backend.storage.sqlite.pool import AsyncConnectionPool

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

#### `backend/storage/lancedb/connection.py` — `LanceDBConnectionCache`

Cache singleton de objetos `AsyncConnection`. Uma conexão por path.

```python
from backend.storage.lancedb.connection import get_lancedb

db = await get_lancedb()                      # usa settings.lancedb_dir
db = await get_lancedb("/data/my-lancedb")    # path explícito

table = await db.open_table("articles")
results = await table.search(query_vec).limit(10).to_list()
```

#### `backend/storage/lancedb/index.py` — `create_ivf_index`, `create_fts_index`

Criação on-demand de índices IVF_PQ e FTS (Full-Text Search).

```python
from backend.storage.lancedb.index import create_ivf_index, create_fts_index

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

#### `backend/storage/lancedb/optimize.py` — `optimize_table`, `schedule_optimize`

Compactação de fragmentos e remoção de versões antigas.

```python
from backend.storage.lancedb.optimize import optimize_table, schedule_optimize

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

## Roadmap de storage ainda em aberto

- Schema versioning com `storage/migrations/` e um runner de migrations
- ~~Protocols tipados e factories unificadas para os dois modos
  (lite/complete)~~ — feito: `backend/storage/protocols.py`
  (`CheckpointerBackend`/`StoreBackend`/`VectorStoreBackend`/etc.) +
  `backend/storage/factory.py`.
- ~~Integração do `AsyncConnectionPool` com o checkpointer~~ — feito:
  `VectoraSqliteSaver` (`backend/persistence/native/sqlite_checkpointer.py`)
  já abre sobre `AsyncConnectionPool`.
- ~~Store nativo para memória do agente~~ — feito: `VectoraStore`
  (`backend/persistence/native/store.py`), exposto via `StoreBackend`
  Protocol, namespace em tupla (`("user", user_id, "memories")`).
- ~~`LanceDB` como `VectorStoreBackend` nativo~~ — feito:
  `backend/storage/vectorstore/lancedb_backend.py` implementa o Protocol
  `VectorStoreBackend` nativo (`backend/storage/vectorstore/base.py`).

---

## Configuração unificada — registry declarativo (`backend/config/`)

O Vectora tem, e continua tendo, **4 mecanismos de persistência de
configuração desacoplados**: `.env`/`os.environ`/`settings` singleton via
`backend/services/env_keys.py`, `RuntimeSettings` em SQLite
(`backend/workspace/runtime_settings.py`), tabelas SQLite ad hoc do
`provider_routing.py` (modelos registrados por gateway), e
`~/.vectora/config.toml` via `backend/services/license.py`. O registry em
`backend/config/` não substitui nenhum deles — declara, por cima, um
contrato tipado único, hoje consumido pelo CLI auto-gerado (abaixo).
Motivação original: `PATCH /admin/api-keys` e `POST /auth/envs` cada um
com sua própria lógica de "grava no `.env` + atualiza `os.environ` +
atualiza `settings`" (motivo original da existência do `env_keys.py`) —
migrar esses dois handlers REST pra delegar ao registry, como prova de
conceito antes de expandir pra mais categorias, **continua pendente**.

**Peças:**

- `backend/config/registry.py` — `SettingField` (chave, categoria,
  `cli_flag`, descrição, adapter, `secret: bool`) e o registry global
  (`setting_field()` para declarar, `get_field`/`fields_for_category`/
  `all_categories` para consultar). Chave duplicada levanta
  `DuplicateSettingFieldError` — cada campo só pode ser declarado uma vez.
- `backend/config/adapters.py` — `EnvAdapter`, `RuntimeSettingsAdapter`,
  `ConfigTomlAdapter`: cada um sabe ler/escrever num dos mecanismos reais
  acima. Um `SettingField` não guarda valor — delega ao adapter.
- `backend/config/fields.py` — onde os campos são de fato declarados;
  importar este módulo (feito uma vez em `backend/config/__init__.py`) é o
  que popula o registry. Cobre hoje as categorias `integrations` (API keys
  de LLM/search), `connect` (tokens de bot de mensageria) e `preferences`
  (tema, idioma, timezone, `default_model`, `allow_public_signup`).

**Escopo deliberado: só pares chave→valor escalares entram no registry.**
Recursos em formato de coleção — modelos registrados por gateway
(`provider_routing.py`), memórias (`memory.py`), perfil de conta
(`/auth/me`) — não são forçados nesse molde; continuam com CRUD próprio,
especializado. O registry resolve a duplicação de get/set de config
simples, não tenta virar ORM genérico.

**CLI auto-gerado** (`backend/cli/config.py`): um subcomando por
categoria, construído a partir do registry —
`vectora config <categoria> --get [chave]` / `--set chave=valor`. Chave
que não existe na categoria retorna erro amigável, não stack trace.
Comandos anteriores a este registry (`config keys`, `config docker/qdrant/
redis`) continuam existindo como estão — cobrem wizards interativos e
orquestração de infra, não um simples get/set.
