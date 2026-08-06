import os
import io
import json
import time
import tempfile
import unittest

from ultron.interfaces.server import UltronAPIHandler

class TestEnvironmentHealth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.repo_path = cls.temp_dir.name

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_health_endpoint_diagnostics(self):
        """Verify GET /api/v1/health returns complete diagnostics without side effects."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/v1/health"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.get_repo_root_path = lambda: self.repo_path

        start_t = time.time()
        handler.handle_v1_health()
        duration_ms = (time.time() - start_t) * 1000

        # Must execute in < 50ms (lightweight check)
        self.assertLess(duration_ms, 50.0)

        output = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(output)
        
        self.assertEqual(data["status"], "healthy")
        self.assertIn("environment", data)
        self.assertIn("rkm_database", data)
        self.assertIn("modules", data)
        self.assertIn("active_job", data)

        env = data["environment"]
        self.assertIn("python_version", env)
        self.assertIn("platform", env)

    def test_static_asset_charset_and_cache_headers(self):
        """Verify static files are served with charset=utf-8 and Cache-Control: no-cache headers."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/index.js"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        
        headers_sent = {}
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: headers_sent.update({k: v})
        handler.end_headers = lambda: None

        handler.do_GET()
        
        self.assertIn("Content-Type", headers_sent)
        self.assertIn("charset=utf-8", headers_sent["Content-Type"])
        self.assertIn("Cache-Control", headers_sent)
        self.assertEqual(headers_sent["Cache-Control"], "no-cache, must-revalidate")

if __name__ == "__main__":
    unittest.main()
