"""
ultron.tests.test_agent_bridge
Unit test suite asserting Model Context Protocol (MCP) JSON-RPC 2.0 tool dispatching.
"""

import unittest
import json
from ultron.core.agent_bridge import AgentBridge


class TestAgentBridge(unittest.TestCase):
    """Unit tests for AgentBridge MCP protocol implementation."""

    def setUp(self):
        self.sample_analysis = {
            "health_score": 88.0,
            "stats": {
                "total_files": 2,
                "total_functions": 10,
                "health_score": 88.0
            },
            "risks": [
                {
                    "file": "ultron/core/hub.py",
                    "file_path": "ultron/core/hub.py",
                    "level": "HIGH",
                    "impact_score": 14.5,
                    "complexity": 12,
                    "coupling_score": 8,
                    "definitions": ["Hub", "dispatch"],
                    "dependencies": ["ultron.config"]
                },
                {
                    "file": "ultron/core/leaf.py",
                    "file_path": "ultron/core/leaf.py",
                    "level": "LOW",
                    "impact_score": 2.0,
                    "complexity": 2,
                    "coupling_score": 1,
                    "definitions": ["Leaf"],
                    "dependencies": []
                }
            ],
            "modularity": {
                "health_grade": "A"
            }
        }

    def test_list_mcp_tools(self):
        """Asserts all expected MCP tools are listed with valid input schemas."""
        tools = AgentBridge.list_mcp_tools()
        names = [t["name"] for t in tools]
        self.assertIn("ultron_get_architecture_summary", names)
        self.assertIn("ultron_query_risk_hotspots", names)
        self.assertIn("ultron_get_file_context", names)
        self.assertIn("ultron_get_refactoring_plan", names)

    def test_call_architecture_summary(self):
        """Asserts ultron_get_architecture_summary returns structured metrics."""
        res = AgentBridge.call_mcp_tool("ultron_get_architecture_summary", {}, self.sample_analysis)
        self.assertFalse(res["isError"])
        content_text = res["content"][0]["text"]
        data = json.loads(content_text)
        self.assertEqual(data["health_score"], 88.0)
        self.assertEqual(data["total_files"], 2)
        self.assertEqual(data["high_risk_files"], 1)

    def test_call_query_risk_hotspots(self):
        """Asserts ultron_query_risk_hotspots returns top risk files sorted by impact score."""
        res = AgentBridge.call_mcp_tool("ultron_query_risk_hotspots", {"limit": 1}, self.sample_analysis)
        self.assertFalse(res["isError"])
        data = json.loads(res["content"][0]["text"])
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["file"], "ultron/core/hub.py")
        self.assertEqual(data[0]["level"], "HIGH")

    def test_call_get_file_context(self):
        """Asserts ultron_get_file_context returns file AST facts and dependencies."""
        res = AgentBridge.call_mcp_tool(
            "ultron_get_file_context",
            {"file_path": "ultron/core/hub.py"},
            self.sample_analysis
        )
        self.assertFalse(res["isError"])
        data = json.loads(res["content"][0]["text"])
        self.assertEqual(data["complexity"], 12)
        self.assertIn("Hub", data["definitions"])

    def test_call_unknown_tool(self):
        """Asserts calling unknown tool returns isError: True."""
        res = AgentBridge.call_mcp_tool("unknown_tool_xyz", {}, self.sample_analysis)
        self.assertTrue(res["isError"])

    def test_jsonrpc_initialize(self):
        """Asserts JSON-RPC initialize request returns standard serverInfo."""
        req = {"jsonrpc": "2.0", "id": 101, "method": "initialize", "params": {}}
        resp = AgentBridge.handle_jsonrpc_request(req, self.sample_analysis)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 101)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "ultron-mcp-bridge")
        self.assertEqual(resp["result"]["serverInfo"]["version"], "0.1.999")

    def test_jsonrpc_invalid_request(self):
        """Asserts invalid JSON-RPC format returns error code -32600."""
        req = {"method": "tools/list"}  # missing jsonrpc: "2.0"
        resp = AgentBridge.handle_jsonrpc_request(req, self.sample_analysis)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32600)


if __name__ == "__main__":
    unittest.main()
