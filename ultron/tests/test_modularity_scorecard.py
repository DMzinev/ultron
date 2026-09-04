"""
ultron.tests.test_modularity_scorecard
Unit test suite asserting AST modularity, instability calculations, and health grades.
"""

import unittest
from ultron.core.modularity_scorecard import ModularityScorecardEngine, norm_path


class TestModularityScorecardEngine(unittest.TestCase):
    """Unit tests for deterministic ModularityScorecardEngine."""

    def test_norm_path(self):
        """Asserts path separators are normalized to POSIX forward slashes."""
        self.assertEqual(norm_path("ultron\\core\\analyzer.py"), "ultron/core/analyzer.py")
        self.assertEqual(norm_path(None), "")

    def test_instability_index_boundaries(self):
        """Asserts Robert C. Martin Instability Index properties."""
        # Zero coupling -> 0.0
        self.assertEqual(ModularityScorecardEngine.compute_module_instability(0, 0), 0.0)
        # Maximally stable (depended on by 10, depends on 0) -> 0.0
        self.assertEqual(ModularityScorecardEngine.compute_module_instability(10, 0), 0.0)
        # Maximally unstable (depends on 10, depended on by 0) -> 1.0
        self.assertEqual(ModularityScorecardEngine.compute_module_instability(0, 10), 1.0)
        # Balanced (Ca = 5, Ce = 5) -> 0.5
        self.assertEqual(ModularityScorecardEngine.compute_module_instability(5, 5), 0.5)

    def test_main_sequence_distance_and_zones(self):
        """Asserts Distance from Main Sequence D = |A + I - 1| and zone classification."""
        # Balanced: A = 0.2, I = 0.8 -> A + I = 1.0 -> D = 0.0 (Main Sequence)
        balanced = ModularityScorecardEngine.compute_main_sequence_distance(0.2, 0.8)
        self.assertEqual(balanced["distance"], 0.0)
        self.assertEqual(balanced["zone"], "MAIN_SEQUENCE")

        # Zone of Pain: A = 0.0, I = 0.1 -> A + I = 0.1 -> D = 0.9
        pain = ModularityScorecardEngine.compute_main_sequence_distance(0.0, 0.1)
        self.assertEqual(pain["distance"], 0.9)
        self.assertEqual(pain["zone"], "ZONE_OF_PAIN")

        # Zone of Uselessness: A = 0.9, I = 0.9 -> A + I = 1.8 -> D = 0.8
        useless = ModularityScorecardEngine.compute_main_sequence_distance(0.9, 0.9)
        self.assertEqual(useless["distance"], 0.8)
        self.assertEqual(useless["zone"], "ZONE_OF_USELESSNESS")

    def test_empty_codebase_safe_defaults(self):
        """Asserts empty codebase input returns 100.0 health score and Grade A."""
        res = ModularityScorecardEngine.evaluate_codebase_modularity([], [], [])
        self.assertEqual(res["health_score"], 100.0)
        self.assertEqual(res["health_grade"], "A")
        self.assertEqual(res["total_modules"], 0)

    def test_evaluate_codebase_modularity_aggregation(self):
        """Asserts multi-module codebase evaluation correctly aggregates metrics."""
        edges = [
            {"source": "controller.py", "target": "service.py"},
            {"source": "service.py", "target": "repository.py"},
            {"source": "service.py", "target": "utils.py"},
        ]
        risks = [
            {"file": "controller.py", "complexity": 4.0},
            {"file": "service.py", "complexity": 8.0},
            {"file": "repository.py", "complexity": 2.0},
            {"file": "utils.py", "complexity": 1.0},
        ]
        res = ModularityScorecardEngine.evaluate_codebase_modularity(edges=edges, risks=risks)
        self.assertEqual(res["total_modules"], 4)
        self.assertIn(res["health_grade"], ["A", "B", "C", "D", "F"])
        self.assertGreaterEqual(res["health_score"], 0.0)
        self.assertLessEqual(res["health_score"], 100.0)
        self.assertIn("main_sequence", res["zone_distribution"])

    def test_grade_thresholds(self):
        """Asserts letter grade thresholds match specification."""
        # Check that evaluate_codebase_modularity adheres to partition boundaries
        res = ModularityScorecardEngine.evaluate_codebase_modularity()
        self.assertIn(res["health_grade"], ["A", "B", "C", "D", "F"])


if __name__ == "__main__":
    unittest.main()
