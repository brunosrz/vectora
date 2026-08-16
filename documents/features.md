# Vectora × Hermes Agent — Comparativo de features e níveis de implementação (revalidação 2026-08-16)

> **Regra de leitura**: nenhuma célula é binária. Cada capacidade tem um
> **nível de implementação** próprio — `ausente` / `esqueleto` / `funcional
> básico` / `funcional com edge cases` / `maduro/produção`. Nunca tratar
> "Vectora tem X" ou "Hermes tem X" como resposta de sim/não. A comparação é
> sempre bidirecional: o que falta no Vectora E o que falta no Hermes.

---

## 0. Achado de conduta desta rodada — corrigir antes de tudo

A tarefa de tracking do projeto marca **"Sprint 23: liveness ativa de subagente (heartbeat + cancelamento real)"** como `completed`. A revalidação de código real (2026-08-16) encontrou que isso **não é verdade**: `backend/engine/subagents.py` (o motor nativo, ainda não ligado ao dispatch de produção — ver `Sprint 29` do plano) continua com `LivenessConfig(heartbeat_interval_s=30, max_stalled_heartbeats=3)` + `_watch_liveness()` que só cancela por **timeout de inatividade** — não há cancelamento real sob pedido explícito (nenhum equivalente a `request_hard_interrupt()` do Hermes), e o comentário do próprio código de Vectora (`backend/scheduling/liveness.py:1-10`) reconhece que `classify_liveness` é regex leve, puramente informativo, mais fraco que o próprio watchdog de `subagents.py`. A parte de "validação formal de escopo RBAC do subagente" da mesma sprint está sim entregue (`_tools_outside_user_scope()`), então não é uma sprint 100% falsa — é uma sprint **parcialmente reportada como concluída sem sê-lo**, o mesmo padrão que motivou a crise do LangChain (ver `Sprint 29`). Corrigido na seção "Pendências conhecidas" do plano de desenvolvimento e nos itens da Fase 1 da `Sprint 29`.

---

## 1. Hermes Agent — trajetória desde a última rodada (release notes + issues, ago/2026)

Ritmo de release mantido alto: de v0.13.0 (07/mai) a v0.20.1 (13/ago), 8
releases em ~3 meses. Destaques de arquitetura desde a comparação anterior:

- **v0.20.0 "The Herald"** (03/ago): voz conversacional em tempo real
  (streaming TTS, barge-in, wake words on-device), citações de pesquisa
  "grounded" com fact-checking, **protocolo A2A v1.0** (agent-to-agent),
  webhooks assinados de saída, artifacts renderizados no desktop com live
  preview.
- **v0.19.0 "The Quicksilver"** (20/jul): -80% no tempo do primeiro token,
  app desktop 14× mais rápido em streaming de markdown, integração de
  secrets (Bitwarden/1Password), ledger de entrega durável a crash.
- **v0.18.0 "The Judgment"** (01/jul): zero P0/P1 abertas (marco de
  segurança), Mixture-of-Agents como modelo selecionável de primeira
  classe, comando `/learn` pra criar skills reutilizáveis a partir de
  demonstrações.
- **v0.15.0 "The Velocity"** (28/mai): Kanban evoluiu pra plataforma
  multi-agente com auto-decomposição e swarm topology (o Vectora só fechou
  a parte de decomposição via `Sprint 20`, sem swarm topology).
- **v0.13.0 "The Tenacity"** (07/mai): comando `/goal` (Ralph loop) e
  correção de 8 vulnerabilidades P0 com redação (redaction) ligada por
  padrão.

**Issues abertas relevantes** (`P1`+`area/auth`: só 2, ambas bug em OAuth
existente, não feature nova; `type/feature`: 12, majoritariamente P3 —
provider MAIA Router, UI de imagem no desktop, limite de workers
concorrentes no Kanban, grupos de sessão com auto-agrupamento por IA,
recall assíncrono oportunista de memória). Nenhuma delas é um gap estrutural
que mude a priorização deste documento — a maior parte é polimento de
produto específico do domínio de mensageria do Hermes.

