# Vectora — Persona Packs

> Pacotes pré-curados de Skills + tools + prompts otimizados para
> personas específicas. Permite que um membro não-técnico do time use o
> mesmo Vectora dos engenheiros, com o agente afinado para o contexto
> dele.
>
> **Princípio:** Vectora é um único produto, **não 8 produtos**.
> Persona pack é uma _camada de personalização_ sobre o core — não um
> fork. Mesma instalação, mesma KB, mesma infra. Cada user instala a
> persona que faz sentido para o trabalho dele.
>
> **Alinhamento:** este doc detalha o que está esboçado em
> `docs/positioning.md` (persona terciária — não-técnicos do mesmo
> time) e `docs/products.md` (Tier 2C plugins).

---

## Como funciona um persona pack

### Estrutura técnica

Cada persona pack é um diretório no formato Skills do Vectora:

```
~/.vectora/personas/<persona-slug>/
├── manifest.json          # nome, descrição, versão, autor, tools necessárias
├── system_prompt.md       # injetado no orchestrator quando ativo
├── skills/                # skills específicas da persona
│   ├── <skill-1>.skill.md
│   ├── <skill-2>.skill.md
│   └── ...
├── slash_commands/        # /comandos custom expostos no chat
│   ├── <cmd-1>.md
│   └── ...
├── recipes/               # workflows multi-step exemplificados
│   ├── <recipe-1>.md
│   └── ...
└── kb/                    # KB embedada na instalação (opcional)
    ├── <topic>.md
    └── ...
```

### Lifecycle

```bash
# Listar disponíveis
vectora personas list

# Instalar
vectora personas install marketing-pack

# Ativar (uma por vez por sessão — pode trocar a qualquer momento)
vectora personas activate marketing-pack

# Desativar (volta ao Vectora "padrão")
vectora personas deactivate

# Desinstalar
vectora personas remove marketing-pack
```

### UI no chat web

Header do chat mostra persona ativa:

```
┌─────────────────────────────────────────────────────┐
│  Vectora · 🎯 Marketing Pack          [trocar ▼]    │
├─────────────────────────────────────────────────────┤
│  Workspace: marca-acme                              │
│  Modelo: gemini-3.5-flash                           │
└─────────────────────────────────────────────────────┘
```

Switch rápido entre personas via dropdown — sem fechar conversa, sem
perder contexto. Persona muda o **comportamento e o sistema** do
agente, não o histórico.

### Distribuição

- **First-party packs** (este doc) — mantidos pela Vectora Company,
  versionados junto do Vectora, no marketplace `vectora.company/personas`
- **Community packs** — qualquer um pode publicar; mesma estrutura
  Skills; sem certificação Vectora
- **Internal packs** (empresa) — empresa cria packs internos para
  cargos específicos do time, distribuídos via registry custom

---

## Persona Pack 1 — Marketing

### Para quem

- Profissionais de marketing em empresa tech (não-técnicos)
- Marketing manager, content creator, brand specialist, growth marketer
- Cargo típico: solo marketing em PME, ou time pequeno (2–5 pessoas)

### O que entrega

**Tools necessárias** (todas nativas ou plugins Tier 2C):

- `web_search` (research de concorrência)
- `web_fetch` + `web_crawl` (monitoramento de menções)
- `image_generate` (assets para campanhas — via `ia-plus.md`)
- `xlsx_generate` (relatórios para chefia)
- `pptx_generate` (decks de campanha)
- `chart_generate` (visualizações de métricas)
- `rag_search` sobre brand guidelines + histórico de campanhas
- Plugin: Google Analytics (Tier 2C)
- Plugin: PostHog ou Mixpanel
- Plugin: Slack (publicar atualizações de campanha)

**Skills inclusas:**

- `content-calendar` — gera calendário editorial mensal
- `post-draft` — rascunha posts para LinkedIn/X/Instagram com brand voice
- `email-draft` — emails de campanha (newsletter, lançamento, retenção)
- `landing-copy` — copy de landing page seguindo padrões de conversão
- `ab-test-analysis` — analisa resultados de A/B test e recomenda
- `seo-research` — keyword research + análise de SERP
- `competitor-monitor` — relatório semanal de movimento dos competidores

**Slash commands:**

- `/campaign new <nome>` — cria estrutura de campanha
- `/post <plataforma> <tema>` — rascunho rápido de post
- `/seo <keyword>` — análise SEO da keyword
- `/voice check <texto>` — verifica se texto está alinhado com brand voice

