"""
Test P3-E1 — Path-Security Adversarial Test Suite.

Validates Fail-Closed Strict Rejection policy across all filesystem-touching
endpoints: browse_folder, list-dirs, get-file, save-file, analyze, v1/analyze.

Each test is deterministic and does NOT use @unittest.skip or self.skipTest().
Symlink tests fall back to unittest.mock.patch when OS privileges are unavailable.
"""

import io
import json
import os
import tempfile
import unittest
from unittest import mock

from ultron.interfaces.server import UltronAPIHandler
from ultron.interfaces.api.browse_folder import select_folder_dialog, WINDOWS_RESERVED_NAMES


class TestPathSecurity(unittest.TestCase):
    """Adversarial path-safety tests for Fail-Closed Strict Rejection policy."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.repo_path = cls.temp_dir.name
        cls.file_main = os.path.join(cls.repo_path, "main.py")
        with open(cls.file_main, "w", encoding="utf-8") as f:
            f.write("def run():\n    return 42\n")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

    def _create_handler(self, path, payload=None, method="POST"):
        """Reusable mock handler factory (mirrors test_security_and_migration)."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.command = method
        handler.path = path
        handler.wfile = io.BytesIO()
        handler.headers = {}

        if payload is not None:
            raw_body = json.dumps(payload).encode("utf-8")
            handler.rfile = io.BytesIO(raw_body)
            handler.headers["Content-Length"] = str(len(raw_body))
        else:
            handler.rfile = io.BytesIO(b"")
            handler.headers["Content-Length"] = "0"

        handler.send_response = lambda code: setattr(handler, "last_code", code)
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.get_repo_root_path = lambda: self.repo_path
        return handler

    # ── browse_folder tests ──────────────────────────────────────────

    def test_browse_folder_null_byte_rejection(self):
        """Null bytes in initial_dir return explicit error without crashing."""
        result = select_folder_dialog(initial_dir="/tmp/repo\0injected", headless=True)
        self.assertTrue(result["cancelled"])
        self.assertIn("null byte", result.get("error", "").lower())

    def test_browse_folder_allowed_root_traversal_rejection(self):
        """Traversal outside allowed_root is rejected."""
        nested = os.path.join(self.repo_path, "sub", "deep")
        os.makedirs(nested, exist_ok=True)
        escape_path = os.path.join(nested, "..", "..", "..", "..")
        result = select_folder_dialog(
            initial_dir=escape_path,
            headless=True,
            allowed_root=self.repo_path
        )
        self.assertTrue(result["cancelled"])
        self.assertIn("outside allowed root", result.get("error", "").lower())

    def test_browse_folder_allowed_root_valid_nested(self):
        """Legitimate nested subdirectory within allowed_root succeeds."""
        nested = os.path.join(self.repo_path, "sub")
        os.makedirs(nested, exist_ok=True)
        result = select_folder_dialog(
            initial_dir=nested,
            headless=True,
            allowed_root=self.repo_path
        )
        self.assertFalse(result["cancelled"])
        self.assertTrue(result["path"])

    # ── list-dirs tests ──────────────────────────────────────────────

    def test_list_dirs_null_byte_rejection(self):
        """GET /api/list-dirs with null byte in path returns HTTP 400."""
        handler = self._create_handler("/api/list-dirs", method="GET")
        handler.get_query_data = lambda: {"path": "/tmp/repo\0evil"}
        handler.handle_list_dirs()
        res = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertIn("null byte", res.get("error", "").lower())

    def test_list_dirs_nonexistent_directory_rejection(self):
        """GET /api/list-dirs with nonexistent path returns HTTP 400."""
        handler = self._create_handler("/api/list-dirs", method="GET")
        handler.get_query_data = lambda: {"path": "/nonexistent_path_abc_xyz_999"}
        handler.handle_list_dirs()
        res = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertIn("error", res)

    # ── get-file / save-file tests ───────────────────────────────────

    def test_get_file_traversal_escape_rejection(self):
        """POST /api/get-file with ../../../etc/passwd returns HTTP 400."""
        handler = self._create_handler("/api/get-file", {
            "repo": self.repo_path,
            "file": "../../../etc/passwd"
        })
        handler.handle_get_file()
        res = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertIn("error", res)

    def test_save_file_traversal_escape_rejection(self):
        """POST /api/save-file with ../../../escaped.txt returns HTTP 400."""
        handler = self._create_handler("/api/save-file", {
            "repo": self.repo_path,
            "file": "../../../escaped.txt",
            "content": "pwned"
        })
        handler.handle_save_file()
        res = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertIn("error", res)
        # Verify escaped file was NOT created
        escaped = os.path.join(self.repo_path, "..", "..", "..", "escaped.txt")
        self.assertFalse(os.path.exists(os.path.realpath(escaped)))

    # ── analyze tests ────────────────────────────────────────────────

    def test_analyze_root_filesystem_rejection(self):
        """POST /api/analyze targeting system root returns HTTP 400."""
        root = os.path.abspath(os.sep)
        handler = self._create_handler("/api/analyze", {"repo": root})
        handler.handle_analyze()
        res = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res.get("status"), "error")
        self.assertIn("prohibited", res.get("message", "").lower())

    def test_analyze_null_byte_rejection(self):
        """POST /api/analyze with null bytes in repo returns HTTP 400."""
        handler = self._create_handler("/api/analyze", {"repo": "/tmp/repo\0evil"})
        handler.handle_analyze()
        res = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res.get("status"), "error")
        self.assertIn("null byte", res.get("error", "").lower())

    # ── symlink escape test ──────────────────────────────────────────

    def test_symlink_escape_rejection(self):
        """
        Symlink pointing outside sandbox is rejected by get-file/save-file.
        Falls back to mock.patch if OS denies os.symlink (Windows without
        SeCreateSymbolicLinkPrivilege). Does NOT use unittest.skip.
        """
        outside_dir = tempfile.mkdtemp()
        secret_file = os.path.join(outside_dir, "secret.txt")
        with open(secret_file, "w", encoding="utf-8") as f:
            f.write("TOP SECRET")

        symlink_name = "escape_link"
        symlink_path = os.path.join(self.repo_path, symlink_name)

        try:
            os.symlink(outside_dir, symlink_path)
            real_symlink = True
        except (OSError, NotImplementedError):
            real_symlink = False

        if real_symlink:
            # Real symlink test — realpath resolves outside repo boundary
            handler = self._create_handler("/api/get-file", {
                "repo": self.repo_path,
                "file": os.path.join(symlink_name, "secret.txt")
            })
            handler.handle_get_file()
            res = json.loads(handler.wfile.getvalue().decode("utf-8"))
            self.assertIn("error", res)
            self.assertEqual(getattr(handler, "last_code", None), 400)
            # Cleanup
            try:
                os.remove(symlink_path)
            except Exception:
                pass
        else:
            # Mock fallback — simulate realpath resolving outside boundary and execute handler
            fake_resolved = os.path.join(outside_dir, "secret.txt")
            orig_realpath = os.path.realpath

            def mock_realpath(p):
                if symlink_name in str(p):
                    return fake_resolved
                return orig_realpath(p)

            with mock.patch("os.path.realpath", side_effect=mock_realpath):
                handler = self._create_handler("/api/get-file", {
                    "repo": self.repo_path,
                    "file": os.path.join(symlink_name, "secret.txt")
                })
                handler.handle_get_file()
                res = json.loads(handler.wfile.getvalue().decode("utf-8"))
                self.assertIn("error", res)
                self.assertEqual(getattr(handler, "last_code", None), 400)

        # Cleanup outside dir
        try:
            os.remove(secret_file)
            os.rmdir(outside_dir)
        except Exception:
            pass

    # ── v1/analyze tests ─────────────────────────────────────────────

    def test_v1_analyze_null_byte_rejection(self):
        """POST /api/v1/analyze with null bytes in repo returns HTTP 400."""
        handler = self._create_handler("/api/v1/analyze", {"repo": "/tmp/repo\0evil"})
        handler.handle_v1_analyze()
        res = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertEqual(getattr(handler, "last_code", None), 400)
        self.assertIn("null byte", res.get("message", "").lower())

    def test_v1_analyze_reserved_device_name_rejection(self):
        """POST /api/v1/analyze targeting Windows reserved device name returns HTTP 400."""
        handler = self._create_handler("/api/v1/analyze", {"repo": "CON"})
        handler.handle_v1_analyze()
        res = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertEqual(getattr(handler, "last_code", None), 400)
        self.assertIn("reserved device name", res.get("message", "").lower())

    def test_v1_analyze_root_filesystem_rejection(self):
        """POST /api/v1/analyze targeting system root returns HTTP 400."""
        root = os.path.abspath(os.sep)
        handler = self._create_handler("/api/v1/analyze", {"repo": root})
        handler.handle_v1_analyze()
        res = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertEqual(getattr(handler, "last_code", None), 400)
        self.assertIn("prohibited", res.get("message", "").lower())

    def test_v1_analyze_module_delegate_null_byte_rejection(self):
        """Module-level handle_v1_analyze delegate rejects null bytes with HTTP 400."""
        from ultron.interfaces.api.routes.analysis_routes import handle_v1_analyze as delegate_v1_analyze
        handler = self._create_handler("/api/v1/analyze", {"repo": "/tmp/repo\0evil"})
        delegate_v1_analyze(handler)
        res = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertEqual(getattr(handler, "last_code", None), 400)
        self.assertIn("null byte", res.get("message", "").lower())

    def test_analyze_reserved_device_rejection(self):
        """POST /api/analyze targeting Windows reserved device name returns HTTP 400."""
        handler = self._create_handler("/api/analyze", {"repo": "CON"})
        handler.handle_analyze()
        res = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res.get("status"), "error")
        self.assertIn("reserved device name", res.get("error", "").lower())

    # ── save-file additional security tests ──────────────────────────

    def test_save_file_reserved_device_rejection(self):
        """POST /api/save-file targeting CON returns HTTP 400."""
        handler = self._create_handler("/api/save-file", {
            "repo": self.repo_path,
            "file": "CON",
            "content": "payload"
        })
        handler.handle_save_file()
        res = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertIn("reserved device name", res.get("error", "").lower())
        self.assertEqual(getattr(handler, "last_code", None), 400)

    def test_save_file_directory_target_rejection(self):
        """POST /api/save-file targeting an existing subdirectory returns HTTP 400."""
        sub_dir = os.path.join(self.repo_path, "sub_folder")
        os.makedirs(sub_dir, exist_ok=True)
        handler = self._create_handler("/api/save-file", {
            "repo": self.repo_path,
            "file": "sub_folder",
            "content": "payload"
        })
        handler.handle_save_file()
        res = json.loads(handler.wfile.getvalue().decode("utf-8"))
        self.assertIn("error", res)
        self.assertEqual(getattr(handler, "last_code", None), 400)

    # ── Windows reserved device names test ───────────────────────────

    def test_windows_reserved_device_names_rejection(self):
        """Attempts to target CON, PRN, AUX, NUL return rejection."""
        for name in ("CON", "PRN", "AUX", "NUL"):
            result = select_folder_dialog(initial_dir=name, headless=True)
            self.assertTrue(result["cancelled"], f"{name} should be rejected")
            self.assertIn("reserved device name", result.get("error", "").lower(),
                          f"{name} should mention reserved device name")

    def test_windows_reserved_device_colon_rejection(self):
        """Attempts to target CON: or NUL: with trailing colon return rejection."""
        for name in ("CON:", "NUL:"):
            result = select_folder_dialog(initial_dir=name, headless=True)
            self.assertTrue(result["cancelled"], f"{name} should be rejected")
            self.assertIn("reserved device name", result.get("error", "").lower())


if __name__ == "__main__":
    unittest.main()
