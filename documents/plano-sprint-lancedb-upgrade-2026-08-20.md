# Sprint — LanceDB: reconciliação da versão travada + adoção de features novas

## Contexto e conflito a resolver

O pin atual em `vectora/pyproject.toml` (`"lancedb>=0.36.0,<0.37.0"`) existe
por uma causa concreta, reproduzida isoladamente na sessão que o introduziu:
com `lancedb==0.37.1`, a thread de background do runtime async da lib (Rust,
via Tokio) fica presa em `GetQueuedCompletionStatus` (IOCP do Windows) depois
de volume suficiente de testes anteriores rodarem no mesmo processo — não é
falha de um teste isolado, é acúmulo. Com `0.36.0` a mesma suíte (295/295)
passa 100% de forma determinística. Downgrade + regenerar `uv.lock` eliminou
o hang.

Pedido do usuário: **estudar o LanceDB, remover a restrição de versão, subir
para a última versão disponível, rodar lint+testes, avaliar todos os erros/
avisos, estudar o que mudou entre versões, planejar uma refatoração completa
do vector store para usar cada feature/API nova.**

### O que a pesquisa desta sprint de planejamento já confirmou

- **`0.37.1` continua sendo a última versão _estável_** (checado agora,
  2026-08-20, via PyPI e GitHub Releases do `lancedb/lancedb`) — não houve
  nenhum lançamento estável depois dele até esta data.
- Existe uma série **`0.38.0-beta.N`** em desenvolvimento ativo (betas entre
  14–19/08/2026), com features novas relevantes (colunas computadas via SQL,
  stats de LSM em `RemoteTable.sync`, fixes de offset em hybrid search) — mas
  é **beta**, não release estável. `[[feedback-always-latest-deps]]` do
  usuário pede a última versão **estável** das libs, não beta em produção —
  subir pra um beta seria trocar um risco conhecido (hang) por um risco
  desconhecido (bugs de pré-release) sem necessidade.
- **Nenhum changelog entre `0.36.0` e `0.37.1`, nem a issue tracker pública do
  `lancedb/lancedb`, menciona um fix relacionado a IOCP/`GetQueuedCompletionStatus`/
  hang de thread de background no Windows.** A pesquisa via WebSearch/WebFetch
  não achou o issue exato que bateria com o nosso sintoma (achou só um issue
  não relacionado, #3559, sobre deadlock de CUDA/multiprocessing do
  `sentence-transformers`, sintoma e causa diferentes dos nossos).

**Conclusão honesta**: não há evidência de que o bug que nos fez travar em
`0.37.1` tenha sido corrigido rio acima. Subir a versão agora, sem mais dados,
reintroduziria o mesmo hang que já foi reproduzido de forma rigorosa (A/B
isolado). Ao mesmo tempo, recusar permanentemente também não é a resposta —
o pedido do usuário é legítimo (a lib evolui, ficar 2+ minors pra trás tem
custo). O caminho é **desbloquear com dados reais**, não escolher um lado às
cegas.

## Parte A — Reprodução hermética do hang (pré-requisito de tudo o resto)

### Problema com a evidência atual

A reprodução original dependia de "quantos testes rodaram antes" no mesmo
processo — sintoma de estado acumulado (threads/handles/conexões não
liberadas), não de uma chamada isolada. Isso é frágil como regression gate:
não dá pra rodar em CI de forma confiável nem pra anexar a um issue upstream
com um repro de 10 linhas que o time do LanceDB consiga rodar.

### Trabalho

**A.1** — Escrever um script standalone (`scripts/repro_lancedb_windows_hang.py`,
fora da suíte pytest) que isola a condição real: abrir/fechar N conexões
`lancedb.connect_async` em sequência (sem pytest, sem fixtures, só o loop de
event asyncio nu), até reproduzir o hang de forma determinística com
`0.37.1`. Documentar o N mínimo observado.

**A.2** — Rodar esse script contra `0.36.0` (deve terminar limpo, baseline) e
contra `0.37.1` (deve travar, confirmação). Registrar tempo/PID/thread dump
(via `faulthandler.dump_traceback` ou `py-spy dump` se disponível) do estado
travado — é a evidência que falta pro issue upstream ser acionável.

**A.3** — Abrir issue em `lancedb/lancedb` (GitHub) com o repro do A.1, o
dump de thread do A.2, versão do Windows, Python 3.13, e link pra esta
investigação. Guardar o link do issue nesta sprint (vira `[[lancedb-upstream-issue]]`
pra referência futura).

## Parte B — Auditoria de API atual vs. `0.37.1`/`0.38.0-beta`

Superfície hoje usada por `backend/storage/lancedb/` e
`backend/storage/vectorstore/lancedb_backend.py`: `connect_async`,
`open_table`/`create_table`/`drop_table`/`list_tables`/`table_names`,
`vector_search().limit().to_pandas()`, `search(query, query_type="fts")`,
`create_index` (IVF_PQ e FTS via `lancedb.index.FTS`), `create_fts_index`,
`table.optimize()`, `table.cleanup_old_versions()`, `table.count_rows()`,
`table.add()`, `table.delete()`.

