"""Remember — gatilho automático a cada N turnos (backend/services/remember_trigger.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.services.learning import DistillationResult, SkillDraft
from backend.services.remember_trigger import (
    REMEMBER_TRIGGER_EVERY_N_TURNS,
    maybe_trigger_remember,
)


@pytest.fixture
def _no_pending(monkeypatch):
    monkeypatch.setattr(
        "backend.api.handlers.threads.get_remember_pending",
        AsyncMock(return_value=False),
    )


@pytest.mark.asyncio
async def test_not_a_multiple_of_n_does_not_distill(monkeypatch, _no_pending):
    monkeypatch.setattr(
        "backend.api.handlers.threads.increment_remember_turn_count",
        AsyncMock(return_value=REMEMBER_TRIGGER_EVERY_N_TURNS - 1),
    )
    distill = AsyncMock()
    monkeypatch.setattr("backend.services.learning.distill_transcript", distill)

    await maybe_trigger_remember("t1", "u1")

    distill.assert_not_called()


@pytest.mark.asyncio
async def test_pending_proposal_blocks_new_trigger(monkeypatch):
    monkeypatch.setattr(
        "backend.api.handlers.threads.increment_remember_turn_count",
        AsyncMock(return_value=REMEMBER_TRIGGER_EVERY_N_TURNS),
    )
    monkeypatch.setattr(
        "backend.api.handlers.threads.get_remember_pending",
        AsyncMock(return_value=True),
    )
    distill = AsyncMock()
    monkeypatch.setattr("backend.services.learning.distill_transcript", distill)

    await maybe_trigger_remember("t1", "u1")

    distill.assert_not_called()


@pytest.mark.asyncio
async def test_multiple_of_n_without_pending_distills_and_writes_proposal(
    monkeypatch, _no_pending
):
    monkeypatch.setattr(
        "backend.api.handlers.threads.increment_remember_turn_count",
        AsyncMock(return_value=REMEMBER_TRIGGER_EVERY_N_TURNS),
    )
    from backend.services import agent_factory

    monkeypatch.setattr(
        agent_factory,
        "aget_thread_messages",
        AsyncMock(return_value=[("human", "gosto de respostas curtas", "")]),
    )
    monkeypatch.setattr(
        "backend.services.learning.distill_transcript",
        AsyncMock(
            return_value=DistillationResult(
                skills=[SkillDraft(name="Nova", description="d", content="c")],
                facts=["fato durável"],
            )
        ),
    )
    monkeypatch.setattr("backend.workspace.skills.list_skills", lambda user_id: [])
    set_pending = AsyncMock()
    monkeypatch.setattr(
        "backend.api.handlers.threads.set_remember_pending", set_pending
    )
    artifact_calls: list[dict] = []

    class _FakeCreateArtifact:
        def invoke(self, payload: dict) -> str:
            artifact_calls.append(payload)
            return "{}"

    monkeypatch.setattr("backend.tools.fs.create_artifact", _FakeCreateArtifact())

    await maybe_trigger_remember("t1", "u1")

    set_pending.assert_called_once_with("t1", True)
    assert artifact_calls[0]["artifact_type"] == "remember_proposal"
    assert "Nova" in artifact_calls[0]["content"]
    assert "fato durável" in artifact_calls[0]["content"]


@pytest.mark.asyncio
async def test_nothing_reusable_does_not_mark_pending_nor_write_artifact(
    monkeypatch, _no_pending
):
    """Erro/borda: sem nada reaproveitável no transcript, não marca pending
    nem grava artifact — resultado vazio é válido, não gera ruído."""
    monkeypatch.setattr(
        "backend.api.handlers.threads.increment_remember_turn_count",
        AsyncMock(return_value=REMEMBER_TRIGGER_EVERY_N_TURNS),
    )
    from backend.services import agent_factory

    monkeypatch.setattr(
        agent_factory,
        "aget_thread_messages",
        AsyncMock(return_value=[("human", "oi", "")]),
    )
    monkeypatch.setattr(
        "backend.services.learning.distill_transcript",
        AsyncMock(return_value=DistillationResult()),
    )
    monkeypatch.setattr("backend.workspace.skills.list_skills", lambda user_id: [])
    set_pending = AsyncMock()
    monkeypatch.setattr(
        "backend.api.handlers.threads.set_remember_pending", set_pending
    )

    await maybe_trigger_remember("t1", "u1")

    set_pending.assert_not_called()


@pytest.mark.asyncio
async def test_empty_transcript_returns_without_distilling(monkeypatch, _no_pending):
    """Erro/borda: thread sem nenhuma mensagem ainda (transcript vazio) não
    chama distill_transcript à toa."""
    monkeypatch.setattr(
        "backend.api.handlers.threads.increment_remember_turn_count",
        AsyncMock(return_value=REMEMBER_TRIGGER_EVERY_N_TURNS),
    )
    from backend.services import agent_factory

    monkeypatch.setattr(
        agent_factory, "aget_thread_messages", AsyncMock(return_value=[])
    )
    distill = AsyncMock()
    monkeypatch.setattr("backend.services.learning.distill_transcript", distill)

    await maybe_trigger_remember("t1", "u1")

    distill.assert_not_called()


@pytest.mark.asyncio
async def test_exception_never_propagates(monkeypatch):
    """Best-effort: qualquer falha interna nunca propaga (nunca pode afetar
    o turno de chat que já terminou)."""
    monkeypatch.setattr(
        "backend.api.handlers.threads.increment_remember_turn_count",
        AsyncMock(side_effect=RuntimeError("banco indisponível")),
    )

    await maybe_trigger_remember("t1", "u1")  # não deve levantar
