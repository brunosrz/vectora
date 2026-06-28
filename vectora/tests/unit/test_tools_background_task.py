"""Tests TDD para create_background_task (FASE 2.4).

Cobre: criação de tarefa via serviço, kind inválido, ausência de sessão,
tipo de trigger inválido e invariante de invalidates metadata.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from backend.tools.background import create_background_task


def _cfg(thread_id: str = "t1", workspace_id: str = "ws1", user_id: str = "u1") -> Any:
    return {
        "configurable": {
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "user_id": user_id,
        }
    }


def _fake_task(task_name: str = "Minha tarefa") -> Any:
    class _FakeTask:
        def __init__(self) -> None:
            self.id = "task-123"
            self.name = task_name
            self.kind = "routine"
            self.trigger_type = "interval"

        def to_dict(self) -> dict:
            return {"id": self.id, "name": self.name}

    return _FakeTask()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cria_tarefa_rotina() -> None:
    """Tarefa de rotina com cron válido → status: created."""
    with patch(
        "backend.tools.background.background_tasks.create_task",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = _fake_task("Tarefa teste")

        result = json.loads(
            await create_background_task.ainvoke(
                {
                    "name": "Tarefa teste",
                    "instruction": "Verifica logs diariamente",
                    "kind": "routine",
                    "trigger_type": "interval",
                    "trigger_config": {"cron_expr": "0 9 * * *"},
                },
                _cfg(),
            )
        )

    assert result["status"] == "created"
    assert result["task_id"] == "task-123"


# ---------------------------------------------------------------------------
# Kind inválido
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kind_invalido_retorna_erro() -> None:
    """Kind não reconhecido → status: error, não propaga."""
    result = json.loads(
        await create_background_task.ainvoke(
            {
                "name": "X",
                "instruction": "X",
                "kind": "magic",
                "trigger_type": "interval",
                "trigger_config": {},
                "config": _cfg(),
            }
        )
    )
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Trigger inválido
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_invalido_retorna_erro() -> None:
    """trigger_type desconhecido → status: error."""
    result = json.loads(
        await create_background_task.ainvoke(
            {
                "name": "X",
                "instruction": "X",
                "kind": "routine",
                "trigger_type": "telepathy",
                "trigger_config": {},
                "config": _cfg(),
            }
        )
    )
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Sem sessão no config
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sem_sessao_retorna_erro() -> None:
    """Config sem thread_id → status: error."""
    result = json.loads(
        await create_background_task.ainvoke(
            {
                "name": "X",
                "instruction": "X",
                "kind": "routine",
                "trigger_type": "manual",
                "trigger_config": {},
                "config": {"configurable": {}},
            }
        )
    )
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Metadata invariantes
# ---------------------------------------------------------------------------


def test_create_background_task_invalida_tasks() -> None:
    # A aba foi renomeada de "background" para "tasks" (Tarefas).
    extras = getattr(create_background_task, "extras", {}) or {}
    assert "tasks" in extras.get("invalidates", [])


def test_create_background_task_e_destrutiva() -> None:
    extras = getattr(create_background_task, "extras", {}) or {}
    assert extras.get("destructive") is False
