"""
Test suite for Ultron version command, resolver, schema, and packaging invariants.
"""

import os
import sys
import json
import shutil
import venv
import zipfile
import tempfile
import unittest
import subprocess
from unittest.mock import patch

from ultron._version import __version__ as CANONICAL_VERSION
from ultron import get_version
from ultron.interfaces.cli.commands.version import _probe, get_version_info, run_version_command


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestVersionCommand(unittest.TestCase):
    """Hermetic unit, CLI, and integration tests for Ultron version interfaces."""

    def test_get_version_returns_string(self):
        """Verify get_version() returns a non-empty string."""
        ver = get_version()
        self.assertIsInstance(ver, str)
        self.assertTrue(len(ver) > 0)

    def test_get_version_matches_canonical_constant(self):
        """Verify get_version() matches CANONICAL_VERSION in dev tree."""
        self.assertEqual(get_version(), CANONICAL_VERSION)
        self.assertEqual(CANONICAL_VERSION, "1.5.0")

    def test_get_version_fallback_on_missing_package(self):
        """Verify get_version() falls back to __version__ when PackageNotFoundError is raised."""
        from importlib.metadata import PackageNotFoundError

        def mock_meta_version(name):
            raise PackageNotFoundError(name)

        with patch("importlib.metadata.version", side_effect=mock_meta_version):
            ver = get_version()
            self.assertEqual(ver, CANONICAL_VERSION)

    def test_cli_version_flag(self):
        """Verify 'python -m ultron --version' outputs version and exits 0."""
        proc = subprocess.run(
            [sys.executable, "-m", "ultron.interfaces.ultron", "--version"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn(f"ultron {CANONICAL_VERSION}", proc.stdout)

    def test_cli_version_subcommand(self):
        """Verify 'python -m ultron version' outputs version and exits 0."""
        proc = subprocess.run(
            [sys.executable, "-m", "ultron.interfaces.ultron", "version"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), f"ultron {CANONICAL_VERSION}")

    def test_cli_version_json_schema(self):
        """Verify 'ultron version --json' outputs compliant versioned JSON schema."""
        proc = subprocess.run(
            [sys.executable, "-m", "ultron.interfaces.ultron", "version", "--json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual(data.get("version"), CANONICAL_VERSION)
        self.assertEqual(data.get("schema_version"), "1.0.0")
        self.assertIn("python", data)
        self.assertIn("path", data)
        self.assertIsInstance(data.get("capabilities"), dict)

        caps = data["capabilities"]
        self.assertIn("radon", caps)
        self.assertIn("pystray", caps)
        self.assertIn("pillow", caps)
        self.assertIsInstance(caps["radon"], bool)
        self.assertIsInstance(caps["pystray"], bool)
        self.assertIsInstance(caps["pillow"], bool)

    def test_cli_version_help(self):
        """Verify 'ultron version --help' outputs usage help and exits 0."""
        proc = subprocess.run(
            [sys.executable, "-m", "ultron.interfaces.ultron", "version", "--help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("usage: ultron version", proc.stdout)
        self.assertIn("--json", proc.stdout)

    def test_cli_version_rejects_unknown_args(self):
        """Verify 'ultron version --bogus' fails with exit code 2."""
        proc = subprocess.run(
            [sys.executable, "-m", "ultron.interfaces.ultron", "version", "--bogus"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unrecognized arguments", proc.stderr)

    def test_probe_uses_find_spec_no_import_side_effects(self):
        """Verify _probe accurately checks availability without module import side-effects."""
        # Probe an unimported standard library module
        self.assertTrue(_probe("uuid"))
        self.assertFalse(_probe("definitely_nonexistent_bogus_package_12345"))

    def test_clean_wheel_outside_repo_execution(self):
        """
        Build wheel, install into clean isolated virtualenv outside repo,
        purge PYTHONPATH, and execute 'ultron --version' and 'ultron version --json'
        from an external working directory.
        """
        uv_bin = shutil.which("uv")
        build_dir = os.path.join(REPO_ROOT, "build")
        egg_info_dir = os.path.join(REPO_ROOT, "ultron_risk_scorer.egg-info")
        with tempfile.TemporaryDirectory(prefix="ultron_wheel_test_") as tmp_dir:
            try:
                wheel_dir = os.path.join(tmp_dir, "wheel")
                env_dir = os.path.join(tmp_dir, "venv")
                outside_workdir = os.path.join(tmp_dir, "workdir")
                os.makedirs(wheel_dir, exist_ok=True)
                os.makedirs(outside_workdir, exist_ok=True)

                # 1. Build Wheel
                if uv_bin:
                    build_cmd = [uv_bin, "build", "--wheel", "--out-dir", wheel_dir]
                else:
                    build_cmd = [
                        sys.executable, "-m", "pip", "wheel",
                        "--no-deps", "--no-build-isolation",
                        "-w", wheel_dir, ".",
                    ]

                build_proc = subprocess.run(
                    build_cmd,
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                self.assertEqual(
                    build_proc.returncode, 0,
                    f"Wheel build failed:\n{build_proc.stderr}"
                )

                whl_files = [f for f in os.listdir(wheel_dir) if f.endswith(".whl")]
                self.assertEqual(len(whl_files), 1)
                whl_path = os.path.join(wheel_dir, whl_files[0])

                # 2. Create isolated venv
                venv.create(env_dir, with_pip=True)

                # 3. Resolve executable paths cross-platform
                if sys.platform == "win32":
                    venv_python = os.path.join(env_dir, "Scripts", "python.exe")
                    venv_ultron = os.path.join(env_dir, "Scripts", "ultron.exe")
                else:
                    venv_python = os.path.join(env_dir, "bin", "python")
                    venv_ultron = os.path.join(env_dir, "bin", "ultron")

                # 4. Install wheel into venv
                if uv_bin:
                    install_cmd = [uv_bin, "pip", "install", "--python", venv_python, whl_path]
                else:
                    install_cmd = [venv_python, "-m", "pip", "install", "--no-deps", whl_path]

                install_proc = subprocess.run(
                    install_cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                self.assertEqual(
                    install_proc.returncode, 0,
                    f"Wheel installation failed:\n{install_proc.stderr}"
                )

                # 5. Purge PYTHONPATH and prepare execution environment
                clean_env = dict(os.environ)
                clean_env.pop("PYTHONPATH", None)

                # 6. Run 'ultron --version' from external cwd
                run_bin = venv_ultron if os.path.exists(venv_ultron) else venv_python
                run_args = [run_bin, "--version"] if run_bin == venv_ultron else [venv_python, "-m", "ultron.interfaces.ultron", "--version"]

                proc_ver = subprocess.run(
                    run_args,
                    cwd=outside_workdir,
                    env=clean_env,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(
                    proc_ver.returncode, 0,
                    f"External 'ultron --version' failed:\n{proc_ver.stderr}"
                )
                self.assertIn(f"ultron {CANONICAL_VERSION}", proc_ver.stdout)

                # 7. Run 'ultron version --json' from external cwd
                json_args = [run_bin, "version", "--json"] if run_bin == venv_ultron else [venv_python, "-m", "ultron.interfaces.ultron", "version", "--json"]

                proc_json = subprocess.run(
                    json_args,
                    cwd=outside_workdir,
                    env=clean_env,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(
                    proc_json.returncode, 0,
                    f"External 'ultron version --json' failed:\n{proc_json.stderr}"
                )
                json_data = json.loads(proc_json.stdout)
                self.assertEqual(json_data["version"], CANONICAL_VERSION)
                # Path must resolve to installed package in site-packages, NOT the repo root
                installed_path = os.path.normpath(json_data["path"])
                repo_norm = os.path.normpath(REPO_ROOT)
                self.assertFalse(
                    installed_path.lower().startswith(repo_norm.lower()),
                    f"Installed path {installed_path} must not be inside repo {repo_norm}"
                )
            finally:
                if os.path.exists(build_dir):
                    shutil.rmtree(build_dir, ignore_errors=True)
                if os.path.exists(egg_info_dir):
                    shutil.rmtree(egg_info_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