**Recipes (workflows multi-step):**

- "Lançamento de feature" — coordena posts, email, landing, analytics
- "Resposta a comentário negativo" — análise + draft + sugestão de tom
- "Relatório mensal" — coleta métricas + gera deck + envia para chefe

### Exemplos de interação

> _"Cria 5 posts para LinkedIn sobre o lançamento da feature X, seguindo
> nossa brand voice."_
>
> → Agente consulta RAG da brand guidelines, busca histórico de posts
> de feature passados, gera 5 variações com diferentes ângulos
> (técnico, benefício, social proof, problema/solução, behind-the-scenes),
> propõe horários de publicação baseado em analytics passados.

> _"Como nossas campanhas de Q1 performaram vs Q4?"_
>
> → Agente consulta plugin Analytics, gera comparativo, identifica
> 3 insights principais, propõe ações para Q2, salva como decision log.

### KPIs do persona pack

- Tempo de criação de post: de 45 min → 8 min
- Posts publicados/semana: 3 → 8
- Brand voice consistency score: avaliação semanal automática
- Insights acionáveis por relatório: ≥ 3

---

## Persona Pack 2 — Designer

### Para quem

- Product designer, UX designer, UI designer
- Design lead em PME
- Designer freelance com múltiplos clientes

### Tools necessárias

- `image_generate` + `image_edit` (mockups, ilustrações, ícones)
- `diagram_mermaid` (fluxos de user journey)
- Plugin Figma (RAG sobre comentários e componentes)
- `browser_screenshot` (referência de competidores)
- `docx_generate` (briefs e specs)

### Skills inclusas

- `mockup-rapido` — gera mockup baseado em descrição + brand
- `flow-user` — desenha fluxo de jornada do usuário
- `accessibility-check` — analisa screenshot/HTML e identifica problemas
  WCAG
- `design-system-audit` — verifica consistência de uso de tokens
- `competitor-screens` — coleta + organiza screens de competidores
- `iconography` — gera set de ícones consistentes
- `microcopy` — sugere copy para UI elements (CTAs, error states, empty
  states)

### Slash commands

- `/mockup <descrição>` — gera mockup direto
- `/icon <conceito>` — gera ícone SVG
- `/check accessibility <url|screenshot>` — audit de acessibilidade
- `/microcopy <contexto>` — sugestões de microcopy

### Recipes

- "Auditoria de design system" — sweep no Figma + relatório de
  inconsistências
- "Pesquisa de competidores" — coleta screens + organiza por feature +
  identifica padrões
- "Handoff para dev" — gera spec + exporta assets + sumariza decisões

### Exemplos

> _"Audita esta página em busca de problemas de acessibilidade WCAG AA."_
>
> → Agente captura screenshot + analisa HTML (se URL) ou OCR + análise
> visual, identifica: contraste insuficiente, alt text faltante,
> heading hierarchy quebrada, foco invisível em teclado, etc. Gera
> relatório priorizado.

---

## Persona Pack 3 — Product Manager (PM)

### Para quem

- Product Manager em PME tech
- Product Owner
- Founder no papel de PM (early-stage)

### Tools necessárias

- `rag_search` sobre roadmap, decisões, conversas com usuários, métricas
- Plugin Linear ou Jira (RAG + criar issues)
- Plugin Notion ou Confluence (escrever PRD)
- `chart_generate` (priorização visual: RICE, ICE)
- `pptx_generate` (decks para stakeholders)
- Plugin PostHog/Mixpanel (analytics)

### Skills inclusas

- `prd-draft` — gera PRD com contexto do produto via RAG
- `prioritization-rice` — score RICE de features
- `user-research-summary` — sumariza entrevistas/transcrições
- `competitive-analysis` — análise de feature parity vs concorrentes
- `release-notes` — gera release notes a partir de PRs mergeados
- `roadmap-update` — atualiza roadmap visual + comunica a stakeholders
- `decision-log` — registra decisões com contexto + alternativas

### Slash commands

- `/prd new <feature>` — inicia PRD com template
- `/prioritize <lista>` — score RICE de uma lista
- `/research summarize <link>` — sumariza transcrição/notas
- `/release notes` — gera release notes do último sprint
- `/decision <título>` — registra decisão no log

### Recipes

- "Discovery → Spec → Build" — fluxo completo de feature
- "Stakeholder update mensal" — coleta progresso + gera deck
- "Análise de churn" — pega data + identifica padrões + propõe ações

### Exemplos

