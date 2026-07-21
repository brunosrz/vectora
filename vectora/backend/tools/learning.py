"""Remember — learning loop do agente.

``learn_from_session`` destila o transcript da thread atual em skills e
fatos duráveis, mas NÃO persiste nada — só devolve a proposta pro agente
apresentar ao usuário. ``install_learned_skill`` é quem persiste (grava
``SKILL.md`` via ``workspace.skills``) e está em ``_REQUIRE_APPROVAL``
(``backend/services/middleware.py``) — pausa para aprovação HITL antes de
gravar, mesmo tratamento de ``terminal``/``file_write``. Fatos duráveis
reaproveitam a tool ``save_memory`` já existente, com ``metadata={"tag":
"user_model"}`` — sem duplicar o mecanismo de persistência de memória.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from backend.services.learning import dedupe_skill_drafts, distill_transcript

logger = logging.getLogger(__name__)


@tool(
    extras={
        "destructive": False,
        "category": "memory",
        "icon": "sparkles",
    }
)
async def learn_from_session(
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Analisa o transcript da thread atual e propõe skills reutilizáveis
    e fatos duráveis a aprender — não grava nada ainda.

    Devolva a proposta ao usuário para revisão antes de chamar
    ``install_learned_skill`` (por skill) e ``save_memory`` (por fato),
    que exigem confirmação explícita. Se não houver nada de reaproveitável
    no transcript, a lista vem vazia — isso é um resultado válido, não um
    erro; não force a criação de uma skill genérica.
    """
    try:
        configurable = (config or {}).get("configurable") or {}
        thread_id = configurable.get("thread_id", "")
        user_id = configurable.get("user_id", "local")

        if not thread_id:
            return json.dumps(
                {"status": "error", "error": "thread_id ausente no config"}
            )

        from backend.services import agent_factory

        pairs = await agent_factory.aget_thread_messages(thread_id)
        transcript = "\n".join(f"{role}: {text}" for role, text, _ in pairs)

        result = await distill_transcript(transcript)

        from backend.workspace.skills import list_skills

        existing_names = {s.name for s in list_skills(user_id)}
        skills = dedupe_skill_drafts(result.skills, existing_names)

        return json.dumps(
            {
                "status": "ok",
                "skills": [s.model_dump() for s in skills],
                "facts": result.facts,
            }
        )
    except Exception as exc:
        logger.exception("learn_from_session: falha ao destilar transcript")
        return json.dumps({"status": "error", "error": str(exc)})


@tool(
    extras={
        "invalidates": ["skills"],
        "destructive": True,
        "category": "memory",
        "icon": "sparkles",
    }
)
async def install_learned_skill(
    name: str,
    description: str,
    content: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Grava uma skill proposta por ``learn_from_session`` como
    ``SKILL.md`` — pausa para aprovação do usuário antes de executar
    (mesmo tratamento HITL de ``terminal``/``file_write``).

    Args:
        name: Nome curto da skill (vira o slug da pasta).
        description: Quando usar essa skill.
        content: Passo a passo em Markdown (corpo do SKILL.md).
    """
    try:
        configurable = (config or {}).get("configurable") or {}
        user_id = configurable.get("user_id", "local")

        from backend.workspace.skills import install_skill_from_content

        skill = install_skill_from_content(user_id, name, description, content)
        logger.info("learning: skill instalada id=%s user=%s", skill.id, user_id)
        return json.dumps({"status": "installed", "skill_id": skill.id})
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc)})
