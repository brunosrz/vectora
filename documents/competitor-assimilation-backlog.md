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
> **Norte inegociável: RAG.** O maior poder do Vectora é a recuperação (RAG
> híbrido + Context Graph), e a **rag-library** é o objetivo central
> pós-lançamento. Tudo aqui é **paridade secundária** — só entra se não
> competir com o tempo da rag-library. Features marcadas 🎯 **reforçam** o
> norte (ligam direto em RAG/memória) e têm prioridade sobre as demais.
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
  (checkpointer LangGraph) e produz duas saídas via `response_format`:
  1. **Skills reutilizáveis** → grava `SKILL.md` em
     `~/.vectora/skills/{user_id}/` (formato que já carregamos on-demand no
     deep-agent). Dedup por similaridade de embedding contra as skills
     existentes antes de gravar (usa o próprio pipeline de embeddings).
  2. **Fatos duráveis sobre o usuário** → `save_memory` (BaseStore), com tag
     `user_model`.
- **`/journey`.** Query na memória `user_model` + timeline de skills criadas →
  resumo "o que aprendi sobre você". Renderiza no Memory tab do workbench.
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

**Por que pro Vectora.** Casa com o posicionamento "multi-acesso" e com o
`api-roadmap.md`. Vira ponte reversa: ferramentas de terceiros passam a falar
com o Vectora (roteando pro nosso multi-LLM + RAG) sem MCP. Amplia superfície
de integração sem lock-in.

**Como implementar.**

- Novo router `backend/api/handlers/openai_compat.py` montado sob `/v1`:
  `POST /v1/chat/completions` + `GET /v1/models` (lista os modelos com chave
  configurada, mesma fonte do seletor do chat).
- **Dois modos** (query/header `X-Vectora-Mode`): `raw` (passthrough ao LLM
  resolvido, sem agente — latência mínima, pra autocomplete/edits) e `agent`
  (roteia pelo `create_deep_agent`, ganhando RAG/tools). Default `raw`.
- **Tradução.** Request OpenAI → nossa resolução de provider
  (`FallbackChatModel` + settings). Streaming: reempacotar os chunks no
  formato `data: {...}\n\n` do OpenAI (adaptador irmão do `adapt_stream`).
- **Auth.** Reusa o middleware: Bearer com Vectora Token (Pro) ou usuário
  local. Rate-limit por tier (já temos `slowapi`).
- **Cuidado.** Não expor `agent` mode sem HITL desligado explicitamente —
  ferramentas externas não têm UI de aprovação; documentar que `agent` mode
  roda em permission mode restrito.

**Esforço.** Médio. **Dependências:** provider resolution (existe), auth
middleware (existe), SSE adapter (existe base).

---

### H-3. Worktree-per-task + override de modelo por task

**O que é.** No Kanban multi-agente do Hermes, cada task roda num **git
worktree próprio** e pode ter **override de modelo por task** (tasks
diferentes, modelos diferentes, em paralelo, sem pisar no working tree).

**Por que pro Vectora.** Resolve a contenção real quando subagentes/tasks
editam arquivos em paralelo (hoje compartilham o working tree). Habilita o
"agent swarm sob HITL" do radar sem corromper o repo.

**Como implementar.**

- **Worktree por task.** Ao iniciar uma task que escreve arquivos, criar
  `git worktree add .vectora/worktrees/{task_id} <branch>`; o subagent opera
  ali. Na conclusão: PR (via `gh`) ou merge com HITL; limpar o worktree.
  Integra na aba **Tarefas** do workbench e nas git tools (`backend/tools/git.py`).
- **Override de modelo.** Adicionar `model` opcional ao registro da task e ao
  `ChatConfig`; `agent_factory` já constrói um grafo por modelo — reusar pra
  buildar o grafo da task com o modelo escolhido. UI: seletor de modelo por
  task na aba Tarefas.
- **Concorrência.** Cada worktree = working tree isolado, então o lock do
  SQLite (D2, `busy_timeout`) já cobre o checkpointer compartilhado.

**Esforço.** Médio-alto. **Dependências:** Tarefas (existe), git tools
(existe), subagentes (existe). **Anti-Devin:** merge/PR sempre passa por HITL.

---

## Paperclip (paperclipai) — orquestração de times de agentes

### P-1 🎯 Biblioteca de artefatos do workspace (indexada em RAG)

**O que é.** "Company Artifacts": tudo que os agentes produzem (arquivos,
mídia, docs) é **indexado numa página com escopo da empresa**, pesquisável.

**Por que pro Vectora.** É semente direta da **rag-library** — a saída do
agente vira conhecimento recuperável, com escopo de workspace. Une o que já
temos solto: `create_artifact`, a aba Plan e o RAG.

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

## Priorização sugerida (impacto × proximidade do norte)

1. **P-1** 🎯 Biblioteca de artefatos indexada — semente da rag-library.
2. **H-1** 🎯 Learning loop — skills/memória auto-melhoráveis.
3. **P-3** Gates de PR — baixo custo, alto valor de confiança, reusa hooks.
4. **H-2** Proxy OpenAI-compatível — amplia integração sem lock-in.
5. **H-3** Worktree-per-task — destrava swarm/paralelo com segurança.
6. **P-4** Ticketing/heartbeats — depende do H-3.
7. **P-2** Governança/budgets — feature Enterprise, modo servidor.

> Tudo **pós-1.0** salvo P-3 (barato) — a rag-library tem precedência sobre
> qualquer item que compita pelo mesmo tempo de engenharia.

## Fontes

- Hermes Agent (Nous Research) — releases/changelog/docs, v0.18.0 (jul/2026):
  `github.com/NousResearch/hermes-agent`, `hermes-agent.nousresearch.com/docs`.
- Paperclip (paperclipai) — repo/docs (MIT, 2026):
  `github.com/paperclipai/paperclip`, `paperclip.ing`.
- Consultado em jul/2026. Confirmar detalhes de API antes de implementar (as
  release notes evoluem).
