import os
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from ultron.interfaces.api.browse_folder import select_folder_dialog
from ultron.interfaces.server import UltronAPIHandler
from ultron.core.pipeline import orchestrator

class TestAIHandoffAndFolderPicker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.repo_path = cls.temp_dir.name
        
        # Create a sample python file in temp repo
        cls.sample_file = os.path.join(cls.repo_path, "main.py")
        with open(cls.sample_file, "w", encoding="utf-8") as f:
            f.write("def run():\n    print('Hello Ultron')\n")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    @patch("tkinter.filedialog.askdirectory", return_value="")
    def test_select_folder_dialog_headless_safety(self, mock_ask):
        """Verify select_folder_dialog returns fallback=True cleanly when GUI is unavailable or in test runner."""
        res = select_folder_dialog(self.repo_path)
        self.assertIsInstance(res, dict)
        self.assertIn("cancelled", res)
        self.assertIn("fallback", res)
        self.assertIn("path", res)

    def test_context_brief_rkm_first(self):
        """Verify POST /api/v1/context-brief uses RKM DB first and renders Claude, Codex, and Antigravity outputs."""
        # Initialize RKM run
        orchestrator.analyze_repository(self.repo_path, force=True)
        
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/v1/context-brief"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        
        req_payload = {
            "repo": self.repo_path,
            "target_file": "main.py"
        }
        handler.get_post_data = lambda: req_payload
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.get_repo_root_path = lambda: self.repo_path

        handler.handle_v1_context_brief()
        
        output = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(output)
        
        self.assertEqual(data["status"], "success")
        self.assertIn("canonical_brief", data)
        self.assertIn("handoff", data)
        
        handoff = data["handoff"]
        self.assertIn("claude", handoff)
        self.assertIn("codex", handoff)
        self.assertIn("antigravity", handoff)
        
        # Verify Antigravity output contains file:// reference
        self.assertIn("file:///", handoff["antigravity"])
        self.assertIn("claude -p", handoff["claude"])

    def test_handle_analyze_invalid_directory(self):
        """Verify handle_analyze returns HTTP 400 with clear diagnostic message on invalid folder."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/analyze"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        
        req_payload = {
            "repo": "C:/invalid_nonexistent_directory_xyz"
        }
        handler.get_post_data = lambda: req_payload
        
        responses = []
        handler.send_response = lambda code: responses.append(code)
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.send_json_response = lambda code, body: handler.wfile.write(json.dumps(body).encode('utf-8'))

        handler.handle_analyze()
        
        output = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(output)
        self.assertIn("error", data)
        self.assertIn("does not exist", data["error"])

    def test_v1_ai_push_endpoint(self):
        """Verify handle_v1_ai_push returns explanation and backward-compat keys."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/v1/ai/push"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        
        req_payload = {
            "repo": self.repo_path,
            "target_file": "main.py",
            "persona": "developer"
        }
        handler.get_post_data = lambda: req_payload
        handler.get_repo_root_path = lambda: self.repo_path
        handler.send_json_response = lambda code, body: handler.wfile.write(json.dumps(body).encode('utf-8'))

        handler.handle_v1_ai_push()
        
        output = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(output)
        self.assertEqual(data.get("status"), "success")
        self.assertIn("explanation", data)
        self.assertIn("ai_response", data)
        self.assertIn("message", data)
        self.assertEqual(data["explanation"], data["ai_response"])

    def test_v1_analyze_synchronous_payload(self):
        """Verify handle_v1_analyze returns full synchronous payload for small repositories."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/v1/analyze"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        
        req_payload = {
            "repo": self.repo_path,
            "force": True
        }
        handler.get_post_data = lambda: req_payload
        handler.get_repo_root_path = lambda: self.repo_path
        handler.send_json_response = lambda code, body: handler.wfile.write(json.dumps(body).encode('utf-8'))

        handler.handle_v1_analyze()
        
        output = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(output)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("mode"), "sync")
        self.assertIn("stats", data)
        self.assertIn("risks", data)
        self.assertIn("dependency_graph", data)
        self.assertIn("recommendations", data)
        self.assertIn("file_tree", data)
        self.assertIn("health_score", data)

if __name__ == "__main__":
    unittest.main()