---

## 2. Matriz-resumo por área (revalidada)

| Área                                               | Quem lidera hoje                                      | Mudou desde 2026-08-14?                                                                                                                                                           |
| -------------------------------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SSO/OIDC                                           | Hermes (multi-provider, mais maduro)                  | **Vectora fechou o gap** — de "zero código" para funcional single-IDP (`Sprint 21`)                                                                                               |
| Redação de audit log                               | Empate                                                | **Vectora fechou** (`Sprint 24`)                                                                                                                                                  |
| Service account / API token                        | Empate                                                | **Vectora fechou** (`Sprint 24`)                                                                                                                                                  |
| Recuperação de senha                               | **Vectora** (Hermes não confirmado)                   | **Vectora fechou** (`Sprint 24`)                                                                                                                                                  |
| Multi-tenant SaaS real                             | Nenhum — continua lacuna compartilhada                | Sem mudança — `org_id` existe como campo de contexto mas **zero query SQL filtra por ele**                                                                                        |
| Sandbox OS-level (bwrap/Landlock/Seatbelt)         | **Vectora, folga ainda maior que o registrado antes** | Confirmado: Hermes **não tem nenhum** equivalente Rust/nativo — isolamento dele é só via Docker/cloud                                                                             |
| Guardrail de loop preso                            | Empate                                                | **Vectora fechou** (`Sprint 19`)                                                                                                                                                  |
| Denylist de arquivo sensível sem sandbox ativo     | Empate                                                | **Vectora fechou** (`Sprint 19`)                                                                                                                                                  |
| **Allowlist de env pro subprocess MCP local**      | Hermes                                                | **Sem mudança — nunca virou sprint**, gap real desde 2026-08-14                                                                                                                   |
| Memória / RAG / Context Graph                      | **Vectora, folga ainda maior**                        | Sem mudança relevante — Vectora segue muito à frente                                                                                                                              |
| Decomposer automático (Kanban triage→children)     | Empate                                                | **Vectora fechou** (`Sprint 20`)                                                                                                                                                  |
| **Capability token / dedup de subagente nativo**   | Hermes                                                | **Gap novo, não coberto** — `backend/engine/subagents.py` (motor nativo) não tem nada disso; `Sprint 16 WS7` cobriu só `backend/tools/background.py` (caminho de produção antigo) |
| **Liveness ativa (heartbeat + cancelamento real)** | Hermes                                                | **Continua ausente**, apesar de `Sprint 23` reportar como concluído — ver seção 0                                                                                                 |
| Validação RBAC subagente vs pai                    | Empate                                                | **Vectora fechou** (`Sprint 23`, parte real)                                                                                                                                      |
| Goal-mode (Ralph loop)                             | Hermes                                                | Sem mudança — deliberadamente adiado (`Sprint 25`, decisão de produto)                                                                                                            |
| Marketplace de skills (fontes múltiplas)           | Hermes, folga grande (10 fontes vs 1)                 | Sem mudança — `Sprint 22` só reavaliou, não adicionou fonte nova                                                                                                                  |
| Composição nomeada de toolsets                     | Hermes                                                | Sem mudança — `Sprint 28` bloqueada esperando `Sprint 14` completar (correto, `Sprint 14` não está completa)                                                                      |
| MCP marketplace (discovery multi-fonte)            | **Vectora**                                           | Sem mudança — vantagem já existente, 3 fontes com merge                                                                                                                           |
| Filesystem/Git/Terminal/Browser compartilhados     | **Vectora, com folga real**                           | Sem mudança — vantagem consolidada                                                                                                                                                |
| Contrato de streaming tipado                       | **Vectora** (20 tipos vs 7)                           | Cresceu de 17 para 20 tipos desde a última contagem                                                                                                                               |
| Kanban — maturidade de board no desktop            | Hermes (1430 linhas vs 496)                           | Gap não fechado, baixa prioridade                                                                                                                                                 |
| Terminal — persistência de buffer entre reloads    | Hermes (`revive-buffer.ts`), Vectora não confirmado   | Não verificado a fundo, candidato a checagem futura                                                                                                                               |

