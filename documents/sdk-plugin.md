# Vectora — Extension SDK & Plugin Runtime (`.vext`)

> Como o Vectora deixa de ser um produto fechado-extensível-só-por-MCP e
> passa a ter um **SDK de extensões open source** equivalente ao `.vsix`
> do VS Code: usuários (e a própria Vectora Company) empacotam **tools,
> interfaces, integrações, comandos e render hints** num único artefato
> buildado, instalável em 1 clique, que roda tanto no app desktop
> (Electron + binário Nuitka) quanto no modo self-hosted (FastAPI + SPA).
>
> **Por que existir:** hoje a extensibilidade do Vectora está fragmentada
> em três mecanismos que **não cobrem interface nem lógica nova de
> backend empacotada**: MCP servers (`mcp-library.md` — só tools de
> terceiros via protocolo), skills `.skill.md` (`skills-library.md` —
> só prompt + tools requeridas), e os plugins DLC Tier 2C
> (`products.md` — conceito comercial sem runtime real). Nenhum deles
> permite o que o VS Code permite: alguém escrever uma extensão que
> adiciona **uma aba nova no workbench**, **um conjunto de tools
> nativas**, **um card de integração**, **um render hint** e
> **comandos de barra** — tudo num pacote único, assinado, versionado e
> instalável. Este documento define esse mecanismo: o formato `.vext`, o
> SDK (Python **e** TypeScript), o Extension Host, e **3 plugins
> próprios** como prova de conceito.
>
> **Cardinal:** não basta desenhar o SDK — entregamos **suporte real**
> no produto (host de extensões no backend e no frontend) + **3
> extensões first-party funcionais** (`vectora-ruff`, `vectora-eslint`,
> `vectora-email`) que se instalam pelo mesmo fluxo que um terceiro
> usaria. Sem as 3 PoC rodando de ponta a ponta, o bloco não está
> concluído.

---

## 1. Posicionamento entre os mecanismos existentes

O Vectora já tem 3 formas de estender o agente. O Extension SDK é a
**camada que as unifica e adiciona o que falta (UI + lógica empacotada)**:

| Mecanismo                   | O que estende                                                                     | Empacota UI? | Empacota tools Python? | Buildado/assinado? | Doc                 |
| --------------------------- | --------------------------------------------------------------------------------- | ------------ | ---------------------- | ------------------ | ------------------- |
| **MCP server**              | Tools de terceiros via protocolo MCP                                              | ❌           | ❌ (processo externo)  | parcial            | `mcp-library.md`    |
| **Skill (`.skill.md`)**     | Prompt + tools requeridas (procedural)                                            | ❌           | ❌                     | ✅ (sign opcional) | `skills-library.md` |
| **Plugin DLC (Tier 2C)**    | Conceito comercial (conectores pagos)                                             | —            | —                      | — (sem runtime)    | `products.md`       |
| **Extensão `.vext` (este)** | **Tools + UI + comandos + render hints + integrações + skills + MCP empacotados** | ✅           | ✅                     | ✅                 | este                |

**Decisão de arquitetura:** a extensão `.vext` é o **container guarda-chuva**.
Uma extensão pode _conter_ uma ou mais skills (`.skill.md`), declarar um ou
mais MCP servers, e ainda adicionar tools nativas + UI. Skills e MCP
continuam existindo isolados para casos simples; o `.vext` é para quando se
quer entregar **uma experiência completa empacotada** (o equivalente a uma
extensão de VS Code, que pode trazer comandos + views + language server +
settings ao mesmo tempo).

Os **plugins DLC Tier 2C** (`products.md`) passam a ser, na prática,
extensões `.vext` first-party com licença comercial — o marketplace pago
reusa o registry de extensões. O programa de revenue-share 70/30 continua
válido sobre o mesmo formato.

---

## 2. Modelo conceitual: contribuições + Extension Host

Copiamos o modelo mental do VS Code (provado em escala): uma extensão
**declara contribuições** num manifesto e o **Extension Host** as ativa.
O backend (FastAPI) tem um host; o frontend (SPA) tem outro. Nenhum
código por extensão precisa ser conhecido pelo core — o despacho é
**schema-driven**, exatamente como já fazemos com `render_hint`
(princípio 6 do plano mestre).

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
   • expõe via /tools/schema (já existe)                 • integra cards de Settings
