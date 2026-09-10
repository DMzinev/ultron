"""
ultron/tests/test_mcp_client_roundtrip.py

End-to-end integration test suite for Task P3-B2 per docs/AGENT_EXECUTION_PLAN_PHASE3.md:
"MCP Client-Compatibility Round Trip"

Validates that an external agent client (Cursor, Claude Desktop, Antigravity) can:
1. Spawn Ultron's MCP middleware (python -u -m ultron.interfaces.mcp_server) over native OS stdio.
2. Complete the standard JSON-RPC 2.0 initialize protocol handshake.
3. Discover all 7 canonical tools via tools/list and validate their inputSchemas.
4. Execute sequential tools/call requests for all 7 canonical tools across a continuous session against a real fixture repo.
5. Execute legacy tool aliases (ultron_generate_fix).
6. Verify protocol notifications produce zero stdout pollution and ping returns immediate response.
7. Verify resilience to unknown methods (-32601) without crashing the continuous session.
8. Verify graceful shutdown (clean exit code 0) upon stdin EOF.
"""

import os
import sys
import json
import queue
import threading
import subprocess
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class MCPClientSession:
    """Simulates an external agent client connected to Ultron MCP server over stdio."""

    def __init__(self, repo_root=REPO_ROOT):
        self.repo_root = repo_root
        cmd = [sys.executable, "-u", "-m", "ultron.interfaces.mcp_server"]
        env = {**os.environ, "PYTHONPATH": self.repo_root}
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=self.repo_root,
            env=env,
        )
        self.stderr_lines = []
        self.stdout_queue = queue.Queue()

        self.stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self.stdout_thread = threading.Thread(target=self._drain_stdout, daemon=True)
        self.stderr_thread.start()
        self.stdout_thread.start()

    def _drain_stderr(self):
        try:
            for line in iter(self.proc.stderr.readline, ""):
                self.stderr_lines.append(line)
        except Exception:
            pass

    def _drain_stdout(self):
        try:
            for line in iter(self.proc.stdout.readline, ""):
                line_str = line.strip()
                if line_str:
                    self.stdout_queue.put(line_str)
        except Exception:
            pass

    def send_request(self, payload_dict):
        raw = json.dumps(payload_dict) + "\n"
        self.proc.stdin.write(raw)
        self.proc.stdin.flush()

    def send_notification(self, payload_dict):
        raw = json.dumps(payload_dict) + "\n"
        self.proc.stdin.write(raw)
        self.proc.stdin.flush()

    def read_response(self, timeout=5.0):
        try:
            raw_line = self.stdout_queue.get(timeout=timeout)
            return json.loads(raw_line)
        except queue.Empty:
            raise TimeoutError(
                f"Timed out after {timeout}s waiting for MCP server response. Stderr: {self.stderr_lines}"
            )

    def close(self, timeout=3.0):
        if self.proc:
            if self.proc.stdin and not self.proc.stdin.closed:
                try:
                    self.proc.stdin.close()
                except Exception:
                    pass
            ret = None
            try:
                ret = self.proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                ret = self.proc.wait(timeout=timeout)
            if self.proc.stdout and not self.proc.stdout.closed:
                try:
                    self.proc.stdout.close()
                except Exception:
                    pass
            if self.proc.stderr and not self.proc.stderr.closed:
                try:
                    self.proc.stderr.close()
                except Exception:
                    pass
            return ret
        return 0


