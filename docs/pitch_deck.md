# Vectora

**Inteligência Artificial self-hosted que é sua — instalada na sua infra,
controlada pela sua equipe, sem que seus dados saiam do seu ambiente.**

---

## O Problema

Toda ferramenta de IA que você usa hoje guarda seus dados em servidores de
outra empresa.

Seu código. Sua documentação. Suas conversas. Seu contexto de projeto.
**Tudo isso sai da sua máquina e vai para a nuvem de outra pessoa.**

Para desenvolvedores independentes isso é inconveniente. Para empresas, é
um risco jurídico, um problema de compliance e uma dependência estratégica.

E mesmo as alternativas "open" deixam um vácuo: as que são open-source não
têm RAG decente nem chat web multi-usuário; as comerciais cobram por
assento e mandam tudo para a nuvem delas.

---

## A Solução: AI self-hosted comercial, com preço honesto

**Vectora é um aplicativo de IA self-hosted** — você instala e roda na sua
própria máquina ou num servidor que você controla. Sua base de conhecimento,
histórico de sessões e documentos indexados ficam no **seu ambiente**.

A diferença para outras alternativas self-hosted: o Vectora é um **produto
comercial maduro**, não um projeto de fim de semana. Entrega RAG de produção,
chat web multi-usuário com RBAC, integração MCP nativa, instaladores
assinados, auto-update, suporte direto do fundador — coisas que produtos
open-source de hobby raramente entregam juntas.

### Por que self-hosted significa controle real

- **Dados nunca passam pelos nossos servidores.** O Vectora conecta direto
  às APIs que você configurou (OpenAI, Gemini, Cohere, Anthropic, Tavily) e
  aos MCPs que você instalou. Não há servidor intermediário da Vectora
  Company no caminho.
- **LGPD/GDPR**: a responsabilidade pelo tratamento dos dados é entre
  **você e cada provider que você escolheu conectar**. Nossos Termos de Uso
  descrevem exatamente o que trafega em cada integração.
- **Auditável internamente**: clientes Pro recebem o binário compilado +
  documentação completa de arquitetura. Empresas Enterprise podem solicitar
  auditoria sob NDA.

### O que isso NÃO é

O Vectora **não é open source**. É código proprietário licenciado —
parecido com Cursor, Linear ou Notion: você roda na sua infra (ou na
máquina deles), mas o código-fonte é da empresa. A diferença é que **a
infra é sempre sua**.

Versões anteriores do projeto chegaram a ser publicadas como Apache 2.0
durante a fase de prototipagem. Aquela fase terminou: o Vectora hoje é
um produto comercial em escala de PME, sustentado por assinatura, com SLA
e roadmap de produto. Quem instalou as versões antigas Apache continua
livre para mantê-las — mas o produto da Vectora Company evolui sob
licença comercial.

---

## Stack de Hospedagem

O núcleo do Vectora é **extremamente leve**. Roda em qualquer dispositivo:
de uma VPS de entrada a um servidor corporativo, ou no notebook do dev.

**Onde recomendamos hospedar:**

- **Uso profissional → VPS.** O Vectora na VPS dá acesso SSH + chat web
  com autenticação RBAC. Seu time acessa de qualquer lugar; sua infra fica
  separada do seu computador pessoal.
- **Uso pessoal → qualquer dispositivo.** PC, notebook, servidor em casa,
  Raspberry Pi, Termux no Android. O Vectora em si não exige hardware
  potente.

**O LLM é o único componente que exige decisão:** o Vectora se conecta a
qualquer provedor (OpenAI, Gemini, Claude, Cohere, Ollama). Os prompts vão
para o provedor que você escolheu, sujeitos aos termos dele.

**Sobre Ollama**: suportado, mas não recomendado como ponto de partida.
Modelos competitivos exigem dezenas/centenas de GB de VRAM — hardware fora
do alcance da maioria. Em VPS, simplesmente não dá. Use Ollama apenas se já
tem o hardware certo por outras razões.

**Integrações externas obrigatórias para funcionar completo:**

- **Cohere** — embeddings, reranking e transcrição (STT) que sustentam o RAG
  e a entrada de áudio.
