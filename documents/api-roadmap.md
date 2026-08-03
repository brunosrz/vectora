# Vectora — Roadmap da API REST (Edge Completa)

> Anexo ao trabalho de `docs.vectora.company` (migração pra Hugo + Hextra):
> a página `api-reference/roadmap` do novo site documenta honestamente que
> hoje só `/v1/classify`, `/v1/extract` e `/v1/jobs` (+ SSE) existem — o
> resto da API REST completa (`/v1/chat`, `/v1/documents`, SDKs, webhooks)
> era **fictício** no site antigo. Este documento é o plano real por trás
> dessa lacuna: como fechar a distância entre "o que o produto faz hoje
> só pelo chat web/CLI/MCP" e "uma edge de API pública completa", em
> sprints executáveis.
>
> Detalha e substitui a parte de API dos Blocos **J** (REST API v1 +
> Segurança Hardening) e **L** (SDKs & API Ecosystem) do `plan.md` — que
> continuam válidos como registro histórico, mas ficaram genéricos demais
> pra guiar implementação. Este doc nasce já sabendo exatamente o que o
> backend tem hoje (levantado nesta sessão: workbench de 9 abas, 3
> dialogs de configurações, 70+ tools, storage lite/complete, MCP em
> `/mcp`), então cada sprint mapeia pra um recurso real que já existe
> internamente — não é desenho especulativo.

---

## Por que isso importa

Hoje o Vectora só é acessível por três portas: **chat web** (SPA, autenticação por cookie httpOnly, sem versionamento de API), **CLI** (uso local), e **MCP** (delegação de tools pra outro agente, não uma API de produto). Nenhuma dessas portas serve pra o caso de uso que o usuário pediu: **um terceiro construir um produto próprio em cima do Vectora, sem acesso ao código-fonte, só à borda da API** — a mesma lógica do Cursor/Linear/Notion, mas aplicada ao próprio Vectora como plataforma, não só como produto fechado.

Isso é literalmente o modelo de **Licenciamento OEM** já desenhado em `documents/business-model.md` ("uma empresa compra uma licença, constrói um produto próprio em cima da API, vende assinatura própria") — hoje esse modelo **não tem API pra sustentá-lo**. Este roadmap é o que faz o OEM sair do papel.

## O que já existe vs. o que falta (não confundir)

| Já existe (internamente)                                                            | Onde                                      | Falta pra virar API pública                                                                                                                  |
| ----------------------------------------------------------------------------------- | ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Chat com streaming, threads, HITL                                                   | SSE interno do frontend                   | Versionar, autenticar via API key/OAuth2 (não cookie), documentar, dar suporte a WebSocket como alternativa ao SSE                           |
| Workbench (files, git, terminal, RAG, context graph, plans, tasks, search, preview) | Endpoints internos consumidos só pela SPA | Mesma coisa: expor como recursos REST versionados, com schema Pydantic público e OpenAPI                                                     |
| Settings (Preferências, Ambiente, Administração)                                    | Endpoints internos da SPA                 | Idem — hoje é UI-only, precisa virar CRUD via API                                                                                            |
| Auth (JWT + cookie, RBAC, invites)                                                  | `backend/services/auth.py`                | Expor fluxo equivalente pra clientes não-browser (token opaco/JWT direto na resposta, sem depender de cookie)                                |
| MCP server                                                                          | `/mcp`, sempre-ativo                      | Autenticação já pública; escrita/terminal agora exigem `mcp_write_approved` por workspace (gate, não HITL síncrono — ver §MCP abaixo)        |
| `/v1/classify`, `/v1/extract`, `/v1/jobs`+SSE                                       | `backend/api/handlers/v1/`                | Já é o padrão certo (rate limit por tier, schema Pydantic, OpenAPI automático) — os sprints abaixo replicam esse padrão pros outros recursos |

**Princípio central**: nenhum sprint abaixo reescreve lógica de negócio. Cada endpoint novo é uma casca fina sobre o serviço/handler que já existe pro chat web — o trabalho é de **exposição, autenticação, versionamento e documentação**, não de reimplementação.

---

## Princípios cardinais (herdados + específicos da API)

