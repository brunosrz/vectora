"""Retrieval Node — Executa o RetrievalService (embed + vector search + rerank).

Responsabilidade: dado um query no State, busca documentos no LanceDB,
aplica CohereRerank e injeta o resultado em state['rag_docs'].

Diferença do rag_subgraph:
- rag_subgraph: pipeline completo com decisão de fallback para web_search
- retrieval.py: nó atômico de busca + rerank (sem fallback), usado como
  componente interno pelo rag_subgraph e por workers que precisam de contexto
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vectora.state import Document, State

logger = logging.getLogger(__name__)


async def retrieval_node(state: State) -> dict:
    """Executa vector_search + CohereRerank e popula state['rag_docs'].

    Extrai a query da última HumanMessage, busca no LanceDB e aplica rerank.
    Retorna dict vazio se RAG não estiver habilitado ou sem resultados.
    """
    from vectora.config.settings import settings
    from vectora.nodes.rag_subgraph import _call_vector_search, _extract_query

    if not settings.enable_rag:
        logger.debug("retrieval_node: RAG desabilitado, skipping")
        return {}

    query = _extract_query(state)
    if not query:
        logger.debug("retrieval_node: sem query, skipping")
        return {}

    logger.info("retrieval_node: buscando '%s...'", query[:60])

    import contextlib

    from vectora.services.tracer import tracer

    session_id: int | None = None
    with contextlib.suppress(Exception):
        session_id = state.get("session_metadata", {}).get("thread_id")  # type: ignore[assignment]

    try:
        async with tracer.span("retrieval_node", "search", session_id=session_id) as s:
            docs = await _call_vector_search(query)
            if not docs:
                logger.info("retrieval_node: sem resultados para '%s'", query[:60])
                s.set(n_results=0)
                return {}
            reranked = await _rerank(docs, query)
            logger.info("retrieval_node: %d docs após rerank", len(reranked))
            s.set(n_results=len(reranked))
    except Exception:
        docs = await _call_vector_search(query)
        if not docs:
            return {}
        reranked = await _rerank(docs, query)

    return {"rag_docs": reranked, "rag_query": query}


async def _rerank(docs: list[Document], query: str) -> list[Document]:
    """Aplica CohereRerank nos docs. Retorna docs originais se falhar."""
    from vectora.config.settings import settings
    from vectora.state import Document

    try:
        from langchain_cohere import CohereRerank
        from langchain_core.documents import Document as LCDoc
        from pydantic import SecretStr

        api_key = settings.get_cohere_api_key()
        if not api_key:
            return docs

        reranker = CohereRerank(
            cohere_api_key=SecretStr(api_key),
            model=settings.reranker_model,
            top_n=min(3, len(docs)),
        )
        lc_docs = [
            LCDoc(
                page_content=str(d.get("page_content", "")),
                metadata=d.get("metadata", {}),
            )
            for d in docs
        ]
        reranked = reranker.compress_documents(lc_docs, query)
        return [
            Document(
                page_content=doc.page_content,
                metadata=doc.metadata,
                relevance_score=getattr(doc, "relevance_score", None),
            )
            for doc in reranked
        ]
    except Exception as e:
        logger.warning("retrieval_node: rerank falhou (%s), usando docs originais", e)
        return docs
