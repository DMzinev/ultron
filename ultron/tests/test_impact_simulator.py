"""
ultron.tests.test_impact_simulator
Hermetic automated unit tests for Task P4-C2: Differential Impact Simulator.
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest

from ultron.interfaces.cli.commands.impact import (
    run_impact_command,
    _discover_test_files,
    _is_test_file,
    _extract_ast_imports,
    _map_affected_files_to_tests,
    _detect_test_runner,
    _synthesize_test_command
)


class TestImpactSimulator(unittest.TestCase):
    """Hermetic unit tests for ultron.interfaces.cli.commands.impact."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="ultron_impact_test_")
        # Build synthetic repository layout:
        # src/
        #   utils.py        (leaf utility)
        #   service.py      (imports utils)
        #   app.py          (imports service)
        #   orphan.py       (untested module)
        # tests/
        #   test_utils.py   (imports utils)
        #   test_service.py (imports service)
        #   test_app.py     (imports app)
        # fixtures/
        #   fixture_repo/
        #     test_dummy.py (non-test fixture data)

        self.src_dir = os.path.join(self.tmp_dir, "src")
        self.test_dir = os.path.join(self.tmp_dir, "tests")
        self.fixture_dir = os.path.join(self.tmp_dir, "fixtures", "fixture_repo")

        os.makedirs(self.src_dir, exist_ok=True)
        os.makedirs(self.test_dir, exist_ok=True)
        os.makedirs(self.fixture_dir, exist_ok=True)

        with open(os.path.join(self.src_dir, "__init__.py"), "w", encoding="utf-8") as f:
            f.write("")

        with open(os.path.join(self.src_dir, "utils.py"), "w", encoding="utf-8") as f:
            f.write("def add(a, b): return a + b\n")

        with open(os.path.join(self.src_dir, "service.py"), "w", encoding="utf-8") as f:
            f.write("from src.utils import add\ndef compute(x): return add(x, 10)\n")

        with open(os.path.join(self.src_dir, "app.py"), "w", encoding="utf-8") as f:
            f.write("from src.service import compute\ndef main(): return compute(5)\n")

        with open(os.path.join(self.src_dir, "orphan.py"), "w", encoding="utf-8") as f:
            f.write("def isolated(): return 42\n")

        with open(os.path.join(self.test_dir, "test_utils.py"), "w", encoding="utf-8") as f:
            f.write("import unittest\nfrom src.utils import add\nclass TestUtils(unittest.TestCase):\n    def test_add(self): self.assertEqual(add(1, 2), 3)\n")

        with open(os.path.join(self.test_dir, "test_service.py"), "w", encoding="utf-8") as f:
            f.write("import unittest\nfrom src.service import compute\nclass TestService(unittest.TestCase):\n    def test_compute(self): self.assertEqual(compute(1), 11)\n")

        with open(os.path.join(self.test_dir, "test_app.py"), "w", encoding="utf-8") as f:
            f.write("import unittest\nfrom src.app import main\nclass TestApp(unittest.TestCase):\n    def test_main(self): self.assertEqual(main(), 15)\n")

        # Non-test fixture file that should be pruned
        with open(os.path.join(self.fixture_dir, "test_fixture_data.py"), "w", encoding="utf-8") as f:
            f.write("# Fixture mock data file\nx = 1\n")

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _run_impact(self, target_file, **kwargs):
        """Helper to run impact command and capture stdout/stderr."""
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            exit_code = run_impact_command(
                target_file=target_file,
                repo_path=self.tmp_dir,
                **kwargs
            )
            out = sys.stdout.getvalue()
            err = sys.stderr.getvalue()
            return exit_code, out, err
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def test_fixture_pruning_and_discovery(self):
        """Verify _discover_test_files ignores fixture directories."""
        discovered = _discover_test_files(self.tmp_dir)
        self.assertIn("tests/test_utils.py", discovered)
        self.assertIn("tests/test_service.py", discovered)
        self.assertIn("tests/test_app.py", discovered)
        for d in discovered:
            self.assertNotIn("fixtures", d)
            self.assertNotIn("test_fixture_data.py", d)

    def test_is_test_file_classifier(self):
        """Verify _is_test_file correctly classifies files and rejects fixtures."""
        self.assertTrue(_is_test_file("tests/test_core.py"))
        self.assertTrue(_is_test_file("pkg/tests/test_router.py"))
        self.assertTrue(_is_test_file("test_root.py"))
        self.assertTrue(_is_test_file("tests/engine_test.py"))
        self.assertFalse(_is_test_file("fixtures/repo/test_mock.py"))
        self.assertFalse(_is_test_file("ultron/core/test_runner_service.py"))
        self.assertFalse(_is_test_file("src/utils.py"))

    def test_impact_on_leaf_module(self):
        """Verify impact on a top-level module (app.py) with 0 callers returns LOW severity."""
        code, out, err = self._run_impact("src/app.py", json_output=True)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["target_file"], "src/app.py")
        self.assertEqual(data["direct_callers"], [])
        self.assertEqual(data["transitive_callers"], [])
        self.assertEqual(data["affected_files"], ["src/app.py"])
        self.assertIn("tests/test_app.py", data["affected_tests"])
        self.assertEqual(data["severity"], "LOW")
        self.assertIn("python -m unittest tests/test_app.py", data["recommended_test_command"])

    def test_impact_on_transitive_root_utility(self):
        """Verify modifying utils.py cascades to service.py and app.py."""
        code, out, err = self._run_impact("src/utils.py", json_output=True)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["target_file"], "src/utils.py")
        self.assertIn("src/service.py", data["direct_callers"])
        self.assertIn("src/app.py", data["transitive_callers"])
        self.assertIn("src/utils.py", data["affected_files"])
        self.assertIn("src/service.py", data["affected_files"])
        self.assertIn("src/app.py", data["affected_files"])

        # Test mapping should reach all 3 tests
        self.assertIn("tests/test_utils.py", data["affected_tests"])
        self.assertIn("tests/test_service.py", data["affected_tests"])
        self.assertIn("tests/test_app.py", data["affected_tests"])

    def test_impact_target_is_test_file(self):
        """Condition 2: Target inside tests/ defaults to 0 callers, blast_score 0.0, and self-mapped."""
        code, out, err = self._run_impact("tests/test_utils.py", json_output=True)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["target_file"], "tests/test_utils.py")
        self.assertEqual(data["direct_callers"], [])
        self.assertEqual(data["transitive_callers"], [])
        self.assertEqual(data["affected_files"], ["tests/test_utils.py"])
        self.assertEqual(data["affected_tests"], ["tests/test_utils.py"])
        self.assertEqual(data["blast_score"], 0.0)
        self.assertEqual(data["severity"], "LOW")
        self.assertEqual(data["recommended_test_command"], "python -m unittest tests/test_utils.py")

    def test_impact_max_depth_bounding(self):
        """Verify max_depth limits transitive caller traversal."""
        # max_depth=1 should only include direct callers (service.py), not app.py
        code, out, err = self._run_impact("src/utils.py", max_depth=1, json_output=True)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("src/service.py", data["direct_callers"])
        self.assertEqual(data["transitive_callers"], [])
        self.assertNotIn("src/app.py", data["affected_files"])
        self.assertNotIn("tests/test_app.py", data["affected_tests"])

    def test_impact_untested_module_fallback(self):
        """Verify unmapped module reports empty tests and emits fallback discovery command."""
        code, out, err = self._run_impact("src/orphan.py", json_output=True)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["affected_tests"], [])
        self.assertEqual(data["recommended_test_command"], "python -m unittest discover")
        self.assertIn("No mapped test files found", data["explanation"])

    def test_impact_nonexistent_file_error(self):
        """Verify nonexistent file returns exit code 1 with structured error."""
        code, out, err = self._run_impact("src/nonexistent.py", json_output=True)
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual(data["status"], "error")
        self.assertIn("does not exist", data["error"])

    def test_impact_null_byte_security(self):
        """Verify null-byte injection returns exit code 1."""
        code, out, err = self._run_impact("src/utils.py\0injection", json_output=True)
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual(data["status"], "error")
        self.assertIn("null-byte", data["error"])

    def test_impact_path_traversal_escape(self):
        """Condition 4: Traversal escapes outside repository return exit code 1."""
        code, out, err = self._run_impact("../../outside.py", json_output=True)
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual(data["status"], "error")
        self.assertIn("escape detected", data["error"])

    def test_impact_missing_target_argument(self):
        """Condition 5: Missing or blank target argument returns exit code 1."""
        code, out, err = self._run_impact("", json_output=True)
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual(data["status"], "error")
        self.assertIn("Missing required", data["error"])

    def test_impact_runner_selection_pytest(self):
        """Condition 7: Explicit runner='pytest' generates pytest syntax."""
        code, out, err = self._run_impact("src/app.py", runner="pytest", json_output=True)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["runner"], "pytest")
        self.assertTrue(data["recommended_test_command"].startswith("pytest tests/test_app.py"))

    def test_impact_runner_auto_detection_pytest(self):
        """Condition 7: Auto-detects pytest when pytest.ini is present."""
        with open(os.path.join(self.tmp_dir, "pytest.ini"), "w", encoding="utf-8") as f:
            f.write("[pytest]\n")
        self.assertEqual(_detect_test_runner(self.tmp_dir), "pytest")

        code, out, err = self._run_impact("src/app.py", runner="auto", json_output=True)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["runner"], "pytest")

    def test_syntax_error_resilience_in_test_files(self):
        """Condition 3: Broken test files with syntax errors do not crash AST parsing."""
        broken_test = os.path.join(self.test_dir, "test_broken.py")
        with open(broken_test, "w", encoding="utf-8") as f:
            f.write("def broken syntax (: this is invalid python :::")
        imports = _extract_ast_imports(broken_test)
        self.assertEqual(imports, set())

        # Command still executes cleanly
        code, out, err = self._run_impact("src/utils.py", json_output=True)
        self.assertEqual(code, 0)

    def test_human_readable_hud_output(self):
        """Verify human-readable console HUD renders without crashing."""
        code, out, err = self._run_impact("src/utils.py", json_output=False)
        self.assertEqual(code, 0)
        self.assertIn("[ULTRON] DIFFERENTIAL IMPACT SIMULATOR", out)
        self.assertIn("Target File:", out)
        self.assertIn("Impact Severity:", out)
        self.assertIn("Affected Modules:", out)
        self.assertIn("Recommended Test Execution Command:", out)


if __name__ == "__main__":
    unittest.main()
