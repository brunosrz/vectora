# Vectora — Roadmap de Extensibilidade

> Consolida quatro frentes de roadmap que, isoladas, descreviam mecanismos
> sobrepostos de estender o agente: SDK de extensões (`.vext`), biblioteca
> de MCP servers, biblioteca de skills, e modalidades de IA além de texto
> (voz, imagem). Nenhuma delas está implementada — este documento é o mapa
> único de para onde a extensibilidade do Vectora vai, escrito uma vez em
> vez de três marketplaces quase-idênticos.
>
> **Estado atual do produto** (ver `history.md` — "O Vectora hoje"): local-first,
> sem cloud obrigatória. Free roda 100% local sem conta; Pro é opcional e
> cobre trial/billing/licenciamento via `services.vectora.company`, um
> **Cloudflare Worker pequeno** (não um "Vectora Cloud" rodando o produto de
> terceiros). Todo mecanismo de registry/marketplace descrito aqui é pensado
> para caber nesse worker — sem exigir um backend SaaS novo.

---

## 1. Panorama: quatro mecanismos, um continuum

O Vectora tem hoje (ou terá) quatro formas de crescer além do core:

| Mecanismo               | O que estende                                                                 | Empacota UI?              | Empacota tools Python?       | Buildado/assinado?        |
| ----------------------- | ----------------------------------------------------------------------------- | ------------------------- | ---------------------------- | ------------------------- |
| **MCP server**          | Tools de terceiros via protocolo MCP                                          | não                       | não (processo externo)       | parcial                   |
| **Skill (`.skill.md`)** | Prompt + tools requeridas (procedural)                                        | não                       | não                          | sim (assinatura opcional) |
| **Extensão `.vext`**    | Tools + UI + comandos + render hints + integrações + skills + MCP empacotados | sim                       | sim                          | sim                       |
| **Modalidades de IA**   | Capabilities novas do próprio core (TTS/STT/image gen)                        | sim (componentes nativos) | n/a (é o core, não extensão) | n/a                       |

Os três primeiros formam uma escada de escopo crescente: uma **skill** é só
comportamento (prompt + tools já existentes); um **MCP server** adiciona
tools novas via protocolo, sem UI; uma **extensão `.vext`** é o container
guarda-chuva que pode empacotar as duas coisas junto com UI nativa
(abas de workbench, render hints, comandos). Skills e MCP continuam
existindo como mecanismos standalone para casos simples — o `.vext` é
para quando alguém quer entregar uma experiência completa, análoga a uma
extensão de VS Code.

Modalidades de IA (voz, imagem) são diferentes em natureza: não são
mecanismo de terceiro, são capability nova do próprio produto, exposta
depois como tools que qualquer skill/extensão/MCP client pode chamar.

---

## 2. SDK de extensões (`.vext`)

### 2.1 Por que existir

MCP cobre só tools de terceiro via protocolo; skills cobrem só prompt +
tools requeridas. Nenhum dos dois permite o que uma extensão de VS Code
permite: adicionar uma aba nova no workbench, um conjunto de tools
nativas, um card de integração, um render hint e comandos de barra — tudo
num pacote único, assinado, versionado e instalável em um clique, rodando
tanto no desktop (Electron + binário Nuitka) quanto no self-hosted
(FastAPI + SPA).

### 2.2 Modelo conceitual: contribuições + Extension Host

Mesmo modelo mental do VS Code: uma extensão **declara contribuições** num
manifesto e um **Extension Host** as ativa — despacho schema-driven, sem
o core precisar conhecer código de cada extensão (o mesmo princípio já
usado por `render_hint`).

