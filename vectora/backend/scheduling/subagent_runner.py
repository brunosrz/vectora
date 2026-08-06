"""Invoca uma SOUL específica isoladamente, fora do fluxo síncrono de
delegação do orchestrator (tool `task()`).

Diferente de ``agent_factory.get_user_agent`` (grafo completo com todas as
tools + o catálogo inteiro de SOULs disponível via `task()`), aqui o grafo
compilado usa SÓ as tools e o system prompt da SOUL pedida — o LLM não tem a
opção de responder fora do escopo daquela SOUL. Reusa o mesmo
checkpointer/store compartilhado (``agent_factory.get_checkpointer``/
``get_store``) para as runs aparecerem na mesma infraestrutura de
threads/histórico que o resto do produto.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _spec_for(subagent_type: str) -> Any:
    from backend.agents.souls import SOUL_CATALOG

    soul = SOUL_CATALOG.get(subagent_type)
    if soul is None:
        raise ValueError(
            f"subagent_type inválido: {subagent_type!r}. Válidos: {SUBAGENT_TYPES}"
        )
    return soul


#: Nomes das SOULs do catálogo, espelhados aqui como literal — não pode vir
#: de ``SOUL_CATALOG`` em import-time: ``backend/tools/background.py`` importa
#: este nome no topo do módulo e é importado por ``backend/nodes/tools.py``,
#: que ``souls.py`` importa de volta (ciclo nodes.tools → background →
#: subagent_runner → souls → nodes.tools). Testado contra o catálogo real em
#: ``tests/unit/test_scheduling_subagent_runner.py``.
SUBAGENT_TYPES = (
    "coder",
    "search",
    "reviewer",
    "tester",
    "devops",
    "writer-docs",
    "data-analyst",
    "security-auditor",
    "browser-qa",
    "planner",
)


async def build_subagent_graph(subagent_type: str, model_id: str = "") -> Any:
    """Compila um grafo deepagents isolado, só com as tools/prompt da SOUL
    pedida — sem `subagents=` (não delega mais fundo).

    Propaga o mesmo middleware do agente principal (HITL dinâmico incluso) —
    sem isso, uma execução agendada de SOUL nunca pausa pra aprovação mesmo
    chamando `terminal`/`file_write`.
    """
    from typing import cast as _cast

    from deepagents import create_deep_agent
    from langchain_core.language_models.chat_models import BaseChatModel

    from backend.llm.fallback_chat_model import FallbackChatModel
    from backend.services import agent_factory
    from backend.services.middleware import build_middleware_stack

    soul = _spec_for(subagent_type)

    checkpointer = await agent_factory.get_checkpointer()
    store = await agent_factory.get_store()

    llm: BaseChatModel = _cast(
        "BaseChatModel", FallbackChatModel(primary_model_id=model_id)
    )

    return create_deep_agent(
        llm,
        tools=soul.tools,
        system_prompt=soul.system_prompt,
        middleware=build_middleware_stack(),
        checkpointer=checkpointer,
        store=store,
        name=f"vectora-subagent-{subagent_type}",
    )
