# Diagnóstico de bugs (relatados 2026-08-11) + Plano Unificado consolidado

> Documento vivo: consolida o plano de desenvolvimento 0.1.10/0.1.11 com o plano
> de escopo completo (dívidas de Sprints subescopadas) e registra o diagnóstico
> dos bugs reportados ao vivo. Planejamento em markdown (diretriz §9) — código
> é implementado somente após aprovação deste escopo.

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
- **B.** Versionamento da Library (S6): `package_name`/`version`/`GET /:name/versions`.
- **C.** Kanban paridade UI (S7): comentários+timeline (schema novo), editor de
  dependência N/M, run history no card, rename tab "Tasks".
- **D.** Fallback de modelo com imagem (S9): roteamento/sugestão automática.
- **E.** Governança de custo/liveness (Paperclip): `budget_policies` + liveness.
- **F.** Segurança/retenção: `ingest_docs`→`resolve_within_workspace` (tornar
  imediato, não condicional), egress allowlist no sandbox, SOULs vs RBAC pai,
  provider `openrouter` no rerank.
- **G.** Busca híbrida texto+vetor no RAG (promovida).
- **H.** Fechamento do motor nativo (restos S14): `nine_router`, guardrails finais.
- **I.** Features registradas p/ futuro (RAPTOR, memória wiki, etc.) — cada uma
  uma sprint própria, após motor nativo assentar.

### Fase 2 — Plano 0.1.x restante (Sprints 0–18) conforme executado/verificável
(Manter o cronograma original do documento 0.1.10, apenas incorporando
correções das Fases 0–1 onde se aplicam.)

---

## Verificação
- `uv run pytest` nos módulos alterados (adapters, provider_fallback, chat).
- Frontend `vitest` para o hook de stream (duplicação).
- `$env:PYTHONUTF8=1; scons lint && scons tests`.