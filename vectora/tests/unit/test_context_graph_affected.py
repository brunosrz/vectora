"""Testes para backend/services/context_graph/affected.py.

Cobre: resolve_seed, affected_nodes, format_affected.
"""

from __future__ import annotations

import networkx as nx

from backend.services.context_graph.affected import (
    DEFAULT_AFFECTED_RELATIONS,
    AffectedHit,
    affected_nodes,
    format_affected,
    resolve_seed,
)


def _make_graph() -> nx.DiGraph:
    """Grafo dirigido simples para testes:

    A -[calls]-> B -[calls]-> C
    D -[imports]-> B
    E -[unknown_rel]-> B
    """
    g = nx.DiGraph()
    g.add_node("node.A", label="Alpha", source_file="src/a.py")
    g.add_node("node.B", label="Beta()", source_file="src/b.py")
    g.add_node("node.C", label="Gamma", source_file="src/c.py")
    g.add_node("node.D", label="Delta", source_file="src/d.py")
    g.add_node("node.E", label="Epsilon", source_file="src/e.py")

    g.add_edge("node.A", "node.B", relation="calls")
    g.add_edge("node.B", "node.C", relation="calls")
    g.add_edge("node.D", "node.B", relation="imports")
    g.add_edge("node.E", "node.B", relation="unknown_rel")

    return g


# ─────────────────────────── resolve_seed ────────────────────────────────────


class TestResolveSeed:
    def test_exact_id(self) -> None:
        g = _make_graph()
        assert resolve_seed(g, "node.A") == "node.A"

    def test_exact_label(self) -> None:
        g = _make_graph()
        assert resolve_seed(g, "Alpha") == "node.A"

    def test_bare_name_strips_parens(self) -> None:
        g = _make_graph()
        assert resolve_seed(g, "Beta") == "node.B"

    def test_exact_source_file(self) -> None:
        g = _make_graph()
        assert resolve_seed(g, "src/c.py") == "node.C"

    def test_substring_unique(self) -> None:
        g = _make_graph()
        assert resolve_seed(g, "Gamm") == "node.C"

    def test_ambiguous_returns_none(self) -> None:
        g = _make_graph()
        g.add_node("node.X", label="Alpha", source_file="src/x.py")
        assert resolve_seed(g, "Alpha") is None

    def test_not_found_returns_none(self) -> None:
        g = _make_graph()
        assert resolve_seed(g, "nonexistent_xyz") is None

    def test_case_insensitive_label(self) -> None:
        g = _make_graph()
        assert resolve_seed(g, "alpha") == "node.A"


# ─────────────────────────── affected_nodes ──────────────────────────────────


class TestAffectedNodes:
    def test_depth_1(self) -> None:
        g = _make_graph()
        hits = affected_nodes(g, "node.B", depth=1)
        hit_ids = {h.node_id for h in hits}
        assert "node.A" in hit_ids
        assert "node.D" in hit_ids
        assert "node.E" not in hit_ids

    def test_depth_2_propagates_transitively(self) -> None:
        g = _make_graph()
        g.add_edge("node.X", "node.A", relation="calls")
        g.add_node("node.X", label="X", source_file="src/x.py")
        hits = affected_nodes(g, "node.B", depth=2)
        hit_ids = {h.node_id for h in hits}
        assert "node.A" in hit_ids
        assert "node.X" in hit_ids

    def test_unlisted_relation_not_propagated(self) -> None:
        g = _make_graph()
        hits = affected_nodes(g, "node.B", depth=1)
        hit_ids = {h.node_id for h in hits}
        assert "node.E" not in hit_ids

    def test_empty_graph_returns_empty(self) -> None:
        g = nx.DiGraph()
        g.add_node("node.A", label="A")
        hits = affected_nodes(g, "node.A", depth=2)
        assert hits == []

    def test_returns_affected_hit_dataclass(self) -> None:
        g = _make_graph()
        hits = affected_nodes(g, "node.B", depth=1)
        assert all(isinstance(h, AffectedHit) for h in hits)
        alpha_hit = next(h for h in hits if h.node_id == "node.A")
        assert alpha_hit.depth == 1
        assert alpha_hit.via_relation == "calls"

    def test_seed_not_in_hits(self) -> None:
        g = _make_graph()
        hits = affected_nodes(g, "node.B", depth=2)
        assert all(h.node_id != "node.B" for h in hits)

    def test_default_relations_tuple(self) -> None:
        assert "calls" in DEFAULT_AFFECTED_RELATIONS
        assert "imports" in DEFAULT_AFFECTED_RELATIONS
        assert "inherits" in DEFAULT_AFFECTED_RELATIONS


# ─────────────────────────── format_affected ─────────────────────────────────


class TestFormatAffected:
    def test_valid_seed_returns_formatted_text(self) -> None:
        g = _make_graph()
        text = format_affected(g, "Beta")
        assert "Beta" in text
        assert "Alpha" in text or "node.A" in text
        assert "calls" in text

    def test_invalid_seed_returns_no_match_message(self) -> None:
        g = _make_graph()
        text = format_affected(g, "this_does_not_exist_xyz")
        assert (
            "No unique node match" in text
            or "não encontrado" in text.lower()
            or "nonexistent" in text.lower()
            or "no unique" in text.lower()
        )

    def test_no_affected_nodes_says_none_found(self) -> None:
        g = nx.DiGraph()
        g.add_node("node.Lone", label="Lone", source_file="lone.py")
        text = format_affected(g, "node.Lone")
        assert "No affected nodes" in text
