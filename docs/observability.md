# Vectora — Observabilidade

> Plano de instrumentação interna + integrações com plataformas de
> observabilidade externas. Cobre métricas, logs, traces e alertas —
> tanto para o operador do Vectora (admin do servidor) quanto para o
> usuário final (cost tracking, debug de sessão).
>
> **Princípio:** observabilidade é **opt-in granular**. Vectora não
> exporta dados por padrão. Operador decide o que enviar para onde,
> com controle total sobre PII e conteúdo de mensagens.
>
> **Premissa cardinal:** self-hosted significa que **nenhum dado de
> observabilidade sai do servidor do cliente** sem ação explícita do
> operador. Inclusive métricas agregadas que Vectora Company gostaria
> de coletar para roadmap — operador pode opt-in (com recompensa) ou
> manter 100% privado.

---

## Por que observabilidade importa para o Vectora

Agentes de IA são **caixas pretas estatísticas**. O mesmo prompt pode
gerar resultados diferentes em runs diferentes. Para operar em
produção (especialmente em time + setor regulado), saber **o que o
agente fez, quanto custou, quanto demorou e onde falhou** não é
opcional — é requisito de confiança.

Áreas críticas de visibilidade:

1. **Custo** — tokens consumidos por usuário/thread/feature
2. **Latência** — p50/p95/p99 por endpoint, por tool, por LLM
3. **Erros** — falhas de tool, timeouts, rejeitos de LLM, HITL cancelado
4. **Qualidade RAG** — score de reranker, hit rate, contexto irrelevante
5. **Adoção** — features usadas, tools chamadas, skills ativas
6. **Saúde de infra** — DB, vector store, cache, queues
7. **Auditoria** — quem fez o quê, quando (compliance LGPD/SOC2)

---

## Instrumentação interna (sempre presente)

### OpenTelemetry como spec base

Vectora usa **OpenTelemetry** como padrão de instrumentação. Por
padrão, traces ficam em **memória** (acessíveis via `/traces`
endpoint interno) — exportar para coletor externo é opt-in.

**Bibliotecas:**

- `opentelemetry-api`
- `opentelemetry-sdk`
- `opentelemetry-instrumentation-fastapi`
- `opentelemetry-instrumentation-httpx`
- `opentelemetry-instrumentation-asyncpg` (Pro tier)
- `opentelemetry-instrumentation-redis` (Pro tier)
- `opentelemetry-exporter-otlp` (opt-in)

### Spans emitidos

```
vectora.session
├── vectora.thread
│   ├── vectora.agent.orchestrator
│   │   ├── vectora.tool.<tool_name>
│   │   ├── vectora.llm.<provider>.<model>
│   │   │   ├── input_tokens
│   │   │   ├── output_tokens
│   │   │   ├── cost_usd
│   │   │   └── latency_ms
│   │   └── vectora.rag.search
│   │       ├── query_expand
│   │       ├── vector_search
│   │       ├── rerank
│   │       └── decision
│   ├── vectora.agent.coder
│   ├── vectora.agent.rag
│   └── vectora.agent.search
└── vectora.checkpoint
```

Cada span tem atributos padronizados:

- `vectora.user_id`
- `vectora.workspace_id`
- `vectora.thread_id`
- `vectora.tier` (plus/pro/team/enterprise)
- `vectora.feature` (chat/cli/mcp/rest/desktop)
- Atributos específicos do tipo de span

### Métricas emitidas

Métricas Prometheus-compatíveis em `/metrics` endpoint (Pro tier).

**Counters:**

- `vectora_threads_total{tier,feature}` — threads criadas
- `vectora_tool_calls_total{tool_name,status}` — tool calls por status
- `vectora_llm_requests_total{provider,model,status}` — requests para LLM
- `vectora_rag_searches_total{workspace_id,result}` — searches por resultado (hit/miss/fallback)
- `vectora_hitl_decisions_total{action,decision}` — HITL approve/reject
- `vectora_errors_total{component,severity}` — erros por componente
- `vectora_auth_events_total{event_type,status}` — login/logout/token refresh

**Gauges:**

- `vectora_active_sessions` — sessões ativas
- `vectora_active_users` — usuários ativos (últimos 5 min)
- `vectora_embedding_queue_depth` — tamanho da fila de embedding
- `vectora_workspaces_total{tier}` — total de workspaces por tier

**Histograms:**