**B.1** — Para cada chamada acima, confirmar contra a doc oficial
(`lancedb.github.io/lancedb/python/python/`) se a assinatura mudou entre
`0.36.0` e `0.37.1`/`0.38.0-beta`. O changelog já sinalizou uma breaking
change relevante: **`add_columns` virou builder pattern** — não é chamado
hoje no nosso código (grep confirma), mas registrar mesmo assim como um
"não nos afeta, mas atenção se alguém for usar".

**B.2** — Levantar avisos de depreciação: rodar o repro do Parte A e o
`optimize_table`/`create_ivf_index`/`create_fts_index` existentes contra
`0.37.1` isolado (fora da suíte completa, pra não disparar o hang) e
capturar todo `DeprecationWarning`/`FutureWarning` emitido.

## Parte C — Features novas: candidatas a adoção (por versão)

Levantamento inicial via changelog público — **cada item abaixo precisa de
confirmação de disponibilidade na versão exata durante a implementação**
(a pesquisa desta sprint usou fetch de changelog via ferramenta de IA
auxiliar, que já errou datas uma vez nesta mesma pesquisa — não tratar como
100% preciso sem checar a doc/changelog primário no momento de implementar):

1. **LSM checkpoint/flush/compact** (gestão explícita de Log-Structured
   Merge) — pode substituir o `schedule_optimize()` atual
   (`backend/storage/lancedb/optimize.py`), que hoje só chama
   `table.optimize()` + `cleanup_old_versions()` num loop `asyncio.sleep`
   sem nenhum controle fino. Ganho: compactação sob demanda/dirigida por
   métrica em vez de só por tempo fixo (1h).
2. **Job handles em operações async** (ex.: `create_index` retornando um
   handle acompanhável) — hoje `create_ivf_index`/`create_fts_index` fazem
   só `await` cego sem progresso nem cancelamento. Índices IVF_PQ em
   coleções grandes (>100k linhas) podem demorar; um handle com progresso
   melhora UX de "reconstruir índice" nas Settings.
3. **FTS com lista de stop-words customizável** — `search_text()` hoje usa
   `FTS()` default. Corpus em português tem stop-words diferentes do
   default (provavelmente inglês) — ganho de qualidade de busca textual
   direto, sem custo de migração de schema.
4. **OpenTelemetry metrics** — observabilidade nativa da lib (latência de
   query, tamanho de fragmento, etc.) em vez de só os `logger.debug/warning`
   manuais espalhados no código atual. Alinha com qualquer telemetria OTel
   que o backend já exponha (`backend/persistence/telemetry.py`) — avaliar
   integração no boot.
5. **Colunas computadas via SQL** (`0.38.0-beta` — não adotar em produção
   enquanto for beta; registrar como "observar até virar estável").

## Ordem de execução e critério de avanço

1. **Parte A é bloqueante** — sem repro hermético + issue upstream, não faz
   sentido tentar subir a versão de novo (repetiria o mesmo A/B já feito,
   sem novidade).
2. Enquanto o issue upstream (A.3) não tiver resposta/fix, **o pin
   `<0.37.0` permanece** — não é recusa permanente, é "esperando dado
   externo que ainda não existe". Reavaliar a cada release novo do LanceDB
   (checar changelog por menção a IOCP/Windows/hang antes de tentar de
   novo).
3. **Parte C (features) não depende da Parte A/B terminar** — os itens 1–3
   (LSM optimize, job handles, FTS stop-words) precisam só ser confirmados
   como disponíveis já em `0.36.x` (provável, já que `0.33.0`/`0.36.0` do
   changelog já traziam LSM/metrics) — se sim, dá pra adotá-los **sem subir
   de versão**, decorrelacionando "usar features novas" de "estar na última
   versão". Esse é o maior desbloqueio prático: entrega valor ao usuário
   (features novas, sprint de refatoração de verdade) sem reintroduzir o
   hang.
4. Se/quando a Parte A confirmar fix upstream, reavaliar o pin e então
   revisitar os itens do item 3 acima que dependiam de versão nova
   (nenhum identificado até agora, mas B.1 pode revelar algum).

## Testes (TDD, CLAUDE.md §18)

- Script de A.1 não é teste pytest (é reprodução isolada por natureza —
  rodar dentro da suíte reintroduziria o próprio hang que ele existe pra
  provar). Documentar isso explicitamente no cabeçalho do script.
- Cada feature adotada na Parte C entra com happy path + erro/borda no
  mesmo teste existente da função que ela estende (ex.: `optimize_table`
  ganha teste de LSM checkpoint bem-sucedido + falha de checkpoint não
  derruba a task de background, mesmo padrar já usado no arquivo).
- Regressão: `test_storage_lancedb_backend.py` (ou onde a suíte atual
  cobrir `LanceDBBackend`) precisa continuar 100% verde em `0.36.0` durante
  toda a Parte C — nenhuma feature nova pode assumir uma API que só existe
  em `0.37+`.

## Verificação

- `uv run pytest tests/ -q --tb=short` completo, com o pin ainda em
  `<0.37.0`, depois de cada item da Parte C implementado.
- Rodar o script do A.1 contra a versão pinada atual como smoke test de
  "não travou" antes de cada commit desta sprint.
- `scons lint && scons tests` como gate final, como sempre.
