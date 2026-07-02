"""Tests — Root Admin Panel (P1+P2).

Verifica:
- handler admin existe com os endpoints esperados
- endpoints exigem role admin/root (decoradores aplicados)
- schemas de resposta têm estrutura correta
"""

from __future__ import annotations

import pytest


class TestAdminHandlerExists:
    """src/api/handlers/admin.py deve existir com os endpoints esperados."""

    def test_module_exists(self):
        import backend.api.handlers.admin as mod

        assert mod is not None

    def test_router_exists(self):
        from backend.api.handlers.admin import router

        assert router is not None

    def test_list_users_route_registered(self):
        from backend.api.handlers.admin import router

        paths = [r.path for r in router.routes]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        assert any("users" in p for p in paths)

    def test_system_info_route_registered(self):
        from backend.api.handlers.admin import router

        paths = [r.path for r in router.routes]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        assert any("system" in p for p in paths)

    def test_config_route_registered(self):
        from backend.api.handlers.admin import router

        paths = [r.path for r in router.routes]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        assert any("config" in p for p in paths)

    def test_tools_override_route_registered(self):
        from backend.api.handlers.admin import router

        paths = [r.path for r in router.routes]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        assert any("tools" in p for p in paths)


class TestAdminRequiresAdminRole:
    """Endpoints admin devem checar permissão de role."""

    def test_require_admin_decorator_exists(self):
        from backend.api.handlers.admin import require_admin

        assert callable(require_admin)

    def test_require_admin_raises_for_member(self):
        """member não tem acesso a endpoints admin."""
        from unittest.mock import MagicMock

        from backend.api.handlers.admin import require_admin

        mock_user = MagicMock()
        mock_user.role = "member"

        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            require_admin(mock_user)

    def test_require_admin_passes_for_root(self):
        from unittest.mock import MagicMock

        from backend.api.handlers.admin import require_admin

        mock_user = MagicMock()
        mock_user.role = "root"

        # Não deve levantar exceção
        result = require_admin(mock_user)
        assert result is None or result == mock_user

    def test_require_admin_passes_for_admin(self):
        from unittest.mock import MagicMock

        from backend.api.handlers.admin import require_admin

        mock_user = MagicMock()
        mock_user.role = "admin"

        result = require_admin(mock_user)
        assert result is None or result == mock_user


class TestAdminSystemInfo:
    """Estrutura do sistema info."""

    def test_system_info_fields_exist(self):
        from backend.api.handlers.admin import _build_system_info

        info = _build_system_info()
        assert "version" in info
        assert "python_version" in info
        assert "platform" in info


class TestApiKeysMaskKey:
    """_mask_key oculta segredos mantendo prefixo e sufixo."""

    def test_mask_key_long(self):
        from backend.api.handlers.admin import _mask_key

        masked = _mask_key("AIzaSyDEADBEEF12345XYZ")
        assert masked.startswith("AIzaSy")
        assert masked.endswith("5XYZ")
        assert "•" in masked

    def test_mask_key_short(self):
        from backend.api.handlers.admin import _mask_key

        masked = _mask_key("abc")
        assert masked == "•••"

    def test_mask_key_empty(self):
        from backend.api.handlers.admin import _mask_key

        assert _mask_key("") == ""


