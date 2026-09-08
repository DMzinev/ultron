# Model Context Protocol (MCP) Server for Ultron AI Middleware
import sys
import os
import json
import traceback

def log_err(msg):
    """Routes diagnostic logging strictly to stderr to prevent stdout JSON-RPC corruption."""
    sys.stderr.write(f"[Ultron MCP] {msg}\n")
    sys.stderr.flush()

def _resolve_paths(file_param, repo_param=None):
    """Normalizes repo and target file paths cross-platform with forward-slash POSIX format."""
    abs_repo = os.path.abspath(repo_param or os.getcwd())
    if not file_param:
        return abs_repo, None, None
    raw_file = str(file_param).replace("\\", "/")
    abs_target = raw_file if os.path.isabs(raw_file) else os.path.normpath(os.path.join(abs_repo, raw_file))
    abs_target = os.path.abspath(abs_target)
    norm_rel = os.path.relpath(abs_target, abs_repo).replace("\\", "/")
    return abs_repo, abs_target, norm_rel

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
                "serverInfo": {"name": "ultron-mcp-middleware", "version": "1.4.0"}
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
                    },
                    {
                        "name": "get_risk_profile",
                        "description": "Calculates file risk profile (LOW/MEDIUM/HIGH), impact score, McCabe complexity, coupling callers, and 4-signal confidence basis.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string", "description": "Path to target file within repository."},
                                "repo_path": {"type": "string", "description": "Absolute path to repository root (defaults to current working directory)."}
                            },
                            "required": ["file_path"]
                        }
                    },
                    {
                        "name": "get_blast_radius",
                        "description": "Traces downstream dependent files that directly or transitively break if this target file is modified.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string", "description": "Path to target file within repository."},
                                "repo_path": {"type": "string", "description": "Absolute path to repository root (defaults to current working directory)."},
                                "max_depth": {"type": "integer", "description": "Maximum transitive depth to trace dependents (default 3)."}
                            },
                            "required": ["file_path"]
                        }
                    },
                    {
                        "name": "compile_mission",
                        "description": "Generates the grounded 7-field AI agent mission envelope with blast radius, must-not-touch public signatures, complexity ceiling, and verification commands.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "target_file": {"type": "string", "description": "Path to target file within repository."},
                                "intent": {"type": "string", "description": "High-level user intent or refactor task objective."},
                                "repo_path": {"type": "string", "description": "Absolute path to repository root (defaults to current working directory)."},
                                "format": {"type": "string", "enum": ["json", "markdown"], "description": "Output format: 'json' (default) returns structured envelope; 'markdown' returns rendered prompt string."}
                            },
                            "required": ["target_file"]
                        }
                    },
                    {
                        "name": "audit_file",
                        "description": "Audits a Python source file for name confusion, typos, and call sequence anomalies.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "target_file": {"type": "string", "description": "Path to target file within repository."},
                                "repo_path": {"type": "string", "description": "Absolute path to repository root (defaults to current working directory)."},
                                "typo_threshold": {"type": "number", "description": "String similarity ratio threshold (default 0.75)."}
                            },
                            "required": ["target_file"]
                        }
                    }
                ]
            }
        }
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        try:
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
            elif tool_name == "get_risk_profile":
                raw_path = arguments.get("file_path") or arguments.get("target_file")
                if not raw_path:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": "Missing required parameter: 'file_path'"}],
                            "isError": True
                        }
                    }
                abs_repo, abs_target, norm_rel = _resolve_paths(raw_path, arguments.get("repo_path"))
                if not os.path.exists(abs_target):
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": f"File not found: '{abs_target}'"}],
                            "isError": True
                        }
                    }

                from ultron.core import analyzer
                from ultron.core.risk import scoring
                codebase = analyzer.analyze_directory(abs_repo)
                risks = scoring.evaluate_risks(codebase, target_files=[], repo_path=abs_repo)
                
                matched_packet = None
                for r in risks:
                    r_path = str(getattr(r, "file_path", "")).replace("\\", "/")
                    if r_path == norm_rel or os.path.basename(r_path) == os.path.basename(norm_rel):
                        matched_packet = r
                        break

                if matched_packet:
                    res_dict = matched_packet.to_dict()
                else:
                    from ultron.core.rkm.risk_intelligence import compute_risk_profile
                    prof = compute_risk_profile(norm_rel, complexity=1.0, coupling_fanout=0, repo_path=abs_repo)
                    res_dict = {
                        "file_path": norm_rel,
                        "level": "LOW",
                        "impact_score": round(prof.score, 2),
                        "complexity": 1.0,
                        "coupling_score": 0,
                        "callers": [],
                        "confidence": round(prof.confidence_vector.get("overall", 0.6), 2),
                        "signals": prof.signals,
                        "mitigation": "No immediate architectural risks detected."
                    }

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(res_dict, indent=2)}]
                    }
                }
            elif tool_name == "get_blast_radius":
                raw_path = arguments.get("file_path") or arguments.get("target_file")
                if not raw_path:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": "Missing required parameter: 'file_path'"}],
                            "isError": True
                        }
                    }
                abs_repo, abs_target, norm_rel = _resolve_paths(raw_path, arguments.get("repo_path"))
                if not os.path.exists(abs_target):
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": f"File not found: '{abs_target}'"}],
                            "isError": True
                        }
                    }
                max_depth = int(arguments.get("max_depth", 3))

                if max_depth <= 0:
                    res_dict = {
                        "target_file": norm_rel,
                        "blast_radius": [],
                        "blast_count": 0,
                        "dependencies": [],
                        "is_leaf": True,
                        "blast_score": 0.0,
                        "explanation": f"Max depth is {max_depth}; blast radius tracing omitted for '{norm_rel}'."
                    }
                else:
                    from ultron.core import analyzer
                    from ultron.core.risk import scoring
                    codebase = analyzer.analyze_directory(abs_repo)
                    risks = scoring.evaluate_risks(codebase, target_files=[], repo_path=abs_repo)
                    
                    target_callers = []
                    target_comp = 1.0
                    for r in risks:
                        r_path = str(getattr(r, "file_path", "")).replace("\\", "/")
                        if r_path == norm_rel or os.path.basename(r_path) == os.path.basename(norm_rel):
                            target_callers = [str(c).replace("\\", "/") for c in getattr(r, "callers", [])]
                            target_comp = float(getattr(r, "complexity", 1.0))
                            break

                    blast_radius = sorted(list(set(c for c in target_callers if c != norm_rel)))
                    
                    target_data = codebase.get(norm_rel, {})
                    if not target_data:
                        for k, v in codebase.items():
                            if k.replace("\\", "/") == norm_rel or os.path.basename(k) == os.path.basename(norm_rel):
                                target_data = v
                                break
                    dependencies = sorted(list(set(target_data.get("imports", []))))
                    
                    blast_score = round(len(blast_radius) * 1.5 * (target_comp ** 0.5), 2)
                    res_dict = {
                        "target_file": norm_rel,
                        "blast_radius": blast_radius,
                        "blast_count": len(blast_radius),
                        "dependencies": dependencies,
                        "is_leaf": len(blast_radius) == 0,
                        "blast_score": blast_score,
                        "explanation": (
                            f"Leaf module with 0 downstream dependents."
                            if len(blast_radius) == 0
                            else f"{len(blast_radius)} module(s) directly or transitively depend on '{norm_rel}'."
                        )
                    }

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(res_dict, indent=2)}]
                    }
                }
            elif tool_name == "compile_mission":
                raw_path = arguments.get("target_file") or arguments.get("file_path")
                if not raw_path:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": "Missing required parameter: 'target_file'"}],
                            "isError": True
                        }
                    }
                abs_repo, abs_target, norm_rel = _resolve_paths(raw_path, arguments.get("repo_path"))
                if not os.path.exists(abs_target):
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": f"File not found: '{abs_target}'"}],
                            "isError": True
                        }
                    }

                intent = arguments.get("intent", "")
                fmt = str(arguments.get("format", "json")).lower()

                from ultron.core.prompt import compile_mission_envelope
                envelope = compile_mission_envelope(
                    intent=intent,
                    target_file=norm_rel,
                    repo_path=abs_repo
                )

                if fmt == "markdown":
                    text_out = envelope.get("rendered_prompt", "")
                else:
                    text_out = json.dumps(envelope, indent=2)

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": text_out}]
                    }
                }
            elif tool_name == "audit_file":
                raw_path = arguments.get("target_file") or arguments.get("file_path")
                if not raw_path:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": "Missing required parameter: 'target_file'"}],
                            "isError": True
                        }
                    }
                abs_repo, abs_target, norm_rel = _resolve_paths(raw_path, arguments.get("repo_path"))
                if not os.path.exists(abs_target):
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": f"File not found: '{abs_target}'"}],
                            "isError": True
                        }
                    }

                typo_thresh = float(arguments.get("typo_threshold", 0.75))

                from ultron.core import classifier
                names = classifier.build_models(abs_repo, exclude_file=abs_target)
                anomalies = classifier.audit_target_file(
                    abs_target,
                    names,
                    typo_threshold=typo_thresh
                )

                res_dict = {
                    "target_file": norm_rel,
                    "status": "clean" if len(anomalies) == 0 else "anomalies_detected",
                    "anomaly_count": len(anomalies),
                    "anomalies": anomalies
                }

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(res_dict, indent=2)}]
                    }
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                }
        except Exception as e:
            log_err(f"Exception executing tool '{tool_name}': {e}\n{traceback.format_exc()}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error executing tool '{tool_name}': {str(e)}"}],
                    "isError": True
                }
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
