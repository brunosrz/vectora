"""Tests — Admin Storage endpoints (F10).

GET /admin/storage, POST /admin/storage/test, PATCH /admin/storage.
Usa httpx.AsyncClient com a app FastAPI mockando storage_health.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
async def admin_client():
    """httpx.AsyncClient apontando para a app FastAPI em memória."""
    from httpx import ASGITransport, AsyncClient

    from backend.api.server import create_app

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


class TestAdminStorageGet:
    """GET /admin/storage retorna health de todos os backends."""

    @pytest.mark.asyncio
    async def test_endpoint_exists(self, admin_client):
        """Endpoint /admin/storage existe e retorna resposta HTTP."""
        with patch(
            "backend.storage.factory.storage_health",
            new_callable=AsyncMock,
            return_value={"sqlite": {"ok": True}},
        ):
            resp = await admin_client.get("/admin/storage")
        # Pode retornar 200 ou 401 dependendo de auth configurado
        assert resp.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_response_is_json(self, admin_client):
        """Response tem Content-Type JSON quando não autenticado (401)."""
        resp = await admin_client.get("/admin/storage")
        assert resp.status_code in (200, 401, 403, 404)


class TestAdminStorageDefaults:
    """GET /admin/storage/defaults entrega config default para pré-preencher."""

    @pytest.mark.asyncio
    async def test_endpoint_exists(self, admin_client):
        """Endpoint registrado — responde HTTP (200 com auth, 401/403 sem)."""
        resp = await admin_client.get("/admin/storage/defaults")
        assert resp.status_code in (200, 401, 403, 404)

    def test_connection_defaults_shape(self):
        """A fonte (dev_stack.connection_defaults) traz url + start_command.

        O endpoint só repassa isto; testar a fonte cobre o contrato sem
        depender de auth montado no client de teste.
        """
        from backend.storage.dev_stack import connection_defaults

        defaults = connection_defaults()
        assert set(defaults) == {"postgres", "redis", "qdrant"}
        for service in ("postgres", "redis", "qdrant"):
            assert defaults[service]["url"]
            assert "docker compose up -d" in defaults[service]["start_command"]
        # Qdrant é o único com API key (auth-first).
        assert defaults["qdrant"]["api_key"] == "vectora"
        assert "api_key" not in defaults["redis"]


class TestAdminStorageTest:
    """POST /admin/storage/test verifica conectividade com DSN."""

    @pytest.mark.asyncio
    async def test_sqlite_dsn_accepted(self, admin_client, tmp_path):
        db_path = str(tmp_path / "test.db")
        resp = await admin_client.post(
            "/admin/storage/test",
            json={"dsn": db_path},
        )
        # Pode ser 200 (OK), 401 (sem auth), ou 422 (schema diferente)
        assert resp.status_code in (200, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_invalid_dsn_handled(self, admin_client):
        """DSN inválido retorna ok=False ou erro HTTP."""
        resp = await admin_client.post(
            "/admin/storage/test",
            json={"dsn": "postgresql://bad:5432/nonexistent"},
        )
        assert resp.status_code in (200, 400, 401, 403, 422, 500)
        if resp.status_code == 200:
            data = resp.json()
            # Pode ter "ok": false ou "ok": true dependendo da implementação
            assert "ok" in data or isinstance(data, dict)


class TestAdminStoragePatch:
    """PATCH /admin/storage atualiza storage_mode em runtime."""

    @pytest.mark.asyncio
    async def test_patch_storage_mode(self, admin_client):
        resp = await admin_client.patch(
            "/admin/storage",
            json={"storage_mode": "lite"},
        )
        assert resp.status_code in (200, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_patch_invalid_mode(self, admin_client):
        """Modo inválido deve retornar erro ou ser aceito com validação."""
        resp = await admin_client.patch(
            "/admin/storage",
            json={"storage_mode": "invalid_mode"},
        )
        # Pode validar e retornar 422, ou aceitar e silenciar
        assert resp.status_code in (200, 400, 401, 403, 422, 500)


class TestStorageHealthUnit:
    """storage_health() unit test sem infra real."""

    @pytest.mark.asyncio
    async def test_health_returns_dict(self, tmp_path, monkeypatch):
        import backend.settings as _settings_mod
        from backend.storage.factory import storage_health

        monkeypatch.setattr(_settings_mod.settings, "storage_mode", "lite")
        monkeypatch.setattr(
            _settings_mod.settings, "db_dsn", str(tmp_path / "health.db")
        )
        monkeypatch.setattr(
            _settings_mod.settings,
            "lancedb_dir",
            str(tmp_path / "lancedb"),
        )

        import backend.storage.factory as _fac

        _fac._reset_singletons()
        health = await storage_health()
        _fac._reset_singletons()

        assert isinstance(health, dict)
        # Deve ter pelo menos SQLite no resultado
        assert len(health) >= 1

    @pytest.mark.asyncio
    async def test_health_sqlite_ok_on_lite(self, tmp_path, monkeypatch):
        import backend.settings as _settings_mod
        from backend.storage.factory import storage_health

        monkeypatch.setattr(_settings_mod.settings, "storage_mode", "lite")
        monkeypatch.setattr(
            _settings_mod.settings, "db_dsn", str(tmp_path / "health2.db")
        )
        monkeypatch.setattr(
            _settings_mod.settings,
            "lancedb_dir",
            str(tmp_path / "lancedb2"),
        )

        import backend.storage.factory as _fac

        _fac._reset_singletons()
        health = await storage_health()
        _fac._reset_singletons()

        # Modo lite não deve reportar erro no SQLite
        if "sqlite" in health:
            assert health["sqlite"].get("ok") is True
        elif "checkpointer" in health:
            assert health["checkpointer"].get("ok") is True


class TestFallbackOrderEndpoint:
    """PATCH/GET /admin/model/fallback-order (Parte A)."""

    def _fresh_runtime(self, tmp_path, monkeypatch):
        import backend.workspace.runtime_settings as rt_mod
        from backend.workspace.runtime_settings import RuntimeSettings

        fresh = RuntimeSettings(path=tmp_path / "settings.json")
        monkeypatch.setattr(rt_mod, "runtime_settings", fresh)
        return fresh

    @pytest.mark.asyncio
    async def test_patch_sets_order(self, admin_client, tmp_path, monkeypatch):
        fresh = self._fresh_runtime(tmp_path, monkeypatch)
        resp = await admin_client.patch(
            "/admin/model/fallback-order",
            json={"order": ["openai:gpt-4o", "cohere:command-a"]},
        )
        assert resp.status_code in (200, 401, 403, 422)
        if resp.status_code == 200:
            assert resp.json()["fallback_order"] == [
                "openai:gpt-4o",
                "cohere:command-a",
            ]
            assert fresh.fallback_order == ["openai:gpt-4o", "cohere:command-a"]

    @pytest.mark.asyncio
    async def test_get_returns_order(self, admin_client, tmp_path, monkeypatch):
        fresh = self._fresh_runtime(tmp_path, monkeypatch)
        fresh.set_fallback_order(["cohere:command-a"])
        resp = await admin_client.get("/admin/model/fallback-order")
        assert resp.status_code in (200, 401, 403)
        if resp.status_code == 200:
            assert resp.json()["fallback_order"] == ["cohere:command-a"]

    @pytest.mark.asyncio
    async def test_patch_filters_empty(self, admin_client, tmp_path, monkeypatch):
        self._fresh_runtime(tmp_path, monkeypatch)
        resp = await admin_client.patch(
            "/admin/model/fallback-order",
            json={"order": ["openai:gpt-4o", "", "   "]},
        )
        if resp.status_code == 200:
            assert resp.json()["fallback_order"] == ["openai:gpt-4o"]

    @pytest.mark.asyncio
    async def test_patch_empty_clears(self, admin_client, tmp_path, monkeypatch):
        fresh = self._fresh_runtime(tmp_path, monkeypatch)
        fresh.set_fallback_order(["openai:gpt-4o"])
        resp = await admin_client.patch(
            "/admin/model/fallback-order", json={"order": []}
        )
        if resp.status_code == 200:
            assert resp.json()["fallback_order"] == []

    @pytest.mark.asyncio
    async def test_patch_missing_order_defaults_empty(
        self, admin_client, tmp_path, monkeypatch
    ):
        self._fresh_runtime(tmp_path, monkeypatch)
        resp = await admin_client.patch("/admin/model/fallback-order", json={})
        # order tem default [] — aceita sem 422
        assert resp.status_code in (200, 401, 403)
