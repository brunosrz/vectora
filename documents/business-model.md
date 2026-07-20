# Vectora Company — Modelo de Negócio

> Documento consolidado de estratégia de negócio: portfólio de produtos,
> licenciamento OEM, parcerias estratégicas e operação da company (legal,
> billing, site, distribuição, marketing) — antes quatro documentos
> separados (produtos, OEM, parcerias, operação da company), unificados
> aqui como fonte de verdade única.
>
> **Princípio cardinal:** somos uma empresa de produtividade. IA é o
> motor, não o produto. O produto é o resultado — trabalho feito mais
> rápido, com mais contexto, com menos atrito.

---

## Portfólio de produtos

### Visão geral

```
Vectora Company
│
├── TIER 1 — Produto Principal
│   └── Vectora (self-hosted AI agent + chat web + RAG + MCP)
│
├── TIER 2 — Extensões do Vectora
│   ├── Vectora VSIX        (integração nativa VS Code)
│   ├── Vectora Host/Client (separação servidor/máquina local)
│   └── Vectora Plugins     (DLCs: conectores, agentes especializados)
│
└── TIER 3 — Produtos Independentes
    ├── Núcleo (recomendados para lançar primeiro)
    │   ├── Vectora Helpdesk    (suporte interno/externo com RAG)
    │   └── Vectora Code Review (revisão de PR com contexto do projeto)
    │
    └── Candidatos (avaliados, lançamento condicional)
        ├── Vectora Inbox       (email + Slack com RAG)
        ├── Vectora Compliance  (LGPD/GDPR/SOC2 assistido)
        ├── Vectora Onboarding  (trilha personalizada de funcionário)
        ├── Vectora Spec        (PRDs/specs com contexto)
        └── Vectora Pages       (KB inteligente — adiar / não recomendado)
```

Foco declarado: PMEs de tecnologia — B2B, produtividade real, sem IA por
IA. Cada produto do portfólio precisa (1) resolver um problema real e
recorrente dessas empresas, (2) ter ângulo defensável contra a
concorrência (idealmente self-hosted decisivo), (3) ter sinergia técnica
com o Vectora (RAG/agente/LLM como motor essencial), (4) ARPU compatível
com operação enxuta (fundador solo ou time pequeno).

### TIER 1 — Vectora: produto principal

**Posicionamento:** _"AI self-hosted comercial para PMEs de tecnologia —
sua infra, seus dados, sua IA."_

Não é coding assistant nem chatbot genérico. É um agente de produtividade
com memória real do trabalho do usuário — retreinável via AGENTS.md,
Skills e RAG, com suporte a multi-usuários, workspaces, sandbox,
worktrees e controle total dos dados.

- **Para devs:** coding assistant com contexto real do codebase, code
  review, git workflows, terminal integrado.
- **Para o time de produto:** documentação viva, RAG sobre specs e
  decisões passadas, geração de PRDs com contexto do projeto.
- **Para operações/gestão:** automação de relatórios, análise de dados
  internos, respostas contextuais sobre processos da empresa.

Uma futura REST API pública faria do Vectora o motor RAG de qualquer
aplicação interna da empresa, sem precisar construir um pipeline de
embedding do zero — ver "Licenciamento OEM" abaixo para o modelo de
monetização dessa via de uso.

**Planos atuais:**

| Plano | Descrição                                                                      | Preço         |
| ----- | ------------------------------------------------------------------------------ | ------------- |
| Free  | 100% local, sem conta, SQLite + LanceDB                                        | Grátis        |
| Pro   | Trial/billing/licenciamento via `services.vectora.company`, features avançadas | ver dashboard |

O desenho de planos pagos (Plus/Pro/Team com tiers de preço fixos,
Host/Client, VSIX incluso) é a direção de médio prazo descrita nas seções
de Tier 2 abaixo; o mecanismo de billing que sustenta qualquer plano pago
já está em produção (ver "Operação da company").

### TIER 2A — Vectora VSIX (extensão VS Code)

