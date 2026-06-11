# Vectora Company — Strategic Partnership Plan

> Documento de planejamento de longo prazo para parcerias estratégicas com
> Cohere e Tavily. Não é um plano de ação imediato — é um registro de
> raciocínio e estratégia para quando o Vectora atingir relevância suficiente
> para iniciar essas conversas. O objetivo é não perder essa visão.

---

## O argumento central

O Vectora não é apenas um cliente do Cohere ou do Tavily. É um **canal de
distribuição** para ambos.

A maioria das PMEs de tecnologia nunca vai contratar Cohere ou Tavily
diretamente. Não porque não precisem — porque nunca vão construir a
infraestrutura que torna esses serviços úteis por conta própria. Construir
um pipeline RAG com embedding, vector store, reranker e busca web integrada
é trabalho de semanas para um time experiente. A maioria das empresas não
tem esse time nem esse tempo.

O Vectora entrega essa infraestrutura pronta. E ao fazer isso, ele leva
o Cohere e o Tavily a empresas que de outra forma nunca os teriam como
fornecedores.

**Analogia:** da mesma forma que jogos precisam de um console para ser
vendidos, o Cohere precisa de um ambiente operacional para chegar ao usuário
final. Seu foco é B2B — eles não têm app próprio para o público final,
e isso é uma lacuna que o Vectora preenche naturalmente.

---

## Parceria com Cohere

### Por que o Cohere se importaria

**1. Distribuição para um mercado que eles não alcançam diretamente**

O Cohere vende APIs para empresas com times de engenharia. O Vectora
alcança PMEs de tech que não vão construir pipelines RAG do zero — mas
que vão usar o Vectora e, ao fazer isso, vão gerar volume de chamadas
para os endpoints do Cohere.

**2. O Cohere já está dentro do Vectora de forma estrutural**

Não é uma integração superficial. O Cohere é o backbone do sistema RAG
do Vectora em duas camadas que não são substituíveis trivialmente:

- **Embedding:** `embed-multilingual-v3.0` (1024 dims) — indexa todos
  os documentos de todos os workspaces de todos os usuários do Vectora
- **Reranker:** `rerank-multilingual-v3.0` — executado a cada busca RAG,
  independente do LLM escolhido pelo usuário

Isso significa: **mesmo empresas que usam GPT-4 ou Claude como LLM principal
no Vectora estão gerando receita para o Cohere** via embedding e reranking.
O Cohere não compete pelo LLM — ele ganha independente de qual LLM vence.

**3. Crescimento mútuo com expansão do catálogo Cohere**

À medida que o Cohere lança novos modelos (geração de imagens, STT, TTS,
modelos multimodais), o Vectora passa a suportar todos eles. Cada novo
modelo do Cohere que entra no Vectora aumenta o caso de uso para assinar
o Cohere. O Vectora vira o ambiente de testes e adoção de novos produtos
do Cohere para PMEs.

**4. Alinhamento de posicionamento B2B**

O Cohere é explicitamente focado em B2B enterprise. O Vectora é self-hosted
com foco em PMEs de tech. Não há sobreposição de mercado — há complementaridade:
o Cohere serve grandes empresas diretamente; o Vectora serve médias e pequenas
empresas com a mesma infraestrutura de qualidade.

### O que poderia ser negociado

**Cenário A — Parceria de distribuição (mais provável no curto prazo):**

- Cohere oferece créditos ou desconto de volume para usuários do Vectora
- Vectora é listado como "parceiro oficial" no site do Cohere
- Co-marketing: posts, webinars, caso de uso conjunto
- Sem exclusividade — outros providers de embedding/rerank continuam disponíveis

**Cenário B — Cohere como provider preferencial (médio prazo):**

- Cohere financia desenvolvimento de integrações específicas (ex: suporte
  a novos modelos do Cohere no Vectora com prioridade)
- Vectora recomenda Cohere como opção padrão no wizard de setup
- Acesso antecipado a novos modelos do Cohere para integração no Vectora
  antes do lançamento público

**Cenário C — Investimento ou aquisição (longo prazo, se houver interesse):**

- Cohere faz investimento seed/série A no Vectora
- Ou adquire o Vectora para ter um "ambiente operacional" próprio
- **Cláusula inegociável:** em qualquer cenário de investimento ou aquisição,
  acesso a LLMs concorrentes (OpenAI, Anthropic, Google) nunca é removido.
  Isso vai contra o princípio fundacional do Vectora de democratizar IA.
  Um Vectora que só roda Cohere não é o Vectora.

### Momento certo para abordar

Não agora. O Cohere não vai olhar para um produto sem base de usuários.

**Gatilhos para iniciar a conversa:**

- Vectora com 500+ usuários ativos gerando volume mensurável de chamadas
  para a API do Cohere
- Vectora listado em conteúdo de terceiros (influenciadores, artigos)
  como "usa Cohere para RAG"
- Caso de uso documentado de empresa usando Vectora + Cohere em produção

**Canal de entrada:**

- LinkedIn — engenheiros de developer relations do Cohere
- Ou via programa oficial de parceiros do Cohere (se existir)
- Não ir direto para o topo — começar com a equipe de partnerships/devrel

---

## Parceria com Tavily

### Por que o Tavily se importaria

