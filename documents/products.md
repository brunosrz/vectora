# Vectora Company — Product Portfolio Plan

> Plano de longo prazo do portfólio da Vectora Company. Cobre todos os
> ativos planejados: produto principal, extensões, plugins/DLCs e
> produtos independentes. Foco: PMEs de tecnologia — B2B, produtividade
> real, sem IA por IA.
>
> **Princípio cardinal:** somos uma empresa de produtividade. IA é o motor,
> não o produto. O produto é o resultado — trabalho feito mais rápido,
> com mais contexto, com menos atrito.
>
> Este documento substitui o antigo `longo-prazo.md`. A reformulação
> elimina o Tier 3 anterior (Briefd / Flowlog / Forma) por sobreposição
> entre Briefd↔Flowlog e desconexão temática do Forma com o stack
> central do Vectora. O novo Tier 3 traz 7 candidatos avaliados por
> TAM, concorrência, sinergia técnica e diferencial real do self-hosted.

---

## Visão de Portfólio

```
Vectora Company
│
├── TIER 1 — Produto Principal
│   └── Vectora (self-hosted AI agent + chat web + RAG + MCP)
│
├── TIER 2 — Extensões do Vectora
│   ├── Vectora VSIX        (integração nativa VS Code)
│   ├── Vectora Host/Client (separação servidor/máquina local)
│   └── Vectora Plugins     (DLCs: conectores, agentes especializados,
│                            ex-Tier 3 absorvidos)
│
└── TIER 3 — Produtos Independentes
    ├── Núcleo (recomendados para lançar)
    │   ├── Vectora Helpdesk   (suporte interno/externo com RAG)
    │   └── Vectora Code Review (revisão de PR com contexto do projeto)
    │
    └── Candidatos (avaliados, lançamento condicional)
        ├── Vectora Inbox       (email + Slack com RAG)
        ├── Vectora Compliance  (LGPD/GDPR/SOC2 assistido)
        ├── Vectora Onboarding  (trilha personalizada de funcionário)
        ├── Vectora Spec        (PRDs/specs com contexto)
        └── Vectora Pages       (KB inteligente — adiar / não recomendado)
```

---

## TIER 1 — Vectora: Produto Principal

### Posicionamento

> **"AI self-hosted comercial para PMEs de tecnologia — sua infra, seus dados, sua IA."**

Não é coding assistant. Não é chatbot. É um agente de produtividade com
memória real do seu trabalho — retreinável via AGENTS.md, Skills e RAG,
com suporte a multi-usuários, workspaces, sandbox, worktrees, REST API e
controle total dos dados.

**Para devs:** coding assistant com contexto real do codebase, code review,
git workflows, terminal integrado.

**Para o time de produto:** documentação viva, RAG sobre specs e decisões
passadas, geração de PRDs com contexto do projeto.

**Para operações/gestão:** automação de relatórios, análise de dados internos,
respostas contextuais sobre processos da empresa.

**REST API (plan Bloco J):** o Vectora vira o motor RAG de qualquer
aplicação interna da empresa — sem precisar construir pipeline de embedding
do zero.

### Planos atuais

| Plano | Descrição                                                        | Preço           |
| ----- | ---------------------------------------------------------------- | --------------- |
| Plus  | CLI + MCP + Desktop, SQLite + LanceDB, single-thread             | $7 · R$20/mês   |
| Pro   | Chat web multi-usuário, PostgreSQL + Qdrant + Redis, REST API v1 | $20 · R$55/mês  |
| Team  | Pro + Host/Client + VSIX + SSO                                   | $49 · R$130/mês |

O plano **Team** é introduzido quando Host/Client e VSIX estiverem
prontos. Empresas com 5+ usuários pagam por seat (desconto por volume
acima de 10 seats).

OEM e Enterprise: ver `docs/oem.md`.

---

## TIER 2A — Vectora VSIX: Extensão VS Code

### O que é

Extensão oficial do Vectora para VS Code. Conecta o editor diretamente ao
Vectora Agent rodando localmente ou no servidor da empresa, sem precisar
alternar para o chat web ou o terminal.

### Por que faz sentido

O dev já está no VS Code. Sair do editor para um chat web quebra o fluxo.
O VSIX elimina esse atrito — o Vectora vira um painel lateral do editor,
como o GitHub Copilot, mas com contexto real do projeto via RAG local.

