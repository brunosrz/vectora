# Vectora × Hermes Agent — Comparativo de features e níveis de implementação (revalidação 2026-08-19)

> **Regra de leitura**: nenhuma célula é binária. Cada capacidade tem um
> **nível de implementação** próprio — `ausente` / `esqueleto` / `funcional
básico` / `funcional com edge cases` / `maduro/produção`. Nunca tratar
> "Vectora tem X" ou "Hermes tem X" como resposta de sim/não. A comparação é
> sempre bidirecional: o que falta no Vectora E o que falta no Hermes.

---

## 1. Matriz-resumo por área (revalidada)

| Área                                            | Quem lidera hoje                      | Observação                                                                                                                                                 |
| ----------------------------------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SSO/OIDC                                        | Hermes (multi-provider, mais maduro)  | Vectora tem SSO funcional single-IDP (discovery `.well-known`, PKCE S256, JWKS)                                                                            |
| Redação de audit log                            | Empate                                | Os dois redigem campos sensíveis antes de persistir log                                                                                                    |
| Service account / API token                     | Empate                                | Os dois têm tokens de máquina com escopo e revogação                                                                                                       |
| Recuperação de senha                            | Vectora (Hermes não confirmado)       | Fluxo fim-a-fim no Vectora                                                                                                                                 |
| Sandbox OS-level (bwrap/Landlock/Seatbelt)      | **Vectora, folga grande**             | Hermes não tem nenhum equivalente nativo — isolamento dele é só via Docker/cloud                                                                           |
| Guardrail de loop preso                         | Empate                                | Os dois detectam repetição de tool call, não só contador fixo                                                                                              |
| Denylist de arquivo sensível sem sandbox ativo  | Empate                                | Proteção independente do sandbox estar ativo, nos dois                                                                                                     |
| Allowlist de env pro subprocess MCP local       | Empate                                | Vectora fechou o gap — allowlist mínimo (`_SAFE_SUBPROCESS_ENV_KEYS`) + extras declarados por servidor via `env_vars`, sem herdar `os.environ` inteiro     |
| Memória / RAG / Context Graph                   | **Vectora, folga grande**             | Subsistema nativo completo, sem equivalente direto no Hermes                                                                                               |
| Decomposer automático (Kanban triage→children)  | Empate                                | Os dois populam grafo de subtarefas automaticamente a partir de um card                                                                                    |
| Capability token / dedup de subagente nativo    | Empate                                | Vectora fechou o gap — `backend/engine/subagents.py` tem `subagent_capability_token` (HMAC) e dedup por `correlation_id` no motor nativo                   |
| Liveness ativa (heartbeat + cancelamento real)  | Empate                                | Vectora fechou o gap — `request_hard_interrupt()` cancela por pedido explícito, validado por capability token, além do watchdog passivo                    |
| Validação RBAC subagente vs pai                 | Empate                                | Os dois filtram tools do subagente contra o escopo do chamador                                                                                             |
| Goal-mode (Ralph loop)                          | Empate                                | Vectora fechou o gap — `backend/engine/goal_mode.py::run_goal` encadeia turnos com gates de qualidade + judge LLM até o objetivo ser cumprido              |
| Marketplace de skills (fontes múltiplas)        | Hermes, folga grande (10 fontes vs 1) | Vectora tem só 1 fonte remota, sem fallback local                                                                                                          |
| Composição nomeada de toolsets                  | Empate                                | Vectora fechou o gap — `backend/tools/groups.py` resolve `includes` recursivo com detecção real de ciclo (`ToolGroupCycleError`), consumido por `souls.py` |
| MCP marketplace (discovery multi-fonte)         | **Vectora**                           | 3 fontes com merge e prioridade, vantagem real                                                                                                             |
| Filesystem/Git/Terminal/Browser compartilhados  | **Vectora, com folga real**           | Edição real de arquivo (Monaco), git worktrees, terminal PTY compartilhado, browser multi-tab                                                              |
| Contrato de streaming tipado                    | **Vectora** (20 tipos vs 7)           | Vocabulário mais rico, desenhado pra múltiplos painéis simultâneos                                                                                         |
| Kanban — maturidade de board no desktop         | Hermes (1430 linhas vs 496)           | Baixa prioridade de fechar                                                                                                                                 |
| Terminal — persistência de buffer entre reloads | Hermes tem, Vectora não confirmado    | Candidato a checagem                                                                                                                                       |

---

## 2. Auth

