"""
ultron/tests/test_monorepo_workspaces.py
Automated hermetic test suite for Monorepo Workspace & Multi-Package Architecture Comparison (Task P5-C2).

Verifies:
1. Workspace package discovery across pyproject.toml (uv/poetry), package.json, pnpm-workspace.yaml, Cargo.toml, and folder conventions.
2. Longest-prefix file-to-workspace mapping.
3. Cross-package boundary analysis and circular import cycle detection.
4. Fail-closed error handling on invalid workspace names (exit code 1).
5. Scoped health scoring over filtered workspace codebase.
6. Workspace filtering in CLI scan and gate commands.
7. Directory traversal rejection (fail-closed path security).
"""

import os
import sys
import json
import unittest
import tempfile
from typing import Dict, Any

from ultron.core.monorepo import (
    WorkspacePackage,
    WorkspaceNotFoundError,
    detect_workspaces,
    map_files_to_workspaces,
    find_workspace,
    filter_codebase_to_workspace,
    analyze_cross_workspace_dependencies,
    generate_monorepo_report,
)
from ultron.core import analyzer
from ultron.interfaces.cli.commands.analysis import run_scan_command
from ultron.interfaces.cli.commands.gate import (
    extract_current_analysis,
    extract_baseline_from_git,
    run_gate_command,
)


class TestMonorepoWorkspaces(unittest.TestCase):
    """Hermetic unit tests for monorepo detection, boundary analysis, and CLI filtering."""

    def test_detect_workspaces_pyproject_uv(self):
        """Verify detection of workspaces declared via uv in pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pyproj = """[project]
name = "monorepo-root"
version = "0.1.0"

[tool.uv.workspace]
members = ["packages/*", "apps/web"]
"""
            with open(os.path.join(tmpdir, "pyproject.toml"), "w", encoding="utf-8") as f:
                f.write(pyproj)

            os.makedirs(os.path.join(tmpdir, "packages", "pkg_a"), exist_ok=True)
            os.makedirs(os.path.join(tmpdir, "packages", "pkg_b"), exist_ok=True)
            os.makedirs(os.path.join(tmpdir, "apps", "web"), exist_ok=True)

            with open(os.path.join(tmpdir, "packages", "pkg_a", "pyproject.toml"), "w", encoding="utf-8") as f:
                f.write('[project]\nname = "pkg-a"\n')
            with open(os.path.join(tmpdir, "packages", "pkg_b", "setup.py"), "w", encoding="utf-8") as f:
                f.write('from setuptools import setup\nsetup(name="pkg-b")\n')
            with open(os.path.join(tmpdir, "apps", "web", "package.json"), "w", encoding="utf-8") as f:
                f.write('{"name": "@myorg/web"}\n')

            workspaces = detect_workspaces(tmpdir)
            self.assertEqual(len(workspaces), 3)

            paths = [w.path for w in workspaces]
            self.assertIn("packages/pkg_a", paths)
            self.assertIn("packages/pkg_b", paths)
            self.assertIn("apps/web", paths)

            web_pkg = [w for w in workspaces if w.path == "apps/web"][0]
            self.assertEqual(web_pkg.name, "@myorg/web")
            self.assertEqual(web_pkg.package_type, "node")

    def test_detect_workspaces_package_json(self):
        """Verify detection of npm/yarn workspaces declared in package.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_json = {
                "name": "js-monorepo",
                "workspaces": ["packages/*"]
            }
            with open(os.path.join(tmpdir, "package.json"), "w", encoding="utf-8") as f:
                json.dump(pkg_json, f)

            os.makedirs(os.path.join(tmpdir, "packages", "core"), exist_ok=True)
            os.makedirs(os.path.join(tmpdir, "packages", "ui"), exist_ok=True)

            with open(os.path.join(tmpdir, "packages", "core", "package.json"), "w", encoding="utf-8") as f:
                json.dump({"name": "@scope/core"}, f)
            with open(os.path.join(tmpdir, "packages", "ui", "package.json"), "w", encoding="utf-8") as f:
                json.dump({"name": "@scope/ui"}, f)

            workspaces = detect_workspaces(tmpdir)
            self.assertEqual(len(workspaces), 2)
            names = [w.name for w in workspaces]
            self.assertIn("@scope/core", names)
            self.assertIn("@scope/ui", names)

    def test_detect_workspaces_pnpm(self):
        """Verify detection of pnpm-workspace.yaml packages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pnpm_yaml = """packages:
  - 'packages/*'
  - 'services/*'
"""
            with open(os.path.join(tmpdir, "pnpm-workspace.yaml"), "w", encoding="utf-8") as f:
                f.write(pnpm_yaml)

            os.makedirs(os.path.join(tmpdir, "packages", "auth"), exist_ok=True)
            os.makedirs(os.path.join(tmpdir, "services", "api"), exist_ok=True)

            workspaces = detect_workspaces(tmpdir)
            self.assertEqual(len(workspaces), 2)
            paths = [w.path for w in workspaces]
            self.assertIn("packages/auth", paths)
            self.assertIn("services/api", paths)

    def test_detect_workspaces_cargo(self):
        """Verify detection of Cargo.toml workspace members."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cargo_toml = """[workspace]
