# Vectora

Inteligência Artificial que é sua — instalada, controlada e evoluída por você.

---

## O Problema

Toda ferramenta de IA que você usa hoje guarda seus dados em servidores de outra empresa.

Seu código. Sua documentação. Suas conversas. Seu contexto de projeto.  
**Tudo isso sai da sua máquina e vai para a nuvem de outra pessoa.**

Para desenvolvedores independentes isso é inconveniente.  
Para empresas, é um risco jurídico, um problema de compliance e uma dependência estratégica.

---

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

**E o Ollama?** Suportamos, mas não recomendamos como ponto de partida. Para ter resultados satisfatórios com um LLM local, você precisa de modelos com dezenas ou centenas de bilhões de parâmetros — o que exige hardware extremamente high-end: dezenas de gigabytes de VRAM ou RAM compartilhada. Mesmo notebooks recentes com 32 GB de RAM e NPU sofrem. Em uma VPS, esse processamento simplesmente não existe. Ollama faz sentido para quem já tem o hardware certo por outras razões — é suportado, funciona bem, mas não é o caminho para a maioria dos casos de uso.

Ferramentas opcionais como **Tavily** (busca web) e **Cohere** (reranking) também são APIs externas — configuráveis e substituíveis.

**Custo:** você não paga por assento nem por número de usuários. Paga pelos tokens que consome nas APIs que escolheu usar.

**LGPD e compliance:** o Vectora não armazena seus dados em nenhum servidor nosso. Ao conectar APIs externas, você — como operador — é o responsável pelo tratamento dos dados perante a lei. Nossos Termos de Uso descrevem exatamente quais dados trafegam para cada integração.

---

## Posicionamento: Concorrente e Parceiro ao Mesmo Tempo

À primeira vista, o Vectora compete com ferramentas como **Claude Code**, **Codex** e **Hermes Agent**.  
Quando usado como CLI ou como chat, ele é de fato uma alternativa direta.

Mas o Vectora tem um modo que nenhum concorrente tem: **modo MCP**.

> O protocolo MCP foi criado para conectar ferramentas a inteligências artificiais.  
> O Vectora expõe uma ferramenta chamada `delegate_to_vectora`.

Isso significa que um desenvolvedor pode continuar usando o Claude Code ou o Codex  
e, quando eles chegam num limite — indexar conhecimento, fazer RAG em documentação interna,  
busca com relevância semântica — **eles delegam para o Vectora**.

**Nossos concorrentes viram usuários do Vectora.**  
Não substituímos o fluxo de trabalho existente. Nós o estendemos.

---

## Arquitetura de Agentes

O Vectora não é um único modelo respondendo perguntas.  
É um sistema de **quatro agentes especializados**, cada um com domínio próprio.

---

### 🔵 Vectora Agent

**O orquestrador.**

Recebe a tarefa, entende o contexto, decide qual agente especialista acionar  
e consolida as respostas em uma entrega coerente.  
É o ponto de entrada único — para o usuário e para quem delega via MCP.

---

### 🟣 Vectora RAG Agent

**O astro do projeto. Especializado em Recuperação de Conhecimento.**

Nossos concorrentes não têm um agente dedicado a RAG.  
Alguns sequer têm as ferramentas para isso.

O Vectora RAG indexa qualquer base de conhecimento — documentação, código, wikis, PDFs —  
e responde com contexto real do seu projeto, não com alucinação baseada em dados de treinamento.

---

### 🟡 Vectora Search Agent

**Especializado não só em buscar, mas em relevância e apresentação.**

A diferença entre "retornar resultados" e "entregar a resposta certa" é enorme.  
O Search Agent filtra ruído, reordena por relevância e entrega a informação  
no formato mais útil para quem perguntou.

---

### 🟢 Vectora Coder Agent

**Especializado em desenvolvimento com boas práticas.**

Escreve, revisa e refatora código com entendimento do padrão do projeto —  
porque ele leu o projeto antes de tocar nele.

---

## RAG: O Que é e Por Que Importa

**Retrieval-Augmented Generation** é o conjunto de tecnologias que torna o Vectora "retreinável" para qualquer projeto.

