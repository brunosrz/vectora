"""Remember — distill_transcript/dedupe_skill_drafts: destilação de um
transcript em skills reutilizáveis e fatos duráveis, via LLM estruturado."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.learning import (
    DistillationResult,
    SkillDraft,
    dedupe_skill_drafts,
    distill_transcript,
)


@pytest.mark.asyncio
async def test_distill_transcript_empty_input_returns_empty_result_without_llm_call(
    monkeypatch,
):
    load_llm_mock = MagicMock()
    monkeypatch.setattr("backend.services.utils.load_llm", load_llm_mock)

    result = await distill_transcript("   ")

    assert result == DistillationResult()
    load_llm_mock.assert_not_called()


@pytest.mark.asyncio
async def test_distill_transcript_happy_path_returns_skills_and_facts(monkeypatch):
    expected = DistillationResult(
        skills=[
            SkillDraft(
                name="Debug de streaming duplicado",
                description="Use quando tokens SSE duplicarem",
                content="1. Verifique o fallback model\n2. Confira reasoning blocks",
            )
        ],
        facts=["Usuário prefere respostas em português brasileiro"],
    )
    structured = MagicMock()
    structured.ainvoke = AsyncMock(return_value=expected)
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr("backend.services.utils.load_llm", MagicMock(return_value=llm))

    result = await distill_transcript("user: bug no streaming\nassistant: corrigido")

    assert result == expected


@pytest.mark.asyncio
async def test_distill_transcript_llm_failure_degrades_to_empty_result(monkeypatch):
    llm = MagicMock()
    llm.with_structured_output.side_effect = RuntimeError("modelo indisponível")
    monkeypatch.setattr("backend.services.utils.load_llm", MagicMock(return_value=llm))

    result = await distill_transcript("user: oi\nassistant: olá")

    assert result == DistillationResult()


def test_dedupe_skill_drafts_removes_names_already_installed():
    drafts = [
        SkillDraft(name="Debug de streaming", description="d", content="c"),
        SkillDraft(name="Nova skill", description="d2", content="c2"),
    ]

    result = dedupe_skill_drafts(drafts, {"debug de streaming"})

    assert [d.name for d in result] == ["Nova skill"]


def test_dedupe_skill_drafts_no_existing_names_keeps_all_drafts():
    drafts = [SkillDraft(name="A", description="d", content="c")]

    result = dedupe_skill_drafts(drafts, set())

    assert result == drafts
