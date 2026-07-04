# Vectora — Mercado e Posicionamento

> Documento canônico consolidado: posicionamento, concorrência, personas
> e narrativa de venda — antes quatro documentos separados (posicionamento,
> análise de concorrência, personas, pitch deck), unificados aqui como
> fonte única para copy de site, pitch, onboarding e material de vendas.
>
> **Por que existir:** posicionamento difuso mata produto. "Vectora é
> para qualquer um que use IA" é a melhor forma de não vender para
> ninguém. Este doc afia o discurso e remove duplicação entre os quatro
> documentos originais.
>
> **Quem aprova mudanças:** Bruno (fundador). Posicionamento, análise de
> concorrência e pivô de público são decisão estratégica, não tarefa
> delegável.

---

## Posicionamento canônico

### A frase canônica

> **"Vectora é o agente de produtividade local-first para engenheiros
> sêniores e seus times — escreve código com contexto real do projeto,
> e atende o resto da empresa (PM, marketing, design, exec) com a mesma
> base de conhecimento."**

Cabe num tweet. Diz para quem é (engenheiros sêniores + times), o que
faz (produtividade, não só código), o diferencial técnico (local-first,
contexto real via RAG), e a expansão natural (resto da empresa via
mesma KB).

### O Problema

Toda ferramenta de IA popular guarda seus dados em servidores de outra
empresa. Seu código, sua documentação, suas conversas, seu contexto de
projeto — tudo sai da sua máquina para a nuvem de outra pessoa. Para
devs independentes isso é inconveniente; para empresas, é risco
jurídico, problema de compliance e dependência estratégica.

Mesmo as alternativas "open" deixam um vácuo: as open-source não têm
RAG decente nem chat web multi-usuário; as comerciais cobram por
assento e mandam tudo para a nuvem delas.

O mercado de agentes de IA explodiu, mas quase todas as soluções —
cloud ou self-hosted — resolvem o mesmo problema (escrever código com
um LLM bom). **Nenhuma resolve o problema adjacente e mais difícil:
fazer o agente conhecer de verdade o seu projeto.** Sem conhecimento
indexado, o agente alucina sobre a base, ignora convenções, desconhece
a doc interna — e quanto maior o projeto, pior.

### A solução

Vectora é um **agente de IA local-first**: instala e roda na sua
própria máquina ou num servidor que você controla. Base de
conhecimento, histórico de sessões e documentos indexados ficam no seu
ambiente. Não há login obrigatório, não há nuvem obrigatória — o
**Free tier roda 100% local, sem conta**.

O plano **Pro é opcional** e cobre trial, billing e licenciamento via
`services.vectora.company` — um Worker Cloudflare pequeno e focado, não
um backend SaaS que hospeda ou executa instâncias do produto por conta
do usuário. Contratar Pro não muda onde o agente roda; muda apenas
quais recursos (stack de alto desempenho, chat web multi-usuário,
webhooks, REST API) ficam disponíveis.

A diferença para outras alternativas self-hosted: Vectora é um
**produto comercial maduro**, não um projeto de fim de semana. Entrega
RAG de produção, chat web multi-usuário com RBAC, integração MCP
nativa, instaladores assinados, auto-update e suporte direto do
fundador — combinação que produtos open-source de hobby raramente
entregam junta.

**Por que local-first significa controle real:**

- **Dados nunca passam por um servidor intermediário da Vectora
  Company.** O agente conecta direto às APIs configuradas (OpenAI,
  Gemini, Cohere, Anthropic, Tavily) e aos MCPs instalados.
- **LGPD/GDPR**: a responsabilidade pelo tratamento dos dados é entre
  o operador e cada provider conectado. Os Termos de Uso descrevem
  exatamente o que trafega em cada integração.
- **Auditável internamente**: clientes Pro+ recebem o binário
  compilado e documentação completa de arquitetura; Enterprise pode
  solicitar auditoria de código sob NDA.

**O que isso NÃO é:** Vectora não é open source. É código proprietário
licenciado — parecido com Cursor, Linear ou Notion: você roda na sua
infra, mas o código-fonte é da empresa. A diferença central é que **a
infra é sempre sua**. Versões anteriores do projeto foram publicadas
como Apache 2.0 durante a fase de prototipagem; essa fase terminou.
Quem instalou as versões antigas continua livre para mantê-las, mas o
produto atual evolui sob licença comercial.

### O que Vectora **é**

- **Local-first, sem login obrigatório.** Free tier funciona
  inteiramente offline de conta — só as APIs de LLM/RAG que você mesmo
  configurar exigem rede.
- **Agente com memória real.** RAG sobre código, docs, decisões e
  histórico de trabalho — não um assistente amnésico que esquece o
  projeto a cada mensagem.
- **Arquitetura deep-agent.** Orquestrador + subagentes especializados
  (coder, search) via `create_deep_agent` (LangGraph/deepagents), com
  middleware HITL para ações destrutivas — não uma rede neural própria
  fazendo roteamento.
- **Auditável.** Toda resposta cita fontes (`[1] [2]`). Toda tool call
  é registrada com input/output. Toda decisão de routing é rastreável.
- **Multi-modal nativo.** LLM + embedding + reranker + STT + TTS +
  geração de imagem sob protocolos abstratos — trocar provider é
  mudança de config, não de código.
- **Multi-acesso.** O mesmo agente atende via CLI, chat web, desktop
  app, MCP server (delegação) e REST API (integração).
- **Multi-pessoa.** A mesma instalação serve devs sêniores, PMs,
  marketing, design e executivos — cada perfil acessa via persona
  packs que afinam o agente para seu domínio.
- **Auto-treinável.** Indexação via `/rag add`, comportamento ajustável
  via `AGENTS.md`, capacidades estendidas via Skills e plugins MCP. O
  usuário decide o que o agente sabe.

### O que Vectora **NÃO é** (anti-positioning explícito)

