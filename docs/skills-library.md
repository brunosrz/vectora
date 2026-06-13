# Vectora — Skills Library

> Base técnica para distribuição, descoberta e gerenciamento de Skills.
> Skills são unidades reusáveis de comportamento do agente — prompts
> especializados + tools requeridas + exemplos curados. Persona packs
> (`docs/personas.md`) são bundles de Skills.
>
> **Princípio:** Skills devem ser tão fáceis de instalar quanto MCPs
> (`docs/mcp-library.md`). Marketplace integrado, CLI paritária,
> versionamento confiável, assinatura opcional.

---

## O que é uma Skill (formato `.skill.md`)

Vectora adota o formato Skills da spec Deep Agents (Anthropic), com
extensões mínimas. Uma Skill é um único arquivo Markdown com
frontmatter:

```markdown
---
id: prd-draft
name: PRD Draft
version: 1.2.0
description: Gera Product Requirements Document com contexto via RAG
author: vectora-official
tags: [product, pm, document, rag]
required_tools:
  - rag_search
  - docx_generate
  - workspace_read
required_plugins:
  - vectora-linear # opcional, fallback se ausente
optional_tools:
  - chart_generate
tier_min: pro
license: proprietary # ou: mit, apache-2.0, custom
signature: gpg:0x1234ABCD # opcional
---

# PRD Draft

## Quando usar

Quando o user pede para criar um PRD (Product Requirements Document)
de uma feature nova. Especialmente útil quando o produto já tem
histórico de decisões indexado no RAG.

## Como executar

1. Identifique o nome e escopo da feature pelo prompt do user
2. Busque no RAG: decisões passadas relacionadas, conversas com
   usuários sobre a dor, métricas relevantes
3. Estruture o PRD seguindo o template padrão (Problem, Goals, Non-Goals,
   User Stories, Success Metrics, Risks, Open Questions)
4. Gere `.docx` via tool `docx_generate` se user pedir export
5. Salve como decision log via skill `decision-log` (composição)

## Template

[Problem]
... contexto da dor + dados quantitativos do RAG ...

[Goals]
... 3-5 goals SMART ...

(... template completo ...)

## Exemplos de prompts

- "Cria PRD para feature de bulk export"
- "PRD para nova integração Stripe, considerando decisão de Q3/24"
- "Estrutura PRD do feature flag system"

## Variáveis configuráveis

- `template_style`: "minimal" | "detailed" | "lean"
- `include_metrics`: true | false
- `output_format`: "markdown" | "docx" | "both"
```

### Campos obrigatórios

| Campo            | Descrição                     |
| ---------------- | ----------------------------- |
| `id`             | Slug único (kebab-case)       |
| `name`           | Nome legível                  |
| `version`        | semver (`MAJOR.MINOR.PATCH`)  |
| `description`    | 1 linha                       |
| `author`         | Username/org no registry      |
| `tags`           | Array de tags para busca      |
| `required_tools` | Tools nativas/MCP necessárias |

### Campos opcionais

| Campo               | Descrição                                             |
| ------------------- | ----------------------------------------------------- |
| `required_plugins`  | Plugins Tier 2C necessários                           |
| `optional_tools`    | Tools que enriquecem mas não são obrigatórias         |
| `tier_min`          | Plano mínimo (`plus` / `pro` / `team` / `enterprise`) |
| `license`           | SPDX identifier + `proprietary` / `custom`            |
| `signature`         | Hash GPG da chave do publicador                       |
| `requires_skills`   | Outras skills (composição)                            |
| `requires_personas` | Persona pack necessário                               |
| `cost_estimate`     | Estimativa de tokens/$ por execução                   |
| `hitl_required`     | Boolean — força HITL antes de executar                |

---

## Discovery e marketplace

### Sidebar dedicada no chat web

Já planejada em `docs/positioning.md` e `docs/mcp-library.md`. Skills
ganha sua própria área:

