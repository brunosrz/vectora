# Vectora — Roadmap de Extensibilidade

> Mapa único de para onde a extensibilidade do Vectora vai: SDK de extensões
> (`.vext`, ainda não iniciado), registry de MCP servers (parcialmente real),
> biblioteca de skills (parcialmente real) e modalidades de IA além de texto
> (imagem/voz/vídeo já shippam via as tools nativas; falta câmbio de faixa
> pra STT e infraestrutura dedicada).
>
> **Estado atual do produto** (ver `history.md` — "O Vectora hoje"): local-first,
> sem cloud obrigatória. Free roda 100% local sem conta; Pro é opcional e
> cobre trial/billing/licenciamento via `services.vectora.company`, um
> **Cloudflare Worker pequeno** (não um "Vectora Cloud" rodando o produto de
> terceiros). Os catálogos de MCP e skills já vivem nesse worker (D1); o de
> extensões continua placeholder.

---

## 1. Panorama: quatro mecanismos, um continuum

O Vectora tem hoje (ou terá) quatro formas de crescer além do core:

| Mecanismo             | Estado real hoje                                                                                                                                            | Empacota UI?     | Empacota tools Python?       | Buildado/assinado? |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ---------------------------- | ------------------ |
| **MCP server**        | Implementado: config por usuário (`~/.vectora/mcp/<user_id>.json`), catálogo em D1 + registro oficial + fallback local, endpoints REST de install/uninstall | não              | não (processo externo)       | não                |
| **Skill**             | Implementado: instalação via git/path local por usuário, catálogo em D1 (curado + auto-discovery GitHub)                                                    | não              | não                          | não                |
| **Extensão `.vext`**  | Não iniciado — só design                                                                                                                                    | sim (proposto)   | sim (proposto)               | sim (proposto)     |
| **Modalidades de IA** | Parcial: imagem, TTS e vídeo (gen + análise) já são tools nativas; STT ainda não existe                                                                     | parcial (ver §6) | n/a (é o core, não extensão) | n/a                |

Os três primeiros formam uma escada de escopo crescente: uma **skill** é só
comportamento (prompt + instruções, sem tools novas); um **MCP server**
adiciona tools novas via protocolo, sem UI; uma **extensão `.vext`** seria o
container guarda-chuva que empacota as duas coisas junto com UI nativa (abas
de workbench, render hints, comandos) — esse terceiro nível ainda não existe
em código, é puro design (§2). MCP e skills já funcionam como mecanismos
standalone reais, só sem a CLI dedicada e sem sandbox/assinatura que o
roadmap original previa (ver §3, §4).

Modalidades de IA (imagem, voz, vídeo) são diferentes em natureza: não são
mecanismo de terceiro, são capability do próprio core (`backend/tools/
media.py`), expostas como tools que qualquer skill/MCP client já pode
chamar hoje.

---

## 2. SDK de extensões (`.vext`)

**Nenhum código deste mecanismo existe ainda** — sem `vectora_ext`, sem
Extension Host, sem `.vext` no repositório. Esta seção é inteiramente
design/roadmap, mantida porque justifica escolhas já tomadas em MCP e
skills (formato de manifesto, scopes, verbos de CLI — ver §5) que foram
desenhadas para caber neste mecanismo maior quando ele existir.

### 2.1 Por que existir

MCP cobre só tools de terceiro via protocolo; skills cobrem só prompt +
instruções. Nenhum dos dois permite o que uma extensão de VS Code permite:
adicionar uma aba nova no workbench, um conjunto de tools nativas, um card
de integração, um render hint e comandos de barra — tudo num pacote único,
assinado, versionado e instalável em um clique, rodando tanto no desktop
(Electron + backend compilado) quanto no self-hosted (FastAPI + SPA).

### 2.2 Modelo conceitual: contribuições + Extension Host

