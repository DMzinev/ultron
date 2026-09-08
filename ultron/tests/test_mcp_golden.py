"""
ultron/tests/test_mcp_golden.py

Golden test suite for Task D3: MCP Tool Parity per docs/AGENT_EXECUTION_PLAN.md.
Validates all 4 new MCP tools (get_risk_profile, get_blast_radius, compile_mission, audit_file)
over standard JSON-RPC 2.0 stdio request handling against synthetic fixtures:
clean_repo, mixed_repo, and tangled_repo.
"""

import os
import json
import tempfile
import unittest

from ultron.interfaces.mcp_server import handle_mcp_request


class TestMCPGolden(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "fixtures")
        )
        cls.clean_repo = os.path.join(cls.fixtures_dir, "clean_repo")
        cls.mixed_repo = os.path.join(cls.fixtures_dir, "mixed_repo")
        cls.tangled_repo = os.path.join(cls.fixtures_dir, "tangled_repo")

    def _call_tool(self, name, arguments, req_id=1):
        raw_req = json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        })
        resp = handle_mcp_request(raw_req)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.get("jsonrpc"), "2.0")
        self.assertEqual(resp.get("id"), req_id)
        return resp

    # -----------------------------------------------------------------------
    # Tool 1: get_risk_profile
    # -----------------------------------------------------------------------

    def test_golden_get_risk_profile_clean_repo(self):
        """Assert get_risk_profile on clean_repo/service.py returns calibrated LOW risk with 4 signals."""
        resp = self._call_tool("get_risk_profile", {
            "file_path": "service.py",
            "repo_path": self.clean_repo
        })
        self.assertNotIn("isError", resp.get("result", {}))
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)

        self.assertEqual(data.get("file_path"), "service.py")
        self.assertEqual(data.get("level"), "LOW")
        self.assertIsInstance(data.get("impact_score"), (int, float))
        self.assertIn("signals", data)
        signals = data["signals"]
        self.assertEqual(signals.get("ast", {}).get("status"), "active")
        self.assertEqual(signals.get("coupling", {}).get("status"), "active")
        self.assertIn(signals.get("churn", {}).get("status"), ("active", "unavailable"))
        self.assertEqual(signals.get("coverage", {}).get("status"), "unavailable")

    def test_golden_get_risk_profile_mixed_repo(self):
        """Assert get_risk_profile on mixed_repo/risky_core.py flags planted HIGH risk."""
        resp = self._call_tool("get_risk_profile", {
            "file_path": "risky_core.py",
            "repo_path": self.mixed_repo
        })
        self.assertNotIn("isError", resp.get("result", {}))
        data = json.loads(resp["result"]["content"][0]["text"])

        self.assertEqual(data.get("file_path"), "risky_core.py")
        self.assertEqual(data.get("level"), "HIGH")
        self.assertGreaterEqual(data.get("complexity", 0), 15)
        self.assertIn("risky_dispatcher.py", data.get("callers", []))

    # -----------------------------------------------------------------------
    # Tool 2: get_blast_radius
    # -----------------------------------------------------------------------

    def test_golden_get_blast_radius_clean_repo(self):
        """Assert service.py blast radius is handlers.py; main.py is leaf module."""
        # Target 1: service.py has 1 dependent (handlers.py)
        resp = self._call_tool("get_blast_radius", {
            "file_path": "service.py",
            "repo_path": self.clean_repo
        })
        self.assertNotIn("isError", resp.get("result", {}))
        data = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(data.get("target_file"), "service.py")
        self.assertEqual(data.get("blast_radius"), ["handlers.py"])
        self.assertEqual(data.get("blast_count"), 1)
        self.assertFalse(data.get("is_leaf"))

        # Target 2: main.py is a leaf module
        resp_leaf = self._call_tool("get_blast_radius", {
            "file_path": "main.py",
            "repo_path": self.clean_repo
        })
        data_leaf = json.loads(resp_leaf["result"]["content"][0]["text"])
        self.assertEqual(data_leaf.get("target_file"), "main.py")
        self.assertEqual(data_leaf.get("blast_radius"), [])
        self.assertEqual(data_leaf.get("blast_count"), 0)
        self.assertTrue(data_leaf.get("is_leaf"))

    def test_golden_get_blast_radius_tangled_repo_god_module(self):
        """Assert god_module.py has 6 dependents in tangled_repo."""
        resp = self._call_tool("get_blast_radius", {
            "file_path": "god_module.py",
            "repo_path": self.tangled_repo
        })
        self.assertNotIn("isError", resp.get("result", {}))
        data = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(data.get("blast_count"), 6)
        expected = {"client.py", "cycle_c.py", "entry.py", "helpers.py", "service.py", "worker.py"}
        self.assertEqual(set(data.get("blast_radius", [])), expected)

    def test_golden_get_blast_radius_boundary_depth_zero(self):
        """Assert max_depth=0 returns empty blast radius."""
        resp = self._call_tool("get_blast_radius", {
            "file_path": "service.py",
            "repo_path": self.clean_repo,
            "max_depth": 0
        })
        data = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(data.get("blast_radius"), [])
        self.assertEqual(data.get("blast_count"), 0)
        self.assertTrue(data.get("is_leaf"))

    # -----------------------------------------------------------------------
    # Tool 3: compile_mission
    # -----------------------------------------------------------------------

    def test_golden_compile_mission_json(self):
        """Assert compile_mission produces structured 7-field mission envelope."""
        resp = self._call_tool("compile_mission", {
            "target_file": "god_module.py",
            "repo_path": self.tangled_repo,
            "intent": "Break down monolithic god module"
        })
        self.assertNotIn("isError", resp.get("result", {}))
        data = json.loads(resp["result"]["content"][0]["text"])

        required_fields = [
            "intent", "target_file", "blast_radius", "must_not_touch",
            "complexity_ceiling", "verification_command", "rollback_instruction",
            "token_budget_hint", "rendered_prompt"
        ]
        for field in required_fields:
            self.assertIn(field, data)
            self.assertTrue(data[field], f"Field '{field}' was empty")

        self.assertEqual(data.get("target_file"), "god_module.py")
        self.assertEqual(data.get("intent"), "Break down monolithic god module")

    def test_golden_compile_mission_markdown_format(self):
        """Assert compile_mission with format='markdown' returns rendered prompt text."""
        resp = self._call_tool("compile_mission", {
            "target_file": "service.py",
            "repo_path": self.clean_repo,
            "intent": "Refactor service logic",
            "format": "markdown"
        })
        self.assertNotIn("isError", resp.get("result", {}))
        text = resp["result"]["content"][0]["text"]
        self.assertIn("[1. INTENT]", text)
        self.assertIn("[2. BLAST RADIUS]", text)
        self.assertIn("[5. VERIFICATION COMMAND]", text)

    # -----------------------------------------------------------------------
    # Tool 4: audit_file
    # -----------------------------------------------------------------------

    def test_golden_audit_file_clean(self):
        """Assert audit_file on clean_repo/service.py reports clean status."""
        resp = self._call_tool("audit_file", {
            "target_file": "service.py",
            "repo_path": self.clean_repo
        })
        self.assertNotIn("isError", resp.get("result", {}))
        data = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(data.get("target_file"), "service.py")
        self.assertEqual(data.get("status"), "clean")
        self.assertEqual(data.get("anomaly_count"), 0)
        self.assertEqual(data.get("anomalies"), [])

    def test_golden_audit_file_planted_typo_detected(self):
        """Assert audit_file detects planted typo in temporary out-of-sample file."""
        typo_lines = [
            "# Temporary defect injection module",
            "def run_service_call():",
            "    return format_respones()",
            ""
        ]
        typo_code = chr(10).join(typo_lines)

        fd, temp_path = tempfile.mkstemp(suffix="_audit_test.py", dir=self.clean_repo)
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(typo_code)

            resp = self._call_tool("audit_file", {
                "target_file": os.path.basename(temp_path),
                "repo_path": self.clean_repo,
                "typo_threshold": 0.75
            })
            self.assertNotIn("isError", resp.get("result", {}))
            data = json.loads(resp["result"]["content"][0]["text"])
            self.assertEqual(data.get("status"), "anomalies_detected")
            self.assertGreaterEqual(data.get("anomaly_count"), 1)
        finally:
            os.close(fd)
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    # -----------------------------------------------------------------------
    # Boundary & Error Handling
    # -----------------------------------------------------------------------

    def test_golden_missing_parameters_returns_isError(self):
        """Assert missing required parameters return isError: True without crashing server."""
        for tool_name in ["get_risk_profile", "get_blast_radius", "compile_mission", "audit_file"]:
            resp = self._call_tool(tool_name, {})
            self.assertTrue(resp.get("result", {}).get("isError"), f"{tool_name} did not return isError on missing param")

    def test_golden_missing_file_returns_isError(self):
        """Assert non-existent target file returns isError: True."""
        resp = self._call_tool("get_risk_profile", {
            "file_path": "non_existent_file_xyz.py",
            "repo_path": self.clean_repo
        })
        self.assertTrue(resp.get("result", {}).get("isError"))
        self.assertIn("File not found", resp["result"]["content"][0]["text"])

    def test_golden_unknown_tool_returns_jsonrpc_error(self):
        """Assert calling unknown tool returns JSON-RPC -32601 code."""
        raw_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 99,
            "method": "tools/call",
            "params": {"name": "unknown_tool_xyz", "arguments": {}}
        })
        resp = handle_mcp_request(raw_req)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"].get("code"), -32601)


if __name__ == "__main__":
    unittest.main()