Diferença do Copilot: o Vectora sabe sobre o **seu** projeto específico,
não sobre código genérico da internet. Código proprietário, documentação
interna, decisões de arquitetura — tudo indexado e acessível.

### Funcionalidades

**Chat inline:**

- Painel lateral com chat completo do Vectora Agent
- Contexto automático do arquivo aberto + seleção de código
- `/rag add` direto do painel — indexa o workspace atual

**Code actions (menu de contexto):**

- Clique direito no código → "Explicar com Vectora"
- Clique direito → "Refatorar com Vectora"
- Clique direito → "Gerar testes para este arquivo"
- Clique direito → "Revisar este diff"

**Inline suggestions (futuramente):**

- Sugestões baseadas no RAG local (não autocomplete genérico)
- Ativadas apenas quando o Vectora tem contexto suficiente do projeto

**Conexão:**

- Via ACP Protocol (plan Bloco I4/J7) ou diretamente `VECTORA_API_URL`
  - `VECTORA_TOKEN`
- Suporta conexão local (localhost) e remota (VPS/servidor da empresa)
- Autenticação via VECTORA_TOKEN ou sessão OAuth do Host

### Modelo de distribuição

- Publicado no VS Code Marketplace (gratuito para instalar)
- Requer licença Plus ou superior para funcionar
- Plano Team inclui VSIX desbloqueado para todos os usuários do servidor

### Tecnologia

- TypeScript + VS Code Extension API
- `FileSystemProvider` para expor workspaces remotos como pseudo-locais
- Comunicação com o Agent via REST/SSE (mesma API do chat web)
- Painel lateral: WebView com React (reutiliza componentes do chat)

---

## TIER 2B — Vectora Host / Client

### O problema que resolve

Hoje o Vectora é host + client no mesmo processo: você instala, sobe o
servidor, acessa via URL. Funciona bem para uso individual ou para equipes
onde todos acessam o servidor central via chat web.

O problema: um dev que trabalha remotamente com arquivos locais (seu PC
pessoal ou notebook da empresa) não tem como dar ao Vectora acesso a esses
arquivos sem sincronizar tudo para o servidor — o que compromete a
privacidade e a praticidade.

### A solução: separação Host / Client

**Vectora Host** — roda no servidor da empresa (ou VPS dedicada):

- Banco vetorial, PostgreSQL, usuários, workspaces compartilhados
- Interface web de administração (painel root)
- Gerencia autenticação e emissão de convites para Clients
- Expõe API REST interna autenticada para os Clients
- É a instalação atual do Vectora em modo `--mode host`

**Vectora Client** — roda na máquina local de cada usuário:

- Conecta ao Host via OAuth interno (token de sessão por usuário, não as
  envs do banco)
- Acesso total ao filesystem local (workspace local)
- Sincroniza contexto com o Host: memórias, workspaces compartilhados,
  histórico
- Funciona offline para operações locais; sincroniza quando reconecta
- É um binário leve — não precisa de PostgreSQL/Qdrant locais

**Resultado:** o dev tem o Vectora no notebook com acesso a arquivos
locais **e** conectado à base de conhecimento centralizada da empresa.

### Fluxo de onboarding Host → Client

```
Admin no Host:
  Configurações → Usuários → "Convidar Client"
  → Gera código temporário (estilo Pix copia-e-cola, 10 min de validade)
  → Ou QR Code para app mobile

Usuário no Client:
  vectora client connect
  → "Cole o código de convite ou escaneie o QR:"
  → [código]
  → Conectado ao servidor da empresa como <email> (role: member)
```

**Segurança:**

- Client nunca recebe credenciais do PostgreSQL, Qdrant ou Redis
- Host emite JWT de sessão específico para o Client
- Revogação instantânea: admin remove → JWT invalidado
- Dados locais do Client não sobem sem consentimento explícito

### Modos de operação

```
vectora --mode standalone   # comportamento atual (host + client no mesmo processo)
vectora --mode host         # apenas servidor — sem TUI local
vectora client connect      # apenas client — conecta a um host remoto
vectora client sync         # sincroniza workspaces e memórias com o host
```

### Casos de uso

**Empresa com 10 devs:** 1 VPS com Vectora Host (PostgreSQL + Qdrant);
cada dev instala Vectora Client no notebook; workspaces compartilhados
ficam no Host; código pessoal/local fica no Client; admin gerencia
usuários pelo painel web.

