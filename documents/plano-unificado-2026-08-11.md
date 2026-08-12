# Diagnóstico de bugs (relatados 2026-08-11) + Plano Unificado consolidado

> Documento vivo: consolida o plano de desenvolvimento 0.1.10/0.1.11 com o plano
> de escopo completo (dívidas de Sprints subescopadas) e registra o diagnóstico
> dos bugs reportados ao vivo. Planejamento em markdown (diretriz §9) — código
> é implementado somente após aprovação deste escopo.

## Status de execução

- **0.1 Erro 402** — `classify_stream_error` reconhece 402/`OpenRouterCreditError`
  → código `ACCOUNT_CREDIT` + mensagem i18n (pt/en/es). Commit `4719c08b`.
- **0.2 Duplicação de envio** — guard atômico síncrono `useSendGuard` no
  `handleSend`/`processMessage`. Commit `fde9db7e`.
- **0.3 "Mentiu que criou arquivos"** — causa raiz é o Bug 1 (402 quebrava o
  stream no meio da implementação, preservando resposta parcial que prometia
  arquivos, sem erro visível nem retry). Com o 0.1, o erro vira `ErrorEvent`
  com retry; a parte de orquestração (criar só o plano) é comportamento de LLM,
  não bug determinístico — não recebe heurística de código. Resolvido via 0.1/0.2.

---

## Parte 1 — Diagnóstico dos bugs reportados (2026-08-11)

### Bug 1 (grave, causa raiz confirmada): "ficou processando e não respondeu" com kimi/nine router

**Sintoma:** mensagem via nine router (modelo `kimi-k2.5`) fica "processando" e
nunca responde. Depois, via OpenRouter, "duplica a mensagem".

**Causa raiz (log):**

```
backend.llm.openrouter.client.OpenRouterCreditError:
  [kimi/kimi-k2.5] [402]:
  {"error":{"message":"We're unable to verify your membership benefits at this
  time. Please ensure your membership is active.","type":"invalid_request_error"}}
```

Este erro (HTTP 402 — sem crédito/membership) **não é reconhecido** por:

1. `backend/llm/provider_fallback.py::is_quota_error()` — reconhece só
   `QuotaExhaustedError` + `OpenRouterRateLimitError` por tipo, e substring dos
   markers `_QUOTA_MARKERS = ("429", "resource_exhausted", "quota", "rate limit")`.
   A mensagem do 402 ("membership benefits") não contém nenhum marker.
2. `backend/api/adapters.py::classify_stream_error()` — o 402 não casa
   `RATE_LIMIT` (usa só "429") nem `AUTH` (usa só "401"/"403").

**Efeito:** o `FallbackChatModel._astream` trata como erro não-quota → propaga
imediatamente (quebra o stream) → `adapt_stream` emite `ErrorEvent` genérico que
o frontend renderiza como "processando" indefinido.

**Fix proposto (2 partes):**

- `classify_stream_error`: adicionar código/classificação para **402** →
  mensagem clara ao usuário ("Crédito/membership do provedor indisponível") e
  non-reusable (não é falha transitória, é estado de conta).
- `is_quota_error` (ou tratamento em `FallbackChatModel`): decidir se 402
  deve (a) disparar fallback para outro provider/outro modelo, ou (b) virar
  erro de usuário. **Recomendação:** virar erro de usuário (402 é conta do
  provedor, não esgotamento do modelo em si) — tentar fallback esconderia o
  problema de conta. Registrar decisão explícita.

### Bug 2 (em investigação): "duplicação de mensagem"

O `use-stream-handler.processStream` adiciona a bolha do assistente de forma
idempotente (`ensureMessageExists`). A duplicação reportada é no **envio da
mensagem do usuário** — confirmar o path de `send` (chat-interface) e se há
retry/re-send sem dedup por `clientMessageId`/`optimisticId`.

### Bug 3 (comportamento de orquestração, não storage): "mentiu que criou arquivos"

Workspace `Snake` tem só `project.godot`/`icon.svg` + o plano
(`.vectora/plans/plano-...md` e artifact em `~/.vectora/artifacts/...`). Nenhum
`.gd` existe. O agente criou o **plano** (correto para o pedido "crie um plano")
mas relatou como se a implementação estivesse feita. Não é bug de `create_artifact`
ou `file_write`; é o orquestrador (Sprints 11/14 — SOULs/HITL/orquestração nativa)
não fechar o ciclo "planejou → confirmou → implementou de fato".

