"""Engine — process_retrieval e helpers de cascading Tavily → LanceDB.

Este módulo foi reduzido ao essencial após a migração para workers especializados.
A lógica de call_llm foi movida para base.py (invoke_llm) e cada worker
(direct_worker, search_worker, coder_worker) usa sua própria instância de LLM.

Responsabilidade atual:
- process_retrieval: detecta resultados de web_search/fetch_url e enfileira
  para embedding no LanceDB (cascading automático fire-and-forget)
- _extract_tavily_results / _process_tavily_results: helpers do cascading
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from langchain_core.messages import ToolMessage

from vectora.state import Document
from vectora.tools import embedding

if TYPE_CHECKING:
    from langchain_core.runnables import Runnable
    from langgraph.runtime import Runtime

    from vectora.context import Context
    from vectora.state import State

logger = logging.getLogger(__name__)


async def process_retrieval(state: State, runtime: Runtime[Context]) -> dict:
    """Cascading automático: web_search/fetch_url → LanceDB (fire-and-forget).

    Monitora as últimas ToolMessages do histórico. Quando detecta resultados
    de web_search ou fetch_url, enfileira o conteúdo para embedding assíncrono
    no LanceDB e rastreia os queue_ids em state['pending_embeds'].
    """
    messages = state["messages"]
    if not messages:
        return {}

    current_retrieval = state.get("retrieval_results") or {}
    all_queue_ids: list[str] = list(state.get("pending_embeds") or [])
    new_results_found = False
    web_triggered = False

    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            break
        if msg.name not in ("web_search", "fetch_url"):
            continue

        try:
            data = json.loads(
                msg.content if isinstance(msg.content, str) else str(msg.content)
            )
        except json.JSONDecodeError:
            logger.warning(
                "process_retrieval: JSON inválido",
                extra={"tool": msg.name, "preview": msg.content[:100]},
            )
            continue

        results = _extract_tavily_results(data, msg.name)
        if not results:
            continue

        formatted_docs, queue_ids = await _process_tavily_results(
            results, msg.name, embedding
        )
        if not formatted_docs:
            continue

        current_retrieval[msg.name] = formatted_docs
        all_queue_ids.extend(queue_ids)
        new_results_found = True
        web_triggered = True
        logger.info(
            "process_retrieval: cascading",
            extra={
                "source": msg.name,
                "docs": len(formatted_docs),
                "queued": len(queue_ids),
            },
        )

    update: dict = {}
    if new_results_found:
        update["retrieval_results"] = current_retrieval
    if all_queue_ids:
        update["pending_embeds"] = all_queue_ids
    if web_triggered:
        update["web_search_triggered"] = True
    return update


def _extract_tavily_results(data: dict | list, tool_name: str) -> list[dict] | None:
    """Extrai lista de resultados de estrutura Tavily flexível."""
    if isinstance(data, dict):
        return data.get("results", [])
    if isinstance(data, list):
        return data
    logger.warning(
        "process_retrieval: formato inesperado",
        extra={"tool": tool_name, "type": type(data).__name__},
    )
    return None


async def _process_tavily_results(
    results: list[dict], source: str, embedding_tool: Runnable
) -> tuple[list[Document], list[str]]:
    """Formata docs Tavily e enfileira cada um para embedding fire-and-forget.

    Returns:
        (formatted_docs, queue_ids)
    """
    formatted_docs: list[Document] = []
    queue_ids: list[str] = []

    for r in results:
        content = r.get("content", "").strip()
        if not content:
            continue

        metadata = {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "source": source,
        }
        formatted_docs.append(Document(page_content=content, metadata=metadata))

        try:
            raw = await embedding_tool.ainvoke(
                input={"text": content, "collection": "articles", "metadata": metadata},
            )
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, dict) and data.get("queue_id"):
                queue_ids.append(data["queue_id"])
                logger.debug(
                    "process_retrieval: enfileirado",
                    extra={"queue_id": data["queue_id"], "source": source},
                )
        except Exception as e:
            logger.warning(
                "process_retrieval: falha ao enfileirar", extra={"error": str(e)}
            )

    return formatted_docs, queue_ids