- **Tavily** — busca web. Sem Tavily, o Vectora opera sem acesso à internet.

São APIs externas com seus próprios termos. Os dados que trafegam por elas
(queries de busca, chunks para embedding, áudio para transcrição) são de
responsabilidade do operador.

**Custo das APIs:** você paga **direto aos providers**, sem markup nosso.
Sua assinatura do Vectora não inclui tokens de IA — inclui o software, o
suporte, as atualizações e os créditos opcionais dos nossos parceiros (ver
**Modelo de Negócio** mais abaixo).

---

## Posicionamento: Concorrente e Parceiro ao Mesmo Tempo

À primeira vista, o Vectora compete com **Claude Code**, **Codex**,
**OpenCode** e **Hermes Agent**. Como CLI ou chat, é alternativa direta.

O campo está dividido:

- **Claude Code e Codex**: serviços em nuvem com custo por assinatura, sem
  self-host.
- **OpenCode e Hermes**: open-source e self-hosted — mais próximos do
  Vectora — mas nenhum tem RAG dedicado nem chat web multi-usuário para VPS.

E o Vectora tem um modo que nenhum concorrente tem: **modo MCP**.

> O protocolo MCP foi criado para conectar ferramentas a IAs. O Vectora
> expõe `delegate_to_vectora` — qualquer agente externo pode invocar.

Um dev pode continuar usando Claude Code ou Codex no dia a dia e, quando
chega num limite (indexar conhecimento, RAG em docs internas, busca com
relevância semântica), **delega para o Vectora**. **Nossos concorrentes
viram usuários do Vectora.** Não substituímos o fluxo de trabalho — o
estendemos.

### Sobre o Perssua

