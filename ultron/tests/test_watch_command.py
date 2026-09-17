"""
ultron.tests.test_watch_command
Hermetic unit test suite for Task P5-B2: Continuous Architecture Watch Mode Daemon.
"""

import io
import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from ultron.interfaces.cli.commands.watch import (
    compute_file_blast_radius,
    detect_changes,
    format_watch_event,
    run_watch_command,
    scan_mtimes,
)
from ultron.interfaces.cli.formatting import strip_ansi


class TestWatchCommand(unittest.TestCase):
    """Hermetic unit tests for the watch daemon CLI command and file monitoring engine."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_mtimes_discovery_and_pruning(self):
        """Asserts scan_mtimes finds tracked python files and prunes ignored directories."""
        # Create normal files
        f1 = os.path.join(self.repo_dir, "app.py")
        sub_dir = os.path.join(self.repo_dir, "pkg")
        os.makedirs(sub_dir, exist_ok=True)
        f2 = os.path.join(sub_dir, "module.py")
        txt = os.path.join(self.repo_dir, "readme.txt")

        # Create ignored directory files
        git_dir = os.path.join(self.repo_dir, ".git", "hooks")
        venv_dir = os.path.join(self.repo_dir, ".venv", "lib")
        ultron_dir = os.path.join(self.repo_dir, ".ultron")
        pycache_dir = os.path.join(self.repo_dir, "__pycache__")
        os.makedirs(git_dir, exist_ok=True)
        os.makedirs(venv_dir, exist_ok=True)
        os.makedirs(ultron_dir, exist_ok=True)
        os.makedirs(pycache_dir, exist_ok=True)

        f_git = os.path.join(git_dir, "hook.py")
        f_venv = os.path.join(venv_dir, "dep.py")
        f_ultron = os.path.join(ultron_dir, "state.py")
        f_pycache = os.path.join(pycache_dir, "app.cpython-310.py")

        for p in (f1, f2, txt, f_git, f_venv, f_ultron, f_pycache):
            with open(p, "w", encoding="utf-8") as f:
                f.write("# content")

        snapshot = scan_mtimes(self.repo_dir)

        self.assertIn("app.py", snapshot)
        self.assertIn("pkg/module.py", snapshot)
        self.assertNotIn("readme.txt", snapshot)
        self.assertNotIn(".git/hooks/hook.py", snapshot)
        self.assertNotIn(".venv/lib/dep.py", snapshot)
        self.assertNotIn(".ultron/state.py", snapshot)
        self.assertNotIn("__pycache__/app.cpython-310.py", snapshot)

    def test_detect_changes_modified_added_deleted(self):
        """Asserts detect_changes identifies modified, added, and deleted files correctly."""
        old_snapshot = {
            "stable.py": (1000.0, 50),
            "to_modify.py": (1000.0, 50),
            "to_delete.py": (1000.0, 50),
        }
        new_snapshot = {
            "stable.py": (1000.0, 50),
            "to_modify.py": (1001.0, 60),  # modified mtime and size
            "added.py": (1000.0, 50),      # new file
        }

        modified, added, deleted = detect_changes(old_snapshot, new_snapshot)

        self.assertEqual(modified, ["to_modify.py"])
        self.assertEqual(added, ["added.py"])
        self.assertEqual(deleted, ["to_delete.py"])

    def test_detect_changes_no_op(self):
        """Asserts detect_changes returns empty lists when snapshots match."""
        snapshot = {
            "a.py": (1000.0, 50),
            "b.py": (2000.0, 100),
        }
        modified, added, deleted = detect_changes(snapshot, snapshot)
        self.assertEqual(modified, [])
        self.assertEqual(added, [])
        self.assertEqual(deleted, [])

    def test_compute_file_blast_radius(self):
        """Asserts compute_file_blast_radius traverses upstream dependencies."""
        edges = [
            {"source": "caller.py", "target": "callee.py", "type": "imports"},
            {"source": "transit.py", "target": "caller.py", "type": "imports"},
            {"source": "unrelated.py", "target": "other.py", "type": "imports"},
        ]

        # callee.py has 2 upstream dependents: caller.py and transit.py
        radius = compute_file_blast_radius(self.repo_dir, "callee.py", cached_edges=edges)
        self.assertEqual(radius, 2)

        # caller.py has 1 upstream dependent: transit.py
        radius_caller = compute_file_blast_radius(self.repo_dir, "caller.py", cached_edges=edges)
        self.assertEqual(radius_caller, 1)

        # unrelated.py has 0 upstream dependents
        radius_unrelated = compute_file_blast_radius(self.repo_dir, "unrelated.py", cached_edges=edges)
        self.assertEqual(radius_unrelated, 0)

    def test_format_watch_event_colored_and_plain(self):
        """Asserts event formatting emits readable text and honors color disabling."""
        event = {
            "timestamp": "12:34:56",
            "change_type": "MODIFIED",
            "file": "core/engine.py",
            "level": "HIGH",
            "blast_radius": 3,
            "health_before": 85.0,
            "health_after": 82.0,
            "delta": -3.0,
        }

        colored = format_watch_event(event, color=True)
        plain = format_watch_event(event, color=False)

        self.assertIn("12:34:56", plain)
        self.assertIn("MODIFIED", plain)
        self.assertIn("core/engine.py", plain)
        self.assertIn("[HIGH]", plain)
        self.assertIn("blast radius: 3 files", plain)
        self.assertIn("health: 82.0 (-3.0)", plain)

        # Stripping ANSI from colored should match plain text
        self.assertEqual(strip_ansi(colored), plain)

    def test_format_watch_event_positive_and_negative_deltas(self):
        """Asserts health deltas format properly with explicit positive and negative signs."""
        event_pos = {
            "timestamp": "12:00:00",
            "change_type": "ADDED",
            "file": "new.py",
            "level": "LOW",
            "blast_radius": 1,
            "health_before": 80.0,
            "health_after": 85.0,
            "delta": 5.0,
        }
        text_pos = format_watch_event(event_pos, color=False)
        self.assertIn("health: 85.0 (+5.0)", text_pos)
        self.assertIn("blast radius: 1 file", text_pos)

        event_zero = {
            "timestamp": "12:00:00",
            "change_type": "DELETED",
            "file": "old.py",
            "level": "LOW",
            "blast_radius": 0,
            "health_before": 85.0,
            "health_after": 85.0,
            "delta": 0.0,
        }
        text_zero = format_watch_event(event_zero, color=False)
        self.assertIn("health: 85.0 (+0.0)", text_zero)

    def test_run_watch_command_nonexistent_directory(self):
        """Asserts run_watch_command returns exit code 1 when repository does not exist."""
        bad_dir = os.path.join(self.repo_dir, "nonexistent_subfolder")
        code = run_watch_command(repo_path=bad_dir)
        self.assertEqual(code, 1)

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code_json = run_watch_command(repo_path=bad_dir, json_output=True)
            self.assertEqual(code_json, 1)
            parsed = json.loads(buf.getvalue().strip())
            self.assertEqual(parsed.get("status"), "error")

    def test_run_watch_command_once_mode(self):
        """Asserts run_watch_command runs a single iteration and exits cleanly under once=True."""
        f = os.path.join(self.repo_dir, "test.py")
        with open(f, "w", encoding="utf-8") as fp:
            fp.write("def hello(): pass\n")

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = run_watch_command(
                repo_path=self.repo_dir,
                once=True,
                sleep_fn=lambda _: None
            )
        self.assertEqual(code, 0)
        self.assertIn("Ultron Architecture Watcher active", buf.getvalue())

    def test_run_watch_command_detects_modification_and_invokes_callback(self):
        """Asserts change is detected across polling ticks and callback is invoked with event data."""
        fpath = os.path.join(self.repo_dir, "target.py")
        with open(fpath, "w", encoding="utf-8") as fp:
            fp.write("def calculate(): return 1\n")

        events_received = []

        def record_event(evt):
            events_received.append(evt)

        sleep_count = 0

        def mock_sleep(_duration):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count == 1:
                # Simulate file edit during sleep
                time.sleep(0.01)
                with open(fpath, "w", encoding="utf-8") as fp:
                    fp.write("def calculate():\n    # complex change\n    return 42\n")

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = run_watch_command(
                repo_path=self.repo_dir,
                interval=0.01,
                debounce=0.0,
                max_ticks=2,
                sleep_fn=mock_sleep,
                callback=record_event
            )

        self.assertEqual(code, 0)
        self.assertEqual(len(events_received), 1)
        evt = events_received[0]
        self.assertEqual(evt["file"], "target.py")
        self.assertEqual(evt["change_type"], "MODIFIED")
        self.assertIn("health_after", evt)
        self.assertIn("target.py", buf.getvalue())

    def test_run_watch_command_json_output(self):
        """Asserts json_output=True emits single-line JSON objects."""
        fpath = os.path.join(self.repo_dir, "service.py")
        with open(fpath, "w", encoding="utf-8") as fp:
            fp.write("def run(): pass\n")

        sleep_count = 0

        def mock_sleep(_):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count == 1:
                with open(fpath, "a", encoding="utf-8") as fp:
                    fp.write("def stop(): pass\n")

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = run_watch_command(
                repo_path=self.repo_dir,
                interval=0.01,
                debounce=0.0,
                max_ticks=2,
                json_output=True,
                sleep_fn=mock_sleep
            )

        self.assertEqual(code, 0)
        out = buf.getvalue().strip()
        lines = [line for line in out.splitlines() if line.strip()]
        self.assertGreaterEqual(len(lines), 1)
        parsed = json.loads(lines[-1])
        self.assertEqual(parsed["file"], "service.py")
        self.assertEqual(parsed["change_type"], "MODIFIED")

    def test_run_watch_command_strict_exit_on_degradation(self):
        """Asserts strict=True exits with code 1 if health score degrades."""
        fpath = os.path.join(self.repo_dir, "lib.py")
        with open(fpath, "w", encoding="utf-8") as fp:
            fp.write("def foo(): return 1\n")

        def mock_sleep(_):
            with open(fpath, "a", encoding="utf-8") as fp:
                fp.write("def bar(): return 2\n")

        # Mock extract_current_analysis to simulate health score drop on second call
        analyses = [
            {"health_score": 90.0, "risks": [], "repo": self.repo_dir, "total_files": 1, "policy_violations": []},
            {"health_score": 85.0, "risks": [{"file_path": "lib.py", "level": "HIGH"}], "repo": self.repo_dir, "total_files": 1, "policy_violations": []},
        ]

        with patch("ultron.interfaces.cli.commands.watch.extract_current_analysis", side_effect=analyses):
            code = run_watch_command(
                repo_path=self.repo_dir,
                interval=0.01,
                debounce=0.0,
                max_ticks=2,
                strict=True,
                sleep_fn=mock_sleep
            )
            self.assertEqual(code, 1)

    def test_run_watch_command_keyboard_interrupt_clean_exit(self):
        """Asserts KeyboardInterrupt exits cleanly with code 0 without raising exception."""
        def mock_sleep_interrupt(_):
            raise KeyboardInterrupt()

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = run_watch_command(
                repo_path=self.repo_dir,
                sleep_fn=mock_sleep_interrupt
            )
        self.assertEqual(code, 0)
        self.assertIn("Ultron Architecture Watcher stopped", buf.getvalue())

    def test_cli_subcommand_dispatch_watch(self):
        """Asserts ultron main() correctly dispatches watch subcommand with flags."""
        from ultron.interfaces.ultron import main

        test_args = [
            "ultron", "watch",
            "--repo", self.repo_dir,
            "--once",
            "--no-color",
        ]

        buf = io.StringIO()
        with patch.object(sys, "argv", test_args):
            with patch("sys.stdout", buf):
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
        self.assertIn("Ultron Architecture Watcher active", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