```

**Princípio cardinal:** a extensão **nunca** é compilada dentro do binário
Nuitka. Ela é **sideloaded em runtime** a partir de
`~/.vectora/extensions/<user_id>/<ext_id>/` — exatamente como um `.vsix`
não é compilado dentro do VS Code. Isso é o que torna o ecossistema
aberto: o core fecha (proprietário, Nuitka), as extensões abrem (SDK
open source, instaláveis sem rebuild do produto).

---

## 3. Formato de pacote: `.vext`

### 3.1 Existe formato pronto para reusar?

Avaliação honesta dos candidatos:

| Formato          | Container        | Por que **não** serve direto                                                                                                                           |
| ---------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `.vsix` (VSCode) | ZIP + OPC        | Manifesto (`extension.vsixmanifest`) e modelo de ativação **acoplados ao VS Code**; só Node/JS; não tem noção de tool de agente nem de backend Python. |
| `.whl` (Python)  | ZIP              | Só Python; sem UI, sem manifesto de contribuições, sem assinatura nativa.                                                                              |
| `.crx` (Chrome)  | ZIP + assinatura | Acoplado ao runtime do Chrome; modelo de permissões web, não de agente.                                                                                |
| `.zip` cru       | ZIP              | Sem manifesto, sem assinatura, sem versionamento.                                                                                                      |

**Conclusão:** não há formato cross-ecossistema (Python + TS + tools de
agente + UI) pronto. **Criamos o nosso**, mas **reaproveitando o
container que todos esses formatos já usam: ZIP**. `.vsix`, `.whl` e
`.crx` são todos ZIP por baixo — é a escolha de container correta
(universal, streamable, com toolchain madura em toda linguagem). O que
criamos é o **layout interno + manifesto + esquema de assinatura**, não
um container novo.

**Decisão:** `.vext` = arquivo **ZIP** com extensão renomeada, manifesto
`vectora-extension.json` na raiz, e assinatura destacada. Igual à
estratégia do `.vsix` (que é ZIP renomeado), mas com manifesto próprio
do Vectora.

### 3.2 Layout interno do `.vext`

```
acme-email.vext   (ZIP)
├── vectora-extension.json     # manifesto (obrigatório)
├── README.md                  # exibido no marketplace
├── CHANGELOG.md
├── LICENSE                     # SPDX; SDK e template são MIT
├── icon.png                    # 128×128, exibido na UI
├── backend/                    # contribuições Python (opcional)
│   ├── __init__.py
│   ├── tools.py                # @ext.tool(...)
│   ├── hooks.py                # @ext.on_event(...)
│   └── vendor/                 # wheels das deps (sem rede no install)
├── node/                       # runtime Node/TS de backend (opcional)
│   └── dist/index.js           # bundle único (esbuild)
├── ui/                         # contribuições de frontend (opcional)
│   └── dist/
│       ├── index.js            # ESM, default export = registro de contribuições
│       └── assets/
├── skills/                     # skills .skill.md empacotadas (opcional)
│   └── *.skill.md
├── mcp/                        # MCP servers declarados (opcional)
│   └── servers.json
└── SIGNATURE                   # assinatura destacada (minisign/GPG) do ZIP sem este arquivo
```

Todas as pastas (`backend/`, `node/`, `ui/`, `skills/`, `mcp/`) são
**opcionais** — uma extensão pode ser só-UI, só-tools-Python,
só-integração, ou qualquer combinação.

### 3.3 Manifesto `vectora-extension.json`

```jsonc
{
  "manifest_version": 1,
  "id": "acme.email", // <publisher>.<name>, único no registry
  "name": "Email",
  "version": "1.2.0", // semver estrito
  "publisher": "acme",
  "description": "Caixa de entrada e envio de email via IMAP/SMTP no Vectora.",
  "license": "MIT",
  "homepage": "https://github.com/acme/vectora-email",
  "icon": "icon.png",
  "categories": ["integrations", "communication"],
  "keywords": ["email", "imap", "smtp", "inbox"],

  "engines": { "vectora": ">=1.2.0" }, // compat de versão do host

  "permissions": {
    // mesmo modelo de mcp-library.md
    "network": ["imap.*", "smtp.*"], // allow-list de hosts
    "filesystem": ["workspace"], // "workspace" | path globs | false
    "secrets": ["EMAIL_PASSWORD", "GOOGLE_OAUTH_TOKEN"], // chaves no vault do user
    "spawn_processes": false,
  },

  "contributes": {
    "tools": [
      {
        "name": "email_search",
        "entry": "backend.tools:email_search",
        "render_hint": "table",
        "category": "communication",
        "destructive": false,
      },
      {
        "name": "email_send",
        "entry": "backend.tools:email_send",
        "render_hint": "code_block",
        "category": "communication",
        "destructive": true,
      },
    ],
    "workbench_tabs": [
      {
        "id": "inbox",
        "title_key": "ext.acme.email.inbox",
        "icon": "Mail",
        "ui_entry": "ui/dist/index.js#InboxTab",
      },
    ],
    "slash_commands": [
      {
        "command": "/email",
        "title_key": "ext.acme.email.cmd",
        "tool": "email_search",
      },
    ],
    "render_hints": [
      { "id": "email_thread", "ui_entry": "ui/dist/index.js#EmailThreadView" },
    ],
    "integrations": [
      {
        "id": "email",
        "env_var": "EMAIL_PASSWORD",
        "oauth": "google",
        "docs_url": "https://github.com/acme/vectora-email#setup",
      },
    ],
    "settings": [
      { "key": "acme.email.poll_interval_s", "type": "number", "default": 60 },
    ],
    "skills": ["skills/triage-inbox.skill.md"],
    "mcp_servers": "mcp/servers.json",
  },

  "entrypoints": {
    "backend": {
      "runtime": "python",
      "module": "backend",
      "isolation": "subprocess",
    },
    "node": { "runtime": "node", "main": "node/dist/index.js" },
    "ui": { "module": "ui/dist/index.js" },
  },
}
```

Schema versionado (`manifest_version`) e validado por Pydantic no backend
(`backend/types/extension.py`) + Zod no frontend
(`frontend/lib/extensions/manifest.ts`). Strings de UI **sempre por
chave i18n** (`*_key`) — a extensão traz seu próprio CSV de traduções
(`ui/i18n/strings.csv`), mesclado no `useT()` em runtime (princípio 2 do
plano mestre vale para extensões também).

---

## 4. Pontos de contribuição (contribution points)

Cada tipo de contribuição mapeia para infra **que já existe** no Vectora —
o host só conecta. Esta é a razão de o suporte ser viável sem reescrever
o core.

| Contribuição        | Como o host conecta                                                                                          | Reusa (código real)                                                                               |
| ------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| **tools**           | registra `BaseTool` no toolset resolvido por usuário; aparece em `/tools/schema`; ABAC aplica                | `backend/services/tool_resolver.py`, `tool_policy.py`, `tools/__init__.py::ALL_TOOLS`             |
| **workbench_tabs**  | entrada nova em `WORKBENCH_TABS`; ícone em `TAB_ICON`; render no `WorkbenchContent`; componente lazy via ESM | `frontend/lib/stores/workbench-store.ts`, `frontend/components/workbench/`                        |
| **slash_commands**  | entrada no registry de slash commands                                                                        | `frontend/lib/constants/slash-commands.ts`                                                        |
| **render_hints**    | novo `RenderHint` + componente no dispatcher (schema-driven, sem switch hardcoded)                           | `frontend/components/chat/tool-call-renderer.tsx`, `lib/types/render.ts`                          |
| **integrations**    | card novo na aba Integrações; chave guardada no vault KeePass; OAuth opcional                                | `backend/api/handlers/oauth.py`, `services/secrets/`                                              |
| **settings**        | chaves tipadas mescladas no settings-store por usuário                                                       | `frontend/lib/stores/settings-store.ts`                                                           |
| **skills**          | paths passados a `skills=[...]` do agente                                                                    | `backend/services/skills.py`, `agent_factory.py`                                                  |
| **mcp_servers**     | registrados no manager de plugins MCP do usuário                                                             | `backend/services/plugins.py`                                                                     |
| **hooks** (eventos) | callbacks em eventos de ciclo de vida (`on_thread_created`, `on_tool_executed`, `on_rag_indexed`)            | dispatcher de eventos novo (`services/extensions/events.py`); alinha com webhooks de `plan.md` L3 |

---

## 5. Os dois SDKs (Python + TypeScript)

### 5.1 SDK Python — `vectora-extension-sdk` (import `vectora_ext`)

> Nome deliberadamente distinto do `vectora-sdk` (cliente REST do
> `plan.md` Bloco L) para não colidir. O SDK de extensão é **autoral**
> (escrever extensões); o REST SDK é **consumidor** (chamar a API).

API mínima, declarativa, espelhando `@tool` do LangChain que o backend
já usa:

```python
# backend/tools.py de uma extensão
from vectora_ext import extension, ToolContext