> _"Cria um PRD para feature de bulk export CSV, considerando que já
> tivemos discussão similar em Q3 do ano passado."_
>
> → Agente busca no RAG decisões/discussões sobre bulk export, busca
> issues relacionadas no Linear, gera PRD com contexto histórico
> ("considerando a decisão de Q3/24 sobre não suportar Excel nativo,
> esta feature usa CSV…"), inclui edge cases lembrados.

---

## Persona Pack 4 — Liderança / C-Level

### Para quem

- CEO, CTO, CFO, COO em startup/PME
- Founders que ainda fazem múltiplos papéis
- Diretores em empresa média

### Tools necessárias

- Acesso a TODOS os workspaces da empresa (admin role)
- `rag_search` sobre tudo: finance, hr, product, customer
- `chart_generate` + `dashboard_generate` (KPIs visuais)
- `pptx_generate` (decks para board, investidores)
- `docx_generate` (memos estratégicos, propostas)
- Plugin Stripe/financials (Tier 2C)
- Plugin Linear/Jira (read sobre velocidade do time)
- Plugin Datadog/Sentry (health da operação)
- `xlsx_generate` (modelagem financeira)

### Skills inclusas

- `kpi-dashboard` — gera dashboard executivo dinâmico
- `board-deck` — deck mensal para board (template + dados)
- `investor-update` — email mensal para investidores
- `strategic-memo` — memo estratégico (mercado, decisão, recommendation)
- `hiring-scorecard` — scorecard de candidato com contexto da role
- `financial-model` — modelo financeiro 12 meses (xlsx)
- `meeting-summary` — sumariza reunião gravada (via ia-plus STT)
- `decision-record` — registra decisão estratégica com contexto

### Slash commands

- `/kpi dashboard` — abre dashboard ao vivo
- `/board deck <mês>` — gera deck mensal
- `/investor update` — rascunha email
- `/memo <título>` — inicia memo estratégico
- `/hire <candidato>` — gera scorecard

### Recipes

- "Fechamento de mês" — coleta dados + gera deck + agenda board
- "Decisão de pivô" — análise de cenários + memo + decision record
- "Onboarding de novo investidor" — gera data room + deck histórico

### Exemplos

> _"Como está nossa retenção comparada ao trimestre passado?"_
>
> → Agente consulta plugin Analytics + Stripe, gera gráfico comparativo,
> identifica que retenção D30 caiu 4 pp, busca no RAG eventos do
> trimestre que podem explicar (mudança de pricing, bug em onboarding),
> sugere 3 hipóteses a investigar.

---

## Persona Pack 5 — Sales / Business Development

### Para quem

- Account Executive, BDR, SDR
- Sales lead em PME
- Founder fazendo vendas (early-stage)

### Tools necessárias

- `rag_search` sobre case studies, proposals passadas, objection handling
- Plugin CRM (HubSpot ou Salesforce — Tier 2C)
- `web_fetch` + `web_search` (research de conta)
- `docx_generate` (propostas)
- `pptx_generate` (decks de vendas)
- Plugin LinkedIn (research de stakeholders — quando viável)

### Skills inclusas

- `account-research` — research completo de empresa (tamanho, stack,
  pain points, decision makers)
- `proposal-draft` — proposta customizada com case studies relevantes
- `email-cold` — cold email com personalização real
- `email-followup` — follow-up sequence
- `objection-handler` — busca no RAG como objeções similares foram
  resolvidas
- `meeting-prep` — briefing pré-call com contexto da conta
- `deal-summary` — sumariza estado do deal para CRM

### Slash commands

- `/account research <empresa>` — research em 2 min
- `/proposal <conta>` — gera proposta
- `/cold <conta>` — gera cold email
- `/objection <texto>` — como lidar com esta objeção
- `/meeting prep <reunião>` — briefing pré-call

### Recipes

- "Cold outbound campaign" — lista de contas + research + cold emails
- "Deal closing" — proposta + objections handling + termos
- "Quarterly business review" — prep de QBR com cliente

### Exemplos

> _"Vou ter call com CTO da Acme amanhã. Prepara briefing."_
>
> → Agente busca: empresa no CRM (histórico), site (stack, news), CTO
> no LinkedIn (background, posts recentes), casos de uso similares no
> RAG (clientes parecidos). Gera briefing de 1 página: pain points
> prováveis, ângulos de venda, casos relevantes, 5 perguntas para
> validar suposições.

---

## Persona Pack 6 — Ops / IT / DevOps

### Para quem

- Sysadmin, DevOps engineer, SRE
- IT manager em PME
- Engineering Manager preocupado com infra

### Tools necessárias

- `terminal` (já nativo)
- `docker_ps_logs`, `kubectl_read` (já planejado em native-tools Onda 5)
- `db_query`, `db_introspect` (Onda 2)
- Plugin Datadog, Sentry, Grafana (Tier 2C)
- `chart_generate` (dashboards de saúde)
- `docx_generate` (runbooks, post-mortems)

### Skills inclusas

- `runbook-generator` — gera runbook a partir de descrição do procedimento
- `incident-report` — template de incident report
- `post-mortem` — template + roteiro de blameless post-mortem
- `infra-audit` — checklist de health da infra
- `oncall-handoff` — sumário de status para próximo on-call
- `log-analyzer` — analisa logs em busca de padrões
- `alert-triage` — classifica alerta + sugere próximos passos

### Slash commands

- `/runbook <procedimento>` — gera runbook
- `/incident new <título>` — inicia incident report
- `/handoff` — sumário para próximo on-call
- `/triage <alerta>` — triagem rápida
- `/infra audit` — health check

### Recipes

- "Resposta a incidente" — incident report + war room + post-mortem
- "Onboarding de novo serviço" — checklist + runbook + monitoring +
  alertas
- "Audit trimestral" — varredura de segurança + custos + performance

### Exemplos

> _"Tem alerta de CPU em produção. Triagem rápida."_
>
> → Agente consulta Datadog (CPU history, alertas relacionados),
> consulta kubectl (pods afetados), busca no RAG runbooks similares,
> identifica que padrão é igual a incident #234 (memory leak em service
> X após deploy), sugere: rollback do deploy + criar issue para fix.

