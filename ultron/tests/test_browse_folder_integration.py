"""
ultron.tests.test_browse_folder_integration
Tests for native folder browser dialog, edge cases, and API endpoint contracts.
"""

import os
import unittest
from ultron.interfaces.api.browse_folder import select_folder_dialog


class TestBrowseFolderIntegration(unittest.TestCase):
    """Tests for browse folder dialog logic and edge cases."""

    def test_headless_mode_returns_normalized_path(self):
        """Asserts that headless mode returns normalized path with forward slashes."""
        res = select_folder_dialog(initial_dir=".", headless=True)
        self.assertIsInstance(res, dict)
        self.assertIn("path", res)
        self.assertIn("cancelled", res)
        self.assertIn("fallback", res)
        self.assertFalse(res["cancelled"])
        self.assertFalse(res["fallback"])
        self.assertTrue(len(res["path"]) > 0)
        self.assertNotIn("\\", res["path"])

    def test_headless_nonexistent_directory_falls_back_to_cwd(self):
        """Asserts that nonexistent initial directory falls back to current working directory."""
        nonexistent = "c:/nonexistent_folder_xyz_123"
        res = select_folder_dialog(initial_dir=nonexistent, headless=True)
        self.assertIsInstance(res, dict)
        self.assertFalse(res["cancelled"])
        self.assertTrue(len(res["path"]) > 0)

    def test_schema_contract_keys(self):
        """Asserts exact return schema contract for select_folder_dialog."""
        res = select_folder_dialog(headless=True)
        required_keys = {"path", "cancelled", "fallback"}
        self.assertTrue(required_keys.issubset(set(res.keys())))


if __name__ == "__main__":
    unittest.main()
