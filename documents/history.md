---
title: "Como eu criei o Vectora"
date: "2026-07-03T09:00:00-03:00"
slug: como-criei-o-vectora
tags:
  - infra
  - python
  - golang
  - ia
  - rag
  - llm
  - startup
  - arquitetura
draft: false
---

> Este post registra a trajetória de ideias, decisões e descartes até a
> arquitetura atual do Vectora. Não é um plano de implementação nem
> documentação técnica — é a história pessoal por trás do projeto. A última
> seção, "O Vectora hoje", fecha com o que existe de fato hoje.

## Zyris Rag — o conceito enxuto

Um agente de IA focado em RAG dentro de game engines.

O Zyris Engine era um fork da Godot que eu mantinha, modificando o núcleo da
engine de um jeito que não daria para fazer só com plugins ou GDExtension —
daí o fork.

A ideia do Zyris Rag não era restrita ao Zyris Engine: cobriria a Godot e a
Asset Library da comunidade, com os próprios usuários publicando seus
buckets de dados.

A proposta era simples na cabeça: usar uma LLM como Gemini, ChatGPT, Claude
ou outra, e por cima dela um RAG que deixasse o usuário selecionar a versão
da engine e das ferramentas que estava usando. Isso serviria como
"treinamento" do modelo, já que os buckets teriam conjuntos de GDScript,
cenas, markdowns e a documentação em XML da própria Godot.

Por que a ideia foi cancelada rápido?

- Eu tinha pouca visão de como desenvolver esse sistema de verdade. Tinha
  decidido usar Go desde o início, mas ainda não tinha me aprofundado na
  linguagem.
- O nome e o nicho eram um problema à parte: ficaria extremamente nichado e
  mal recebido pela própria comunidade — os mantenedores da Godot Engine
  reprovam o uso de IA, e boa parte dos colaboradores também. Daria para
  construir uma comunidade em volta disso, mas minúscula a ponto de não
  valer a pena.

## Vectora V1 — o agente que voou perto demais do Sol

Renomeei Zyris Rag para Vectora e ampliei os horizontes. Estudei Go a sério
e montei uma stack de respeito — mas com um problema recorrente: excesso, e
um conflito enorme de arquitetura.

Arquiteturei tudo em Go puro. Ou era o que eu achava:

- **Bubbletea**
- **Bbolt → BadgerDB** (troquei no meio do caminho)
- **Chromem-Go**
- **Gin**
- **Langchaingo**
- **MCP & ACP** (Agent Client Protocol)
- **Llama.cpp** com instalação gerenciada e integrada

Os perigos foram aparecendo aos poucos:

**Qual LLM, embedding e reranker usar?** A princípio, qualquer um — eu não
tinha fechado a stack. O Vectora era um agente principal, mas extremamente
abstrato, permitindo qualquer IA possível. Isso multiplicou o trabalho de
construir o framework agêntico, as tools e o treinamento.

**Llama.cpp gerenciado?** Aqui quebrei as pernas: quis incluir um installer
e um provider só para ele, em vez de fazer como todo mundo faz — conectar
direto via HTTP a uma instalação que o próprio usuário já tem.

**Chromem-Go?** Extremamente imaturo para ser o banco vetorial do produto
principal.

**Bubbletea e ACP?** Fazia sentido o Vectora ser um agente principal
competindo diretamente com Claude Code, Gemini CLI e o Codex da OpenAI? Se
fosse uma empresa grande por trás, talvez. Mas era open source, em Go, numa
realidade em que os agentes de código já começavam a saturar o mercado.
Dava para seguir por esse caminho, mas seria bem mais difícil do que
parecia.

## Vectora V2 — na teoria eu ficaria rico, mas na prática...

O Vectora V2 nasceu com um propósito totalmente diferente: nada de bancos de
dados embarcados, SDKs oficiais no lugar do Langchaingo, stack fechada em
Gemini & Voyage, e um subagente MCP no lugar do Llama.cpp.

Na teoria eu tinha resolvido todos os problemas da versão anterior — e ainda
ganhei um SaaS conectando o desktop às LLMs e ao banco de dados. Na prática,
eu estava pedindo, na cara dura, para que ninguém usasse o produto — ou pior,
para que fizessem fork do projeto só para tirar a dependência de uma nuvem
que não era open source.