---

## Persona Pack 7 — Compliance / Legal

### Para quem

- Compliance officer, DPO (Data Protection Officer)
- Legal counsel em PME
- Founder lidando com primeiros compliance requirements

### Tools necessárias

- `rag_search` sobre regulamentações (LGPD, GDPR, SOC2 — embedados no pack)
- `pdf_generate` (políticas, termos)
- `docx_generate` (relatórios, evidências)
- Plugin AWS/GCP/Azure (coleta de evidence de infra)
- `xlsx_generate` (risk register, asset inventory)

### Skills inclusas

- `policy-draft` — gera política (privacidade, segurança, retenção,
  etc.) baseada em template + contexto da empresa
- `dpia-assessment` — Data Protection Impact Assessment
- `security-questionnaire` — responde questionário de cliente com base
  no RAG da empresa
- `evidence-collection` — coleta evidências de controles via plugins
  cloud
- `risk-register-update` — atualiza risk register
- `compliance-gap-analysis` — analisa gaps vs framework escolhido
- `breach-response-template` — template de resposta a incidente de dados

### Slash commands

- `/policy new <tipo>` — inicia política
- `/dpia <processamento>` — DPIA de processamento de dados
- `/sq <questionário>` — responde security questionnaire
- `/evidence <controle>` — coleta evidence
- `/risk add <risco>` — adiciona ao register

### Recipes

- "Onboarding SOC 2 Type 1" — gap analysis + plano de remediation
- "Resposta a auditoria" — coleta evidences + gera relatório
- "Incident response LGPD" — checklist + comunicação + relatório ANPD

### Exemplos

> _"Cliente XYZ mandou security questionnaire de 80 perguntas. Responde
> baseado no que já temos documentado."_
>
> → Agente lê o questionnaire, consulta RAG sobre políticas internas
>
> - evidences já coletadas, responde 65 perguntas com confiança ≥ 90%,
>   marca 15 perguntas como "requer revisão humana" (gaps ou ambiguidade),
>   gera diff de evidence gaps para coletar.

---

## Persona Pack 8 — Data Analyst

### Para quem

- Data analyst em empresa tech
- BI specialist em PME
- Founder/PM com necessidade de análise (em time sem analyst)

### Tools necessárias

- `db_query`, `db_introspect` (Onda 2 — native-tools)
- `code_python` (REPL persistente para análise — Onda 2)
- `chart_generate` + `dashboard_generate`
- `xlsx_read` + `xlsx_generate`
- `pdf_generate` (relatórios)
- Plugin warehouse (Snowflake, BigQuery, Redshift — quando disponível)
- Plugin PostHog/Mixpanel
- `pptx_generate` (decks de insights)

### Skills inclusas