| Capacidade                         | Hermes                                                                                                | Vectora                                                                                                                                                                                                    |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SSO/OIDC                           | Maduro — dois providers reais (`self_hosted` genérico PKCE+JWKS, `nous` proprietário), 862+671 linhas | **Funcional, single-IDP** — `backend/rbac/oidc.py` (256 linhas), discovery `.well-known`, PKCE S256, JWKS via `PyJWKClient`. `state` em memória de processo, não sobrevive restart (trade-off documentado) |
| Audit log com redação              | Maduro — `_REDACTED_FIELDS` (8 campos)                                                                | **Funcional, equivalente** — `_REDACTED_METADATA_FIELDS` (`backend/rbac/auth.py:1104-1123`), inspirado explicitamente no Hermes                                                                            |
| Service account / token de máquina | Existe (não auditado a fundo nesta rodada)                                                            | **Funcional** — `backend/rbac/token_auth.py`, tokens opacos `vst_` hasheados SHA-256, scopes com wildcard, revogação idempotente. Único consumidor real hoje é automação de webhook                        |
| Reset de senha                     | Não confirmado nesta rodada                                                                           | **Maduro/completo** — fluxo fim-a-fim (`/auth/password-reset/{request,confirm}`)                                                                                                                           |

**Conclusão**: Vectora tem paridade ou vantagem em SSO (single-IDP, mas real), audit redaction, service token e reset de senha.

---

## 3. Sandbox / Segurança

**Correção de premissa importante**: o Hermes **não tem** nenhum
equivalente a `bwrap.rs`/`landlock.rs`/`seatbelt.rs` — não há isolamento de
processo local via namespaces/Landlock/Seatbelt em lugar nenhum do
repositório. O isolamento de execução do Hermes é 100% via containers
(Docker) e ambientes cloud (Modal, Vercel Sandbox).

| Capacidade                                    | Hermes                                                                                                                                                       | Vectora                                                                                                                                                                                                                                  |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sandbox de processo local (Linux)             | **Ausente**                                                                                                                                                  | **Maduro** — bwrap real + seccomp BPF via `pyseccomp` (denylist de syscalls perigosas), degrada graciosamente se ausente                                                                                                                 |
| Landlock filesystem                           | Ausente                                                                                                                                                      | **Maduro** — ABI V1 completa via `ctypes`/syscall cru                                                                                                                                                                                    |
| Landlock rede (ABI V4)                        | Ausente                                                                                                                                                      | **Maduro, fail-closed correto** — nega TCP exceto portas liberadas; se kernel não suportar V4, retorna `False` explicitamente em vez de fingir a restrição (ressalva: kernel 6.5+ é recente, na prática nem sempre disponível)           |
| Seatbelt macOS                                | Ausente                                                                                                                                                      | **Funcional, limitação reconhecida no próprio código** — `sandbox-exec` é API não documentada da Apple, rigor estruturalmente menor que Linux                                                                                            |
| Hardening de Docker                           | Maduro (cap-drop, no-new-privileges, cgroup limits)                                                                                                          | **Maduro, paridade real confirmada** — mesmas flags, mesmo desenho                                                                                                                                                                       |
| SSRF guard                                    | **Mais sofisticado no fluxo de browser real** — revalida URL pós-navegação (cobre redirect/DNS rebinding), mas é **fail-open** documentado em falha de probe | **Funcional, mais raso** — só pré-flight (fail-closed em falha de resolução, mais seguro nesse ponto), mas sem revalidação pós-redirect (TOCTOU real não coberto)                                                                        |
| **Allowlist de env pro subprocess MCP local** | Maduro                                                                                                                                                       | **Maduro, paridade real** — `backend/tools/mcp.py::_safe_subprocess_env()` monta um allowlist mínimo (`_SAFE_SUBPROCESS_ENV_KEYS`) e só soma variáveis extras declaradas pelo servidor (`env_vars`); não herda mais `os.environ` inteiro |

**Conclusão**: Vectora lidera com folga grande — a pilha de isolamento OS-level simplesmente não tem paralelo no Hermes. O gap de allowlist de env do subprocess MCP, que existia em revalidações anteriores, já foi fechado.

---

## 4. Memória / RAG / Context-Graph

