# Vectora

Inteligência Artificial que é sua — instalada, controlada e evoluída por você.

## O Problema

Toda ferramenta de IA que você usa hoje guarda seus dados em servidores de outra empresa.

Seu código. Sua documentação. Suas conversas. Seu contexto de projeto.  
**Tudo isso sai da sua máquina e vai para a nuvem de outra pessoa.**

Para desenvolvedores independentes isso é inconveniente.  
Para empresas, é um risco jurídico, um problema de compliance e uma dependência estratégica.

## A Solução: Self-Hosted AI

**Vectora é um aplicativo de inteligência artificial self-hosted.**

Você instala e roda na sua própria máquina ou em um servidor dedicado que você controla.  
Sua base de conhecimento, seu histórico de sessões, seus documentos indexados — **ficam no seu ambiente.**

**O que "self-hosted" significa de verdade:**

O núcleo do Vectora — orquestração, RAG, memória, workspaces, checkpoints — é extremamente leve. Roda em qualquer dispositivo: de uma VPS de entrada a um servidor corporativo, ou até no Termux num Android.

**Onde recomendamos hospedar:**

- **Uso profissional → VPS.** Uma VPS dá acesso ao Vectora por SSH e pelo chat web com autenticação RBAC. Seu time acessa de qualquer lugar; sua infra fica separada do seu computador pessoal.
- **Uso pessoal → qualquer dispositivo.** PC, notebook, servidor em casa, Raspberry Pi. O Vectora em si não exige hardware potente.

**O LLM é o único componente que exige decisão:**

O Vectora se conecta a qualquer provedor de LLM via API — OpenAI, Gemini, Claude, Cohere, entre outros. Os prompts vão para o provedor que você escolheu, sujeitos aos termos e à política de dados deles. Você decide o que usar; você assume a responsabilidade.

**E o Ollama?** Suportamos como provedor de LLM, mas não recomendamos como ponto de partida. Para ter resultados satisfatórios, você precisa de modelos com dezenas ou centenas de bilhões de parâmetros — hardware extremamente high-end: dezenas de gigabytes de VRAM ou RAM compartilhada. Mesmo notebooks recentes com 32 GB e NPU sofrem. Em VPS esse processamento simplesmente não existe. Ollama faz sentido para quem já tem o hardware certo por outras razões. Além disso, usar Ollama não elimina as dependências externas: Cohere (embeddings e reranking) e Tavily (busca web) continuam sendo integrações obrigatórias — o Vectora não suporta alternativas self-hosted para essas funções, e o LangChain/LangGraph suporta Ollama apenas como LLM.

Duas integrações são necessárias para o funcionamento completo:

- **Cohere** — fornece os embeddings e o reranking que sustentam o RAG. Sem Cohere, o Vectora perde a capacidade de indexar e buscar conhecimento.
- **Tavily** — fornece a busca web. Sem Tavily, o Vectora opera sem acesso à internet.

Ambas são APIs externas com seus próprios termos de serviço. Os dados que trafegam por elas (queries de busca, chunks de documentos para embedding) são de responsabilidade do operador.

**Custo:** você não paga por assento nem por número de usuários. Paga pelos tokens que consome nas APIs que escolheu usar.

**LGPD e compliance:** não existe um servidor Vectora no meio do caminho. O seu Vectora se conecta diretamente às APIs que você configurou e aos MCPs que você instalou. Nós não vemos nem intermediamos nada. A responsabilidade pelo tratamento dos dados é entre você e cada provedor que você conectou — e nossos Termos de Uso descrevem exatamente o que trafega em cada integração.

## Posicionamento: Concorrente e Parceiro ao Mesmo Tempo

À primeira vista, o Vectora compete com ferramentas como **Claude Code**, **Codex**, **OpenCode** e **Hermes Agent**.  
Quando usado como CLI ou como chat, ele é de fato uma alternativa direta.

O campo está dividido: Claude Code e Codex são serviços em nuvem com custo por assinatura. OpenCode e Hermes são open-source e self-hosted — concorrentes mais próximos — mas nenhum dos dois tem RAG nem chat web para uso em VPS com times.

Mas o Vectora tem um modo que nenhum concorrente tem: **modo MCP**.

