import http.server
import json
import os
import sys

from ultron.interfaces.api.state import (
    LAST_ANALYSIS,
    ACTIVE_JOB,
    PORT,
    LOOPBACK_HOST,
    BROWSE_DIALOG_TIMEOUT,
    WEB_DIR,
    CONFIG_DIR,
    CONFIG_FILE,
    _is_local_origin,
    coerce_file_list,
    validate_repo_path,
)
from ultron.interfaces.api.router import APIRouter
import ultron.interfaces.api.routes
from ultron.interfaces.api.routes.analysis_routes import AnalysisRoutesMixin
from ultron.interfaces.api.routes.graph_routes import GraphRoutesMixin
from ultron.interfaces.api.routes.agent_routes import AgentRoutesMixin
from ultron.interfaces.api.routes.audit_routes import AuditRoutesMixin
from ultron.interfaces.api.routes.system_routes import SystemRoutesMixin

try:
    from ultron.experimental import delta
except ImportError:
    delta = None
try:
    from ultron.experimental import design_oracle
except ImportError:
    design_oracle = None


class UltronAPIHandler(
    AnalysisRoutesMixin,
    GraphRoutesMixin,
    AgentRoutesMixin,
    AuditRoutesMixin,
    SystemRoutesMixin,
    http.server.SimpleHTTPRequestHandler
):
    def end_headers(self):
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
        
        if APIRouter.dispatch(self, parsed_path, "GET"):
            return
            
        get_dispatch = {
            "/api/v1/risk-profile": self.handle_v1_risk_profile,
            "/api/v1/decision": self.handle_v1_decision,
            "/api/architecture-health": self.handle_architecture_health,
            "/api/file-tree": self.handle_file_tree,
            "/api/analyze": self.handle_analyze,
            "/api/dependency-graph": self.handle_dependency_graph,
            "/api/audit": self.handle_audit,
            "/api/report": self.handle_report,
            "/api/get-repo-root": self.handle_get_repo_root,
            "/api/list-dirs": self.handle_list_dirs,
            "/api/v1/progress": self.handle_v1_progress,
            "/api/v1/status": self.handle_v1_progress,
            "/api/v1/health": self.handle_v1_health,
            "/api/health": self.handle_v1_health,
            "/api/v1/summary": self.handle_v1_summary,
            "/api/v1/runs": self.handle_v1_runs,
            "/api/v1/hotspots": self.handle_v1_hotspots,
            "/api/v1/recommendations": self.handle_v1_recommendations,
            "/api/v1/history": self.handle_v1_history,
        }
        
        handler = get_dispatch.get(parsed_path)
        if handler:
            handler()
            return
        if parsed_path.startswith("/api/v1/risk-profile"):
            self.handle_v1_risk_profile()
            return
        if parsed_path.startswith("/api/v1/decision"):
            self.handle_v1_decision()
            return
            
        if parsed_path in ("/", ""):
            file_path = os.path.join(WEB_DIR, "index.html")
        else:
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

        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png",
            ".svg": "image/svg+xml; charset=utf-8"
        }
        ext = os.path.splitext(file_path)[1]
        content_type = content_types.get(ext, "text/plain; charset=utf-8")

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
        
        if APIRouter.dispatch(self, req_path, "POST"):
            return
            
        post_dispatch = {
            "/api/v1/analyze": self.handle_v1_analyze,
            "/api/v1/overview": self.handle_v1_overview,
            "/api/v1/cancel-analysis": self.handle_v1_cancel_analysis,
            "/api/v1/compare": self.handle_v1_compare,
            "/api/v1/explain-violation": self.handle_v1_explain_violation,
            "/api/config": self.handle_config,
            "/api/analyze": self.handle_analyze,
            "/api/audit": self.handle_audit,
            "/api/generate": self.handle_generate,
            "/api/file-tree": self.handle_file_tree,
            "/api/architecture-health": self.handle_architecture_health,
            "/api/get-file": self.handle_get_file,
            "/api/save-file": self.handle_save_file,
            "/api/run-tests": self.handle_run_tests,
            "/api/diff-risk": self.handle_diff_risk,
            "/api/dependency-graph": self.handle_dependency_graph,
            "/api/predict-impact": self.handle_predict_impact,
            "/api/save-session": self.handle_save_session,
            "/api/calibrate": self.handle_calibrate,
            "/api/playground": self.handle_playground,
            "/api/log-risk-feedback": self.handle_log_risk_feedback,
            "/api/pledge/create": self.handle_pledge_create,
            "/api/pledge/verify": self.handle_pledge_verify,
            "/api/report": self.handle_report,
            "/api/design-oracle": self.handle_design_oracle,
            "/api/browse-folder": self.handle_browse_folder,
            "/api/v1/context-brief": self.handle_v1_context_brief,
            "/api/v1/export-brief": self.handle_v1_export_brief,
            "/api/v1/ai/critique": self.handle_v1_ai_critique,
            "/api/set-repo-root": self.handle_set_repo_root,
            "/api/v1/mcp/setup": getattr(self, "handle_v1_mcp_setup", None),
        }
        
        handler = post_dispatch.get(req_path)
        if handler:
            handler()
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
        cmd = getattr(self, "command", "POST")
        if cmd == "GET":
            q_data = self.get_query_data()
            if isinstance(q_data, dict) and q_data.get("repo"):
                return q_data

        post_data = self.get_post_data()
        if post_data is None:
            return None
        if isinstance(post_data, dict):
            if "repo" not in post_data or not post_data["repo"]:
                post_data["repo"] = "."
            return post_data
        return post_data

    def send_json_response(self, status_code, data, message=None):
        try:
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            if data is not None and isinstance(data, (dict, list)):
                response_bytes = json.dumps(data).encode('utf-8')
            elif message is not None:
                payload = {"status": "error" if status_code >= 400 else "ok", "message": message}
                response_bytes = json.dumps(payload).encode('utf-8')
            else:
                response_bytes = json.dumps({}).encode('utf-8')
            self.wfile.write(response_bytes)
        except (OSError, BrokenPipeError, ConnectionResetError):
            pass


def serve(port=8000):
    """Launches the Ultron REST API & Web Dashboard Server."""
    import sys as _sys
    for _stream in (_sys.stdout, _sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    server_address = (LOOPBACK_HOST, port)
    httpd = http.server.HTTPServer(server_address, UltronAPIHandler)
    print(f"[*] Ultron Dashboard Server running on http://{LOOPBACK_HOST}:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")
        httpd.server_close()