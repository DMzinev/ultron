"""
ultron.tests.test_workspace_manager
Unit test suite asserting multi-repository workspace management and monorepo subpackage discovery.
"""

import os
import shutil
import tempfile
import unittest
from ultron.core.workspace_manager import WorkspaceManager, norm_path


class TestWorkspaceManager(unittest.TestCase):
    """Unit tests for deterministic WorkspaceManager."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_norm_path(self):
        """Asserts path normalization to POSIX forward slashes."""
        self.assertEqual(norm_path("ultron\\core\\workspace_manager.py"), "ultron/core/workspace_manager.py")
        self.assertEqual(norm_path(None), "")

    def test_add_workspace_and_auto_activate(self):
        """Asserts adding a workspace registers and auto-activates the first entry."""
        mgr = WorkspaceManager()
        ws = mgr.add_workspace(self.temp_dir, name="TempRepo")
        self.assertEqual(ws["name"], "TempRepo")
        self.assertTrue(ws["active"])
        self.assertEqual(mgr.get_active_workspace()["id"], ws["id"])

    def test_set_active_workspace_and_switching(self):
        """Asserts switching active workspace activates the target and deactivates others."""
        dir2 = tempfile.mkdtemp()
        try:
            mgr = WorkspaceManager()
            ws1 = mgr.add_workspace(self.temp_dir, name="Repo1")
            ws2 = mgr.add_workspace(dir2, name="Repo2")

            self.assertEqual(mgr.get_active_workspace()["id"], ws1["id"])

            mgr.set_active_workspace(ws2["id"])
            self.assertEqual(mgr.get_active_workspace()["id"], ws2["id"])

            all_ws = mgr.list_workspaces()
            self.assertEqual(len(all_ws), 2)
            active_list = [w for w in all_ws if w["active"]]
            self.assertEqual(len(active_list), 1)
            self.assertEqual(active_list[0]["id"], ws2["id"])
        finally:
            shutil.rmtree(dir2, ignore_errors=True)

    def test_invalid_path_raises_file_not_found(self):
        """Asserts non-existent directory raises FileNotFoundError."""
        mgr = WorkspaceManager()
        with self.assertRaises(FileNotFoundError):
            mgr.add_workspace(os.path.join(self.temp_dir, "non_existent_folder_xyz"))

        with self.assertRaises(ValueError):
            mgr.add_workspace("")

    def test_discover_monorepo_subpackages(self):
        """Asserts automatic discovery of nested subpackages with manifests."""
        # Create nested packages
        pkg_a = os.path.join(self.temp_dir, "packages", "service-a")
        pkg_b = os.path.join(self.temp_dir, "packages", "service-b")
        os.makedirs(pkg_a, exist_ok=True)
        os.makedirs(pkg_b, exist_ok=True)

        with open(os.path.join(pkg_a, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write("[project]\nname = 'service-a'\n")

        with open(os.path.join(pkg_b, "package.json"), "w", encoding="utf-8") as f:
            f.write('{"name": "service-b"}\n')

        mgr = WorkspaceManager()
        subpackages = mgr.discover_monorepo_subpackages(self.temp_dir)
        self.assertEqual(len(subpackages), 2)
        pkg_names = [p["name"] for p in subpackages]
        self.assertIn("service-a", pkg_names)
        self.assertIn("service-b", pkg_names)

    def test_deterministic_workspace_id_generation(self):
        """Asserts identical path produces identical deterministic workspace ID."""
        mgr = WorkspaceManager()
        id1 = mgr._generate_workspace_id(self.temp_dir)
        id2 = mgr._generate_workspace_id(self.temp_dir)
        self.assertEqual(id1, id2)


if __name__ == "__main__":
    unittest.main()