| Vectora **NÃO é**                                       | Para isso use:                                                                                         |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Gerador de apps com 1 prompt                            | Lovable, v0, Bolt.new, Replit Agent                                                                    |
| Autocomplete inline no editor                           | GitHub Copilot, Codeium, Cursor Tab                                                                    |
| Substituto de engenheiro júnior                         | Devin, Cognition, Magic.dev (quando provarem que funcionam de verdade)                                 |
| Chat de IA para conversa casual                         | ChatGPT, Claude.ai, Gemini app                                                                         |
| Assistente de reuniões                                  | Perssua, Otter.ai, Fireflies                                                                           |
| Wiki/documentação editorial colaborativa                | Notion, Confluence, Outline                                                                            |
| BI tool / dashboard SaaS dedicado                       | Metabase, Looker, Tableau                                                                              |
| Automação no-code de workflows                          | Zapier, n8n, Make                                                                                      |
| Plataforma de hosting de apps                           | Vercel, Netlify, Render                                                                                |
| Sistema de tickets / project management                 | Jira, Linear, Asana                                                                                    |
| CRM                                                     | Salesforce, HubSpot, Pipedrive                                                                         |
| Backend SaaS que hospeda instâncias do produto por você | Não existe — Vectora não roda "na nossa nuvem"; `services.vectora.company` só cuida de licença/billing |

Vectora **integra** com vários destes (via MCP ou plugins DLC), mas
**não substitui** nenhum.

### Frases que **não** devem ser usadas (anti-copy)

| Frase ruim                             | Por que é ruim                                                            |
| -------------------------------------- | ------------------------------------------------------------------------- |
| "Construa apps com IA em minutos"      | É promessa de vibe coding — não somos isso                                |
| "Substitua sua equipe de devs"         | Falso e antipático                                                        |
| "IA mais poderosa do mercado"          | Subjetivo, indefensável, todo mundo diz                                   |
| "Grátis para sempre"                   | Impreciso — Free é local e permanente, mas Pro é pago; ser preciso        |
| "Mais barato que ChatGPT Plus"         | Comparação errada — público diferente                                     |
| "Funciona sem configuração"            | Falso — exige instalar, configurar API keys, indexar workspaces           |
| "Tudo que ChatGPT faz, mas privado"    | Reduz Vectora a "ChatGPT local", ignora RAG/MCP/agentes                   |
| "Compatível com qualquer LLM"          | Vago e meio-verdade — só Gemini/OpenAI/Anthropic/Cohere/Ollama            |
| "Crie um SaaS completo com 1 prompt"   | Vibe coding outra vez                                                     |
| "Vectora Cloud" / "rodamos seu agente" | Não existe mais essa oferta — Vectora não hospeda instâncias de terceiros |

### Checklist de coerência

Toda peça pública (site, README, post, deck, vídeo) deve passar por:

- [ ] A frase canônica aparece sem mutação significativa
- [ ] Nenhuma das frases proibidas aparece
- [ ] Pelo menos uma das frases canon de venda é usada
- [ ] Se menciona concorrente, o diferencial está claro e honesto (sem fud)
- [ ] Se menciona price, está alinhado com `docs/products.md`
- [ ] Se menciona feature em roadmap, status correto (✅ disponível /
      🔄 em desenvolvimento / 📋 planejado)
- [ ] Se menciona open source, **deixa claro que NÃO é** (versões
      antigas Apache não contam)
- [ ] Nenhuma referência a "Vectora Cloud" rodando desktop de terceiros
      em Docker, a Supabase como backend, ou a uma rede neural própria
      (VCR) roteando o agente — nada disso existe no produto atual

Mudança de posicionamento (pivô de público, lançamento de produto
Tier 3, concorrente novo relevante) exige atualização deste doc com
aprovação explícita do fundador.

---

## Concorrência

> Análise honesta dos concorrentes diretos e adjacentes. Para cada
> player: forças, fraquezas, o que Vectora aprende, o que Vectora não
> vai copiar e por quê. Leitura interna — não é material de venda, mas
> alimenta as frases de posicionamento contra cada concorrente.
>
> **Atualizar trimestralmente.** Mercado de IA muda rápido demais para
> análise anual.

### Mapa do mercado

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
│ Aider, Continue.dev │      │ Local-first comerc. │      │ GitHub Copilot,     │
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

### Tier 1 — Concorrentes diretos (mesmo público)

#### 1. Claude Code (Anthropic)

CLI agentic first-party da Anthropic. Lock-in total a Claude, cloud-only.

**Forças:** UX de CLI excelente, Skills nativas (`.skill.md`, formato
que adotamos), MCP first-class, Plan mode profundo, slash commands
hierárquicos, hooks (`pre-tool-use`/`post-tool-use`/`stop`), background
tasks com notificação, documentação forte, integração com IDE.

**Fraquezas:** lock-in total a Claude (nenhum outro LLM mesmo via MCP),
cloud-only (código sempre passa pela Anthropic), sem chat web
multi-usuário, RAG fraco (depende de re-leitura de arquivos), caro
($20/mês entry + tokens via API), sem persona packs, sem REST API
pública.

**O que Vectora aprende:** adotar `.skill.md` (já fazemos), hooks
(roadmap), Plan mode explícito, slash commands hierárquicos (parcial),
status line custom no chat web, background tasks com notificação, CLI
paridade `mcp add/remove/list`.

**O que Vectora NÃO copia:** lock-in a LLM único (princípio
fundacional), cloud-managed (somos local-first), pricing alto, foco
engineering-only.

> _"Claude Code é excelente — usamos como referência de UX. Mas você
> fica refém de um único LLM, manda código para Anthropic, e seu time
> não-técnico não consegue usar. Vectora resolve os três."_

#### 2. Cursor

Editor (fork do VS Code) com agente integrado, cloud-managed. Produto
mais popular do segmento hoje.

**Forças:** Tab autocomplete treinado no codebase, Composer mode
(multi-file edits em batch), @-mentions universais, background agents,
bug hunter proativo, Privacy Mode contratual, modelos de ponta, grande
comunidade, pricing simples ($20/mês).

