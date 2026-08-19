# reimagined-agents — visão de extrair o motor nativo do Vectora numa lib open source

> **Estágio: ideia registrada, não iniciada.** Este documento existe pra guardar a
> visão e o raciocínio por trás dela — nenhuma linha de código desta lib existe
> ainda, e não deve existir até essa decisão ser retomada explicitamente. Planejamento
> mora em markdown, implementação mora em código (CLAUDE.md §9) — este arquivo é
> intencionalmente o primeiro, não o segundo.
>
> **Atualização:** a migração do núcleo agêntico do Vectora pra fora de
> LangChain/LangGraph/deepagents (que este documento tratava como pré-requisito ainda
> não iniciado) **já aconteceu** — o backend roda hoje 100% sobre o motor nativo
> (`backend/engine/conversation_loop.py::run_conversation`, `ChatClient` Protocol,
> `TOOL_REGISTRY`, `SessionStore`, `backend/persistence/telemetry.py`). Isso não
> aconteceu construindo `reimagined-agents` como lib publicável — foi reescrita
> direta dentro do próprio Vectora. O que resta desta visão é só a pergunta seguinte:
> extrair esse motor nativo já validado em produção numa lib Python separada,
> publicável e reutilizável por outros projetos. O resto deste documento fica como
> registro histórico do raciocínio original, com os tempos verbais ajustados.

## O que é

`reimagined-agents` é o nome de código de uma futura biblioteca Python **open source**,
publicável fora do Vectora, que extrairia o motor agêntico nativo que hoje já
substituiu três dependências que antes eram centrais ao núcleo agêntico do produto —
**deepagents**, **LangChain** e **LangGraph** — e todos os conectores que vinham
colados a elas:

- **Conectores de storage** — os wrappers que antes acoplavam checkpointing/state/
  vector store/cache a essas libs (`AsyncSqliteSaver`/`AsyncPostgresSaver`,
  `AsyncSqliteStore`/`AsyncPostgresStore` do LangGraph; `langchain_qdrant`,
  `langchain_redis`, `langchain_community.vectorstores` etc.) já saíram por clientes
  nativos das próprias libs de storage (`backend/storage/`, `backend/persistence/`).
- **Conectores de provider de modelo** — as integrações que antes eram feitas via
  `langchain-openai`, `langchain-anthropic`, `langchain-google-genai` e equivalentes
  (Google, Anthropic, OpenAI, e os demais providers que o Vectora suporta via
  roteamento) já saíram pelo Protocol `ChatClient` nativo (`backend/llm/base.py`) —
  streaming, tool-calling, contagem de uso/custo, tudo sem a abstração
  `BaseChatModel` do LangChain.

O motor resultante já é usado pelo próprio Vectora em produção (fonte primária de
validação — "dogfooding" real, não uma lib feita no vácuo). A pergunta em aberto é
se vale a pena desenhá-lo — retroativamente — como peça independente, publicável e
reutilizável por qualquer outro projeto Python que precise de um motor de agente sem
a superfície pesada do LangChain/LangGraph.

## Por que (motivação original, ainda válida)

Motivação registrada na sessão de planejamento que precedeu a migração:

- LangChain, na experiência real de operar o Vectora em produção, se mostrou um
  framework frágil pros propósitos do produto — bugs conhecidos e não reportados
  em `astream`/streaming (o mesmo tipo de bug real que motivou a migração nativa
  de OpenRouter/Ollama/Tavily documentada em `rustling-hatching-summit.md`,
  incluindo um caso onde `delta.tool_calls` era descartado silenciosamente em
  produção por várias revisões seguidas antes de ser pego). Não foi uma opinião
  abstrata sobre o framework — foi um histórico concreto de incidentes.
- Já havia precedente de sucesso real dentro do próprio Vectora fazendo exatamente
  esse tipo de troca em escopo menor: OpenRouter, Ollama e Tavily saíram de
  integrações via LangChain pra clientes HTTP nativos, mantendo a interface que o
  resto do sistema já esperava — sem regressão de comportamento, com testes de
  paridade cobrindo a troca. Esse precedente se confirmou depois na migração
  completa do núcleo agêntico.