- `vectora_llm_latency_seconds{provider,model}` — latência de chamadas LLM
- `vectora_tool_duration_seconds{tool_name}` — duração de tools
- `vectora_rag_search_duration_seconds{stage}` — duração por estágio do RAG
- `vectora_request_duration_seconds{endpoint,method,status}` — requests HTTP
- `vectora_token_usage_input{provider,model,user_id}` — tokens consumidos input
- `vectora_token_usage_output{provider,model,user_id}` — tokens consumidos output
- `vectora_cost_usd{provider,model,user_id}` — custo em USD

### Logs estruturados

Vectora usa logging JSON estruturado (`structlog`). Cada log line tem:

```json
{
  "timestamp": "2026-06-05T14:23:15.123Z",
  "level": "info",
  "logger": "vectora.tool.rag",
  "message": "rag_search completed",
  "user_id": "u_abc123",
  "workspace_id": "ws_def456",
  "thread_id": "th_ghi789",
  "trace_id": "abc...",
  "span_id": "def...",
  "tool_name": "rag_search",
  "duration_ms": 423,
  "result_count": 5,
  "score_top": 0.89,
  "rerank_used": true,
  "fallback_used": false
}
```

**Níveis:**

- `DEBUG` — desabilitado por padrão; usado para debug ativo
- `INFO` — eventos significativos (tool call, LLM request)
- `WARN` — degradação não-fatal (fallback acionado, timeout retried)
- `ERROR` — falhas (tool falhou, LLM rejeitou)
- `CRITICAL` — falhas de infraestrutura

### Traces visíveis no chat web

Já implementado parcialmente — comando `/traces` no chat mostra
spans da thread atual:

```
Thread: th_ghi789 (12 turns, 1m 23s)
├── ▶ turn 1 (4.2s)
│   ├── orchestrator decide (0.8s) → use rag_search
│   ├── rag_search (1.3s) → 5 results, top score 0.89
│   │   ├── query_expand (0.2s) → 3 queries
│   │   ├── vector_search (0.5s) → 12 candidates
│   │   ├── rerank (0.4s) → 5 final
│   │   └── decision (0.2s) → high score, inject direct
│   └── llm anthropic/claude-4.5-sonnet (2.1s) → 1.234 tokens, $0.018
├── ▶ turn 2 ...
```

Plano `ux.md` UX-44 expande essa visualização.

---

## Integrações com plataformas externas (opt-in)

### Quando ativar uma integração

```bash
vectora observability enable datadog
vectora observability enable sentry
vectora observability enable langsmith
```

Cada integração tem doc próprio em `docs/integrations/observability-<plataforma>.md`
com configuração detalhada.

### Plataformas suportadas

| Plataforma        | Tipo          | Tier           | Status       |
| ----------------- | ------------- | -------------- | ------------ |
| **OpenTelemetry** | spec genérica | Plus+          | ✅ Nativo    |
| **Prometheus**    | metrics       | Pro+           | ✅ Endpoint  |
| **Grafana**       | dashboards    | Pro+           | ✅ Templates |
| **LangSmith**     | LLM tracing   | Plus+          | ✅ Plugin    |
| **Datadog**       | full          | Pro+           | 🔄 Em dev    |
| **New Relic**     | full          | Pro+           | 🔄 Em dev    |
| **Sentry**        | errors        | Plus+          | 🔄 Em dev    |
| **PostHog**       | product       | Plus+ (opt-in) | 🔄 Em dev    |
| **Honeycomb**     | traces        | Pro+           | 📋 Planejado |
| **Loki/Tempo**    | logs/traces   | Pro+           | 📋 Planejado |
| **OpenObserve**   | open-source   | Plus+          | 📋 Planejado |
| **SigNoz**        | open-source   | Plus+          | 📋 Planejado |
| **Jaeger**        | traces        | Plus+          | 📋 Planejado |
| **Elasticsearch** | logs          | Pro+           | 📋 Planejado |

---

### 1. OpenTelemetry (genérico)

Spec base que todas as outras integrações implementam. Endpoint OTLP
configurável:

```bash
# Via env vars
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.empresa.com:4317
export OTEL_EXPORTER_OTLP_HEADERS="api-key=xxx"
export OTEL_SERVICE_NAME=vectora

# Ou via config Vectora
vectora observability config otlp \
  --endpoint https://otel.empresa.com:4317 \
  --header "api-key=xxx"
```

Funciona com qualquer backend OTel-compatible (incluindo Datadog,
New Relic, Honeycomb, Jaeger, etc. — basta apontar endpoint).

### 2. Prometheus + Grafana

