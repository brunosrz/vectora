@docs/plan.mdenter plan mode use subagents para analisar o chat, src, testes, company, deploy, update-server, desktop; tambem deve revisar toda a pasta docs/ e vc deve criar um novo plano de implementação, mas nates do novo plano, edite o plano original, implementamos varios blocos (creio que praticamente todos os blocos relacionados a deep agents e a company) vc deve marcar eles como concluidos e deve revisar a api externa, redis e outros, como a api externa usa redis para lidar com messages queue? como ta a escalabilidade do projeto? ja foi implementaddo ate o bloco S? oq do plano original ainda não foi implementado? oq esta faltando? crie um plano enter plan mode nesse plano vc deve planejar os blocos de implementação que ainad não foram concluidos, deve corrigir erros de compilação,deve aumentar a cobertura dos testes backend (fazendo testes coverage, identificando as falhas / pontos criticos que os testes não cobrem)

# Plano — Próximos blocos (G/F/J), correções de build e cobertura de testes backend

## Contexto

Auditoria completa do repo (subagents em `src/`, `chat/`, `desktop/`, `deploy/`,
`update-server/`, `company/`, `docs/`) contra o plano mestre `docs/plan.md`
(blocos A–S). O `docs/plan.md` **já foi atualizado** nesta sessão com o status
real de cada bloco (TOC + cabeçalhos). Resumo do que a auditoria encontrou:

### Status dos blocos (gravado em docs/plan.md)

| Bloco                          | Status                                                                          |
| ------------------------------ | ------------------------------------------------------------------------------- |
| A–D, System Experience         | ✅ Concluídos (já marcados antes)                                               |
| E (Deep Agents harness + TUI)  | ✅ Concluído — pendência E.B-3 (HITL `interrupt_on`)                            |
| F (Storage Postgres/Qdrant)    | 🟡 Lite/protocols/migrations OK; F4 checkpointer Postgres e F6 Qdrant pendentes |
| G (Redis distribuído)          | 🟡 deps + healthcheck OK; **caches in-memory** travam multi-réplica             |
| H (Deep Agents 1)              | ✅ Concluído — pendências H3 (prompt cache) e Tavily                            |
| I (Deep Agents 2: sandbox/ACP) | ❌ Não iniciado                                                                 |
| J (REST API v1 + hardening)    | 🟡 Só `/v1/classify` e `/v1/extract`; sem OAuth2/API-keys/rate-limit            |
| K (Billing & license)          | ✅ Concluído (validação, connect, edge functions)                               |
| L (SDKs)                       | ❌ Não iniciado (depende de J)                                                  |
| M (Observability)              | 🟡 logging estruturado OK; sem OTel/Sentry/probes                               |
| N (Distribution)               | 🟡 desktop+auto-update-server+Docker OK; N5–N9 pendentes                        |
| O–S (Company)                  | ✅ P/Q concluídos; O/R/S são majoritariamente ops externas                      |

### Respostas às perguntas da auditoria

**API externa + Redis/message queue**: a API externa v1 hoje são só 2 endpoints
(`/v1/classify`, `/v1/extract` em `src/api/handlers/v1/`). O chat usa
Connect-RPC + SSE (`/vectora.chat.v1.ChatService/StreamChat`). **Redis NÃO é
usado como message queue em lugar nenhum** — está declarado no pyproject e tem
healthcheck no admin, mas zero uso real. A fila de embeddings é SQLite-based
(worker em `src/services/background.py`), e long-running requests são SSE +
asyncio tasks no mesmo processo.

**Escalabilidade**: o backend é **single-process only** hoje. Pontos que
quebram multi-réplica: `llm_tools._bound_cache` (dict global),
`plugins._mcp_tools_cache` + `_versions`, `workspace._active`, rate-limit
slowapi in-memory, pool SQLite por processo, SSE sem sticky session.

**Erros de compilação encontrados**: (1) e2e `tests/e2e/test_gemini_cli.py`
importa `vectora.mcp.server`, mas o wheel empacota como `src` (pyproject
`packages = ["src"]`) — o módulo real é `src.mcp.server`; (2) demais projetos
compilam limpos (chat tsc ✅, desktop tsc ✅, company build ✅, update-server ✅,
pre-commit 100% verde).

**Cobertura**: a medição com `--cov=src --cov-report=json` será feita como
primeiro passo da Frente 3 na execução (não nesta sessão de planejamento);
pyproject já tem `pytest-cov` configurado.

---

## O que será implementado (3 frentes, em ordem)

## Frente 1 — Correções de build/teste (rápida)

1. **e2e MCP import**: corrigir `tests/e2e/test_gemini_cli.py` para importar
   `src.mcp.server` (o pacote real) em vez de `vectora.mcp.server`; manter um
   skip-with-reason quando o binário/CLI não estiver instalado.
2. Rodar `pre-commit run --all-files` + `pnpm build` (company) + `tsc`
   (desktop/chat) e corrigir qualquer regressão que apareça.

## Frente 2 — Bloco G real: Redis como cache + invalidação + fila (escalabilidade)

Objetivo: destravar multi-réplica. Seguir o desenho do bloco G do plano mestre
(docs/plan.md linha ~4194), implementação mínima e incremental:

1. **`src/services/kv.py`** — abstração KV assíncrona com 2 backends:
   `MemoryKV` (default, lite) e `RedisKV` (quando `REDIS_URL` setado; usa
   `redis.asyncio` já no pyproject). Interface: `get/set/delete/publish/subscribe`
   com TTL. Factory lê `settings.redis_url`.
