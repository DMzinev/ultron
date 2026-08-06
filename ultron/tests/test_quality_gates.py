import os
import io
import json
import tempfile
import unittest

from ultron.interfaces.server import UltronAPIHandler

class TestQualityGates(unittest.TestCase):
    """
    Quality Engineering & Hardening Test Suite verifying the 4 Quality Gates:
    Gate 1: End-to-End User Journeys
    Gate 2: Failure Injection & Recovery
    Gate 3: State Stability & Repeated Executions
    Gate 4: Release Hardening & Unified API Schemas
    """

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.repo_path = cls.temp_dir.name
        
        # Create a sample multi-file repository structure
        cls.file_main = os.path.join(cls.repo_path, "main.py")
        with open(cls.file_main, "w", encoding="utf-8") as f:
            f.write("from helper import add\n\ndef run():\n    return add(2, 3)\n")
            
        cls.file_helper = os.path.join(cls.repo_path, "helper.py")
        with open(cls.file_helper, "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    if a > 0:\n        return a + b\n    return b\n")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

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

    # -------------------------------------------------------------
    # GATE 1: End-to-End User Journey Validation
    # -------------------------------------------------------------
    def test_gate1_full_user_journey_e2e(self):
        """Gate 1: Connect repo -> analyze -> summary -> explain -> ai-push -> context brief."""
        # 1. Analyze repo
        h_analyze = self._create_handler("/api/analyze", {"repo": self.repo_path})
        h_analyze.handle_analyze()
        res_analyze = json.loads(h_analyze.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res_analyze["status"], "success")
        self.assertGreater(res_analyze["stats"]["total_files"], 0)

        # 2. Get Summary
        h_summary = self._create_handler("/api/v1/summary", method="GET")
        h_summary.handle_v1_summary()
        res_summary = json.loads(h_summary.wfile.getvalue().decode("utf-8"))
        self.assertIn("initialized", res_summary)

        # 3. Explain Entity via Design Oracle
        h_explain = self._create_handler("/api/design-oracle", {
            "repo": self.repo_path,
            "entity_id": "helper.py",
            "file": "helper.py",
            "action": "explain"
        })
        h_explain.handle_design_oracle()
        res_explain = json.loads(h_explain.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res_explain["status"], "success")

        # 4. Auto-Push AI
        h_push = self._create_handler("/api/v1/ai-push", {
            "repo": self.repo_path,
            "target_file": "helper.py",
            "persona": "developer"
        })
        h_push.handle_v1_ai_push()
        res_push = json.loads(h_push.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res_push["status"], "success")
        self.assertIn("ai_response", res_push)

        # 5. Context Brief Export
        h_brief = self._create_handler("/api/v1/context-brief", {
            "repo": self.repo_path,
            "target_file": "helper.py"
        })
        h_brief.handle_v1_context_brief()
        res_brief = json.loads(h_brief.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res_brief["status"], "success")
        self.assertIn("handoff", res_brief)

    # -------------------------------------------------------------
    # GATE 2: Failure Injection & Recovery
    # -------------------------------------------------------------
    def test_gate2_failure_nonexistent_directory(self):
        """Gate 2: Non-existent directory returns 400 Bad Request with structured error schema."""
        bad_dir = os.path.join(self.repo_path, "non_existent_folder_xyz")
        h = self._create_handler("/api/analyze", {"repo": bad_dir})
        h.handle_analyze()
        res = json.loads(h.wfile.getvalue().decode("utf-8"))
        self.assertEqual(getattr(h, "last_code", 200), 400)
        self.assertEqual(res["status"], "error")
        self.assertIn("message", res)

    def test_gate2_failure_file_instead_of_directory(self):
        """Gate 2: Passing a single file path instead of directory returns 400 Bad Request."""
        h = self._create_handler("/api/analyze", {"repo": self.file_main})
        h.handle_analyze()
        res = json.loads(h.wfile.getvalue().decode("utf-8"))
        self.assertEqual(getattr(h, "last_code", 200), 400)
        self.assertEqual(res["status"], "error")
        self.assertIn("file, not a directory", res["message"])

    def test_gate2_failure_empty_python_directory(self):
        """Gate 2: Directory with no Python files returns 400 Bad Request gracefully."""
        empty_dir = tempfile.TemporaryDirectory()
        try:
            h = self._create_handler("/api/analyze", {"repo": empty_dir.name})
            h.handle_analyze()
            res = json.loads(h.wfile.getvalue().decode("utf-8"))
            self.assertEqual(getattr(h, "last_code", 200), 400)
            self.assertEqual(res["status"], "error")
            self.assertIn("No code files found", res["message"])
        finally:
            empty_dir.cleanup()

    def test_gate2_failure_ai_push_offline_fallback(self):
        """Gate 2: AI Push handles proxy offline cleanly and returns native AST AI explanation."""
        h = self._create_handler("/api/v1/ai-push", {
            "repo": self.repo_path,
            "target_file": "main.py",
            "persona": "security"
        })
        h.handle_v1_ai_push()
        res = json.loads(h.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["persona"], "security")
        self.assertIn("ai_response", res)
        self.assertIn("source", res)

    # -------------------------------------------------------------
    # GATE 3: Performance, Memory, & State Stability
    # -------------------------------------------------------------
    def test_gate3_repeated_analysis_stability(self):
        """Gate 3: Analyze repository 20 times in sequence to verify zero tracebacks or state leaks."""
        for i in range(20):
            h = self._create_handler("/api/analyze", {"repo": self.repo_path})
            h.handle_analyze()
            res = json.loads(h.wfile.getvalue().decode("utf-8"))
            self.assertEqual(res["status"], "success")

    # -------------------------------------------------------------
    # GATE 4: Release Hardening & Unified API Schemas
    # -------------------------------------------------------------
    def test_gate4_health_check_schema(self):
        """Gate 4: Health check endpoint returns complete operational schema."""
        h = self._create_handler("/api/v1/health", method="GET")
        h.handle_v1_health()
        res = json.loads(h.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res["status"], "healthy")
        self.assertIn("environment", res)
        self.assertIn("rkm_database", res)
        self.assertIn("modules", res)

if __name__ == "__main__":
    unittest.main()