```
Documento / Código / Wiki
        ↓
   [ Embedding ]          ← IA que organiza conteúdo em chunks legíveis
        ↓
  [ Vector Store ]        ← Banco de dados vetorial local
        ↓
  [ Vector Search ]       ← Busca semântica no Vector Store
        ↓
   [ Reranker ]           ← IA que filtra e reordena por relevância
        ↓
     [ LLM ]              ← Responde com contexto real do seu projeto
```

**Na prática:** você aponta o Vectora para a documentação ou o código-base do seu projeto.  
Ele indexa tudo. A partir daí, ele sabe tudo sobre aquele projeto —  
sem retreinamento, sem fine-tuning, sem enviar dados para ninguém.

---

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

---

## Vectora para Empresas

O Vectora tem um **aplicativo web self-hosted** que se conecta diretamente aos agentes.

Uma empresa instala um único Vectora em seu servidor interno.  
Todos os funcionários acessam pelo browser — sem instalar nada, sem configurar nada.  
O agente tem acesso à worktree dos projetos internos e pode contribuir diretamente no código.

**O que isso significa na prática:**

- O histórico de sessões, os documentos indexados e a base de conhecimento ficam no servidor da empresa
- O custo não escala por usuário — escala com os tokens que você consome nas APIs escolhidas
- Com Ollama: nenhum dado sai da rede interna. Com APIs externas: a empresa decide quais provedores usar e aceita os termos deles
- Funciona em rede interna sem internet — desde que o LLM também seja local (Ollama)
- **LGPD:** o Vectora não é o controlador dos seus dados. Mas se você usar APIs externas (OpenAI, Cohere, etc.), a empresa é responsável por essa transferência de dados. Nossos Termos de Uso detalham cada integração e o que trafega por ela.
- SOC 2 e auditorias de segurança: o código é open-source (Apache 2.0) — auditável por qualquer time interno

---

## Diferenciais em Resumo

|                                       | Vectora | Claude Code |  Codex  | Hermes  |
| ------------------------------------- | :-----: | :---------: | :-----: | :-----: |
| Self-hosted                           |   ✅    |     ❌      |   ❌    |   ❌    |
| Base de conhecimento local (RAG)      |   ✅    |     ❌      |   ❌    |   ❌    |
| Suporte a LLM local (Ollama)          |   ✅    |     ❌      |   ❌    |   ❌    |
| Agente RAG dedicado                   |   ✅    |     ❌      |   ❌    |   ❌    |
| Modo MCP (parceiro de outros agentes) |   ✅    |     ❌      |   ❌    |   ❌    |
| Multi-agente especializado            |   ✅    |     ❌      | Parcial | Parcial |
| App web para times                    |   ✅    |     ❌      |   ❌    |   ❌    |
| Custo por usuário                     |   ❌    |     ✅      |   ✅    |   ✅    |
| Open-source (auditável)               |   ✅    |     ❌      |   ❌    |   ❌    |

> ¹ Ollama é suportado mas requer hardware high-end para resultados satisfatórios (modelos com dezenas a centenas de bilhões de parâmetros, dezenas de GB de VRAM). O uso recomendado é com APIs externas em VPS — o Vectora em si é leve; o LLM é que exige poder computacional.

---

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

---

## Por Que Agora

O mercado de ferramentas de IA para desenvolvimento explodiu.  
Mas todas as soluções líderes compartilham o mesmo problema estrutural:  
são serviços em nuvem com custo por assento, dependência de disponibilidade externa  
e acesso aos seus dados que você não controla nem audita.

O Vectora não elimina APIs externas — você ainda vai querer um LLM bom e busca web.  
Mas a diferença é que **você escolhe quais dados saem e para onde vão**, em vez de aceitar um pacote fechado.

A demanda por soberania de dados não é uma tendência passageira.  
É uma exigência crescente de compliance (LGPD, GDPR, SOC 2), de segurança e de controle estratégico.

**Vectora é a única IA de desenvolvimento que você instala na sua infraestrutura, audita o código-fonte e evolui conforme sua necessidade.**

---

## Contato

**Bruno Soares** — bruno.soarxz@gmail.com  
GitHub: [github.com/brunosrz](https://github.com/brunosrz)

---

_Vectora — Apache 2.0 — Self-hosted. Seus dados. Sua IA._