```
                       my-extension.vext  (arquivo único, ZIP assinado)
                                  │  install
        ┌─────────────────────────┴──────────────────────────┐
        ▼                                                      ▼
 BACKEND HOST (FastAPI/Python)                        FRONTEND HOST (SPA/React)
 backend/services/extensions/host.py                 frontend/lib/extensions/host.ts
   • descobre + valida + assina                          • carrega bundles UI (ESM/iframe)
   • registra tools no tool_resolver                     • monta abas no workbench-store
   • monta skills/mcp no agent_factory                   • registra render hints
   • aplica permissions + sandbox                        • registra slash commands
   • expõe via /tools/schema                             • integra cards de Settings
```

Princípio cardinal: a extensão **nunca** é compilada dentro do binário
Nuitka. É sideloaded em runtime a partir de
`~/.vectora/extensions/<user_id>/<ext_id>/` — exatamente como um `.vsix`
não é compilado dentro do VS Code. O core fecha (proprietário, Nuitka);
as extensões abrem (SDK open source, instaláveis sem rebuild do produto).

### 2.3 Formato de pacote

Nenhum formato existente (`.vsix`, `.whl`, `.crx`) serve direto — cada um
é acoplado ao próprio runtime. Todos eles, porém, são ZIP por baixo, então
o Vectora reaproveita o container (ZIP universal, streamable, toolchain
madura) e define apenas o layout interno + manifesto + esquema de
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

Todas as pastas são opcionais — uma extensão pode ser só-UI,
só-tools-Python, só-integração, ou qualquer combinação. O manifesto
`vectora-extension.json` declara `permissions` (network/filesystem/
secrets/spawn_processes), `contributes` (tools, workbench_tabs,
slash_commands, render_hints, integrations, settings, skills,
mcp_servers) e `entrypoints` (backend/node/ui). Schema versionado
(`manifest_version`) e validado por Pydantic no backend e Zod no
frontend. Strings de UI sempre por chave i18n — a extensão traz seu
próprio conjunto de traduções, mesclado em runtime.

### 2.4 Pontos de contribuição

Cada tipo de contribuição mapeia para infraestrutura que já existe hoje —
o host só conecta, não reescreve o core:

| Contribuição    | Reusa (código real)                                                  |
| --------------- | -------------------------------------------------------------------- |
| tools           | `tool_resolver.py`, `tool_policy.py`, `tools/__init__.py::ALL_TOOLS` |
| workbench_tabs  | `workbench-store.ts`, `components/workbench/`                        |
| slash_commands  | `constants/slash-commands.ts`                                        |
| render_hints    | `tool-call-renderer.tsx`, `types/render.ts`                          |
| integrations    | `api/handlers/oauth.py`, `services/secrets/`                         |
| settings        | `stores/settings-store.ts`                                           |
| skills          | `services/skills.py`, `agent_factory.py`                             |
| mcp_servers     | `services/plugins.py`                                                |
| hooks (eventos) | dispatcher de eventos de ciclo de vida (novo)                        |

### 2.5 Os dois SDKs

**Python** (`vectora-extension-sdk`, import `vectora_ext`) — API
declarativa espelhando o `@tool` do LangChain:

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

**TypeScript** (`@vectora/extension-sdk`) cobre dois cenários: (a)
contribuições de UI via `defineExtension()`, consumido pelo host do
frontend ao carregar o bundle ESM; (b) lógica de backend em Node/TS via
`defineBackend()`, rodando como sidecar com harness JSON-RPC sobre
stdio — o mesmo padrão de um MCP server stdio, reaproveitando
diretamente a infra descrita em §3.

### 2.6 Compatibilidade com Electron + Nuitka

O ponto não-trivial: o core é compilado por Nuitka onefile (fechado);
extensões precisam rodar sem recompilar o binário.

- **Backend Python `in-process`** (extensões confiáveis/first-party): o
  host adiciona a extensão ao `sys.path` e importa via `importlib` — o
  CPython embutido no onefile interpreta módulos externos em runtime.
  Deps de terceiros vêm vendorizadas como wheels dentro do `.vext` —
  zero pip no install.