> O protocolo MCP foi criado para conectar ferramentas a inteligências artificiais.  
> O Vectora expõe uma ferramenta chamada `delegate_to_vectora`.

Isso significa que um desenvolvedor pode continuar usando o Claude Code ou o Codex  
e, quando eles chegam num limite — indexar conhecimento, fazer RAG em documentação interna,  
busca com relevância semântica — **eles delegam para o Vectora**.

**Nossos concorrentes viram usuários do Vectora.**  
Não substituímos o fluxo de trabalho existente. Nós o estendemos.

### Uma Comparação Honesta: O Perssua

Quando falamos de IAs brasileiras no desktop, o [Perssua](https://perssua.com) inevitavelmente aparece — e merece ser mencionado com respeito.

O Perssua é um assistente de reuniões desenvolvido por uma única pessoa (Lucas Montano, ex-líder de desenvolvimento Android na Disney+). Ele diferencia falantes numa reunião, transcreve em tempo real, gera resumos, traduz ao vivo, tem modo stealth (visível só para você, mesmo que sua tela esteja sendo compartilhada), suporte a chat por texto, voz e captura de tela, e um gerenciador de LLMs locais via llama.cpp com otimização TurboQuant. É um produto impressionante.

**Mas Vectora e Perssua não competem.** São propostas completamente diferentes:

|                    | Vectora                                         | Perssua                                    |
| ------------------ | ----------------------------------------------- | ------------------------------------------ |
| Para quem          | Desenvolvedores e times técnicos                | Profissionais em reuniões                  |
| Foco central       | Agente de desenvolvimento com RAG               | Assistente de reuniões com transcrição     |
| Forma de acesso    | CLI, chat web, futuramente desktop              | App desktop exclusivo                      |
| RAG                | Pilar central — indexa código e docs do projeto | Presente mas não divulgado publicamente    |
| Áudio / voz        | ❌ não implementado (roadmap)                   | ✅ diferenciação por falante em tempo real |
| Execução de código | ✅ terminal, edição de arquivos                 | ❌ não é o foco                            |
| Modo MCP           | ✅ parceiro de outros agentes                   | ❌                                         |
| Self-hosted        | ✅ roda na sua infra                            | ❌ app desktop local                       |

Rivalizamos muito mais com Claude Code, Codex, OpenCode e Hermes do que com o Perssua. São iniciativas complementares — um dev pode usar o Perssua em reuniões e o Vectora no seu terminal sem nenhum conflito.

## Por Que Agora

O mercado de agentes de IA para desenvolvimento explodiu — mas todas as soluções, cloud ou self-hosted, resolvem o mesmo problema: escrever e executar código com um LLM bom. Nenhuma resolve o problema adjacente e mais difícil: **fazer o agente conhecer de verdade o seu projeto.**

Sem conhecimento indexado, o agente alucina sobre sua base de código, ignora suas convenções, desconhece sua documentação interna. Quanto maior o projeto, pior o problema.

O Vectora resolve isso com RAG. Não como feature secundária — como pilar central da arquitetura. É o único agente de desenvolvimento com um sub-agente dedicado exclusivamente à recuperação e auditoria de conhecimento. Isso significa que quando o Vectora responde sobre o seu projeto, ele está respondendo **com base no que você indexou** — não com base no que o modelo foi treinado para achar que é verdade.

A demanda por isso cresce junto com a complexidade dos projetos e a exigência de controle sobre o que a IA sabe. **Vectora é a única ferramenta de desenvolvimento que você instala na sua infraestrutura, audita o código-fonte, alimenta com o seu próprio conhecimento e evolui conforme sua necessidade.**

## Arquitetura de Agentes

O Vectora não é um único modelo respondendo perguntas.  
É um sistema de **quatro agentes especializados**, cada um com domínio próprio.

### 🔵 Vectora Agent

**O orquestrador.**

Recebe a tarefa, entende o contexto, decide qual agente especialista acionar  
e consolida as respostas em uma entrega coerente.  
É o ponto de entrada único — para o usuário e para quem delega via MCP.

### 🟣 Vectora RAG Agent

**O astro do projeto. Especializado em Recuperação de Conhecimento.**

Nossos concorrentes não têm um agente dedicado a RAG.  
Alguns sequer têm as ferramentas para isso.

O Vectora RAG indexa qualquer base de conhecimento — documentação, código, wikis, PDFs —  
e responde com contexto real do seu projeto, não com alucinação baseada em dados de treinamento.

### 🟡 Vectora Search Agent

**Especializado não só em buscar, mas em relevância e apresentação.**

A diferença entre "retornar resultados" e "entregar a resposta certa" é enorme.  
O Search Agent filtra ruído, reordena por relevância e entrega a informação  
no formato mais útil para quem perguntou.

### 🟢 Vectora Coder Agent

**Especializado em desenvolvimento com boas práticas.**

Escreve, revisa e refatora código com entendimento do padrão do projeto —  
porque ele leu o projeto antes de tocar nele.

## RAG: O Que é e Por Que Importa

**Retrieval-Augmented Generation** é o conjunto de tecnologias que torna o Vectora "retreinável" para qualquer projeto.

```
── INGESTÃO ──────────────────────────────────────────────────────────────
  Documento / Código / Wiki / PDF
          ↓
     [ Embedding ]         ← Cohere: conteúdo → vetores semânticos
          ↓
    [ Vector Store ]       ← LanceDB local (nunca sai da sua infra)

── RECUPERAÇÃO (Vectora RAG Agent) ───────────────────────────────────────
          ↓
  [ Expand Query ]         ← LLM gera N reformulações da query (multi-query)
          ↓
   [ Vector Search ]       ← Dense (Cohere embeddings) + BM25 esparso,
                              fundidos via Reciprocal Rank Fusion
          ↓
  [ Decisão de qualidade ] ← avalia score dos resultados
     ├── score alto  → injeta direto no contexto
     ├── score médio → [ Reranker ] (Cohere CohereRerank) → injeta
     └── score baixo → [ Web Search ] → curadoria (Cohere rerank
                           + LLM judge filtra antes de persistir) → injeta

── SÍNTESE ───────────────────────────────────────────────────────────────
          ↓
       [ LLM ]             ← responde com base no contexto auditado
```

O Vectora RAG Agent é o pipeline inteiro — da expansão da query até a injeção do contexto. Ele não é um wrapper em volta de um modelo: é um pipeline de recuperação com múltiplos estágios de qualidade. O score decide o caminho; nenhum resultado chega ao LLM sem passar pelo filtro de relevância. Quando a busca local falha, a web é consultada e o conteúdo passa por um gate de curadoria (reranker + LLM judge) antes de ser persistido — separando o que é lixo do que é conhecimento real.

**Na prática:** você aponta o Vectora para a documentação ou o código-base do seu projeto.  
Ele indexa tudo. A partir daí, ele responde com base no que está lá —  
sem retreinamento, sem fine-tuning.

## Grupos de Ferramentas

Além dos agentes, o Vectora disponibiliza conjuntos de ferramentas especializadas:

| Grupo             | O que faz                                                      | Status                |
| ----------------- | -------------------------------------------------------------- | --------------------- |
| **File System**   | Leitura, escrita, edição e navegação de arquivos e pastas      | ✅ Disponível         |
| **Web**           | Busca na internet, extração de conteúdo, validação de links    | ✅ Disponível         |
| **RAG**           | Embedding, busca vetorial, reranking, ingestão de documentos   | ✅ Disponível         |
| **Workspace**     | Contexto do projeto ativo, manifests, isolamento por workspace | 🔄 Em desenvolvimento |
| **Memory**        | Memória episódica persistente entre sessões                    | ✅ Disponível         |
| **MCP**           | Delegação e recebimento de tarefas via protocolo MCP           | ✅ Disponível         |
| **Git**           | Commits, branches, pull requests, code review assistido        | 📋 Roadmap            |
| **Office**        | Documentos Word, planilhas Excel, apresentações PowerPoint     | 📋 Roadmap            |
| **Database**      | Consultas SQL, migrações, análise exploratória                 | 📋 Roadmap            |
| **Communication** | Slack, e-mail, tickets (Linear, Jira, GitHub Issues)           | 📋 Roadmap            |

## Como Usar o Vectora

O Vectora está disponível hoje em **dois modos de acesso**. Um terceiro está em desenvolvimento.

### CLI / TUI — disponível agora

```bash
uv tool install vectora-agent
vectora chat
```

Interface de texto no terminal — Rich TUI com comandos `/rag`, `/workspaces`, `/traces`, `/memory`. Ideal para quem já vive no terminal.

### Chat Web — disponível agora

```bash
vectora server chat    # sobe o agent + interface web na porta 8080
```

Acesse pelo browser em qualquer dispositivo na rede. Renderização de tool calls, diff de arquivos, progresso de ingestão — tudo no browser sem instalar nada nos clientes. Para times em VPS.

### App Desktop — roadmap v0.5

App nativo (`.exe` / `.app` / `.deb` / AppImage) construído em **Flet** (Python sobre Flutter).

Dois modos no mesmo binário:

- **Embedded** — agent roda in-process, SQLite + LanceDB. Instala e usa offline.
- **Connected** — conecta a um `vectora server` remoto via ConnectRPC. Ideal para times.

Notificações nativas, system tray, drag-and-drop de arquivos para indexação, visualização de tool calls igual ao chat web. E porque usa Flutter como target: o mesmo código-fonte gera `.apk` e `.ipa` para Android e iOS (connected mode apenas — mobile exige server remoto).

**Não há áudio/voz no Vectora** — nem TTS nem STT estão no roadmap atual. Para essas necessidades, o Perssua é a referência brasileira correta.

## Stack Tecnológica

O Vectora tem dois perfis de deploy — mesma interface, infraestrutura diferente.

### Stack Econômica (default — zero configuração extra)

Para uso pessoal, solo dev ou times pequenos. Roda em qualquer máquina sem serviços externos de infra.

| Camada                            | Tecnologia                   |
| --------------------------------- | ---------------------------- |
| Checkpoints / histórico de sessão | SQLite (`AsyncSqliteSaver`)  |
| Vector store (RAG)                | LanceDB (arquivo local)      |
| Cache                             | sem cache (direto nas APIs)  |
| Fila de embedding                 | SQLite (embutido no Vectora) |
| Requisitos mínimos                | 2 núcleos / 4 GB RAM         |

### Stack Alto Desempenho (opt-in — roadmap v0.4)

Para times maiores, VPS compartilhada ou quando a carga justifica serviços dedicados. Ativado via config (`CHECKPOINT_BACKEND`, `VECTOR_BACKEND`, `CACHE_BACKEND`) — zero breaking change para quem usa a stack econômica.

| Camada                            | Tecnologia                                             |
| --------------------------------- | ------------------------------------------------------ |
| Checkpoints / histórico de sessão | **PostgreSQL** (`AsyncPostgresSaver`)                  |
| Vector store (RAG)                | **Qdrant** (servidor dedicado, sparse vectors nativos) |
| Cache                             | **Redis** (embedding cache + LLM response cache)       |
| Fila de embedding                 | PostgreSQL / Redis                                     |
| Requisitos sugeridos              | 8+ núcleos / 16+ GB RAM + serviços externos            |

**Por que PostgreSQL?** Concurrent writes, connection pool, durabilidade production-grade. SQLite é ótimo para um usuário; com múltiplos usuários simultâneos escrevendo checkpoints, PostgreSQL escala sem atrito.

**Por que Qdrant?** Sparse vectors nativos (BM42), UI web própria, filtros avançados por metadata, e performance superior em coleções grandes. LanceDB é excelente file-based; Qdrant é a escolha quando o volume de indexação cresce além de dezenas de milhares de documentos.

**Por que Redis?** Evitar re-embeddar o mesmo conteúdo (embedding cache por hash) e reutilizar respostas LLM idênticas. Em VPS com múltiplos usuários consultando a mesma base, o ganho em latência e custo de tokens é significativo.

## Comparativo de Interfaces

| Característica       | CLI (TUI)              | Chat Web                | Desktop (roadmap)                             |
| -------------------- | ---------------------- | ----------------------- | --------------------------------------------- |
| Status               | ✅ Disponível          | ✅ Disponível           | 📋 Roadmap v0.5                               |
| Plataforma           | Terminal (qualquer OS) | Qualquer browser        | Win / macOS / Linux + Android/iOS (connected) |
| Instalação           | `uv tool install`      | Agent rodando + browser | Instalador nativo (.exe / .app / .deb / .apk) |
| Modo offline         | ✅                     | ✅ (agent local)        | ✅ embedded / ❌ connected                    |
| Notificações nativas | ❌                     | Toast browser           | ✅ OS nativo                                  |
| System tray          | ❌                     | ❌                      | ✅                                            |
| Background mode      | Sessão tmux            | Aba aberta              | ✅ nativo                                     |
| Drag-and-drop        | ❌                     | Parcial                 | ✅ nativo                                     |
| Mobile               | ❌                     | Responsivo              | ✅ roadmap (.apk / .ipa — connected only)     |
| Áudio / voz          | ❌                     | ❌                      | ❌                                            |
| Auto-update          | `uv tool upgrade`      | Recarregar              | Popup nativo                                  |

## Vectora para Empresas

O Vectora tem um **aplicativo web self-hosted** que se conecta diretamente aos agentes.

Uma empresa instala um único Vectora em seu servidor interno.  
Todos os funcionários acessam pelo browser — sem instalar nada, sem configurar nada.  
O agente tem acesso à worktree dos projetos internos e pode contribuir diretamente no código.

**O que isso significa na prática:**

- O histórico de sessões, os documentos indexados e a base de conhecimento ficam no servidor da empresa
- O custo não escala por usuário — escala com os tokens que você consome nas APIs escolhidas
- O LLM pode ser local (Ollama) ou via API externa, mas independentemente disso, Cohere (embeddings e reranking) e Tavily (busca web) são integrações externas obrigatórias.
- Funciona em rede interna para o núcleo do sistema, mas requer acesso externo ao Cohere e ao Tavily
- **LGPD:** não existe um servidor Vectora no meio do caminho. O seu Vectora se conecta diretamente às APIs que você configurou — o LLM escolhido, Cohere, Tavily — e aos MCPs que você mesmo instalou. Nós não vemos, não armazenamos e não intermediamos nenhum dado seu. A responsabilidade pelo tratamento dos dados perante a LGPD é entre você e cada provedor que você escolheu conectar.
- SOC 2 e auditorias de segurança: o código é open-source (Apache 2.0) — auditável por qualquer time interno

## Integração com Paperclip

O Vectora expõe um **modo headless** — uma API ConnectRPC sem interface gráfica, pensada para ser consumida diretamente por outros sistemas.

O **Paperclip** é um dos casos de uso mais diretos. Com o headless mode, você configura o Paperclip para usar o Vectora como o agente de um usuário ou papel específico dentro da sua organização:

**Cenário típico em uma empresa paperclip:**

- O CEO e o CTO apontam diretamente para o Vectora. Todas as respostas passam pelo RAG — o que o agente sabe é exatamente o que foi indexado na base de conhecimento da empresa.
- Os demais colaboradores usam o agente de sua preferência. Quando esse agente precisa de conhecimento indexado, busca semântica avançada ou RAG sobre documentação interna, ele delega para o Vectora via MCP e recebe de volta a resposta já processada.

Dois modos de integração, um único Vectora:

| Modo         | Como funciona                                                   | Para quem                                                      |
| ------------ | --------------------------------------------------------------- | -------------------------------------------------------------- |
| **Headless** | Paperclip usa o Vectora diretamente como backend                | Usuários que precisam que 100% das respostas venham do RAG     |
| **MCP**      | Outros agentes delegam tarefas para o Vectora quando necessário | Times que já têm um agente preferido e querem estender com RAG |

## Diferenciais em Resumo

|                                       | Vectora | Claude Code | OpenCode |  Codex  | Hermes  |      Perssua       |
| ------------------------------------- | :-----: | :---------: | :------: | :-----: | :-----: | :----------------: |
| Self-hosted                           |   ✅    |     ❌      |    ✅    |   ❌    |   ✅    |     ✅ (local)     |
| Base de conhecimento local (RAG)      |   ✅    |     ❌      |    ❌    |   ❌    |   ❌    |     ✅ (docs)      |
| Suporte a múltiplos LLMs              |   ✅    |     ❌      |    ✅    | Parcial |   ✅    | ✅ (via llama.cpp) |
| Agente RAG dedicado                   |   ✅    |     ❌      |    ❌    |   ❌    |   ❌    |         ❌         |
| Modo MCP (parceiro de outros agentes) |   ✅    |     ❌      |    ❌    |   ❌    |   ❌    |         ❌         |
| Multi-agente especializado            |   ✅    |     ❌      |    ❌    | Parcial | Parcial |         ❌         |
| App web para times (VPS)              |   ✅    |     ❌      |    ❌    |   ❌    |   ❌    |         ❌         |
| App desktop nativo                    | 📋 v0.5 |     ❌      |    ❌    |   ❌    |   ❌    |         ✅         |
| Áudio / voz                           |   ❌    |     ❌      |    ❌    |   ❌    |   ❌    |         ✅         |
| Transcrição de reuniões               |   ❌    |     ❌      |    ❌    |   ❌    |   ❌    |         ✅         |
| Foco em desenvolvimento               |   ✅    |     ✅      |    ✅    |   ✅    |   ✅    |      Parcial       |
| CLI / terminal                        |   ✅    |     ✅      |    ✅    |   ✅    |   ✅    |         ❌         |
| Custo por usuário                     |   ❌    |     ✅      |    ❌    |   ✅    |   ❌    |         ✅         |
| Open-source (auditável)               |   ✅    |     ❌      |    ✅    |   ❌    |   ✅    |         ❌         |

> **Nota sobre o Perssua:** incluímos na tabela para referência, mas não rivaliza com o Vectora. São ferramentas com propósitos completamente distintos — um dev pode usar os dois sem nenhum conflito.

## Roadmap

O Vectora nasce com foco em desenvolvimento de software — mas a visão é mais ampla.

### v0.1.0 — Estabilidade e Controle

- Human-in-the-loop (HITL): aprovação antes de ações destrutivas (terminal, edição de arquivos)
- Workspaces por projeto: isolamento de conhecimento RAG por diretório de trabalho
- Manifests de workspace: o agente sabe o que está indexado e responde direto do manifest quando possível

### v0.2.0 — RAG Avançado

- Hybrid RAG: busca densa (embeddings) + esparsa (BM25) fundidas por Reciprocal Rank Fusion
- Multi-query retrieval: N reformulações da query para maximizar recall
- LangGraph Store para memória semântica namespaceada por workspace

### v0.3.0 — Migração para Deep Agents + Novos Domínios

- Migração do grafo para o framework Deep Agents
- **Git Agent**: commits, branches, PRs, code review
- **Office Agent**: documentos, planilhas, apresentações
- **Database Agent**: queries SQL, schema, migrações, análise
- **Communication Agent**: Slack, e-mail, tickets (via MCP ou integração nativa)

### v0.4.0 — Stack Alto Desempenho (opt-in)

- PostgreSQL como checkpointer (concurrent writes, durabilidade production-grade)
- Qdrant como vector store (sparse vectors nativos, performance em escala)
- Redis como cache distribuído (embedding cache + LLM response cache)
- Servidor multi-tenant com RBAC

### v0.5.0 — App Desktop

- App nativo (Flet / Flutter) para Windows, macOS e Linux
- Modo embedded: agent in-process, SQLite + LanceDB, funciona offline
- Modo connected: aponta para `vectora server` remoto (ideal para times)
- Notificações nativas, system tray, drag-and-drop
- Roadmap mobile: Android e iOS em connected mode

### Futuro

- ACP Protocol: integração nativa com Zed, JetBrains, VS Code, Neovim
- A2A Protocol: Vectora como sub-agente de outros agentes via LangSmith
- Áudio / voz: TTS e STT não estão no roadmap atual — não é o foco do Vectora

## Contato

**Bruno Soares** — bruno.soarxz@gmail.com  
GitHub: [github.com/brunosrz](https://github.com/brunosrz)

_Vectora — Apache 2.0 — Self-hosted. Seus dados. Sua IA._