Endpoint `/metrics` exposto (Pro tier, opt-in via config). Grafana
templates oficiais inclusos:

```yaml
# docker-compose.yml (referência)
services:
  vectora:
    environment:
      VECTORA_METRICS_ENABLED: "true"
      VECTORA_METRICS_ENDPOINT: "/metrics"

  prometheus:
    image: prom/prometheus
    volumes:
      - ./vectora-prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    volumes:
      - ./vectora-dashboards:/etc/grafana/provisioning/dashboards
```

**Templates de dashboard inclusos:**

- `vectora-overview` — saúde geral do servidor
- `vectora-cost` — custo de tokens por usuário/feature/dia
- `vectora-rag` — performance do pipeline RAG
- `vectora-agents` — uso de cada sub-agente
- `vectora-llm` — latência e erros por provider/modelo
- `vectora-infra` — DB, cache, vector store
- `vectora-users` — adoção por feature e persona

Hosted em `vectora.company/grafana-templates`. Auto-import via:

```bash
vectora observability grafana import
```

### 3. LangSmith (LLM-specific tracing)

Plugin oficial — alinhado com nosso stack LangChain. Especializado em
debug de LLM calls (cadeias, prompts, retries).

```bash
vectora observability enable langsmith \
  --api-key $LANGSMITH_API_KEY \
  --project vectora-prod
```

Cada thread vira um trace LangSmith com:

- Mensagens completas (input/output)
- Tool calls + resultados
- Token usage por LLM call
- Custos
- Latências por nó do grafo LangGraph

**Privacidade:** mensagens **completas** vão para LangSmith. Para PII-sensitive,
use o modo `redact_messages: true` que substitui conteúdo por hashes.

### 4. Datadog (integração full)

Datadog é o padrão de mercado em PMEs/Enterprise. Integração full
cobre:

- APM (traces)
- Metrics
- Logs
- RUM (se chat web exposto publicamente)
- Synthetics (health checks)

```bash
vectora observability enable datadog \
  --api-key $DD_API_KEY \
  --site us5.datadoghq.com \
  --env production
```

Dashboards Datadog oficiais publicados no marketplace Datadog
(`vectora-monorepo`).

### 5. Sentry (error tracking)

Capturas de erros não-fatal, exceptions, performance issues.

```bash
vectora observability enable sentry \
  --dsn $SENTRY_DSN \
  --environment production \
  --traces-sample-rate 0.1
```

**Privacidade:** stack traces enviadas; mensagens do user e conteúdo
RAG **não** são enviados por padrão. Sentry breadcrumbs filtrados para
remover PII.

### 6. PostHog (product analytics)

Não-padrão para observabilidade, mas útil para entender adoção de
features:

```bash
vectora observability enable posthog \
  --api-key $POSTHOG_API_KEY \
  --host https://us.posthog.com
```

Eventos rastreados (opt-in, customizáveis):

- `feature_used` (qual feature foi invocada)
- `tool_called` (qual tool foi chamada)
- `skill_activated` (qual skill foi usada)
- `persona_switched` (qual persona foi ativada)
- `subscription_action` (upgrade/downgrade/cancel)

**Importante:** PostHog não recebe conteúdo de mensagens — só metadata
de qual feature/tool foi usada.

### 7. Honeycomb (traces ricos)

Specialista em traces de alta cardinalidade. Útil para debug profundo
em produção.

Configuração via OTLP padrão apontando para Honeycomb.

### 8. Loki + Tempo (stack open-source Grafana)

Para empresas que rodam stack Grafana inteiro:

- Loki → logs
- Tempo → traces
- Prometheus → metrics
- Grafana → dashboards unificados

Configuração via OTLP + Loki API.

### 9. OpenObserve / SigNoz (alternativas open-source full)

Para empresas que querem observability stack 100% self-hosted
(complementa filosofia self-host do Vectora):

```bash
vectora observability enable openobserve --endpoint http://openobserve:5080
vectora observability enable signoz --endpoint http://signoz:4317
```

Ambos suportam OTLP nativamente.

---

## Cost tracking (visível ao usuário)

Tracking detalhado de custos visível no chat e em dashboard:

### Por thread (no chat)

Cada thread mostra rodapé:

```
Thread: prd-bulk-export-csv
├── 12 turns · 23 tool calls · 4.2 min
└── Custo: $0.087 USD (Pro tier — incluso)
    ├── LLM: $0.061 (gemini-3.5-flash, anthropic-claude-4.5-sonnet)
    ├── Embedding: $0.012 (cohere-multilingual-v3)
    ├── Reranker: $0.008 (cohere-rerank-multilingual-v3)
    └── Other: $0.006 (Tavily, image gen)
```

