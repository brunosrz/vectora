# Vectora Company — Long-Term Asset Plan

> Plano de longo prazo da Vectora Company. Cobre todos os ativos planejados:
> produto principal, extensões, plugins/DLCs e produtos independentes.
> Foco: PMEs de tecnologia — B2B, produtividade real, sem IA por IA.
>
> **Princípio cardinal:** somos uma empresa de produtividade. IA é o motor,
> não o produto. O produto é o resultado — trabalho feito mais rápido,
> com mais contexto, com menos atrito.

---

## Visão de Portfólio

```
Vectora Company
│
├── TIER 1 — Produto Principal
│   └── Vectora (self-hosted AI agent + chat)
│
├── TIER 2 — Extensões do Vectora
│   ├── Vectora VSIX        (integração nativa VS Code)
│   ├── Vectora Host/Client (separação servidor/máquina local)
│   └── Vectora Plugins     (DLCs: conectores, agentes especializados)
│
└── TIER 3 — Produtos Independentes
    ├── Briefd              (documentação viva de projetos)
    ├── Flowlog             (registro de decisões e contexto de time)
    └── Forma               (formulários e coleta de dados internos)
```

---

## TIER 1 — Vectora: Produto Principal

### Posicionamento revisado

> **"O ChatGPT self-hosted da sua empresa."**

Não é um coding assistant. Não é um chatbot. É um agente de produtividade
com memória real do seu trabalho — retreinável via AGENTS.md, Skills e RAG,
com suporte a multi-usuários, workspaces, sandbox, worktrees, API REST e
controle total dos dados.

**Para devs:** coding assistant com contexto real do codebase, code review,
git workflows, terminal integrado.

**Para o time de produto:** documentação viva, RAG sobre specs e decisões
passadas, geração de PRDs com contexto do projeto.

**Para operações/gestão:** automação de relatórios, análise de dados internos,
respostas contextuais sobre processos da empresa.

**API REST (Bloco Z do chat-first):** o Vectora vira o motor RAG de qualquer
aplicação interna da empresa — sem precisar construir pipeline de embedding
do zero.

### Planos revisados com Host/Client

| Plano | Descrição                                           | Preço           |
| ----- | --------------------------------------------------- | --------------- |
| Plus  | CLI + MCP, SQLite + LanceDB, single-thread          | $7 · R$20/mês   |
| Pro   | Chat web multi-usuário, PostgreSQL + Qdrant + Redis | $20 · R$55/mês  |
| Team  | Pro + Host/Client + VSIX + SSO                      | $49 · R$130/mês |

O plano Team é introduzido quando Host/Client e VSIX estiverem prontos.
Empresas com 5+ usuários pagam por seat (desconto por volume acima de 10 seats).

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

- Sugestões inline baseadas no RAG local (não autocomplete genérico)
- Ativadas apenas quando o Vectora tiver contexto suficiente do projeto

**Conexão:**

- Conecta via ACP Protocol (Bloco Z do chat-first) ou diretamente via
  `VECTORA_API_URL` + `VECTORA_TOKEN`
- Suporta conexão local (localhost) e remota (VPS/servidor da empresa)
- Autenticação via VECTORA_TOKEN ou sessão OAuth do Host (quando Host/Client
  estiver ativo)

### Modelo de distribuição

- Publicado no VS Code Marketplace (gratuito para instalar)
- Requer licença Plus ou superior para funcionar
- Plano Team inclui VSIX desbloqueado para todos os usuários do servidor

### Tecnologia

- TypeScript + VS Code Extension API
- Comunicação com o Agent via REST/SSE (mesma API do Chat web)
- Painel lateral: WebView com React (pode reusar componentes do chat)

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

- Armazena o banco de dados vetorial, PostgreSQL, usuários, workspaces compartilhados
- Interface web de administração (painel root)
- Gerencia autenticação e emissão de convites para Clients
- Expõe API REST interna autenticada para os Clients se conectarem
- É a instalação atual do Vectora em modo `--mode host`

**Vectora Client** — roda na máquina local de cada usuário:

- Conecta ao Host via OAuth interno (token de sessão por usuário, não as envs do banco)
- Tem acesso total ao filesystem local (workspace local)
- Sincroniza contexto com o Host: memórias, workspaces compartilhados, histórico
- Funciona offline para operações locais; sincroniza quando reconecta
- É um binário leve — não precisa de PostgreSQL/Qdrant locais

