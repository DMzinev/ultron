"""
ultron.core.agent_bridge
Model Context Protocol (MCP) JSON-RPC 2.0 bridge and tool dispatcher.
"""

from typing import Dict, Any, List, Optional
import json


def _find_risk_by_file(risks: List[Dict[str, Any]], target_file: str) -> Optional[Dict[str, Any]]:
    """Locates a risk record matching the normalized file path."""
    for r in risks:
        path = str(r.get("file_path", r.get("file", ""))).replace("\\", "/").strip()
        if path == target_file:
            return r
    return None


def _handle_architecture_summary(
    args: Dict[str, Any],
    data: Dict[str, Any],
    risks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generates repository architecture summary payload."""
    stats = data.get("stats", {})
    total_files = stats.get("total_files", len(risks))
    high_risks = sum(1 for r in risks if r.get("level") == "HIGH")
    summary = {
        "health_score": data.get("health_score", 100.0),
        "total_files": total_files,
        "total_functions": stats.get("total_functions", 0),
        "high_risk_files": high_risks,
        "modularity_grade": data.get("modularity", {}).get("health_grade", "A")
    }
    return {
        "isError": False,
        "content": [{"type": "text", "text": json.dumps(summary, indent=2)}]
    }


def _handle_query_risk_hotspots(
    args: Dict[str, Any],
    data: Dict[str, Any],
    risks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Queries top architectural hotspots sorted by impact score."""
    limit = int(args.get("limit", 5))
    sorted_risks = sorted(risks, key=lambda r: float(r.get("impact_score", 0)), reverse=True)
    return {
        "isError": False,
        "content": [{"type": "text", "text": json.dumps(sorted_risks[:limit], indent=2)}]
    }


def _handle_get_file_context(
    args: Dict[str, Any],
    data: Dict[str, Any],
    risks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Retrieves file context facts from risk index or default clean template."""
    file_path = str(args.get("file_path", "")).replace("\\", "/").strip()
    matched = _find_risk_by_file(risks, file_path)
    content_data = matched if matched else {
        "file": file_path,
        "status": "Clean or unindexed",
        "complexity": 1,
        "coupling_score": 0,
        "definitions": [],
        "dependencies": []
    }
    return {
        "isError": False,
        "content": [{"type": "text", "text": json.dumps(content_data, indent=2)}]
    }


def _handle_get_refactoring_plan(
    args: Dict[str, Any],
    data: Dict[str, Any],
    risks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Constructs refactoring action plan for target file."""
    file_path = str(args.get("file_path", "")).replace("\\", "/").strip()
    matched = _find_risk_by_file(risks, file_path)
    comp = matched.get("complexity", 1) if matched else 1
    plan = {
        "target": file_path,
        "current_complexity": comp,
        "target_complexity": min(comp, 8),
        "directives": [
            "Isolate branching conditions into helper functions",
            "Preserve all public signature contracts",
            "Maintain 100% test pass rate"
        ]
    }
    return {
        "isError": False,
        "content": [{"type": "text", "text": json.dumps(plan, indent=2)}]
    }


_TOOL_DISPATCH = {
    "ultron_get_architecture_summary": _handle_architecture_summary,
    "ultron_query_risk_hotspots": _handle_query_risk_hotspots,
    "ultron_get_file_context": _handle_get_file_context,
    "ultron_get_refactoring_plan": _handle_get_refactoring_plan,
}


def _rpc_initialize(req_id: Any, params: Dict[str, Any], analysis_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Handles JSON-RPC 2.0 initialize method."""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "ultron-mcp-bridge",
                "version": "0.1.999"
            }
        }
    }


def _rpc_tools_list(req_id: Any, params: Dict[str, Any], analysis_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Handles JSON-RPC 2.0 tools/list method."""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "tools": AgentBridge.list_mcp_tools()
        }
    }


def _rpc_tools_call(req_id: Any, params: Dict[str, Any], analysis_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Handles JSON-RPC 2.0 tools/call method."""
    tool_name = params.get("name")
    tool_args = params.get("arguments", {})
    result = AgentBridge.call_mcp_tool(tool_name, tool_args, analysis_data)
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": result
    }


_RPC_DISPATCH = {
    "initialize": _rpc_initialize,
    "tools/list": _rpc_tools_list,
    "tools/call": _rpc_tools_call,
}


class AgentBridge:
    """Deterministic MCP tool dispatcher and JSON-RPC 2.0 message handler."""

    @staticmethod
    def list_mcp_tools() -> List[Dict[str, Any]]:
        """Returns the list of available MCP tools and their schemas."""
        return [
            {
                "name": "ultron_get_architecture_summary",
                "description": "Returns high-level repository architecture health score, file count, and risk breakdown.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "ultron_query_risk_hotspots",
                "description": "Returns top architectural risk hotspots sorted by impact score.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Maximum number of hotspots to return.", "default": 5}
                    }
                }
            },
            {
                "name": "ultron_get_file_context",
                "description": "Returns architectural facts, complexity, coupling, and definitions for a target file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Relative or absolute path of target file."}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "ultron_get_refactoring_plan",
                "description": "Generates a grounded refactoring action plan for a high-complexity module.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Target module path."}
                    },
                    "required": ["file_path"]
                }
            }
        ]

    @staticmethod
    def call_mcp_tool(
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        analysis_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Dispatches an MCP tool invocation against analysis telemetry."""
        handler = _TOOL_DISPATCH.get(name)
        if not handler:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Unknown tool: '{name}'"}]
            }

        args = arguments or {}
        data = analysis_data or {}
        risks = data.get("risks", [])
        return handler(args, data, risks)

    @staticmethod
    def handle_jsonrpc_request(
        req: Dict[str, Any],
        analysis_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handles a single JSON-RPC 2.0 request dictionary and returns standard JSON-RPC 2.0 response."""
        if not isinstance(req, dict) or req.get("jsonrpc") != "2.0":
            req_id = req.get("id") if isinstance(req, dict) else None
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32600, "message": "Invalid Request: Must be valid JSON-RPC 2.0 object"}
            }

        req_id = req.get("id")
        method = str(req.get("method"))
        handler = _RPC_DISPATCH.get(method)

        if handler:
            params = req.get("params") or {}
            return handler(req_id, params, analysis_data)

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not found"
            }
        }

