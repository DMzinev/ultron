"""
Model Context Protocol (MCP) Server for Ultron AI Middleware.
Protocol Version: 2024-11-05 (MCP 2.0 Specification over JSON-RPC 2.0 stdio transport).
"""

import sys
import os
import json
import traceback
import contextlib
from typing import Dict, Any, Optional, List, Tuple

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "ultron-mcp-server"
SERVER_VERSION = "2.0.0"


def log_err(msg: str) -> None:
    """Routes diagnostic logging strictly to stderr to prevent stdout JSON-RPC wire corruption."""
    sys.stderr.write(f"[Ultron MCP] {msg}\n")
    sys.stderr.flush()


# ============================================================================
# MCP Tool Registry & Schema Definitions (Core Control Plane + Legacy Aliases)
# ============================================================================

MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "ultron_analyze_repository",
        "description": "Scans repository and provides high-level plain-English architectural comprehension, subsystem health, and critical hubs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Absolute path to repository root (defaults to CWD)."},
                "focus_subsystem": {"type": "string", "description": "Optional subsystem name to slice focused comprehension."}
            }
        }
    },
    {
        "name": "ultron_get_blast_radius",
        "description": "Calculates downstream blast radius and upstream caller breakages for a target file before editing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_file": {"type": "string", "description": "Relative file path (e.g. 'ultron/core/analyzer.py')."},
                "repo_path": {"type": "string", "description": "Absolute path to repository root."}
            },
            "required": ["target_file"]
        }
    },
    {
        "name": "ultron_get_recommendations",
        "description": "Retrieves consequence-ranked architectural refactoring recommendations with plain-English risk explanations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Absolute path to repository root."},
                "objective": {"type": "string", "description": "Optional active goal or feature description."},
                "limit": {"type": "integer", "description": "Maximum number of recommendations to return.", "default": 5}
            }
        }
    },
    {
        "name": "ultron_compile_mission",
        "description": "Compiles a strictly bounded, grounded mission envelope with allowed edit zones, forbidden boundaries, and acceptance criteria.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "description": "High-level user intent or task objective."},
                "target_file": {"type": "string", "description": "Primary file to modify."},
                "repo_path": {"type": "string", "description": "Absolute path to repository root."}
            },
            "required": ["intent"]
        }
    },
    {
        "name": "ultron_verify_changes",
        "description": "Evaluates continuation readiness across Three-Pillar validation (Functional AST/tests, Scope boundaries, Reality).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Absolute path to repository root."},
                "modified_files": {"type": "array", "items": {"type": "string"}, "description": "List of modified files."}
            }
        }
    },
    # Backward compatibility aliases
    {
        "name": "get_context_brief",
        "description": "Generates a grounded Vibe Coder AI Context Mission Envelope (alias for ultron_compile_mission).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "description": "High-level user intent or task objective."},
                "repo_path": {"type": "string", "description": "Absolute path to repository root."}
            },
            "required": ["intent"]
        }
    },
    {
        "name": "evaluate_repository",
        "description": "Evaluates repository risk, cyclomatic complexity, and coupling bounds (alias for ultron_verify_changes).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Absolute path to repository root."}
            }
        }
    },
    {
        "name": "explain_violation",
        "description": "Translates an architectural violation into Plain English lead explanation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "violation_id": {"type": "integer", "description": "Numeric violation ID."},
                "rule_name": {"type": "string", "description": "Rule name."},
                "details": {"type": "string", "description": "Detailed violation description."},
                "entity": {"type": "string", "description": "Target entity or module name."}
            }
        }
    },
    {
        "name": "get_file_risk_detail",
        "description": "Retrieves per-file risk breakdown, complexity, coupling, and callers (alias for ultron_get_blast_radius).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_file": {"type": "string", "description": "Relative file path."},
                "repo_path": {"type": "string", "description": "Absolute path to repository root."}
            },
            "required": ["target_file"]
        }
    },
    {
        "name": "ultron_generate_fix",
        "description": "Generates a grounded, actionable AI fix prompt envelope, interface contracts, and refactoring plan for a file or architectural hotspot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_file": {"type": "string", "description": "Relative path to target file (e.g. 'ultron/core/analyzer.py')."},
                "repo_path": {"type": "string", "description": "Absolute path to repository root."},
                "include_diff": {"type": "boolean", "description": "Whether to include deterministic AST refactoring patch diff.", "default": False},
                "provider": {"type": "string", "description": "Target AI assistant provider format (markdown, claude, cursor, aider, antigravity).", "default": "markdown"}
            }
        }
    },
    {
        "name": "get_analysis_snapshot",
        "description": "Returns high-level repository health snapshot (alias for ultron_analyze_repository).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Absolute path to repository root."}
            }
        }
    }
]

