# reimagined-agents — visão de uma lib open source pra substituir LangChain/LangGraph/deepagents

> **Estágio: ideia registrada, não iniciada.** Este documento existe pra guardar a
> visão e o raciocínio por trás dela — nenhuma linha de código desta lib existe
> ainda, e não deve existir até essa decisão ser retomada explicitamente. Planejamento
> mora em markdown, implementação mora em código (CLAUDE.md §9) — este arquivo é
> intencionalmente o primeiro, não o segundo.

## O que é

`reimagined-agents` é o nome de código de uma futura biblioteca Python **open source**,
publicável fora do Vectora, que substituiria de uma vez três dependências hoje
centrais ao núcleo agêntico do produto — **deepagents**, **LangChain** e **LangGraph**
— e todos os conectores que vêm coladas a elas:

- **Conectores de storage** — os wrappers que hoje acoplam checkpointing/state/vector
  store/cache a essas libs (`AsyncSqliteSaver`/`AsyncPostgresSaver`,
  `AsyncSqliteStore`/`AsyncPostgresStore` do LangGraph; `langchain_qdrant`,
  `langchain_redis`, `langchain_community.vectorstores` etc.). A Sprint 12 do plano de
  desenvolvimento do Vectora (`C:\Users\Machi\.claude\plans\iterative-bouncing-treehouse.md`)
  já ataca a metade dessa frente — troca esses conectores por clientes nativos das
  próprias libs de storage, mas **mantendo** LangChain/LangGraph/deepagents como
  camada agêntica. `reimagined-agents` é o que vem depois: a camada agêntica em si
  deixa de existir como dependência externa.
- **Conectores de provider de modelo** — as integrações hoje feitas via
  `langchain-openai`, `langchain-anthropic`, `langchain-google-genai` e equivalentes
  (Google, Anthropic, OpenAI, e os demais providers que o Vectora já suporta via
  roteamento). Isso inclui tudo que hoje passa pela abstração `BaseChatModel` do
  LangChain — streaming, tool-calling, contagem de uso/custo.

O motor resultante seria usado pelo próprio Vectora (fonte primária de validação — "dogfooding" real, não uma lib feita no vácuo) mas desenhado desde o início pra funcionar como
peça independente, publicável e reutilizável por qualquer outro projeto Python que
precise de um motor de agente sem a superfície pesada do LangChain/LangGraph.

## Por que

Motivação registrada nesta sessão de planejamento, no contexto da Sprint 11/12 do
Vectora:

- LangChain, na experiência real de operar o Vectora em produção, já se mostrou um
  framework frágil pros propósitos do produto — bugs conhecidos e não reportados
  anteriormente em `astream`/streaming (o mesmo tipo de bug real que motivou a
  migração nativa de OpenRouter/Ollama/Tavily documentada em
  `rustling-hatching-summit.md`, incluindo um caso onde `delta.tool_calls` era
  descartado silenciosamente em produção por várias revisões seguidas antes de ser
  pego). Não é uma opinião abstrata sobre o framework — é um histórico concreto de
  incidentes.
- Já existe precedente de sucesso real dentro do próprio Vectora fazendo exatamente
  esse tipo de troca em escopo menor: OpenRouter, Ollama e Tavily saíram de
  integrações via LangChain pra clientes HTTP nativos, mantendo a interface que o
  resto do sistema já esperava — sem regressão de comportamento, com testes de
  paridade cobrindo a troca.
- O Hermes Agent (`C:\Users\Machi\AppData\Local\hermes\hermes-agent`) é prova viva de
  que dá pra construir um agente de produção inteiro — loop de conversa, adapters por
  provider (Anthropic, Gemini, Bedrock, Azure, Vertex, Codex/Responses), persistência,
  delegação — sem depender de LangChain/LangGraph em nenhum ponto. Não é um
  experimento pequeno: é um agente real, em uso, com ~7000 linhas só no loop de
  conversa.

## O que NÃO é (por enquanto)