---

## 3. Auth / Multi-tenant (revalidado 2026-08-16)

| Capacidade                                     | Hermes                                                                                                        | Vectora                                                                                                                                                                                                    |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SSO/OIDC                                       | Maduro — dois providers reais (`self_hosted` genérico PKCE+JWKS, `nous` proprietário), 862+671 linhas         | **Funcional, single-IDP** — `backend/rbac/oidc.py` (256 linhas), discovery `.well-known`, PKCE S256, JWKS via `PyJWKClient`. `state` em memória de processo, não sobrevive restart (trade-off documentado) |
| Audit log com redação                          | Maduro — `_REDACTED_FIELDS` (8 campos)                                                                        | **Funcional, equivalente** — `_REDACTED_METADATA_FIELDS` (`backend/rbac/auth.py:1104-1123`), inspirado explicitamente no Hermes                                                                            |
| Service account / token de máquina             | Existe (não auditado a fundo nesta rodada)                                                                    | **Funcional** — `backend/rbac/token_auth.py`, tokens opacos `vst_` hasheados SHA-256, scopes com wildcard, revogação idempotente. Único consumidor real hoje é automação de webhook                        |
| Reset de senha                                 | Não confirmado nesta rodada                                                                                   | **Maduro/completo** — fluxo fim-a-fim (`/auth/password-reset/{request,confirm}`)                                                                                                                           |
| Multi-tenant real (org_id particionando dados) | **Ausente como partição** — `org_id` só aparece em claims de billing, Hermes é single-user/local por natureza | **Esqueleto** — `VectoraContext.org_id` existe e é propagado, mas **zero query SQL filtra por `org_id`** em todo `backend/` (grep confirmado)                                                              |

**Conclusão**: Vectora fechou 3 dos 5 gaps que o documento anterior listava (SSO, audit redaction, service token) e abriu um novo à frente do Hermes (reset de senha). Multi-tenant continua lacuna real e compartilhada — não é regressão, é decisão de arquitetura ainda não tomada (`Sprint 26`).

---

## 4. Sandbox / Segurança (revalidado 2026-08-16)

**Correção de premissa importante desta rodada**: o Hermes **não tem** nenhum
equivalente a `bwrap.rs`/`landlock.rs`/`seatbelt.rs` — não há isolamento de
processo local via namespaces/Landlock/Seatbelt em lugar nenhum do
repositório. O isolamento de execução do Hermes é 100% via containers
(Docker) e ambientes cloud (Modal, Vercel Sandbox). A vantagem do Vectora
nesta área é ainda maior do que o documento anterior registrava.