**Dev solo com máquina poderosa em casa:** Vectora Host na máquina de
casa (ou VPS barata); Vectora Client no notebook do trabalho; todos os
workspaces sincronizados — trabalha de qualquer lugar.

**App mobile (futuramente):** QR Code gerado pelo Host; app escaneia →
conecta como Client mobile; acesso read-only ao chat e workspaces via
smartphone.

---

## TIER 2C — Vectora Plugins (DLC Marketplace)

### Conceito

Plugins são extensões compráveis separadamente que adicionam capacidades
ao Vectora. Não são parte do core — são DLCs opcionais que expandem o
produto para casos de uso específicos.

Distribuídos via `vectora.company/plugins` (marketplace próprio) e
instaláveis via `vectora plugin install <nome>`.

### Plugins planejados — conectores

**Vectora for Jira / Linear** (Plugin)

- Tools: `issue_list`, `issue_create`, `sprint_summary`, `cycle_status`
- RAG automático sobre descrições e comentários de issues
- Webhook de mudanças → re-indexação automática
- Caso de uso: _"o que está bloqueado no sprint atual?"_ / _"crie uma
  issue para o bug que acabei de descrever"_

**Vectora for Notion** (Plugin)

- RAG sobre páginas e databases do Notion via OAuth
- Indexação automática via webhook
- Caso de uso: documentação interna como base de conhecimento do agente

**Vectora for Figma** (Plugin)

- RAG sobre comentários e descrições de componentes do Figma
- Ferramenta de contexto para devs: _"o que o design especifica para este
  componente?"_

**Vectora for Google Workspace** (Plugin)

- RAG sobre Google Docs, Sheets e Drive compartilhados
- Caso de uso: _"resuma as decisões da última reunião"_ (RAG sobre Google
  Doc da ata)

**Vectora for Slack** (Plugin)

- Conector bidirecional: ler histórico de canais como contexto +
  responder direto no Slack
- Útil para integração leve com times já no Slack

### Plugins planejados — agentes especializados

**Vectora Analytics Agent** (Plugin Pro)

- Conecta a bancos da empresa (MySQL, PostgreSQL, BigQuery)
- Tools: `sql_query`, `chart_generate`, `data_summary`
- Caso de uso: _"quantos usuários ativos tivemos essa semana?"_ sem SQL

**Vectora Security Agent** (Plugin Pro)

- Analisa PRs em busca de vulnerabilidades
- RAG sobre CVEs relevantes para o stack da empresa
- Caso de uso: revisão de segurança automatizada antes do merge

**Vectora Onboarding Agent** (Plugin) — _ver Tier 3 candidato 5_

- Gera trilha de onboarding personalizada por cargo
- Responde dúvidas com RAG sobre KB da empresa
- Disponível como plugin (recomendado) ou produto independente, conforme
  decisão final do Tier 3.

**Vectora Spec Agent** (Plugin) — _ver Tier 3 candidato 6_

- Apoia PMs na escrita de PRDs/specs com contexto de produto via RAG
- Mesma observação: pode ser plugin ou produto independente.

### Modelo de precificação dos plugins

- Conectores simples (Notion, Linear, Figma, Slack):
  **$5–10/mês por workspace**
- Conectores premium (Google Workspace, Jira full):
  **$10–15/mês por workspace**
- Agentes especializados (Analytics, Security):
  **$15–25/mês por workspace**
- Bundles: "Productivity Pack" (Notion + Jira + Google Workspace) com
  desconto

### Marketplace

`vectora.company/plugins`:

- Página por plugin: descrição, screenshots, reviews, preço
- Trial de 14 dias por plugin
- Instalação: `vectora plugin install vectora-jira` → autentica via
  VECTORA_TOKEN
- Plugins de terceiros podem entrar (revenue share 70/30) após programa de
  developer relations estabelecido (ano 2+)

---

## TIER 3 — Produtos Independentes

> Estes produtos são desenvolvidos e lançados **depois** do Vectora estar
> estabelecido no mercado (base de clientes, receita estável, pelo menos
> 1 funcionário contratado). Não são extensões do Vectora — são produtos
> separados que resolvem problemas reais de PMEs de tecnologia e que se
> beneficiam de uma base de usuários que já confia na Vectora Company.
>
> **Critério de inclusão:** o produto deve (1) resolver um problema real
> e recorrente de PMEs de tech, (2) ter ângulo defensável contra
> concorrência (idealmente self-hosted decisivo), (3) ter sinergia técnica
> com o Vectora (RAG/agente/LLM como motor essencial), (4) ARPU ≥ $30/mês
> ou ticket alto compatível com 1 fundador.