Quando se fala em IAs brasileiras no desktop, o
[Perssua](https://perssua.com) (de Lucas Montano) aparece. É um assistente
de reuniões: diferencia falantes, transcreve em tempo real, traduz ao vivo,
tem modo stealth.

**Vectora e Perssua não competem.** Propostas distintas:

|                    | Vectora                                  | Perssua                                 |
| ------------------ | ---------------------------------------- | --------------------------------------- |
| Para quem          | Devs e times técnicos                    | Profissionais em reuniões               |
| Foco central       | Agente de desenvolvimento com RAG        | Assistente de reuniões                  |
| Forma de acesso    | CLI, chat web, desktop app, MCP, REST    | App desktop exclusivo                   |
| RAG                | Pilar central — indexa código/docs       | Presente, não divulgado                 |
| Áudio              | STT/TTS via API (input/output do agente) | Diferenciação de falantes em tempo real |
| Execução de código | ✅ terminal, edição, git                 | ❌ não é o foco                         |
| Modo MCP           | ✅ parceiro de outros agentes            | ❌                                      |
| Self-hosted        | ✅ VPS/local                             | ✅ (app local)                          |

Rivalizamos muito mais com Claude Code/Codex/OpenCode/Hermes. Um dev pode
usar Perssua em reuniões e Vectora no terminal sem conflito.

---

## Por Que Agora

O mercado de agentes de IA explodiu — mas quase todas as soluções, cloud
ou self-hosted, resolvem o mesmo problema (escrever código com um LLM bom).
**Nenhuma resolve o problema adjacente e mais difícil: fazer o agente
conhecer de verdade o seu projeto.**

Sem conhecimento indexado, o agente alucina sobre sua base, ignora suas
convenções, desconhece sua doc interna. Quanto maior o projeto, pior.

O Vectora resolve isso com RAG. **Como pilar central**, não como feature
secundária. É o único agente de desenvolvimento com sub-agente dedicado
exclusivamente à recuperação e auditoria de conhecimento. Quando o Vectora
responde sobre o seu projeto, responde **com base no que você indexou** —
não no que o modelo achou que era verdade.

---

## Modalidades de IA (6, não 3)

Versões anteriores do Vectora ofereciam 3 modalidades de IA: chat/code,
embedding e reranker. **Hoje o produto cobre 6**, com providers escolhidos
por mérito em cada categoria — sem lock-in.

| Modalidade            | Provider primário               | Fallbacks                     | Onde aparece                            |
| --------------------- | ------------------------------- | ----------------------------- | --------------------------------------- |
| **LLM chat/code**     | Gemini 3.5 Flash (default)      | OpenAI GPT-5.x, Anthropic 4.x | Orchestrator, Coder, Search             |
| **LLM multilingual**  | Cohere Aya Expanse 32B          | Aya 8B, Aya Tiny              | Workloads pt-BR / sensíveis a custo     |
| **Embedding**         | Cohere `embed-multilingual-v3`  | Gemini text-embedding-004     | Indexação RAG                           |
| **Reranker**          | Cohere `rerank-multilingual-v3` | —                             | Pipeline RAG estágio 3                  |
| **STT** (áudio→texto) | Cohere Transcribe               | OpenAI Whisper, Gemini audio  | Input por voz no chat, transcrições     |
| **TTS** (texto→áudio) | Gemini speech-generation        | OpenAI TTS-1-HD               | "Ler em voz alta" + síntese sob demanda |
| **Image generation**  | Gemini 3.5 nano-banana-pro      | OpenAI `gpt-image-1`          | Diagramas, mockups, ilustrações         |

Geração de **vídeo** está fora de escopo (custo 20–100× maior, latência
inviável para UX de chat, qualidade ainda inconsistente).

### Por que essa stack

- **Cohere** é o backbone do RAG (embedding + reranker + STT + Aya). É um
  parceiro estratégico planejado — alinha com nosso roadmap.
- **Gemini** é o canivete suíço multimodal — chat + image + TTS + audio
  input num só provider, com custo competitivo.
- **OpenAI/Anthropic** ficam como opcionais premium para workloads
  específicas (reasoning pesado, fallback de qualidade).

Tudo passa por Protocol abstrato — trocar provider é mudança de config, não
de código. O usuário escolhe qual provider usar em cada categoria via
Settings → Mídia, ou traz suas próprias chaves (**BYOK**) e bypassa nossas
quotas mensais.

---

## Arquitetura de Agentes

O Vectora não é um único modelo respondendo perguntas. É um sistema de
**agentes especializados**, cada um com domínio próprio, orquestrados pelo
framework Deep Agents (LangChain).

### 🔵 Vectora Agent — o orquestrador

Recebe a tarefa, entende o contexto, decide qual subagente acionar e
consolida as respostas. Ponto de entrada único — para o usuário e para
quem delega via MCP.

### 🟣 Vectora RAG Agent — recuperação de conhecimento

O astro do projeto. Nossos concorrentes não têm sub-agente dedicado a RAG.
Indexa qualquer base (docs, código, wikis, PDFs) e responde com contexto
real do seu projeto — sem alucinação baseada em dados de treinamento.

### 🟡 Vectora Search Agent — busca e relevância

Especializado em relevância e apresentação, não só busca. Filtra ruído,
reordena por relevância, entrega no formato útil. Pipeline web →
curadoria (reranker + LLM judge) → injeção no contexto.

### 🟢 Vectora Coder Agent — desenvolvimento

Escreve, revisa e refatora código com entendimento do padrão do projeto —
porque leu o projeto antes de tocar nele. Suporta git workflows
(commits, branches, PRs via `gh`), worktrees, terminal integrado.

### 🎨 Vectora Media Agent (roadmap)

Quando o volume de operações de mídia (imagem, áudio) justificar,
ganhamos sub-agente dedicado. Hoje as tools de mídia vivem no orchestrator
direto.

---

## RAG: O Que é e Por Que Importa

```
── INGESTÃO ──────────────────────────────────────────────
  Documento / Código / Wiki / PDF
          ↓
     [ Embedding ]     ← Cohere: conteúdo → vetores semânticos
          ↓
   [ Vector Store ]    ← LanceDB local (Plus) ou Qdrant (Pro)

── RECUPERAÇÃO (Vectora RAG Agent) ───────────────────────
          ↓
  [ Expand Query ]     ← LLM gera N reformulações (multi-query)
          ↓
   [ Vector Search ]   ← Dense (Cohere) + BM25 esparso, RRF
          ↓
  [ Score gate ]
     ├── alto   → injeta direto
     ├── médio  → [ Reranker Cohere ] → injeta
     └── baixo  → [ Web Search Tavily ] → curadoria
                  (reranker + LLM judge filtra) → persiste

── SÍNTESE ────────────────────────────────────────────────
          ↓
       [ LLM ]         ← responde com base no contexto auditado,
                         com citações [1][2] referenciando chunks
```

O RAG do Vectora é o pipeline inteiro — da expansão da query até a injeção
do contexto, com **citações verificáveis** na resposta (clicar em `[1]`
abre o chunk original, com path/URL e score do reranker).

Nenhum resultado chega ao LLM sem passar pelo filtro de relevância. Quando
a busca local falha, a web é consultada e o conteúdo passa por um gate de
curadoria (reranker + LLM judge) antes de ser persistido — separando o que
é lixo do que é conhecimento real.

---

## Grupos de Ferramentas

Além dos agentes, o Vectora disponibiliza conjuntos de ferramentas
especializadas, todas registradas com metadata (`render_hint`, `category`,
`destructive`, `icon`) para renderização schema-driven no chat:

| Grupo                   | O que faz                                                     | Status                             |
| ----------------------- | ------------------------------------------------------------- | ---------------------------------- |
| **File System**         | Leitura, escrita, edição, navegação, busca grep               | ✅ Disponível                      |
| **Web**                 | Busca, fetch, crawl, map, research (Tavily v2)                | ✅ Disponível                      |
| **RAG**                 | Embedding, vector search, reranking, ingestão                 | ✅ Disponível                      |
| **Workspace**           | Contexto do projeto, manifests, isolamento por workspace      | ✅ Disponível                      |
| **Memory**              | Memória episódica persistente por usuário                     | ✅ Disponível                      |
| **MCP**                 | Delegação e recebimento via protocolo MCP                     | ✅ Disponível                      |
| **Git**                 | Status, log, diff, branch, checkout, commit, push, worktree   | ✅ Disponível                      |
| **gh CLI**              | PRs, issues, code review assistido                            | ✅ Disponível                      |
| **Terminal**            | PTY persistente (xterm.js no browser, persistente por sessão) | ✅ Disponível                      |
| **Skills**              | Skills nativas Deep Agents instaláveis via git URL            | ✅ Disponível                      |
| **Media (image/audio)** | Geração de imagem, transcrição, síntese de voz                | 🔄 Em desenvolvimento (ia-plus.md) |
| **Office**              | Documentos Word, planilhas, apresentações                     | 📋 Roadmap                         |
| **Database**            | SQL, migrações, análise exploratória                          | 📋 Roadmap                         |
| **Communication**       | Slack, e-mail, tickets (via MCP ou integrações nativas)       | 📋 Roadmap                         |

---

## Como Usar o Vectora — 5 Modos

O mesmo binário compilado entrega 5 interfaces de uso.

### 1. CLI / TUI

Interface textual no terminal — Textual TUI com comandos `/rag`,
`/workspaces`, `/traces`, `/memory`, `/clone`, `/branch`, `/pr`. Ideal
para quem vive no terminal.

```
vectora chat
```

### 2. Chat Web (multi-usuário)

```
vectora server chat   # sobe o agent + interface web na porta 8080
```

Acesse pelo browser de qualquer dispositivo na rede. Renderização
schema-driven de tool calls (diff, terminal, search results, table,
artifact card, image preview, audio player), HITL para ações destrutivas,
multi-usuário com RBAC, workspaces git com worktrees, plugins MCP por
usuário, skills, command bar, slash commands.

Stack: **Vite + TanStack Router (SPA) + React 19 + shadcn/ui + Tailwind 4**.
Servido como assets estáticos pelo próprio FastAPI — mesma origem do
backend, sem proxy intermediário.

### 3. Desktop App (formato principal de envio)

App nativo para Windows, macOS e Linux — instaladores assinados:

- **Windows**: `.msi` + NSIS `.exe` (Azure Trusted Signing EV cert)
- **macOS**: `.dmg` universal x64+arm64 (Apple Developer ID + notarização)
- **Linux**: `.AppImage` + `.deb` + `.rpm` (GPG signed)

Arquitetura: **Electron shell + Nuitka onefile**. Um único binário com a
SPA Vite embutida como data dir; FastAPI roda local na loopback; Electron
carrega `http://127.0.0.1:<port>/`. System tray, deep-link `vectora://`,
auto-update via electron-updater (rollout faseado 5% → 25% → 100%,
quarentena automática em falha repetida).

Sem dependência de Python ou Node instalados no cliente — o instalador
traz tudo.

### 4. MCP Server

```
vectora server mcp --transport stdio    # ou --transport sse
```

Expõe todas as tools do Vectora via protocolo MCP. Claude Code, Codex,
dcode, Zed (via ACP), JetBrains e qualquer cliente MCP podem consumir.
`delegate_to_vectora` permite que agentes externos invoquem o Vectora
inteiro como sub-agente.

### 5. Headless / REST API v1

```
vectora server headless
```

REST API limpa em `/v1/*` com OAuth2 client credentials + compatibilidade
OpenAI (`/v1/chat/completions` aceita shape OpenAI; SDKs Python e TS
oficiais). Webhooks para eventos (`thread.created`, `rag.indexed`, etc.).
Integradores: n8n, Zapier, Make, GitHub Actions, soluções corporativas.

---

## Stack Tecnológica

Dois perfis de deploy — **mesma interface, infraestrutura diferente**. A
escolha entre eles é uma config; trocar não exige reescrever código.

### Stack Econômica (default — incluso no plano Plus)

Para uso pessoal, dev solo, ou times muito pequenos. Roda em qualquer
máquina sem serviços externos de infra.

| Camada                  | Tecnologia                             |
| ----------------------- | -------------------------------------- |
| Checkpoints / histórico | SQLite (`AsyncSqliteSaver` LangGraph)  |
| Store de memória        | SqliteStore (`langgraph.store.sqlite`) |
| Vector store (RAG)      | LanceDB (arquivo local) + FTS nativo   |
| Cache                   | em memória (sem cache distribuído)     |
| Fila de embedding       | SQLite (embutido)                      |
| Requisitos mínimos      | 2 núcleos / 4 GB RAM                   |

### Stack Alto Desempenho (opt-in — plano Pro)

Para times maiores, VPS compartilhada, ou quando a carga justifica
serviços dedicados. Ativado via config (`storage.mode = "complete"`) —
sem breaking change para quem usa a Econômica.

| Camada                  | Tecnologia                                       |
| ----------------------- | ------------------------------------------------ |
| Checkpoints / histórico | **PostgreSQL** (`AsyncPostgresSaver`)            |
| Store de memória        | **PostgresStore** (semantic search)              |
| Vector store (RAG)      | **Qdrant** (hybrid dense + sparse BM42)          |
| Cache                   | **Redis** (KV + RedisCache + RedisSemanticCache) |
| Fila de embedding       | PostgreSQL (`FOR UPDATE SKIP LOCKED`)            |
| Rate limiting           | Redis sliding window                             |
| Requisitos sugeridos    | 8+ núcleos / 16+ GB RAM + serviços               |

**BaaS suportado** (PostgreSQL e Qdrant gerenciados): Supabase, Neon,
Qdrant Cloud, com wizard CLI/UI que cuida das pegadinhas de cada provider
(pgbouncer transaction mode, sslmode, extensões pgvector).

### Pipeline de build

- **Backend**: Python 3.13 + FastAPI + LangGraph + Cohere/Gemini/OpenAI/Anthropic SDKs
- **Frontend**: Vite 8 + TanStack Router + React 19 + shadcn/ui + Tailwind 4
- **Compilação**: Nuitka 4.x onefile + SCons como task runner
- **Desktop**: Electron + electron-builder + electron-updater
- **Lint**: ruff + ty (Astral type checker) + tsc + oxlint (oxc)
- **Test**: pytest + pytest-asyncio + cobertura comportamental por PR

---

## Modelo de Negócio

Preços deliberadamente baixos. Estratégia: volume + fidelização, não
margem alta em poucas contas.

| Plano          | Preço                     | Inclui                                                                                         |
| -------------- | ------------------------- | ---------------------------------------------------------------------------------------------- |
| **Trial**      | Grátis, 30 dias do Plus   | Sem cartão na criação. Acesso completo às features do Plus.                                    |
| **Plus**       | **$7 / R$ 20** /mês       | CLI + MCP + Desktop + Stack Econômica. Single-user. Quotas mensais leves.                      |
| **Pro**        | **$20 / R$ 55** /mês      | Tudo do Plus + Chat web multi-usuário + Stack Alto Desempenho + Webhooks + REST API v1.        |
| **Team**       | **$49 / R$ 130** /mês     | Tudo do Pro + Host/Client + VSIX + SSO. **Quando Tier 2A/2B entregar.**                        |
| **OEM**        | A partir de **$199** /mês | Uso comercial via REST API para servir usuários externos. Tiers escaláveis. Ver `docs/oem.md`. |
| **Enterprise** | Contrato customizado      | SLA, suporte dedicado, DPA, revenue share. On-premise air-gapped.                              |

### Como BR e INTL são cobrados

- **Brasil** (detectado por país): Asaas. Aceita **PIX**, **boleto** e
  cartão. Pix Automático recorrente para subscriptions.
- **Internacional**: Stripe. Cartão internacional + Apple Pay + Google Pay
  - Link.

### Não pagamos seus tokens — você paga

A assinatura cobre **o software, o suporte, as atualizações e os créditos
opcionais de Cohere/Tavily** (quando essas parcerias forem ativadas).
**Não cobre tokens de LLM/embedding** — você paga direto ao provider que
escolheu, sem markup nosso.

Quem traz a própria chave (`BYOK`) bypassa nossas quotas mensais de
geração de imagem, STT e TTS. Tier de assinatura ainda gate quais
**backends de storage** ficam disponíveis (SQLite/LanceDB no Plus,
PostgreSQL/Qdrant/Redis no Pro), mas tokens de IA são sempre por sua conta.

### Cancelamento e reembolso

- Cancelamento self-service via Customer Portal (Stripe/Asaas).
- Acesso mantido até o fim do período pago.
- Reembolso de 14 dias após primeira cobrança (não trial), sem perguntas.

---

## Diferenciais em Resumo

|                                                  |       Vectora       | Claude Code  |  OpenCode  |      Codex      |   Hermes   | Cursor  |
| ------------------------------------------------ | :-----------------: | :----------: | :--------: | :-------------: | :--------: | :-----: |
| Self-hosted (sua infra)                          |         ✅          |      ❌      |     ✅     |       ❌        |     ✅     |   ❌    |
| Código auditável internamente                    |  ✅ (sob NDA Pro+)  |      ❌      | ✅ (open)  |       ❌        | ✅ (open)  |   ❌    |
| RAG dedicado com sub-agente                      |         ✅          |      ❌      |     ❌     |       ❌        |     ❌     | Parcial |
| Multi-LLM (OpenAI + Gemini + Anthropic + Cohere) |         ✅          |      ❌      |     ✅     |     Parcial     |     ✅     | Parcial |
| Multi-agente especializado                       |         ✅          |      ❌      |     ❌     |     Parcial     |  Parcial   |   ❌    |
| Chat web multi-usuário (RBAC)                    |         ✅          |      ❌      |     ❌     |       ❌        |     ❌     |   ❌    |
| MCP server (parceiro de outros agentes)          |         ✅          |      ❌      |     ❌     |       ❌        |     ❌     |   ❌    |
| REST API + SDKs Python/TS                        |         ✅          |   Parcial    |     ❌     |       ❌        |     ❌     |   ❌    |
| Webhooks                                         |         ✅          |      ❌      |     ❌     |       ❌        |     ❌     |   ❌    |
| App desktop nativo assinado                      |         ✅          |      ❌      |     ❌     |       ❌        |     ❌     |   ✅    |
| Auto-update                                      |         ✅          |     n/a      |   manual   |       n/a       |   manual   |   ✅    |
| Áudio (STT + TTS)                                |      🔄 em dev      |      ❌      |     ❌     |       ❌        |     ❌     |   ❌    |
| Geração de imagens                               |      🔄 em dev      |      ❌      |     ❌     |       ❌        |     ❌     |   ❌    |
| Custo                                            |     $7–$20/mês      | $20–$200/mês |   Grátis   | Inclus. ChatGPT |   Grátis   | $20/mês |
| Suporte direto do fundador                       | ✅ (WhatsApp/email) |      ❌      | comunidade |       ❌        | comunidade |   ❌    |

---

## Vectora para Empresas

Uma empresa instala **um único Vectora** no servidor interno. Todos os
funcionários acessam pelo browser — sem instalar nada nas máquinas.
O agente tem acesso à worktree dos projetos internos e pode contribuir
diretamente no código (com HITL para ações destrutivas).

**O que isso significa na prática:**

- Histórico de sessões, documentos indexados e base de conhecimento ficam
  **no servidor da empresa**.
- Custo não escala por assento na nossa cobrança — escala apenas com tokens
  consumidos nas APIs que você escolheu (pagos direto ao provider).
- LLM pode ser local (Ollama) ou via API externa, mas **Cohere e Tavily
  são integrações externas obrigatórias** para RAG e busca web.
- Funciona em rede interna para o core; requer acesso externo para Cohere
  e Tavily.
- **LGPD**: sem servidor Vectora intermediário. Sua instalação se conecta
  direto às APIs que você configurou.
- **Auditoria**: clientes Pro+ recebem documentação completa de
  arquitetura sob NDA. Enterprise pode solicitar auditoria de código.

### Integração com sistemas internos (Paperclip e similares)

O **modo headless** com REST API v1 + OAuth2 client credentials permite
que qualquer sistema interno consuma o Vectora como motor de IA com RAG.

**Cenário típico em uma empresa:**

- **CEO/CTO** apontam direto para o Vectora — 100% das respostas passam
  pelo RAG da empresa.
- **Demais colaboradores** usam o agente de sua preferência (Claude Code,
  Cursor, etc.); quando precisam de RAG sobre docs internas, esse agente
  **delega para o Vectora via MCP** e recebe a resposta já processada.

| Modo         | Como funciona                                                | Para quem                                               |
| ------------ | ------------------------------------------------------------ | ------------------------------------------------------- |
| **Headless** | Sistema usa Vectora diretamente como backend via REST/OAuth  | Quem precisa que 100% das respostas venham do RAG       |
| **MCP**      | Outros agentes delegam tarefas para o Vectora quando preciso | Times que já têm agente preferido e querem estender RAG |

---

## Roadmap

O Vectora hoje cobre o **Tier 1** do plano de portfólio. Próximas frentes:

### Em desenvolvimento (próximos 6 meses)

- **IA+** (ia-plus.md): TTS + STT + geração de imagens, com 6 modalidades
  totais de IA.
- **Deep Agents 2.0** (plan Bloco I): sandbox + worktree por user,
  interpreters Python/JS persistentes, paralelismo real de subagents.
- **Storage Infrastructure** (plan Bloco F): hardening do lite, BaaS
  recipes, migrations tool, admin storage panel.
- **REST API v1** (plan Bloco J): OAuth2 client credentials + endpoints
  Vectora-nativos + compat OpenAI + ACP server público.
- **Cache distribuído** (plan Bloco G): Redis para multi-server,
  langchain-redis (RedisCache, SemanticCache, History).

### Tier 2 — Extensões do Vectora (6–12 meses)

- **Vectora VSIX**: extensão oficial VS Code. Painel lateral com chat,
  contexto automático do arquivo aberto, `/rag add` direto. Conecta via
  ACP ou REST. Publicado no VS Code Marketplace.
- **Vectora Host/Client**: separação servidor central + cliente local por
  usuário. Cada dev tem o Vectora no notebook com acesso a arquivos
  locais **e** conectado à base de conhecimento centralizada da empresa.
- **Plugins / DLC Marketplace** (`vectora.company/plugins`): conectores
  pagos para Jira, Notion, Linear, Figma, Google Workspace, Analytics
  Agent, Security Agent.

### Tier 3 — Produtos Independentes (ano 2+)

Lançados **depois** do Vectora estabelecido. Funcionam sem o Vectora; se
integram naturalmente via RAG. Avaliação completa de candidatos e
critérios de seleção em `docs/products.md`.

**Núcleo recomendado (lançar primeiro):**

- **Vectora Helpdesk** — chatbot de suporte (interno ou externo) com RAG
  sobre a KB da empresa, citações verificáveis e handoff para humano.
  Self-hosted decisivo para saúde, banco, jurídico, governo.
- **Vectora Code Review** — bot que comenta PRs com revisão
  contextualizada (não lint genérico). Conhece os padrões internos do
  projeto via RAG sobre código + histórico de PRs. Self-hosted onde
  GitHub Copilot review não chega.

**Candidatos avaliados (lançamento condicional):**

- Vectora Inbox (email + Slack com RAG)
- Vectora Compliance (LGPD / GDPR / SOC 2 assistido)
- Vectora Onboarding e Vectora Spec/PRD — provavelmente lançados antes
  como plugins do Tier 2C, promovidos a produtos só com tração validada.

### Integrações de editor (médio prazo)

- **ACP Protocol**: integração nativa com Zed, JetBrains, VS Code, Neovim.
  Vectora exposto como ACP server consumível pelos editores.
- **A2A Protocol**: Vectora como sub-agente de outros agentes via
  LangSmith.

### Fora de escopo

- **Geração de vídeo**: custo, latência e qualidade ainda não justificam.
  Reabrir quando Cohere ou Gemini lançar vídeo sub-30-segundos com
  latência < 30 s e custo < $0.10.
- **Voice cloning premium**: gate ético + tier futuro, não prioridade.

---

## Parceiros Estratégicos

O Vectora não é só um cliente do Cohere e do Tavily — é um **canal de
distribuição** para ambos. PMEs que nunca contratariam essas APIs
diretamente passam a usar via Vectora.

### Cohere

Backbone estrutural do Vectora em **quatro camadas não-triviais de
substituir**: embedding, reranker, transcrição (STT) e Aya
(multilingual). Mesmo empresas que usam GPT-4 ou Claude como LLM
principal estão gerando receita para o Cohere via essas camadas. O
Cohere não compete pelo LLM — ganha independente de qual LLM vence.

Detalhes do plano de parceria estão em `docs/apoiadores.md`.

### Tavily

Motor de busca web do Vectora. Toda busca passa pelo Tavily — Search
Agent, fallback do RAG subgraph, web cache. Como o Tavily é puro B2B sem
produto consumer, o Vectora é um vetor natural de adoção.

### Princípio fundacional

Em qualquer parceria, **acesso a LLMs concorrentes nunca é removido**.
Um Vectora que só roda Cohere ou só Gemini não é o Vectora. Democratizar
escolha é parte da proposta.

---

## Para Quem é o Vectora

**Idealmente:**

- **Dev solo profissional**: usa CLI + Desktop App em projetos próprios.
  Plus a $7/mês cobre 90% do uso.
- **Time de 3–10 devs**: instala Pro numa VPS de R$50–100/mês. Cada dev
  acessa via chat web ou MCP do editor preferido.
- **PME tech (até 50 devs)**: roda Pro multi-tenant numa VPS própria.
  Plano Team quando Host/Client entregar.
- **Empresa com sistemas internos**: usa OEM tier para alimentar produtos
  próprios via REST API (ex: Paperclip).

**NÃO é para:**

- Quem quer chat de IA para conversa casual (use ChatGPT free).
- Quem quer assistente de reunião (use Perssua).
- Quem só quer autocomplete de código sem RAG (use GitHub Copilot).

---

## Contato

**Bruno Soares** — fundador e único desenvolvedor (por enquanto)

- Email: **bruno.soarxz@gmail.com**
- Suporte comercial: **support@vectora.company**
- Site: **vectora.company** (em construção)
- Docs: **docs.vectora.company** (em construção)
- WhatsApp: disponível para clientes Pro+ após assinatura
- Status page: **status.vectora.company**

---

_Vectora — software comercial self-hosted. Sua infra, seus dados, seu controle._
