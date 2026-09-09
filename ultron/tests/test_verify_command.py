r"""
ultron/tests/test_verify_command.py

Automated unit and integration test suite for Task P2-B1 per docs/AGENT_EXECUTION_PLAN_PHASE2.md:
"Single Source-of-Truth Test Command + CI Wiring"

Asserts:
1. In-process execution of clean, failing, erroring, and skipped test suites.
2. Output format regex stability: ^TESTS:\s+(\d+)\s+ran,\s+(\d+)\s+failed,\s+(\d+)\s+errors,\s+(\d+)\s+skipped$.
3. Machine-readable pure JSON isolation with zero stdout pollution.
4. Real subprocess end-to-end execution of scripts/verify.py and ultron verify.
5. Definition of Done (DoD): Deliberately broken tests strictly exit with code 1.
"""

import os
import sys
import io
import re
import json
import shutil
import tempfile
import unittest
import subprocess
import contextlib

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ultron.interfaces.cli.commands.verify import (
    run_verify_command,
    build_verify_parser,
    main as verify_main
)


class TestVerifyCommand(unittest.TestCase):
    """Hermetic unit and subprocess test suite for the verify command."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="ultron_verify_test_")
        self.script_path = os.path.join(REPO_ROOT, "scripts", "verify.py")

    def tearDown(self):
        # Evict any modules imported from temp directories to avoid unittest loader collision
        to_del = [
            m for m, mod in list(sys.modules.items())
            if (getattr(mod, "__file__", None) and (mod.__file__.startswith(self.temp_dir) or "ultron_verify_test_" in mod.__file__))
            or m.startswith("test_sample")
        ]
        for m in to_del:
            sys.modules.pop(m, None)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_synthetic_test(self, content: str, filename: str = "test_sample.py") -> str:
        """Helper to create a synthetic test file in a temp directory."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def test_verify_clean_suite_in_process(self):
        """Clean passing test suite must exit 0 and report 0 failed, 0 errors, 0 skipped."""
        self._create_synthetic_test("""
import unittest
class SamplePassTest(unittest.TestCase):
    def test_pass(self):
        self.assertTrue(True)
""", filename="test_sample_clean.py")
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run_verify_command(
                repo_path=self.temp_dir,
                test_dir=".",
                pattern="test_*.py"
            )
        self.assertEqual(code, 0)
        stdout_val = out.getvalue().strip()
        self.assertIn("TESTS: 1 ran, 0 failed, 0 errors, 0 skipped", stdout_val)

    def test_verify_failing_suite_in_process(self):
        """Failing test suite must exit 1 and report 1 failed."""
        self._create_synthetic_test("""
import unittest
class SampleFailTest(unittest.TestCase):
    def test_fail(self):
        self.fail("Deliberate synthetic failure")
""", filename="test_sample_fail.py")
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run_verify_command(
                repo_path=self.temp_dir,
                test_dir=".",
                pattern="test_*.py"
            )
        self.assertEqual(code, 1)
        stdout_val = out.getvalue().strip()
        self.assertIn("TESTS: 1 ran, 1 failed, 0 errors, 0 skipped", stdout_val)

    def test_verify_erroring_suite_in_process(self):
        """Erroring test suite must exit 1 and report 1 error."""
        self._create_synthetic_test("""
import unittest
class SampleErrorTest(unittest.TestCase):
    def test_error(self):
        raise RuntimeError("Deliberate synthetic crash")
""", filename="test_sample_err.py")
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run_verify_command(
                repo_path=self.temp_dir,
                test_dir=".",
                pattern="test_*.py"
            )
        self.assertEqual(code, 1)
        stdout_val = out.getvalue().strip()
        self.assertIn("TESTS: 1 ran, 0 failed, 1 errors, 0 skipped", stdout_val)

    def test_verify_skipped_suite_in_process(self):
        """Skipped test suite must exit 0 and report 1 skipped."""
        self._create_synthetic_test("""
import unittest
class SampleSkipTest(unittest.TestCase):
    def test_skip(self):
        self.skipTest("Deliberate synthetic skip")
""", filename="test_sample_skip.py")
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run_verify_command(
                repo_path=self.temp_dir,
                test_dir=".",
                pattern="test_*.py"
            )
        self.assertEqual(code, 0)
        stdout_val = out.getvalue().strip()
        self.assertIn("TESTS: 1 ran, 0 failed, 0 errors, 1 skipped", stdout_val)

    def test_verify_json_output_clean(self):
        """When --json is specified, stdout must contain pure valid JSON exclusively."""
        self._create_synthetic_test("""
import unittest
class SamplePassTest(unittest.TestCase):
    def test_pass(self):
        print("Spurious print that should be silenced")
        self.assertTrue(True)
""", filename="test_sample_json.py")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = run_verify_command(
                repo_path=self.temp_dir,
                test_dir=".",
                pattern="test_*.py",
                json_output=True
            )
        self.assertEqual(code, 0)
        stdout_val = out.getvalue().strip()
        # Must parse as clean JSON
        try:
            data = json.loads(stdout_val)
        except json.JSONDecodeError as e:
            self.fail(f"JSON stdout contaminated: {e}; raw: {stdout_val!r}")

        self.assertEqual(data["status"], "PASSED")
        self.assertTrue(data["passed"])
        self.assertEqual(data["exit_code"], 0)
        self.assertEqual(data["ran"], 1)
        self.assertEqual(data["failed"], 0)
        self.assertEqual(data["errors"], 0)
        self.assertEqual(data["skipped"], 0)
        self.assertIn("duration", data)

    def test_verify_regex_stability(self):
        """Summary line format must strictly match the standardized regex."""
        self._create_synthetic_test("""
import unittest
class SampleMultiTest(unittest.TestCase):
    def test_p(self): self.assertTrue(True)
    def test_s(self): self.skipTest("skip")
""", filename="test_sample_multi.py")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            run_verify_command(repo_path=self.temp_dir, test_dir=".")
        
        stdout_val = out.getvalue().strip()
        pattern = r"^TESTS:\s+(\d+)\s+ran,\s+(\d+)\s+failed,\s+(\d+)\s+errors,\s+(\d+)\s+skipped$"
        match = re.search(pattern, stdout_val, re.MULTILINE)
        self.assertIsNotNone(match, f"Summary line failed to match regex: {stdout_val!r}")
        ran, failed, errors, skipped = match.groups()
        self.assertEqual(ran, "2")
        self.assertEqual(failed, "0")
        self.assertEqual(errors, "0")
        self.assertEqual(skipped, "1")

    def test_scripts_verify_subprocess_clean(self):
        """Subprocess execution of scripts/verify.py on clean suite yields exit code 0."""
        self._create_synthetic_test("""
import unittest
class SubprocessCleanTest(unittest.TestCase):
    def test_ok(self): self.assertEqual(1 + 1, 2)
""")
        res = subprocess.run(
            [sys.executable, self.script_path, "--repo", self.temp_dir, "--test-dir", "."],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        self.assertEqual(res.returncode, 0, f"Expected 0, got {res.returncode}. Stderr: {res.stderr}")
        self.assertIn("TESTS: 1 ran, 0 failed, 0 errors, 0 skipped", res.stdout)

    def test_scripts_verify_subprocess_failure_dod(self):
        """
        Definition of Done (DoD):
        A deliberately-broken test strictly proves the verification gate fails the build (exit code 1).
        """
        self._create_synthetic_test("""
import unittest
class SubprocessBrokenTest(unittest.TestCase):
    def test_broken(self): self.assertEqual("red", "green")
""")
        res = subprocess.run(
            [sys.executable, self.script_path, "--repo", self.temp_dir, "--test-dir", "."],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        self.assertEqual(res.returncode, 1, f"Expected exit code 1 on broken test, got {res.returncode}")
        self.assertIn("TESTS: 1 ran, 1 failed, 0 errors, 0 skipped", res.stdout)
        self.assertIn("AssertionError", res.stderr)

    def test_cli_subcommand_dispatch_help(self):
        """CLI arguments for scripts/verify.py and ultron verify display cleanly."""
        res_script = subprocess.run(
            [sys.executable, self.script_path, "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(res_script.returncode, 0)
        self.assertIn("--pattern", res_script.stdout)
        self.assertIn("--test-dir", res_script.stdout)
        self.assertIn("--json", res_script.stdout)

        res_ultron = subprocess.run(
            [sys.executable, "-m", "ultron.interfaces.ultron", "verify", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(res_ultron.returncode, 0)
        self.assertIn("--pattern", res_ultron.stdout)
        self.assertIn("--json", res_ultron.stdout)


if __name__ == "__main__":
    unittest.main()
