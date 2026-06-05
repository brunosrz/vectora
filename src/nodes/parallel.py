"""parallel_dispatch node — home permanente (movido de src/graph.py para E5)."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.agents.orchestrator import _PARALLEL_AGENT_PROMPTS

if TYPE_CHECKING:
    from src.state import State

logger = logging.getLogger(__name__)


async def parallel_dispatch(state: State, config: RunnableConfig) -> dict[str, Any]:
    """Executa múltiplas tasks de agentes em paralelo via asyncio.gather.

    Cada task é executada chamando o LLM com o prompt do agent correspondente.
    Em modo paralelo, agentes respondem diretamente sem tool calls.
    """
    from src.services.utils import load_llm

    tasks = state.get("parallel_tasks") or []  # type: ignore[attr-defined]
    if not tasks:
        logger.info("parallel_dispatch: nenhuma task, retornando vazio")
        return {"parallel_results": []}

    async def _run_task(task: Any) -> dict[str, Any]:
        agent = task.get("agent", "search")
        task_query = task.get("task_query", "")
        reason = task.get("reason", "")

        system_prompt = _PARALLEL_AGENT_PROMPTS.get(
            agent, _PARALLEL_AGENT_PROMPTS["search"]
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=task_query),
        ]

        try:
            llm = load_llm()
            response = await llm.ainvoke(messages, config=config)
            return {
                "agent": agent,
                "task": task_query,
                "reason": reason,
                "response": str(getattr(response, "content", response)),
                "success": True,
            }
        except Exception as e:
            logger.warning("parallel_dispatch: task[%s] falhou: %s", agent, e)
            return {
                "agent": agent,
                "task": task_query,
                "reason": reason,
                "response": f"Erro ao executar task: {e}",
                "success": False,
            }

    logger.info("parallel_dispatch: executando %d tasks em paralelo", len(tasks))
    results = await asyncio.gather(*[_run_task(t) for t in tasks])
    logger.info(
        "parallel_dispatch: %d/%d tasks bem-sucedidas",
        sum(1 for r in results if r.get("success")),
        len(results),
    )
    return {"parallel_results": list(results)}