### Avaliação consolidada — 7 candidatos

| #   | Produto                 | TAM       | Concorrência      | Self-hosted decisivo? | Sinergia Vectora | ARPU esperado   | Status           |
| --- | ----------------------- | --------- | ----------------- | --------------------- | ---------------- | --------------- | ---------------- |
| 1   | **Vectora Helpdesk**    | Enorme    | Brutal            | **SIM**               | Total (RAG)      | $50–200/mês     | **Núcleo**       |
| 2   | **Vectora Code Review** | Grande    | Brutal            | **SIM**               | Total (RAG)      | $30–80/dev/mês  | **Núcleo**       |
| 3   | **Vectora Inbox**       | Enorme    | Pesada            | Forte                 | Alta (RAG email) | $20–50/user/mês | Candidato        |
| 4   | **Vectora Compliance**  | Crescendo | Média             | **Ultra forte**       | Alta             | $200–500/mês    | Candidato        |
| 5   | **Vectora Onboarding**  | Médio     | Média             | Médio                 | Alta             | $15–40/user/mês | Candidato/Plugin |
| 6   | **Vectora Spec/PRD**    | Pequeno   | Fragmentado       | Médio                 | Alta             | $20–60/user/mês | Candidato/Plugin |
| 7   | **Vectora Pages (KB)**  | Enorme    | Notion/Confluence | Forte                 | Total            | $10–30/user/mês | Adiar            |

**Eliminados** (não constam acima):

- **Vectora Standup**: ARPU baixo (Geekbot cobra $3/user), RAG não é
  central, mercado saturado.
- **Vectora Meet**: **colide com Perssua** — quebra a diferenciação clara
  já estabelecida. Não lançar.
- **Vectora Workflows**: self-hosted é commodity nesse mercado (n8n
  self-hosted é gratuito). Sem ângulo defensável.

---

### Núcleo recomendado — lançar primeiro

#### 1. Vectora Helpdesk

**Tagline:** _"Suporte que conhece a sua empresa — rodando na sua infra."_

**O problema:**
Setores regulados (saúde, banco, jurídico, governo) **não podem** mandar
conversas de cliente para OpenAI/Anthropic. Hoje resolvem com humanos
caros ou Salesforce Einstein (caríssimo e cloud). E PMEs sem
infraestrutura de IA acabam usando Intercom Fin / Zendesk AI sem opção
de auditoria.

**O que é:**
Chatbot de suporte (interno para colaboradores ou externo para clientes)
com RAG sobre a KB da empresa. Cliente clica "Falar com IA"; a IA responde
com base em docs/tickets/playbooks da empresa indexados; escala para
humano quando o score do RAG fica baixo ou o cliente pede explicitamente.

**Como funciona:**

- Widget JavaScript embedável (`<script src="vectora-helpdesk.js">`)
- Conecta ao Vectora Helpdesk backend (self-hosted ou Cloud)
- KB pode vir de qualquer fonte: Notion, Confluence, Markdown, PDFs,
  histórico de tickets resolvidos
- Citações verificáveis em toda resposta (`[1] [2]` linkando ao chunk)
- Handoff para humano via Slack/Discord/email quando necessário
- Analytics: tickets resolvidos, tópicos recorrentes, gaps de KB

**Diferenciais:**

- **Self-hosted** — rodando dentro do firewall da empresa
- **Multi-LLM** — escolhe o LLM conforme custo/qualidade
- **Transparência total** — toda resposta vem com fontes citadas
- **Reusa Vectora Pro** — clientes Pro já têm o RAG; Helpdesk adiciona o
  widget + analytics + handoff

**Concorrência:**

- Intercom Fin: $0.99/conversa, cloud-only
- Zendesk AI: caro, cloud-only
- Glean for Support: enterprise, cloud-only
- Mendable, Chatbase, Botpress: cloud-only ou self-hosted sem RAG decente

**Modelo de negócio:**

- SaaS: $50/mês até 500 conversas/mês + $0.10/conversa adicional
- Self-hosted: $299/mês flat (conversas ilimitadas)
- Trial: 30 dias
- Enterprise: contrato customizado com SLA