### Por usuário (no painel admin)

Dashboard `vectora.company/admin/cost`:

```
Usuário: ana@acme.com (Pro tier)
├── Este mês: $4.23 USD
│   ├── LLM: $3.12 (73%)
│   ├── Embedding: $0.45 (10%)
│   ├── Reranker: $0.34 (8%)
│   ├── Image gen: $0.18 (4%)
│   ├── STT: $0.09 (2%)
│   └── TTS: $0.05 (1%)
└── Quotas restantes:
    ├── Imagens: 247 / 300
    ├── STT: 284 / 300 min
    └── TTS: 583 / 600 min
```

### Tier gate e alertas

- Admin pode setar **budget alerts** por usuário/workspace/total
- Notificações por email + chat quando atingir 80% / 90% / 100% do budget
- Tier gate em `services/license.py` valida quotas antes de cada
  operação custosa
- BYOK (user com chave própria) bypassa quotas mas continua sendo
  trackado para visibility

---

## Privacidade e PII

### O que **nunca** sai do servidor por padrão

- Conteúdo de mensagens do usuário
- Conteúdo de respostas do agente
- Conteúdo de documentos do RAG
- Conteúdo de tool calls
- Conteúdo de arquivos do workspace
- Email, nome real, telefone do usuário

### O que pode ser exportado (opt-in admin)

- Metadata: timestamps, user_id (hashed), workspace_id (hashed), thread_id
- Métricas agregadas: contagens, durações, custos
- Stack traces de erros (sem variáveis locais com PII)
- Eventos de feature usage (qual feature, qual tool, sem conteúdo)

### Modos de privacidade

```bash
# Modo strict — apenas métricas agregadas
vectora observability privacy strict

# Modo balanced (default) — métricas + stack traces sem PII
vectora observability privacy balanced

# Modo debug — TUDO, incluindo conteúdo (só para debug ativo)
vectora observability privacy debug --duration 1h
```

Modo `debug` é **temporário** — auto-reverte para `balanced` após
duração configurada. Log explicito quando ativo. Banner vermelho na UI.

### LGPD / GDPR compliance

- DPA (Data Processing Agreement) disponível para Pro+ tiers
- Operador é o controlador de dados; Vectora Company é o operador (no
  caso de telemetria opt-in para roadmap)
- Right to erasure: `vectora user delete <user_id>` apaga tudo
- Right to portability: `vectora user export <user_id>` gera bundle JSON

---

## Telemetria opt-in para Vectora Company

> **Programa opcional para ajudar a evoluir o Vectora.** Operador
> recebe descontos por participar (até 15% no plano).

### O que é coletado (se opt-in)

- Versão do Vectora instalada
- Features mais usadas (não conteúdo)
- Erros comuns (stack traces sem PII)
- Performance benchmarks agregados
- Modelo de LLM mais usado
- Plugins/skills mais instalados

### O que **nunca** é coletado, mesmo opt-in

- Conteúdo de mensagens
- Conteúdo de documentos
- PII de usuários finais
- Tokens, chaves, secrets
- IPs de usuários finais

### Como participar

```bash
vectora telemetry opt-in --discount-code TELEMETRY15
```

Adiciona 15% de desconto no próximo billing. Pode opt-out a qualquer
momento sem perda do desconto (mas próximo billing reverte).

### Transparência

Todos os dados coletados em modo telemetria opt-in são públicos em
`vectora.company/telemetry-data` (agregados, anonimizados). Permite
auditoria comunitária.

---

## Alertas recomendados

Conjunto inicial de alertas para operador (Grafana / Datadog / etc.):

### Críticos (PagerDuty / OnCall)

- `vectora_request_duration_seconds{p99} > 10s` por 5 min → backend lento
- `vectora_errors_total{severity="critical"} > 0` → falha de infra
- `vectora_active_sessions == 0` por 5 min → servidor down
- `vectora_embedding_queue_depth > 10000` por 10 min → queue stuck
- `vectora_llm_requests_total{status="error"} / total > 0.10` por 5 min → LLM provider down

### Avisos (Slack)

- `vectora_cost_usd{user} > budget_alert` → user atingiu limite
- `vectora_rag_searches_total{result="miss"} / total > 0.30` por 1h → RAG fraco
- `vectora_hitl_decisions_total{decision="rejected"} / total > 0.20` por 1h → agente propondo coisa errada
- `vectora_llm_latency_seconds{p95} > 5s` por 30 min → degradação leve