Extensão oficial que conecta o editor diretamente ao Vectora Agent local
ou remoto, sem alternar para o chat web ou o terminal. Diferencial frente
ao GitHub Copilot: o Vectora conhece o **projeto específico** do usuário
via RAG local — código proprietário, documentação interna, decisões de
arquitetura — não código genérico da internet.

Funcionalidades planejadas: chat inline com contexto automático do
arquivo aberto, `/rag add` direto do painel, code actions de menu de
contexto (explicar/refatorar/gerar testes/revisar diff), e futuramente
inline suggestions baseadas em RAG local.

Distribuição: VS Code Marketplace (instalação gratuita), mas requer
licença paga para funcionar. Tecnicamente: TypeScript + VS Code Extension
API, `FileSystemProvider` para workspaces remotos, comunicação via
REST/SSE com o mesmo backend do chat web.

### TIER 2B — Vectora Host / Client

Problema a resolver: hoje o Vectora roda host + client no mesmo
processo. Um dev que trabalha remotamente com arquivos locais não tem
como dar ao Vectora acesso a esses arquivos sem sincronizar tudo para o
servidor — o que compromete privacidade e praticidade.

Solução proposta: separar **Vectora Host** (servidor da empresa/VPS —
banco vetorial, PostgreSQL, usuários, workspaces compartilhados, painel
de administração) de **Vectora Client** (máquina local de cada usuário —
acesso total ao filesystem local, sincroniza contexto com o Host,
funciona offline). O Client nunca recebe credenciais de banco — apenas
um token de sessão emitido pelo Host, revogável instantaneamente.

Modos de operação planejados: `--mode standalone` (atual), `--mode host`,
`client connect`, `client sync`.

### TIER 2C — Vectora Plugins (marketplace de DLCs)

Extensões compráveis separadamente, distribuídas via
`vectora.company/plugins` e instaláveis via `vectora plugin install
<nome>`. Não fazem parte do core.

**Conectores planejados:** Jira/Linear, Notion, Figma, Google Workspace,
Slack — cada um com RAG automático sobre o conteúdo da fonte e,
idealmente, reindexação via webhook.

**Agentes especializados planejados:** Analytics Agent (SQL sobre bancos
da empresa), Security Agent (revisão de PRs contra CVEs), Onboarding
Agent e Spec Agent (ambos também avaliados como produtos Tier 3
independentes — ver abaixo).

Precificação de referência: conectores simples $5–10/workspace/mês,
conectores premium $10–15/workspace/mês, agentes especializados
$15–25/workspace/mês, com bundles combinados. Plugins de terceiros
entrariam com revenue share 70/30 depois de um programa de developer
relations estabelecido.

### TIER 3 — Produtos independentes

Desenvolvidos e lançados **depois** do Vectora estar estabelecido no
mercado (base de clientes, receita estável, pelo menos um funcionário
contratado). Não são extensões — são produtos separados que se
beneficiam de uma base de usuários que já confia na Vectora Company.

**Avaliação consolidada:**

| #   | Produto             | TAM       | Concorrência      | Self-hosted decisivo? | Sinergia Vectora | ARPU esperado   | Status           |
| --- | ------------------- | --------- | ----------------- | --------------------- | ---------------- | --------------- | ---------------- |
| 1   | Vectora Helpdesk    | Enorme    | Brutal            | Sim                   | Total (RAG)      | $50–200/mês     | Núcleo           |
| 2   | Vectora Code Review | Grande    | Brutal            | Sim                   | Total (RAG)      | $30–80/dev/mês  | Núcleo           |
| 3   | Vectora Inbox       | Enorme    | Pesada            | Forte                 | Alta (RAG email) | $20–50/user/mês | Candidato        |
| 4   | Vectora Compliance  | Crescendo | Média             | Ultra forte           | Alta             | $200–500/mês    | Candidato        |
| 5   | Vectora Onboarding  | Médio     | Média             | Médio                 | Alta             | $15–40/user/mês | Candidato/Plugin |
| 6   | Vectora Spec/PRD    | Pequeno   | Fragmentado       | Médio                 | Alta             | $20–60/user/mês | Candidato/Plugin |
| 7   | Vectora Pages (KB)  | Enorme    | Notion/Confluence | Forte                 | Total            | $10–30/user/mês | Adiar            |