1. **Auth-first, sempre via token — nunca cookie.** Cookie httpOnly continua exclusivo da SPA. Todo endpoint `/v1/*` novo autentica via `Authorization: Bearer` (API key ou token OAuth2 client credentials), nunca por sessão de navegador.
2. **Schema-first.** Todo endpoint tem Pydantic request/response, aparece em `/openapi.json` automaticamente — sem exceção, sem endpoint "informal".
3. **HITL não é opcional pra terceiros.** Uma tool call destrutiva disparada via API **ainda** pausa — o terceiro recebe um evento `interrupt` (via SSE/WebSocket/webhook) e resolve via endpoint dedicado. Não existe modo "bypassa aprovação porque é API".
4. **Rate limit por tier, sempre.** Todo endpoint novo entra no mesmo esquema já usado por `/v1/classify` (Free 10/min, Pro 100/min) — ninguém fica de fora.
5. **v1 é aditivo.** Breaking change vira `/v2`, nunca uma mudança silenciosa em `/v1`.
6. **O que NÃO expor.** Conteúdo bruto do vault de secrets (`.kdbx`), DSN de banco, chave JWT do servidor, e qualquer endpoint que já não seja auditado no chat web — a API não é uma porta dos fundos pra coisas que nem o próprio usuário root vê na UI.
7. **Todo endpoint novo nasce com teste.** Par caminho-feliz + caminho-de-erro no mesmo arquivo, seguindo `documents/testing-guide.md` — sem exceção pra "é só um CRUD simples".

---

## Sprints

### Sprint API-1 — Fundação de autenticação de terceiros

Sem isso, nenhum sprint depois faz sentido.

- **OAuth2 client credentials** (retoma J1 do `plan.md`): um terceiro registra uma "aplicação" (client_id/client_secret), troca por um `access_token` de curta duração via `POST /v1/oauth/token`.
- **API keys com escopo** (`read`/`write`/`admin`) como alternativa mais simples pra integrações server-to-server sem fluxo OAuth completo — reaproveita o mesmo modelo de escopos já usado no dashboard do `company` (ver `company/src/server/fns/api-keys.ts` como referência de padrão, adaptado pro backend Vectora).
- **Middleware bearer + scopes** (J2): todo handler `/v1/*` novo declara o escopo mínimo exigido; middleware único valida token + escopo antes de qualquer lógica de negócio.
- **Rate limit unificado**: generalizar `tier_rate_limit` (hoje só em classify/extract/jobs) pra um decorator aplicável a qualquer router novo.

**Exit**: um cliente externo troca credenciais por um token e chama um endpoint protegido com sucesso; sem token ou com escopo errado, recebe 401/403 consistente.

**Arquivos**: `backend/api/middleware/auth.py` (extensão), `backend/api/handlers/v1/oauth.py` (novo), `backend/services/api_keys.py` (novo, ou reaproveitar padrão de `backend/services/auth.py`).

---

### Sprint API-2 — Auth de usuário via API

- `POST /v1/auth/signup`, `POST /v1/auth/login`, `POST /v1/auth/logout`, `POST /v1/auth/refresh`, `GET /v1/auth/me`.
- Reaproveita 100% a lógica de `backend/services/auth.py` — só muda o transporte: resposta traz o token no corpo (`access_token`, `refresh_token`), não em cookie.
- RBAC (`root`/`admin`/`member`/`viewer`) e convites (`POST /v1/admin/invites`) entram aqui ou no Sprint API-8 (Administração) — decidir na hora, dependendo de qual sprint estiver ativo primeiro.

**Exit**: um app terceiro autentica um usuário final do Vectora (signup ou login) e opera em nome dele via Bearer token, sem nunca tocar em cookie.

---

### Sprint API-3 — Chat & Threads

O núcleo da "edge" — se só um sprint pudesse ser feito, seria este.

- `GET/POST /v1/threads`, `DELETE /v1/threads/{id}`
- `GET /v1/threads/{id}/messages`, `POST /v1/threads/{id}/messages` (enviar mensagem)
- `GET /v1/threads/{id}/stream` (SSE) **e** `GET /v1/threads/{id}/ws` (WebSocket) — os dois transportes, cliente escolhe.
- **HITL via API**: quando uma tool call pede aprovação, o stream emite `{"type": "interrupt", "interrupt_id": "...", "tool": "...", "diff_preview": "..."}`. O terceiro resolve com `POST /v1/threads/{id}/interrupts/{interrupt_id}/resolve {"decision": "approve"|"edit"|"reject", ...}`.
- Modos de permissão (perguntar sempre/aceitar edições/autônomo/plano) configuráveis por requisição ou por thread, mesmo enum já usado no chat web.

