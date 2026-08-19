# Vectora — Backlog de Assimilação de Concorrentes

> **O que é este doc.** Uma lista **acionável** de features que valem a pena
> implementar no Vectora, destiladas das notas de lançamento de concorrentes
> diretos (não guardamos as release notes em si — guardamos a decisão). Cada
> item traz: **o que é**, **por que faz sentido pro Vectora**, **como
> implementar** (ancorado no nosso stack real) e **esforço/dependências**.
>
> **Índice/análise** de concorrência vive em
> [`market-and-positioning.md`](./market-and-positioning.md) (seção "Radar de
> assimilação"). Este doc é o backlog técnico que aquele radar aponta.
>
> **Norte inegociável: workspace compartilhado.** O diferencial estrutural
> do Vectora é usuário e agente operando nas mesmas superfícies
> (filesystem, git, terminal, browser, RAG) — RAG híbrido + Context Graph
> são capacidades centrais desse workspace, com a **Library** como pilar
> de aquisição, não o pitch primário (RAG é replicável por qualquer
> concorrente que invista nisso; o workspace não é). Tudo aqui é
> **paridade secundária** — só entra se não competir com o tempo do
> workspace/Library. Features marcadas 🎯 **reforçam** o norte (ligam
> direto em RAG/memória/workspace) e têm prioridade sobre as demais.
>
> **Regra anti-Devin.** Qualquer feature de escala (swarm, orquestração,
> background pesado) entra **com HITL e workspace visível**. Escala sem
> supervisão é anti-positioning.
>
> **Fontes:** CHANGELOG/docs oficiais do Hermes Agent (Nous Research, v0.18.0,
> jul/2026) e do Paperclip (paperclipai, MIT, 2026). Reavaliar a cada release
> relevante.

---

## Hermes Agent (Nous Research) — self-hosted, self-improving

### H-0. Os 6 pilares da home (hermes-agent.nousresearch.com) — o que é cópia de verdade

A home do Hermes resume o produto em 6 blocos de marketing. Os nomes de
sprint do Vectora (#211-#216) usaram os mesmos rótulos, o que sugeria cópia
dos 6 — **não é o caso**. Auditoria real via agentes de exploração em
2026-07-29 (código, não nome de task): só **Remember** e **Connect** são de
fato inspirados no Hermes. Search, Schedule, Delegate e o sandbox (rotulado
"Experiment") já existiam no Vectora com implementação própria, anterior a
qualquer leitura do Hermes — Schedule/Delegate com nomes internos diferentes
("Background Tasks"/tools `schedule_task`+`task()`), o sandbox é baseado no
`ai-jail` do Akita (não no Hermes, que nem documenta a própria sandbox em
detalhe equivalente).

| #   | Pilar (Hermes)                                                 | É cópia do Hermes?                      | Estado real no Vectora (auditado 2026-07-29)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --- | -------------------------------------------------------------- | --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Connect** — Telegram/Discord/Slack/WhatsApp/Signal/Email/CLI | **Sim**                                 | Implementado em `backend/services/connect/`: Telegram (long polling, `python-telegram-bot`), Discord (WebSocket Gateway, `discord.py`), Slack (**Socket Mode** via `slack_bolt`, não Events API) e Email (**IMAP polling + SMTP direto**, stdlib). As 4 são conexões _outbound_ — nenhuma exige IP público, domínio ou túnel pelo gateway. `messaging.py` seguiu como a abstração comum; os adapters só traduzem formato e `connect/runner.py` resolve thread + roda o agente. Mapeamento persistido em `connect_thread_mappings`. Credencial por instalação (bot próprio do usuário), nunca bot central. WhatsApp/Signal/CLI ficaram de fora por decisão — no Hermes dependem de bridge Node/Baileys e do daemon não-oficial `signal-cli`.                                                                                                                                                                                                         |
| 2   | **Remember** — memória persistente, skills auto-geradas        | **Sim**                                 | Real, mas mais enxuto que o design (H-1 abaixo): `backend/tools/learning.py` + `backend/services/learning.py` + `backend/services/remember_trigger.py` — gatilho automático a cada 5 turnos (`REMEMBER_TRIGGER_EVERY_N_TURNS`, fire-and-forget em `api/adapters.py`), destila via LLM, propõe skill/fato como artifact na aba Plan, HITL real antes de persistir (`save_learned_fact`/`install_learned_skill`). O painel "o que aprendi sobre você" existe (`GET /memory/journey` + seção no Memory tab). **Não existem** `/learn` (a tool `learn_from_session` cobre a mesma função com outro nome), `/journey` como comando de chat (virou painel), nem job via NATS `vectora-jobs`.                                                                                                                                                                                                                                                              |
| 3   | **Schedule** — agendamento em linguagem natural                | **Não** — Vectora já tinha antes        | Implementado de ponta a ponta: `backend/scheduling/background_tasks.py` (loop asyncio, tick 60s, `croniter`) + `backend/scheduling/nl_schedule.py` (`parse_natural_schedule` — regex determinístico em pt/en/es, não LLM; o Hermes delega essa conversão ao próprio LLM da conversa, mais flexível a qualquer idioma mas menos testável) + tool `schedule_task` (`backend/tools/background.py`) + endpoints `backend/api/handlers/background.py` + aba "Tarefas" no frontend (`tasks-tab.tsx`). Funcional, não stub. Ganhou timezone do usuário (`user_timezone`), quota por workspace e catch-up com janela de tolerância — tarefa `interval` muito atrasada pula pro próximo ciclo em vez de disparar retroativamente; `once` nunca é pulada.                                                                                                                                                                                                     |
| 4   | **Delegate** — subagentes isolados, worktree-per-task          | **Não** — Vectora já tinha antes        | Delegação vem do motor nativo (`backend/engine/subagents.py`, chamado por `agent_factory.py`) — cada subagente é uma instância nova de `run_conversation` com `SessionStore` thread própria, sem depender de `deepagents`/LangGraph; worktree-per-task é real (`backend/scheduling/delegate.py`) e cobre background tasks tipo `coder`; a delegação síncrona roda no workspace principal **por design** (não é trabalho paralelo, é troca de persona no mesmo turno) — há teste travando esse invariante. Achado da auditoria do código do Hermes: lá `delegate_task` é chamada LLM recursiva em `ThreadPoolExecutor`, **sem worktree nenhum** (o worktree do Hermes é flag de sessão inteira, `hermes -w`), então o Vectora supera o Hermes aqui em vez de alcançá-lo. Terminal isolado por subagente não existe como feature própria. Nome interno real: "Background Tasks"/"tarefas em segundo plano", não "Delegate" como produto.              |
| 5   | **Search** — busca web, browser, visão, geração de imagem, TTS | **Não** — Vectora já tinha antes        | Busca web (Tavily + fallback DuckDuckGo/Playwright) e browser automation (Playwright multi-aba) — completos e robustos. Visão — real: bloqueio explícito pra Cohere/Ollama (sem multimodal); pra OpenRouter, a capability é checada por modelo via `architecture.input_modalities` do catálogo público da OpenRouter, não um bloqueio de provider inteiro. Geração de imagem e TTS existem em `backend/tools/media.py` (`generate_image`/`text_to_speech`), resolvidas pelo provider **ativo da sessão** via `PROVIDER_CAPABILITIES` — se o modelo escolhido não suporta, a tool avisa e **nunca** desvia pra outro provider por conta própria (chamaria e cobraria uma API que o usuário não pediu). Browser: o Vectora vai além do Hermes — observabilidade nativa inspirada no `chrome-devtools-mcp` sobre Playwright+Chromium direto, enquanto o Hermes chama um binário CLI proprietário (`agent-browser`) que esconde o Playwright do agente. |
| 6   | Sandbox (rotulado "Experiment") — isolamento de execução       | **Não** — baseado no `ai-jail` do Akita | `backend/sandbox/`: 4 backends reais (`local` via bwrap+Landlock+seccomp+rlimits, `docker`, `ssh`, `modal`) — **Singularity nunca foi implementado** (só citado num teste como nome arbitrário de backend desconhecido). `local` é o mais completo (e supera o `local` do Hermes, que é `subprocess.Popen` puro, sem isolamento nenhum); `docker` ganhou cap-drop ALL, no-new-privileges, tmpfs e limites de cpu/memória/PIDs **condicionais a haver cgroup delegado** — aplicá-los cegamente impede o container de subir em LXC não-privilegiado, lição tirada do `docker.py` do Hermes. `modal` tem teto de cpu/memória por perfil. WSL2 é o mecanismo que faz `local` funcionar no Windows, não um backend separado. Existe teste de escape real contra bwrap de verdade (Linux-only, com skip-guard) — o Hermes não tem equivalente.                                                                                                            |

Os itens H-1/H-2/H-3 abaixo vêm de uma leitura mais funda do changelog/docs
do Hermes (não da home) — H-1 mapeia pro pilar Remember; H-2 (proxy
OpenAI-compatível) e H-3 (worktree-per-task, que na prática o Vectora já
tinha antes via git worktree próprio) não têm cópia 1:1 confirmada — H-2
**nunca foi implementado** (nenhum endpoint `/v1/chat/completions` no
backend).

---

### H-1 🎯 Learning loop: skills auto-geradas + modelo do usuário

**O que é.** O maior diferencial do Hermes é o "built-in learning loop": ele
cria skills a partir da experiência, refina-as durante o uso e constrói um
modelo de quem é o usuário ao longo das sessões (workflows `/learn` e
`/journey`).

**Por que pro Vectora.** Liga direto no nosso norte: skills e memórias
destiladas viram **contexto recuperável** (RAG/BaseStore). É o que transforma
"agente com memória" em "agente que fica melhor com você" — sem depender de
fine-tuning, coerente com multi-LLM.

**Como implementar.**

- **Gatilho.** Comando `/learn` no chat + job pós-sessão opcional (enfileirado
  no NATS `vectora-jobs`, ver `backend/scheduling/mq.py`/`services/jobs.py`).
- **Destilação.** Um subagent/reflexão lê o transcript da thread
  (`SessionStore` nativo) e produz duas saídas via `response_format`:
  1. **Skills reutilizáveis** → grava `SKILL.md` em
     `~/.vectora/skills/{user_id}/` (formato que já carregamos on-demand pelo
     motor nativo). Dedup por similaridade de embedding contra as skills
     existentes antes de gravar (usa o próprio pipeline de embeddings).
  2. **Fatos duráveis sobre o usuário** → `save_memory` (`ctx.store`, o
     `StoreBackend` do `CompositeBackend`), com tag `user_model`.
- **Painel "o que aprendi sobre você".** `GET /memory/journey` cruza os fatos
  com tag `user_model` no BaseStore com as skills de `source="learning-loop"`;
  o Memory tab do workbench renderiza a lista, só leitura. Substitui o comando
  de chat `/journey` do design original — o painel é sempre visível, não
  depende de o usuário saber o nome de um comando.
- **HITL obrigatório.** Nada é persistido sem o usuário revisar num diff
  ("aprendi X sobre você / criei a skill Y — salvar?"). Opt-in por padrão.
- **Fecha o ciclo com RAG.** Skills e memórias entram no retrieval, então a
  próxima sessão já recupera o aprendizado.

**Esforço.** Alto. **Dependências:** skills system (existe), BaseStore
(existe), embedding queue (existe), jobs NATS (existe). **Risco:** qualidade
da destilação — precisa de eval (ver `testing-guide.md`).

---

### H-2. Proxy OpenAI-compatível (`/v1/chat/completions`)

**O que é.** O Hermes expõe um proxy local OpenAI-compatível que transforma
qualquer provider autenticado num endpoint que Codex/Aider/Cline/Continue
conseguem consumir.

**Por que pro Vectora.** Vira ponte reversa: ferramentas de terceiros passam a
falar com o Vectora (roteando pro nosso multi-LLM + RAG) sem depender de MCP.
Amplia superfície de integração sem lock-in.

> **Atenção ao propor.** A API pública `/v1/*` (extract/classify/jobs) foi
> removida por completo — sem autenticação de terceiros real, sem SDKs, sem
> tração. A decisão foi não sustentar meio-caminho: qualquer API pública
> futura, incluindo esta, precisa nascer com autenticação de verdade
> (API key/OAuth2 client_credentials) desde o design, não reaproveitar o
> prefixo `/v1` nem a fundação abandonada.

**Como implementar.**

- Novo router `backend/api/handlers/openai_compat.py` montado sob `/v1`:
  `POST /v1/chat/completions` + `GET /v1/models` (lista os modelos com chave
  configurada, mesma fonte do seletor do chat).
- **Dois modos** (query/header `X-Vectora-Mode`): `raw` (passthrough ao LLM
  resolvido, sem agente — latência mínima, pra autocomplete/edits) e `agent`
  (roteia pelo motor nativo, `backend/engine/conversation_loop.py::
run_conversation`, ganhando RAG/tools). Default `raw`.
- **Tradução.** Request OpenAI → nossa resolução de provider
  (`FallbackChatClient`, resolvido por chamada — ver `agent_factory.py`).
  Streaming: reempacotar os chunks no formato `data: {...}\n\n` do OpenAI
  (adaptador irmão do `adapt_stream`).
- **Auth.** Reusa o middleware: Bearer com Vectora Token (Pro) ou usuário
  local. Rate-limit por tier (já temos `slowapi`).
- **Cuidado.** Não expor `agent` mode sem HITL desligado explicitamente —
  ferramentas externas não têm UI de aprovação; documentar que `agent` mode
  roda em permission mode restrito.

**Esforço.** Médio. **Dependências:** provider resolution (existe), auth
middleware (existe), SSE adapter (existe base).

---

### H-3. Worktree-per-task + override de modelo por task

**O que é.** No Kanban multi-agente do Hermes, a home/documentação falam em
task com **git worktree próprio** e **override de modelo por task**, mas a
auditoria do código real não confirmou o worktree por task: `delegate_task`
roda em `ThreadPoolExecutor`, no mesmo processo, sem isolamento de PTY. No
Vectora, o worktree por task em segundo plano já existe de verdade, então a
comparação útil aqui é só o override de modelo por task (quando houver
perfil/agente), não o worktree de marketing.

> **Correção (auditoria do código real, 2026-07-30).** A parte de "worktree por
> task delegada" **não se confirma no código do Hermes**: `delegate_task` é uma
> chamada LLM recursiva em `ThreadPoolExecutor`, mesmo processo, sem worktree
> nem PTY isolado. O worktree do Hermes é uma flag de **sessão inteira**
> (`hermes -w`), e o schema do kanban (`hermes_cli/kanban_db.py`) tem
> `workspace_kind`/`workspace_path`/`branch_name` por task — isto é, o worktree
> existe no **kanban**, não na delegação. O Vectora já tinha
> `create_task_worktree` para background tasks antes disso. O override de
> modelo por task segue válido como ideia não implementada.

**Por que pro Vectora.** Resolve a contenção real quando subagentes/tasks
editam arquivos em paralelo (hoje compartilham o working tree). Habilita o
"agent swarm sob HITL" do radar sem corromper o repo.

**Como implementar.**

- **Worktree por task.** Ao iniciar uma task que escreve arquivos, criar
  `git worktree add .vectora/worktrees/{task_id} <branch>`; o subagent opera
  ali. Na conclusão: PR (via `gh`) ou merge com HITL; limpar o worktree.
  Integra na aba **Tarefas** do workbench e nas git tools (`backend/tools/git.py`).
- **Override de modelo.** Adicionar `model` opcional ao registro da task e ao
  `ChatConfig`; `agent_factory` já resolve o `ChatClient` por chamada
  (`FallbackChatClient`) — reusar essa resolução pra rodar a task com o
  modelo escolhido em vez do modelo default da sessão. UI: seletor de modelo
  por task na aba Tarefas.
- **Concorrência.** Cada worktree = working tree isolado, então o lock do
  SQLite (D2, `busy_timeout`) já cobre o checkpointer compartilhado.

**Esforço.** Médio-alto. **Dependências:** Tarefas (existe), git tools
(existe), subagentes (existe). **Anti-Devin:** merge/PR sempre passa por HITL.

---

### H-4. Inventário de tools do Hermes — o que existe lá e não aqui

**Levantado na auditoria de código de 2026-07-29/30** (~70 tools no Hermes,
confirmadas contra `hermes-agent/`). Serve como mapa de candidatos, não
como lista de coisas a copiar: a maioria das categorias abaixo já foi
decidida (entrou no plano de sprints ou foi descartada com motivo).

**Categorias que o Hermes tem e o Vectora não tinha:**

| Categoria                 | No Hermes                                                                                                                                                                                                                                                                                                                         | Decisão pro Vectora                                                                                                                                                                                                                                                                               |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Kanban multi-agente       | `hermes_cli/kanban_db.py` — 7 status, `task_links` para dependências, claim atômico por CAS (`UPDATE ... WHERE status='ready' AND claim_lock IS NULL`), heartbeat que estende o TTL do claim, bloqueio tipado (`dependency`/`needs_input`/`capability`/`transient`). Filhos de `delegate_task` são **proibidos** de mutar o board | **Entregue** — `backend/scheduling/kanban.py` sobre o `background_tasks` existente, 9 estados (mais que os 6 do Hermes), prioridade/tenant/assignee no card, dependências com contagem N/M, comentários, timeline de eventos, filtros de topo; feature pública (flag `enableKanbanMode` removida) |
| Smart home                | 4 tools de Home Assistant via API REST                                                                                                                                                                                                                                                                                            | **Entregue** — `backend/tools/homeassistant.py`, `ha_call_service` marcada `destructive=True` (sempre HITL, age no mundo físico)                                                                                                                                                                  |
| Vídeo                     | `video_generation_tool.py` + `vision_tools.py::video_analyze`                                                                                                                                                                                                                                                                     | Planejado (Sprint 19), como extensão do capability matrix                                                                                                                                                                                                                                         |
| `computer_use`            | Controle de mouse/teclado do desktop                                                                                                                                                                                                                                                                                              | Planejado (Sprint 21) com o maior rigor do plano: HITL sempre, ignorando `permission_mode`, e opt-in explícito no `vectora.toml`                                                                                                                                                                  |
| Aprovação "inteligente"   | `tools/approval.py` — LLM auxiliar auto-aprova comandos reconhecidos, com allowlist persistente                                                                                                                                                                                                                                   | Planejado (Sprint 22), mas **mais conservador**: no Vectora o avaliador no máximo marca a sugestão como pré-aprovada; nunca pula o HITL sozinho                                                                                                                                                   |
| Mensageria além das 4     | 21 plataformas em `plugins/platforms/` (WhatsApp, Signal, Matrix, Teams, Feishu, WeCom, LINE, IRC, SMS, ntfy…)                                                                                                                                                                                                                    | Fora de escopo por ora — WhatsApp depende de bridge Node/Baileys e Signal do daemon não-oficial `signal-cli`, ambos de manutenção pesada                                                                                                                                                          |
| Singularity (sandbox HPC) | 268 linhas reais em `tools/environments/`                                                                                                                                                                                                                                                                                         | **Descartado** deliberadamente: nicho HPC, baixo valor pro público do Vectora. Registrado aqui para não voltar como "esquecimento"                                                                                                                                                                |

**Onde o Vectora já vai além do Hermes** (relevante para posicionamento, ver
`market-and-positioning.md`):

- **Sandbox `local`**: bwrap + Landlock LSM + seccomp-bpf + rlimits, contra
  `subprocess.Popen` puro no Hermes — lá o backend `local` não tem isolamento
  nenhum. O Vectora também tem teste de escape real; o Hermes não.
- **Browser**: observabilidade nativa inspirada no `chrome-devtools-mcp` sobre
  Playwright+Chromium direto, contra um binário CLI proprietário
  (`agent-browser`) que esconde o Playwright do agente e não expõe network
  log/heap snapshot/tracing.
- **HITL de memória**: o Hermes grava skills/memória **sem aprovação por
  padrão** (`skills.write_approval: false`); no Vectora `install_learned_skill`
  e `save_learned_fact` sempre pausam.
- **Delegação isolada**: ver a correção em H-3 acima.

---

## Paperclip (paperclipai) — orquestração de times de agentes

### P-1 🎯 Biblioteca de artefatos do workspace (indexada em RAG)

**O que é.** "Company Artifacts": tudo que os agentes produzem (arquivos,
mídia, docs) é **indexado numa página com escopo da empresa**, pesquisável.

**Por que pro Vectora.** Vale copiar a **forma** — feed unificado de outputs
do workspace, agrupável por task, com preview — não a mecânica: o Paperclip
não tem embeddings nem vector store, é agregação relacional (docs + work
products + attachments) com busca fuzzy via Postgres trigram, não RAG
semântico. No Vectora essa biblioteca de artefatos se conectaria à
**rag-library** de verdade (embedding real), unindo o que já temos solto:
`create_artifact`, a aba Plan e o RAG.

**Como implementar.**

- **Auto-index.** Hook em `create_artifact` e nas escritas de arquivo
  (`file_write`/`file_edit`) → enfileira job de embedding (fila
  `embedding_queue.db` já existente) com metadados `{workspace_id, kind,
source}`. Escopo de workspace no filtro do retriever.
- **Biblioteca.** Nova seção "Biblioteca" no workbench (ou expandir a aba
  Plan): lista os artefatos do workspace, com **busca RAG** (reusa o Memory
  tab / `vector_search` filtrado por `workspace_id`).
- **Governança.** Respeita `.vectoraignore` (não indexar segredos) e o RBAC
  (viewer lê, member cria).
- **Ponte pra rag-library.** Quando a rag-library existir, esta biblioteca
  vira o front-end natural dela — exportável/compartilhável entre workspaces.

**Esforço.** Médio. **Dependências:** embedding queue (existe), artifacts
(existe), RAG scoping por workspace (parcial). **Prioridade alta** (norte).

---

### P-2. Governança de agentes: budgets + goals + org

**O que é.** Paperclip modela agentes como **funcionários num org chart** —
papéis, linhas de reporte, **budgets** (teto de custo), heartbeats e
governança; cada agente tem **goal** e orçamento rastreados num dashboard.

**Por que pro Vectora.** Fortalece a história **Pro/Enterprise** (chat web
multi-usuário + RBAC já existe). Dá ao admin controle de custo real — algo que
nenhum concorrente local-first entrega junto com RAG.

**Como implementar.**

- **Budgets.** Tabela `agent_budgets` (SQLite — auth/config sempre em SQLite):
  teto de tokens/custo por usuário e por workspace, janela (dia/mês). Antes de
  cada chamada LLM, checar saldo (o tracking de uso já existe em
  `usage.ts`/usage-popover); bloquear ou avisar ao estourar. Endpoint admin
  `PATCH /admin/budgets`.
- **Goals.** Objetivo persistente por sessão/agente (campo em
  `RuntimeSettings.frontend_prefs` ou tabela dedicada), exibido no topo do
  workspace — o agente lê como contexto de sistema.
- **Org.** O org chart = os roles RBAC (root/admin/member/viewer) que já
  temos + uma view no painel Admin (quem reporta a quem, quem gasta quanto).
- **Escopo.** Feature de modo servidor/VPS (multi-usuário); no local (1
  usuário) é só o teto de custo pessoal.

**Esforço.** Médio-alto. **Dependências:** RBAC (existe), tracking de uso
(existe), painel Admin (existe). **Nota:** não virar "zero-human company" —
governança é pra **dar controle ao humano**, não removê-lo.

---

### P-3. Gates automáticos de qualidade/segurança em PR

**O que é.** Paperclip roda **quality e security gates automáticos** antes de
PRs seguirem.

**Por que pro Vectora.** Fecha o loop do fluxo de código com confiança — o
agente não abre PR sem passar no crivo. Coerente com "auditável".

**Como implementar.**

- Reusar o **sistema de hooks** (Frente B, já feito: pre/post tool). Um
  **post-tool hook** em `gh_pr_create` dispara: `scons lint` do subprojeto
  afetado + scan de segredos (detect-private-key/bandit) + `scons tests`
  direcionado. Resultado vira comentário no PR via `gh` e/ou bloqueia o merge.
- Config por workspace (`.vectora/gates.toml`): quais gates rodam, bloqueante
  vs. aviso.
- Ganho extra: expõe como **skill** (`SKILL.md`) reutilizável — casa com H-1.

**Esforço.** Médio. **Dependências:** hooks (existe), git/gh tools (existe),
scons (existe).

---

### P-4. Ticketing com heartbeats + triggers (@-mention / assignment)

**O que é.** Agentes rodam em **heartbeats agendados** e **triggers por
evento** (atribuição de task, `@-mention`); tickets com org/delegação.

**Por que pro Vectora.** Evolução natural da aba **Tarefas** (cron + webhook
já existem) para um modelo de tickets com delegação humano↔agente — útil no
chat web multi-usuário.

**Como implementar.**

- Tabela `tickets` (status, assignee = usuário **ou** subagent, prioridade,
  trigger). A aba Tarefas vira um **Kanban** (colunas por status).
- **Heartbeat** = o scheduler cron que já temos "cutuca" tickets abertos.
- **Trigger por @-mention** = detectar `@agent`/`@user` no chat → cria/atribui
  ticket; **assignment** dispara um job NATS que roda o trabalho (worktree do
  H-3 se envolver código).
- **HITL** na entrega: ticket concluído por agente entra em "Revisão" antes de
  fechar, nunca auto-fecha mudança de código.

**Esforço.** Médio-alto. **Dependências:** Tarefas (existe), NATS jobs
(existe), chat @-mentions (Frente B parcial). Depende idealmente do H-3.

---

## Claude Code / Anthropic Platform (jul/2026)

> Destilado do CHANGELOG do Claude Code (série 2.1.x) e das release notes da
> Claude Platform/API. Anthropic é **um** provider no nosso multi-LLM — então
> assimilamos os **padrões** (não a API específica), garantindo fallback para
> providers que não suportem.

### C-1 🎯 Memória hierárquica navegável (paths/depth)

**O que é.** O memory tool da Anthropic evoluiu para **memory stores
hierárquicos**: memórias organizadas por caminho (`path_prefix`), listáveis
com profundidade limitada (`depth`) e ordem estável.

**Por que pro Vectora.** Nosso `save_memory`/`get_memory` hoje é
chave-valor plano. Caminhos (`projeto/decisões/…`, `usuário/preferências/…`)
dão memória **navegável, escopável por workspace/usuário e recuperável** —
upgrade direto do `StoreBackend` nativo e destino natural do que o H-1 destila.

**Como implementar.**

- O `StoreBackend` nativo (`backend/storage/protocols.py`) já suporta
  **namespace em tupla** + `key` — usar a tupla como segmentos de path. Nada
  de schema novo no lite (SQLite) nem no complete (Postgres/Qdrant).
- Nova tool `list_memory(path_prefix, depth)` + `save_memory(path=..., ...)`;
  o Memory tab do workbench ganha uma **árvore** navegável.
- Migração: memórias planas atuais → path `default/`.
- Fecha com RAG: paths viram filtros de retrieval (memória escopada por
  projeto entra no contexto certo).

**Esforço.** Médio. **Dependências:** `StoreBackend` (existe, já tem
namespaces), Memory tab (existe).

### C-2. `response_inclusion`: higiene de contexto nas web/RAG tools

**O que é.** As web search/fetch tools ganharam `response_inclusion` para
**dropar do contexto os result blocks já consumidos** — economiza token em
loops agenticos longos.

**Por que pro Vectora.** Em sessão longa, resultados antigos de web/RAG
incham o histórico e desfocam o modelo. Barato e alto valor.

**Como implementar.**

- Nas tools `backend/tools/web.py` e nas de RAG: depois que um resultado é
  citado numa resposta, **compactar** o bloco bruto no histórico deixando só
  a citação `[N]` + fonte (a resposta segue auditável, o contexto encolhe).
- Roda como etapa do motor nativo (`backend/engine/conversation_loop.py`),
  não um middleware externo — ainda não existe compaction de contexto no
  engine hoje, esta é a primeira. Opt-in, ligado por padrão em execuções
  longas/background.

**Esforço.** Médio. **Dependências:** web/RAG tools (existem), compaction de
contexto no motor nativo (não existe ainda).

### C-3 🎯 Hook `post-session`

**O que é.** Lifecycle hook que roda **após a sessão concluir**, antes de
limpar o workspace.

**Por que pro Vectora.** É o **gatilho canônico do H-1** (destilar
skills/memória ao fim da sessão) e também serve auto-commit, telemetria e
cleanup.

**Como implementar.**

- Estender o sistema de hooks (Frente B, já feito: pre/post tool) com o ponto
  `post-session`, disparado no encerramento da thread (`/end`, idle timeout ou
  fechar a sessão). Roda hooks de `.vectora/hooks/` (shell/skill).
- O H-1 registra aqui um hook que enfileira o job de destilação (NATS).

**Esforço.** Baixo-médio. **Dependências:** hooks (existe), jobs NATS (existe).

### C-4. Sandbox de código stateful (REPL) + programmatic tool calling

**O que é.** O code execution tool ganhou **estado de REPL persistente** entre
chamadas e **programmatic tool calling** (o agente escreve código que
orquestra várias tools de uma vez).

**Por que pro Vectora.** Complementa o PTY (shell interativo) com um REPL de
linguagem **com estado** — ideal para análise de dados/RAG: manter dataframes
e variáveis entre passos sem re-executar tudo. Programmatic calling reduz
overhead quando são muitas tool calls.

**Como implementar.**

- Kernel Python persistente por sessão (`thread_id` → namespace vivo), tool
  `code_exec(code)` que preserva o estado entre chamadas. Isolar: só em
  workspace **confiado**, timeout por célula, **sem acesso a credenciais**
  (espelha `sandbox.credentials` do Claude Code).
- Distinto do terminal (PTY): este é REPL de linguagem, não shell.
- Anti-Devin: efeitos colaterais (escrita/rede) passam por HITL.

**Esforço.** Alto. **Dependências:** workspace trust (existe), infra de
sandbox/jobs. **Risco:** segurança do sandbox — avaliar isolamento (subprocess

- limites de OS) antes.

### C-5. Lista de bloqueio no permission mode (comandos irreversíveis)

**O que é.** O auto mode do Claude Code **bloqueia git/IaC destrutivos**
(`push --force`, `reset --hard`, `terraform destroy`) sem pedido explícito,
mesmo em modo autônomo.

**Por que pro Vectora.** Fecha nossos modes `auto`/`bypass` com rede de
segurança — assimila a escala **sem virar Devin**. Hoje o `auto` não pausa
nada; uma denylist de comandos irreversíveis é o meio-termo.

**Como implementar.**

- No middleware HITL: além dos modes, uma **denylist de padrões** que
  **sempre** exigem confirmação, mesmo em `auto` (`git push --force`,
  `git reset --hard`, `rm -rf`, `terraform destroy`, `DROP TABLE`, etc.).
- Classificador leve nos tools `terminal`/git antes de executar; config em
  `.vectora/gates.toml` (reusa o arquivo do P-3).

**Esforço.** Médio. **Dependências:** HITL middleware (existe), permission
modes (existem).

### C-6. System message mid-sessão preservando prompt cache

**O que é.** O Opus 4.8 aceita mensagens `role: "system"` **no meio** da
conversa, mudando instruções sem invalidar o prompt cache.

**Por que pro Vectora.** Sessões longas (workbench aberto horas) mudam
contexto (troca de workspace, skill nova, permission mode) — hoje isso pode
invalidar o `cache_llm`. Injetar a mudança mid-sessão mantém o cache hit e
reduz custo/latência.

**Como implementar.**

- No motor nativo (`backend/engine/conversation_loop.py::run_conversation`),
  quando o contexto de sistema muda no meio da sessão, inserir um bloco
  `system` **no meio** do array em vez de reconstruir o system prompt no
  topo.
- Depende de suporte do provider (Anthropic sim); **fallback** para providers
  sem suporte = rebuild no topo (degrada só o cache, não a correção).

> **Correção.** O `cache_llm`/`native_redis_cache` (cache global de resposta
> LLM via `langchain_core.caches.BaseCache`) foi removido por completo
> (commit `23c19d55`) — não tinha consumidor de produção desde o corte do
> dispatch pro `ChatClient` nativo. Este item não depende mais dele: o
> "prompt cache" aqui é o cache **do lado do provider** (ex. prompt caching
> da Anthropic), não um cache local do Vectora — não há mecanismo próprio a
> integrar, só a ordem dos blocos da mensagem enviada ao provider.

**Esforço.** Médio. **Dependências:** motor nativo (existe), capability do
provider (parcial).

---

## Filtro de conteúdo: o Vectora não tem, por decisão

O Vectora não implementa nenhum filtro de conteúdo: não há lista de palavras,
não há classificador de saída, e nenhum system prompt (`backend/agents/
_identity.py`, `coder.py`, `search.py`, o prompt do orchestrator em
`backend/services/agent_factory.py`) instrui o agente a recusar assunto
nenhum. Os únicos bloqueios do código são de **execução** — comandos de
terminal perigosos em `backend/tools/fs.py` — e não têm relação com o que o
modelo escreve.

A censura que um usuário eventualmente encontra vem do **modelo escolhido**,
não do produto. Gemini, OpenAI, Anthropic e Cohere aplicam as próprias
políticas do lado deles. Onde o provider deixa configurar isso, o Vectora
manda o threshold mais permissivo — é o caso do Gemini, via
`_gemini_safety_settings()` em `backend/services/utils.py`; parte das
categorias o Google não permite desligar, e isso é limite da plataforma.
Ollama e OpenRouter, os caminhos para modelos sem censura, não têm filtro
nenhum no percurso.

Isto está registrado aqui porque a **ausência** de guardrail se parece com
lacuna numa auditoria rápida — e já foi tratada como tal antes. Há teste
travando o invariante (`tests/unit/test_no_content_guardrails.py`), com um
caso que planta uma instrução de recusa e exige que o detector a acuse, para
que o teste de ausência não passe trivialmente.

Para referência: o Hermes também não tem guardrail de conteúdo no core, e vai
além — distribui em `optional-skills/security/godmode/` uma skill opt-in cujo
propósito declarado é contornar os filtros de provedores terceiros.

## Priorização sugerida (impacto × proximidade do norte)

1. **P-1** 🎯 Biblioteca de artefatos indexada — semente da rag-library.
2. **H-1** 🎯 Learning loop — skills/memória auto-melhoráveis.
3. **C-1** 🎯 Memória hierárquica (paths/depth) — upgrade do BaseStore, base do H-1.
4. **C-3** 🎯 Hook `post-session` — gatilho canônico do H-1 (barato, destrava).
5. **P-3 + C-5** Gates de PR + denylist de comandos irreversíveis — baratos,
   reusam hooks/HITL, fecham o fluxo com segurança.
6. **C-2** `response_inclusion` — higiene de contexto, barato, melhora loops.
7. **H-2** Proxy OpenAI-compatível — amplia integração sem lock-in.
8. **H-3** Worktree-per-task — destrava swarm/paralelo com segurança.
9. **P-4** Ticketing/heartbeats — depende do H-3.
10. **C-4** REPL sandbox stateful — capacidade nova, exige análise de segurança.
11. **C-6** System message mid-sessão — economia em sessão longa (Anthropic-first).
12. **P-2** Governança/budgets — feature Enterprise, modo servidor.

> Tudo **pós-1.0** salvo os baratos (P-3, C-5, C-3) — a rag-library tem
> precedência sobre qualquer item que compita pelo mesmo tempo de engenharia.

## Fontes

- Hermes Agent (Nous Research) — releases/changelog/docs, v0.18.0 (jul/2026):
  `github.com/NousResearch/hermes-agent`, `hermes-agent.nousresearch.com/docs`.
- Paperclip (paperclipai) — repo/docs (MIT, 2026):
  `github.com/paperclipai/paperclip`, `paperclip.ing`.
- Claude Code — CHANGELOG (série 2.1.x):
  `github.com/anthropics/claude-code/blob/main/CHANGELOG.md`.
- Claude Platform / API — release notes:
  `platform.claude.com/docs/en/release-notes/api`.
- Consultado em jul/2026. Confirmar detalhes de API antes de implementar (as
  release notes evoluem). Nota: features da Anthropic são assimiladas como
  **padrões** (multi-LLM), com fallback para providers que não suportem.

---

## Auditoria comparativa de tooling — Hermes Agent vs Vectora (02/08/2026)

Esta seção registra uma comparação direta do código-fonte local do Hermes Agent
(`C:\\Users\\Machi\\AppData\\Local\\hermes\\hermes-agent`) com o Vectora,
sem tratar nomes de módulos internos como ferramentas de produto.

> **Atualização.** O servidor MCP embutido do Vectora (`/mcp` como protocolo
> FastMCP exposto a harnesses externos) foi removido — o Vectora consome
> servidores MCP externos (`backend/tools/mcp.py`, marketplace de conectores),
> mas não expõe mais a si mesmo como servidor MCP.

### Dependências do Hermes que merecem avaliação no Vectora

O Hermes separa dependências core de extras opcionais; o Vectora não deve copiar
esse conjunto inteiro para as dependências obrigatórias. Os itens com valor
claro para o produto são:

- `youtube-transcript-api`: transcrição de vídeos do YouTube, hoje oferecida
  pelo Hermes como skill `youtube-content`, não como tool core. No Vectora,
  deve entrar como capability explícita de mídia/conteúdo, com URL/ID validado,
  retorno estruturado e tratamento de transcript indisponível.
- `faster-whisper`: STT local; complementa o STT remoto já existente e evita
  enviar áudio para um provider quando o usuário escolhe processamento local.
  Deve ser opcional, pois adiciona wheels grandes e runtime/modelos locais.
- `audioop-lts`: compatibilidade de processamento de áudio em Python moderno;
  avaliar somente se o caminho local de STT realmente precisar dele.
- `google-api-python-client`: só vale para integrações Google adicionais que
  não sejam cobertas pelo cliente atual de Drive/Gmail; não adicionar apenas
  por paridade de manifesto.
- `slack-sdk` e extras de voz/webhook dos adapters: revisar se algum fluxo do
  Connect do Vectora usa APIs ausentes no `slack-bolt` atual; não duplicar
  Socket Mode sem necessidade.
- `Pillow`: já existe no Vectora e cobre a parte de normalização de imagens.
  `pyautogui-next`, Playwright e MCP também já existem; o gap de `computer_use`
  é de superfície e segurança, não de dependência básica.

### Capacidades funcionais presentes no Hermes e ausentes ou incompletas no Vectora

A lista abaixo exclui helpers internos, APIs do próprio Hermes e ferramentas
que o Vectora já possui com nome diferente. Ela é o backlog funcional real,
não uma instrução para implementar tudo imediatamente.

#### Comunicação e ciclo de vida

- `send_message`: enviar mensagem proativamente para um canal/contato já
  configurado, incluindo listagem de destinos, thread/reação e mídia. O Vectora
  possui adapters Connect e tools de Slack, mas não possui uma tool genérica
  equivalente para entrega proativa multi-plataforma.
- `channels_list`, `conversations_list`, `conversation_get`, `messages_read` e
  `messages_send`: inspeção e operação genérica sobre conversas do gateway.
  O Vectora possui Connect por plataforma, porém não uma camada unificada de
  consulta/envio equivalente.
- `react_to_message`: reação em mensagens recebidas. Não há equivalente
  genérico no conjunto atual de tools do Vectora.
- `events_poll`/`events_wait`: espera por eventos de gateway para workflows
  longos. O Vectora tem eventos/SSE internos, mas não expõe essa espera como
  capability geral do agente.

#### Terminal e processos

- `read_terminal`: leitura do conteúdo corrente de uma sessão PTY.
- `terminal` com ciclo de vida completo de background: criação com ID,
  `poll`/`log`, envio de stdin, `submit`, `close` e `kill` como operações
  distintas. O Vectora possui sessões de terminal, mas a superfície não é
  equivalente em completude e precisa de uma auditoria específica antes de
  ser considerada paridade.
- seleção de backend de terminal e consulta de backends disponíveis
  (`select_terminal_backend`, `get_terminal_backends`), incluindo políticas de
  ambiente remoto/VM/container expostas ao agente.

#### Áudio, vídeo e conteúdo externo

- STT unificado (`transcribe_audio`) com backends local `faster-whisper`,
  OpenAI/Groq/Mistral/xAI/ElevenLabs/DeepInfra e providers por plugin. O
  Vectora tem caminhos de transcrição por provider, mas não o registry local +
  command-provider do Hermes.
- transcript de YouTube via skill dedicada (`youtube-content`), com extração
  de transcript e workflows de resumo/thread/blog.
- configuração de voz contínua/wake-word (`voice_mode`, `wake_word`) e TTS
  streaming. O Vectora tem TTS, mas não o loop de voz/wake-word completo.
- fontes de imagem e recuperação/redimensionamento de imagem (`image_source`)
  como camada explícita de ingestão multimodal.

#### Infraestrutura de ferramentas e governança

- `tool_search`/registro dinâmico: descoberta de tools por capability/toolset,
  além do registry estático do Vectora.
- `get_toolsets`, `get_toolset_config`, `toggle_toolset`, seleção de provider e
  modelo por toolset (`select_toolset_provider`, `select_toolset_model`). O
  Vectora tem políticas e capability matrix, mas não uma UX/registry geral de
  toolsets equivalente.
- `permissions_list_open`/`permissions_respond` e aprovação operacional
  associada a comandos, além do HITL do grafo. O Vectora possui HITL, mas ainda
  não expõe a mesma superfície de gerenciamento de permissões pendentes.
- `project`/workspaces nomeados do Hermes: múltiplos projetos selecionáveis
  como contexto operacional. O Vectora tem workspaces, mas deve comparar
  seleção, isolamento e persistência antes de declarar equivalência.

### `computer_use`: gap confirmado e escopo ampliado

O Vectora atualmente implementa somente `screenshot`, `click` e `type_text` em
`backend/tools/computer_use.py`, com opt-in por workspace e HITL obrigatório.
Isso é uma boa fundação de segurança, mas não é paridade funcional com o
computer-use do Hermes.

O plano passa a exigir uma expansão por camadas, sempre mantendo opt-in
explícito, aprovação humana por ação e registro auditável:

1. **Observação**: screenshot por monitor/janela, captura de região, escala,
   cursor/set-of-marks e metadados de resolução.
2. **Ponteiro**: move, click simples/duplo/direito/middle, drag, hover e
   scroll vertical/horizontal.
3. **Teclado**: pressionar tecla, hotkey, texto Unicode seguro, copiar/colar
   com confirmação e tratamento de layouts.
4. **Janelas e sincronização**: wait, foco de janela, listagem de janelas,
   abrir/fechar quando permitido e detecção de mudança de tela.
5. **Segurança**: limites de coordenada, bloqueio de áreas sensíveis,
   confirmação renovada para ações irreversíveis, trilha de screenshots e
   teste de fail-closed em workspace sem `[computer_use]`.

A expansão é feature de roadmap, não deve ser implementada junto de uma
correção incidental. O primeiro sprint deve comparar a API do Hermes com a
biblioteca multiplataforma escolhida no Vectora e escrever contrato/testes
antes de adicionar ações físicas.

### Sprints adicionados ao plano

- **Sprint 47 — Tool registry/capability audit**: catalogar tools por contrato,
  toolset, provider e superfície de execução; expor a diferença entre tool
  registrada, disponível e habilitada. Sem adicionar feature de usuário ainda.
- **Sprint 48 — STT local e YouTube transcript**: avaliar `faster-whisper` e
  `youtube-transcript-api` como extras opcionais; definir modelos, cache,
  limites de arquivo/URL, idioma, artifacts e fallback explícito.
- **Sprint 49 — Mensageria proativa unificada**: desenhar `send_message`,
  listagem de destinos e reações sobre o Connect existente, com HITL para
  envio externo e idempotência. Implementação aguarda solicitação explícita.
- **Sprint 50 — Terminal/process lifecycle parity**: auditar e completar
  leitura, polling, logs, stdin, close/kill e seleção de backend das sessões
  PTY do Vectora, sem confundir isso com o terminal sandboxado.
- **Sprint 51 — Computer use completo**: implementar as camadas de observação,
  ponteiro, teclado, janelas e sincronização descritas acima, com testes TDD,
  HITL por ação, opt-in e verificação ao vivo controlada.
- **Sprint 52 — Tool governance**: aproximar a gestão de toolsets, permissões
  pendentes e seleção de provider/modelo do modelo do Hermes, preservando a
  arquitetura deep-agent e as políticas próprias do Vectora.

Esses sprints ficam registrados como **features futuras**. Bugs da versão
atual continuam podendo ser corrigidos imediatamente; nenhum desses itens deve ser implementado sem pedido explícito do usuário.

### Fontes auditadas

- Hermes: `pyproject.toml`, `uv.lock`, `tools/`, `hermes_cli/` e skills locais.
- Vectora: `pyproject.toml`, `uv.lock`, `backend/tools/` e
  `backend/nodes/tools.py`. (`backend/mcp/server.py` não existe mais — o
  servidor MCP embutido foi removido por completo; `backend/tools/mcp.py` é
  o client que consome servidores MCP externos, ver nota de atualização
  acima.)
- A contagem de módulos não é tratada como contagem de tools: módulos Hermes
  como `approval.py`, `path_security.py` e `tool_backend_helpers.py` são
  infraestrutura, enquanto o inventário do Vectora foi conferido contra o
  registro de `ALL_TOOLS`.
