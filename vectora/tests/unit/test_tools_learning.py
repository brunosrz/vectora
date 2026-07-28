"""Remember — tools learn_from_session/install_learned_skill/save_learned_fact."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from backend.services.learning import DistillationResult, SkillDraft
from backend.tools.learning import (
    install_learned_skill,
    learn_from_session,
    save_learned_fact,
)
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
            return_value=[
                ("human", "bug no streaming", "", []),
                ("ai", "corrigido", "", []),
            ]
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
        AsyncMock(return_value=[("human", "oi", "", [])]),
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


@pytest.mark.asyncio
async def test_install_learned_skill_mirrors_artifact_and_resolves_pending(
    monkeypatch, tmp_path
):
    """Instalar uma skill aprovada espelha um artifact na aba Plan e limpa
    a proposta pendente do gatilho automático (WB-5)."""
    from backend.workspace import skills as skills_module

    monkeypatch.setattr(
        skills_module, "_skills_dir", lambda user_id: tmp_path / user_id
    )
    skills_module._versions.clear()

    create_artifact_calls: list[dict] = []

    class _FakeCreateArtifact:
        def invoke(self, payload: dict) -> str:
            create_artifact_calls.append(payload)
            return "{}"

    monkeypatch.setattr("backend.tools.fs.create_artifact", _FakeCreateArtifact())
    resolve_calls: list[str] = []

    async def _fake_set_pending(thread_id: str, pending: bool) -> None:
        resolve_calls.append(thread_id)
        assert pending is False

    monkeypatch.setattr(
        "backend.api.handlers.threads.set_remember_pending", _fake_set_pending
    )

    result = json.loads(
        await install_learned_skill.ainvoke(
            {
                "name": "Skill espelhada",
                "description": "quando usar",
                "content": "passo a passo",
            },
            {"configurable": {"user_id": "u1", "thread_id": "t-mirror"}},
        )
    )

    assert result["status"] == "installed"
    assert create_artifact_calls[0]["artifact_type"] == "skill_learned"
    assert resolve_calls == ["t-mirror"]


@pytest.mark.asyncio
async def test_save_learned_fact_persists_via_save_memory(monkeypatch):
    save_memory_calls: list[dict] = []

    class _FakeSaveMemory:
        async def ainvoke(self, payload: dict) -> str:
            save_memory_calls.append(payload)
            return "ok"

    class _FakeCreateArtifact:
        def invoke(self, payload: dict) -> str:
            return "{}"

    monkeypatch.setattr("backend.tools.memory.save_memory", _FakeSaveMemory())
    monkeypatch.setattr("backend.tools.fs.create_artifact", _FakeCreateArtifact())
    monkeypatch.setattr(
        "backend.api.handlers.threads.set_remember_pending",
        AsyncMock(),
    )

    result = json.loads(
        await save_learned_fact.ainvoke(
            {"fact": "usuário prefere respostas curtas"},
            {"configurable": {"user_id": "u1", "thread_id": "t1"}},
        )
    )

    assert result["status"] == "saved"
    assert save_memory_calls[0]["content"] == "usuário prefere respostas curtas"
    assert save_memory_calls[0]["metadata"] == {
        "tag": "user_model",
        "source": "learn_from_session",
    }


@pytest.mark.asyncio
async def test_save_learned_fact_error_returns_status_error_not_raised(monkeypatch):
    class _BoomSaveMemory:
        async def ainvoke(self, payload: dict) -> str:
            raise RuntimeError("store indisponível")

    monkeypatch.setattr("backend.tools.memory.save_memory", _BoomSaveMemory())

    result = json.loads(
        await save_learned_fact.ainvoke(
            {"fact": "fato qualquer"},
            {"configurable": {"user_id": "u1", "thread_id": "t1"}},
        )
    )

    assert result["status"] == "error"
    assert "store indisponível" in result["error"]