| Capacidade                                       | Hermes                                                                                          | Vectora                                                                                                                                                                                    |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Memória — seções endereçáveis vs overwrite total | Maduro — `MEMORY.md`/`USER.md` com entradas delimitadas, sem histórico versionado por timestamp | **Maduro, com histórico versionado** — `memory_consolidation.py` arquiva versão anterior em `.history/` antes de sobrescrever, mais completo que o Hermes nesse ponto específico           |
| Promoção assíncrona com trilha de auditoria      | Parcial — edição direta via CLI/TUI, sem job de background propondo mudanças validadas          | **Maduro** — job periódico (6h) propõe consolidação como artifact HITL, só persiste com aprovação explícita                                                                                |
| Índice unificado de memória (fatos+skills+RAG)   | Não encontrado como índice único — provedores plugáveis externos                                | **Funcional, mas raso na busca** — `search_unified_memory` agrega os 3 tipos, mas só fatos têm busca semântica real (com embedding configurado); skills/buckets são sempre substring match |
| Parsing multi-linguagem (tree-sitter)            | Ausente                                                                                         | **Maduro** — extração AST determinística, ~30 linguagens                                                                                                                                   |
| GraphRAG / comunidades (Leiden)                  | Ausente                                                                                         | **Maduro, sem paralelo no Hermes** — pipeline completo extração→NetworkX→Leiden→GraphRAG                                                                                                   |

**Conclusão**: maior assimetria bidirecional do comparativo — Vectora tem um subsistema de Context Graph inteiro sem equivalente no Hermes, e amadureceu memória de conversa (histórico versionado, promoção HITL) além do que o Hermes tem nativamente. Ressalva: o Hermes compensa via ecossistema de provedores de memória externos plugáveis (supermemory, honcho, hindsight) que não foram avaliados em profundidade — não é comparável 1:1 sem essa investigação adicional, se vier a ser prioridade.

---

## 5. Subagentes / Orquestração

| Capacidade                                            | Hermes                                                                               | Vectora                                                                                                                                                                                                                                                                                |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Capability token (anti-forge de handle)               | **Maduro** — HMAC-SHA256 por processo, `hmac.compare_digest`                         | **Maduro, paridade real** — `backend/engine/subagents.py::subagent_capability_token()` (HMAC-SHA256 sobre `correlation_id`, mesma chave de assinatura que `backend/tools/background.py::_capability_token` já usava), validado via `hmac.compare_digest` em `request_hard_interrupt()` |
| Dedup por correlation-id                              | **Maduro**                                                                           | **Maduro, paridade real** — delegações concorrentes com o mesmo `correlation_id` reaproveitam a execução em andamento (`_IN_FLIGHT_BY_CORRELATION`)                                                                                                                                    |
| Liveness ativa (heartbeat + cancelamento sob demanda) | **Maduro** — `request_hard_interrupt()` cancela de verdade sob pedido                | **Maduro, paridade real** — `request_hard_interrupt(correlation_id, capability_token)` cancela a `conversation_task` associada quando o token bate, além do watchdog passivo por timeout                                                                                               |
| Validação RBAC filho vs pai                           | Funcional                                                                            | **Funcional, replicado corretamente** — `_tools_outside_user_scope()` filtra contra `tool_policy.effective_disabled`                                                                                                                                                                   |
| Goal-mode (Ralph loop)                                | **Muito maduro** — judge LLM, quality gates determinísticos, turn budget, auto-pause | **Funcional, paridade real** — `backend/engine/goal_mode.py::run_goal` encadeia turnos até gates de qualidade (comandos externos) e um judge LLM aprovarem o objetivo, com auto-pause em falhas seguidas de judge e sem decidir por cima de HITL pendente                              |

**Conclusão**: gap fechado nesta revalidação. O motor nativo de subagentes ganhou capability token, dedup por correlation-id, cancelamento ativo sob pedido e goal-mode — paridade real com o Hermes nesta área, onde antes havia o maior gap aberto do comparativo.

---

## 6. MCP / Tools / Marketplace

| Capacidade                                                    | Hermes                                                                                                              | Vectora                                                                                                                                                                                                                                                              |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Composição nomeada de toolsets (`includes` recursivo + ciclo) | **Maduro** — `toolsets.py` (1040 linhas), `resolve_toolset()` com detecção de ciclo                                 | **Maduro, paridade real** — `backend/tools/groups.py::resolve_tool_group()` resolve `includes` recursivo com união deduplicada e `ToolGroupCycleError` real, consumido por `backend/agents/souls.py` (enforcement real de tools por SOUL, não concatenação estática) |
| Fontes de discovery de skill                                  | **Muito maduro** — 10 classes de `SkillSource` (GitHub, WellKnown, Url, SkillsSh, ClawHub, LobeHub, BrowseSh, etc.) | **Esqueleto/parcial** — 1 fonte remota (`registry_client.fetch_catalog`), sem fallback local hardcoded, catálogo pode ficar vazio                                                                                                                                    |
| MCP marketplace (discovery de servers)                        | Sem equivalente dedicado encontrado                                                                                 | **Funcional, vantagem real do Vectora** — 3 fontes com merge e prioridade (D1 próprio, registry oficial MCP, fallback local de 6 conectores curados)                                                                                                                 |