Mesmo modelo mental do VS Code: uma extensão **declara contribuições** num
manifesto e um **Extension Host** as ativa — despacho schema-driven, sem
o core precisar conhecer código de cada extensão (o mesmo princípio já
usado por `render_hint`, ver `frontend/lib/types/render.ts`).

```
                       my-extension.vext  (arquivo único, ZIP assinado)
                                  │  install
        ┌─────────────────────────┴──────────────────────────┐
        ▼                                                      ▼
 BACKEND HOST (FastAPI/Python)                        FRONTEND HOST (SPA/React)
 backend/services/extensions/host.py (a criar)        frontend/lib/extensions/host.ts (a criar)
   • descobre + valida + assina                          • carrega bundles UI (ESM/iframe)
   • registra tools no TOOL_REGISTRY                      • monta abas no workbench-store
   • monta skills/mcp no agent_factory                    • registra render hints
   • aplica permissions + sandbox                         • registra slash commands
   • expõe via /tools/schema                              • integra cards de Settings
```

Princípio cardinal: a extensão **nunca** é compilada dentro do binário
distribuído. Seria sideloaded em runtime a partir de
`~/.vectora/extensions/<user_id>/<ext_id>/` — exatamente como um `.vsix`
não é compilado dentro do VS Code. O core fecha (proprietário, compilado
via Nuitka+PyInstaller — ver `documents/launch-and-distribution.md` §1); as
extensões abrem (SDK open source, instaláveis sem rebuild do produto).

### 2.3 Formato de pacote (proposto)

Nenhum formato existente (`.vsix`, `.whl`, `.crx`) serve direto — cada um
é acoplado ao próprio runtime. Todos eles, porém, são ZIP por baixo, então
o Vectora reaproveitaria o container (ZIP universal, streamable, toolchain
madura) e definiria apenas o layout interno + manifesto + esquema de
assinatura:

```
acme-email.vext   (ZIP)
├── vectora-extension.json     # manifesto (obrigatório)
├── README.md / CHANGELOG.md / LICENSE / icon.png
├── backend/                    # contribuições Python (opcional)
│   ├── tools.py                # @ext.tool(...)
│   ├── hooks.py                # @ext.on_event(...)
│   └── vendor/                 # wheels das deps (sem rede no install)
├── node/dist/index.js          # runtime Node/TS de backend (opcional)
├── ui/dist/index.js            # contribuições de frontend (opcional), ESM
├── skills/*.skill.md           # skills empacotadas (opcional)
├── mcp/servers.json            # MCP servers declarados (opcional)
└── SIGNATURE                   # assinatura destacada (minisign/GPG)
```

Todas as pastas seriam opcionais. O manifesto `vectora-extension.json`
declararia `permissions` (network/filesystem/secrets/spawn_processes),
`contributes` (tools, workbench_tabs, slash_commands, render_hints,
integrations, settings, skills, mcp_servers) e `entrypoints`
(backend/node/ui). Schema versionado (`manifest_version`), validado por
Pydantic no backend e Zod no frontend.

### 2.4 Pontos de contribuição

Cada tipo de contribuição mapearia pra infraestrutura que já existe hoje —
o host só conectaria, não reescreveria o core:

| Contribuição    | Reusa (código real hoje)                                                         |
| --------------- | -------------------------------------------------------------------------------- |
| tools           | `backend/tools/registry.py` (`vtool`, `TOOL_REGISTRY`), `backend/nodes/tools.py` |
| workbench_tabs  | `workbench-store.ts`, `frontend/components/workbench/`                           |
| slash_commands  | `frontend/lib/constants/` (comandos de barra existentes)                         |
| render_hints    | `tool-call-renderer.tsx`, `frontend/lib/types/render.ts`                         |
| integrations    | handlers OAuth (`backend/api/handlers/oauth.py` se existir) + vault de secrets   |
| settings        | store de settings do frontend                                                    |
| skills          | `backend/workspace/skills.py`, `backend/services/agent_factory.py`               |
| mcp_servers     | `backend/workspace/plugins.py`, `backend/tools/mcp.py`                           |
| hooks (eventos) | dispatcher de eventos de ciclo de vida (novo)                                    |

