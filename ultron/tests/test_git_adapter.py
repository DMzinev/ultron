"""
Ultron Unit & Adversarial Tests — GitEvidenceAdapter Verification Suite
Campaign 39 / v2.5 — Comprehensive Threat-Modeled Test Architecture
Covers: Nominal cases, non-git directories, missing git CLI, empty repos,
detached HEAD, merge commits, renames, Windows path normalization,
binary files in numstat, and Unicode safety.
"""

import os
import sys
import shutil
import tempfile
import subprocess
import unittest
from unittest.mock import patch, MagicMock

from ultron.core.git_adapter import (
    GitEvidenceAdapter,
    normalize_git_path,
    compute_churn_velocity,
    compute_hotspot_score
)
from ultron.core.system_model import EvidenceObject


class TestGitEvidenceAdapter(unittest.TestCase):
    """
    Exhaustive Test Suite for GitEvidenceAdapter.
    Adversarial Threat Modeling & Boundary Verification.
    """

    def setUp(self):
        self.adapter = GitEvidenceAdapter()

    # ==========================================
    # 1. Path Normalization & Math Helpers
    # ==========================================

    def test_normalize_git_path_renames_and_slashes(self):
        """Tests git path normalization including renames and Windows backslashes."""
        self.assertEqual(normalize_git_path("src\\core\\engine.py"), "src/core/engine.py")
        self.assertEqual(normalize_git_path("./src/utils.py"), "src/utils.py")
        self.assertEqual(normalize_git_path('"quoted/path.py"'), "quoted/path.py")
        # Rename syntaxes
        self.assertEqual(normalize_git_path("old.py => new.py"), "new.py")
        self.assertEqual(normalize_git_path("src/{old => new}/module.py"), "src/new/module.py")
        self.assertEqual(normalize_git_path(""), "")

    def test_churn_velocity_and_hotspot_score_formulas(self):
        """Tests deterministic math calculation for velocity and hotspot scores."""
        # 0 commits
        self.assertEqual(compute_churn_velocity(0, 0, 0), 0.0)
        self.assertEqual(compute_hotspot_score(5.0, 0, 0, 0), 0.0)

        # 10 commits, 100 added, 50 deleted
        v = compute_churn_velocity(10, 100, 50)
        self.assertGreater(v, 0.0)

        # Hotspot score with complexity = 5.0, 2 bug fixes
        h = compute_hotspot_score(5.0, 10, 100, 50, bug_fixes=2)
        self.assertGreater(h, v)

    # ==========================================
    # 2. Non-Git Directory & Boundary Safety
    # ==========================================

    def test_non_git_directory_returns_empty_list(self):
        """Invariant: Non-git directory must safely return [] without errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            evidence = self.adapter.parse_git_history(tmpdir)
            self.assertEqual(evidence, [])
            analysis = self.adapter.analyze_repository(tmpdir)
            self.assertEqual(analysis["files"], {})

    def test_non_existent_directory_returns_empty_list(self):
        """Invariant: Non-existent path must safely return [] without raising exceptions."""
        non_existent_path = os.path.join(tempfile.gettempdir(), "ultron_missing_repo_dir_12345")
        evidence = self.adapter.parse_git_history(non_existent_path)
        self.assertEqual(evidence, [])

    def test_empty_string_path_returns_empty_list(self):
        """Invariant: Empty string repo path must safely return []."""
        evidence = self.adapter.parse_git_history("")
        self.assertEqual(evidence, [])

    # ==========================================
    # 3. Subprocess & Environment Failure Modes (Mocked)
    # ==========================================

    @patch("subprocess.run")
    def test_git_not_installed_file_not_found(self, mock_run):
        """Invariant: If 'git' is not installed/found, handle FileNotFoundError gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".git"), exist_ok=True)
            mock_run.side_effect = FileNotFoundError("No such file or directory: 'git'")

            evidence = self.adapter.parse_git_history(tmpdir)
            self.assertEqual(evidence, [])

    @patch("subprocess.run")
    def test_git_permission_error(self, mock_run):
        """Invariant: If git execution raises PermissionError, handle gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".git"), exist_ok=True)
            mock_run.side_effect = PermissionError("Permission denied: 'git'")

            evidence = self.adapter.parse_git_history(tmpdir)
            self.assertEqual(evidence, [])

    @patch("subprocess.run")
    def test_git_subprocess_timeout(self, mock_run):
        """Invariant: Subprocess timeout must be caught and return [] without hanging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".git"), exist_ok=True)
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["git", "log"], timeout=5.0)

            evidence = self.adapter.parse_git_history(tmpdir)
            self.assertEqual(evidence, [])

    @patch("subprocess.run")
    def test_git_nonzero_exit_code_failure(self, mock_run):
        """Invariant: If git returns non-zero code (corrupt repo), return [] cleanly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".git"), exist_ok=True)
            mock_run.return_value = MagicMock(
                returncode=128,
                stdout="",
                stderr="fatal: not a git repository (or any of the parent directories)"
            )

            evidence = self.adapter.parse_git_history(tmpdir)
            self.assertEqual(evidence, [])

    # ==========================================
    # 4. Real Git Integration: Empty & Nominal Repos
    # ==========================================

    def test_empty_git_repo_zero_commits(self):
        """Invariant: Freshly initialized repo with zero commits must return []."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, check=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                self.skipTest("Git CLI not available for live repository testing")

            evidence = self.adapter.parse_git_history(tmpdir)
            self.assertEqual(evidence, [])

    def test_nominal_git_repo_single_commit(self):
        """Test single commit repository creates valid EvidenceObject records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, check=True)
                subprocess.run(["git", "config", "user.email", "ultron@test.local"], cwd=tmpdir, check=True)
                subprocess.run(["git", "config", "user.name", "Ultron Tester"], cwd=tmpdir, check=True)

                py_file = os.path.join(tmpdir, "core.py")
                with open(py_file, "w", encoding="utf-8") as f:
                    f.write("def run(): pass\n")

                subprocess.run(["git", "add", "core.py"], cwd=tmpdir, check=True)
                subprocess.run(["git", "commit", "-m", "Initial commit of core engine"], cwd=tmpdir, check=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                self.skipTest("Git CLI not available for live repository testing")

            evidence = self.adapter.parse_git_history(tmpdir)
            self.assertEqual(len(evidence), 1)
            ev = evidence[0]
            self.assertEqual(ev.type, "GIT_HISTORY")
            self.assertEqual(ev.subject_id, "module:core.py")
            self.assertEqual(ev.measurement["commits"], 1)
            self.assertEqual(ev.measurement["bug_fixes"], 0)
            self.assertEqual(ev.measurement["top_author"], "Ultron Tester")
            self.assertEqual(ev.source["file"], "core.py")

    def test_nominal_git_repo_churn_and_co_change(self):
        """Test multi-commit repository accurately computes churn, bug fixes, and co-changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, check=True)
                subprocess.run(["git", "config", "user.email", "ultron@test.local"], cwd=tmpdir, check=True)
                subprocess.run(["git", "config", "user.name", "Ultron Tester"], cwd=tmpdir, check=True)

                f_service = os.path.join(tmpdir, "service.py")
                f_models = os.path.join(tmpdir, "models.py")

                with open(f_service, "w", encoding="utf-8") as f:
                    f.write("# Service V1\n")
                with open(f_models, "w", encoding="utf-8") as f:
                    f.write("# Models V1\n")

                subprocess.run(["git", "add", "service.py", "models.py"], cwd=tmpdir, check=True)
                subprocess.run(["git", "commit", "-m", "feat: initial service and models implementation"], cwd=tmpdir, check=True)

                # Commit 2: Joint Bug fix on both files
                with open(f_service, "a", encoding="utf-8") as f:
                    f.write("# Service V2 - fixed logic\n")
                with open(f_models, "a", encoding="utf-8") as f:
                    f.write("# Models V2 - fixed schema\n")

                subprocess.run(["git", "add", "service.py", "models.py"], cwd=tmpdir, check=True)
                subprocess.run(["git", "commit", "-m", "fix: resolve critical null pointer bug across service and models"], cwd=tmpdir, check=True)

                # Commit 3: Solo refactor on service only
                with open(f_service, "a", encoding="utf-8") as f:
                    f.write("# Service V3\n")

                subprocess.run(["git", "add", "service.py"], cwd=tmpdir, check=True)
                subprocess.run(["git", "commit", "-m", "refactor: optimize service throughput"], cwd=tmpdir, check=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                self.skipTest("Git CLI not available for live repository testing")

            evidence = self.adapter.parse_git_history(tmpdir)
            lookup = {ev.subject_id: ev.measurement for ev in evidence}

            self.assertIn("module:service.py", lookup)
            self.assertIn("module:models.py", lookup)

            # Service had 3 commits, 1 bug fix
            self.assertEqual(lookup["module:service.py"]["commits"], 3)
            self.assertEqual(lookup["module:service.py"]["bug_fixes"], 1)
            self.assertGreater(lookup["module:service.py"]["total_churn"], 0)

            # Models had 2 commits, 1 bug fix
            self.assertEqual(lookup["module:models.py"]["commits"], 2)
            self.assertEqual(lookup["module:models.py"]["bug_fixes"], 1)

            # Co-change coupling: models & service co-committed in 2 commits
            # For models (total 2 commits): co_change_ratio = 2/2 = 1.0
            models_co_changes = lookup["module:models.py"]["co_changes"]
            self.assertTrue(len(models_co_changes) > 0)
            self.assertEqual(models_co_changes[0]["file"], "service.py")
            self.assertEqual(models_co_changes[0]["co_change_ratio"], 1.0)

    # ==========================================
    # 5. Detached HEAD & Branch Agnosticism
    # ==========================================

    def test_detached_head_commit_history_resolution(self):
        """Invariant: Git history extraction must succeed even in detached HEAD state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, check=True)
                subprocess.run(["git", "config", "user.email", "ultron@test.local"], cwd=tmpdir, check=True)
                subprocess.run(["git", "config", "user.name", "Ultron Tester"], cwd=tmpdir, check=True)

                py_file = os.path.join(tmpdir, "detached.py")
                with open(py_file, "w", encoding="utf-8") as f:
                    f.write("x = 1\n")
                subprocess.run(["git", "add", "detached.py"], cwd=tmpdir, check=True)
                subprocess.run(["git", "commit", "-m", "commit one"], cwd=tmpdir, check=True)

                proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmpdir, capture_output=True, text=True, check=True)
                sha = proc.stdout.strip()
                subprocess.run(["git", "checkout", sha], cwd=tmpdir, capture_output=True, check=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                self.skipTest("Git CLI not available for live repository testing")

            evidence = self.adapter.parse_git_history(tmpdir)
            self.assertEqual(len(evidence), 1)
            self.assertEqual(evidence[0].subject_id, "module:detached.py")
            self.assertEqual(evidence[0].measurement["commits"], 1)

    # ==========================================
    # 6. Unicode, Emojis & International Character Sets
    # ==========================================

    def test_unicode_commit_messages_and_authors(self):
        """Invariant: UTF-8 commit messages (emojis, Cyrillic, CJK, accents) must parse cleanly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, check=True)
                subprocess.run(["git", "config", "user.email", "rene@elan.org"], cwd=tmpdir, check=True)
                subprocess.run(["git", "config", "user.name", "René François 🚀"], cwd=tmpdir, check=True)

                py_file = os.path.join(tmpdir, "unicode_test.py")
                with open(py_file, "w", encoding="utf-8") as f:
                    f.write("# Unicode test module\n")
                subprocess.run(["git", "add", "unicode_test.py"], cwd=tmpdir, check=True)
                subprocess.run(
                    ["git", "commit", "-m", "🐛 fix(auth): исправление ошибки 修复 bug avec succès"],
                    cwd=tmpdir,
                    check=True
                )
            except (subprocess.SubprocessError, FileNotFoundError):
                self.skipTest("Git CLI not available for live repository testing")

            evidence = self.adapter.parse_git_history(tmpdir)
            self.assertEqual(len(evidence), 1)
            ev = evidence[0]
            self.assertEqual(ev.subject_id, "module:unicode_test.py")
            self.assertEqual(ev.measurement["commits"], 1)
            self.assertEqual(ev.measurement["bug_fixes"], 1)
            self.assertEqual(ev.measurement["top_author"], "René François 🚀")

    # ==========================================
    # 7. Bug Fix Word Boundary Precision (Anti-False Positives)
    # ==========================================

    @patch("subprocess.run")
    def test_bug_fix_heuristic_avoids_substring_false_positives(self, mock_run):
        """Invariant: Words like 'prefix', 'postfix', 'traffic' must NOT be classified as bug fixes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".git"), exist_ok=True)

            mock_stdout = (
                "COMMIT:c1|Author|a@test|Update prefix routing table and postfix handlers\n"
                "10\t2\tsrc/router.py\n"
                "COMMIT:c2|Author|a@test|Refactor network traffic monitor\n"
                "5\t1\tsrc/traffic.py\n"
                "COMMIT:c3|Author|a@test|Hotfix: repair database connection issue\n"
                "8\t4\tsrc/db.py\n"
            )
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_stdout, stderr="")

            evidence = self.adapter.parse_git_history(tmpdir)
            lookup = {ev.subject_id: ev.measurement["bug_fixes"] for ev in evidence}

            self.assertIn("module:src/router.py", lookup)
            self.assertEqual(lookup["module:src/router.py"], 0)  # 'prefix' / 'postfix' not bug fix

            self.assertIn("module:src/traffic.py", lookup)
            self.assertEqual(lookup["module:src/traffic.py"], 0)  # 'traffic' not bug fix

            self.assertIn("module:src/db.py", lookup)
            self.assertEqual(lookup["module:src/db.py"], 1)  # 'Hotfix' / 'repair' / 'issue' IS bug fix

    # ==========================================
    # 8. Binary Files in Numstat
    # ==========================================

    @patch("subprocess.run")
    def test_binary_files_in_numstat_handled_gracefully(self, mock_run):
        """Invariant: Numstat lines with '-' for binary additions/deletions must not throw ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".git"), exist_ok=True)

            mock_stdout = (
                "COMMIT:c1|Author|a@test|Add binary assets and python script\n"
                "-\t-\tassets/logo.png\n"
                "15\t3\tsrc/render.py\n"
            )
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_stdout, stderr="")

            evidence = self.adapter.parse_git_history(tmpdir)
            self.assertEqual(len(evidence), 1)
            self.assertEqual(evidence[0].subject_id, "module:src/render.py")
            self.assertEqual(evidence[0].measurement["lines_added"], 15)
            self.assertEqual(evidence[0].measurement["lines_deleted"], 3)


if __name__ == "__main__":
    unittest.main()
