"""Tests TDD para create_background_task (FASE 2.4).

Cobre: criação de tarefa via serviço, kind inválido, ausência de sessão,
tipo de trigger inválido e invariante de invalidates metadata.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from backend.tools.background import (
    create_background_task,
    schedule_subagent_task,
    schedule_task,
)


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


# ---------------------------------------------------------------------------
# schedule_task (Sprint "Schedule" — linguagem natural pra cron)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_schedule_task_parses_natural_language_and_creates_routine() -> None:
    fake = _fake_task("Resumo diário")
    fake.next_run_at = "2026-07-22T09:00:00+00:00"
    with patch(
        "backend.tools.background.background_tasks.create_task",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = fake

        result = json.loads(
            await schedule_task.ainvoke(
                {
                    "name": "Resumo diário",
                    "instruction": "Resuma os commits de hoje",
                    "when": "todo dia às 9h",
                },
                config=_cfg(),
            )
        )

        assert result["status"] == "created"
        assert result["cron_expr"] == "0 9 * * *"
        assert result["next_run_at"] == "2026-07-22T09:00:00+00:00"
        mock_create.assert_awaited_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["trigger_type"] == "interval"
        assert call_kwargs["trigger_config"] == {"cron_expr": "0 9 * * *"}
        assert call_kwargs["kind"] == "routine"


@pytest.mark.asyncio
async def test_schedule_task_ambiguous_when_returns_error_without_creating() -> None:
    # Erro/borda: horário que o parser não reconhece nunca vira um
    # agendamento adivinhado — pede pra reformular, e nem chama create_task.
    with patch(
        "backend.tools.background.background_tasks.create_task",
        new_callable=AsyncMock,
    ) as mock_create:
        result = json.loads(
            await schedule_task.ainvoke(
                {
                    "name": "Tarefa vaga",
                    "instruction": "faça algo",
                    "when": "quando der",
                },
                config=_cfg(),
            )
        )

        assert result["status"] == "error"
        mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_schedule_task_missing_session_returns_error() -> None:
    result = json.loads(
        await schedule_task.ainvoke(
            {
                "name": "n",
                "instruction": "i",
                "when": "todo dia às 9h",
            },
            config={"configurable": {}},
        )
    )

    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# schedule_subagent_task
# ---------------------------------------------------------------------------


def _fake_subagent_task(
    task_id: str = "task-sub-1", next_run_at: str = "2026-07-23T12:00:00+00:00"
) -> Any:
    class _FakeTask:
        def __init__(self) -> None:
            self.id = task_id
            self.next_run_at = next_run_at

    return _FakeTask()


@pytest.mark.asyncio
async def test_schedule_subagent_task_agenda_coder_com_sucesso() -> None:
    with patch(
        "backend.tools.background.background_tasks.create_task",
        new=AsyncMock(return_value=_fake_subagent_task()),
    ) as mock_create:
        result = json.loads(
            await schedule_subagent_task.ainvoke(
                {
                    "subagent_type": "coder",
                    "description": "corrigir o bug do parser",
                    "when": "em 30 minutos",
                },
                config=_cfg(),
            )
        )

        assert result["status"] == "created"
        assert result["task_id"] == "task-sub-1"
        assert result["subagent_type"] == "coder"
        assert result["run_at"] == "2026-07-23T12:00:00+00:00"
        _, kwargs = mock_create.call_args
        assert kwargs["trigger_type"] == "once"
        assert kwargs["trigger_config"] == {"subagent_type": "coder"}
        assert kwargs["next_run_at"] is not None


@pytest.mark.asyncio
async def test_schedule_subagent_task_tipo_invalido_nao_cria_tarefa() -> None:
    with patch(
        "backend.tools.background.background_tasks.create_task",
        new=AsyncMock(),
    ) as mock_create:
        result = json.loads(
            await schedule_subagent_task.ainvoke(
                {
                    "subagent_type": "orchestrator",
                    "description": "não deveria rodar",
                    "when": "em 10 minutos",
                },
                config=_cfg(),
            )
        )

        assert result["status"] == "error"
        assert "subagent_type inválido" in result["error"]
        mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_schedule_subagent_task_horario_nao_reconhecido_retorna_erro() -> None:
    with patch(
        "backend.tools.background.background_tasks.create_task",
        new=AsyncMock(),
    ) as mock_create:
        result = json.loads(
            await schedule_subagent_task.ainvoke(
                {
                    "subagent_type": "search",
                    "description": "pesquisar concorrentes",
                    "when": "algum dia desses",
                },
                config=_cfg(),
            )
        )

        assert result["status"] == "error"
        mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_schedule_subagent_task_missing_session_returns_error() -> None:
    result = json.loads(
        await schedule_subagent_task.ainvoke(
            {
                "subagent_type": "search",
                "description": "d",
                "when": "em 5 minutos",
            },
            config={"configurable": {}},
        )
    )

    assert result["status"] == "error"
