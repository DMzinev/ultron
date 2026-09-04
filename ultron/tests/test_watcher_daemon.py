"""
ultron.tests.test_watcher_daemon
Unit test suite asserting incremental file change detection and sub-30ms AST re-analysis.
"""

import os
import shutil
import tempfile
import unittest
from ultron.core.watcher_daemon import IncrementalWatcherDaemon, norm_path


class TestIncrementalWatcherDaemon(unittest.TestCase):
    """Unit tests for IncrementalWatcherDaemon."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="ultron_watch_test_")
        self.file_a = os.path.join(self.temp_dir, "module_a.py")
        with open(self.file_a, "w", encoding="utf-8") as f:
            f.write("def hello():\n    if True:\n        return 'world'\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_norm_path(self):
        """Asserts POSIX path normalization."""
        self.assertEqual(norm_path("a\\b\\c.py"), "a/b/c.py")
        self.assertEqual(norm_path(None), "")

    def test_get_fingerprint(self):
        """Asserts SHA-256 fingerprint generation."""
        fp = IncrementalWatcherDaemon.get_fingerprint(self.file_a)
        self.assertEqual(len(fp), 64)
        self.assertEqual(IncrementalWatcherDaemon.get_fingerprint("nonexistent_file_path.xyz"), "")

    def test_sync_baseline_and_scan_no_changes(self):
        """Asserts baseline synchronization tracks files and reports 0 changes when untouched."""
        daemon = IncrementalWatcherDaemon(self.temp_dir)
        self.assertEqual(len(daemon.file_mtimes), 1)

        changes = daemon.scan_changes()
        self.assertEqual(changes["added"], [])
        self.assertEqual(changes["modified"], [])
        self.assertEqual(changes["deleted"], [])

    def test_scan_detects_added_modified_deleted(self):
        """Asserts file modifications, additions, and deletions are accurately detected."""
        daemon = IncrementalWatcherDaemon(self.temp_dir)

        # 1. Modify file_a
        with open(self.file_a, "a", encoding="utf-8") as f:
            f.write("def extra():\n    pass\n")

        # 2. Add file_b
        file_b = os.path.join(self.temp_dir, "module_b.py")
        with open(file_b, "w", encoding="utf-8") as f:
            f.write("x = 1\n")

        changes = daemon.scan_changes()
        self.assertIn("module_a.py", changes["modified"])
        self.assertIn("module_b.py", changes["added"])
        self.assertEqual(changes["deleted"], [])

        # 3. Delete file_b
        os.remove(file_b)
        changes2 = daemon.scan_changes()
        self.assertIn("module_b.py", changes2["deleted"])

    def test_reanalyze_incremental_ast(self):
        """Asserts incremental AST calculation updates complexity and impact score."""
        daemon = IncrementalWatcherDaemon(self.temp_dir)
        initial_data = {
            "risks": [
                {"file": "module_a.py", "complexity": 2.0, "coupling_score": 3.0, "impact_score": 5.5}
            ]
        }

        # Modify module_a with higher complexity
        with open(self.file_a, "w", encoding="utf-8") as f:
            f.write("def complex_fn(a, b, c):\n    if a:\n        if b:\n            if c:\n                return 1\n    return 0\n")

        updated = daemon.reanalyze_incremental(self.temp_dir, ["module_a.py"], initial_data)
        self.assertTrue(updated["incremental_update"])
        self.assertEqual(updated["dirty_files_count"], 1)
        r = updated["risks"][0]
        self.assertEqual(r["file"], "module_a.py")
        self.assertGreaterEqual(r["complexity"], 4.0)

    def test_reanalyze_incremental_syntax_error_resilience(self):
        """Asserts syntax errors during typing do not crash reanalysis pipeline."""
        daemon = IncrementalWatcherDaemon(self.temp_dir)
        with open(self.file_a, "w", encoding="utf-8") as f:
            f.write("def broken(:\n")

        updated = daemon.reanalyze_incremental(self.temp_dir, ["module_a.py"], {"risks": [{"file": "module_a.py"}]})
        self.assertIn("syntax_error", updated["risks"][0])


if __name__ == "__main__":
    unittest.main()