---

## Parte 2 — Plano Unificado consolidado

Fusão do plano 0.1.10/0.1.11 (Sprints 0–18) com o plano de escopo completo
(6 novas sprints de dívida). Reordenação com as correções de bugs acima.

### Fase 0 — Correções de infraestrutura imediatas (antes de qualquer feature)

- **0.1** Classificar HTTP 402 (`OpenRouterCreditError`) com erro de usuário legível. [Bug 1]
- **0.2** Investigar e corrigir duplicação de envio no frontend. [Bug 2]
- **0.3** Verificar pipeline de orquestração p/ fechar ciclo "plano→implementa". [Bug 3]

### Fase 1 — Concluir dívidas de escopo (detalhado anteriormente)

- **A.** Unificação de persistência (completar registry da S3): `SqliteTableAdapter`,
  `UserRowAdapter`, migrar `/auth/envs` + `/admin/api-keys`, categorias
  `provider_routing`/`memory`/`account`.

  **Execução real (2026-08-12).** Implementado quase por inteiro fora do ciclo
  formal de sprint, em 5 commits (`2970f264`→`52c46f5b`), antes deste item
  virar sprint no plano principal — registrado aqui a posteriori:
  - `SqliteTableAdapter` → entregue como `RegisteredModelsTableAdapter`
    (`2970f264`, contrato de coleção no registry), cobrindo as tabelas
    `*_registered_models` do `provider_routing.py`.
  - `UserRowAdapter` → entregue (`1f4e446e`) para `users.env_overrides_json`.
  - **Além do previsto**: `UserProfileAdapter`/`MemoryAdapter` (`52c46f5b`) —
    `account` e `memory` também viraram coleções no registry, não só os
    overrides de env que o texto original citava.
  - Retrofit REST: `PATCH /admin/api-keys` (`a1ae3226`) e `POST/DELETE
/auth/envs` (`884ed45b`) migrados para delegar ao registry — fecha a
    duplicação de lógica de API key que o próprio `env_keys.py` já
    documentava.
  - **Lacuna real restante**: as categorias `provider_routing`/`memory`/
    `account` têm adapter funcionando no backend, mas `backend/cli/config.py`
    mantém `_REGISTRY_CATEGORIES = {"integrations", "connect", "preferences"}`
    (linha ~317) — não existe hoje um `vectora config provider-routing`/
    `memory`/`account` equivalente ao `--get/--set` escalar das outras 3
    categorias, porque essas são coleções (list, não par chave→valor). Vira
    Sprint 19 abaixo.

- **B.** Versionamento da Library (S6) — detalhado na Sprint 20 abaixo.
- **C.** Kanban paridade UI (S7) — detalhado na Sprint 21 abaixo.
- **D.** Fallback de modelo com imagem (S9) — detalhado na Sprint 22 abaixo.
- **E.** Governança de custo/liveness (Paperclip) — detalhado na Sprint 23 abaixo.
- **F.** Segurança/retenção pendente — detalhado na Sprint 24 abaixo.
- **G.** Busca híbrida texto+vetor no RAG — **já implementada** como Sprint 16
  WS5 do plano principal (`backend/storage/vectorstore/base.py::search_text`,
  fusão de score em `tools/rag.py::vector_search`); listada aqui por engano
  como pendente, corrigido nesta revisão. Nenhuma ação nova.
- **H.** Fechamento do motor nativo (restos S14) — detalhado na Sprint 25 abaixo.
- **I.** Features registradas p/ futuro (RAPTOR, memória wiki, etc.) — detalhado
  na Sprint 26 abaixo.

### Fase 2 — Plano 0.1.x restante

O cronograma detalhado (Sprints 0–26, incluindo as novas Sprints 19–26 abaixo)
vive em `C:\Users\Machi\.claude\plans\iterative-bouncing-treehouse.md` — este
documento não duplica esse conteúdo para não virar uma segunda fonte de
verdade desalinhada; só os 3 bugs da Parte 1 e o resumo de Fase 1 acima são
específicos deste arquivo.

---

## Sprint 19 — Persistência: comando CLI para coleções do registry