**Exit**: um cliente CLI/mobile próprio de um terceiro manda mensagem, recebe streaming, e aprova uma ação destrutiva via API pura — replica o fluxo do chat web sem usar nenhuma linha da SPA.

**Arquivos**: `backend/api/handlers/v1/threads.py` (novo), reaproveita `backend/services/agent_factory.py` e o adapter de streaming já existente (`backend/api/adapters.py`).

---

### Sprint API-4 — Workspaces & Files

- `GET/POST /v1/workspaces`, `POST /v1/workspaces/{id}/trust`
- `GET /v1/workspaces/{id}/files` (árvore), `GET /v1/workspaces/{id}/files/{path}` (ler), `PUT` (escrever/editar), `DELETE` (lixeira/permanente), `POST .../pin`
- `GET /v1/workspaces/{id}/files/{path}/history` (versões via git log/show)

Toda a lógica de trust folder, safe roots e anti-traversal (`resolve_within_workspace`) já existe e é reaproveitada — a API só herda essas garantias, não reimplementa.

**Exit**: CRUD completo de arquivos de um workspace via API, com os mesmos gates de segurança do chat web (sem escrita em pasta não confiável, sem escapar do workspace).

---

### Sprint API-5 — Git & Terminal

- `GET /v1/workspaces/{id}/git/status`, `/diff`, `/log`, `/branches`; `POST .../commit`, `/push`, `/pull`, `/stash`, `/worktrees`
- `POST /v1/workspaces/{id}/terminal` (cria sessão PTY) + `GET /v1/workspaces/{id}/terminal/{session_id}/ws` (stream bidirecional real, mesmo PTY do chat web)

Terminal via API é a superfície mais sensível deste roadmap — herda HITL e trust folder sem exceção, e é candidato natural a ficar **Pro-only** ou atrás de um escopo `admin` dedicado (decisão de produto, não técnica).

**Exit**: operações git completas + um terminal interativo de verdade via WebSocket, ambos gated exatamente como no chat web.

---

### Sprint API-6 — RAG, Context Graph & Search

- `POST /v1/workspaces/{id}/rag/ingest`, `GET/POST .../rag/search`, `GET/DELETE .../rag/collections`
- `POST /v1/workspaces/{id}/graph/build`, `GET .../graph/status`, `POST .../graph/query`, `.../graph/explain`
- `GET /v1/workspaces/{id}/search` (busca em arquivos, com suporte a regex via prefixo `r:`, mesma convenção da workbench)

**Exit**: um terceiro indexa conhecimento e busca via API sem nunca abrir o chat web — habilita, por exemplo, um bot de Slack que responde com RAG do Vectora.

---

### Sprint API-7 — Plans, Tasks & Webhooks

- `GET /v1/threads/{id}/artifacts` (planos/specs gerados pelo agente)
- `GET/POST /v1/tasks`, `POST /v1/tasks/{id}/run`, `GET /v1/tasks/{id}/logs`, `DELETE /v1/tasks/{id}` — CRUD das tarefas em segundo plano hoje só na aba Tasks da workbench
- **Webhooks de saída** (novo — hoje o Vectora só _recebe_ webhooks de terceiros pra tarefas, nunca emite os próprios): `POST /v1/webhooks` registra uma URL + lista de eventos (`thread.completed`, `task.run.finished`, `hitl.interrupt`, `context_graph.build.done`); o Vectora chama essa URL quando o evento acontece, com assinatura HMAC no header pra o terceiro validar autenticidade.

**Exit**: um terceiro registra um webhook e recebe eventos assíncronos sem fazer polling em nenhum endpoint.

---

### Sprint API-8 — Settings (Preferências, Ambiente, Administração)

Espelha 1:1 os três dialogs de configurações já mapeados em `documents/` (ver a página `guides/using-settings` do novo site de docs):

- `GET/PATCH /v1/me/preferences` (tema, idioma, system prompt, fallback de modelos), `GET/POST/DELETE /v1/me/memories`
- `GET/POST/DELETE /v1/me/envs`, `GET/POST/DELETE /v1/skills`, `GET/POST/DELETE /v1/mcp-plugins` (+ tool policy por plugin), `GET/POST/DELETE /v1/integrations`
- `GET/PATCH/DELETE /v1/admin/users`, `POST/DELETE /v1/admin/invites`, `PATCH /v1/admin/tools/{name}/toggle`, `GET/POST/DELETE /v1/admin/safe-folders`, `GET /v1/admin/system`, `GET/PATCH /v1/admin/config`

