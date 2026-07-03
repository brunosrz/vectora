# Fases de desenvolvimento, como chegamos no Vectora?

> Este documento é histórico — registra a trajetória de ideias, decisões e
> descartes até a arquitetura atual. Não é um plano de implementação. O
> conteúdo até "Vectora V3" é a história pessoal por trás do projeto
> (destinada também ao blog pessoal do autor); a seção final ("O Vectora
> hoje") descreve o que existe de fato no repositório agora.

## Zyris Rag - O Conceito Enxuto

Um agent de ia focado em RAG em game engines

Zyris Engine é um fork da Godot criado por mim, ele modifica diretamente o núcleo da engine de forma que não daria pra fazer com plugins / GDExtension, por isso o fork

A ideia com o Zyris Rag não era restrita ao Zyris Engine, ela iria cobrir Godot e Asset Library da comunidade, com os próprios usuários conseguindo publicar seus buckets de dados

Qual a ideia aqui? Bem, usaria uma LLM como Gemini. ChatGPT, Claude ou outra, e por cima dela, incluiria o RAG, serviria justamente para que o usuário selecionasse a versão da engine e das ferramentas que ele tá usando, e isso servir como "treinamento" do modelo, isso pq os buckets teriam conjuntos de gdscript, cenas, markdowns e documentação (XML da Godot)

Porque essa ideia foi rapidamente cancelada? Bem, tinha pouca visão de como realmente desenvolver esse sistema, apesar de ter definido Golang no início, eu ainda não tinha me aprofundado na linguagem

Outro problema era o nome e o nicho, ficaria algo extremamente nichado e reprovado pela própria comunidade, visto que os mantenedores da Godot Engine reprovam o uso de IA, e boa parte dos colaboradores dela também... Teria a chance de criar sua própria comunidade em volta isso, mas extremamente minúscula, ao ponto de não valer a pena

## Vectora v1 - o agent que voou perto demais do Sol

Renomeei Zyris Rag para Vectora, e ampliei seus horizontes, estudei Golang e montei uma stack de respeito, mas tinha um problema nisso tudo, recheado de excessos e um conflito enorme de arquitetura

Arquiteturei tudo em go puro, ou era oq eu pensava...

Bubbletea

Bbolt -> BadgerDB (mudei no meio do caminho)

Chromem Go

Gin

Langchaingo

MCP & ACP (Agent Client Protocol)

Llamacpp - instalação gerenciada e integrada

Mas aqui tem vários perigos que aos poucos eu fui notando...

Primeiro, qual LLM, Embedding e Reranker usar? A princípio qualquer um, não tinha fechado a stack, Vectora era um agent principal, mas extremamente abstrato, ao permitir qualquer IA possível, meu trabalho pra desenvolver o Agentic Framework, Tools e Treinamento aumentou aos montes

Llamacpp gerenciado? Aqui quebrei minhas pernas, quis incluir um installer e um provider só pra ele, invés de fazer como todos fazem, conectar ao http diretamente pela instalação feita pelo próprio usuário

Chromem Go? Extremamente imaturo, principalmente pra ser o nosso produto principal.

Bubbletea e ACP? É realmente tão importante ele ser um Agent principal assim? Tipo, como que eu vou concorrer diretamente com Claude Code, Gemini CLI e Openai Codex? Se fosse uma grande empresa desenvolvendo o Vectora... Mas é open source, em go... E numa realidade onde agents já começaram a saturar, seguir esse caminho seria possível, mas muito mais complicado

## Vectora V2 - Na teoria eu ficaria rico, mas na prática...

Vectora v2 nasceu com um propósito totalmente diferente, nada de banco de dados embarcados, SDKs oficiais no lugar de langchaingo, stack de aí fechada com Gemini & Voyage, somente subagent MCP, sem llamacpp

Na teoria, eu resolvi todos os problemas da versão anterior, e ainda ganhei um SaaS conectando o Desktop com as LM & Data Base, mas na prática, eu estava praticamente pedindo para que ninguém usasse, ou que até mesmo forkasse meu projeto e tirasse a dependência de um cloud não open source...

Voltando um pouco na explicação, nesse ponto do plano separei o Vectora em 5 frentes, um site de documentação feito em Hugo + Hextra, um site de dashboard para você fazer login e ter o controle de gastos e de armazenamento, integrações em Typescript para diversos agents e ide, um app desktop e um backend em nuvem no qual o desktop e as integrações dependessem

Iríamos ter plano gratuito BYOK, plus, pro e team, como o banco de dados seria terceirizado via API, os planos pagos teriam que render com margem para podermos oferecer um gratuito, além do plano pago ter um limite maior para storage, eles iriam contar com créditos de IA para o Gemini & Voyage

Outro benefício dessa abordagem e o real motivo de ter seguido ela, foi saber que a Openai tem o GPT Store, onde por ele eu seria capaz de integrar o Vectora diretamente ao ChatGPT, oq traria muita visibilidade pro projeto

GPT Store precisa de url https fixa, por isso a nescessidade de um Vectora Cloud, que rodaria um Vectora Desktop em docker para os usuários via GPT Store, para demais usuários, não teria nescessidade disso já que cada usuário teria o seu app desktop instalado, logo o desktop em docker seria sobre demanda

Qual o grande problema disso tudo? Bem, primeiro que manter uma aplicação cloud aumentaria os custos de operação, até porque ela não seria open source, segundo que, ela acaba matando até às frentes open source, visto que nenhum outro Dev iria trabalhar de graça nos repositórios open source, sabendo que ele mesmo terá que pagar para usar oq ele fez... Google e Openai, ambas tem seus Agent CLI open source e que dependem de um backend pago, mas tem um porém muito grande, elas são empresas gigantescas, e não estão ali apenas como uma etapa de login + banco de dados, elas estão ali no meio como as próprias desenvolvedoras de suas respectivas LLM's... Não dá pra comparar

Outro problema enorme... Bastaria alguém pegar o projeto opensource, forkar ele, e remover todas as conexões com nosso backend cloud, e trocar pra uma estrutura própria de banco de dados... Ele continuaria com as LLM via BYOK, e poderia ter o armazenamento que quisesse se rodasse o banco de dados localmente, ou então ele mesmo conectaria a um externo, mas teria seu próprio controle de gastos, bem mais barato que o Vectora...

## Vectora V3 - Pé no chão e cabeça erguida

Voltei pra ideia original de ter tudo embarcado, mas fui além, troquei chromemgo por Milvus, BadgerDB por Embed Postgres, dashboard separado para integrado, e assim removi completamente o Cloud e os planos pagos, e fiz mais uma grande mudança...

Durante a V2, estruturei um conjunto excelente de tools, skills, Agentic Framework e Context Engine, mas sentia que faltava algo...

Vectora Cognitive Runtime, nossa própria inteligência artificial neural, não uma LLM, nem Embedding ou Reranker, algo mais simples, uma LM Context Policy

Usar o Gemini como motor do Agentic Framework era estranho e aumentava gastos em um processo que deveria diminuilos, foi daí que surgiu a ideia de termos uma micro inteligência artificial, algo simples mas poderoso, tudo que ela precisa é tomar decisões e adicionar contexto

Pytorch + Transformes, essa é a solução, ao desenvolver do zero uma LM, além de virar de fato um engenheiro de IA, eu agrego algo que nenhum outro concorrente tem, uma IA extremamente leve / pequena que não interage com o usuário, ele tá ali apenas para analisar seu prompt, fazer microsearchs no projeto e na memória, adicionar a chamada de uma tool, e entregar a sua query original + a complementação feita pelo VCR ao Gemini e Voyage

Oq isso significa?

Significa que o Vectora finalmente encontrou sua identidade real.

Não somos uma LLM. Não somos um provider. Não somos um clone de Claude Code. Não somos uma wrapper de API. Não somos um simples agent framework.

O Vectora é um sistema cognitivo contextual.

A grande virada de chave da V3 foi entender que o problema principal nunca foi "qual LLM usar", e sim "como preparar a informação correta antes da LLM agir".

Claude, Gemini, GPT e qualquer outro modelo já são extremamente bons em raciocínio e geração de resposta, o problema é que eles trabalham cegos, dependem de contexto manual, prompts enormes, usuários extremamente específicos, e pipelines gigantescos de RAG tentando compensar isso.

O VCR muda completamente esse fluxo.

Ao invés da LLM receber apenas:

"erro de GHA do Vectora, teste vec203 falhou"

Ela passa a receber:

prompt original

workflows relacionados

arquivos relevantes

testes relacionados

memória contextual

informações do projeto

decisões de tools

sinais de retrieval

hints semânticos

expansão contextual da query

Tudo isso antes mesmo da LLM começar a raciocinar.

E o mais importante:

isso acontece localmente.

O VCR não substitui o Gemini. Não substitui o Voyage. Não substitui embeddings. Não substitui rerankers.

Ele orquestra tudo.

A ideia nunca foi competir diretamente com frontier models. A ideia é reduzir a cegueira delas.

Enquanto outros agents dependem de prompts gigantescos, chains enormes, dezenas de chamadas desnecessárias e context windows absurdas, o Vectora tenta resolver o problema antes.

O VCR funciona como uma camada cognitiva intermediária.

Usuário -> VCR -> LLM.

Mas diferente de um simples middleware, o VCR entende semanticamente o ambiente.

Ele sabe que:

GHA == GitHub Actions

workflow == pipeline

vec203 provavelmente é um teste

compile failed provavelmente envolve build pipeline

arquivos em .github/workflows são relevantes

logs recentes possuem prioridade

memória de debugging anterior pode importar

Isso reduz drasticamente:

custo

latência

contexto inútil

hallucination

retrieval desnecessário

chamadas redundantes

E o mais importante:

faz o Vectora deixar de ser dependente exclusivamente da inteligência de terceiros.

A LLM continua sendo terceirizada. Mas a cognição contextual passa a ser nossa.

Isso muda completamente o valor do projeto.

Porque o diferencial deixa de ser:

"qual modelo usamos"

E passa a ser:

"como pensamos antes de usar o modelo"

Essa foi a primeira vez que o Vectora deixou de parecer apenas mais um agent open source e começou a parecer uma arquitetura realmente própria.

O VCR também resolve outro problema enorme das versões anteriores:

determinismo.

Nas V1 e V2, praticamente toda a inteligência dependia diretamente do comportamento da LLM principal.

Isso tornava:

debugging extremamente difícil

resultados inconsistentes

pipelines frágeis

custos imprevisíveis

comportamento pouco observável

Com o VCR, as decisões passam a ser estruturadas.

Antes da LLM agir, já existe:

uma strategy

retrieval targets

tool planning

memory resolution

confidence score

recovery policy

Isso transforma o Vectora em algo muito mais próximo de um runtime cognitivo do que de um simples chatbot agent.

E isso também muda a relação do projeto com open source.

Nas versões anteriores, praticamente tudo poderia ser recriado facilmente por forks:

trocar provider

trocar banco

trocar cloud

trocar embedding

remover SaaS

Agora existe algo realmente difícil de replicar:

o comportamento cognitivo do sistema.

Porque o valor passa a estar:

nos datasets

nos traces

nas decisões

na policy

na arquitetura contextual

no treinamento do VCR

E não apenas em conectar APIs.

O mais importante de tudo:

o Vectora finalmente volta a fazer sentido como projeto local-first.

Sem cloud obrigatória. Sem login obrigatório. Sem backend proprietário. Sem vendor lock-in. Sem depender de infraestrutura paga para existir.

Tudo roda localmente.

A única dependência externa opcional continua sendo a própria LLM escolhida pelo usuário.

E até isso, no futuro, pode ser substituído parcialmente.

Porque o VCR abre portas enormes:

memory policies

adaptive retrieval

semantic routing

tool prediction

autonomous context planning

self-improving traces

contextual learning

local reasoning pipelines

O Vectora deixa de ser apenas um agent.

E começa a virar um sistema operacional cognitivo para IA contextual.

## O Vectora hoje

A V3 acertou o essencial — local-first, sem cloud obrigatória, sem vendor
lock-in — mas o VCR (a micro-LM neural treinada do zero) não foi adiante.
Treinar e manter um modelo próprio é um projeto de pesquisa em si, com custo
de dados, treinamento e manutenção que competia com o tempo de construir o
produto de verdade. Essa peça foi cortada, junto com Milvus/Embed Postgres
como backend obrigatório e a ideia de um "agent principal" concorrendo
frontalmente com Claude Code/Gemini CLI/Codex.

O que ficou, e o que existe hoje no repositório:

- **Arquitetura**: `create_deep_agent` (LangGraph + deepagents), não mais um
  orchestrator manual por nós nem uma LM própria fazendo roteamento. Tools,
  subagents (coder, search), middleware HITL (`HumanInTheLoopMiddleware`) e
  `context_schema` — o "pensar antes de usar o modelo" da V3 virou engenharia
  de contexto (tools de fs/git/web/rag, skills por harness, memória via
  Redis/SQLite) em vez de uma rede neural própria.
- **Storage**: dois modos, não um banco obrigatório. `lite` (SQLite +
  LanceDB, default, zero infra) e `complete` (Postgres + Qdrant + Redis, para
  quem já tem infra). Usuários/auth/settings sempre em SQLite, local,
  independente do modo.
- **Desktop + backend são uma moeda só**: o backend Python sempre roda; o
  frontend React pode estar visível (janela Electron) ou oculto
  (headless/bandeja). IPC via named pipe/unix socket, nunca TCP — web/VPS é a
  única superfície TCP, por design.
- **MCP sempre-ativo**: montado no mesmo processo FastAPI (`/mcp`), não um
  processo stdio separado.
- **Free/Pro, sem SaaS obrigatório**: Free é 100% local, sem conta. Pro é
  opcional, cobre trial/billing/licenciamento — servido por
  `services.vectora.company` (Cloudflare Worker próprio, substituiu Supabase),
  não um "Vectora Cloud" rodando o desktop de terceiros em Docker. O GPT
  Store e o Vectora-Desktop-em-Docker-sob-demanda da V2 foram abandonados
  junto com a ideia de cloud obrigatória.
- **`services/`**: unifica o antigo relay (OAuth/webhooks do desktop) +
  update-server (distribuição de releases) + auth/billing/license/GDPR/
  api-keys/issues da company (que antes dependiam do Supabase). Sem RLS —
  autorização é código, em cada handler.
- **A única ideia de roadmap da V2/V3 que sobrevive**: a biblioteca de RAG
  pré-indexado (o "Zyris Rag" original de buckets de dados publicáveis pela
  comunidade, depois "RAG library" na V2/V3) — hoje existe como placeholder
  mínimo em `services/src/rag-library/` (catálogo + download), sob um nome
  ainda a definir (não será "RAG library" nem "buckets" — nome final em
  aberto). Continua fora do escopo de curto prazo: só entra em
  desenvolvimento depois do lançamento do Vectora.

Não somos mais um agent tentando ser o "quinto grande CLI". Somos um
produto local-first com engenharia de contexto embarcada, um backend próprio
pequeno só para o que realmente precisa de servidor (licença, pagamento,
distribuição de releases), e nada além disso.