- Não é uma decisão de que o Vectora vai migrar pra essa lib em breve. A Sprint 13 do
  plano atual (migração do núcleo agêntico pra fora de LangChain/LangGraph/deepagents,
  ainda não iniciada) é sobre o Vectora ficar **nativo por si só** — não
  necessariamente sobre construir uma lib publicável nova no meio do caminho. Se
  `reimagined-agents` acabar nascendo como extração natural desse trabalho (a mesma
  lógica que a Sprint 13 escrever pro Vectora virando uma lib de propósito geral),
  ótimo — mas isso é uma decisão a ser tomada quando a Sprint 13 já estiver
  concluída e o padrão nativo já estiver validado em produção, não antes.
- Não tem escopo técnico definido ainda — nenhuma API, nenhuma escolha de nome de
  módulo, nenhuma decisão de "vai ter checkpointer plugável" ou "vai ter grafo de
  execução declarativo". Definir isso agora seria projetar pra um requisito
  hipotético antes de ter o requisito real (a própria Sprint 13, que ainda nem
  começou) — exatamente o tipo de over-engineering que este projeto evita por
  princípio.
- Não tem cronograma. Fica registrada como visão até o momento em que fizer sentido
  revisitar — provavelmente só depois da Sprint 13 estar madura em produção.

## Abordagem de desenvolvimento (quando essa lib for de fato construída)

Já decidido, mesmo sem escopo técnico definido: o método de construção não vai ser
"escrever do zero olhando pra documentação". Vai ser **engenharia reversa direta**,
com três fontes comparadas lado a lado:

1. **Código-fonte real do LangChain/LangGraph/deepagents** — não a documentação
   pública, o código em si (do jeito que a investigação da Sprint 12 já fez pra
   mapear os touchpoints de storage: ler `deepagents/graph.py`,
   `langgraph.checkpoint.*`, etc. diretamente). Serve de base de comparação pra saber
   exatamente o que está sendo substituído e por quê — e pra não perder nenhuma
   funcionalidade real usada pelo Vectora no processo.
2. **Hermes Agent** (`C:\Users\Machi\AppData\Local\hermes\hermes-agent`) — referência
   de implementação nativa já validada em produção, usada como precedente de "como
   fazer isso sem framework" em cada peça equivalente (adapters por provider, loop de
   conversa, persistência de sessão).
3. **O próprio Vectora** — pós-Sprint-13, como segunda referência de implementação
   nativa real (paralela ao Hermes, não substituta dela), já adaptada às
   necessidades específicas de um workspace multi-superfície (o que o Hermes, sendo
   mais próximo de um CLI/TUI, não precisa resolver da mesma forma).

A prática concreta, quando a hora chegar: pegar o código-fonte real de cada peça do
LangChain/LangGraph/deepagents que está sendo substituída, usar como referência de
design (partindo do que já existe, não de uma reimplementação ingênua do zero),
e reconstruir/reimaginar essa peça comparando ativamente contra o que o Hermes e o
Vectora nativo já fazem de equivalente — daí o nome "reimagined-agents": não é um
clone do LangChain, é uma reconstrução informada por três fontes reais (a lib
original, e as duas implementações nativas já provadas em produção).

## Ver também

- `C:\Users\Machi\.claude\plans\iterative-bouncing-treehouse.md` — Sprint 12 (storage
  nativo, em andamento) e a nota ao fim da Sprint 11 sobre a Sprint 13 (migração do
  núcleo agêntico), que é o passo real que precisa acontecer antes de qualquer
  decisão concreta sobre esta lib.
- `C:\Users\Machi\.claude\plans\rustling-hatching-summit.md` — precedente de migração
  nativa dentro do próprio Vectora (OpenRouter/Ollama/Tavily), incluindo as
  armadilhas reais encontradas (streaming, formatos de resposta assimétricos, bugs
  silenciosos só descobertos em auditoria posterior) que qualquer trabalho futuro
  nesta linha precisa levar em conta.