### 2.5 Os dois SDKs (propostos)

**Python** (`vectora-extension-sdk`, import `vectora_ext`) — API
declarativa espelhando o `@vtool` nativo (`backend/tools/registry.py`):

```python
from vectora_ext import extension, ToolContext

ext = extension(id="acme.email")

@ext.tool(render_hint="table", category="communication")
async def email_search(query: str, ctx: ToolContext) -> list[dict]:
    """Busca emails na caixa de entrada do usuário."""
    creds = await ctx.secret("EMAIL_PASSWORD")
    ...
```

CLI de autoria: `vectora-ext init|build|sign|validate|publish`.

**TypeScript** (`@vectora/extension-sdk`) cobriria dois cenários: (a)
contribuições de UI via `defineExtension()`, consumido pelo host do
frontend ao carregar o bundle ESM; (b) lógica de backend em Node/TS via
`defineBackend()`, rodando como sidecar com harness JSON-RPC sobre
stdio — o mesmo padrão de um MCP server stdio, reaproveitando a infra real
descrita em §3.

### 2.6 Compatibilidade com o binário compilado

O ponto não-trivial: o core é compilado (Nuitka `--mode=package` +
PyInstaller `--onedir`, ver `launch-and-distribution.md` §1.1); extensões
precisam rodar sem recompilar o binário.

- **Backend Python `in-process`** (extensões confiáveis/first-party): o
  host adiciona a extensão ao `sys.path` e importa via `importlib` — o
  CPython empacotado interpreta módulos externos em runtime. Deps de
  terceiros viriam vendorizadas como wheels dentro do `.vext` — zero pip
  no install.
- **Backend Python `subprocess`/sandbox** (default para terceiros
  não-assinados): processo separado com interpretador próprio, falando
  JSON-RPC — idêntico ao modelo MCP stdio já usado por
  `backend/tools/mcp.py`.
- **Frontend TS**: bundle ESM servido pelo FastAPI, carregado via
  `import()` dinâmico; UI não-confiável rodaria em `<iframe>`
  sandboxed/`<webview>`.
- **Node sidecar**: o host spawnaria o processo Node como subprocesso
  assíncrono; Node não é embutido no binário — seria requisito de sistema
  declarado, e a ausência dele desabilitaria a extensão com erro tipado,
  não crash.

### 2.7 CLI do usuário (proposta)

Espelharia a sintaxe REST hoje exposta por MCP/skills (§3, §5) para um
único padrão de aprendizado:

```bash
vectora ext list / search / install <fonte> / info / enable|disable
vectora ext update / remove / permissions
```

Hoje `backend/cli/` não tem nenhum comando `mcp`/`skills`/`ext` — MCP e
skills são gerenciados via REST (`/mcp/*`, `/skills/*`) consumido pela SPA,
não por CLI. Uma CLI de gerenciamento paritária é trabalho futuro comum às
três frentes, não só extensões.

### 2.8 Segurança e trust (proposta)

Reaproveitaria o modelo de MCP quando este ganhar sandbox/assinatura (§3.3)
— não um esquema paralelo. Adicionaria duas camadas específicas de
extensão: ABAC por usuário (admin desabilita extensão/tool por usuário),
deny-globs herdados do filesystem (`.env`, `*.kdbx`, `.ssh/**`,
`master.kek` nunca legíveis mesmo com `filesystem: workspace` declarado), e
secrets resolvidos por nome via vault (a extensão nunca recebe a chave
crua no manifesto).

### 2.9 Critério de aceite

Três extensões first-party validariam as combinações de runtime/superfície
antes de abrir para terceiros — Python puro (`vectora-ruff`), Node sidecar
(`vectora-eslint`) e full-stack com OAuth/UI/skill (`vectora-email`). Sem
as três rodando de ponta a ponta pelo fluxo público de instalação, o SDK
não está pronto.

---

## 3. MCP: estado real e o que falta

