"""
ultron.tests.test_cycle_detector
Unit test suite asserting circular dependency and circular import detection properties.
"""

import unittest
from ultron.core.cycle_detector import CycleDetector, norm_id


class TestCycleDetector(unittest.TestCase):
    """Unit tests for deterministic CycleDetector."""

    def test_norm_id(self):
        """Asserts path normalization to POSIX format."""
        self.assertEqual(norm_id("ultron\\core\\analyzer.py"), "ultron/core/analyzer.py")
        self.assertEqual(norm_id(None), "")

    def test_acyclic_graph_has_zero_cycles(self):
        """Asserts DAGs return empty cycle lists."""
        edges = [
            {"source": "a.py", "target": "b.py"},
            {"source": "b.py", "target": "c.py"},
            {"source": "a.py", "target": "c.py"},
        ]
        cycles = CycleDetector.find_all_cycles(edges=edges)
        self.assertEqual(len(cycles), 0)

    def test_two_node_mutual_import_cycle(self):
        """Asserts 2-node mutual import is detected."""
        edges = [
            {"source": "mod_a.py", "target": "mod_b.py"},
            {"source": "mod_b.py", "target": "mod_a.py"},
        ]
        cycles = CycleDetector.find_all_cycles(edges=edges)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0]["length"], 2)
        self.assertEqual(set(cycles[0]["nodes"]), {"mod_a.py", "mod_b.py"})
        self.assertEqual(cycles[0]["cycle_path"], ["mod_a.py", "mod_b.py", "mod_a.py"])

    def test_three_node_cycle(self):
        """Asserts 3-node directed cycle is detected and canonicalized."""
        edges = [
            {"source": "x.py", "target": "y.py"},
            {"source": "y.py", "target": "z.py"},
            {"source": "z.py", "target": "x.py"},
        ]
        cycles = CycleDetector.find_all_cycles(edges=edges)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0]["length"], 3)
        self.assertEqual(cycles[0]["cycle_path"], ["x.py", "y.py", "z.py", "x.py"])

    def test_disjoint_multiple_cycles(self):
        """Asserts multiple disconnected cycles are both found."""
        edges = [
            {"source": "c1_a.py", "target": "c1_b.py"},
            {"source": "c1_b.py", "target": "c1_a.py"},
            {"source": "c2_x.py", "target": "c2_y.py"},
            {"source": "c2_y.py", "target": "c2_x.py"},
        ]
        cycles = CycleDetector.find_all_cycles(edges=edges)
        self.assertEqual(len(cycles), 2)

    def test_break_cycle_edge_recommendation(self):
        """Asserts break edge suggestion selects candidate with lowest friction."""
        cycle_path = ["alpha.py", "beta.py", "gamma.py", "alpha.py"]
        node_lookup = {
            "alpha.py": {"complexity": 10.0, "fanout": 5.0},
            "beta.py": {"complexity": 2.0, "fanout": 1.0}, # lowest friction target
            "gamma.py": {"complexity": 8.0, "fanout": 4.0},
        }
        rec = CycleDetector.suggest_break_cycle_edge(cycle_path, node_lookup=node_lookup)
        self.assertEqual(rec["target"], "beta.py")
        self.assertEqual(rec["source"], "alpha.py")


if __name__ == "__main__":
    unittest.main()
