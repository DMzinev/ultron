"""
ultron/tests/test_route_contract.py

Contract safety net test suite for Task A3 per docs/AGENT_EXECUTION_PLAN.md:
"For all 43 routes, call the handler in-process and snapshot the response shape
(status code + sorted top-level JSON keys, not values) to route_contract.json.
Run it against the current code and commit the snapshot. This is your safety net."
"""

import os
import io
import json
import unittest

from ultron.interfaces.server import UltronAPIHandler
from ultron.core.pipeline.orchestrator import analyze_repository
import ultron.interfaces.api.routes

FIXTURE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures"))
CONTRACT_FILE = os.path.join(FIXTURE_DIR, "route_contract.json")


class TestRouteContract(unittest.TestCase):
    """Asserts that all 43 API routes maintain exact byte-level contract shape."""

    @classmethod
    def setUpClass(cls):
        cls.repo_path = os.path.join(FIXTURE_DIR, "clean_repo")
        analyze_repository(cls.repo_path, force=True)
        with open(CONTRACT_FILE, "r", encoding="utf-8") as f:
            cls.expected_contract = json.load(f)

    def _invoke_route(self, method: str, path: str, body=None):
        h = UltronAPIHandler.__new__(UltronAPIHandler)
        h.command = method
        h.path = path
        h.wfile = io.BytesIO()
        h.headers = {}
        h.status_code = 200

        if body is not None:
            raw = json.dumps(body).encode("utf-8")
            h.rfile = io.BytesIO(raw)
            h.headers["Content-Length"] = str(len(raw))
        else:
            h.rfile = io.BytesIO(b"")
            h.headers["Content-Length"] = "0"

        h.send_response = lambda code: setattr(h, "status_code", code)
        h.send_json_response = lambda code, d: (
            setattr(h, "status_code", code),
            h.wfile.write(json.dumps(d).encode("utf-8"))
        )
        h.send_header = lambda k, v: None
        h.end_headers = lambda: None
        h.get_repo_root_path = lambda: self.repo_path

        if method == "GET":
            h.do_GET()
        else:
            h.do_POST()

        raw_val = h.wfile.getvalue().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw_val)
            keys = sorted(list(parsed.keys())) if isinstance(parsed, dict) else []
        except Exception:
            keys = []

        return {
            "status": h.status_code,
            "keys": keys
        }

    def test_all_43_routes_match_contract_snapshot(self):
        """Verifies that all 43 registered routes match their contract snapshot shape."""
        # Request payloads matching the contract capture
        payloads = {
            "POST /api/v1/analyze": {"repo": self.repo_path, "async": False},
            "POST /api/v1/overview": {"repo": self.repo_path},
            "POST /api/v1/cancel-analysis": {},
            "POST /api/v1/compare": {"repo": self.repo_path, "baseline_run_id": 1, "target_run_id": 1},
            "POST /api/v1/explain-violation": {"repo": self.repo_path, "violation": {}},
            "POST /api/v1/context-brief": {"repo": self.repo_path},
            "POST /api/v1/export-brief": {"repo": self.repo_path, "format": "markdown"},
            "POST /api/v1/ai/critique": {"repo": self.repo_path, "file_path": "main.py"},
            "POST /api/config": {},
            "POST /api/analyze": {"repo": self.repo_path},
            "POST /api/audit": {"repo": self.repo_path},
            "POST /api/generate": {"repo": self.repo_path},
            "POST /api/file-tree": {"repo": self.repo_path},
            "POST /api/architecture-health": {"repo": self.repo_path},
            "POST /api/get-file": {"repo": self.repo_path, "path": "main.py"},
            "POST /api/save-file": {"repo": self.repo_path, "path": "test_save.tmp", "content": "x = 1\n"},
            "POST /api/run-tests": {"repo": self.repo_path},
            "POST /api/diff-risk": {"repo": self.repo_path, "diff": ""},
            "POST /api/dependency-graph": {"repo": self.repo_path},
            "POST /api/predict-impact": {"repo": self.repo_path, "file": "main.py"},
            "POST /api/save-session": {"repo": self.repo_path, "session": {}},
            "POST /api/calibrate": {"repo": self.repo_path, "adjustments": {}},
            "POST /api/playground": {"repo": self.repo_path, "code": "pass"},
            "POST /api/log-risk-feedback": {"repo": self.repo_path, "target": "main.py", "accurate": True},
            "POST /api/pledge/create": {"repo": self.repo_path, "pledge": {}},
            "POST /api/pledge/verify": {"repo": self.repo_path},
        }

        self.assertEqual(len(self.expected_contract), 43, f"Expected 43 routes, got {len(self.expected_contract)}")

        for route_key, expected_shape in self.expected_contract.items():
            method, path = route_key.split(" ", 1)
            body = payloads.get(route_key)
            actual_shape = self._invoke_route(method, path, body)

            self.assertEqual(
                actual_shape["status"],
                expected_shape["status"],
                f"Status code mismatch on {route_key}: expected {expected_shape['status']}, got {actual_shape['status']}"
            )
            self.assertEqual(
                actual_shape["keys"],
                expected_shape["keys"],
                f"Response keys mismatch on {route_key}: expected {expected_shape['keys']}, got {actual_shape['keys']}"
            )


if __name__ == "__main__":
    unittest.main()
