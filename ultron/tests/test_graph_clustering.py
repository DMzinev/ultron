"""
ultron.tests.test_graph_clustering
Unit test suite asserting deterministic multi-level graph clustering and edge weight aggregation.
"""

import unittest
from ultron.core.graph_clustering import GraphClusterEngine


class TestGraphClusterEngine(unittest.TestCase):
    """Unit tests for GraphClusterEngine."""

    def setUp(self):
        self.sample_graph = {
            "nodes": [
                {"id": "src/core/engine.py", "complexity": 14, "level": "HIGH"},
                {"id": "src/core/parser.py", "complexity": 6, "level": "LOW"},
                {"id": "src/interfaces/cli.py", "complexity": 4, "level": "LOW"},
                {"id": "src/interfaces/web.py", "complexity": 8, "level": "MED"},
                {"id": "main.py", "complexity": 2, "level": "LOW"}
            ],
            "links": [
                {"source": "src/core/engine.py", "target": "src/core/parser.py", "weight": 2},
                {"source": "src/interfaces/cli.py", "target": "src/core/engine.py", "weight": 3},
                {"source": "src/interfaces/web.py", "target": "src/core/engine.py", "weight": 5},
                {"source": "main.py", "target": "src/interfaces/cli.py", "weight": 1}
            ]
        }

    def test_system_level_clustering(self):
        """Asserts system level clusters nodes into top-level domains."""
        res = GraphClusterEngine.cluster_graph(self.sample_graph, level="system")
        self.assertEqual(res["level"], "system")
        node_ids = [n["id"] for n in res["nodes"]]
        self.assertIn("core", node_ids)
        self.assertIn("interfaces", node_ids)
        self.assertIn("(root)", node_ids)
        self.assertEqual(res["stats"]["total_files"], 5)

    def test_edge_weight_aggregation(self):
        """Asserts multiple links between same domains are merged and weights summed."""
        res = GraphClusterEngine.cluster_graph(self.sample_graph, level="system")
        # interfaces -> core has two file links (3 + 5 = 8)
        inter_edge = next((l for l in res["links"] if l["source"] == "interfaces" and l["target"] == "core"), None)
        self.assertIsNotNone(inter_edge)
        self.assertEqual(inter_edge["weight"], 8)
        self.assertEqual(inter_edge["sub_links_count"], 2)

    def test_file_level_passthrough(self):
        """Asserts level='file' preserves raw node and link counts."""
        res = GraphClusterEngine.cluster_graph(self.sample_graph, level="file")
        self.assertEqual(res["level"], "file")
        self.assertEqual(len(res["nodes"]), 5)
        self.assertEqual(len(res["links"]), 4)

    def test_empty_graph_handling(self):
        """Asserts empty graph dictionary returns valid empty cluster response."""
        res = GraphClusterEngine.cluster_graph({}, level="system")
        self.assertEqual(res["level"], "file")
        self.assertEqual(len(res["nodes"]), 0)
        self.assertEqual(len(res["links"]), 0)

    def test_single_node_graph(self):
        """Asserts single node graph clusters gracefully without exceptions."""
        single_g = {"nodes": [{"id": "app.py", "complexity": 1}], "links": []}
        res = GraphClusterEngine.cluster_graph(single_g, level="system")
        self.assertEqual(len(res["nodes"]), 1)
        self.assertEqual(res["nodes"][0]["id"], "(root)")

    def test_common_prefix_clustering(self):
        """Asserts repos with single root prefix (e.g. ultron/...) correctly segment subdomains."""
        g = {
            "nodes": [
                {"id": "ultron/core/engine.py", "complexity": 10},
                {"id": "ultron/interfaces/web.py", "complexity": 5}
            ],
            "links": [
                {"source": "ultron/interfaces/web.py", "target": "ultron/core/engine.py", "weight": 2}
            ]
        }
        res = GraphClusterEngine.cluster_graph(g, level="system")
        domains = [n["id"] for n in res["nodes"]]
        self.assertIn("core", domains)
        self.assertIn("interfaces", domains)

    def test_flat_repository_anti_collapse(self):
        """Asserts flat repositories (<60 files at root) do not collapse to a single circle."""
        flat_g = {
            "nodes": [{"id": f"mod_{i}.py", "complexity": i + 1} for i in range(10)],
            "links": [{"source": f"mod_{i}.py", "target": f"mod_{i+1}.py", "weight": 1} for i in range(9)]
        }
        res = GraphClusterEngine.cluster_graph(flat_g, level="system")
        # Must NOT collapse to 1 node
        self.assertEqual(len(res["nodes"]), 10)
        self.assertEqual(len(res["links"]), 9)
        self.assertTrue(res.get("stats", {}).get("adaptive_fallback", False))

    def test_large_flat_repository_prefix_clustering(self):
        """Asserts large flat repositories (>60 files) cluster by prefix instead of single (root)."""
        large_flat_nodes = []
        for i in range(80):
            pfx = "core" if i < 30 else ("api" if i < 60 else "utils")
            large_flat_nodes.append({"id": f"{pfx}_mod_{i}.py", "complexity": 2})
        large_flat_links = [{"source": "core_mod_0.py", "target": "api_mod_30.py", "weight": 2}]
        g = {"nodes": large_flat_nodes, "links": large_flat_links}
        res = GraphClusterEngine.cluster_graph(g, level="system")
        node_ids = [n["id"] for n in res["nodes"]]
        self.assertGreaterEqual(len(node_ids), 2)
        self.assertIn("core", node_ids)
    def test_adaptive_boundary_expansion_thresholds(self):
        """Adaptive Test Expansion: asserts boundary transitions at N=2, N=59, N=60, N=61."""
        for n_nodes in [2, 15, 59, 60]:
            g = {"nodes": [{"id": f"flat_{i}.py", "complexity": 1} for i in range(n_nodes)], "links": []}
            res = GraphClusterEngine.cluster_graph(g, level="system")
            self.assertEqual(len(res["nodes"]), n_nodes, f"Failed preservation at boundary N={n_nodes}")

        # At N=61 with 2 prefixes: must cluster by prefix rather than single (root)
        g_61 = {
            "nodes": [{"id": f"alpha_{i}.py", "complexity": 1} for i in range(31)] +
                     [{"id": f"beta_{i}.py", "complexity": 1} for i in range(30)],
            "links": []
        }
        res_61 = GraphClusterEngine.cluster_graph(g_61, level="system")
        self.assertEqual(len(res_61["nodes"]), 2)
        pfx_ids = {n["id"] for n in res_61["nodes"]}
        self.assertEqual(pfx_ids, {"alpha", "beta"})


if __name__ == "__main__":
    unittest.main()
