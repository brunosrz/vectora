"""Tests for vectora/graph.py"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END

from vectora.graph import _orchestrator_route, build_graph

if TYPE_CHECKING:
    from vectora.state import State


def test_build_graph_compiles():
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer)
    assert graph is not None


def test_graph_has_expected_nodes():
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer)
    nodes = set(graph.nodes.keys())
    expected = {
        "orchestrator",
        "search",
        "coder",
        "rag_subgraph",
        "process_retrieval",
    }
    assert expected.issubset(nodes)


class TestOrchestratorRoute:
    def _state(self, decision) -> State:
        return {"messages": [], "session_metadata": {}, "routing_decision": decision}  # type: ignore[typeddict-item]

    def test_respond_routes_to_end(self):
        assert _orchestrator_route(self._state("respond")) == END

    def test_search_routes_to_search(self):
        assert _orchestrator_route(self._state("search")) == "search"

    def test_coder_routes_to_coder(self):
        assert _orchestrator_route(self._state("coder")) == "coder"

    def test_rag_routes_to_rag_subgraph(self):
        assert _orchestrator_route(self._state("rag")) == "rag_subgraph"

    def test_none_defaults_to_end(self):
        state: State = {"messages": [], "session_metadata": {}}
        assert _orchestrator_route(state) == END

    def test_tools_compat_routes_to_search(self):
        assert _orchestrator_route(self._state("tools")) == "search"