**Descrição:** fecha a única lacuna real restante do item A (ver "Execução
real" acima) — as categorias `provider_routing`/`memory`/`account` já têm
adapter de coleção funcionando no backend (`RegisteredModelsTableAdapter`/
`UserRowAdapter`/`UserProfileAdapter`/`MemoryAdapter`), mas nenhum comando CLI
as expõe.

### Escopo

1. Novo verbo `vectora config <categoria> --list` (distinto do `--get/--set`
   escalar já usado por `integrations`/`connect`/`preferences`) para as 3
   categorias de coleção — lista os itens (ex.: modelos registrados por
   gateway, memórias do usuário, perfil de conta) em vez de um par chave→valor.
2. `backend/cli/config.py::_run_category_command` ganha um branch para
   coleção (`fields_for_category` não se aplica — chama o adapter direto via
   um método `list_items()`/equivalente adicionado a cada adapter de coleção).
3. Sem alterar o comportamento das 3 categorias escalares já existentes.

### Testes

- CLI: `vectora config provider-routing --list` lista os modelos registrados
  (happy) + categoria sem nenhum item registrado ainda mostra mensagem clara,
  não erro (edge).
- Regressão: `--get/--set` das categorias escalares continuam funcionando
  sem alteração de comportamento.

### Verificação

`uv run pytest tests/unit/test_cli_config.py -q` + smoke manual dos 3 comandos
novos via `uv run vectora config provider-routing/memory/account --list`.

---

## Sprint 20 — Versionamento real da Library (dívida da Sprint 6)

**Descrição:** hoje `rag_packages`/`skills_catalog` tratam "1 `id` = 1 pacote"
— atualizar um bucket/skill publicado força um pacote inteiro novo em vez de
uma nova versão do mesmo. Fecha a dívida registrada explicitamente no commit
da Sprint 6 original ("não implementado pela metade — avaliar como sprint
própria se o produto pedir").

### Escopo

1. **Schema** (`services/migrations/`): `rag_packages` e `skills_catalog`
   ganham `package_name TEXT` + `version TEXT NOT NULL DEFAULT '0.0.1'` —
   várias linhas por `package_name`, uma por versão (mesmo padrão semver já
   usado em outros pontos do projeto).
2. **Endpoints**: `GET /rag-library/` e `GET /registry/skills` agrupam por
   `package_name`, retornando por default a versão mais recente; novo
   `GET /:name/versions` lista todas as versões de um pacote.
3. **Publish/install**: `POST /rag-library/publish`/`POST /skills` passam a
   ler `version` do manifest (`skill.json`)/metadata do bucket quando
   presente, default `0.0.1` quando ausente; `downloads_count` incrementado
   por versão específica, não pelo pacote inteiro.
4. **Frontend**: `library-memory-section.tsx`/`library-skills-section.tsx`
   mostram a versão mais recente por padrão, com um seletor para ver versões
   anteriores via o novo endpoint.

### Testes

- `services/tests/rag-library/routes.test.ts` (miniflare real, padrão já
  usado): publicar 2 versões do mesmo `package_name` → `GET /` retorna a mais
  recente; `GET /:name/versions` retorna as duas ordenadas; instalar uma
  versão específica incrementa o `downloads_count` dela, não da outra (happy).
  Bad path: pacote sem `version` no manifest usa default `0.0.1` sem quebrar;
  `GET /:name/versions` para nome inexistente devolve lista vazia, não 500.
- Mesma cobertura para `services/tests/registry/routes.test.ts` (skills).

### Verificação

`pnpm --dir services run test` + smoke: publicar via `publish_skill_tool`
duas versões da mesma skill de teste, confirmar agrupamento na Library Tab.

### Execução real (2026-08-12)

- **Schema, endpoints e publish (itens 1-3) — entregues.** `services/src/lib/
versioning.ts` novo (`compareVersions`/`latestPerPackage`, compartilhado
  entre `rag-library` e `registry`, evitando duplicar a lógica de
  agrupamento nos dois catálogos). `GET /rag-library/` e `GET /registry/
skills` colapsam por `package_name`; `GET /rag-library/:name/versions` e
  `GET /registry/skills/:name/versions` novos. `POST /rag-library/publish` e
  `POST /registry/skills` aceitam `version`/`package_name` opcionais
  (default `0.0.1`/nome normalizado). 267 testes verdes (`pnpm --dir
services run test`), `tsc --noEmit` limpo.
- **Achado durante a implementação**: parte do schema (colunas `package_name`/
  `version` nas duas tabelas) e um teste de `rag-library` já estavam
  parcialmente escritos e sem commit no working tree, de uma sessão anterior
  — reaproveitados como ponto de partida em vez de refeitos do zero.
- **Item 4 (frontend — seletor de versões) cortado deliberadamente nesta
  passada.** `library-memory-section.tsx`/`library-skills-section.tsx`
  continuam mostrando só o que a API já retornava antes (a versão mais
  recente, agora correta graças ao agrupamento do backend) — não ganharam
  UI para navegar versões anteriores. Backend/API já suportam isso
  (`GET /:name/versions`), então não é dívida de dado, só de UI; registrado
  aqui para não ficar perdido (CLAUDE.md §9), candidato a entrar junto de
  qualquer sprint futura que já esteja mexendo nesses dois componentes.

---

## Sprint 21 — Kanban: paridade de UI restante (dívida da Sprint 7)

**Descrição:** fecha os itens explicitamente registrados como fora de escopo
no commit da Sprint 7 ("mini-editor de dependência com contagem N/M,
comentários + timeline de eventos, run history conectado ao card, rename da
tab 'Tasks'"). Budget/liveness (também citados lá) viram Sprint 23 própria —
são governança de custo, não paridade de UI, e merecem tratamento e testes
separados.

### Escopo

1. **Comentários por task**: nova tabela (thread simples: autor, texto,
   timestamp) + endpoint CRUD, painel de comentários no card do Kanban.
2. **Timeline de eventos**: expor os eventos já emitidos internamente pela
   state machine (`backend/scheduling/kanban.py`) como lista cronológica no
   card, em vez de só atualizar `updated_at` silenciosamente — sem schema
   novo além de talvez persistir o evento (avaliar se a state machine já loga
   o suficiente para reconstruir, ou se precisa de tabela `task_events`).
3. **Editor de dependência N/M**: substitui o badge de texto `blocked_by` por
   um mini-editor com contagem de progresso (N de M dependências concluídas),
   reusando a state machine já validada.
4. **Run history no card**: conectar `GET /runs` (já existe) ao card — hoje
   desconectado do board.
5. **Rename da tab**: label "Tasks"/"Tarefas" → "Rotinas" ou "Agendamentos"
   (JSDoc do componente já usa a nomenclatura certa, só falta refletir na UI),
   3 idiomas.

### Testes

- Backend: comentário round-trip (criar/listar/deletar); timeline reflete
  transições reais de estado da task (happy) + task sem nenhum evento ainda
  mostra lista vazia, não erro (edge); dependência com ciclo é rejeitada
  (bad path) — contagem N/M correta com dependências parcialmente concluídas.
- Frontend: `kanban-board.test.tsx` — card renderiza comentários/timeline/
  run history a partir de dados injetados (padrão já usado no resto do
  workbench); rename refletido nos 3 idiomas (paraglide compile limpo).

### Verificação

`uv run pytest tests/unit/test_scheduling_kanban.py tests/unit/test_api_kanban.py -q`

- `pnpm --dir vectora/frontend exec vitest run components/workbench/tabs/__tests__/kanban*`
- smoke: criar task com 2 dependências, resolver 1, confirmar "1/2" no card;
  adicionar comentário e recarregar a página, confirmar persistência.

### Execução real (2026-08-12)

- **Itens 3, 4 e 5 — entregues.** `backend/scheduling/kanban.py::
get_dependencies` (pais diretos de `vectora_task_links` com status) +
  `TaskOut.dependencies` (`backend/api/handlers/background.py`) — o
  contador N/M real substitui o badge de texto `blocked_by` que o
  frontend já declarava mas o backend nunca populava (achado confirmado
  nesta sprint: campo morto desde a Sprint 7). `list_runs_for_task` +
  `GET /sessions/{thread_id}/background/tasks/{task_id}/runs` novo —
  fecha a desconexão registrada no texto original ("endpoint existe, só
  por session"). Rename "Tasks"/"Tarefas" → "Rotinas"/"Routines"/"Rutinas"
  nos 3 idiomas. 11 testes de backend + 33 de frontend (2 novos + 31
  preexistentes, todos verdes após a migração do `blocked_by` pro
  `dependencies`).
- **Itens 1 e 2 (comentários + timeline com schema novo) cortados
  deliberadamente nesta passada.** Exigem tabela nova e endpoints CRUD
  próprios — escopo maior e mais arriscado que os itens 3-5, que
  reaproveitaram infraestrutura já existente (`vectora_task_links`,
  `vectora_background_runs`). Continuam registrados como pendência
  explícita, candidatos a sprint própria.
- **Achado durante a implementação**: `_to_out` (handler REST) era
  síncrona e várias chamadas não passavam por `await` — virou `async def`
  pra poder consultar `get_dependencies`; os 4 call-sites existentes
  foram migrados no mesmo commit (nenhum ficou esquecido, confirmado
  pela suíte completa passando).

---

## Sprint 22 — Fallback automático de modelo com suporte a imagem (dívida da Sprint 9)

**Descrição:** a Sprint 9 corrigiu a checagem de capability por modelo
(OpenRouter deixou de ser tratado como "sem visão" por padrão), mas o
roteamento/sugestão automática quando o modelo ativo não processa imagem
ficou registrado como não construído.

### Escopo

1. Config nova: "modelo de imagem de fallback" configurável na UI (Provider
   Routing ou Preferências — decidir durante implementação, não hardcoded).
2. Quando o usuário anexa imagem e o modelo ativo não suporta (via o mesmo
   catálogo de capability já usado pela Sprint 9), o backend/frontend roteia
   automaticamente para o fallback configurado, ou sugere explicitamente (uma
   escolha, não as duas — decidir durante implementação com base no que já
   existe de UX para troca de modelo).
3. Sem fallback configurado: mantém o comportamento atual (aviso bloqueando
   o envio) — não regride quem não configurou nada.

### Testes

- Backend/frontend: modelo ativo sem visão + anexo + fallback configurado →
  usa o fallback (happy); modelo ativo já processa imagem → não interfere
  (edge); sem fallback configurado → aviso atual preservado (regressão).

### Verificação

Smoke: configurar um modelo sem visão como ativo, anexar imagem, confirmar
que o fallback assume automaticamente (ou sugere, conforme decisão de UX).

### Execução real (2026-08-12)

- **Decisão de UX tomada**: roteia automaticamente (não sugere) — reaproveita
  a mesma lógica de override de `configurable["model"]` por request que já
  existe pra outros casos, sem exigir um novo componente de "sugestão" na UI.
- **Config nova**: `image_fallback_model` entrou no registry declarativo
  (`backend/config/fields.py`, categoria `preferences`) — ganha CLI (`vectora
config preferences --set image_fallback_model=...`) de graça, herdando a
  infraestrutura da Sprint 19. Backend: `backend/api/handlers/chat.py::
_resolve_image_fallback_model` — `None` se não configurado ou se o próprio
  fallback também não processa imagem (config inconsistente não vira loop de
  bloqueio disfarçado). Endpoints REST dedicados (`GET`/`PATCH /admin/model/
image-fallback`, mesmo padrão de `/admin/model/fallback-order`) porque não
  existe hoje uma rota REST genérica que exponha campos do registry por
  categoria — construir uma ficou fora do escopo desta sprint.
- **UI**: nova seção em `frontend/components/settings/preferencias/tabs/
fallbacks-tab.tsx` (mesma aba que já lida com fallback de modelo
  cross-provider) — select com "Nenhum" (default, comportamento antigo) +
  lista de `getAllowedModels()`.
- 24 testes de backend (3 de `_resolve_image_fallback_model` + 3 dos
  endpoints REST + regressão dos existentes) + 7 de frontend (3 novos),
  todos verdes.

---

## Sprint 23 — Governança de custo e liveness de subagentes (Paperclip)

**Descrição:** registrado na Sprint 7 original como "reforça o princípio
anti-Devin" — freio automático contra gasto descontrolado e detecção de
"worker vivo mas travado", nunca autonomia adicional.

### Escopo

1. **Budget/cost hard-stop**: análogo simples de `budget_policies` (escopo =
   agente/task/workspace, limite, `warnPercent`, hard-stop automático que
   pausa o escopo ao estourar) — aplicado sobre `backend/scheduling/
background_tasks.py`/`kanban.py`, que hoje não rastreiam custo em nenhum
   nível.
2. **Liveness semântica**: classificador leve (regex sobre output do
   subagente, não LLM-judge) sinalizando `blocked_external`/`manager_review`/
   `planning_only` — puramente informativo, aciona HITL mais cedo, nunca
   gatilho de ação automática.
3. **Fora de escopo, deliberado** (herdado da nota original): hierarquia
   `reportsTo` multi-nível, "delegação só via ticket" substituindo
   `schedule_subagent_task`, qualquer modelo de "contratar um time e deixar
   rodar".

### Testes

- `budget_policies`: estoura em cada dimensão de escopo (happy) + escopo sem
  `warnPercent` configurado não quebra (edge) + pausa automática realmente
  impede nova execução no escopo até reset manual (bad path testado
  positivamente).
- Liveness: classificador identifica os 3 padrões de texto corretamente
  (happy) + output sem nenhum padrão reconhecido não dispara falso positivo
  (edge).

### Verificação

`uv run pytest tests/unit/test_scheduling_budget.py tests/unit/test_scheduling_liveness.py -q`

- smoke: configurar budget baixo numa task de teste, confirmar pausa
  automática ao estourar.

### Execução real (2026-08-12)

- **Achado crítico investigando o item 1**: o mecanismo de budget
  (`backend/scheduling/budget.py`) já existia por inteiro — hard-stop,
  herança de teto do perfil de agente, `check_budget` já plugado em
  `run_task` — mas **nunca funcionava de verdade**: `record_run_cost` (a
  função que grava `estimated_cost_cents`) não tinha nenhum call-site em
  todo o backend. `check_budget` sempre via `total=0` e nunca bloqueava
  nada, silenciosamente. Corrigido: `run_task` (`background_tasks.py`)
  agora extrai `usage_metadata` da última mensagem do agente
  (`_extract_usage`), resolve o modelo usado (override do perfil ou
  provider/model ativo do runtime) e chama `record_run_cost` de verdade
  ao concluir a run.
- **Item 1 (warnPercent)**: `budget_warn_percent` novo (coluna em
  `vectora_background_tasks`) + `budget_status()` (leitura pura,
  reaproveitada por `check_budget`) — cruzar o percentual loga aviso, sem
  bloquear; só `budget_cents` estourado continua bloqueando de verdade.
- **Item 2 (liveness)**: `backend/scheduling/liveness.py` novo —
  `classify_liveness()`, 3 padrões regex (`blocked_external`/
  `manager_review`/`planning_only`), gravado no novo campo
  `vectora_background_runs.liveness` junto do custo, ao final de cada run.
  Puramente informativo — nenhum código consome o rótulo pra agir
  automaticamente ainda (fora de escopo desta sprint, como o texto original
  já previa).
- 41 testes de backend (27 de budget/liveness novos ou tocados + 95 de
  regressão nos módulos que consomem `run_task`/Kanban/tools), `ruff`+`ty`
  limpos.

---

## Sprint 24 — Segurança e retenção pendentes

**Descrição:** consolida os itens de segurança que ficaram condicionais ou
registrados como pendência em sprints anteriores. Egress allowlist do sandbox
(Landlock ABI V4) e SOULs-vs-RBAC do pai **já foram resolvidos** nas Sprints
16 WS6/WS8 do plano principal — não entram aqui, citados só para não serem
repropostos por engano.

### Escopo

1. **`is_safe_file_path` → `resolve_within_workspace` em `ingest_docs`**: a
   Sprint 14 WS13 deixou isso condicional ("verificar na implementação: se
   `rag_ingest.py`/`tools/rag.py::ingest_docs` recebem `directory_path` como
   argumento de tool chamável pelo modelo, migrar"). Resolver a condicional
   agora: confirmar via grep se `ingest_docs` é de fato tool chamável pelo
   modelo (não só endpoint REST) e, se confirmado, migrar sem mais adiar —
   é defesa de path traversal, não deveria ficar pendente indefinidamente.
2. **Provider `openrouter` no dropdown de rerank**: a Sprint 18 confirmou que
   `_build_openrouter_reranker` já existe no backend mas nunca foi exposto no
   dropdown do frontend (decisão deliberada até então: nenhum gateway
   dinâmico tinha rerank nativo estável o bastante). Reavaliar essa decisão —
   se ainda vale a pena, expor como 4ª opção no `ProviderSelect` do
   `rag-settings-panel.tsx`, reusando o campo `rerank_provider_available` já
   adicionado na Sprint 18 (adicionar `"openrouter"` ao dict).

### Testes

- `ingest_docs`: path com `..`/symlink escapando o workspace é rejeitado via
  `resolve_within_workspace` (bad path, mesmo padrão de `fs.py::_confine`) +
  path válido dentro do workspace continua funcionando (regressão).
- `ProviderSelect`: opção `openrouter` aparece habilitada quando
  `rerank_provider_available["openrouter"]` é `True` (happy) + segue
  desabilitada sem key/config equivalente (edge, mesmo padrão da Sprint 18).

### Verificação

`uv run pytest tests/unit/test_rag_ingest.py tests/unit/test_rag_handler.py -q`

- `pnpm --dir vectora/frontend exec vitest run components/workbench/__tests__/rag-settings-panel.test.tsx`.

---

## Sprint 25 — Fechamento de conectores e motor nativo (dívida da Sprint 13/14)

**Descrição:** dois itens que a Sprint 13 (WS-H) e a Sprint 14 (WS10)
deixaram para "depois" explicitamente. **Nota de sequenciamento**: esta
sprint só faz sentido depois que a Sprint 14 WS3-WS12 (motor de execução
nativo, ainda em andamento — ver tarefas #84-95 do plano) estiver concluída;
não é substituta nem duplicata dela.

### Escopo

1. **Branch `nine_router`**: decidir e implementar — migra para
   `VectoraOpenAIChat`/client nativo equivalente com `base_url`
   parametrizável, ou permanece isolado com justificativa documentada (hoje
   é o único branch preso a `langchain-openai` depois que os outros 3
   saírem, conforme já registrado na Sprint 13-H original).
2. **Guardrails finais pós-motor-nativo**: validar que `LoopCapConfig`,
   prompt injection estendido, retry/backoff e timeout do AITL (Sprint 14
   WS10) continuam corretos depois que o loop nativo (WS5) e streaming (WS6)
   estiverem completos — não é escopo novo, é a verificação de que a Sprint
   14 não deixou nenhum guardrail órfão na transição.

### Testes

- `nine_router`: paridade de comportamento antes/depois da migração (mesmo
  padrão de teste de paridade já usado nos outros 4 providers migrados).
- Guardrails: suíte completa de `tests/engine/test_guardrails.py` (já
  planejada na Sprint 14 WS10) roda sem regressão após o motor nativo.

### Verificação

Parte do gate final da Sprint 14 (`scons lint && scons tests`) — não tem
verificação própria separada, é a última costura antes do fechamento do
motor nativo.

---

## Sprint 26 — Backlog de features futuras (sem escopo detalhado)

**Descrição:** itens citados em investigações anteriores (Sprints 15/16) mas
deliberadamente não escopados — cada um exige sua própria investigação antes
de virar plano de implementação. Esta sprint não implementa nada; só formaliza
que continuam candidatos, evitando que sumam do radar.

### Itens (cada um = 1 sprint de investigação própria antes de qualquer código)

1. **RAPTOR** (sumarização hierárquica recursiva sobre embeddings) — maior
   ganho de qualidade para perguntas amplas tipo "resuma este projeto", mas
   exige pipeline de clustering + LLM em batch na ingestão. Alto esforço.
2. **Memória de longo prazo estilo `ai-memory`** (promoção assíncrona
   validada: sessão → sinal forte → página de wiki com trilha de auditoria)
   — por pedido explícito do usuário (Sprint 15), só entra depois que a
   Sprint 14 (motor nativo) e a Sprint 15 (auditoria) estiverem assentadas.
3. **Memory Library como canal de distribuição de skills** (Ideia D da
   investigação da Sprint 16) — depende de quanto `services/src/rag-library/`
   é agnóstico de tipo de conteúdo; não avaliado a fundo ainda.
4. **`callflow_html`** (export de arquitetura em HTML+Mermaid, achado do
   relatório graphify) — esforço médio, boa UX de documentação; feature de
   Context Graph, não de Memory.
5. **Overlay filesystem copy-on-write no sandbox** — avaliado e
   deliberadamente não priorizado (depende de overlayfs em WSL2, histórico
   de bugs conhecidos).
6. **Captura incremental de memória via hooks** (em vez de batch pós-hoc) —
   adiar até a Sprint 14 assentar; introduzir pipeline de eventos novo agora
   competiria pelo mesmo tempo de estabilização do motor nativo.

### Verificação

Nenhuma — item de registro, não de implementação. Cada entrada sai desta
lista só quando ganhar sua própria sprint de escopo completo.

---

## Verificação

- `uv run pytest` nos módulos alterados (adapters, provider_fallback, chat).
- Frontend `vitest` para o hook de stream (duplicação).
- `$env:PYTHONUTF8=1; scons lint && scons tests`.
