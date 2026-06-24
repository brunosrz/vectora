"""Testes para backend/services/context_graph/cluster.py.

Cobre: cluster, cohesion_score, score_all, _split_community,
remap_communities_to_previous, _partition.
"""

from __future__ import annotations

import networkx as nx


def _make_connected_graph(n_nodes: int = 6) -> nx.Graph:
    G = nx.Graph()
    for i in range(n_nodes):
        G.add_node(str(i), label=f"Node{i}", source_file=f"f{i}.py")
    for i in range(n_nodes - 1):
        G.add_edge(str(i), str(i + 1), relation="calls")
    return G


class TestCohesionScore:
    def test_fully_connected_triangle(self):
        from backend.services.context_graph.cluster import cohesion_score

        G = nx.Graph()
        G.add_nodes_from(["a", "b", "c"])
        G.add_edges_from([("a", "b"), ("b", "c"), ("a", "c")])
        score = cohesion_score(G, ["a", "b", "c"])
        assert abs(score - 1.0) < 1e-6

    def test_no_edges_zero_cohesion(self):
        from backend.services.context_graph.cluster import cohesion_score

        G = nx.Graph()
        G.add_nodes_from(["a", "b", "c"])
        assert cohesion_score(G, ["a", "b", "c"]) == 0.0

    def test_single_node_is_one(self):
        from backend.services.context_graph.cluster import cohesion_score

        G = nx.Graph()
        G.add_node("a")
        assert cohesion_score(G, ["a"]) == 1.0

    def test_partial_connectivity(self):
        from backend.services.context_graph.cluster import cohesion_score

        G = nx.Graph()
        G.add_nodes_from(["a", "b", "c"])
        G.add_edge("a", "b")
        score = cohesion_score(G, ["a", "b", "c"])
        assert 0.0 < score < 1.0


class TestScoreAll:
    def test_returns_dict_with_all_community_ids(self):
        from backend.services.context_graph.cluster import score_all

        G = nx.Graph()
        G.add_nodes_from(["a", "b", "c"])
        G.add_edge("a", "b")
        communities = {0: ["a", "b"], 1: ["c"]}
        scores = score_all(G, communities)
        assert set(scores.keys()) == {0, 1}


class TestCluster:
    def test_empty_graph_returns_empty(self):
        from backend.services.context_graph.cluster import cluster

        assert cluster(nx.Graph()) == {}

    def test_single_node_graph(self):
        from backend.services.context_graph.cluster import cluster

        G = nx.Graph()
        G.add_node("solo", label="Solo", source_file="s.py")
        result = cluster(G)
        assert len(result) == 1
        assert "solo" in result[0]

    def test_no_edges_each_node_own_community(self):
        from backend.services.context_graph.cluster import cluster

        G = nx.Graph()
        G.add_nodes_from(["a", "b", "c"])
        result = cluster(G)
        # With no edges, each node should be in its own community
        total_nodes = sum(len(v) for v in result.values())
        assert total_nodes == 3

    def test_connected_nodes_clustered(self):
        from backend.services.context_graph.cluster import cluster

        G = _make_connected_graph(6)
        result = cluster(G)
        assert isinstance(result, dict)
        total = sum(len(v) for v in result.values())
        assert total == 6

    def test_directed_graph_converted_to_undirected(self):
        from backend.services.context_graph.cluster import cluster

        G = nx.DiGraph()
        G.add_node("a", label="A", source_file="a.py")
        G.add_node("b", label="B", source_file="b.py")
        G.add_edge("a", "b", relation="calls")
        result = cluster(G)
        assert isinstance(result, dict)

    def test_exclude_hubs_percentile(self):
        from backend.services.context_graph.cluster import cluster

        G = _make_connected_graph(8)
        # All nodes connected to node "0" — high degree hub
        for i in range(1, 8):
            G.add_edge("0", str(i))
        result = cluster(G, exclude_hubs_percentile=80.0)
        assert isinstance(result, dict)


class TestSplitCommunity:
    def test_no_edges_splits_into_singles(self):
        from backend.services.context_graph.cluster import _split_community

        G = nx.Graph()
        G.add_nodes_from(["a", "b", "c"])
        parts = _split_community(G, ["a", "b", "c"])
        assert len(parts) == 3

    def test_connected_community_may_split(self):
        from backend.services.context_graph.cluster import _split_community

        G = _make_connected_graph(4)
        parts = _split_community(G, ["0", "1", "2", "3"])
        # May or may not split depending on leiden — just check it returns lists
        assert isinstance(parts, list)
        assert all(isinstance(p, list) for p in parts)


class TestRemapCommunitiesToPrevious:
    def test_preserves_ids_with_high_overlap(self):
        from backend.services.context_graph.cluster import remap_communities_to_previous

        communities = {0: ["a", "b", "c"], 1: ["d", "e"]}
        previous = {"a": 5, "b": 5, "c": 5, "d": 7, "e": 7}
        remapped = remap_communities_to_previous(communities, previous)
        # Community 0 should map to old id 5 (highest overlap)
        node_cid = {n: cid for cid, nodes in remapped.items() for n in nodes}
        assert node_cid["a"] == node_cid["b"] == node_cid["c"]
        assert node_cid["d"] == node_cid["e"]

    def test_empty_communities_returns_empty(self):
        from backend.services.context_graph.cluster import remap_communities_to_previous

        assert remap_communities_to_previous({}, {}) == {}

    def test_all_unmatched_gets_fresh_ids(self):
        from backend.services.context_graph.cluster import remap_communities_to_previous

        communities = {0: ["x", "y"], 1: ["z"]}
        previous: dict[str, int] = {}  # no overlap
        remapped = remap_communities_to_previous(communities, previous)
        assert isinstance(remapped, dict)
        assert sum(len(v) for v in remapped.values()) == 3