class TestApiKeysEndpoints:
    """GET/PATCH/POST /admin/api-keys — contratos básicos."""

    @pytest.mark.asyncio
    async def test_get_api_keys_structure(self):
        import os
        from unittest.mock import MagicMock, patch

        request = MagicMock()
        request.state.user = MagicMock(role="root")

        with patch.dict(
            os.environ,
            {
                "GOOGLE_API_KEY": "AIzaSyXXXXLONGKEY123",
                "COHERE_API_KEY": "",
                "TAVILY_API_KEY": "tvly-secretkey987",
            },
        ):
            from backend.api.handlers.admin import get_api_keys

            result = await get_api_keys(request)

        assert "google" in result
        assert "cohere" in result
        assert "tavily" in result
        assert result["google"]["configured"] is True
        assert result["cohere"]["configured"] is False
        assert result["tavily"]["configured"] is True
        assert "AIzaSy" in result["google"]["masked"]

    @pytest.mark.asyncio
    async def test_get_api_keys_returns_masked_not_raw(self):
        import os
        from unittest.mock import MagicMock, patch

        request = MagicMock()
        request.state.user = MagicMock(role="root")

        raw = "AIzaSyDEADBEEFSECRET9999"
        with patch.dict(os.environ, {"GOOGLE_API_KEY": raw}):
            from backend.api.handlers.admin import get_api_keys

            result = await get_api_keys(request)

        assert result["google"]["masked"] != raw

    @pytest.mark.asyncio
    async def test_test_api_key_empty_returns_error(self):
        from unittest.mock import MagicMock

        from backend.api.handlers.admin import TestApiKeyBody, test_api_key

        request = MagicMock()
        request.state.user = MagicMock(role="root")
        body = TestApiKeyBody(provider="google", api_key="")
        result = await test_api_key(request, body)

        assert result["ok"] is False
        assert "vazia" in result["error"].lower() or result["error"]

    @pytest.mark.asyncio
    async def test_test_api_key_unknown_provider(self):
        from unittest.mock import MagicMock

        from backend.api.handlers.admin import TestApiKeyBody, test_api_key

        request = MagicMock()
        request.state.user = MagicMock(role="root")
        body = TestApiKeyBody(provider="openai_unsupported", api_key="sk-123")
        result = await test_api_key(request, body)

        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_patch_api_keys_calls_upsert(self):
        from unittest.mock import MagicMock, patch

        from backend.api.handlers.admin import PatchApiKeysBody, patch_api_keys

        request = MagicMock()
        request.state.user = MagicMock(role="root", id="u1")

        with (
            patch("backend.cli.keys.upsert_env_key") as mock_upsert,
            patch("backend.api.handlers.admin._env_file", return_value=MagicMock()),
        ):
            body = PatchApiKeysBody(
                google_api_key="AIzaSyNEW", cohere_api_key=None, tavily_api_key=None
            )
            result = await patch_api_keys(request, body)

        assert result["status"] == "updated"
        assert "GOOGLE_API_KEY" in result["updated"]
        assert mock_upsert.called