Voltando um pouco: nesse ponto do plano, separei o Vectora em cinco frentes:

1. Um site de documentação em Hugo + Hextra.
2. Um dashboard para login, controle de gastos e de armazenamento.
3. Integrações em TypeScript para diversos agentes e IDEs.
4. Um app desktop.
5. Um backend em nuvem do qual o desktop e as integrações dependiam.

Os planos seriam Free (BYOK), Plus, Pro e Team. Como o banco de dados seria
terceirizado via API, os planos pagos precisavam de margem para bancar um
tier gratuito, além de terem limite maior de storage e créditos de IA para
Gemini & Voyage.

O verdadeiro motivo por trás dessa arquitetura toda: a OpenAI tem a GPT
Store, e por ela eu conseguiria integrar o Vectora diretamente ao ChatGPT —
o que traria muita visibilidade para o projeto.

A GPT Store exige uma URL HTTPS fixa, daí a necessidade de um "Vectora
Cloud" rodando um Vectora Desktop em Docker para os usuários vindos da GPT
Store. Para os demais usuários isso não seria necessário, já que cada um
teria seu próprio app desktop instalado — o desktop em Docker seria
estritamente sob demanda.

Qual era o grande problema disso tudo?

- Manter uma aplicação em nuvem aumentaria os custos de operação, ainda mais
  não sendo open source.
- Isso matava a própria frente open source do projeto: nenhum outro
  desenvolvedor trabalharia de graça em um repositório sabendo que teria que
  pagar para usar o que ele mesmo ajudou a construir. Google e OpenAI têm
  seus Agent CLIs open source dependendo de um backend pago, mas são
  empresas gigantes que estão ali como as próprias desenvolvedoras das LLMs
  — não como um simples meio de login + banco de dados. Não dá para
  comparar.
- Bastaria alguém pegar o projeto open source, dar fork, remover todas as
  conexões com o backend em nuvem e trocar por uma estrutura própria de
  banco de dados. Continuaria funcionando via BYOK, com armazenamento local
  ou externo à escolha do usuário — e um controle de gastos bem mais barato
  que o do próprio Vectora.

## Vectora V3 — pé no chão e cabeça erguida

Voltei para a ideia original de ter tudo embarcado, e fui além: troquei
Chromem-Go por Milvus, BadgerDB por Postgres embarcado, e um dashboard
separado por um integrado. Removi completamente o Cloud e os planos pagos —
e fiz mais uma grande mudança.

Durante a V2 eu tinha estruturado um conjunto excelente de tools, skills,
framework agêntico e context engine, mas sentia que faltava algo: o **VCR —
Vectora Cognitive Runtime**. Não uma LLM, nem um embedding ou reranker. Algo
mais simples: uma LM de context policy, nossa própria inteligência artificial
neural.

Usar o Gemini como motor do framework agêntico era estranho, e aumentava
gastos justamente num processo que deveria reduzi-los. Daí a ideia de uma
micro inteligência artificial — simples, mas poderosa — cujo único trabalho
seria tomar decisões e adicionar contexto.

PyTorch + Transformers: essa seria a solução. Ao desenvolver uma LM do zero
eu não só viraria, de fato, um engenheiro de IA, como agregaria algo que
nenhum concorrente tinha — uma IA extremamente leve, que não interage com o
usuário, e cujo único papel é analisar o prompt, fazer microbuscas no
projeto e na memória, decidir a chamada de uma tool, e entregar a query
original mais a complementação feita pelo VCR ao Gemini e ao Voyage.

O que isso significava? Que o Vectora finalmente tinha encontrado sua
identidade real.

Não somos uma LLM. Não somos um provider. Não somos um clone do Claude Code.
Não somos um wrapper de API. Não somos um simples framework de agentes.

**O Vectora é um sistema cognitivo contextual.**

