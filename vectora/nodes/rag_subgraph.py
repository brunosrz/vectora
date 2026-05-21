"""RAG Subgraph — Pipeline completo de Retrieval-Augmented Generation.

Fluxo:
  START → rag_retrieve → rag_decide → rag_rerank  → rag_inject → END
                                    ↘ rag_websearch → rag_inject → END

Integração com o grafo principal:
  - Entra como nó "rag_subgraph" vindo do router
  - Ao terminar, devolve controle para "call_llm" via END do subgrafo
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from vectora.config.settings import settings
from vectora.state import Document, State

logger = logging.getLogger(__name__)

# Limiares de qualidade para decisão de roteamento interno
_SCORE_HIGH = 0.7  # Resultado bom o suficiente: rerank direto
_SCORE_LOW = 0.4  # Resultado fraco: buscar na web


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _extract_query(state: State) -> str:
    """Extrai texto da última HumanMessage para usar como query RAG."""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            return str(msg.content).strip()
    return ""


def _best_score(docs: list[Document]) -> float:
    """Retorna o maior relevance_score entre os documentos. 0.0 se vazio."""
    if not docs:
        return 0.0
    scores = [
        float(d.get("relevance_score") or 0.0)
        for d in docs
        if d.get("relevance_score") is not None
    ]
    return max(scores, default=0.0)


async def _call_vector_search(
    query: str, collection: str = "articles", limit: int = 5
) -> list[Document]:
    """Chama vector_search diretamente (sem passar pelo ToolNode) e retorna lista de Document."""
    from vectora.tools.rag import vector_search  # importação local para evitar ciclo

    try:
        raw = await vector_search.ainvoke(
            {"query": query, "collection": collection, "limit": limit}
        )
        data = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(data, dict) and data.get("status") in (
            "error",
            "no_results",
            "failed",
        ):
            return []
        results = data.get("results", data) if isinstance(data, dict) else data
        if not isinstance(results, list):
            return []
        return [
            Document(
                page_content=str(r.get("content", "")),
                metadata=r.get("metadata", {}),
                relevance_score=r.get("relevance_score") or r.get("score"),
            )
            for r in results
        ]
    except Exception:
        logger.exception("rag_retrieve: vector_search failed")
        return []


async def _call_web_search(query: str) -> list[dict[str, Any]]:
    """Chama web_search diretamente e retorna lista de resultados brutos."""
    from vectora.tools.web import web_search  # importação local para evitar ciclo

    try:
        raw = web_search.invoke({"query": query})
        data = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and data.get("status") == "error":
            return []
        return []
    except Exception:
        logger.exception("rag_websearch: web_search failed")
        return []


async def _enqueue_for_embedding(
    text: str, collection: str = "articles", metadata: dict[str, Any] | None = None
) -> str | None:
    """Enfileira texto para embedding fire-and-forget. Retorna queue_id ou None."""
    from vectora.tools.rag import embedding  # importação local para evitar ciclo

    try:
        raw = await embedding.ainvoke(
            {"text": text, "collection": collection, "metadata": metadata or {}}
        )
        data = json.loads(raw) if isinstance(raw, str) else raw
        return data.get("queue_id") if isinstance(data, dict) else None
    except Exception:
        logger.warning("rag: failed to enqueue for embedding")
        return None


# ---------------------------------------------------------------------------
# Nós do subgrafo
# ---------------------------------------------------------------------------


async def rag_retrieve(state: State) -> dict:
    """Nó 1: Executa vector_search com a query do usuário."""
    import contextlib

    from vectora.services.tracer import tracer

    session_id: int | None = None
    with contextlib.suppress(Exception):
        session_id = state.get("session_metadata", {}).get("thread_id")  # type: ignore[assignment]

    query = _extract_query(state)
    if not query:
        logger.warning("rag_retrieve: no query found in state")
        return {"rag_query": "", "rag_docs": []}

    logger.info("rag_retrieve: searching for '%s...'", query[:60])

    try:
        async with tracer.span("rag_retrieve", "search", session_id=session_id) as s:
            docs = await _call_vector_search(query)
            best = _best_score(docs)
            s.set(n_docs=len(docs), best_score=round(best, 3), query_len=len(query))
    except Exception:
        docs = await _call_vector_search(query)  # fallback sem tracer

    logger.info(
        "rag_retrieve: found %d docs, best_score=%.3f", len(docs), _best_score(docs)
    )
    return {"rag_query": query, "rag_docs": docs}


def rag_decide(state: State) -> str:
    """Nó 2: Decide o próximo passo com base na qualidade dos resultados.

    Retorna o nome do próximo nó (usado como valor em add_conditional_edges).
    """
    docs = state.get("rag_docs") or []
    score = _best_score(docs)

    if score >= _SCORE_HIGH:
        logger.debug("rag_decide: score=%.3f → rag_inject (direto)", score)
        return "rag_inject"
    if score >= _SCORE_LOW:
        logger.debug("rag_decide: score=%.3f → rag_rerank", score)
        return "rag_rerank"

    logger.debug("rag_decide: score=%.3f → rag_websearch", score)
    return "rag_websearch"


async def rag_rerank(state: State) -> dict:
    """Nó 3a: Aplica CohereRerank e filtra top-3 docs mais relevantes."""
    docs = state.get("rag_docs") or []
    query = state.get("rag_query") or ""

    if not docs or not query:
        return {}

    try:
        from langchain_cohere import CohereRerank
        from langchain_core.documents import Document as LCDoc
        from pydantic import SecretStr

        api_key = settings.get_cohere_api_key()
        if not api_key:
            logger.warning("rag_rerank: COHERE_API_KEY not set, skipping rerank")
            return {}

        reranker = CohereRerank(
            cohere_api_key=SecretStr(api_key),
            model=settings.reranker_model,
            top_n=3,
        )
        lc_docs = [
            LCDoc(
                page_content=str(d.get("page_content", "")),
                metadata=d.get("metadata", {}),
            )
            for d in docs
        ]
        reranked = reranker.compress_documents(lc_docs, query)

        reranked_docs: list[Document] = [
            Document(
                page_content=doc.page_content,
                metadata=doc.metadata,
                relevance_score=getattr(doc, "relevance_score", None),
            )
            for doc in reranked
        ]
        logger.info("rag_rerank: reranked to %d docs", len(reranked_docs))
        return {"rag_docs": reranked_docs}

    except Exception:
        logger.exception("rag_rerank: failed, keeping original docs")
        return {}


async def rag_websearch(state: State) -> dict:
    """Nó 3b: Busca na web quando vector_search não tem resultados suficientes.

    Automaticamente enfileira resultados para embedding (cascading automático).
    """
    query = state.get("rag_query") or _extract_query(state)
    if not query:
        return {"web_search_triggered": True}

    logger.info("rag_websearch: searching web for '%s...'", query[:60])
    results = await _call_web_search(query)

    # Converte resultados web para Document
    web_docs: list[Document] = []
    queue_ids: list[str] = list(state.get("pending_embeds") or [])

    for r in results:
        content = r.get("content", "") or r.get("raw_content", "")
        if not content:
            continue
        source = r.get("url", "")
        title = r.get("title", "")

        web_docs.append(
            Document(
                page_content=content,
                metadata={"source": source, "title": title, "origin": "web_search"},
                relevance_score=None,
            )
        )

        # Cascading automático: enfileira para LanceDB
        if settings.embedding_queue_enabled:
            qid = await _enqueue_for_embedding(
                content,
                collection="articles",
                metadata={"source": source, "title": title, "origin": "web_search"},
            )
            if qid:
                queue_ids.append(qid)

    # Combina docs vetoriais existentes com os da web
    existing_docs = state.get("rag_docs") or []
    all_docs = existing_docs + web_docs

    logger.info(
        "rag_websearch: %d web results, %d queued for embedding",
        len(web_docs),
        len(queue_ids),
    )

    return {
        "rag_docs": all_docs,
        "web_search_triggered": True,
        "pending_embeds": queue_ids,
    }


async def rag_inject(state: State) -> dict:
    """Nó 4: Injeta os documentos RAG como contexto para o call_llm.

    Adiciona uma SystemMessage com os documentos recuperados antes do histórico.
    O call_llm irá encontrar este contexto e usá-lo para formular a resposta.
    """
    docs = state.get("rag_docs") or []
    query = state.get("rag_query") or ""

    if not docs:
        logger.debug("rag_inject: no docs to inject")
        return {}

    # Formata documentos como bloco de contexto
    lines = [
        "## Contexto Recuperado (RAG)\n",
        f"Query: {query}\n",
        f"Documentos encontrados: {len(docs)}\n\n",
    ]

    for i, doc in enumerate(docs[:5], 1):  # máximo 5 docs para não estourar contexto
        content = doc.get("page_content", "")
        meta = doc.get("metadata", {})
        source = meta.get("source", "")
        title = meta.get("title", "")
        score = doc.get("relevance_score")

        lines.append(f"### [{i}] {title or source or 'Documento'}")
        if source:
            lines.append(f"Fonte: {source}")
        if score is not None:
            lines.append(f"Score: {score:.3f}")
        lines.append(f"\n{content[:800]}\n")  # trunca para economizar tokens

    context_text = "\n".join(lines)

    # Injeta como SystemMessage adicional no histórico
    # Nota: add_messages irá appender esta mensagem ao histórico existente
    context_msg = SystemMessage(
        content=context_text,
        name="rag_context",
    )

    logger.info("rag_inject: injected %d docs into context", len(docs))

    return {"messages": [context_msg]}


# ---------------------------------------------------------------------------
# Construtor do subgrafo
# ---------------------------------------------------------------------------


def build_rag_subgraph():  # type: ignore[return]  # noqa: ANN201
    """Constrói e compila o subgrafo RAG.

    Returns:
        CompiledStateGraph pronto para ser usado como nó no grafo principal.
    """
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(State)  # ty: ignore[invalid-argument-type]

    builder.add_node("rag_retrieve", rag_retrieve)
    builder.add_node("rag_decide_node", _rag_decide_node)  # wrapper para nó síncrono
    builder.add_node("rag_rerank", rag_rerank)
    builder.add_node("rag_websearch", rag_websearch)
    builder.add_node("rag_inject", rag_inject)

    builder.add_edge(START, "rag_retrieve")
    builder.add_edge("rag_retrieve", "rag_decide_node")

    # Roteamento condicional baseado na qualidade dos docs
    builder.add_conditional_edges(
        "rag_decide_node",
        _route_after_decide,
        {
            "rag_inject": "rag_inject",
            "rag_rerank": "rag_rerank",
            "rag_websearch": "rag_websearch",
        },
    )

    builder.add_edge("rag_rerank", "rag_inject")
    builder.add_edge("rag_websearch", "rag_inject")
    builder.add_edge("rag_inject", END)

    return builder.compile()


# Wrapper síncrono para o nó decide (LangGraph exige que nós retornem dict)
async def _rag_decide_node(state: State) -> dict:
    """Nó de decisão — não altera estado, apenas serve de pivot para conditional_edges."""
    return {}


def _route_after_decide(state: State) -> str:
    """Função de roteamento chamada por add_conditional_edges após _rag_decide_node."""
    return rag_decide(state)
