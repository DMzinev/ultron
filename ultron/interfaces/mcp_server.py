import sys
import os
import json
import traceback

# Configure sys.path to find moved files under their new subdirectories
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_dir, "..", ".."))
for _subdir in ["core", "experimental", "interfaces", "validation", "tests"]:
    sys.path.append(os.path.abspath(os.path.join(_root, "ultron", _subdir)))
sys.path.append(_root)
sys.path.append(os.path.abspath(os.path.join(_root, "umags")))

import analyzer
import risk
import prompt
import classifier

# Standard tool definitions
TOOLS = [
    {
        "name": "analyze_codebase",
        "description": "Analyzes the codebase structure, McCabe complexity, module coupling, and generates integration risk scores.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Absolute path to the codebase repository root directory."
                },
                "intent": {
                    "type": "string",
                    "description": "The natural language change intent or description of the modification."
                },
                "files": {
                    "type": "string",
                    "description": "Comma-separated list of relative file paths targeted for modification."
                }
            },
            "required": ["repo"]
        }
    },
    {
        "name": "audit_file_anomalies",
        "description": "Audits a modified file for statistical anomalies (spelling typos / name confusion and Markovian call sequence flows).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Absolute path to the codebase repository root directory."
                },
                "target_file": {
                    "type": "string",
                    "description": "Absolute path to the modified python file to audit."
                },
                "typo_threshold": {
                    "type": "number",
                    "description": "Normalized string similarity threshold (0.0 to 1.0) for typo detection (default: 0.75).",
                    "default": 0.75
                },
                "prob_threshold": {
                    "type": "number",
                    "description": "Markov transition probability threshold (0.0 to 1.0) for call sequence anomaly detection (default: 0.0).",
                    "default": 0.0
                }
            },
            "required": ["repo", "target_file"]
        }
    },
    {
        "name": "generate_prompt",
        "description": "Generates a contract-pruned, optimized prompt with exact signatures and caller context for AI agents.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Absolute path to the codebase repository root directory."
                },
                "intent": {
                    "type": "string",
                    "description": "Natural language intent describing what modifications are planned."
                },
                "files": {
                    "type": "string",
                    "description": "Comma-separated list of relative file paths targeted for modification."
                }
            },
            "required": ["repo", "intent"]
        }
    }
]

def debug_log(msg):
    print(f"[Ultron-MCP] {msg}", file=sys.stderr, flush=True)

def handle_analyze_codebase(args):
    repo_path = os.path.abspath(args["repo"])
    if not os.path.isdir(repo_path):
        return f"Error: Repository path '{repo_path}' is not a directory."
        
    intent = args.get("intent", "")
    files_str = args.get("files", "")
    target_files = [f.strip() for f in files_str.split(",") if f.strip()] if files_str else []
    
    codebase = analyzer.analyze_directory(repo_path)
    risks = risk.evaluate_risks(codebase, target_files, intent, repo_path=repo_path)
    
    return json.dumps({
        "success": True,
        "risks_evaluated": len(risks),
        "risks": risks
    }, indent=2)

def handle_audit_file_anomalies(args):
    repo_path = os.path.abspath(args["repo"])
    if not os.path.isdir(repo_path):
        return f"Error: Repository path '{repo_path}' is not a directory."
        
    target_file = os.path.abspath(args["target_file"])
    if not os.path.exists(target_file):
        return f"Error: Target file '{target_file}' does not exist."
        
    typo_threshold = float(args.get("typo_threshold", 0.75))
    prob_threshold = float(args.get("prob_threshold", 0.0))
    
    names, probs = classifier.build_models(repo_path, exclude_file=target_file)
    anomalies = classifier.audit_target_file(
        target_file, 
        names, 
        probs, 
        typo_threshold=typo_threshold, 
        prob_threshold=prob_threshold
    )
    
    return json.dumps({
        "success": True,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies
    }, indent=2)

def handle_generate_prompt(args):
    repo_path = os.path.abspath(args["repo"])
    if not os.path.isdir(repo_path):
        return f"Error: Repository path '{repo_path}' is not a directory."
        
    intent = args["intent"]
    files_str = args.get("files", "")
    target_files = [f.strip() for f in files_str.split(",") if f.strip()] if files_str else []
    
    codebase = analyzer.analyze_directory(repo_path)
    risks = risk.evaluate_risks(codebase, target_files, intent, repo_path=repo_path)
    opt_prompt = prompt.generate_optimized_prompt(intent, codebase, risks)
    
    return opt_prompt

def serve():
    debug_log("Starting stdio MCP Server...")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            req = json.loads(line)
            method = req.get("method")
            msg_id = req.get("id")
            
            # Respond to JSON-RPC initialization
            if method == "initialize":
                res = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "ultron-pre-execution-layer",
                            "version": "1.0.0"
                        }
                    }
                }
            elif method == "tools/list":
                res = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": TOOLS
                    }
                }
            elif method == "tools/call":
                params = req.get("params", {})
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                
                debug_log(f"Calling tool: {tool_name}")
                
                try:
                    if tool_name == "analyze_codebase":
                        result_text = handle_analyze_codebase(tool_args)
                    elif tool_name == "audit_file_anomalies":
                        result_text = handle_audit_file_anomalies(tool_args)
                    elif tool_name == "generate_prompt":
                        result_text = handle_generate_prompt(tool_args)
                    else:
                        raise ValueError(f"Unknown tool: {tool_name}")
                        
                    res = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": result_text
                                }
                            ]
                        }
                    }
                except Exception as tool_err:
                    res = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {
                            "code": -32603,
                            "message": str(tool_err),
                            "data": traceback.format_exc()
                        }
                    }
            else:
                # Handle unhandled methods gracefully (initialized notifications, etc.)
                if msg_id is not None:
                    res = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {}
                    }
                else:
                    continue
                    
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as e:
            debug_log(f"Global exception in event loop: {e}")
            debug_log(traceback.format_exc())

if __name__ == "__main__":
    serve()