**Exit**: um painel administrativo construído por um terceiro gerencia uma instância Vectora inteira (usuários, tools, config) só via API — sem nunca abrir o painel de Administração nativo.

---

### Sprint API-9 — OpenAPI, Docs & SDKs

- OpenAPI polido: descrições ricas, exemplos de request/response em todo endpoint (não só schema técnico), tags organizadas por recurso (Auth, Threads, Workspaces, Files, Git, RAG, Tasks, Webhooks, Settings, Admin).
- `docs.vectora.company/docs/api-reference` (o site Hugo migrado) passa a ter uma página por recurso, gerada ou validada em CI contra o `/openapi.json` real — nunca mais diverge do que existe de fato (é exatamente o problema que motivou a reescrita do site).
- SDKs oficiais: `pip install vectora-sdk` (Python) e `@vectora/sdk` (TypeScript), thin wrappers tipados sobre o OpenAPI — sem lógica própria além de conveniência de chamada + tipos.
- Compatibilidade com a API da OpenAI (J4 do `plan.md`) como opção, não obrigação — permite apontar SDKs OpenAI existentes pro Vectora quando fizer sentido pro caso de uso do terceiro.

**Exit**: alguém de fora do time roda `pip install vectora-sdk`, segue o quick-start dos docs, e manda a primeira mensagem em menos de 5 minutos.

---

### Sprint API-10 — Hardening & Compliance

Fecha o que falta do Bloco J (`plan.md`) além dos recursos de produto:

- Encryption at rest onde ainda não existe (Frente A do Bloco J).
- Auditoria de toda chamada `/v1/*` externa (quem, quando, escopo usado, resultado) — extensão da tabela de audit já existente.
- Testes de carga nos endpoints mais sensíveis (terminal via WebSocket, streaming de chat) e uma rodada de revisão de segurança dedicada (`/code-review` ou pentest externo) antes de anunciar a API como GA.

**Exit**: `scons tests` cobre 100% dos endpoints novos com par feliz/erro (nenhum endpoint sem teste, por `documents/testing-guide.md`); relatório de auditoria de segurança sem findings críticos abertos.

---

## Ordem recomendada e dependências

```
API-1 (auth de terceiro) ──┬── API-2 (auth de usuário)
                            │
                            ├── API-3 (chat/threads) ──┐
                            ├── API-4 (workspaces/files)│
                            ├── API-5 (git/terminal)    ├── API-9 (OpenAPI/docs/SDKs)
                            ├── API-6 (RAG/graph/search)│
                            ├── API-7 (tasks/webhooks)  │
                            └── API-8 (settings)  ──────┘
                                                          └── API-10 (hardening, por último)
```

API-1 é bloqueante de tudo. API-2 a API-8 podem rodar em paralelo entre si (cada um toca um recurso diferente do backend, sem sobreposição de arquivos). API-9 só faz sentido depois que a superfície principal (pelo menos API-2 a API-4) estiver estável — documentar uma API que ainda muda todo dia é retrabalho. API-10 fecha o roadmap, não abre.

## Relação com o resto do produto

- **Não substitui o MCP.** MCP continua sendo o mecanismo de _delegação entre agentes_ (Claude Code chamando Vectora como sub-agente); esta API é o mecanismo de _terceiros construindo produtos_ em cima do Vectora. São públicos os dois, mas servem casos de uso diferentes — ver `documents/extensibility-roadmap.md` §1 pra o continuum skill → MCP → extensão, que é ortogonal a este roadmap. Diferente do resto da API pública (autenticação por API key/JWT é a única barreira), o MCP tem uma segunda camada além da autenticação: escrita de arquivo/edição/terminal via `/mcp` exigem aprovação explícita e persistida por workspace (`Workspace.mcp_write_approved`, `POST /workspaces/approve-mcp-write`) — um client MCP autenticado que nunca recebeu essa aprovação lê normalmente mas não muta nada. Ver `documents/agent-core-roadmap.md` §4 e `docs/content/en/guides/mcp-integration.md` para o detalhe completo.
- **Viabiliza o Licenciamento OEM** de `documents/business-model.md` — sem esta API, o tier OEM ali descrito não tem o que vender.
- **Alimenta o Bloco L** (`plan.md`) — SDKs, GitHub Actions oficiais e a integração com n8n/Zapier/Make citada em `documents/market-and-positioning.md` dependem de API-9 estar pronto primeiro.