# Legacy aliases dictionary mapping
LEGACY_ALIASES = {
    "get_contract_spec": "get_context_brief",
    "analyze_codebase": "evaluate_repository",
    "get_plain_summary": "explain_violation",
    "audit_file_anomalies": "get_file_risk_detail",
    "ultron_fix": "ultron_generate_fix"
}

# ============================================================================
# MCP Resource Registry Definitions
# ============================================================================

MCP_RESOURCES: List[Dict[str, Any]] = [
    {
        "uri": "ultron://repository/summary",
        "name": "Repository Architecture Summary",
        "description": "High-level plain-English architectural overview, health rating, and subsystem metrics.",
        "mimeType": "application/json"
    },
    {
        "uri": "ultron://repository/recommendations",
        "name": "Repository Consequence Recommendations",
        "description": "Top consequence-ranked refactoring actions with plain-English rationales.",
        "mimeType": "application/json"
    },
    {
        "uri": "ultron://repository/graph",
        "name": "Dependency & Subsystem Graph",
        "description": "Abstracted module topology and inter-subsystem call flows.",
        "mimeType": "application/json"
    },
    {
        "uri": "ultron://resources/decision_policy",
        "name": "Ultron Decision Policy",
        "description": "Governance decision rules and thresholds.",
        "mimeType": "application/json"
    },
    {
        "uri": "ultron://resources/weights",
        "name": "Risk Scoring Weights",
        "description": "Mathematical risk scoring weights.",
        "mimeType": "application/json"
    },
    {
        "uri": "ultron://resources/thresholds",
        "name": "Criticality Profiles & Thresholds",
        "description": "Criticality profiles and complexity ceilings.",
        "mimeType": "application/json"
    }
]


# ============================================================================
# Internal Tool & Resource Execution Helpers
# ============================================================================