**1. O Tavily é o motor de busca web do Vectora**

Toda busca web feita por qualquer usuário do Vectora passa pelo Tavily.
Search Agent, cascading web → LanceDB, fallback do RAG subgraph —
todos consomem a API do Tavily. À medida que a base de usuários cresce,
o volume de buscas por mês cresce proporcionalmente.

**2. O Tavily é um produto sem distribuição própria**

O Tavily não tem produto consumer. É puro B2B API — você paga por busca,
você usa nos seus sistemas. Isso significa que o crescimento deles depende
inteiramente de desenvolvedores integrando a API em produtos.

O Vectora é exatamente isso: um produto com uma base crescente de usuários
que gera chamadas constantes para o Tavily sem que o usuário final precise
saber que o Tavily existe.

**3. Posicionamento no ecossistema LangChain**

O Vectora usa `langchain-tavily` (Tavily v2 com parâmetros avançados:
`topic`, `time_range`, `include_raw_content`, `tavily_extract`). Isso
significa que o Vectora está usando a integração oficial e mais avançada
do Tavily — não uma chamada HTTP básica. Isso já é um argumento de parceria:
o Vectora é um showcase de uso avançado do Tavily dentro do ecossistema LangChain.

### O que poderia ser negociado

**Cenário A — Créditos e co-marketing (mais provável):**

- Tavily oferece créditos gratuitos para usuários em trial do Vectora
  (reduz barreira de entrada — usuário experimenta o Vectora com busca
  web funcionando sem precisar criar conta no Tavily imediatamente)
- Vectora listado como caso de uso no site do Tavily
- Co-marketing conjunto: "Vectora + Tavily: busca web com RAG contextual"

**Cenário B — Integração preferencial:**

- Acesso antecipado a novas features do Tavily (ex: `tavily_extract`
  multi-URL já foi uma feature nova — ter isso antes dos concorrentes)
- Tavily patrocina desenvolvimento de uma feature específica no Vectora
  que demonstra capacidades avançadas da API deles

**Cenário C — Parceria de revenue share:**

- Vectora recomenda Tavily como motor web padrão (já é o padrão hoje)
- Tavily oferece comissão sobre novos usuários que chegam via Vectora
  (código de referência automático no wizard de setup)

### Momento certo para abordar

O Tavily é uma empresa menor e mais acessível que o Cohere. A conversa
pode acontecer mais cedo — mesmo com 100–200 usuários ativos já é
possível mostrar um número de buscas/mês que justifica a conversa.

**Gatilhos:**

- Volume mensurável de buscas/mês gerado pelo Vectora (tracking via
  `license_checks` + estimativa por usuário ativo)
- Caso de uso documentado mostrando o Vectora usando Tavily para algo
  além do básico (ex: curadoria web com gate reranker + Tavily)

**Canal de entrada:**

- LinkedIn — o Tavily é uma startup pequena, o CEO provavelmente
  responde mensagem direta
- Ou via Discord/comunidade do LangChain onde o Tavily é ativo

---

## O que não negociar em hipótese alguma

Em qualquer parceria, independente do valor financeiro envolvido:

**1. Remoção de providers concorrentes**
O Vectora nunca vai remover OpenAI, Anthropic, Google Gemini ou qualquer
outro provider para favorecer um parceiro. Isso vai contra o princípio
fundacional de democratizar IA. Um usuário do Vectora sempre poderá
escolher qual LLM usar.

**2. Coleta de dados de conversas**
Nenhum parceiro recebe acesso ao conteúdo das conversas ou dos workspaces
dos usuários. Self-hosted significa que esses dados nunca saem do servidor
do cliente.

**3. Mudança de posicionamento**
O Vectora não vira um produto do Cohere ou do Tavily. Continua sendo
um produto da Vectora Company com identidade própria. Parceria é
co-marketing e integração preferencial — não white-label ou rebrand.

---

## Registro de raciocínio: por que planejar isso agora

Este documento existe por uma razão simples: boas oportunidades de parceria
são perdidas não por falta de interesse, mas por falta de preparação.

Quando o Vectora atingir relevância suficiente para iniciar essas conversas,
Bruno já terá clareza sobre:

- O que o Vectora oferece para cada parceiro (argumento de valor)
- O que é negociável e o que não é (linhas vermelhas)
- Qual o momento certo e o canal certo para abordar
- O que pedir em cada cenário (créditos, co-marketing, investimento)

Sem esse planejamento, a primeira conversa com o Cohere ou o Tavily vai
ser improvisada — e uma conversa improvisada sobre parceria estratégica
raramente resulta no melhor acordo possível.

---

## Próximos passos (quando o momento chegar)

1. **Preparar deck de parceria** (2 páginas): números de usuários, volume
   de chamadas de API, caso de uso documentado, proposta específica
2. **Identificar o contato certo** em cada empresa (não CEO — partnerships
   ou devrel)
3. **Primeira abordagem:** mensagem curta no LinkedIn com contexto e
   pedido de call de 30 min — sem mandar deck frio
4. **Call de exploração:** entender o que faz sentido para eles antes
   de apresentar o que queremos
5. **Proposta formal** somente após entender o interesse mútuo

---

_Última atualização: planejamento inicial — revisitar quando Vectora
atingir 500+ usuários ativos._
