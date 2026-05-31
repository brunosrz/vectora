"""RAG Subgraph — Pipeline completo de Retrieval-Augmented Generation.

Fluxo:
  START → rag_expand_query → rag_retrieve → rag_decide → rag_rerank  → rag_inject → END
                                                        ↘ rag_websearch → rag_inject → END

Integração com o grafo principal:
  - Entra como nó "rag_subgraph" vindo do router
  - Ao terminar, devolve controle para "call_llm" via END do subgrafo

Melhorias C1-C3:
  C1 — Hybrid RAG: dense (Cohere) + BM25 sparse com RRF merge
  C2 — Multi-query: LLM gera N variantes da query para aumentar recall
  C3 — HyDE: documento hipotético quando score inicial é baixo
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.config.settings import settings
from src.state import Document, State

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
        except (TypeError, ValueError):
            return None
    dist = r.get("score")
    if dist is not None:
        try:
            return 1.0 / (1.0 + float(dist))
        except (TypeError, ValueError):
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


# ---------------------------------------------------------------------------
# C1 — Hybrid RAG: BM25 + RRF
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    """Tokenização simples para BM25 — divide por palavras e lowercasa.

    Usa regex em vez de NLTK para manter o código multilíngue sem deps extras.
    Funciona bem para PT-BR, inglês e código-fonte (tokens alfanuméricos).
    """
    return re.findall(r"\w+", text.lower())


def _bm25_search(
    query: str, docs: list[Document], n_results: int = 5
) -> list[Document]:
    """Rerank de docs usando BM25Okapi — retorna top N por score esparso.

    Se `rank-bm25` não estiver disponível ou a lista estiver vazia, devolve os
    docs originais truncados a n_results (degradação graciosa).
    """
    if not docs:
        return []
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        logger.debug("rank-bm25 não disponível, skip BM25")
        return docs[:n_results]

    corpus = [_tokenize(d.get("page_content", "")) for d in docs]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(_tokenize(query))

    ranked = sorted(zip(scores, docs, strict=False), key=lambda x: x[0], reverse=True)
    return [doc for _, doc in ranked[:n_results]]


def _rrf_merge(
    dense_docs: list[Document],
    sparse_docs: list[Document],
    k: int = 60,
    n_results: int = 5,
) -> list[Document]:
    """Reciprocal Rank Fusion — combina rankings denso e esparso.

    RRF score = Σ 1/(k + rank_i + 1) para cada lista i que contém o doc.
    k=60 é o valor canônico da literatura (Cormack et al., 2009).
    """

    def _doc_key(doc: Document) -> str:
        meta = doc.get("metadata") or {}
        return meta.get("source", "") + "|" + (doc.get("page_content") or "")[:80]

    rrf_scores: dict[str, float] = {}
    doc_map: dict[str, Document] = {}

    for rank, doc in enumerate(dense_docs):
        key = _doc_key(doc)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        doc_map[key] = doc

    for rank, doc in enumerate(sparse_docs):
        key = _doc_key(doc)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        doc_map.setdefault(key, doc)

    sorted_keys = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)
    return [doc_map[key] for key in sorted_keys[:n_results]]


async def _call_vector_search(
    query: str, collection: str = "articles", limit: int = 5
) -> list[Document]:
    """Chama vector_search diretamente (sem passar pelo ToolNode) e retorna lista de Document."""
    from src.tools.rag import vector_search  # importação local para evitar ciclo

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


async def _call_vector_search_all(
    query: str,
    limit: int = 5,
    workspace_id: str | None = None,
) -> list[Document]:
    """Busca em TODAS as coleções LanceDB e mescla resultados com hybrid RAG (C1).

    Antes consultava apenas dois nomes fixos (`articles` + `web_cache`). Agora
    descobre as tabelas via `table_names()` e busca em cada uma, em paralelo.
    "Indexou → o RAG acha", qualquer que seja a coleção.

    **C1 — Hybrid RAG (BM25 + Dense + RRF)**:
    Quando `settings.rag_hybrid_enabled`, usa `rag_hybrid_fetch_limit` (20)
    candidatos por coleção, re-ranqueia com BM25 e funde os dois rankings via
    Reciprocal Rank Fusion — maior recall sem perder precisão.

    Resultados da coleção web recebem `metadata["origin"]="web_search"`.

    Quando `workspace_id` é fornecido (B5), filtra por workspace pós-retrieval.
    """
    import asyncio

    collections = await _list_collections()
    if not collections:
        return []

    # C1: usa pool maior para dar mais candidatos ao BM25
    fetch_limit = (
        settings.rag_hybrid_fetch_limit if settings.rag_hybrid_enabled else limit
    )

    results = await asyncio.gather(
        *[_call_vector_search(query, name, fetch_limit) for name in collections],
        return_exceptions=True,
    )

    web_collection = settings.rag_collection_web
    dense_docs: list[Document] = []
    for name, res in zip(collections, results, strict=False):
        if not isinstance(res, list):
            continue
        if name == web_collection:
            for d in res:
                meta = d.get("metadata") or {}
                meta.setdefault("origin", "web_search")
                d["metadata"] = meta
        dense_docs.extend(res)

    # Filtro por workspace (B5)
    if workspace_id:
        filtered: list[Document] = []
        for doc in dense_docs:
            meta = doc.get("metadata") or {}
            doc_ws = meta.get("workspace_id")
            if doc_ws is None or doc_ws in (workspace_id, "__global__"):
                filtered.append(doc)
        dense_docs = filtered

    if not dense_docs:
        return []

    # C1 — BM25 + RRF: reranqueia os candidatos densos com BM25 e funde
    if settings.rag_hybrid_enabled and len(dense_docs) > 1:
        sparse_docs = _bm25_search(query, dense_docs, n_results=limit)
        docs = _rrf_merge(dense_docs, sparse_docs, n_results=limit)
    else:
        docs = dense_docs[:limit]

    return docs


# ---------------------------------------------------------------------------
# C2 — Multi-query retrieval
# ---------------------------------------------------------------------------


async def _generate_query_variants(query: str, n: int = 3) -> list[str]:
    """LLM gera N reformulações da query para aumentar o recall vetorial (C2).

    Retorna a lista de variantes incluindo a query original.
    Em caso de falha (sem API key, LLM indisponível), retorna só a original.
    """
    from src.services.utils import load_llm

    try:
        llm = load_llm()
        prompt = (
            f"Gere {n - 1} reformulações diferentes desta query para busca semântica.\n"
            f"Cada variante deve cobrir ângulos distintos do mesmo tema.\n"
            f"Responda APENAS com as variantes, uma por linha, sem numeração.\n\n"
            f"Query original: {query}"
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = str(response.content).strip()
        variants = [v.strip() for v in raw.splitlines() if v.strip()]
        # Garante que a query original está na lista e limita ao n pedido
        all_variants = [query] + [v for v in variants if v != query]
        return all_variants[: max(n, 1)]
    except Exception:
        logger.debug(
            "_generate_query_variants: falha ao gerar variantes", exc_info=True
        )
        return [query]


# ---------------------------------------------------------------------------
# C3 — HyDE (Hypothetical Document Embedding)
# ---------------------------------------------------------------------------


async def _hyde_search(query: str, workspace_id: str | None = None) -> list[Document]:
    """Gera um documento hipotético via LLM e usa-o como query de embedding (C3).

    HyDE (Hypothetical Document Embeddings) melhora recall para perguntas
    abstratas onde a query tem pouca sobreposição lexical com os documentos.
    O LLM gera um "modelo de resposta", que é embeddado e buscado.
    """
    from src.services.utils import load_llm

    try:
        llm = load_llm()
        hyde_prompt = (
            "Escreva um trecho técnico conciso (2-4 parágrafos) que responderia "
            "diretamente a esta pergunta. Seja específico e use terminologia técnica.\n\n"
            f"Pergunta: {query}\n\n"
            "Responda apenas com o conteúdo do trecho, sem introduções."
        )
        response = await llm.ainvoke([HumanMessage(content=hyde_prompt)])
        hypothetical_doc = str(response.content).strip()

        if not hypothetical_doc:
            return []

        # O doc hipotético vira a nova query — o vetor do doc responde melhor
        # à pergunta do que o vetor da pergunta em si (lacuna embedding gap).
        hyde_docs = await _call_vector_search_all(
            hypothetical_doc,
            workspace_id=workspace_id,
        )
        logger.debug("HyDE: %d docs via documento hipotético", len(hyde_docs))
        return hyde_docs

    except Exception:
        logger.debug("_hyde_search: falha, skipping HyDE", exc_info=True)
        return []


def _deduplicate_docs(docs: list[Document]) -> list[Document]:
    """Remove docs duplicados por (source, primeiros 80 chars do conteúdo)."""
    seen: set[str] = set()
    result: list[Document] = []
    for doc in docs:
        meta = doc.get("metadata") or {}
        key = meta.get("source", "") + "|" + (doc.get("page_content") or "")[:80]
        if key not in seen:
            seen.add(key)
            result.append(doc)
    return result


async def _call_web_search(query: str) -> list[dict[str, Any]]:
    """Chama web_search diretamente e retorna lista de resultados brutos."""
    from src.tools.web import web_search  # importação local para evitar ciclo

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


async def rag_retrieve(state: State, config: RunnableConfig) -> dict:
    """Nó 2: Executa vector_search com multi-query (C2) e HyDE (C3).

    C2 — Multi-query: usa variantes geradas por `rag_expand_query` (se presentes)
    para buscas paralelas com deduplicação, aumentando recall.

    C3 — HyDE: quando score inicial < `rag_hyde_threshold`, gera documento
    hipotético via LLM e combina os resultados com a busca original.

    Workspace: filtra por workspace_id quando fornecido via config (B5).
    """
    import asyncio
    import contextlib

    from src.services.tracer import tracer

    session_id: str | None = None
    with contextlib.suppress(Exception):
        session_id = state.get("session_metadata", {}).get("thread_id")

    # workspace_id: prioritiza config (runtime), fallback ao state
    workspace_id: str | None = None
    with contextlib.suppress(Exception):
        workspace_id = (config.get("configurable") or {}).get("workspace_id")
    if workspace_id is None:
        workspace_id = state.get("session_metadata", {}).get("workspace_id")  # type: ignore[call-overload]

    query = _extract_query(state)
    if not query:
        logger.warning("rag_retrieve: no query found in state")
        return {"rag_query": "", "rag_docs": [], "rag_query_variants": None}

    logger.info("rag_retrieve: searching for '%s...'", query[:60])

    # C2 — Multi-query: usa variantes se disponíveis (geradas por rag_expand_query)
    variants = state.get("rag_query_variants") or []
    queries_to_search = variants or [query]

    try:
        async with tracer.span("rag_retrieve", "search", session_id=session_id) as s:  # ty: ignore[invalid-argument-type]
            if len(queries_to_search) > 1:
                # Busca paralela para cada variante
                batch_results = await asyncio.gather(
                    *[
                        _call_vector_search_all(q, workspace_id=workspace_id)
                        for q in queries_to_search
                    ]
                )
                all_docs: list[Document] = []
                for batch in batch_results:
                    all_docs.extend(batch)
                docs = _deduplicate_docs(all_docs)
                logger.info(
                    "rag_retrieve: multi-query %d variantes → %d docs únicos",
                    len(queries_to_search),
                    len(docs),
                )
            else:
                docs = await _call_vector_search_all(query, workspace_id=workspace_id)

            best = _best_score(docs)
            s.set(
                n_docs=len(docs),
                best_score=round(best, 3),
                query_len=len(query),
                n_variants=len(queries_to_search),
            )
    except Exception:
        docs = await _call_vector_search_all(query, workspace_id=workspace_id)
        best = _best_score(docs)

    # C3 — HyDE: se score inicial < threshold, tenta com documento hipotético
    if (
        settings.rag_hyde_enabled
        and best < settings.rag_hyde_threshold
        and query  # não roda se não há query
    ):
        logger.debug(
            "rag_retrieve: score %.3f < %.3f, tentando HyDE",
            best,
            settings.rag_hyde_threshold,
        )
        hyde_docs = await _hyde_search(query, workspace_id=workspace_id)
        if hyde_docs:
            combined = _deduplicate_docs(docs + hyde_docs)
            logger.info(
                "rag_retrieve: HyDE adicionou %d docs (total %d)",
                len(hyde_docs),
                len(combined),
            )
            docs = combined

    logger.info(
        "rag_retrieve: found %d docs, best_score=%.3f", len(docs), _best_score(docs)
    )
    return {"rag_query": query, "rag_docs": docs}


async def rag_expand_query(state: State) -> dict:
    """Nó 1: Gera variantes da query com LLM para multi-query retrieval (C2).

    Quando `settings.rag_multi_query_enabled`, usa o LLM para reformular a query
    em N variantes cobrindo ângulos distintos. `rag_retrieve` recebe essas
    variantes e executa buscas paralelas, aumentando o recall.

    Se desabilitado ou em caso de falha, retorna vazio → `rag_retrieve` usa a
    query original (comportamento pré-C2, degradação graciosa).
    """
    if not settings.rag_multi_query_enabled:
        return {}

    query = _extract_query(state)
    if not query:
        return {}

    variants = await _generate_query_variants(query, n=settings.rag_multi_query_n)

    if len(variants) <= 1:
        return {}  # Só a original — não há ganho em multi-query

    logger.info(
        "rag_expand_query: %d variantes geradas para '%s...'",
        len(variants),
        query[:50],
    )
    return {"rag_query_variants": variants}


def rag_decide(state: State) -> str:
    """Decide o próximo passo com base na qualidade dos resultados.

    Retorna o nome do próximo nó (usado como valor em add_conditional_edges).

    score ≥ 0.7 → rag_inject  (alta confiança — injeta direto)
    score ≥ 0.4 → rag_rerank  (média confiança — rerank antes de injetar)
    score < 0.4 → search      (baixa confiança — delega para o search real com rag_pending=True)
    """
    docs = state.get("rag_docs") or []
    score = _best_score(docs)

    if score >= _SCORE_HIGH:
        logger.debug("rag_decide: score=%.3f → rag_inject (direto)", score)
        return "rag_inject"
    if score >= _SCORE_LOW:
        logger.debug("rag_decide: score=%.3f → rag_rerank", score)
        return "rag_rerank"

    logger.debug("rag_decide: score=%.3f → search (rag_pending)", score)
    return "search"


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

    from src.nodes.web_curation import curate_and_enqueue

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


_AUDIT_TOOLS = None


def _get_audit_tools() -> list:
    """Ferramentas disponíveis para o auditor RAG (subconjunto de ALL_TOOLS)."""
    global _AUDIT_TOOLS
    if _AUDIT_TOOLS is None:
        from src.nodes.tools import ALL_TOOLS

        _audit_names = frozenset(
            {
                "manage_retriever",
                "fetch_url",
                "embedding",
                "web_search",
                "vector_search",
            }
        )
        _AUDIT_TOOLS = [t for t in ALL_TOOLS if t.name in _audit_names]
        logger.debug("audit tools: %s", [t.name for t in _AUDIT_TOOLS])
    return _AUDIT_TOOLS


_audit_llm = None


def _get_audit_llm() -> object:
    """LLM singleton do auditor RAG, com ferramentas de auditoria."""
    global _audit_llm
    if _audit_llm is None:
        from src.services.utils import load_llm

        _audit_llm = load_llm().bind_tools(_get_audit_tools())  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        logger.debug("audit LLM inicializado")
    return _audit_llm


async def rag_search_audit(state: State) -> dict:
    """Nó de auditoria pós-rerank: Search Agent valida e corrige os docs recuperados.

    Roda após `rag_rerank` (score médio) e após `rag_websearch` (score baixo) —
    nos dois caminhos onde há maior chance de conteúdo errado ou homônimo.

    Fluxo interno (mini agent loop, máx 3 iterações):
      audit_llm → [tool_calls?] → ToolNode → audit_llm → ... → done

    Ferramentas disponíveis para o auditor:
    - `manage_retriever action="delete"` — remove fonte errada do bucket
    - `manage_retriever action="list"`  — inspeciona o que está indexado
    - `fetch_url`    — busca fonte canônica fornecida pelo usuário
    - `embedding`    — indexa conteúdo correto no bucket `search`
    - `web_search`   — busca adicional quando necessário
    - `vector_search` — verifica o que já está no RAG

    Conteúdo novo vai para `settings.rag_collection_search` ("search") —
    separado de `articles` (usuário) e `web_cache` (web automático).

    Não re-executa o pipeline RAG completo. Conteúdo indexado agora aparece
    na próxima query. O valor imediato é a limpeza de entradas erradas.
    """
    import asyncio

    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )
    from langgraph.prebuilt.tool_node import ToolNode

    docs = state.get("rag_docs") or []
    query = state.get("rag_query") or _extract_query(state)

    if not query or not docs:
        return {}

    # Monta sumário dos docs recuperados para o auditor avaliar
    doc_summary_lines = []
    for i, doc in enumerate(docs[:5], 1):
        meta = doc.get("metadata") or {}
        source = meta.get("source", "")
        score = doc.get("relevance_score")
        preview = (doc.get("page_content") or "")[:200].replace("\n", " ")
        score_str = f" (score={score:.3f})" if score is not None else ""
        doc_summary_lines.append(f"[{i}]{score_str} {source}\n  {preview}")
    doc_summary = "\n".join(doc_summary_lines)

    # Extrai mensagens recentes do usuário para detectar URLs canônicas fornecidas
    recent_human = ""
    for msg in reversed(state.get("messages", [])[-6:]):
        if isinstance(msg, HumanMessage):
            recent_human = str(msg.content)[:500]
            break

    audit_system = f"""Você é o **Search Agent** do Vectora no papel de auditor do RAG.

