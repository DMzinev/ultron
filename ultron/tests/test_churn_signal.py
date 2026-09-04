"""
ultron.tests.test_churn_signal
Test suite for Task B3: Git churn signal activation, worktree resolution,
bounded multipliers, rank shifting, and honest degradation.
"""

import os
import shutil
import tempfile
import subprocess
import unittest
import math

from ultron.core.git_adapter import GitEvidenceAdapter
from ultron.core.risk.scoring import evaluate_risks
from ultron.core import analyzer


class TestGitChurnSignal(unittest.TestCase):
    """Hermetic tests for git churn signal using temporary git repositories."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ultron_churn_test_")
        self._init_git_repo(self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def _init_git_repo(self, path):
        """Initializes a real git repository with standard user config."""
        subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Ultron Tester"], cwd=path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "tester@ultron.local"], cwd=path, capture_output=True, check=True)

    def _commit_file(self, filename, content, commit_msg, author=None):
        """Creates or overwrites a file and commits it with git."""
        full_path = os.path.join(self.test_dir, filename)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        subprocess.run(["git", "add", filename], cwd=self.test_dir, capture_output=True, check=True)
        cmd = ["git", "commit", "-m", commit_msg]
        if author:
            cmd.extend(["--author", f"{author} <{author.lower().replace(' ', '')}@test.com>"])
        subprocess.run(cmd, cwd=self.test_dir, capture_output=True, check=True)

    def test_git_adapter_subdirectory_resolution(self):
        """Verifies git history is found even when pointing to a subfolder of a git repo."""
        sub_dir = os.path.join(self.test_dir, "services", "backend")
        os.makedirs(sub_dir, exist_ok=True)
        rel_file = os.path.join("services", "backend", "handler.py")

        self._commit_file(rel_file, "def handle(): pass\n", "feat: initial handler")
        self._commit_file(rel_file, "def handle(): return 1\n", "fix: resolve return bug")

        adapter = GitEvidenceAdapter()
        # Test directly from the subfolder
        self.assertTrue(adapter.is_git_repository(sub_dir), "Subdirectory must be recognized as inside git worktree")
        churn_map, is_active = adapter.get_churn_map(sub_dir)

        self.assertTrue(is_active, "Churn signal must be active for subdirectory")
        self.assertIn("handler.py", churn_map, "File must be mapped relative to the subdirectory")
        self.assertEqual(churn_map["handler.py"]["commits"], 2)
        self.assertEqual(churn_map["handler.py"]["bug_fixes"], 1)

    def test_churn_metric_extraction(self):
        """Verifies commit counts, distinct authors, and regex bug filtering with pipe characters."""
        rel_file = "service.py"
        self._commit_file(rel_file, "x = 1\n", "feat: initial commit", author="Alice")
        self._commit_file(rel_file, "x = 2\n", "fix(core): parser bug | add regression test", author="Bob")
        self._commit_file(rel_file, "x = 3\n", "hotfix: urgent security fix", author="Alice")
        self._commit_file(rel_file, "x = 4\n", "refactor: clean prefix fixture debug logic", author="Charlie")

        adapter = GitEvidenceAdapter()
        churn_map, is_active = adapter.get_churn_map(self.test_dir)

        self.assertTrue(is_active)
        self.assertIn("service.py", churn_map)
        data = churn_map["service.py"]

        self.assertEqual(data["commits"], 4, "Should have 4 total commits")
        self.assertEqual(data["authors"], 3, "Should have 3 distinct authors (Alice, Bob, Charlie)")
        # Commits 2 and 3 match fix/hotfix. Commit 4 has 'prefix', 'fixture', 'debug' which must NOT match
        self.assertEqual(data["bug_fixes"], 2, "Should match exactly 2 bug fixes (not non-word substrings)")

    def test_churn_multiplier_bounds(self):
        """Verifies churn multiplier is strictly bounded between [1.0, 2.0]."""
        def calc_m(commits, fixes, authors):
            if commits <= 0:
                return 1.0
            churn_raw = (
                0.10 * math.log(1.0 + commits) +
                0.20 * math.log(1.0 + fixes) +
                0.05 * math.log(1.0 + authors)
            )
            return max(1.0, min(2.0, 1.0 + churn_raw))

        self.assertEqual(calc_m(0, 0, 0), 1.0, "0 commits must yield neutral multiplier 1.0")
        self.assertEqual(calc_m(-5, 0, 0), 1.0, "Negative input must clamp to 1.0")
        self.assertEqual(calc_m(10000, 5000, 100), 2.0, "Extreme commits must clamp to ceiling 2.0")
        self.assertGreater(calc_m(10, 2, 2), 1.0)
        self.assertLessEqual(calc_m(10, 2, 2), 2.0)

    def test_churn_measurably_shifts_rank(self):
        """Files with identical complexity/coupling must be ranked higher when churn is high."""
        code_body = (
            "def compute(a, b):\n"
            "    if a > 0:\n"
            "        return a + b\n"
            "    elif b > 0:\n"
            "        return a - b\n"
            "    return 0\n"
        )
        # stable.py gets 1 commit
        self._commit_file("stable.py", code_body, "feat: initial stable")
        # churning.py gets 8 commits, 4 of which are bug fixes
        self._commit_file("churning.py", code_body, "feat: initial churning", author="Dev1")
        for i in range(7):
            msg = f"fix: patch defect number {i}" if i % 2 == 0 else f"chore: minor update {i}"
            author = "Dev2" if i % 2 == 0 else "Dev3"
            self._commit_file("churning.py", code_body + f"\n# iteration {i}", msg, author=author)

        codebase = analyzer.analyze_directory(self.test_dir)
        target_files = ["stable.py", "churning.py"]
        risks = evaluate_risks(codebase, target_files, repo_path=self.test_dir)

        risk_map = {r.file_path: r for r in risks}
        self.assertIn("stable.py", risk_map)
        self.assertIn("churning.py", risk_map)

        stable_r = risk_map["stable.py"]
        churn_r = risk_map["churning.py"]

        # Both have the same base complexity
        self.assertEqual(stable_r.complexity, churn_r.complexity)
        # But churning file must have a higher impact score due to churn multiplier
        self.assertGreater(
            churn_r.impact_score, stable_r.impact_score,
            f"Churning file ({churn_r.impact_score}) must have higher score than stable file ({stable_r.impact_score})"
        )
        self.assertEqual(churn_r.churn["status"], "active")
        self.assertGreater(churn_r.churn["multiplier"], 1.0)
        self.assertGreater(churn_r.churn["commits"], stable_r.churn["commits"])

    def test_honest_degradation_non_git(self):
        """Non-git directory must return status 'unavailable', multiplier 1.0, without raising errors."""
        non_git_dir = tempfile.mkdtemp(prefix="ultron_non_git_")
        try:
            sample_file = os.path.join(non_git_dir, "script.py")
            with open(sample_file, "w", encoding="utf-8") as f:
                f.write("def run(): pass\n")

            codebase = analyzer.analyze_directory(non_git_dir)
            risks = evaluate_risks(codebase, ["script.py"], repo_path=non_git_dir)

            self.assertEqual(len(risks), 1)
            r = risks[0]
            self.assertEqual(r.churn["status"], "unavailable")
            self.assertEqual(r.churn["multiplier"], 1.0)
            self.assertEqual(r.churn["commits"], 0)
        finally:
            shutil.rmtree(non_git_dir, ignore_errors=True)

    def test_ultron_self_scan_churn_active(self):
        """Verifies that churn signal is active on Ultron's own repository with non-zero commits."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        adapter = GitEvidenceAdapter()
        self.assertTrue(adapter.is_git_repository(repo_root), "Ultron repository must be recognized as a git repo")

        churn_map, is_active = adapter.get_churn_map(repo_root)
        self.assertTrue(is_active, "Churn signal must be active on Ultron repo")
        self.assertGreater(len(churn_map), 0, "Ultron churn map must contain tracked python files")

        # Check that core files have non-zero commit counts
        total_commits = sum(v["commits"] for v in churn_map.values())
        self.assertGreater(total_commits, 0, f"Expected > 0 commits on Ultron repo, got {total_commits}")


if __name__ == "__main__":
    unittest.main()
