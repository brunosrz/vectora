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

from backend.scheduling import background_tasks

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


@tool(extras={"destructive": False, "category": "workspace", "icon": "list"})
async def list_background_tasks(
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lista as tarefas em segundo plano desta sessão e o status da última run.

    Use para saber o que está rodando/agendado antes de responder ao usuário
    (ex.: "tenho 2 rotinas ativas, uma terminou com X"). Não recebe argumentos —
    a sessão vem do contexto.

    Returns:
        JSON com ``tasks``: id, name, kind, enabled, last_run_at e o status/resumo
        da execução mais recente (``last_run``), quando houver.
    """
    try:
        configurable = (config or {}).get("configurable") or {}
        session_id = configurable.get("thread_id", "")
        if not session_id:
            return json.dumps({"status": "error", "error": "session_id ausente"})

        tasks = await background_tasks.list_tasks(session_id)
        runs = await background_tasks.list_runs(session_id)
        latest_by_task: dict[str, dict[str, Any]] = {}
        for r in runs:  # list_runs vem ordenado por started_at DESC
            latest_by_task.setdefault(r["task_id"], r)

        out = []
        for t in tasks:
            last = latest_by_task.get(t.id)
            out.append(
                {
                    "task_id": t.id,
                    "name": t.name,
                    "kind": t.kind,
                    "enabled": t.enabled,
                    "last_run_at": t.last_run_at,
                    "last_run": (
                        {
                            "run_id": last["id"],
                            "status": last["status"],
                            "summary": (last.get("summary") or "")[:300],
                        }
                        if last
                        else None
                    ),
                }
            )
        return json.dumps({"status": "ok", "tasks": out}, ensure_ascii=False)
    except Exception as e:
        logger.exception("list_background_tasks: erro inesperado")
        return json.dumps({"status": "error", "error": str(e)})


@tool(extras={"destructive": False, "category": "workspace", "icon": "info"})
async def get_task_status(
    task_id: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Status de uma tarefa específica + suas execuções recentes.

    Args:
        task_id: id da tarefa (de ``list_background_tasks`` ou ``create_background_task``).

    Returns:
        JSON com os campos da task e a lista de runs recentes (status/summary).
    """
    try:
        task = await background_tasks.get_task(task_id)
        if task is None:
            return json.dumps({"status": "error", "error": "task não encontrada"})
        runs = await background_tasks.list_runs(task.session_id)
        task_runs = [
            {
                "run_id": r["id"],
                "status": r["status"],
                "summary": (r.get("summary") or "")[:300],
                "started_at": r.get("started_at"),
                "finished_at": r.get("finished_at"),
            }
            for r in runs
            if r["task_id"] == task_id
        ]
        return json.dumps(
            {
                "status": "ok",
                "task_id": task.id,
                "name": task.name,
                "kind": task.kind,
                "enabled": task.enabled,
                "last_run_at": task.last_run_at,
                "runs": task_runs,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        logger.exception("get_task_status: erro inesperado")
        return json.dumps({"status": "error", "error": str(e)})


@tool(extras={"destructive": False, "category": "workspace", "icon": "file-text"})
async def get_task_result(
    run_id: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Resultado (resumo) de uma execução específica de tarefa.

    Args:
        run_id: id da run (de ``list_background_tasks``/``get_task_status``).

    Returns:
        JSON com status, summary e a thread da run (para abrir o histórico
        completo), ou erro se a run não existe.
    """
    try:
        run = await background_tasks._get_run(run_id)
        if run is None:
            return json.dumps({"status": "error", "error": "run não encontrada"})
        return json.dumps(
            {
                "status": "ok",
                "run_id": run["id"],
                "run_status": run["status"],
                "summary": run.get("summary") or "",
                "run_thread_id": run.get("run_thread_id"),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        logger.exception("get_task_result: erro inesperado")
        return json.dumps({"status": "error", "error": str(e)})
