"""Curadoria de resultados web antes de persistir no RAG (Bloco A5.2).

Conteúdo da web é a **única superfície de contaminação** do RAG do Vectora.
RAG local é seguro: o usuário escolhe o que indexar. Mas o cascading
automático das web tools indexava *todo* resultado de busca, misturando
lixo com os docs curados — e sem forma de desfazer.

Este módulo é o gate de qualidade. Nenhum resultado web é persistido sem:

    resultados web (N)
      → CohereRerank contra a query → relevance_score por resultado
      → descarta score < settings.web_persist_min_score
      → LLM judge (1 call estruturada, batch) avalia os sobreviventes
      → aprovados são enfileirados no bucket web; rejeitados, descartados

`curate_and_enqueue` é o ponto de entrada usado pelos dois call-sites de
cascading (process_retrieval em engine.py, rag_websearch em rag_subgraph.py).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from vectora.config.settings import settings
from vectora.state import Document
from vectora.types import CurationDecision, WebResultVerdict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schemas do LLM judge
# ---------------------------------------------------------------------------


_JUDGE_PROMPT = """Você é o curador da base de conhecimento (RAG) do Vectora.

Sua tarefa: decidir quais resultados de busca web merecem ser PERSISTIDOS na
base vetorial do projeto. Conteúdo persistido vira fonte da verdade para
respostas futuras — lixo persistido contamina o projeto permanentemente.

Critérios para keep=true:
- O conteúdo é DIRETAMENTE relevante à query e ao projeto descrito no contexto
- A fonte é confiável e específica (doc oficial, repositório correto, referência técnica)
- Agrega informação útil e não-genérica

Critérios para keep=false (descartar):
- Conteúdo genérico, tangencial ou só superficialmente relacionado
- Fonte duvidosa: listagem de marketplace, agregador, SEO spam
- Trata de um projeto/produto HOMÔNIMO porém diferente do projeto-alvo
- Página de navegação, índice ou conteúdo sem substância

Na dúvida, prefira keep=false. É melhor não indexar do que contaminar a base.
Avalie cada resultado pelo seu índice. Responda com um verdict por resultado."""


_judge_llm: Any = None


def _get_judge_llm() -> Any:
    """Obtém o LLM judge singleton (structured output → CurationDecision)."""
    global _judge_llm
    if _judge_llm is None:
        from vectora.services.utils import load_llm

        _judge_llm = load_llm().with_structured_output(CurationDecision)
        logger.debug("web_curation: LLM judge inicializado")
    return _judge_llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _result_text(r: dict[str, Any]) -> str:
    """Extrai o texto de um resultado web (content ou raw_content)."""
    return (r.get("content") or r.get("raw_content") or "").strip()


async def _rerank_results(
    results: list[dict[str, Any]], query: str
) -> list[tuple[dict[str, Any], float]]:
    """Reranqueia os resultados web contra a query.

    Returns:
        Lista [(resultado, score)]. Se o reranker estiver indisponível, todos
        recebem score 1.0 — passam o gate do reranker e o LLM judge decide.
    """
    try:
        from langchain_cohere import CohereRerank
        from langchain_core.documents import Document as LCDoc
        from pydantic import SecretStr

        api_key = settings.get_cohere_api_key()
        if not api_key:
            logger.warning("web_curation: sem COHERE_API_KEY, judge decide sozinho")
            return [(r, 1.0) for r in results]

        lc_docs: list[LCDoc] = []
        for i, r in enumerate(results):
            text = _result_text(r)
            if text:
                lc_docs.append(LCDoc(page_content=text, metadata={"_idx": i}))

        if not lc_docs:
            return []

        reranker = CohereRerank(
            cohere_api_key=SecretStr(api_key),
            model=settings.reranker_model,
            top_n=len(lc_docs),  # queremos TODOS pontuados, não só o top-k
        )
        reranked = reranker.compress_documents(lc_docs, query)

        scored: list[tuple[dict[str, Any], float]] = []
        for doc in reranked:
            idx = doc.metadata.get("_idx")
            # CohereRerank grava o score em metadata['relevance_score'].
            score = float(doc.metadata.get("relevance_score") or 0.0)
            if idx is not None and 0 <= idx < len(results):
                scored.append((results[idx], score))
        return scored
    except Exception:
        logger.warning("web_curation: rerank falhou, judge decide sozinho")
        return [(r, 1.0) for r in results]


async def _judge(
    survivors: list[tuple[dict[str, Any], float]],
    query: str,
    *,
    task: str | None,
    project_context: str | None,
) -> dict[int, WebResultVerdict]:
    """LLM judge — uma única call em batch sobre os sobreviventes do reranker.

    Returns:
        {index: verdict}. Dict vazio se o judge falhar — o caller trata isso
        como fail-safe (rejeita tudo: melhor não indexar do que contaminar).
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    items: list[str] = []
    for i, (r, score) in enumerate(survivors):
        content = _result_text(r)[:1200]
        items.append(
            f"### Resultado [{i}]\n"
            f"Título: {r.get('title', '')}\n"
            f"URL: {r.get('url', '')}\n"
            f"Score reranker: {score:.2f}\n"
            f"Conteúdo:\n{content}\n"
        )

    project_block = (
        f"\n## Contexto do projeto\n{project_context[:3000]}\n"
        if project_context
        else ""
    )
    task_block = f"\n## Tarefa atual\n{task}\n" if task else ""

    human = HumanMessage(
        content=(
            f"Query da busca: {query}\n"
            f"{project_block}{task_block}\n"
            f"## Resultados a avaliar ({len(survivors)})\n\n"
            + "\n".join(items)
            + f"\n\nPara CADA resultado [0..{len(survivors) - 1}], "
            "decida keep=true (persistir) ou keep=false (descartar)."
        )
    )

    try:
        llm = _get_judge_llm()
        decision: CurationDecision = await llm.ainvoke(
            [SystemMessage(content=_JUDGE_PROMPT), human]
        )
        return {v.index: v for v in decision.verdicts}
    except Exception:
        logger.exception("web_curation: LLM judge falhou — fail-safe: rejeita tudo")
        return {}


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


