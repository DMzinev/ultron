"""
test_adversarial_ugly_repo.py - Adversarial Test Suite for Ugly / Real-World Repositories (v2.7.0)

Asserts that Ultron handles deliberately ugly, broken, and messy repositories without crashing:
1. Syntax errors in source files
2. Unicode file names (e.g. üñîçødé_tëst.py)
3. Deep nested directory hierarchies
4. Zero-byte empty files
5. Large multi-function files
6. Broken external imports
7. Circular import dependencies
8. Non-git folders (missing .git directory)
"""

import io
import os
import shutil
import tempfile
import unittest

from ultron.core.pipeline.orchestrator import analyze_repository
from ultron.core.safety_evaluator import SafetyEvaluator
from ultron.core.agent_context_builder import AgentContextBuilder
from ultron.core.objective_tracker import ObjectiveTracker
from ultron.interfaces.server import UltronAPIHandler


class TestAdversarialUglyRepository(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="ultron_ugly_repo_")
        self.repo_dir = os.path.join(self.tmp_dir, "ugly_project")
        os.makedirs(self.repo_dir, exist_ok=True)

        # 1. File with Syntax Error
        with open(os.path.join(self.repo_dir, "syntax_error.py"), "w", encoding="utf-8") as f:
            f.write("def broken_syntax(:\n    print('broken')\n")

        # 2. File with Unicode filename
        with open(os.path.join(self.repo_dir, "üñîçødé_tëst.py"), "w", encoding="utf-8") as f:
            f.write("def unicode_symbol_fn():\n    return '✓ üñîçødé'\n")

        # 3. Deep nested path
        deep_dir = os.path.join(self.repo_dir, "a", "b", "c", "d", "e")
        os.makedirs(deep_dir, exist_ok=True)
        with open(os.path.join(deep_dir, "deep_module.py"), "w", encoding="utf-8") as f:
            f.write("def deep_nested_fn():\n    return 42\n")

        # 4. Zero-byte empty file
        with open(os.path.join(self.repo_dir, "empty.py"), "w", encoding="utf-8") as f:
            f.write("")

        # 5. Large file (500 functions)
        with open(os.path.join(self.repo_dir, "large_file.py"), "w", encoding="utf-8") as f:
            lines = ["# Large file fixture with 500 functions\n"]
            for i in range(500):
                lines.append(f"def generated_function_{i}():\n    return {i} * 2\n\n")
            f.writelines(lines)

        # 6. Broken external imports
        with open(os.path.join(self.repo_dir, "broken_imports.py"), "w", encoding="utf-8") as f:
            f.write("import non_existent_package_xyz_999\nfrom fake_module_123 import fake_function\n\ndef caller():\n    pass\n")

        # 7. Circular imports (A -> B -> A)
        with open(os.path.join(self.repo_dir, "cycle_a.py"), "w", encoding="utf-8") as f:
            f.write("import cycle_b\n\ndef fn_a():\n    return cycle_b.fn_b()\n")

        with open(os.path.join(self.repo_dir, "cycle_b.py"), "w", encoding="utf-8") as f:
            f.write("import cycle_a\n\ndef fn_b():\n    return cycle_a.fn_a()\n")

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_ugly_repo_analysis_resilience(self):
        """Verify pipeline execution on ugly repo returns structured results without throwing exceptions."""
        bundle = analyze_repository(self.repo_dir, force=True)

        # Result must be valid bundle containing facts and risks
        self.assertIsNotNone(bundle)
        self.assertTrue(len(bundle.files) > 0)
        self.assertIsInstance(bundle.codebase, dict)
        self.assertIsInstance(bundle.risks, list)

        # Verify unicode file is captured
        has_unicode = any("üñîçødé" in str(f) for f in bundle.files)
        self.assertTrue(has_unicode, f"Expected unicode file to be present in files: {bundle.files}")

        # Verify deep path is captured
        has_deep = any("deep_module" in str(f) for f in bundle.files)
        self.assertTrue(has_deep, f"Expected deep module in files: {bundle.files}")

        # Verify large file (500 functions) captured
        large_files = [f for f in bundle.files if "large_file" in str(f)]
        self.assertGreaterEqual(len(large_files), 1, "Large file should exist in discovered files")

    def test_ugly_repo_unified_payload_projection(self):
        """Verify unified analysis payload builds cleanly for an ugly repository."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.wfile = io.BytesIO()
        handler.headers = {}
        payload = handler._build_analysis_payload(self.repo_dir, force=True)

        self.assertIsInstance(payload, dict)
        self.assertIn("snapshot_id", payload)
        self.assertIn("model_hash", payload)
        self.assertIn("identity", payload)
        self.assertIn("dependency_graph", payload)
        self.assertIn("risks", payload)
        self.assertIn("stats", payload)

        # Verify stats are accurate and non-zero
        stats = payload["stats"]
        self.assertGreater(stats.get("total_files", 0), 0)
        self.assertGreater(stats.get("total_definitions", 0), 0)

        # Verify risk matrix contains items without NaN values
        risks = payload["risks"]
        self.assertIsInstance(risks, list)
        for r in risks:
            self.assertFalse(isinstance(r.get("impact_score"), float) and str(r.get("impact_score")) == "nan")
            self.assertFalse(isinstance(r.get("complexity"), float) and str(r.get("complexity")) == "nan")

    def test_ugly_repo_safety_and_agent_context(self):
        """Verify SafetyEvaluator and AgentContextBuilder function on ugly repo without crashing."""
        tracker = ObjectiveTracker(self.repo_dir)
        tracker.set_objective(
            title="Clean Ugly Repo",
            description="Refactor circular dependencies and fix syntax errors.",
            tasks=[{"id": "t1", "title": "Decouple cycle_a and cycle_b", "status": "in_progress"}]
        )

        builder = AgentContextBuilder()
        ctx = builder.build(
            objective_state=tracker.get_objective(),
            repo_path=self.repo_dir
        )

        # Context generation must succeed and render valid markdown
        self.assertIsInstance(ctx.active_task, dict)
        md_text = builder.render_markdown(ctx)
        self.assertIn("Clean Ugly Repo", md_text)
        self.assertIn("Decouple cycle_a and cycle_b", md_text)

        # Safety evaluator must evaluate cleanly
        report = SafetyEvaluator.evaluate(modified_files=["syntax_error.py", "empty.py"])
        self.assertIn(report.badge, ["CONTINUE BUILDING", "PAUSE & REVIEW"])


if __name__ == "__main__":
    unittest.main()