Eliminados da avaliação: Vectora Standup (ARPU baixo, mercado saturado),
Vectora Meet (colidiria com o produto Perssua, quebrando diferenciação),
Vectora Workflows (self-hosted é commodity nesse mercado — n8n
self-hosted já é gratuito, sem ângulo defensável).

**Núcleo — lançar primeiro:**

_Vectora Helpdesk_ — _"Suporte que conhece a sua empresa — rodando na sua
infra."_ Chatbot de suporte com RAG sobre a KB da empresa, citações
verificáveis, handoff para humano. Ataca o mesmo espaço de Intercom Fin/
Zendesk AI, mas para setores regulados que não podem mandar conversas de
cliente para clouds de terceiros. Reusa ~90% do stack Vectora Pro
(pipeline RAG, multi-LLM, storage, REST API); a equipe entrega apenas
widget JS + dashboard + lógica de handoff. Modelo: SaaS $50/mês até 500
conversas + $0.10/conversa adicional, ou self-hosted $299/mês flat.

_Vectora Code Review_ — _"Code review que conhece os padrões da sua
empresa."_ Bot que comenta PRs no GitHub/GitLab com revisão
contextualizada via RAG sobre codebase + histórico de PRs + AGENTS.md —
não lint genérico. Compete com CodeRabbit/Greptile/Copilot review, mas
para times com código sensível que não podem mandar diffs para a cloud.
Reusa ~95% do stack (RAG sobre código, git tools, `gh` integration,
MCP). Modelo: SaaS $30/dev/mês (mínimo 3 devs) ou self-hosted $499/mês
flat.

**Candidatos avaliados — lançamento condicional:**

- _Vectora Inbox_: cliente de email/Slack com RAG sobre histórico de
  comunicação. UX de email é produto inteiro (IMAP/SMTP/calendário/
  anexos/threading) — condicional a Helpdesk e Code Review estarem
  rentáveis e a um time de pelo menos 2 devs.
- _Vectora Compliance_: agente de LGPD/GDPR/SOC2/ISO27001/HIPAA. Ciclo de
  venda longo, exige conhecimento jurídico — condicional à contratação de
  alguém com esse background. Diferencial: nenhum player global domina
  bem a LGPD (regulação local com sutilezas — ANPD, RIPD).
- _Vectora Onboarding_ e _Vectora Spec/PRD_: TAM pequeno demais para
  produto independente — recomendação é lançar como **plugins** do Tier
  2C primeiro e validar tração antes de promover.
- _Vectora Pages_: adiar. Brigar com Notion/Confluence exige 10+ devs e
  venda enterprise; alternativas self-hosted gratuitas (Outline,
  BookStack) já cobrem o espaço. Melhor caminho é um plugin que conecta a
  KBs existentes, não reinventar edição/colaboração.

### Princípios de produto para o portfólio

1. Self-hosted é diferencial, não limitação — cada produto Tier 3 oferece
   versão self-hosted.
2. Integração, não dependência — cada produto Tier 3 funciona sem o
   Vectora; a integração multiplica valor, não cria lock-in.
3. Sinergia técnica obrigatória — mínimo 70% de reuso do stack (RAG,
   multi-LLM, storage, MCP, REST). Produtos sem essa sinergia foram
   descartados (Meet, Workflows).
4. IA como motor silencioso — nenhum produto se anuncia como "IA"; o que
   se anuncia é o resultado (suporte que resolve, review que conhece o
   projeto).
5. Cada produto resolve uma dor específica e recorrente, sem "features by
   features".
6. Lançamento sequencial, não paralelo — receita de cada camada financia
   a próxima.
7. Self-hosted decisivo, não decorativo — só entra no portfólio quando
   resolve dor real de compliance/regulação/política interna de dados.
8. Janela de oportunidade existe e fecha — decisões de lançamento
   consideram isso (ex: Copilot review crescendo rápido, Vanta/Drata
   consolidando compliance).

