# reimagined-agents — extrair o motor nativo do Vectora numa lib open source

Proposta ativa, não escopada tecnicamente. O motor de conversa nativo do
Vectora (`backend/engine/conversation_loop.py::run_conversation`, Protocol
`ChatClient`, `TOOL_REGISTRY`, `SessionStore`) está em produção, validado por
dogfooding real, e não depende de LangChain, LangGraph ou deepagents em
nenhum ponto — confirmado por varredura no backend: zero import dessas
libs restando. A pergunta em aberto é apenas se vale a pena extrair esse
motor, retroativamente, como pacote Python publicável e reutilizável por
outros projetos que precisem de um motor de agente sem a superfície pesada
do LangChain/LangGraph.

## Estado atual

- **Motor nativo**: concluído e em produção dentro do Vectora. Nenhum
  provider (incluindo `nine_router`) depende mais de `langchain-openai`,
  `langchain-anthropic` ou `langchain-google-genai`.
- **Storage nativo**: `AsyncSqliteSaver`/`AsyncPostgresSaver` e equivalentes
  do LangGraph, `langchain_qdrant`, `langchain_redis`,
  `langchain_community.vectorstores` — todos substituídos por clientes
  nativos das próprias libs de storage (`backend/storage/`,
  `backend/persistence/`).
- **Extração para lib separada**: não iniciada. Nenhuma linha de código de
  `reimagined-agents` existe fora do Vectora.

## O que a lib entregaria

Um pacote Python publicável, independente do Vectora, com:

- Loop de conversa genérico (equivalente a `run_conversation`, sem
  acoplamento a schemas específicos do Vectora).
- Protocol `ChatClient` desacoplado, com adapters de referência para pelo
  menos Anthropic, OpenAI-compatível e Google Gemini.
- Registry de tools plugável (equivalente ao `TOOL_REGISTRY`), sem exigir o
  formato de tool específico do Vectora.
- Interface de persistência de sessão plugável (equivalente a
  `SessionStore`), com implementação de referência em SQLite.

Fora de escopo por decisão: checkpointer plugável no estilo LangGraph, grafo
de execução declarativo, qualquer abstração que reproduza a superfície do
LangChain. O ponto da lib é ser mais simples que o que ela substitui.

## Referências de design

A extração não parte de documentação de outra lib nem de reimplementação
ingênua — parte de três fontes já concretas:

1. **Código-fonte do LangChain/LangGraph/deepagents que foi substituído**
   (`deepagents/graph.py`, `langgraph.checkpoint.*`, lidos diretamente durante
   a migração original) — usado para confirmar que nenhuma funcionalidade
   real usada pelo Vectora fica pra trás na extração.
2. **Hermes Agent** (`C:\Users\Machi\AppData\Local\hermes\hermes-agent`) —
   agente de produção real, sem LangChain/LangGraph, com loop de conversa,
   adapters por provider (Anthropic, Gemini, Bedrock, Azure, Vertex,
   Codex/Responses) e persistência de sessão. Referência direta para o
   `run_conversation` nativo do Vectora e para a generalização da lib.
3. **O próprio motor nativo do Vectora** (`backend/engine/`) — segunda
   implementação de referência, já adaptada a um workspace multi-superfície
   (desktop + web), o que o Hermes, mais próximo de um CLI/TUI, não precisa
   resolver.

## Próximos passos reais

1. Decidir se a extração entra no roadmap — não é trabalho de manutenção do
   Vectora, é um projeto novo com superfície pública própria (versionamento,
   compatibilidade, documentação, testes fora do contexto de um único
   produto).
2. Se aprovada: escopar a API pública mínima (loop, `ChatClient`, tool
   registry, session store) comparando lado a lado com o Hermes Agent e com o
   motor nativo do Vectora, documentando explicitamente onde os dois
   divergem e por quê.
3. Definir o modelo de distribuição (nome do pacote, versionamento semver,
   onde publicar) antes de qualquer código.
4. Definir se o Vectora passa a consumir a lib extraída como dependência
   (dogfooding contínuo) ou se `backend/engine/` continua como implementação
   própria em paralelo — a primeira opção garante que a lib não diverge do
   uso real, mas acopla o release do Vectora ao da lib.

Nenhum destes passos tem dono nem prazo definido ainda.

## Ver também

- `C:\Users\Machi\.claude\plans\rustling-hatching-summit.md` — precedente de
  migração nativa dentro do próprio Vectora (OpenRouter/Ollama/Tavily),
  incluindo as armadilhas reais encontradas (streaming, formatos de resposta
  assimétricos, bugs silenciosos só descobertos em auditoria posterior) que
  qualquer trabalho de extração precisa levar em conta.
