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

from ultron.core import analyzer
from ultron.core import risk
from ultron.core import prompt
from ultron.core import classifier
from ultron.core import predict
from ultron.core import pledge
from ultron.core import fuzz
from ultron.core import logistic
from ultron.core import translate
from ultron.interfaces.api.router import APIRouter
import ultron.interfaces.api.routes

try:
    from ultron.experimental import delta
except ImportError:
    delta = None
try:
    from ultron.experimental import design_oracle
except ImportError:
    design_oracle = None


LAST_ANALYSIS = {
    "file_path": None,
    "delta_i": 0.0,
    "mkr": 1.0,
    "delta_cest": 0.0
}

ACTIVE_JOB = {
    "status": "idle",
    "progress_step": "Done",
    "error": None,
    "cancel_requested": False,
    "job_id": None
}

PORT = 8000
LOOPBACK_HOST = "127.0.0.1"
# A modal folder dialog blocks this single-threaded server, so give up on it
# rather than letting one unanswered window take the whole API down.
BROWSE_DIALOG_TIMEOUT = 20

# Only same-machine origins may call the API. The server exposes unauthenticated
# file read/write endpoints, so a wildcard ACAO would let any website a user visits
# drive their local filesystem.
def _is_local_origin(origin: str) -> bool:
    if not origin:
        return False
    try:
        from urllib.parse import urlparse
        host = urlparse(origin).hostname
    except Exception:
        return False
    return host in ("127.0.0.1", "localhost", "::1")


