import os
import io
import sys
import json
import tempfile
import unittest
from unittest.mock import patch

from ultron.core import sentinel
from ultron.core import context_brief
from ultron.interfaces.server import UltronAPIHandler

class TestKanbanReleaseStability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.repo_path = os.path.abspath(os.path.normpath(cls.temp_dir.name))

        # Create sample module for tests
        cls.sample_file = os.path.join(cls.repo_path, "sample_module.py")
        with open(cls.sample_file, "w", encoding="utf-8") as f:
            f.write("def calculate(a, b):\n    if a > 0:\n        return a + b\n    return b\n")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_sentinel_radon_fallback(self):
        """Verify sentinel calculates AST complexity when radon is absent."""
        code = "def sample(x):\n    if x > 10:\n        for i in range(x):\n            print(i)\n    return x\n"
        # Test get_file_ast_and_metadata with current sentinel state
        tree, complexity, imports, funcs, lines, comments = sentinel.get_file_ast_and_metadata(code)
        self.assertIsNotNone(tree)
        self.assertGreaterEqual(complexity, 1)

        # Force radon absence
        with patch.object(sentinel, 'HAS_RADON', False), patch.object(sentinel, 'ComplexityVisitor', None):
            tree_fb, complexity_fb, _, _, _, _ = sentinel.get_file_ast_and_metadata(code)
            self.assertIsNotNone(tree_fb)
            self.assertGreaterEqual(complexity_fb, 2)  # if + for = at least 2

    def test_context_brief_data_uninitialized_fallback(self):
        """Verify compile_brief_data produces populated top_risks dictionary."""
        brief_data = context_brief.compile_brief_data(self.repo_path)
        self.assertEqual(brief_data["repository_uuid"], "uninitialized")
        self.assertIn("health_score", brief_data)
        self.assertIn("top_risks", brief_data)
        self.assertIsInstance(brief_data["top_risks"], list)
        self.assertIn("raw_text", brief_data)

    def test_server_get_query_data(self):
        """Verify UltronAPIHandler parses GET query parameters correctly."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.command = "GET"
        handler.path = f"/api/analyze?repo={self.repo_path}&intent=test"

        q_data = handler.get_request_data()
        self.assertEqual(q_data.get("repo"), self.repo_path)
        self.assertEqual(q_data.get("intent"), "test")
    def test_evaluate_risks_no_targets_no_intent_scans_all(self):
        """Edge case 1: empty targets + empty intent = full-repo scan."""
        from ultron.core import analyzer
        from ultron.core import risk as risk_mod
        codebase = analyzer.analyze_directory(self.repo_path)
        self.assertGreater(len(codebase), 0, "Codebase must have at least one file")
        risks = risk_mod.evaluate_risks(codebase, [], "", repo_path=self.repo_path)
        self.assertGreater(len(risks), 0, "Full-repo scan must return risks for discovered files")
        scored_files = {r.file_path for r in risks}
        for f in codebase:
            self.assertIn(f, scored_files, f"File '{f}' should be scored in full-repo scan")

    def test_evaluate_risks_unmatched_intent_returns_empty(self):
        """Edge case 2: empty targets + non-matching intent = empty (correct)."""
        from ultron.core import analyzer
        from ultron.core import risk as risk_mod
        codebase = analyzer.analyze_directory(self.repo_path)
        risks = risk_mod.evaluate_risks(codebase, [], "zzz_nonexistent_gibberish_xyz", repo_path=self.repo_path)
        self.assertEqual(len(risks), 0, "Unmatched intent should return empty risks")

    def test_evaluate_risks_explicit_target_respected(self):
        """Edge case 3: explicit target + empty intent = only that target."""
        from ultron.core import analyzer
        from ultron.core import risk as risk_mod
        codebase = analyzer.analyze_directory(self.repo_path)
        first_file = list(codebase.keys())[0]
        risks = risk_mod.evaluate_risks(codebase, [first_file], "", repo_path=self.repo_path)
        self.assertEqual(len(risks), 1)
        self.assertEqual(risks[0].file_path, first_file)

    def test_evaluate_risks_explicit_target_with_intent(self):
        """Edge case 4: explicit target + intent = only that target (intent ignored)."""
        from ultron.core import analyzer
        from ultron.core import risk as risk_mod
        codebase = analyzer.analyze_directory(self.repo_path)
        first_file = list(codebase.keys())[0]
        risks = risk_mod.evaluate_risks(codebase, [first_file], "some_intent", repo_path=self.repo_path)
        self.assertEqual(len(risks), 1)
        self.assertEqual(risks[0].file_path, first_file)

if __name__ == "__main__":
    unittest.main()
