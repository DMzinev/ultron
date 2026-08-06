import os
import io
import json
import tempfile
import unittest

from ultron.interfaces.server import UltronAPIHandler
from ultron.core.pipeline import orchestrator

class TestServerDashboardEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.repo_path = cls.temp_dir.name
        
        # Create a sample python file in temp repo
        cls.sample_file = os.path.join(cls.repo_path, "sample_module.py")
        with open(cls.sample_file, "w", encoding="utf-8") as f:
            f.write("def calculate(a, b):\n    if a > 0:\n        return a + b\n    return b\n")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_summary_uninitialized(self):
        """Verify GET /api/v1/summary returns uninitialized state without creating DB file."""
        empty_dir = tempfile.TemporaryDirectory()
        try:
            db_path = os.path.join(empty_dir.name, ".ultron", "repository.db")
            self.assertFalse(os.path.exists(db_path))

            # Simulate handler
            handler = UltronAPIHandler.__new__(UltronAPIHandler)
            handler.path = "/api/v1/summary"
            handler.wfile = io.BytesIO()
            handler.headers = {}
            
            responses = []
            def fake_send_response(code):
                responses.append(code)
            def fake_send_header(k, v):
                pass
            def fake_end_headers():
                pass
            
            handler.send_response = fake_send_response
            handler.send_header = fake_send_header
            handler.end_headers = fake_end_headers
            handler.get_repo_root_path = lambda: empty_dir.name

            handler.handle_v1_summary()
            
            # Verify DB was NOT created as a side effect
            self.assertFalse(os.path.exists(db_path))
            
            output = handler.wfile.getvalue().decode('utf-8')
            data = json.loads(output)
            self.assertFalse(data["initialized"])
            self.assertEqual(data["total_files"], 0)
        finally:
            empty_dir.cleanup()

    def test_summary_initialized(self):
        """Verify GET /api/v1/summary returns populated metrics when RKM DB exists."""
        # Initialize RKM run
        orchestrator.analyze_repository(self.repo_path, force=True)
        
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/v1/summary"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.get_repo_root_path = lambda: self.repo_path

        handler.handle_v1_summary()
        
        output = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(output)
        self.assertTrue(data["initialized"])
        self.assertGreaterEqual(data["total_files"], 1)

    def test_design_oracle_explain(self):
        """Verify POST /api/design-oracle action=explain constructs RiskProfile -> Decision -> Response."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/design-oracle"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        
        req_payload = {
            "repo": self.repo_path,
            "action": "explain",
            "entity_id": "sample_module.py"
        }
        handler.get_post_data = lambda: req_payload
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.get_repo_root_path = lambda: self.repo_path

        handler.handle_design_oracle()
        
        output = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(output)
        if "status" not in data:
            print("DESIGN ORACLE OUTPUT:", data)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["entity_id"], "sample_module.py")
        self.assertIn("decision", data)
        self.assertIn("communication", data)
        self.assertIn("developer", data["communication"])
        self.assertIn("manager", data["communication"])
        self.assertIn("founder", data["communication"])
        self.assertIn("security", data["communication"])
        self.assertIn("ai_agent", data["communication"])
        self.assertIn("trust_chain", data)
        self.assertIn("repair_simulation", data)

    def test_api_v1_ai_push_success_and_fallback(self):
        """Verify POST /api/v1/ai-push handles dispatch cleanly with native fallback on proxy offline."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/v1/ai-push"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        
        req_payload = {
            "repo": self.repo_path,
            "target_file": "sample_module.py",
            "persona": "developer"
        }
        handler.get_post_data = lambda: req_payload
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.get_repo_root_path = lambda: self.repo_path

        handler.handle_v1_ai_push()
        
        output = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(output)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["entity_id"], "sample_module.py")
        self.assertEqual(data["persona"], "developer")
        self.assertIn("ai_response", data)
        self.assertIn("source", data)

    def test_health_check_endpoint(self):
        """Verify GET /api/v1/health returns healthy status schema for sidebar indicator."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/v1/health"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.get_repo_root_path = lambda: self.repo_path

        handler.handle_v1_health()

        output = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(output)
        self.assertEqual(data["status"], "healthy")
        self.assertIn("environment", data)
        self.assertIn("rkm_database", data)

    def test_api_v1_recommendations_uninitialized(self):
        """Verify GET /api/v1/recommendations returns complete fallback schema on uninitialized DB."""
        empty_dir = tempfile.TemporaryDirectory()
        try:
            handler = UltronAPIHandler.__new__(UltronAPIHandler)
            handler.path = "/api/v1/recommendations?limit=10"
            handler.wfile = io.BytesIO()
            handler.headers = {}
            handler.send_response = lambda code: None
            handler.send_header = lambda k, v: None
            handler.end_headers = lambda: None
            handler.get_repo_root_path = lambda: empty_dir.name

            handler.handle_v1_recommendations()

            output = handler.wfile.getvalue().decode('utf-8')
            data = json.loads(output)
            self.assertEqual(data["source"], "fallback")
            self.assertEqual(data["fallback_reason"], "db_uninitialized")
            self.assertEqual(data["recommendations"], [])
        finally:
            empty_dir.cleanup()

    def test_api_v1_recommendations_invalid_limit(self):
        """Verify GET /api/v1/recommendations returns 400 Bad Request on invalid limit."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/v1/recommendations?limit=invalid"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        
        status_codes = []
        handler.send_response = lambda code: status_codes.append(code)
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None

        handler.handle_v1_recommendations()
        self.assertIn(400, status_codes)

    def test_api_v1_export_brief_success(self):
        """Verify POST /api/v1/export-brief renders from canonical brief for all 4 targets."""
        for fmt in ["claude", "codex", "antigravity", "json"]:
            handler = UltronAPIHandler.__new__(UltronAPIHandler)
            handler.path = "/api/v1/export-brief"
            handler.wfile = io.BytesIO()
            handler.headers = {}
            handler.get_post_data = lambda f=fmt: {"format": f}
            handler.send_response = lambda code: None
            handler.send_header = lambda k, v: None
            handler.end_headers = lambda: None
            handler.get_repo_root_path = lambda: self.repo_path

            handler.handle_v1_export_brief()

            output = handler.wfile.getvalue().decode('utf-8')
            data = json.loads(output)
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["format"], fmt)
            if fmt == "json":
                self.assertIn("brief", data)
            else:
                self.assertIn("content", data)

    def test_api_v1_export_brief_invalid_format(self):
        """Verify POST /api/v1/export-brief returns 400 Bad Request on unsupported format."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/v1/export-brief"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        handler.get_post_data = lambda: {"format": "unsupported_format"}
        
        status_codes = []
        handler.send_response = lambda code: status_codes.append(code)
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None

        handler.handle_v1_export_brief()
        self.assertIn(400, status_codes)

if __name__ == "__main__":
    unittest.main()