| Capacidade                                    | Hermes                                                                                                                                                       | Vectora                                                                                                                                                                                                                             |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sandbox de processo local (Linux)             | **Ausente**                                                                                                                                                  | **Maduro** — bwrap real + seccomp BPF via `pyseccomp` (denylist de syscalls perigosas), degrada graciosamente se ausente                                                                                                            |
| Landlock filesystem                           | Ausente                                                                                                                                                      | **Maduro** — ABI V1 completa via `ctypes`/syscall cru                                                                                                                                                                               |
| Landlock rede (ABI V4)                        | Ausente                                                                                                                                                      | **Maduro, fail-closed correto** — nega TCP exceto portas liberadas; se kernel não suportar V4, retorna `False` explicitamente em vez de fingir a restrição (ressalva: kernel 6.5+ é recente, na prática nem sempre disponível)      |
| Seatbelt macOS                                | Ausente                                                                                                                                                      | **Funcional, limitação reconhecida no próprio código** — `sandbox-exec` é API não documentada da Apple, rigor estruturalmente menor que Linux                                                                                       |
| Hardening de Docker                           | Maduro (cap-drop, no-new-privileges, cgroup limits)                                                                                                          | **Maduro, paridade real confirmada** — mesmas flags, mesmo desenho                                                                                                                                                                  |
| SSRF guard                                    | **Mais sofisticado no fluxo de browser real** — revalida URL pós-navegação (cobre redirect/DNS rebinding), mas é **fail-open** documentado em falha de probe | **Funcional, mais raso** — só pré-flight (fail-closed em falha de resolução, mais seguro nesse ponto), mas sem revalidação pós-redirect (TOCTOU real não coberto)                                                                   |
| **Allowlist de env pro subprocess MCP local** | Maduro                                                                                                                                                       | **Ausente** — `backend/tools/mcp.py::_build_connections()` não passa `env=` explícito, herda `os.environ` inteiro do processo pai (API keys de LLM inclusive) pro subprocess MCP. **Gap real desde 2026-08-14, nunca virou sprint** |

**Conclusão**: Vectora lidera com folga ainda maior que o documento anterior sugeria — a pilha de isolamento OS-level simplesmente não tem paralelo no Hermes. O único gap real e não fechado é a allowlist de env do subprocess MCP, que precisa entrar na próxima sprint.

---

## 5. Memória / RAG / Context-Graph (revalidado 2026-08-16)

| Capacidade                                       | Hermes                                                                                          | Vectora                                                                                                                                                                                    |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Memória — seções endereçáveis vs overwrite total | Maduro — `MEMORY.md`/`USER.md` com entradas delimitadas, sem histórico versionado por timestamp | **Maduro, com histórico versionado** — `memory_consolidation.py` arquiva versão anterior em `.history/` antes de sobrescrever, mais completo que o Hermes nesse ponto específico           |
| Promoção assíncrona com trilha de auditoria      | Parcial — edição direta via CLI/TUI, sem job de background propondo mudanças validadas          | **Maduro** — job periódico (6h) propõe consolidação como artifact HITL, só persiste com aprovação explícita                                                                                |
| Índice unificado de memória (fatos+skills+RAG)   | Não encontrado como índice único — provedores plugáveis externos                                | **Funcional, mas raso na busca** — `search_unified_memory` agrega os 3 tipos, mas só fatos têm busca semântica real (com embedding configurado); skills/buckets são sempre substring match |
| Parsing multi-linguagem (tree-sitter)            | Ausente                                                                                         | **Maduro** — extração AST determinística, ~30 linguagens                                                                                                                                   |
| GraphRAG / comunidades (Leiden)                  | Ausente                                                                                         | **Maduro, sem paralelo no Hermes** — pipeline completo extração→NetworkX→Leiden→GraphRAG                                                                                                   |

**Conclusão**: maior assimetria bidirecional do comparativo — Vectora tem um subsistema de Context Graph inteiro sem equivalente no Hermes, e amadureceu memória de conversa (histórico versionado, promoção HITL) além do que o Hermes tem nativamente. Ressalva: o Hermes compensa via ecossistema de provedores de memória externos plugáveis (supermemory, honcho, hindsight) que não foram avaliados em profundidade — não é comparável 1:1 sem essa investigação adicional, se vier a ser prioridade.

---

## 6. Subagentes / Orquestração (revalidado 2026-08-16)