### Sequenciamento e receita de referência

```
Ano 1 — Vectora core estabelecido: tração, receita, primeira contratação
Ano 2 — Tier 2 (VSIX, Host/Client, marketplace de plugins) + Helpdesk (beta)
Ano 3 — Helpdesk e Code Review em produção; avaliação dos candidatos Tier 3
Ano 4+ — Lançamento condicional de candidatos, bundle "Vectora Suite"
```

Essas projeções de receita (ex.: ~$3.000/mês conservador ao fim do Ano 1,
~$23.000/mês otimista ao fim do Ano 3) são cenários de planejamento, não
compromissos — servem para dimensionar quando cada camada do portfólio
se torna viável.

---

## Licenciamento OEM

### O cenário que o modelo resolve

Uma futura API REST do Vectora abriria a possibilidade de empresas
comprarem uma licença, construírem um produto próprio em cima dela (um
app estilo ChatGPT, uma IDE, uma ferramenta de automação interna) e
venderem esse produto com assinatura própria. Isso é saudável — significa
que o Vectora é bom o suficiente para servir de base a outros produtos —
mas cria um problema econômico: se essa empresa tem milhares de usuários
pagantes no produto dela, a licença que paga à Vectora Company (de um
único servidor) não reflete o valor que está monetizando em cima.

Distinção central:

- **Uso interno** (já coberto pelas licenças padrão): funcionários da
  própria empresa usando o Vectora.
- **Uso como motor de produto externo** (requer OEM License): a API do
  Vectora alimenta um produto vendido para clientes externos à
  organização licenciada.

### Estrutura de tiers OEM

| Tier           | Usuários externos | Preço mensal      | Inclui                                                       |
| -------------- | ----------------- | ----------------- | ------------------------------------------------------------ |
| OEM Starter    | até 500           | $199/mês          | 1 instância + suporte básico                                 |
| OEM Growth     | até 5.000         | $599/mês          | 2 instâncias + suporte prioritário                           |
| OEM Scale      | até 25.000        | $1.499/mês        | Instâncias ilimitadas + SLA + suporte dedicado               |
| OEM Enterprise | acima de 25.000   | Negociação direta | Contrato customizado + revenue share (2–5% da receita bruta) |

### Termos

**Permitido com OEM License:** usar a API para alimentar produto externo
comercial, construir interface própria (white-label de UX), vender
assinatura própria, escalar dentro do tier contratado.

**Nunca permitido, mesmo com OEM License:** remover/ofuscar a atribuição
"Powered by Vectora" (exceto contratos Enterprise negociados
especificamente), redistribuir o código-fonte, revender a licença em si
como produto concorrente, remover as restrições de licença para usuários
finais.

### Detecção e enforcement

Monitoramento de volume de chamadas de API por token de licença; volume
atípico para o plano contratado gera flag automático para revisão.
Processo: notificação amigável → período de regularização de 30 dias →
suspensão se não regularizado. O objetivo declarado é monetizar
corretamente, não punir — uma empresa usando o Vectora como motor externo
é exatamente o perfil de cliente que a Vectora Company quer, só precisa
do contrato certo.

### Perfil de cliente e canal de vendas

Startups SaaS de IA que não querem construir infraestrutura própria,
agências que querem oferecer features de IA a clientes, empresas de
software legado que querem "adicionar IA" sem reescrever tudo. Venda OEM
não é self-serve — requer call comercial; o fundador conduz as primeiras
vendas diretamente e só contrata sales dedicado com 3+ clientes OEM
ativos.

---

## Parcerias estratégicas

> Registro de raciocínio para quando o Vectora atingir relevância
> suficiente para iniciar essas conversas — não é plano de ação
> imediato.

### O argumento central

O Vectora não é apenas cliente do Cohere ou do Tavily — é um **canal de
distribuição** para ambos. A maioria das PMEs de tecnologia nunca
contrataria esses provedores diretamente, porque nunca construiria a
infraestrutura (pipeline RAG com embedding, vector store, reranker, busca
web) que os torna úteis. O Vectora entrega essa infraestrutura pronta, e
ao fazer isso leva esses provedores a empresas que de outra forma nunca
os teriam como fornecedores.