- **Backend Python `subprocess`/sandbox** (default para terceiros
  não-assinados): processo separado com interpretador próprio, falando
  JSON-RPC — idêntico ao modelo MCP stdio, com o mesmo sandbox por SO
  (bubblewrap/sandbox-exec/AppContainer).
- **Frontend TS**: bundle ESM servido pelo FastAPI, carregado via
  `import()` dinâmico; UI não-confiável pode rodar em `<iframe>`
  sandboxed / `<webview>`.
- **Node sidecar**: o host spawna o processo Node como subprocesso
  assíncrono; Node não é embutido no binário — é requisito de sistema
  declarado (`engines`), e a ausência dele desabilita a extensão com
  erro tipado, não crash.

### 2.7 CLI do usuário

Espelha a sintaxe de `vectora mcp`/`vectora skills` (§3, §4) para um
único padrão de aprendizado:

```bash
vectora ext list / search / install <fonte> / info / enable|disable
vectora ext update / remove / permissions
```

Fontes de instalação: registry oficial, arquivo `.vext` local, URL, ou
`git+https://...`. Scopes (`user`/`workspace`/`project`) e precedência
idênticos aos de skills/MCP (§5).

### 2.8 Segurança e trust

Reaproveita diretamente o modelo descrito em §5 (assinatura, permissões
declaradas + consentidas, sandbox por default, badges de confiança, CVE
response) — **não** um esquema paralelo. Adiciona duas camadas
específicas de extensão:

- **ABAC por usuário**: admin pode desabilitar uma extensão (ou tools
  dela) por usuário via `tool_policy`.
- **Deny-globs herdados**: nenhuma extensão lê `.env`, `*.kdbx`,
  `.ssh/**`, `master.kek`, mesmo com `filesystem: ["workspace"]`
  declarado.
- **Secrets via vault**: a extensão nunca recebe a chave crua no
  manifesto; pede por nome (`ctx.secret("X")`) e o host resolve do vault
  do usuário.
- **Defensividade é do host, não da extensão**: toda tool de extensão é
  envolvida em `try/except` tipado pelo host — extensão buggada nunca
  derruba o grafo.

### 2.9 Provas de conceito

Três extensões first-party validam as combinações de runtime/superfície
antes de abrir para terceiros:

| Extensão         | Prova                                                                                      | Runtime |
| ---------------- | ------------------------------------------------------------------------------------------ | ------- |
| `vectora-ruff`   | SDK Python puro, tools in-process, diagnósticos, slash command                             | Python  |
| `vectora-eslint` | SDK TS, backend em Node sidecar (JSON-RPC stdio, modelo MCP)                               | Node    |
| `vectora-email`  | Full: Python + React + integração OAuth/secrets + aba nova no workbench + skill empacotada | Py + TS |

Sem as três rodando de ponta a ponta pelo fluxo público de instalação, o
SDK não está pronto — é o critério de aceite.

### 2.10 Roadmap de extensões de interação (pós-SDK)

Catálogo de extensões a construir depois de validar o SDK, todas via o
mesmo `.vext`:

| Extensão                | Categoria                                      | Runtime |
| ----------------------- | ---------------------------------------------- | ------- |
| `vectora-docker`        | devops (tools + UI de containers/logs)         | Python  |
| `vectora-prettier`      | formatter (tools + format-on-save)             | Node    |
| `vectora-pytest`        | testes (tools + test explorer)                 | Python  |
| `vectora-slack`         | interações (tools + integração + webhooks)     | Py + TS |
| `vectora-calendar`      | interações (tools + UI + OAuth)                | Py + TS |
| `vectora-jira`/`linear` | interações (tools + integração + render hints) | Python  |
| `vectora-postgres-cli`  | devops (query/introspect + storage browser)    | Python  |

Conectores comerciais pagos (Notion, Jira, Figma, Google Workspace e
similares) são pensados como **extensões `.vext` first-party pagas** —
mesmo formato, licença comercial, revenue-share sobre o mesmo registry
descrito em §6.