A grande virada de chave da V3 foi entender que o problema principal nunca
foi "qual LLM usar", e sim "como preparar a informação certa antes da LLM
agir". Claude, Gemini, GPT e qualquer outro modelo já são extremamente bons
em raciocínio e geração de resposta — o problema é que eles trabalham cegos,
dependendo de contexto manual, prompts enormes, usuários extremamente
específicos, e pipelines gigantescos de RAG tentando compensar isso.

O VCR mudava completamente esse fluxo. Em vez da LLM receber só:

> "erro de GHA do Vectora, teste vec203 falhou"

ela passaria a receber prompt original, workflows relacionados, arquivos
relevantes, testes relacionados, memória contextual, informações do
projeto, decisões de tools, sinais de retrieval, hints semânticos e a
expansão contextual da query — tudo isso antes mesmo da LLM começar a
raciocinar. E o mais importante: isso aconteceria localmente.

O VCR não substituiria o Gemini, nem o Voyage, nem embeddings, nem
rerankers. Ele orquestraria tudo. A ideia nunca foi competir diretamente com
frontier models, e sim reduzir a cegueira delas.

Enquanto outros agentes dependem de prompts gigantescos, chains enormes,
dezenas de chamadas desnecessárias e context windows absurdas, o Vectora
tentaria resolver o problema antes — com o VCR funcionando como uma camada
cognitiva intermediária:

```
Usuário → VCR → LLM
```

Mas diferente de um simples middleware, o VCR entenderia semanticamente o
ambiente. Ele saberia que GHA é GitHub Actions, que workflow é pipeline, que
`vec203` provavelmente é um teste, que "compile failed" provavelmente
envolve o build pipeline, que arquivos em `.github/workflows` são
relevantes, que logs recentes têm prioridade, e que memória de debugging
anterior pode importar.

Isso reduziria drasticamente custo, latência, contexto inútil, alucinação,
retrieval desnecessário e chamadas redundantes. E o mais importante: faria
o Vectora deixar de depender exclusivamente da inteligência de terceiros. A
LLM continuaria terceirizada — mas a cognição contextual passaria a ser
nossa.

Isso mudava completamente o valor do projeto, porque o diferencial deixava
de ser "qual modelo usamos" e passava a ser "como pensamos antes de usar o
modelo". Foi a primeira vez que o Vectora deixou de parecer apenas mais um
agente open source e começou a parecer uma arquitetura realmente própria.

O VCR também resolveria outro problema grande das versões anteriores:
**determinismo**. Nas V1 e V2, praticamente toda a inteligência dependia
diretamente do comportamento da LLM principal, o que tornava o debugging
extremamente difícil, os resultados inconsistentes, os pipelines frágeis, os
custos imprevisíveis e o comportamento pouco observável.

Com o VCR, as decisões passariam a ser estruturadas: antes da LLM agir, já
existiria uma strategy, retrieval targets, tool planning, memory
resolution, confidence score e recovery policy. Isso transformaria o
Vectora em algo muito mais próximo de um runtime cognitivo do que de um
simples chatbot agent.

E isso mudaria a relação do projeto com open source. Nas versões
anteriores, praticamente tudo podia ser recriado facilmente por forks —
trocar provider, trocar banco, trocar cloud, trocar embedding, remover o
SaaS. Com o VCR existiria algo realmente difícil de replicar: o
comportamento cognitivo do sistema. O valor passaria a estar nos datasets,
nos traces, nas decisões, na policy, na arquitetura contextual e no
treinamento do VCR — não apenas em conectar APIs.

O mais importante de tudo: o Vectora finalmente voltaria a fazer sentido
como projeto local-first. Sem cloud obrigatória, sem login obrigatório, sem
backend proprietário, sem vendor lock-in, sem depender de infraestrutura
paga para existir. Tudo rodando localmente, com a única dependência externa
opcional sendo a própria LLM escolhida pelo usuário — e mesmo essa,
futuramente, poderia ser substituída em parte, porque o VCR abriria portas
para memory policies, adaptive retrieval, semantic routing, tool
prediction, autonomous context planning, self-improving traces, contextual
learning e local reasoning pipelines.

O Vectora deixaria de ser apenas um agente, e passaria a virar um sistema
operacional cognitivo para IA contextual.

## O Vectora hoje

