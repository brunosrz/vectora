"""Tool para criar tarefas em segundo plano via agente.

Permite ao agente registrar rotinas (cron), heartbreaks (webhook) ou
tarefas manuais em nome da sessão ativa.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from backend.services import background_tasks

logger = logging.getLogger(__name__)


@tool(
    extras={
        "invalidates": ["tasks"],
        "destructive": False,
        "category": "workspace",
        "icon": "clock",
    }
)
async def create_background_task(
    name: str,
    instruction: str,
    kind: str,
    trigger_type: str,
    trigger_config: dict[str, Any] | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Cria uma tarefa em segundo plano para esta sessão.

    Tarefas rodam o agente autonomamente conforme o trigger configurado.

    Args:
        name: Nome curto da tarefa (ex: "Verificar logs diariamente")
        instruction: Instrução completa que o agente executará
        kind: Tipo — routine (periódica) | heartbreak (via webhook)
        trigger_type: Gatilho — interval (cron) | webhook | manual
        trigger_config: Config do trigger (ex: {"cron_expr": "0 9 * * *"})
    """
    try:
        configurable = (config or {}).get("configurable") or {}
        session_id = configurable.get("thread_id", "")
        user_id = configurable.get("user_id", "")

        if not session_id:
            return json.dumps(
                {"status": "error", "error": "session_id ausente no config"}
            )

        task = await background_tasks.create_task(
            session_id=session_id,
            user_id=user_id,
            kind=kind,
            name=name,
            instruction=instruction,
            trigger_type=trigger_type,
            trigger_config=trigger_config or {},
        )
        return json.dumps({"status": "created", "task_id": task.id, "name": task.name})

    except ValueError as e:
        return json.dumps({"status": "error", "error": str(e)})
    except Exception as e:
        logger.exception("create_background_task: erro inesperado")
        return json.dumps({"status": "error", "error": str(e)})