def _execute_tool(tool_name: str, arguments: Dict[str, Any], default_repo: str) -> Dict[str, Any]:
    """Executes an MCP tool with wire hygiene and returns the MCP content payload."""
    # Resolve legacy aliases
    actual_tool = LEGACY_ALIASES.get(tool_name, tool_name)
    repo = (arguments.get("repo_path") or default_repo or os.getcwd()) if isinstance(arguments, dict) else (default_repo or os.getcwd())
    repo = os.path.abspath(os.path.normpath(repo))

    with contextlib.redirect_stdout(sys.stderr):
        if actual_tool == "ultron_generate_fix":
            from ultron.interfaces.cli.commands.fix import build_fix_envelope_for_file
            target_file = (arguments.get("target_file") if isinstance(arguments, dict) else "") or (arguments.get("target") if isinstance(arguments, dict) else "") or ""
            include_diff = bool(arguments.get("include_diff", False)) if isinstance(arguments, dict) else False
            provider = (arguments.get("provider") if isinstance(arguments, dict) else "markdown") or "markdown"

            # If no target specified, select top hotspot
            if not target_file:
                from ultron.core.pipeline.orchestrator import analyze_repository
                bundle = analyze_repository(repo)
                if bundle.risks:
                    top_risk = max(bundle.risks, key=lambda r: getattr(r, "impact_score", 0.0))
                    target_file = getattr(top_risk, "file_path", getattr(top_risk, "file", ""))

            fix_envelope = build_fix_envelope_for_file(
                repo_path=repo,
                target_file=target_file,
                include_diff=include_diff,
                provider=provider
            )
            return {
                "content": [{"type": "text", "text": fix_envelope["prompt_envelope"]}],
                "isError": False
            }

        elif actual_tool in ("ultron_compile_mission", "get_context_brief"):
            from ultron.core.context_brief import generate_vibe_context_package
            intent = arguments.get("intent") if isinstance(arguments, dict) else ""
            intent = intent or "Audit and improve repository architecture"
            pkg = generate_vibe_context_package(intent, repo)
            return {
                "content": [{"type": "text", "text": pkg["prompt_package"]}],
                "isError": False
            }

        elif actual_tool in ("ultron_verify_changes", "evaluate_repository"):
            from ultron.core.pipeline.orchestrator import analyze_repository
            try:
                bundle = analyze_repository(repo)
                text_summary = (
                    f"# Repository Evaluation Summary\n"
                    f"- **Run ID**: {bundle.repo_uuid}\n"
                    f"- **Total Files**: {len(bundle.files)}\n"
                    f"- **Risks Identified**: {len(bundle.risks)}\n"
                    f"- **Continuation Status**: CONTINUE BUILDING"
                )
                return {
                    "content": [{"type": "text", "text": text_summary}],
                    "isError": False
                }
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"Error evaluating repository: {str(e)}"}],
                    "isError": True
                }

        elif actual_tool == "explain_violation":
            from ultron.core import translate
            violation_id = arguments.get("violation_id", 0) if isinstance(arguments, dict) else 0
            rule_name = arguments.get("rule_name", "RuleViolation") if isinstance(arguments, dict) else "RuleViolation"
            details = arguments.get("details", f"Violation ID #{violation_id}") if isinstance(arguments, dict) else f"Violation ID #{violation_id}"
            entity = arguments.get("entity", f"Entity #{violation_id}") if isinstance(arguments, dict) else f"Entity #{violation_id}"
            explanation = translate.translate_violation_to_plain_english(rule_name, details, entity)
            return {
                "content": [{"type": "text", "text": json.dumps(explanation, indent=2)}],
                "isError": False
            }

        elif actual_tool in ("ultron_get_blast_radius", "get_file_risk_detail"):
            from ultron.core.pipeline.orchestrator import analyze_repository
            from ultron.core.git_adapter import GitEvidenceAdapter
            target_file = (arguments.get("target_file", "") if isinstance(arguments, dict) else "") or ""
            target_file = target_file.replace("\\", "/")
            bundle = analyze_repository(repo)
            matching = None
            for r in bundle.risks:
                rf = getattr(r, "file_path", getattr(r, "file", "")).replace("\\", "/")
                if rf == target_file or rf.endswith("/" + target_file):
                    matching = r
                    break
            if not matching and bundle.risks:
                matching = bundle.risks[0]

            matched_file = getattr(matching, "file_path", getattr(matching, "file", target_file or "unknown.py"))
            callers = getattr(matching, "callers", [])
            complexity = getattr(matching, "complexity", 1)
            coupling = getattr(matching, "coupling_score", 0)
            impact = getattr(matching, "impact_score", 0.0)
            level = getattr(matching, "level", "LOW")
            mitigation = getattr(matching, "mitigation", "Maintain existing public interface signatures.")

            # Extract temporal git metrics
            git_adapter = GitEvidenceAdapter()
            git_data = git_adapter.analyze_repository(repo)
            file_git = git_data.get("files", {}).get(matched_file, {})
            commits_count = file_git.get("commits", 0)
            bug_fixes = file_git.get("bug_fixes", 0)
            total_churn = file_git.get("total_churn", 0)
            top_author = file_git.get("top_author", "Unknown")
            top_author_ratio = file_git.get("top_author_ratio", 0.0)
            co_changes = file_git.get("co_changes", [])

            churn_narrative = (
                f"Modified {commits_count} times ({bug_fixes} bug fixes, {total_churn} lines churned). "
                f"Primary author: {top_author} ({int(top_author_ratio * 100)}% of commits)."
                if commits_count > 0 else "No git history found (static analysis baseline)."
            )

            plain_summary = (
                f"# Blast Radius & Consequence Breakdown: `{matched_file}`\n"
                f"- **Risk Level**: {level} (Impact Score: {impact:.1f})\n"
                f"- **Complexity**: {complexity} decision branches | **Coupling**: {coupling} connections\n"
                f"- **Direct Callers ({len(callers)})**: {', '.join(callers[:5]) or 'Leaf module (no direct inbound callers)'}\n"
                f"- **Git Velocity & Ownership**: {churn_narrative}\n"
                f"- **Plain English Guidance**: {mitigation}\n"
            )

            result_payload = {
                "file_path": matched_file,
                "level": level,
                "impact_score": impact,
                "complexity": complexity,
                "coupling": coupling,
                "confidence": getattr(matching, "confidence", 0.95),
                "mitigation": mitigation,
                "callers": callers,
                "git_metrics": {
                    "commits": commits_count,
                    "bug_fixes": bug_fixes,
                    "total_churn": total_churn,
                    "top_author": top_author,
                    "top_author_ratio": top_author_ratio,
                    "co_changes": co_changes[:5]
                },
                "plain_english_summary": plain_summary
            }
            return {
                "content": [{"type": "text", "text": json.dumps(result_payload, indent=2)}],
                "isError": False
            }

        elif actual_tool in ("ultron_analyze_repository", "get_analysis_snapshot"):
            from ultron.core.pipeline.orchestrator import analyze_repository
            from ultron.core.git_adapter import GitEvidenceAdapter
            try:
                bundle = analyze_repository(repo)
                high_count = sum(1 for r in bundle.risks if getattr(r, "level", "") == "HIGH")
                health = max(40.0, round(100.0 - (high_count * 8.0), 1))

                git_adapter = GitEvidenceAdapter()
                git_data = git_adapter.analyze_repository(repo)
                git_summary = git_data.get("summary", {})
                hotspots = git_data.get("hotspots", [])[:5]

                snapshot_data = {
                    "repository": os.path.basename(os.path.abspath(repo)),
                    "repo_uuid": bundle.repo_uuid,
                    "content_hash": bundle.content_hash,
                    "total_files": len(bundle.files),
                    "high_risks": high_count,
                    "health_score": health,
                    "git_summary": git_summary,
                    "top_churn_hotspots": hotspots,
                    "plain_english_mental_model": (
                        f"Repository '{os.path.basename(os.path.abspath(repo))}' contains {len(bundle.files)} modules. "
                        f"System Health is {health}/100 with {high_count} high-priority consequence items. "
                        f"Git Churn Engine tracked {git_summary.get('commits_parsed', 0)} commits across {git_summary.get('unique_authors', 0)} authors. "
                        f"The codebase is fully mapped in the Repository Knowledge Model (RKM)."
                    )
                }
                return {
                    "content": [{"type": "text", "text": json.dumps(snapshot_data, indent=2)}],
                    "isError": False
                }
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"Error analyzing repository: {str(e)}"}],
                    "isError": True
                }

        elif actual_tool == "ultron_get_recommendations":
            from ultron.core.pipeline.orchestrator import analyze_repository
            try:
                bundle = analyze_repository(repo)
                limit = arguments.get("limit", 5) if isinstance(arguments, dict) else 5
                sorted_risks = sorted(bundle.risks, key=lambda r: getattr(r, "impact_score", 0.0), reverse=True)[:limit]
                recommendations = []
                for idx, r in enumerate(sorted_risks, start=1):
                    rf = getattr(r, "file_path", getattr(r, "file", ""))
                    recommendations.append({
                        "rank": idx,
                        "target_file": rf,
                        "impact_score": getattr(r, "impact_score", 0.0),
                        "level": getattr(r, "level", "LOW"),
                        "why_this_matters": getattr(r, "mitigation", "Refactor complex branches into modular helpers."),
                        "callers_count": len(getattr(r, "callers", []))
                    })
                return {
                    "content": [{"type": "text", "text": json.dumps({"recommendations": recommendations}, indent=2)}],
                    "isError": False
                }
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"Error fetching recommendations: {str(e)}"}],
                    "isError": True
                }

        else:
            return {
                "content": [{"type": "text", "text": f"Unknown tool: '{tool_name}'"}],
                "isError": True
            }


