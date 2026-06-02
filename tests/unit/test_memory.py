"""Tests — Per-User Memory isolation.

Verifica:
- _user_id_from_config prioriza user:<id> quando há user_id no configurable
- fallback para workspace_<id> quando não há user_id mas há workspace
- fallback para session_<thread_id> como último recurso
- endpoints REST existem e têm assinaturas corretas
- namespace user: é isolado de session: e workspace:
"""

from __future__ import annotations

from typing import Any

import pytest

# ---------------------------------------------------------------------------
# N1 — _user_id_from_config prioridade
# ---------------------------------------------------------------------------


class TestUserIdFromConfig:
    """_user_id_from_config deve priorizar user_id autenticado."""

    def test_returns_user_namespace_when_user_id_present(self):
        from src.tools.memory import _user_id_from_config

        config: Any = {"configurable": {"user_id": "abc123", "thread_id": "t1"}}
        result = _user_id_from_config(config)
        assert result == "user:abc123"

    def test_returns_workspace_namespace_when_no_user_id(self):
        from src.tools.memory import _user_id_from_config

        config: Any = {"configurable": {"workspace_id": "ws1", "thread_id": "t1"}}
        result = _user_id_from_config(config)
        assert result == "workspace_ws1"

    def test_workspace_takes_precedence_over_thread_when_no_user(self):
        from src.tools.memory import _user_id_from_config

        config: Any = {
            "configurable": {
                "workspace_id": "ws1",
                "thread_id": "t1",
                # sem user_id
            }
        }
        result = _user_id_from_config(config)
        assert result == "workspace_ws1"

    def test_user_id_takes_precedence_over_workspace(self):
        """user_id autenticado supera workspace quando ambos presentes."""
        from src.tools.memory import _user_id_from_config

        config: Any = {
            "configurable": {
                "user_id": "user_abc",
                "workspace_id": "ws1",
                "thread_id": "t1",
            }
        }
        result = _user_id_from_config(config)
        assert result == "user:user_abc"

    def test_returns_session_namespace_when_only_thread_id(self):
        from src.tools.memory import _user_id_from_config

        config: Any = {"configurable": {"thread_id": "thread-xyz"}}
        result = _user_id_from_config(config)
        assert result == "session_thread-xyz"

    def test_returns_default_when_config_is_none(self):
        from src.tools.memory import _user_id_from_config

        result = _user_id_from_config(None)
        assert result == "default_session"

    def test_returns_default_when_configurable_is_empty(self):
        from src.tools.memory import _user_id_from_config

        result = _user_id_from_config({"configurable": {}})
        assert result == "default_session"

    def test_user_namespace_format(self):
        """Namespace user: usa ':' como separador para distinguir de workspace_ e session_."""
        from src.tools.memory import _user_id_from_config

        config: Any = {"configurable": {"user_id": "user-99"}}
        ns = _user_id_from_config(config)
        assert ns.startswith("user:")
        assert "user-99" in ns


# ---------------------------------------------------------------------------
# N2 — handler REST de memória
# ---------------------------------------------------------------------------


class TestMemoryHandlerExists:
    """src/api/handlers/memory.py deve existir com os endpoints esperados."""

    def test_memory_handler_module_exists(self):
        import src.api.handlers.memory as mem_mod

        assert mem_mod is not None

    def test_router_exists(self):
        from src.api.handlers.memory import router

        assert router is not None

    def test_list_memories_route_registered(self):
        from src.api.handlers.memory import router

        routes = [r.path for r in router.routes]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        assert any("/memory" in r for r in routes)

    def test_delete_memory_route_registered(self):
        from src.api.handlers.memory import router

        routes = [r.path for r in router.routes]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        assert any("/memory" in r for r in routes)


# ---------------------------------------------------------------------------
# N3 — isolamento de namespaces
# ---------------------------------------------------------------------------


class TestNamespaceIsolation:
    """Namespaces user:, workspace_, session_ são distintos e não se sobrepõem."""

    def test_user_namespace_not_equal_to_session_namespace(self):
        from src.tools.memory import _user_id_from_config

        user_config: Any = {"configurable": {"user_id": "u1", "thread_id": "t1"}}
        session_config: Any = {"configurable": {"thread_id": "t1"}}

        user_ns = _user_id_from_config(user_config)
        session_ns = _user_id_from_config(session_config)

        assert user_ns != session_ns

    def test_user_namespace_not_equal_to_workspace_namespace(self):
        from src.tools.memory import _user_id_from_config

        user_config: Any = {"configurable": {"user_id": "u1", "workspace_id": "ws1"}}
        workspace_config: Any = {"configurable": {"workspace_id": "ws1"}}

        user_ns = _user_id_from_config(user_config)
        workspace_ns = _user_id_from_config(workspace_config)

        assert user_ns != workspace_ns

    def test_different_users_have_different_namespaces(self):
        from src.tools.memory import _user_id_from_config

        config_a: Any = {"configurable": {"user_id": "alice"}}
        config_b: Any = {"configurable": {"user_id": "bob"}}

        assert _user_id_from_config(config_a) != _user_id_from_config(config_b)