### Cohere

O Cohere já é o backbone estrutural do RAG do Vectora, não uma integração
superficial: `embed-multilingual-v3.0` indexa todos os documentos de
todos os workspaces, e `rerank-multilingual-v3.0` roda a cada busca RAG
**independente do LLM escolhido pelo usuário** — ou seja, mesmo empresas
usando GPT-4 ou Claude como LLM principal geram receita para o Cohere via
embedding e reranking.

Cenários de negociação, do mais provável ao mais distante:

- **Distribuição:** créditos/desconto de volume para usuários do
  Vectora, listagem como parceiro oficial, co-marketing.
- **Provider preferencial:** Cohere financia integrações específicas,
  Vectora recomenda Cohere como padrão no setup, acesso antecipado a
  novos modelos.
- **Investimento ou aquisição** (longo prazo, se houver interesse): com
  uma cláusula inegociável em qualquer cenário — acesso a LLMs
  concorrentes (OpenAI, Anthropic, Google) nunca é removido. Um Vectora
  que só roda Cohere não é o Vectora.

Gatilho para abordar: 500+ usuários ativos gerando volume mensurável de
chamadas ao Cohere, ou caso de uso documentado em produção. Canal:
equipe de partnerships/devrel, não o topo da empresa.

### Tavily

O Tavily é o motor de busca web do Vectora (Search Agent, cascading web →
vector store, fallback do RAG) e não tem produto consumer próprio — seu
crescimento depende de desenvolvedores integrando a API em produtos. O
Vectora usa a integração oficial mais avançada (`langchain-tavily` v2,
com `topic`/`time_range`/`include_raw_content`/`tavily_extract`), o que
já é argumento de parceria por si só (showcase de uso avançado dentro do
ecossistema LangChain).

Cenários: créditos para trials + co-marketing (mais provável), acesso
antecipado a features novas, ou revenue share via código de referência no
wizard de setup. Como o Tavily é uma empresa menor, a conversa pode
acontecer mais cedo — mesmo com 100–200 usuários ativos já há volume
suficiente para justificá-la.

### Linhas vermelhas — não negociar em hipótese alguma

1. **Remoção de providers concorrentes.** O Vectora nunca remove OpenAI,
   Anthropic, Gemini ou qualquer outro provider para favorecer um
   parceiro — vai contra o princípio de democratizar IA.
2. **Coleta de dados de conversas.** Nenhum parceiro recebe acesso ao
   conteúdo de conversas ou workspaces dos usuários — self-hosted
   significa que esses dados nunca saem do servidor do cliente.
3. **Mudança de posicionamento.** O Vectora não vira produto do Cohere ou
   do Tavily. Parceria é co-marketing e integração preferencial, não
   white-label ou rebrand.

### Preparação

Quando o momento chegar: deck de parceria de 2 páginas (números de
usuários, volume de API, caso de uso documentado), identificação do
contato certo (partnerships/devrel, não CEO), abordagem inicial curta no
LinkedIn sem deck frio, call de exploração antes de qualquer proposta
formal.

---

## Operação da company

### Identidade e legal

Estrutura jurídica: MEI/ME no CNPJ do fundador, conta PJ para receber
pagamentos. Domínio principal `vectora.company`, com `docs.` e `api.`
como subdomínios. Marca registrável no INPI quando a receita justificar.

Documentos legais obrigatórios para o site e para o billing:

- **Política de Privacidade** (`/privacy`): dados coletados (email, nome,
  logs de validação de licença, dados de pagamento processados pelo
  provedor de cobrança — nunca cartão armazenado localmente); dados
  explicitamente **não** coletados (conteúdo de conversas, arquivos,
  código — self-hosted significa que isso fica no servidor do cliente);
  base legal LGPD/GDPR; retenção; direitos do titular (portabilidade,
  esquecimento).