A V3 acertou o essencial — local-first, sem cloud obrigatória, sem vendor
lock-in — mas o VCR (a micro-LM neural treinada do zero) não foi adiante.
Treinar e manter um modelo próprio é um projeto de pesquisa em si, com custo
de dados, treinamento e manutenção que competia com o tempo de construir o
produto de verdade. Essa peça foi cortada, junto com Milvus/Postgres
embarcado como backend obrigatório e a ideia de um "agente principal"
concorrendo de frente com Claude Code, Gemini CLI e Codex.

O que ficou, e o que existe hoje no repositório:

- **Arquitetura.** Motor de conversa nativo (`backend/engine/
conversation_loop.py::run_conversation`, loop `while` imperativo) — passou
  por `create_deep_agent` (LangGraph + deepagents) no meio do caminho, mas
  isso também foi substituído por engenharia própria, sem depender de
  orchestrator manual por nós nem de uma LM própria fazendo roteamento.
  Tools resolvidas via `TOOL_REGISTRY`, subagents (coder, search) via
  `backend/engine/subagents.py`, HITL via `should_require_approval`
  (`backend/engine/hitl.py`) — o "pensar antes de usar o modelo" da V3 virou
  engenharia de contexto (tools de fs/git/web/rag, skills por harness,
  memória via Redis/SQLite) em vez de uma rede neural própria.
- **Storage.** Dois modos, não um banco obrigatório: `lite` (SQLite +
  LanceDB, default, zero infra) e `complete` (Postgres + Qdrant + Redis,
  para quem já tem infra). Usuários, auth e settings sempre em SQLite,
  local, independente do modo.
- **Desktop + backend são uma moeda só.** O backend Python sempre roda; o
  frontend React pode estar visível (janela Electron) ou oculto
  (headless/bandeja). IPC via named pipe/unix socket, nunca TCP — web/VPS é
  a única superfície TCP, por design.
- **MCP é client, não server.** O servidor MCP embutido (`/mcp`, montado
  no mesmo processo FastAPI, invocável por Claude Desktop e outros
  harnesses) foi removido — sem autenticação real e com risco de
  canibalização (assinar Pro só pra usar o RAG via outro harness, sem
  nunca abrir o resto do workspace). O Vectora só **consome** servidores
  MCP externos (`backend/tools/mcp.py`, marketplace de conectores).
- **Sem API pública.** A API REST `/v1` (extract/classify/jobs) chegou a
  existir e foi removida antes do lançamento — sem autenticação de
  terceiros real, sem SDKs, sem tração. Visão OEM de longo prazo, não
  fundação técnica atual.
- **Free/Pro, sem SaaS obrigatório.** Free é 100% local, sem conta. Pro é
  opcional, cobre trial/billing/licenciamento — servido por
  `services.vectora.company` (um Worker Cloudflare próprio, que substituiu o
  Supabase), não um "Vectora Cloud" rodando o desktop de terceiros em
  Docker. A GPT Store e o Vectora Desktop em Docker sob demanda da V2 foram
  abandonados junto com a ideia de cloud obrigatória.
- **`services/`.** Unifica o antigo relay — renomeado para `gateway` em
  2026-07-20, rename limpo sem período de transição — (OAuth/webhooks do
  desktop) + o
  update-server (distribuição de releases) + auth/billing/license/GDPR/
  api-keys/issues da company (que antes dependiam do Supabase). Sem RLS —
  autorização é código, em cada handler.
- **A única ideia de roadmap da V2/V3 que sobrevive:** a biblioteca de RAG
  pré-indexado — o "Zyris Rag" original de buckets de dados publicáveis pela
  comunidade, depois "RAG library" na V2/V3 — hoje existe como placeholder
  mínimo em `services/src/rag-library/` (catálogo + download), sob um nome
  ainda a definir. Continua fora do escopo de curto prazo: só entra em
  desenvolvimento depois do lançamento do Vectora.

Não somos mais um agente tentando ser o "quinto grande CLI". Somos um
produto local-first com engenharia de contexto embarcada, um backend
próprio pequeno só para o que realmente precisa de servidor — licença,
pagamento, distribuição de releases — e nada além disso.