- O Hermes Agent (`C:\Users\Machi\AppData\Local\hermes\hermes-agent`) foi prova viva
  de que dá pra construir um agente de produção inteiro — loop de conversa, adapters
  por provider (Anthropic, Gemini, Bedrock, Azure, Vertex, Codex/Responses),
  persistência, delegação — sem depender de LangChain/LangGraph em nenhum ponto. Não
  era um experimento pequeno: é um agente real, em uso, com ~7000 linhas só no loop
  de conversa — e serviu de referência direta pro `run_conversation` nativo do
  Vectora.

## O que NÃO é (por enquanto)

- Não é uma decisão de que o Vectora vai migrar pra essa lib em breve. A migração do
  núcleo agêntico pra fora de LangChain/LangGraph/deepagents **já está concluída** —
  o Vectora já é **nativo por si só**. O que falta decidir é só se
  `reimagined-agents` nasce como extração desse trabalho já pronto numa lib de
  propósito geral — isso é uma decisão a ser tomada agora que o padrão nativo já
  está validado em produção, não antes (condição que antes bloqueava a discussão).
- Não tem escopo técnico definido ainda — nenhuma API, nenhuma escolha de nome de
  módulo, nenhuma decisão de "vai ter checkpointer plugável" ou "vai ter grafo de
  execução declarativo" pra fora do Vectora. Definir isso sem uma decisão explícita
  de extrair seria over-engineering — o motor nativo já existe e funciona dentro do
  Vectora; o trabalho de extração é o que ainda não foi escopado.
- Não tem cronograma. Fica registrada como visão até o momento em que fizer sentido
  revisitar.

## Abordagem de desenvolvimento (quando essa lib for de fato construída)

Já decidido, mesmo sem escopo técnico definido: o método de extração não vai ser
"escrever do zero olhando pra documentação de outra lib". Vai ser **generalização
direta do motor nativo já em produção**, comparado lado a lado com duas referências:

1. **Código-fonte do LangChain/LangGraph/deepagents que já foi substituído** — não a
   documentação pública, o código em si, do jeito que a investigação que precedeu a
   migração já fez pra mapear os touchpoints de storage (`deepagents/graph.py`,
   `langgraph.checkpoint.*`, etc. lidos diretamente). Serve de base de comparação pra
   documentar exatamente o que foi substituído e por quê — e pra garantir que nenhuma
   funcionalidade real usada pelo Vectora ficou pra trás na extração.
2. **Hermes Agent** (`C:\Users\Machi\AppData\Local\hermes\hermes-agent`) — referência
   de implementação nativa já validada em produção, usada como precedente de "como
   fazer isso sem framework" em cada peça equivalente (adapters por provider, loop de
   conversa, persistência de sessão).
3. **O próprio Vectora** — o motor nativo já em produção (`backend/engine/`), como
   segunda referência de implementação nativa real (paralela ao Hermes, não
   substituta dela), já adaptada às necessidades específicas de um workspace
   multi-superfície (o que o Hermes, sendo mais próximo de um CLI/TUI, não precisa
   resolver da mesma forma).

A prática concreta, quando a hora chegar: pegar o código-fonte real de cada peça do
LangChain/LangGraph/deepagents que foi substituída, usar como referência de design
(partindo do que já existe, não de uma reimplementação ingênua do zero), e
generalizar a peça nativa equivalente já em produção no Vectora, comparando
ativamente contra o que o Hermes faz de equivalente — daí o nome "reimagined-agents":
não é um clone do LangChain, é uma extração informada por três fontes reais (a lib
original que foi substituída, e as duas implementações nativas já provadas em
produção).

## Ver também

- `C:\Users\Machi\.claude\plans\rustling-hatching-summit.md` — precedente de migração
  nativa dentro do próprio Vectora (OpenRouter/Ollama/Tavily), incluindo as
  armadilhas reais encontradas (streaming, formatos de resposta assimétricos, bugs
  silenciosos só descobertos em auditoria posterior) que qualquer trabalho futuro
  nesta linha precisa levar em conta.