---

## 3. Registry de MCP servers

### 3.1 Por que existir

Descoberta de MCP servers hoje é manual (CLI + awesome-lists no GitHub) e
sem validação de segurança embutida. O Vectora resolve as três pontas:
descoberta integrada, instalação em um clique, sandbox e assinatura por
padrão.

MCP é o mecanismo para o **long tail** — qualquer server público do
ecossistema que não vale a pena tornar nativo nem embutir como extensão
first-party. Para o usuário, tools vindas de tool nativa, extensão `.vext`
ou MCP parecem iguais: mesmo render, mesma rastreabilidade, mesmo HITL.

### 3.2 Instalação e configuração

CLI paritária com Claude Code para facilitar migração:

```bash
vectora mcp list / search <termo> / inspect <server>
vectora mcp add <server> [--scope user|workspace|project] [--transport stdio|http|sse|ws]
vectora mcp add <server> --no-sandbox   # requer flag explícita
vectora mcp remove / config / env / enable / disable
vectora mcp sync                        # atualiza catálogo local
vectora mcp registry add|list|remove <url>   # registry custom de empresa
```

Transports suportados: `stdio` (binário local), `http`, `sse`, `ws`.
Manifest local em `~/.vectora/mcp.json`, com `permissions` declaradas por
server (internet, filesystem, spawn_processes) e `scope`
(`user`/`workspace`/`project`, precedência do mais específico).

Fluxo de instalação: resolve manifest do registry → verifica assinatura
→ exibe permissões para aprovação → sobe sandbox se aplicável → hot-load
no processo rodando (sem restart) → confirmação com contagem de tools
descobertas.

### 3.3 Sandbox por padrão

Servers `stdio` não-assinados rodam isolados por padrão
(bubblewrap/Linux, sandbox-exec/macOS, AppContainer ou WSL2/Windows),
restringindo filesystem, network, spawn de processos e acesso a env vars
ao que foi declarado. Desabilitar exige `--no-sandbox` explícito.
Servers `http`/`sse`/`ws` rodam remotos (sem sandbox local), mas toda
chamada passa pelo cliente Vectora, que loga input/output.

### 3.4 Registry: onde vive

O registry combina duas fontes:

- **Registry oficial Vectora** — cache local em
  `~/.vectora/mcp-registry/index.json`, sincronizado sob demanda
  (`vectora mcp sync`). A fonte remota é servida pelo endpoint
  `GET /registry/mcp` do worker `services` (`services/src/registry/routes.ts`)
  — hoje um placeholder que devolve lista vazia; o cliente já sabe cair
  para o índice local quando o remoto está vazio. Amadurecer esse
  endpoint (proxy real para o registro oficial do MCP e/ou
  `awesome-mcp-servers`) é trabalho futuro dentro do mesmo worker —
  não exige um serviço novo.
- **Registry custom por empresa** — qualquer organização pode hospedar o
  próprio índice (`vectora mcp registry add https://mcps.empresa.com/registry.json`)
  seguindo o mesmo schema, para MCPs internos sem expor publicamente.

Cada entrada do registry inclui `id`, `transport`, `install_command`,
`tools` expostas, `permissions` default, `signature`, `vectora_verified`,
`community_score` e `last_updated`.

### 3.5 Submissão e curadoria

1. PR no repositório público do registry adicionando a entrada.
2. Review automático (CI valida schema, roda testes do server).
3. Review manual de segurança.
4. Aprovado → entra como community-listed (`vectora_verified: false`).
5. Após instalações suficientes sem incidente de segurança em uma
   janela de tempo → promovido a `vectora_verified: true`.

### 3.6 Badges de confiança