**Fraquezas:** cloud-managed (contexto sempre vai para a infra deles),
sem self-host/local-first real, RAG fraco vs Vectora, mono-pessoa (é
editor, não plataforma), sem MCP first-class, sem chat web, sem REST
API.

**O que Vectora aprende:** Composer mode (HITL agregado multi-arquivo),
@-mentions completos (`@docs`, `@web`, `@symbol`, `@past-chat` — já
temos `@file`), background agents com retomada, privacy mode explícito
na UI, bug hunter proativo opt-in, pricing simples.

**O que Vectora NÃO copia:** tab autocomplete treinado por usuário
(anti-vibe-coding), ser um editor (somos plataforma, integramos via
VSIX), cloud-managed, mono-pessoa.

> _"Cursor é o melhor editor com IA do mercado. Mas seu CTO não
> consegue auditar o código que processa seus dados, seu PM não pode
> usar para fazer PRDs, e seu sistema interno não tem API para
> integrar. Vectora integra com Cursor via MCP — e cobre os outros
> casos."_

#### 3. Codeium / Windsurf

Autocomplete (Codeium) + editor agentic (Windsurf), mesmo player,
cloud-managed.

**Forças:** Cascade mode agentic, Flow mode (contexto entre sessões),
live preview integrado, free tier generoso, enterprise self-hosted
(único nesse segmento).

**Fraquezas:** sem MCP/extensibilidade externa, sem RAG sobre docs
personalizados, sem chat web para times, pricing enterprise opaco
(>$15k/ano), UX inconsistente entre os dois produtos sob a mesma marca.

**O que Vectora aprende:** live preview (render hint já em
`agent-core-roadmap.md`), Flow mode (memória semântica entre dias), Cascade
mode (já coberto via Deep Agents), self-host como diferencial
enterprise validado.

**O que Vectora NÃO copia:** dois produtos com mesma marca (Vectora é
um produto só), pricing enterprise opaco.

> _"Codeium/Windsurf provou que self-hosted vende bem em enterprise.
> Vectora democratiza isso — instala a partir de R$20/mês, não
> $15k/ano."_

#### 4. Aider (open source)

CLI agentic Python, MIT, pair-programming via terminal.

**Forças:** auto-commit com mensagem AI gerada, repo-map via
tree-sitter, lint+test loop com auto-fix, voice mode, architect/coder
split, `CONVENTIONS.md` injetado, integração git nativa, gratuito.

**Fraquezas:** CLI-only, mono-pessoa, sem MCP, sem RAG semântico
(repo-map é estático), sem multi-LLM trivial, sem persona packs.

**O que Vectora aprende:** auto-commit opcional (flag por workspace),
repo-map tree-sitter como complemento ao RAG vetorial, lint+test loop
como skill, architect/coder split (economia de tokens), voice mode
(já planejado em `extensibility-roadmap.md`).

**O que Vectora NÃO copia:** CLI-only (somos multi-modo), open source
(escolha estratégica comercial), mono-pessoa.

> _"Aider é uma obra de engenharia. Se você é dev solo no terminal, use
> Aider — é gratuito. Vectora atende você ao escalar para time,
> precisar de chat web, integrar com sistemas, ou estender com MCP."_

#### 5. Continue.dev (open source)

Extensão VS Code/JetBrains open source, agente configurável.

**Forças:** context providers extensíveis, multi-provider real
(incluindo Ollama), local-first com Ollama polido, custom commands,
Apache 2.0.

**Fraquezas:** só dentro de IDE, sem CLI, sem chat web, sem MCP
(atrasado), configuração complexa (`config.json` enorme), RAG
experimental, UX inferior a Cursor.

**O que Vectora aprende:** context providers como API plugável
(nosso RAG hoje é hardcoded), multi-provider polido (já temos, validar
UX), wizard de setup Ollama melhor.

**O que Vectora NÃO copia:** só IDE, open source, configuração via JSON
pesada.

> _"Continue.dev é a opção open source para extensão de IDE. Se você só
> quer chat dentro do VS Code e tudo bem configurar JSON, use. Vectora
> oferece VSIX equivalente + chat web + CLI + REST API + RAG de
> produção — pagando $7-20/mês."_

#### 6. Sourcegraph Cody

Agente focado em code search em escala, com versão self-hosted
Enterprise.

**Forças:** multi-repo context, code graph via análise estática,
self-host enterprise maduro, integração com Sourcegraph Search, suporte
a stacks legados.

**Fraquezas:** caríssimo (~$60–200/dev/mês), Cody isolado é fraco
(depende de Sourcegraph rodando), setup pesado, sem MCP, sem persona
packs.

**O que Vectora aprende:** multi-repo context (gap real hoje), code
graph complementar ao RAG (análise estática de calls/refs), self-hosted
enterprise vende bem.

**O que Vectora NÃO copia:** pricing enterprise (somos PME-first),
acoplamento a outra ferramenta, setup pesado.

> _"Sourcegraph Cody é a opção para empresa BIG que já paga
> Sourcegraph. Vectora atende PMEs que querem ~90% do valor por ~10% do
> preço, sem precisar instalar stack inteiro."_

#### 7. Devin / Cognition AI

"Primeiro engenheiro de software AI". Workspace visível, long-running
tasks, cloud-managed e caro.

**Forças:** long-running tasks com retomada, workspace visível
(browser + terminal), memória de sessões passadas, planning interface
explícita, marketing forte.

**Fraquezas:** cloud-managed e caro ($500/mês entry), resultados
inconsistentes (benchmarks mostraram demo cherry-picked), sem
self-host, sem MCP, posicionamento "substituir júnior" é polêmico.

**O que Vectora aprende:** workspace visível (workbench já existe,
aumentar visibilidade), long-running tasks com retomada, planning
interface explícita, memória de sessões passadas (já via LangGraph
Store).

**O que Vectora NÃO copia:** pricing $500/mês, posicionamento
"substitui júnior" (falso e antipático), marketing cherry-picked,
cloud-only.

