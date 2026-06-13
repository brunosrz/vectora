# Vectora — Análise de Concorrentes

> Análise honesta dos concorrentes diretos e adjacentes do Vectora.
> Para cada player: forças, fraquezas, o que Vectora **aprende**, o
> que Vectora **não vai copiar e por quê**.
>
> Documento de leitura interna. Não é material de venda — é
> autocrítica e aprendizado. Versão pública (selecionando partes) pode
> virar blog post comparativo, mas o documento integral fica entre
> equipe.
>
> **Atualizar trimestralmente.** Mercado de IA muda rápido demais
> para análise anual.

---

## Mapa do mercado (jun/2026)

```
                          ┌───────────────────────────────────────┐
                          │  AGENTES DE DEV — CLOUD-MANAGED       │
                          │  Claude Code, Cursor, Codex, Windsurf │
                          │  Devin, Replit Agent, Bolt, Lovable   │
                          └───────────────────────────────────────┘
                                          │
                                          │
            ┌─────────────────────────────┼─────────────────────────────┐
            │                             │                             │
            ▼                             ▼                             ▼
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│ SELF-HOSTED OPEN    │      │ ★ VECTORA ★         │      │ AUTOCOMPLETE / IDE  │
│ Aider, Continue.dev │      │ Self-hosted comerci.│      │ GitHub Copilot,     │
│ OpenCode, OpenDevin │      │ RAG-first + MCP +   │      │ Codeium, Tabnine    │
│ Hermes Agent, Cline │      │ chat web + REST API │      │ Pieces              │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
                                          │
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              │                           │                           │
              ▼                           ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│ ENTERPRISE CODE     │    │ MEETING / VOICE     │    │ VIBE CODING         │
│ Sourcegraph Cody,   │    │ Perssua (BR)        │    │ Lovable, v0,        │
│ Greptile,           │    │ Otter, Fireflies    │    │ Bolt.new, Replit    │
│ Tabnine Enterprise  │    │ Granola, Tactiq     │    │                     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

---

## Tier 1 — Concorrentes diretos (mesmo público)

### 1. Claude Code (Anthropic)

**O que é:** CLI agentic da Anthropic, distribuído como produto first-party.
Usa Claude como LLM (lock-in).

**Forças:**

- UX de CLI excelente — `claude` é simples de usar do dia 1
- Skills nativas com formato `.skill.md` (que adotamos)
- MCP first-class (lançado pela Anthropic)
- Plan mode profundo antes de execução
- Custom slash commands hierárquicos (user/project/local)
- Hooks (`pre-tool-use`, `post-tool-use`, `stop`) — power users adoram
- Background tasks com notificação
- Documentação técnica forte (anthropic.com/claude-code)
- Integração com IDE (status line, file context)

**Fraquezas:**

- **Lock-in total a Claude** — nenhum outro LLM, mesmo via MCP
- **Cloud-only** — código sempre passa pela Anthropic
- **Sem chat web multi-usuário** — é CLI, ponto
- **RAG fraco** — depende de re-leitura de arquivos no contexto
- **Caro:** $20/mês entry + custo de tokens via API
- **Sem persona packs** — engenheiros only
- **Sem REST API pública** para integração de sistemas

**O que Vectora aprende:**

- ✅ **Adotar formato `.skill.md`** (já fazemos)
- ✅ **Adotar hooks** (`pre-tool-use`, `post-tool-use`, etc.) — adicionar no roadmap
- ✅ **Adotar Plan mode** — modo explícito de planejamento antes de execução
- ✅ **Adotar Custom slash commands com hierarquia** — já parcialmente
- ✅ **Status line custom no chat web** — ux.md UX-41 atividade do agente
- ✅ **Background tasks com notificação** — incluir em UX
- ✅ **Excelência em UX de CLI** — Textual TUI deve igualar ou superar
- ✅ **CLI paridade `mcp add/remove/list`** — `mcp-library.md` define

**O que Vectora NÃO copia:**

- ❌ Lock-in a LLM único — princípio fundacional
- ❌ Cloud-managed — somos self-hosted por design
- ❌ Pricing alto — Plus a $7 é nossa entrada
- ❌ Foco engineering-only — persona packs expandem audiência

**Posicionamento contra:**

> _"Claude Code é excelente — usamos como referência de UX. Mas você
> fica refém de um único LLM, manda código para Anthropic, e seu time
> não-técnico não consegue usar. Vectora resolve os três."_

---

### 2. Cursor

**O que é:** Editor (fork do VS Code) com agente integrado. Cloud-managed.
Atualmente o produto mais popular do segmento.

**Forças:**

- **Tab autocomplete treinado no codebase** — exclusivo, muito bom
- **Composer mode** — multi-file edits aprovados em batch
- @-mentions universais (@file, @docs, @web, @symbol, @past-chat)
- **Background agents** que continuam tarefas
- **Bug hunter** proativo (analisa código em background)
- **Privacy Mode** com guarantia de zero retention contratual
- UX nativo de editor — não precisa alternar contexto
- Modelos de ponta (Claude, GPT, Gemini)
- Grande comunidade e documentação
- Pricing simples: $20/mês

**Fraquezas:**

- **Cloud-managed** — todo o contexto vai para Cursor (mesmo com Privacy Mode, processa na infra deles)
- **Sem self-host** — empresa em setor regulado não usa
- **RAG é fraco** vs Vectora (depende de `@codebase` que é re-indexação leve)
- **Mono-pessoa** — é um editor, não plataforma multi-usuário
- **Não tem MCP first-class** (planejado mas não chegou)
- **Não tem chat web** para times remotos
- **Não tem REST API** para integração com sistemas internos

**O que Vectora aprende:**

- ✅ **Composer mode** — HITL agregado para múltiplos arquivos (não 1 por 1)
- ✅ **@-mentions completos** — `@file` já existe, falta `@docs`, `@web`, `@symbol`, `@past-chat`
- ✅ **Background agents** — tarefas longas com retomada (ux.md UX-43)
- ✅ **Privacy mode explícito na UI** — dizer "rodando localmente, zero retention"
- ✅ **Bug hunter proativo** — agente passivo que sugere fixes (opt-in)
- ✅ **Pricing simples** — Plus $7 / Pro $20 vs matriz complexa

**O que Vectora NÃO copia:**

- ❌ Tab autocomplete treinado por user — não é nosso foco (anti-vibe-coding)
- ❌ Ser um editor — somos plataforma, integramos com editores via VSIX
- ❌ Cloud-managed — somos self-hosted
- ❌ Mono-pessoa — somos multi-usuário desde o início

**Posicionamento contra:**

> _"Cursor é o melhor editor com IA do mercado. Mas seu CTO não consegue
> auditar o código que processa seus dados, seu PM não pode usar para
> fazer PRDs, e seu sistema interno não tem API para integrar. Vectora
> integra com Cursor via MCP — e cobre os outros casos."_

---

### 3. Codeium / Windsurf

**O que é:** Codeium = produto de autocomplete; Windsurf = editor agentic
(mesmo player, dois produtos). Cloud-managed.

**Forças:**

- **Cascade mode** (Windsurf) — agentic multi-step com bom flow
- **Flow mode** — contexto contínuo entre sessões
- Live preview integrado
- Free tier generoso (Codeium autocomplete)
- Suporta enterprise self-hosted (Codeium Enterprise) — único nesse segmento

**Fraquezas:**

- **Sem MCP / extensibilidade externa**
- **Sem RAG sobre docs personalizados** (só código)
- **Sem chat web para times**
- **Pricing enterprise opaco** (>$15k/ano para Codeium Enterprise self-hosted)
- **UX inconsistente** entre Codeium e Windsurf (dois produtos sob mesma marca confunde)

**O que Vectora aprende:**

- ✅ **Live preview** — render hint `live_preview` para HTML/SVG/Component (já em native-tools.md)
- ✅ **Flow mode** — sessões persistentes que mantém contexto entre dias (memória semântica)
- ✅ **Cascade mode** — sub-agentes encadeados explícitos (já temos via Deep Agents)
- ✅ **Self-host como diferencial enterprise** — validar que Codeium ganha dinheiro nisso

**O que Vectora NÃO copia:**

- ❌ Dois produtos com mesma marca — Vectora é UM produto
- ❌ Pricing enterprise opaco — nosso pricing é público

**Posicionamento contra:**

> _"Codeium/Windsurf provou que self-hosted vende bem em enterprise.
> Vectora democratiza isso — self-host a partir de R$20/mês, não
> $15k/ano."_

---

### 4. Aider (open source)

**O que é:** CLI agentic puro Python, open source MIT, foco em
pair-programming via terminal.

**Forças:**

- **Auto-commit por mudança** com mensagem AI gerada (brilhante)
- **Repo-map via tree-sitter** — contexto comprimido de codebase
- **Lint+test loop** — roda lint/test e auto-fix até passar
- **Voice mode** — fala com IA
- **Architect/coder split** — modelo grande planeja, modelo barato edita
- **Conventions file** — `CONVENTIONS.md` injetado em todo contexto
- Excelente integração git nativa
- Open source completo (MIT) com comunidade ativa
- Gratuito

**Fraquezas:**

- **CLI-only** — sem chat web, sem desktop app, sem mobile
- **Mono-pessoa** — não pensado para times
- **Sem MCP** — fechado em torno do que vem out-of-box
- **Sem RAG semântico** — repo-map é estático
- **Sem multi-LLM trivial** — funciona melhor com Claude/GPT
- **Sem persona packs** — engineers only

**O que Vectora aprende:**

- ✅ **Auto-commit opcional** — flag `auto_commit: true` para times que querem
- ✅ **Repo-map tree-sitter** — alternativa/complemento ao RAG vetorial para projetos pequenos
- ✅ **Lint+test loop** — skill `lint-and-fix` que executa até passar
- ✅ **Architect/coder split** — modelo grande planeja, pequeno executa (economia de tokens significativa)
- ✅ **Conventions file** — Vectora já tem `AGENTS.md`, validar paridade
- ✅ **Voice mode trivial** — já planejado em `ia-plus.md`

**O que Vectora NÃO copia:**

- ❌ CLI-only — somos multi-modo
- ❌ Open source — somos comercial licenciado (por escolha estratégica)
- ❌ Mono-pessoa — multi-usuário desde o início

**Posicionamento contra:**

> _"Aider é uma obra de engenharia. Se você é dev solo no terminal,
> use Aider — é gratuito. Vectora atende você ao escalar para time,
> precisar de chat web, integrar com sistemas, ou estender com MCP."_

---

### 5. Continue.dev (open source)

**O que é:** Extensão de VS Code/JetBrains open source com agente
configurável.

**Forças:**

- **Context providers extensíveis** (plugin model próprio)
- **Multi-provider real** (Claude, GPT, Gemini, Ollama, etc.)
- **Local-first com Ollama** integração polida
- **Custom commands** via config.json
- **Open source Apache 2.0**

**Fraquezas:**

- **Só funciona dentro de IDE** (VS Code / JetBrains)
- **Sem CLI**
- **Sem chat web**
- **Sem MCP** (planejado mas atrasado)
- **Configuração complexa** — `config.json` enorme
- **RAG é experimental** — não confiável
- **Falta polish** — UX inferior a Cursor

**O que Vectora aprende:**

- ✅ **Context providers como API** — Vectora poderia ter `ContextProvider` plugável (nosso RAG hoje é hardcoded)
- ✅ **Multi-provider polido** — já temos, validar UX
- ✅ **Local-first com Ollama de qualidade** — wizard de setup melhor
- ✅ **Open source posicionamento** (eles atraem devs por isso) — Vectora compensa com self-host + pricing baixo

**O que Vectora NÃO copia:**

- ❌ Só IDE — somos multi-modo
- ❌ Open source — escolha estratégica
- ❌ Configuração via JSON pesada — preferimos UI + CLI

**Posicionamento contra:**

> _"Continue.dev é a opção open source para extensão de IDE. Se você
> só quer chat dentro do VS Code e tudo bem configurar JSON, use.
> Vectora oferece VSIX equivalente + chat web + CLI + REST API + RAG
> de produção — pagando $7-20/mês."_

---

### 6. Sourcegraph Cody

**O que é:** Cody = agente da Sourcegraph, focado em code search at
scale. Tem versão self-hosted Enterprise.

**Forças:**

- **Multi-repo context** — único forte nesse aspecto
- **Code graph** (chamadores/chamados via análise estática)
- **Self-host enterprise** maduro
- **Integração com Sourcegraph Search** (líder em code search)
- Suporte a stacks legados (COBOL, Fortran)

**Fraquezas:**

- **Caríssimo** (~$60-200/dev/mês enterprise)
- **Cody isolado é fraco** — depende de Sourcegraph rodando
- **Setup pesado** — Sourcegraph + Cody = stack significativo
- **Sem MCP**
- **Sem persona packs**

**O que Vectora aprende:**

- ✅ **Multi-repo context** — gap real do Vectora hoje
- ✅ **Code graph complementar ao RAG** — análise estática (calls, refs) aumenta precisão
- ✅ **Self-hosted enterprise vende** — Cody ganha dinheiro com isso

**O que Vectora NÃO copia:**

- ❌ Pricing enterprise — somos PME-first
- ❌ Acoplamento a outra ferramenta — Vectora é standalone
- ❌ Setup pesado — Plus deve subir em 5 minutos

**Posicionamento contra:**

> _"Sourcegraph Cody é a opção para empresa BIG que já paga
> Sourcegraph. Vectora atende PMEs que querem ~90% do valor por
> ~10% do preço, sem precisar instalar stack inteiro."_

---

### 7. Devin / Cognition AI

**O que é:** Devin = "primeiro engenheiro de software AI". Workspace
visível com browser + terminal + code editor. Long-running tasks.

**Forças:**

- **Long-running tasks** com retomada
- **Workspace visível** (browser + terminal lado a lado)
- **Memória de sessões passadas**
- **Planning interface** explícita
- **Marketing impressionante** (Cognition AI vale $4B+)

**Fraquezas:**

- **Cloud-managed e caro** ($500/mês entry)
- **Resultados inconsistentes** — vários benchmarks mostraram que o demo era cherry-picked
- **Sem self-host**
- **Sem MCP**
- **Foco em "substituir júnior"** — posicionamento polêmico

**O que Vectora aprende:**

- ✅ **Workspace visível (workbench)** — Vectora já tem; aumentar visibilidade
- ✅ **Long-running tasks com retomada** — ux.md UX-43 tracks isso
- ✅ **Planning interface explícita** — Plan mode (do Claude Code)
- ✅ **Memory de sessões passadas** — já temos via LangGraph Store

**O que Vectora NÃO copia:**

- ❌ Pricing $500/mês — somos PME-friendly
- ❌ Posicionamento "substitui júnior" — falso e antipático
- ❌ Marketing cherry-picked — somos honestos sobre limitações
- ❌ Cloud-only — somos self-hosted

**Posicionamento contra:**

> _"Devin é demo bonito por $500/mês. Vectora é produto real por $7-20/mês
> que você instala na sua infra, faz o que diz que faz, e seu time
> aprende a usar bem em 1 semana."_

---

### 8. Replit Agent

**O que é:** Agente integrado ao Replit IDE. Fullstack scaffolding
em minutos.

**Forças:**

- **Live preview embutido** (gera app, vê funcionando, deploy 1 clique)
- **Fullstack scaffolding** (Next.js, FastAPI, etc.) em minutos
- **Deploy integrado** (Replit Deployments)
- **Excelente para protótipos**
- **Free tier funcional**

**Fraquezas:**

- **Roda só no Replit** (cloud, sem self-host)
- **Foco vibe coding** — não é para engenheiros sêniores
- **Sem RAG sobre projetos externos**
- **Lock-in à infra Replit** (deploy só lá)

**O que Vectora aprende:**

- ✅ **Live preview embutido** — `dashboard_preview`, `live_preview` (native-tools.md)
- ✅ **Scaffolding como skill** — skill `scaffold` que gera projeto a partir de template

**O que Vectora NÃO copia:**

- ❌ Foco vibe coding — anti-positioning explícito (`positioning.md`)
- ❌ Cloud-only — self-hosted
- ❌ Lock-in de hosting — agnóstico

**Posicionamento contra:**

> _"Replit Agent é ótimo para prototipar app do zero em 10 minutos. Mas
> não serve para trabalhar em codebases existentes, atender time
> multi-disciplinar, ou rodar na sua infra. Use Replit para protótipo,
> Vectora para o produto sério."_

---

## Tier 2 — Concorrentes adjacentes (público diferente, sobreposição parcial)

### 9. GitHub Copilot

**O que é:** Autocomplete + chat da Microsoft/GitHub. $19/mo individual,
$39/mo enterprise. Cloud-only.

**Sobreposição:** baixa — Copilot é autocomplete, Vectora é agente

**Fraquezas para nosso público:**

- Sem RAG sobre docs/projeto
- Sem MCP / extensibilidade
- Sem self-host
- Sem chat web multi-usuário
- Sem persona packs

**Aprendizado:**

- ✅ Distribuição via Marketplace (VS Code) — Vectora VSIX
- ✅ Pricing competitivo + tier enterprise opaco (eles ganham bem)
- ✅ Integração com GitHub Actions — Vectora pode ter actions oficial

**Posicionamento:**

> _"Copilot é autocomplete; Vectora é agente. São coisas diferentes —
> muitos usuários usam ambos. Vectora foca onde Copilot não chega:
> RAG sobre docs internas, agente multi-step, time multi-disciplinar."_

---

### 10. Tabnine

**O que é:** Autocomplete enterprise self-hosted. Cliente histórico
em setor regulado.

**Sobreposição:** parcial — Tabnine tem chat agent mas é fraco

**O que Vectora aprende:**

- ✅ Setor regulado paga bem por self-hosted — validar tese
- ✅ Compliance certifications (SOC 2, HIPAA, ISO) atraem enterprise

---

### 11. Pieces

**O que é:** Snippet manager + AI augmented (memory de copy/paste,
context awareness). Local-first.

**Sobreposição:** baixa — Pieces é knowledge management; Vectora é agente

**O que Vectora aprende:**

- ✅ Context awareness automático (clipboard, browser tabs, IDE state) — useful
- ✅ Local-first como diferencial vendido bem

---

### 12. Greptile

**O que é:** Code review automation com RAG sobre codebase. Cloud-only.

**Sobreposição:** **alta** — concorre diretamente com Vectora Code
Review (Tier 3 núcleo em `products.md`)

**O que Vectora aprende:**

- ✅ Pricing model ($30/dev/mês) confirma viabilidade do Vectora Code Review
- ✅ UX de comentário inline no PR
- ✅ Onboarding fácil via GitHub App

**Posicionamento (futuro Vectora Code Review):**

> _"Greptile é a referência em code review com RAG — cloud-only.
> Vectora Code Review entrega o mesmo, self-hosted, integrado ao
> Vectora Pro que você já tem."_

---

### 13. CodeRabbit

**O que é:** AI code review via GitHub App. Cloud-only.

**Sobreposição:** **alta** — concorre com Vectora Code Review

**Fraquezas:**

- Cloud-only
- Comentários verbosos demais (queixa comum)
- Sem self-host

**Aprendizado:**

- ✅ ARPU realista ($24/dev/mês)
- ✅ Lições de UX (não ser verboso)

---

### 14. Gemini CLI (Google)

**O que é:** CLI agentic do Google, similar a Claude Code mas com Gemini.

**Forças:**

- **Extensions marketplace integrado** (https://geminicli.com/extensions/)
- Suporte a Gemini multimodal nativo
- Free tier generoso

**Aprendizado crítico:**

- ✅ **Marketplace de extensões dentro do produto** — não só GitHub awesome list. Isso valida `mcp-library.md`
- ✅ Discovery integrado é vetor de adoção

---

## Tier 3 — Adjacências importantes (não competimos, mas referência)

### 15. Lovable / v0 / Bolt.new (vibe coding)

**O que é:** Geração de apps fullstack a partir de prompts. Cloud-only.

**Sobreposição:** **zero** — somos anti-positioning explícito

**Aprendizado:**

- Vibe coding é mercado grande mas tem teto baixo (apps gerados não
  evoluem para produção)
- UX de live preview é mestre — `live_preview` render hint
- Tese: vibe coding atrai juniors / não-devs; Vectora atrai sêniores

---

### 16. Perssua (BR)

**O que é:** Assistente de reuniões brasileiro.

**Sobreposição:** **zero** — mercado diferente

**Aprendizado:**

- Produto BR pode vencer mesmo contra player global (Otter, Fireflies)
- Lucas Montano (fundador) prova que solo founder vende bem em PT-BR
- Self-hosted "no desktop" também tem mercado

**Posicionamento:** colaborativo, não competitivo. Já documentado em
`positioning.md` e `pitch_deck.md`.

---

### 17. Aider/OpenCode/OpenDevin/Hermes Agent (open source self-hosted)

**Sobreposição:** **alta no público alvo** (devs preocupados com
privacidade), **baixa no produto** (eles são open + free, somos
comercial + pago)

**Aprendizado:**

- Open source não monetiza facilmente — eles têm comunidade mas não
  receita
- Vectora oferece "open source-like UX" (self-hosted, auditável sob NDA)
  - suporte profissional pago
- Pricing barato ($7/mês) reduz fricção vs grátis

**Posicionamento:**

> _"OpenCode/Hermes são open-source legítimos. Se você quer total
> liberdade de código + zero pagamento, use. Vectora atende quem
> prefere produto polido + suporte direto + atualizações garantidas
> por $7/mês."_

---

## Tier 4 — Players observados mas não relevantes hoje

| Player                    | Por que monitorar                               |
| ------------------------- | ----------------------------------------------- |
| **Magic.dev**             | Pode ser próximo Devin — vale acompanhar        |
| **Cody (Sourcegraph)**    | Já coberto, mas reposicionando-se em 2026       |
| **Sweep AI**              | PR automation focado em issue → PR              |
| **Pythagora / GPT Pilot** | App generation similar a Devin                  |
| **MetaGPT**               | Multi-agente acadêmico, sem produto consumer    |
| **CrewAI**                | Framework de multi-agente, não produto end-user |
| **Cline (open source)**   | Ex-Claude Dev — extensão VS Code agentic        |
| **DeepSeek Coder**        | Modelo open weights; muda landscape de LLM      |

---

## Padrões transversais — o que TODOS estão fazendo

Observado em pelo menos 5+ players:

1. **MCP first-class** — virou padrão de fato (Anthropic publicou,
   todos adotam)
2. **Multi-LLM com BYOK** — lock-in a um LLM virou tabu
3. **Plan mode explícito** — agente mostra plano antes de executar
4. **Workspace visível** — não-blackbox; user vê o que agente faz
5. **HITL para destrutivo** — confirma antes de delete/push
6. **Cost tracking visível** — user vê quanto gastou em tokens
7. **Skills/custom commands** — extensibilidade por usuário
8. **Hooks/triggers** — automação além do chat (pre/post tool)

Vectora já cobre os 8 ou tem em roadmap.

## Padrões transversais — o que NINGUÉM está fazendo bem

Oportunidades de diferenciação:

1. **Marketplace integrado de MCPs no produto** — Gemini CLI é o
   único que tenta; UX ainda fraca → `mcp-library.md` resolve
2. **Persona packs para não-devs** — ninguém faz; gap real → `personas.md`
3. **Beta program estruturado com recompensa** — ninguém formaliza →
   `beta-program.md`
4. **Self-hosted multi-usuário** com chat web → Vectora único
5. **REST API + OAuth + Webhooks** para integrar com sistemas internos
   → ninguém em segmento PME
6. **6 modalidades de IA nativas** (LLM+embedding+rerank+TTS+STT+image)
   → ninguém combina; `ia-plus.md`
7. **Modular install via packs Nuitka** — ninguém faz; binário pesado
   sem opção de slim → `native-tools.md` resolve
8. **CLI paridade Claude Code** para migração trivial — ninguém oferece

---

## Matriz comparativa consolidada (resumo)

| Feature                       | Vectora  | Claude Code | Cursor | Aider | Continue |  Cody   |  Devin  | Copilot |
| ----------------------------- | :------: | :---------: | :----: | :---: | :------: | :-----: | :-----: | :-----: |
| Self-hosted                   |    ✅    |     ❌      |   ❌   |  ✅   |    ✅    |   ✅¹   |   ❌    |   ❌    |
| Multi-LLM (não-lock-in)       |    ✅    |     ❌      |   ✅   |  ✅   |    ✅    |   ✅    |  Parc.  |  Parc.  |
| RAG dedicado com sub-agente   |    ✅    |     ❌      | Parc.  |  ❌   |    ❌    |  Parc.  |   ❌    |   ❌    |
| Multi-agente especializado    |    ✅    |     ❌      |   ❌   |  ❌   |    ❌    |   ❌    |  Parc.  |   ❌    |
| Chat web multi-usuário (RBAC) |    ✅    |     ❌      |   ❌   |  ❌   |    ❌    |   ❌    |   ❌    |   ❌    |
| MCP server (expor delegação)  |    ✅    |     ❌²     |   ❌   |  ❌   |    ❌    |   ❌    |   ❌    |   ❌    |
| MCP client (consumir)         |    ✅    |     ✅      | Plan.  |  ❌   |  Plan.   |   ❌    |   ❌    |   ❌    |
| MCP Library integrada (UI)    |    🔄    |     ❌      |   ❌   |  ❌   |    ❌    |   ❌    |   ❌    |   ❌    |
| REST API + SDKs               |    🔄    |    Parc.    |   ❌   |  ❌   |    ❌    |   ✅    |   ❌    |   ❌    |
| Webhooks                      |    🔄    |     ❌      |   ❌   |  ❌   |    ❌    |   ❌    |   ❌    |   ❌    |
| Desktop app assinado          |    ✅    |     ❌      |   ✅   |  ❌   |    ❌    |   ❌    |   ❌    |   ❌    |
| VSIX (VS Code extension)      |    🔄    |     ❌      |  N/A   |  ❌   |    ✅    |   ✅    |   ❌    |   ✅    |
| Áudio nativo (STT + TTS)      |    🔄    |     ❌      |   ❌   | Parc. |    ❌    |   ❌    |   ❌    |   ❌    |
| Geração de imagens            |    🔄    |     ❌      |   ❌   |  ❌   |    ❌    |   ❌    |   ❌    |   ❌    |
| Persona packs (não-devs)      |    🔄    |     ❌      |   ❌   |  ❌   |    ❌    |   ❌    |   ❌    |   ❌    |
| Hooks (pre/post tool)         |    🔄    |     ✅      |   ❌   |  ❌   |    ❌    |   ❌    |   ❌    |   ❌    |
| Plan mode explícito           |    🔄    |     ✅      |   ❌   | Parc. |    ❌    |   ❌    |   ✅    |   ❌    |
| Custom slash commands hier.   |    🔄    |     ✅      | Parc.  | Parc. |    ✅    |   ❌    |   ❌    |   ❌    |
| Auto-commit por mudança       |    📋    |     ❌      |   ❌   |  ✅   |    ❌    |   ❌    |   ❌    |   ❌    |
| Live preview embedded         |    🔄    |     ❌      |   ❌   |  ❌   |    ❌    |   ❌    |   ✅    |   ❌    |
| Architect/coder split         |    📋    |     ❌      |   ❌   |  ✅   |    ❌    |   ❌    |   ❌    |   ❌    |
| Programa beta formal          |    🔄    |     ❌      |   ❌   |  ❌   |    ❌    |   ❌    |   ❌    |   ❌    |
| Custo                         | $7–20/mo |   $20+/mo   | $20/mo | Free  |   Free   | $60+/mo | $500/mo | $19/mo  |

¹ Self-hosted é Sourcegraph Enterprise pago
² Claude Code é cliente MCP, não server (não pode ser delegado-a)
🔄 Em desenvolvimento (documentado em outros docs)
📋 Planejado (não documentado formalmente ainda)

---

## Aprendizados consolidados (lista priorizada)

### Top 5 features para implementar pré-lançamento (do que aprendi com concorrentes)

1. **Hooks** (do Claude Code) — `pre-tool-use`, `post-tool-use`, `stop`
2. **Plan mode explícito** (do Claude Code + Devin) — modo de planejamento antes da execução
3. **@-mentions universais** (do Cursor) — `@docs`, `@web`, `@symbol`, `@past-chat` (já temos `@file`)
4. **Composer mode** (do Cursor) — HITL agregado para multi-file edits
5. **Auto-commit opcional** (do Aider) — flag por workspace

### Top 5 features para roadmap pós-lançamento

6. **Multi-repo context** (do Cody) — RAG cross-repo
7. **Code graph com tree-sitter** (do Aider + Cody) — análise estática
8. **Architect/coder split** (do Aider) — economia de tokens significativa
9. **Background agents com retomada** (do Cursor) — tarefas longas
10. **Bug hunter proativo** (do Cursor) — agente passivo opt-in

### Top 3 "não fazer" claros

1. **Não copiar Devin** — long-running autônomo sem supervisão é
   bandeira vermelha; preferimos HITL + workspace visível
2. **Não copiar vibe coding** — Lovable/v0/Bolt atendem público
   diferente; nosso anti-positioning é estratégico
3. **Não copiar pricing enterprise opaco** — Cody/Codeium Enterprise
   cobram fortunas; preferimos transparência + ARPU baixo

---

## Atualizações futuras deste doc

- **Trimestral**: review completo (q1, q2, q3, q4)
- **Quando lançar feature relevante**: atualizar matriz comparativa
- **Quando concorrente novo emerge**: adicionar Tier 4 ou promover
- **Quando concorrente desaparece**: remover ou mover para "histórico"

**Responsável**: Bruno (fundador). Análise de concorrência é decisão
estratégica, não delegável.