**Sinergia com Vectora:** 90%. Backend reusa pipeline RAG, multi-LLM,
storage backends (PostgreSQL/Qdrant) e REST API. Equipe entrega o
**widget JS** + dashboard de analytics + lógica de handoff. ~3 meses para
MVP a partir do Vectora Pro estável.

**Risco principal:** brigar com Intercom Fin / Salesforce Einstein. O
diferencial só prende cliente se a venda for clara para o **buyer
regulado** (segmentação rigorosa).

---

#### 2. Vectora Code Review

**Tagline:** _"Code review que conhece os padrões da sua empresa."_

**O problema:**
Code review automatizado virou commodity (GitHub Copilot review, Codacy,
CodeRabbit, Greptile). Mas todos esses são cloud-only e usam **regras
genéricas** — não conhecem os padrões internos do projeto. E times com
código sensível (defesa, fintech, BigTech BR) não podem mandar diff
algum para a cloud.

**O que é:**
Bot que comenta PRs no GitHub/GitLab com revisão contextualizada — não
lint genérico, mas review baseado em **padrões internos do projeto** via
RAG sobre o codebase + histórico de PRs.

**Como funciona:**

- Instala como GitHub App / GitLab integration
- Indexa o repo via Vectora (RAG sobre código + commits + PRs anteriores)
- A cada PR novo, analisa o diff contra:
  - Padrões internos (extraídos automaticamente do código + AGENTS.md)
  - Decisões de arquitetura passadas (RAG sobre PRs/decisões mergeadas)
  - Convenções específicas (naming, structure, idioms)
- Comenta inline no PR via API do GitHub/GitLab
- HITL: dev pode "👍/👎" cada comentário para refinar o modelo

**Diferenciais:**

- **Self-hosted** — código nunca sai da infra
- **Conhece o projeto** — não regras genéricas
- **Multi-LLM** — escolhe modelo por contexto/custo
- **Reusa Vectora Pro** — RAG sobre código já existe

**Concorrência:**

- CodeRabbit: $24/dev/mês, cloud-only
- Greptile: cloud-only
- GitHub Copilot review: $19/mo (incluso Copilot), cloud-only
- Sourcery, Codacy: lint genérico, cloud-only

**Modelo de negócio:**

- SaaS: $30/dev/mês (mínimo 3 devs)
- Self-hosted: $499/mês flat (repos e devs ilimitados)
- Trial: 30 dias
- Enterprise: SLA + suporte dedicado

**Sinergia com Vectora:** 95%. Reusa praticamente tudo — RAG sobre código,
git tools (`git_diff`, `git_log`), `gh` integration, MCP. Equipe entrega
o **GitHub App** + lógica de comentário inline + UI de configuração de
padrões. ~2 meses para MVP a partir do Vectora Pro estável.

**Risco principal:** GitHub Copilot review está crescendo rapidamente.
Janela de oportunidade pode estar fechando. Mitigação: foco no segmento
regulado/self-hosted onde Copilot não chega.

---

### Candidatos avaliados — lançamento condicional

#### 3. Vectora Inbox

**Tagline:** _"Inbox que conhece a sua empresa, não só o teor genérico do email."_

**O que é:**
Cliente leve de email/Slack que prioriza, filtra e rascunha respostas
usando RAG sobre histórico de comunicação + KB da empresa.

**Por que self-hosted importa:** emails contêm dados de cliente, deals,
IP sensível. Superhuman ($30/mo) manda tudo para a cloud deles.

**Sinergia Vectora:** alta — RAG decide prioridade + LLM rascunha resposta
no tom da empresa.

**Concorrência:** Superhuman, Spike, Front, Missive — todos consolidados,
todos cloud.

**Modelo:** $30/user/mês SaaS, $149/mês self-hosted ≤ 10 users.

**Risco principal:** UX de email é **muito** pesada de construir (IMAP/
SMTP/calendário/anexos/spam/threading). Não é "skin sobre o Vectora" — é
produto inteiro. Lançamento condicional a (1) Vectora Helpdesk e Code
Review estarem rentáveis, (2) ter time de pelo menos 2 devs.

---

#### 4. Vectora Compliance

**Tagline:** _"Compliance que roda na sua infra, não na nuvem do fornecedor."_