| Capacidade                                            | Hermes                                                                                                                    | Vectora                                                                                                                                                                                                                                                                                                                     |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Capability token (anti-forge de handle)               | **Maduro** — HMAC-SHA256 por processo, `hmac.compare_digest`                                                              | **Ausente no motor nativo** — `backend/engine/subagents.py::run_subagent()` roda inline sem handle assinado. (`backend/tools/background.py::schedule_subagent_task`, caminho de produção antigo, tem capability token desde `Sprint 16 WS7` — mas isso não cobre o motor nativo que vai virar produção real na `Sprint 29`) |
| Dedup por correlation-id                              | **Maduro**                                                                                                                | **Ausente no motor nativo** — mesma ressalva acima                                                                                                                                                                                                                                                                          |
| Liveness ativa (heartbeat + cancelamento sob demanda) | **Maduro** — `request_hard_interrupt()` cancela de verdade sob pedido                                                     | **Só timeout passivo** — `_watch_liveness()` cancela por inatividade, não por pedido explícito. Reportado como "concluído" na `Sprint 23`, não está — ver seção 0                                                                                                                                                           |
| Validação RBAC filho vs pai                           | Funcional                                                                                                                 | **Funcional, replicado corretamente** — `_tools_outside_user_scope()` filtra contra `tool_policy.effective_disabled`                                                                                                                                                                                                        |
| Goal-mode (Ralph loop)                                | **Muito maduro** — `hermes_cli/goals.py` (2157 linhas): judge LLM, quality gates determinísticos, turn budget, auto-pause | **Ausente, sem vestígio de trabalho** — nenhuma ocorrência de "goal"/"judge"/"quality_gate" em `backend/` fora do comentário que descreve a ausência. Deliberadamente adiado (`Sprint 25`, decisão de produto pendente)                                                                                                     |

**Conclusão**: maior gap real e ainda aberto do comparativo inteiro. O motor nativo de subagentes (`backend/engine/subagents.py`) — que é justamente o que a `Sprint 29` vai promover a produção — está menos hardened do que o caminho antigo que está substituindo. Isso precisa ser resolvido **dentro** da `Sprint 29`, não depois, porque senão o corte de dispatch promove um subsistema mais frágil a produção.

---

## 7. MCP / Tools / Marketplace (revalidado 2026-08-16)

| Capacidade                                                    | Hermes                                                                                                              | Vectora                                                                                                                                                                       |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Composição nomeada de toolsets (`includes` recursivo + ciclo) | **Maduro** — `toolsets.py` (1040 linhas), `resolve_toolset()` com detecção de ciclo                                 | **Ausente** — `souls.py` usa concatenação estática de listas Python (`FS_TOOLS + GIT_TOOLS + ...`). Bloqueada corretamente (`Sprint 28`) esperando `Sprint 14`/`29` completar |
| Fontes de discovery de skill                                  | **Muito maduro** — 10 classes de `SkillSource` (GitHub, WellKnown, Url, SkillsSh, ClawHub, LobeHub, BrowseSh, etc.) | **Esqueleto/parcial** — 1 fonte remota (`registry_client.fetch_catalog`), sem fallback local hardcoded, catálogo pode ficar vazio                                             |
| MCP marketplace (discovery de servers)                        | Sem equivalente dedicado encontrado                                                                                 | **Funcional, vantagem real do Vectora** — 3 fontes com merge e prioridade (D1 próprio, registry oficial MCP, fallback local de 6 conectores curados)                          |

**Conclusão**: Hermes lidera com folga grande em discovery de skills (10 fontes vs 1). Vectora tem uma vantagem pontual em discovery de MCP servers especificamente (escopo mais estreito, mas bem desenhado). Composição de toolsets segue como gap conhecido, corretamente sequenciado depois do corte de dispatch.

---

## 8. Streaming / UI / Workbench (revalidado 2026-08-16)