**Conclusão**: Hermes lidera com folga grande em discovery de skills (10 fontes vs 1). Vectora tem uma vantagem pontual em discovery de MCP servers especificamente (escopo mais estreito, mas bem desenhado). Composição de toolsets deixou de ser gap — `backend/tools/groups.py` fechou a paridade com `includes` nomeado e detecção de ciclo real.

---

## 7. Streaming / UI / Workbench

| Capacidade                             | Hermes                                                                                             | Vectora                                                                                                                                                                             |
| -------------------------------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Vocabulário de eventos de streaming    | **Funcional, deliberadamente magro** — 7 tipos, desenhado pra plataformas de mensagens sem UI rica | **Mais rico, desenhado para múltiplos painéis** — 20 tipos, incluindo `WorkbenchInvalidate`/`TerminalLine`/`NodeStatus`/`RagCitations` específicos de alimentar painéis simultâneos |
| Editor de código no painel de arquivos | **Ausente** — árvore de arquivo é navegação/preview, sem editor embutido (zero "monaco" no repo)   | **Maduro** — Monaco real editável (`@monaco-editor/react`), mais variante readonly pra preview                                                                                      |
| Git no painel                          | Médio — foco em revisar/"ship"                                                                     | **Maduro** — worktrees reais via UI (criar/listar)                                                                                                                                  |
| Terminal persistente                   | **Maduro, com replay de buffer entre sessões**                                                     | Terminal persistente confirmado (mesma sessão PTY usuário↔agente), mas **persistência de buffer entre reloads não confirmada** — candidato a checagem                               |
| Kanban no desktop                      | **Maduro, board grande** (1430 linhas)                                                             | Funcional, mais raso (496 linhas) — baixa prioridade de fechar                                                                                                                      |
| Memory tab unificada                   | Sem equivalente                                                                                    | **Presente** — RAG+skills+memory+journey num só painel                                                                                                                              |
| Context Graph tab                      | Ausente                                                                                            | **Presente, sem equivalente no Hermes**                                                                                                                                             |

**Conclusão**: os dois produtos investiram em direções diferentes — Hermes em profundidade de mensageria/Kanban, Vectora em profundidade de dev-workbench (editor real, git, context graph). Ponto a verificar: persistência de buffer de terminal entre reloads, onde o Hermes tem um mecanismo dedicado e o Vectora não foi confirmado.

---

## 8. Correção — plugins MCP contados como capacidade disponível ao Hermes

4 projetos locais (`graphify-8`, `omskills-main`, `chrome-devtools-mcp-main`, `ragflow-main`) são conectáveis ao Hermes como servidores MCP — tratá-los como "ausentes no Hermes" nas seções acima seria injusto, já que o Hermes é cliente MCP e pode plugá-los. Cada um foi investigado, com ressalvas reais — nem tudo vira paridade automática:

**`graphify-8` (Context Graph)** — servidor MCP real e funcional (`graphify/serve.py`, ~2100 linhas, tools `query_graph`/`get_pr_impact`/etc., plug-and-play). Extração AST via tree-sitter (~30-40 linguagens) e clustering Leiden/Louvain são **equivalentes/empatados** com o Vectora — os dois parecem compartilhar a mesma base de código (`backend/context_graph/cluster.py` do Vectora tem o mesmo código de Leiden/graspologic, comentário por comentário). **O gap não fecha em GraphRAG**: o graphify-8 se declara explicitamente "not a vector index — no embeddings, no vector store" (é uma alternativa deliberadamente sem vetores ao RAG denso); `backend/context_graph/graph_index.py` do Vectora indexa os nós do grafo em LanceDB com embedding multi-provider e faz busca híbrida vetor+grafo, capacidade que o graphify-8 não tem por design. **Veredito**: empate em extração/clustering via plugin; Vectora mantém vantagem real e específica em GraphRAG.