**O que é:**
Agente especializado em compliance (LGPD, GDPR, SOC 2, ISO 27001, HIPAA).
Gera políticas, mapeia dados sensíveis, responde questionários de cliente
("Security Questionnaire"), mantém evidence collection contínuo.

**Por que self-hosted importa:** dados de compliance são meta-sensíveis.
É irônico mandar mapa de dados sensíveis para uma cloud terceira.
Vanta/Drata mandam — e isso fecha portas em mercados regulados.

**Sinergia Vectora:** alta — RAG sobre regulamentações + agente
especializado treinado em compliance + integrações com AWS/GCP/Azure
para coleta automática de evidence.

**Concorrência:**

- Vanta: $8k–25k/ano, cloud
- Drata: similar
- Secureframe: similar
- Strike Graph, Sprinto: mid-market

**Modelo:** $200/mês early-stage, $500/mês growth, contratos enterprise
$2k–10k/mês.

**Diferencial brasileiro:** nenhum dos players globais domina LGPD bem
(é regulação local, com sutilezas — ANPD, RIPD, etc.). Vectora pode
liderar nesse vertical.

**Risco principal:** ciclo de venda longo (3–6 meses), exige conhecimento
legal real, vendas consultivas. **Difícil para fundador solo.** Lançamento
condicional a contratação de pelo menos 1 pessoa com background jurídico/
compliance.

---

#### 5. Vectora Onboarding

**Tagline:** _"Onboarding que sabe tudo que sua empresa sabe."_

**O que é:**
Assistente especializado em onboarding de novo funcionário. Gera trilha
personalizada por cargo, responde dúvidas com RAG sobre tudo da empresa,
monitora progresso, identifica gaps de documentação.

**Concorrência:** Lessonly ($420/mês+), Trainual ($300/mês+), WorkRamp.
Mercado existente, nenhum gigante dominante.

**Modelo:** $15–40/user/mês SaaS, $99/mês self-hosted.

**Decisão recomendada:** **lançar primeiro como plugin do Tier 2C**
(`Vectora Onboarding Agent`). Validar tração antes de promover para
produto independente. Diferencial técnico claro além de "self-hosted +
RAG da empresa" é fraco — sem ângulo distintivo, fica indistinguível de
add-on do Vectora Pro.

---

#### 6. Vectora Spec/PRD

**Tagline:** _"PM tool que sabe por que vocês escolheram as coisas."_

**O que é:**
Ferramenta para PMs criarem specs/PRDs com IA que conhece o contexto do
produto via RAG (roadmap, decisões anteriores, código, conversas com
usuários, métricas).

**Concorrência:** Productboard, Linear, Notion + ChatGPT já cobrem.

**Modelo:** $20–60/user/mês SaaS, $99/mês self-hosted.

**Decisão recomendada:** **lançar como plugin do Tier 2C**
(`Vectora Spec Agent`) e/ou integração nativa com Linear/Notion. TAM
muito pequeno (só PMs) para sustentar produto independente.

---

### Adiar — não recomendado lançar como Tier 3

#### 7. Vectora Pages (KB inteligente)

**O que seria:**
Substituto de Notion/Confluence com KB pesquisável por IA built-in,
importando multi-source.

**Por que adiar:**

- Notion vale $10B; Confluence é dinheiro vivo da Atlassian. Brigar nesse
  espaço requer 10+ devs e venda enterprise.
- Outline e BookStack já fazem self-hosted **gratuito** com comunidade
  ativa. Vectora Pages teria que ser nitidamente superior para justificar
  preço.
- Atlassian Intelligence está adicionando IA nativa ao Confluence — janela
  fechando.
- Dispersa foco do core do Vectora.

**Alternativa:** transformar em **plugin do Vectora** que conecta a Notion/
Confluence/Outline existentes (RAG sobre KB já presente). Sem reinventar
a wheel da edição/colaboração.

---

### Recomendação de sequenciamento