**Resultado:** o dev tem o Vectora no notebook com acesso a arquivos locais
**e** conectado à base de conhecimento centralizada da empresa. Melhor dos
dois mundos.

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

- O Client nunca recebe as credenciais do PostgreSQL, Qdrant ou Redis
- O Host emite um JWT de sessão específico para o Client
- Revogação instantânea: admin remove o Client no painel → JWT invalidado
- Dados locais do Client não sobem para o Host sem consentimento explícito
  (workspace local ≠ workspace compartilhado)

### Modos de operação

```
vectora --mode standalone   # comportamento atual (host + client no mesmo processo)
vectora --mode host         # apenas servidor — sem TUI local
vectora client connect      # apenas client — conecta a um host remoto
vectora client sync         # sincroniza workspaces e memórias com o host
```

### Casos de uso

**Empresa com 10 devs:**

- 1 VPS com Vectora Host (PostgreSQL + Qdrant)
- Cada dev instala Vectora Client no notebook
- Workspaces compartilhados da empresa ficam no Host
- Código pessoal/local de cada dev fica no Client
- Admin gerencia usuários e permissões pelo painel web do Host

**Dev solo com máquina poderosa em casa:**

- Vectora Host na máquina de casa (ou VPS barata)
- Vectora Client no notebook do trabalho
- Todos os workspaces sincronizados — trabalha de qualquer lugar

**App mobile (futuramente):**

- QR Code gerado pelo Host
- App escaneia → conecta como Client mobile
- Acesso read-only ao chat e workspaces via smartphone

---

## TIER 2C — Vectora Plugins (DLC Marketplace)

### Conceito

Plugins são extensões compráveis separadamente que adicionam capacidades
ao Vectora. Não são parte do core — são DLCs opcionais que expandem o
produto para casos de uso específicos.

Distribuídos via `vectora.company/plugins` (marketplace próprio) e
instaláveis via `vectora plugin install <nome>`.

### Plugins planejados

**Vectora for Jira** (Plugin)

- Agente especializado em issues do Jira
- Tools: `jira_issue_list`, `jira_issue_create`, `jira_sprint_summary`
- RAG automático sobre descrições e comentários de issues
- Caso de uso: "o que está bloqueado no sprint atual?" / "crie uma issue
  para o bug que acabei de descrever"

**Vectora for Notion** (Plugin)

- RAG sobre páginas e databases do Notion via OAuth
- Indexação automática quando páginas são atualizadas (webhook Notion)
- Caso de uso: documentação interna como base de conhecimento do Vectora

**Vectora for Linear** (Plugin)

- Mesmo conceito do Jira, para times que usam Linear
- Tools: `linear_issue_create`, `linear_cycle_summary`, `linear_project_status`

**Vectora for Figma** (Plugin)

- RAG sobre comentários e descrições de componentes do Figma
- Ferramenta de contexto para devs: "o que o design especifica para este
  componente?"
- Não gera imagens — consome contexto de design

**Vectora for Google Workspace** (Plugin)

- RAG sobre Google Docs, Sheets e Drive da empresa
- Indexação de documentos compartilhados como base de conhecimento
- Caso de uso: "resuma as decisões da última reunião" (RAG sobre Google Doc
  da ata)

**Vectora Analytics Agent** (Plugin Pro)

- Agente especializado em análise de dados
- Conecta a bancos de dados da empresa (MySQL, PostgreSQL, BigQuery)
- Tools: `sql_query`, `chart_generate`, `data_summary`
- Caso de uso: "quantos usuários ativos tivemos essa semana?" sem precisar
  escrever SQL

**Vectora Security Agent** (Plugin Pro)

- Agente especializado em segurança de código
- Analisa PRs em busca de vulnerabilidades
- RAG sobre CVEs relevantes para o stack da empresa
- Caso de uso: revisão de segurança automatizada antes do merge

### Modelo de precificação dos plugins

- Plugins de conectores simples (Notion, Linear, Figma): $5–10/mês por workspace
- Plugins de agentes especializados (Analytics, Security): $15–25/mês por workspace
- Bundles: "Productivity Pack" (Notion + Jira + Google Workspace) com desconto

### Marketplace

`vectora.company/plugins`:

- Página por plugin: descrição, screenshots, reviews, preço
- Trial de 14 dias por plugin
- Instalação: `vectora plugin install vectora-jira` → autentica via VECTORA_TOKEN

---

