"""Tools de agente para o board Kanban (``vectora_background_tasks``).

Expõe ao agente, durante a conversa, o que hoje só existe como agendamento
(`create_background_task`/`schedule_task` em `backend/tools/background.py`):
ler e mover cards no mesmo board que a sidebar de Tarefas mostra.

Máquina de estados real em `backend.scheduling.kanban` — estas tools nunca
fazem `UPDATE` arbitrário de `status`; delegam a `set_status`/`block_task`/
`unblock_task`, que validam a transição e recusam o que for inválido.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from backend.scheduling import background_tasks, kanban

logger = logging.getLogger(__name__)

#: Bloqueio padrão quando `kanban_update_status(status="blocked")` não
#: especifica `block_kind` — o motivo mais comum de um agente se bloquear
#: sozinho é faltar algo que só uma pessoa resolve.
_DEFAULT_BLOCK_KIND = "needs_input"


@tool(extras={"destructive": False, "category": "workspace", "icon": "trello"})
async def kanban_list(
    status: str | None = None,
    agent_profile_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lista os cards do board Kanban desta sessão, com filtro opcional.

    Só leitura — nunca pede aprovação (HITL).

    Args:
        status: filtra por coluna (`triage`|`todo`|`scheduled`|`ready`|
            `running`|`blocked`|`review`|`done`|`archived`). Sem filtro,
            lista todas.
        agent_profile_id: filtra pelos cards que herdam este perfil de
            agente. Sem filtro, lista independente do perfil.

    Returns:
        JSON com `cards`: id, name, kind, status, block_kind, block_reason,
        agent_profile_id, last_run_at.
    """
    try:
        if status is not None and status not in kanban.KANBAN_STATUSES:
            return json.dumps(
                {
                    "status": "error",
                    "error": (
                        f"status {status!r} fora da taxonomia — válidos: "
                        f"{', '.join(kanban.KANBAN_STATUSES)}"
                    ),
                }
            )

        configurable = (config or {}).get("configurable") or {}
        session_id = configurable.get("thread_id", "")
        if not session_id:
            return json.dumps(
                {"status": "error", "error": "session_id ausente no config"}
            )

        tasks = await background_tasks.list_tasks(session_id)
        cards = [
            {
                "task_id": t.id,
                "name": t.name,
                "kind": t.kind,
                "status": t.status,
                "block_kind": t.block_kind,
                "block_reason": t.block_reason,
                "agent_profile_id": t.agent_profile_id,
                "last_run_at": t.last_run_at,
            }
            for t in tasks
            if (status is None or t.status == status)
            and (agent_profile_id is None or t.agent_profile_id == agent_profile_id)
        ]
        return json.dumps({"status": "ok", "cards": cards}, ensure_ascii=False)
    except Exception as e:
        logger.exception(
            "kanban_list: erro inesperado", extra={"status_filtro": status}
        )
        return json.dumps({"status": "error", "error": str(e)})


@tool(
    extras={
        "invalidates": ["tasks"],
        "destructive": True,
        "category": "workspace",
        "icon": "plus-square",
    }
)
async def kanban_create(
    name: str,
    instruction: str,
    kind: str = "subagent",
    agent_profile_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Cria um card novo no board Kanban, pronto pra rodar sob demanda.

    Diferente de `create_background_task`/`schedule_task` (que agendam
    execução autônoma via cron/webhook), o card nasce com
    `trigger_type="manual"` — só dispara quando algo (o usuário, outra task,
    `run_background_task_now`) pedir explicitamente.

    Args:
        name: nome curto do card (coluna do board).
        instruction: instrução completa que o agente executará ao rodar.
        kind: `subagent` (default) | `routine` | `heartbreak`.
        agent_profile_id: perfil de agente a herdar (instrução/modelo/
            budget), se algum.

    Returns:
        JSON com `task_id` e `status` (coluna inicial do card) em sucesso.
    """
    try:
        if not name.strip():
            return json.dumps({"status": "error", "error": "name não pode ser vazio"})
        if not instruction.strip():
            return json.dumps(
                {"status": "error", "error": "instruction não pode ser vazia"}
            )

        configurable = (config or {}).get("configurable") or {}
        session_id = configurable.get("thread_id", "")
        user_id = configurable.get("user_id", "")
        workspace_id = configurable.get("workspace_id")
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
            trigger_type="manual",
            workspace_id=workspace_id,
            agent_profile_id=agent_profile_id,
        )
        return json.dumps(
            {"status": "created", "task_id": task.id, "kanban_status": task.status}
        )
    except ValueError as e:
        return json.dumps({"status": "error", "error": str(e)})
    except Exception as e:
        logger.exception("kanban_create: erro inesperado")
        return json.dumps({"status": "error", "error": str(e)})


@tool(
    extras={
        "invalidates": ["tasks"],
        "destructive": True,
        "category": "workspace",
        "icon": "move",
    }
)
async def kanban_update_status(
    task_id: str,
    status: str,
    block_kind: str | None = None,
    block_reason: str | None = None,
) -> str:
    """Move um card do board pra outra coluna, pela máquina de estados real.

    Não é um `UPDATE` livre: `status="blocked"` passa por `block_task`
    (tipa o bloqueio, decide `todo` vs `blocked` vs escalonamento pra
    `triage`); `status="ready"` passa por `unblock_task` (limpa o motivo do
    bloqueio); qualquer outra coluna passa por `set_status`, que recusa
    valores fora de `KANBAN_STATUSES`.

    Args:
        task_id: id do card (de `kanban_list`).
        status: coluna alvo (`triage`|`todo`|`scheduled`|`ready`|`running`|
            `blocked`|`review`|`done`|`archived`).
        block_kind: só usado quando `status="blocked"` — `dependency`|
            `needs_input`|`capability`|`transient`. Default `needs_input`.
        block_reason: só usado quando `status="blocked"` — motivo legível.

    Returns:
        JSON com o novo estado (`status`, `block_kind`, `block_reason`) em
        sucesso, ou erro tipado se a task não existe ou a transição é
        inválida.
    """
    try:
        if status == "blocked":
            await kanban.block_task(
                task_id, block_kind or _DEFAULT_BLOCK_KIND, block_reason or ""
            )
        elif status == "ready":
            await kanban.unblock_task(task_id)
        else:
            await kanban.set_status(task_id, status)

        estado: dict[str, Any] = await kanban.get_task_status(task_id)
        return json.dumps({"result": "ok", "task_id": task_id, **estado})
    except ValueError as e:
        return json.dumps({"status": "error", "error": str(e)})
    except Exception as e:
        logger.exception(
            "kanban_update_status: erro inesperado",
            extra={"task_id": task_id, "status_pedido": status},
        )
        return json.dumps({"status": "error", "error": str(e)})
