# Vectora

O **Vectora** é um assistente de IA de código aberto (licença Apache 2.0) desenvolvido especialmente para desenvolvedores. Ele é projetado com foco no local-first e auto-hospedado (self-hosted), funcionando perfeitamente como um sub-agente poderoso dentro de qualquer orquestrador compatível com o protocolo MCP (como Claude Code, Claude Desktop, Paperclip e extensões do VS Code).

Em sua essência, o Vectora resolve o **problema do abismo de conhecimento (knowledge gap)**: os LLMs não conhecem sua base de código, sua documentação ou as versões mais recentes das tecnologias da sua stack. O Vectora preenche essa lacuna utilizando RAG (Retrieval-Augmented Generation / Geração Aumentada por Recuperação) — você indexa seus documentos uma única vez e, a partir de então, todas as interações com a IA passam a ter consciência contextual completa.

---

## Por que o Vectora?

Esta seção destaca as principais vantagens e diferenciais que tornam o Vectora uma escolha ideal para enriquecer o contexto dos seus assistentes de IA:

- **Nativo de RAG**: Cada conversa é apoiada por um banco de dados vetorial local. Indexe documentações, códigos e wikis — e sua IA realmente passará a conhecê-los.
- **14 ferramentas integradas**: Operações de arquivo, terminal, busca na web, busca vetorial, memória e ponte MCP — tudo pronto para uso.
- **Arquitetura de sub-agente**: Projetado para rodar como um servidor MCP. O Claude Code pode delegar tarefas complexas para o Vectora, que realiza o raciocínio e retorna a resposta.
- **Memória persistente**: Memória entre sessões armazenada em SQLite. O Vectora lembra das suas preferências, contexto do projeto e decisões anteriores.
- **Infraestrutura zero**: SQLite + LanceDB. Não é necessário Docker para uso local, dispensando instâncias de Postgres, Redis ou serviços em nuvem.
- **Suporte a Múltiplos LLMs**: Google Gemini (plano gratuito), Cohere (plano gratuito), OpenAI, Anthropic ou Ollama (execução totalmente local).

---

## Pré-requisitos

Para que o Vectora funcione perfeitamente, é fundamental configurar os provedores de inteligência artificial corretos. Antes de iniciar, certifique-se de obter as chaves de API necessárias conforme detalhado a seguir:

### Cohere — Obrigatório

A Cohere fornece os modelos de embedding e reranking que o Vectora usa para indexação e busca semântica em RAG. Integração first-class no LangChain e excelente cobertura multilíngue (português incluso).

