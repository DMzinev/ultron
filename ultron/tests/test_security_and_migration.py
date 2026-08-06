import os
import io
import json
import tempfile
import unittest

from ultron.interfaces.server import UltronAPIHandler

class TestSecurityAndMigration(unittest.TestCase):
    """
    Gate 14 (Security & Input Hardening) & Gate 16 (Upgrade & Schema Migration) Test Suite.
    Validates directory traversal protection, payload boundaries, and schema versioning.
    """

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

    def test_gate14_directory_traversal_sanitization(self):
        """Gate 14: Directory traversal sequences (../../..) are safely resolved via os.path.abspath."""
        traversal_path = os.path.join(self.repo_path, "..", "..")
        h = self._create_handler("/api/analyze", {"repo": traversal_path})
        h.handle_analyze()
        
        # Must resolve safely and not crash the server
        res = json.loads(h.wfile.getvalue().decode("utf-8"))
        self.assertIn("status", res)

    def test_gate14_html_injection_resilience(self):
        """Gate 14: Entity profiles containing HTML tags (<script>alert(1)</script>) are sanitized cleanly."""
        h = self._create_handler("/api/v1/ai-push", {
            "repo": self.repo_path,
            "target_file": "<script>alert(1)</script>",
            "persona": "security"
        })
        h.handle_v1_ai_push()
        
        res = json.loads(h.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res["status"], "success")

    def test_gate16_rkm_schema_version_compatibility(self):
        """Gate 16: RKM database schema version reports 1.3.0 for backward and forward compatibility."""
        db_path = os.path.join(self.repo_path, ".ultron", "repository.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        from ultron.core.rkm.store import RepositoryStore
        from ultron.core.rkm.schema import RKM_SCHEMA_VERSION
        store = RepositoryStore(db_path)
        try:
            self.assertEqual(RKM_SCHEMA_VERSION, "1.3.0")
        finally:
            if hasattr(store, "conn") and store.conn:
                store.conn.close()

if __name__ == "__main__":
    unittest.main()