```
Ano 1 — Vectora core estabelecido
  Foco total no Tier 1. Validar tração, gerar receita, contratar.

Ano 2, Q1–Q2 — Tier 2A/2B (extensões do Vectora)
  Lançar VSIX (Q1), Host/Client (Q2). Plano Team disponível.

Ano 2, Q3–Q4 — Tier 2C (plugins) + 1º produto Tier 3
  Lançar marketplace de plugins (Notion, Jira, Linear, Google Workspace).
  Lançar **Vectora Helpdesk** como primeiro produto Tier 3.
  Motivo: alta sinergia (90% reuso de código), ARPU alto ($50–299/mês),
  segmento regulado é venda enterprise mais lenta — começar cedo.

Ano 3, Q1–Q2 — 2º produto Tier 3
  Lançar **Vectora Code Review**.
  Motivo: maior sinergia técnica (95% reuso), ARPU médio mas escala por
  dev. Aproveita base de Pro/Team já estabelecida.

Ano 3, Q3–Q4 — Avaliar candidatos
  Com receita do Helpdesk + Code Review estabilizada, avaliar:
   - Inbox (se time ≥ 2 devs e tração no Helpdesk justificar)
   - Compliance (se contratar pessoa com background jurídico)
   - Onboarding/Spec (lançar como plugins Tier 2C, não produtos)

Ano 4+ — Bundle "Vectora Suite"
  Vectora + Helpdesk + Code Review + plugins selecionados em pacote
  desconto.
```

### Plugins absorvidos do antigo Tier 3

Os produtos descartados do Tier 3 anterior (Briefd, Flowlog, Forma)
podem ser revisitados como plugins do Vectora ao longo do tempo, se
houver demanda dos usuários:

- **Auto-docs estilo Briefd**: já é parcialmente coberto pelo Vectora
  Pro (RAG sobre docs gerados pelo agente). Plugin opcional adicionaria
  geração automática + sync com Notion/Confluence.
- **Decision log estilo Flowlog**: pode ser feature do Vectora
  (`/decision register …` slash command) ou plugin que persiste em base
  estruturada.
- **Forma**: descartado. Mercado de formulários é commodity (Typeform,
  Tally, Fillout) sem ângulo defensável para o Vectora.

---

## Cronograma de longo prazo

```
ANO 1 — Estabelecer o Vectora
  Q1: Lançamento Vectora Tier 1 (campanha influencers BR)
  Q2: PWA / mobile + polish UX (ux.md sprints UX-1 a UX-7)
  Q3: REST API v1 + SDKs Python/TS + Webhooks (plan Bloco J + L)
  Q4: IA+ (TTS + STT + image gen — ia-plus.md sprints M1–M4)

ANO 2 — Expandir o ecossistema (Tier 2 + 1º Tier 3)
  Q1: Vectora VSIX (Tier 2A)
  Q2: Vectora Host/Client (Tier 2B) + plano Team
  Q3: Marketplace de plugins (Tier 2C) — Notion + Jira + Google + Linear
  Q4: Vectora Helpdesk (Tier 3 núcleo #1) — beta fechado

ANO 3 — Portfólio completo (Tier 3 núcleo)
  Q1: Vectora Helpdesk — lançamento público
  Q2: Vectora Code Review (Tier 3 núcleo #2) — beta fechado
  Q3: Vectora Code Review — lançamento público
  Q4: Avaliação dos candidatos Tier 3 (Inbox / Compliance / Onboarding)

ANO 4+ — Dependente de tração e equipe
  - Lançamento condicional de candidatos Tier 3
  - App mobile Vectora Client
  - Vectora Enterprise (on-premise air-gapped, SLA, suporte dedicado)
  - Expansão internacional com equipe de sales B2B
  - Bundle "Vectora Suite"
```

---

## Modelo de receita consolidado

### Vectora (Tier 1 + 2)

| Produto                                    | Preço SaaS / mês      | Tipo       |
| ------------------------------------------ | --------------------- | ---------- |
| Vectora Plus                               | $7 · R$20             | Assinatura |
| Vectora Pro                                | $20 · R$55            | Assinatura |
| Vectora Team                               | $49 · R$130           | Assinatura |
| Vectora Enterprise                         | Customizado           | Contrato   |
| VSIX                                       | Incluso no Team       | Bundle     |
| Host/Client                                | Incluso no Team       | Bundle     |
| Plugin Notion                              | $5/workspace          | DLC        |
| Plugin Jira                                | $10/workspace         | DLC        |
| Plugin Linear                              | $5/workspace          | DLC        |
| Plugin Figma                               | $5/workspace          | DLC        |
| Plugin Google Workspace                    | $10/workspace         | DLC        |
| Plugin Slack                               | $5/workspace          | DLC        |
| Plugin Analytics Agent                     | $25/workspace         | DLC Pro    |
| Plugin Security Agent                      | $25/workspace         | DLC Pro    |
| Plugin Onboarding Agent                    | $15/workspace         | DLC        |
| Plugin Spec Agent                          | $15/workspace         | DLC        |
| Productivity Pack (Notion + Jira + Google) | $18/ws (desconto 28%) | Bundle     |

