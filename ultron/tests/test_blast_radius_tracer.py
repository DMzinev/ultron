"""
ultron.tests.test_blast_radius_tracer
Unit test suite asserting graph reachability, cyclic termination, and blast radius calculation.
"""

import unittest
from ultron.core.blast_radius import BlastRadiusTracer, norm_id


class TestBlastRadiusTracer(unittest.TestCase):
    """Unit tests for BlastRadiusTracer graph traversal and impact calculation."""

    def setUp(self):
        # Linear Graph: A -> B -> C -> D -> E
        self.linear_nodes = [{"id": x, "complexity": 2.0} for x in ["A", "B", "C", "D", "E"]]
        self.linear_edges = [
            {"source": "A", "target": "B"},
            {"source": "B", "target": "C"},
            {"source": "C", "target": "D"},
            {"source": "D", "target": "E"},
        ]

        # Cyclic Graph: X -> Y -> Z -> X
        self.cyclic_nodes = [{"id": x} for x in ["X", "Y", "Z"]]
        self.cyclic_edges = [
            {"source": "X", "target": "Y"},
            {"source": "Y", "target": "Z"},
            {"source": "Z", "target": "X"},
        ]

    def test_norm_id(self):
        """Asserts path separators are normalized to POSIX forward slashes."""
        self.assertEqual(norm_id("ultron\\core\\scoring.py"), "ultron/core/scoring.py")
        self.assertEqual(norm_id("mod.py"), "mod.py")
        self.assertEqual(norm_id(None), "")

    def test_linear_downstream_and_upstream(self):
        """Asserts direct and transitive parents/dependents on linear chain."""
        # For node 'C':
        # Downstream (C depends on D, and D depends on E): direct=[D], transitive=[E]
        downstream = BlastRadiusTracer.find_downstream_dependents(self.linear_nodes, self.linear_edges, "C")
        self.assertEqual(downstream["direct_dependents"], ["D"])
        self.assertEqual(downstream["transitive_dependents"], ["E"])
        self.assertEqual(downstream["total_downstream_count"], 2)
        self.assertFalse(downstream["cycle_detected"])

        # Upstream (B depends on C, and A depends on B): direct=[B], transitive=[A]
        upstream = BlastRadiusTracer.find_upstream_dependencies(self.linear_nodes, self.linear_edges, "C")
        self.assertEqual(upstream["direct_parents"], ["B"])
        self.assertEqual(upstream["transitive_parents"], ["A"])
        self.assertEqual(upstream["total_upstream_count"], 2)
        self.assertFalse(upstream["cycle_detected"])

    def test_cyclic_graph_termination_and_flag(self):
        """Asserts cyclic graph traversal terminates without recursion and sets cycle_detected."""
        res = BlastRadiusTracer.find_downstream_dependents(self.cyclic_nodes, self.cyclic_edges, "X")
        self.assertTrue(res["cycle_detected"])
        self.assertEqual(res["direct_dependents"], ["Y"])
        self.assertEqual(res["transitive_dependents"], ["Z"])
        self.assertEqual(res["total_downstream_count"], 2)

    def test_depth_bounding(self):
        """Asserts traversal strictly respects max_depth parameter."""
        # Max depth = 1 from 'A' should only see 'B' (direct), not 'C', 'D', 'E'
        bounded = BlastRadiusTracer.find_downstream_dependents(self.linear_nodes, self.linear_edges, "A", max_depth=1)
        self.assertEqual(bounded["direct_dependents"], ["B"])
        self.assertEqual(bounded["transitive_dependents"], [])
        self.assertEqual(bounded["total_downstream_count"], 1)

    def test_shortest_path_finding(self):
        """Asserts shortest path resolution across graph."""
        path_a_to_e = BlastRadiusTracer.find_shortest_path(self.linear_nodes, self.linear_edges, "A", "E")
        self.assertEqual(path_a_to_e, ["A", "B", "C", "D", "E"])

        path_self = BlastRadiusTracer.find_shortest_path(self.linear_nodes, self.linear_edges, "C", "C")
        self.assertEqual(path_self, ["C"])

        # Disconnected or reverse path (E cannot reach A in directed graph)
        path_disconnected = BlastRadiusTracer.find_shortest_path(self.linear_nodes, self.linear_edges, "E", "A")
        self.assertEqual(path_disconnected, [])

    def test_blast_radius_score_computation(self):
        """Asserts blast score calculation integrates reachability and complexity."""
        blast_info = BlastRadiusTracer.compute_blast_radius_score("C", self.linear_nodes, self.linear_edges)
        self.assertEqual(blast_info["target_id"], "C")
        self.assertEqual(blast_info["total_impacted_modules"], 4) # 2 down + 2 up
        self.assertGreater(blast_info["blast_score"], 0.0)


if __name__ == "__main__":
    unittest.main()