### Informativos (dashboard)

- Cost diário projetado vs mês passado
- Taxa de adoção de feature nova
- Top tools usadas
- Skills mais ativadas

---

## Cronograma de implementação

```
Pré-lançamento
  Sprint O-1 (1 semana): instrumentação base
    - OpenTelemetry SDK + instrumentation FastAPI/httpx
    - Spans básicos (orchestrator, tool, llm, rag)
    - Atributos padronizados
    - Logs JSON estruturados

  Sprint O-2 (1 semana): métricas
    - Endpoint /metrics (Pro tier)
    - Counters/gauges/histograms básicos
    - Cost tracking visível no chat + admin dashboard

Pós-lançamento Q1
  Sprint O-3 (2 semanas): integrações iniciais
    - OTLP exporter funcional
    - LangSmith plugin
    - Prometheus + Grafana templates oficiais

  Sprint O-4 (1 semana): privacidade
    - Modos privacy (strict/balanced/debug)
    - Auto-revert de debug mode
    - Banner UI

Pós-lançamento Q2
  Sprint O-5 (2 semanas): integrações enterprise
    - Datadog (full)
    - Sentry (errors)
    - PostHog (opt-in)

  Sprint O-6 (1 semana): alertas
    - Templates de alerta Grafana/Datadog
    - Documentação de severidades
    - Tutorial de setup

Pós-lançamento Q3
  - Demais integrações (Honeycomb, Loki/Tempo, OpenObserve, SigNoz)
  - Programa telemetria opt-in com descontos
  - DPA template para Pro+
```

---

## Documentos derivados

Cada integração ganha doc próprio detalhado em `docs/integrations/observability/`:

- `docs/integrations/observability/opentelemetry.md`
- `docs/integrations/observability/prometheus-grafana.md`
- `docs/integrations/observability/langsmith.md`
- `docs/integrations/observability/datadog.md`
- `docs/integrations/observability/sentry.md`
- `docs/integrations/observability/posthog.md`
- (etc.)

Cada doc cobre: setup, configuração, troubleshooting, dashboards
inclusos, limitações conhecidas.

---

## Relacionamento com outros docs

| Doc                    | Relação                                                                    |
| ---------------------- | -------------------------------------------------------------------------- |
| `docs/products.md`     | Tier 2C plugins para Datadog/Sentry/Grafana                                |
| `docs/personas.md`     | Persona pack "Ops/IT" usa tools de observability                           |
| `docs/positioning.md`  | Self-hosted significa observability sob controle do operador               |
| `docs/native-tools.md` | Tools `dns_lookup`, `kubectl_read`, etc. complementam ops/observability    |
| `docs/mcp-library.md`  | MCPs de observability (Datadog MCP, Sentry MCP) disponíveis no marketplace |
| `docs/beta-program.md` | Telemetria opt-in pode informar quem usa quais features para beta          |
| `docs/oem.md`          | OEM exige instrumentation detalhada para SLA                               |

---

## Princípios cardinais

1. **Observability é opt-in granular.** Operador escolhe o que envia
   para onde. Default mínimo: traces em memória, métricas básicas.

2. **Conteúdo nunca sai por padrão.** Mensagens, docs, tool I/O — tudo
   fica local. Exportar requer modo explícito.

3. **Cost tracking sempre visível ao user.** Transparência total — user
   sabe o que está custando antes e depois.

4. **OpenTelemetry como spec base.** Trabalhar com OTel garante
   portabilidade entre backends (Datadog, Honeycomb, Jaeger, etc.).

5. **Self-hosted observability é first-class.** Loki/Tempo, OpenObserve,
   SigNoz suportados — operador pode ficar 100% on-prem.

6. **Templates Grafana/Datadog oficiais.** Setup em minutos, não em
   horas. Dashboard pronto para uso, não exemplo genérico.

7. **Alertas templados.** Operador não precisa inventar regras —
   templates cobrem 90% dos casos típicos.

8. **Telemetria opt-in com recompensa.** Quem ajuda o Vectora a
   evoluir ganha desconto. Quem não quer participa, sem prejuízo.

9. **LGPD/GDPR by design.** DPA template, right to erasure, modo
   privacy strict — tudo nativo, não add-on.

10. **Debug mode é temporário.** Modo verbose com conteúdo completo
    auto-reverte. Banner UI quando ativo. Impossível esquecer ligado.