- **Termos de Uso / EULA** (`/terms`): licença de uso não exclusiva, não
  transferível, não sublicenciável; o que é permitido (uso comercial
  dentro da organização licenciada) e o que não é (redistribuição,
  sublicenciamento, engenharia reversa para concorrência, revenda de
  acesso); trial sem cartão obrigatório; cancelamento a qualquer momento
  com acesso mantido até o fim do período pago.

### Billing, auth e licenciamento — arquitetura atual

O billing e a autenticação da company **não usam mais Supabase**. A
company foi migrada integralmente para um backend próprio: um Cloudflare
Worker chamado **`services`** (`services.vectora.company`), que também
absorveu o antigo `relay` — renomeado para `gateway` em 2026-07-20 — (OAuth/
webhooks do desktop) e o `update-server`
(distribuição de releases). Tudo roda em D1 (SQLite gerenciado pela
Cloudflare) — não há RLS de banco; autorização é código, verificada em
cada handler via sessão resolvida a partir do token Bearer.

O que `services` implementa hoje, por área:

- **Auth** (`services/src/auth/`): signup com verificação de email
  obrigatória, login por email/senha, magic link, sessão via **token
  opaco** (não JWT — a company é a única consumidora, comunicação
  server-to-server, então não há motivo para carregar claims num JWT).
  Cadastro protegido por Turnstile.
- **Billing** (`services/src/billing/`): checkout e portal de assinatura
  com **dois provedores conforme o país do usuário** — Stripe para
  clientes internacionais, **Asaas para o Brasil** (evita as fricções de
  Stripe com cartões/boleto BR). Webhooks de ambos os provedores mantêm
  `subscriptions.status`/`tier` sincronizados; cancelamento sempre
  rebaixa o tier para `free` (o gate `require_pro()` no backend Python
  verifica tier, não status).
- **License** (`services/src/license/`): validação do VECTORA_TOKEN
  (`/validate`, endpoint público, sem sessão — é o único mecanismo de
  auth que o desktop/CLI usa) e troca de email/senha por token
  (`/agent-login`).
- **GDPR** (`services/src/gdpr/`): export de dados do usuário (perfil,
  assinaturas, histórico de validação de licença, API keys) e exclusão de
  conta, com hard-delete agendado via Cloudflare Cron Trigger nativo (não
  mais `pg_cron`).
- **API keys** (`services/src/api-keys/`): emissão e gestão de chaves de
  API com escopos (`read`/`write`/`admin`).

- **Issues & waitlist** (`services/src/issues/`): formulário público de
  bug/feedback/feature, protegido por Turnstile.
- **RAG library** (`services/src/rag-library/`): catálogo mínimo (leitura
  em D1 + redirect para storage externo) de pacotes RAG pré-indexados —
  ver "Catálogo de conhecimento pré-indexado" abaixo.

O modelo Free/Pro reflete essa arquitetura: **Free é 100% local, sem
conta** — não passa por `services` em nenhum momento. **Pro é opcional**
e cobre trial/billing/licenciamento, servido inteiramente por
`services.vectora.company`. Não existe um "Vectora Cloud" hospedando
instâncias de desktop de terceiros em Docker, nem integração com GPT
Store — essa direção, explorada em versões anteriores do produto, foi
abandonada junto com a ideia de cloud obrigatória. O que sobrevive dela é
descrito a seguir.

### Catálogo de conhecimento pré-indexado (direção de roadmap)

Uma ideia recorrente nas iterações do produto — desde o "Zyris Rag"
original até versões posteriores do planejamento — é oferecer uma
biblioteca de bases de conhecimento pré-indexadas (stacks de programação,
frameworks, domínios verticais) que o usuário ativa conforme necessário,
em vez de indexar tudo do zero. A instância mínima disso já existe como
placeholder em `services/src/rag-library/`: um catálogo em D1 com
metadados (nome, versão, checksum, URL de storage) e redirect para um
provedor de storage externo — sem reindexação nem upload de terceiros
nesta fase.