class TestCreateInviteRequiresPro:
    """Convidar membro adicional é feature de time — exige plano Pro.

    O 1º usuário (root) nasce direto no signup, sem passar por /admin/invites
    (backend/services/auth.py::signup) — este endpoint gateia só convites de
    membros extras (2º+ usuário).
    """

    @pytest.mark.asyncio
    async def test_create_invite_raises_402_on_free(self, tmp_path, monkeypatch):
        from unittest.mock import MagicMock

        from backend.api.handlers.admin import CreateInviteBody, create_invite
        from backend.services import license as lic

        monkeypatch.setattr(lic, "CACHE_PATH", tmp_path / "license_cache.json")

        request = MagicMock()
        request.state.user = MagicMock(role="admin", id="u1")
        body = CreateInviteBody(role="member", email="novo@example.com")

        with pytest.raises(Exception) as exc:
            await create_invite(request, body)
        assert exc.value.status_code == 402  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]

    @pytest.mark.asyncio
    async def test_create_invite_passes_gate_on_pro(self, tmp_path, monkeypatch):
        """Com plano pro, o gate libera (segue para require_admin / lógica normal)."""
        import json
        from datetime import UTC, datetime
        from unittest.mock import MagicMock

        from backend.api.handlers.admin import CreateInviteBody, create_invite
        from backend.services import license as lic

        cache_path = tmp_path / "license_cache.json"
        cache_path.write_text(
            json.dumps(
                {
                    "tier": "pro",
                    "status": "active",
                    "days_remaining": 30,
                    "expires_at": "2027-01-01",
                    "validated_at": datetime.now(UTC).isoformat(),
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(lic, "CACHE_PATH", cache_path)

        # Sem role admin/root → passa pelo gate de pro e falha depois no
        # require_admin (403), não no gate de tier (402) — confirma a ordem.
        request = MagicMock()
        request.state.user = MagicMock(role="member", id="u1")
        body = CreateInviteBody(role="member", email="novo@example.com")

        with pytest.raises(Exception) as exc:
            await create_invite(request, body)
        assert exc.value.status_code == 403  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]


class TestToggleToolGlobal:
    """Kill-switch global de tools (/admin/tools, /admin/tools/{name}/toggle).

    Antes, o toggle não persistia nada (TODO em código) e list_tools_admin
    sempre devolvia enabled=True — um admin podia desligar uma tool
    "destructive" e ela continuar ativa pro agente. Estes testes cobrem a
    persistência real via tool_policy.GLOBAL_SCOPE e a leitura de volta.
    """

    @pytest.fixture(autouse=True)
    def iso_dir(self, tmp_path, monkeypatch):
        from backend.services import tool_policy

        monkeypatch.setattr(tool_policy, "_policy_dir", lambda: tmp_path / "tools")

    @staticmethod
    def _admin_request():
        from unittest.mock import MagicMock

        request = MagicMock()
        request.state.user = MagicMock(role="admin", id="admin-1")
        return request

    @pytest.mark.asyncio
    async def test_list_tools_all_enabled_by_default(self):
        from backend.api.handlers.admin import list_tools_admin

        result = await list_tools_admin(self._admin_request())
        assert result["total"] > 0
        assert all(t["enabled"] for t in result["tools"])

    @pytest.mark.asyncio
    async def test_toggle_off_persists_and_reflects_in_list(self):
        from backend.api.handlers.admin import (
            ToolToggleBody,
            list_tools_admin,
            toggle_tool,
        )
        from backend.nodes.tools import ALL_TOOLS

        target = ALL_TOOLS[0].name

        res = await toggle_tool(
            self._admin_request(), target, ToolToggleBody(enabled=False)
        )
        assert res == {"status": "ok", "tool": target, "enabled": False}

        listing = await list_tools_admin(self._admin_request())
        entry = next(t for t in listing["tools"] if t["name"] == target)
        assert entry["enabled"] is False

    @pytest.mark.asyncio
    async def test_toggle_persists_via_tool_policy_global_scope(self):
        """A persistência real é tool_policy — não um dict/atributo local do handler."""
        from backend.api.handlers.admin import ToolToggleBody, toggle_tool
        from backend.nodes.tools import ALL_TOOLS
        from backend.services import tool_policy

        target = ALL_TOOLS[0].name
        await toggle_tool(self._admin_request(), target, ToolToggleBody(enabled=False))

        assert target in tool_policy.get_disabled(tool_policy.GLOBAL_SCOPE)
        assert tool_policy.is_allowed("qualquer-usuario", target) is False

    @pytest.mark.asyncio
    async def test_toggle_back_on_reenables(self):
        from backend.api.handlers.admin import ToolToggleBody, toggle_tool
        from backend.nodes.tools import ALL_TOOLS
        from backend.services import tool_policy

        target = ALL_TOOLS[0].name
        await toggle_tool(self._admin_request(), target, ToolToggleBody(enabled=False))
        await toggle_tool(self._admin_request(), target, ToolToggleBody(enabled=True))

        assert tool_policy.is_allowed("qualquer-usuario", target) is True

    @pytest.mark.asyncio
    async def test_toggle_unknown_tool_404(self):
        from fastapi import HTTPException

        from backend.api.handlers.admin import ToolToggleBody, toggle_tool

        with pytest.raises(HTTPException) as exc:
            await toggle_tool(
                self._admin_request(),
                "ferramenta-que-nao-existe",
                ToolToggleBody(enabled=False),
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_toggle_requires_admin_role(self):
        from unittest.mock import MagicMock

        from fastapi import HTTPException

        from backend.api.handlers.admin import ToolToggleBody, toggle_tool
        from backend.nodes.tools import ALL_TOOLS

        request = MagicMock()
        request.state.user = MagicMock(role="member", id="u1")

        with pytest.raises(HTTPException) as exc:
            await toggle_tool(request, ALL_TOOLS[0].name, ToolToggleBody(enabled=False))
        assert exc.value.status_code == 403
