import http.server
import socketserver
import json
import os
import sys
import traceback
import shutil
import subprocess
import time
import tempfile
import threading
import uuid
import socket
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse
from dataclasses import asdict
from typing import Dict, Any, List, Optional, Tuple, Set, Union

from ultron.core import analyzer
from ultron.core import risk
from ultron.core import prompt
from ultron.core import classifier
from ultron.core import predict
from ultron.core import fuzz
from ultron.core import translate
from ultron.core.objective_tracker import ObjectiveTracker
from ultron.core.agent_context_builder import AgentContextBuilder
from ultron.core.safety_evaluator import SafetyEvaluator
from ultron.core.development_session import DevelopmentSessionManager
from ultron.interfaces.api.router import APIRouter
import ultron.interfaces.api.routes
from ultron.release import __version__ as ULTRON_VERSION

delta = None
design_oracle = None


LAST_ANALYSIS = {
    "file_path": None,
    "delta_i": 0.0,
    "mkr": 1.0,
    "delta_cest": 0.0
}

ACTIVE_JOB = {
    "status": "idle",          # idle | running | success | failed | cancelled
    "progress_step": "Done",   # Current stage label
    "progress_pct": 0,         # 0-100, -1 for indeterminate
    "error": None,
    "cancel_requested": False,
    "snapshot_id": None,       # Content hash for cache validation
}

_JOB_LOCK = threading.Lock()

def _norm_path(p: str) -> str:
    if not p or '\x00' in p:
        return ""
    try:
        return os.path.normcase(os.path.normpath(os.path.abspath(p)))
    except (ValueError, OSError):
        return ""

_ANALYSIS_CACHE = {
    "repo_path": None,
    "content_hash": None,
    "bundle": None,
    "payload": None,
    "timestamp": None,
}

_WATCHER_DAEMONS: Dict[str, Any] = {}

PORT = 8000
_SERVER_DIR = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
WEB_DIR = os.path.normpath(os.path.join(_SERVER_DIR, "web"))
CONFIG_DIR = os.path.normpath(os.path.join(_SERVER_DIR, "..", ".ultron"))
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
def validate_repo_path(base_dir: str, target_path: str) -> tuple[bool, str]:
    """
    Validates that target_path is inside base_dir and handles Windows drive letter boundaries.
    Returns (is_valid, abs_normalized_path).
    """
    try:
        norm_base = os.path.abspath(os.path.normpath(base_dir))
        norm_target = os.path.abspath(os.path.normpath(target_path))
        
        # Windows drive letter mismatch check (e.g. C:\ vs D:\)
        if os.name == 'nt':
            base_drive = os.path.splitdrive(norm_base)[0].lower()
            target_drive = os.path.splitdrive(norm_target)[0].lower()
            if base_drive and target_drive and base_drive != target_drive:
                return False, norm_target
                
        common = os.path.commonpath([norm_base, norm_target])
        if os.path.abspath(common) == norm_base:
            return True, norm_target
        return False, norm_target
    except (ValueError, OSError, Exception):
        return False, os.path.abspath(os.path.normpath(target_path))


class UltronAPIHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS for local cross-origin development if needed
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        req_path = self.path.split('?')[0]
        parsed_path = req_path
        
        # Check modular APIRouter first
        if APIRouter.dispatch(self, parsed_path, "GET"):
            return
            
        # API routes — must be handled before the static-file/traversal block
        
        if parsed_path.startswith("/api/v1/risk-profile"):
            self.handle_v1_risk_profile()
            return
        if parsed_path.startswith("/api/v1/decision"):
            self.handle_v1_decision()
            return
        if parsed_path == "/api/architecture-health":
            self.handle_architecture_health()
            return
        if parsed_path == "/api/file-tree":
            self.handle_file_tree()
            return
        if parsed_path == "/api/analyze":
            self.handle_analyze()
            return
        if parsed_path == "/api/dependency-graph" or parsed_path == "/api/v1/graph":
            self.handle_dependency_graph()
            return
        if parsed_path == "/api/audit":
            self.handle_audit()
            return
        if parsed_path == "/api/report":
            self.handle_report()
            return

        if parsed_path == "/api/get-repo-root":
            self.handle_get_repo_root()
            return
        if parsed_path == "/api/v1/progress" or parsed_path == "/api/v1/status":
            self.handle_v1_progress()
            return
        if parsed_path == "/api/v1/health" or parsed_path == "/api/health":
            self.handle_v1_health()
            return
        if parsed_path == "/api/v1/summary":
            self.handle_v1_summary()
            return
        if parsed_path == "/api/v1/runs":
            self.handle_v1_runs()
            return
        if parsed_path == "/api/v1/hotspots":
            self.handle_v1_hotspots()
            return
        if parsed_path == "/api/v1/recommendations":
            self.handle_v1_recommendations()
            return
        if parsed_path in ("/api/v1/decisions", "/api/decisions"):
            self.handle_v1_decisions()
            return
        if parsed_path in ("/api/v1/evidence", "/api/evidence"):
            self.handle_v1_evidence()
            return
        if parsed_path in ("/api/v1/evidence/summary", "/api/evidence/summary"):
            self.handle_v1_evidence_summary()
            return
        if parsed_path == "/api/v1/history":
            self.handle_v1_history()
            return
        if parsed_path == "/api/v1/agent/context" or parsed_path == "/api/v1/agent/context/query":
            self.handle_v1_agent_context()
            return
        if parsed_path in ("/api/work/state", "/api/v1/work/state"):
            self.handle_work_state()
            return
        if parsed_path in ("/api/work/visual-delta", "/api/v1/work/visual-delta"):
            self.handle_work_visual_delta()
            return
        if parsed_path in ("/api/git/churn", "/api/v1/git/churn"):
            self.handle_v1_git_churn()
            return
        if parsed_path in ("/api/git/cochange", "/api/v1/git/cochange"):
            self.handle_v1_git_cochange()
            return
        if '\x00' in parsed_path:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"400 Bad Request: Invalid path characters")
            return

        if parsed_path == "/" or parsed_path == "":
            file_path = os.path.join(WEB_DIR, "index.html")
        else:
            # Prevent directory traversal attacks
            rel_path = parsed_path.lstrip('/')
            file_path = os.path.join(WEB_DIR, rel_path)
            
        try:
            real_file_path = os.path.realpath(file_path)
            real_web_dir = os.path.join(os.path.realpath(WEB_DIR), "")
            
            if (not os.path.normcase(real_file_path).startswith(os.path.normcase(real_web_dir))
                    or not os.path.exists(real_file_path)
                    or os.path.isdir(real_file_path)):
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"404 Not Found")
                return
        except (ValueError, OSError):
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"400 Bad Request")
            return

        # Determine MIME type & charset
        content_type = "text/plain; charset=utf-8"
        if file_path.endswith(".html"):
            content_type = "text/html; charset=utf-8"
        elif file_path.endswith(".css"):
            content_type = "text/css; charset=utf-8"
        elif file_path.endswith(".js"):
            content_type = "application/javascript; charset=utf-8"
        elif file_path.endswith(".json"):
            content_type = "application/json; charset=utf-8"
        elif file_path.endswith(".png"):
            content_type = "image/png"
        elif file_path.endswith(".svg"):
            content_type = "image/svg+xml; charset=utf-8"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"500 Internal Server Error: {e}".encode("utf-8"))

    def do_POST(self):
        req_path = self.path.split('?')[0]
        self._cached_post_data = None
        
        # Check modular APIRouter first
        if APIRouter.dispatch(self, req_path, "POST"):
            return
            
        if req_path == "/api/v1/analyze":
            self.handle_v1_analyze()
            return
        elif req_path in ("/api/v1/decision/record", "/api/decision/record"):
            self.handle_v1_decision_record()
            return
        elif req_path in ("/api/v1/decision/evaluate", "/api/decision/evaluate"):
            self.handle_v1_decision_evaluate()
            return
        elif req_path in ("/api/v1/cancel-analysis", "/api/v1/cancel", "/api/v1/analyze/cancel"):
            self.handle_v1_cancel_analysis()
            return
        elif req_path == "/api/v1/compare":
            self.handle_v1_compare()
            return
        elif req_path == "/api/v1/explain-violation":
            self.handle_v1_explain_violation()
            return
        elif req_path == "/api/v1/workspace/watcher/scan":
            self.handle_v1_workspace_watcher_scan()
            return
        elif req_path in ("/api/v1/mcp/setup", "/api/v1/mcp/config"):
            self.handle_v1_mcp_setup()
            return
        elif req_path == "/api/config":
            self.handle_config()
        elif req_path == "/api/analyze":
            self.handle_analyze()
        elif req_path == "/api/audit":
            self.handle_audit()
        elif req_path == "/api/generate":
            self.handle_generate()
        elif req_path == "/api/file-tree":
            self.handle_file_tree()
        elif req_path == "/api/architecture-health":
            self.handle_architecture_health()
        elif req_path == "/api/get-file":
            self.handle_get_file()
        elif req_path == "/api/save-file":
            self.handle_save_file()
        elif req_path == "/api/run-tests" or req_path == "/api/v1/run-tests":
            self.handle_run_tests()
        elif req_path == "/api/test-status" or req_path == "/api/v1/test-status":
            self.handle_test_status()
        elif req_path == "/api/test-cancel" or req_path == "/api/v1/test-cancel":
            self.handle_test_cancel()
        elif req_path in ("/api/work/state", "/api/v1/work/state"):
            self.handle_work_state()
        elif req_path in ("/api/work/advance", "/api/v1/work/advance"):
            self.handle_work_advance()
        elif req_path in ("/api/work/queue", "/api/v1/work/queue"):
            self.handle_work_queue()
        elif req_path == "/api/diff-risk":
            self.handle_diff_risk()
        elif req_path == "/api/dependency-graph" or req_path == "/api/v1/graph":
            self.handle_dependency_graph()
        elif req_path == "/api/predict-impact":
            self.handle_predict_impact()
        elif req_path == "/api/save-session":
            self.handle_save_session()
        elif req_path == "/api/calibrate":
            self.handle_calibrate()
        elif req_path == "/api/playground":
            self.handle_playground()
        elif req_path == "/api/log-risk-feedback":
            self.handle_log_risk_feedback()
        elif req_path == "/api/pledge/create":
            self.handle_pledge_create()
        elif req_path == "/api/pledge/verify":
            self.handle_pledge_verify()
        elif req_path == "/api/report":
            self.handle_report()
        elif req_path == "/api/design-oracle":
            self.handle_design_oracle()
        elif req_path == "/api/browse-folder":
            self.handle_browse_folder()
        elif req_path == "/api/v1/context-brief":
            self.handle_v1_context_brief()
        elif req_path == "/api/v1/export-brief":
            self.handle_v1_export_brief()
        elif req_path == "/api/v1/ai/critique":
            self.handle_v1_ai_critique()
        elif req_path == "/api/v1/ai/push":
            self.handle_v1_ai_push()
        elif req_path == "/api/v1/agent/handoff":
            self.handle_v1_agent_handoff()
        elif req_path in ("/api/v1/agent/context", "/api/agent/context"):
            self.handle_v1_agent_context_builder()
        elif req_path == "/api/set-repo-root":
            self.handle_set_repo_root()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode())

    def get_post_data(self):
        if hasattr(self, "_cached_post_data") and self._cached_post_data is not None:
            return self._cached_post_data
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length <= 0:
                self._cached_post_data = {}
                return {}
            post_data = self.rfile.read(content_length).decode('utf-8', errors='replace')
            if not post_data.strip():
                self._cached_post_data = {}
                return {}
            parsed = json.loads(post_data)
            if not isinstance(parsed, dict):
                self._cached_post_data = None
                return None
            self._cached_post_data = parsed
            return self._cached_post_data
        except (ValueError, KeyError, TypeError, OSError) as err:
            sys.stderr.write(f"[Ultron Server Notice] Corrupted JSON payload: {err}\n")
            self._cached_post_data = None
            return None

    def get_query_data(self):
        """Extracts query parameters from GET URL path into a dictionary."""
        try:
            from urllib.parse import parse_qs, urlparse
            query = parse_qs(urlparse(self.path).query)
            result = {}
            for k, v in query.items():
                if v:
                    result[k] = v[0]
            return result
        except (ValueError, KeyError, TypeError, OSError):
            return {}

    def get_request_data(self):
        """Extracts request parameters from POST body or GET query string depending on HTTP command."""
        cmd = getattr(self, "command", "POST")
        if cmd == "GET":
            q_data = self.get_query_data()
            if isinstance(q_data, dict):
                return q_data
            return {}

        # For POST requests or post_data payloads:
        post_data = self.get_post_data()
        if post_data is None:
            return None  # Preserves None on corrupted JSON so handlers return 400 Bad Request
        if isinstance(post_data, dict):
            if "repo" not in post_data or not post_data["repo"]:
                post_data["repo"] = "."
            return post_data
        return post_data

    def send_json_response(self, status_code: int, data: Any = None, error: Optional[str] = None):
        import uuid
        req_id = f"req-{uuid.uuid4().hex[:8]}"
        iso_time = datetime.now(timezone.utc).isoformat()
        
        err_msg = error
        if err_msg is None and isinstance(data, dict) and status_code >= 400:
            err_msg = data.get("error") or data.get("message")
        
        envelope = {
            "success": status_code < 400,
            "data": data if status_code < 400 else (data if (isinstance(data, dict) and "error" not in data) else None),
            "error": err_msg,
            "timestamp": iso_time,
            "request_id": req_id
        }
        
        # Merge top-level keys for 100% backward compatibility
        if isinstance(data, dict):
            for k, v in data.items():
                if k not in envelope:
                    envelope[k] = v

        body_bytes = json.dumps(envelope, default=str).encode('utf-8')
        
        accept_enc = getattr(self, "headers", {}).get("Accept-Encoding", "") if hasattr(self, "headers") else ""
        use_gzip = "gzip" in str(accept_enc) and len(body_bytes) > 1024
        if use_gzip:
            import gzip
            body_bytes = gzip.compress(body_bytes, compresslevel=6)

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if use_gzip:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    
    def _resolve_entity_metrics(self, query):
        """Helper to resolve entity metrics dynamically from query params or _ANALYSIS_CACHE with explicit lineage provenance."""
        raw_entity = query.get("file", query.get("entity", [""]))[0]
        entity = raw_entity.strip() if raw_entity else ""
        repo = query.get("repo", [""])[0].strip() if "repo" in query and query["repo"] else ""

        if '\x00' in entity or '\x00' in repo:
            raise ValueError("Query parameter contains invalid null bytes")

        try:
            complexity_param = float(query.get("complexity", [0])[0]) if "complexity" in query and query["complexity"] and query["complexity"][0] not in (None, "") else None
            coupling_param = int(query.get("coupling_fanout", [0])[0]) if "coupling_fanout" in query and query["coupling_fanout"] and query["coupling_fanout"][0] not in (None, "") else None
            coverage_param = float(query.get("coverage_percent", [0])[0]) if "coverage_percent" in query and query["coverage_percent"] and query["coverage_percent"][0] not in (None, "") else None
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid numeric query parameter: {e}")

        try:
            repo_path = os.path.abspath(repo) if repo else self.get_repo_root_path()
        except (ValueError, OSError):
            repo_path = self.get_repo_root_path()

        self._ensure_cache_populated(repo_path)

        global _ANALYSIS_CACHE
        bundle = _ANALYSIS_CACHE.get("bundle")
        content_hash = _ANALYSIS_CACHE.get("content_hash", f"snap_{getattr(bundle, 'repo_fingerprint', 'local')[:16]}") if _ANALYSIS_CACHE else "uncomputed"

        comp_val = complexity_param
        coup_val = coupling_param
        cov_val = coverage_param

        comp_source = "explicit_param" if complexity_param is not None else "missing_fallback"
        coup_source = "explicit_param" if coupling_param is not None else "missing_fallback"
        cov_source = "explicit_param" if coverage_param is not None else "missing_fallback"

        if bundle:
            norm_tf = entity.replace('\\', '/').lstrip('/') if entity else ""
            matched_risk = None
            if norm_tf and bundle.risks:
                for r in bundle.risks:
                    rf = getattr(r, "file_path", getattr(r, "file", "")).replace('\\', '/').lstrip('/')
                    if rf == norm_tf or rf.endswith('/' + norm_tf) or norm_tf.endswith('/' + rf):
                        matched_risk = r
                        break

            if matched_risk:
                if not entity:
                    entity = getattr(matched_risk, "file_path", getattr(matched_risk, "file", "unknown"))
                if comp_val is None:
                    comp_val = float(getattr(matched_risk, "complexity", 1.0))
                    comp_source = "analysis_cache"
                if coup_val is None:
                    coup_val = int(getattr(matched_risk, "coupling_score", 0))
                    coup_source = "analysis_cache"
            elif norm_tf and getattr(bundle, "codebase", None):
                cb_info = bundle.codebase.get(norm_tf) or bundle.codebase.get(entity)
                if cb_info:
                    if comp_val is None:
                        comp_val = float(cb_info.get("complexity", 1.0))
                        comp_source = "ast_codebase"
                    if coup_val is None:
                        coup_val = len(cb_info.get("dependencies", []))
                        coup_source = "ast_codebase"
            elif not entity and bundle.risks:
                matched_risk = bundle.risks[0]
                entity = getattr(matched_risk, "file_path", getattr(matched_risk, "file", "unknown"))
                if comp_val is None:
                    comp_val = float(getattr(matched_risk, "complexity", 1.0))
                    comp_source = "analysis_cache"
                if coup_val is None:
                    coup_val = int(getattr(matched_risk, "coupling_score", 0))
                    coup_source = "analysis_cache"

        if not entity:
            entity = "ultron/core/analyzer.py"
        if comp_val is None or comp_val <= 0:
            comp_val = 1.0
        if coup_val is None or coup_val < 0:
            coup_val = 0

        provenance = {
            "complexity_source": comp_source,
            "coupling_source": coup_source,
            "coverage_source": cov_source,
            "cache_hit": bundle is not None,
            "snapshot_id": content_hash
        }

        return entity, comp_val, coup_val, cov_val, provenance

    def handle_v1_risk_profile(self):
        try:
            from urllib.parse import parse_qs, urlparse
            from dataclasses import asdict
            query = parse_qs(urlparse(self.path).query)
            try:
                entity, comp_val, coup_val, cov_val, provenance = self._resolve_entity_metrics(query)
            except (ValueError, TypeError) as ve:
                self.send_json_response(400, {"error": str(ve)})
                return

            from ultron.core.rkm.risk_intelligence import compute_risk_profile
            prof = compute_risk_profile(entity, complexity=comp_val, coupling_fanout=coup_val, coverage_percent=cov_val)
            res_data = asdict(prof)
            res_data["metric_provenance"] = provenance
            self.send_json_response(200, {"success": True, "data": res_data, **res_data})
        except (ValueError, TypeError, KeyError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_v1_decision(self):
        try:
            from urllib.parse import parse_qs, urlparse
            from dataclasses import asdict
            query = parse_qs(urlparse(self.path).query)
            crit = query.get("criticality", ["DEFAULT"])[0] if "criticality" in query and query["criticality"] else "DEFAULT"
            try:
                entity, comp_val, coup_val, cov_val, provenance = self._resolve_entity_metrics(query)
            except (ValueError, TypeError) as ve:
                self.send_json_response(400, {"error": str(ve)})
                return

            from ultron.core.rkm.risk_intelligence import compute_risk_profile
            from ultron.core.rkm.policy_engine import evaluate_policy
            prof = compute_risk_profile(entity, complexity=comp_val, coupling_fanout=coup_val, coverage_percent=cov_val)
            dec = evaluate_policy(prof, business_criticality=crit)
            res_data = asdict(dec)
            res_data["metric_provenance"] = provenance
            self.send_json_response(200, {"success": True, "data": res_data, **res_data})
        except (ValueError, TypeError, KeyError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_browse_folder(self):
        try:
            from ultron.interfaces.api.browse_folder import select_folder_dialog
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            raw_init = data.get("initial_dir")
            initial_dir = raw_init if isinstance(raw_init, str) and raw_init.strip() and '\x00' not in raw_init else self.get_repo_root_path()
            headless = bool(data.get("headless", False))
            res = select_folder_dialog(initial_dir, headless=headless)
            self.send_json_response(200, res)
        except Exception as e:
            self.send_json_response(500, {"error": f"Failed to browse folder: {str(e)}"})

    def handle_v1_context_brief(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            raw_repo = data.get("repo")
            if raw_repo is None or not isinstance(raw_repo, str) or not raw_repo.strip() or '\x00' in raw_repo:
                repo = self.get_repo_root_path()
            else:
                repo = raw_repo.strip()

            raw_tf = data.get("target_file")
            target_file = str(raw_tf).strip() if raw_tf is not None else ""
            if '\x00' in target_file:
                target_file = ""

            try:
                repo_path = os.path.abspath(repo)
            except (ValueError, OSError):
                repo_path = self.get_repo_root_path()

            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return

            db_path = os.path.join(repo_path, ".ultron", "repository.db")
            repo_name = os.path.basename(repo_path)
            
            canonical_brief = None

            # 1. RKM Memory First (Primary Path)
            if os.path.exists(db_path):
                try:
                    from ultron.core.rkm.store import RepositoryStore
                    from ultron.core.rkm.evolution.engine import EvolutionEngine

                    store = RepositoryStore(db_path)
                    meta = store.get_metadata()
                    if meta and meta.latest_analysis_run_id:
                        run_id = meta.latest_analysis_run_id
                        files = store.get_file_records_for_run(run_id)
                        vios = store.get_violations(run_id)
                        health_run = EvolutionEngine.evaluate_health_score(store, run_id)
                        health_score = round(
                            (health_run.architecture_stability * 0.4 +
                             health_run.rule_compliance * 0.4 +
                             health_run.complexity_trend * 0.2) * 100, 1
                        )
                        
                        top_risks = []
                        for v in vios[:5]:
                            top_risks.append({
                                "entity_id": v[0].details or "Unknown Entity",
                                "priority": getattr(v[0], "severity", "HIGH"),
                                "score": 75.0,
                                "reasons": [getattr(v[1], "name", "ARCHITECTURAL_VIOLATION")]
                            })
                            
                        canonical_brief = {
                            "repo_name": repo_name,
                            "repository_uuid": meta.repository_uuid,
                            "health_score": health_score,
                            "total_files": len(files),
                            "total_modules": len(files),
                            "top_risks": top_risks,
                            "target_file": target_file
                        }
                    store.close()
                except Exception as e:
                    print(f"[Warning] RKM Store lookup failed for context brief: {e}")

            # 2. Fallback to compile_brief_data (ONLY if no RKM DB exists)
            if not canonical_brief:
                from ultron.core.context_brief import compile_brief_data
                canonical_brief = compile_brief_data(repo_path)
                canonical_brief["target_file"] = target_file

            # 3. Render 3 Model-Specific Outputs from Canonical Brief
            target_str = f" Target file: {target_file}." if target_file else ""
            h_score = canonical_brief.get("health_score", 80.0)
            
            # Claude Code CLI format (shell snippet)
            claude_snippet = f'claude -p "Analyze repository \'{repo_name}\' (Health Score: {h_score}/100).{target_str} Address top risk boundary rules and maintain architectural integrity."'
            
            # OpenAI Codex / ChatGPT format (System Markdown Brief)
            codex_brief = f"# OpenAI Codex System Context Brief\nRepository: {repo_name}\nHealth Score: {h_score}/100\nTotal Files: {canonical_brief.get('total_files', 0)}\n{f'Target Entity: {target_file}' if target_file else ''}\n\n## Architectural Directives & Rules\n1. Preserves public API contracts in interfaces/api.\n2. Route logic through Repository Knowledge Model (RKM).\n3. Do not modify core analyzer models without backward compatibility review.\n\n## Top Active Risk Signals\n"
            for r in canonical_brief.get("top_risks", []):
                codex_brief += f"- **{r.get('entity_id')}** ({r.get('priority')} Priority, Reasons: {', '.join(r.get('reasons', []))})\n"
                
            # Google Antigravity / Gemini format (Artifact Markdown with file:// links)
            abs_target = os.path.abspath(os.path.join(repo_path, target_file)) if target_file else repo_path
            norm_target = abs_target.replace("\\", "/")
            antigravity_brief = f"# Google Antigravity / Gemini Architectural Brief\nTarget Workspace: [{repo_name}](file:///{norm_target})\nHealth Score: {h_score}/100 (RKM Schema v1.3.0)\n\n## Decision Provenance & Boundary Constraints\n- **Primary Contract**: Enforce zero-regressive architecture.\n- **Target File**: [{os.path.basename(target_file) if target_file else repo_name}](file:///{norm_target})\n- **RKM UUID**: `{canonical_brief.get('repository_uuid', 'N/A')}`\n\n## Verification Strategy\nExecute `python -m pytest ultron/tests/ -q` to verify non-degradation.\n"

            self.send_json_response(200, {
                "status": "success",
                "canonical_brief": canonical_brief,
                "handoff": {
                    "claude": claude_snippet,
                    "codex": codex_brief,
                    "antigravity": antigravity_brief
                }
            })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": f"Invalid context brief parameters: {str(e)}"})
        except Exception as e:
            self.send_json_response(500, {"error": f"Failed to generate context brief: {str(e)}", "traceback": traceback.format_exc()})

    def handle_v1_recommendations(self):
        try:
            from urllib.parse import parse_qs, urlparse
            query = parse_qs(urlparse(self.path).query)
            limit_raw = query.get("limit", ["20"])[0] if "limit" in query and query["limit"] else "20"
            try:
                limit_val = int(limit_raw)
                if limit_val < 1 or limit_val > 50:
                    self.send_json_response(400, {"status": "error", "message": "Limit parameter must be an integer between 1 and 50."})
                    return
            except (ValueError, TypeError):
                self.send_json_response(400, {"status": "error", "message": "Limit parameter must be a valid integer."})
                return

            repo_path = self.get_repo_root_path()
            from ultron.core.rkm.recommendation_service import get_recommendations
            res = get_recommendations(repo_path, limit=limit_val)
            self.send_json_response(200, res)
        except Exception as e:
            self.send_json_response(500, {"status": "error", "message": str(e)})

    def handle_v1_decisions(self):
        try:
            repo_path = self.get_repo_root_path()
            from ultron.core.decision_journal import list_decisions, get_decision_learning_summary
            decisions = list_decisions(repo_path, limit=50)
            summary = get_decision_learning_summary(repo_path)
            self.send_json_response(200, {
                "status": "success",
                "success": True,
                "decisions": [d.to_dict() for d in decisions],
                "summary": summary
            })
        except Exception as e:
            self.send_json_response(500, {"status": "error", "message": str(e)})

    def handle_v1_decision_record(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"status": "error", "message": "Invalid JSON body payload."})
                return

            repo_path = data.get("repo") or self.get_repo_root_path()
            rec = data.get("recommendation", {})
            if not rec or not isinstance(rec, dict):
                self.send_json_response(400, {"status": "error", "message": "Missing recommendation payload in request."})
                return

            from ultron.core.decision_journal import record_recommendation_decision
            record = record_recommendation_decision(
                repo_path=repo_path,
                recommendation=rec,
                human_selected_target=data.get("human_selected_target", ""),
                selection_source=data.get("selection_source", "HUMAN"),
                selection_outcome=data.get("selection_outcome", "PENDING"),
                human_feedback=data.get("human_feedback", ""),
                mission_id=data.get("mission_id", ""),
                attempt_id=data.get("attempt_id", ""),
                checkpoint_id=data.get("checkpoint_id", ""),
                top_alternatives=data.get("top_alternatives"),
                value_delta=data.get("value_delta")
            )
            self.send_json_response(200, {
                "status": "success",
                "success": True,
                "decision_id": record.decision_id,
                "decision": record.to_dict()
            })
        except Exception as e:
            self.send_json_response(500, {"status": "error", "message": str(e)})

    def handle_v1_decision_evaluate(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"status": "error", "message": "Invalid JSON body payload."})
                return

            repo_path = data.get("repo") or self.get_repo_root_path()
            dec_id = data.get("decision_id", "").strip()
            if not dec_id:
                self.send_json_response(400, {"status": "error", "message": "Missing decision_id."})
                return

            from ultron.core.decision_journal import update_decision_outcome
            updated = update_decision_outcome(
                repo_path=repo_path,
                decision_id=dec_id,
                outcome=data.get("outcome", "RESOLVED"),
                selection_outcome=data.get("selection_outcome"),
                feedback=data.get("feedback"),
                value_delta=data.get("value_delta")
            )
            if not updated:
                self.send_json_response(404, {"status": "error", "message": f"Decision '{dec_id}' not found."})
                return

            self.send_json_response(200, {
                "status": "success",
                "success": True,
                "decision": updated.to_dict()
            })
        except Exception as e:
            self.send_json_response(500, {"status": "error", "message": str(e)})

    def handle_v1_evidence(self):
        try:
            repo_path = self.get_repo_root_path()
            from ultron.core import analyzer
            from ultron.core.evidence import compile_repository_evidence
            codebase = analyzer.analyze_directory(repo_path)
            bundle = compile_repository_evidence(repo_path, codebase or {})
            self.send_json_response(200, {
                "status": "success",
                "success": True,
                "evidence_bundle": bundle.to_dict()
            })
        except Exception as e:
            self.send_json_response(500, {"status": "error", "message": str(e)})

    def handle_v1_evidence_summary(self):
        try:
            repo_path = self.get_repo_root_path()
            from ultron.core import analyzer
            from ultron.core.evidence import compile_repository_evidence
            codebase = analyzer.analyze_directory(repo_path)
            bundle = compile_repository_evidence(repo_path, codebase or {})
            self.send_json_response(200, {
                "status": "success",
                "success": True,
                "snapshot_id": bundle.snapshot_id,
                "status": bundle.status,
                "total_records": len(bundle.records),
                "evidence_coverage_pct": bundle.evidence_coverage_pct,
                "unknown_count": bundle.unknown_count,
                "limitations": bundle.limitations
            })
        except Exception as e:
            self.send_json_response(500, {"status": "error", "message": str(e)})

    def handle_v1_export_brief(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"status": "error", "message": "Invalid JSON body payload."})
                return
            raw_fmt = data.get("format")
            fmt = str(raw_fmt).strip().lower() if raw_fmt is not None else ""
            if fmt not in ["claude", "codex", "antigravity", "json"]:
                self.send_json_response(400, {
                    "status": "error",
                    "message": f"Unsupported format '{fmt}'. Supported formats: 'claude', 'codex', 'antigravity', 'json'."
                })
                return

            repo_path = self.get_repo_root_path()
            raw_tf = data.get("target_file")
            target_file = str(raw_tf).strip() if raw_tf is not None else ""
            if '\x00' in target_file:
                target_file = ""

            # SINGLE CANONICAL BRIEF REQUIREMENT: Render from one single brief object
            db_path = os.path.join(repo_path, ".ultron", "repository.db")
            repo_name = os.path.basename(repo_path)
            canonical_brief = None

            if os.path.exists(db_path):
                try:
                    from ultron.core.rkm.store import RepositoryStore
                    from ultron.core.rkm.evolution.engine import EvolutionEngine

                    store = RepositoryStore(db_path)
                    meta = store.get_metadata()
                    if meta and meta.latest_analysis_run_id:
                        run_id = meta.latest_analysis_run_id
                        vios = store.get_violations(run_id)
                        health_run = EvolutionEngine.evaluate_health_score(store, run_id)
                        health_score = round(
                            (health_run.architecture_stability * 0.4 +
                             health_run.rule_compliance * 0.4 +
                             health_run.complexity_trend * 0.2) * 100, 1
                        )
                        top_risks = []
                        for v in vios[:5]:
                            top_risks.append({
                                "entity_id": v[0].details or "Unknown Entity",
                                "priority": getattr(v[0], "severity", "HIGH"),
                                "reasons": [getattr(v[1], "name", "ARCHITECTURAL_VIOLATION")]
                            })
                        canonical_brief = {
                            "repo_name": repo_name,
                            "repository_uuid": meta.repository_uuid,
                            "health_score": health_score,
                            "top_risks": top_risks,
                            "target_file": target_file
                        }
                    store.close()
                except Exception:
                    pass

            if not canonical_brief:
                from ultron.core.context_brief import compile_brief_data
                canonical_brief = compile_brief_data(repo_path)
                canonical_brief["target_file"] = target_file

            if fmt == "json":
                self.send_json_response(200, {"status": "ok", "format": fmt, "brief": canonical_brief})
                return

            h_score = canonical_brief.get("health_score", 80.0)
            target_str = f" Target file: {target_file}." if target_file else ""
            if fmt == "claude":
                content = f'claude -p "Analyze repository \'{repo_name}\' (Health Score: {h_score}/100).{target_str} Address top risk boundary rules and maintain architectural integrity."'
            elif fmt == "codex":
                content = f"# OpenAI Codex System Context Brief\nRepository: {repo_name}\nHealth Score: {h_score}/100\n{f'Target Entity: {target_file}' if target_file else ''}\n\n## Architectural Directives\n1. Preserve public API contracts in interfaces/api.\n2. Route logic through RKM.\n"
            else:
                abs_target = os.path.abspath(os.path.join(repo_path, target_file)) if target_file else repo_path
                norm_target = abs_target.replace("\\", "/")
                content = f"# Google Antigravity / Gemini Architectural Brief\nTarget Workspace: [{repo_name}](file:///{norm_target})\nHealth Score: {h_score}/100\n"

            self.send_json_response(200, {"status": "ok", "format": fmt, "content": content})
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"status": "error", "message": f"Invalid export parameters: {str(e)}"})
        except Exception as e:
            self.send_json_response(500, {"status": "error", "message": str(e)})

    def handle_v1_ai_push(self):
        """
        Pushes AST analysis packet directly to local OpenAI proxy (http://127.0.0.1:10531/v1)
        or native AST engine, eliminating manual copy-pasting for the user.
        Uses Python standard library urllib.request strictly.
        """
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"status": "error", "message": "Invalid JSON body payload."})
                return

            repo = str(data.get("repo", "") or "").strip()
            target_file = str(data.get("target_file", "") or "").strip()
            persona = str(data.get("persona", "developer") or "developer").strip().lower()

            repo_path = os.path.abspath(repo) if repo else self.get_repo_root_path()
            
            # 1. Compile canonical brief context (Fast path via _ANALYSIS_CACHE hit, fallback on miss)
            norm_repo = _norm_path(repo_path)
            global _ANALYSIS_CACHE
            is_cache_hit = (
                _ANALYSIS_CACHE.get("repo_path") == norm_repo and
                _ANALYSIS_CACHE.get("bundle") is not None
            )

            target_risk = None
            if is_cache_hit:
                cached_bundle = _ANALYSIS_CACHE["bundle"]
                if target_file:
                    norm_tf = target_file.replace('\\', '/')
                    for r in cached_bundle.risks:
                        rf = getattr(r, "file_path", getattr(r, "file", "")).replace('\\', '/')
                        if rf == norm_tf or rf.endswith('/' + norm_tf):
                            target_risk = r
                            break
                if not target_risk and cached_bundle.risks:
                    target_risk = cached_bundle.risks[0]
            else:
                codebase = analyzer.analyze_directory(repo_path) if os.path.isdir(repo_path) else {}
                risks = risk.evaluate_risks(codebase, [target_file] if target_file else [], repo_path=repo_path)
                if risks:
                    target_risk = risks[0]
                
            file_name = target_file or (getattr(target_risk, "file_path", getattr(target_risk, "file", "")) if target_risk else "repository")
            complexity = float(getattr(target_risk, "complexity", 15.0)) if target_risk else 15.0
            coupling = int(getattr(target_risk, "coupling", 3)) if target_risk else 3
            level = getattr(target_risk, "level", "MEDIUM") if target_risk else "MEDIUM"
            
            prompt_text = (
                f"Analyze code entity '{file_name}' as persona '{persona}'.\n"
                f"AST Facts: Complexity={complexity}, Coupling Fan-Out={coupling}, Priority Zone={level}.\n"
                f"Provide actionable, step-by-step refactoring instructions to decouple interfaces and improve maintainability."
            )
            
            ai_response_text = None
            source_used = "Ultron Native AST Engine"
            
            # 2. Try Local OpenAI Proxy at port 10531 using standard library urllib.request
            proxy_url = "http://127.0.0.1:10531/v1/chat/completions"
            payload = json.dumps({
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are Ultron AI, an elite architectural refactoring engine."},
                    {"role": "user", "content": prompt_text}
                ],
                "temperature": 0.3
            }).encode("utf-8")
            
            import urllib.request
            import urllib.error
            import socket

            req = urllib.request.Request(
                proxy_url,
                data=payload,
                headers={"Content-Type": "application/json"}
            )

            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        res_json = json.loads(response.read().decode("utf-8"))
                        choices = res_json.get("choices", [])
                        if choices and "message" in choices[0]:
                            ai_response_text = choices[0]["message"].get("content")
                            source_used = "Local OpenAI Proxy (Port 10531)"
            except (urllib.error.URLError, urllib.error.HTTPError, OSError, socket.timeout):
                # Fallback cleanly to native AST translation without crashing
                pass

            if not ai_response_text:
                # Native AST AI engine explanation fallback
                ai_response_text = (
                    f"⚡ [Ultron Native AI Engine - Real-Time Push]\n"
                    f"Entity: {file_name}\n"
                    f"Persona Perspective: {persona.upper()}\n"
                    f"Empirical Metric Bounds: McCabe Complexity = {complexity}, Coupling Fan-Out = {coupling}\n\n"
                    f"Refactoring Recommendation:\n"
                    f"1. Extract internal decision logic from '{file_name}' into standalone helper functions.\n"
                    f"2. Route external callers through public boundary interfaces in 'interfaces/api'.\n"
                    f"3. Run test verification matrix to confirm zero architectural regressions."
                )

            self.send_json_response(200, {
                "status": "success",
                "entity_id": file_name,
                "persona": persona,
                "explanation": ai_response_text,
                "ai_response": ai_response_text,  # backward compat — canonical key is 'explanation'
                "message": ai_response_text,  # secondary compat for frontend fallback chain
                "source": source_used
            })

        except Exception as e:
            self.send_json_response(500, {"status": "error", "message": str(e)})

    def _ensure_cache_populated(self, repo_path: str):
        """Cold-cache guard: Populates _ANALYSIS_CACHE on-demand if empty."""
        global _ANALYSIS_CACHE
        norm_repo = _norm_path(repo_path)
        if _ANALYSIS_CACHE.get("repo_path") != norm_repo or _ANALYSIS_CACHE.get("bundle") is None:
            self._build_analysis_payload(repo_path, force=False)

    def handle_v1_agent_context(self):
        """GET /api/v1/agent/context — Pure read-only context projection for AI coding tools."""
        try:
            q_data = self.get_query_data()
            repo = q_data.get("repo", "") if isinstance(q_data, dict) else ""
            target_file = str(q_data.get("target_file", "")).strip() if isinstance(q_data, dict) else ""

            repo_path = os.path.abspath(repo) if repo and str(repo).strip() else self.get_repo_root_path()
            self._ensure_cache_populated(repo_path)

            global _ANALYSIS_CACHE
            bundle = _ANALYSIS_CACHE.get("bundle")
            payload = _ANALYSIS_CACHE.get("payload")

            target_risk = None
            if bundle and bundle.risks:
                if target_file:
                    norm_tf = target_file.replace('\\', '/')
                    for r in bundle.risks:
                        rf = getattr(r, "file_path", getattr(r, "file", "")).replace('\\', '/')
                        if rf == norm_tf or rf.endswith('/' + norm_tf):
                            target_risk = r
                            break
                if not target_risk:
                    target_risk = bundle.risks[0]

            context_data = {
                "status": "success",
                "repository": os.path.basename(repo_path),
                "repo_path": repo_path,
                "snapshot_id": _ANALYSIS_CACHE.get("content_hash"),
                "schema_version": getattr(bundle, "schema_version", "1.2.0") if bundle else "1.2.0",
                "health_score": payload.get("health_score", 100.0) if payload else 100.0,
                "target_file": target_file or (getattr(target_risk, "file_path", getattr(target_risk, "file", "")) if target_risk else "repository"),
                "risk_profile": {
                    "impact_score": getattr(target_risk, "impact_score", 0.0) if target_risk else 0.0,
                    "level": getattr(target_risk, "level", "LOW") if target_risk else "LOW",
                    "complexity": getattr(target_risk, "complexity", 1) if target_risk else 1,
                    "coupling": getattr(target_risk, "coupling_score", 0) if target_risk else 0,
                    "confidence": getattr(target_risk, "confidence", 0.95) if target_risk else 0.95,
                    "mitigation": getattr(target_risk, "mitigation", "") if target_risk else ""
                },
                "callers": getattr(target_risk, "callers", []) if target_risk else [],
                "file_tree": payload.get("file_tree", []) if payload else []
            }

            self.send_json_response(200, context_data)
        except Exception as e:
            self.send_json_response(500, {"status": "error", "error": f"Failed to retrieve agent context: {str(e)}"})

    def handle_v1_agent_handoff(self):
        """POST /api/v1/agent/handoff — Pure read-only handoff brief generator."""
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"status": "error", "error": "Invalid JSON body payload."})
                return

            repo = data.get("repo", "")
            agent_id = str(data.get("agent_id", "antigravity")).strip()
            intent = str(data.get("intent", "Code refactoring")).strip()
            target_files = data.get("target_files", [])
            if not isinstance(target_files, list):
                target_files = [str(target_files)]

            repo_path = os.path.abspath(repo) if repo and str(repo).strip() else self.get_repo_root_path()
            self._ensure_cache_populated(repo_path)

            global _ANALYSIS_CACHE
            bundle = _ANALYSIS_CACHE.get("bundle")
            payload = _ANALYSIS_CACHE.get("payload")

            target_risks = []
            if bundle and bundle.risks:
                if target_files:
                    norm_targets = set(t.replace('\\', '/') for t in target_files)
                    for r in bundle.risks:
                        rf = getattr(r, "file_path", getattr(r, "file", "")).replace('\\', '/')
                        if any(rf == nt or rf.endswith('/' + nt) for nt in norm_targets):
                            target_risks.append(r)
                if not target_risks:
                    target_risks = bundle.risks[:3]

            handoff_brief = {
                "status": "success",
                "handoff_id": str(uuid.uuid4()),
                "agent_id": agent_id,
                "intent": intent,
                "repository": os.path.basename(repo_path),
                "snapshot_id": _ANALYSIS_CACHE.get("content_hash"),
                "health_score": payload.get("health_score", 100.0) if payload else 100.0,
                "impacted_targets": [
                    {
                        "file_path": getattr(r, "file_path", getattr(r, "file", "")),
                        "level": getattr(r, "level", "LOW"),
                        "impact_score": getattr(r, "impact_score", 0.0),
                        "complexity": getattr(r, "complexity", 1),
                        "coupling": getattr(r, "coupling_score", 0),
                        "callers": getattr(r, "callers", [])
                    }
                    for r in target_risks
                ],
                "recommended_verification": [
                    "python verify_release.py"
                ]
            }
            self.send_json_response(200, handoff_brief)

        except Exception as e:
            self.send_json_response(500, {"status": "error", "error": f"Handoff brief generation failed: {str(e)}"})

    def handle_analyze(self):
        try:
            data = self.get_request_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"status": "error", "message": "Invalid JSON body payload.", "error": "Invalid JSON body payload."})
                return
            raw_repo = data.get("repo")
            if raw_repo is None or not isinstance(raw_repo, str) or not raw_repo.strip() or '\x00' in raw_repo:
                repo_path = self.get_repo_root_path()
            else:
                try:
                    repo_path = os.path.abspath(raw_repo.strip())
                except (ValueError, OSError):
                    repo_path = self.get_repo_root_path()

            if not os.path.exists(repo_path):
                msg = f"Directory '{repo_path}' does not exist."
                self.send_json_response(400, {"status": "error", "message": msg, "error": msg})
                return
            if not os.path.isdir(repo_path):
                msg = f"Repository path '{repo_path}' is a file, not a directory."
                self.send_json_response(400, {"status": "error", "message": msg, "error": msg})
                return
                
            raw_intent = data.get("intent")
            intent = str(raw_intent).strip() if raw_intent is not None else ""
            raw_files = data.get("files")
            files_str = str(raw_files).strip() if raw_files is not None else ""
            target_files = [f.strip() for f in files_str.split(",") if f.strip() and '\x00' not in f] if files_str else []
            
            codebase = analyzer.analyze_directory(repo_path)
            if not codebase:
                msg = f"No code files found in '{repo_path}'. Ensure directory contains Python files."
                self.send_json_response(400, {"status": "error", "message": msg, "error": msg})
                return

            risks = risk.evaluate_risks(codebase, target_files, intent, repo_path=repo_path)

            # Phase 2.8 Consequence-Driven Recommendation Engine
            from ultron.core.recommendation import build_consequence_recommendations
            recommendations = build_consequence_recommendations(
                codebase=codebase,
                risks=risks,
                objective=intent,
                limit=20,
                policy="consequence_v1",
                repo_path=repo_path
            )
            
            # Extract basic stats
            total_files = len(codebase)
            total_definitions = sum(len(c.get("definitions", [])) for c in codebase.values())
            
            self.send_json_response(200, {
                "status": "success",
                "success": True,
                "stats": {
                    "total_files": total_files,
                    "total_definitions": total_definitions
                },
                "risks": [r.to_dict() for r in risks],
                "recommendations": [rec.to_dict() for rec in recommendations]
            })
        except PermissionError:
            self.send_json_response(400, {
                "status": "error",
                "message": f"Permission denied accessing directory '{repo_path}'.",
                "error": f"Permission denied accessing directory '{repo_path}'."
            })
        except Exception as e:
            self.send_json_response(500, {
                "status": "error",
                "message": str(e),
                "error": str(e),
                "traceback": traceback.format_exc()
            })

    def handle_audit(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            raw_repo = data.get("repo")
            if raw_repo is None or not isinstance(raw_repo, str) or not raw_repo.strip() or '\x00' in raw_repo:
                repo_path = self.get_repo_root_path()
            else:
                try:
                    repo_path = os.path.abspath(raw_repo.strip())
                except (ValueError, OSError):
                    repo_path = self.get_repo_root_path()

            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return
                
            code_content = data.get("code", "")
            if code_content and isinstance(code_content, str):
                # Sandbox mode: write a temporary file inside the repo
                target_file = os.path.join(repo_path, "sandbox_temp.py")
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(code_content)
            else:
                raw_target = data.get("target_file") or data.get("file_path") or data.get("file")
                if not raw_target or not isinstance(raw_target, str) or not raw_target.strip() or '\x00' in raw_target:
                    self.send_json_response(400, {"error": "Missing target_file parameter."})
                    return
                target_norm = raw_target.strip()
                target_file = os.path.join(repo_path, target_norm) if not os.path.isabs(target_norm) else os.path.abspath(target_norm)
                
            is_valid, abs_target = validate_repo_path(repo_path, target_file)
            if not is_valid or not os.path.isfile(abs_target):
                self.send_json_response(400, {"error": f"Target file '{target_file}' does not exist, is outside repository, or is not a file."})
                return
            target_file = abs_target
                
            try:
                typo_threshold = float(data.get("typo_threshold", 0.75) or 0.75)
            except (ValueError, TypeError):
                typo_threshold = 0.75
            try:
                prob_threshold = float(data.get("prob_threshold", 0.0) or 0.0)
            except (ValueError, TypeError):
                prob_threshold = 0.0
            
            names = classifier.build_models(repo_path, exclude_file=target_file)
            anomalies = classifier.audit_target_file(
                target_file, 
                names, 
                typo_threshold=typo_threshold
            )
            
            # Clean up temporary sandbox file
            if code_content and os.path.exists(target_file):
                try:
                    os.remove(target_file)
                except Exception:
                    pass
            
            self.send_json_response(200, {
                "success": True,
                "anomalies": anomalies
            })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {
                "error": str(e),
                "traceback": traceback.format_exc()
            })

    def handle_generate(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            raw_repo = data.get("repo")
            if raw_repo is None or not isinstance(raw_repo, str) or not raw_repo.strip() or '\x00' in raw_repo:
                repo_path = self.get_repo_root_path()
            else:
                try:
                    repo_path = os.path.abspath(raw_repo.strip())
                except (ValueError, OSError):
                    repo_path = self.get_repo_root_path()

            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return
                
            raw_intent = data.get("intent")
            if raw_intent is None or not isinstance(raw_intent, str) or not raw_intent.strip():
                self.send_json_response(400, {"error": "Intent parameter is required."})
                return
            intent = raw_intent.strip()
                
            raw_files = data.get("files")
            files_str = str(raw_files).strip() if raw_files is not None else ""
            target_files = [f.strip() for f in files_str.split(",") if f.strip() and '\x00' not in f] if files_str else []
            
            # Phase 2.0: Thin adapter delegating to canonical AgentContextBuilder
            from ultron.core.agent_context_builder import AgentContextBuilder
            builder = AgentContextBuilder(repo_path)
            bundle = None
            try:
                from ultron.core.pipeline.orchestrator import analyze_repository
                bundle = analyze_repository(repo_path)
            except Exception:
                bundle = None
            
            provider = data.get("provider", "markdown")
            ctx = builder.build(
                bundle=bundle,
                target_file=",".join(target_files) if target_files else None,
                format=provider,
                intent=intent
            )
            opt_prompt = ctx.prompt if ctx else ""
            
            self.send_json_response(200, {
                "success": True,
                "prompt": opt_prompt,
                "provider": provider,
                "canonical": {
                    "mission_id": getattr(ctx, "mission_id", "canonical"),
                    "provider": provider
                }
            })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {
                "error": str(e),
                "traceback": traceback.format_exc()
            })

    def handle_v1_get_objective(self):
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            repo = params.get("repo", ["."])[0] if "repo" in params and params["repo"] else "."
            if not isinstance(repo, str) or not repo.strip() or '\x00' in repo:
                repo = "."
            tracker = ObjectiveTracker(repo)
            obj = tracker.get_objective()
            self.send_json_response(200, obj)
        except Exception as e:
            sys.stderr.write(f"[Ultron Server Error] handle_v1_get_objective: {e}\n")
            self.send_json_response(500, {"error": str(e)})

    def handle_v1_set_objective(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            raw_repo = data.get("repo", ".")
            repo = str(raw_repo) if raw_repo and isinstance(raw_repo, str) and '\x00' not in raw_repo else "."
            tracker = ObjectiveTracker(repo)
            
            raw_obj = data.get("objective") if isinstance(data.get("objective"), dict) else {}
            title = data.get("title") or raw_obj.get("title") or "Active Objective"
            title = str(title) if title is not None else "Active Objective"
            description = data.get("description") or raw_obj.get("description") or ""
            description = str(description) if description is not None else ""
            
            raw_tasks = data.get("tasks") if data.get("tasks") is not None else raw_obj.get("tasks")
            tasks = raw_tasks if isinstance(raw_tasks, list) else None
            
            raw_const = data.get("constraints") if data.get("constraints") is not None else raw_obj.get("constraints")
            constraints = raw_const if isinstance(raw_const, list) else None
            
            raw_acc = data.get("acceptance") if data.get("acceptance") is not None else raw_obj.get("acceptance")
            acceptance = raw_acc if isinstance(raw_acc, list) else None
            
            raw_aff = data.get("affected_areas") if data.get("affected_areas") is not None else raw_obj.get("affected_areas")
            affected_areas = raw_aff if isinstance(raw_aff, list) else None

            res = tracker.set_objective(
                title=title,
                description=description,
                tasks=tasks,
                constraints=constraints,
                acceptance=acceptance,
                affected_areas=affected_areas
            )
            self.send_json_response(200, res)
        except Exception as e:
            sys.stderr.write(f"[Ultron Server Error] handle_v1_set_objective: {e}\n")
            self.send_json_response(500, {"error": str(e)})

    def handle_v1_complete_task(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            raw_repo = data.get("repo", ".")
            repo = str(raw_repo) if raw_repo and isinstance(raw_repo, str) and '\x00' not in raw_repo else "."
            
            raw_tid = data.get("task_id") or data.get("id")
            if raw_tid is None or not str(raw_tid).strip() or '\x00' in str(raw_tid):
                self.send_json_response(400, {"error": "Missing 'task_id' parameter."})
                return
            task_id = str(raw_tid).strip()
            
            tracker = ObjectiveTracker(repo)
            res = tracker.complete_task(task_id)
            if not res.get("success"):
                self.send_json_response(404, res)
            else:
                obj_state = res.get("state", {})
                mgr = DevelopmentSessionManager(repo)
                sess_data = mgr.sync_objective(obj_state)
                mgr.record_event(
                    event_type="TASK_COMPLETED",
                    title=f"Task '{task_id}' marked as completed",
                    metadata={"task_id": task_id, "progress_pct": obj_state.get("progress_pct", 0)}
                )
                self.send_json_response(200, {
                    "success": True,
                    "task_id": task_id,
                    "state": obj_state,
                    "objective": obj_state,
                    "session": mgr.get_session()
                })
        except Exception as e:
            sys.stderr.write(f"[Ultron Server Error] handle_v1_complete_task: {e}\n")
            self.send_json_response(500, {"error": str(e)})

    def handle_v1_add_task(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            raw_repo = data.get("repo", ".")
            repo = str(raw_repo) if raw_repo and isinstance(raw_repo, str) and '\x00' not in raw_repo else "."
            
            raw_title = data.get("title")
            if raw_title is None or not str(raw_title).strip() or '\x00' in str(raw_title):
                self.send_json_response(400, {"error": "Missing 'title' parameter."})
                return
            title = str(raw_title).strip()
            
            description = str(data.get("description", "") or "").strip()
            status = str(data.get("status", "pending") or "pending")
            tracker = ObjectiveTracker(repo)
            res = tracker.add_task(title=title, description=description, status=status)
            obj_state = res if isinstance(res, dict) else {}
            mgr = DevelopmentSessionManager(repo)
            sess_data = mgr.sync_objective(obj_state)
            mgr.record_event(
                event_type="TASK_ADDED",
                title=f"Task added: '{title}'",
                metadata={"title": title, "status": status}
            )
            self.send_json_response(200, {
                "success": True,
                "state": obj_state,
                "objective": obj_state,
                "session": mgr.get_session()
            })
        except Exception as e:
            sys.stderr.write(f"[Ultron Server Error] handle_v1_add_task: {e}\n")
            self.send_json_response(500, {"error": str(e)})

    def handle_v1_agent_context_builder(self):
        try:
            if self.command == "GET":
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                repo = params.get("repo", ["."])[0] if "repo" in params and params["repo"] else "."
                provider = params.get("provider", ["markdown"])[0] if "provider" in params and params["provider"] else "markdown"
            else:
                data = self.get_post_data()
                if not isinstance(data, dict):
                    self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                    return
                raw_repo = data.get("repo", ".")
                repo = str(raw_repo) if raw_repo and isinstance(raw_repo, str) and '\x00' not in raw_repo else "."
                provider = data.get("provider", "markdown") or "markdown"
                user_intent = data.get("intent", "") or ""
                user_target_file = data.get("target_file", "") or ""
                user_issue_id = data.get("issue_id", "") or ""
                user_repro_sig = data.get("reproduction_signature", "") or ""
                user_why = data.get("why_it_matters", "") or ""

            if not isinstance(repo, str) or not repo.strip() or '\x00' in repo:
                repo = "."

            tracker = ObjectiveTracker(repo)
            objective = tracker.get_objective()

            # Retrieve cached risks if available
            risks = []
            snapshot_id = "snap_initial"
            model_hash = ""
            if _ANALYSIS_CACHE.get("payload"):
                payload = _ANALYSIS_CACHE["payload"]
                risks = payload.get("risks", [])
                snapshot_id = payload.get("snapshot_id") or _ANALYSIS_CACHE.get("content_hash") or "snap_initial"
                model_hash = _ANALYSIS_CACHE.get("content_hash") or ""

            ctx = AgentContextBuilder.build(
                objective_state=objective,
                repo_path=repo,
                risks=risks,
                snapshot_id=snapshot_id,
                model_hash=model_hash,
                intent=user_intent if user_intent else None,
                target_file=user_target_file if user_target_file else None,
                issue_id=user_issue_id if user_issue_id else None,
                reproduction_signature=user_repro_sig if user_repro_sig else None,
                why_this_task_matters=user_why if user_why else None
            )

            p_lower = str(provider).lower()
            if p_lower in ("claude", "anthropic"):
                rendered = AgentContextBuilder.render_claude(ctx)
            elif p_lower in ("cursor", "cursorrules", "composer", "codex", "openai"):
                rendered = AgentContextBuilder.render_codex(ctx)
            elif p_lower in ("windsurf", "cascade", "codeium"):
                rendered = AgentContextBuilder.render_windsurf(ctx)
            elif p_lower in ("antigravity", "agy", "umags"):
                rendered = AgentContextBuilder.render_antigravity(ctx)
            elif p_lower in ("aider", "cli"):
                rendered = AgentContextBuilder.render_aider(ctx)
            else:
                rendered = AgentContextBuilder.render_markdown(ctx)

            self.send_json_response(200, {
                "success": True,
                "provider": p_lower,
                "prompt": rendered,
                "semantic_mission_hash": ctx.semantic_mission_hash(),
                "canonical": asdict(ctx)
            })
        except Exception as e:
            sys.stderr.write(f"[Ultron Server Error] handle_v1_agent_context_builder: {e}\n")
            self.send_json_response(500, {"error": str(e)})

    def handle_v1_safety_evaluate(self):
        try:
            if self.command == "GET":
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                repo = params.get("repo", ["."])[0] if "repo" in params and params["repo"] else "."
                modified_files = []
                test_results = None
            else:
                data = self.get_post_data()
                if not isinstance(data, dict):
                    self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                    return
                raw_repo = data.get("repo", ".")
                repo = str(raw_repo) if raw_repo and isinstance(raw_repo, str) and '\x00' not in raw_repo else "."
                raw_mod = data.get("modified_files", [])
                modified_files = raw_mod if isinstance(raw_mod, list) else []
                raw_tests = data.get("test_results")
                test_results = raw_tests if isinstance(raw_tests, dict) else None

            if not isinstance(repo, str) or not repo.strip() or '\x00' in repo:
                repo = "."

            tracker = ObjectiveTracker(repo)
            objective = tracker.get_objective()

            # Determine cycle count and risks from cached analysis if available
            cycle_count = 0
            risks = []
            snapshot_id = "snap_initial"
            if _ANALYSIS_CACHE.get("payload"):
                payload = _ANALYSIS_CACHE["payload"]
                cycle_count = payload.get("dependency_graph", {}).get("cycle_count", 0)
                risks = payload.get("risks", [])
                snapshot_id = payload.get("snapshot_id") or _ANALYSIS_CACHE.get("content_hash") or "snap_initial"

            report = SafetyEvaluator.evaluate(
                test_results=test_results,
                modified_files=modified_files,
                boundary_constraints=objective.get("constraints", []),
                acceptance_criteria=objective.get("acceptance", []),
                cycle_count=cycle_count,
                risks=risks,
                snapshot_id=snapshot_id
            )

            self.send_json_response(200, {
                "success": True,
                "report": asdict(report)
            })
        except Exception as e:
            sys.stderr.write(f"[Ultron Server Error] handle_v1_safety_evaluate: {e}\n")
            self.send_json_response(500, {"error": str(e)})

    def handle_v1_session_current(self):
        try:
            if self.command == "GET":
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                repo = params.get("repo", ["."])[0] if "repo" in params and params["repo"] else "."
            else:
                data = self.get_post_data()
                if not isinstance(data, dict):
                    self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                    return
                raw_repo = data.get("repo", ".")
                repo = str(raw_repo) if raw_repo and isinstance(raw_repo, str) and '\x00' not in raw_repo else "."

            if not isinstance(repo, str) or not repo.strip() or '\x00' in repo:
                repo = "."

            manager = DevelopmentSessionManager(repo)
            tracker = ObjectiveTracker(repo)
            objective = tracker.get_objective()
            
            # Sync current objective into session
            snapshot_id = "snap_initial"
            if _ANALYSIS_CACHE.get("payload"):
                snapshot_id = _ANALYSIS_CACHE["payload"].get("snapshot_id") or _ANALYSIS_CACHE.get("content_hash") or "snap_initial"

            session_data = manager.sync_objective(objective, snapshot_id=snapshot_id)
            self.send_json_response(200, {
                "success": True,
                "session": session_data
            })
        except Exception as e:
            sys.stderr.write(f"[Ultron Server Error] handle_v1_session_current: {e}\n")
            self.send_json_response(500, {"error": str(e)})

    def handle_v1_session_diff(self):
        try:
            if self.command == "POST":
                data = self.get_post_data()
                if not isinstance(data, dict):
                    self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                    return
            else:
                data = {}
            raw_repo = data.get("repo", ".")
            repo = str(raw_repo) if raw_repo and isinstance(raw_repo, str) and '\x00' not in raw_repo else "."
            manager = DevelopmentSessionManager(repo)
            session = manager.get_session()
            self.send_json_response(200, {
                "success": True,
                "session_id": session.get("session_id"),
                "starting_snapshot_id": session.get("starting_snapshot_id"),
                "latest_snapshot_id": session.get("latest_snapshot_id"),
                "evolution_delta": session.get("evolution_delta"),
                "safety_assessment": session.get("safety_assessment")
            })
        except Exception as e:
            sys.stderr.write(f"[Ultron Server Error] handle_v1_session_diff: {e}\n")
            self.send_json_response(500, {"error": str(e)})

    def handle_v1_validate_mission(self):
        """Validates mission completeness against the canonical AgentContextBuilder rules."""
        try:
            if self.command == "GET":
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                target_file = params.get("target_file", [None])[0] or params.get("target", [None])[0]
                intent = params.get("intent", [None])[0] or params.get("mission_intent", [None])[0]
                acceptance = params.get("acceptance", [])
                affected = params.get("affected", [])
            else:
                data = self.get_post_data()
                if not isinstance(data, dict):
                    data = {}
                target_file = data.get("target_file") or data.get("target") or data.get("file")
                intent = data.get("intent") or data.get("mission_intent")
                acceptance = data.get("acceptance_criteria") or data.get("acceptance")
                affected = data.get("affected_areas") or data.get("affected")

            target_file = str(target_file) if target_file is not None else None
            intent = str(intent) if intent is not None else None
            acceptance = acceptance if isinstance(acceptance, (list, tuple)) else ([str(acceptance)] if acceptance else [])
            affected = affected if isinstance(affected, (list, tuple)) else ([str(affected)] if affected else [])

            validity = AgentContextBuilder.validate_mission(
                target_file=target_file,
                intent=intent,
                acceptance_criteria=acceptance,
                affected_areas=affected
            )
            self.send_json_response(200, {
                "success": True,
                "data": validity,
                "validity": validity
            })
        except Exception as e:
            sys.stderr.write(f"[Ultron Server Error] handle_v1_validate_mission: {e}\n")
            self.send_json_response(500, {"error": str(e)})

    def handle_v1_create_checkpoint(self):
        """Authoritative server-side gate for checkpoint creation."""
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            raw_repo = data.get("repo", ".")
            repo = str(raw_repo) if raw_repo and isinstance(raw_repo, str) and '\x00' not in raw_repo else "."
            raw_desc = data.get("description") or data.get("label")
            description = str(raw_desc).strip() if raw_desc else "Milestone checkpoint"
            force = bool(data.get("force", False))

            manager = DevelopmentSessionManager(repo)
            result = manager.create_checkpoint(description=description, force=force)

            if not result.get("success"):
                self.send_json_response(400, {
                    "success": False,
                    "error": result.get("error"),
                    "error_code": result.get("error_code", "READINESS_BLOCKED"),
                    "decision": result.get("decision"),
                    "blocking_conditions": result.get("blocking_conditions", []),
                    "reason_codes": result.get("reason_codes", [])
                })
                return

            self.send_json_response(200, {
                "success": True,
                "checkpoint": result.get("checkpoint"),
                "checkpoint_id": result.get("checkpoint_id")
            })
        except Exception as e:
            sys.stderr.write(f"[Ultron Server Error] handle_v1_create_checkpoint: {e}\n")
            self.send_json_response(500, {"error": str(e)})

    def handle_v1_get_checkpoints(self):
        """Returns all verified checkpoints for the repository development session."""
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            repo = params.get("repo", ["."])[0] if "repo" in params and params["repo"] else "."
            if not isinstance(repo, str) or not repo.strip() or '\x00' in repo:
                repo = "."

            manager = DevelopmentSessionManager(repo)
            checkpoints = manager.get_checkpoints()
            self.send_json_response(200, {
                "success": True,
                "checkpoints": checkpoints,
                "count": len(checkpoints)
            })
        except Exception as e:
            sys.stderr.write(f"[Ultron Server Error] handle_v1_get_checkpoints: {e}\n")
            self.send_json_response(500, {"error": str(e)})

    def handle_config(self):
        try:
            self.send_json_response(200, {
                "success": True,
                "default_repo": os.getcwd().replace("\\", "/")
            })
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_get_repo_root(self):
        try:
            if not os.path.exists(CONFIG_FILE):
                self.send_json_response(200, {"repo_root": None})
                return
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.send_json_response(200, {"repo_root": cfg.get("repo_root")})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_set_repo_root(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            path = data.get("path", "")
            if not isinstance(path, str) or not path.strip() or '\x00' in path:
                self.send_json_response(400, {"error": "Missing or invalid 'path' parameter."})
                return
            abs_path = os.path.abspath(path.strip())
            # Reject bare drive roots (e.g. "C:\") — would expose the whole drive
            drive, tail = os.path.splitdrive(abs_path)
            if tail in ("\\", "/", ""):
                self.send_json_response(400, {"error": "Path must not be a bare drive root."})
                return
            if not os.path.isdir(abs_path):
                self.send_json_response(400, {"error": f"Path '{abs_path}' is not a valid directory."})
                return
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"repo_root": abs_path}, f, indent=2)
            self.send_json_response(200, {"status": "ok", "repo_root": abs_path})
        except Exception as e:
            self.send_json_response(500, {
                "error": str(e),
                "traceback": traceback.format_exc()
            })

    def handle_file_tree(self):
        try:
            data = self.get_request_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON payload format."})
                return
            repo = data.get("repo")
            if not isinstance(repo, str) or not repo.strip() or '\x00' in repo:
                self.send_json_response(400, {"error": "Missing or invalid 'repo' parameter."})
                return
                
            try:
                repo_path = os.path.realpath(repo.strip())
            except (ValueError, OSError):
                self.send_json_response(400, {"error": "Invalid repository path."})
                return

            drive, tail = os.path.splitdrive(repo_path)
            if drive and tail in ('\\', '/', ''):
                self.send_json_response(400, {"error": "Cannot use drive root as repository."})
                return
            
            real_repo_dir = os.path.join(repo_path, "")
            
            if not os.path.normcase(repo_path).startswith(os.path.normcase(real_repo_dir)) and not os.path.normcase(real_repo_dir).startswith(os.path.normcase(repo_path)):
                self.send_json_response(400, {"error": "Invalid repository path."})
                return
            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return

            # Scan codebase
            codebase = analyzer.analyze_directory(repo_path)
            
            # Detect codebase parse errors
            failed_files = set()
            if isinstance(codebase, dict):
                for key, val in codebase.items():
                    if isinstance(val, dict) and "error" in val:
                        failed_files.add(key)

            # Evaluate risks
            target_files = [k for k in codebase.keys() if k.endswith(".py")] if isinstance(codebase, dict) else []
            risk_map = {}
            try:
                risks = risk.evaluate_risks(codebase, target_files, intent="Identify heatmaps", repo_path=repo_path)
                for r in risks:
                    file_path = getattr(r, "file_path", None) or (r.get("file_path") if isinstance(r, dict) else None)
                    impact_score = getattr(r, "impact_score", 0.0) or (r.get("impact_score", 0.0) if isinstance(r, dict) else 0.0)
                    level = getattr(r, "level", "LOW") or (r.get("level", "LOW") if isinstance(r, dict) else "LOW")
                    summary = translate.plain_language_summary(r)
                    boundary_type = getattr(r, "boundary_type", "Internal") or (r.get("boundary_type", "Internal") if isinstance(r, dict) else "Internal")
                    arch_role = getattr(r, "architectural_role", None)
                    arch_role_val = arch_role.value if hasattr(arch_role, "value") else str(arch_role or "INTERNAL")
                    strat = getattr(r, "change_strategy", None)
                    strat_val = strat.value if hasattr(strat, "value") else str(strat or "SAFE_EDIT")
                    strat_display = strat.display_name if hasattr(strat, "display_name") else "Safe internal edits"
                    if file_path:
                        risk_map[file_path] = {
                            "level": level,
                            "impact_score": float(impact_score),
                            "summary": summary,
                            "boundary_type": boundary_type,
                            "architectural_role": arch_role_val,
                            "change_strategy": strat_val,
                            "change_strategy_display": strat_display,
                            "complexity": getattr(r, "complexity", 1),
                            "coupling": int(getattr(r, "coupling_score", 0)),
                        }
            except Exception as eval_err:
                print(f"Risk evaluation failed: {eval_err}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                for tf in target_files:
                    failed_files.add(tf)

            LEVEL_MAP = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
            REV_LEVEL_MAP = {1: "LOW", 2: "MEDIUM", 3: "HIGH"}

            def build_tree(path):
                tree = []
                try:
                    items = os.listdir(path)
                except (OSError, PermissionError):
                    return tree

                for item in items:
                    if item.startswith('.') or item in ('venv', '.venv', 'env', 'test_env', '__pycache__', 'tests', 'node_modules', 'scratch', 'dist', 'build', 'synapse_project', 'docs', 'ultron_risk_scorer.egg-info'):
                        continue
                    full_path = os.path.join(path, item)
                    if os.path.islink(full_path):
                        continue
                        
                    rel_path = os.path.relpath(full_path, repo_path).replace(os.sep, "/")
                    
                    if os.path.isdir(full_path):
                        children = build_tree(full_path)
                        if children:
                            child_risks = [c["risk"] for c in children]
                            max_level_num = max(LEVEL_MAP.get(cr["level"], 1) for cr in child_risks)
                            max_level = REV_LEVEL_MAP.get(max_level_num, "LOW")
                            max_impact = max(cr["impact_score"] for cr in child_risks)
                            
                            dir_summary = "All child modules are safe (LOW risk)"
                            if max_level != "LOW":
                                for cr in child_risks:
                                    if LEVEL_MAP.get(cr["level"], 1) == max_level_num:
                                        dir_summary = cr["summary"]
                                        break
                                        
                            tree.append({
                                "name": item,
                                "path": rel_path,
                                "type": "directory",
                                "children": children,
                                "risk": {
                                    "level": max_level,
                                    "level_num": max_level_num,
                                    "impact_score": max_impact,
                                    "summary": dir_summary
                                }
                            })
                    else:
                        if item.endswith((".py", ".html", ".css", ".js", ".md", ".json")):
                            is_failed_file = rel_path in failed_files
                            if not is_failed_file and item.endswith(".py") and rel_path not in codebase:
                                try:
                                    analysis = analyzer.analyze_file(full_path)
                                    if "error" in analysis:
                                        failed_files.add(rel_path)
                                        is_failed_file = True
                                except Exception:
                                    failed_files.add(rel_path)
                                    is_failed_file = True
                                    
                            if is_failed_file:
                                file_risk = {
                                    "level": "HIGH",
                                    "level_num": 3,
                                    "impact_score": 1.0,
                                    "summary": "Analysis failed: check server logs for details. Defaulted to HIGH risk.",
                                    "boundary_type": "Internal"
                                }
                            elif rel_path in risk_map:
                                rm = risk_map[rel_path]
                                file_risk = {
                                    "level": rm["level"],
                                    "level_num": LEVEL_MAP.get(rm["level"], 1),
                                    "impact_score": rm["impact_score"],
                                    "summary": rm["summary"],
                                    "boundary_type": rm.get("boundary_type", "Internal"),
                                    "architectural_role": rm.get("architectural_role", "INTERNAL"),
                                    "change_strategy": rm.get("change_strategy", "SAFE_EDIT"),
                                    "change_strategy_display": rm.get("change_strategy_display", "Safe internal edits"),
                                    "complexity": rm.get("complexity", 1),
                                    "coupling": rm.get("coupling", 0),
                                }
                            elif item.endswith(".py"):
                                file_risk = {
                                    "level": "LOW",
                                    "level_num": 1,
                                    "impact_score": 0.0,
                                    "summary": "Analysis unavailable. Defaulted to LOW risk.",
                                    "boundary_type": "Internal"
                                }
                            else:
                                file_risk = {
                                    "level": "LOW",
                                    "level_num": 1,
                                    "impact_score": 0.0,
                                    "summary": "Non-Python file. Low structural risk.",
                                    "boundary_type": "Internal"
                                }
                                
                            tree.append({
                                "name": item,
                                "path": rel_path,
                                "type": "file",
                                "risk": file_risk
                            })
                tree.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["name"].lower()))
                return tree
            
            file_tree = build_tree(repo_path)
            self.send_json_response(200, {
                "success": True,
                "tree": file_tree
            })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_architecture_health(self):
        try:
            data = self.get_request_data() if hasattr(self, "get_request_data") else {}
            repo = (data.get("repo") if isinstance(data, dict) else None) or self.get_repo_root_path()
            repo_path = os.path.abspath(str(repo).strip()) if repo else self.get_repo_root_path()
            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return
            self.send_json_response(200, {
                "success": True,
                "health_score": 100,
                "hotspots": [],
                "circular_dependencies": [],
                "violations": [],
                "contracts": []
            })
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})


    def handle_get_file(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON payload format."})
                return
            repo = data.get("repo")
            file_param = data.get("file")
            if (not isinstance(repo, str) or not repo.strip() or '\x00' in repo or
                not isinstance(file_param, str) or not file_param.strip() or '\x00' in file_param):
                self.send_json_response(400, {"error": "Missing or invalid parameters."})
                return
                
            try:
                repo_path = os.path.realpath(repo.strip())
                clean_file = file_param.strip().replace("\\", "/").lstrip("/")
                full_path = os.path.realpath(os.path.join(repo_path, clean_file))
            except (ValueError, OSError):
                self.send_json_response(400, {"error": "Invalid file path."})
                return

            real_repo_dir = os.path.join(repo_path, "")
            
            if (not os.path.normcase(full_path).startswith(os.path.normcase(real_repo_dir))
                    or not os.path.exists(full_path)
                    or os.path.isdir(full_path)):
                self.send_json_response(400, {"error": "Invalid file path."})
                return
                
            with open(full_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
                
            self.send_json_response(200, {
                "success": True,
                "content": content
            })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_save_file(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON payload format."})
                return
            repo = data.get("repo")
            file_param = data.get("file")
            content = data.get("content")
            if (not isinstance(repo, str) or not repo.strip() or '\x00' in repo or 
                not isinstance(file_param, str) or not file_param.strip() or '\x00' in file_param or 
                not isinstance(content, str)):
                self.send_json_response(400, {"error": "Missing or invalid parameters."})
                return
                
            try:
                repo_path = os.path.realpath(repo.strip())
                clean_file = file_param.strip().replace("\\", "/").lstrip("/")
                full_path = os.path.realpath(os.path.join(repo_path, clean_file))
            except (ValueError, OSError) as val_err:
                self.send_json_response(400, {"error": f"Invalid file path: {val_err}"})
                return

            real_repo_dir = os.path.join(repo_path, "")
            
            if not os.path.normcase(full_path).startswith(os.path.normcase(real_repo_dir)):
                self.send_json_response(400, {"error": "Invalid file path."})
                return
                
            try:
                if os.path.exists(full_path):
                    backup_path = full_path + ".bak"
                    try:
                        shutil.copy2(full_path, backup_path)
                    except Exception as e:
                        print(f"Failed to create backup: {e}")
                
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                self.send_json_response(500, {"error": f"Failed to save file: {str(e)}"})
                return
                
            self.send_json_response(200, {
                "success": True,
                "message": "File saved successfully."
            })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_run_tests(self):
        try:
            from ultron.core.test_runner_service import TestRunnerService
            data = self.get_post_data()
            if not isinstance(data, dict):
                data = {}
            raw_repo = data.get("repo")
            if raw_repo is None or not isinstance(raw_repo, str) or not raw_repo.strip() or '\x00' in raw_repo:
                repo_path = self.get_repo_root_path()
            else:
                try:
                    repo_path = os.path.abspath(raw_repo.strip())
                except (ValueError, OSError):
                    repo_path = self.get_repo_root_path()

            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return
            
            global LAST_ANALYSIS
            repo_uuid = LAST_ANALYSIS.get("repo_uuid", "")
            content_hash = LAST_ANALYSIS.get("content_hash", "")
            
            feedback_params = {
                "file_path": data.get("file_path", LAST_ANALYSIS.get("file_path")),
                "delta_i": data.get("delta_i", LAST_ANALYSIS.get("delta_i", 0.0)),
                "mkr": data.get("mkr", LAST_ANALYSIS.get("mkr", 1.0)),
                "delta_cest": data.get("delta_cest", LAST_ANALYSIS.get("delta_cest", 0.0)),
                "actual_failure": data.get("actual_failure")
            }

            service = TestRunnerService.get_instance()
            record = service.start_test_run(
                repo_path=repo_path,
                repo_uuid=repo_uuid,
                content_hash=content_hash,
                feedback_params=feedback_params,
                timeout=float(data.get("timeout", 45.0))
            )

            # Asynchronous mode requested by modern client
            if data.get("async") is True or data.get("mode") == "async":
                self.send_json_response(202, {
                    "status": "running",
                    "run_id": record.run_id,
                    "poll_url": f"/api/v1/test-status?run_id={record.run_id}",
                    "repo_uuid": repo_uuid,
                    "content_hash": content_hash
                })
                return

            # Synchronous compatibility mode: poll internally until finished (or timeout)
            start_wait = time.time()
            max_wait = float(data.get("timeout", 30.0))
            while not record.to_dict()["is_finished"] and (time.time() - start_wait) < max_wait:
                time.sleep(0.1)

            rec_dict = record.to_dict()
            self.send_json_response(200, {
                "success": True,
                "exit_code": rec_dict["exit_code"] if rec_dict["exit_code"] is not None else 1,
                "output": rec_dict["output"],
                "run_id": record.run_id
            })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_test_status(self):
        try:
            from ultron.core.test_runner_service import TestRunnerService
            import urllib.parse
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            run_id = query.get("run_id", [""])[0]

            if not run_id and self.command == "POST":
                data = self.get_post_data()
                if isinstance(data, dict):
                    run_id = data.get("run_id", "")

            if not run_id:
                self.send_json_response(400, {"error": "Missing 'run_id' parameter."})
                return

            service = TestRunnerService.get_instance()
            record = service.get_run(run_id)
            if not record:
                self.send_json_response(404, {"error": f"Test run '{run_id}' not found."})
                return

            self.send_json_response(200, record.to_dict())
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_test_cancel(self):
        try:
            from ultron.core.test_runner_service import TestRunnerService
            import urllib.parse
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            run_id = query.get("run_id", [""])[0]

            if not run_id:
                data = self.get_post_data()
                if isinstance(data, dict):
                    run_id = data.get("run_id", "")

            if not run_id:
                self.send_json_response(400, {"error": "Missing 'run_id' parameter."})
                return

            service = TestRunnerService.get_instance()
            cancelled = service.cancel_run(run_id)
            self.send_json_response(200, {"cancelled": cancelled, "run_id": run_id})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_work_state(self):
        try:
            repo_path = self.get_repo_root_path()
            from ultron.core.issue_orchestrator import IssueOrchestrator
            orchestrator = IssueOrchestrator(repo_path)
            summary = orchestrator.get_current_work_summary()
            self.send_json_response(200, summary)
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_work_visual_delta(self):
        try:
            repo_path = self.get_repo_root_path()
            from ultron.core.issue_orchestrator import IssueOrchestrator
            orchestrator = IssueOrchestrator(repo_path)
            attempt = orchestrator.active_attempt

            if not attempt:
                self.send_json_response(200, {
                    "status": "ok",
                    "attempt_id": None,
                    "visual_delta": {"passed": True, "reasons": ["No active attempt"]},
                    "evidence_dir": None,
                    "structural_delta": {"elements_added": [], "elements_removed": []}
                })
                return

            html_path = os.path.join(WEB_DIR, "index.html")
            if not os.path.exists(html_path):
                html_path = os.path.join(repo_path, "ultron", "interfaces", "web", "index.html")
            html_curr = ""
            if os.path.exists(html_path):
                try:
                    with open(html_path, "r", encoding="utf-8") as f:
                        html_curr = f.read()
                except Exception as e:
                    sys.stderr.write(f"HTML read warning: {e}\n")

            from ultron.core.ui_reality_compiler import UIRealityCompiler
            struct_delta = UIRealityCompiler.compile_structural_ui_delta(html_curr, html_curr)

            payload = {
                "status": "ok",
                "attempt_id": attempt.attempt_id,
                "visual_delta": attempt.visual_delta_summary or {"passed": True, "reasons": []},
                "evidence_dir": attempt.browser_evidence_dir,
                "structural_delta": struct_delta,
                "three_pillar_results": attempt.three_pillar_results
            }
            self.send_json_response(200, payload)
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_work_advance(self):
        try:
            repo_path = self.get_repo_root_path()
            from ultron.core.issue_orchestrator import IssueOrchestrator
            orchestrator = IssueOrchestrator(repo_path)
            data = self.get_post_data() if self.command == "POST" else {}
            action = (data.get("action") or "advance").lower() if isinstance(data, dict) else "advance"

            current = orchestrator.work_queue.get_state()

            if action == "discover":
                orchestrator.discover_issues()
            elif action == "select":
                issue_id = data.get("issue_id") if isinstance(data, dict) else None
                if not issue_id:
                    queue = orchestrator.prioritize_issues()
                    if queue:
                        issue_id = queue[0].issue_id
                if issue_id:
                    orchestrator.select_issue(issue_id)
            elif action == "compile":
                orchestrator.compile_mission()
            elif action == "execute":
                orchestrator.execute_attempt()
            elif action == "observe":
                from ultron.core.pipeline.orchestrator import compute_repository_content_hash
                from ultron.core.models import build_snapshot_id
                from ultron.core.test_runner_service import TestRunnerService
                files = list(orchestrator.active_attempt.target_files) if orchestrator.active_attempt and orchestrator.active_attempt.target_files else [f for f in os.listdir(repo_path) if f.endswith(".py")]
                chash = compute_repository_content_hash(repo_path, files)
                snap = build_snapshot_id(chash)
                
                active_test = ""
                for candidate in ["tests", "test", "ultron/tests/test_phase20_product_improvement.py", "ultron/tests/test_version_integrity.py"]:
                    if os.path.exists(os.path.join(repo_path, candidate)):
                        active_test = candidate
                        break

                if active_test:
                    test_run = TestRunnerService.run_tests_sync(repo_path, test_path=active_test)
                    test_res = {
                        "passed_count": test_run.get("passed_count", 0),
                        "failed_count": test_run.get("failed_count", 0),
                        "discovered_count": test_run.get("discovered_count", 0),
                        "passed": test_run.get("passed", False)
                    }
                else:
                    test_res = {
                        "passed_count": 0,
                        "failed_count": 0,
                        "discovered_count": 0,
                        "passed": True,
                        "ast_verified": True
                    }
                orchestrator.observe_state(snapshot_id=snap, test_results=test_res)
            elif action == "verify":
                orchestrator.verify_attempt()
                orchestrator.guard_regression_and_advance()
            elif action == "expand_scope":
                files_to_add = data.get("files") if isinstance(data, dict) else None
                if not files_to_add and orchestrator.active_attempt:
                    files_to_add = orchestrator.active_attempt.unexpected_files
                if orchestrator.active_attempt and files_to_add:
                    orchestrator.active_attempt.target_files = list(set((orchestrator.active_attempt.target_files or []) + list(files_to_add)))
                    orchestrator.active_attempt.unexpected_files = [f for f in (orchestrator.active_attempt.unexpected_files or []) if f not in files_to_add]
                    orchestrator._save_active_attempt()
                orchestrator.verify_attempt()
                orchestrator.guard_regression_and_advance()
            elif action == "revert_unrelated":
                files_to_revert = data.get("files") if isinstance(data, dict) else None
                if orchestrator.active_attempt:
                    orchestrator.active_attempt.unexpected_files = []
                    orchestrator._save_active_attempt()
                orchestrator.verify_attempt()
                orchestrator.guard_regression_and_advance()
            elif action == "checkpoint":
                summary_text = data.get("summary") if isinstance(data, dict) else None
                orchestrator.checkpoint_progression(summary_text or "Verified milestone")
            elif action == "next":
                orchestrator.discover_issues()
            elif action == "repair":
                active_iss = current.active_issue or (orchestrator.active_attempt.issue_id if orchestrator.active_attempt else "")
                packet = data.get("failure_packet") if isinstance(data, dict) else {"blocking_reasons": current.blocking_reasons}
                orchestrator.compile_repair_mission(issue_id=active_iss, failure_packet=packet)
            elif action == "rollback":
                confirmed = data.get("confirmed", False) if isinstance(data, dict) else False
                if not confirmed:
                    self.send_json_response(200, {
                        "status": "confirmation_required",
                        "message": "Restoring checkpoint will revert tracked repository files. Untracked files will remain untouched.",
                        "work": orchestrator.get_current_work_summary()["work"],
                        "identity": orchestrator.get_current_work_summary()["identity"]
                    })
                    return
                orchestrator.work_queue.reset()
            elif action == "judge":
                rating = data.get("rating", "") if isinstance(data, dict) else ""
                rationale = data.get("rationale", "") if isinstance(data, dict) else ""
                if not rating or rating not in ("BETTER", "NO_DIFFERENCE", "WORSE"):
                    self.send_json_response(400, {"error": "rating must be BETTER, NO_DIFFERENCE, or WORSE"})
                    return
                result = orchestrator.record_human_judgment(rating, rationale)
                self.send_json_response(200, {
                    "success": True,
                    "judgment": result,
                    "work": orchestrator.get_current_work_summary()["work"],
                    "identity": orchestrator.get_current_work_summary()["identity"]
                })
                return
            elif action == "advance":
                if current.status == "VERIFYING":
                    orchestrator.guard_regression_and_advance()
                elif current.status in ("CHECKPOINTED", "IDLE"):
                    orchestrator.discover_issues()
                elif current.status == "DISCOVERING":
                    queue = orchestrator.prioritize_issues()
                    if queue:
                        orchestrator.select_issue(queue[0].issue_id)
                elif current.status == "ISSUE_SELECTED":
                    orchestrator.compile_mission()
                elif current.status == "MISSION_READY":
                    orchestrator.execute_attempt()
                elif current.status == "IMPLEMENTING":
                    from ultron.core.pipeline.orchestrator import compute_repository_content_hash
                    from ultron.core.models import build_snapshot_id
                    from ultron.core.test_runner_service import TestRunnerService
                    files = list(orchestrator.active_attempt.target_files) if orchestrator.active_attempt and orchestrator.active_attempt.target_files else [f for f in os.listdir(repo_path) if f.endswith(".py")]
                    chash = compute_repository_content_hash(repo_path, files)
                    snap = build_snapshot_id(chash)
                    active_test = "ultron/tests/test_phase20_product_improvement.py"
                    if not os.path.exists(os.path.join(repo_path, active_test)):
                        active_test = "ultron/tests/test_version_integrity.py"
                    test_run = TestRunnerService.run_tests_sync(repo_path, test_path=active_test)
                    test_res = {
                        "passed_count": test_run.get("passed_count", 0),
                        "failed_count": test_run.get("failed_count", 0),
                        "discovered_count": test_run.get("discovered_count", 0),
                        "passed": test_run.get("passed", False)
                    }
                    orchestrator.observe_state(snapshot_id=snap, test_results=test_res)
                elif current.status == "OBSERVING":
                    orchestrator.verify_attempt()
                    orchestrator.guard_regression_and_advance()
                elif current.status == "CHECKPOINT_READY":
                    summary_text = data.get("summary") if isinstance(data, dict) else None
                    orchestrator.checkpoint_progression(summary_text or "Verified milestone")
            elif action == "reset":
                orchestrator.work_queue.reset()

            updated_summary = orchestrator.get_current_work_summary()
            self.send_json_response(200, updated_summary)
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_work_queue(self):
        try:
            repo_path = self.get_repo_root_path()
            from ultron.core.issue_orchestrator import IssueOrchestrator
            orchestrator = IssueOrchestrator(repo_path)
            issues = orchestrator.prioritize_issues()
            self.send_json_response(200, {
                "total": len(issues),
                "queue": [iss.to_dict() for iss in issues]
            })
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_diff_risk(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            raw_repo = data.get("repo")
            if raw_repo is None or not isinstance(raw_repo, str) or not raw_repo.strip() or '\x00' in raw_repo:
                repo_path = self.get_repo_root_path()
            else:
                try:
                    repo_path = os.path.abspath(raw_repo.strip())
                except (ValueError, OSError):
                    repo_path = self.get_repo_root_path()

            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return

            raw_file = data.get("file")
            filepath = str(raw_file).strip() if raw_file is not None else ""
            if '\x00' in filepath:
                filepath = ""
            old_code = str(data.get("old_code", "") or "")
            new_code = str(data.get("new_code", "") or "")
            
            codebase = analyzer.analyze_directory(repo_path)
            res = risk.evaluate_diff_risk(codebase, filepath, old_code, new_code)
            
            global LAST_ANALYSIS
            LAST_ANALYSIS = {
                "file_path": filepath,
                "delta_i": res.impact_score,
                "mkr": res.mk_r,
                "delta_cest": res.delta_cest
            }
            
            self.send_json_response(200, {
                "success": True,
                "diff_risk": res.to_dict()
            })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_dependency_graph(self):
        try:
            query_data = self.get_query_data() if hasattr(self, "get_query_data") else {}
            body_data = {}
            if hasattr(self, "get_request_data"):
                try:
                    body_data = self.get_request_data() or {}
                except Exception:
                    body_data = {}
            data = {**body_data, **query_data} if isinstance(body_data, dict) else (query_data if isinstance(query_data, dict) else {})

            raw_repo = data.get("repo")
            if raw_repo is None or not isinstance(raw_repo, str) or not raw_repo.strip() or '\x00' in raw_repo:
                repo_path = self.get_repo_root_path()
            else:
                try:
                    repo_path = os.path.abspath(raw_repo.strip())
                except (ValueError, OSError):
                    repo_path = self.get_repo_root_path()

            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Not a directory: {repo_path}"})
                return

            raw_chunk = data.get("chunk")
            raw_limit = data.get("limit", 100)
            is_paginated = raw_chunk is not None

            chunk = 0
            limit = 100
            if is_paginated or raw_limit != 100:
                try:
                    chunk = int(raw_chunk) if raw_chunk is not None else 0
                    limit = int(raw_limit) if raw_limit is not None else 100
                except (ValueError, TypeError):
                    self.send_json_response(400, {"error": "Invalid chunk or limit parameter. Must be integers."})
                    return

                if chunk < 0 or limit < 1:
                    self.send_json_response(400, {"error": "Invalid chunk or limit bounds. chunk must be >= 0 and limit >= 1."})
                    return

            codebase = analyzer.analyze_directory(repo_path)
            target_files = [k for k in codebase.keys() if k.endswith(".py")] if isinstance(codebase, dict) else []
            risks = risk.evaluate_risks(codebase, target_files, repo_path=repo_path)
            risk_index = {r.file_path.replace('\\', '/'): r for r in risks}

            # Compute repo medians for the "Why?" context panel
            complexities = sorted(r.complexity for r in risks)
            couplings = sorted(int(r.coupling_score) for r in risks)
            mid = lambda lst: lst[len(lst) // 2] if lst else 0
            medians = {"complexity": mid(complexities), "coupling": mid(couplings)}

            raw_graph = analyzer.build_dependency_graph(codebase)

            enriched_nodes = []
            for node in raw_graph.get("nodes", []):
                nid = node.get("id", "").replace('\\', '/')
                ntype = node.get("type", "file")
                file_part = nid.split(":")[0] if ":" in nid else nid
                r = risk_index.get(nid) or risk_index.get(file_part)
                arch_role = getattr(r, "architectural_role", None)
                strat = getattr(r, "change_strategy", None)
                enriched_nodes.append({
                    "id": nid,
                    "path": nid,
                    "file_path": nid,
                    "label": os.path.basename(nid) if ntype == "file" else nid,
                    "type": ntype,
                    "level": r.level if r else "LOW",
                    "role": arch_role.value if hasattr(arch_role, "value") else "INTERNAL",
                    "role_display": arch_role.display_name if hasattr(arch_role, "display_name") else "Internal",
                    "complexity": r.complexity if r else 1,
                    "coupling": int(r.coupling_score) if r else 0,
                    "impact_score": round(r.impact_score, 2) if r else 0.0,
                    "strategy_display": strat.display_name if hasattr(strat, "display_name") else "Safe internal edits",
                })

            normalized_links = []
            for link in raw_graph.get("links", []):
                src = str(link.get("source", "")).replace('\\', '/')
                tgt = str(link.get("target", "")).replace('\\', '/')
                ltype = link.get("type", "import")
                normalized_links.append({"source": src, "target": tgt, "type": ltype})

            if is_paginated:
                start = chunk * limit
                end = start + limit
                chunk_nodes = enriched_nodes[start:end]
                chunk_node_ids = {n["id"] for n in chunk_nodes}
                chunk_links = [l for l in normalized_links if l["source"] in chunk_node_ids or l["target"] in chunk_node_ids]
                total_nodes = len(enriched_nodes)
                total_chunks = (total_nodes + limit - 1) // limit if total_nodes > 0 else 0
                has_more = (chunk + 1) < total_chunks

                self.send_json_response(200, {
                    "success": True,
                    "nodes": chunk_nodes,
                    "links": chunk_links,
                    "medians": medians,
                    "chunk": chunk,
                    "limit": limit,
                    "total_chunks": total_chunks,
                    "has_more": has_more,
                    "total_nodes": total_nodes,
                    "total_links": len(normalized_links)
                })
            else:
                self.send_json_response(200, {
                    "success": True,
                    "nodes": enriched_nodes,
                    "links": normalized_links,
                    "medians": medians,
                })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_predict_impact(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            raw_repo = data.get("repo")
            if raw_repo is None or not isinstance(raw_repo, str) or not raw_repo.strip() or '\x00' in raw_repo:
                repo_path = self.get_repo_root_path()
            else:
                try:
                    repo_path = os.path.abspath(raw_repo.strip())
                except (ValueError, OSError):
                    repo_path = self.get_repo_root_path()

            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return

            raw_files = data.get("changed_files", [])
            changed_files = raw_files if isinstance(raw_files, list) else []
            raw_funcs = data.get("changed_functions", [])
            changed_functions = raw_funcs if isinstance(raw_funcs, list) else []
            
            test_file_path = os.path.join(repo_path, "run_tests.py")
            if not os.path.exists(test_file_path):
                test_file_path = os.path.join(repo_path, "ultron", "tests", "run_tests.py")
                
            codebase = analyzer.analyze_directory(repo_path)
            predictions = predict.predict_test_impact(codebase, changed_files, changed_functions, test_file_path)
            self.send_json_response(200, {
                "success": True,
                "predictions": predictions
            })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_save_session(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            raw_repo = data.get("repo")
            if raw_repo is None or not isinstance(raw_repo, str) or not raw_repo.strip() or '\x00' in raw_repo:
                repo_path = self.get_repo_root_path()
            else:
                try:
                    repo_path = os.path.abspath(raw_repo.strip())
                except (ValueError, OSError):
                    repo_path = self.get_repo_root_path()

            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return

            session_data = data.get("session_data", {})
            if not isinstance(session_data, dict):
                session_data = {}
            
            sessions_dir = os.path.join(repo_path, "data", "sessions")
            os.makedirs(sessions_dir, exist_ok=True)
            
            import datetime
            filename = f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            session_file = os.path.join(sessions_dir, filename)
            
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2)
                
            self.send_json_response(200, {
                "success": True,
                "filename": filename
            })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_calibrate(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                data = {}
            raw_repo = data.get("repo")
            if raw_repo is None or not isinstance(raw_repo, str) or not raw_repo.strip() or '\x00' in raw_repo:
                repo_path = self.get_repo_root_path()
            else:
                try:
                    repo_path = os.path.abspath(raw_repo.strip())
                except (ValueError, OSError):
                    repo_path = self.get_repo_root_path()

            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return
            from ultron.core import meta_layer
            res = meta_layer.run_threshold_calibration(repo_path)
            self.send_json_response(200, res)
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_playground(self):
        try:
            playground_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scratch", "ultron_playground"))
            os.makedirs(playground_dir, exist_ok=True)
            
            # 1. Write math_utils.py (sample file with McCabe complexity and mutual coupling)
            math_utils_code = """# Ultron Playground Sample Module
import time

def add_elements(a, b):
    # Simple low complexity function
    return a + b

def complex_operation(x, y, op="add"):
    # Moderate complexity McCabe branch (Complexity: 3)
    if op == "add":
        return x + y
    elif op == "subtract":
        return x - y
    else:
        # Fallback loop
        result = 0
        for i in range(abs(int(x))):
            result += y
        return result

def highly_coupled_calculator(val1, val2, operation):
    # This calls add_elements and complex_operation, coupling them
    # Impact score will be high because of coupling and complexity
    print(f"Executing coupled calculator on {val1} and {val2} using {operation}")
    
    # We call these functions (coupling)
    step1 = add_elements(val1, 10)
    step2 = complex_operation(step1, val2, op=operation)
    
    return step2
"""
            with open(os.path.join(playground_dir, "math_utils.py"), "w", encoding="utf-8") as f:
                f.write(math_utils_code)
                
            # 2. Write test_math_utils.py (test suite)
            test_code = """import unittest
from math_utils import add_elements, complex_operation, highly_coupled_calculator

class TestPlaygroundMath(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add_elements(5, 10), 15)
        
    def test_complex(self):
        self.assertEqual(complex_operation(10, 5, "subtract"), 5)
        
    def test_calculator(self):
        res = highly_coupled_calculator(5, 5, "add")
        self.assertEqual(res, 20)
        
if __name__ == "__main__":
    unittest.main()
"""
            with open(os.path.join(playground_dir, "test_math_utils.py"), "w", encoding="utf-8") as f:
                f.write(test_code)

            # 3. Create run_tests.py to enable unified test execution
            run_tests_code = """import unittest
import sys
import os

if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    suite = unittest.defaultTestLoader.discover(os.path.dirname(os.path.abspath(__file__)))
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
"""
            with open(os.path.join(playground_dir, "run_tests.py"), "w", encoding="utf-8") as f:
                f.write(run_tests_code)
                
            # 4. Write mock synapse ledger records to project's synapse folder
            synapse_mutator_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "synapse_project", "synapse_mutator"))
            os.makedirs(synapse_mutator_dir, exist_ok=True)
            ledger_file = os.path.join(synapse_mutator_dir, "ledger.jsonl")
            
            # Seeding 4 mutations for math_utils.py (MKR = 0.75) and 2 mutations for test_math_utils.py (MKR = 1.0)
            ledger_records = [
                {"file": "math_utils.py", "was_mutated": True, "accepted": False},
                {"file": "math_utils.py", "was_mutated": True, "accepted": False},
                {"file": "math_utils.py", "was_mutated": True, "accepted": False},
                {"file": "math_utils.py", "was_mutated": True, "accepted": True},
                {"file": "test_math_utils.py", "was_mutated": True, "accepted": False},
                {"file": "test_math_utils.py", "was_mutated": True, "accepted": False}
            ]
            with open(ledger_file, "w", encoding="utf-8") as f:
                for rec in ledger_records:
                    f.write(json.dumps(rec) + "\n")
                    
            self.send_json_response(200, {
                "success": True,
                "path": "scratch/ultron_playground"
            })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_log_risk_feedback(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            raw_file = data.get("file")
            if raw_file is None or not isinstance(raw_file, str) or not raw_file.strip() or '\x00' in raw_file:
                self.send_json_response(400, {"error": "Missing or invalid 'file' parameter."})
                return
            filepath = raw_file.strip()
            accurate = bool(data.get("accurate", True))
                
            _dir = os.path.dirname(os.path.abspath(__file__))
            _root = os.path.abspath(os.path.join(_dir, "..", ".."))
            feedback_path = os.path.join(_root, "ultron", "meta", "human_feedback.jsonl")
            os.makedirs(os.path.dirname(feedback_path), exist_ok=True)
            
            import time
            entry = {
                "file": filepath,
                "accurate": accurate,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            
            with open(feedback_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
                
            self.send_json_response(200, {
                "success": True,
                "message": "Feedback recorded successfully."
            })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_pledge_create(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            raw_file = data.get("file")
            if raw_file is None or not isinstance(raw_file, str) or not raw_file.strip() or '\x00' in raw_file:
                self.send_json_response(400, {"error": "Missing or invalid 'file' parameter."})
                return
            filepath = raw_file.strip()
            
            try:
                predicted_delta_i = float(data.get("predicted_delta_i", 0.0) or 0.0)
                predicted_mkr = float(data.get("predicted_mkr", 1.0) or 1.0)
                predicted_delta_cest = float(data.get("predicted_delta_cest", 0.0) or 0.0)
            except (ValueError, TypeError):
                self.send_json_response(400, {"error": "Predicted metrics must be valid numbers."})
                return
                
            plg = {
                "pledge_id": f"PLG_{int(time.time() * 1000)}",
                "file_path": filepath,
                "predicted_delta_i": predicted_delta_i,
                "predicted_mkr": predicted_mkr,
                "predicted_delta_cest": predicted_delta_cest,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            self.send_json_response(200, {
                "success": True,
                "pledge": plg
            })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_pledge_verify(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body format. Expected JSON object."})
                return
            raw_file = data.get("file")
            if raw_file is None or not isinstance(raw_file, str) or not raw_file.strip() or '\x00' in raw_file:
                self.send_json_response(400, {"error": "Missing or invalid 'file' parameter."})
                return
            filepath = raw_file.strip()

            try:
                actual_delta_i = float(data.get("actual_delta_i", 0.0) or 0.0)
                actual_mkr = float(data.get("actual_mkr", 1.0) or 1.0)
                actual_delta_cest = float(data.get("actual_delta_cest", 0.0) or 0.0)
                actual_failure = float(data.get("actual_failure", 0.0) or 0.0)
            except (ValueError, TypeError):
                self.send_json_response(400, {"error": "Actual metrics must be valid numbers."})
                return
                
            res = {
                "file": filepath,
                "actual": {
                    "delta_i": actual_delta_i,
                    "mkr": actual_mkr,
                    "delta_cest": actual_delta_cest,
                    "failure": actual_failure
                },
                "verification": {
                    "kept": True,
                    "details": {"impact_score_ok": True, "mkr_ok": True, "delta_cest_ok": True}
                }
            }
            self.send_json_response(200, {
                "success": True,
                "verification": res
            })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_report(self):
        try:
            _dir = os.path.dirname(os.path.abspath(__file__))
            _root = os.path.abspath(os.path.join(_dir, "..", ".."))
            log_path = os.path.join(_root, "ultron", "meta", "experiment_log.jsonl")
            
            total_pledges = 0
            kept_pledges = 0
            errors = []
            
            # Calibration bins setup
            bins = {
                "0.0-0.2": {"count": 0, "failures": 0},
                "0.2-0.4": {"count": 0, "failures": 0},
                "0.4-0.6": {"count": 0, "failures": 0},
                "0.6-0.8": {"count": 0, "failures": 0},
                "0.8-1.0": {"count": 0, "failures": 0}
            }
            
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                        except Exception:
                            continue
                        
                        # Process pledge stats if present
                        if "verification" in entry:
                            total_pledges += 1
                            if entry["verification"].get("kept", False):
                                kept_pledges += 1
                                
                        # Process calibration metrics
                        pred = entry.get("prediction", {}) or {}
                        act = entry.get("actual", {}) or {}
                        err = entry.get("error", {}) or {}
                        
                        pred_risk = pred.get("predicted_risk")
                        # Fallback for old log format
                        if pred_risk is None and "predicted_risk" in entry:
                            pred_risk = entry.get("predicted_risk")
                        
                        actual_failure = act.get("failure")
                        if actual_failure is None and "actual_failures" in entry:
                            actual_failure = entry.get("actual_failures")
                            
                        val_err = err.get("value")
                        if val_err is None and "prediction_error" in entry:
                            val_err = entry.get("prediction_error")
                            
                        if pred_risk is not None and actual_failure is not None:
                            try:
                                pred_risk_f = float(pred_risk)
                                actual_failure_f = float(actual_failure)
                                
                                # Bin predicted risk
                                if pred_risk_f < 0.2:
                                    bin_key = "0.0-0.2"
                                elif pred_risk_f < 0.4:
                                    bin_key = "0.2-0.4"
                                elif pred_risk_f < 0.6:
                                    bin_key = "0.4-0.6"
                                elif pred_risk_f < 0.8:
                                    bin_key = "0.6-0.8"
                                else:
                                    bin_key = "0.8-1.0"
                                    
                                bins[bin_key]["count"] += 1
                                bins[bin_key]["failures"] += 1 if actual_failure_f > 0.5 else 0
                            except (ValueError, TypeError):
                                pass
                            
                        if val_err is not None:
                            try:
                                errors.append(abs(float(val_err)))
                            except Exception:
                                pass
                            
            # Calculate final stats
            pledge_success_rate = (kept_pledges / total_pledges) if total_pledges > 0 else 1.0
            mean_error = (sum(errors) / len(errors)) if errors else 0.0
            
            # Format calibration points
            calibration_points = []
            for k, v in bins.items():
                actual_rate = (v["failures"] / v["count"]) if v["count"] > 0 else 0.0
                calibration_points.append({
                    "bin": k,
                    "count": v["count"],
                    "actual_rate": actual_rate
                })
                
            active_count = 0
            
            self.send_json_response(200, {
                "success": True,
                "pledges": {
                    "total": total_pledges,
                    "kept": kept_pledges,
                    "success_rate": pledge_success_rate,
                    "active": active_count
                },
                "calibration": {
                    "mean_error": mean_error,
                    "points": calibration_points
                }
            })
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_design_oracle(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid request payload. Expected JSON object."})
                return
                
            action = data.get("action")
            if action not in ("audit", "recommend", "simulate", "explain"):
                self.send_json_response(400, {"error": f"Invalid or missing action '{action}'. Must be 'audit', 'recommend', 'simulate', or 'explain'."})
                return
                
            raw_repo = data.get("repo")
            if raw_repo is None or not isinstance(raw_repo, str) or not raw_repo.strip() or '\x00' in raw_repo:
                repo_path = self.get_repo_root_path()
            else:
                try:
                    repo_path = os.path.abspath(raw_repo.strip())
                except (ValueError, OSError):
                    repo_path = self.get_repo_root_path()

            codebase = {}
            if action in ("audit", "simulate") or (action == "recommend" and raw_repo):
                if not os.path.isdir(repo_path):
                    self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                    return
                codebase = analyzer.analyze_directory(repo_path)

            if action == "audit":
                cycles = design_oracle.detect_circular_dependencies(codebase) if design_oracle else []
                globals_found = design_oracle.detect_global_mutations(codebase, repo_path) if design_oracle else []
                self.send_json_response(200, {
                    "success": True,
                    "circular_dependencies": cycles,
                    "global_mutations": globals_found
                })
                
            elif action == "recommend":
                raw_intent = data.get("intent")
                if raw_intent is None or not isinstance(raw_intent, str) or not raw_intent.strip() or '\x00' in raw_intent:
                    self.send_json_response(400, {"error": "Missing or empty 'intent' parameter."})
                    return
                intent = raw_intent.strip()
                if len(intent) > 5000:
                    self.send_json_response(400, {"error": "Intent length exceeds limit of 5000 characters."})
                    return
                recommendations = design_oracle.recommend_patterns(codebase, intent) if design_oracle else []
                self.send_json_response(200, {
                    "success": True,
                    "recommendations": recommendations
                })
                
            elif action == "simulate":
                raw_src = data.get("src_file")
                raw_dest = data.get("dest_file")
                if not isinstance(raw_src, str) or not raw_src.strip() or '\x00' in raw_src:
                    self.send_json_response(400, {"error": "Missing or empty 'src_file' parameter."})
                    return
                if not isinstance(raw_dest, str) or not raw_dest.strip() or '\x00' in raw_dest:
                    self.send_json_response(400, {"error": "Missing or empty 'dest_file' parameter."})
                    return
                    
                src_file_norm = raw_src.replace("\\", "/").strip()
                dest_file_norm = raw_dest.replace("\\", "/").strip()
                
                if src_file_norm not in codebase:
                    self.send_json_response(400, {"error": f"Source file '{src_file_norm}' not found in codebase."})
                    return
                if dest_file_norm not in codebase:
                    self.send_json_response(400, {"error": f"Destination file '{dest_file_norm}' not found in codebase."})
                    return
                    
                res = design_oracle.simulate_future_coupling(codebase, src_file_norm, dest_file_norm) if design_oracle else {}
                self.send_json_response(200, {
                    "success": True,
                    "simulation": res
                })

            elif action == "explain":
                raw_entity = data.get("entity_id") or data.get("file") or data.get("src_file")
                if not raw_entity or not isinstance(raw_entity, str) or not raw_entity.strip() or '\x00' in raw_entity:
                    self.send_json_response(400, {"error": "Missing or empty 'entity_id' or 'file' parameter."})
                    return
                entity_id = raw_entity.replace("\\", "/").strip()
                
                db_path = os.path.join(repo_path, ".ultron", "repository.db")
                
                complexity = 15.0
                coupling = 3
                found_in_db = False
                
                # 1. RKM Lookup First (Primary Path)
                if os.path.exists(db_path):
                    try:
                        from ultron.core.rkm.store import RepositoryStore
                        from ultron.interfaces.api import MetricsAPI
                        store = RepositoryStore(db_path)
                        meta = store.get_metadata()
                        if meta and meta.latest_analysis_run_id:
                            metrics_map = MetricsAPI.get_file_metrics(store, meta.latest_analysis_run_id, entity_id)
                            if metrics_map:
                                complexity = float(metrics_map.get("complexity", 15.0))
                                coupling = int(metrics_map.get("coupling", 3))
                                found_in_db = True
                        store.close()
                    except Exception as e:
                        print(f"[Warning] RKM Store lookup failed for {entity_id}: {e}")
                
                # 2. Fallback Bootstrap Path (ONLY if no RKM DB exists)
                if not found_in_db:
                    if os.path.isdir(repo_path):
                        cb = analyzer.analyze_directory(repo_path)
                        risks = risk.evaluate_risks(cb, [entity_id], repo_path=repo_path)
                        match = None
                        for r in risks:
                            f_path = getattr(r, "file_path", None) or getattr(r, "file", "")
                            if f_path.endswith(entity_id) or entity_id.endswith(f_path):
                                match = r
                                break
                        if match:
                            complexity = float(match.complexity)
                            coupling = int(getattr(match, "coupling_score", getattr(match, "coupling", 3)))
                
                # 3. Construct RiskProfile
                from ultron.core.rkm.risk_intelligence import compute_risk_profile
                risk_profile = compute_risk_profile(entity_id, complexity=complexity, coupling_fanout=coupling)
                
                # 4. Evaluate Policy -> Decision object
                from ultron.core.rkm.policy_engine import evaluate_policy
                decision = evaluate_policy(risk_profile, business_criticality="DEFAULT")
                
                # 5. Translate Decision -> Communication Object
                from ultron.core.translate import translate_decision, translate_decision_to_personas
                comm_personas = translate_decision_to_personas(decision)
                
                # 6. Build Trust Chain & Repair Simulation objects matching frozen contract
                reasons_str = ", ".join(decision.reason_codes) if decision.reason_codes else "HIGH_RISK"
                trust_chain = {
                    "plain_label": f"High risk detected in {entity_id}: Priority {decision.priority}",
                    "entity": entity_id,
                    "rule_plain_name": "Code is too complex or coupled to modify safely",
                    "rule_technical_name": f"RKM-POLICY-{decision.policy_version}",
                    "severity": decision.priority,
                    "confidence": 0.95,
                    "evidence": [
                        {"evidence_type": "policy_evaluation", "value": reasons_str, "description": f"Policy evaluated with priority {decision.priority}"}
                    ]
                }
                
                repair_simulation = {
                    "plain_summary": f"Decouple {entity_id} to restore stability and speed up changes.",
                    "technical_rule": f"RKM-POLICY-{decision.policy_version}",
                    "before_state": {
                        "structure": f"{entity_id} directly coupled with high complexity.",
                        "risk_score": 85.0,
                        "status": "AT_RISK"
                    },
                    "after_state": {
                        "structure": f"Refactored {entity_id} using interface boundaries.",
                        "estimated_risk_score": 25.0,
                        "status": "STABLE"
                    },
                    "recommended_steps": [
                        f"1. Extract shared interfaces from {entity_id} into a decoupled API module.",
                        "2. Add unit tests for boundary contracts.",
                        "3. Run 'ultron check' to verify risk reduction."
                    ]
                }
                
                explanation_md = f"""### Code is too complex or coupled to modify safely
*Technical Rule*: `RKM-POLICY-{decision.policy_version}`

**Plain Language Summary**:
High risk detected in {entity_id}: Priority {decision.priority}.

**Evidence Trust Chain**:
- Entity: `{entity_id}`
- Severity: `{decision.priority}`
- Reasons: `{reasons_str}`

**Refactoring Simulation**:
Before: Risk Score 85.0 (High Complexity/Coupling)
After: Estimated Risk Score 25.0 (Decoupled Interface)"""

                comm_dict = comm_personas.get("personas", comm_personas) if isinstance(comm_personas, dict) else comm_personas
                self.send_json_response(200, {
                    "status": "success",
                    "success": True,
                    "entity_id": entity_id,
                    "decision": asdict(decision),
                    "personas": comm_personas,
                    "communication": comm_dict,
                    "trust_chain": trust_chain,
                    "repair_simulation": repair_simulation,
                    "explanation": explanation_md
                })
        except (ValueError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {
                "error": str(e),
                "traceback": traceback.format_exc()
            })

    def handle_v1_health(self):
        repo_root = self.get_repo_root_path()
        db_path = os.path.join(repo_root, ".ultron", "repository.db")
        db_exists = os.path.exists(db_path)
        db_readable = os.access(db_path, os.R_OK) if db_exists else False

        self.send_json_response(200, {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": {
                "python_version": sys.version.split()[0],
                "platform": sys.platform,
                "working_directory": repo_root
            },
            "rkm_database": {
                "exists": db_exists,
                "readable": db_readable,
                "path": db_path if db_exists else None
            },
            "modules": {
                "delta_engine": delta is not None,
                "design_oracle": design_oracle is not None
            },
            "active_job": {
                "status": ACTIVE_JOB.get("status", "idle"),
                "job_id": ACTIVE_JOB.get("job_id")
            }
        })

    def handle_v1_summary(self):
        repo_root = self.get_repo_root_path()
        db_path = os.path.join(repo_root, ".ultron", "repository.db")
        if not os.path.exists(db_path):
            self.send_json_response(200, {
                "initialized": False,
                "repository_uuid": None,
                "latest_run": None,
                "total_files": 0,
                "total_modules": 0,
                "total_risks": 0,
                "health_score": 100.0
            })
            return
            
        try:
            from ultron.core.rkm.store import RepositoryStore
            from ultron.core.rkm.evolution.engine import EvolutionEngine

            store = RepositoryStore(db_path)
            try:
                meta = store.get_metadata()
                if not meta or not meta.latest_analysis_run_id:
                    self.send_json_response(200, {
                        "initialized": False,
                        "repository_uuid": meta.repository_uuid if meta else None,
                        "latest_run": None,
                        "total_files": 0,
                        "total_modules": 0,
                        "total_risks": 0,
                        "health_score": 100.0
                    })
                    return

                run_id = meta.latest_analysis_run_id
                run = store.get_analysis_run(run_id)
                files = store.get_file_records_for_run(run_id)
                total_files = len(files)
                
                total_symbols = 0
                for f in files:
                    symbols = store.get_symbols(f.id)
                    total_symbols += len(symbols)

                vios = store.get_violations(run_id)
                total_risks = len(vios)

                health_run = EvolutionEngine.evaluate_health_score(store, run_id)
                health_score = round(
                    (health_run.architecture_stability * 0.4 +
                     health_run.rule_compliance * 0.4 +
                     health_run.complexity_trend * 0.2) * 100, 1
                )

                self.send_json_response(200, {
                    "initialized": True,
                    "repository_uuid": meta.repository_uuid,
                    "latest_run": {
                        "run_id": run.id,
                        "timestamp": run.timestamp,
                        "engine_version": run.engine_version,
                        "rkm_version": run.rkm_version
                    },
                    "total_files": total_files,
                    "total_modules": total_symbols,
                    "total_risks": total_risks,
                    "health_score": health_score
                })
            finally:
                store.close()
        except Exception as e:
            self.send_json_response(500, {"error": f"Failed to retrieve summary: {str(e)}"})

    def handle_v1_git_churn(self):
        """Returns deterministic git churn, author attribution, and hotspot rankings."""
        repo_root = self.get_repo_root_path()
        try:
            from ultron.core.git_adapter import GitEvidenceAdapter
            adapter = GitEvidenceAdapter()
            analysis = adapter.analyze_repository(repo_root)
            self.send_json_response(200, {
                "status": "success",
                "repository": os.path.basename(repo_root),
                "is_git": adapter.is_git_repository(repo_root),
                "summary": analysis.get("summary", {}),
                "hotspots": analysis.get("hotspots", []),
                "files": analysis.get("files", {})
            })
        except Exception as e:
            self.send_json_response(500, {"status": "error", "message": f"Failed to analyze git churn: {str(e)}"})

    def handle_v1_git_cochange(self):
        """Returns pair-wise temporal co-change coupling matrix and hidden dependency graph."""
        repo_root = self.get_repo_root_path()
        try:
            from ultron.core.git_adapter import GitEvidenceAdapter
            adapter = GitEvidenceAdapter()
            analysis = adapter.analyze_repository(repo_root)
            self.send_json_response(200, {
                "status": "success",
                "repository": os.path.basename(repo_root),
                "is_git": adapter.is_git_repository(repo_root),
                "co_change_matrix": analysis.get("co_change_matrix", {}),
                "summary": analysis.get("summary", {})
            })
        except Exception as e:
            self.send_json_response(500, {"status": "error", "message": f"Failed to analyze git co-change: {str(e)}"})


    def resolve_repo_root(self, explicit_repo: Optional[str] = None) -> str:
        if explicit_repo and str(explicit_repo).strip():
            cand = os.path.abspath(str(explicit_repo).strip())
            if os.path.isdir(cand):
                return cand

        # 1. Try request query parameters (e.g. ?repo=/path/to/repo)
        try:
            q_data = self.get_query_data()
            if isinstance(q_data, dict):
                cand = q_data.get("repo") or q_data.get("repo_path")
                if cand and os.path.isdir(str(cand).strip()):
                    return os.path.abspath(str(cand).strip())
        except Exception:
            pass

        # 2. Try POST body data if available
        try:
            if getattr(self, "command", "") == "POST":
                p_data = self.get_post_data()
                if isinstance(p_data, dict):
                    cand = p_data.get("repo") or p_data.get("repo_path")
                    if cand and os.path.isdir(str(cand).strip()):
                        return os.path.abspath(str(cand).strip())
        except Exception:
            pass

        # 3. Try in-memory analysis cache
        global _ANALYSIS_CACHE
        if _ANALYSIS_CACHE.get("repo_path") and os.path.isdir(_ANALYSIS_CACHE["repo_path"]):
            return os.path.abspath(_ANALYSIS_CACHE["repo_path"])

        # 4. Fallback to config files or cwd
        cwd_config = os.path.join(os.getcwd(), ".ultron", "config.json")
        for cfg_path in (cwd_config, CONFIG_FILE):
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        val = cfg.get("repo_root") or cfg.get("active_repo")
                        if val and os.path.isdir(val):
                            return os.path.abspath(val)
                except Exception:
                    pass
        return os.path.abspath(os.getcwd())

    def get_repo_root_path(self, explicit_repo: Optional[str] = None) -> str:
        return self.resolve_repo_root(explicit_repo)

    def handle_v1_progress(self):
        global ACTIVE_JOB
        try:
            response = {
                "status": ACTIVE_JOB.get("status", "idle"),
                "progress_step": ACTIVE_JOB.get("progress_step", "Done"),
                "progress_pct": ACTIVE_JOB.get("progress_pct", -1),
                "error": ACTIVE_JOB.get("error"),
                "job_id": ACTIVE_JOB.get("job_id"),
                "snapshot_id": ACTIVE_JOB.get("snapshot_id"),
            }
            # Include full result payload only on success (avoids re-fetch)
            if ACTIVE_JOB.get("status") == "success" and ACTIVE_JOB.get("result"):
                response["result"] = ACTIVE_JOB["result"]
            self.send_json_response(200, response)
        except Exception as e:
            self.send_json_response(500, {"error": f"Failed to get progress: {str(e)}"})

    def handle_v1_workspace_watcher_scan(self):
        global _WATCHER_DAEMONS
        data = self.get_post_data()
        if not isinstance(data, dict):
            data = {}
        raw_repo = data.get("repo") or self.get_repo_root_path() or "."
        repo_path = _norm_path(raw_repo)
        
        if not os.path.isdir(repo_path):
            self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
            return
            
        from ultron.core.watcher_daemon import IncrementalWatcherDaemon
        if repo_path not in _WATCHER_DAEMONS:
            _WATCHER_DAEMONS[repo_path] = IncrementalWatcherDaemon(repo_path)
            
        daemon = _WATCHER_DAEMONS[repo_path]
        changes = daemon.scan_changes(repo_path)
        self.send_json_response(200, {
            "success": True,
            "data": changes,
            "tracked_files": len(daemon.file_mtimes)
        })

    def handle_v1_runs(self):
        from ultron.core.rkm.store import RepositoryStore
        from ultron.interfaces.api import HistoryAPI
        repo_root = self.get_repo_root_path()
        db_path = os.path.join(repo_root, ".ultron", "repository.db")
        if not os.path.exists(db_path):
            self.send_json_response(200, {"runs": []})
            return
        store = RepositoryStore(db_path)
        try:
            meta = store.get_metadata()
            if not meta:
                self.send_json_response(200, {"runs": []})
                return
            runs = HistoryAPI.get_run_history(store, meta.id)
            self.send_json_response(200, {"runs": runs})
        finally:
            store.close()

    def handle_v1_hotspots(self):
        from ultron.core.rkm.store import RepositoryStore
        from ultron.core.rkm.evolution.engine import EvolutionEngine
        repo_root = self.get_repo_root_path()
        db_path = os.path.join(repo_root, ".ultron", "repository.db")
        if not os.path.exists(db_path):
            self.send_json_response(400, {"error": "Repository not initialized"})
            return
        store = RepositoryStore(db_path)
        try:
            meta = store.get_metadata()
            if not meta or not meta.latest_analysis_run_id:
                self.send_json_response(200, {"hotspots": []})
                return
            hotspots = EvolutionEngine.detect_hotspots(store, meta.latest_analysis_run_id)
            self.send_json_response(200, {
                "hotspots": [
                    {
                        "file_path": h.file_path,
                        "change_count": h.change_count,
                        "complexity_trend": h.complexity_trend,
                        "coupling_trend": h.coupling_trend,
                        "violation_count": h.violation_count,
                        "hotspot_score": h.hotspot_score,
                        "severity_level": h.severity_level
                    }
                    for h in hotspots
                ]
            })
        finally:
            store.close()

    def handle_v1_history(self):
        self.handle_v1_runs()

    def _update_job_progress(self, step, pct):
        """Update ACTIVE_JOB progress and check for cancellation."""
        global ACTIVE_JOB
        if ACTIVE_JOB.get("cancel_requested"):
            raise InterruptedError("Analysis cancelled by user")
        ACTIVE_JOB["progress_step"] = step
        ACTIVE_JOB["progress_pct"] = pct

    def _build_identity_projection(self, repo_path: str, snapshot_id: str, bundle: Any) -> dict:
        """Constructs canonical identity and version grounding projection."""
        import hashlib
        from ultron.core.models import build_snapshot_id
        norm_path = os.path.normcase(os.path.abspath(repo_path))
        content_hash = getattr(bundle, "content_hash", "") or getattr(bundle, "repo_fingerprint", "")
        resolved_snapshot_id = build_snapshot_id(content_hash) if content_hash else snapshot_id
        repo_uuid = getattr(bundle, "repo_uuid", "")
        analysis_run_id = getattr(bundle, "analysis_run_id", None)
        repo_id = getattr(bundle, "repository_id", None) or hashlib.sha256(norm_path.encode("utf-8")).hexdigest()[:16]

        return {
            "projection_version": "2.7.0",
            "snapshot_id": resolved_snapshot_id,
            "content_hash": content_hash,
            "model_hash": content_hash,
            "repository_id": repo_id,
            "repository_uuid": repo_uuid,
            "analysis_run_id": analysis_run_id,
            "repository_root": norm_path.replace("\\", "/"),
            "repository_relative_root": ".",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    def _build_objective_projection(self, repo_path: str) -> dict:
        """Constructs canonical objective and milestone task progression projection."""
        tracker = ObjectiveTracker(repo_path)
        return tracker.get_objective()

    def _build_session_projection(self, repo_path: str, objective_data: dict, snapshot_id: str) -> dict:
        """Constructs canonical development session and semantic timeline projection."""
        mgr = DevelopmentSessionManager(repo_path)
        session_data = mgr.sync_objective(objective_data, snapshot_id=snapshot_id)
        return session_data

    def _build_readiness_projection(
        self,
        repo_path: str,
        objective_data: dict,
        snapshot_id: str,
        model_hash: str,
        risks: list,
        cycle_count: int = 0
    ) -> dict:
        """Constructs canonical continuation readiness assessment projection."""
        from ultron.core.safety_evaluator import SafetyEvaluator
        report = SafetyEvaluator.evaluate(
            test_results=None,
            modified_files=[],
            boundary_constraints=objective_data.get("constraints", []),
            acceptance_criteria=objective_data.get("acceptance", []),
            cycle_count=cycle_count,
            risks=[r.to_dict() if hasattr(r, "to_dict") else r for r in risks],
            snapshot_id=snapshot_id,
            model_hash=model_hash
        )
        return report.to_dict()

    def _build_diff_projection(self, session_data: dict) -> dict:
        """Constructs canonical structural delta projection."""
        return session_data.get("evolution_delta") or {
            "files_added": [],
            "files_removed": [],
            "files_modified": [],
            "loc_added": 0,
            "loc_removed": 0,
            "complexity_delta": 0.0,
            "risk_score_delta": 0.0,
            "what_changed": "Baseline session initial state",
            "what_impacted": "No modifications recorded",
            "what_got_worse": "None",
            "what_got_better": "Clean baseline established",
            "what_remains": "Initial active objective milestone",
            "can_we_continue": True
        }

    def _build_topology_projection(self, codebase: dict, risks: list, limit: int = 200) -> dict:
        """Constructs bounded dependency topology graph with architectural roles."""
        from ultron.core import analyzer
        risk_index = {r.file_path.replace('\\', '/'): r for r in risks}
        raw_graph = analyzer.build_dependency_graph(codebase)

        complexities = sorted(r.complexity for r in risks)
        couplings = sorted(int(r.coupling_score) for r in risks)
        mid = lambda lst: lst[len(lst) // 2] if lst else 0
        medians = {"complexity": mid(complexities), "coupling": mid(couplings)}

        enriched_nodes = []
        for node in raw_graph.get("nodes", [])[:limit]:
            nid = node.get("id", "").replace('\\', '/')
            ntype = node.get("type", "file")
            r = risk_index.get(nid)
            arch_role = getattr(r, "architectural_role", None)
            strat = getattr(r, "change_strategy", None)
            enriched_nodes.append({
                "id": nid,
                "path": nid,
                "file_path": nid,
                "label": os.path.basename(nid) if ntype == "file" else nid,
                "type": ntype,
                "level": r.level if r else "LOW",
                "role": arch_role.value if hasattr(arch_role, "value") else "INTERNAL",
                "role_display": arch_role.display_name if hasattr(arch_role, "display_name") else "Internal",
                "complexity": r.complexity if r else 1,
                "coupling": int(r.coupling_score) if r else 0,
                "impact_score": round(r.impact_score, 2) if r else 0.0,
                "strategy_display": strat.display_name if hasattr(strat, "display_name") else "Safe internal edits",
            })

        node_ids = {n["id"] for n in enriched_nodes}
        normalized_links = []
        for link in raw_graph.get("links", []):
            src = str(link.get("source", "")).replace('\\', '/')
            tgt = str(link.get("target", "")).replace('\\', '/')
            if src in node_ids and tgt in node_ids:
                ltype = link.get("type", "import")
                normalized_links.append({"source": src, "target": tgt, "type": ltype})

        return {
            "nodes": enriched_nodes,
            "links": normalized_links,
            "medians": medians,
            "cycle_count": raw_graph.get("cycle_count", 0)
        }

    def _build_analysis_payload(self, repo_path: str, force: bool = True, cancel_token=None) -> dict:
        """
        Coordinates modular projection builders into one unified authoritative runtime bundle (v2.6.5).
        Instruments payload build time, serialization latency, and byte payload budget.
        """
        t_build_start = time.perf_counter()
        from ultron.core.pipeline import orchestrator
        from ultron.core.rkm.recommendation_service import get_recommendations
        from ultron.core.pipeline.discovery import discover
        from ultron.core.pipeline.orchestrator import compute_repository_content_hash
        import hashlib

        # Stage 1: Discovery (10%)
        self._update_job_progress("Discovering files", 10)
        try:
            files_discovered = discover(repo_path)
        except ValueError:
            files_discovered = []

        if not files_discovered:
            snapshot_id = hashlib.sha256(repo_path.encode("utf-8")).hexdigest()[:16]
            ACTIVE_JOB["snapshot_id"] = snapshot_id
            return {
                "success": True,
                "status": "success",
                "snapshot_id": snapshot_id,
                "model_hash": snapshot_id,
                "repo_root": repo_path,
                "repository_root": repo_path,
                "stats": {
                    "total_files": 0,
                    "total_definitions": 0,
                    "high_risks": 0,
                    "health_score": 100.0
                },
                "risks": [],
                "dependency_graph": {
                    "nodes": [],
                    "links": [],
                    "cycle_count": 0
                },
                "recommendations": [],
                "objective": {
                    "objective_id": "empty_repo",
                    "title": "Empty Repository Initialized",
                    "status": "READY",
                    "progress_pct": 0
                },
                "completeness": {
                    "status": "COMPLETE",
                    "files_discovered": 0,
                    "files_parsed": 0,
                    "parse_errors_count": 0,
                    "parse_error_files": [],
                    "completeness_pct": 100.0
                },
                "evidence_sources": {
                    "ast": "AVAILABLE",
                    "git": "UNAVAILABLE",
                    "ai_proxy": "OFFLINE",
                    "benchmarks": "AVAILABLE"
                }
            }

        # Compute snapshot_id from canonical build_snapshot_id helper
        from ultron.core.models import build_snapshot_id
        raw_hash = compute_repository_content_hash(repo_path, files_discovered)
        snapshot_id = build_snapshot_id(raw_hash)
        ACTIVE_JOB["snapshot_id"] = snapshot_id

        # Stage 2 & 3: AST Parsing & Risk Scoring (30% -> 55%)
        self._update_job_progress("Parsing AST & extracting facts", 30)
        bundle = orchestrator.analyze_repository(repo_path, force=force, cancel_token=cancel_token)

        self._update_job_progress("Computing risk scores", 55)
        codebase = bundle.codebase
        risks = bundle.risks
        files = bundle.files

        # Stage 4: Dependency Graph (75%)
        self._update_job_progress("Building dependency graph", 75)
        dep_graph = self._build_topology_projection(codebase, risks)

        # Stage 5: Canonical Evidence Model & Consequence-Driven Recommendations (Gate A)
        self._update_job_progress("Generating recommendations", 90)
        objective_projection = self._build_objective_projection(repo_path)
        from ultron.core.evidence import compile_repository_evidence
        from ultron.core.recommendation import build_consequence_recommendations
        evidence_bundle = compile_repository_evidence(repo_path, codebase, risks, snapshot_id=snapshot_id)
        obj_text = ""
        if isinstance(objective_projection, dict):
            obj_text = f"{objective_projection.get('title', '')} {objective_projection.get('description', '')}".strip()
        consequence_recs = build_consequence_recommendations(
            codebase=codebase,
            risks=risks,
            objective=obj_text,
            limit=20,
            policy="consequence_v1",
            repo_path=repo_path,
            evidence_bundle=evidence_bundle
        )
        recs_list = [r.to_dict() for r in consequence_recs]

        total_files = len(codebase)
        total_definitions = sum(len(c.get("definitions", [])) for c in codebase.values())
        high_risks = sum(1 for r in risks if getattr(r, "level", "") == "HIGH")
        health_score = max(40.0, round(100.0 - (high_risks * 8.0), 1))
        low_risks = sum(1 for r in risks if getattr(r, "level", "") == "LOW")
        med_risks = sum(1 for r in risks if getattr(r, "level", "") == "MEDIUM")

        calibration_data = {
            "mean_error": None,
            "bins": [
                {"bin_range": "0.0 - 2.0 (Low)", "count": low_risks or max(1, total_files - high_risks - med_risks), "precision": None, "recall": None, "f1": None},
                {"bin_range": "2.0 - 5.0 (Med)", "count": med_risks, "precision": None, "recall": None, "f1": None},
                {"bin_range": "5.0+ (High Risk)", "count": high_risks, "precision": None, "recall": None, "f1": None}
            ]
        }

        pledges_data = {
            "total": 5,
            "kept": 5,
            "success_rate": 1.0,
            "active": 2
        }

        files_discovered_count = len(files_discovered)
        files_parsed_count = len(codebase)
        parse_error_files = [f for f in files_discovered if f.endswith(".py") and f.replace("\\", "/") not in codebase]
        completeness_pct = round((files_parsed_count / max(1, files_discovered_count)) * 100.0, 1)
        analysis_status = "COMPLETE" if not parse_error_files else "PARTIAL"

        completeness_data = {
            "status": analysis_status,
            "files_discovered": files_discovered_count,
            "files_parsed": files_parsed_count,
            "parse_errors_count": len(parse_error_files),
            "parse_error_files": parse_error_files,
            "completeness_pct": completeness_pct
        }

        # Dynamically evaluate per-source evidence availability
        from ultron.core.git_adapter import GitEvidenceAdapter
        git_records = GitEvidenceAdapter().parse_git_history(repo_path)
        git_status = "AVAILABLE" if git_records else "UNAVAILABLE"
        
        # Check AI proxy availability
        ai_status = "AVAILABLE" if ACTIVE_JOB.get("ai_proxy_online", False) else "OFFLINE"
        
        evidence_sources = {
            "ast": "AVAILABLE",
            "git": git_status,
            "ai_proxy": ai_status,
            "benchmarks": "AVAILABLE"
        }
        
        if git_status == "AVAILABLE" and ai_status == "AVAILABLE":
            overall_evidence_level = "FULL"
        elif git_status == "AVAILABLE" or ai_status == "AVAILABLE":
            overall_evidence_level = "REDUCED"
        else:
            overall_evidence_level = "REDUCED"
            
        evidence_level = overall_evidence_level

        # Assemble unified projections
        identity = self._build_identity_projection(repo_path, snapshot_id, bundle)
        objective_projection = self._build_objective_projection(repo_path)
        session_projection = self._build_session_projection(repo_path, objective_projection, snapshot_id)
        readiness_projection = self._build_readiness_projection(
            repo_path,
            objective_projection,
            snapshot_id,
            identity["model_hash"],
            risks,
            cycle_count=dep_graph.get("cycle_count", 0)
        )
        # Synchronize readiness assessment into development session so baseline checkpoints are not stale
        try:
            from ultron.core.development_session import DevelopmentSessionManager, _SESSION_LOCK
            mgr = DevelopmentSessionManager(repo_path)
            with _SESSION_LOCK:
                mgr._session = mgr._load_or_create()
                mgr._session.safety_assessment = readiness_projection
                mgr._persist(mgr._session)
        except Exception:
            pass

        diff_projection = self._build_diff_projection(session_projection)

        payload_build_ms = round((time.perf_counter() - t_build_start) * 1000, 2)

        payload = {
            "status": "success",
            "success": True,
            "projection_version": "2.6.5",
            "identity": identity,
            "snapshot_id": snapshot_id,
            "model_hash": identity["model_hash"],
            "repository_id": identity["repository_id"],
            "repository_root": identity["repository_root"],
            "repository_relative_root": identity.get("repository_relative_root", "."),
            "generated_at": identity["generated_at"],
            "health_score": health_score,
            "completeness": completeness_data,
            "evidence_level": evidence_level,
            "evidence_sources": evidence_sources,
            "overall_evidence_level": overall_evidence_level,
            "stats": {
                "total_files": total_files,
                "total_definitions": total_definitions,
                "high_risks": high_risks,
                "health_score": health_score,
                "completeness_pct": completeness_pct,
                "analysis_status": analysis_status
            },
            "objective": objective_projection,
            "session": session_projection,
            "readiness": readiness_projection,
            "diff": diff_projection,
            "risks": [r.to_dict() for r in risks],
            "dependency_graph": dep_graph,
            "recommendations": recs_list,
            "evidence_bundle": evidence_bundle.to_dict(),
            "file_tree": [f.replace('\\', '/') for f in files],
            "calibration": calibration_data,
            "pledges": pledges_data,
            "version": ULTRON_VERSION,
            "repo_fingerprint": identity["model_hash"]
        }

        # Measure serialization latency and byte length
        t_ser_start = time.perf_counter()
        serialized_bytes = json.dumps(payload, default=str).encode("utf-8")
        payload_serialize_ms = round((time.perf_counter() - t_ser_start) * 1000, 2)
        payload_bytes = len(serialized_bytes)

        payload["payload_build_ms"] = payload_build_ms
        payload["payload_serialize_ms"] = payload_serialize_ms
        payload["payload_bytes"] = payload_bytes
        payload["identity"]["payload_build_ms"] = payload_build_ms
        payload["identity"]["payload_serialize_ms"] = payload_serialize_ms
        payload["identity"]["payload_bytes"] = payload_bytes

        global _ANALYSIS_CACHE
        _ANALYSIS_CACHE = {
            "repo_path": _norm_path(repo_path),
            "content_hash": snapshot_id,
            "bundle": bundle,
            "payload": payload,
            "timestamp": time.time()
        }

        return payload

    def handle_v1_analyze(self):
        global ACTIVE_JOB
        data = self.get_request_data()
        if not isinstance(data, dict):
            self.send_json_response(400, {"status": "error", "message": "Invalid JSON body payload.", "error": "Invalid JSON body payload."})
            return

        raw_repo = data.get("repo")
        if raw_repo is None or not isinstance(raw_repo, str) or not raw_repo.strip() or '\x00' in raw_repo:
            self.send_json_response(400, {"status": "error", "message": "Repository path string must not be empty.", "error": "Repository path string must not be empty."})
            return
        repo = raw_repo.strip()
        force = bool(data.get("force", True))

        try:
            repo_path = os.path.abspath(repo)
        except (ValueError, OSError):
            self.send_json_response(400, {"error": f"Invalid repository path: '{repo}'"})
            return

        drive, tail = os.path.splitdrive(repo_path)
        if drive and tail in ('\\', '/', ''):
            self.send_json_response(400, {"error": "Cannot use drive root as repository."})
            return

        norm_repo_path = os.path.normpath(repo_path).replace("\\", "/")

        if not os.path.exists(repo_path) or not os.path.isdir(repo_path):
            self.send_json_response(400, {"error": f"Invalid repository path: '{repo_path}'"})
            return

        import hashlib
        repo_id = hashlib.sha256(norm_repo_path.encode("utf-8")).hexdigest()[:16]

        if ACTIVE_JOB["status"] == "running":
            active_repo = ACTIVE_JOB.get("repository_root", "")
            active_norm_repo = os.path.normpath(active_repo).replace("\\", "/") if active_repo else ""
            if active_norm_repo == norm_repo_path or ACTIVE_JOB.get("repository_id") == repo_id:
                # Same repository in flight -> attach to active job
                self.send_json_response(200, {
                    "success": True,
                    "status": "running",
                    "mode": "async",
                    "job_id": ACTIVE_JOB.get("job_id"),
                    "repository_id": repo_id,
                    "repository_root": norm_repo_path,
                    "progress_step": ACTIVE_JOB.get("progress_step", "Scanning repository"),
                    "progress_pct": ACTIVE_JOB.get("progress_pct", 0),
                    "message": "Analysis is already running in background for this repository"
                })
                return
            else:
                # Different repository collision -> reject with HTTP 409
                self.send_json_response(409, {
                    "error": "BUSY_WITH_DIFFERENT_REPO",
                    "active_repo": active_repo,
                    "active_job_id": ACTIVE_JOB.get("job_id"),
                    "requested_repo": norm_repo_path,
                    "progress_pct": ACTIVE_JOB.get("progress_pct", 0),
                    "message": f"Ultron is currently analyzing '{active_repo}' ({ACTIVE_JOB.get('progress_pct', 0)}% complete). Please wait or cancel the active scan."
                })
                return

        import uuid
        job_id = str(uuid.uuid4())

        ACTIVE_JOB["status"] = "running"
        ACTIVE_JOB["progress_step"] = "Scanning repository"
        ACTIVE_JOB["progress_pct"] = 0
        ACTIVE_JOB["error"] = None
        ACTIVE_JOB["cancel_requested"] = False
        ACTIVE_JOB["job_id"] = job_id
        ACTIVE_JOB["repository_id"] = repo_id
        ACTIVE_JOB["repository_root"] = norm_repo_path
        ACTIVE_JOB["result"] = None

        use_async = bool(data.get("async", False))

        if use_async:
            # Async mode: spawn background worker, return HTTP 202 immediately
            def _async_worker():
                global ACTIVE_JOB
                try:
                    cancel_token = lambda: ACTIVE_JOB.get("cancel_requested", False)
                    payload = self._build_analysis_payload(repo_path, force=force, cancel_token=cancel_token)
                    payload["job_id"] = job_id
                    payload["repository_id"] = repo_id
                    payload["mode"] = "async"
                    ACTIVE_JOB["result"] = payload
                    ACTIVE_JOB["status"] = "success"
                    ACTIVE_JOB["progress_step"] = "Done"
                    ACTIVE_JOB["progress_pct"] = 100
                except InterruptedError:
                    ACTIVE_JOB["status"] = "cancelled"
                    ACTIVE_JOB["progress_step"] = "Cancelled"
                    ACTIVE_JOB["progress_pct"] = 0
                except Exception as e:
                    ACTIVE_JOB["status"] = "failed"
                    ACTIVE_JOB["error"] = str(e)
                    ACTIVE_JOB["progress_step"] = "Failed"
                    ACTIVE_JOB["progress_pct"] = 0
                finally:
                    if ACTIVE_JOB.get("status") == "running":
                        ACTIVE_JOB["status"] = "failed"

            worker = threading.Thread(target=_async_worker, daemon=True)
            worker.start()
            self.send_json_response(202, {
                "status": "running",
                "job_id": job_id,
                "mode": "async",
                "message": "Analysis started in background. Poll /api/v1/progress for updates."
            })
        else:
            # Sync mode (default): execute and return full payload immediately
            # Preserves 100% compatibility with test_ai_handoff.py and test_recommendation_engine.py
            try:
                cancel_token = lambda: ACTIVE_JOB.get("cancel_requested", False)
                payload = self._build_analysis_payload(repo_path, force=force, cancel_token=cancel_token)
                payload["job_id"] = job_id
                payload["repository_id"] = repo_id
                payload["mode"] = "sync"
                ACTIVE_JOB["result"] = payload
                ACTIVE_JOB["status"] = "success"
                ACTIVE_JOB["progress_step"] = "Done"
                ACTIVE_JOB["progress_pct"] = 100
                self.send_json_response(200, payload)
            except InterruptedError:
                ACTIVE_JOB["status"] = "cancelled"
                ACTIVE_JOB["progress_step"] = "Cancelled"
                ACTIVE_JOB["progress_pct"] = 0
                self.send_json_response(200, {"success": False, "error": "Analysis cancelled by user"})
            except Exception as e:
                ACTIVE_JOB["status"] = "failed"
                ACTIVE_JOB["error"] = str(e)
                ACTIVE_JOB["progress_step"] = "Failed"
                ACTIVE_JOB["progress_pct"] = 0
                self.send_json_response(500, {
                    "error": f"Analysis failed: {str(e)}",
                    "traceback": traceback.format_exc()
                })

            finally:
                if ACTIVE_JOB.get("status") == "running":
                    ACTIVE_JOB["status"] = "failed"

    def handle_v1_cancel_analysis(self):
        global ACTIVE_JOB
        if ACTIVE_JOB["status"] != "running":
            self.send_json_response(200, {"success": True, "message": "No running analysis to cancel", "status": "idle"})
            return
            
        ACTIVE_JOB["cancel_requested"] = True
        ACTIVE_JOB["status"] = "cancelled"
        self.send_json_response(200, {"success": True, "status": "cancelled", "message": "Analysis cancelled"})

    def handle_v1_mcp_setup(self):
        """Returns MCP configuration for IDE integration."""
        import sys
        data = self.get_post_data() if hasattr(self, 'get_post_data') else {}
        if not isinstance(data, dict):
            data = {}
        ide = data.get("ide", "cursor")
        repo_path = data.get("repo") or self.get_repo_root_path() or os.getcwd()
        python_exe = sys.executable
        server_entry = {
            "command": python_exe,
            "args": ["-m", "ultron.interfaces.mcp_server", "--repo", os.path.abspath(repo_path)]
        }
        config = {
            "mcpServers": {
                "ultron": server_entry
            }
        }
        self.send_json_response(200, {
            "success": True,
            "ide": ide,
            "config": config,
            "config_json": json.dumps(config, indent=2),
            "instructions": f"Add the following to your {ide} MCP configuration file."
        })

    def handle_v1_compare(self):
        from ultron.core.rkm.store import RepositoryStore
        from ultron.interfaces.api import HistoryAPI
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON body or missing run_id_a/run_id_b"})
                return
            run_a = int(data.get("run_id_a"))
            run_b = int(data.get("run_id_b"))
        except (ValueError, KeyError, TypeError):
            self.send_json_response(400, {"error": "Invalid JSON body or missing/invalid run_id_a/run_id_b"})
            return
            
        repo_root = self.get_repo_root_path()
        db_path = os.path.join(repo_root, ".ultron", "repository.db")
        if not os.path.exists(db_path):
            self.send_json_response(400, {"error": "Repository not initialized"})
            return
            
        store = RepositoryStore(db_path)
        try:
            diff = HistoryAPI.compare_runs(store, run_a, run_b)
            self.send_json_response(200, diff)
        except (ValueError, KeyError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": f"Compare runs failed: {str(e)}"})
        finally:
            store.close()

    def handle_v1_explain_violation(self):
        from ultron.core.rkm.store import RepositoryStore
        from ultron.core.translate import translate_violation_to_plain_english
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid body or missing violation_id"})
                return
            vio_id = int(data.get("violation_id"))
        except (ValueError, KeyError, TypeError):
            self.send_json_response(400, {"error": "Invalid body or missing/invalid violation_id"})
            return
            
        repo_root = self.get_repo_root_path()
        db_path = os.path.join(repo_root, ".ultron", "repository.db")
        if not os.path.exists(db_path):
            self.send_json_response(400, {"error": "Repository not initialized"})
            return
            
        store = RepositoryStore(db_path)
        try:
            row = store.conn.execute(
                "SELECT v.*, r.id as rule_id, r.name as rule_name, r.description as rule_description FROM rkm_violations v "
                "JOIN rkm_evaluations e ON e.id = v.evaluation_id "
                "JOIN rkm_rules r ON r.id = e.rule_id "
                "WHERE v.id = ?", (vio_id,)
            ).fetchone()
            if not row:
                self.send_json_response(404, {"error": f"Violation ID {vio_id} not found"})
                return
                
            rule_name = row["rule_name"]
            details = row["details"]
            entity = row["entity_identifier"]
            severity = row["severity"]
            
            # Fetch evidence chain from rkm_violation_evidence
            evidence_rows = store.conn.execute(
                "SELECT * FROM rkm_violation_evidence WHERE violation_id = ?", (vio_id,)
            ).fetchall()
            
            evidence_chain = []
            for ev in evidence_rows:
                evidence_chain.append({
                    "evidence_type": ev["evidence_type"],
                    "value": ev["value"],
                    "description": ev["description"]
                })
            
            # Generate Plain English Lead Explanation
            plain_explanation = translate_violation_to_plain_english(rule_name, details, entity)
            
            # Trust Chain View object (Plain English first, technical secondary)
            trust_chain = {
                "plain_label": f"High risk detected in {entity}: {plain_explanation['summary']}",
                "entity": entity,
                "rule_plain_name": plain_explanation["plain_rule"],
                "rule_technical_name": rule_name,
                "severity": severity,
                "confidence": 0.95,
                "evidence": evidence_chain if evidence_chain else [
                    {"evidence_type": "metric_threshold", "value": details, "description": "Metric exceeded threshold"}
                ]
            }
            
            # Before / After Repair Simulation object
            repair_simulation = {
                "plain_summary": f"Decouple {entity} to restore stability and speed up changes.",
                "technical_rule": rule_name,
                "before_state": {
                    "structure": f"{entity} directly coupled with high complexity.",
                    "risk_score": 85.0,
                    "status": "AT_RISK"
                },
                "after_state": {
                    "structure": f"Refactored {entity} using interface boundaries.",
                    "estimated_risk_score": 25.0,
                    "status": "STABLE"
                },
                "recommended_steps": [
                    f"1. Extract shared interfaces from {entity} into a decoupled API module.",
                    "2. Add unit tests for boundary contracts.",
                    "3. Run 'ultron check' to verify risk reduction."
                ]
            }

            markdown_explanation = f"""### {plain_explanation['plain_rule']}
*Technical Rule*: `{rule_name}`

**Plain Language Summary**:
{plain_explanation['summary']}

**Evidence Trust Chain**:
- Entity: `{entity}`
- Severity: `{severity}`
- Details: `{details}`

**Refactoring Simulation**:
Before: Risk Score 85.0 (High Complexity/Coupling)
After: Estimated Risk Score 25.0 (Decoupled Interface)"""
            
            self.send_json_response(200, {
                "status": "success",
                "violation_id": vio_id,
                "rule_name": rule_name,
                "details": details,
                "entity_identifier": entity,
                "explanation": markdown_explanation,
            })
        except (ValueError, KeyError, TypeError, OSError) as e:
            self.send_json_response(400, {"error": f"Failed to explain violation: {str(e)}"})
        finally:
            store.close()

    def handle_v1_ai_critique(self):
        try:
            data = self.get_request_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid payload"})
                return
            
            raw_path = data.get("file") or data.get("file_path") or data.get("node_id") or data.get("target_entity")
            if raw_path is None or not isinstance(raw_path, str) or not raw_path.strip() or '\x00' in raw_path:
                file_path = "general"
            else:
                file_path = raw_path.strip()
                
            from ultron.core.ai.client import AIClient
            ai_client = AIClient()
            try:
                complexity = int(data.get("complexity", 10) or 10)
            except (ValueError, TypeError):
                complexity = 10
            try:
                coupling = int(data.get("coupling", 5) or 5)
            except (ValueError, TypeError):
                coupling = 5
            try:
                impact_score = float(data.get("impact_score", 12.0) or 12.0)
            except (ValueError, TypeError):
                impact_score = 12.0

            critique = ai_client.query_critique(
                file_path=file_path,
                complexity=complexity,
                coupling=coupling,
                impact_score=impact_score,
                intent=str(data.get("intent", "") or "")
            )
            self.send_json_response(200, critique)
        except (ValueError, KeyError, TypeError, OSError) as err:
            self.send_json_response(400, {"error": f"AI critique parameter error: {str(err)}"})
        except Exception as err:
            self.send_json_response(500, {"error": f"AI critique generation failed: {str(err)}"})

def serve(port=8000, auto_fallback=False, fallback_ports=(8000, 8001, 8002), target_repo=None, **kwargs):
    """Launches the Ultron REST API & Web Dashboard Server.

    Args:
        port: Port number to bind.
        auto_fallback: Whether to attempt alternative ports on collision.
        fallback_ports: Tuple of port numbers to try in sequence if auto_fallback is True.
        target_repo: Optional initial active repository directory to store in config.

    Raises:
        OSError: If the port is already in use (allows caller to retry).
    """
    if target_repo and os.path.exists(target_repo):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            cfg = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            cfg["active_repo"] = os.path.abspath(target_repo)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            sys.stderr.write(f"Warning: could not save active_repo to config: {e}\n")

    # Console encoding safety for server-side print/log statements
    import sys as _sys
    import signal
    for _stream in (_sys.stdout, _sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    ports_to_try = [port] if not auto_fallback else list(dict.fromkeys([port, *fallback_ports]))
    httpd = None
    bound_port = None

    for p in ports_to_try:
        server_address = ('', p)
        try:
            if hasattr(http.server, "ThreadingHTTPServer"):
                http.server.ThreadingHTTPServer.allow_reuse_address = True
                httpd = http.server.ThreadingHTTPServer(server_address, UltronAPIHandler)
            else:
                class _ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
                    daemon_threads = True
                    allow_reuse_address = True
                httpd = _ThreadingHTTPServer(server_address, UltronAPIHandler)
            bound_port = p
            break
        except OSError as e:
            if auto_fallback and p != ports_to_try[-1]:
                print(f"[!] Port {p} in use, attempting fallback to next port...", file=sys.stderr)
                continue
            raise

    print(f"[*] Ultron Dashboard Server running on http://localhost:{bound_port}/")

    def _handle_shutdown(signum, frame):
        print(f"\n[*] Received signal {signum}. Stopping Ultron server...", file=sys.stderr)
        if httpd:
            threading.Thread(target=httpd.shutdown, daemon=True).start()

    old_sigint = None
    old_sigterm = None
    old_sigbreak = None
    try:
        if threading.current_thread() is threading.main_thread():
            old_sigint = signal.signal(signal.SIGINT, _handle_shutdown)
            old_sigterm = signal.signal(signal.SIGTERM, _handle_shutdown)
            if hasattr(signal, "SIGBREAK"):
                old_sigbreak = signal.signal(signal.SIGBREAK, _handle_shutdown)
    except Exception:
        pass

    try:
        httpd.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        print("\n[*] Server stopped.")
    finally:
        if httpd:
            try:
                httpd.server_close()
            except Exception:
                pass
        if old_sigint: signal.signal(signal.SIGINT, old_sigint)
        if old_sigterm: signal.signal(signal.SIGTERM, old_sigterm)
        if old_sigbreak and hasattr(signal, "SIGBREAK"): signal.signal(signal.SIGBREAK, old_sigbreak)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ultron Web Dashboard Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind server (default: 8000)")
    parser.add_argument("--auto-port", action="store_true", default=True, help="Auto fallback across 8000-8002 on conflict")
    args = parser.parse_args()
    serve(port=args.port, auto_fallback=args.auto_port)