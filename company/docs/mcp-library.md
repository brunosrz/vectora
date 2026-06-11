# Vectora — MCP Library

> Marketplace integrado para descobrir, instalar e gerenciar MCP servers
> do ecossistema. Pareado com [`native-tools.md`](native-tools.md) que
> define o que está dentro do Vectora — este define como o user
> estende.
>
> **Por que existir:** Claude Code e Cursor exigem CLI manual para
> instalar MCPs. Discovery é via GitHub awesome-list. Validação de
> segurança é manual. Vectora resolve as três pontas: descoberta no
> sidebar, instalação em 1 clique, sandbox + assinatura por padrão.

---

## Arquitetura em três camadas

```
┌──────────────────────────────────────────────────────────────┐
│  1. NATIVE TOOLS (compilado no binário)                      │
│     ~70 tools — File system, Git, RAG, Web, Office, etc.     │
│     Ver docs/native-tools.md                                 │
├──────────────────────────────────────────────────────────────┤
│  2. PLUGINS FIRST-PARTY (Tier 2C — DLC marketplace)         │
│     Notion, Jira, Linear, Figma, Slack, Datadog, ...         │
│     Curadoria + suporte oficial Vectora                      │
│     Ver docs/products.md §Tier 2C                            │
├──────────────────────────────────────────────────────────────┤
│  3. MCP LIBRARY (este doc)                                   │
│     Qualquer MCP server público do ecossistema               │
│     Community-driven, instalado sob demanda                  │
└──────────────────────────────────────────────────────────────┘
```

A MCP Library cobre o **long tail** — tudo que não vale tornar nativo
nem cuidar como plugin first-party. Para o user, todas as três camadas
parecem iguais: tool calls com mesmo render, mesma rastreabilidade,
mesmo HITL.

---

## UX do painel sidebar

Adicionado à navegação principal do chat web:

```
┌────────────────────┐
│  ⚡ Vectora        │
├────────────────────┤
│ 💬 Conversas       │
│ 📁 Workspaces      │
│ 🧠 Memórias        │
│ 🔧 Skills          │
│ 🧩 MCP Library  ← NOVO
│ ⚙️  Settings       │
└────────────────────┘
```

Clique abre painel full-height:

```
┌─────────────────────────────────────────────────────────────────┐
│ 🧩 MCP Library                                  [+ Add Custom]  │
├─────────────────────────────────────────────────────────────────┤
│ 🔍 buscar MCP servers...                       [filter ▼]       │
├─────────────────────────────────────────────────────────────────┤
│ INSTALADOS (3)                                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ✅ docs-langchain        stdio · user-scope        [⋮]      │ │
│ │    docs de bibliotecas LangChain via MCP                    │ │
│ │    8 tools · v1.2.3 · 24 chamadas hoje                      │ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ✅ github-official       http  · user-scope        [⋮]      │ │
│ │    GitHub API completo (search, issues, PRs)                │ │
│ │    18 tools · v0.9.1 · 47 chamadas hoje                     │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ ⭐ DESTAQUES (community-voted)                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 🌐 context7                                       [+ install]│ │
│ │    Docs atualizados de bibliotecas como contexto LLM        │ │
│ │    ⭐ 2.4k · ✅ assinado · 🛡️ sandbox · 4 tools             │ │
│ │    [Detalhes] [GitHub] [Docs]                               │ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 🎭 playwright                                     [+ install]│ │
│ │    Browser automation completo                              │ │
│ │    ⭐ 1.8k · ✅ assinado · 🛡️ sandbox · 14 tools            │ │
│ │    [Detalhes] [GitHub] [Docs]                               │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ CATEGORIAS                                                      │
│ Database (12) · Cloud (24) · CRM (8) · DevOps (18)              │
│ Search (9)    · Productivity (31) · Communication (14)          │
│ Finance (6)   · Media (11) · Specialized (47)                   │
└─────────────────────────────────────────────────────────────────┘
```

### Card de detalhes (clique em "Detalhes")