> _"Devin é demo bonito por $500/mês. Vectora é produto real por
> $7–20/mês que você instala na sua infra, faz o que diz que faz, e seu
> time aprende a usar bem em 1 semana."_

#### 8. Replit Agent

Agente integrado ao Replit IDE, fullstack scaffolding em minutos.

**Forças:** live preview embutido, fullstack scaffolding rápido, deploy
integrado, excelente para protótipos, free tier funcional.

**Fraquezas:** roda só no Replit (sem self-host/local), foco vibe
coding (não para engenheiros sêniores), sem RAG sobre projetos
externos, lock-in à infra Replit.

**O que Vectora aprende:** live preview embutido (`dashboard_preview`,
`live_preview`), scaffolding como skill.

**O que Vectora NÃO copia:** foco vibe coding (anti-positioning
explícito), cloud-only, lock-in de hosting.

> _"Replit Agent é ótimo para prototipar app do zero em 10 minutos. Mas
> não serve para trabalhar em codebases existentes, atender time
> multi-disciplinar, ou rodar na sua infra. Use Replit para protótipo,
> Vectora para o produto sério."_

### Tier 2 — Concorrentes adjacentes (público diferente, sobreposição parcial)

**GitHub Copilot** — autocomplete + chat, cloud-only. Sobreposição
baixa (Copilot é autocomplete, Vectora é agente). Sem RAG, sem MCP, sem
self-host, sem chat web, sem persona packs. Aprendizado: distribuição
via Marketplace VS Code, pricing competitivo, GitHub Actions oficial.

> _"Copilot é autocomplete; Vectora é agente. São coisas diferentes —
> muitos usuários usam ambos."_

**Tabnine** — autocomplete enterprise self-hosted, cliente histórico em
setor regulado. Confirma que setor regulado paga bem por self-hosted;
compliance certifications (SOC 2, HIPAA, ISO) atraem enterprise.

**Pieces** — snippet manager + AI, local-first. Sobreposição baixa
(knowledge management vs agente). Aprendizado: context awareness
automático (clipboard, browser, IDE state), local-first vendido bem.

**Greptile** — code review automation com RAG, cloud-only.
Sobreposição alta com o futuro Vectora Code Review (Tier 3). Confirma
viabilidade de pricing (~$30/dev/mês); aprendizado de UX de comentário
inline no PR e onboarding via GitHub App.

**CodeRabbit** — AI code review via GitHub App, cloud-only.
Sobreposição alta com Vectora Code Review. Aprendizado: ARPU realista
($24/dev/mês), não ser verboso demais nos comentários.

**Gemini CLI (Google)** — CLI agentic similar a Claude Code, com
extensions marketplace integrado. Aprendizado crítico: marketplace de
extensões dentro do produto (não só GitHub awesome list) valida
`extensibility-roadmap.md`; discovery integrado é vetor de adoção.

### Tier 3 — Adjacências importantes (não competimos, mas referência)

**Lovable / v0 / Bolt.new (vibe coding)** — geração de apps fullstack a
partir de prompt, cloud-only. Sobreposição zero — anti-positioning
explícito. Aprendizado: vibe coding é mercado grande mas com teto baixo
(apps gerados não evoluem para produção); UX de live preview é mestre;
tese de que vibe coding atrai juniors/não-devs, Vectora atrai sêniores.

**Perssua (BR)** — assistente de reuniões brasileiro (Lucas Montano).
Sobreposição zero — mercado diferente. Diferencia falantes, transcreve
em tempo real, traduz ao vivo, modo stealth.

|                    | Vectora                                  | Perssua                                 |
| ------------------ | ---------------------------------------- | --------------------------------------- |
| Para quem          | Devs e times técnicos                    | Profissionais em reuniões               |
| Foco central       | Agente de desenvolvimento com RAG        | Assistente de reuniões                  |
| Forma de acesso    | CLI, chat web, desktop, MCP, REST        | App desktop exclusivo                   |
| RAG                | Pilar central — indexa código/docs       | Presente, não divulgado                 |
| Áudio              | STT/TTS via API (input/output do agente) | Diferenciação de falantes em tempo real |
| Execução de código | Terminal, edição, git                    | Não é o foco                            |
| Modo MCP           | Parceiro de outros agentes               | Não tem                                 |
| Local-first        | Sim (VPS ou local)                       | Sim (app local)                         |

Rivalizamos muito mais com Claude Code/Cursor/OpenCode/Hermes. Um dev
pode usar Perssua em reuniões e Vectora no terminal sem conflito.
Aprendizado: produto BR pode vencer contra player global (Otter,
Fireflies); solo founder vende bem em PT-BR; self-hosted "no desktop"
também tem mercado.

**Aider / OpenCode / OpenDevin / Hermes Agent (open source local-first)**
— sobreposição alta no público-alvo (devs preocupados com privacidade),
baixa no produto (eles são open + free, Vectora é comercial + pago).
Open source não monetiza facilmente — comunidade sem receita. Vectora
oferece "open source-like UX" (local-first, auditável sob NDA) +
suporte profissional pago; pricing barato ($7/mês) reduz fricção vs
grátis.

> _"OpenCode/Hermes são open-source legítimos. Se você quer total
> liberdade de código + zero pagamento, use. Vectora atende quem
> prefere produto polido + suporte direto + atualizações garantidas por
> $7/mês."_

### Tier 4 — Players observados mas não relevantes hoje

| Player                | Por que monitorar                               |
| --------------------- | ----------------------------------------------- |
| Magic.dev             | Pode ser próximo Devin — vale acompanhar        |
| Sourcegraph Cody      | Já coberto, mas reposicionando-se em 2026       |
| Sweep AI              | PR automation focado em issue → PR              |
| Pythagora / GPT Pilot | App generation similar a Devin                  |
| MetaGPT               | Multi-agente acadêmico, sem produto consumer    |
| CrewAI                | Framework de multi-agente, não produto end-user |
| Cline (open source)   | Ex-Claude Dev — extensão VS Code agentic        |
| DeepSeek Coder        | Modelo open weights; muda landscape de LLM      |