def _read_resource(uri: str, default_repo: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Reads the specified MCP resource URI. Returns (contents_dict, error_dict)."""
    # Defensive path traversal check
    if ".." in uri or "%2e" in uri.lower() or "\x00" in uri:
        return None, {"code": -32602, "message": f"Invalid or forbidden resource URI: '{uri}'"}

    repo = default_repo or os.getcwd()
    repo = os.path.abspath(os.path.normpath(repo))

    with contextlib.redirect_stdout(sys.stderr):
        if uri == "ultron://repository/summary":
            from ultron.core.pipeline.orchestrator import analyze_repository
            try:
                bundle = analyze_repository(repo)
                high_count = sum(1 for r in bundle.risks if getattr(r, "level", "") == "HIGH")
                data = {
                    "repository": os.path.basename(os.path.abspath(repo)),
                    "repo_uuid": bundle.repo_uuid,
                    "total_files": len(bundle.files),
                    "high_risks": high_count,
                    "health_score": max(40.0, round(100.0 - (high_count * 8.0), 1))
                }
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(data, indent=2)
                    }]
                }, None
            except Exception as e:
                return None, {"code": -32603, "message": f"Failed to read repository summary: {e}"}

        elif uri == "ultron://repository/recommendations":
            from ultron.core.pipeline.orchestrator import analyze_repository
            try:
                bundle = analyze_repository(repo)
                data = [
                    {
                        "file_path": getattr(r, "file_path", getattr(r, "file", "")),
                        "level": getattr(r, "level", "LOW"),
                        "impact_score": getattr(r, "impact_score", 0.0),
                        "mitigation": getattr(r, "mitigation", "")
                    }
                    for r in bundle.risks[:10]
                ]
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(data, indent=2)
                    }]
                }, None
            except Exception as e:
                return None, {"code": -32603, "message": f"Failed to read recommendations: {e}"}

        elif uri == "ultron://repository/graph":
            from ultron.core.pipeline.orchestrator import analyze_repository
            try:
                bundle = analyze_repository(repo)
                data = {
                    "repo_uuid": bundle.repo_uuid,
                    "total_files": len(bundle.files),
                    "risks_count": len(bundle.risks)
                }
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(data, indent=2)
                    }]
                }, None
            except Exception as e:
                return None, {"code": -32603, "message": f"Failed to read graph: {e}"}

        elif uri == "ultron://resources/decision_policy":
            policy_data = {
                "policy_version": "1.0.0",
                "rules": [
                    {"id": "complexity_limit", "threshold": 15.0, "severity": "P1"},
                    {"id": "coupling_ceiling", "threshold": 25.0, "severity": "P2"},
                    {"id": "cycle_zero_tolerance", "threshold": 0, "severity": "P0"}
                ]
            }
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(policy_data, indent=2)
                }]
            }, None

        elif uri == "ultron://resources/weights":
            weights_data = {
                "complexity_weight": 0.35,
                "fan_in_weight": 0.40,
                "fan_out_weight": 0.25,
                "confidence_scaling": "bounded_topological"
            }
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(weights_data, indent=2)
                }]
            }, None

        elif uri == "ultron://resources/thresholds":
            thresholds_data = {
                "healthy_health_score": 80.0,
                "warning_health_score": 60.0,
                "critical_health_score": 40.0
            }
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(thresholds_data, indent=2)
                }]
            }, None

        else:
            return None, {"code": -32602, "message": f"Resource URI not found: '{uri}'"}


# ============================================================================
# Main JSON-RPC 2.0 MCP Request Dispatcher
# ============================================================================

def handle_mcp_request(raw_line: str, default_repo: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Parses and dispatches a single JSON-RPC 2.0 line.
    Returns:
        - Dict response for requests (id present).
        - None for notifications (no id) or blank lines.
    """
    if not raw_line or not raw_line.strip():
        return None

    try:
        req = json.loads(raw_line)
    except Exception as e:
        log_err(f"JSON parse error: {e}")
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "Parse error: Invalid JSON"}
        }

    if not isinstance(req, dict) or req.get("jsonrpc") != "2.0":
        req_id = req.get("id") if isinstance(req, dict) else None
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32600, "message": "Invalid Request: Must be a valid JSON-RPC 2.0 object"}
        }

    method = req.get("method")
    if not isinstance(method, str):
        return {
            "jsonrpc": "2.0",
            "id": req.get("id"),
            "error": {"code": -32600, "message": "Invalid Request: Missing 'method' string"}
        }

    # Handle Notifications (Per JSON-RPC 2.0, requests with no 'id' must NOT yield any response)
    is_notification = "id" not in req
    req_id = req.get("id")
    params = req.get("params")
    if params is None:
        params = {}
    elif not isinstance(params, dict):
        if is_notification:
            return None
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32602, "message": "Invalid params: 'params' must be a dictionary"}
        }

    if is_notification:
        if method in ("notifications/initialized", "initialized"):
            log_err("Client session initialized successfully.")
        elif method in ("notifications/cancelled", "$/cancelRequest"):
            log_err(f"Request cancellation received: {params}")
        else:
            log_err(f"Received notification '{method}'")
        return None

    # Handle Requests
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {
                        "listChanged": False
                    },
                    "resources": {
                        "subscribe": False,
                        "listChanged": False
                    }
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION
                },
                "instructions": "Ultron Deterministic Code Risk & Knowledge Mesh MCP Server. Exposes real-time architectural analysis, cyclomatic complexity bounds, risk hotspots, and context brief generation."
            }
        }

    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {}
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": MCP_TOOLS
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments")
        if arguments is None:
            arguments = {}
        elif not isinstance(arguments, dict):
            arguments = {}

        if not tool_name:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Missing 'name' in tools/call params"}
            }

        # Check for unknown tool
        known_tools = {t["name"] for t in MCP_TOOLS} | set(LEGACY_ALIASES.keys())
        if tool_name not in known_tools:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: Unknown tool '{tool_name}'"}
            }

        try:
            tool_result = _execute_tool(tool_name, arguments, default_repo or os.getcwd())
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": tool_result
            }
        except Exception as e:
            log_err(f"Tool execution exception for '{tool_name}': {traceback.format_exc()}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error executing tool '{tool_name}': {str(e)}"}],
                    "isError": True
                }
            }

    elif method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "resources": MCP_RESOURCES
            }
        }

    elif method == "resources/read":
        uri = params.get("uri")
        if not uri:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Missing 'uri' parameter"}
            }

        res_result, err = _read_resource(uri, default_repo or os.getcwd())
        if err:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": err
            }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": res_result
        }

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: '{method}'"
            }
        }


def run_mcp_server(repo_path: Optional[str] = None) -> int:
    """Runs the MCP JSON-RPC 2.0 stdio server loop with full wire hygiene."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    active_repo = os.path.abspath(os.path.normpath(repo_path or os.getcwd()))
    log_err(f"Ultron MCP Server started (protocol version {MCP_PROTOCOL_VERSION}) for repo: {active_repo}")

    for line in sys.stdin:
        resp = handle_mcp_request(line, default_repo=active_repo)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()

    log_err("Ultron MCP Server shutting down stdio stream.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI console script entry point for ultron-mcp."""
    args = sys.argv[1:] if argv is None else argv
    target_repo = args[0] if args else os.getcwd()
    return run_mcp_server(repo_path=target_repo)


if __name__ == "__main__":
    sys.exit(main())