- `sql-generate` — gera SQL a partir de pergunta + schema
- `chart-from-query` — query + viz inline
- `dashboard-build` — dashboard completo a partir de descrição
- `data-quality-audit` — audita tabela (nulls, duplicates, types)
- `cohort-analysis` — análise de coortes
- `retention-curve` — curva de retenção
- `funnel-analysis` — análise de funil
- `notebook-template` — scaffold de notebook Jupyter para análise

### Slash commands

- `/sql <pergunta>` — gera SQL para a pergunta
- `/chart <query>` — query + visualização
- `/dashboard <tema>` — dashboard a partir de descrição
- `/cohort <evento>` — análise de coorte
- `/notebook new <tema>` — scaffold de notebook

### Recipes

- "Análise ad-hoc → Insight" — fluxo completo de pergunta a deck
- "Dashboard semanal automático" — schedule + entrega para Slack
- "Audit de data quality" — varredura + relatório priorizado

### Exemplos

> _"Quero saber se feature X aumentou retenção D30 vs antes do
> lançamento."_
>
> → Agente identifica tabelas relevantes via introspect, gera SQL de
> coortes (pré vs pós-lançamento), executa, gera curva de retenção,
> faz teste estatístico de significância, gera dashboard com resultado,
> interpreta ("+2.4 pp em D30, significativo p<0.05"), salva análise
> como decision log.

---

## Persona Pack 9 — Onboarding (assistente de novo funcionário)

> Antes mencionado em `docs/products.md` candidato Tier 3 #5. Aqui
> formalizado como persona pack (decisão preferencial vs produto
> independente).

### Para quem

- Novo funcionário em qualquer cargo (PM, dev, marketing, design, ops)
- People Ops / HR configura o pack para cada nova contratação

### Tools necessárias

- `rag_search` sobre tudo da empresa indexado (admin libera escopo)
- Plugin calendar (gerencia agenda de onboarding)
- Plugin Slack (notifica buddies e managers)
- `pdf_read` (lê documentos de onboarding antigos)
- `chart_generate` (mostra progresso do plano)

### Skills inclusas

- `onboarding-plan-generate` — gera trilha personalizada (cargo, equipe,
  buddy, primeiras 30/60/90 dias)
- `kb-answer` — responde dúvidas com base no RAG da empresa
- `progress-monitor` — acompanha progresso, identifica bloqueios
- `mentor-request` — sugere mentor interno para tópico
- `tooling-setup-helper` — guia setup de ferramentas (com tools nativas
  - plugins)

### Slash commands

- `/onboarding plan` — meu plano atual
- `/ask <dúvida>` — pergunta a "alma" da empresa
- `/who knows <tópico>` — quem é referência interna no tópico

### Recipes

- "Primeiro dia" — checklist + tour + reuniões
- "Primeira semana" — projetos pequenos + 1:1s + leitura essencial
- "30/60/90" — checkpoints estruturados

---

## Persona Pack 10 — Engineering Lead (refinamento da persona primária)

> Vectora **base** já serve engenheiro sênior. Este pack ADICIONA
> contexto/skills específicos para **tech leads e EMs** — gestão de
> time, mentorship, escolha de tech, etc.

### Tools necessárias

- Tudo que dev sênior usa +
- Plugin Linear/Jira (visão de sprint, velocity)
- Plugin GitHub (PR review patterns, code health)
- `chart_generate` (métricas de saúde do time)

### Skills inclusas

- `1on1-prep` — prep de 1:1 com membro do time
- `tech-decision` — framework para decisão técnica (ADR + RFC)
- `code-review-coaching` — feedback construtivo em PR review
- `team-health-check` — pulse do time
- `hiring-loop-design` — desenha loop de entrevistas para role
- `arch-decision-record` — gera ADR formal
- `rfc-draft` — gera RFC para mudança grande

### Slash commands

- `/1on1 <pessoa>` — prep de 1:1
- `/adr <título>` — inicia ADR
- `/rfc <título>` — inicia RFC
- `/team health` — pulse atual

### Exemplos

> _"Vou ter 1:1 com a Ana amanhã. Prep."_
>
> → Agente busca: PRs mergeados/abertos da Ana (último mês),
> conversas dela em threads do time (Slack/Discord), 1:1 anterior
> notes, sprint atual + bloqueios. Gera briefing: o que ela está
> trabalhando, possíveis preocupações (PRs abertos há > 5 dias),
> reconhecimentos a fazer (PR X recebeu elogio), perguntas para validar
> assumptions sobre satisfação/crescimento.

---

## Distribuição

### Marketplace público

