"""Tests para o DiagnosticToolNode dinâmico (S6).

O nó resolve o toolset por usuário (via tool_resolver) a partir do
``config.configurable.user_id``. Validamos a resolução (quais tools entram no
ToolNode efetivo); a execução em si é responsabilidade do ToolNode do LangGraph,
coberta pelos testes de grafo.
"""

from __future__ import annotations

import pytest
from langchain_core.tools import tool

from src.nodes.debug import DiagnosticToolNode


@tool
def echo_tool(text: str) -> str:
    """Devolve o texto recebido."""
    return f"echo:{text}"


@tool
def other_tool(x: str) -> str:
    """Outra tool."""
    return x


@pytest.mark.asyncio
async def test_resolves_user_toolset(monkeypatch):
    async def _resolve(uid):
        assert uid == "u1"
        return [echo_tool]

    monkeypatch.setattr("vectora.services.tool_resolver.resolve_tools", _resolve)

    dnode = DiagnosticToolNode(tools=[echo_tool, other_tool])
    node = await dnode._user_node({"configurable": {"user_id": "u1"}})
    assert "echo_tool" in node.tools_by_name
    assert "other_tool" not in node.tools_by_name


@pytest.mark.asyncio
async def test_disabled_tool_absent_from_node(monkeypatch):
    # Tool desabilitada para o usuário → não entra no ToolNode efetivo,
    # então não pode ser executada.
    async def _resolve(_uid):
        return []

    monkeypatch.setattr("vectora.services.tool_resolver.resolve_tools", _resolve)

    dnode = DiagnosticToolNode(tools=[echo_tool])
    node = await dnode._user_node({"configurable": {"user_id": "u1"}})
    assert "echo_tool" not in node.tools_by_name


@pytest.mark.asyncio
async def test_local_user_gets_all_builtins(monkeypatch):
    from src.services import tool_resolver

    # Sem user_id → resolve_tools usa o caminho local (ALL_TOOLS).
    monkeypatch.setattr(tool_resolver, "ALL_TOOLS", [echo_tool, other_tool])

    dnode = DiagnosticToolNode(tools=[echo_tool])
    node = await dnode._user_node({"configurable": {}})
    assert "echo_tool" in node.tools_by_name
    assert "other_tool" in node.tools_by_name


@pytest.mark.asyncio
async def test_resolution_failure_falls_back_to_self(monkeypatch):
    async def _boom(_uid):
        raise RuntimeError("down")

    monkeypatch.setattr("vectora.services.tool_resolver.resolve_tools", _boom)

    dnode = DiagnosticToolNode(tools=[echo_tool])
    node = await dnode._user_node({"configurable": {"user_id": "u1"}})
    # Fallback é o próprio nó (toolset base).
    assert node is dnode
