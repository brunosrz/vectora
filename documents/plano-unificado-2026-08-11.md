# Pendências do plano de desenvolvimento

Este documento listava o diagnóstico de bugs e o plano de sprints de
0.1.10/0.1.11. A investigação do código atual confirma que a grande maioria
já foi implementada: os três bugs diagnosticados (erro 402 do OpenRouter,
duplicação de envio, orquestração "planejou mas não implementou") foram
corrigidos; a unificação de persistência, o fallback de imagem, a governança
de custo/liveness de subagentes, os itens de segurança (path traversal em
`ingest_docs`, rerank via OpenRouter) e o versionamento de pacotes na
Library estão implementados no backend; o motor de conversa nativo está
completo e sem nenhuma dependência restante de LangChain/LangGraph/
deepagents (inclusive o provider `nine_router`, que era o último ponto preso
a `langchain-openai`); e os guardrails (`LoopCapConfig`, prompt injection,
retry/backoff, timeout do AITL) têm cobertura própria em
`tests/unit/test_engine_guardrails.py`.

O que segue é só o que genuinamente ainda não foi construído.

## Pendente: comando CLI para categorias de coleção do registry

`backend/cli/config.py::_REGISTRY_CATEGORIES` ainda cobre só
`integrations`/`connect`/`preferences` (par chave→valor via `--get/--set`).
As categorias `provider_routing`, `memory` e `account` já têm adapter de
coleção funcionando no backend (`RegisteredModelsTableAdapter`,
`UserRowAdapter`, `UserProfileAdapter`, `MemoryAdapter`), mas nenhum comando
CLI as expõe.

Falta: um verbo `vectora config <categoria> --list` para essas 3 categorias
de coleção, com branch próprio em `_run_category_command` (chama
`list_items()` no adapter em vez do `--get/--set` escalar). Sem alterar o
comportamento das categorias escalares existentes.

## Pendente: seletor de versões na Library (frontend)

O backend já suporta múltiplas versões por pacote (`services/src/lib/
versioning.ts`, `GET /rag-library/:name/versions`, `GET /registry/skills/
:name/versions`). `library-memory-section.tsx` e `library-skills-section.tsx`
continuam mostrando só a versão mais recente, sem UI para navegar versões
anteriores. Não é dívida de dado — é só UI a construir.

## Pendente: comentários e timeline no Kanban

`backend/scheduling/kanban.py` não tem tabela de comentários nem eventos
persistidos. Faltam:

- **Comentários por task**: tabela (autor, texto, timestamp) + endpoint CRUD
  - painel no card do Kanban.
- **Timeline de eventos**: expor as transições de estado da task (hoje só
  atualizam `updated_at` silenciosamente) como lista cronológica no card —
  avaliar se dá para reconstruir a partir do que a state machine já loga ou
  se precisa de uma tabela `task_events` nova.

## Backlog de features futuras (sem escopo detalhado)

Itens candidatos, cada um exigindo sua própria investigação antes de virar
plano de implementação — nenhum tem código hoje:

1. **RAPTOR** (sumarização hierárquica recursiva sobre embeddings) — maior
   ganho de qualidade para perguntas amplas ("resuma este projeto"), exige
   pipeline de clustering + LLM em batch na ingestão. Alto esforço.
2. **Memória de longo prazo estilo wiki** (promoção assíncrona validada:
   sessão → sinal forte → página com trilha de auditoria).
3. **Memory Library como canal de distribuição de skills** — depende de
   quanto `services/src/rag-library/` é agnóstico de tipo de conteúdo; não
   avaliado a fundo.
4. **`callflow_html`** (export de arquitetura em HTML+Mermaid) — esforço
   médio, boa UX de documentação; feature de Context Graph, não de memória.
5. **Overlay filesystem copy-on-write no sandbox** — avaliado e
   deliberadamente não priorizado (depende de overlayfs em WSL2, histórico
   de bugs conhecidos).
6. **Captura incremental de memória via hooks** (em vez de batch pós-hoc).

## Verificação

- `uv run pytest tests/unit/test_cli_config.py tests/unit/test_scheduling_kanban.py -q`
  quando os itens de CLI/Kanban acima forem implementados.
- `pnpm --dir services run test` + `pnpm --dir vectora/frontend exec vitest run`
  para o seletor de versões da Library.
- `$env:PYTHONUTF8=1; scons lint && scons tests` como gate final de qualquer
  um destes itens.
