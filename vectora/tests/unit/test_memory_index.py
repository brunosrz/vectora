"""Tests — índice de busca unificado (fatos + skills + buckets RAG).

Verifica:
- busca com termo presente nos três tipos retorna os três (happy path)
- usuário sem nenhuma memória de nenhum tipo retorna lista vazia sem lançar
- falha isolada num tipo (skills corrompidas) não derruba os outros dois
- filtro por `types` restringe a busca a um subconjunto
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest
from langgraph.store.memory import InMemoryStore

from backend.services.memory_index import search_unified_memory
from backend.vtypes.skill import Skill


@dataclass
class _FakeBucket:
    id: str
    name: str
    description_md: str
    source_path: str | None = None
    created_at: str = ""


@pytest.fixture
def store():
    return InMemoryStore()


def _make_skill(name: str = "godot-helper") -> Skill:
    return Skill(
        id="skill-1",
        name=name,
        description="Ajuda com projetos Godot 4.7",
        source="https://example.com/skill.git",
        path="/tmp/skill",
        installed_at="2026-08-08T00:00:00Z",
        installed_by="user-1",
    )


class TestSearchUnifiedMemoryHappyPath:
    """Query que bate nos três tipos retorna os três simultaneamente."""

    async def test_returns_fact_skill_and_bucket(self, store, monkeypatch):
        await store.aput(
            ("user", "user-1", "memories"),
            "godot-fact",
            {"content": "Godot usa GDScript por padrão", "metadata": {}},
        )
        monkeypatch.setattr(
            "backend.services.agent_factory.get_store", AsyncMock(return_value=store)
        )
        monkeypatch.setattr(
            "backend.workspace.skills.list_skills",
            lambda user_id: [_make_skill("godot-helper")],
        )
        monkeypatch.setattr(
            "backend.services.rag_buckets.list_buckets",
            lambda rs, workspace_id: [
                _FakeBucket(
                    id="bucket-1",
                    name="Godot Docs",
                    description_md="Documentação oficial do Godot 4.7",
                )
            ],
        )

        hits = await search_unified_memory(
            "godot", user_id="user-1", workspace_id="ws-1"
        )

        types = {h.type for h in hits}
        assert types == {"fact", "skill", "rag_bucket"}
        assert any(h.id == "godot-fact" for h in hits)
        assert any(h.id == "skill-1" for h in hits)
        assert any(h.id == "bucket-1" for h in hits)


class TestSearchUnifiedMemoryEmptyUser:
    """Usuário sem nenhuma memória de nenhum tipo não lança, devolve []."""

    async def test_empty_user_returns_empty_list(self, store, monkeypatch):
        monkeypatch.setattr(
            "backend.services.agent_factory.get_store", AsyncMock(return_value=store)
        )
        monkeypatch.setattr("backend.workspace.skills.list_skills", lambda user_id: [])
        monkeypatch.setattr(
            "backend.services.rag_buckets.list_buckets",
            lambda rs, workspace_id: [],
        )

        hits = await search_unified_memory(
            "qualquer coisa", user_id="user-sem-nada", workspace_id="ws-1"
        )

        assert hits == []

    async def test_no_workspace_id_skips_bucket_search_without_raising(
        self, store, monkeypatch
    ):
        monkeypatch.setattr(
            "backend.services.agent_factory.get_store", AsyncMock(return_value=store)
        )
        monkeypatch.setattr("backend.workspace.skills.list_skills", lambda user_id: [])

        hits = await search_unified_memory(
            "qualquer coisa", user_id="user-1", workspace_id=None
        )

        assert hits == []


class TestSearchUnifiedMemoryIsolatesFailures:
    """Storage corrompido num tipo não derruba a busca dos outros dois."""

    async def test_corrupted_skills_index_does_not_break_facts_and_buckets(
        self, store, monkeypatch
    ):
        await store.aput(
            ("user", "user-1", "memories"),
            "surviving-fact",
            {"content": "fato sobrevive à falha de skills", "metadata": {}},
        )
        monkeypatch.setattr(
            "backend.services.agent_factory.get_store", AsyncMock(return_value=store)
        )

        def _raise(user_id: str) -> list[Skill]:
            raise RuntimeError("index.json corrompido")

        monkeypatch.setattr("backend.workspace.skills.list_skills", _raise)
        monkeypatch.setattr(
            "backend.services.rag_buckets.list_buckets",
            lambda rs, workspace_id: [
                _FakeBucket(
                    id="bucket-1", name="Bucket", description_md="fato de teste"
                )
            ],
        )

        hits = await search_unified_memory(
            "fato", user_id="user-1", workspace_id="ws-1"
        )

        types = {h.type for h in hits}
        assert "skill" not in types
        assert "fact" in types
        assert "rag_bucket" in types

    async def test_broken_store_does_not_break_skills_and_buckets(self, monkeypatch):
        monkeypatch.setattr(
            "backend.services.agent_factory.get_store",
            AsyncMock(side_effect=RuntimeError("store indisponível")),
        )
        monkeypatch.setattr(
            "backend.workspace.skills.list_skills",
            lambda user_id: [_make_skill()],
        )
        monkeypatch.setattr(
            "backend.services.rag_buckets.list_buckets",
            lambda rs, workspace_id: [],
        )

        hits = await search_unified_memory(
            "godot", user_id="user-1", workspace_id="ws-1"
        )

        types = {h.type for h in hits}
        assert "fact" not in types
        assert "skill" in types


class TestSearchUnifiedMemoryTypesFilter:
    """`types` restringe a busca a um subconjunto explícito."""

    async def test_types_filter_skips_untargeted_storages(self, store, monkeypatch):
        await store.aput(
            ("user", "user-1", "memories"),
            "a-fact",
            {"content": "conteúdo", "metadata": {}},
        )
        skills_called = False

        def _list_skills(user_id: str) -> list[Skill]:
            nonlocal skills_called
            skills_called = True
            return [_make_skill()]

        monkeypatch.setattr(
            "backend.services.agent_factory.get_store", AsyncMock(return_value=store)
        )
        monkeypatch.setattr("backend.workspace.skills.list_skills", _list_skills)
        monkeypatch.setattr(
            "backend.services.rag_buckets.list_buckets",
            lambda rs, workspace_id: [],
        )

        hits = await search_unified_memory(
            "conteúdo",
            user_id="user-1",
            workspace_id="ws-1",
            types=frozenset({"fact"}),
        )

        assert all(h.type == "fact" for h in hits)
        assert skills_called is False