### Produtos independentes (Tier 3 núcleo)

| Produto             | SaaS                               | Self-hosted | Trial   |
| ------------------- | ---------------------------------- | ----------- | ------- |
| Vectora Helpdesk    | $50/mês até 500 conv. + $0.10/conv | $299/mês    | 30 dias |
| Vectora Code Review | $30/dev/mês (mín 3 devs)           | $499/mês    | 30 dias |

### Receita projetada conservadora — fim do Ano 1

```
100 assinantes Vectora Plus  ($7)        = $700/mês
 50 assinantes Vectora Pro   ($20)       = $1.000/mês
 20 assinantes Vectora Team  ($49)       = $980/mês
 30 workspaces com plugins   ($10 avg)   = $300/mês
                                           ──────────
Total mensal estimado Ano 1:             = ~$3.000/mês (~R$15.000/mês)
```

Suficiente para contratar 1 funcionário part-time ou freelancer recorrente
e reinvestir no Tier 2.

### Receita projetada otimista — fim do Ano 3

```
300 Plus   ($7)          = $2.100/mês
200 Pro    ($20)         = $4.000/mês
 80 Team   ($49)         = $3.920/mês
 50 Helpdesk ($150 avg)  = $7.500/mês
 30 Code Review ($120 avg) = $3.600/mês
150 plugins ($12 avg)    = $1.800/mês
                           ──────────
Total mensal Ano 3:      = ~$22.920/mês (~R$115.000/mês)
```

Permite time enxuto de 3–4 pessoas + investimento em vendas B2B.

---

## Princípios de produto para o portfólio

1. **Self-hosted é diferencial, não limitação.** Cada produto oferece
   versão self-hosted. PMEs de tech valorizam controle de dados — isso
   vira vantagem competitiva contra SaaS pure-cloud.

2. **Integração, não dependência.** Cada produto Tier 3 funciona sem o
   Vectora. A integração é um multiplicador de valor — não um lock-in.

3. **Sinergia técnica obrigatória.** Cada produto Tier 3 deve reusar pelo
   menos 70% do stack do Vectora (RAG, multi-LLM, storage, MCP, REST).
   Produtos sem essa sinergia (ex: Vectora Meet, Vectora Workflows) foram
   descartados.

4. **IA como motor silencioso.** Nenhum produto se anuncia como "IA".
   O resultado anunciado é produtividade — suporte que resolve, code
   review que conhece o projeto, compliance que organiza sozinho.

5. **Cada produto resolve uma dor específica e recorrente.** Sem
   "features by features". Sem "também pode fazer X". Cada produto tem
   uma razão de existir que cabe em uma frase.

6. **Lançamento sequencial, não paralelo.** Um produto por vez, bem feito,
   com base de usuários estabelecida antes do próximo. Receita do Vectora
   financia Tier 2. Receita do Tier 2 + Tier 3 núcleo financia candidatos.

7. **Self-hosted e preço honesto atraem empresas sérias.** Empresas que
   escolhem instalar software no próprio servidor pensam a longo prazo
   sobre fornecedores — menor churn, pagam mais cedo, recomendam mais.

8. **Self-hosted decisivo, não decorativo.** Cada produto Tier 3 só entra
   no portfólio se o self-hosted resolver uma dor real (compliance,
   regulação setorial, política interna de dados). "Self-hosted bonitinho"
   sem caso de uso forte é descartado — vide Vectora Workflows.

9. **Concorrência saudável é OK.** Helpdesk briga com Intercom Fin; Code
   Review briga com CodeRabbit. Ângulo defensável (self-hosted + RAG sobre
   contexto interno) é suficiente quando o segmento tem dor real de
   privacidade/personalização.

10. **Janela de oportunidade existe — e fecha.** Code Review tem GitHub
    Copilot review crescendo rápido; Compliance tem Vanta/Drata
    consolidando. Decisões de lançamento devem considerar quando a janela
    fecha (mitigado por segmento regulado + self-hosted onde os
    concorrentes não chegam).