### 3.1 O que já existe

Ao contrário de um mecanismo puramente aspiracional, MCP **já funciona em
produção** por dois caminhos:

- **Conexão fixa via settings** (`backend/tools/mcp.py::VectoraMCPClient`)
  — um servidor `stdio`/`sse`/`streamable_http` configurado globalmente via
  `mcp_server_url`/`mcp_command` nas Settings, exposto como a tool única
  `call_mcp_tool`.
- **Marketplace por usuário** (`backend/workspace/plugins.py` +
  `backend/api/handlers/mcp_marketplace.py`) — cada usuário tem sua própria
  lista de servidores em `~/.vectora/mcp/<user_id>.json`, cada tool remota
  vira uma `ToolSpec` nativa individual (não uma tool-proxy genérica),
  resolvida via `GET /mcp/registry`, `POST /mcp/install`,
  `POST /mcp/uninstall`. As tools instaladas entram no toolset do agente do
  mesmo jeito que uma tool nativa — mesmo render, mesma rastreabilidade.

O que falta frente ao design original: **não há CLI** (`vectora mcp ...`
não existe — só REST), **não há sandbox** de processo `stdio` (o
subprocess roda com o allowlist mínimo de env vars, mas sem isolamento de
filesystem/rede via bubblewrap/sandbox-exec/AppContainer), e **não há
assinatura/verificação de manifesto**.

### 3.2 Registry: as três fontes reais

`list_registry()` (`backend/api/handlers/mcp_marketplace.py`) mescla três
fontes, nessa ordem de prioridade:

1. **Registry Vectora** — D1, curado, servido por
   `GET /registry/mcp` (`services/src/registry/routes.ts`). Populado por
   PR manual (seed em `services/migrations/0001_schema.sql`,
   `catalog_source='curated'`) e por um **cron automático**
   (`services/src/registry/discovery.ts::discoverMcp`, chamado pelo
   `scheduled()` do worker) que pagina `registry.modelcontextprotocol.io`
   e faz upsert — nunca sobrescrevendo uma linha curada.
2. **Registry oficial de MCP** (`registry.modelcontextprotocol.io`) —
   consultado direto pelo cliente Python
   (`backend/services/registry_client.py::fetch_official_mcp_registry`),
   catálogo amplo da comunidade, só servers com pacote npm/stdio (único
   transporte que `_connector_to_server` sabe converter em `McpServer`
   hoje).
3. **Fallback hardcoded** (`_REGISTRY` em `mcp_marketplace.py`) — seis
   conectores (Brave Search, Filesystem, GitHub, Postgres, Slack,
   Sequential Thinking), só entra se nem 1 nem 2 responderem.

As duas primeiras são buscadas em paralelo; a lista final ordena
verificados primeiro, resto alfabético. `list_wellknown_catalog`-equivalente
para MCP não existe (esse padrão é só de skills, ver §4).

### 3.3 O que falta construir

- **CLI** (`vectora mcp list/search/add/remove/enable/disable`) — hoje só
  REST via SPA.
- **Sandbox por padrão** para `stdio` não-verificado (bubblewrap/Linux,
  sandbox-exec/macOS, AppContainer/Windows).
- **Assinatura de manifesto** e badges de confiança na UI (`Verified by
Vectora`, `Signed by publisher`, `Community-listed`, `Unsigned`).
- **Scopes** (`user`/`workspace`/`project`) — hoje só existe isolamento por
  usuário (`~/.vectora/mcp/<user_id>.json`), sem workspace/project.
- **Registry custom por empresa** (`vectora mcp registry add <url>`) — não
  implementado; hoje só as três fontes fixas de §3.2.
- **Importador de outras ferramentas** (`vectora mcp import --from
claude-code`) — não implementado.

---

## 4. Skills: estado real e o que falta

### 4.1 O que já existe

Skills são reais e usadas em produção — `backend/workspace/skills.py` +
`backend/api/handlers/skills.py`:

- Instalação por **URL git** (`git clone --depth 1`) ou **path local**
  (cópia recursiva), uma pasta por skill em
  `~/.vectora/skills/<user_id>/<skill_id>/`, indexada em `index.json`.
- Validação mínima: a raiz precisa ter `SKILL.md` com frontmatter
  declarando `name` e `description` — sem isso a instalação é rejeitada.
  **Não há** validação de `version`/`tags`/`required_tools`/`tier_min`/
  `license`/`signature` — esses campos, descritos abaixo em §4.3 como
  formato-alvo, ainda não são impostos pelo instalador real.
  `list_skill_paths(user_id)` alimenta o resolver de skills do
  `agent_factory`.
- `install_skill_from_content` instala skills geradas em memória pelo loop
  de aprendizado do agente (sem passar por git/cópia).
- `POST /skills/publish` publica uma skill (sempre por URL git, nunca
  upload de blob) no catálogo remoto com `verified=0`, curadoria manual
  via `PATCH /registry/admin/skills/:id/verify`.
- `GET /skills/catalog` lê o catálogo remoto (D1, `skills_catalog`) — sem
  fallback hardcoded local: catálogo vazio é estado válido, não erro.

### 4.2 Registry: curadoria + auto-discovery

Igual a MCP, o catálogo de skills combina seed curado (PR manual,
`catalog_source='curated'`) com um cron de auto-discovery
(`discovery.ts::discoverSkills`) que busca repositórios GitHub públicos
contendo `SKILL.md` via code search — habilitado só quando `GITHUB_TOKEN`
está configurado no worker; sem ele, essa metade do discovery fica
desligada, sem erro. Skills.sh (cogitado inicialmente como terceira fonte)
foi descartado: exige `VERCEL_OIDC_TOKEN` só emitido dentro do runtime de
deploy da própria Vercel, inacessível a um Worker de terceiro (sem
alternativa de API key documentada até a data desta revisão).

Existe também um **catálogo well-known local** (`list_wellknown_catalog`,
`~/.vectora/skills-wellknown/` ou `VECTORA_SKILLS_WELLKNOWN_DIR`) — segunda
fonte de discovery sem rede, mesmo layout de uma skill instalada.

### 4.3 Formato-alvo (roadmap, não imposto hoje)

O formato `.skill.md` rico abaixo é o alvo de médio prazo — hoje só
`name`/`description` são obrigatórios e verificados pelo instalador real:

```markdown
---
id: prd-draft
name: PRD Draft
version: 1.2.0
description: Gera Product Requirements Document com contexto via RAG
author: vectora-official
tags: [product, pm, document, rag]
required_tools: [rag_search, docx_generate, workspace_read]
tier_min: pro
license: proprietary
signature: gpg:0x1234ABCD
---
```

Campos adicionais previstos: `requires_skills` (composição — uma skill
orquestrando outras), `hitl_required`, `cost_estimate`.

### 4.4 O que falta construir

- **CLI** (`vectora skills list/search/install/update/remove/create/
validate/test/build/sign/publish`) — hoje só REST.
- **Versionamento real** — o instalador atual não lê `version` do
  frontmatter nem impõe semver; não há `.vectora/skills.lock.json`.
- **Scopes** (`user`/`workspace`/`project`/`runtime`) — hoje só isolamento
  por usuário.
- **Composição** (`requires_skills`) — não resolvido pelo instalador.
- **Trust model completo** (badges, aviso de skill não-assinada antes de
  instalar) — hoje `verified` é só um bit no catálogo remoto, sem exibição
  de badge nem assinatura GPG verificada.
- **Conjunto de skills oficiais de lançamento** (code review, ADR, RFC,
  PRD, etc.) — nenhuma seed oficial existe ainda no catálogo curado.

---

## 5. Infraestrutura compartilhada: "um registry, três catálogos"