```
┌─────────────────────────────────────────────────────────────────┐
│ 🎭 playwright                                  [← Voltar]       │
├─────────────────────────────────────────────────────────────────┤
│ Browser automation via Playwright                               │
│ ⭐ 1.847 instalações no Vectora · 4.2★ (62 reviews)            │
│ ✅ Assinado por @microsoft (verificado)                         │
│ 🛡️ Roda em sandbox por padrão                                  │
│ 📦 Tamanho: 80 MB (Chromium incluído)                          │
│ 📅 Última atualização: 2 dias atrás                            │
├─────────────────────────────────────────────────────────────────┤
│ TOOLS EXPOSTAS (14)                                             │
│ • browser_open                                                  │
│ • browser_close                                                 │
│ • browser_screenshot                                            │
│ • browser_navigate                                              │
│ • browser_fill                                                  │
│ • browser_click                                                 │
│ • browser_extract_text                                          │
│ • ... (ver mais)                                                │
├─────────────────────────────────────────────────────────────────┤
│ PERMISSÕES SOLICITADAS                                          │
│ 🌐 Internet (qualquer URL)                                      │
│ 💾 Filesystem (escrever screenshots em ~/Downloads)             │
│ 🖥️  Spawnar processos (Chromium)                                │
│                                                                 │
│ [Cancelar] [Instalar com sandbox] [Instalar sem sandbox]        │
└─────────────────────────────────────────────────────────────────┘
```

### Menu de gerenciamento (⋮ no item instalado)

```
┌──────────────────────────────────┐
│ ⋮ Menu                           │
├──────────────────────────────────┤
│ 🔄 Atualizar                     │
│ ⏸  Desabilitar temporariamente   │
│ 🔧 Editar configuração           │
│ 📊 Ver métricas de uso           │
│ 🔍 Inspecionar tools             │
│ 🛡️  Editar permissões            │
│ 📤 Compartilhar config           │
│ 🗑️  Desinstalar                  │
└──────────────────────────────────┘
```

---

## CLI — paridade com Claude Code

Todo o gerenciamento da MCP Library também via CLI. Comandos espelham a
sintaxe do Claude Code para facilitar migração:

### Listar / buscar / inspecionar

```bash
# Listar instalados
vectora mcp list

# Listar com detalhes
vectora mcp list --verbose

# Buscar no catálogo
vectora mcp search browser

# Inspecionar tools de um server (instalado ou não)
vectora mcp inspect playwright
vectora mcp inspect https://mcp.example.com/server.json

# Ver tools ativas (de todos os MCPs instalados)
vectora mcp tools
```

### Instalar / desinstalar

```bash
# Instalar do catálogo (Vectora resolve URL/transport)
vectora mcp add context7
vectora mcp add playwright --scope user

# Instalar com URL custom (paridade Claude Code)
vectora mcp add docs-langchain --transport http --scope user \
    https://docs.langchain.com/mcp

vectora mcp add my-internal-mcp --transport stdio --scope project \
    /usr/local/bin/my-mcp-server

# Instalar sem sandbox (requer flag explícita)
vectora mcp add untrusted-mcp --no-sandbox --transport stdio ./server.py

# Desinstalar
vectora mcp remove context7
vectora mcp remove playwright --scope user
```

### Configuração

```bash
# Editar config de um server (abre editor)
vectora mcp config playwright

# Setar env var específica do server
vectora mcp env playwright BROWSER=firefox

# Habilitar/desabilitar temporariamente (sem desinstalar)
vectora mcp disable playwright
vectora mcp enable playwright
```

### Sync do registry

```bash
# Atualizar catálogo local
vectora mcp sync

# Mudar fonte do registry
vectora mcp registry add https://registry.empresa.com/mcps
vectora mcp registry list
vectora mcp registry remove https://registry.empresa.com/mcps
```

### Scopes

Três níveis (paridade Claude Code):

| Scope       | Arquivo                                    | Quem vê                            |
| ----------- | ------------------------------------------ | ---------------------------------- |
| `user`      | `~/.vectora/mcp.json`                      | Todos os workspaces do user        |
| `workspace` | `<workspace>/.vectora/mcp.json`            | Apenas neste workspace             |
| `project`   | `<projeto>/.vectora/mcp.json` (gitignored) | Apenas neste projeto, devs do time |

Precedência: `project` > `workspace` > `user` (mais específico vence).

---

## Protocolo de instalação

### Tipos de MCP suportados

| Transport | O que é                                          | Exemplo                             |
| --------- | ------------------------------------------------ | ----------------------------------- |
| `stdio`   | Binário local que se comunica via stdin/stdout   | `npx -y @anthropic/mcp-server-time` |
| `http`    | Servidor HTTP remoto (request/response)          | `https://docs.langchain.com/mcp`    |
| `sse`     | Servidor HTTP com Server-Sent Events (streaming) | `https://mcp.exemplo.com/sse`       |
| `ws`      | WebSocket (full-duplex, raro mas suportado)      | `wss://mcp.exemplo.com/ws`          |

