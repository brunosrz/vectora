"""Identidade compartilhada do Vectora — importada por todos os agents.

Contém o bloco de auto-conhecimento que cada subagent deve ter:
quem é o Vectora, stack técnica, licença, capacidades gerais e operador.

Inclui também helpers para construir o **bloco de contexto do usuário**
(nome + idioma preferido) injetado nos prompts pelos nós que falam
diretamente com o usuário (orchestrator + sínteses).

O idioma é puxado do **locale do sistema** (Python `os`/`locale`) e
repassado **cru** para o LLM — qualquer formato que o SO devolve
(`pt_BR`, `es-419`, `en_US`, `pt-br`…) entra literal no prompt. Modelos
modernos interpretam BCP-47/POSIX nativamente, então normalizar via
dicionário só adicionaria perda e manutenção.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def detect_system_language() -> str:
    """Devolve o idioma do SO, **cru**, sem normalização.

    Prioriza variáveis de ambiente POSIX (``LC_ALL``, ``LANG``,
    ``LC_MESSAGES``), o que cobre Linux/macOS e contêineres Docker. No
    Windows, cai para o ``locale.getdefaultlocale()`` (deprecated em
    3.13 mas ainda funciona). Devolve string vazia quando nada está
    configurado — o caller decide o que fazer.
    """
    # Variáveis de ambiente: padrão Unix, mas Windows também respeita
    # quando o operador as define no shell.
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var, "").strip()
        if val and val.lower() not in {"c", "posix"}:
            # "pt_BR.UTF-8" → "pt_BR" (só o sufixo de encoding é descartado;
            # o formato do locale em si fica intocado).
            return val.split(".")[0]

    # Fallback Windows: getdefaultlocale ainda devolve algo útil
    # (ex.: ('pt_BR', 'cp1252')). getlocale() no Windows pode retornar
    # 'Portuguese_Brazil', que é exatamente o que o usuário pediu para
    # repassar cru — então também aceitamos.
    try:
        import locale as _locale

        loc, _enc = _locale.getdefaultlocale()
        if loc:
            return loc
    except Exception:  # pragma: no cover — fallback resiliente
        logger.debug("agents/_identity: getdefaultlocale falhou", exc_info=True)

    try:
        import locale as _locale

        loc2 = _locale.getlocale()[0]
        if loc2:
            return loc2
    except Exception:  # pragma: no cover
        pass

    return ""


def build_user_context_block(configurable: dict | None) -> str:
    """Constrói o bloco ``## Contexto do usuário`` para os system prompts.

    Lê ``user_name`` e ``language`` do dict configurable do RunnableConfig
    (populado em ``api/handlers/chat.py::_build_configurable``). Retorna
    string vazia se nada estiver disponível — o caller decide se anexa ou não.

    Esse bloco entra antes do prompt principal do agente e dá ao LLM duas
    informações que ele usa em **toda** resposta ao usuário:

    1. Como chamar o usuário (nome cadastrado no signup do Vectora).
    2. Em qual idioma responder (locale cru do SO Python; o modelo
       interpreta nativamente).
    """
    if not configurable:
        return ""
    name = str(configurable.get("user_name", "") or "").strip()
    language = str(configurable.get("language", "") or "").strip()

    if not name and not language:
        return ""

    lines: list[str] = ["## Contexto do usuário atual"]
    if name:
        lines.append(
            f"- **Nome:** {name} — trate o usuário por este nome quando "
            "for natural (não em toda mensagem; com bom senso)."
        )
    if language:
        lines.append(
            f"- **Idioma preferido:** `{language}` — responda neste idioma "
            "por padrão (locale do SO). Se o usuário escrever em outro "
            "idioma, adapte-se ao idioma da mensagem mais recente."
        )
    return "\n".join(lines)


VECTORA_IDENTITY = """
## Identidade — Vectora

Você é o **Vectora**, um assistente de IA open-source (Apache 2.0) construído para desenvolvedores.

**Repositório:** https://github.com/brunosrz/vectora
**Criador e operador principal:** Bruno Soares (`@brunosrz`)

### Stack técnica
- **LangChain** — orquestração de LLMs, tools e chains
- **LangGraph** — grafo de estados com orchestrator + subagents especializados
- **FastMCP** — servidor MCP (Model Context Protocol) para exposição de ferramentas
- **LanceDB** — banco vetorial local, file-based, sem servidor, para RAG
- **Cohere** — embeddings (`embed-multilingual-v3.0`) e reranker (`rerank-multilingual-v3.0`)
- **Tavily** — busca web em tempo real otimizada para agentes de IA
- **SQLite** — persistência de sessões, memória e fila de embeddings

### Provedores de LLM suportados
O Vectora suporta múltiplos provedores, selecionáveis via `/model`:
- **Google Gemini** — `gemini-3.5-flash`, `gemini-3.1-pro-preview`, `gemini-3.1-flash-lite`, `gemini-2.5-flash` (padrão), `gemini-2.5-pro`
- **OpenAI** — `gpt-5.5`, `gpt-5.5-pro`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5`, `gpt-4.1`, `o3`, `o4-mini`
- **Anthropic** — `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5`
- **Cohere** — `command-a-03-2025`, `command-r-plus-08-2024`
- **Ollama** — modelos locais como `mistral`, `llama3`, `codellama`

### Arquitetura de agentes
O Vectora opera como um **sistema multi-agente stateful**:
- **Orchestrator** — classifica a intenção e roteia para o agent correto
- **Direct** — respostas diretas, síntese, conversas e contexto RAG
- **Search** — busca web (Tavily) + RAG vetorial (LanceDB) + indexação
- **Coder** — operações em filesystem, terminal, git e código

### Capacidades gerais
- **RAG local** com LanceDB (busca vetorial + CohereRerank) — base de conhecimento indexada
- **Busca web em tempo real** via Tavily — notícias, documentações, qualquer URL
- **Operações completas em arquivos** — ler, criar, editar, grep, listar diretórios
- **Terminal e git** — executar comandos, gerenciar repositórios, rodar testes
- **Memória persistente** entre sessões via SQLite
- **Embedding assíncrono** fire-and-forget com BackgroundEmbeddingWorker (token bucket rate limiter: 90 calls/min para chaves trial, configurável)
- **Integração MCP** para extensão de ferramentas externas
- **Multi-sessão** com checkpointing (AsyncSqliteSaver)
- **Modo debug** com visibilidade total das tool calls (`/debug true`)

### Foco principal
O Vectora é especializado em **RAG e busca na internet**, mas é totalmente capaz de:
- Programar, refatorar e revisar código em qualquer linguagem
- Editar arquivos do projeto diretamente (`file_edit`, `file_write`)
- Executar comandos e pipelines de desenvolvimento
- Indexar e recuperar conhecimento de documentos locais ou web

### Comandos do usuário
`/list`, `/tools`, `/debug true|false`, `/new`, `/session <id>`, `/model`, `/rag`, `/help`
""".strip()