O desenho de registry único **já é real para dois dos três catálogos**:
`services/src/registry/routes.ts` serve `mcp` e `skills` como recursos
irmãos do mesmo Worker Hono, sobre as mesmas tabelas D1
(`mcp_catalog`/`skills_catalog`, `services/migrations/0001_schema.sql`),
com o mesmo padrão de busca (`?q=`, `?category=`), o mesmo fluxo de
curadoria (seed manual `catalog_source='curated'` + cron `scheduled()` em
`discovery.ts` que nunca sobrescreve uma linha curada) e o mesmo mecanismo
de publicação comunitária (URL git, `verified=0` até revisão de admin).

`GET /registry/extensions` continua um placeholder que devolve lista vazia
— depende do SDK de autoria e do Extension Host de §2, nenhum dos dois
existe ainda.

O que o design original previa e ainda não existe:

- **CLI unificada** (`vectora mcp`/`vectora skills`/`vectora ext`
  compartilhando verbos) — hoje cada catálogo só tem REST.
- **Scopes `project` > `workspace` > `user`** — hoje ambos os catálogos só
  isolam por usuário, sem workspace/project.
- **Registry custom por empresa** — não implementado para nenhum dos dois
  catálogos.
- **Badges de confiança na UI** — o dado (`vectora_verified`/`verified`)
  já existe nas duas tabelas D1; falta a superfície visual.

Onde os catálogos genuinamente divergem, permanecem separados: MCP nunca
empacota UI nem tools Python nativas (processo externo via protocolo);
skills nunca empacotam UI nem lógica nova, só compõem o que já existe;
extensões seriam o único mecanismo a empacotar UI e lógica de backend
juntas — ver tabela de §1.

---

## 6. Modalidades de IA (imagem, voz, vídeo)

### 6.1 O que já está em produção

