"""
Comprehensive Test Suite for Ultron Model Context Protocol (MCP 2.0 Standard).
Tests JSON-RPC 2.0 framing, tool listing and calling, resource listing and reading,
error codes (-32700, -32601, -32602, tool isError: true), legacy aliases,
and real subprocess stdio pipe execution.
"""
import os
import sys
import json
import unittest
import subprocess

from ultron.core.context_brief import generate_vibe_context_package
from ultron.interfaces.mcp_server import handle_mcp_request, MCP_TOOLS, MCP_RESOURCES


class TestMCPProtocolAndFraming(unittest.TestCase):
    """Tests JSON-RPC 2.0 framing, initialization, and protocol-level error codes."""

    def test_vibe_context_package_generation(self):
        pkg = generate_vibe_context_package("Add user authentication")
        self.assertEqual(pkg["status"], "success")
        self.assertEqual(pkg["user_intent"], "Add user authentication")
        self.assertIn("GROUND TRUTH CODEBASE FACTS", pkg["prompt_package"])

    def test_mcp_initialize(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 1)
        self.assertIn("serverInfo", resp["result"])
        self.assertEqual(resp["result"]["serverInfo"]["name"], "ultron-mcp-server")
        self.assertIn("tools", resp["result"]["capabilities"])
        self.assertIn("resources", resp["result"]["capabilities"])

    def test_mcp_ping(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "ping",
            "params": {}
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 2)
        self.assertEqual(resp["result"], {})

    def test_mcp_notification_suppression(self):
        # Notifications (no 'id') must return None (0 bytes emitted to stdout)
        req = json.dumps({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        })
        self.assertIsNone(handle_mcp_request(req))

    def test_parse_error_malformed_json(self):
        malformed_inputs = [
            "{invalid_json",
            "{\"jsonrpc\": \"2.0\", \"method\": ",
            "{\"jsonrpc\": \"2.0\", 'single_quotes': 1}",
            "\x00\x01\x02",
        ]
        for bad_raw in malformed_inputs:
            resp = handle_mcp_request(bad_raw)
            self.assertIsNotNone(resp)
            self.assertEqual(resp.get("jsonrpc"), "2.0")
            self.assertIn("error", resp)
            self.assertEqual(resp["error"]["code"], -32700)

    def test_empty_and_whitespace_lines(self):
        self.assertIsNone(handle_mcp_request(""))
        self.assertIsNone(handle_mcp_request("   "))
        self.assertIsNone(handle_mcp_request("\n\t\r\n"))

    def test_non_dict_json_payloads(self):
        non_dict_payloads = ["[1, 2, 3]", "\"just a string\"", "12345", "true"]
        for payload in non_dict_payloads:
            resp = handle_mcp_request(payload)
            self.assertIsNotNone(resp)
            self.assertIn("error", resp)
            self.assertIn(resp["error"]["code"], [-32600, -32700, -32602])

    def test_method_not_found(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 101,
            "method": "nonexistent/rpc_endpoint",
            "params": {}
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp["id"], 101)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_invalid_params_type(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 102,
            "method": "tools/call",
            "params": "not-a-dict"
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp["id"], 102)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32602)


class TestMCPToolListingAndCalling(unittest.TestCase):
    """Tests tool listing and execution across core tools and legacy aliases."""

    def test_tools_list_schema(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 200,
            "method": "tools/list",
            "params": {}
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp["id"], 200)
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]

        expected_tools = [
            "ultron_analyze_repository",
            "ultron_get_blast_radius",
            "ultron_get_recommendations",
            "ultron_compile_mission",
            "ultron_verify_changes",
            "get_context_brief",
            "evaluate_repository",
            "explain_violation",
            "get_file_risk_detail",
            "get_analysis_snapshot"
        ]
        for exp in expected_tools:
            self.assertIn(exp, tool_names)

    def test_tool_call_ultron_compile_mission(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 201,
            "method": "tools/call",
            "params": {
                "name": "ultron_compile_mission",
                "arguments": {"intent": "Fix circular dependency", "repo_path": os.getcwd()}
            }
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp["id"], 201)
        content = resp["result"]["content"][0]["text"]
        self.assertIn("[OBJECTIVE & USER INTENT]", content)
        self.assertIn("Fix circular dependency", content)

    def test_tool_call_ultron_get_blast_radius(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 202,
            "method": "tools/call",
            "params": {
                "name": "ultron_get_blast_radius",
                "arguments": {"target_file": "ultron/core/analyzer.py", "repo_path": os.getcwd()}
            }
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp["id"], 202)
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("file_path", payload)
        self.assertIn("impact_score", payload)
        self.assertIn("complexity", payload)
        self.assertIn("plain_english_summary", payload)

    def test_tool_call_ultron_analyze_repository(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 203,
            "method": "tools/call",
            "params": {
                "name": "ultron_analyze_repository",
                "arguments": {"repo_path": os.getcwd()}
            }
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp["id"], 203)
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("health_score", payload)
        self.assertIn("plain_english_mental_model", payload)

    def test_tool_call_ultron_get_recommendations(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 204,
            "method": "tools/call",
            "params": {
                "name": "ultron_get_recommendations",
                "arguments": {"repo_path": os.getcwd(), "limit": 3}
            }
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp["id"], 204)
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("recommendations", payload)

    def test_tool_call_ultron_verify_changes(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 205,
            "method": "tools/call",
            "params": {
                "name": "ultron_verify_changes",
                "arguments": {"repo_path": os.getcwd()}
            }
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp["id"], 205)
        text = resp["result"]["content"][0]["text"]
        self.assertIn("CONTINUE BUILDING", text)

    def test_tool_call_legacy_aliases(self):
        aliases = [
            ("get_contract_spec", {"intent": "Check aliases"}, "[OBJECTIVE & USER INTENT]"),
            ("analyze_codebase", {"repo_path": os.getcwd()}, "Repository Evaluation Summary"),
            ("get_plain_summary", {"violation_id": 1}, "plain_rule"),
            ("audit_file_anomalies", {"target_file": "ultron/core/analyzer.py"}, "file_path")
        ]
        for alias_name, args, expected_content in aliases:
            req = json.dumps({
                "jsonrpc": "2.0",
                "id": 206,
                "method": "tools/call",
                "params": {"name": alias_name, "arguments": args}
            })
            resp = handle_mcp_request(req)
            self.assertEqual(resp["id"], 206)
            self.assertIn("result", resp)
            text = resp["result"]["content"][0]["text"]
            self.assertIn(expected_content, text)

    def test_tool_call_unknown_tool(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 207,
            "method": "tools/call",
            "params": {"name": "unregistered_tool", "arguments": {}}
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp["id"], 207)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)