Esse catálogo permanece fora do escopo de curto prazo — só entra em
desenvolvimento ativo depois do lançamento do Vectora — e o nome final
ainda está em aberto (não será "RAG library" nem "buckets", que foram
nomes de trabalho de fases anteriores).

Importante: isso não implica um "Vectora Cloud" completo com créditos de
IA inclusos, parcerias de infraestrutura para plano gratuito subsidiado,
ou um Data Store que substitui a customização total do self-hosted. Essa
versão mais ampla do conceito foi avaliada e não é a direção atual — o
que segue vivo é apenas o catálogo de conhecimento pré-indexado como
complemento opcional ao RAG customizado, não como produto cloud
separado.

### Site (vectora.company)

Landing single-page com hero, vídeos de produto sem narração, explicação
de RAG via diagrama animado, diagramas de arquitetura (CLI/MCP/Chat Web,
agentes especializados, empresa em VPS com múltiplos usuários), tabela de
planos, FAQ e páginas legais. Autenticação e dashboard (token, status de
licença, histórico de validações, gestão de assinatura) consomem os
endpoints de `services` descritos acima — não mais Supabase Auth SSR.
i18n inicial: `pt-BR` (default) e `en`.

### Documentação (docs.vectora.company)

Getting started (instalação, quick-start, VECTORA_TOKEN, primeiro
workspace), guias (deploy em VPS, setup de equipe, RAG, MCP, git
workflows, API keys), referência (CLI, config, tools, agentes, API,
servidor MCP), self-hosting (requisitos, Docker, reverse proxy, storage
backends, updates) e changelog público. Padrão de qualidade: toda página
com pré-requisitos, passos numerados, resultado esperado e
troubleshooting.

### Suporte e comunidade

Canais: WhatsApp Business com horário explícito, email de suporte com
SLA de resposta, GitHub Issues público com templates e triagem regular.
Comunidade via GitHub Discussions inicialmente (Discord como expansão
futura). Programa de beta testers (10–20 pessoas recrutadas em
comunidades de dev) antes de qualquer campanha de lançamento maior, em
troca de acesso Pro gratuito e feedback estruturado. Status page pública
para uptime do site e da API de validação de licença.

### Distribuição e lançamento

PyPI como canal principal de instalação, com imagem Docker de referência.
Kit de lançamento para influenciadores (licença gratuita temporária, guia
de instalação, sugestões de demo, assets de marca) distribuído com 1–2
semanas de antecedência, priorizando canais brasileiros na primeira fase
e internacionais depois. Posts de lançamento coordenados em canais
próprios (LinkedIn, Reddit, X, Hacker News) e vídeo trailer/tutorial no
YouTube.

### Marketing pós-lançamento

Cronograma T-30 a T+14 dias cobrindo recrutamento de beta testers, envio
de kits, publicação do site e da documentação, e o dia de lançamento
coordenado. Métricas de sucesso definidas em cenários conservador e
otimista (instalações, contas criadas, trials ativos, assinantes
pagantes) e indicadores de qualidade (conversão trial→pago, churn em 30
dias). Conteúdo recorrente pós-lançamento ("casos de uso do Vectora") para
manter tração orgânica, com cupons de desconto permanente para early
adopters como incentivo à conversão rápida no lançamento.

### Princípios da operação

1. **Self-hosted é a proposta de valor central** em toda comunicação —
   dados sempre ficam no servidor do cliente; a company nunca armazena
   conversas, código ou arquivos.
2. **Produto primeiro, empresa depois** — nenhuma frente de marketing
   começa sem o produto estável.
3. **Suporte pessoal é diferencial** — contato direto com o fundador é
   uma vantagem que empresas grandes não conseguem replicar.
4. **Documentação é produto** — recebe o mesmo cuidado que o código.
5. **Preço honesto** — estratégia de volume e fidelização, não margem
   alta em poucas contas.
6. **Open source como comunidade, fechado como produto** — issues, docs
   e changelog públicos; código proprietário, mas transparente sobre o
   que o produto faz.
7. **Um fundador, muita alavancagem** — influenciadores como marketing,
   beta testers como QA informal, comunidade como suporte de primeiro
   nível.