class TestMCPClientRoundtrip(unittest.TestCase):
    """End-to-end integration tests proving MCP client compatibility over real stdio."""

    @classmethod
    def setUpClass(cls):
        cls.fixtures_dir = os.path.join(REPO_ROOT, "ultron", "tests", "fixtures")
        cls.clean_repo = os.path.join(cls.fixtures_dir, "clean_repo")
        cls.expected_tools = [
            "get_context_brief",
            "evaluate_repository",
            "explain_violation",
            "get_risk_profile",
            "get_blast_radius",
            "compile_mission",
            "audit_file",
        ]

    def setUp(self):
        self.session = MCPClientSession(REPO_ROOT)

    def tearDown(self):
        if hasattr(self, "session") and self.session:
            self.session.close(timeout=2.0)

    # -----------------------------------------------------------------------
    # 1. Protocol Handshake: initialize
    # -----------------------------------------------------------------------

    def test_client_handshake_initialize(self):
        """Assert client initialize handshake returns protocol 2024-11-05 and server capabilities."""
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "cursor-client", "version": "0.45.0"}
            }
        })
        resp = self.session.read_response(timeout=5.0)

        self.assertEqual(resp.get("jsonrpc"), "2.0")
        self.assertEqual(resp.get("id"), 1)
        result = resp.get("result", {})
        self.assertEqual(result.get("protocolVersion"), "2024-11-05")
        self.assertIn("tools", result.get("capabilities", {}))
        self.assertEqual(result.get("serverInfo", {}).get("name"), "ultron-mcp-middleware")
        self.assertEqual(result.get("serverInfo", {}).get("version"), "1.4.0")

    # -----------------------------------------------------------------------
    # 2. Tool Discovery & Schema Validation: tools/list
    # -----------------------------------------------------------------------

    def test_client_tool_discovery_and_schema_validation(self):
        """Assert tools/list returns exactly 7 canonical tools with valid JSON schemas."""
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        })
        resp = self.session.read_response(timeout=5.0)

        self.assertEqual(resp.get("jsonrpc"), "2.0")
        self.assertEqual(resp.get("id"), 2)
        tools = resp.get("result", {}).get("tools", [])
        tool_names = [t.get("name") for t in tools]

        self.assertEqual(len(tools), 7, f"Expected exactly 7 canonical tools, got {len(tools)}: {tool_names}")
        self.assertEqual(set(tool_names), set(self.expected_tools))

        for t in tools:
            name = t.get("name")
            self.assertIsInstance(name, str)
            self.assertIn(name, self.expected_tools)

            desc = t.get("description", "")
            self.assertIsInstance(desc, str)
            self.assertGreater(len(desc), 10, f"Description too short for tool '{name}'")

            schema = t.get("inputSchema", {})
            self.assertEqual(schema.get("type"), "object", f"inputSchema for '{name}' must be 'object'")
            self.assertIsInstance(schema.get("properties"), dict, f"properties for '{name}' must be dict")

            required = schema.get("required", [])
            self.assertIsInstance(required, list, f"required for '{name}' must be a list")
            for req_prop in required:
                self.assertIn(req_prop, schema.get("properties", {}),
                              f"Required property '{req_prop}' not defined in properties of tool '{name}'")

    # -----------------------------------------------------------------------
    # 3. Full Round Trip: Sequential execution of all 7 canonical tools
    # -----------------------------------------------------------------------

    def test_client_roundtrip_all_canonical_tools(self):
        """Execute all 7 canonical tools sequentially over a single continuous stdio session."""
        # 1. initialize
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 10,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"}
        })
        init_resp = self.session.read_response(timeout=5.0)
        self.assertEqual(init_resp.get("id"), 10)

        # 2. tools/list
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/list",
            "params": {}
        })
        list_resp = self.session.read_response(timeout=5.0)
        self.assertEqual(list_resp.get("id"), 11)

        # 3. Tool 1: get_context_brief
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "get_context_brief",
                "arguments": {
                    "intent": "Audit circular dependencies",
                    "repo_path": self.clean_repo
                }
            }
        })
        resp1 = self.session.read_response(timeout=5.0)
        self.assertEqual(resp1.get("id"), 12)
        self.assertNotIn("isError", resp1.get("result", {}))
        text1 = resp1["result"]["content"][0]["text"]
        self.assertIn("[OBJECTIVE & USER INTENT]", text1)
        self.assertIn("Audit circular dependencies", text1)

        # 4. Tool 2: evaluate_repository
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {
                "name": "evaluate_repository",
                "arguments": {"repo_path": self.clean_repo}
            }
        })
        resp2 = self.session.read_response(timeout=10.0)
        self.assertEqual(resp2.get("id"), 13)
        self.assertNotIn("isError", resp2.get("result", {}))
        text2 = resp2["result"]["content"][0]["text"]
        self.assertIn("Repository evaluation completed", text2)

        # 5. Tool 3: explain_violation
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 14,
            "method": "tools/call",
            "params": {
                "name": "explain_violation",
                "arguments": {"violation_id": 42}
            }
        })
        resp3 = self.session.read_response(timeout=5.0)
        self.assertEqual(resp3.get("id"), 14)
        self.assertNotIn("isError", resp3.get("result", {}))
        text3 = resp3["result"]["content"][0]["text"]
        data3 = json.loads(text3)
        self.assertIn("plain_rule", data3)
        self.assertIn("summary", data3)
        self.assertIn("action", data3)

        # 6. Tool 4: get_risk_profile
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 15,
            "method": "tools/call",
            "params": {
                "name": "get_risk_profile",
                "arguments": {
                    "file_path": "service.py",
                    "repo_path": self.clean_repo
                }
            }
        })
        resp4 = self.session.read_response(timeout=5.0)
        self.assertEqual(resp4.get("id"), 15)
        self.assertNotIn("isError", resp4.get("result", {}))
        text4 = resp4["result"]["content"][0]["text"]
        data4 = json.loads(text4)
        self.assertEqual(data4.get("file_path"), "service.py")
        self.assertEqual(data4.get("level"), "LOW")
        self.assertIsInstance(data4.get("impact_score"), (int, float))
        self.assertIn("signals", data4)

        # 7. Tool 5: get_blast_radius
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 16,
            "method": "tools/call",
            "params": {
                "name": "get_blast_radius",
                "arguments": {
                    "file_path": "service.py",
                    "repo_path": self.clean_repo,
                    "max_depth": 2
                }
            }
        })
        resp5 = self.session.read_response(timeout=5.0)
        self.assertEqual(resp5.get("id"), 16)
        self.assertNotIn("isError", resp5.get("result", {}))
        text5 = resp5["result"]["content"][0]["text"]
        data5 = json.loads(text5)
        self.assertEqual(data5.get("target_file"), "service.py")
        self.assertIsInstance(data5.get("blast_count"), int)
        self.assertIsInstance(data5.get("dependencies"), list)

        # 8. Tool 6: compile_mission
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 17,
            "method": "tools/call",
            "params": {
                "name": "compile_mission",
                "arguments": {
                    "target_file": "service.py",
                    "repo_path": self.clean_repo,
                    "intent": "Refactor interface signatures"
                }
            }
        })
        resp6 = self.session.read_response(timeout=5.0)
        self.assertEqual(resp6.get("id"), 17)
        self.assertNotIn("isError", resp6.get("result", {}))
        text6 = resp6["result"]["content"][0]["text"]
        data6 = json.loads(text6)
        self.assertEqual(data6.get("target_file"), "service.py")
        self.assertIn("rendered_prompt", data6)
        self.assertIn("blast_radius", data6)
        self.assertIn("verification_command", data6)

        # 9. Tool 7: audit_file
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 18,
            "method": "tools/call",
            "params": {
                "name": "audit_file",
                "arguments": {
                    "target_file": "service.py",
                    "repo_path": self.clean_repo
                }
            }
        })
        resp7 = self.session.read_response(timeout=5.0)
        self.assertEqual(resp7.get("id"), 18)
        self.assertNotIn("isError", resp7.get("result", {}))
        text7 = resp7["result"]["content"][0]["text"]
        data7 = json.loads(text7)
        self.assertEqual(data7.get("target_file"), "service.py")
        self.assertEqual(data7.get("status"), "clean")
        self.assertEqual(data7.get("anomaly_count"), 0)

    # -----------------------------------------------------------------------
    # 4. Legacy Tool Execution: ultron_generate_fix
    # -----------------------------------------------------------------------

    def test_client_roundtrip_legacy_tool_execution(self):
        """Assert calling legacy tool ultron_generate_fix returns valid fix envelope."""
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 30,
            "method": "tools/call",
            "params": {
                "name": "ultron_generate_fix",
                "arguments": {
                    "target_file": "service.py",
                    "repo_path": self.clean_repo
                }
            }
        })
        resp = self.session.read_response(timeout=5.0)
        self.assertEqual(resp.get("id"), 30)
        self.assertNotIn("isError", resp.get("result", {}))
        text = resp["result"]["content"][0]["text"]
        self.assertIn("ULTRON AI FIX ENVELOPE: service.py", text)

    # -----------------------------------------------------------------------
    # 5. Protocol Notifications and Ping
    # -----------------------------------------------------------------------

    def test_client_notifications_and_ping(self):
        """Assert notifications produce zero output and ping immediately returns {}."""
        # Notifications must NOT produce any stdout response per JSON-RPC / MCP specs
        self.session.send_notification({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        })
        # Follow with ping to verify the next stdout line is the ping response
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 50,
            "method": "ping"
        })
        resp = self.session.read_response(timeout=5.0)
        self.assertEqual(resp.get("jsonrpc"), "2.0")
        self.assertEqual(resp.get("id"), 50)
        self.assertEqual(resp.get("result"), {})

    # -----------------------------------------------------------------------
    # 6. Unknown Method Resilience
    # -----------------------------------------------------------------------

    def test_client_unknown_method_resilience(self):
        """Assert unknown method returns JSON-RPC -32601 and session remains responsive."""
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 60,
            "method": "nonexistent/custom_method"
        })
        resp = self.session.read_response(timeout=5.0)
        self.assertEqual(resp.get("jsonrpc"), "2.0")
        self.assertEqual(resp.get("id"), 60)
        self.assertEqual(resp.get("error", {}).get("code"), -32601)

        # Confirm session is still alive and processes subsequent ping
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 61,
            "method": "ping"
        })
        resp_ping = self.session.read_response(timeout=5.0)
        self.assertEqual(resp_ping.get("id"), 61)
        self.assertEqual(resp_ping.get("result"), {})

    # -----------------------------------------------------------------------
    # 7. Graceful Shutdown on Stdin EOF
    # -----------------------------------------------------------------------

    def test_client_graceful_shutdown_on_stdin_close(self):
        """Assert child process exits cleanly with return code 0 when client closes stdin."""
        self.session.send_request({
            "jsonrpc": "2.0",
            "id": 70,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"}
        })
        resp = self.session.read_response(timeout=5.0)
        self.assertEqual(resp.get("id"), 70)

        exit_code = self.session.close(timeout=3.0)
        self.assertEqual(exit_code, 0, f"Expected clean exit code 0, got {exit_code}")


if __name__ == "__main__":
    unittest.main()