### Padrões transversais — o que TODOS estão fazendo

Observado em 5+ players: MCP first-class virou padrão de fato,
multi-LLM com BYOK (lock-in a um LLM virou tabu), plan mode explícito,
workspace visível (não-blackbox), HITL para ações destrutivas, cost
tracking visível, skills/custom commands extensíveis, hooks/triggers
além do chat. Vectora já cobre os 8 ou tem em roadmap.

### Padrões transversais — o que NINGUÉM está fazendo bem

Oportunidades de diferenciação:

1. Marketplace integrado de MCPs no produto (Gemini CLI é o único que
   tenta, UX ainda fraca) → `extensibility-roadmap.md`
2. Persona packs para não-devs — ninguém faz, gap real → seção
   Personas abaixo
3. Beta program estruturado com recompensa — ninguém formaliza →
   `launch-and-distribution.md`
4. Chat web multi-usuário local-first → Vectora único
5. REST API + OAuth + Webhooks para sistemas internos → ninguém no
   segmento PME
6. Seis modalidades de IA nativas (LLM+embedding+rerank+TTS+STT+imagem)
   → ninguém combina; ver `extensibility-roadmap.md`
7. Instalação modular via packs Nuitka — ninguém faz, binário pesado
   sem opção slim → `agent-core-roadmap.md`
8. CLI paridade Claude Code para migração trivial — ninguém oferece

### Matriz comparativa consolidada

| Feature                       | Vectora  | Claude Code | Cursor | Aider | Continue |  Cody   |  Devin  | Copilot |
| ----------------------------- | :------: | :---------: | :----: | :---: | :------: | :-----: | :-----: | :-----: |
| Local-first / self-hosted     |    ✅    |     ❌      |   ❌   |  ✅   |    ✅    |   ✅¹   |   ❌    |   ❌    |
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
🔄 Em desenvolvimento · 📋 Planejado (não documentado formalmente ainda)

### Aprendizados consolidados (lista priorizada)

**Top 5 pré-lançamento:** hooks (Claude Code), Plan mode explícito
(Claude Code + Devin), @-mentions universais (Cursor), Composer mode
(Cursor), auto-commit opcional (Aider).

**Top 5 pós-lançamento:** multi-repo context (Cody), code graph com
tree-sitter (Aider + Cody), architect/coder split (Aider), background
agents com retomada (Cursor), bug hunter proativo opt-in (Cursor).

**Top 3 "não fazer":** não copiar Devin (long-running autônomo sem
supervisão é bandeira vermelha — preferimos HITL + workspace visível);
não copiar vibe coding (público diferente, anti-positioning
estratégico); não copiar pricing enterprise opaco (preferimos
transparência + ARPU baixo).

---

## Personas / buyer-anti-buyer

> Pacotes pré-curados de Skills + tools + prompts para personas
> específicas. Um membro não-técnico do time usa o mesmo Vectora dos
> engenheiros, com o agente afinado ao contexto dele.
>
> **Princípio:** Vectora é um único produto, **não 8 produtos**.
> Persona pack é camada de personalização sobre o core — não um fork.
> Mesma instalação, mesma KB, mesma infra.

### Para quem Vectora foi feito (buyer personas)

**Primária — Engenheiro Sênior + Tech Lead.** 5+ anos de experiência,
lê stack trace, sabe o que é race condition. Não pede para a IA
"resolver o bug" — pede para mostrar onde o estado divergiu e propor
abordagens com trade-offs. Trabalha em projetos de médio/grande porte
(monolitos legados, microserviços com convenções internas, 50k+
linhas). Já testou Cursor/Copilot, gostou em parte, mas se frustra
quando o modelo ignora padrões da equipe. Valoriza local-first por
motivos reais: código proprietário, dados de cliente, regulação
setorial. Preço de $7–20/mês é trivial vs a hora dele.

**Secundária — Time técnico (3–50 devs).** CTO/VP Engineering/EM decide
a compra. Cada dev usa via VSIX, chat web ou desktop; compartilham
workspaces, decisões, skills internas. Empresa com alguma sensibilidade
a dados (fintech, saúde, jurídico, governo, defesa). Já tem
Cohere/Tavily ou aceita pagar; já tem PostgreSQL/Redis ou aceita subir.

**Terciária — Não-técnicos do mesmo time.** PM, Product Designer,
Marketing, Sales, Exec da mesma empresa. **Não compra o Vectora
sozinho** — chega por arrasto, porque o time técnico já tem. Usa para
tarefas adjacentes (PRD com contexto do produto, deck com dados do RAG,
resumo de reunião). Instala persona packs específicas (ver seção
abaixo). Pressiona admin a comprar plano Team para liberar Vectora para
mais gente da empresa.

**Enterprise — Empresa com requirements pesados.** 50+ devs ou setor
regulado. Compra OEM ou Enterprise. Quer SLA, DPA, suporte dedicado,
auditoria sob NDA, on-premise air-gapped. Ciclo de venda longo (3–6
meses) — não é foco do primeiro ano.

### Para quem Vectora **NÃO** foi feito (anti-buyer personas)

- **"Vibe coder" / não-engenheiro construindo app.** Quer 3 mensagens →
  SaaS pronto, não lê código, confia 100% no LLM. Use Lovable, v0 ou
  Bolt — Vectora vai frustrar essa pessoa porque exige entender o que
  está acontecendo e ler o diff antes de aprovar.
- **Dev júnior aprendendo.** Vectora é poderoso demais sem supervisão —
  tools destrutivas (terminal, edit, git push) podem causar estrago.
  Recomendação honesta: Copilot ou Cursor por 6+ meses, migrar para
  Vectora quando souber o que está aprovando.
