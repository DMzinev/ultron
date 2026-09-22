"""
ultron/tests/test_cli_formatting.py
Hermetic unit tests for CLI ANSI formatting, color detection,
terminal dashboard rendering, and scan/gate command ergonomics.
"""

import io
import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

from ultron.interfaces.cli.formatting import (
    RESET,
    BOLD,
    RED,
    GREEN,
    YELLOW,
    CYAN,
    supports_color,
    can_encode_unicode,
    strip_ansi,
    colorize,
    format_badge,
    format_score_bar,
    format_scan_dashboard,
    format_gate_summary,
    safe_print,
)
from ultron.interfaces.cli.commands.analysis import run_scan_command
from ultron.interfaces.cli.commands.gate import run_gate_command


class TestCLIFormatting(unittest.TestCase):
    """Hermetic unit tests covering terminal formatting utilities and commands."""

    def test_supports_color_detection(self):
        """Asserts color detection respects overrides, NO_COLOR, TERM=dumb, and TTY."""
        # Force override takes absolute precedence
        self.assertTrue(supports_color(force_color=True))
        self.assertFalse(supports_color(force_color=False))

        # NO_COLOR standard (non-empty disables color)
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertFalse(supports_color())
        with patch.dict(os.environ, {"NO_COLOR": "true"}):
            self.assertFalse(supports_color())

        # Empty NO_COLOR does not disable color on TTY
        mock_tty = MagicMock()
        mock_tty.isatty.return_value = True
        with patch.dict(os.environ, {"NO_COLOR": "", "TERM": "xterm-256color"}):
            with patch("sys.platform", "linux"):
                self.assertTrue(supports_color(stream=mock_tty))

        # TERM=dumb disables color
        with patch.dict(os.environ, {"TERM": "dumb", "NO_COLOR": ""}):
            self.assertFalse(supports_color(stream=mock_tty))

        # Non-TTY stream disables color by default
        mock_nontty = MagicMock()
        mock_nontty.isatty.return_value = False
        with patch.dict(os.environ, {"NO_COLOR": "", "TERM": "xterm", "GITHUB_ACTIONS": "", "CI": ""}):
            self.assertFalse(supports_color(stream=mock_nontty))

    def test_can_encode_unicode(self):
        """Asserts encoding probe identifies UTF-8 vs ASCII/legacy charmaps."""
        utf8_stream = MagicMock()
        utf8_stream.encoding = "utf-8"
        self.assertTrue(can_encode_unicode(utf8_stream))

        ascii_stream = MagicMock()
        ascii_stream.encoding = "ascii"
        self.assertFalse(can_encode_unicode(ascii_stream))

        cp1252_stream = MagicMock()
        cp1252_stream.encoding = "cp1252"
        self.assertFalse(can_encode_unicode(cp1252_stream))

    def test_colorize_and_strip_ansi(self):
        """Asserts text styling wraps with codes and strip_ansi removes them cleanly."""
        text = "Ultron Engine"
        styled = colorize(text, BOLD, GREEN)
        self.assertIn("\033[1m", styled)
        self.assertIn("\033[32m", styled)
        self.assertIn(RESET, styled)

        plain = strip_ansi(styled)
        self.assertEqual(plain, text)

        # Disabled color returns raw text without escape codes
        disabled = colorize(text, BOLD, RED, enabled=False)
        self.assertEqual(disabled, text)
        self.assertEqual(strip_ansi(""), "")

    def test_format_badge(self):
        """Asserts badges format correctly with and without color."""
        # Uncolored
        self.assertEqual(format_badge("HIGH", "HIGH", color=False), "[HIGH]")
        self.assertEqual(format_badge("PASS", "PASS", color=False), "[PASS]")
        self.assertEqual(format_badge("CRITICAL", "CRITICAL", color=False), "[CRITICAL]")

        # Colored
        badge_crit = format_badge("CRITICAL", "CRITICAL", color=True)
        self.assertIn("\033[31m", badge_crit)
        self.assertEqual(strip_ansi(badge_crit), "[CRITICAL]")

        badge_pass = format_badge("PASS", "PASS", color=True)
        self.assertIn("\033[32m", badge_pass)
        self.assertEqual(strip_ansi(badge_pass), "[PASS]")

    def test_format_score_bar_ranges_and_descriptors(self):
        """Asserts score progress bar renders correct descriptors and clamped bounds."""
        # >= 90: Excellent
        bar_95 = format_score_bar(95.0, color=False, use_unicode=False)
        self.assertIn("95.0/100", bar_95)
        self.assertIn("(Excellent)", bar_95)
        self.assertIn("#", bar_95)

        # >= 80: Good
        bar_82 = format_score_bar(82.0, color=False, use_unicode=True)
        self.assertIn("82.0/100", bar_82)
        self.assertIn("(Good)", bar_82)
        self.assertIn("█", bar_82)

        # >= 60: Fair
        bar_65 = format_score_bar(65.0, color=False, use_unicode=False)
        self.assertIn("65.0/100", bar_65)
        self.assertIn("(Fair)", bar_65)

        # < 60: Needs Attention
        bar_40 = format_score_bar(40.0, color=False, use_unicode=False)
        self.assertIn("40.0/100", bar_40)
        self.assertIn("(Needs Attention)", bar_40)

        # Clamping
        bar_clamp_high = format_score_bar(150.0, color=False, use_unicode=False)
        self.assertIn("150.0/100", bar_clamp_high)
        bar_clamp_low = format_score_bar(-10.0, color=False, use_unicode=False)
        self.assertIn("-10.0/100", bar_clamp_low)

    def test_format_scan_dashboard_visual_alignment(self):
        """Asserts scan dashboard box-drawing renders with perfect column alignment."""
        analysis = {
            "repo": "sample_repo",
            "total_files": 42,
            "health_score": 85.5,
            "risks": [
                {"file_path": "core/engine.py", "level": "HIGH", "complexity": 18, "mitigation": "Refactor nested loop."},
                {"file_path": "api/router.py", "level": "MEDIUM", "complexity": 10, "mitigation": "Break into sub-routes."},
                {"file_path": "utils/helpers.py", "level": "LOW", "complexity": 3}
            ],
            "policy_violations": [{"rule": "NO_CIRCULAR_IMPORTS"}]
        }

        dashboard_unicode = format_scan_dashboard(analysis, color=True, use_unicode=True, width=72)
        self.assertIn("ULTRON ARCHITECTURAL INTELLIGENCE SCAN", dashboard_unicode)
        self.assertIn("sample_repo", dashboard_unicode)
        self.assertIn("core/engine.py", dashboard_unicode)
        self.assertIn("Policy Violations: 1", dashboard_unicode)

        # Invariant Directive 1: Visible line widths must be strictly identical across all box rows
        lines = dashboard_unicode.splitlines()
        widths = [len(strip_ansi(line)) for line in lines]
        self.assertTrue(len(set(widths)) == 1, f"Mismatched line widths detected in box dashboard: {set(widths)}")

        # ASCII mode
        dashboard_ascii = format_scan_dashboard(analysis, color=False, use_unicode=False, width=72)
        self.assertIn("+", dashboard_ascii)
        self.assertIn("|", dashboard_ascii)
        ascii_widths = [len(strip_ansi(line)) for line in dashboard_ascii.splitlines()]
        self.assertTrue(len(set(ascii_widths)) == 1, f"Mismatched ASCII widths: {set(ascii_widths)}")

    def test_format_scan_dashboard_clean_codebase(self):
        """Asserts scan dashboard displays clean message when zero hotspots exist."""
        clean_analysis = {
            "repo": "clean_repo",
            "total_files": 12,
            "health_score": 100.0,
            "risks": [],
            "policy_violations": []
        }
        dashboard = format_scan_dashboard(clean_analysis, color=False, use_unicode=False)
        self.assertIn("No high or medium risk hotspots detected", dashboard)
        self.assertIn("Policy Violations: 0", dashboard)

    def test_format_gate_summary_pass_and_fail(self):
        """Asserts gate summary renders passed and failed decisions with uniform widths."""
        current_analysis = {"health_score": 92.0, "total_files": 30}
        
        # Passed Gate
        pass_decision = {
            "passed": True,
            "current_health": 92.0,
            "baseline_health": 90.0,
            "health_delta": 2.0,
            "high_risk_count": 0,
            "high_violations_count": 0,
            "reasons": []
        }
        pass_summary = format_gate_summary(pass_decision, current_analysis, color=True, use_unicode=True, width=70)
        self.assertIn("PASSED", pass_summary)
        self.assertIn("+2.0 pts", pass_summary)
        pass_widths = [len(strip_ansi(l)) for l in pass_summary.splitlines()]
        self.assertEqual(len(set(pass_widths)), 1, f"Passed summary box rows must be aligned: {set(pass_widths)}")

        # Failed Gate
        fail_decision = {
            "passed": False,
            "current_health": 75.0,
            "baseline_health": 85.0,
            "health_delta": -10.0,
            "high_risk_count": 3,
            "high_violations_count": 2,
            "reasons": ["Health score dropped by 10.0 pts", "Found 3 HIGH risk files"]
        }
        fail_summary = format_gate_summary(fail_decision, current_analysis, color=True, use_unicode=True, width=70)
        self.assertIn("FAILED", fail_summary)
        self.assertIn("-10.0 pts", fail_summary)
        self.assertIn("THRESHOLD BREACHES & REGRESSIONS:", fail_summary)
        self.assertIn("Health score dropped by 10.0 pts", fail_summary)
        fail_widths = [len(strip_ansi(l)) for l in fail_summary.splitlines()]
        self.assertEqual(len(set(fail_widths)), 1, f"Failed summary box rows must be aligned: {set(fail_widths)}")

    def test_safe_print_resilience(self):
        """Asserts safe_print handles UnicodeEncodeError and prints cleanly."""
        buf = io.StringIO()
        safe_print("Simple text", file=buf)
        self.assertEqual(buf.getvalue(), "Simple text\n")

        # Test UnicodeEncodeError fallback: mock print to raise if non-ascii, verify ascii replacement works
        faulty_stream = io.StringIO()
        def fail_print_non_ascii(text, file=None):
            if any(ord(c) > 127 for c in text):
                raise UnicodeEncodeError("charmap", text, 0, 1, "character maps to <undefined>")
            faulty_stream.write(text + "\n")

        with patch("builtins.print", side_effect=fail_print_non_ascii):
            # Should safely fallback to ASCII replacement without raising
            safe_print("─│┌┐", file=faulty_stream)
            output = faulty_stream.getvalue()
            self.assertIn("????", output)

    def test_run_scan_command_json_output(self):
        """Asserts run_scan_command with json_output=True emits pure valid JSON."""
        mock_analysis = {
            "repo": "/tmp/test_repo",
            "total_files": 15,
            "health_score": 88.0,
            "risks": [{"file_path": "a.py", "level": "LOW", "complexity": 2}],
            "policy_violations": []
        }

        with patch("ultron.interfaces.cli.commands.analysis.extract_current_analysis", return_value=mock_analysis):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                code = run_scan_command(repo_path="/tmp/test_repo", json_output=True)
                self.assertEqual(code, 0)
                output = mock_stdout.getvalue()
                data = json.loads(output)
                self.assertEqual(data["status"], "success")
                self.assertEqual(data["repo"], "/tmp/test_repo")
                self.assertEqual(data["total_files"], 15)
                self.assertEqual(data["health_score"], 88.0)
                # Verify zero ANSI escape codes leaked into JSON output
                self.assertNotIn("\033[", output)

    def test_run_scan_command_terminal_dashboard(self):
        """Asserts run_scan_command renders dashboard to stdout when not json."""
        mock_analysis = {
            "repo": "my_project",
            "total_files": 5,
            "health_score": 90.0,
            "risks": [],
            "policy_violations": []
        }

        with patch("ultron.interfaces.cli.commands.analysis.extract_current_analysis", return_value=mock_analysis):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                code = run_scan_command(repo_path="my_project", json_output=False, no_color=True)
                self.assertEqual(code, 0)
                output = mock_stdout.getvalue()
                self.assertIn("ULTRON ARCHITECTURAL INTELLIGENCE SCAN", output)
                self.assertIn("my_project", output)
                self.assertNotIn("\033[", output)

    def test_run_scan_command_error_handling(self):
        """Asserts run_scan_command handles analysis exceptions gracefully."""
        with patch("ultron.interfaces.cli.commands.analysis.extract_current_analysis", side_effect=RuntimeError("Disk read error")):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                code = run_scan_command(repo_path="broken_repo", json_output=True)
                self.assertEqual(code, 1)
                data = json.loads(mock_stdout.getvalue())
                self.assertEqual(data["status"], "error")
                self.assertIn("Disk read error", data["error"])

            with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
                code_text = run_scan_command(repo_path="broken_repo", json_output=False)
                self.assertEqual(code_text, 1)
                self.assertIn("Scan failed: Disk read error", mock_stderr.getvalue())

    def test_gate_command_color_and_no_color_options(self):
        """Asserts run_gate_command honors force_color and no_color options."""
        mock_analysis = {
            "repo": "gate_test",
            "total_files": 10,
            "health_score": 85.0,
            "risks": [],
            "policy_violations": []
        }

        with patch("ultron.interfaces.cli.commands.gate.extract_current_analysis", return_value=mock_analysis):
            with patch("sys.stderr", new_callable=io.StringIO):
                # Test no_color=True suppresses ANSI
                with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                    exit_code = run_gate_command(repo_path="gate_test", no_color=True, fail_on_regression=False)
                    self.assertEqual(exit_code, 0)
                    self.assertNotIn("\033[", mock_stdout.getvalue())

                # Test force_color=True enables ANSI
                with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                    exit_code = run_gate_command(repo_path="gate_test", force_color=True, fail_on_regression=False)
                    self.assertEqual(exit_code, 0)
                    self.assertIn("\033[", mock_stdout.getvalue())

    def test_gate_command_ci_env_forced_color(self):
        """Asserts GITHUB_ACTIONS=true + GITHUB_STEP_SUMMARY + force_color=True emits ANSI on stdout (Blocker B1 fix)."""
        mock_analysis = {
            "repo": "ci_gate_test",
            "total_files": 12,
            "health_score": 90.0,
            "risks": [],
            "policy_violations": []
        }
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_STEP_SUMMARY": "step_summary.md"}):
            with patch("ultron.interfaces.cli.commands.gate.extract_current_analysis", return_value=mock_analysis):
                with patch("builtins.open", unittest.mock.mock_open()):
                    with patch("sys.stderr", new_callable=io.StringIO):
                        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                            exit_code = run_gate_command(repo_path="ci_gate_test", force_color=True, fail_on_regression=False)
                            self.assertEqual(exit_code, 0)
                            self.assertIn("\033[", mock_stdout.getvalue())
                            self.assertIn("ULTRON ARCHITECTURAL QUALITY GATE", mock_stdout.getvalue())

    def test_gate_command_ci_env_no_color(self):
        """Asserts GITHUB_ACTIONS=true + no_color=True emits zero ANSI on stdout and stderr."""
        mock_analysis = {
            "repo": "ci_gate_no_color",
            "total_files": 5,
            "health_score": 75.0,
            "risks": [],
            "policy_violations": []
        }
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            with patch("ultron.interfaces.cli.commands.gate.extract_current_analysis", return_value=mock_analysis):
                with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
                    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                        exit_code = run_gate_command(repo_path="ci_gate_no_color", no_color=True, fail_on_regression=False)
                        self.assertEqual(exit_code, 0)
                        self.assertNotIn("\033[", mock_stdout.getvalue())
                        self.assertNotIn("\033[", mock_stderr.getvalue())

    def test_gate_command_explicit_annotations_with_and_without_color(self):
        """Asserts --github-annotations emits annotations to stdout, and color responds strictly to force_color/no_color."""
        mock_analysis = {
            "repo": "ann_test",
            "total_files": 8,
            "health_score": 95.0,
            "risks": [],
            "policy_violations": []
        }
        with patch("ultron.interfaces.cli.commands.gate.extract_current_analysis", return_value=mock_analysis):
            with patch("sys.stderr", new_callable=io.StringIO):
                # Annotations with forced color
                with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                    exit_code = run_gate_command(repo_path="ann_test", github_annotations=True, force_color=True, fail_on_regression=False)
                    self.assertEqual(exit_code, 0)
                    out = mock_stdout.getvalue()
                    self.assertIn("::notice", out)
                    self.assertIn("\033[", out)

                # Annotations with no color
                with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                    exit_code = run_gate_command(repo_path="ann_test", github_annotations=True, no_color=True, fail_on_regression=False)
                    self.assertEqual(exit_code, 0)
                    out = mock_stdout.getvalue()
                    self.assertIn("::notice", out)
                    self.assertNotIn("\033[", out)

    def test_gate_command_json_output_zero_pollution(self):
        """Asserts json_output=True emits strictly valid JSON to stdout without ANSI or workflow commands."""
        mock_analysis = {
            "repo": "json_test",
            "total_files": 15,
            "health_score": 88.0,
            "risks": [],
            "policy_violations": []
        }
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            with patch("ultron.interfaces.cli.commands.gate.extract_current_analysis", return_value=mock_analysis):
                with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
                    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                        exit_code = run_gate_command(repo_path="json_test", json_output=True, fail_on_regression=False)
                        self.assertEqual(exit_code, 0)
                        raw_stdout = mock_stdout.getvalue()
                        self.assertNotIn("\033[", raw_stdout)
                        self.assertNotIn("::notice", raw_stdout)
                        self.assertNotIn("::error", raw_stdout)
                        parsed = json.loads(raw_stdout)
                        self.assertEqual(parsed.get("status"), "PASSED")
                        # Workflow annotations redirect to stderr in JSON mode
                        self.assertIn("::notice", mock_stderr.getvalue())

    def test_gate_command_no_color_env_precedence(self):
        """Asserts NO_COLOR disables color by default, but explicit force_color=True overrides it."""
        mock_analysis = {
            "repo": "no_color_test",
            "total_files": 4,
            "health_score": 80.0,
            "risks": [],
            "policy_violations": []
        }
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            with patch("ultron.interfaces.cli.commands.gate.extract_current_analysis", return_value=mock_analysis):
                with patch("sys.stderr", new_callable=io.StringIO):
                    # Default with NO_COLOR=1: no ANSI
                    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                        exit_code = run_gate_command(repo_path="no_color_test", fail_on_regression=False)
                        self.assertEqual(exit_code, 0)
                        self.assertNotIn("\033[", mock_stdout.getvalue())

                    # Explicit force_color=True overrides NO_COLOR=1
                    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                        exit_code = run_gate_command(repo_path="no_color_test", force_color=True, fail_on_regression=False)
                        self.assertEqual(exit_code, 0)
                        self.assertIn("\033[", mock_stdout.getvalue())

    def test_gate_command_newline_and_box_integrity(self):
        """Asserts format_gate_summary produces consistent box-drawing across colored and plain output."""
        gate_decision = {
            "passed": True,
            "current_health": 92.5,
            "baseline_health": 90.0,
            "health_delta": 2.5,
            "high_risk_count": 0,
            "high_violations_count": 0,
            "total_violations_count": 0
        }
        analysis = {"repo": "box_test", "total_files": 20}
        colored = format_gate_summary(gate_decision, analysis, color=True)
        plain = format_gate_summary(gate_decision, analysis, color=False)

        self.assertIn("\033[", colored)
        self.assertNotIn("\033[", plain)
        self.assertEqual(strip_ansi(colored), plain)
        # Consistent line endings
        self.assertIn("\n", plain)
        self.assertNotIn("\r\n", plain)

    def test_cli_scan_subcommand_dispatch(self):
        """Asserts ultron main() correctly dispatches scan subcommand with flags."""
        from ultron.interfaces.ultron import main
        mock_analysis = {
            "repo": "dispatch_test",
            "total_files": 8,
            "health_score": 95.0,
            "risks": [],
            "policy_violations": []
        }

        with patch("sys.argv", ["ultron", "scan", "--repo", "dispatch_test", "--json"]):
            with patch("ultron.interfaces.cli.commands.analysis.extract_current_analysis", return_value=mock_analysis):
                with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                    with self.assertRaises(SystemExit) as cm:
                        main()
                    self.assertEqual(cm.exception.code, 0)
                    data = json.loads(mock_stdout.getvalue())
                    self.assertEqual(data["status"], "success")
                    self.assertEqual(data["total_files"], 8)


if __name__ == "__main__":
    unittest.main()
