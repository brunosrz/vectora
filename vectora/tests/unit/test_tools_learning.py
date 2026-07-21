"""Remember — tools learn_from_session/install_learned_skill."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from backend.services.learning import DistillationResult, SkillDraft
from backend.tools.learning import install_learned_skill, learn_from_session
from backend.vtypes.skill import Skill


@pytest.mark.asyncio
async def test_learn_from_session_missing_thread_id_returns_error():
    result = json.loads(await learn_from_session.ainvoke({}, {}))

    assert result["status"] == "error"
    assert "thread_id" in result["error"]


@pytest.mark.asyncio
async def test_learn_from_session_returns_deduped_proposal(monkeypatch):
    from backend.services import agent_factory

    monkeypatch.setattr(
        agent_factory,
        "aget_thread_messages",
        AsyncMock(
            return_value=[("human", "bug no streaming", ""), ("ai", "corrigido", "")]
        ),
    )
    monkeypatch.setattr(
        "backend.tools.learning.distill_transcript",
        AsyncMock(
            return_value=DistillationResult(
                skills=[
                    SkillDraft(name="Já instalada", description="d", content="c"),
                    SkillDraft(name="Nova", description="d2", content="c2"),
                ],
                facts=["fato durável"],
            )
        ),
    )
    monkeypatch.setattr(
        "backend.workspace.skills.list_skills",
        lambda user_id: [
            Skill(
                id="ja-instalada",
                name="Já instalada",
                description="d",
                source="git",
                path="/tmp/x",
                installed_at="2026-01-01T00:00:00Z",
                installed_by=user_id,
            )
        ],
    )

    result = json.loads(
        await learn_from_session.ainvoke(
            {}, {"configurable": {"thread_id": "t1", "user_id": "u1"}}
        )
    )

    assert result["status"] == "ok"
    assert [s["name"] for s in result["skills"]] == ["Nova"]
    assert result["facts"] == ["fato durável"]


@pytest.mark.asyncio
async def test_learn_from_session_no_signal_returns_empty_lists_not_error(
    monkeypatch,
):
    from backend.services import agent_factory

    monkeypatch.setattr(
        agent_factory,
        "aget_thread_messages",
        AsyncMock(return_value=[("human", "oi", "")]),
    )
    monkeypatch.setattr(
        "backend.tools.learning.distill_transcript",
        AsyncMock(return_value=DistillationResult()),
    )
    monkeypatch.setattr("backend.workspace.skills.list_skills", lambda user_id: [])

    result = json.loads(
        await learn_from_session.ainvoke({}, {"configurable": {"thread_id": "t1"}})
    )

    assert result == {"status": "ok", "skills": [], "facts": []}


@pytest.mark.asyncio
async def test_install_learned_skill_calls_workspace_skills(monkeypatch, tmp_path):
    from backend.workspace import skills as skills_module

    monkeypatch.setattr(
        skills_module, "_skills_dir", lambda user_id: tmp_path / user_id
    )
    skills_module._versions.clear()

    result = json.loads(
        await install_learned_skill.ainvoke(
            {
                "name": "Skill aprendida",
                "description": "quando usar",
                "content": "passo a passo",
            },
            {"configurable": {"user_id": "u1"}},
        )
    )

    assert result["status"] == "installed"
    assert result["skill_id"] == "skill-aprendida"


@pytest.mark.asyncio
async def test_install_learned_skill_duplicate_returns_error_not_exception(
    monkeypatch, tmp_path
):
    from backend.workspace import skills as skills_module

    monkeypatch.setattr(
        skills_module, "_skills_dir", lambda user_id: tmp_path / user_id
    )
    skills_module._versions.clear()
    skills_module.install_skill_from_content("u1", "Dup", "d", "c")

    result = json.loads(
        await install_learned_skill.ainvoke(
            {
                "name": "Dup",
                "description": "d2",
                "content": "c2",
            },
            {"configurable": {"user_id": "u1"}},
        )
    )

    assert result["status"] == "error"
    assert "já instalada" in result["error"]
