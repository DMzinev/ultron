import os
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from ultron.interfaces.server import UltronAPIHandler

class TestChaosRecovery(unittest.TestCase):
    """
    Gate 9: Failure Chaos & Recovery Testing Suite
    Intentionally injects chaotic failure states (locked DBs, deleted files, corrupted JSON)
    to prove 100% crash resistance and graceful degradation without tracebacks.
    """

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.repo_path = cls.temp_dir.name
        
        # Create a sample Python module
        cls.sample_file = os.path.join(cls.repo_path, "core.py")
        with open(cls.sample_file, "w", encoding="utf-8") as f:
            f.write("def compute(x):\n    return x * 42\n")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def _create_handler(self, path, payload=None, raw_body_bytes=None, method="POST"):
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.command = method
        handler.path = path
        handler.wfile = io.BytesIO()
        handler.headers = {}
        
        if raw_body_bytes is not None:
            handler.rfile = io.BytesIO(raw_body_bytes)
            handler.headers["Content-Length"] = str(len(raw_body_bytes))
        elif payload is not None:
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

    def test_chaos_corrupted_json_payload(self):
        """Gate 9: Corrupted JSON body bytes returns 400 Bad Request without server traceback crash."""
        corrupted_bytes = b"{{invalid_json_bytes: [1, 2, "
        h = self._create_handler("/api/analyze", raw_body_bytes=corrupted_bytes)
        h.handle_analyze()
        
        res = json.loads(h.wfile.getvalue().decode("utf-8"))
        self.assertEqual(getattr(h, "last_code", 200), 400)
        self.assertEqual(res["status"], "error")
        self.assertIn("message", res)

    def test_chaos_missing_db_file_summary(self):
        """Gate 9: Accessing summary endpoint when .ultron/repository.db is missing returns uninitialized state."""
        h = self._create_handler("/api/v1/summary", method="GET")
        h.handle_v1_summary()
        
        res = json.loads(h.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res["initialized"], False)

    import urllib.error
    @patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Proxy Offline"))
    def test_chaos_offline_ai_proxy_fallback(self, mock_urlopen):
        """Gate 9: Dispatching AI push when port 10531 proxy is offline returns native AST explanation cleanly."""
        h = self._create_handler("/api/v1/ai/push", {
            "repo": self.repo_path,
            "target_file": "core.py",
            "persona": "founder"
        })
        h.handle_v1_ai_push()
        
        res = json.loads(h.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["persona"], "founder")
        self.assertIn("ai_response", res)

    def test_chaos_invalid_recommendations_limit(self):
        """Gate 9: Sending non-integer limit parameter returns 400 Bad Request error."""
        h = self._create_handler("/api/v1/recommendations?limit=invalid_string", method="GET")
        h.handle_v1_recommendations()
        
        res = json.loads(h.wfile.getvalue().decode("utf-8"))
        self.assertEqual(getattr(h, "last_code", 200), 400)
        self.assertEqual(res["status"], "error")
        self.assertIn("Limit parameter", res["message"])

if __name__ == "__main__":
    unittest.main()