2. **Invalidação dos caches in-memory** (mantêm o dict local como L1, Redis
   pub/sub como invalidador L2):
   - `src/services/llm_tools.py::_bound_cache` — invalida em
     `tools:changed:{user_id}`.
   - `src/services/plugins.py::_mcp_tools_cache`/`_versions` — bump de versão
     publicado no canal; réplicas descartam a entrada local.
   - `src/services/workspace.py::_active` — persistir workspace ativo no KV
     (chave `ws:active:{user_id}`), dict local vira cache read-through.
3. **Fila de mensagens p/ API externa (Redis Streams)** — novo
   `src/services/queue.py`: `enqueue(stream, payload)` + consumer group
   (`XADD`/`XREADGROUP`/`XACK`). Primeiro consumidor: fila de embeddings
   (background worker passa a aceitar backend redis-stream além do SQLite
   atual — flag `storage_mode=complete`+redis). Segundo: webhooks de saída
   (Bloco L futuro) já nascem na fila.
4. **Rate-limit distribuído**: trocar o storage do slowapi para Redis quando
   `REDIS_URL` presente (slowapi suporta `storage_uri`).
5. Testes unit (fakeredis ou `MemoryKV` + contrato comum de testes para os
   dois backends) e atualização do `deploy/docker-compose.yml` (já tem redis).

## Frente 3 — Cobertura de testes backend

1. Rodar `uv run pytest tests/unit tests/integration --cov=src
--cov-report=term-missing --cov-report=json` como primeiro passo da
   execução. Identificar os módulos com pior cobertura e alto risco
   (handlers de API, storage, license, auth).
2. Escrever testes para os gaps críticos (priorizados por risco × uso):
   - `src/api/handlers/license.py` — novos endpoints `/license/validate` e
     `/license/connect` (httpx mockado, 401/404/503, persistência do token).
   - `src/api/server.py::_license_revalidation_loop` — loop não derruba o
     servidor em falha.
   - `src/api/handlers/v1/*` — classify/extract com modelo mockado.
   - Módulos identificados pelo coverage.json com <50% (lista exata será
     extraída do relatório no início da execução).
3. Meta: subir cobertura global de `src/` em pelo menos +10 p.p. ou cobrir
   100% dos módulos críticos listados; adicionar `--cov-fail-under` brando
   (ex: 60) no pyproject para não regredir.

## Fora de escopo desta iteração (próximos blocos, ordem sugerida)

- **F4/F6** (checkpointer Postgres + Qdrant) — próximo após G.
- **J completo** (OAuth2 client_credentials, API keys, OpenAI-compat) — após F/G.
- **I** (sandbox/ACP), **L** (SDKs), **M** (OTel/Sentry), **N5–N9** (distros/IDE).
- **E.B-3** (HITL interrupt_on) e **H3** (prompt cache) — pendências pontuais
  que podem entrar como itens avulsos.

## Verificação

- `uv run pytest tests/unit tests/integration -q` verde; cobertura ≥ meta.
- `pre-commit run --all-files` verde.
- Com `docker compose -f deploy/docker-compose.yml up` (redis ativo):
  2 réplicas do backend respondem com cache/invalidação consistente
  (teste manual: trocar tool/plugin em uma réplica e ver a outra recarregar).
- `docs/plan.md` com status atualizado (já feito) commitado junto.
- Commits em português, sem Co-Authored-By.

Vou adicionar essa especificação ao plano da company. Lendo a seção P3 (Auth) atual para encaixar:

Adicionado e commitado (`0bf8e0b`). A especificação **P3.1 — Auth avançada** entrou nos dois planos:

**Em [company/plan.md](company/plan.md) § P3.1** (spec completa):

- **TOTP / authenticator app**: usa o MFA nativo do Supabase (`auth.mfa.enroll/challenge/verify`) — QR code no dashboard, 10 recovery codes show-once, e enforcement `aal2` nas operações sensíveis (token, billing, API keys) quando o fator está ativo.
- **Login com Google e GitHub**: botões "Continuar com..." via `signInWithOAuth`, com vínculo automático à conta de mesmo email. O login pede só o mínimo (`openid email profile` / `read:user`).
- **Escopos extras por consentimento incremental**: Drive (read-only) e Calendar são conectados depois, em Dashboard → Integrações — aí sim aparece a tela de consent do Google com os escopos extras. O refresh token fica criptografado server-side na tabela nova `oauth_connections` (RLS deny-all); o agente self-hosted obtém access tokens curtos via edge function `oauth-token` autenticada pelo `VECTORA_TOKEN` — nunca vê o refresh token.
- **GitHub com seleção de repositório**: em vez de OAuth scope `repo` (que daria acesso a tudo), um **GitHub App "Vectora"** — a tela nativa de instalação do GitHub mostra "Only select repositories", e as permissões (`contents: write`, `pull_requests: write`, `issues: write`) valem só para os repos escolhidos. O agente commita via installation access token (TTL 1h) restrito a esses repos.
- **Passkeys (WebAuthn)**: Supabase não tem suporte nativo, então a spec usa `@simplewebauthn/server` + `browser` com tabela `passkey_credentials`, conditional UI no login e fallback para senha+TOTP.

**Em [docs/plan.md](docs/plan.md)**: cabeçalho do Bloco P agora registra "P3.1 Auth avançada PENDENTE" com um resumo apontando para a spec da company.

Ordem de entrega sugerida na spec: TOTP → OAuth social → escopos estendidos → Passkeys (a mais complexa). A cobertura em background segue rodando — continuo a Frente 3 quando ela terminar.

A saída está idêntica há ~40min — a run travou (testes de integração chamando LLM real). Vou matá-la e rodar cobertura só dos unit (rápida e determinística):
