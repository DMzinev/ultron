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
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

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

    def test_api_v1_risk_profile_dynamic_and_invalid_param(self):
        """Verify GET /api/v1/risk-profile resolves dynamic metrics and validates parameters."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = f"/api/v1/risk-profile?entity=sample_module.py&repo={self.repo_path}"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.get_repo_root_path = lambda: self.repo_path

        handler.handle_v1_risk_profile()
        output = handler.wfile.getvalue().decode('utf-8')
        res = json.loads(output)
        self.assertTrue(res["success"])
        data = res["data"]
        self.assertEqual(data["entity_id"], "sample_module.py")
        self.assertIn("score", data)
        self.assertIn("signals", data)
        self.assertIn("metric_provenance", data)
        prov = data["metric_provenance"]
        self.assertIn("complexity_source", prov)
        self.assertIn("cache_hit", prov)
        self.assertIn("snapshot_id", prov)

        # Invalid param test
        handler_bad = UltronAPIHandler.__new__(UltronAPIHandler)
        handler_bad.path = "/api/v1/risk-profile?complexity=invalid_num"
        handler_bad.wfile = io.BytesIO()
        status_codes = []
        handler_bad.send_response = lambda code: status_codes.append(code)
        handler_bad.send_header = lambda k, v: None
        handler_bad.end_headers = lambda: None
        handler_bad.handle_v1_risk_profile()
        self.assertIn(400, status_codes)

    def test_api_v1_decision_dynamic(self):
        """Verify GET /api/v1/decision evaluates policy dynamically."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = f"/api/v1/decision?entity=sample_module.py&criticality=HIGH&repo={self.repo_path}"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.get_repo_root_path = lambda: self.repo_path

        handler.handle_v1_decision()
        output = handler.wfile.getvalue().decode('utf-8')
        res = json.loads(output)
        self.assertTrue(res["success"])
        data = res["data"]
        self.assertEqual(data["entity_id"], "sample_module.py")
        self.assertIn("priority", data)
        self.assertIn("risk_score", data)
        self.assertIn("metric_provenance", data)
        prov = data["metric_provenance"]
        self.assertIn("complexity_source", prov)
        self.assertIn("cache_hit", prov)
        self.assertIn("snapshot_id", prov)

    def test_api_v1_dependency_graph_chunked_and_invalid_param(self):
        """Verify GET /api/v1/dependency-graph supports chunking and handles invalid params with 400."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = f"/api/v1/dependency-graph?repo={self.repo_path}&chunk=0&limit=5"
        handler.wfile = io.BytesIO()
        handler.headers = {}
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.get_query_data = lambda: {"repo": self.repo_path, "chunk": "0", "limit": "5"}

        handler.handle_dependency_graph()
        output = handler.wfile.getvalue().decode('utf-8')
        res = json.loads(output)
        self.assertTrue(res["success"])
        self.assertEqual(res["chunk"], 0)
        self.assertEqual(res["limit"], 5)
        self.assertIn("total_chunks", res)
        self.assertIn("has_more", res)

        # Invalid param test
        handler_bad = UltronAPIHandler.__new__(UltronAPIHandler)
        handler_bad.path = "/api/v1/dependency-graph?chunk=invalid_num"
        handler_bad.headers = {}
        handler_bad.wfile = io.BytesIO()
        handler_bad.get_repo_root_path = lambda: self.repo_path
        status_codes = []
        handler_bad.send_response = lambda code: status_codes.append(code)
        handler_bad.send_header = lambda k, v: None
        handler_bad.end_headers = lambda: None
        handler_bad.get_query_data = lambda: {"chunk": "invalid_num"}
        handler_bad.handle_dependency_graph()
        self.assertIn(400, status_codes)

    def test_api_v1_objective_and_agent_context_endpoints(self):
        """Verify GET/POST /api/v1/objective and POST /api/v1/agent/context."""
        # 1. GET objective
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.command = "GET"
        handler.path = f"/api/v1/objective?repo={self.repo_path}"
        handler.headers = {}
        handler.wfile = io.BytesIO()
        handler.send_response = lambda code: None
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None

        handler.handle_v1_get_objective()
        output = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(output)
        self.assertIn("title", data)
        self.assertIn("tasks", data)

        # 2. Agent context builder
        handler_ctx = UltronAPIHandler.__new__(UltronAPIHandler)
        handler_ctx.command = "POST"
        handler_ctx.path = "/api/v1/agent/context"
        handler_ctx.headers = {}
        handler_ctx.wfile = io.BytesIO()
        handler_ctx.get_post_data = lambda: {"repo": self.repo_path, "provider": "claude"}
        handler_ctx.send_response = lambda code: None
        handler_ctx.send_header = lambda k, v: None
        handler_ctx.end_headers = lambda: None

        handler_ctx.handle_v1_agent_context_builder()
        out_ctx = handler_ctx.wfile.getvalue().decode('utf-8')
        data_ctx = json.loads(out_ctx)
        self.assertTrue(data_ctx["success"])
        self.assertIn("<ultron_mission_envelope", data_ctx["prompt"])

        # 3. Safety evaluate
        handler_safe = UltronAPIHandler.__new__(UltronAPIHandler)
        handler_safe.command = "POST"
        handler_safe.path = "/api/v1/safety/evaluate"
        handler_safe.headers = {}
        handler_safe.wfile = io.BytesIO()
        handler_safe.get_post_data = lambda: {
            "repo": self.repo_path,
            "test_results": {"passed": True, "passed_count": 10, "failed_count": 0}
        }
        handler_safe.send_response = lambda code: None
        handler_safe.send_header = lambda k, v: None
        handler_safe.end_headers = lambda: None

        handler_safe.handle_v1_safety_evaluate()
        out_safe = handler_safe.wfile.getvalue().decode('utf-8')
        data_safe = json.loads(out_safe)
        self.assertTrue(data_safe["success"])
        self.assertEqual(data_safe["report"]["badge"], "CONTINUE BUILDING")

    def test_unified_v2_6_5_analysis_payload(self):
        """Verify _build_analysis_payload returns unified authoritative runtime contract (v2.6.5)."""
        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.wfile = io.BytesIO()
        handler.headers = {}
        payload = handler._build_analysis_payload(self.repo_path, force=True)

        # 1. Identity & Version Grounding
        self.assertEqual(payload["projection_version"], "2.6.5")
        self.assertIn("snapshot_id", payload)
        self.assertIn("model_hash", payload)
        self.assertIn("repository_id", payload)
        self.assertIn("repository_root", payload)
        self.assertIn("repository_relative_root", payload)
        self.assertIn("generated_at", payload)

        # 2. Performance Telemetry
        self.assertIn("payload_bytes", payload)
        self.assertIn("payload_build_ms", payload)
        self.assertIn("payload_serialize_ms", payload)
        self.assertGreater(payload["payload_bytes"], 0)

        # 3. Unified State Projections
        self.assertIn("objective", payload)
        self.assertIn("session", payload)
        self.assertIn("readiness", payload)
        self.assertIn("diff", payload)
        self.assertIn("stats", payload)
        self.assertIn("risks", payload)
        self.assertIn("dependency_graph", payload)
        self.assertIn("recommendations", payload)
        self.assertIn("file_tree", payload)

        # 4. Snapshot-Bound Readiness Check
        self.assertEqual(payload["readiness"]["snapshot_id"], payload["snapshot_id"])
        self.assertEqual(payload["readiness"]["model_hash"], payload["model_hash"])

        # 5. Session Timeline Presence
        self.assertIsInstance(payload["session"].get("timeline"), list)

    def test_api_v1_run_tests_async_and_poll_status(self):
        """Verify POST /api/v1/run-tests with async=True returns 202 and polls via GET /api/v1/test-status."""
        import io
        import json
        import time

        handler = UltronAPIHandler.__new__(UltronAPIHandler)
        handler.path = "/api/v1/run-tests"
        handler.command = "POST"
        body = json.dumps({"repo": self.repo_path, "async": True}).encode("utf-8")
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        handler.headers = {"Content-Length": str(len(body))}
        
        responses = []
        handler.send_response = lambda code: responses.append(code)
        handler.send_header = lambda k, v: None
        handler.end_headers = lambda: None
        handler.get_repo_root_path = lambda: self.repo_path

        handler.handle_run_tests()
        self.assertIn(202, responses)
        
        response_bytes = handler.wfile.getvalue()
        async_res = json.loads(response_bytes.decode("utf-8"))
        self.assertEqual(async_res.get("status"), "running")
        self.assertIn("run_id", async_res)
        run_id = async_res["run_id"]

        # Now test GET /api/v1/test-status?run_id=...
        handler_poll = UltronAPIHandler.__new__(UltronAPIHandler)
        handler_poll.path = f"/api/v1/test-status?run_id={run_id}"
        handler_poll.command = "GET"
        handler_poll.wfile = io.BytesIO()
        handler_poll.headers = {}
        poll_responses = []
        handler_poll.send_response = lambda code: poll_responses.append(code)
        handler_poll.send_header = lambda k, v: None
        handler_poll.end_headers = lambda: None

        handler_poll.handle_test_status()
        self.assertIn(200, poll_responses)
        poll_data = json.loads(handler_poll.wfile.getvalue().decode("utf-8"))
        self.assertEqual(poll_data.get("run_id"), run_id)
        self.assertIn(poll_data.get("status"), ("queued", "running", "completed", "failed"))

        # Clean up background run
        from ultron.core.test_runner_service import TestRunnerService
        TestRunnerService.get_instance().cancel_run(run_id)


if __name__ == "__main__":
    unittest.main()