Diferente do resto deste documento, esta frente **já shippa**:
`backend/tools/media.py` expõe `generate_image`, `text_to_speech`,
`generate_video` e `analyze_video` como tools nativas normais (mesmo
`@vtool`/`TOOL_REGISTRY` de qualquer outra tool), reutilizando o **provider
de chat já ativo na sessão** — não uma camada de abstração `Protocol`
separada por modalidade. Regra central: a tool nunca troca de provider por
conta própria; se o modelo ativo não suporta a modalidade
(`provider_supports(provider, "image"|"tts")`), devolve erro explicando (ex.:
"troque para Gemini/OpenAI, ou configure um modelo de imagem/voz nas
Settings para Ollama/OpenRouter") em vez de chamar silenciosamente outro
provider (e cobrar por uma API que o usuário não pediu).

Geração de vídeo (`generate_video`, Veo no Gemini) já existe, com polling
assíncrono (intervalo 10s, teto 900s) e distinção explícita entre "falhou"
e "não terminou a tempo" (`VideoGenerationTimeoutError` — o job pode seguir
rodando e sendo cobrado no provider mesmo após o timeout local).
`analyze_video` fecha o par gen+análise.

Saída: arquivo binário em `~/.vectora/artifacts/{session_id}/media/` — raiz
irmã de `create_artifact`, mas em subpasta própria (mídia é binário
imutável; regerar produz um arquivo novo, não uma versão do anterior via
histórico de artifact).

### 6.2 Gaps reais frente ao produto acabado

- **STT (fala → texto) não existe** — nenhuma tool `audio_transcribe`/
  `speech_to_text` no repositório hoje. É o único buraco de modalidade
  ainda não coberto.
- **Render hints declarados não batem com o enum do frontend** —
  `generate_image`/`text_to_speech` declaram `render_hint="image"`/`"audio"`
  em `ToolExtras`, mas `frontend/lib/types/render.ts::RenderHint` só lista
  `"image_preview"` (não `"image"`) e não tem nenhum valor `"audio"` — sem
  ajuste em um dos dois lados, essas tools caem no fallback genérico
  (`json`) em vez de um preview de imagem/player de áudio dedicado.
- **Sem entidade de asset persistida** — imagens/vídeos/áudios são hoje só
  um path de arquivo devolvido em JSON, não um `asset_id` referenciável via
  endpoint próprio; não há GC granular nem re-render barato sem embutir o
  blob.
- **Sem quota/HITL por custo dedicados** — a tool usa a chave/plano que já
  está configurado para chat; não há teto mensal nem aprovação HITL
  específica de custo de mídia.
- **Sem exposição fora do chat** — não há comando CLI (`vectora media
gen-image|transcribe|speak`) nem tool exposta a clientes MCP externos
  especificamente para mídia (hoje só acessível de dentro de uma conversa
  do próprio Vectora).

### 6.3 Roadmap: fechar os gaps, não redesenhar do zero

Como a capability central já existe, o trabalho restante é infraestrutura
ao redor, não a modalidade em si:

1. **STT** — nova tool `audio_transcribe`, mesmo padrão de
   `provider_supports`/erro explícito de `media.py`.
2. **Alinhar render hints** — decidir se o enum do frontend ganha
   `"image"`/`"audio"` como aliases de `"image_preview"`/um novo tipo
   `"audio_player"`, ou se as tools passam a declarar os hints que já
   existem no enum.
3. **Assets como entidades persistidas** — `asset_id` + `GET /assets/{id}`,
   pra thread sharing sem embutir blob e GC granular.
4. **Quotas por tier + HITL por custo** — cota mensal Free (local, sem
   custo) vs. Pro (cota generosa), BYOK bypassa a cota (mesmo modelo já
   aplicado ao LLM de chat).
5. **Exposição via CLI e MCP always-on** — `vectora media ...` e a mesma
   tool disponível a clientes MCP externos, sujeita às mesmas quotas.

Posicionamento (mantido do desenho original): isto não compete com
produtos de transcrição de reunião (diarização em tempo real, modo
stealth) — é modalidade de input/output do agente de produtividade.
Geração de imagem/vídeo cobre diagramas, mockups, ícones e redesenho
rápido de fluxo, não "arte generativa" como produto à parte.

---

## 7. Princípios cardinais (unificados)

1. **Escada de escopo, não mecanismos concorrentes.** Skill → MCP →
   extensão `.vext` é um continuum de "só comportamento" até "produto
   completo empacotado". Os dois primeiros degraus já existem em código; o
   terceiro é só design.
2. **Um registry, três catálogos — dois já reais.** MCP e skills já
   compartilham Worker, schema D1, fluxo de curadoria e verbos REST;
   extensões entram no mesmo desenho quando o SDK existir.
3. **`services` é o backend de todos os catálogos.** O Cloudflare Worker
   que já serve auth/billing/license também serve os índices de MCP e
   skills — nenhum catálogo justificou (ou justificará) um serviço novo.
4. **Sandbox e assinatura por padrão para código não-confiável — ainda não
   implementado para nenhum mecanismo.** MCP `stdio` roda sem isolamento
   de processo hoje; skills não têm verificação de assinatura. É a maior
   lacuna de segurança das duas frentes já em produção.
5. **Core fechado, mecanismo de extensão aberto.** O produto continua
   compilado (Nuitka + PyInstaller); os SDKs de autoria e o formato
   `.vext` seriam open source quando existirem.
6. **Modalidades de IA são capability do core, não plugin — e já
   parcialmente entregue.** Imagem, TTS e vídeo já são tools nativas atrás
   do provider de chat ativo; falta STT e a infraestrutura de assets/quota
   ao redor (§6.3).
7. **Permissões explícitas, sempre.** Todo mecanismo (MCP, extensão,
   modalidade com custo) declara o que precisa; hoje isso vale para
   `env_vars` de servidores MCP e para o aviso de provider incompatível em
   mídia — falta estender pra consentimento explícito de permissões amplas
   (filesystem/network) quando sandbox existir.
8. **Nada disto é crítico para o lançamento.** As quatro frentes continuam
   roadmap pós-lançamento — o produto local-first de hoje não depende de
   nenhuma delas (nem das partes já implementadas) para funcionar.
