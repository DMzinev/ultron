"""
ultron/tests/test_mcp_adversarial.py

Adversarial test suite for Task P2-C2 per docs/AGENT_EXECUTION_PLAN_PHASE2.md:
"MCP Tool Error-Path Hardening"

Validates:
1. Malformed JSON-RPC payloads (syntax errors, truncated strings, whitespace).
2. Invalid request structures (primitives, arrays, missing/non-string methods).
3. Invalid parameter & argument types (non-dict params, non-dict arguments).
4. Nonexistent file paths across all 5 file tools (get_risk_profile, get_blast_radius, compile_mission, audit_file, ultron_generate_fix).
5. Missing required tool arguments (empty dicts).
6. Unknown methods and unknown tools return standard JSON-RPC -32601 code.
7. MCP ping and notification handling.
8. Subprocess stdio stream stress test (30 mixed rapid requests piped over stdio to ultron-mcp child process).
"""

import os
import sys
import json
import subprocess
import unittest

from ultron.interfaces.mcp_server import handle_mcp_request

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestMCPAdversarial(unittest.TestCase):
    """Hermetic unit tests enforcing defensive exception shielding and JSON-RPC 2.0 spec compliance."""

    @classmethod
    def setUpClass(cls):
        cls.fixtures_dir = os.path.join(REPO_ROOT, "ultron", "tests", "fixtures")
        cls.clean_repo = os.path.join(cls.fixtures_dir, "clean_repo")

    # -----------------------------------------------------------------------
    # 1. Malformed JSON Syntax Errors
    # -----------------------------------------------------------------------

    def test_malformed_json_syntax(self):
        """Assert invalid JSON syntax returns JSON-RPC -32700 Parse error with id: None."""
        malformed_samples = [
            "{bad json",
            '{"jsonrpc": "2.0", "id": 1, "method":',
            '{"id": 1, "method": "tools/list"} trailing_garbage',
            "{{{{",
        ]
        for bad in malformed_samples:
            resp = handle_mcp_request(bad)
            self.assertIsNotNone(resp, f"Expected error response for {bad!r}")
            self.assertEqual(resp.get("jsonrpc"), "2.0")
            self.assertIsNone(resp.get("id"))
            self.assertEqual(resp.get("error", {}).get("code"), -32700)

    def test_empty_and_whitespace_lines(self):
        """Assert empty and whitespace lines return None without crashing."""
        for line in ["", "   ", "\n", "\t\r\n"]:
            resp = handle_mcp_request(line)
            self.assertIsNone(resp)

    # -----------------------------------------------------------------------
    # 2. Invalid Request Structures
    # -----------------------------------------------------------------------

    def test_invalid_root_payload_types(self):
        """Assert non-object root payloads return JSON-RPC -32600 Invalid Request."""
        primitives = [
            "42",
            '"ping"',
            "true",
            "false",
            "null",
            "[1, 2, 3]",
            '[{"jsonrpc": "2.0", "method": "tools/list"}]'
        ]
        for prim in primitives:
            resp = handle_mcp_request(prim)
            self.assertIsNotNone(resp, f"Expected response for {prim}")
            self.assertEqual(resp.get("jsonrpc"), "2.0")
            self.assertIsNone(resp.get("id"))
            self.assertEqual(resp.get("error", {}).get("code"), -32600)
            self.assertIn("object", resp.get("error", {}).get("message", "").lower())

    def test_missing_or_invalid_method(self):
        """Assert missing or non-string method returns JSON-RPC -32600 Invalid Request."""
        invalid_requests = [
            {"jsonrpc": "2.0", "id": 1},
            {"jsonrpc": "2.0", "id": 2, "method": 123},
            {"jsonrpc": "2.0", "id": 3, "method": None},
            {"jsonrpc": "2.0", "id": 4, "method": ""},
            {"jsonrpc": "2.0", "id": 5, "method": "   "},
            {"jsonrpc": "2.0", "id": 6, "method": ["tools/list"]},
        ]
        for req in invalid_requests:
            resp = handle_mcp_request(json.dumps(req))
            self.assertIsNotNone(resp)
            self.assertEqual(resp.get("id"), req.get("id"))
            self.assertEqual(resp.get("error", {}).get("code"), -32600)

    # -----------------------------------------------------------------------
    # 3. Invalid Params & Arguments
    # -----------------------------------------------------------------------

    def test_invalid_params_type(self):
        """Assert non-dict params returns JSON-RPC -32602 Invalid params."""
        bad_params = [
            {"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": "not_a_dict"},
            {"jsonrpc": "2.0", "id": 11, "method": "tools/list", "params": 42},
            {"jsonrpc": "2.0", "id": 12, "method": "tools/list", "params": ["item"]},
        ]
        for req in bad_params:
            resp = handle_mcp_request(json.dumps(req))
            self.assertIsNotNone(resp)
            self.assertEqual(resp.get("id"), req.get("id"))
            self.assertEqual(resp.get("error", {}).get("code"), -32602)

    def test_invalid_tools_call_arguments_type(self):
        """Assert non-dict arguments in tools/call returns JSON-RPC -32602."""
        bad_calls = [
            {"jsonrpc": "2.0", "id": 20, "method": "tools/call", "params": {"name": "get_risk_profile", "arguments": "str"}},
            {"jsonrpc": "2.0", "id": 21, "method": "tools/call", "params": {"name": "get_risk_profile", "arguments": 99}},
            {"jsonrpc": "2.0", "id": 22, "method": "tools/call", "params": {"name": "get_risk_profile", "arguments": [1]}},
            {"jsonrpc": "2.0", "id": 23, "method": "tools/call", "params": {"name": 1234, "arguments": {}}},
            {"jsonrpc": "2.0", "id": 24, "method": "tools/call", "params": {"arguments": {}}},
        ]
        for req in bad_calls:
            resp = handle_mcp_request(json.dumps(req))
            self.assertIsNotNone(resp)
            self.assertEqual(resp.get("id"), req.get("id"))
            self.assertEqual(resp.get("error", {}).get("code"), -32602)

    # -----------------------------------------------------------------------
    # 4. Unknown Method, Unknown Tool, Ping, and Notifications
    # -----------------------------------------------------------------------

    def test_unknown_method(self):
        """Assert unknown method returns JSON-RPC -32601 Method not found."""
        req = json.dumps({"jsonrpc": "2.0", "id": 30, "method": "unknown/method_xyz"})
        resp = handle_mcp_request(req)
        self.assertEqual(resp.get("id"), 30)
        self.assertEqual(resp.get("error", {}).get("code"), -32601)

    def test_unknown_tool_in_tools_call(self):
        """Assert unknown tool name in tools/call returns JSON-RPC -32601."""
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 31,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool_abc", "arguments": {}}
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp.get("id"), 31)
        self.assertEqual(resp.get("error", {}).get("code"), -32601)

    def test_mcp_ping_and_notifications(self):
        """Assert ping returns empty result; notifications return None (no reply)."""
        ping_req = json.dumps({"jsonrpc": "2.0", "id": 32, "method": "ping"})
        ping_resp = handle_mcp_request(ping_req)
        self.assertEqual(ping_resp.get("id"), 32)
        self.assertEqual(ping_resp.get("result"), {})

        notif_req = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        notif_resp = handle_mcp_request(notif_req)
        self.assertIsNone(notif_resp, "Notifications must not receive a response")

    # -----------------------------------------------------------------------
    # 5. Nonexistent File Handling (All 5 File Tools)
    # -----------------------------------------------------------------------

    def test_nonexistent_file_handling_across_all_tools(self):
        """Assert nonexistent file paths return isError: True without raising unhandled exceptions."""
        tools_to_test = [
            ("get_risk_profile", "file_path"),
            ("get_blast_radius", "file_path"),
            ("compile_mission", "target_file"),
            ("audit_file", "target_file"),
            ("ultron_generate_fix", "target_file"),
        ]

        for req_id, (tool_name, arg_key) in enumerate(tools_to_test, start=40):
            req = json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": {
                        arg_key: "phantom_module_does_not_exist_404.py",
                        "repo_path": self.clean_repo
                    }
                }
            })
            resp = handle_mcp_request(req)
            self.assertIsNotNone(resp, f"No response for {tool_name}")
            self.assertEqual(resp.get("id"), req_id)
            result = resp.get("result", {})
            self.assertTrue(result.get("isError"), f"{tool_name} did not return isError on missing file")
            content = result.get("content", [{}])[0].get("text", "")
            self.assertIn("File not found", content)

    # -----------------------------------------------------------------------
    # 6. Missing Required Arguments Across Tools
    # -----------------------------------------------------------------------

    def test_missing_required_arguments_across_all_tools(self):
        """Assert calling tools with empty arguments returns isError: True."""
        tools_to_test = [
            "get_risk_profile",
            "get_blast_radius",
            "compile_mission",
            "audit_file",
            "ultron_generate_fix"
        ]

        for req_id, tool_name in enumerate(tools_to_test, start=50):
            req = json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": {}
                }
            })
            resp = handle_mcp_request(req)
            self.assertIsNotNone(resp)
            self.assertEqual(resp.get("id"), req_id)
            result = resp.get("result", {})
            self.assertTrue(result.get("isError"), f"{tool_name} did not return isError on empty args")
            content = result.get("content", [{}])[0].get("text", "")
            self.assertIn("Missing required parameter", content)

    # -----------------------------------------------------------------------
    # 7. Subprocess Stdio Stream Concurrency & Stress Test
    # -----------------------------------------------------------------------

    def test_subprocess_stdio_stream_stress(self):
        """
        Stress test: streams 30 mixed rapid back-to-back requests down stdio to
        a real running ultron-mcp child process, verifying zero crashes, 1:1 FIFO
        response alignment, and clean exit 0 on stdin EOF.
        """
        cmd = [sys.executable, "-u", "-m", "ultron.interfaces.mcp_server"]
        env = {**os.environ, "PYTHONPATH": REPO_ROOT}

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # Prevent 4KB stderr buffer deadlock on Windows
            text=True,
            encoding="utf-8",
            cwd=REPO_ROOT
        )

        try:
            # Build 30 varied requests mixing happy paths, invalid JSON, and errors
            requests = []
            expected_ids = []

            for i in range(1, 31):
                mod = i % 6
                if mod == 1:
                    # Valid initialize
                    requests.append(json.dumps({"jsonrpc": "2.0", "id": i, "method": "initialize"}))
                    expected_ids.append(i)
                elif mod == 2:
                    # Malformed JSON (syntax error)
                    requests.append(f'{{"jsonrpc": "2.0", "id": {i}, "method":')
                    expected_ids.append(None)  # Parse error yields id: None
                elif mod == 3:
                    # Non-object primitive root
                    requests.append(f"{i * 100}")
                    expected_ids.append(None)  # Root non-dict yields id: None
                elif mod == 4:
                    # Tool call with nonexistent file
                    requests.append(json.dumps({
                        "jsonrpc": "2.0",
                        "id": i,
                        "method": "tools/call",
                        "params": {
                            "name": "get_risk_profile",
                            "arguments": {"file_path": f"nonexistent_{i}.py", "repo_path": self.clean_repo}
                        }
                    }))
                    expected_ids.append(i)
                elif mod == 5:
                    # Unknown tool
                    requests.append(json.dumps({
                        "jsonrpc": "2.0",
                        "id": i,
                        "method": "tools/call",
                        "params": {"name": f"unknown_tool_{i}", "arguments": {}}
                    }))
                    expected_ids.append(i)
                else:
                    # Valid tools/list
                    requests.append(json.dumps({"jsonrpc": "2.0", "id": i, "method": "tools/list"}))
                    expected_ids.append(i)

            input_payload = "\n".join(requests) + "\n"
            stdout_data, _ = proc.communicate(input=input_payload, timeout=20)

            # Subprocess must stay alive throughout and exit cleanly with code 0 on EOF
            self.assertEqual(proc.returncode, 0, f"Child process crashed with exit code {proc.returncode}")

            # Parse responses from stdout
            output_lines = [l.strip() for l in stdout_data.strip().split("\n") if l.strip()]
            self.assertEqual(len(output_lines), len(expected_ids),
                             f"Expected {len(expected_ids)} responses, got {len(output_lines)}")

            for idx, line in enumerate(output_lines):
                parsed = json.loads(line)
                self.assertEqual(parsed.get("jsonrpc"), "2.0")
                expected_id = expected_ids[idx]
                if expected_id is not None:
                    self.assertEqual(parsed.get("id"), expected_id,
                                     f"Response index {idx} id mismatch: expected {expected_id}, got {parsed.get('id')}")

        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()


if __name__ == "__main__":
    unittest.main()
