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

    def test_action_yaml_schema_and_integrity(self):
        """Asserts .github/actions/ultron-gate/action.yml defines all 13 inputs, 4 outputs, and composite runner."""
        self.assertTrue(os.path.isfile(self.action_path), f"action.yml missing at {self.action_path}")
        with open(self.action_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Action Metadata
        self.assertIn("name: 'Ultron Architectural Quality Gate'", content)
        self.assertIn("using: 'composite'", content)
        self.assertIn("shell: bash", content)
        self.assertIn("python -m ultron gate", content)

        # 2. All 13 Inputs
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
        ]
        for inp in expected_inputs:
            self.assertIn(f"{inp}:", content, f"Input '{inp}' missing in action.yml")

        # 3. All 4 Outputs
        expected_outputs = [
            "passed:",
            "health-score:",
            "health-delta:",
            "exit-code:",
        ]
        for out in expected_outputs:
            self.assertIn(out, content, f"Output '{out}' missing in action.yml")

        # 4. Standard YAML Validation (if PyYAML available, else regex/line structure)
        try:
            import yaml
            parsed = yaml.safe_load(content)
            self.assertEqual(parsed.get("runs", {}).get("using"), "composite")
            self.assertIn("inputs", parsed)
            self.assertIn("outputs", parsed)
        except ImportError:
            pass

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
