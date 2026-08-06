# Model Context Protocol (MCP) Server for Ultron AI Middleware
import sys
import os
import json
import traceback

def log_err(msg):
    """Routes diagnostic logging strictly to stderr to prevent stdout JSON-RPC corruption."""
    sys.stderr.write(f"[Ultron MCP] {msg}\n")
    sys.stderr.flush()

def handle_mcp_request(raw_line):
    if not raw_line or not raw_line.strip():
        return None
        
    try:
        req = json.loads(raw_line)
    except Exception as e:
        log_err(f"Invalid JSON-RPC request: {e}")
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "Parse error"}
        }

    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})

    log_err(f"Received MCP method: {method}")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ultron-mcp-middleware", "version": "1.3.0"}
            }
        }
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "get_context_brief",
                        "description": "Generates a grounded Vibe Coder AI Context Mission Envelope with RKM facts, constraints, and allowed/forbidden files.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "intent": {"type": "string", "description": "High-level user intent or task objective."},
                                "repo_path": {"type": "string", "description": "Absolute path to repository root."}
                            }
                        }
                    },
                    {
                        "name": "evaluate_repository",
                        "description": "Evaluates repository risk, cyclomatic complexity, and coupling bounds.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "repo_path": {"type": "string", "description": "Absolute path to repository root."}
                            }
                        }
                    },
                    {
                        "name": "explain_violation",
                        "description": "Translates an architectural violation into Plain English lead explanation and evidence chain.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "violation_id": {"type": "integer", "description": "Numeric violation ID from RKM DB."}
                            }
                        }
                    }
                ]
            }
        }
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "get_context_brief":
            from ultron.core.context_brief import generate_vibe_context_package
            intent = arguments.get("intent", "")
            repo = arguments.get("repo_path", os.getcwd())
            pkg = generate_vibe_context_package(intent, repo)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": pkg["prompt_package"]}]
                }
            }
        elif tool_name == "evaluate_repository":
            from ultron.core.pipeline.orchestrator import analyze_repository
            repo = arguments.get("repo_path", os.getcwd())
            run_id = analyze_repository(repo)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Repository evaluation completed. Run ID: {run_id}"}]
                }
            }
        elif tool_name == "explain_violation":
            from ultron.core import translate
            violation_id = arguments.get("violation_id", 0)
            explanation = translate.translate_violation_to_plain_english("RuleViolation", f"Violation ID #{violation_id}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(explanation, indent=2)}]
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
            }
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {}
        }

def run_mcp_server():
    log_err("Ultron MCP Middleware Server listening on stdio...")
    for line in sys.stdin:
        resp = handle_mcp_request(line)
        if resp:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    run_mcp_server()