URL: `vectora.company/personas`

- Cada pack tem página própria com screenshots, exemplos, reviews,
  changelog
- Trial 14 dias por pack
- Reviews comunidade após install
- Versionamento + auto-update opt-in

### Pricing dos persona packs

| Pack                  | Preço        | Tipo                                     |
| --------------------- | ------------ | ---------------------------------------- |
| Marketing             | $10/mês/user | DLC                                      |
| Designer              | $10/mês/user | DLC                                      |
| PM                    | $10/mês/user | DLC                                      |
| Leadership            | $15/mês/user | DLC (premium)                            |
| Sales                 | $10/mês/user | DLC                                      |
| Ops / IT              | Incluso Pro  | Bundle                                   |
| Compliance            | $20/mês/user | DLC (specialized)                        |
| Data Analyst          | $15/mês/user | DLC (premium)                            |
| Onboarding            | $5/mês/user  | DLC (light)                              |
| Engineering Lead      | Incluso Team | Bundle                                   |
| **Productivity Pack** | $25/mês/user | Marketing + PM + Sales bundle (40% desc) |
| **Enterprise Pack**   | $50/mês/user | Todos os packs                           |

### Bundles institucionais

Empresa que assina Team com 10+ seats pode ter um pack incluído
gratuitamente por seat. Ex: empresa de design libera Designer pack para
todo o time sem custo extra.

### Internal packs (custom)

Empresa pode criar persona pack próprio para cargos específicos:

```bash
# Criar pack interno
vectora personas create --name acme-customer-success

# Editar manifest, skills, slash commands localmente

# Publicar no registry interno da empresa
vectora personas publish --registry https://personas.acme.com/registry
```

---

## Cronograma de implementação

```
Pré-lançamento
  Sprint P-1: framework de persona pack
    - Schema de manifest
    - Loader + activator
    - CLI: install/activate/deactivate/remove
    - UI: switch de persona no header

Pós-lançamento Q1
  Sprint P-2: 4 packs iniciais
    - Marketing
    - Designer
    - PM
    - Engineering Lead

Pós-lançamento Q2
  Sprint P-3: mais 3 packs
    - Leadership
    - Sales
    - Data Analyst

Pós-lançamento Q3
  Sprint P-4: 3 packs especializados
    - Ops/IT
    - Compliance
    - Onboarding

Pós-lançamento Q4
  - Marketplace público com community packs
  - Internal packs para empresas Team+
  - Bundles institucionais
```

---

## Como persona packs se relacionam com outros docs

| Doc                      | Relação                                                        |
| ------------------------ | -------------------------------------------------------------- |
| `docs/positioning.md`    | Define que Vectora atende não-técnicos via persona packs       |
| `docs/products.md`       | Tier 2C — alguns packs viram plugins quando vendor-específicos |
| `docs/native-tools.md`   | Define tools que cada persona pack pode usar nativamente       |
| `docs/mcp-library.md`    | Persona packs podem requerer MCPs específicos (auto-install)   |
| `docs/ia-plus.md`        | Persona packs usam image_generate, TTS, STT, transcribe        |
| `docs/chat-first.md`     | Render hints novos podem ser criados para outputs de persona   |
| `docs/beta-program.md`   | Cada novo pack passa por beta antes do lançamento público      |
| `docs/skills-library.md` | Skills marketplace é base técnica para persona packs           |

---

## Princípios cardinais

1. **Um Vectora, múltiplas personalidades.** Não é forking; é
   personalização sobre o core.

2. **Switching é trivial.** Trocar de persona não perde contexto da
   conversa — só muda comportamento do agente.

3. **Personas reusam KB.** Marketing pack vê os mesmos dados que dev
   pack — diferentes lentes sobre os mesmos workspaces.

4. **Quality > quantidade.** Melhor 8 packs excelentes que 30 medianos.

5. **Community + first-party.** Vectora mantém qualidade nos
   first-party; comunidade publica complementos.

6. **Tier gates honestos.** Algumas personas (Ops, Eng Lead) inclusas
   em planos Pro/Team. Outras são DLC. Sempre claro o que é o quê.

7. **Persona = produto interno simples; não substitui produto externo
   (Tier 3).** Vectora Helpdesk continua sendo produto independente —
   persona "Customer Support" interna serve o suporte INTERNO da
   empresa, não o cliente final.

8. **Internal packs preservam diferenciação Vectora.** Empresa cria
   packs próprios sem precisar pedir nossa permissão — mesmo modelo de
   internal MCP registry.
