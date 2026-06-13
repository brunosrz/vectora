"""Engine — process_retrieval: cascading curado de web_search → LanceDB.

A lógica de call_llm vive em base.py (invoke_llm); cada worker usa sua
própria instância de LLM.

Responsabilidade atual:
- process_retrieval: detecta resultados de web_search e os passa pelo gate
  de curadoria (web_curation) antes de qualquer persistência no LanceDB.
  Antes do Bloco A5 isso enfileirava todo resultado indiscriminadamente —
  a única superfície de contaminação do RAG. Agora reranker + LLM judge
  decidem o que merece virar fonte da verdade.
- _extract_tavily_results: helper de parsing dos resultados Tavily.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, ToolMessage

from src.nodes.web_curation import curate_and_enqueue

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

    from src.context import Context
    from src.state import State

logger = logging.getLogger(__name__)


def _last_human_text(messages: list) -> str:
    """Extrai o texto da última HumanMessage — query para o gate de curadoria."""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return str(msg.content).strip()
    return ""


async def process_retrieval(state: State, runtime: Runtime[Context]) -> dict:
    """Cascading curado: web_search → gate de curadoria → LanceDB.

    Monitora as últimas ToolMessages. Quando detecta resultados de web_search,
    passa-os por `curate_and_enqueue` — reranker + LLM judge — que persiste
    apenas o conteúdo aprovado no bucket web. Os queue_ids dos aprovados são
    rastreados em state['pending_embeds'].

    fetch_url não entra no cascading: o usuário escolheu aquela URL
    explicitamente (intenção de leitura, não de indexação) e o conteúdo é
    texto puro, não uma lista de resultados.
    """
    messages = state["messages"]
    if not messages:
        return {}

    current_retrieval = state.get("retrieval_results") or {}
    all_queue_ids: list[str] = list(state.get("pending_embeds") or [])
    new_results_found = False
    web_triggered = False

    # Sinais que o gate de curadoria usa para julgar relevância ao projeto.
    query = _last_human_text(list(messages))
    task = state.get("orchestrator_task")
    project_context = state.get("project_context")

    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            break
        if msg.name != "web_search":
            continue

        try:
            data = json.loads(
                msg.content if isinstance(msg.content, str) else str(msg.content)
            )
        except json.JSONDecodeError:
            logger.warning(
                "process_retrieval: JSON inválido",
                extra={"tool": msg.name, "preview": str(msg.content)[:100]},
            )
            continue

        results = _extract_tavily_results(data, msg.name)
        if not results:
            continue

        formatted_docs, queue_ids = await curate_and_enqueue(
            results,
            query,
            task=task,
            project_context=project_context,
        )
        if not formatted_docs:
            continue

        current_retrieval[msg.name] = formatted_docs
        all_queue_ids.extend(queue_ids)
        new_results_found = True
        web_triggered = True
        logger.info(
            "process_retrieval: cascading curado",
            extra={
                "source": msg.name,
                "docs": len(formatted_docs),
                "persisted": len(queue_ids),
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
    """Extrai a lista de resultados de uma estrutura Tavily flexível."""
    if isinstance(data, dict):
        return data.get("results", [])
    if isinstance(data, list):
        return data
    logger.warning(
        "process_retrieval: formato inesperado",
        extra={"tool": tool_name, "type": type(data).__name__},
    )
    return None
