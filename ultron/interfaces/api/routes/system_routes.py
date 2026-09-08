"""
Ultron REST API — System, Configuration, File, Test & Architecture Health Route Mixin
"""

import os
import sys
import json
import shutil
import subprocess
import threading
import tempfile
import traceback
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse
from dataclasses import asdict

from ultron.core import analyzer
from ultron.core import risk
from ultron.core import translate
from ultron.interfaces.api.router import APIRouter
from ultron.core.language_adapter import PythonLanguageAdapter
from ultron.core.system_query import SystemQueryEngine
from ultron.core.system_model import SystemModelManager
from ultron.interfaces.api.state import (
    LAST_ANALYSIS,
    ACTIVE_JOB,
    BROWSE_DIALOG_TIMEOUT,
    CONFIG_DIR,
    CONFIG_FILE,
)

try:
    from ultron.experimental import delta
except ImportError:
    delta = None
try:
    from ultron.experimental import design_oracle
except ImportError:
    design_oracle = None

logger = logging.getLogger(__name__)

# Shared in-memory system model manager cache
_GLOBAL_MODEL_MANAGER: Optional[SystemModelManager] = None
_GLOBAL_MODEL_MANAGERS: Dict[str, SystemModelManager] = {}


def get_or_build_system_model(handler: Any) -> SystemModelManager:
    """Helper to retrieve or build the canonical SystemModel for the active repository."""
    global _GLOBAL_MODEL_MANAGER, _GLOBAL_MODEL_MANAGERS

    repo_path = "."
    if hasattr(handler, "get_repo_root_path"):
        try:
            repo_path = handler.get_repo_root_path()
        except Exception:
            repo_path = "."
    elif hasattr(handler, "current_repo_path"):
        repo_path = getattr(handler, "current_repo_path", ".") or "."

    norm_path = os.path.normcase(os.path.abspath(repo_path)).replace("\\", "/")
    if norm_path in _GLOBAL_MODEL_MANAGERS:
        return _GLOBAL_MODEL_MANAGERS[norm_path]

    if _GLOBAL_MODEL_MANAGER is not None:
        return _GLOBAL_MODEL_MANAGER

    adapter = PythonLanguageAdapter()
    graph = adapter.parse_repository(repo_path)
    manager = SystemModelManager()
    manager.graph = graph
    _GLOBAL_MODEL_MANAGER = manager
    _GLOBAL_MODEL_MANAGERS[norm_path] = manager
    return manager


def reset_system_model_cache() -> None:
    """Resets global in-memory model manager cache."""
    global _GLOBAL_MODEL_MANAGER, _GLOBAL_MODEL_MANAGERS
    _GLOBAL_MODEL_MANAGER = None
    _GLOBAL_MODEL_MANAGERS.clear()


@APIRouter.register("/api/v1/system/graph", "GET")
def handle_v1_system_graph(handler: Any) -> None:
    """GET /api/v1/system/graph — Returns full canonical SystemGraph payload."""
    manager = get_or_build_system_model(handler)
    payload = {
        "success": True,
        "data": manager.serialize(),
        "error": None
    }
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


@APIRouter.register("/api/v1/system/node", "GET")
def handle_v1_system_node(handler: Any) -> None:
    """GET /api/v1/system/node?id=... — Returns metadata for a target SystemNode."""
    target_id = ""
    if hasattr(handler, "path") and "?" in handler.path:
        query_str = handler.path.split("?", 1)[1]
        for param in query_str.split("&"):
            if param.startswith("id="):
                target_id = param.split("=", 1)[1]
                break

    if not target_id:
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"success": False, "data": None, "error": "Query parameter 'id' is required"}).encode("utf-8"))
        return

    manager = get_or_build_system_model(handler)
    query_engine = SystemQueryEngine(manager.graph)
    node = query_engine.find_node(target_id)

    if not node:
        handler.send_response(404)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"success": False, "data": None, "error": f"Node '{target_id}' not found in SystemModel"}).encode("utf-8"))
        return

    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps({"success": True, "data": node.to_dict(), "error": None}, ensure_ascii=False).encode("utf-8"))


@APIRouter.register("/api/v1/agent/context", "POST")
def handle_v1_agent_context(handler: Any) -> None:
    """POST /api/v1/agent/context — Returns targeted agent context subgraph."""
    post_data = {}
    if hasattr(handler, "get_post_data"):
        try:
            post_data = handler.get_post_data() or {}
        except Exception as e:
            handler.send_response(400)
            handler.send_header("Content-Type", "application/json; charset=utf-8")
            handler.end_headers()
            handler.wfile.write(json.dumps({"success": False, "data": None, "error": f"Invalid JSON payload: {e}"}).encode("utf-8"))
            return

    target = post_data.get("target") or post_data.get("file_path") or post_data.get("node_id")
    if not target:
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"success": False, "data": None, "error": "Field 'target' or 'file_path' is required in POST body"}).encode("utf-8"))
        return

    depth = int(post_data.get("depth", 2))
    manager = get_or_build_system_model(handler)
    query_engine = SystemQueryEngine(manager.graph)
    ctx = query_engine.get_agent_context(target, depth=depth)

    if not ctx.get("found"):
        handler.send_response(404)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"success": False, "data": ctx, "error": ctx.get("error")}).encode("utf-8"))
        return

    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps({"success": True, "data": ctx, "error": None}, ensure_ascii=False).encode("utf-8"))