- **Quem quer "IA grátis" ilimitada e sem instalar nada.** O Free tier
  é local e permanente, mas exige instalar e trazer as próprias chaves
  de API — não é um serviço hospedado grátis. Quem quer zero setup e
  zero custo de infra local usa OpenCode, Continue.dev ou Aider
  (open-source de verdade) ou paga um SaaS cloud-managed direto.
- **Quem precisa de assistente de reuniões / áudio em tempo real.**
  Vectora tem TTS/STT (via `extensibility-roadmap.md`) como input/output do agente,
  não diarização ao vivo de reuniões. Use Perssua (BR) ou Otter.ai /
  Fireflies.
- **Marketing genérico, ops sem RAG necessário.** Quem só quer "ChatGPT
  pra escrever post de LinkedIn" não precisa do Vectora — use ChatGPT
  direto. Vectora faz sentido para marketing **quando** existe brand
  voice documentada + histórico de campanhas indexado + integração com
  analytics; sem RAG, é overkill.

### Como funciona um persona pack

Cada persona pack é um diretório no formato Skills do Vectora:

```
~/.vectora/personas/<persona-slug>/
├── manifest.json          # nome, descrição, versão, autor, tools necessárias
├── system_prompt.md       # injetado no orchestrator quando ativo
├── skills/                # skills específicas da persona
├── slash_commands/        # /comandos custom expostos no chat
├── recipes/               # workflows multi-step exemplificados
└── kb/                    # KB embedada na instalação (opcional)
```

Lifecycle via CLI: `vectora personas list / install / activate /
deactivate / remove`. O header do chat web mostra a persona ativa com
switch rápido via dropdown — trocar de persona não perde contexto da
conversa, só muda comportamento e sistema do agente.

Distribuição em três camadas: **first-party** (mantidos pela Vectora
Company, marketplace `vectora.company/personas`), **community**
(qualquer um publica, mesma estrutura Skills, sem certificação), e
**internal** (empresa cria packs próprios para cargos específicos via
registry custom).

### Catálogo de persona packs

| Pack                    | Para quem                                           | Exemplo de uso                                                                            |
| ----------------------- | --------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **Marketing**           | Marketing manager, content creator, growth marketer | Gera posts com brand voice via RAG, analisa performance de campanha vs trimestre anterior |
| **Designer**            | Product/UX/UI designer                              | Audita acessibilidade WCAG de uma página, gera mockup a partir de descrição               |
| **Product Manager**     | PM, Product Owner, founder-PM                       | PRD com contexto histórico de decisões via RAG + issues do Linear                         |
| **Liderança / C-Level** | CEO, CTO, CFO, founders multi-papel                 | Dashboard executivo, análise de retenção com hipóteses via RAG de eventos do trimestre    |
| **Sales / BD**          | AE, BDR, SDR, founder vendendo                      | Briefing pré-call com research de conta, CRM e LinkedIn combinados                        |
| **Ops / IT / DevOps**   | Sysadmin, SRE, IT manager                           | Triagem de alerta cruzando Datadog + kubectl + runbooks similares no RAG                  |
| **Compliance / Legal**  | Compliance officer, DPO, legal counsel              | Responde security questionnaire de 80 perguntas com base em políticas já documentadas     |
| **Data Analyst**        | Data analyst, BI specialist                         | Gera SQL, roda análise de coorte, monta dashboard e interpreta significância estatística  |
| **Onboarding**          | Novo funcionário em qualquer cargo                  | Trilha personalizada de 30/60/90 dias + Q&A sobre a "alma" da empresa via RAG             |
| **Engineering Lead**    | Tech lead, EM (refina a persona primária)           | Prep de 1:1 cruzando PRs, sprint e conversas recentes do membro do time                   |

Cada pack define tools necessárias, skills, slash commands e recipes
(workflows multi-step) próprios — detalhamento técnico completo por
pack vive no backlog de produto, não neste documento de mercado.

### Pricing dos persona packs

| Pack                                       | Preço        | Tipo              |
| ------------------------------------------ | ------------ | ----------------- |
| Marketing / Designer / PM / Sales          | $10/mês/user | DLC               |
| Leadership                                 | $15/mês/user | DLC (premium)     |
| Data Analyst                               | $15/mês/user | DLC (premium)     |
| Compliance                                 | $20/mês/user | DLC (specialized) |
| Onboarding                                 | $5/mês/user  | DLC (light)       |
| Ops / IT                                   | Incluso Pro  | Bundle            |
| Engineering Lead                           | Incluso Team | Bundle            |
| Productivity Pack (Marketing + PM + Sales) | $25/mês/user | Bundle (40% desc) |
| Enterprise Pack (todos)                    | $50/mês/user | Bundle            |

Empresa com Team de 10+ seats pode ter um pack incluso gratuitamente
por seat (ex: empresa de design libera o Designer pack para todo o
time). Empresas também podem criar persona packs internos próprios
(`vectora personas create` / `publish --registry`) sem depender da
Vectora Company.

### Princípios cardinais dos persona packs

1. Um Vectora, múltiplas personalidades — personalização sobre o core,
   não forking.
2. Switching é trivial — trocar de persona não perde contexto da
   conversa.
3. Personas reusam a mesma KB — diferentes lentes sobre os mesmos
   workspaces.
4. Qualidade > quantidade — melhor poucos packs excelentes que muitos
   medianos.
5. Community + first-party lado a lado, com barra de qualidade
   diferente.
6. Tier gates honestos — sempre claro o que é bundle vs DLC pago.
7. Persona não substitui produto Tier 3 independente (ex: persona
   "Customer Support" interna serve o suporte da própria empresa;
   Vectora Helpdesk continua produto separado para atender cliente
   final).

---

## Pitch / narrativa de venda

### Frases canon de venda por público

**Tech lead / engenheiro sênior:**

> _"Cursor é ótimo até você cansar de explicar a mesma decisão de
> arquitetura toda semana. Vectora lembra — porque você indexou no
> RAG. E roda na sua infra, então pode ler todo o código sem medo."_

**CTO de PME tech:**

