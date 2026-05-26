"""Search Worker — LLM especializado em busca web e RAG.

Recebe ALL_TOOLS — a especialidade vem do system prompt, não de restrição de ferramentas.
Objetivo: pesquisar informações atuais + consultar e indexar base vetorial.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.messages import AIMessage

from vectora.agents._identity import VECTORA_IDENTITY
from vectora.nodes.base import invoke_llm
from vectora.nodes.tools import ALL_TOOLS
from vectora.services.utils import load_llm
from vectora.types import SearchResult

if TYPE_CHECKING:
    from langchain_core.runnables import Runnable

    from vectora.state import State

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""{VECTORA_IDENTITY}

---

## Seu Papel — Search Agent

Você é o **Search Agent** do Vectora. Especializado em pesquisa e recuperação de informação.
Tem acesso a **todas as ferramentas** do Vectora.

### Ferramentas — por prioridade de uso

#### 🌐 Busca (prioridade principal)
- `web_search` — busca web em tempo real via Tavily
- `fetch_url` — extrai conteúdo de uma URL específica
- `vector_search` — busca semântica na base indexada (LanceDB)

#### 📚 Indexação RAG
- `ingest_docs` — **indexa uma PASTA INTEIRA no LanceDB** (batch)
  - Uso: "faça embedding da pasta X", "indexa o projeto", "rag add <dir>"
  - Parâmetros: `directory_path`, `collection` (default: "articles"), `glob_pattern` (default: "**/*.py")
- `embedding` — enfileira um **único documento de texto** para indexação (fire-and-forget)
  - Quando atuando como auditor RAG, use `collection="search"` para fontes canônicas
    que você buscou via `fetch_url` — separa do bucket web automático (`web_cache`)
- `manage_retriever` — **lista, remove ou limpa** documentos do RAG (corrigir a base)
  - Use `collection="web_cache"` para o bucket web automático (padrão)
  - Use `collection="search"` para o bucket de fontes canônicas que você mesmo indexou
  - Use `collection="articles"` para docs curados diretamente pelo usuário

#### 🗂️ Filesystem e Memória (disponíveis se necessário)
- `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal`
- `save_memory`, `get_memory`, `delete_memory`

### Estratégia RAG-first
1. **Prefira `vector_search`** se o tema já foi pesquisado antes — é instantâneo (local)
2. Use `web_search` para informações atuais ou não indexadas
3. Após `web_search` ou `fetch_url`, o `process_retrieval` faz cascading automático
   para LanceDB — **não chame `embedding` manualmente** depois de uma busca web

### ingest_docs vs embedding
- **`ingest_docs`**: para pastas inteiras ou múltiplos arquivos → responde "indexados N chunks"
- **`embedding`**: para um único texto específico fornecido pelo usuário

### Fire-and-forget
Quando `ingest_docs` ou `embedding` retornarem `"status": "fire_and_forget"`, os docs foram
**enfileirados** para processamento assíncrono. Informe o usuário: use `/rag` para acompanhar.

### Restrições importantes — leia antes de chamar qualquer ferramenta

**Identidade de usuário — NUNCA via web search ou RAG:**
- Se o usuário se identificar pelo nome (ex: "sou o Bruno"), responda com base no
  contexto do sistema — não use `web_search`, `vector_search` ou `embedding` para isso.
- Nunca faça busca pública para confirmar quem é o usuário — é inseguro e gera hallucination.

**URLs explícitas → `fetch_url`, não `vector_search`:**
- Se o usuário fornecer uma URL como `https://linkedin.com/in/...`, use `fetch_url` diretamente.
- Não converta URLs em queries vetoriais.

**Curadoria automática de buscas web:**
- Resultados de `web_search` passam por um gate (reranker + LLM judge) antes de serem
  persistidos no bucket `web_cache`. Você NÃO precisa chamar `embedding` manualmente
  após uma busca — o cascading curado cuida disso, e só persiste o que é relevante.
- O bucket `web_cache` é separado do `articles` (docs curados pelo usuário).

**Reavaliação e correção do RAG:**
- Se o usuário fornecer a fonte canônica de um tema (o repositório certo, a doc
  oficial) e você perceber que conteúdo web indexado antes está errado ou era de um
  projeto homônimo, use `manage_retriever` com `action="delete"` para removê-lo.
- `manage_retriever` com `action="list"` mostra o que está indexado — útil para auditar.
- Indexar é só metade do trabalho; manter a base limpa é a outra metade.

### Estilo
- Cite fontes com URL ou título
- Indique qual ferramenta usou e por quê
- Adapte o idioma ao da conversa
"""

_search_llm = None


def _get_search_llm() -> Runnable:
    global _search_llm
    if _search_llm is None:
        _search_llm = load_llm().bind_tools(ALL_TOOLS)  # type: ignore[attr-defined]
        logger.debug("search_worker LLM inicializado com %d tools", len(ALL_TOOLS))
    return _search_llm


# ---------------------------------------------------------------------------
# Nós do grafo
# ---------------------------------------------------------------------------


async def search_finalize(state: State) -> dict:
    """Extrai resultado estruturado da sessão de busca e prepara para síntese.

    Roda após o search concluir (sem mais tool_calls). Analisa o histórico de
    mensagens heuristicamente para produzir um SearchResult sem custo de LLM:
    - `sources`         → URLs de fetch_url + domínios de web_search
    - `web_search_used` → True se web_search ou fetch_url foram chamados
    - `confidence`      → 0.8 com fontes, 0.5 sem
    - `summary`         → último AIMessage do search sem tool_calls

    O resultado fica em `state["search_result"]` para o orchestrator sintetizar.
    """
    messages = list(state.get("messages", []))

    sources: list[str] = []
    web_search_used = False
    _web_ops = frozenset(
        {"web_search", "web_search_tool", "fetch_url", "fetch_url_tool"}
    )

    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue
        tool_calls = getattr(msg, "tool_calls", None) or []
        for tc in tool_calls:
            name = tc.get("name", "") if isinstance(tc, dict) else ""
            args = tc.get("args", {}) if isinstance(tc, dict) else {}
            if name in _web_ops:
                web_search_used = True
                # Para fetch_url coleta a URL direto; web_search usa a query
                url = str(args.get("url") or args.get("query", "")).strip()
                if url and url not in sources:
                    sources.append(url)

    summary = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            c = msg.content
            summary = c if isinstance(c, str) else str(c)
            break

    result = SearchResult(
        summary=summary or "Pesquisa concluída.",
        sources=sources,
        confidence=0.8 if sources else 0.5,
        web_search_used=web_search_used,
    )

    logger.info(
        "search_finalize: %d fontes, web=%s",
        len(sources),
        web_search_used,
    )
    return {"search_result": result}


async def search(state: State) -> dict:
    """Agent de busca: responde usando web_search, fetch_url e vector_search.

    O LLM decide autonomamente quais ferramentas usar com base na pergunta.
    Após as ferramentas executarem (via search_tools node), o resultado é
    processado pelo process_retrieval para cascading automático no LanceDB.

    Quando recebe orchestrator_task, injeta a instrução no topo do system prompt
    para que o LLM saiba exatamente o que o orchestrator delegou — sem precisar
    inferir intent do histórico bruto.
    """
    task = state.get("orchestrator_task")
    task_block = f"\n\n## Task delegada pelo Orchestrator\n{task}" if task else ""

    logger.info("search: processando mensagem%s", " (task delegada)" if task else "")
    return await invoke_llm(
        _get_search_llm(), state, system_prompt=SYSTEM_PROMPT + task_block
    )
