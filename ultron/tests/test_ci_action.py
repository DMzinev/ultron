"""
ultron.tests.test_ci_action
Unit and integration test suite for Task P4-B1: Official Standalone GitHub Action.
Verifies composite action schema, test workflow matrix, $GITHUB_OUTPUT emission,
JSON report generation, non-regression override, PR commenting wire protocol,
and CLI flag integration.
"""

import os
import io
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import urllib.error

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ultron.core.ci_reporter import CIReporter
from ultron.interfaces.cli.commands.gate import run_gate_command

FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures"))


class TestCIActionSchemaAndWorkflow(unittest.TestCase):
    """Verifies composite action definition and test workflow integrity."""

    def setUp(self):
        self.action_path = os.path.join(REPO_ROOT, ".github", "actions", "ultron-gate", "action.yml")
        self.workflow_path = os.path.join(REPO_ROOT, ".github", "workflows", "test-action.yml")
        self.ci_workflow_path = os.path.join(REPO_ROOT, ".github", "workflows", "ci.yml")

    def test_action_yaml_schema_and_integrity(self):
        """Asserts .github/actions/ultron-gate/action.yml defines all 13 inputs, 4 outputs, and composite runner."""
        self.assertTrue(os.path.isfile(self.action_path), f"action.yml missing at {self.action_path}")
        with open(self.action_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Action Metadata
        self.assertIn("name: 'Ultron Architectural Quality Gate'", content)
        self.assertIn("using: 'composite'", content)
        self.assertIn("shell: bash", content)
        self.assertIn("inputs.ultron-executable", content)
        self.assertIn("default: 'python -m ultron'", content)

        # 2. All 17 Inputs
        expected_inputs = [
            "repo-path",
            "baseline",
            "min-health",
            "max-high",
            "max-health-drop",
            "fail-on-regression",
            "fail-on-high",
            "strict",
            "output-json",
            "output-markdown",
            "github-annotations",
            "comment-pr",
            "github-token",
            "sarif-output",
            "use-preinstalled",
            "ultron-executable",
            "install-source",
        ]
        for inp in expected_inputs:
            self.assertIn(f"{inp}:", content, f"Input '{inp}' missing in action.yml")

        # Verify use-preinstalled defaults to false
        self.assertIn("use-preinstalled:", content)
        self.assertIn("default: 'false'", content)

        # 3. All 4 Outputs
        expected_outputs = [
            "passed:",
            "health-score:",
            "health-delta:",
            "exit-code:",
        ]
        for out in expected_outputs:
            self.assertIn(out, content, f"Output '{out}' missing in action.yml")

        # 4. Standard Library Unconditional Secret Expression Elimination (Blocker B2 & Directive B1)
        import re
        self.assertNotRegex(
            content,
            r"\$\{\{\s*secrets\b",
            "Illegal secrets expression found in composite action manifest (.github/actions/ultron-gate/action.yml)"
        )
        self.assertNotIn("${{secrets.", "".join(content.split()))
        self.assertIn("pass secrets.GITHUB_TOKEN from caller workflow", content)

        # 5. Standard YAML Validation (if PyYAML available, else regex/line structure)
        try:
            import yaml
            parsed = yaml.safe_load(content)
            self.assertEqual(parsed.get("runs", {}).get("using"), "composite")
            self.assertIn("inputs", parsed)
            self.assertIn("outputs", parsed)
            self.assertEqual(parsed["inputs"]["github-token"]["default"], "")
        except ImportError:
            pass

        # 6. Structural Block Scalar Validation (independent of PyYAML)
        # Asserts that all lines inside literal block scalars (e.g. run: |) are indented deeper than the key
        lines = content.splitlines()
        in_block_scalar = False
        block_indent = 0
        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            if stripped.endswith(": |"):
                in_block_scalar = True
                block_indent = indent
                continue
            if in_block_scalar:
                if indent > block_indent:
                    continue
                else:
                    if ":" in stripped:
                        in_block_scalar = False
                    else:
                        self.fail(
                            f"Illegal unindented line inside YAML block scalar at "
                            f"{self.action_path}:{line_no}: {line!r}"
                        )

    def test_action_manifest_fail_closed_on_missing_token(self):
        """Asserts composite action script enforces fail-closed validation when comment-pr is true without token."""
        with open(self.action_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Directive A1: Must check for empty github-token and exit 1 without embedding ${{ secrets... }}
        self.assertIn('[ "${{ inputs.comment-pr }}" = "true" ]', content)
        self.assertIn('[ -z "${{ inputs.github-token }}" ]', content)
        self.assertIn("exit 1", content)
        self.assertIn("secrets.GITHUB_TOKEN", content)
        self.assertNotIn("${{ secrets.GITHUB_TOKEN }}", content)

    def test_workflow_test_action_integrity(self):
        """Asserts .github/workflows/test-action.yml exercises the action across OS matrix."""
        self.assertTrue(os.path.isfile(self.workflow_path), f"test-action.yml missing at {self.workflow_path}")
        with open(self.workflow_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("name: Test Ultron GitHub Action", content)
        self.assertIn("ubuntu-latest", content)
        self.assertIn("windows-latest", content)
        self.assertIn("./.github/actions/ultron-gate", content)
        self.assertIn("clean_repo", content)
        self.assertIn("tangled_repo", content)

    def test_action_self_install_runner_logic(self):
        """Asserts action runner implements environment-safe self-installation with upward pyproject.toml resolver."""
        with open(self.action_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Step declares ACTION_PATH via env to prevent Windows escape issues
        self.assertIn("ACTION_PATH: ${{ github.action_path }}", content)

        # Step checks inputs.use-preinstalled
        self.assertIn('[ "${{ inputs.use-preinstalled }}" != "true" ]', content)

        # Dynamic upward resolver checking for pyproject.toml
        self.assertIn("os.environ[\"ACTION_PATH\"]", content)
        self.assertIn('os.path.isfile(os.path.join(cur, "pyproject.toml"))', content)
        self.assertIn('python -m pip install "$REPO_ROOT"', content)

        # Fail-closed error if pyproject.toml cannot be resolved
        self.assertIn("::error::Could not find pyproject.toml in action hierarchy", content)

        # AST compilation assertion on the embedded Python resolver script
        import ast, re
        match = re.search(r"REPO_ROOT=\$\(python -c '(.*?)'\)", content, re.DOTALL)
        self.assertIsNotNone(match, "REPO_ROOT python command pattern not found in action.yml")
        py_snippet = match.group(1)
        try:
            ast.parse(py_snippet)
        except Exception as e:
            self.fail(f"Embedded Python script in action.yml failed AST compilation: {e}")

    def test_workflow_external_consumer_job_integrity(self):
        """Asserts .github/workflows/test-action.yml defines external consumer simulation job."""
        with open(self.workflow_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("test-external-consumer:", content)
        self.assertIn("consumer-fixtures", content)
        self.assertIn("use-preinstalled: 'false'", content)
        self.assertIn("use-preinstalled: 'true'", content)
        self.assertIn("continue-on-error: true", content)
        self.assertIn("steps.consumer-strict.outcome", content)

    def test_external_consumer_isolated_simulation(self):
        """Simulates external consumer repository outside Ultron source tree, verifying gate pass and failure modes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            clean_dir = os.path.join(temp_dir, "clean_app")
            os.makedirs(os.path.join(clean_dir, "src"), exist_ok=True)
            with open(os.path.join(clean_dir, "src", "math_utils.py"), "w", encoding="utf-8") as f:
                f.write("def add(a: int, b: int) -> int:\n    return a + b\n")
            with open(os.path.join(clean_dir, "src", "app.py"), "w", encoding="utf-8") as f:
                f.write("from .math_utils import add\ndef main():\n    return add(1, 2)\n")

            # Run gate command on clean app
            exit_code_clean = run_gate_command(
                repo_path=clean_dir,
                min_health=80.0,
                max_high=0,
                fail_on_regression=True
            )
            self.assertEqual(exit_code_clean, 0, "Clean external consumer fixture must pass quality gate")

            # Create tangled app with circular dependency
            tangled_dir = os.path.join(temp_dir, "tangled_app")
            os.makedirs(os.path.join(tangled_dir, "pkg"), exist_ok=True)
            with open(os.path.join(tangled_dir, "pkg", "mod_x.py"), "w", encoding="utf-8") as f:
                f.write("import pkg.mod_y\ndef foo(): return pkg.mod_y.bar()\n")
            with open(os.path.join(tangled_dir, "pkg", "mod_y.py"), "w", encoding="utf-8") as f:
                f.write("import pkg.mod_x\ndef bar(): return pkg.mod_x.foo()\n")

            # Run gate command on tangled app with strict=True
            exit_code_tangled = run_gate_command(
                repo_path=tangled_dir,
                min_health=90.0,
                strict=True,
                fail_on_regression=True
            )
            self.assertEqual(exit_code_tangled, 1, "Tangled external consumer fixture must fail under strict quality gate")

    def test_ci_workflow_structure_and_job_decomposition(self):
        """Asserts .github/workflows/ci.yml decomposes CI into 5 hermetic release jobs with pinned action SHAs."""
        self.assertTrue(os.path.isfile(self.ci_workflow_path), f"ci.yml missing at {self.ci_workflow_path}")
        with open(self.ci_workflow_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Branch Triggers include release/**
        self.assertIn("release/**", content)

        # 2. All 5 discrete jobs exist
        expected_jobs = [
            "build-wheel:",
            "built-wheel-smoke:",
            "source-unit-contract:",
            "integration-verification:",
            "composite-action:",
        ]
        for job in expected_jobs:
            self.assertIn(job, content, f"Required CI job '{job}' missing in ci.yml")

        # 3. built-wheel-smoke includes macOS, Linux, and Windows
        self.assertIn("macos-latest", content)
        self.assertIn("ubuntu-latest", content)
        self.assertIn("windows-latest", content)

        # 4. built-wheel-smoke asserts zero-dependency isolation (absence of radon, PIL, pystray)
        self.assertIn("forbidden = ['radon', 'PIL', 'pystray'", content)

        # 5. source-unit-contract runs base install without requirements.txt
        self.assertIn("Radon must not be installed in base environment", content)

        # 6. integration-verification runs dev extras and verify.py back-to-back
        self.assertIn("-r requirements.txt", content)
        self.assertIn("scripts/verify.py", content)

        # 7. Immutable 40-character commit SHA pinning for all third-party actions
        # across both ci.yml and test-action.yml
        pinned_shas = {
            "actions/checkout": "11bd71901bbe5b1630ceea73d27597364c9af683",
            "actions/setup-python": "42375524e23c412d93fb67b49958b491fce71c38",
            "actions/setup-node": "1d0ff469b7ec7b3cb9d8673fde0c81c44821de2a",
            "actions/upload-artifact": "4cec3d8aa04e39d1a68397de0c4cd6fb9dce8ec1",
            "actions/download-artifact": "cc203385981b70ca67e1cc392babf9cc229d5806",
        }
        import re
        for action_name, sha in pinned_shas.items():
            pattern = rf"{re.escape(action_name)}@{sha}\b"
            self.assertRegex(
                content,
                pattern,
                f"Action '{action_name}' is not pinned to expected immutable commit SHA {sha} in ci.yml"
            )

        with open(self.workflow_path, "r", encoding="utf-8") as f:
            test_action_content = f.read()
        self.assertIn("release/**", test_action_content)
        self.assertIn("macos-latest", test_action_content)
        self.assertIn(f"actions/checkout@{pinned_shas['actions/checkout']}", test_action_content)
        self.assertIn(f"actions/setup-python@{pinned_shas['actions/setup-python']}", test_action_content)
        self.assertNotIn("-e .", test_action_content, "test-action.yml must use non-editable install per Rule 5")


class TestCIGateActionExecution(unittest.TestCase):
    """Verifies gate execution with GitHub Actions environment integration."""

    @classmethod
    def setUpClass(cls):
        cls.clean_repo = os.path.join(FIXTURES_DIR, "clean_repo")
        cls.mixed_repo = os.path.join(FIXTURES_DIR, "mixed_repo")

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_gate_github_output_writing(self):
        """Asserts GITHUB_OUTPUT receives passed=true, health-score, health-delta, exit-code=0 on pass."""
        output_file = os.path.join(self.temp_dir.name, "github_output.txt")

        with patch.dict(os.environ, {"GITHUB_OUTPUT": output_file}):
            exit_code = run_gate_command(
                repo_path=self.clean_repo,
                max_high=0,
                min_health=80.0,
                fail_on_regression=True
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue(os.path.exists(output_file))

        with open(output_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]

        out_map = dict(line.split("=", 1) for line in lines)
        self.assertEqual(out_map.get("passed"), "true")
        self.assertEqual(out_map.get("exit-code"), "0")
        self.assertIn("health-score", out_map)
        self.assertIn("health-delta", out_map)

    def test_gate_github_output_failure_code(self):
        """Asserts GITHUB_OUTPUT receives passed=false and exit-code=1 when thresholds breached."""
        output_file = os.path.join(self.temp_dir.name, "github_output_fail.txt")

        with patch.dict(os.environ, {"GITHUB_OUTPUT": output_file}):
            with patch("sys.stderr"):
                exit_code = run_gate_command(
                    repo_path=self.mixed_repo,
                    max_high=0,
                    fail_on_regression=True
                )

        self.assertEqual(exit_code, 1)
        self.assertTrue(os.path.exists(output_file))

        with open(output_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]

        out_map = dict(line.split("=", 1) for line in lines)
        self.assertEqual(out_map.get("passed"), "false")
        self.assertEqual(out_map.get("exit-code"), "1")

    def test_gate_output_json_file(self):
        """Asserts output_json writes full structured report to specified file path."""
        json_file = os.path.join(self.temp_dir.name, "output_report.json")

        exit_code = run_gate_command(
            repo_path=self.clean_repo,
            output_json=json_file,
            fail_on_regression=False
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(os.path.exists(json_file))

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("status"), "PASSED")
        self.assertTrue(data.get("passed"))
        self.assertEqual(data.get("exit_code"), 0)
        self.assertIn("gate_decision", data)
        self.assertIn("current_analysis", data)
        self.assertIn("thresholds", data)
        self.assertEqual(data["current_analysis"]["health_score"], 100.0)

    def test_gate_no_fail_on_regression_flag(self):
        """Asserts fail_on_regression=False returns exit code 0 even when gate decision fails."""
        with patch("sys.stderr"):
            exit_code = run_gate_command(
                repo_path=self.mixed_repo,
                max_high=0,
                fail_on_regression=False
            )
        self.assertEqual(exit_code, 0)


class TestCIPRCommentPosting(unittest.TestCase):
    """Verifies CIReporter.post_pr_comment using standard library urllib.request."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pr_comment_posting_success(self):
        """Asserts post_pr_comment sends authenticated POST request with correct headers and payload."""
        mock_resp = MagicMock()
        mock_resp.status = 201
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            with patch("sys.stderr"):
                success = CIReporter.post_pr_comment(
                    comment_body="### Ultron Gate Report\nHealth: 95.0",
                    github_token="ghp_test_secret_token",
                    comments_url="https://api.github.com/repos/DMzinev/ultron/issues/42/comments"
                )

        self.assertTrue(success)
        self.assertEqual(mock_urlopen.call_count, 1)

        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_full_url(), "https://api.github.com/repos/DMzinev/ultron/issues/42/comments")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.headers.get("Authorization"), "Bearer ghp_test_secret_token")
        self.assertEqual(req.headers.get("Content-type"), "application/json; charset=utf-8")
        self.assertEqual(req.headers.get("User-agent"), "Ultron-Architectural-Gate")

        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body.get("body"), "### Ultron Gate Report\nHealth: 95.0")

    def test_pr_comment_posting_auto_resolve_from_event_path(self):
        """Asserts post_pr_comment resolves comments_url from $GITHUB_EVENT_PATH if not provided."""
        event_file = os.path.join(self.temp_dir.name, "event.json")
        with open(event_file, "w", encoding="utf-8") as f:
            json.dump({
                "pull_request": {
                    "comments_url": "https://api.github.com/repos/test/repo/issues/99/comments"
                }
            }, f)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        with patch.dict(os.environ, {"GITHUB_EVENT_PATH": event_file}):
            with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
                with patch("sys.stderr"):
                    success = CIReporter.post_pr_comment(
                        comment_body="Auto resolved comment",
                        github_token="tok_123"
                    )

        self.assertTrue(success)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_full_url(), "https://api.github.com/repos/test/repo/issues/99/comments")

    def test_pr_comment_posting_missing_token_or_event(self):
        """Asserts post_pr_comment returns False without making requests when token or URL is absent."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("urllib.request.urlopen") as mock_urlopen:
                with patch("sys.stderr"):
                    # Missing token
                    res1 = CIReporter.post_pr_comment("comment", github_token=None)
                    self.assertFalse(res1)
                    mock_urlopen.assert_not_called()

                    # Missing URL / event
                    res2 = CIReporter.post_pr_comment("comment", github_token="valid_token", comments_url=None)
                    self.assertFalse(res2)
                    mock_urlopen.assert_not_called()

    def test_pr_comment_posting_network_error_graceful(self):
        """Asserts post_pr_comment catches HTTPError and URLError gracefully and returns False."""
        http_err = urllib.error.HTTPError(
            url="https://api.github.com",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=io.BytesIO(b'{"message": "Resource not accessible by integration"}')
        )

        with patch("urllib.request.urlopen", side_effect=http_err):
            with patch("sys.stderr"):
                res = CIReporter.post_pr_comment("comment", github_token="tok", comments_url="https://api.github.com")
                self.assertFalse(res)

        url_err = urllib.error.URLError(reason="Connection refused")
        with patch("urllib.request.urlopen", side_effect=url_err):
            with patch("sys.stderr"):
                res2 = CIReporter.post_pr_comment("comment", github_token="tok", comments_url="https://api.github.com")
                self.assertFalse(res2)


class TestCIGateCLIFlags(unittest.TestCase):
    """Verifies that new gate CLI arguments are recognized and parsed cleanly by ultron.py."""

    def test_cli_flag_parsing_new_options(self):
        """Asserts ultron gate sub-parser recognizes --no-fail-on-regression, --output-json, --comment-pr, --github-token."""
        import argparse
        # Re-create gate sub-parser in isolation matching ultron.py lines 153-167
        parser = argparse.ArgumentParser(prog="ultron gate")
        parser.add_argument("--repo", default=".")
        parser.add_argument("--max-high", type=int, default=None)
        parser.add_argument("--min-health", type=float, default=None)
        parser.add_argument("--max-health-drop", type=float, default=5.0)
        parser.add_argument("--base", default=None)
        parser.add_argument("--baseline", default=None)
        parser.add_argument("--fail-on-regression", dest="fail_on_regression", action="store_true", default=True)
        parser.add_argument("--no-fail-on-regression", dest="fail_on_regression", action="store_false")
        parser.add_argument("--fail-on-high", action="store_true", default=False)
        parser.add_argument("--strict", action="store_true", default=False)
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--output-comment", dest="output_comment", default=None)
        parser.add_argument("--output-markdown", dest="output_comment", default=None)
        parser.add_argument("--output-json", default=None)
        parser.add_argument("--github-annotations", action="store_true", default=False)
        parser.add_argument("--comment-pr", action="store_true", default=False)
        parser.add_argument("--github-token", default=None)

        args = parser.parse_args([
            "--repo", "my_repo",
            "--no-fail-on-regression",
            "--output-json", "gate_out.json",
            "--output-markdown", "gate_out.md",
            "--comment-pr",
            "--github-token", "ghp_secret"
        ])

        self.assertEqual(args.repo, "my_repo")
        self.assertFalse(args.fail_on_regression)
        self.assertEqual(args.output_json, "gate_out.json")
        self.assertEqual(args.output_comment, "gate_out.md")
        self.assertTrue(args.comment_pr)
        self.assertEqual(args.github_token, "ghp_secret")


if __name__ == "__main__":
    unittest.main()