### Formato do manifest local (`~/.vectora/mcp.json`)

```json
{
  "version": "1.0",
  "servers": {
    "docs-langchain": {
      "transport": "http",
      "url": "https://docs.langchain.com/mcp",
      "scope": "user",
      "enabled": true,
      "installed_at": "2026-06-05T14:23:00Z",
      "permissions": {
        "internet": true,
        "filesystem": false,
        "spawn_processes": false
      },
      "auth": {
        "type": "bearer",
        "token_env": "DOCS_LANGCHAIN_TOKEN"
      }
    },
    "playwright": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@microsoft/mcp-server-playwright"],
      "scope": "user",
      "enabled": true,
      "sandbox": true,
      "permissions": {
        "internet": true,
        "filesystem": ["~/Downloads"],
        "spawn_processes": ["chromium"]
      },
      "env": {
        "BROWSER": "chromium"
      }
    },
    "my-internal-mcp": {
      "transport": "stdio",
      "command": "/usr/local/bin/my-mcp-server",
      "scope": "project",
      "enabled": true,
      "sandbox": false,
      "signature_warning_acknowledged": true
    }
  }
}
```

### Validação na instalação

Quando user clica "Instalar" (ou `vectora mcp add`):

```
1. Resolver manifest do registry
   → busca em ~/.vectora/mcp-registry/index.json
   → fallback: fetch direto da URL passada

2. Verificar assinatura (se servidor declarou)
   → manifest assinado com GPG da org publicadora
   → para Vectora-verified, manifest assinado pela Vectora Company
   → não-assinado: aviso amarelo "este server não é verificado"

3. Exibir permissões solicitadas para o user aprovar
   → Internet (read/write, escopo de domínios opcional)
   → Filesystem (paths específicos vs amplo)
   → Spawn processes (lista de binários)
   → Network (portas, hosts)

4. Setup sandbox (se sandbox=true)
   → Linux: bubblewrap ou systemd-nspawn
   → macOS: sandbox-exec
   → Windows: AppContainer ou WSL2 wrapper
   → server stdio rodando dentro

5. Hot-load no Vectora rodando
   → mcp-client conecta e descobre tools
   → tools aparecem como disponíveis para o agent
   → sem restart do Vectora

6. Notificação de sucesso
   → "playwright instalado. 14 tools disponíveis."
```

### Sandbox por padrão

Servers `stdio` não-assinados rodam em sandbox **por padrão**. User pode
desabilitar via `--no-sandbox` (com aviso explícito).

Sandbox restringe:

- Filesystem para paths declarados nas permissões
- Network para domínios declarados
- Spawn de processos
- Acesso a env vars (apenas as declaradas em `env`)

Servers `http`/`sse`/`ws` não precisam de sandbox local (rodam remoto),
mas todas as chamadas passam pelo cliente Vectora que logga
input/output.

---

## Fonte do registry

### Registry oficial Vectora (`~/.vectora/mcp-registry/index.json`)

Cache local atualizado diariamente (ou via `vectora mcp sync`).

**Fonte primária:**

- Registry oficial do MCP (quando lançado por Anthropic/comunidade)
- Fallback: scrape de `awesome-mcp-servers` GitHub

**Cada entrada inclui:**

- `id`, `name`, `description`, `homepage`, `repo`
- `transport`, `install_command` (npx/docker/binary URL)
- `tools` (lista das tools expostas com descrição)
- `permissions` (default solicitadas)
- `signature` (chave GPG da org publicadora, se houver)
- `vectora_verified` (boolean: passou por revisão interna do Vectora)
- `community_score` (estrelas, instalações, reviews)
- `last_updated`

### Registry custom (empresa)

Empresas podem hostar registry próprio com MCPs internos:

```bash
vectora mcp registry add https://mcps.minhaempresa.com/registry.json
```

Manifest do registry custom segue o mesmo schema. Servers do registry
custom **podem** aparecer com prefixo (`@minhaempresa/...`) ou em
categoria separada na UI.

### Submissão de novo MCP

Para entrar no registry oficial Vectora:

1. PR no repo público `vectora-company/mcp-registry` adicionando entrada
2. Review automático (CI valida schema, dispara testes do server)
3. Review manual de segurança (membro Vectora avalia)
4. Aprovação → entra como `vectora_verified: false` (community-listed)
5. Após 100+ instalações + 0 incidentes de segurança em 30 dias →
   promovido a `vectora_verified: true`

---

