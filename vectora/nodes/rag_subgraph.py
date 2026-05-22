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


def _result_score(r: dict[str, Any]) -> float | None:
    """Normaliza o score de um resultado de `vector_search` para similaridade.

    O `vector_search` devolve duas formas conforme o rerank esteja ativo:

    - **com rerank** — chave `relevance_score`: já é uma relevância 0-1 do
      Cohere (maior = melhor). Usada como está.
    - **sem rerank** — chave `score`: é o `_distance` L2 do LanceDB
      (**menor** = melhor). Tratá-la como similaridade inverteria o
      roteamento de `rag_decide`. Converte-se para uma similaridade
      monotônica e limitada em `(0, 1]` via `1 / (1 + distância)`.
    """
    rel = r.get("relevance_score")
    if rel is not None:
        try:
            return float(rel)
        except TypeError, ValueError:
            return None
    dist = r.get("score")
    if dist is not None:
        try:
            return 1.0 / (1.0 + float(dist))
        except TypeError, ValueError:
            return None
    return None


async def _list_collections() -> list[str]:
    """Lista todas as tabelas LanceDB existentes. Retorna [] em qualquer falha."""
    try:
        import lancedb
    except ImportError:
        return []
    if settings.lancedb_dir is None:
        return []
    try:
        db = await lancedb.connect_async(str(settings.lancedb_dir))
        return list(await db.table_names())
    except Exception:
        logger.debug("_list_collections: falha ao listar tabelas", exc_info=True)
        return []


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
                relevance_score=_result_score(r),
            )
            for r in results
        ]
    except Exception:
        logger.exception("rag_retrieve: vector_search failed")
        return []


async def _call_vector_search_all(query: str, limit: int = 5) -> list[Document]:
    """Busca em TODAS as coleções LanceDB existentes e mescla os resultados.

    Antes consultava apenas dois nomes fixos (`articles` + `web_cache`). Mas o
    conteúdo pode ser indexado em outras coleções — `/rag add` infere o nome
    pela extensão/pasta (`code`, `docs`, `notes`…), e a tool `embedding`
    aceita qualquer coleção. Resultado: docs ficavam órfãos, indexados mas
    fora do alcance da busca.

    Agora descobre as tabelas via `table_names()` e busca em cada uma, em
    paralelo. "Indexou → o RAG acha", qualquer que seja a coleção.

    Resultados da coleção web (`rag_collection_web`) recebem
    `metadata["origin"]="web_search"` para o reranker e o LLM ponderarem a
    confiança da fonte.
    """
    import asyncio

    collections = await _list_collections()
    if not collections:
        return []

    results = await asyncio.gather(
        *[_call_vector_search(query, name, limit) for name in collections],
        return_exceptions=True,
    )

    web_collection = settings.rag_collection_web
    docs: list[Document] = []
    for name, res in zip(collections, results, strict=False):
        if not isinstance(res, list):
            continue
        if name == web_collection:
            for d in res:
                meta = d.get("metadata") or {}
                meta.setdefault("origin", "web_search")
                d["metadata"] = meta
        docs.extend(res)
    return docs


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
            docs = await _call_vector_search_all(query)
            best = _best_score(docs)
            s.set(n_docs=len(docs), best_score=round(best, 3), query_len=len(query))
    except Exception:
        docs = await _call_vector_search_all(query)  # fallback sem tracer

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
                relevance_score=doc.metadata.get("relevance_score"),
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

    Os resultados passam pelo gate de curadoria (reranker + LLM judge) antes
    de qualquer persistência — só conteúdo aprovado vai para o bucket web.
    Os resultados completos ainda entram em `rag_docs` como contexto imediato
    do turno (transiente, não é contaminação).
    """
    query = state.get("rag_query") or _extract_query(state)
    existing_ids: list[str] = list(state.get("pending_embeds") or [])
    if not query:
        return {"web_search_triggered": True}

    logger.info("rag_websearch: searching web for '%s...'", query[:60])
    results = await _call_web_search(query)
    if not results:
        return {"web_search_triggered": True, "pending_embeds": existing_ids}

    from vectora.nodes.web_curation import curate_and_enqueue

    web_docs, queue_ids = await curate_and_enqueue(
        results,
        query,
        task=state.get("orchestrator_task"),
        project_context=state.get("project_context"),
    )

    # Combina docs vetoriais existentes com os da web
    existing_docs = state.get("rag_docs") or []
    all_docs = existing_docs + web_docs

    logger.info(
        "rag_websearch: %d resultados web, %d persistidos no bucket web",
        len(web_docs),
        len(queue_ids),
    )

    return {
        "rag_docs": all_docs,
        "web_search_triggered": True,
        "pending_embeds": existing_ids + queue_ids,
    }


async def rag_inject(state: State) -> dict:
    """Nó 4: Injeta os documentos RAG como contexto para o call_llm.

    Adiciona uma SystemMessage com os documentos recuperados antes do histórico.
    O call_llm irá encontrar este contexto e usá-lo para formular a resposta.
    """
    docs = state.get("rag_docs") or []
    query = state.get("rag_query") or ""

    if not docs:
        # Mesmo sem docs, emite o marcador `rag_context`. Ele é o sinal
        # determinístico de que o pipeline RAG já rodou neste turno —
        # o orchestrator o detecta para sintetizar e encerrar. Sem este
        # marcador, o orchestrator não saberia que o RAG já buscou e
        # re-rotearia para o subgrafo (loop infinito → GraphRecursionError).
        empty_msg = SystemMessage(
            content=(
                "## Contexto Recuperado (RAG)\n\n"
                f"Query: {query}\n\n"
                "Nenhum documento relevante foi encontrado na base de "
                "conhecimento indexada para esta consulta."
            ),
            name="rag_context",
        )
        logger.info("rag_inject: nenhum doc — emitindo marcador rag_context vazio")
        return {"messages": [empty_msg]}

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

        origin = meta.get("origin")
        lines.append(f"### [{i}] {title or source or 'Documento'}")
        if source:
            # Marca a procedência: docs curados pelo usuário vs cache web.
            tag = " — fonte: web (cache)" if origin == "web_search" else ""
            lines.append(f"Fonte: {source}{tag}")
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