> _"Local-first comercial. Sem markup de tokens. Mesmo agente atende
> seus devs (via VSIX/chat), seu PM (via persona pack), e sistemas
> internos (via REST API). $20/mês por seat ou plano Team para o time
> inteiro."_

**Empresa em setor regulado:**

> _"Seus dados nunca passam pelo nosso servidor — você liga direto às
> APIs que escolheu. Auditoria de código sob NDA. Suporte para
> on-premise air-gapped no plano Enterprise."_

**Usuário não-técnico do mesmo time:**

> _"O Vectora já está rodando no servidor da sua empresa. Você instala
> a persona pack 'marketing' (ou 'design', 'pm', 'sales') e ganha um
> assistente que conhece os clientes, as campanhas e a marca — porque
> tudo já está no RAG da empresa."_

**Integrador / partner:**

> _"REST API limpa, OAuth2 client credentials, SDKs Python/TS, MCP
> server expondo todas as tools. O Vectora vira o motor RAG do seu
> produto sem você precisar construir o pipeline do zero."_

### Concorrente e parceiro ao mesmo tempo

À primeira vista, Vectora compete com Claude Code, Cursor, OpenCode e
Hermes Agent — como CLI ou chat, é alternativa direta. Mas Vectora tem
um modo que nenhum concorrente direto tem: **modo MCP**. Expõe
`delegate_to_vectora` — qualquer agente externo pode invocar.

Um dev pode continuar usando Claude Code ou Cursor no dia a dia e,
quando chega num limite (indexar conhecimento, RAG em docs internas,
busca com relevância semântica), **delega para o Vectora**. Nossos
concorrentes viram usuários do Vectora — não substituímos o fluxo de
trabalho, o estendemos.

### Por que agora

O Vectora resolve o problema adjacente que nenhum concorrente resolve
de verdade: fazer o agente conhecer o projeto. RAG **como pilar
central**, não feature secundária — o único agente de desenvolvimento
com sub-agente dedicado exclusivamente à recuperação e auditoria de
conhecimento. Quando o Vectora responde sobre o projeto, responde **com
base no que foi indexado** — não no que o modelo achou que era
verdade.

### Arquitetura de agentes (para audiência técnica)

Vectora não é um único modelo respondendo perguntas — é um sistema de
agentes especializados orquestrados via `create_deep_agent`
(LangGraph/deepagents):

- **Vectora Agent (orquestrador)** — recebe a tarefa, decide qual
  subagente acionar, consolida respostas. Ponto de entrada único, para
  o usuário e para quem delega via MCP.
- **Vectora RAG Agent** — indexa qualquer base (docs, código, wikis,
  PDFs) e responde com contexto real do projeto. Nenhum concorrente
  direto tem sub-agente dedicado a isso.
- **Vectora Search Agent** — relevância e apresentação: filtra ruído,
  reordena por relevância, entrega no formato útil (busca web →
  curadoria via reranker + LLM judge → injeção no contexto).
- **Vectora Coder Agent** — escreve, revisa e refatora código com
  entendimento do padrão do projeto. Suporta git workflows completos,
  worktrees, terminal integrado.
- **Vectora Media Agent (roadmap)** — quando o volume de operações de
  mídia justificar um sub-agente dedicado; hoje as tools de mídia vivem
  no orchestrator.

Pipeline de RAG completo (ingestão → expansão de query → busca híbrida
dense+esparsa → score gate → reranking ou busca web com curadoria →
síntese com citações verificáveis `[1][2]`) — nenhum resultado chega ao
LLM sem passar pelo filtro de relevância.

### Seis modalidades de IA, sem lock-in

LLM chat/code, LLM multilingual (Cohere Aya), embedding, reranker, STT,
TTS e geração de imagem — cada categoria com provider escolhido por
mérito (Gemini como canivete suíço multimodal, Cohere como backbone do
RAG, OpenAI/Anthropic como opcionais premium), tudo sob protocolo
abstrato: trocar provider é mudança de config. Geração de vídeo fica
fora de escopo por ora (custo 20–100× maior, latência inviável para UX
de chat).

### Cinco modos de uso (mesmo binário)

CLI/TUI, chat web multi-usuário (RBAC), desktop app nativo assinado
(Windows/macOS/Linux, Electron + Nuitka onefile, IPC local nunca TCP),
MCP server (consumido por Claude Code, Cursor, Zed, JetBrains e
qualquer cliente MCP), e modo headless via REST API v1 (OAuth2 client
credentials, compat OpenAI, webhooks) para integradores (n8n, Zapier,
Make, GitHub Actions, sistemas corporativos).

### Modelo de negócio

Preços deliberadamente baixos — volume e fidelização, não margem alta
em poucas contas.

| Plano          | Preço                | Inclui                                                                                                                                                             |
| -------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Free**       | Grátis, permanente   | 100% local, sem conta. CLI + MCP + Desktop + stack econômica (SQLite/LanceDB). Traz as próprias chaves de API.                                                     |
| **Plus**       | $7 / R$20 por mês    | Tudo do Free + quotas mensais leves de créditos de parceiros (Cohere/Tavily), sem precisar de chave própria.                                                       |
| **Pro**        | $20 / R$55 por mês   | Tudo do Plus + chat web multi-usuário + stack de alto desempenho (Postgres/Qdrant/Redis) + webhooks + REST API v1. Billing/licença via `services.vectora.company`. |
| **Team**       | $49 / R$130 por mês  | Tudo do Pro + Host/Client + VSIX + SSO (quando essas frentes entregarem).                                                                                          |
| **OEM**        | A partir de $199/mês | Uso comercial via REST API para servir usuários externos, tiers escaláveis.                                                                                        |
| **Enterprise** | Contrato customizado | SLA, suporte dedicado, DPA, revenue share, on-premise air-gapped.                                                                                                  |

