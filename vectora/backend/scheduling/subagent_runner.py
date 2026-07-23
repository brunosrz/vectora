"""Invoca um subagente específico (coder/search) isoladamente, fora do
fluxo síncrono de delegação do orchestrator (tool `task()`).

Diferente de ``agent_factory.get_user_agent`` (grafo completo com todas as
tools + os dois subagentes disponíveis via `task()`), aqui o grafo compilado
usa SÓ as tools e o system prompt do ``SUBAGENT_SPEC`` do tipo pedido — o
LLM não tem a opção de responder fora do escopo daquele subagente. Reusa o
mesmo checkpointer/store compartilhado (``agent_factory.get_checkpointer``/
``get_store``) para as runs aparecerem na mesma infraestrutura de
threads/histórico que o resto do produto.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

SUBAGENT_TYPES = ("coder", "search")


def _spec_for(subagent_type: str) -> dict[str, Any]:
    if subagent_type == "coder":
        from backend.agents.coder import SUBAGENT_SPEC
    elif subagent_type == "search":
        from backend.agents.search import SUBAGENT_SPEC
    else:
        raise ValueError(
            f"subagent_type inválido: {subagent_type!r}. Válidos: {SUBAGENT_TYPES}"
        )
    return SUBAGENT_SPEC


async def build_subagent_graph(subagent_type: str, model_id: str = "") -> Any:
    """Compila um grafo deepagents isolado, só com as tools/prompt do
    subagente pedido — sem `subagents=` (não delega mais fundo)."""
    from typing import cast as _cast

    from deepagents import create_deep_agent
    from langchain_core.language_models.chat_models import BaseChatModel

    from backend.llm.fallback_chat_model import FallbackChatModel
    from backend.services import agent_factory

    spec = _spec_for(subagent_type)

    checkpointer = await agent_factory.get_checkpointer()
    store = await agent_factory.get_store()

    llm: BaseChatModel = _cast(
        "BaseChatModel", FallbackChatModel(primary_model_id=model_id)
    )

    return create_deep_agent(
        llm,
        tools=spec["tools"],
        system_prompt=spec["system_prompt"],
        checkpointer=checkpointer,
        store=store,
        name=f"vectora-subagent-{subagent_type}",
    )
