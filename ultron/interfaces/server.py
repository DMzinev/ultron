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
            "/api/architecture-health": self.handle_architecture_health, "/api/file-tree": self.handle_file_tree,
            "/api/analyze": self.handle_analyze, "/api/dependency-graph": self.handle_dependency_graph,
            "/api/audit": self.handle_audit, "/api/report": self.handle_report,
            "/api/get-repo-root": self.handle_get_repo_root, "/api/list-dirs": self.handle_list_dirs,
            "/api/v1/progress": self.handle_v1_progress, "/api/v1/status": self.handle_v1_progress,
            "/api/v1/health": self.handle_v1_health, "/api/health": self.handle_v1_health,
            "/api/v1/summary": self.handle_v1_summary, "/api/v1/recommendations": self.handle_v1_recommendations,
        }
        
        handler = get_dispatch.get(parsed_path)
        if handler:
            handler()
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
            ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
            ".png": "image/png", ".svg": "image/svg+xml; charset=utf-8"
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
            "/api/v1/analyze": self.handle_v1_analyze, "/api/v1/overview": self.handle_v1_overview,
            "/api/v1/cancel-analysis": self.handle_v1_cancel_analysis, "/api/config": self.handle_config,
            "/api/analyze": self.handle_analyze, "/api/audit": self.handle_audit,
            "/api/generate": self.handle_generate, "/api/file-tree": self.handle_file_tree,
            "/api/architecture-health": self.handle_architecture_health, "/api/get-file": self.handle_get_file,
            "/api/save-file": self.handle_save_file, "/api/dependency-graph": self.handle_dependency_graph,
            "/api/playground": self.handle_playground, "/api/log-risk-feedback": self.handle_log_risk_feedback,
            "/api/pledge/create": self.handle_pledge_create, "/api/pledge/verify": self.handle_pledge_verify,
            "/api/report": self.handle_report, "/api/design-oracle": self.handle_design_oracle,
            "/api/browse-folder": self.handle_browse_folder, "/api/v1/context-brief": self.handle_v1_context_brief,
            "/api/v1/export-brief": self.handle_v1_export_brief, "/api/v1/ai/critique": self.handle_v1_ai_critique,
            "/api/set-repo-root": self.handle_set_repo_root, "/api/v1/mcp/setup": getattr(self, "handle_v1_mcp_setup", None),
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


def _persist_repo_root(active_repo):
    if active_repo and os.path.isdir(os.path.abspath(active_repo)):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            cfg = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            cfg["repo_root"] = os.path.abspath(active_repo)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass


def create_server(host=LOOPBACK_HOST, start_port=8000, max_attempts=50):
    """Deterministically binds to the first free port starting at start_port."""
    import errno as _errno
    for offset in range(max_attempts):
        candidate_port = start_port + offset
        if candidate_port > 65535:
            break
        try:
            httpd = http.server.HTTPServer((host, candidate_port), UltronAPIHandler)
            return httpd, httpd.server_address[1]
        except OSError as e:
            is_in_use = (
                getattr(e, "errno", None) in (_errno.EADDRINUSE, _errno.EACCES, 48, 98, 10048, 10013)
                or getattr(e, "winerror", None) in (10048, 10013)
                or any(k in str(e).lower() for k in ("address already in use", "already permitted", "access permissions"))
            )
            if not is_in_use or offset == max_attempts - 1:
                raise
    raise OSError(f"Could not bind to any free port in range {start_port}-{start_port + max_attempts - 1} on {host}")


def serve(port=8000, host=LOOPBACK_HOST, open_browser=False, repo=None,
          max_attempts=50, auto_fallback=True, target_repo=None, **kwargs):
    """Launches the Ultron REST API & Web Dashboard Server."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try: stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception: pass

    _persist_repo_root(repo or target_repo)
    httpd, bound_port = create_server(host=host, start_port=port, max_attempts=max_attempts if auto_fallback else 1)
    display_host = "127.0.0.1" if host in ("0.0.0.0", "", None) else host
    server_url = f"http://{display_host}:{bound_port}/"
    print(f"[*] Ultron Dashboard Server running on {server_url}")

    if open_browser:
        import threading, time, webbrowser
        def _launch():
            time.sleep(0.8)
            try: webbrowser.open(server_url)
            except Exception: pass
        threading.Thread(target=_launch, daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")
    finally:
        httpd.server_close()


def main():
    """CLI entrypoint for ultron-server."""
    import argparse
    parser = argparse.ArgumentParser(prog="ultron-server", description="Ultron Architecture Web Dashboard Server")
    parser.add_argument("--port", type=int, default=8000, help="Initial port to bind (default: 8000)")
    parser.add_argument("--host", default=LOOPBACK_HOST, help=f"Host interface to bind (default: {LOOPBACK_HOST})")
    parser.add_argument("--repo", default=".", help="Repository root directory to inspect (default: .)")
    parser.add_argument("--open", action="store_true", default=False, help="Open browser automatically")
    parser.add_argument("--no-browser", action="store_true", default=False, help="Explicitly disable opening browser")
    args = parser.parse_args()
    serve(port=args.port, host=args.host, open_browser=bool(args.open and not args.no_browser), repo=args.repo)


if __name__ == "__main__":
    main()