# Unit tests for Vibe Coder AI Middleware & MCP Server
import os
import sys
import unittest
import json

from ultron.core.context_brief import generate_vibe_context_package
from ultron.interfaces.mcp_server import handle_mcp_request

class TestMCPMiddleware(unittest.TestCase):

    def test_vibe_context_package_generation(self):
        pkg = generate_vibe_context_package("Add user authentication")
        self.assertEqual(pkg["status"], "success")
        self.assertEqual(pkg["user_intent"], "Add user authentication")
        self.assertIn("GROUND TRUTH CODEBASE FACTS", pkg["prompt_package"])
        self.assertIn("Forbidden", pkg["prompt_package"])

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

    def test_mcp_tools_list(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 2)
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        expected_tools = [
            "get_context_brief",
            "evaluate_repository",
            "explain_violation",
            "get_risk_profile",
            "get_blast_radius",
            "compile_mission",
            "audit_file"
        ]
        for t in expected_tools:
            self.assertIn(t, tool_names)

    def test_mcp_tools_call_get_context_brief(self):
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_context_brief",
                "arguments": {"intent": "Fix circular dependency"}
            }
        })
        resp = handle_mcp_request(req)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 3)
        content = resp["result"]["content"][0]["text"]
        self.assertIn("[OBJECTIVE & USER INTENT]", content)
        self.assertIn("Fix circular dependency", content)

if __name__ == "__main__":
    unittest.main()