## TIER 3 — Produtos Independentes

> Estes produtos são desenvolvidos e lançados **depois** do Vectora estar
> estabelecido no mercado (base de clientes, receita estável, pelo menos
> 1 funcionário contratado). Não são extensões do Vectora — são produtos
> separados que resolvem problemas reais de PMEs de tecnologia e que se
> beneficiam de uma base de usuários que já confia na Vectora Company.
>
> **Critério de inclusão:** o produto deve (1) resolver um problema real
> e recorrente de PMEs de tech, (2) não concorrer com gigantes estabelecidos
> frontalmente, (3) ter sinergia natural com o Vectora (pode se integrar,
> mas não depende).

---

### Produto Independente 1 — Briefd

**Tagline:** _"A documentação que se escreve sozinha."_

**O problema:**
PMEs de tecnologia têm um problema crônico com documentação: ou não existe,
ou está desatualizada, ou está espalhada em 5 ferramentas diferentes (Notion,
Confluence, Google Docs, comentários no código, mensagens no Slack). Quando
alguém novo entra na empresa — ou quando o dev que construiu um sistema sai —
o conhecimento some junto.

Ferramentas como Notion e Confluence resolvem o **armazenamento** mas não
o **custo de manutenção**: alguém precisa escrever e atualizar tudo
manualmente. Isso nunca acontece de forma consistente.

**O que é o Briefd:**
Um sistema de documentação viva que captura contexto automaticamente das
ferramentas que o time já usa — e gera, mantém e atualiza documentação
sem precisar que alguém sente e escreva.

**Como funciona:**

- Conecta às ferramentas da empresa (GitHub, Jira, Linear, Slack, Notion,
  Google Workspace)
- Detecta quando algo importante acontece: PR mergeado, decisão tomada em
  reunião, arquitetura modificada, novo componente criado
- Usa IA para extrair o contexto relevante e gerar/atualizar o documento
  correspondente automaticamente
- Documentos ficam num repositório central acessível via busca semântica
- Time pode revisar, editar e aprovar antes de publicar (ou configurar
  para publicar automaticamente)

**Funcionalidades core:**

- **Auto-docs de código:** conecta ao GitHub, analisa PRs e commits,
  gera/atualiza documentação técnica automaticamente