class TestMCPResourceListingAndReading(unittest.TestCase):
    """Tests MCP resource listing, reading, and path traversal defense."""

    def test_resources_list(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 300,
            "method": "resources/list",
            "params": {}
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp["id"], 300)
        uris = [r["uri"] for r in resp["result"]["resources"]]
        self.assertIn("ultron://repository/summary", uris)
        self.assertIn("ultron://repository/recommendations", uris)
        self.assertIn("ultron://repository/graph", uris)
        self.assertIn("ultron://resources/decision_policy", uris)
        self.assertIn("ultron://resources/weights", uris)
        self.assertIn("ultron://resources/thresholds", uris)

    def test_resources_read_valid_uris(self):
        valid_uris = [
            "ultron://repository/summary",
            "ultron://repository/recommendations",
            "ultron://repository/graph",
            "ultron://resources/decision_policy",
            "ultron://resources/weights",
            "ultron://resources/thresholds"
        ]
        for uri in valid_uris:
            req = json.dumps({
                "jsonrpc": "2.0",
                "id": 301,
                "method": "resources/read",
                "params": {"uri": uri}
            })
            resp = handle_mcp_request(req)
            self.assertEqual(resp["id"], 301, f"Failed for {uri}")
            self.assertIn("result", resp, f"No result for {uri}: {resp.get('error')}")
            contents = resp["result"]["contents"]
            self.assertTrue(len(contents) > 0)
            self.assertEqual(contents[0]["uri"], uri)

    def test_resources_read_path_traversal_defense(self):
        traversals = [
            "ultron://resources/../../etc/passwd",
            "ultron://resources/..\\..\\windows\\win.ini",
            "ultron://resources/%2e%2e%2fescape"
        ]
        for attack_uri in traversals:
            req = json.dumps({
                "jsonrpc": "2.0",
                "id": 302,
                "method": "resources/read",
                "params": {"uri": attack_uri}
            })
            resp = handle_mcp_request(req)
            self.assertEqual(resp["id"], 302)
            self.assertIn("error", resp)
            self.assertEqual(resp["error"]["code"], -32602)


class TestMCPSubprocessStdioExecution(unittest.TestCase):
    """End-to-end integration tests over real subprocess stdio pipes."""

    def setUp(self):
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "ultron.interfaces.mcp_server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1
        )

    def tearDown(self):
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()

    def _send_and_receive(self, payload_dict):
        raw_msg = json.dumps(payload_dict) + "\n"
        self.proc.stdin.write(raw_msg)
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        self.assertTrue(line, "Subprocess stdout closed unexpectedly.")
        return json.loads(line.strip())

    def test_full_stdio_session_lifecycle(self):
        # 1. Initialize
        init_resp = self._send_and_receive({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        })
        self.assertEqual(init_resp["id"], 1)
        self.assertIn("serverInfo", init_resp["result"])

        # 2. Ping
        ping_resp = self._send_and_receive({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "ping",
            "params": {}
        })
        self.assertEqual(ping_resp["id"], 2)

        # 3. Tools List
        tools_resp = self._send_and_receive({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/list",
            "params": {}
        })
        self.assertEqual(tools_resp["id"], 3)
        tools = [t["name"] for t in tools_resp["result"]["tools"]]
        self.assertIn("ultron_analyze_repository", tools)

        # 4. Resources List
        res_resp = self._send_and_receive({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/list",
            "params": {}
        })
        self.assertEqual(res_resp["id"], 4)
        self.assertTrue(len(res_resp["result"]["resources"]) >= 3)

        # 5. Clean EOF Exit
        self.proc.stdin.close()
        return_code = self.proc.wait(timeout=3.0)
        self.assertEqual(return_code, 0)


if __name__ == "__main__":
    unittest.main()