async def curate_web_results(
    results: list[dict[str, Any]],
    query: str,
    *,
    task: str | None = None,
    project_context: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Aplica o gate de curadoria (reranker + LLM judge) aos resultados web.

    Args:
        results: resultados brutos da web (dicts com content/url/title)
        query: query da busca — usada no reranker e no judge
        task: task delegada pelo orchestrator (sinal extra de relevância)
        project_context: AGENTS.md/CLAUDE.md do projeto — diz ao judge o que
            é "o projeto", essencial para distinguir homônimos

    Returns:
        (approved, rejected). Cada item é o dict original enriquecido com
        'relevance_score' e 'curation_reason'.
    """
    if not results:
        return [], []

    # Kill-switch: sem gate, aprova tudo (comportamento legado).
    if not settings.web_curation_enabled:
        passthrough = [
            {**r, "relevance_score": None, "curation_reason": "curation disabled"}
            for r in results
        ]
        return passthrough, []

    # Etapa 1 — reranker
    scored = await _rerank_results(results, query)
    threshold = settings.web_persist_min_score
    survivors = [(r, s) for r, s in scored if s >= threshold]
    rejected: list[dict[str, Any]] = [
        {
            **r,
            "relevance_score": s,
            "curation_reason": f"reranker score {s:.2f} < {threshold}",
        }
        for r, s in scored
        if s < threshold
    ]

    if not survivors:
        logger.info(
            "web_curation: 0/%d resultados sobreviveram ao reranker", len(results)
        )
        return [], rejected

    # Etapa 2 — LLM judge
    verdicts = await _judge(
        survivors, query, task=task, project_context=project_context
    )

    approved: list[dict[str, Any]] = []
    for i, (r, score) in enumerate(survivors):
        verdict = verdicts.get(i)
        if verdict is None:
            # Judge não cobriu este índice (ou falhou) → fail-safe: descarta.
            rejected.append(
                {
                    **r,
                    "relevance_score": score,
                    "curation_reason": "LLM judge não avaliou — descartado por segurança",
                }
            )
            continue
        enriched = {**r, "relevance_score": score, "curation_reason": verdict.reason}
        (approved if verdict.keep else rejected).append(enriched)

    logger.info(
        "web_curation: %d aprovados, %d rejeitados de %d resultados",
        len(approved),
        len(rejected),
        len(results),
    )
    return approved, rejected


async def curate_and_enqueue(
    results: list[dict[str, Any]],
    query: str,
    *,
    task: str | None = None,
    project_context: str | None = None,
    collection: str | None = None,
) -> tuple[list[Document], list[str]]:
    """Roda o gate de curadoria e enfileira só os aprovados para embedding.

    Args:
        results: resultados brutos da web
        query: query da busca
        task: task delegada pelo orchestrator
        project_context: contexto do projeto (AGENTS.md etc.)
        collection: bucket LanceDB de destino (default: settings.rag_collection_web)

    Returns:
        (formatted_docs, queue_ids).
        - formatted_docs: TODOS os resultados como Document — contexto imediato
          do LLM no turno atual (transiente, não é contaminação).
        - queue_ids: apenas dos resultados APROVADOS — o que de fato é
          persistido no LanceDB.
    """
    collection = collection or settings.rag_collection_web

    approved, rejected = await curate_web_results(
        results, query, task=task, project_context=project_context
    )

    for r in rejected:
        logger.info(
            "web_curation rejeitado: %s — %s",
            r.get("url", "?"),
            r.get("curation_reason", ""),
        )

    # Contexto imediato — todos os resultados (transiente, não persiste)
    formatted_docs: list[Document] = []
    for r in results:
        content = _result_text(r)
        if content:
            formatted_docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "source": "web_search",
                    },
                    relevance_score=r.get("relevance_score"),
                )
            )

    # Persistência — só os aprovados, no bucket web
    from vectora.tools.rag import embedding

    queue_ids: list[str] = []
    for r in approved:
        content = _result_text(r)
        if not content:
            continue
        metadata = {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "source": r.get("url", ""),
            "origin": "web_search",
            "relevance_score": r.get("relevance_score"),
            "curation_reason": r.get("curation_reason", ""),
            "indexed_for_query": query[:200],
            "indexed_at": datetime.now(UTC).isoformat(),
        }
        try:
            raw = await embedding.ainvoke(
                {"text": content, "collection": collection, "metadata": metadata}
            )
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, dict) and data.get("queue_id"):
                queue_ids.append(data["queue_id"])
        except Exception:
            logger.warning("web_curation: falha ao enfileirar resultado aprovado")

    logger.info(
        "web_curation: %d/%d resultados persistidos no bucket '%s'",
        len(queue_ids),
        len(results),
        collection,
    )
    return formatted_docs, queue_ids