class SystemRoutesMixin:
    """Provides system, configuration, file, test and health API endpoints for UltronAPIHandler."""

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

    def handle_list_dirs(self):
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

    def handle_browse_folder(self):
        try:
            from ultron.interfaces.api.browse_folder import select_folder_dialog
            data = self.get_post_data()
            initial_dir = data.get("initial_dir") or self.get_repo_root_path()

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


    def handle_architecture_health(self):
        try:
            data = self.get_request_data() if hasattr(self, "get_request_data") else (self.get_post_data() if hasattr(self, "get_post_data") else getattr(self, "query", {}))
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid request payload. Expected JSON object."})
                return
            repo = data.get("repo")
            if not isinstance(repo, str) or not repo.strip():
                self.send_json_response(400, {"error": "Missing or invalid 'repo' parameter."})
                return
                
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
                is_empty = (state == "analysis_empty")
                self.send_json_response(200, {
                    "success": True if is_empty else False,
                    "state": state,
                    "health_score": 100 if is_empty else None,
                    "sub_scores": {
                        "architecture_stability": 1.0,
                        "rule_compliance": 1.0,
                        "risk_distribution": 1.0
                    } if is_empty else None,
                    "health_band": "healthy" if is_empty else None,
                    "explanation": "Repository health is rated HEALTHY (100.0/100). No code files analyzed." if is_empty else None,
                    "message": (
                        "No Python files found in this repository."
                        if is_empty
                        else "Python files were found but none could be analyzed. Check the server console for parse errors."
                    ),
                    "analyzed_file_count": 0,
                    "hotspots": [],
                    "circular_dependencies": [],
                    "violations": [],
                    "contracts": []
                })
                return

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

            from ultron.core.rkm.evolution.engine import EvolutionEngine

            cycle_count = len(cycles)
            cycle_score = max(0.0, 1.0 - 0.8 * cycle_count)

            total_loc = 0
            for rel in target_files:
                abs_f = os.path.join(repo_path, rel)
                try:
                    with open(abs_f, "r", encoding="utf-8", errors="ignore") as f:
                        total_loc += sum(1 for line in f if line.strip())
                except (OSError, UnicodeDecodeError):
                    pass
            if total_loc <= 0:
                total_loc = max(1, sum(os.path.getsize(os.path.join(repo_path, rel)) for rel in target_files if os.path.exists(os.path.join(repo_path, rel))) // 35)

            density = len(violations) / max(0.1, total_loc / 1000.0)
            compliance_score = max(0.0, 1.0 - density / 3.0)

            high_files_count = sum(1 for r in risks if getattr(r, "level", None) == "HIGH")
            distribution_score = max(0.0, 1.0 - 5.0 * (high_files_count / max(1, len(target_files))))

            sub_scores = {
                "architecture_stability": round(cycle_score, 4),
                "rule_compliance": round(compliance_score, 4),
                "risk_distribution": round(distribution_score, 4),
            }
            composite = (cycle_score * 0.40 + compliance_score * 0.40 + distribution_score * 0.20) * 100.0
            health_score = round(max(0.0, min(100.0, composite)), 1)
            health_band = EvolutionEngine.get_health_band(health_score)
            explanation = EvolutionEngine.format_health_explanation(health_score, sub_scores)

            self.send_json_response(200, {
                "success": True,
                "state": "ok",
                "health_score": health_score,
                "sub_scores": sub_scores,
                "health_band": health_band,
                "explanation": explanation,
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


    def handle_v1_recommendations(self):
        try:
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

    def handle_work_state(self):
        try:
            repo = self.get_repo_root_path() if hasattr(self, "get_repo_root_path") else "."
            from ultron.core.issue_orchestrator import IssueOrchestrator
            orch = IssueOrchestrator(repo)
            summary = orch.get_current_work_summary()
            self.send_json_response(200, {"status": "ok", "work_state": summary})
        except Exception as e:
            self.send_json_response(500, {"status": "error", "error": str(e)})

    def handle_work_advance(self):
        try:
            data = self.get_post_data() or {}
            repo = data.get("repo") or (self.get_repo_root_path() if hasattr(self, "get_repo_root_path") else ".")
            from ultron.core.issue_orchestrator import IssueOrchestrator
            orch = IssueOrchestrator(repo)
            outcome = orch.advance_next_step()
            self.send_json_response(200, {"status": "ok", "result": outcome})
        except Exception as e:
            self.send_json_response(500, {"status": "error", "error": str(e)})

    def handle_work_visual_delta(self):
        try:
            repo = self.get_repo_root_path() if hasattr(self, "get_repo_root_path") else "."
            from ultron.core.issue_orchestrator import IssueOrchestrator
            orch = IssueOrchestrator(repo)
            delta_info = getattr(orch, "get_visual_delta", None)
            delta_data = delta_info() if callable(delta_info) else {"changed_files": [], "diff": ""}
            self.send_json_response(200, {"status": "ok", "visual_delta": delta_data})
        except Exception as e:
            self.send_json_response(500, {"status": "error", "error": str(e)})