| Capacidade                             | Hermes                                                                                             | Vectora                                                                                                                                                                                             |
| -------------------------------------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Vocabulário de eventos de streaming    | **Funcional, deliberadamente magro** — 7 tipos, desenhado pra plataformas de mensagens sem UI rica | **Mais rico, desenhado para múltiplos painéis** — 20 tipos (cresceu de 17), incluindo `WorkbenchInvalidate`/`TerminalLine`/`NodeStatus`/`RagCitations` específicos de alimentar painéis simultâneos |
| Editor de código no painel de arquivos | **Ausente** — árvore de arquivo é navegação/preview, sem editor embutido (zero "monaco" no repo)   | **Maduro** — Monaco real editável (`@monaco-editor/react`), mais variante readonly pra preview                                                                                                      |
| Git no painel                          | Médio — foco em revisar/"ship"                                                                     | **Maduro** — worktrees reais via UI (criar/listar)                                                                                                                                                  |
| Terminal persistente                   | **Maduro, com replay de buffer entre sessões** (`revive-buffer.ts`)                                | Terminal persistente confirmado (mesma sessão PTY usuário↔agente), mas **persistência de buffer entre reloads não confirmada** — candidato a checagem                                               |
| Kanban no desktop                      | **Maduro, board grande** (1430 linhas)                                                             | Funcional, mais raso (496 linhas) — baixa prioridade de fechar                                                                                                                                      |
| Memory tab unificada                   | Sem equivalente                                                                                    | **Presente** — RAG+skills+memory+journey num só painel                                                                                                                                              |
| Context Graph tab                      | Ausente                                                                                            | **Presente, sem equivalente no Hermes**                                                                                                                                                             |

**Conclusão**: os dois produtos investiram em direções diferentes — Hermes em profundidade de mensageria/Kanban, Vectora em profundidade de dev-workbench (editor real, git, context graph). Ponto a verificar: persistência de buffer de terminal entre reloads, onde o Hermes tem um mecanismo dedicado e o Vectora não foi confirmado.

---

## 8.5. Correção — plugins MCP contados como capacidade nativa do Hermes

O usuário apontou, corretamente, que 4 projetos locais (`C:\Users\Machi\Desktop\vectora\{graphify-8,omskills-main,chrome-devtools-mcp-main,ragflow-main}`) são conectáveis ao Hermes como servidores MCP — e que tratá-los como "ausentes no Hermes" nas seções 5, 7 e 8 acima é injusto, já que o Hermes é cliente MCP e pode plugá-los. 4 agentes leram os 4 projetos e confirmaram, com ressalvas reais por projeto — nem tudo vira paridade automática:

**`graphify-8` (Context Graph)** — servidor MCP real e funcional (`graphify/serve.py`, ~2100 linhas, tools `query_graph`/`get_pr_impact`/etc., plug-and-play). Extração AST via tree-sitter (~30-40 linguagens) e clustering Leiden/Louvain são **equivalentes/empatados** com o Vectora — os dois parecem compartilhar a mesma base de código (`backend/context_graph/cluster.py` do Vectora tem o mesmo código de Leiden/graspologic, comentário por comentário). **O gap não fecha em GraphRAG**: o graphify-8 se declara explicitamente "not a vector index — no embeddings, no vector store" (é uma alternativa deliberadamente sem vetores ao RAG denso); `backend/context_graph/graph_index.py` do Vectora indexa os nós do grafo em LanceDB com embedding multi-provider e faz busca híbrida vetor+grafo, capacidade que o graphify-8 não tem por design. **Correção de veredito**: de "Vectora lidera com folga, sem equivalente" para "empate em extração/clustering via plugin; Vectora mantém vantagem real e específica em GraphRAG".

**`ragflow-main` (RAG)** — tem servidor MCP real (`mcp/server/server.py`, 3 tools: `ragflow_retrieval`/`list_datasets`/`list_chats`), mas é um proxy fino sobre a REST API do RAGFlow — exige rodar a stack standalone inteira (Elasticsearch/Infinity + MySQL + Redis + MinIO + task executors + UI própria pra criar datasets) antes de expor as 3 tools. Não é "plugar e usar", é operar uma aplicação externa completa ao lado do Hermes. Tecnicamente é um motor de RAG mais profundo que o do Vectora nalguns eixos (parsing multimodal, mais opções de rerank, GraphRAG próprio), mas ao custo de infraestrutura pesada. **Correção de veredito**: de "Vectora lidera, sem equivalente no Hermes" para "Vectora lidera em simplicidade/integração nativa (código+docs, sem infra externa); Hermes alcança paridade funcional via plugin RAGFlow, ao custo operacional de uma stack externa completa".

