"""GET /skills/catalog — catálogo curado de skills do registry remoto,
distinto de GET /skills (que lista as instaladas)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.api.handlers import skills as skills_handler


@pytest.mark.asyncio
async def test_get_skills_catalog_returns_remote_entries(monkeypatch):
    monkeypatch.setattr(
        skills_handler.registry_client,
        "fetch_catalog",
        AsyncMock(return_value=[{"id": "s1", "name": "Skill 1"}]),
    )

    result = await skills_handler.get_skills_catalog()

    assert result == {"entries": [{"id": "s1", "name": "Skill 1"}], "total": 1}


@pytest.mark.asyncio
async def test_get_skills_catalog_empty_is_not_error(monkeypatch):
    monkeypatch.setattr(
        skills_handler.registry_client, "fetch_catalog", AsyncMock(return_value=[])
    )

    result = await skills_handler.get_skills_catalog()

    assert result == {"entries": [], "total": 0}


class TestPublishUserSkill:
    @pytest.mark.asyncio
    async def test_publica_com_token_configurado(self, monkeypatch):
        from backend.services import license as license_service

        monkeypatch.setattr(license_service, "_get_token", lambda: "tok-123")
        monkeypatch.setattr(
            skills_handler.registry_client,
            "publish_skill",
            AsyncMock(return_value="remote-skill-1"),
        )

        result = await skills_handler.publish_user_skill(
            skills_handler.PublishSkillRequest(
                source="https://github.com/user/skill",
                name="Minha Skill",
                description="faz coisas",
                category="devtools",
                tags=["cli"],
            )
        )

        assert result == {"status": "published", "skill_id": "remote-skill-1"}

    @pytest.mark.asyncio
    async def test_sem_token_retorna_erro_sem_publicar(self, monkeypatch):
        from backend.services import license as license_service

        monkeypatch.setattr(license_service, "_get_token", lambda: None)
        publish_spy = AsyncMock()
        monkeypatch.setattr(
            skills_handler.registry_client, "publish_skill", publish_spy
        )

        result = await skills_handler.publish_user_skill(
            skills_handler.PublishSkillRequest(
                source="https://github.com/user/skill",
                name="x",
                description="y",
            )
        )

        assert result["status"] == "error"
        publish_spy.assert_not_called()

    @pytest.mark.asyncio
    async def test_erro_do_registry_vira_erro_tipado_nao_excecao(self, monkeypatch):
        from backend.services import license as license_service

        monkeypatch.setattr(license_service, "_get_token", lambda: "tok-123")
        monkeypatch.setattr(
            skills_handler.registry_client,
            "publish_skill",
            AsyncMock(
                side_effect=skills_handler.RegistryClientError("source inválido")
            ),
        )

        result = await skills_handler.publish_user_skill(
            skills_handler.PublishSkillRequest(
                source="não é url", name="x", description="y"
            )
        )

        assert result["status"] == "error"
        assert "inválido" in result["error"]
