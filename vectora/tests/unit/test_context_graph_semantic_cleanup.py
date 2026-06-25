"""Testes para backend/services/context_graph/semantic_cleanup.py."""

from __future__ import annotations

from backend.services.context_graph.semantic_cleanup import (
    MAX_SEMANTIC_FRAGMENT_BYTES,
    MAX_SEMANTIC_HYPEREDGE_NODES,
    _is_sentence_like_rationale_label,
    sanitize_semantic_fragment,
    validate_semantic_fragment,
)

# ─────────────────────────── validate_semantic_fragment ──────────────────────


class TestValidateSemanticFragment:
    def test_valid_minimal_fragment(self) -> None:
        fragment = {
            "nodes": [{"id": "node.A", "label": "A", "file_type": "code"}],
            "edges": [{"source": "node.A", "target": "node.A", "relation": "calls"}],
            "hyperedges": [],
        }
        assert validate_semantic_fragment(fragment) == []

    def test_not_a_dict_returns_error(self) -> None:
        errors = validate_semantic_fragment(["not", "a", "dict"])
        assert any("JSON object" in e or "must be a JSON object" in e for e in errors)

    def test_payload_too_large(self) -> None:
        big_text = "x" * (MAX_SEMANTIC_FRAGMENT_BYTES + 1)
        errors = validate_semantic_fragment({"nodes": [], "extra": big_text})
        assert any("bytes" in e for e in errors)

    def test_invalid_node_id(self) -> None:
        fragment = {
            "nodes": [{"id": "bad/id", "label": "A", "file_type": "code"}],
            "edges": [],
        }
        errors = validate_semantic_fragment(fragment)
        assert any("path separators" in e or "unsupported" in e for e in errors)

    def test_invalid_file_type(self) -> None:
        fragment = {
            "nodes": [{"id": "node.A", "label": "A", "file_type": "illegal_type"}],
            "edges": [],
        }
        errors = validate_semantic_fragment(fragment)
        assert any("file_type" in e for e in errors)

    def test_hyperedge_too_many_nodes(self) -> None:
        many_nodes = [f"n{i}" for i in range(MAX_SEMANTIC_HYPEREDGE_NODES + 1)]
        fragment = {
            "nodes": [],
            "edges": [],
            "hyperedges": [{"id": "he.1", "nodes": many_nodes}],
        }
        errors = validate_semantic_fragment(fragment)
        assert any("hyperedge" in e.lower() or "256" in e for e in errors)

    def test_valid_fragment_all_file_types(self) -> None:
        for ft in ("code", "document", "paper", "image", "rationale", "concept"):
            errors = validate_semantic_fragment(
                {"nodes": [{"id": "n.1", "label": "N", "file_type": ft}], "edges": []}
            )
            assert errors == [], f"file_type {ft!r} should be valid"


# ─────────────────────────── sanitize_semantic_fragment ──────────────────────