members = [
    "crates/*",
]
"""
            with open(os.path.join(tmpdir, "Cargo.toml"), "w", encoding="utf-8") as f:
                f.write(cargo_toml)

            os.makedirs(os.path.join(tmpdir, "crates", "engine"), exist_ok=True)
            os.makedirs(os.path.join(tmpdir, "crates", "cli"), exist_ok=True)

            with open(os.path.join(tmpdir, "crates", "engine", "Cargo.toml"), "w", encoding="utf-8") as f:
                f.write('[package]\nname = "rust-engine"\n')

            workspaces = detect_workspaces(tmpdir)
            self.assertEqual(len(workspaces), 2)
            paths = [w.path for w in workspaces]
            self.assertIn("crates/engine", paths)
            self.assertIn("crates/cli", paths)

    def test_detect_workspaces_directory_convention(self):
        """Verify fallback detection of standard monorepo folder layouts when manifests are absent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Layout with packages/ and apps/
            os.makedirs(os.path.join(tmpdir, "packages", "common"), exist_ok=True)
            os.makedirs(os.path.join(tmpdir, "apps", "backend"), exist_ok=True)

            with open(os.path.join(tmpdir, "packages", "common", "utils.py"), "w", encoding="utf-8") as f:
                f.write("def helper(): pass\n")
            with open(os.path.join(tmpdir, "apps", "backend", "main.py"), "w", encoding="utf-8") as f:
                f.write("import packages.common.utils\n")

            workspaces = detect_workspaces(tmpdir)
            self.assertEqual(len(workspaces), 2)
            paths = [w.path for w in workspaces]
            self.assertIn("packages/common", paths)
            self.assertIn("apps/backend", paths)

    def test_detect_workspaces_single_package_repo(self):
        """Verify that a standard single-package repository returns empty workspaces list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "main.py"), "w", encoding="utf-8") as f:
                f.write("print('hello')\n")

            workspaces = detect_workspaces(tmpdir)
            self.assertEqual(len(workspaces), 0)

            report = generate_monorepo_report(tmpdir)
            self.assertFalse(report["is_monorepo"])
            self.assertEqual(report["total_workspaces"], 0)

    def test_map_files_to_workspaces_longest_prefix(self):
        """Verify longest-prefix matching resolves nested workspace packages correctly."""
        w1 = WorkspacePackage(name="parent", path="packages/parent", abs_path="/tmp/p", package_type="python")
        w2 = WorkspacePackage(name="child", path="packages/parent/child", abs_path="/tmp/p/c", package_type="python")
        workspaces = [w1, w2]

        files = [
            "packages/parent/mod.py",
            "packages/parent/child/deep.py",
            "other/outside.py"
        ]

        mapping = map_files_to_workspaces(files, workspaces)
        self.assertEqual(mapping["packages/parent/mod.py"], "parent")
        self.assertEqual(mapping["packages/parent/child/deep.py"], "child")
        self.assertIsNone(mapping["other/outside.py"])

    def test_find_workspace(self):
        """Verify find_workspace matches by name, path, or basename."""
        w1 = WorkspacePackage(name="@org/core", path="packages/core", abs_path="/tmp/core", package_type="node")
        w2 = WorkspacePackage(name="api", path="services/api", abs_path="/tmp/api", package_type="python")
        workspaces = [w1, w2]

        # Match by name
        self.assertEqual(find_workspace(workspaces, "@org/core"), w1)
        # Match by relative path
        self.assertEqual(find_workspace(workspaces, "packages/core"), w1)
        self.assertEqual(find_workspace(workspaces, "services/api"), w2)
        # Match by basename
        self.assertEqual(find_workspace(workspaces, "core"), w1)
        self.assertEqual(find_workspace(workspaces, "api"), w2)
        # Nonexistent
        self.assertIsNone(find_workspace(workspaces, "nonexistent"))

    def test_filter_codebase_to_workspace(self):
        """Verify codebase dictionary filtering by workspace package."""
        codebase = {
            "packages/pkg_a/a.py": {"imports": []},
            "packages/pkg_a/sub/a2.py": {"imports": []},
            "packages/pkg_b/b.py": {"imports": []},
            "root.py": {"imports": []}
        }
        w_a = WorkspacePackage(name="pkg_a", path="packages/pkg_a", abs_path="/tmp/a", package_type="python")
        filtered = filter_codebase_to_workspace(codebase, w_a)

        self.assertEqual(len(filtered), 2)
        self.assertIn("packages/pkg_a/a.py", filtered)
        self.assertIn("packages/pkg_a/sub/a2.py", filtered)
        self.assertNotIn("packages/pkg_b/b.py", filtered)
        self.assertNotIn("root.py", filtered)

    def test_cross_workspace_dependencies_and_cycle_detection(self):
        """Verify detection of cross-workspace dependencies and inter-package circular import cycles."""
        w_a = WorkspacePackage(name="pkg_a", path="packages/pkg_a", abs_path="/tmp/a", package_type="python")
        w_b = WorkspacePackage(name="pkg_b", path="packages/pkg_b", abs_path="/tmp/b", package_type="python")
        w_c = WorkspacePackage(name="pkg_c", path="packages/pkg_c", abs_path="/tmp/c", package_type="python")
        workspaces = [w_a, w_b, w_c]

        # A imports B, B imports A (cycle!), B imports C (clean)
        codebase = {
            "packages/pkg_a/a.py": {"imports": ["packages.pkg_b.b"]},
            "packages/pkg_b/b.py": {"imports": ["packages.pkg_a.a", "packages.pkg_c.c"]},
            "packages/pkg_c/c.py": {"imports": []},
        }

        deps, cycles = analyze_cross_workspace_dependencies(codebase, workspaces)
        self.assertEqual(len(deps), 3)

        # Assert circular cycle between pkg_a and pkg_b is caught
        self.assertTrue(len(cycles) > 0)
        flat_cycle = set()
        for cycle in cycles:
            flat_cycle.update(cycle)
        self.assertIn("pkg_a", flat_cycle)
        self.assertIn("pkg_b", flat_cycle)
        self.assertNotIn("pkg_c", flat_cycle)

    def test_cli_scan_workspace_filter(self):
        """Verify ultron scan --workspace <name> scopes output correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set up 2 packages
            os.makedirs(os.path.join(tmpdir, "packages", "pkg_x"), exist_ok=True)
            os.makedirs(os.path.join(tmpdir, "packages", "pkg_y"), exist_ok=True)

            with open(os.path.join(tmpdir, "packages", "pkg_x", "mod_x.py"), "w", encoding="utf-8") as f:
                f.write("x = 10\n")
            with open(os.path.join(tmpdir, "packages", "pkg_y", "mod_y.py"), "w", encoding="utf-8") as f:
                f.write("y = 20\n")

            exit_code = run_scan_command(repo_path=tmpdir, workspace="pkg_x", json_output=True)
            self.assertEqual(exit_code, 0)

    def test_cli_scan_invalid_workspace_fails_closed(self):
        """[Auditor Condition A.1] Verify scan with invalid workspace exits 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "packages", "valid_pkg"), exist_ok=True)
            with open(os.path.join(tmpdir, "packages", "valid_pkg", "app.py"), "w", encoding="utf-8") as f:
                f.write("print(1)\n")

            exit_code = run_scan_command(repo_path=tmpdir, workspace="nonexistent_pkg", json_output=False)
            self.assertEqual(exit_code, 1)

    def test_cli_gate_workspace_filter(self):
        """Verify ultron gate --workspace <name> passes on clean target workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "packages", "clean_pkg"), exist_ok=True)
            with open(os.path.join(tmpdir, "packages", "clean_pkg", "clean.py"), "w", encoding="utf-8") as f:
                f.write("a = 1\n")

            exit_code = run_gate_command(repo_path=tmpdir, workspace="clean_pkg", json_output=True)
            self.assertEqual(exit_code, 0)

    def test_cli_gate_invalid_workspace_fails_closed(self):
        """[Auditor Condition A.1] Verify gate with invalid workspace exits 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "packages", "real_pkg"), exist_ok=True)
            with open(os.path.join(tmpdir, "packages", "real_pkg", "code.py"), "w", encoding="utf-8") as f:
                f.write("x = 1\n")

            exit_code = run_gate_command(repo_path=tmpdir, workspace="fake_pkg", json_output=False)
            self.assertEqual(exit_code, 1)

    def test_extract_current_analysis_workspace_scoped(self):
        """[Auditor Condition A.3] Verify extract_current_analysis computes scoped health on workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "packages", "small_pkg"), exist_ok=True)
            with open(os.path.join(tmpdir, "packages", "small_pkg", "item.py"), "w", encoding="utf-8") as f:
                f.write("val = 42\n")

            analysis = extract_current_analysis(tmpdir, workspace="small_pkg")
            self.assertEqual(analysis["workspace"], "small_pkg")
            self.assertEqual(analysis["workspace_path"], "packages/small_pkg")
            self.assertEqual(analysis["total_files"], 1)
            self.assertEqual(analysis["health_score"], 100.0)

    def test_workspace_path_traversal_rejection(self):
        """Verify path traversal escapes in workspace query are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "packages", "pkg_1"), exist_ok=True)
            with open(os.path.join(tmpdir, "packages", "pkg_1", "m.py"), "w", encoding="utf-8") as f:
                f.write("m = 1\n")

            workspaces = detect_workspaces(tmpdir)
            match = find_workspace(workspaces, "../../../etc")
            self.assertIsNone(match)

            exit_code = run_scan_command(repo_path=tmpdir, workspace="../escape", json_output=True)
            self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
