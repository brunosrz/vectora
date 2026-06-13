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
        import src.api.handlers.admin as mod

        assert mod is not None

    def test_router_exists(self):
        from src.api.handlers.admin import router

        assert router is not None

    def test_list_users_route_registered(self):
        from src.api.handlers.admin import router

        paths = [r.path for r in router.routes]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        assert any("users" in p for p in paths)

    def test_system_info_route_registered(self):
        from src.api.handlers.admin import router

        paths = [r.path for r in router.routes]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        assert any("system" in p for p in paths)

    def test_config_route_registered(self):
        from src.api.handlers.admin import router

        paths = [r.path for r in router.routes]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        assert any("config" in p for p in paths)

    def test_tools_override_route_registered(self):
        from src.api.handlers.admin import router

        paths = [r.path for r in router.routes]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        assert any("tools" in p for p in paths)


class TestAdminRequiresAdminRole:
    """Endpoints admin devem checar permissão de role."""

    def test_require_admin_decorator_exists(self):
        from src.api.handlers.admin import require_admin

        assert callable(require_admin)

    def test_require_admin_raises_for_member(self):
        """member não tem acesso a endpoints admin."""
        from unittest.mock import MagicMock

        from src.api.handlers.admin import require_admin

        mock_user = MagicMock()
        mock_user.role = "member"

        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            require_admin(mock_user)

    def test_require_admin_passes_for_root(self):
        from unittest.mock import MagicMock

        from src.api.handlers.admin import require_admin

        mock_user = MagicMock()
        mock_user.role = "root"

        # Não deve levantar exceção
        result = require_admin(mock_user)
        assert result is None or result == mock_user

    def test_require_admin_passes_for_admin(self):
        from unittest.mock import MagicMock

        from src.api.handlers.admin import require_admin

        mock_user = MagicMock()
        mock_user.role = "admin"

        result = require_admin(mock_user)
        assert result is None or result == mock_user


class TestAdminSystemInfo:
    """Estrutura do sistema info."""

    def test_system_info_fields_exist(self):
        from src.api.handlers.admin import _build_system_info

        info = _build_system_info()
        assert "version" in info
        assert "python_version" in info
        assert "platform" in info