O pipeline RAG acabou de recuperar e reranquear documentos para a query abaixo.
Sua tarefa é validar se esses documentos são genuinamente relevantes.

**Ações disponíveis:**
1. Se um doc é claramente de projeto errado ou homônimo → `manage_retriever action="delete"` com o source.
2. Se o usuário forneceu uma URL canônica recentemente → `fetch_url` + `embedding` no bucket `{settings.rag_collection_search}`.
3. Se os docs parecem corretos → responda "OK" sem chamar tools.

**Regras:**
- Não chame `vector_search` para re-buscar — o pipeline já fez isso.
- Conteúdo indexado agora aparece em queries futuras, não nesta.
- Seja cirúrgico: delete apenas o que é **claramente** errado.
- Máximo 2 ações de tool por auditoria.

**Query:** {query}
**Mensagem recente do usuário:** {recent_human or "(nenhuma)"}

**Documentos recuperados ({len(docs)}):**
{doc_summary}
"""

    audit_messages = [
        SystemMessage(content=audit_system),
        HumanMessage(content=f"Audite os documentos para a query: {query}"),
    ]

    audit_tools = _get_audit_tools()
    audit_tool_node = ToolNode(tools=audit_tools)
    llm = _get_audit_llm()

    # Mini agent loop — máx 3 iterações para evitar loop infinito
    max_audit_steps = 3
    for step in range(max_audit_steps):
        try:
            response = await llm.ainvoke(audit_messages)  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
            audit_messages.append(response)

            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                # Sem tool_calls — auditoria concluída
                logger.info(
                    "rag_search_audit: concluída em %d iteração(ões) — %s",
                    step + 1,
                    str(getattr(response, "content", ""))[:80],
                )
                break

            # Executa as tool_calls via ToolNode
            tool_input: State = {"messages": audit_messages}  # type: ignore[assignment]  # ty: ignore[missing-typed-dict-key]
            tool_output = await asyncio.to_thread(
                lambda ti=tool_input: audit_tool_node.invoke(ti)
            )
            tool_msgs = tool_output.get("messages", [])
            # Adiciona apenas as ToolMessages novas (não re-adiciona as anteriores)
            new_tool_msgs = [m for m in tool_msgs if isinstance(m, ToolMessage)]
            audit_messages.extend(new_tool_msgs)

            logger.debug(
                "rag_search_audit step %d: %d tool_calls executadas",
                step + 1,
                len(tool_calls),
            )

        except Exception:
            logger.exception("rag_search_audit: falha na iteração %d", step + 1)
            break

    return {}


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
    """Constrói e compila o subgrafo RAG com C1/C2/C3 + auditoria pós-rerank.

    Fluxo:
      START → rag_expand_query (C2) → rag_retrieve (C1+C3) → rag_decide_node
                → rag_inject                      (score alto  ≥ 0.7 — alta confiança)
                → rag_rerank → rag_search_audit → rag_inject  (score médio ≥ 0.4)
                → rag_websearch → rag_search_audit → rag_inject (score baixo < 0.4)
              → END

    `rag_search_audit` (Search Agent) roda após o reranker nos caminhos de
    menor confiança. Pode chamar manage_retriever/fetch_url/embedding para
    corrigir a base antes do inject. Score alto vai direto — já tem confiança
    suficiente para não precisar de auditoria.

    Returns:
        CompiledStateGraph pronto para ser usado como nó no grafo principal.
    """
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(State)  # ty: ignore[invalid-argument-type]

    builder.add_node("rag_expand_query", rag_expand_query)  # C2 multi-query
    builder.add_node("rag_retrieve", rag_retrieve)
    builder.add_node("rag_decide_node", _rag_decide_node)  # wrapper para nó síncrono
    builder.add_node("rag_rerank", rag_rerank)
    builder.add_node("rag_websearch", rag_websearch)
    builder.add_node("rag_search_audit", rag_search_audit)  # Search Agent pós-rerank
    builder.add_node("rag_inject", rag_inject)

    builder.add_edge(START, "rag_expand_query")
    builder.add_edge("rag_expand_query", "rag_retrieve")
    builder.add_edge("rag_retrieve", "rag_decide_node")

    # Roteamento condicional baseado na qualidade dos docs
    builder.add_conditional_edges(
        "rag_decide_node",
        _route_after_decide,
        {
            "rag_inject": "rag_inject",  # score alto → injeta direto
            "rag_rerank": "rag_rerank",  # score médio → rerank → audit
            "rag_websearch": "rag_websearch",  # score baixo → web → audit
        },
    )

    # Ambos os caminhos de menor confiança passam pelo Search Agent auditor
    builder.add_edge("rag_rerank", "rag_search_audit")
    builder.add_edge("rag_websearch", "rag_search_audit")
    builder.add_edge("rag_search_audit", "rag_inject")
    builder.add_edge("rag_inject", END)

    return builder.compile()


# Wrapper síncrono para o nó decide (LangGraph exige que nós retornem dict)
async def _rag_decide_node(state: State) -> dict:
    """Nó de decisão — seta rag_pending quando score é baixo (roteamento para search)."""
    docs = state.get("rag_docs") or []
    score = _best_score(docs)
    # Quando score < _SCORE_LOW, _route_after_decide retorna "search".
    # Precisamos marcar rag_pending=True para que search_finalize saiba
    # que deve retornar para rag_inject em vez do orchestrator.
    if score < _SCORE_LOW:
        return {"rag_pending": True}
    return {}


def _route_after_decide(state: State) -> str:
    """Função de roteamento chamada por add_conditional_edges após _rag_decide_node."""
    return rag_decide(state)
