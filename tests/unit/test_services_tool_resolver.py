"""Tests para vectora/services/tool_resolver.py — toolset por usuário (S4).

resolve_tools = built-ins permitidas (tool_policy) + tools MCP do usuário.
Mocka tool_policy e plugins.get_user_mcp_tools para isolar a lógica.
"""

from __future__ import annotations

import pytest

from vectora.services import tool_resolver


class _FakeTool:
    def __init__(self, name: str) -> None:
        self.name = name


@pytest.fixture
def fake_all_tools(monkeypatch):
    tools = [_FakeTool("file_read"), _FakeTool("terminal"), _FakeTool("grep")]
    monkeypatch.setattr(tool_resolver, "ALL_TOOLS", tools)
    return tools


@pytest.mark.asyncio
async def test_local_user_gets_all_tools(fake_all_tools, monkeypatch):
    """Sem user_id (CLI/local) → ALL_TOOLS, sem consulta de policy/MCP."""
    result = await tool_resolver.resolve_tools(None)
    assert [t.name for t in result] == ["file_read", "terminal", "grep"]


@pytest.mark.asyncio
async def test_filters_disabled_tools(fake_all_tools, monkeypatch):
    monkeypatch.setattr(
        "vectora.services.tool_policy.is_allowed",
        lambda uid, name: name != "terminal",
    )

    async def _no_mcp(_uid):
        return []

    monkeypatch.setattr(tool_resolver, "get_user_mcp_tools", _no_mcp)

    result = await tool_resolver.resolve_tools("u1")
    names = [t.name for t in result]
    assert "terminal" not in names
    assert "file_read" in names
    assert "grep" in names


@pytest.mark.asyncio
async def test_appends_mcp_tools(fake_all_tools, monkeypatch):
    monkeypatch.setattr(
        "vectora.services.tool_policy.is_allowed", lambda uid, name: True
    )

    async def _mcp(_uid):
        return [_FakeTool("mcp_search")]

    monkeypatch.setattr(tool_resolver, "get_user_mcp_tools", _mcp)

    result = await tool_resolver.resolve_tools("u1")
    names = [t.name for t in result]
    assert "mcp_search" in names
    assert names.count("mcp_search") == 1
    # built-ins continuam presentes
    assert "file_read" in names


@pytest.mark.asyncio
async def test_mcp_failure_degrades_to_builtins(fake_all_tools, monkeypatch):
    monkeypatch.setattr(
        "vectora.services.tool_policy.is_allowed", lambda uid, name: True
    )

    async def _boom(_uid):
        raise RuntimeError("mcp down")

    monkeypatch.setattr(tool_resolver, "get_user_mcp_tools", _boom)

    # Falha de MCP não derruba a resolução — retorna só os built-ins.
    result = await tool_resolver.resolve_tools("u1")
    assert [t.name for t in result] == ["file_read", "terminal", "grep"]