**`omskills-main` (Skills)** — **não é** uma fonte de discovery adicional. É um pacote estático de ~19 skills em formato `SKILL.md` (fork de `mattpocock/skills`), instalado via symlink local (`scripts/link-skills.sh`), sem API, sem registry remoto, sem menção a MCP em lugar nenhum do repo. Conceitualmente diferente das 10 fontes dinâmicas de discovery do Hermes (`toolsets.py`/`skills_hub.py`) — é mais parecido com um pacote de conteúdo que poderia ser instalado manualmente em qualquer um dos dois produtos (o Vectora, aliás, já aceita a URL git desse repo diretamente via `install_skill`). **Sem correção de veredito** — "Hermes lidera em discovery de skills, 10 fontes vs 1" permanece válido, com a ressalva de que "1 fonte" no Vectora é o catálogo curado oficial, não um limite técnico (qualquer URL git funciona via `install_skill`).

**`chrome-devtools-mcp-main` (Browser DevTools)** — confirmado como o servidor MCP **oficial** do Chrome DevTools Team (Google), maduro, testado (~209 blocos de teste), mantido ativamente (v1.6.0, releases frequentes). Expõe ~54 tools (~33 ativas por padrão, o resto atrás de flags experimentais) cobrindo input, navegação, performance trace, network, console, snapshot de acessibilidade, heap snapshot granular (11 sub-tools), lighthouse. A contagem real de tools do Vectora nesta área também precisa de correção: não são "~19-25" como uma rodada anterior registrava, e sim **~34** (`browser.py` 14 + `browser_devtools.py` 20). Com o chrome-devtools-mcp contado como plugin do Hermes, **o gap de tooling bruto fecha quase totalmente** (~33-34 de cada lado, ou até 54 se o Hermes ativar as flags experimentais). **A única vantagem que sobra, e que o Hermes estruturalmente não pode adquirir só conectando o mesmo plugin, é o painel visual integrado no workbench** (`browser-tab.tsx` + `browser-devtools-panel.tsx`) — console/network/DOM inspecionáveis diretamente pelo usuário humano, não só pelo agente via protocolo MCP; o chrome-devtools-mcp não tem UI própria, é consumido só por clientes MCP. **Correção de veredito**: de "Vectora com folga real (mais tools)" para "empate técnico em cobertura de tools via plugin; vantagem real do Vectora é exclusivamente o painel visual pro usuário humano, que é uma capacidade de frontend, não de tooling do agente".

### Ajuste geral de leitura

Nenhuma dessas 4 correções inverte a conclusão de que o Vectora lidera nas áreas de sandbox, memória/RAG nativo e workbench compartilhado — mas 3 das 4 (graphify-8, ragflow-main, chrome-devtools-mcp) mostram que parte dessa liderança é mais estreita do que parecia quando o ecossistema MCP do concorrente é contado a favor dele, como é justo fazer. A lição prática: comparar "produto A vs produto B" sem contar o que A pode plugar via MCP super-representa a vantagem nativa de B — o comparativo correto é sempre "capacidade nativa + ecossistema plugável de cada lado".

---

## 9. O que fazer a seguir

Ver `Sprint 29` (remoção de LangChain, agora também absorvendo o hardening
do motor nativo de subagentes — capability token, dedup, liveness ativa —
porque é o mesmo código que vai virar produção) e `Sprint 30` (consolidação:
allowlist de env MCP, segunda fonte de skill discovery, verificação de
persistência de buffer de terminal) no plano de desenvolvimento
(`iterative-bouncing-treehouse.md`).
