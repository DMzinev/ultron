"""
ultron.tests.test_git_hooks
Hermetic unit test suite for native Git pre-commit and pre-push quality gate hooks.
Completely isolated from the host repository; all tests use temporary directories.
"""

from io import StringIO
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

from ultron.interfaces.cli.commands.hook import (
    ULTRON_HOOK_SIGNATURE,
    _find_hooks_dir,
    _is_ultron_hook,
    _generate_hook_script,
    install_hooks,
    uninstall_hooks,
    get_hook_status,
    run_hook_command,
)


class TestGitHooks(unittest.TestCase):
    """Hermetic unit tests for Git pre-commit and pre-push quality gate hooks."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = os.path.join(self.temp_dir.name, "repo")
        self.git_dir = os.path.join(self.repo_dir, ".git")
        os.makedirs(self.git_dir, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_find_hooks_dir_standard_repo(self):
        """Verifies hooks directory resolution in standard .git directory."""
        hooks_dir = _find_hooks_dir(self.repo_dir)
        expected = os.path.normpath(os.path.join(self.git_dir, "hooks"))
        self.assertEqual(hooks_dir, expected)
        self.assertTrue(os.path.isdir(hooks_dir))

    def test_find_hooks_dir_worktree_with_commondir(self):
        """Verifies hooks directory resolution in Git worktrees using commondir."""
        # Create main repo structure: main_repo/.git/worktrees/wt1
        main_repo = os.path.join(self.temp_dir.name, "main_repo")
        main_git = os.path.join(main_repo, ".git")
        main_hooks = os.path.join(main_git, "hooks")
        wt_meta = os.path.join(main_git, "worktrees", "wt1")
        os.makedirs(wt_meta, exist_ok=True)
        os.makedirs(main_hooks, exist_ok=True)

        # commondir inside wt_meta points back to main_git (../..)
        with open(os.path.join(wt_meta, "commondir"), "w", encoding="utf-8") as f:
            f.write("../..\n")

        # Create separate worktree directory with .git pointer file
        wt_dir = os.path.join(self.temp_dir.name, "worktree1")
        os.makedirs(wt_dir, exist_ok=True)
        with open(os.path.join(wt_dir, ".git"), "w", encoding="utf-8") as f:
            f.write(f"gitdir: {wt_meta}\n")

        hooks_dir = _find_hooks_dir(wt_dir)
        self.assertEqual(hooks_dir, os.path.normpath(main_hooks))

    def test_find_hooks_dir_submodule_without_commondir(self):
        """Verifies hooks directory resolution in submodules (no commondir)."""
        submod_meta = os.path.join(self.temp_dir.name, "modules", "submod")
        os.makedirs(submod_meta, exist_ok=True)

        submod_dir = os.path.join(self.temp_dir.name, "submodule")
        os.makedirs(submod_dir, exist_ok=True)
        with open(os.path.join(submod_dir, ".git"), "w", encoding="utf-8") as f:
            f.write(f"gitdir: {submod_meta}\n")

        hooks_dir = _find_hooks_dir(submod_dir)
        expected = os.path.normpath(os.path.join(submod_meta, "hooks"))
        self.assertEqual(hooks_dir, expected)

    def test_find_hooks_dir_non_git_repo(self):
        """Verifies ValueError raised if target directory is not a Git repository."""
        non_git = os.path.join(self.temp_dir.name, "plain_dir")
        os.makedirs(non_git, exist_ok=True)
        with self.assertRaises(ValueError) as ctx:
            _find_hooks_dir(non_git)
        self.assertIn("not a Git repository", str(ctx.exception))

    def test_generate_hook_script_signature_and_newlines(self):
        """Verifies hook script format, canonical signature, and forward slashes."""
        script = _generate_hook_script(
            hook_type="pre-commit",
            strict=True,
            fail_on_high=True,
            fail_on_regression=True,
            base="HEAD",
        )
        self.assertTrue(script.startswith("#!/usr/bin/env sh"))
        self.assertIn(ULTRON_HOOK_SIGNATURE, script)
        # Check forward slash normalization on sys.executable
        expected_py = sys.executable.replace("\\", "/")
        self.assertIn(expected_py, script)
        # Confirm no Windows CRLF escaped characters
        self.assertNotIn("\r", script)

    def test_generate_hook_script_4_tier_python_resolution(self):
        """Verifies 4-tier Python resolver ladder in synthesized shell script."""
        script = _generate_hook_script("pre-commit")
        self.assertIn('$VIRTUAL_ENV/bin/python', script)
        self.assertIn('$VIRTUAL_ENV/Scripts/python.exe', script)
        self.assertIn('$GIT_ROOT/.venv/bin/python', script)
        self.assertIn('$GIT_ROOT/.venv/Scripts/python.exe', script)
        self.assertIn('command -v python3', script)

    def test_generate_hook_script_invokes_gate_with_base_head(self):
        """Verifies pre-commit hook passes --base HEAD and quality flags to ultron gate."""
        script = _generate_hook_script(
            hook_type="pre-commit",
            strict=True,
            fail_on_high=True,
            fail_on_regression=True,
            base="HEAD",
        )
        self.assertIn('--base HEAD', script)
        self.assertIn('--strict', script)
        self.assertIn('--fail-on-high', script)
        self.assertIn('--fail-on-regression', script)

    def test_install_hooks_clean(self):
        """Verifies installing hooks into a clean repository."""
        ret = install_hooks(self.repo_dir, hook_types=["pre-commit", "pre-push"])
        self.assertEqual(ret, 0)

        hooks_dir = os.path.join(self.git_dir, "hooks")
        for ht in ("pre-commit", "pre-push"):
            hp = os.path.join(hooks_dir, ht)
            self.assertTrue(os.path.exists(hp))
            self.assertTrue(_is_ultron_hook(hp))
            with open(hp, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn(ULTRON_HOOK_SIGNATURE, content)

    def test_install_hooks_idempotent(self):
        """Verifies repeated installations are idempotent and do not create backups."""
        install_hooks(self.repo_dir, hook_types=["all"])
        hooks_dir = os.path.join(self.git_dir, "hooks")
        pre_commit_path = os.path.join(hooks_dir, "pre-commit")
        with open(pre_commit_path, "r", encoding="utf-8") as f:
            first_content = f.read()

        # Second install
        ret = install_hooks(self.repo_dir, hook_types=["all"])
        self.assertEqual(ret, 0)
        with open(pre_commit_path, "r", encoding="utf-8") as f:
            second_content = f.read()

        self.assertEqual(first_content, second_content)
        # Ensure zero .bak files created
        bak_files = [f for f in os.listdir(hooks_dir) if ".bak." in f]
        self.assertEqual(len(bak_files), 0)

    def test_install_hooks_backs_up_foreign_hook(self):
        """Verifies foreign hooks are backed up with microsecond timestamps."""
        hooks_dir = os.path.join(self.git_dir, "hooks")
        os.makedirs(hooks_dir, exist_ok=True)
        foreign_path = os.path.join(hooks_dir, "pre-commit")
        foreign_content = "#!/bin/sh\necho 'third-party linter'\n"
        with open(foreign_path, "w", encoding="utf-8") as f:
            f.write(foreign_content)

        ret = install_hooks(self.repo_dir, hook_types=["pre-commit"])
        self.assertEqual(ret, 0)

        # Confirm new hook is Ultron managed
        self.assertTrue(_is_ultron_hook(foreign_path))

        # Confirm backup created with original content
        bak_files = [f for f in os.listdir(hooks_dir) if f.startswith("pre-commit.bak.")]
        self.assertEqual(len(bak_files), 1)
        bak_full = os.path.join(hooks_dir, bak_files[0])
        with open(bak_full, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), foreign_content)

    def test_uninstall_hooks_refuses_foreign(self):
        """Verifies uninstall refuses to delete non-Ultron hooks."""
        hooks_dir = os.path.join(self.git_dir, "hooks")
        os.makedirs(hooks_dir, exist_ok=True)
        foreign_path = os.path.join(hooks_dir, "pre-commit")
        foreign_content = "#!/bin/sh\necho 'husky hook'\n"
        with open(foreign_path, "w", encoding="utf-8") as f:
            f.write(foreign_content)

        ret = uninstall_hooks(self.repo_dir, hook_types=["pre-commit"])
        self.assertEqual(ret, 1)

        # Ensure file was not deleted
        self.assertTrue(os.path.exists(foreign_path))
        with open(foreign_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), foreign_content)

    def test_uninstall_hooks_restores_backup(self):
        """Verifies uninstall restores latest foreign hook backup if present."""
        hooks_dir = os.path.join(self.git_dir, "hooks")
        os.makedirs(hooks_dir, exist_ok=True)
        hook_path = os.path.join(hooks_dir, "pre-commit")

        # Create foreign hook then install Ultron hook (which creates backup)
        foreign_content = "#!/bin/sh\necho 'custom gate'\n"
        with open(hook_path, "w", encoding="utf-8") as f:
            f.write(foreign_content)

        install_hooks(self.repo_dir, hook_types=["pre-commit"])
        self.assertTrue(_is_ultron_hook(hook_path))

        # Now uninstall
        ret = uninstall_hooks(self.repo_dir, hook_types=["pre-commit"])
        self.assertEqual(ret, 0)

        # Hook path exists and content is the original foreign content
        self.assertTrue(os.path.exists(hook_path))
        with open(hook_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), foreign_content)

    def test_get_hook_status_reporting(self):
        """Verifies status reporting for installed, foreign, and missing hooks."""
        hooks_dir = os.path.join(self.git_dir, "hooks")
        os.makedirs(hooks_dir, exist_ok=True)

        # Initially missing
        status1 = get_hook_status(self.repo_dir)
        self.assertTrue(status1["success"])
        self.assertEqual(status1["hooks"]["pre-commit"]["status"], "missing")
        self.assertEqual(status1["hooks"]["pre-push"]["status"], "missing")

        # Install pre-commit only
        install_hooks(self.repo_dir, hook_types=["pre-commit"])
        # Create foreign pre-push
        with open(os.path.join(hooks_dir, "pre-push"), "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\necho 'foreign'\n")

        status2 = get_hook_status(self.repo_dir)
        self.assertEqual(status2["hooks"]["pre-commit"]["status"], "installed")
        self.assertEqual(status2["hooks"]["pre-push"]["status"], "foreign")

    def test_cli_dispatch_install_uninstall_status(self):
        """Verifies run_hook_command CLI runner for install, status, and uninstall."""
        class Args:
            repo = self.repo_dir
            action = "install"
            hook_type = "all"
            base = "HEAD"
            strict = True
            fail_on_high = True
            fail_on_regression = True
            force = False
            json = True

        buf = StringIO()
        with patch("sys.stdout", buf):
            ret = run_hook_command(Args())
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue().strip())
        self.assertTrue(data["success"])

        # Check status via CLI
        Args.action = "status"
        buf_status = StringIO()
        with patch("sys.stdout", buf_status):
            ret = run_hook_command(Args())
        self.assertEqual(ret, 0)
        status_data = json.loads(buf_status.getvalue().strip())
        self.assertEqual(status_data["hooks"]["pre-commit"]["status"], "installed")

        # Uninstall via CLI
        Args.action = "uninstall"
        buf_un = StringIO()
        with patch("sys.stdout", buf_un):
            ret = run_hook_command(Args())
        self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