O Vectora utiliza a [Cohere](https://cohere.com/) com `embed-multilingual-v3.0` para embeddings e `rerank-multilingual-v3.0` para ranqueamento. O serviço oferece um **plano gratuito bastante generoso**.

Obtenha sua chave de API aqui: https://dashboard.cohere.com/api-keys

### Tavily — Obrigatório

O Tavily fornece busca web em tempo real e extração de conteúdo de URLs, otimizado especificamente para agentes de IA. O serviço oferece um **plano gratuito** com cotas generosas.

Obtenha sua chave de API aqui: https://app.tavily.com/

### Provedor de LLM — Escolha Um

Além dos embeddings, você precisará de um provedor de modelo de linguagem para processar e responder às mensagens. Escolha um dos provedores da tabela abaixo de acordo com a sua preferência:

| Provedor                         | Plano Gratuito | Obter Chave                                                   |
| -------------------------------- | -------------- | ------------------------------------------------------------- |
| **Google Gemini** ✅ Recomendado | Sim            | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| Cohere                           | Sim            | [dashboard.cohere.com](https://dashboard.cohere.com/api-keys) |
| Ollama (local)                   | Sem custo      | [ollama.ai](https://ollama.ai)                                |
| OpenAI                           | Pago           | [platform.openai.com](https://platform.openai.com/api-keys)   |
| Anthropic                        | Pago           | [console.anthropic.com](https://console.anthropic.com/)       |

---

## Instalação

A instalação do Vectora é simples e flexível, permitindo que você escolha o método que melhor se adapta ao seu ambiente de desenvolvimento. Siga uma das opções abaixo para realizar a instalação:

### Opção 1: UV (Recomendado)

O `uv` é um gerenciador de pacotes e ambientes Python extremamente rápido, sendo o método de instalação mais recomendado para a maioria dos usuários:

```bash
# Instalar globalmente
uv tool install vectora-agent

# Configuração inicial (assistente interativo)
vectora setup

# Iniciar o chat
vectora chat
```

### Opção 2: A partir do Código Fonte

Se você deseja contribuir com o desenvolvimento ou prefere rodar o Vectora diretamente a partir do repositório, siga os passos de compilação abaixo:

```bash
git clone https://github.com/brunosrz/vectora.git
cd vectora

# Instalar com todas as dependências
uv sync

# Configurar suas chaves de API
cp .env.example .env
# Edite o arquivo .env com suas chaves GOOGLE_API_KEY e COHERE_API_KEY

# Executar
uv run vectora chat
```

### Opção 3: Docker

Para quem prefere utilizar containers para isolar o ambiente e facilitar o deploy em servidores ou fluxos multi-agente, o Docker é a escolha ideal:

```bash
# Copiar e configurar o ambiente de execução
cp .env.example .env
# Edite o arquivo .env com as suas chaves de API

# Executar a interface de chat
docker compose run --rm vectora

# Ou executar como servidor MCP (modo multi-agente)
MCP_TRANSPORT=sse docker compose up -d
```

---

## Modos de Execução

O Vectora foi projetado para ser altamente versátil, oferecendo múltiplos modos de execução para atender tanto ao uso pessoal direto no terminal quanto à integração avançada com outros agentes. Conheça as opções disponíveis:

### Modo Chat (TUI Interativa)

Esta é a interface principal do usuário — um painel de controle completo diretamente no terminal desenvolvido com a biblioteca Rich:

```bash
vectora chat
```

Recursos disponíveis: conversas de múltiplos turnos (multi-turn), histórico de sessões, feedback das ferramentas em tempo real (painéis coloridos), alternância do modo de depuração (debug) e troca dinâmica de modelos.

### Servidor MCP — Local (stdio)

Execute o Vectora de forma simplificada em sua máquina local para servir como um sub-agente integrado a outros ecossistemas de desenvolvimento:

Execute o Vectora como um sub-agente MCP para o Claude Code ou Claude Desktop através de um processo local de cliente único.

```bash
vectora mcp-server
```

### Servidor MCP — Remoto (SSE, Multi-Agent)

Para cenários avançados de equipe ou múltiplos orquestradores que precisam acessar os mesmos recursos simultaneamente, utilize o transporte SSE:

Execute o Vectora como um hub compartilhado para múltiplos agentes Paperclip ou orquestradores conectando-se simultaneamente.

```bash
MCP_TRANSPORT=sse MCP_PORT=8000 vectora mcp-server
```

Cada cliente passa seu próprio `thread_id` — as sessões de chat são completamente isoladas umas das outras.

### Assistente de Configuração

Se você estiver iniciando ou alterando suas chaves e provedores, utilize o assistente automatizado para garantir que toda a comunicação esteja correta:

Configuração interativa para definir suas chaves de API, selecionar seu provedor de LLM preferido e testar a conectividade da rede.

```bash
vectora setup
```

---

## Conectando ao Claude Code / Claude Desktop

Para que seus assistentes externos se beneficiem de todo o poder contextual do Vectora, você deve registrá-lo como um servidor MCP. Adicione a configuração abaixo ao seu arquivo `.mcp.json` (localizado na raiz do seu projeto ou globalmente) para que o Claude Code utilize o Vectora como sub-agente:

```json
{
  "mcpServers": {
    "Vectora-MCP": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "/caminho/absoluto/para/vectora",
        "vectora-mcp"
      ]
    }
  }
}
```

Para uma instalação global do Vectora:

```json
{
  "mcpServers": {
    "Vectora-MCP": {
      "command": "vectora-mcp"
    }
  }
}
```

Para uso com Docker (modo SSE, suporte a múltiplos agentes simultâneos):

```json
{
  "mcpServers": {
    "Vectora-MCP": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

---

## Comandos do Chat

Ao interagir no Modo Chat, você pode controlar o comportamento da sessão, trocar modelos e depurar chamadas de ferramentas através de comandos rápidos. Veja a tabela de comandos suportados:

| Comando         | Descrição                                                   |
| --------------- | ----------------------------------------------------------- |
| `/help`         | Mostra uma ajuda rápida                                     |
| `/list`         | Lista todos os comandos disponíveis                         |
| `/tools`        | Lista todas as ferramentas habilitadas                      |
| `/model`        | Lista ou alterna entre os modelos de linguagem              |
| `/debug`        | Ativa/desativa o modo debug (exibe chamadas de ferramentas) |
| `/new`          | Inicia uma nova sessão de conversa                          |
| `/sessions`     | Lista todas as sessões anteriores                           |
| `/session <id>` | Alterna para uma sessão específica pelo seu ID              |
| `/quit`         | Encerra a aplicação                                         |

**Atalhos de teclado:** Pressione `Enter` para enviar a mensagem, ou use `Alt+Enter` / `Shift+Enter` para inserir uma quebra de linha.

---

## Referência de Ferramentas

O Vectora expõe um conjunto robusto de 14 ferramentas nativas que podem ser invocadas pelo LLM interno ou por qualquer cliente MCP conectado:

Esta tabela detalha as ferramentas categorizadas disponíveis para expandir a capacidade de ação do assistente:

| Categoria    | Ferramentas                                                |
| ------------ | ---------------------------------------------------------- |
| **Web**      | `web_search`, `fetch_url`                                  |
| **RAG**      | `vector_search`, `embedding`, `ingest_docs`                |
| **Arquivos** | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir` |
| **Terminal** | `terminal`                                                 |
| **Memória**  | `save_memory`, `get_memory`, `delete_memory`               |
| **MCP**      | `call_mcp_tool`                                            |

---

## Dados e Persistência

Todas as configurações, logs e bancos de dados do Vectora são guardados localmente na sua máquina para garantir privacidade e controle total dos dados. O diretório padrão de armazenamento é `~/.vectora/`:

A estrutura de arquivos do diretório de dados é descrita abaixo:

```
~/.vectora/
├── .env                    # Suas chaves de API
├── chat_config.json        # Configurações persistentes de chat
├── data/
│   ├── vectora.db          # Sessões, memórias e checkpoints (SQLite)
│   ├── embedding_queue.db  # Fila assíncrona de embeddings (SQLite)
│   └── lancedb/            # Banco de dados vetorial para RAG
├── logs/
│   ├── vectora.log         # Logs estruturados em formato JSON
│   └── mcp.log             # Logs dedicados do servidor MCP
└── keys/                   # Chaves de API criptografadas (opcional)
```

---

## Stack de Tecnologia

O Vectora foi construído utilizando as tecnologias mais modernas e robustas para garantir alta performance, baixa latência e total flexibilidade de desenvolvimento:

Esta tabela detalha os principais componentes técnicos que formam a arquitetura do Vectora:

| Camada             | Tecnologia                                                                                             |
| ------------------ | ------------------------------------------------------------------------------------------------------ |
| Linguagem          | Python 3.14+ gerenciado pelo [uv](https://github.com/astral-sh/uv)                                     |
| Framework de Agent | [LangChain](https://langchain.com/) + [LangGraph](https://langchain-ai.github.io/langgraph/)           |
| Banco Vetorial     | [LanceDB](https://lancedb.github.io/lancedb/) — baseado em arquivos, configuração zero                 |
| Embeddings         | [Cohere](https://cohere.com/) — `embed-multilingual-v3.0` + `rerank-multilingual-v3.0`                 |
| Persistência       | SQLite via `aiosqlite` + Checkpointer do LangGraph                                                     |
| Protocolo Contexto | [MCP](https://modelcontextprotocol.io/) via [FastMCP](https://github.com/jlowin/fastmcp)               |
| Interface Terminal | [Rich](https://rich.readthedocs.io/) + [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/) |
| Observabilidade    | [LangSmith](https://smith.langchain.com/) (opcional)                                                   |

---

## Configuração

Você pode ajustar todo o comportamento e conexões do Vectora editando o arquivo de ambiente. Todas as configurações podem ser feitas em `~/.vectora/.env` ou no arquivo `.env` local do projeto:

A estrutura de variáveis suportada no arquivo `.env` é apresentada abaixo:

```env
# Provedor de LLM
LLM_PROVIDER=google-genai
GOOGLE_API_KEY=sua_chave_aqui

# Obrigatório: embeddings e reranking RAG
COHERE_API_KEY=sua_chave_aqui

# Obrigatório: busca web e extração de URLs
TAVILY_API_KEY=sua_chave_aqui

# Opcional: Rastreamento/Observabilidade
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=sua_chave_aqui
LANGSMITH_PROJECT=vectora

# Opcional: Nível de Log
LOG_LEVEL=INFO
```

---

## Licença

Este projeto é disponibilizado sob os termos da Licença Apache 2.0. Para obter detalhes completos sobre permissões e limitações, consulte o arquivo [LICENSE](./LICENSE).
