"""
ultron.tests.test_anti_pattern_detector
Unit test suite asserting architectural anti-pattern and smell detection.
"""

import unittest
from ultron.core.anti_pattern_detector import AntiPatternDetector, norm_path


class TestAntiPatternDetector(unittest.TestCase):
    """Unit tests for deterministic AntiPatternDetector."""

    def test_norm_path(self):
        """Asserts path normalization to POSIX format."""
        self.assertEqual(norm_path("ultron\\core\\analyzer.py"), "ultron/core/analyzer.py")
        self.assertEqual(norm_path(None), "")

    def test_detect_god_object(self):
        """Asserts God Object detection when LOC, complexity, and coupling exceed thresholds."""
        risks = [{
            "file": "monolith_manager.py",
            "lines_of_code": 120,
            "complexity": 15.0
        }]
        edges = [
            {"source": "monolith_manager.py", "target": f"dep_{i}.py"} for i in range(6)
        ]
        patterns = AntiPatternDetector.detect_anti_patterns(edges=edges, risks=risks)
        god_patterns = [p for p in patterns if p["pattern_type"] == "GOD_OBJECT"]
        self.assertEqual(len(god_patterns), 1)
        self.assertEqual(god_patterns[0]["severity"], "HIGH")
        self.assertIn("Decompose", god_patterns[0]["playbook"])

    def test_detect_feature_envy(self):
        """Asserts Feature Envy detection when Ce is high relative to Ca."""
        edges = [
            {"source": "envy_service.py", "target": f"foreign_{i}.py"} for i in range(5)
        ]
        patterns = AntiPatternDetector.detect_anti_patterns(edges=edges, risks=[])
        envy_patterns = [p for p in patterns if p["pattern_type"] == "FEATURE_ENVY"]
        self.assertEqual(len(envy_patterns), 1)
        self.assertEqual(envy_patterns[0]["severity"], "MEDIUM")

    def test_detect_shotgun_surgery(self):
        """Asserts Shotgun Surgery detection on high fan-in bottleneck nodes."""
        edges = [
            {"source": f"caller_{i}.py", "target": "bottleneck_core.py"} for i in range(8)
        ]
        patterns = AntiPatternDetector.detect_anti_patterns(edges=edges, risks=[])
        shotgun_patterns = [p for p in patterns if p["pattern_type"] == "SHOTGUN_SURGERY"]
        self.assertEqual(len(shotgun_patterns), 1)
        self.assertEqual(shotgun_patterns[0]["severity"], "MEDIUM")

    def test_detect_dead_abstraction(self):
        """Asserts Dead Abstraction detection on unreferenced abstract modules."""
        risks = [{"file": "base_unreferenced_interface.py", "complexity": 1.0}]
        patterns = AntiPatternDetector.detect_anti_patterns(edges=[], risks=risks)
        dead_patterns = [p for p in patterns if p["pattern_type"] == "DEAD_ABSTRACTION"]
        self.assertEqual(len(dead_patterns), 1)
        self.assertEqual(dead_patterns[0]["severity"], "LOW")

    def test_empty_clean_codebase(self):
        """Asserts empty or clean codebases yield zero false positive anti-patterns."""
        self.assertEqual(AntiPatternDetector.detect_anti_patterns([], [], []), [])


if __name__ == "__main__":
    unittest.main()