| Badge               | Significa                                            |
| ------------------- | ---------------------------------------------------- |
| Verified by Vectora | Vectora revisou código/binários e assinou o manifest |
| Signed by publisher | Manifest assinado por GPG de organização verificada  |
| Community-listed    | No registry, sem review formal                       |
| Unsigned            | Sem assinatura — atenção ao instalar                 |
| Runs in sandbox     | Server stdio roda isolado                            |

CVE crítico em MCP instalado desabilita o server automaticamente até o
usuário revisar, com update sugerido em um clique.

### 3.7 Migração de outras ferramentas

Importador (`vectora mcp import --from claude-code`) lê a config
existente e instala equivalentes do registry, sinalizando o que não foi
encontrado ou está depreciado.

---

## 4. Biblioteca de skills

### 4.1 Formato `.skill.md`

Vectora adota o formato de Skills da spec Deep Agents (Anthropic), com
extensões mínimas. Uma skill é um único Markdown com frontmatter:

```markdown
---
id: prd-draft
name: PRD Draft
version: 1.2.0
description: Gera Product Requirements Document com contexto via RAG
author: vectora-official
tags: [product, pm, document, rag]
required_tools: [rag_search, docx_generate, workspace_read]
required_extensions: [] # extensões .vext opcionais, com fallback se ausentes
tier_min: pro
license: proprietary
signature: gpg:0x1234ABCD
---

## Quando usar

...

## Como executar

...

## Exemplos de prompts

...
```

Campos obrigatórios: `id`, `name`, `version` (semver), `description`,
`author`, `tags`, `required_tools`. Opcionais notáveis: `requires_skills`
(composição — uma skill orquestrando outras), `tier_min`, `hitl_required`,
`cost_estimate`.

### 4.2 CLI e scopes

```bash
vectora skills list / search <termo> / inspect <skill>
vectora skills install <skill>[@versão] [--scope user|workspace|project]
vectora skills install <url> | git+<repo>
vectora skills update [--all] / remove
vectora skills create <nome> / validate <arquivo> / test <arquivo>
vectora skills build . / sign . / publish . [--registry <url>]
```

Scopes idênticos ao de MCP e extensões: `user` → `workspace` → `project`
→ `runtime` (efêmero, só na sessão), mais específico vence em conflito de
`id`.

### 4.3 Composição e dependências