A assinatura cobre software, suporte, atualizações e créditos
opcionais de parceiros (Cohere/Tavily) — nunca tokens de LLM/embedding
além da quota do plano: esses são pagos direto ao provider escolhido,
sem markup. Quem traz a própria chave (BYOK) bypassa as quotas
mensais. Cobrança regionalizada: Asaas no Brasil (PIX, boleto, cartão,
Pix Automático), Stripe internacional (cartão, Apple Pay, Google Pay,
Link). Cancelamento self-service, acesso até o fim do período pago,
reembolso de 14 dias após a primeira cobrança paga.

### Vectora para empresas

Uma empresa instala **um único Vectora** no servidor interno; os
funcionários acessam pelo browser sem instalar nada localmente. O
agente tem acesso à worktree dos projetos internos e pode contribuir
diretamente no código (com HITL para ações destrutivas). Histórico de
sessões e KB ficam no servidor da empresa; custo escala com tokens
consumidos nas APIs escolhidas, não por assento na cobrança da Vectora.

Dois modos de integração com sistemas internos via headless REST API:

| Modo         | Como funciona                                                | Para quem                                               |
| ------------ | ------------------------------------------------------------ | ------------------------------------------------------- |
| **Headless** | Sistema usa Vectora diretamente como backend via REST/OAuth  | Quem precisa que 100% das respostas venham do RAG       |
| **MCP**      | Outros agentes delegam tarefas para o Vectora quando preciso | Times que já têm agente preferido e querem estender RAG |

### Parceiros estratégicos

Vectora não é só cliente do Cohere e do Tavily — é canal de
distribuição para ambos. **Cohere** é o backbone estrutural em quatro
camadas não-triviais de substituir (embedding, reranker, STT,
multilingual via Aya) — ganha receita independente de qual LLM vence.
**Tavily** é o motor de busca web (Search Agent, fallback do RAG,
web cache); como é B2B puro sem produto consumer, Vectora é vetor
natural de adoção. Princípio fundacional: em qualquer parceria, acesso
a LLMs concorrentes nunca é removido — democratizar escolha é parte da
proposta.

### Diferenciais em resumo

|                                            |       Vectora       | Claude Code |  OpenCode  |      Codex      |   Hermes   | Cursor  |
| ------------------------------------------ | :-----------------: | :---------: | :--------: | :-------------: | :--------: | :-----: |
| Local-first (sua infra)                    |         ✅          |     ❌      |     ✅     |       ❌        |     ✅     |   ❌    |
| Código auditável internamente              |  ✅ (sob NDA Pro+)  |     ❌      | ✅ (open)  |       ❌        | ✅ (open)  |   ❌    |
| RAG dedicado com sub-agente                |         ✅          |     ❌      |     ❌     |       ❌        |     ❌     | Parcial |
| Multi-LLM (OpenAI+Gemini+Anthropic+Cohere) |         ✅          |     ❌      |     ✅     |     Parcial     |     ✅     | Parcial |
| Multi-agente especializado                 |         ✅          |     ❌      |     ❌     |     Parcial     |  Parcial   |   ❌    |
| Chat web multi-usuário (RBAC)              |         ✅          |     ❌      |     ❌     |       ❌        |     ❌     |   ❌    |
| MCP server (parceiro de outros agentes)    |         ✅          |     ❌      |     ❌     |       ❌        |     ❌     |   ❌    |
| REST API + SDKs Python/TS                  |         ✅          |   Parcial   |     ❌     |       ❌        |     ❌     |   ❌    |
| Webhooks                                   |         ✅          |     ❌      |     ❌     |       ❌        |     ❌     |   ❌    |
| App desktop nativo assinado                |         ✅          |     ❌      |     ❌     |       ❌        |     ❌     |   ✅    |
| Auto-update                                |         ✅          |     n/a     |   manual   |       n/a       |   manual   |   ✅    |
| Áudio (STT + TTS)                          |      🔄 em dev      |     ❌      |     ❌     |       ❌        |     ❌     |   ❌    |
| Geração de imagens                         |      🔄 em dev      |     ❌      |     ❌     |       ❌        |     ❌     |   ❌    |
| Custo                                      |      $0–20/mês      | $20–200/mês |   Grátis   | Inclus. ChatGPT |   Grátis   | $20/mês |
| Suporte direto do fundador                 | ✅ (WhatsApp/email) |     ❌      | comunidade |       ❌        | comunidade |   ❌    |

### Para quem é o Vectora (resumo executivo)

**Idealmente:** dev solo profissional (Free ou Plus cobre a maior parte
do uso); time de 3–10 devs (Pro numa VPS de R$50–100/mês, cada dev via
chat web ou MCP do editor preferido); PME tech até 50 devs (Pro
multi-tenant, Team quando Host/Client entregar); empresa com sistemas
internos (tier OEM para alimentar produtos próprios via REST API).

**NÃO é para:** quem quer chat de IA para conversa casual (ChatGPT
free); quem quer assistente de reunião (Perssua); quem só quer
autocomplete de código sem RAG (GitHub Copilot).

### Roadmap resumido (contexto de pitch)

Vectora hoje cobre o **Tier 1** do plano de portfólio. Em
desenvolvimento nos próximos meses: IA+ (TTS/STT/geração de imagem),
Deep Agents com sandbox e worktree por usuário, hardening de storage,
REST API v1 completa, cache distribuído. **Tier 2** (6–12 meses): VSIX
oficial, Host/Client (servidor central + cliente local por dev),
marketplace de plugins/DLC pagos. **Tier 3** (ano 2+): produtos
independentes que funcionam sem o Vectora mas se integram via RAG —
núcleo recomendado é Vectora Helpdesk e Vectora Code Review; demais
candidatos avaliados condicionalmente conforme tração.

### Contato

**Bruno Soares** — fundador e único desenvolvedor (por enquanto)

- Suporte comercial: support@vectora.company
- Site: vectora.company (em construção)
- Docs: docs.vectora.company (em construção)
- WhatsApp: disponível para clientes Pro+ após assinatura
- Status page: status.vectora.company

---

_Vectora — software comercial local-first. Sua infra, seus dados, seu
controle._
