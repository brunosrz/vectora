# Vectora × Hermes Agent — Comparativo de features e níveis de implementação

> Documento vivo. Origem: pedido explícito do usuário (2026-08-14) para estudar a
> fundo o hermes-agent (NousResearch, MIT, open source) como referência
> comparativa — release notes completas (24 releases, mar→ago/2026), página
> `hermesagents.net/evolution/`, issues abertas (`P1`+`area/auth` e
> `type/feature`), e comparação de código-fonte real área por área, via 8
> subagentes de pesquisa rodados em paralelo.
>
> **Regra de leitura deste documento**: nenhuma célula de "quem lidera" é
> absoluta. Cada capacidade tem um **nível de implementação** próprio
> (`ausente` / `stub` / `funcional básico` / `funcional com edge cases` /
> `produção madura com testes/hardening`) — o objetivo é nunca tratar
> "Vectora tem X" ou "Hermes tem X" como resposta binária. Os dois produtos
> têm formas fundamentalmente diferentes (Hermes é gateway multi-plataforma
> de mensageria com CLI/TUI/Desktop; Vectora é workspace chat-first
> webapp/desktop com filesystem/git/terminal/browser compartilhados entre
> usuário e agente) — comparar célula a célula pode enganar se a diferença
> de arquitetura não for levada em conta.
>
> **Auditoria de correção (2026-08-19)**: conferência linha a linha contra o
> código real do Vectora. Principais mudanças desde o levantamento de
> 2026-08-14: SSO/OIDC saiu de "ausente" para implementado
> (`backend/rbac/oidc.py`, commit `61f84426`, 2026-08-15); a allowlist de env
> pro subprocess MCP local foi fechada (`backend/tools/mcp.py`); o guardrail
> de loop preso ganhou detecção de repetição (`backend/engine/
conversation_loop.py`); e a composição nomeada de toolsets, que era só
> proposta, foi implementada (`backend/tools/groups.py`). Os demais itens
> foram conferidos e permanecem como descritos.

---

## 1. Hermes Agent — quem é, trajetória (fonte: 24 release notes + evolution page)

Lançado publicamente em 12/mar/2026 (v0.2.0) após ~8 meses de desenvolvimento
interno, MIT-licensed, 100% público no GitHub, 1.400+ contribuidores. Ritmo de
release extremamente alto: 24 releases em ~5 meses (a cada 5-15 dias, centenas
de PRs por janela — 245 contribuidores só na v0.17.0).

Trajetória de produto em 3 frentes simultâneas:

1. **Alcance** — de 7 para 24+ plataformas de mensageria (Telegram, Discord,
   Slack, WhatsApp, Signal, iMessage, WeChat, LINE, Matrix, etc.) e dezenas de
   providers de LLM.
2. **Profundidade do agente** — memória plugável, Kanban multi-agente durável,
   verificação de trabalho ("done = provado"), voz conversacional.
3. **Superfície de produto** — CLI → TUI (React/Ink) → Dashboard web → Desktop
   Electron nativo → Desktop como plataforma (artifacts sandboxed + Plugin SDK).

Segurança é tratada como esforço contínuo (seção dedicada em toda release, 3
ondas declaradas de "zero P0/P1": v0.13.0, v0.18.0, v0.19.0/v0.20.0).
Performance é benchmarkada publicamente com números exatos.

Releases mais recentes (v0.18.0→v0.20.1, jul-ago/2026): Mixture-of-Agents como
modelo selecionável, `/goal` com completion contracts, `/learn`/`/journey`,
smart approvals como default, secret sources plugáveis (Bitwarden/1Password),
ledger de entrega à prova de crash, voz com barge-in, citações verificáveis,
webhooks assinados, protocolo A2A (Agent-to-Agent) v1.0, limite de iteração
90→500. Timeline completa e evolução por área funcional (auth, memória,
sandbox, orquestração, MCP, streaming/UI, billing, observability) foram
mapeadas release a release nesta investigação¹.