class TestSanitizeSemanticFragment:
    def _base(self) -> dict:
        return {
            "nodes": [
                {"id": "n.real", "label": "RealNode", "file_type": "code"},
            ],
            "edges": [],
            "hyperedges": [],
        }

    def test_removes_rationale_type_node(self) -> None:
        fragment = {
            "nodes": [
                {"id": "n.real", "label": "RealNode", "file_type": "code"},
                {
                    "id": "n.rat",
                    "label": "This is a rationale sentence that explains the design decision made here.",
                    "file_type": "rationale",
                },
            ],
            "edges": [],
            "hyperedges": [],
        }
        result = sanitize_semantic_fragment(fragment)
        ids = {n["id"] for n in result["nodes"]}
        assert "n.rat" not in ids
        assert "n.real" in ids

    def test_converts_rationale_for_edge_to_attribute(self) -> None:
        rationale_text = (
            "This node was created to handle the asynchronous dispatch of all "
            "incoming authentication tokens in the pipeline."
        )
        fragment = {
            "nodes": [
                {"id": "n.target", "label": "AuthHandler", "file_type": "code"},
                {"id": "n.rat", "label": rationale_text, "file_type": "rationale"},
            ],
            "edges": [
                {"source": "n.rat", "target": "n.target", "relation": "rationale_for"}
            ],
            "hyperedges": [],
        }
        result = sanitize_semantic_fragment(fragment)
        ids = {n["id"] for n in result["nodes"]}
        assert "n.rat" not in ids
        target = next(n for n in result["nodes"] if n["id"] == "n.target")
        assert "rationale" in target
        assert rationale_text in target["rationale"]

    def test_removes_orphan_edges(self) -> None:
        fragment = {
            "nodes": [
                {"id": "n.real", "label": "Real", "file_type": "code"},
                {
                    "id": "n.rat",
                    "label": "This is a long rationale sentence that triggers cleanup logic.",
                    "file_type": "rationale",
                },
            ],
            "edges": [
                {"source": "n.rat", "target": "n.real", "relation": "references"},
                {"source": "n.real", "target": "n.real", "relation": "calls"},
            ],
            "hyperedges": [],
        }
        result = sanitize_semantic_fragment(fragment)
        for e in result["edges"]:
            assert e.get("source") != "n.rat"
            assert e.get("target") != "n.rat"

    def test_filters_hyperedge_with_one_member(self) -> None:
        fragment = {
            "nodes": [
                {"id": "n.real", "label": "Real", "file_type": "code"},
                {
                    "id": "n.rat",
                    "label": "Another long sentence that reads like prose and should be cleaned.",
                    "file_type": "rationale",
                },
            ],
            "edges": [],
            "hyperedges": [
                {"id": "he.1", "nodes": ["n.real", "n.rat"]},
            ],
        }
        result = sanitize_semantic_fragment(fragment)
        assert result["hyperedges"] == []

    def test_keeps_hyperedge_with_two_surviving_members(self) -> None:
        fragment = {
            "nodes": [
                {"id": "n.a", "label": "A", "file_type": "code"},
                {"id": "n.b", "label": "B", "file_type": "code"},
                {
                    "id": "n.rat",
                    "label": "This rationale node should be removed from the hyperedge nodes list.",
                    "file_type": "rationale",
                },
            ],
            "edges": [],
            "hyperedges": [{"id": "he.1", "nodes": ["n.a", "n.b", "n.rat"]}],
        }
        result = sanitize_semantic_fragment(fragment)
        assert len(result["hyperedges"]) == 1
        assert set(result["hyperedges"][0]["nodes"]) == {"n.a", "n.b"}

    def test_no_nodes_removed_when_clean(self) -> None:
        fragment = {
            "nodes": [
                {"id": "n.a", "label": "Foo", "file_type": "code"},
                {"id": "n.b", "label": "Bar", "file_type": "document"},
            ],
            "edges": [{"source": "n.a", "target": "n.b", "relation": "imports"}],
            "hyperedges": [],
        }
        result = sanitize_semantic_fragment(fragment)
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1


# ─────────────────────────── _is_sentence_like_rationale_label ───────────────


class TestIsSentenceLikeRationaleLabel:
    def test_short_label_is_false(self) -> None:
        assert _is_sentence_like_rationale_label("AuthService") is False

    def test_long_with_punctuation_is_true(self) -> None:
        label = (
            "This node was created to manage the asynchronous dispatch of all incoming "
            "authentication requests across the pipeline."
        )
        assert _is_sentence_like_rationale_label(label) is True

    def test_long_without_punctuation_is_false(self) -> None:
        label = "A" * 90
        assert _is_sentence_like_rationale_label(label) is False

    def test_empty_string_is_false(self) -> None:
        assert _is_sentence_like_rationale_label("") is False

    def test_many_words_with_colon_is_true(self) -> None:
        label = "Decision: use Redis for session storage because it is fast"
        assert _is_sentence_like_rationale_label(label) is True
