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
  [ Expand Query ]         ← LLM gera N reformulações da query (multi-query C2)
          ↓
   [ Vector Search ]       ← Dense (Cohere embeddings) + BM25 esparso,
                              fundidos via Reciprocal Rank Fusion (C1)
                              + HyDE se score inicial baixo (C3)
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

O Vectora RAG Agent é o subgrafo inteiro — da expansão da query até a injeção do contexto. Ele não é um wrapper em volta de um modelo: é um pipeline de recuperação com múltiplos estágios de qualidade. O score decide o caminho; nenhum resultado chega ao LLM sem passar pelo filtro de relevância. Quando a busca local falha, a web é consultada e o conteúdo passa por um gate de curadoria (reranker + LLM judge) antes de ser persistido — separando o que é lixo do que é conhecimento real.

**Na prática:** você aponta o Vectora para a documentação ou o código-base do seu projeto.  
Ele indexa tudo. A partir daí, ele responde com base no que está lá —  
sem retreinamento, sem fine-tuning.

## Grupos de Ferramentas

Além dos agentes, o Vectora disponibiliza conjuntos de ferramentas especializadas:

| Grupo           | O que faz                                                      |
| --------------- | -------------------------------------------------------------- |
| **File System** | Leitura, escrita, edição e navegação de arquivos e pastas      |
| **Web**         | Busca na internet, extração de conteúdo, validação de links    |
| **RAG**         | Embedding, busca vetorial, reranking, ingestão de documentos   |
| **Workspace**   | Contexto do projeto ativo, manifests, isolamento por workspace |
| **Memory**      | Memória episódica persistente entre sessões                    |
| **MCP**         | Delegação e recebimento de tarefas via protocolo MCP           |

**Em desenvolvimento:** Git, Office (documentos, planilhas, apresentações) e mais.

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

|                                       | Vectora | Claude Code | OpenCode |  Codex  | Hermes  |
| ------------------------------------- | :-----: | :---------: | :------: | :-----: | :-----: |
| Self-hosted                           |   ✅    |     ❌      |    ✅    |   ❌    |   ✅    |
| Base de conhecimento local (RAG)      |   ✅    |     ❌      |    ❌    |   ❌    |   ❌    |
| Suporte a múltiplos LLMs              |   ✅    |     ❌      |    ✅    | Parcial |   ✅    |
| Agente RAG dedicado                   |   ✅    |     ❌      |    ❌    |   ❌    |   ❌    |
| Modo MCP (parceiro de outros agentes) |   ✅    |     ❌      |    ❌    |   ❌    |   ❌    |
| Multi-agente especializado            |   ✅    |     ❌      |    ❌    | Parcial | Parcial |
| App web para times (VPS)              |   ✅    |     ❌      |    ❌    |   ❌    |   ❌    |
| Custo por usuário                     |   ❌    |     ✅      |    ❌    |   ✅    |   ❌    |
| Open-source (auditável)               |   ✅    |     ❌      |    ✅    |   ❌    |   ✅    |

## Roadmap

O Vectora nasce com foco em desenvolvimento de software — mas a visão é mais ampla.

**Próximos grupos de ferramentas:**

- **Git** — commits, branches, pull requests, code review assistido
- **Office** — documentos, planilhas, apresentações diretamente no fluxo de trabalho
- **Database** — consultas, migrações, análise de dados
- **Communication** — Slack, e-mail, tickets de suporte

**Novos agentes especializados** seguirão cada domínio que o Vectora expandir.

A arquitetura foi desenhada para crescer: adicionar um agente novo é adicionar uma especialidade nova.  
O orquestrador já sabe como delegar. Você só precisa construir quem executa.

## Contato

**Bruno Soares** — bruno.soarxz@gmail.com  
GitHub: [github.com/brunosrz](https://github.com/brunosrz)

_Vectora — Apache 2.0 — Self-hosted. Seus dados. Sua IA._