```
┌────────────────────┐
│  ⚡ Vectora        │
├────────────────────┤
│ 💬 Conversas       │
│ 📁 Workspaces      │
│ 🧠 Memórias        │
│ 🔧 Skills      ← este doc
│ 🧩 MCP Library     │
│ 🎯 Personas        │
│ ⚙️  Settings       │
└────────────────────┘
```

### Painel Skills

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔧 Skills                                       [+ Criar Skill] │
├─────────────────────────────────────────────────────────────────┤
│ 🔍 buscar skills...                          [filter ▼]         │
├─────────────────────────────────────────────────────────────────┤
│ INSTALADAS (12)                                                 │
│ ✅ prd-draft               v1.2.0 · pm tag · 47 uses    [⋮]    │
│ ✅ adr-template            v0.9.1 · eng tag · 23 uses   [⋮]    │
│ ✅ release-notes           v2.0.0 · eng tag · 12 uses   [⋮]    │
│ ✅ post-draft              v1.0.3 · marketing · 89 uses [⋮]    │
│ ✅ ...                                                          │
├─────────────────────────────────────────────────────────────────┤
│ ⭐ POPULARES (community)                                        │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 🎨 ui-microcopy        ⭐ 1.2k · ✅ assinada                │ │
│ │    Microcopy para UI (CTAs, error, empty states)            │ │
│ │    [Instalar] [Detalhes] [GitHub]                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 📊 cohort-analysis     ⭐ 890 · ✅ verified by vectora      │ │
│ │    Análise de coorte com SQL automático                     │ │
│ │    [Instalar] [Detalhes] [GitHub]                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ CATEGORIAS                                                      │
│ Product (24) · Engineering (38) · Marketing (16)                │
│ Design (12)  · Sales (9)        · Data (18)                     │
│ Compliance (7) · Ops (15)       · Documentation (22)            │
└─────────────────────────────────────────────────────────────────┘
```

### CLI

```bash
# Listar instaladas
vectora skills list

# Buscar no catálogo
vectora skills search "code review"

# Instalar
vectora skills install prd-draft
vectora skills install vectora-official/release-notes --scope user

# Instalar de URL ou repo Git
vectora skills install https://github.com/acme/my-skills/prd-draft.skill.md
vectora skills install git+https://github.com/acme/skills-pack.git#subpath=marketing/

# Atualizar
vectora skills update prd-draft
vectora skills update --all

# Versionar (pinned)
vectora skills install prd-draft@1.2.0   # versão específica
vectora skills install prd-draft@latest  # default

# Desinstalar
vectora skills remove prd-draft

# Inspecionar (sem instalar)
vectora skills inspect prd-draft
vectora skills inspect ./local-skill.skill.md

# Criar nova
vectora skills create my-new-skill   # scaffold no diretório atual
vectora skills validate ./my-new-skill.skill.md  # checa schema + tools
```

### Scopes (paridade com MCP Library)

| Scope       | Local                                     | Visibilidade                     |
| ----------- | ----------------------------------------- | -------------------------------- |
| `user`      | `~/.vectora/skills/`                      | Todas as sessões do user         |
| `workspace` | `<workspace>/.vectora/skills/`            | Todos os usuários no workspace   |
| `project`   | `<projeto>/.vectora/skills/` (gitignored) | Apenas neste projeto / clone     |
| `runtime`   | embed na conversa                         | Apenas na sessão atual (efêmero) |

Precedência: `project` > `workspace` > `user` > `runtime` (mais
específico vence em caso de conflito de `id`).

---

## Composição de Skills

Skills podem requerer outras skills via `requires_skills`. Exemplo:

```yaml
---
id: feature-launch
requires_skills:
  - prd-draft
  - release-notes
  - post-draft
  - email-draft