Roadmap público (issues abertas, `type/feature`, 100 issues): maior bloco é
paridade completa com a API REST do Discord (~30 issues, quase pronto),
seguido por confiabilidade de delegação/orquestração multi-agente (incluindo
interoperabilidade com um agente externo "Prime Agent") e observabilidade de
compressão de contexto (nascida de um incidente reconhecido publicamente).
Auth aparece só 2x no roadmap de features (GitHub App bot-identity, "A2A Trust
Levels") — os 4 issues P1+area/auth são todos bugs de robustez em torno do
OAuth de assinatura Anthropic, não features novas.

¹ Levantamento feito via `gh release view`/`gh issue list` contra
`NousResearch/hermes-agent` (24 releases, mar→ago/2026) e reproduzível a
qualquer momento — os digests brutos são artefato de pesquisa desta sessão,
não foram commitados como arquivo separado no repo; este documento é a
síntese que substitui/resume esse material.

---

## 2. Matriz-resumo por área

| Área                                                | Quem lidera hoje                               | Lacuna mais séria do Vectora                                                                                                              | Esforço                            |
| --------------------------------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| Auth / SSO                                          | **Empate** (implementado em 2026-08-15)        | Nenhuma — OIDC real entregue (`backend/rbac/oidc.py` + `backend/api/handlers/oidc.py`, Authorization Code + PKCE S256, JWKS); ver seção 3 | —                                  |
| Auth / RBAC produto                                 | **Vectora**                                    | Hermes deliberadamente não tem RBAC granular                                                                                              | —                                  |
| Multi-tenant SaaS                                   | Nenhum dos dois                                | Lacuna **compartilhada** — nenhum isola dados entre orgs num banco compartilhado                                                          | Alto (decisão de arquitetura)      |
| Sandbox / isolamento OS-level                       | **Vectora, folgado**                           | Nenhuma — Hermes só isola via Docker/terceiros                                                                                            | —                                  |
| Guardrail de loop preso                             | Hermes na profundidade da classificação        | Vectora detecta repetição de tool call (`conversation_loop.py`), mas sem a classificação idempotente/mutante do Hermes                    | Baixo (refinamento, não gap bruto) |
| Denylist write/read sem sandbox ativo               | Hermes                                         | Proteção do Vectora depende do sandbox estar ativo                                                                                        | Baixo                              |
| Memória de fatos / RAG / Context Graph              | **Vectora, folgado**                           | Nenhuma — Hermes terceiriza tudo a plugins, sem RAG/context-graph nativo                                                                  | —                                  |
| Delegação básica de subagente                       | Empate (formas diferentes)                     | —                                                                                                                                         | —                                  |
| Decomposer automático (triage → grafo)              | Empate                                         | Nenhuma — `kanban_decompose` implementado, ver seção 6                                                                                    | —                                  |
| Goal-mode (Ralph loop)                              | Empate                                         | Nenhuma — `run_goal` implementado, ver seção 6                                                                                            | —                                  |
| Liveness ativa de subagente                         | Hermes                                         | Vectora só classifica pós-hoc, não detecta travamento em tempo real                                                                       | Médio-alto                         |
| Marketplace de skills (fontes múltiplas)            | Hermes, com folga                              | Vectora tem 1 fonte só (catálogo curado)                                                                                                  | Médio                              |
| Versionamento de skill/pacote                       | Hermes                                         | **Vectora — já resolvido** (`package_name`/`version`/`GET /:name/versions`, commit `f2f798e9`, posterior à pendência que o registrava)    | —                                  |
| Cliente MCP (robustez)                              | Hermes                                         | Vectora sem retry/circuit-breaker dedicado                                                                                                | Baixo-médio                        |
| Catálogo de tools nativas (contagem)                | **Vectora**                                    | —                                                                                                                                         | —                                  |
| Composição/reuso nomeado de toolsets                | Empate                                         | Nenhuma — `backend/tools/groups.py` implementa grupos nomeados com `includes` recursivo e aliases, ver seção 7                            | —                                  |
| Registry de conectores MCP (discovery automatizado) | **Vectora**                                    | —                                                                                                                                         | —                                  |
| Filesystem compartilhado (edição real pelo usuário) | **Vectora, com folga real**                    | Hermes só visualiza (explorador), sem editar/criar pela UI                                                                                | —                                  |
| Terminal compartilhado usuário↔agente               | **Vectora** (diferencial real confirmado)      | Hermes tem 2 terminais separados, um deles read-only                                                                                      | —                                  |
| Browser compartilhado (navegação real, multi-tab)   | **Vectora, com folga real**                    | Hermes é preview de dev server local, não navegador de internet                                                                           | —                                  |
| Context Graph / code intelligence                   | **Vectora** (ausente no Hermes)                | —                                                                                                                                         | —                                  |
| Streaming — contrato tipado                         | **Vectora** (17 eventos Pydantic vs dataclass) | —                                                                                                                                         | —                                  |

---

## 3. Auth, RBAC e multi-tenant

Fonte: subagente dedicado desta investigação (2026-08-14), leitura direta de código em ambos os repositórios.

| Capacidade                       | Hermes                                                                                                        | Vectora                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Lidera                            | Lacuna real                                                                                                                      |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Login/senha                      | Funcional, produção-com-hardening (plugin opcional, timing-safe compare)                                      | Funcional com edge cases (Argon2id, núcleo do produto)                                                                                                                                                                                                                                                                                                                                                                                                                                          | Empate qualitativo                | —                                                                                                                                |
| Token de sessão                  | Produção madura (JWT/JWKS externo RS256, RFC 7009 revoke)                                                     | Funcional com edge cases (HS256 local, rotação a cada refresh)                                                                                                                                                                                                                                                                                                                                                                                                                                  | Hermes (protocolo)                | Não crítico — Vectora é self-host de instância única                                                                             |
| **SSO/OIDC**                     | Produção madura, testada (`self_hosted`/`nous` providers, PKCE S256, JWKS, RFC 8252)                          | **Implementado** (2026-08-15, commit `61f84426`) — `backend/rbac/oidc.py`: Authorization Code + PKCE S256 (nunca `plain`), descoberta via `.well-known/openid-configuration` com `follow_redirects`, verificação de `id_token` via JWKS (`PyJWKClient`), single IDP por instância configurável em `backend/config/registry.py`, wired em `backend/api/handlers/oidc.py` (`app.include_router(oidc_router)` em `server.py`). Login local segue como único caminho quando não há IDP configurado. | Empate qualitativo                | Não confirmado ainda: paridade com RFC 8252 (fluxo nativo/desktop) e client_credentials pra service account — ver linha seguinte |
| API token / service account      | Funcional (seam `token_auth_middleware` desacoplado)                                                          | Ausente — só JWT de usuário                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Hermes                            | Sem mecanismo de credencial máquina-a-máquina                                                                                    |
| **RBAC granular**                | Funcional básico, **deliberadamente raso** (admin/user binário em slash commands, versão completa descartada) | **4 papéis hierárquicos**, funcional com edge cases, usado consistentemente                                                                                                                                                                                                                                                                                                                                                                                                                     | **Vectora, muito à frente**       | —                                                                                                                                |
| Multi-tenant / isolamento de org | Stub (`org_id` decorativo)                                                                                    | Funcional básico (isolamento por projeto local, não SaaS)                                                                                                                                                                                                                                                                                                                                                                                                                                       | Nenhum — **lacuna compartilhada** | Design de arquitetura novo se mirar SaaS multi-org                                                                               |
| Convites de usuário              | Ausente                                                                                                       | Funcional com edge cases (token/TTL/papel pré-atribuído)                                                                                                                                                                                                                                                                                                                                                                                                                                        | **Vectora**                       | —                                                                                                                                |
| Recuperação de senha             | Ausente                                                                                                       | Ausente                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Nenhum                            | Lacuna comum                                                                                                                     |
| Auditoria/logs                   | Funcional (redação automática, arquivo local)                                                                 | Funcional (consultável via API, RBAC próprio) — sem redação automática confirmada                                                                                                                                                                                                                                                                                                                                                                                                               | Dividido                          | Vectora deveria confirmar que `metadata_json` do audit nunca grava token/cookie                                                  |

**Recomendações priorizadas** (detalhe completo no relatório do subagente):

1. ~~Implementar OIDC real antes de vender o benefício "pro"~~ — **feito** (2026-08-15, `backend/rbac/oidc.py`, commit `61f84426`), portou o desenho de `DashboardAuthProvider` do Hermes.
2. Redação automática de campos sensíveis no audit log — baixo esforço (1-2h).
3. Mecanismo de service account / API token — médio esforço (1-2 dias).
4. Fluxo de recuperação de senha — médio esforço (1 dia), reaproveitando o padrão de convite já existente.
5. Multi-tenant real — registrar como decisão de arquitetura em `docs/`, não como sprint.

---

## 4. Sandbox, isolamento e segurança de tools

Fonte: subagente dedicado desta investigação (2026-08-14).

| Capacidade                                            | Hermes                                                                                      | Vectora                                                                                                                                                                                                                                                             | Lidera                                    | Lacuna real                                                                       |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------- |
| **Isolamento OS-level** (seccomp/Landlock/namespaces) | **Nenhum in-tree** — doc oficial admite "só o SO é fronteira"; real só via Docker/terceiros | **Produção madura** — bwrap+seccomp+Landlock(egress V4)+rlimits (Linux), WSL2+bwrap (Windows), Seatbelt (macOS), Singularity                                                                                                                                        | **Vectora, folgado**                      | —                                                                                 |
| Isolamento via container Docker                       | Funcional com hardening documentado (cap-drop, pids-limit, tmpfs)                           | **Funcional, paridade confirmada** — `backend/sandbox/docker.py`: `--cap-drop`, `--security-opt no-new-privileges`, perfis `normal`/`lockdown` com `--memory`/`--cpus`/`--pids-limit`, `--network none --read-only` quando sem rede                                 | **Empate, paridade confirmada**           | —                                                                                 |
| Egress de rede no sandbox                             | Nenhum controle nativo (só SSRF em tools de fetch)                                          | **Landlock ABI V4** — controle real de syscall                                                                                                                                                                                                                      | **Vectora**                               | —                                                                                 |
| Política de aprovação (HITL)                          | Madura — blocklist hardline inamovível (sobrevive a yolo/cron)                              | Funcional — HITL nativo com sobrevivência a restart                                                                                                                                                                                                                 | Empate, vantagem de maturidade pro Hermes | Vectora sem blocklist hardline explícita e documentada                            |
| Detecção de comando perigoso                          | Extenso (+25 padrões documentados) + scanner de conteúdo (Tirith)                           | Não localizado catálogo equivalente — depende do isolamento de sandbox                                                                                                                                                                                              | Hermes na cobertura documentada           | Se sandbox desabilitado (Windows sem WSL2), sem segunda camada                    |
| Proteção de arquivos sensíveis                        | Muito madura (denylist + cross-profile + sandbox-mirror guard)                              | Mask de sandbox nativo, bloqueio a nível de kernel quando ativo                                                                                                                                                                                                     | Dividido                                  | Sem denylist independente do sandbox ativo                                        |
| **Guardrail de loop preso**                           | Maduro — classificação idempotente/mutante + detecção de repetição (642+798 linhas)         | **Implementado, mais simples** — `backend/engine/conversation_loop.py` detecta tool calls consecutivas idênticas e emite aviso de loop preso, além do teto fixo `max_iterations`; sem a classificação idempotente/mutante do Hermes, aqui é só sinal pro LLM/HITL   | Hermes na profundidade da classificação   | Menor — falta a camada de classificação idempotente/mutante, não a detecção em si |
| Prompt injection defense                              | Funcional (scanner de padrão textual)                                                       | Funcional, dupla camada (scanner + envelope `<untrusted_content>`)                                                                                                                                                                                                  | Vectora, ligeira vantagem de design       | Vectora cobre menos padrões (5 regras vs cobertura mais ampla)                    |
| Credential env filtering (MCP/subprocess)             | Maduro                                                                                      | **Implementado** — `backend/tools/mcp.py` monta o subprocess stdio com `env=_safe_subprocess_env(extra_keys)`, allowlist mínima (`_SAFE_SUBPROCESS_ENV_KEYS`) mais chaves extras nomeadas por servidor; o processo filho não herda mais `os.environ` inteiro do pai | Empate                                    | —                                                                                 |
| SSRF protection                                       | Maduro e documentado                                                                        | **Maduro** — `backend/browser/ssrf_guard.py::is_url_ssrf_safe` resolve DNS antes de checar IP privado/loopback/link-local/reservado/multicast (proteção contra DNS rebinding, não só validação de string), usado em `fetch_url`                                     | **Empate, paridade confirmada**           | —                                                                                 |

**Recomendações priorizadas**:

1. Loop guardrail com detecção de repetição — médio esforço (2-3 dias). **Feito** — `backend/engine/conversation_loop.py`, detecção de tool call repetida.
2. Denylist write/read independente do sandbox — baixo esforço (1 dia). **Feito (Sprint 19).**
3. Expandir catálogo de padrões de prompt injection — baixo esforço (0.5 dia). `backend/services/prompt_injection.py` existe; abrangência atual não reauditada nesta revisão.
4. **Allowlist de env pro subprocess MCP local** (`tools/mcp.py`) — **Feito** — `_safe_subprocess_env`/`_SAFE_SUBPROCESS_ENV_KEYS`.
5. Documentar o limite dos guards do Vectora ("defense-in-depth, not a boundary") — trivial (1h).

---

## 5. Memória, RAG e Context Graph

Fonte: subagente dedicado desta investigação (2026-08-14).

**Achado estrutural mais importante**: o hermes-agent core **não tem memória
própria** — `agent/memory_manager.py` é só um orquestrador de `MemoryProvider`s
plugáveis de terceiros (mem0, hindsight, holographic, honcho...), um por vez.
`agent/learning_graph.py` também não é code intelligence — é um grafo de UI
ligando skills+memória por overlap léxico de tokens, sem parsing de código.

| Capacidade                                    | Hermes                                                                        | Vectora                                                                                               | Lidera                                    |
| --------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| Fatos key-value / memória de sessão           | Nenhum nativo — 100% dependente de plugin externo                             | Maduro — `save/get/search/delete_memory`, categorização, busca semântica                              | **Vectora**                               |
| Orquestração de múltiplos backends de memória | Muito maduro (fencing, scrubbing, dispatch assíncrono)                        | Não existe (1 backend só)                                                                             | Hermes (não prioritário pro Vectora hoje) |
| Consolidação/síntese de memória               | Só de skills (`curator.py`), não de conversas                                 | Real e completo — job periódico, síntese LLM, versionado, HITL gate                                   | **Vectora**                               |
| RAG / vetorização própria                     | Ausente no core (só via skills que instruem o LLM a chamar CLIs de terceiros) | Maduro — `VectorStoreBackend` nativo (LanceDB/Qdrant), busca híbrida RRF                              | **Vectora**                               |
| Context graph / code intelligence             | **Ausente**                                                                   | Maduro — tree-sitter ~30 linguagens, passe semântico LLM, cluster, resolução de símbolos, incremental | **Vectora, larga margem**                 |

**Conclusão**: nenhuma ação defensiva necessária nesta área — Vectora lidera
com folga real e nativa. Único ponto de referência de design a considerar (não
prioritário): padrão de dispatch assíncrono serializado + drenagem com timeout
do `memory_manager.py`, caso `memory_consolidation.py` precise rodar mais
operações em background no futuro.

---

## 6. Subagentes, orquestração e Kanban

Fonte: subagente dedicado desta investigação (2026-08-14).

| Capacidade                                          | Hermes                                               | Vectora                                                                                                                                                                                                                                                                                                                                                                                                                                        | Lidera                    | Esforço se fechar                                     |
| --------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- | ----------------------------------------------------- |
| Delegação básica                                    | Produção madura (wait/cancel/reconnect assíncrono)   | Funcional com edge cases (síncrono, sem resume externo)                                                                                                                                                                                                                                                                                                                                                                                        | Empate (design diferente) | —                                                     |
| Capability token / dedup                            | Produção madura (HMAC, correlation_id)               | Ausente — mas não é regressão (Vectora não expõe handle serializável)                                                                                                                                                                                                                                                                                                                                                                          | Hermes                    | Baixo risco hoje                                      |
| **Validação de RBAC scope do subagente vs pai**     | Produção madura (`_validate_request`)                | Mitigação estrutural (allowlist fixa por SOUL), sem checagem formal explícita                                                                                                                                                                                                                                                                                                                                                                  | Hermes em rigor formal    | **Médio** — gap real se SOUL novo ganhar tools amplas |
| Liveness / subagente travado                        | Produção madura (watchdog ativo + cancelamento real) | Básico — regex pós-hoc sobre texto final, puramente informativo                                                                                                                                                                                                                                                                                                                                                                                | Hermes                    | **Médio-alto**                                        |
| Triage automático (LLM classifica task)             | Produção madura                                      | Ausente — cards ficam presos em `triage` esperando ação humana                                                                                                                                                                                                                                                                                                                                                                                 | Hermes                    | Médio                                                 |
| **Decomposer automático** (fan-out triage→children) | Produção madura                                      | **Implementado** — `kanban_decompose` (`backend/tools/kanban.py`) chama `FallbackChatClient` pra propor children (nome/instrução/dependências) a partir de um card em `triage`, cria cada um via `create_task`, liga dependências rejeitando ciclo nó a nó, arquiva o original; fallback determinístico (JSON inválido ou lista vazia = card não muda)                                                                                         | Empate                    | —                                                     |
| **Goal-mode** (Ralph loop)                          | Produção madura (judge + gates + turn budget)        | **Implementado** — `run_goal` (`backend/engine/goal_mode.py`) encadeia turnos de `run_conversation` até dois critérios AND: gates de qualidade (comando externo, ex. suíte de testes, saída 0) e judge (chamada LLM síncrona no padrão `ask_parent_agent`); rejeição reinjeta objetivo + motivo como nova mensagem de usuário; nunca decide por cima de HITL pendente (`stopped_reason="interrupted"` devolve o outcome sem rodar gates/judge) | Empate                    | —                                                     |
| Kanban — máquina de estados                         | 6 estados                                            | **9 estados**, claim atômico CAS, TTL, escalonamento automático                                                                                                                                                                                                                                                                                                                                                                                | **Vectora**               | —                                                     |
| Kanban — UI (prioridade/assignee/comentários)       | —                                                    | Presente, gap de UI anterior parece corrigido (não validado E2E)                                                                                                                                                                                                                                                                                                                                                                               | Vectora                   | Validação, não implementação                          |
| Budget de custo por run                             | Não encontrado equivalente                           | Funcional — `check_budget`/`estimate_cost_cents`, corte automático antes de criar run                                                                                                                                                                                                                                                                                                                                                          | **Vectora**               | —                                                     |

**Recomendações priorizadas**:

1. Baixo esforço — testar/documentar que `SOUL_CATALOG` já mitiga escalonamento de escopo.
2. ~~Portar decomposer automático~~ — **feito** (`kanban_decompose`, `backend/tools/kanban.py`).
3. Médio esforço — checagem formal de RBAC scope na delegação.
4. Médio-alto esforço — liveness ativa com heartbeat + cancelamento real.
5. ~~Goal-mode~~ — **feito** (`run_goal`, `backend/engine/goal_mode.py`).
6. Triage automático (classificar task recém-criada em `triage` sem ação humana) — segue ausente, único item real pendente desta seção. Médio esforço.

---

## 7. MCP, tools e marketplace de skills

Fonte: subagente dedicado desta investigação (2026-08-14).

| Capacidade                                   | Hermes                                                             | Vectora                                                                                                                         | Lidera                                                                 |
| -------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Cliente MCP (robustez)                       | Maduro (OAuth, circuit breaker, cert cliente, >20 testes)          | Funcional mas fino (`MultiServerMCPClient`, 2 conexões fixas)                                                                   | Hermes                                                                 |
| Servidor MCP                                 | Tem os dois lados                                                  | Não tem — decisão deliberada (CLAUDE.md §16)                                                                                    | Diferença de arquitetura, não atraso                                   |
| Catálogo de tools nativas (contagem)         | ~125 tools                                                         | **~163 tools**, registry nativo próprio                                                                                         | **Vectora**                                                            |
| **Composição/reuso nomeado de toolsets**     | Maduro — `toolsets.py` (ver detalhe abaixo)                        | **Implementado** (`backend/tools/groups.py`) — grupos nomeados com `includes` recursivo e detecção de ciclo, ver detalhe abaixo | Empate — Vectora fechou a lacuna                                       |
| **Marketplace de skills (fontes múltiplas)** | **5 fontes** (GitHub/WellKnown/Url/SkillsSh/ClawHub), trust levels | **1 fonte** (catálogo curado + GitHub code-search)                                                                              | **Hermes, com folga**                                                  |
| Versionamento de skill                       | Sim (`_resolve_latest_version`, download por versão)               | **Sim — já implementado** (`package_name`/`version`/`GET /:name/versions`, commit `f2f798e9`)                                   | Empate real — pendência anterior estava obsoleta                       |
| Publish de skill                             | Não tem publish próprio (consome hubs de terceiros)                | `install_skill` via git URL direto                                                                                              | Modelos diferentes, Vectora mais auditável                             |
| Registry de conectores MCP                   | Sem discovery automatizado confirmado                              | **Discovery automatizado** contra registry oficial MCP, persistência D1                                                         | **Vectora**                                                            |
| Sistema de plugins Python de terceiros       | Maduro (4 fontes, manifest, hooks)                                 | Não existe — via MCP client e Skills                                                                                            | Hermes, mas **não recomendado replicar** (contradiz CLAUDE.md §16/§17) |

### Composição de toolsets — como o Hermes faz e o que falta no Vectora

O `toolsets.py` do Hermes é um dict estático `TOOLSETS: dict[str, dict]` onde cada
entrada tem três campos: `description` (texto pra UI/CLI), `tools` (lista de
**nomes-string** de tool, resolvidos contra o registry central) e `includes`
(lista de **nomes de outros toolsets**). A peça que falta no Vectora é
`includes`: um toolset pode compor outros por referência nomeada, resolvida
recursivamente em runtime por `resolve_toolset()` (com detecção de ciclo via
`visited: set[str]`) — ex. `"debugging"` inclui `"web"` + `"file"` sem
precisar listar as tools de novo; `"hermes-gateway"` é a união nomeada de 18
toolsets de plataforma. Há também alias de toolset (`register_toolset_alias`,
usado por servidores MCP conectados dinamicamente) e um mecanismo de bundle-delta
(`bundle_non_core_tools()`) pra desligar só as tools específicas de um bundle
sem esvaziar o núcleo compartilhado por outros. Isso alimenta configuração real
pelo usuário (`hermes tools`, painel do desktop) e a restrição de tools em
`delegate_task` (bloqueia toolsets inteiros por papel — `leaf` não recebe
`delegation`, `orchestrator` recebe de volta — e não filtro tool-a-tool).

**O que o Vectora tem hoje**: `backend/tools/groups.py` define
`TOOL_GROUPS: dict[str, ToolGroupSpec]` — cada grupo tem `name`,
`description`, `tool_names` (strings resolvidas no `TOOL_REGISTRY` nativo em
tempo de resolução, nunca objetos) e `includes: list[str]` opcional
(referência a outros grupos, composta por `resolve_tool_group(name,
visited=None)` recursivamente, com `ToolGroupCycleError` em ciclo real —
mesmo espírito do `resolve_toolset()` do Hermes). `backend/agents/souls.py`
declara `tool_groups: list[str]` por SOUL (ex. `["fs", "git", "memory",
"rag", "browser", "aitl"]`) e resolve lazy no `Soul.tools`, não em
import-time. Há aliases compatíveis com nomes antigos (`browser-qa` →
`browser`, `fs-readonly` → `fs_readonly`, `planner` → `artifact`). O gap que
falta, e que não existia como pendência anterior: nenhum endpoint
(`GET /admin/tool-groups`) expõe o catálogo pra CLI/UI consultarem — a
composição roda só no backend, sem superfície de configuração pelo usuário.

**Recomendações priorizadas**:

1. ~~Composição nomeada de toolsets~~ — **feito** (`backend/tools/groups.py`).
2. Segunda fonte de discovery de skills — médio-alto esforço (3-5 dias), reavaliar decisão anterior de descartar skills.sh.
3. Trust level explícito no catálogo — baixo esforço (1 dia), reaproveitando padrão `vectora_verified`.
4. Retry/circuit-breaker básico em `tools/mcp.py` — baixo-médio esforço (1-2 dias).
5. Endpoint `GET /admin/tool-groups` pra expor o catálogo de `TOOL_GROUPS` — baixo esforço (meio dia), se o produto quiser customização de perfil pelo usuário.
6. **Não fazer**: plugin system Python instalável — contradiz princípio arquitetural do produto.

---

## 8. Streaming, UI e workbench compartilhado

Fonte: subagente dedicado desta investigação (2026-08-14).

**Correção de premissa importante**: Hermes NÃO é "agente único ator,
usuário só observa" — o desktop dele (`apps/desktop`) tem painéis reais de
arquivos, review/diff e terminal manipuláveis pelo usuário. A tese de venda do
Vectora precisa ser mais cirúrgica.

| Capacidade                                            | Hermes                                                                                                                                                                                            | Vectora                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Lidera                                                                                                                                                                                                                       |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Filesystem compartilhado                              | **Médio — só visualização real de arquivos**; sem edição/criação pelo usuário na UI (painel `right-sidebar/files/`, tree+DnD, mas é um explorador, não um editor)                                 | **Alto — criar, editar, deletar, mover pela própria UI**, com resolução de conflito otimista (`expected_sha256` + HTTP 412 quando o agente edita por baixo, com opção de forçar), busca em conteúdo + replace-all em massa, histórico de arquivo via git, gerenciador de `.gitignore`. Edição é **Monaco real** (`frontend/lib/monaco/setup.ts`, mesmo motor do VS Code — o "IDE mode" do produto existe justamente pra aproveitar isso), não um textarea simplificado. Ressalva real: mover arquivo entre pastas por **drag-and-drop não existe hoje** (zero `onDrop`/`draggable` em `files-tab.tsx`) — vira sprint de UX fix.      | **Vectora, com folga real (editor)** — gap real de UX em mover arquivo                                                                                                                                                       |
| Git/diff                                              | Médio-alto (foco em revisar/"ship", não git genérico)                                                                                                                                             | Alto (escopo mais amplo)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Vectora                                                                                                                                                                                                                      |
| **Terminal compartilhado**                            | **Baixo-médio — DOIS terminais separados**, um deles explicitamente read-only/sem PTY                                                                                                             | **Alto — literalmente a mesma sessão pty** compartilhada                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | **Vectora, diferencial real confirmado**                                                                                                                                                                                     |
| Browser compartilhado                                 | **Médio — preview de app rodando localmente** (webview do dev server, devtools/console/error states), não navegação livre de internet                                                             | **Alto — navegador completo**: `browser_navigate` aceita qualquer URL http/https (só o esquema é checado, sem allowlist de host/porta), suporte nativo a **múltiplas abas** (tab strip com favicon/histórico, uma `WebContentsView` por aba no desktop), e o agente opera a **mesma sessão Playwright/CDP do workspace** que a UI observa (painel de devtools inspeciona literalmente a sessão do agente). Tools reais de interação: `navigate`/`click`/`scroll`/`fill`/`drag`/`upload_file`/`fill_form`/`wait_for`/`read_dom`/`screenshot`, mais gestão de dev servers locais como complemento opcional, não como escopo principal. | **Vectora, com folga real**                                                                                                                                                                                                  |
| Kanban/orquestração de tarefas                        | Médio (plugin externo sobre REST próprio)                                                                                                                                                         | Médio-alto (nativo ao streaming, `TodosUpdatedEvent`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Vectora (integração nativa)                                                                                                                                                                                                  |
| **Context graph**                                     | **Ausente**                                                                                                                                                                                       | Alto (tab dedicada)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | **Vectora**                                                                                                                                                                                                                  |
| RAG/memória — síntese automática de skills (Remember) | **Alto — design original**: o Hermes não tem RAG nativo (ver seção 5 — "ausente no core"), mas tem a feature "Remember"/`/learn`, somada a Honcho (modelagem de usuário) e FTS5 (busca de sessão) | **Alto — feature "Remember"**: gatilho automático a cada 5 turnos (`remember_trigger.py`), destila via LLM estruturado tanto **skills novas** (`SKILL.md` completo: nome, descrição, passo a passo) quanto fatos duráveis, com dedup contra o que já foi aprovado; nunca instala nada sozinho — sempre grava proposta revisável (artifact na aba Plan) e exige HITL explícito (`install_learned_skill`/`save_learned_fact`, ambas `destructive: True`) antes de persistir. **Construído diretamente com base no Remember do Hermes** — não é convergência paralela, é o mesmo conceito com HITL/dedup adicionados depois.            | **Duas afirmações diferentes, não empate**: Hermes lidera em design _original_ do conceito (Vectora é o derivado, honestamente creditado); Vectora lidera em RAG/Context Graph nativos, que o Hermes não tem em lugar nenhum |
| Tab "library" unificada                               | Espalhado (skills/ + plugins)                                                                                                                                                                     | Unificada (MCP+Skills+Memory)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Vectora                                                                                                                                                                                                                      |
| **Protocolo de streaming (contrato tipado)**          | Dataclass, não confirmado se documentado como union discriminada                                                                                                                                  | **17 tipos de evento, Pydantic union discriminada explícita**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | **Vectora**                                                                                                                                                                                                                  |

**Achado-chave para reposicionamento de mensagem**: o diferencial real não é
"Hermes não compartilha nada" (falso) — é que o Vectora compartilha a MESMA
sessão de terminal (não cópia read-only) e unifica 9 tabs sob um único
contrato de evento tipado, enquanto o Hermes tem os componentes mas espalhados
em mecanismos de sync diferentes (IPC, REST de plugin, buffer de xterm).

**Recomendações**:

1. Reposicionar o discurso de "shared workbench" com a formulação mais precisa acima — esforço baixo (só copy).
2. **Concorrência de escrita no terminal — investigado**: `PtySession.write()` (`backend/services/pty_session.py:213`) é síncrono sem lock explícito, mas roda dentro do único event loop asyncio do processo — GIL + loop único evitam corrupção de baixo nível em cada chamada individual. Risco residual real, porém baixo: não há fila que agrupe os múltiplos `write()` de um comando do agente como unidade lógica — se o usuário digitar no meio dessa sequência, os bytes podem intercalar. Considerar fila de escrita só se algum bug real de intercalação for reportado, não preventivamente.
3. Avaliar "kanban por subagente" (lanes by profile) se subagentes ganharem peso — médio-alto esforço.
4. **Profundidade da tab `browser` — confirmada**: `frontend/components/workbench/tabs/browser-tab.tsx` tem `TabState` com `history`/`historyIndex`/`canGoBack`/`canGoForward` por aba, multi-tab real tanto em desktop (`WebContentsView`) quanto web — a alegação da tabela acima já estava correta, sem gap a fechar aqui.
5. **Drag-and-drop pra mover arquivo no Filesystem — não existe** (`frontend/components/workbench/files/files-tab.tsx`, zero `onDrop`/`draggable`) — vira sprint de UX fix no plano de desenvolvimento.

---

## 9. Features do Vectora que valeriam ser propostas ao Hermes

**Ressalva de honestidade**: a base de issues do Hermes investigada nesta
sessão foi pequena (só 2 filtros de busca, `P1`+`area/auth` e
`type/feature`, ~100 issues no total) — não é leitura robusta o bastante do
roadmap completo do concorrente pra ser tratada como conclusiva. Esta seção
lista capacidades que o Vectora já tem, de nível maduro, que fariam sentido
como sugestão de contribuição/PR pro Hermes (produto MIT, aberto a PRs
externos) — não é o inverso (o que o Hermes está construindo, isso já está
mapeado nas seções 1 e nas tabelas de cada área acima).

- **Sandbox com isolamento real a nível de SO** (bwrap+seccomp+Landlock(egress
  V4)+rlimits no Linux, Seatbelt no macOS, Singularity) — o Hermes hoje só
  isola via Docker/terceiros, com a própria doc admitindo "só o SO é
  fronteira". É a lacuna mais séria e mais madura do Vectora pra oferecer de
  volta — reduziria o gap de segurança do concorrente sem exigir reescrever
  a arquitetura dele (o padrão bwrap+Landlock é replicável em qualquer
  produto Python/Node que rode em Linux).
- **RAG + Context Graph nativos** — o Hermes terceiriza 100% memória/busca a
  plugins de terceiros (mem0, Honcho, hindsight); nunca teve intelligence de
  código nativa (tree-sitter, GraphRAG). Contribuir a ideia (não o código —
  arquiteturas de storage são diferentes) de um provider nativo opcional
  seria o maior ganho de capacidade "out of the box" que o Hermes poderia
  herdar.
- **Filesystem compartilhado com edição real** (Monaco embutido, conflito
  otimista via `expected_sha256`/412) — o explorador de arquivos do Hermes
  hoje é só visualização; dar ao usuário edição direta pela UI (não só
  visualizar o que o agente fez) fecha uma lacuna de produto real dele.
- **Terminal literalmente compartilhado** (mesma sessão PTY entre usuário e
  agente) — o Hermes tem 2 terminais separados, um deles read-only; unificar
  numa sessão só reduziria a divergência de estado que dois terminais
  paralelos naturalmente criam.

---

## 10. O que o Vectora tem que o Hermes não tem (resumo, para não perder de vista)

- Context Graph / code intelligence nativo (tree-sitter ~30 linguagens, GraphRAG) — **ausência confirmada** no Hermes.
- RAG nativo com vector store próprio (LanceDB/Qdrant), cobrindo **código-fonte e documentos** (não só texto corrido — `backend/embedding/rag_ingest.py` tem atalho `file_types="code"` ao lado de `"markdown"`/`"all"`) mais um índice GraphRAG próprio dos nós do Context Graph (`backend/context_graph/graph_index.py`, mesmo pipeline de embedding, índice LanceDB dedicado) — Hermes terceiriza 100% a skills/plugins, sem RAG nativo de nenhum tipo.
- Consolidação de memória automática e versionada — Hermes só tem MEMORY.md/USER.md em prosa livre.
- Sandbox com isolamento real a nível de SO (seccomp/Landlock/Seatbelt) — Hermes documenta que só tem isolamento real via Docker/terceiros.
- RBAC granular de produto (4 papéis hierárquicos) — Hermes descartou deliberadamente essa complexidade.
- **Filesystem compartilhado com edição real** — o usuário cria, edita, deleta e move arquivos pela própria UI, com resolução de conflito otimista (`expected_sha256`/412) quando o agente edita por baixo; o Hermes só visualiza (explorador read-only).
- Terminal literalmente compartilhado entre usuário e agente (mesma sessão pty) — Hermes tem 2 terminais separados.
- **Browser compartilhado como navegador completo** — navegação livre pra qualquer URL http/https, multi-tab nativo, agente opera a mesma sessão Playwright/CDP que a UI observa; o Hermes é preview de dev server local, não navegador de internet.
- **Remember — síntese automática de skills e fatos via LLM**, com HITL obrigatório antes de persistir — comparável em espírito ao self-improvement loop/`/learn` do Hermes, não é só key-value.
- Contrato de streaming SSE com union discriminada Pydantic de 17 tipos — mais explícito que o vocabulário dataclass do Hermes.
- Kanban com 9 estados (vs 6) e budget de custo por run integrado.
- Discovery automatizado de registry MCP oficial com persistência.
- Catálogo de tools nativas maior em contagem (~163 vs ~125).
- Versionamento de skill/pacote (`package_name`/`version`) — já implementado, não é mais lacuna.
- Editor de arquivo Monaco real (não textarea) — IDE mode existe justamente pra isso.
- SSRF protection madura em `backend/tools/web.py` (`ssrf_guard.py`, com defesa contra DNS rebinding).
- Hardening real do sandbox Docker (`cap-drop`, `security-opt`, `pids-limit`, `read-only`) — paridade confirmada com o padrão do Hermes.
- Browser: multi-tab real com histórico por aba (`canGoBack`/`canGoForward`), tanto desktop quanto web.