Skills podem requerer outras skills (`requires_skills`), formando
meta-workflows sem duplicar lógica (ex.: uma skill de "lançamento de
feature" orquestrando PRD + release notes + post + email). O install
resolve a árvore de dependências — de skills, tools nativas e, quando
aplicável, extensões `.vext` — e pergunta antes de instalar o que falta.

### 4.4 Versionamento

Semver estrito. Auto-update é opt-in por skill: PATCH aplica sem
confirmação, MINOR notifica antes de aplicar, MAJOR nunca é automático.
Pinning via `.vectora/skills.lock.json` garante reprodutibilidade entre
membros de um time.

### 4.5 Trust model

Mesmo espectro de badges do registry de MCP (§3.6): Verified by Vectora
(oficiais, assinadas, revisadas), Signed (community com assinatura GPG
verificada), Community-listed (sem review formal), e skills locais
(criadas pelo próprio usuário/empresa, sem badge, sem necessidade de
publicar). Instalar skill não-assinada exibe aviso explícito, já que
skills executam prompts arbitrários no agente.

### 4.6 Skills oficiais de lançamento

Conjunto inicial cobrindo Engineering (code review, ADR, RFC, release
notes, commit message, PR description), Product (PRD, síntese de
pesquisa, RICE, checklist de release), Documentation, Data e Compliance
— cada uma assinada, testada e documentada, definindo o padrão de
qualidade esperado da comunidade.

### 4.7 Pricing

Free por padrão — skills da comunidade e oficiais fazem parte do
ecossistema sem custo. Programa de skills pagas fica como possibilidade
futura (revenue-share com o publicador), reservado a casos de manutenção
contínua especializada; não é prioridade de lançamento.

---

## 5. Infraestrutura compartilhada: registry e marketplace

MCP e skills descrevem, cada um isoladamente, um "marketplace" quase
idêntico: sidebar de descoberta, cards com badge de confiança, CLI com
`list/search/install/remove`, scopes `user`/`workspace`/`project`,
registry oficial + registry custom por empresa, mesmo fluxo de submissão
via PR. Extensões `.vext` propõem reaproveitar esse mesmo modelo em vez
de inventar um terceiro.

Em vez de tratar como três marketplaces paralelos, o desenho é **um
mecanismo de registry, três catálogos**:

- **Um schema de manifest comum** (id, versão, autor, permissões,
  assinatura, badges de confiança, contagem de instalações) — só o
  payload muda (`tools`/`transport` para MCP, `required_tools`/frontmatter
  para skills, `contributes`/`entrypoints` para extensões).
- **Um fluxo de submissão/curadoria comum**: PR → review automático de
  schema → review de segurança → community-listed → verified após
  instalações sem incidente.
- **Um conjunto de scopes e precedência comum**: `project` > `workspace`
  > `user` (e `runtime` para skills efêmeras).
- **Uma única superfície de registry remoto**: o endpoint do worker
  `services` (hoje só `GET /registry/mcp`, retornando lista vazia) é o
  lugar natural para os três catálogos crescerem — `mcp`, `skills` e
  `extensions` como recursos irmãos do mesmo registry, não três workers
  diferentes. Isso mantém a promessa de "backend pequeno" do Vectora:
  um Cloudflare Worker servindo índices versionados, não uma plataforma
  de marketplace própria.
- **Uma CLI com um padrão só**: `vectora mcp`, `vectora skills` e
  `vectora ext` compartilham verbos (`list`, `search`, `install`,
  `remove`, `enable`/`disable`, `registry add/list/remove`) para que
  aprender um signifique aprender os três.

Onde os três catálogos genuinamente divergem, mantêm-se separados: MCP
não tem UI nem tools Python nativas (é sempre processo externo via
protocolo); skills não empacotam UI nem lógica nova, só compõem o que já
existe; extensões são o único mecanismo que empacota UI e lógica de
backend juntas. A tabela de §1 continua sendo a referência para essa
diferença de escopo.

---

## 6. Modalidades de IA (voz, imagem)

### 6.1 Escopo

Expandir o conjunto de modalidades de IA do produto de três (LLM chat/
code, embedding, reranker) para seis, adicionando **TTS** (texto → voz),
**STT** (voz → texto) e **geração/edição de imagem**. Diferente dos três
mecanismos anteriores, isso não é uma superfície de extensão de
terceiros — é capability nova do próprio core, depois exposta como tools
que qualquer skill, extensão ou cliente MCP pode chamar.

Posicionamento: isso não compete com produtos de transcrição de reunião
(diarização em tempo real, modo stealth) — é modalidade de input/output
do agente de produtividade. Geração de imagem cobre diagramas, mockups,
ícones e redesenho rápido de fluxo, não "arte generativa" como produto
à parte. Vídeo permanece fora de escopo (custo, latência e qualidade
ainda não competitivos para UX de chat).

### 6.2 Camada de abstração

Toda modalidade nova passa por um Protocol abstrato
(`ImageGenerator`, `Transcriber`, `Synthesizer`) com factories que
resolvem o provider por usuário/tier — mesmo padrão já usado para LLM,
para que trocar de provider seja mudança de config, nunca de código:

```python
class ImageGenerator(Protocol):
    async def generate(self, prompt: str, *, size, n, reference_images=None, style_hint=None) -> list[GeneratedImage]: ...
    async def edit(self, source: bytes, prompt: str, *, mask=None) -> GeneratedImage: ...

class Transcriber(Protocol):
    async def transcribe(self, audio: bytes, *, language=None, timestamps=False, diarization=False) -> Transcript: ...

class Synthesizer(Protocol):
    async def synthesize(self, text: str, *, voice, language=None, speed=1.0, ssml=False) -> AsyncIterator[bytes]: ...
```

### 6.3 Tools novas

`image_generate`, `image_edit`, `audio_transcribe`, `audio_synthesize` —
registradas como tools normais (render hints `image_preview`,
`image_grid`, `audio_player`, `transcript`), respeitando `tool_policy` e
HITL por custo estimado (billing-destructive, não filesystem-destructive).
Um node leve de classificação de intenção (`media_intent`) roteia pedidos
em linguagem natural ("cria uma imagem de...", "transcreve isso") para a
tool certa sem o usuário precisar saber qual tool chamar.

### 6.4 Assets como entidades persistidas

Imagens, áudios e transcrições gerados não viajam como blob embutido em
mensagem — viram `asset_id` referenciado, resolvido via endpoint próprio
(`GET /assets/{id}`). Isso mantém re-render barato, permite compartilhar
thread sem embutir o blob, e possibilita GC granular por asset.

### 6.5 Quotas, custo e BYOK

Cada modalidade nova tem quota mensal por tier (Free local não paga
nada; Pro tem cota generosa) e HITL automático acima de um limiar de
custo configurável. Usuário com chave própria (BYOK) de provider
bypassa a quota — mesmo modelo já aplicado a LLM de chat hoje.

### 6.6 UI e captura

Componentes novos no chat: preview de imagem com regenerar/editar/
baixar, grid para múltiplas imagens, player de áudio com waveform e
controle de velocidade, visualização de transcript com diarização
opcional. Captura de voz evolui do hook atual baseado em Web Speech API
(sem cobertura em todos os browsers) para um fallback via
`MediaRecorder` + endpoint de transcrição remoto, com indicação visível
de qual provider está ativo.

### 6.7 Exposição fora do chat

As mesmas tools ficam expostas via MCP (`/mcp`, sempre-ativo) e via CLI
(`vectora media gen-image|transcribe|speak|quota`), para que agentes
externos (Claude Code, outros clientes MCP) possam delegar geração de
mídia ao Vectora quando não tiverem capability própria — sujeito às
mesmas quotas do token configurado.

---

## 7. Princípios cardinais (unificados)

1. **Escada de escopo, não mecanismos concorrentes.** Skill → MCP →
   extensão `.vext` é um continuum de "só comportamento" até "produto
   completo empacotado". Cada um cobre o nível de esforço certo para o
   problema certo.
2. **Um registry, três catálogos.** MCP, skills e extensões compartilham
   schema de manifest, fluxo de curadoria, scopes e verbos de CLI — a
   infraestrutura de descoberta/instalação não se triplica.
3. **`services` é o backend de todos os catálogos.** O Cloudflare Worker
   que já serve auth/billing/license also serve os índices de
   registry — nenhum catálogo justifica um serviço novo.
4. **Sandbox e assinatura por padrão para código não-confiável.** Vale
   igualmente para MCP stdio, extensões de terceiro e skills
   não-assinadas.
5. **Core fechado, mecanismo de extensão aberto.** O produto continua
   compilado (Nuitka); os SDKs de autoria e o formato `.vext` são open
   source.
6. **Modalidades de IA são capability do core, não plugin.** TTS/STT/
   imagem entram como tools nativas atrás do mesmo Protocol de provider
   já usado para LLM — depois disso, sim, ficam disponíveis para
   qualquer skill/extensão/MCP client chamar.
7. **Permissões explícitas, sempre.** Todo mecanismo (MCP, extensão,
   modalidade com custo) declara o que precisa e o usuário aprova antes.
8. **Nada disto é crítico para o lançamento.** As quatro frentes são
   roadmap pós-lançamento — o produto local-first de hoje não depende
   de nenhuma delas para funcionar.