ext = extension(id="acme.email")

@ext.tool(render_hint="table", category="communication")
async def email_search(query: str, ctx: ToolContext) -> list[dict]:
    """Busca emails na caixa de entrada do usuário."""
    # ctx.secret("EMAIL_PASSWORD") lê do vault; ctx.workspace_root confina FS;
    # ctx.http é um httpx async já com timeout/limites do host.
    creds = await ctx.secret("EMAIL_PASSWORD")
    ...

@ext.on_event("thread.created")
async def greet(payload, ctx: ToolContext) -> None:
    ...
```

`vectora_ext` cobre **só a superfície de autoria** — não embute LangGraph
nem FastAPI. As tools viram `BaseTool` quando o host as importa
(`@ext.tool` é açúcar sobre o `@tool` interno + metadata). Defensividade
(princípio 11 do plano) é **garantida pelo host**: ele envolve toda tool
de extensão em `try/except` que devolve erro tipado — extensão buggada
nunca derruba o grafo.

CLI de autoria (instalada com o SDK):

```bash
vectora-ext init my-extension        # scaffold a partir do template
vectora-ext build .                  # → dist/my-extension-1.0.0.vext
vectora-ext sign dist/*.vext --key ~/.minisign/key
vectora-ext validate dist/*.vext     # checa manifesto + entrypoints + permissões
vectora-ext publish dist/*.vext      # PR no registry oficial OU registry custom
```

### 5.2 SDK TypeScript — `@vectora/extension-sdk`

Cobre dois cenários:

**(a) Contribuições de UI** (workbench tabs, render hints, settings,
slash commands) — o SDK provê os tipos + um `registerExtension()` que o
host do frontend invoca ao carregar o bundle ESM:

```ts
// ui/index.ts de uma extensão
import { defineExtension, type WorkbenchTab } from "@vectora/extension-sdk";

const InboxTab: WorkbenchTab = {
  id: "inbox",
  titleKey: "ext.acme.email.inbox",
  icon: "Mail",
  // o host injeta um cliente tipado: api.tools.call("email_search", {...})
  Component: ({ api, workspaceId }) => {
    /* React */
  },
};