- **Decision log:** captura decisões de issues e PRs ("decidimos usar
  PostgreSQL porque...") e as organiza em um registro consultável
- **Onboarding docs:** quando alguém novo entra, o Briefd gera um guia
  de onboarding baseado no que a empresa já tem documentado
- **Changelog automático:** gera changelogs legíveis a partir de commits
  e PRs sem precisar escrever manualmente
- **Busca semântica:** "como funciona o sistema de autenticação?" retorna
  os documentos relevantes, não uma lista de arquivos

**Integração com Vectora:**

- O Briefd exporta toda a documentação como base RAG para o Vectora
- Dentro do Vectora: "qual é a arquitetura do nosso sistema de pagamentos?"
  → busca no Briefd via RAG
- Não é dependência: o Briefd funciona sem o Vectora, e vice-versa

**Modelo de negócio:**

- SaaS: $15/usuário/mês (mínimo 3 usuários)
- Self-hosted (para empresas que não querem dados na nuvem): $99/mês flat
- Trial: 30 dias

**Público:** CTO + devs seniores que sentem a dor da documentação ausente;
PMs que precisam de contexto técnico sem interromper devs.

---

### Produto Independente 2 — Flowlog

**Tagline:** _"Por que aquilo foi construído daquele jeito?"_

**O problema:**
Todo time de tecnologia tem uma versão da mesma conversa: "por que isso foi
feito assim?" A resposta está perdida em algum comentário do Slack de 2 anos
atrás, ou na cabeça de alguém que saiu da empresa, ou simplesmente não existe.

Decisões técnicas, de produto e de design são tomadas todos os dias — e
raramente documentadas com o contexto necessário (o "por quê", não o "o quê").
O resultado: times passam horas em reuniões desfazendo decisões que foram
tomadas por uma boa razão que ninguém mais lembra.

**O que é o Flowlog:**
Um registro de decisões estruturado e consultável. Não é um wiki, não é
um gerenciador de tarefas — é especificamente um lugar para capturar
**decisões** com contexto: o que foi decidido, por quê, quais alternativas
foram consideradas, e quem estava envolvido.

Inspirado no conceito de ADR (Architecture Decision Records) mas generalizado
para qualquer tipo de decisão de time — técnica, de produto, de processo.

**Como funciona:**

- Interface simples para registrar uma decisão em 3 campos:
  - O que foi decidido (1–2 frases)
  - Por que (contexto, alternativas rejeitadas)
  - Impacto (o que muda, o que é afetado)
- Categorias: Técnica, Produto, Design, Processo, Negócio
- Vinculação a projetos, sistemas e pessoas
- Busca semântica: "por que escolhemos TypeScript?" retorna as decisões relevantes
- Timeline: visão cronológica das decisões por projeto
- Revisão periódica: lembrete automático para revisar decisões antigas
  ("essa decisão de 2 anos atrás ainda faz sentido?")

**Integração com Vectora:**

- Decisões do Flowlog viram base RAG do Vectora
- "Por que usamos Redis para cache?" → Vectora consulta o Flowlog via RAG
- Plugin Flowlog para o Vectora (Tier 2C) permite criar decisões via chat:
  "registre que decidimos usar Kafka para o sistema de eventos porque..."

**Diferença do Briefd:**
Briefd captura e mantém documentação técnica de forma automática.
Flowlog é intencional — alguém decide registrar uma decisão.
São complementares: Briefd descreve **o que** o sistema faz;
Flowlog explica **por que** foi construído assim.

**Modelo de negócio:**

- SaaS: $8/usuário/mês (mínimo 3 usuários)
- Self-hosted: $49/mês flat
- Trial: 30 dias
- Plano free: até 3 usuários, 50 decisões (para times pequenos e adoção viral)

**Público:** CTOs, tech leads, PMs seniores — qualquer pessoa que já perdeu
tempo tentando entender por que uma decisão foi tomada.

---

### Produto Independente 3 — Forma

**Tagline:** _"Formulários que entendem o que você precisa saber."_

**O problema:**
PMEs de tecnologia coletam dados o tempo todo: feedback de usuários,
pesquisas internas, onboarding de clientes, aprovações de processos,
checklists de deploy. As ferramentas existentes (Google Forms, Typeform,
Jotform) são genéricas e resolvem o problema de coleta — mas não o problema
de **processamento e contexto**.

O resultado de um formulário é uma planilha. Alguém precisa ler, interpretar
e agir sobre aqueles dados. Em times pequenos, isso raramente acontece de
forma sistemática.

**O que é o Forma:**
Um criador de formulários para uso interno em PMEs de tech, com três
diferenciais:

1. **Processamento automático:** as respostas não viram só uma planilha.
   O Forma categoriza, agrupa e resume automaticamente — "10 pessoas
   responderam. Os principais temas foram X, Y e Z."

2. **Formulários contextuais:** ao invés de campos estáticos, o Forma
   pode fazer perguntas de acompanhamento baseadas nas respostas anteriores
   (como uma entrevista estruturada, não um questionário fixo)

3. **Ações automáticas:** quando um formulário é respondido, o Forma pode
   criar uma issue no Jira, enviar uma notificação no Slack, atualizar um
   registro — sem precisar de Zapier

**Casos de uso para PMEs de tech:**

- **Retrospectiva de sprint:** formulário enviado ao time, respostas
  analisadas automaticamente, temas agrupados, ação criada no Linear
- **Onboarding de novo funcionário:** checklist de onboarding com
  acompanhamento contextual ("você disse que não entendeu X — aqui está
  mais contexto")
- **Aprovação de deploy:** formulário de checklist técnico antes de
  ir para produção, com validações e registro de quem aprovou
- **NPS interno:** pesquisa de satisfação da equipe com análise automática
  de sentimento e temas recorrentes
- **Coleta de requisitos:** PMs coletam requisitos de stakeholders via
  formulário contextual — o Forma faz as perguntas de acompanhamento
  necessárias

**Integração com Vectora:**

- Dados coletados pelo Forma podem ser indexados como base RAG do Vectora
- "Quais foram os principais feedbacks do time no último trimestre?" →
  Vectora consulta histórico do Forma via RAG
- Plugin Forma para Vectora: criar formulários por linguagem natural
  ("crie um formulário de retrospectiva para o time de backend")

**Modelo de negócio:**

- SaaS: $12/mês flat para times de até 20 pessoas
- Acima de 20: $1/usuário/mês
- Self-hosted: $49/mês flat
- Trial: 30 dias
- Plano free: até 3 formulários ativos, 100 respostas/mês

**Público:** PMs, tech leads, RH de empresas de tech, qualquer pessoa
que hoje usa Google Forms mas quer mais do que uma planilha no final.

---

## Cronograma de longo prazo

```
ANO 1 — Estabelecer o Vectora
  Q1: Lançamento do Vectora (Tier 1) — campanha influenciadores
  Q2: Vectora VSIX (Tier 2A) — extensão VS Code
  Q3: Primeiros plugins (Tier 2C) — Notion + GitHub
  Q4: Vectora Host/Client (Tier 2B) — plano Team

ANO 2 — Expandir o ecossistema
  Q1: Marketplace de plugins — lançamento público
  Q2: Plugins Analytics Agent + Security Agent
  Q3: Lançamento do Briefd (Tier 3)
  Q4: Integração Briefd ↔ Vectora

ANO 3 — Portfólio completo
  Q1: Lançamento do Flowlog (Tier 3)
  Q2: Integração Flowlog ↔ Vectora + Briefd
  Q3: Lançamento do Forma (Tier 3)
  Q4: Bundle "Vectora Suite" — Vectora + Briefd + Flowlog + Forma

ALÉM DO ANO 3 — Dependente de tração e equipe
  - App mobile Vectora Client
  - Vectora Enterprise (on-premise, SLA, suporte dedicado)
  - Expansão internacional com equipe de sales B2B
```

---

## Modelo de receita consolidado

### Vectora (Tier 1 + 2)

| Produto          | Preço             | Tipo       |
| ---------------- | ----------------- | ---------- |
| Vectora Plus     | $7 · R$20/mês     | Assinatura |
| Vectora Pro      | $20 · R$55/mês    | Assinatura |
| Vectora Team     | $49 · R$130/mês   | Assinatura |
| VSIX             | Incluso no Team   | Bundle     |
| Host/Client      | Incluso no Team   | Bundle     |
| Plugin Notion    | $5/mês/workspace  | DLC        |
| Plugin Jira      | $5/mês/workspace  | DLC        |
| Plugin Analytics | $25/mês/workspace | DLC        |

### Produtos independentes (Tier 3)

| Produto | Preço SaaS          | Preço Self-hosted | Trial   |
| ------- | ------------------- | ----------------- | ------- |
| Briefd  | $15/user/mês        | $99/mês flat      | 30 dias |
| Flowlog | $8/user/mês         | $49/mês flat      | 30 dias |
| Forma   | $12/mês (≤20 users) | $49/mês flat      | 30 dias |

### Receita projetada conservadora (Ano 1, fim de ano)

```
100 assinantes Vectora Plus ($7)     = $700/mês
 50 assinantes Vectora Pro ($20)     = $1.000/mês
 20 assinantes Vectora Team ($49)    = $980/mês
 30 workspaces com plugins ($10 avg) = $300/mês
                                       ──────────
Total mensal estimado Ano 1:         = ~$3.000/mês (~R$15.000/mês)
```

Suficiente para contratar 1 funcionário part-time ou freelancer recorrente
e reinvestir no desenvolvimento dos produtos de Tier 3.

---

## Princípios de produto para o portfólio

1. **Self-hosted é diferencial, não limitação.** Cada produto oferece
   versão self-hosted. PMEs de tech valorizam controle de dados — isso
   vira vantagem competitiva contra SaaS pure-cloud.

2. **Integração, não dependência.** Briefd, Flowlog e Forma funcionam
   sem o Vectora. A integração é um multiplicador de valor, não um lock-in.

3. **IA como motor silencioso.** Nenhum produto se anuncia como "IA".
   O resultado anunciado é produtividade — documentação que se atualiza,
   decisões que não se perdem, formulários que processam os próprios dados.

4. **Cada produto resolve uma dor específica e recorrente.** Sem features
   por features. Sem "e também pode fazer X". Cada produto tem uma razão
   de existir que cabe em uma frase.

5. **Lançamento sequencial, não paralelo.** Um produto por vez, bem feito,
   com base de usuários estabelecida antes do próximo. Receita do Vectora
   financia o desenvolvimento do Briefd. Receita do Briefd financia o Flowlog.

6. **Self-hosted e preço honesto atraem empresas sérias.** Empresas que
   escolhem instalar software no próprio servidor são empresas que pensam
   a longo prazo sobre fornecedores. Essas empresas têm menor churn,
   pagam mais cedo e recomendam mais.