---
```

A skill `feature-launch` é um meta-workflow que orquestra 4 skills
existentes. Permite criar workflows complexos sem duplicar lógica.

### Resolução de dependências

```
$ vectora skills install feature-launch

Resolving dependencies...
  ✓ prd-draft@1.2.0 already installed
  + release-notes@2.0.0 (will install)
  + post-draft@1.0.3 (will install)
  + email-draft@1.1.0 (will install)
  + feature-launch@0.5.0 (will install)

Tools required:
  - rag_search (native ✓)
  - docx_generate (native ✓)
  - email_send (plugin: vectora-postmark — not installed)

Continue? [y/N]
```

Se um plugin requerido não estiver instalado, Vectora oferece instalar
junto.

---

## Versionamento e auto-update

### Semver

Skills seguem semver estrito:

- **MAJOR**: mudança incompatível (template totalmente diferente, tools
  requeridas mudaram, comportamento esperado diferente)
- **MINOR**: nova funcionalidade compatível (variáveis novas, exemplo
  novo)
- **PATCH**: correções (typo, ajuste de prompt, melhoria de exemplo)

### Auto-update

Por default **opt-in** por skill. User decide:

```bash
vectora skills auto-update prd-draft on
vectora skills auto-update --all on
vectora skills auto-update --all off  # default
```

Skills com auto-update ligado são atualizadas:

- PATCH automaticamente sem confirmação
- MINOR com notificação no chat (next session)
- MAJOR **nunca** automaticamente — exige `vectora skills update prd-draft@2.0.0`

### Pinning para reprodutibilidade

Em projetos críticos, recomendado pinar versões no `.vectora/skills.lock.json`:

```json
{
  "skills": {
    "prd-draft": "1.2.0",
    "release-notes": "2.0.0",
    "adr-template": "0.9.1"
  }
}
```

Commitar no repo do projeto garante que todos os devs têm exatamente as
mesmas skills.

---

## Trust model: skills assinadas vs não-assinadas

### Skills oficiais Vectora

- Publicadas em `vectora-official/*` (org no registry)
- Assinadas com chave GPG da Vectora Company
- Passam por code review interno + testes automatizados
- Badge ✅ "Verified by Vectora" no marketplace

### Skills community

- Qualquer um pode publicar
- Assinatura GPG **encorajada** mas não obrigatória
- Badge ✅ "Signed" se manifest assinado por chave verificada
- Badge 🟡 "Community-listed" sem assinatura

### Skills locais (custom)

- Criadas pelo user/empresa
- Sem assinatura (são suas)
- Sem badge no painel — listadas em seção "Suas Skills"

### Aviso ao instalar não-assinada

```
⚠️ Esta skill não está assinada digitalmente.

  Skill: ui-microcopy by @random-user
  Tools requeridas: rag_search, web_fetch

  Skills não-assinadas podem executar prompts arbitrários no agente.
  Revise o conteúdo antes de instalar.

  [Ver código completo] [Instalar mesmo assim] [Cancelar]
```

---

## Distribuição

### Registry oficial Vectora

URL: `vectora.company/skills`

- Estrutura: cada skill tem página com README, exemplos, reviews,
  changelog, downloads
- Versionamento via GitHub releases (tag = versão)
- Source de verdade: repos GitHub
- CDN serve manifests + arquivos para low-latency

### Distribuição por repositório Git

Skills podem viver em qualquer repo Git público ou privado:

```bash
# Pública
vectora skills install git+https://github.com/acme/skills.git#subpath=marketing/

# Privada (via SSH ou token)
vectora skills install git+ssh://git@github.com/acme-private/skills.git
vectora skills install git+https://oauth2:$TOKEN@github.com/acme-private/skills.git
```

### Registry custom (empresa)

Empresa pode hostar registry próprio:

```bash
vectora skills registry add https://skills.acme.com
vectora skills install @acme/internal-prd-template
```

Manifest do registry custom segue mesmo schema do oficial.

### Marketplace público

Browse em `vectora.company/skills` mostra:

- Top 100 mais instaladas (global)
- Top 20 por categoria
- "Em alta" (crescimento últimas 7 dias)
- "Novas" (publicadas últimos 30 dias)
- Filtros: tier requerido, license, assinatura, tags

---

## Pricing das skills

### Free skills

Padrão. Skills criadas pela comunidade e pela Vectora Company são
geralmente **gratuitas** — fazem parte do ecossistema.

### Paid skills (programa futuro)

Pós-lançamento, abrir programa de skills pagas (revenue share 70/30
com publicador):

- Pricing: $1–10/mês por skill
- Trial: 14 dias por skill paga
- Bundles: publicador pode criar bundles ("Marketing Pro Pack — 12
  skills por $15/mês")

### Skills inclusas em planos

Skills oficiais Vectora **gratuitas** para qualquer tier. Skills
oficiais com `tier_min` configurado (ex: skills enterprise) só
disponíveis nos planos correspondentes.

---

## Tier gating

```yaml
---
id: financial-model
tier_min: leadership-pack # exige persona pack pago
required_tools:
  - xlsx_generate
  - chart_generate
---
```

- `tier_min` pode ser plano (`plus`/`pro`/`team`/`enterprise`)
- Ou pode ser dependência de outro pack (`leadership-pack`, `compliance-pack`, etc.)
- Skill aparece no marketplace para todos, mas com badge "Requer Plano X"
- Tentativa de instalar dispara upgrade flow

---

## Criação de skills

### CLI scaffold

```bash
vectora skills create my-skill
```

Cria:

```
my-skill/
├── my-skill.skill.md       # frontmatter + body
├── README.md               # docs no GitHub
├── test/                   # casos de teste
│   ├── prompt-1.json
│   └── expected-1.txt
└── examples/               # exemplos de uso
    ├── basic.md
    └── advanced.md
```

### Validação

```bash
vectora skills validate ./my-skill.skill.md

✓ Schema válido
✓ Tools requeridas existem (rag_search, docx_generate)
✓ Versão é válida (semver)
✗ Assinatura ausente (skill será marcada como não-assinada)
⚠ README.md não encontrado (recomendado para distribuição)

3/4 passou. Veja warnings acima.
```

### Testes

Skills podem ter testes automatizados:

```json
// test/prompt-1.json
{
  "prompt": "Cria PRD para bulk export CSV",
  "expected_tools_called": ["rag_search", "docx_generate"],
  "expected_output_contains": ["Problem", "Goals", "User Stories"],
  "max_duration_seconds": 30,
  "max_cost_usd": 0.1
}
```

```bash
vectora skills test ./my-skill.skill.md

Running test 1/3: "Cria PRD para bulk export CSV"
  ✓ rag_search called
  ✓ docx_generate called
  ✓ Output contains expected sections
  ✓ Duration 12.3s (limit 30s)
  ✓ Cost $0.03 (limit $0.10)
PASSED

Running test 2/3: ...
```

### Publicação

```bash
# Build (gera dist/ com manifest + assets)
vectora skills build .

# Sign (opcional — recomendado)
vectora skills sign . --key ~/.gnupg/private.key

# Publish (push para registry oficial via PR no repo público)
vectora skills publish .

# Ou publish para registry custom
vectora skills publish . --registry https://skills.acme.com
```

---

## Relacionamento com outros docs

| Doc                    | Relação                                                                  |
| ---------------------- | ------------------------------------------------------------------------ |
| `docs/personas.md`     | Persona packs **são bundles de skills + manifest extra**                 |
| `docs/mcp-library.md`  | Skills podem requerer MCPs; install resolve dependências automaticamente |
| `docs/native-tools.md` | Skills declaram `required_tools` referenciando native tools              |
| `docs/products.md`     | Skills aparecem como plugin DLC em alguns casos (Tier 2C)                |
| `docs/beta-program.md` | Skills novas (especialmente community) podem passar por programa beta    |
| `docs/positioning.md`  | Skills viabilizam o "Vectora para não-técnicos" via personas             |

---

## Cronograma de implementação

```
Pré-lançamento
  Sprint S-1 (2 semanas): backend
    - Schema de manifest .skill.md
    - Resolver de dependências (skills + tools + plugins)
    - Cache local em ~/.vectora/skills/

  Sprint S-2 (1 semana): CLI
    - vectora skills {install/remove/list/search/inspect/update}
    - Scopes user/workspace/project
    - Pinning via skills.lock.json

  Sprint S-3 (2 semanas): UI marketplace
    - Painel Skills na sidebar do chat web
    - Cards de install/manage
    - Categorias + busca
    - Reviews e ratings

  Sprint S-4 (1 semana): validation + testing
    - vectora skills validate / test / build
    - Schema de testes automatizados
    - CI template para skills repos

Pós-lançamento Q1
  - Registry público vectora.company/skills
  - Skills oficiais Vectora (~20 iniciais)
  - Import de skills community curadas

Pós-lançamento Q2
  - Programa de skills pagas (revenue share 70/30)
  - Bundles de publicadores
  - Internal registry para empresas Team+
```

---

## Skills oficiais iniciais (lançamento)

Mínimo 20 skills oficiais no lançamento, divididas por categoria:

**Engineering (6):**

- `code-review` — revisão estruturada de diff
- `adr-template` — Architecture Decision Record
- `rfc-draft` — Request for Comments
- `release-notes` — release notes a partir de PRs mergeados
- `commit-message` — gera commit message convencional
- `pr-description` — PR description estruturada

**Product (4):**

- `prd-draft` — Product Requirements Document
- `user-research-summary` — sumariza entrevistas
- `prioritization-rice` — score RICE
- `release-checklist` — checklist pré-release

**Documentation (4):**

- `api-docs-from-code` — gera docs a partir de código
- `tutorial-write` — tutorial passo a passo
- `troubleshooting-guide` — guia de troubleshooting
- `changelog-entry` — entrada de changelog

**Data (3):**

- `sql-generate` — SQL a partir de pergunta
- `chart-from-query` — query + viz
- `cohort-analysis` — análise de coorte

**Compliance (3):**

- `policy-draft` — política (privacidade, segurança, etc.)
- `dpia-assessment` — DPIA LGPD/GDPR
- `security-questionnaire` — resposta de questionário

Cada uma assinada, testada, documentada — define o padrão de
qualidade que comunidade deve seguir.

---

## Princípios cardinais

1. **Skills são unidades atômicas.** Uma skill faz UMA coisa bem
   definida. Composição via `requires_skills`, não monolitos.

2. **Discovery é UX.** Marketplace integrado + busca rápida + filtros
   úteis. Não cair na armadilha "instale via CLI obscura" do vim.

3. **Versionamento estrito.** Semver enforced. Pinning recomendado
   para projetos críticos.

4. **Trust granular.** Skills oficiais vs assinadas vs community
   vs locais — user vê claramente o nível de confiança.

5. **Persona é bundle de skills, não invenção paralela.** Reaproveita
   infra de skills + manifest extra.

6. **Skills locais > skills publicadas para casos custom.** Empresa
   cria skill interna em 5 minutos sem precisar publicar.

7. **Testes automatizados encorajados.** Skills oficiais têm testes;
   community é incentivada a ter. Validação local antes de publish.

8. **Free por padrão.** Programa pago é opcional, só faz sentido para
   publicadores especializados com manutenção contínua.

9. **CLI paritária com mcp-library e personas.** User aprende um padrão,
   aplica a três coisas.

10. **Manifesto explícito de custos.** Skills declaram `cost_estimate`
    — HITL automático para custo alto, em alinhamento com tools.