## Verificação de segurança

### Para o user (visível na UI)

| Badge                  | Significa                                                 |
| ---------------------- | --------------------------------------------------------- |
| ✅ Verified by Vectora | Vectora revisou código e binários, assinou manifest       |
| ✅ Signed by publisher | Manifest assinado por GPG da org publicadora (verificada) |
| 🟡 Community-listed    | No registry mas sem review formal Vectora                 |
| ⚠️ Unsigned            | Manifest sem assinatura — atenção ao instalar             |
| 🛡️ Runs in sandbox     | Server stdio rodará isolado                               |
| ⚡ Auto-update enabled | Vectora atualiza este server quando há nova versão        |

### Resposta a CVE em MCP instalado

- Vectora monitora CVE feed para MCPs verificados
- CVE crítico em MCP instalado:
  - Notificação push para todos os users afetados
  - Server **desabilitado automaticamente** até user revisar
  - Update sugerido com 1 clique

---

## Métricas de uso por MCP

User vê em Settings → MCP Library → Métricas:

```
playwright (instalado há 14 dias)
  Chamadas totais: 248
  Chamadas última semana: 47
  Tool mais usada: browser_screenshot (89×)
  Tempo médio de resposta: 1.2s
  Falhas: 3 (1.2%)
  Custo estimado: $0 (não consome API paga)

github-official (instalado há 30 dias)
  Chamadas totais: 1.412
  Chamadas última semana: 312
  Tool mais usada: search_issues (456×)
  Tempo médio de resposta: 0.4s
  Falhas: 12 (0.8%)
  Custo estimado: $0 (rate-limited GitHub API gratuito)
```

Útil para identificar MCPs subutilizados (candidatos a desinstalar) e
gargalos de performance.

---

## Migração de Claude Code (importador)

User vindo de Claude Code pode importar MCPs configurados:

```bash
vectora mcp import --from claude-code

# Vectora lê ~/.claude/mcp.json e instala equivalentes:
# ✅ context7 — encontrado no registry, instalando
# ✅ playwright — encontrado no registry, instalando
# ⚠️  custom-internal — não encontrado, copiando config local
# ❌ deprecated-mcp — não disponível, ignorando
```

Equivalente para Cursor (`vectora mcp import --from cursor`) quando
Cursor padronizar formato.

---

## Cronograma de implementação

```
Pré-lançamento (próximos 3 meses)
  Sprint MCP-1 (2 semanas): backend
    - Schema de manifest
    - Fetcher de registry (oficial + custom)
    - Cache local + sync command
    - Validação de assinaturas GPG

  Sprint MCP-2 (2 semanas): CLI completa
    - vectora mcp {add, remove, list, search, inspect, sync, ...}
    - Paridade Claude Code para migração trivial

  Sprint MCP-3 (3 semanas): UI sidebar
    - Painel novo no chat web
    - Cards de install/manage
    - Métricas de uso
    - Migration importer (--from claude-code)

  Sprint MCP-4 (1 semana): sandbox
    - Bubblewrap (Linux)
    - sandbox-exec (macOS)
    - AppContainer/WSL (Windows)
    - Testes de bypass

Pós-lançamento Q1
  - Submissão programa para 3rd parties
  - Auto-update + CVE monitoring
  - Métricas dashboard expandido
```

---

## Princípios cardinais

1. **MCP Library é descoberta, não monocultura.** Vectora não tenta
   replicar tudo — facilita instalar qualquer coisa do ecossistema.

2. **Paridade CLI com Claude Code.** Migração de Claude Code → Vectora
   é trivial para quem já configurou MCPs.

3. **Sandbox por padrão.** Servers não-assinados rodam isolados.
   Desabilitar exige flag explícita.

4. **Permissões granulares.** User aprova exatamente o que cada MCP
   pode fazer (FS paths, network domains, processos).

5. **Custom registry para empresa.** Cada empresa pode hostar seus MCPs
   internos sem expor publicamente.

6. **Hot-load, sem restart.** Instalar/desinstalar/desabilitar MCP é
   imediato — agente roda continuamente.

7. **Métricas visíveis.** User vê quem está sendo usado, quanto, com que
   custo — decide o que manter.

8. **Auto-update opcional.** Por default off; user pode habilitar
   por server.

9. **CVE response automático.** Vulnerabilidade conhecida desabilita
   server até user revisar.

10. **Documentação inline.** Cada tool exposta por MCP mostra docstring
    no chat — user não precisa sair para descobrir o que faz.