export default defineExtension({
  workbenchTabs: [InboxTab],
  renderHints: { email_thread: EmailThreadView },
  slashCommands: [{ command: "/email", titleKey: "ext.acme.email.cmd" }],
});
```

**(b) Lógica de backend em Node/TS** — para extensões cujo backend não é
Python (ex.: `vectora-eslint` que roda o eslint do ecossistema Node). O
SDK provê um harness JSON-RPC sobre stdio; o host spawna o processo Node
(via `pty_registry`/subprocess async) e fala com ele, **igual ao padrão
de um MCP server stdio** — reuso direto da infra de `mcp-library.md`:

```ts
import { defineBackend } from "@vectora/extension-sdk/node";

defineBackend({
  tools: {
    async eslint_check({ paths }, ctx) {
      // ctx.workspaceRoot confina; ctx.spawn roda eslint com limites
      const out = await ctx.spawn("eslint", ["--format=json", ...paths]);
      return parseDiagnostics(out);
    },
  },
});
```

### 5.3 Matriz runtime × superfície

| Extensão escrita em | tools backend                                                      | UI                     | exemplo PoC      |
| ------------------- | ------------------------------------------------------------------ | ---------------------- | ---------------- |
| **Python**          | in-process ou subprocess (interpreter do core ou venv vendorizado) | via bundle TS opcional | `vectora-ruff`   |
| **TypeScript/Node** | sidecar Node (JSON-RPC stdio, modelo MCP)                          | nativo                 | `vectora-eslint` |
| **Python + TS**     | Python no backend, React no frontend                               | nativo                 | `vectora-email`  |

---

## 6. Compatibilidade com Electron + Nuitka (o ponto não-trivial)

O core do Vectora é compilado por **Nuitka onefile** (proprietário,
fechado). Extensões precisam rodar **sem recompilar o binário**. Como:

### 6.1 Extensões nunca entram no binário

O `build-nuitka` (`SConstruct`) embute apenas o core + a SPA
(`chat_static`). Extensões vivem em `~/.vectora/extensions/<user_id>/<id>/`
(extraídas do `.vext` no install) e são carregadas em runtime. O binário
ship com um **Extension Host** que sabe descobrir/validar/carregar — o
host é parte do core; as extensões não.

### 6.2 Backend Python da extensão

Duas estratégias de isolamento (declaradas em `entrypoints.backend.isolation`):

- **`in-process`** (extensões confiáveis/first-party): o host adiciona
  `~/.vectora/extensions/<id>/backend` ao `sys.path` e faz `importlib`.
  Funciona com Nuitka porque o onefile embute um CPython completo capaz
  de **interpretar** módulos `.py` externos em runtime (eles rodam
  interpretados, não compilados — perda de performance irrelevante para
  glue de tool). Deps de terceiros: **vendorizadas** em `backend/vendor/`
  (wheels) dentro do `.vext`, adicionadas ao `sys.path` — **zero pip no
  install** (determinístico, offline, auditável).
- **`subprocess`/`sandbox`** (default para terceiros não-assinados):
  o host roda o backend da extensão num **processo separado** com seu
  próprio interpretador (uv-managed venv) e fala JSON-RPC, idêntico ao
  modelo MCP stdio. Sandbox por SO reusa o de `mcp-library.md`
  (bubblewrap/sandbox-exec/AppContainer). Isolamento real para código
  não-confiável; o core nunca importa código de terceiro no próprio
  processo.

### 6.3 Frontend TS da extensão

O `ui/dist/index.js` é um **bundle ESM** servido pelo FastAPI a partir do
diretório extraído (`GET /extensions/{id}/ui/*`). A SPA o carrega via
`import()` dinâmico em runtime e chama o `default export` para registrar
as contribuições. Para isolamento de UI não-confiável, a aba pode rodar
em **`<iframe>` sandboxed** (web) / **`<webview>`** (Electron) — mesmo
mecanismo da aba Preview proposta no plano ativo de workbenches. UI
first-party confiável carrega inline (sem iframe) para integração visual
total.

### 6.4 Node sidecar (extensões TS de backend)

O host spawna `node ~/.vectora/extensions/<id>/node/dist/index.js` como
subprocesso async e fala JSON-RPC por stdio (reuso de `pty_registry`/
`asyncio.create_subprocess_exec`). Node **não** é embutido no binário —
é requisito de sistema declarado pela extensão (`engines`); ausência →
extensão fica desabilitada com erro tipado e instrução ("instale Node
20+"). Alternativa para quem não quer depender de Node: a extensão TS
compila para WASM ou roda via MCP HTTP remoto.

> **Resumo da compat:** binário fechado + extensões abertas sideloaded =
> exatamente o contrato do VS Code (executável fechado, `.vsix` aberto).
> Nuitka não atrapalha porque (a) Python externo roda interpretado pelo
> CPython embutido e (b) UI e Node são carregados de disco, não
> compilados.

---

## 7. CLI do usuário: `vectora ext` (paridade com `mcp`/`skills`)

Espelha a sintaxe que `mcp-library.md` e `skills-library.md` já definem,
para o usuário aprender **um** padrão:

```bash
vectora ext list                          # extensões instaladas
vectora ext search "linter"               # busca no marketplace
vectora ext install vectora-official/ruff # do registry
vectora ext install ./acme-email.vext     # arquivo local
vectora ext install https://.../email.vext
vectora ext install git+https://github.com/acme/vectora-email.git
vectora ext info acme.email               # manifesto + permissões + tools
vectora ext enable/disable acme.email     # toggle sem desinstalar
vectora ext update acme.email[@1.3.0]
vectora ext remove acme.email
vectora ext permissions acme.email        # revisar/revogar permissões concedidas
```

Scopes (`user`/`workspace`/`project`) e precedência idênticos a skills/MCP.
Instalação de extensão **não-assinada** exige flag/aprovação explícita,
com tela de permissões (igual ao install de MCP em `mcp-library.md`).

---

## 8. Segurança e trust

Reuso direto do que já existe + o modelo de `mcp-library.md`:

1. **Assinatura** (`SIGNATURE` no `.vext`): minisign/GPG. Badges no
   marketplace iguais a skills/MCP: `✅ Verified by Vectora`,
   `✅ Signed by publisher`, `🟡 Community`, `⚠ Unsigned`.
2. **Permissões declaradas + consentidas**: o install mostra `network`/
   `filesystem`/`secrets`/`spawn_processes` solicitados; usuário aprova.
   O host **enforça** — extensão sem `network` declarado não abre socket.
3. **Sandbox por default** para backend não-assinado (subprocess +
   bubblewrap/sandbox-exec/AppContainer).
4. **ABAC por usuário**: admin pode desabilitar uma extensão (ou tools
   dela) por usuário via `tool_policy` (já existe). Isolamento por
   `user_id` — extensão de um usuário não vaza para outro.
5. **Deny-globs herdados** (`security.py::SENSITIVE_DENY_GLOBS` do
   `plan.md` J23): nenhuma extensão lê `.env`, `*.kdbx`, `.ssh/**`,
   `master.kek`, etc., mesmo com `filesystem: ["workspace"]`.
6. **Secrets via vault**: extensão nunca recebe a chave crua no manifesto;
   pede por nome (`ctx.secret("X")`) e o host resolve do KeePass do
   usuário, com a sessão destravada (modelo de `oauth.py`/`secrets/`).
7. **Conteúdo via extensão é não-confiável** (princípio 12 do plano): o
   que uma tool de extensão devolve não tem autoridade de mensagem do
   usuário; instruções de alto impacto vindas dela passam por
   confirmação.
8. **CVE response**: igual a MCP — extensão com CVE crítico é
   desabilitada automaticamente até o usuário revisar.

---

## 9. Marketplace + template open source

- **Registry**: reusa o registry de `mcp-library.md`/`skills-library.md`
  (`vectora.company/extensions` + registry custom por empresa). Mesma
  curadoria, mesmos scopes, mesmo fluxo de submissão (PR no repo público
  → review automático → review de segurança → community-listed →
  verified após N instalações sem incidente).
- **Template SDK open source** (`vectora-company/extension-template`,
  **MIT**): o "vsix template" do enunciado. Repo com:
  - `vectora-extension.json` de exemplo,
  - `backend/tools.py` + `ui/index.tsx` + `skills/` de exemplo,
  - configuração de build (`vectora-ext build`),
  - testes (`vectora-ext test` — TDD: 1 happy + 1 erro por tool),
  - GitHub Action `vectora/extension-ci` (lint + validate + build +
    sign no release).
    Os dois SDKs (`vectora-extension-sdk` PyPI, `@vectora/extension-sdk`
    npm) também são **open source MIT** — o produto core continua
    proprietário; o **kit de autoria** é aberto (mesma estratégia do VS
    Code: editor proprietário/Code-OSS, mas a Extension API é aberta).

---

## 10. Os 3 plugins próprios (prova de conceito)

Escolhidos para cobrir **as três combinações de runtime/superfície** e a
frente de "interações" pedida (email + linters). Docker e os demais
ficam no roadmap (§11).

### 10.1 `vectora-ruff` — extensão Python pura (backend + diagnósticos)

**Prova:** SDK Python, tools backend in-process, contribuição de
diagnósticos, slash command. Sem conta externa, sem rede — a PoC mais
simples e a primeira a entregar.

- **Tools**: `ruff_check(paths?)`, `ruff_format(paths?, write=False)`,
  `ruff_explain(rule)`. Rodam `ruff` (vendorizado como wheel em
  `backend/vendor/`) confinado ao `workspace_root`.
- **UI**: contribui um `render_hint: "diagnostics"` (lista clicável
  estilo "Problems") reusado pela aba Diagnósticos do workbench.
- **Slash command**: `/ruff` → roda `ruff_check` no workspace ativo.
- **Permissões**: `filesystem: ["workspace"]`, `network: false`,
  `spawn_processes: ["ruff"]` (ou in-process via API do ruff).
- **i18n**: `ext.ruff.*` em en/es/pt-BR.

### 10.2 `vectora-eslint` — extensão TypeScript/Node (sidecar)

**Prova:** SDK TS, backend em Node sidecar (JSON-RPC stdio, modelo MCP),
runtime não-Python rodando junto do core.

- **Backend Node** (`node/dist/index.js`): tools `eslint_check(paths?)`,
  `eslint_fix(paths?)`, `eslint_config_explain`. Spawn de `eslint` do
  projeto do usuário (respeita `eslint.config.js`/`.eslintrc` local).
- **UI**: mesma `render_hint: "diagnostics"` que o ruff (prova que duas
  extensões compartilham um render hint).
- **Permissões**: `filesystem: ["workspace"]`, `spawn_processes: ["eslint","node"]`.
- **engines**: `node>=20`. Ausência → desabilita com erro tipado.

### 10.3 `vectora-email` — extensão full (Python backend + React UI + integração + interações)

**Prova:** a fronteira de "interações" pedida no enunciado — Python +
TS + UI + integração com OAuth/secrets + aba nova no workbench.

- **Tools** (Python): `email_search(query)`, `email_read(id)`,
  `email_send(to, subject, body)` (destrutiva → HITL),
  `email_draft(context)` (compõe rascunho via agente).
- **Workbench tab** (React): aba **"Inbox"** — lista de threads de email,
  leitura, responder; chama as tools via o cliente tipado do host.
- **Integração**: card "Email" na aba Integrações; suporta `EMAIL_PASSWORD`
  (IMAP/SMTP) **ou** OAuth Google (reusa `oauth.py`); chave no vault.
- **Skill empacotada**: `triage-inbox.skill.md` ("classifique e priorize
  minha caixa de entrada").
- **Permissões**: `network: ["imap.*","smtp.*","*.googleapis.com"]`,
  `secrets: ["EMAIL_PASSWORD","GOOGLE_OAUTH_TOKEN"]`, `filesystem: false`.
- **render_hint**: `email_thread` (visualização de conversa de email).

Cada PoC vem com README + testes + CI, servindo de exemplo de referência
para terceiros (define o padrão de qualidade, igual às skills oficiais de
`skills-library.md`).

---

## 11. Roadmap de extensões de interação (o "plano futuro" pedido)

As 3 PoC validam o SDK; este é o catálogo de extensões de **interação**
a entregar depois (parte first-party, parte aberta à comunidade). Todas
usam o mesmo `.vext`/SDK — provando que o ecossistema escala sem tocar o
core.

| Extensão                | Categoria  | Superfícies                                                      | Runtime | Prioridade |
| ----------------------- | ---------- | ---------------------------------------------------------------- | ------- | ---------- |
| `vectora-ruff` ✦        | linters    | tools + diagnostics + slash                                      | Python  | **PoC 1**  |
| `vectora-eslint` ✦      | linters    | tools + diagnostics                                              | Node    | **PoC 2**  |
| `vectora-email` ✦       | interações | tools + UI tab + integração + skill                              | Py + TS | **PoC 3**  |
| `vectora-docker`        | devops     | tools (ps/logs/build/compose) + UI tab (containers/logs ao vivo) | Python  | P1         |
| `vectora-prettier`      | formatters | tools + format-on-save hook                                      | Node    | P2         |
| `vectora-pytest`        | testes     | tools + diagnostics + UI (test explorer)                         | Python  | P2         |
| `vectora-slack`         | interações | tools + integração + webhook hooks                               | Py + TS | P2         |
| `vectora-calendar`      | interações | tools + UI tab + OAuth                                           | Py + TS | P3         |
| `vectora-jira`/`linear` | interações | tools + integração + render hints                                | Python  | P3         |
| `vectora-postgres-cli`  | devops     | tools (query/introspect) + UI (storage browser)                  | Python  | P3         |

✦ = prova de conceito entregue neste bloco.

Os conectores comerciais Tier 2C de `products.md` (Notion, Jira, Figma,
Google Workspace, Analytics Agent, Security Agent) passam a ser
**extensões `.vext` first-party pagas** — mesmo formato, licença
comercial, revenue-share no marketplace.

---

## 12. Sub-blocos de implementação (EXT-1 .. EXT-12)

> **Dependências:** o host backend reusa `tool_resolver`/`tool_policy`/
> `secrets`/`security` (já existem). O host frontend reusa o padrão de
> abas do workbench e o dispatcher de render hints. Alinha com a Frente
> 6 do plano ativo (workbenches) — abas de extensão usam o mesmo
> mecanismo das abas nativas novas.

### EXT-1 — Schema do manifesto + validação

`backend/types/extension.py` (Pydantic) + `frontend/lib/extensions/manifest.ts`
(Zod). `manifest_version: 1`. Testes: manifesto válido, inválido, engine
incompatível.

### EXT-2 — Formato `.vext` (pack/unpack/sign/verify)

`backend/services/extensions/package.py`: criar/ler ZIP, validar layout,
assinatura destacada (minisign via `py-minisign` ou GPG). `vectora-ext`
CLI no SDK Python.

### EXT-3 — Extension Host backend (descoberta + ciclo de vida)

`backend/services/extensions/host.py`: descobre em
`~/.vectora/extensions/<user_id>/`, valida, resolve permissões, registra
contribuições. Versão por usuário (bump invalida cache, igual a
`plugins.py`/`skills.py`). Cada tool de extensão envolvida em try/except
tipado pelo host.

### EXT-4 — Isolamento backend (in-process / subprocess / sandbox)

`backend/services/extensions/runners/{inprocess,subprocess}.py`. Sandbox
por SO reusa `mcp-library.md`. Vendoring de wheels (`backend/vendor/`)
para in-process; venv uv para subprocess.

### EXT-5 — Registro de tools/skills/mcp no agente

Liga contribuições ao `tool_resolver.resolve_tools(user_id)`,
`skills=[...]` e `plugins.get_user_mcp_tools(user_id)`. Aparecem em
`/tools/schema` sem mudança no front.

### EXT-6 — Endpoints REST do host

`backend/api/handlers/extensions.py` (auth): `GET /extensions`,
`POST /extensions` (install: arquivo/URL/git), `DELETE /extensions/{id}`,
`POST /extensions/{id}/enable|disable`, `GET /extensions/{id}` (manifesto

- permissões), `GET /extensions/{id}/ui/*` (serve assets ESM). Admin:
  override por usuário (reusa `/admin/users/{id}/tools`).

### EXT-7 — Extension Host frontend (loader ESM + iframe)

`frontend/lib/extensions/host.ts`: `import()` dinâmico dos bundles UI;
registra `workbench_tabs` no `workbench-store`, `render_hints` no
dispatcher, `slash_commands` e `settings`. Modo iframe/webview sandboxed
para UI não-confiável.

### EXT-8 — Eventos/hooks de ciclo de vida

`backend/services/extensions/events.py`: dispatcher de
`thread.created`/`tool.executed`/`rag.indexed`/`message.completed`.
Alinha com webhooks (`plan.md` L3) — extensão pode reagir localmente em
vez de webhook externo.

### EXT-9 — UI de gerenciamento (marketplace + instalados)

`frontend/components/settings/extensions/` + aba/painel "Extensões":
lista instaladas, marketplace (busca/install/permissões/reviews),
toggle, update, revisão de permissões. i18n `extensions.*`.

### EXT-10 — SDKs de autoria (Python + TS) + template open source

Repos `vectora-extension-sdk` (PyPI), `@vectora/extension-sdk` (npm),
`extension-template` (MIT). CLI `vectora-ext init/build/sign/validate/
test/publish`. GitHub Action `vectora/extension-ci`.

### EXT-11 — As 3 extensões PoC (`ruff`, `eslint`, `email`)

Cada uma com manifesto + tools/UI + README + testes + CI, no template.
Instaláveis pelo fluxo normal (`vectora ext install`). São o critério de
aceite do bloco.

### EXT-12 — `scons` + CI: empacotar e publicar extensões

Alvos `scons ext-build`/`scons ext-publish`; pipeline que builda os 3
PoC e publica no registry. Smoke test: instalar cada `.vext` num
servidor limpo e verificar tools + UI.

### Arquivos críticos (visão consolidada)

| Camada          | Arquivos                                                                                                                                                                                                             |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend — tipos | `backend/types/extension.py` (novo)                                                                                                                                                                                  |
| Backend — host  | `backend/services/extensions/{host,package,events}.py`, `runners/{inprocess,subprocess}.py` (novos)                                                                                                                  |
| Backend — REST  | `backend/api/handlers/extensions.py` (novo); `api/server.py` (registrar); `admin.py` (override por usuário)                                                                                                          |
| Backend — reuso | `services/{tool_resolver,tool_policy,plugins,skills,secrets,security,safe_roots}.py`, `tools/__init__.py`, `agent_factory.py`                                                                                        |
| Frontend — host | `frontend/lib/extensions/{host,manifest,loader}.ts` (novos)                                                                                                                                                          |
| Frontend — UI   | `frontend/components/settings/extensions/*` (novo); `lib/stores/workbench-store.ts`, `components/workbench/`, `components/chat/tool-call-renderer.tsx`, `lib/constants/slash-commands.ts`, `lib/i18n/strings.csv.ts` |
| SDKs / template | `vectora-extension-sdk/` (PyPI), `@vectora/extension-sdk/` (npm), `extension-template/` (MIT) — repos novos                                                                                                          |
| PoC             | `extensions/{ruff,eslint,email}/` (novos)                                                                                                                                                                            |
| Build           | `vectora/SConstruct` (`ext-build`/`ext-publish`); `.github/workflows` (extension-ci)                                                                                                                                 |

---

## 13. Verificação (critério de aceite do bloco)

- `vectora-ext init` gera um esqueleto que builda (`vectora-ext build`)
  para um `.vext` válido e assinável.
- `vectora ext install ./vectora-ruff.vext` no app desktop (binário
  Nuitka) **e** no modo self-hosted (FastAPI+SPA): a extensão carrega
  sem rebuild do core.
- `vectora-ruff`: pedir ao agente "rode o ruff" → tool da extensão
  executa confinada ao workspace → diagnósticos renderizam clicáveis.
- `vectora-eslint`: instala, host spawna o sidecar Node, `eslint_check`
  roda e renderiza no **mesmo** render hint do ruff (prova de
  contribuição compartilhada). Sem Node 20+ → erro tipado, não crash.
- `vectora-email`: card de integração aparece; conectar (senha no vault
  ou OAuth Google); **aba "Inbox" nova** aparece no workbench; buscar/ler/
  enviar funciona; `email_send` passa por HITL.
- Permissões: extensão sem `network` declarado não abre socket; tentar
  ler `.env` → negado (deny-glob), sem expor existência.
- Isolamento: extensão de terceiro não-assinada roda em subprocess
  sandbox; admin desabilita uma tool da extensão para um usuário → só
  aquele usuário perde acesso.
- `scons lint`/`scons tests` verdes; testes das 3 PoC (1 happy + 1 erro
  por tool) passam.
- Marketplace lista as 3 PoC com badge "Verified by Vectora"; install em
  1 clique pela UI.

---

## 14. Encaixe no plano mestre (`plan.md`)

Este documento é a **fonte de design**; o `plan.md` ganha um bloco de
execução referenciando-o. Proposta de inserção (sem renomear A–S):

- **Novo bloco `EXT — Extension SDK & Plugin Runtime`**, posicionado
  **depois de I (Deep Agents 2)** — porque reusa sandbox/worktree (I1) e
  ACP (I4) para extensões que rodam agentes — e **antes/par com L (SDKs
  & API Ecosystem)**, já que o `@vectora/extension-sdk` e o
  `vectora-extension-sdk` convivem com os SDKs REST de L (nomes
  distintos, §5.1).
- Atualizar `products.md` Tier 2C: plugins DLC passam a ser extensões
  `.vext` (formato único; revenue-share sobre o registry de extensões).
- Atualizar `mcp-library.md` e `skills-library.md`: MCP e skills viram
  **contribuições empacotáveis** dentro de um `.vext` (continuam
  standalone para casos simples).
- Atualizar `native-tools.md`: o conceito de "packs modulares" converge
  para extensões `.vext` (packs viram extensões first-party).

---

## 15. Relação com outros documentos

| Doc                 | Relação                                                                            |
| ------------------- | ---------------------------------------------------------------------------------- |
| `products.md`       | Tier 2C (plugins DLC) = extensões `.vext` first-party pagas; marketplace reusado   |
| `mcp-library.md`    | Modelo de install/sandbox/permissões/registry reaproveitado; MCP vira contribuição |
| `skills-library.md` | Modelo de pacote/sign/publish/scopes reaproveitado; skill vira contribuição        |
| `native-tools.md`   | Packs modulares convergem para extensões; taxonomia de tools reusada               |
| `chat-first.md`     | Schema-first (render hints), padrão de abas do workbench, build Nuitka/Electron    |
| `plan.md`           | Novo bloco EXT; reusa tool_resolver/tool_policy/secrets/security/agent_factory     |
| `tech.md`           | Atualizar com `backend/services/extensions/`, formato `.vext`, SDKs de autoria     |
| `observability.md`  | Tools de extensão entram nos mesmos spans/métricas (por `extension_id`)            |

---

## 16. Princípios cardinais

1. **Core fechado, extensões abertas.** O produto é proprietário
   (Nuitka); o kit de autoria (SDKs + template + formato `.vext`) é open
   source MIT. Modelo VS Code, não modelo "tudo aberto".

2. **Extensão nunca recompila o core.** Sideload em runtime de
   `~/.vectora/extensions/`. Nuitka embute só core + SPA.

3. **Reusar formato, não inventar container.** `.vext` = ZIP + manifesto,
   como `.vsix`/`.whl`/`.crx`. Inventamos o layout/manifesto, não o ZIP.

4. **Tudo é contribuição declarada.** Manifesto schema-first; o host
   despacha sem código por extensão (igual a `render_hint`).

5. **Sandbox por default para não-confiável.** Backend de terceiro roda
   em subprocess isolado; UI não-confiável em iframe/webview.

6. **Permissões explícitas e enforçadas.** Declaradas no manifesto,
   consentidas no install, aplicadas pelo host. Deny-globs e vault
   herdados do core.

7. **Defensividade é do host, não da extensão.** Toda tool de extensão é
   envolvida em try/except tipado — extensão buggada vira observação para
   o LLM, nunca derruba o grafo.

8. **i18n e ABAC valem para extensões.** Strings por chave nas 3 línguas;
   admin gate por usuário via `tool_policy`.

9. **Um padrão de CLI.** `vectora ext` espelha `vectora mcp` e
   `vectora skills` — o usuário aprende uma vez.

10. **PoC é critério de aceite.** Sem `ruff` + `eslint` + `email`
    instaláveis e funcionando ponta a ponta pelo fluxo público, o SDK
    não está pronto.