def coerce_file_list(value) -> list:
    """Accept a JSON array, a comma-separated string, or nothing.

    The dashboard sends an array while the CLI and older clients send CSV;
    silently ignoring one of those made requests look like whole-repo scans.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(part).strip() for part in value if str(part).strip()]
    return []


WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".ultron")
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
        # Echo the origin only when it is same-machine; never send a wildcard.
        origin = self.headers.get('Origin')
        if _is_local_origin(origin):
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        origin = self.headers.get('Origin')
        self.send_response(200 if _is_local_origin(origin) or not origin else 403)
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
        if parsed_path == "/api/dependency-graph":
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
        if parsed_path == "/api/list-dirs":
            self.handle_list_dirs()
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
        if parsed_path == "/api/v1/history":
            self.handle_v1_history()
            return
        if parsed_path == "/" or parsed_path == "":
            file_path = os.path.join(WEB_DIR, "index.html")
        else:
            # Prevent directory traversal attacks
            rel_path = parsed_path.lstrip('/')
            file_path = os.path.join(WEB_DIR, rel_path)
            
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
        elif req_path == "/api/v1/overview":
            self.handle_v1_overview()
            return
        elif req_path == "/api/v1/cancel-analysis":
            self.handle_v1_cancel_analysis()
            return
        elif req_path == "/api/v1/compare":
            self.handle_v1_compare()
            return
        elif req_path == "/api/v1/explain-violation":
            self.handle_v1_explain_violation()
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
        elif req_path == "/api/run-tests":
            self.handle_run_tests()
        elif req_path == "/api/diff-risk":
            self.handle_diff_risk()
        elif req_path == "/api/dependency-graph":
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
            self._cached_post_data = json.loads(post_data)
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
            if isinstance(q_data, dict) and q_data.get("repo"):
                return q_data

        # For POST requests or post_data payloads:
        post_data = self.get_post_data()
        if post_data is None:
            return None  # Preserves None on corrupted JSON so handlers return 400 Bad Request
        if isinstance(post_data, dict):
            if "repo" not in post_data or not post_data["repo"]:
                post_data["repo"] = "."
            return post_data
        return post_data

    def send_json_response(self, status_code, data):
        import uuid
        req_id = f"req-{uuid.uuid4().hex[:8]}"
        iso_time = datetime.now(timezone.utc).isoformat()
        
        envelope = {
            "success": status_code < 400,
            "data": data if status_code < 400 else None,
            "error": data.get("error") if (isinstance(data, dict) and status_code >= 400) else None,
            "timestamp": iso_time,
            "request_id": req_id
        }
        
        # Merge top-level keys for 100% backward compatibility
        if isinstance(data, dict):
            for k, v in data.items():
                if k not in envelope:
                    envelope[k] = v

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(envelope).encode('utf-8'))

    
    def measure_entity(self, entity):
        """
        Resolve `entity` to a real file inside the repository and measure it.

        Returns (complexity, coupling_fanout, error_response) where error_response is
        None on success. Previously these endpoints ignored `entity` entirely and passed
        fixed literals, so every input - including files that did not exist - produced an
        identical HIGH-risk verdict at confidence 1.0.
        """
        if not entity or not entity.strip():
            return None, None, (400, {"error": "Missing required 'entity' parameter."})

        repo_root = os.path.realpath(self.get_repo_root_path())
        candidate = entity if os.path.isabs(entity) else os.path.join(repo_root, entity)
        abs_entity = os.path.realpath(candidate)

        if not os.path.normcase(abs_entity).startswith(os.path.normcase(os.path.join(repo_root, ""))):
            return None, None, (400, {"error": "Access denied: entity must be inside the repository."})
        if not os.path.isfile(abs_entity):
            return None, None, (404, {"error": f"Entity not found in repository: {entity}"})

        from ultron.core.risk.metrics import get_file_complexity
        complexity = float(get_file_complexity(abs_entity))

        rel_entity = os.path.relpath(abs_entity, repo_root).replace("\\", "/")
        coupling = 0
        try:
            codebase = analyzer.analyze_directory(repo_root)
            packets = risk.evaluate_risks(codebase, [rel_entity], repo_path=repo_root)
            for packet in packets:
                packet_path = (getattr(packet, "file_path", "") or "").replace("\\", "/")
                if packet_path.endswith(rel_entity) or rel_entity.endswith(packet_path):
                    complexity = float(packet.complexity)
                    coupling = int(getattr(packet, "coupling_score", 0))
                    break
        except Exception as e:
            sys.stderr.write(f"[Ultron] Coupling measurement failed for {rel_entity}: {e}\n")

        return complexity, coupling, None

    def handle_v1_risk_profile(self):
        try:
            from urllib.parse import parse_qs, urlparse
            from dataclasses import asdict
            query = parse_qs(urlparse(self.path).query)
            entity = query.get("entity", [""])[0]

            complexity, coupling, err = self.measure_entity(entity)
            if err:
                self.send_json_response(*err)
                return

            from ultron.core.rkm.risk_intelligence import compute_risk_profile
            # coverage_percent is left None on purpose: Ultron has no coverage source, and
            # compute_risk_profile reports confidence 0.0 for the missing signal rather
            # than inventing a plausible-looking number.
            prof = compute_risk_profile(entity, complexity=complexity, coupling_fanout=coupling)
            self.send_json_response(200, asdict(prof))
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_v1_decision(self):
        try:
            from urllib.parse import parse_qs, urlparse
            from dataclasses import asdict
            query = parse_qs(urlparse(self.path).query)
            entity = query.get("entity", [""])[0]
            crit = query.get("criticality", ["DEFAULT"])[0]

            complexity, coupling, err = self.measure_entity(entity)
            if err:
                self.send_json_response(*err)
                return

            from ultron.core.rkm.risk_intelligence import compute_risk_profile
            from ultron.core.rkm.policy_engine import evaluate_policy
            prof = compute_risk_profile(entity, complexity=complexity, coupling_fanout=coupling)
            dec = evaluate_policy(prof, business_criticality=crit)
            self.send_json_response(200, asdict(dec))
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_browse_folder(self):
        try:
            from ultron.interfaces.api.browse_folder import select_folder_dialog
            data = self.get_post_data()
            initial_dir = data.get("initial_dir") or self.get_repo_root_path()

            # The dialog is modal and this server handles one request at a time,
            # so an unanswered dialog would freeze every other endpoint. Wait a
            # bounded time, then hand back to the caller's own folder browser.
            import threading
            result = {}

            def run_dialog():
                try:
                    result["value"] = select_folder_dialog(initial_dir)
                except Exception as exc:
                    result["value"] = {"path": "", "cancelled": True, "fallback": True, "error": str(exc)}

            worker = threading.Thread(target=run_dialog, daemon=True)
            worker.start()
            worker.join(timeout=BROWSE_DIALOG_TIMEOUT)

            if worker.is_alive():
                self.send_json_response(200, {
                    "path": "",
                    "cancelled": True,
                    "fallback": True,
                    "error": "The folder dialog did not return in time. Use the built-in folder browser."
                })
                return

            self.send_json_response(200, result.get("value", {"path": "", "cancelled": True, "fallback": True}))
        except Exception as e:
            self.send_json_response(500, {"error": f"Failed to browse folder: {str(e)}"})

    def handle_list_dirs(self):
        """List subdirectories of a path so the UI can browse folders in-page.

        Replaces the native modal dialog, which blocked the whole server while open.
        """
        try:
            query = self.get_query_data() if hasattr(self, "get_query_data") else {}
            raw = (query or {}).get("path", "")
            if isinstance(raw, list):
                raw = raw[0] if raw else ""
            raw = str(raw or "").strip()

            drives = []
            if os.name == "nt":
                import string
                drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.isdir(f"{d}:\\")]

            target = os.path.abspath(raw) if raw else self.get_repo_root_path()
            if not os.path.isdir(target):
                self.send_json_response(400, {"error": f"'{target}' is not a directory.", "drives": drives})
                return

            entries = []
            try:
                for name in sorted(os.listdir(target), key=str.lower):
                    if name.startswith("."):
                        continue
                    full = os.path.join(target, name)
                    if os.path.isdir(full):
                        entries.append({"name": name, "path": full})
            except PermissionError:
                self.send_json_response(403, {"error": f"Permission denied reading '{target}'.", "drives": drives})
                return

            parent = os.path.dirname(target.rstrip(os.sep))
            self.send_json_response(200, {
                "path": target,
                "parent": parent if parent and parent != target and os.path.isdir(parent) else None,
                "entries": entries,
                "drives": drives
            })
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_v1_context_brief(self):
        try:
            data = self.get_post_data()
            repo = data.get("repo", "") or self.get_repo_root_path()
            repo_path = os.path.abspath(repo)
            target_file = data.get("target_file", "").strip()

            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return

            db_path = os.path.join(repo_path, ".ultron", "repository.db")
            repo_name = os.path.basename(repo_path)
            
            # Always build the canonical brief from live analysis: it carries the
            # real per-file reasons ("McCabe Complexity: 114.0") that an agent can
            # act on. The knowledge base then refines the score and identity.
            from ultron.core.context_brief import compile_brief_data
            canonical_brief = compile_brief_data(repo_path)
            canonical_brief["target_file"] = target_file
            canonical_brief["memory_backed"] = False

            if os.path.exists(db_path):
                try:
                    from ultron.core.rkm.store import RepositoryStore
                    from ultron.core.rkm.evolution.engine import EvolutionEngine

                    store = RepositoryStore(db_path)
                    try:
                        meta = store.get_metadata()
                        if meta and meta.latest_analysis_run_id:
                            run_id = meta.latest_analysis_run_id
                            health_run = EvolutionEngine.evaluate_health_score(store, run_id)
                            canonical_brief["health_score"] = round(
                                (health_run.architecture_stability * 0.4 +
                                 health_run.rule_compliance * 0.4 +
                                 health_run.complexity_trend * 0.2) * 100, 1
                            )
                            canonical_brief["repository_uuid"] = meta.repository_uuid
                            canonical_brief["memory_backed"] = True
                            canonical_brief["violation_count"] = len(store.get_violations(run_id))
                    finally:
                        store.close()
                except Exception as e:
                    print(f"[Warning] RKM Store lookup failed for context brief: {e}")

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
        except Exception as e:
            self.send_json_response(500, {"error": f"Failed to generate context brief: {str(e)}", "traceback": traceback.format_exc()})

    def handle_v1_recommendations(self):
        try:
            from urllib.parse import parse_qs, urlparse
            query = parse_qs(urlparse(self.path).query)
            limit_raw = query.get("limit", ["20"])[0]
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

    def handle_v1_export_brief(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"status": "error", "message": "Invalid JSON body payload."})
                return
            fmt = str(data.get("format", "")).strip().lower()
            if fmt not in ["claude", "codex", "antigravity", "json"]:
                self.send_json_response(400, {
                    "status": "error",
                    "message": f"Unsupported format '{fmt}'. Supported formats: 'claude', 'codex', 'antigravity', 'json'."
                })
                return

            repo_path = self.get_repo_root_path()
            target_file = str(data.get("target_file", "")).strip()

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

            repo = data.get("repo", "")
            target_file = str(data.get("target_file", "")).strip()
            persona = str(data.get("persona", "developer")).strip().lower()

            repo_path = os.path.abspath(repo) if repo and repo.strip() else self.get_repo_root_path()
            
            # 1. Compile canonical brief context
            codebase = analyzer.analyze_directory(repo_path) if os.path.isdir(repo_path) else {}
            risks = risk.evaluate_risks(codebase, [target_file] if target_file else [], repo_path=repo_path)
            
            target_risk = None
            if risks:
                target_risk = risks[0]
                
            file_name = target_file or (getattr(target_risk, "file", "") if target_risk else "repository")
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
                "ai_response": ai_response_text,
                "source": source_used
            })

        except Exception as e:
            self.send_json_response(500, {"status": "error", "message": str(e)})

    def handle_analyze(self):
        try:
            data = self.get_request_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"status": "error", "message": "Invalid JSON body payload.", "error": "Invalid JSON body payload."})
                return
            repo = str(data.get("repo", "")).strip()
            if not repo:
                repo_path = self.get_repo_root_path()
            else:
                repo_path = os.path.abspath(repo)

            if not os.path.exists(repo_path):
                msg = f"Directory '{repo_path}' does not exist."
                self.send_json_response(400, {"status": "error", "message": msg, "error": msg})
                return
            if not os.path.isdir(repo_path):
                msg = f"Repository path '{repo_path}' is a file, not a directory."
                self.send_json_response(400, {"status": "error", "message": msg, "error": msg})
                return
                
            intent = str(data.get("intent", "")).strip()
            target_files = coerce_file_list(data.get("files"))
            
            codebase = analyzer.analyze_directory(repo_path)
            if not codebase:
                msg = f"No code files found in '{repo_path}'. Ensure directory contains Python files."
                self.send_json_response(400, {"status": "error", "message": msg, "error": msg})
                return

            risks = risk.evaluate_risks(codebase, target_files, intent, repo_path=repo_path)

            # Intent matching is keyword-based, so a perfectly reasonable phrase
            # ("improve performance") can match nothing. Returning an empty list
            # made the dashboard look like a clean repo. Fall back to the whole
            # repository instead and tell the caller the intent was ignored.
            intent_matched = True
            if intent and not target_files and not risks:
                intent_matched = False
                risks = risk.evaluate_risks(codebase, [], "", repo_path=repo_path)
            
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
                "intent": {
                    "text": intent,
                    "matched": intent_matched,
                    "message": "" if intent_matched else (
                        f"No files matched \"{intent}\". Showing the whole repository instead."
                    )
                },
                "risks": [r.to_dict() for r in risks]
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
            repo = data.get("repo", "") or os.getcwd()
            repo_path = os.path.abspath(repo)
            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return
                
            code_content = data.get("code", "")
            if code_content:
                # Sandbox mode: write a temporary file inside the repo
                target_file = os.path.join(repo_path, "sandbox_temp.py")
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(code_content)
            else:
                target_file = os.path.abspath(data.get("target_file", ""))
                
            if not os.path.exists(target_file):
                self.send_json_response(400, {"error": f"Target file '{target_file}' does not exist."})
                return
                
            typo_threshold = float(data.get("typo_threshold", 0.75))
            prob_threshold = float(data.get("prob_threshold", 0.0))
            
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
        except Exception as e:
            self.send_json_response(500, {
                "error": str(e),
                "traceback": traceback.format_exc()
            })

    def handle_generate(self):
        try:
            data = self.get_post_data()
            repo = data.get("repo", "") or os.getcwd()
            repo_path = os.path.abspath(repo)
            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return
                
            intent = data.get("intent", "")
            if not intent:
                self.send_json_response(400, {"error": "Intent parameter is required."})
                return
                
            files_str = data.get("files", "")
            target_files = [f.strip() for f in files_str.split(",") if f.strip()] if files_str else []
            
            codebase = analyzer.analyze_directory(repo_path)
            risks = risk.evaluate_risks(codebase, target_files, intent, repo_path=repo_path)
            opt_prompt = prompt.generate_optimized_prompt(intent, codebase, risks)
            
            self.send_json_response(200, {
                "success": True,
                "prompt": opt_prompt
            })
        except Exception as e:
            self.send_json_response(500, {
                "error": str(e),
                "traceback": traceback.format_exc()
            })

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
            configured = None
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    configured = json.load(f).get("repo_root")
            # Fall back to the effective root so a first-run UI has something to
            # show instead of an empty box the user has to guess at.
            self.send_json_response(200, {
                "repo_root": configured or self.get_repo_root_path(),
                "configured": bool(configured)
            })
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_set_repo_root(self):
        try:
            data = self.get_post_data()
            path = data.get("path", "")
            if not isinstance(path, str) or not path.strip():
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
            if not isinstance(repo, str) or not repo.strip():
                self.send_json_response(400, {"error": "Missing or invalid 'repo' parameter."})
                return
                
            repo_path = os.path.realpath(repo)
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
                    if item.startswith('.') or item in ('venv', 'env', 'test_env', '__pycache__', 'tests', 'node_modules', 'scratch', 'dist', 'synapse_project', 'docs', 'ultron_risk_scorer.egg-info'):
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
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_architecture_health(self):
        try:
            data = self.get_request_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid request payload. Expected JSON object."})
                return
            repo = data.get("repo")
            if not isinstance(repo, str) or not repo.strip():
                self.send_json_response(400, {"error": "Missing or invalid 'repo' parameter."})
                return
                
            import tempfile
            base_dir = os.path.join(os.path.realpath(os.getcwd()), "")
            repo_path = os.path.join(os.path.realpath(repo), "")
            temp_base = os.path.join(os.path.realpath(tempfile.gettempdir()), "")
            
            is_under_cwd = os.path.normcase(repo_path).startswith(os.path.normcase(base_dir))
            is_under_temp = os.path.normcase(repo_path).startswith(os.path.normcase(temp_base))
            
            if not is_under_cwd and not is_under_temp:
                self.send_json_response(400, {"error": "Access denied: Repository path must be inside the server directory."})
                return
            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return

            codebase = analyzer.analyze_directory(repo_path)
            target_files = [k for k in codebase.keys() if k.endswith(".py")] if isinstance(codebase, dict) else []

            if not codebase or not target_files:
                # A repository we could not analyze is NOT a healthy repository. Returning
                # health_score=100 here made "analysis produced nothing" visually identical
                # to "your code is flawless", which is the most dangerous possible default
                # for a risk tool. Report an explicit state and no score instead.
                discovered_py = []
                try:
                    for _root, _dirs, _files in os.walk(repo_path):
                        _dirs[:] = [d for d in _dirs if d not in (".git", "__pycache__", ".venv", "node_modules")]
                        if any(f.endswith(".py") for f in _files):
                            discovered_py.append(_root)
                            break
                except OSError:
                    pass

                state = "analysis_empty" if not discovered_py else "analysis_failed"
                self.send_json_response(200, {
                    "success": False,
                    "state": state,
                    "health_score": None,
                    "message": (
                        "No Python files found in this repository."
                        if state == "analysis_empty"
                        else "Python files were found but none could be analyzed. Check the server console for parse errors."
                    ),
                    "analyzed_file_count": 0,
                    "hotspots": [],
                    "circular_dependencies": [],
                    "violations": [],
                    "contracts": []
                })
                return

            # Helper serialization functions
            def serialize_snapshot(s):
                return {
                    "total_coupling_debt": float(s.total_coupling_debt),
                    "total_cycle_count": int(s.total_cycle_count),
                    "total_violations": int(s.total_violations),
                    "avg_instability": float(s.avg_instability),
                    "avg_hotspot_score": float(s.avg_hotspot_score)
                }
                
            def serialize_recommendation(rec):
                return {
                    "filepath": rec.filepath,
                    "principle": rec.principle,
                    "smell": rec.smell,
                    "refactoring": rec.refactoring,
                    "expected_delta": rec.expected_delta,
                    "severity": int(rec.severity),
                    "priority_rank": int(rec.priority_rank)
                }
                
            def serialize_violation(v):
                return {
                    "filepath": v.filepath,
                    "principle": v.principle,
                    "observation": v.observation,
                    "reason": v.reason,
                    "consequences": v.consequences,
                    "severity": int(v.severity)
                }

            def serialize_contract(c):
                return {
                    "filepath": c.filepath,
                    "recommendations": [serialize_recommendation(rec) for rec in c.recommendations],
                    "before_snapshot": serialize_snapshot(c.before_snapshot),
                    "after_snapshot": serialize_snapshot(c.after_snapshot)
                }

            def detect_import_cycles(cb):
                adj = {}
                for rel_path, analysis in cb.items():
                    r_norm = rel_path.replace("\\", "/")
                    adj[r_norm] = set()
                    for imp in analysis.get('imports', []):
                        for pot in cb:
                            pot_norm = pot.replace("\\", "/")
                            pot_base = pot_norm.replace('.py', '').replace('/', '.')
                            if pot_base == imp or pot_base.endswith('.' + imp) or imp.replace('.', '/') in pot_norm:
                                if pot_norm != r_norm:
                                    adj[r_norm].add(pot_norm)
                                break
                visited = {}
                cycles = []
                path = []
                def dfs(node):
                    visited[node] = 1
                    path.append(node)
                    for nbr in sorted(adj.get(node, [])):
                        if visited.get(nbr) == 1:
                            idx = path.index(nbr)
                            cycle = path[idx:] + [nbr]
                            if not any(set(cycle) == set(c) for c in cycles) and len(cycle) <= 8:
                                cycles.append(cycle)
                        elif nbr not in visited:
                            dfs(nbr)
                    path.pop()
                    visited[node] = 2
                for n in sorted(adj.keys()):
                    if n not in visited:
                        dfs(n)
                return cycles

            cycles = detect_import_cycles(codebase)
            violations = []
            hotspots = []
            
            # Evaluate risks across repository
            risks = risk.evaluate_risks(codebase, target_files, intent="Architecture audit", repo_path=repo_path)

            db_path = os.path.join(repo_path, ".ultron", "repository.db")
            if os.path.exists(db_path):
                try:
                    from ultron.core.rkm.store import RepositoryStore
                    from ultron.interfaces.api import ViolationsAPI
                    from ultron.core.rkm.evolution.engine import EvolutionEngine
                    store = RepositoryStore(db_path)
                    meta = store.get_metadata()
                    if meta and meta.latest_analysis_run_id:
                        run_id = meta.latest_analysis_run_id
                        rkm_vios = ViolationsAPI.get_violations(store, run_id)
                        for rv in rkm_vios:
                            violations.append({
                                "filepath": rv.get("file_path") or "Unknown",
                                "principle": rv.get("rule_name") or "Architectural Constraint",
                                "observation": rv.get("details") or rv.get("description") or "",
                                "reason": rv.get("description") or "Constraint violation recorded in RKM",
                                "consequences": "Increases architectural debt and refactoring risk",
                                "severity": 2
                            })
                        h_objs = EvolutionEngine.detect_hotspots(store, run_id)
                        for h in h_objs:
                            hotspots.append({
                                "file": h.file_path.replace("\\", "/"),
                                "hotspot_score": float(h.hotspot_score),
                                "complexity": int(getattr(h, "complexity", 1)),
                                "coupling_debt": float(getattr(h, "coupling_debt", 0.0)),
                                "bug_fix_count": int(h.change_count)
                            })
                    store.close()
                except Exception as ex:
                    sys.stderr.write(f"[Ultron] RKM audit inspection warning: {ex}\n")

            # Fallback heuristic violations if no RKM DB violations found
            if not violations:
                for r in risks:
                    fpath = getattr(r, "file_path", None) or getattr(r, "file", "")
                    cx = getattr(r, "complexity", 1)
                    cp = getattr(r, "coupling_score", getattr(r, "coupling", 0))
                    if cx > 15:
                        violations.append({
                            "filepath": fpath,
                            "principle": "Complexity Limit (SRP)",
                            "observation": f"Cyclomatic complexity is {cx} (threshold 15)",
                            "reason": "Function/module contains excessive conditional decision paths",
                            "consequences": "High cognitive load and regression risk during modifications",
                            "severity": 3 if cx > 30 else 2
                        })
                    if cp > 10:
                        violations.append({
                            "filepath": fpath,
                            "principle": "Coupling Limit (ADP/SDP)",
                            "observation": f"Coupling fanout is {cp} (threshold 10)",
                            "reason": "Direct reliance on too many distinct subsystem dependencies",
                            "consequences": "Cascading breaks when dependent modules change",
                            "severity": 2
                        })

            if not hotspots:
                for r in risks[:10]:
                    fpath = (getattr(r, "file_path", None) or getattr(r, "file", "")).replace("\\", "/")
                    hotspots.append({
                        "file": fpath,
                        "hotspot_score": round(float(getattr(r, "impact_score", 0.0)), 2),
                        "complexity": int(getattr(r, "complexity", 1)),
                        "coupling_debt": round(float(getattr(r, "coupling_score", 0.0)), 1),
                        "bug_fix_count": 1
                    })

            health_score = max(10, min(100, 100 - (len(cycles) * 12 + len(violations) * 3)))

            self.send_json_response(200, {
                "success": True,
                "state": "ok",
                "health_score": health_score,
                "analyzed_file_count": len(target_files),
                "hotspots": hotspots,
                "circular_dependencies": [list(c) for c in cycles],
                "violations": violations,
                "contracts": []
            })
        except Exception as e:
            self.send_json_response(500, {
                "error": f"Internal Server Error: {e}",
                "traceback": traceback.format_exc()
            })

    def handle_get_file(self):
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid JSON payload format."})
                return
            repo = data.get("repo")
            file_param = data.get("file")
            if not isinstance(repo, str) or not repo.strip() or not isinstance(file_param, str) or not file_param.strip():
                self.send_json_response(400, {"error": "Missing or invalid parameters."})
                return
                
            repo_path = os.path.realpath(repo)
            full_path = os.path.realpath(os.path.join(repo_path, file_param))
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
            if not isinstance(repo, str) or not repo.strip() or not isinstance(file_param, str) or not file_param.strip() or not isinstance(content, str):
                self.send_json_response(400, {"error": "Missing or invalid parameters."})
                return
                
            repo_path = os.path.realpath(repo)
            full_path = os.path.realpath(os.path.join(repo_path, file_param))
            real_repo_dir = os.path.join(repo_path, "")
            
            if not os.path.normcase(full_path).startswith(os.path.normcase(real_repo_dir)):
                self.send_json_response(400, {"error": "Invalid file path."})
                return
                
            if os.path.exists(full_path):
                backup_path = full_path + ".bak"
                try:
                    shutil.copy2(full_path, backup_path)
                except Exception:
                    pass
                    
            with open(full_path, "w", encoding="utf-8-sig") as f:
                f.write(content)
                
            self.send_json_response(200, {
                "success": True,
                "message": "File saved successfully."
            })
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_run_tests(self):
        try:
            data = self.get_post_data()
            repo = data.get("repo", "") or os.getcwd()
            repo_path = os.path.abspath(repo)
            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return
            
            test_cmd = [sys.executable, "-m", "unittest", "discover"]
            if os.path.exists(os.path.join(repo_path, "run_tests.py")):
                test_cmd = [sys.executable, "run_tests.py"]
            elif os.path.exists(os.path.join(repo_path, "ultron", "tests", "run_tests.py")):
                test_cmd = [sys.executable, "ultron/tests/run_tests.py"]
                
            res = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                cwd=repo_path,
                timeout=10.0
            )
            
            output = res.stdout + "\n" + res.stderr
            
            # Calibration feedback hook
            global LAST_ANALYSIS
            file_path = data.get("file_path", LAST_ANALYSIS.get("file_path"))
            if file_path:
                delta_i = float(data.get("delta_i", LAST_ANALYSIS.get("delta_i", 0.0)))
                mkr = float(data.get("mkr", LAST_ANALYSIS.get("mkr", 1.0)))
                delta_cest = float(data.get("delta_cest", LAST_ANALYSIS.get("delta_cest", 0.0)))
                actual_failure = float(data.get("actual_failure", 1.0 if res.returncode != 0 else 0.0))
                
                try:
                    delta.learn_from_feedback(
                        file_path=file_path,
                        delta_i=delta_i,
                        mkr=mkr,
                        delta_cest=delta_cest,
                        actual_failure=actual_failure
                    )
                except Exception as ex:
                    print(f"[-] Delta Engine feedback learning failed: {ex}", file=sys.stderr)
            
            self.send_json_response(200, {
                "success": True,
                "exit_code": res.returncode,
                "output": output
            })
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_diff_risk(self):
        try:
            data = self.get_post_data()
            repo_path = os.path.abspath(data.get("repo", ""))
            filepath = data.get("file", "")
            old_code = data.get("old_code", "")
            new_code = data.get("new_code", "")
            
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
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_dependency_graph(self):
        try:
            data = self.get_request_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid payload"})
                return
            repo = data.get("repo", "") or os.getcwd()
            repo_path = os.path.abspath(repo)
            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Not a directory: {repo_path}"})
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
                r = risk_index.get(nid)
                arch_role = getattr(r, "architectural_role", None)
                strat = getattr(r, "change_strategy", None)
                enriched_nodes.append({
                    "id": nid,
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

            self.send_json_response(200, {
                "success": True,
                "nodes": enriched_nodes,
                "links": normalized_links,
                "medians": medians,
            })
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_predict_impact(self):
        try:
            data = self.get_post_data()
            repo_path = os.path.abspath(data.get("repo", ""))
            changed_files = data.get("changed_files", [])
            changed_functions = data.get("changed_functions", [])
            
            test_file_path = os.path.join(repo_path, "run_tests.py")
            if not os.path.exists(test_file_path):
                test_file_path = os.path.join(repo_path, "ultron", "tests", "run_tests.py")
                
            codebase = analyzer.analyze_directory(repo_path)
            predictions = predict.predict_test_impact(codebase, changed_files, changed_functions, test_file_path)
            self.send_json_response(200, {
                "success": True,
                "predictions": predictions
            })
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_save_session(self):
        try:
            data = self.get_post_data()
            repo_path = os.path.abspath(data.get("repo", ""))
            session_data = data.get("session_data", {})
            
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
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_calibrate(self):
        try:
            data = self.get_post_data()
            repo = data.get("repo", "") or os.getcwd()
            repo_path = os.path.abspath(repo)
            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return
            from ultron.core import meta_layer
            res = meta_layer.run_threshold_calibration(repo_path)
            self.send_json_response(200, res)
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
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_log_risk_feedback(self):
        try:
            data = self.get_post_data()
            filepath = data.get("file", "")
            accurate = bool(data.get("accurate", True))
            
            if not filepath:
                self.send_json_response(400, {"error": "Missing 'file' parameter."})
                return
                
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
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_pledge_create(self):
        try:
            data = self.get_post_data()
            filepath = data.get("file", "")
            predicted_delta_i = float(data.get("predicted_delta_i", 0.0))
            predicted_mkr = float(data.get("predicted_mkr", 1.0))
            predicted_delta_cest = float(data.get("predicted_delta_cest", 0.0))
            
            if not filepath:
                self.send_json_response(400, {"error": "Missing 'file' parameter."})
                return
                
            plg = pledge.create_pledge(filepath, predicted_delta_i, predicted_mkr, predicted_delta_cest)
            self.send_json_response(200, {
                "success": True,
                "pledge": plg
            })
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_pledge_verify(self):
        try:
            data = self.get_post_data()
            repo_path = os.path.abspath(data.get("repo", ""))
            filepath = data.get("file", "")
            actual_delta_i = float(data.get("actual_delta_i", 0.0))
            actual_mkr = float(data.get("actual_mkr", 1.0))
            actual_delta_cest = float(data.get("actual_delta_cest", 0.0))
            actual_failure = float(data.get("actual_failure", 0.0))
            
            if not filepath:
                self.send_json_response(400, {"error": "Missing 'file' parameter."})
                return
                
            res = pledge.verify_pledge(filepath, actual_delta_i, actual_mkr, actual_delta_cest, actual_failure)
            self.send_json_response(200, {
                "success": True,
                "verification": res
            })
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
                
            active_count = len(pledge.load_active_pledges())
            
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
                
            repo = data.get("repo", "")
            codebase = {}
            repo_path = ""
            if action in ("audit", "simulate") or (action == "recommend" and repo):
                if not isinstance(repo, str) or not repo.strip():
                    self.send_json_response(400, {"error": "Missing or empty 'repo' parameter."})
                    return
                repo_path = os.path.abspath(repo)
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
                intent = data.get("intent")
                if not isinstance(intent, str) or not intent.strip():
                    self.send_json_response(400, {"error": "Missing or empty 'intent' parameter."})
                    return
                if len(intent) > 5000:
                    self.send_json_response(400, {"error": "Intent length exceeds limit of 5000 characters."})
                    return
                recommendations = design_oracle.recommend_patterns(codebase, intent) if design_oracle else []
                self.send_json_response(200, {
                    "success": True,
                    "recommendations": recommendations
                })
                
            elif action == "simulate":
                src_file = data.get("src_file")
                dest_file = data.get("dest_file")
                if not isinstance(src_file, str) or not src_file.strip():
                    self.send_json_response(400, {"error": "Missing or empty 'src_file' parameter."})
                    return
                if not isinstance(dest_file, str) or not dest_file.strip():
                    self.send_json_response(400, {"error": "Missing or empty 'dest_file' parameter."})
                    return
                    
                src_file_norm = src_file.replace("\\", "/").strip()
                dest_file_norm = dest_file.replace("\\", "/").strip()
                
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
                entity_id = data.get("entity_id") or data.get("file") or data.get("src_file")
                if not entity_id or not isinstance(entity_id, str) or not entity_id.strip():
                    self.send_json_response(400, {"error": "Missing or empty 'entity_id' or 'file' parameter."})
                    return
                entity_id = entity_id.replace("\\", "/").strip()
                
                repo_path = os.path.abspath(repo) if repo and repo.strip() else self.get_repo_root_path()
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
                        {
                            "evidence_type": "metric_threshold",
                            "value": f"Risk Score={decision.risk_score:.1f}",
                            "description": f"Triggered Reason Codes: {reasons_str}"
                        }
                    ]
                }
                
                repair_simulation = {
                    "plain_summary": f"Decouple {entity_id} to restore stability and speed up changes.",
                    "technical_rule": f"RKM-POLICY-{decision.policy_version}",
                    "before_state": {
                        "structure": f"{entity_id} directly coupled with high complexity.",
                        "risk_score": decision.risk_score,
                        "status": "AT_RISK" if decision.risk_score > 50 else "MODERATE"
                    },
                    "after_state": {
                        "structure": f"Refactored {entity_id} using interface boundaries.",
                        "estimated_risk_score": max(10.0, round(decision.risk_score * 0.3, 1)),
                        "status": "STABLE"
                    },
                    "recommended_steps": [
                        f"1. Extract shared interfaces from {entity_id} into a decoupled API module.",
                        "2. Add unit tests for boundary contracts.",
                        "3. Run 'ultron check' to verify risk reduction."
                    ]
                }
                
                from dataclasses import asdict
                self.send_json_response(200, {
                    "status": "success",
                    "entity_id": entity_id,
                    "decision": asdict(decision),
                    "communication": comm_personas["personas"],
                    "trust_chain": trust_chain,
                    "repair_simulation": repair_simulation
                })
                
        except (ValueError, TypeError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {
                "error": f"Internal Server Error: {e}",
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

    def _memory_snapshot(self, repo_path: str) -> dict:
        """Everything the UI needs from the persisted knowledge base, or an
        honest reason why there is nothing yet."""
        db_path = os.path.join(repo_path, ".ultron", "repository.db")
        if not os.path.exists(db_path):
            return {
                "initialized": False,
                "reason": "never_analyzed",
                "latest_run": None,
                "hotspots": [],
                "recommendations": []
            }
        try:
            from ultron.core.rkm.store import RepositoryStore
            from ultron.core.rkm.evolution.engine import EvolutionEngine
            from ultron.core.rkm.recommendation_service import get_recommendations

            store = RepositoryStore(db_path)
            try:
                meta = store.get_metadata()
                if not meta or not meta.latest_analysis_run_id:
                    return {
                        "initialized": False,
                        "reason": "no_completed_run",
                        "latest_run": None,
                        "hotspots": [],
                        "recommendations": []
                    }
                run_id = meta.latest_analysis_run_id
                run = store.get_analysis_run(run_id)
                health_run = EvolutionEngine.evaluate_health_score(store, run_id)
                score = round(
                    (health_run.architecture_stability * 0.4 +
                     health_run.rule_compliance * 0.4 +
                     health_run.complexity_trend * 0.2) * 100, 1
                )
                hotspots = [
                    {
                        "file_path": h.file_path,
                        "change_count": h.change_count,
                        "violation_count": h.violation_count,
                        "hotspot_score": h.hotspot_score,
                        "severity_level": h.severity_level
                    }
                    for h in EvolutionEngine.detect_hotspots(store, run_id)
                ][:10]
            finally:
                store.close()

            recs = get_recommendations(repo_path, limit=10)
            return {
                "initialized": True,
                "reason": None,
                "repository_uuid": meta.repository_uuid,
                "health_score": score,
                "latest_run": {
                    "run_id": run.id,
                    "timestamp": run.timestamp,
                    "engine_version": run.engine_version
                } if run else None,
                "hotspots": hotspots,
                "recommendations": recs.get("recommendations", []) if isinstance(recs, dict) else []
            }
        except Exception as e:
            return {
                "initialized": False,
                "reason": "memory_unreadable",
                "error": str(e),
                "latest_run": None,
                "hotspots": [],
                "recommendations": []
            }

    def handle_v1_overview(self):
        """One request, everything the main screen shows.

        The dashboard previously assembled this from a dozen calls with
        inconsistent repo handling, several of which could never return data.
        """
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                data = {}
            requested = str(data.get("repo", "")).strip()
            repo_path = os.path.abspath(requested) if requested else self.get_repo_root_path()

            if not os.path.exists(repo_path):
                self.send_json_response(400, {"status": "error", "message": f"'{repo_path}' does not exist."})
                return
            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"status": "error", "message": f"'{repo_path}' is a file, not a directory."})
                return

            intent = str(data.get("intent", "")).strip()
            target_files = coerce_file_list(data.get("files"))
            repo_block = {"path": repo_path, "name": os.path.basename(repo_path) or repo_path}

            codebase = analyzer.analyze_directory(repo_path)
            if not codebase:
                self.send_json_response(200, {
                    "status": "success",
                    "state": "analysis_empty",
                    "repo": repo_block,
                    "message": "No Python files found here. Pick a folder that contains Python source.",
                    "stats": {"total_files": 0, "total_definitions": 0, "high": 0, "medium": 0, "low": 0},
                    "health": {"score": None, "source": "none", "explanation": "Nothing to measure yet."},
                    "intent": {"text": intent, "matched": True, "message": ""},
                    "risks": [],
                    "memory": self._memory_snapshot(repo_path)
                })
                return

            risks = risk.evaluate_risks(codebase, target_files, intent, repo_path=repo_path)
            intent_matched = True
            if intent and not target_files and not risks:
                intent_matched = False
                risks = risk.evaluate_risks(codebase, [], "", repo_path=repo_path)

            ranked = sorted(risks, key=lambda r: getattr(r, "impact_score", 0.0), reverse=True)
            levels = [getattr(r, "level", "LOW") for r in ranked]
            high = levels.count("HIGH")
            medium = levels.count("MEDIUM")
            low = len(levels) - high - medium

            memory = self._memory_snapshot(repo_path)
            if memory.get("initialized") and memory.get("health_score") is not None:
                health = {
                    "score": memory["health_score"],
                    "source": "memory",
                    "explanation": "Scored from the last saved analysis (rule compliance, stability, complexity trend)."
                }
            elif ranked:
                penalty = (high / len(ranked)) * 70 + (medium / len(ranked)) * 20
                health = {
                    "score": round(max(0.0, 100.0 - penalty), 1),
                    "source": "live",
                    "explanation": f"{high} of {len(ranked)} files are high risk. Save an analysis to track this over time."
                }
            else:
                health = {"score": None, "source": "none", "explanation": "No files scored."}

            self.send_json_response(200, {
                "status": "success",
                "state": "ok",
                "repo": repo_block,
                "stats": {
                    "total_files": len(codebase),
                    "total_definitions": sum(len(c.get("definitions", [])) for c in codebase.values()),
                    "high": high,
                    "medium": medium,
                    "low": low
                },
                "health": health,
                "intent": {
                    "text": intent,
                    "matched": intent_matched,
                    "message": "" if intent_matched else f"No files matched \"{intent}\". Showing the whole repository instead."
                },
                "risks": [r.to_dict() for r in ranked],
                "memory": memory
            })
        except PermissionError as e:
            self.send_json_response(400, {"status": "error", "message": f"Permission denied: {e}"})
        except Exception as e:
            self.send_json_response(500, {"status": "error", "message": str(e)})

    def get_repo_root_path(self) -> str:
        cwd_config = os.path.join(os.getcwd(), ".ultron", "config.json")
        for cfg_path in (cwd_config, CONFIG_FILE):
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        val = cfg.get("repo_root")
                        if val and os.path.isdir(val):
                            return os.path.abspath(val)
                except Exception:
                    pass
        return os.path.abspath(os.getcwd())

    def handle_v1_progress(self):
        global ACTIVE_JOB
        self.send_json_response(200, {
            "status": ACTIVE_JOB["status"],
            "progress_step": ACTIVE_JOB["progress_step"],
            "error": ACTIVE_JOB["error"],
            "job_id": ACTIVE_JOB["job_id"]
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

    def handle_v1_analyze(self):
        global ACTIVE_JOB
        if ACTIVE_JOB["status"] == "running":
            self.send_json_response(400, {"error": "Analysis is already running"})
            return

        # The dashboard sends the repository it is showing; honouring it keeps the
        # persisted knowledge base pointed at the same tree the user is looking at.
        try:
            body = self.get_post_data()
        except Exception:
            body = {}
        requested_repo = ""
        if isinstance(body, dict):
            requested_repo = str(body.get("repo", "")).strip()
        repo_root = os.path.abspath(requested_repo) if requested_repo else self.get_repo_root_path()
        if not os.path.isdir(repo_root):
            self.send_json_response(400, {"error": f"Repository path '{repo_root}' is not a directory."})
            return

        import uuid
        import threading
        job_id = str(uuid.uuid4())
        
        ACTIVE_JOB["status"] = "running"
        ACTIVE_JOB["progress_step"] = "Scanning repository"
        ACTIVE_JOB["error"] = None
        ACTIVE_JOB["cancel_requested"] = False
        ACTIVE_JOB["job_id"] = job_id
        
        def run_pipeline():
            global ACTIVE_JOB
            try:
                from ultron.core.pipeline import orchestrator
                
                if ACTIVE_JOB["cancel_requested"]:
                    ACTIVE_JOB["status"] = "cancelled"
                    return
                ACTIVE_JOB["progress_step"] = "Reading repository"

                orchestrator.analyze_repository(repo_root, force=True)
                
                if ACTIVE_JOB["cancel_requested"]:
                    ACTIVE_JOB["status"] = "cancelled"
                    return
                ACTIVE_JOB["progress_step"] = "Done"
                ACTIVE_JOB["status"] = "success"
                
            except Exception as e:
                ACTIVE_JOB["status"] = "failed"
                ACTIVE_JOB["error"] = str(e)
                ACTIVE_JOB["progress_step"] = "Done"
                
        thread = threading.Thread(target=run_pipeline, daemon=True)
        thread.start()
        
        self.send_json_response(200, {"success": True, "job_id": job_id, "repo": repo_root})

    def handle_v1_cancel_analysis(self):
        global ACTIVE_JOB
        if ACTIVE_JOB["status"] != "running":
            self.send_json_response(400, {"error": "No running analysis to cancel"})
            return
            
        ACTIVE_JOB["cancel_requested"] = True
        ACTIVE_JOB["status"] = "cancelled"
        self.send_json_response(200, {"success": True})

    def handle_v1_compare(self):
        from ultron.core.rkm.store import RepositoryStore
        from ultron.interfaces.api import HistoryAPI
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data.decode('utf-8'))
            run_a = int(params["run_id_a"])
            run_b = int(params["run_id_b"])
        except Exception:
            self.send_json_response(400, {"error": "Invalid JSON body or missing run_id_a/run_id_b"})
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
        finally:
            store.close()

    def handle_v1_explain_violation(self):
        from ultron.core.rkm.store import RepositoryStore
        from ultron.core.translate import translate_violation_to_plain_english
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data.decode('utf-8'))
            vio_id = int(params["violation_id"])
        except Exception:
            self.send_json_response(400, {"error": "Invalid body or missing violation_id"})
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
            self.send_json_response(500, {"error": f"Failed to explain violation: {str(e)}"})

    def handle_v1_ai_critique(self):
        try:
            data = self.get_request_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid payload"})
                return
            
            file_path = data.get("file", "") or data.get("file_path", "")
            if not file_path:
                self.send_json_response(400, {"error": "Missing required 'file' parameter"})
                return
                
            from ultron.core.ai.client import AIClient
            ai_client = AIClient()
            critique = ai_client.query_critique(
                file_path=file_path,
                complexity=int(data.get("complexity", 10)),
                coupling=int(data.get("coupling", 5)),
                impact_score=float(data.get("impact_score", 12.0)),
                intent=data.get("intent", "")
            )
            self.send_json_response(200, critique)
        except (ValueError, KeyError, TypeError, OSError) as err:
            self.send_json_response(500, {"error": f"AI critique generation failed: {str(err)}"})

def serve(port=8000):
    """Launches the Ultron REST API & Web Dashboard Server.

    Raises:
        OSError: If the port is already in use (allows caller to retry).
    """
    # Console encoding safety for server-side print/log statements
    import sys as _sys
    for _stream in (_sys.stdout, _sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    # Bind loopback only: Ultron exposes unauthenticated filesystem APIs, so it must
    # never be reachable from the network.
    #
    # Note this socket is IPv4-only. On Windows the name 'localhost' usually resolves to
    # ::1 first, so clients that use the hostname pay a ~2s failed-IPv6-connect penalty
    # on every request. Entry points therefore advertise LOOPBACK_HOST, not 'localhost'.
    server_address = (LOOPBACK_HOST, port)
    try:
        httpd = http.server.HTTPServer(server_address, UltronAPIHandler)
    except OSError as e:
        # Re-raise so the caller (start.py) can try a different port
        raise

    print(f"[*] Ultron Dashboard Server running on http://{LOOPBACK_HOST}:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")
        httpd.server_close()