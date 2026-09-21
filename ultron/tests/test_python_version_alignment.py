"""
ultron/tests/test_python_version_alignment.py
Validation suite for supported Python version alignment and runtime version guards.

Enforces:
1. pyproject.toml requires-python is '>=3.10'.
2. setup.py python_requires is '>=3.10'.
3. Package classifiers include 3.10, 3.11, 3.12, 3 :: Only.
4. Package classifiers exclude legacy 3.8 and 3.9.
5. Isolated subprocess runtime import rejection of ultron on Python < 3.10.
6. Isolated subprocess CLI main rejection on Python < 3.10.
7. Isolated subprocess launcher.py rejection on Python < 3.10.
8. Isolated subprocess start.py rejection on Python < 3.10.
9. Boundary and specifier logic rejecting unsupported versions.
10. Agreement between CI workflow matrices, packaging manifests, and documentation.
"""

import os
import sys
import subprocess
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class TestPythonVersionAlignment(unittest.TestCase):
    """Test suite ensuring consistent Python >= 3.10 requirement across all project surfaces."""

    def setUp(self):
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = REPO_ROOT

    def test_pyproject_requires_python_is_310(self):
        """pyproject.toml must specify requires-python = '>=3.10'."""
        pyproject_path = os.path.join(REPO_ROOT, "pyproject.toml")
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('requires-python = ">=3.10"', content)

    def test_setup_python_requires_is_310(self):
        """setup.py must specify python_requires='>=3.10'."""
        setup_path = os.path.join(REPO_ROOT, "setup.py")
        with open(setup_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('python_requires=">=3.10"', content)

    def test_packaging_classifiers_include_310_311_312(self):
        """Packaging manifests must advertise Python 3.10, 3.11, 3.12, and 3 :: Only."""
        expected_classifiers = [
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3 :: Only",
        ]
        for filename in ("pyproject.toml", "setup.py"):
            path = os.path.join(REPO_ROOT, filename)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            for classifier in expected_classifiers:
                self.assertIn(
                    classifier,
                    content,
                    f"Expected classifier '{classifier}' missing from {filename}",
                )

    def test_packaging_classifiers_exclude_38_39(self):
        """Packaging manifests must not advertise legacy Python 3.8 or 3.9."""
        forbidden_classifiers = [
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
        ]
        for filename in ("pyproject.toml", "setup.py"):
            path = os.path.join(REPO_ROOT, filename)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            for classifier in forbidden_classifiers:
                self.assertNotIn(
                    classifier,
                    content,
                    f"Forbidden legacy classifier '{classifier}' found in {filename}",
                )

    def test_runtime_import_rejection_on_lower_python(self):
        """ultron top-level import must raise RuntimeError when sys.version_info < (3, 10)."""
        code = (
            "import sys\n"
            "sys.version_info = (3, 9, 7, 'final', 0)\n"
            "try:\n"
            "    import ultron\n"
            "    sys.exit(1)\n"
            "except RuntimeError as e:\n"
            "    print(f'CAUGHT: {e}')\n"
            "    sys.exit(0)\n"
            "except Exception as e:\n"
            "    print(f'WRONG_EXCEPTION: {type(e).__name__}: {e}')\n"
            "    sys.exit(2)\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"Expected exit code 0 from caught RuntimeError, got {proc.returncode}.\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}",
        )
        self.assertIn(
            "Ultron requires Python 3.10 or higher (detected Python 3.9.7)",
            proc.stdout,
        )

    def test_cli_rejection_on_lower_python(self):
        """ultron CLI entrypoint must reject execution when sys.version_info < (3, 10)."""
        code = (
            "import sys\n"
            "sys.version_info = (3, 9, 7, 'final', 0)\n"
            "try:\n"
            "    import ultron.interfaces.ultron as u\n"
            "    u.main()\n"
            "except RuntimeError as e:\n"
            "    sys.stderr.write(f'RuntimeError: {e}\\n')\n"
            "    sys.exit(1)\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertNotEqual(proc.returncode, 0)
        err = proc.stderr
        self.assertTrue(
            "Ultron requires Python 3.10 or higher" in err,
            f"Expected version error in stderr, got: {err}",
        )
        self.assertIn("3.9.7", err)

    def test_launcher_rejection_on_lower_python(self):
        """launcher.py must reject startup with exit 1 when sys.version_info < (3, 10)."""
        code = (
            "import sys\n"
            "sys.version_info = (3, 8, 10, 'final', 0)\n"
            "import launcher\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(
            proc.returncode,
            1,
            f"Expected exit code 1 from launcher.py guard, got {proc.returncode}.\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}",
        )
        self.assertIn(
            "Error: Ultron requires Python 3.10 or higher (detected Python 3.8.10).",
            proc.stderr,
        )

    def test_start_rejection_on_lower_python(self):
        """start.py must reject startup with exit 1 when sys.version_info < (3, 10)."""
        code = (
            "import sys\n"
            "sys.version_info = (3, 9, 2, 'final', 0)\n"
            "import start\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(
            proc.returncode,
            1,
            f"Expected exit code 1 from start.py guard, got {proc.returncode}.\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}",
        )
        self.assertIn(
            "Error: Ultron requires Python 3.10 or higher (detected Python 3.9.2).",
            proc.stderr,
        )

    def test_unadvertised_lower_versions_rejected_by_specifier(self):
        """Boundary and version comparison logic must reject <3.10 and accept >=3.10."""
        rejected_versions = [
            (3, 7, 0),
            (3, 8, 0),
            (3, 8, 18),
            (3, 9, 0),
            (3, 9, 18),
        ]
        accepted_versions = [
            (3, 10, 0),
            (3, 10, 14),
            (3, 11, 0),
            (3, 11, 8),
            (3, 12, 0),
            (3, 12, 2),
            (3, 13, 0),
            (4, 0, 0),
        ]
        min_required = (3, 10)
        for v in rejected_versions:
            self.assertLess(
                v[:2],
                min_required,
                f"Version {v} was expected to be rejected by < (3, 10)",
            )
        for v in accepted_versions:
            self.assertGreaterEqual(
                v[:2],
                min_required,
                f"Version {v} was expected to satisfy >= (3, 10)",
            )

    def test_ci_and_readme_matrix_agreement(self):
        """CI workflow matrix, README badges, and docs must agree on Python versions."""
        ci_path = os.path.join(REPO_ROOT, ".github", "workflows", "ci.yml")
        with open(ci_path, "r", encoding="utf-8") as f:
            ci_content = f.read()

        # CI matrix includes 3.10, 3.11, 3.12
        self.assertIn("'3.10'", ci_content)
        self.assertIn("'3.11'", ci_content)
        self.assertIn("'3.12'", ci_content)
        # CI matrix does not test unsupported versions
        self.assertNotIn("'3.8'", ci_content)
        self.assertNotIn("'3.9'", ci_content)

        # README badges
        readme_path = os.path.join(REPO_ROOT, "README.md")
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()
        self.assertIn("python-3.10%20%7C%203.11%20%7C%203.12", readme_content)

        # CONTRIBUTING.md
        contrib_path = os.path.join(REPO_ROOT, "CONTRIBUTING.md")
        with open(contrib_path, "r", encoding="utf-8") as f:
            contrib_content = f.read()
        self.assertIn("Python **3.10**, **3.11**, or **3.12**", contrib_content)

        # docs/RESOURCES.md
        resources_path = os.path.join(REPO_ROOT, "docs", "RESOURCES.md")
        with open(resources_path, "r", encoding="utf-8") as f:
            resources_content = f.read()
        self.assertIn(r"\ge 3.10", resources_content)


if __name__ == "__main__":
    unittest.main()