**`ragflow-main` (RAG)** — tem servidor MCP real (`mcp/server/server.py`, 3 tools: `ragflow_retrieval`/`list_datasets`/`list_chats`), mas é um proxy fino sobre a REST API do RAGFlow — exige rodar a stack standalone inteira (Elasticsearch/Infinity + MySQL + Redis + MinIO + task executors + UI própria pra criar datasets) antes de expor as 3 tools. Não é "plugar e usar", é operar uma aplicação externa completa ao lado do Hermes. Tecnicamente é um motor de RAG mais profundo que o do Vectora nalguns eixos (parsing multimodal, mais opções de rerank, GraphRAG próprio), mas ao custo de infraestrutura pesada. **Veredito**: Vectora lidera em simplicidade/integração nativa (código+docs, sem infra externa); Hermes alcança paridade funcional via plugin RAGFlow, ao custo operacional de uma stack externa completa.

**`omskills-main` (Skills)** — **não é** uma fonte de discovery adicional. É um pacote estático de ~19 skills em formato `SKILL.md` (fork de `mattpocock/skills`), instalado via symlink local (`scripts/link-skills.sh`), sem API, sem registry remoto, sem menção a MCP em lugar nenhum do repo. Conceitualmente diferente das 10 fontes dinâmicas de discovery do Hermes (`toolsets.py`/`skills_hub.py`) — é mais parecido com um pacote de conteúdo que poderia ser instalado manualmente em qualquer um dos dois produtos (o Vectora, aliás, já aceita a URL git desse repo diretamente via `install_skill`). **Veredito**: sem mudança — "Hermes lidera em discovery de skills, 10 fontes vs 1" permanece válido, com a ressalva de que "1 fonte" no Vectora é o catálogo curado oficial, não um limite técnico (qualquer URL git funciona via `install_skill`).

**`chrome-devtools-mcp-main` (Browser DevTools)** — confirmado como o servidor MCP **oficial** do Chrome DevTools Team (Google), maduro, testado (~209 blocos de teste), mantido ativamente (v1.6.0, releases frequentes). Expõe ~54 tools (~33 ativas por padrão, o resto atrás de flags experimentais) cobrindo input, navegação, performance trace, network, console, snapshot de acessibilidade, heap snapshot granular (11 sub-tools), lighthouse. A contagem real de tools do Vectora nesta área é **~34** (`browser.py` 14 + `browser_devtools.py` 20). Com o chrome-devtools-mcp contado como plugin do Hermes, **o gap de tooling bruto fecha quase totalmente** (~33-34 de cada lado, ou até 54 se o Hermes ativar as flags experimentais). **A única vantagem que sobra, e que o Hermes estruturalmente não pode adquirir só conectando o mesmo plugin, é o painel visual integrado no workbench** (`browser-tab.tsx` + `browser-devtools-panel.tsx`) — console/network/DOM inspecionáveis diretamente pelo usuário humano, não só pelo agente via protocolo MCP; o chrome-devtools-mcp não tem UI própria, é consumido só por clientes MCP. **Veredito**: empate técnico em cobertura de tools via plugin; vantagem real do Vectora é exclusivamente o painel visual pro usuário humano, que é uma capacidade de frontend, não de tooling do agente.

### Ajuste geral de leitura

Nenhuma dessas 4 correções inverte a conclusão de que o Vectora lidera nas áreas de sandbox, memória/RAG nativo e workbench compartilhado — mas 3 das 4 (graphify-8, ragflow-main, chrome-devtools-mcp) mostram que parte dessa liderança é mais estreita do que parecia quando o ecossistema MCP do concorrente é contado a favor dele, como é justo fazer. A lição prática: comparar "produto A vs produto B" sem contar o que A pode plugar via MCP super-representa a vantagem nativa de B — o comparativo correto é sempre "capacidade nativa + ecossistema plugável de cada lado".

---

## 9. Gaps confirmados, sem ação vinculada aqui

Lista neutra dos pontos em que o Hermes lidera e o Vectora ainda não fechou
o gap, sem apontar para nenhum processo de execução específico:

- Segunda fonte de discovery de skills (só 1 fonte remota, sem fallback).
- Kanban no desktop tem menos profundidade de board que o Hermes (baixa
  prioridade de fechar).
- Persistência de buffer de terminal entre reloads não confirmada (candidato
  a checagem, não gap confirmado).

Gaps que constavam em revalidações anteriores desta lista — allowlist de env
do subprocess MCP local, hardening do motor nativo de subagentes (capability
token, dedup por correlation-id, cancelamento ativo) e Goal-mode (Ralph
loop) — foram fechados e já não aparecem aqui; ver seções 3, 5 e 6 acima.
