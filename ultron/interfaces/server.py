import http.server
import socketserver
import json
import os
import sys
import traceback
import shutil
import subprocess

from ultron.core import analyzer
from ultron.core import risk
from ultron.core import prompt
from ultron.core import classifier
from ultron.core import predict
from ultron.experimental import delta
from ultron.core import pledge
from ultron.core import fuzz
from ultron.core import logistic
from ultron.experimental import design_oracle
from ultron.core import translate


LAST_ANALYSIS = {
    "file_path": None,
    "delta_i": 0.0,
    "mkr": 1.0,
    "delta_cest": 0.0
}

PORT = 8000
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

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
        # Route to static files
        parsed_path = self.path.split('?')[0]
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
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        # Determine MIME type
        content_type = "text/plain"
        if file_path.endswith(".html"):
            content_type = "text/html"
        elif file_path.endswith(".css"):
            content_type = "text/css"
        elif file_path.endswith(".js"):
            content_type = "application/javascript"
        elif file_path.endswith(".json"):
            content_type = "application/json"
        elif file_path.endswith(".png"):
            content_type = "image/png"
        elif file_path.endswith(".svg"):
            content_type = "image/svg+xml"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"500 Internal Server Error: {e}".encode())

    def do_POST(self):
        if self.path == "/api/config":
            self.handle_config()
        elif self.path == "/api/analyze":
            self.handle_analyze()
        elif self.path == "/api/audit":
            self.handle_audit()
        elif self.path == "/api/generate":
            self.handle_generate()
        elif self.path == "/api/file-tree":
            self.handle_file_tree()
        elif self.path == "/api/architecture-health":
            self.handle_architecture_health()
        elif self.path == "/api/get-file":
            self.handle_get_file()
        elif self.path == "/api/save-file":
            self.handle_save_file()
        elif self.path == "/api/run-tests":
            self.handle_run_tests()
        elif self.path == "/api/diff-risk":
            self.handle_diff_risk()
        elif self.path == "/api/dependency-graph":
            self.handle_dependency_graph()
        elif self.path == "/api/predict-impact":
            self.handle_predict_impact()
        elif self.path == "/api/save-session":
            self.handle_save_session()
        elif self.path == "/api/calibrate":
            self.handle_calibrate()
        elif self.path == "/api/playground":
            self.handle_playground()
        elif self.path == "/api/log-risk-feedback":
            self.handle_log_risk_feedback()
        elif self.path == "/api/pledge/create":
            self.handle_pledge_create()
        elif self.path == "/api/pledge/verify":
            self.handle_pledge_verify()
        elif self.path == "/api/report":
            self.handle_report()
        elif self.path == "/api/design-oracle":
            self.handle_design_oracle()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode())

    def get_post_data(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        return json.loads(post_data)

    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def handle_analyze(self):
        try:
            data = self.get_post_data()
            repo = data.get("repo", "")
            if not repo:
                self.send_json_response(400, {"error": "Missing required 'repo' parameter."})
                return
            repo_path = os.path.abspath(repo)
            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Repository path '{repo_path}' is not a directory."})
                return
                
            intent = data.get("intent", "")
            files_str = data.get("files", "")
            target_files = [f.strip() for f in files_str.split(",") if f.strip()] if files_str else []
            
            codebase = analyzer.analyze_directory(repo_path)
            risks = risk.evaluate_risks(codebase, target_files, intent, repo_path=repo_path)
            
            # Extract basic stats
            total_files = len(codebase)
            total_definitions = sum(len(c.get("definitions", [])) for c in codebase.values())
            
            self.send_json_response(200, {
                "success": True,
                "stats": {
                    "total_files": total_files,
                    "total_definitions": total_definitions
                },
                "risks": [r.to_dict() for r in risks]
            })
        except Exception as e:
            self.send_json_response(500, {
                "error": str(e),
                "traceback": traceback.format_exc()
            })

    def handle_audit(self):
        try:
            data = self.get_post_data()
            repo_path = os.path.abspath(data.get("repo", ""))
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
            
            names, probs = classifier.build_models(repo_path, exclude_file=target_file)
            anomalies = classifier.audit_target_file(
                target_file, 
                names, 
                probs, 
                typo_threshold=typo_threshold, 
                prob_threshold=prob_threshold
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
            repo_path = os.path.abspath(data.get("repo", ""))
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

    def handle_file_tree(self):
        try:
            data = self.get_post_data()
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
                    if item.startswith('.') or item in ('venv', 'env', '__pycache__', 'tests', 'node_modules'):
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
            data = self.get_post_data()
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
                self.send_json_response(200, {
                    "success": True,
                    "health_score": 100,
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

            # 1. Circular dependencies
            cycles = design_oracle.detect_circular_dependencies(codebase)
            
            # 2. Abstraction leaks
            leaks = design_oracle.detect_abstraction_leaks(codebase, repo_path)
            total_leaks = sum(len(v) for v in leaks.values()) if isinstance(leaks, dict) else 0
            
            # 3. Violations (Reasoning Cards)
            from ultron.experimental.reasoning import ReasoningEngine
            engine = ReasoningEngine(codebase, repo_path)
            violations = engine.analyze()
            
            # 4. Calculate Health Score
            health_score = 100 - (len(cycles) * 15 + len(violations) * 5 + total_leaks * 2)
            health_score = max(10, min(100, health_score))
            
            # 5. Complexity Hotspots
            risks = []
            try:
                risks = risk.evaluate_risks(codebase, target_files, intent="Identify hotspots", repo_path=repo_path)
            except Exception:
                pass
            hotspots = design_oracle.compute_hotspot_scores(codebase, repo_path, risks)
            
            # 6. Recommended refactoring contracts
            from ultron.experimental.impact_simulator import MetricSnapshot
            from ultron.experimental.contract_generator import ContractGenerator
            from ultron.experimental.knowledge_graph import KNOWLEDGE_GRAPH
            
            debt_scores = design_oracle.score_coupling_debt(codebase)
            total_debt = sum(e["coupling_debt"] for e in debt_scores)
            avg_hs = (sum(e["hotspot_score"] for e in hotspots) / len(hotspots)) if hotspots else 0.0
            avg_inst = (sum(e["instability"] for e in debt_scores) / len(debt_scores)) if debt_scores else 0.0
            
            snapshot = MetricSnapshot(
                total_coupling_debt=float(total_debt),
                total_cycle_count=int(len(cycles)),
                total_violations=int(len(violations)),
                avg_instability=float(avg_inst),
                avg_hotspot_score=float(avg_hs)
            )
            
            generator = ContractGenerator(
                violations, 
                KNOWLEDGE_GRAPH, 
                snapshot, 
                debt_scores=debt_scores, 
                cycles=cycles, 
                hotspots=hotspots
            )
            contracts = generator.generate()
            
            # Clean and normalize path keys for JSON response
            cleaned_hotspots = []
            for h in hotspots:
                cleaned_hotspots.append({
                    "file": h["file"].replace("\\", "/"),
                    "hotspot_score": float(h["hotspot_score"]),
                    "complexity": int(h["complexity"]),
                    "coupling_debt": float(h["coupling_debt"]),
                    "bug_fix_count": int(h["bug_fix_count"])
                })
                
            self.send_json_response(200, {
                "success": True,
                "health_score": health_score,
                "hotspots": cleaned_hotspots,
                "circular_dependencies": [list(c) for c in cycles],
                "violations": [serialize_violation(v) for v in violations],
                "contracts": [serialize_contract(c) for c in contracts]
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
            repo_path = os.path.abspath(data.get("repo", ""))
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
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid payload"})
                return
            repo_path = os.path.abspath(data.get("repo", ""))
            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Not a directory: {repo_path}"})
                return

            codebase = analyzer.analyze_directory(repo_path)
            target_files = [k for k in codebase.keys() if k.endswith(".py")]
            risks = risk.evaluate_risks(codebase, target_files, repo_path=repo_path)
            risk_index = {r.file_path: r for r in risks}

            # Compute repo medians for the "Why?" context panel
            complexities = sorted(r.complexity for r in risks)
            couplings = sorted(int(r.coupling_score) for r in risks)
            mid = lambda lst: lst[len(lst) // 2] if lst else 0
            medians = {"complexity": mid(complexities), "coupling": mid(couplings)}

            raw_graph = analyzer.build_dependency_graph(codebase)

            enriched_nodes = []
            for node in raw_graph.get("nodes", []):
                nid = node.get("id", "")
                r = risk_index.get(nid)
                arch_role = getattr(r, "architectural_role", None)
                strat = getattr(r, "change_strategy", None)
                enriched_nodes.append({
                    "id": nid,
                    "label": os.path.basename(nid),
                    "level": r.level if r else "LOW",
                    "role": arch_role.value if hasattr(arch_role, "value") else "INTERNAL",
                    "role_display": arch_role.display_name if hasattr(arch_role, "display_name") else "Internal",
                    "complexity": r.complexity if r else 1,
                    "coupling": int(r.coupling_score) if r else 0,
                    "impact_score": round(r.impact_score, 2) if r else 0.0,
                    "strategy_display": strat.display_name if hasattr(strat, "display_name") else "Safe internal edits",
                })

            self.send_json_response(200, {
                "success": True,
                "nodes": enriched_nodes,
                "links": raw_graph.get("links", []),
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
            repo_path = os.path.abspath(data.get("repo", ""))
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
            if action not in ("audit", "recommend", "simulate"):
                self.send_json_response(400, {"error": f"Invalid or missing action '{action}'. Must be 'audit', 'recommend', or 'simulate'."})
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
                cycles = design_oracle.detect_circular_dependencies(codebase)
                globals_found = design_oracle.detect_global_mutations(codebase, repo_path)
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
                recommendations = design_oracle.recommend_patterns(codebase, intent)
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
                    
                res = design_oracle.simulate_future_coupling(codebase, src_file_norm, dest_file_norm)
                self.send_json_response(200, {
                    "success": True,
                    "simulation": res
                })
                
        except (ValueError, TypeError) as e:
            self.send_json_response(400, {"error": str(e)})
        except Exception as e:
            self.send_json_response(500, {
                "error": f"Internal Server Error: {e}",
                "traceback": traceback.format_exc()
            })

def serve():
    # Make sure static files folder exists
    os.makedirs(WEB_DIR, exist_ok=True)
    
    # Auto-open browser in a daemon thread
    if os.environ.get("ULTRON_NO_OPEN") != "1":
        import threading
        import time
        import webbrowser
        
        def open_browser():
            time.sleep(1.0)
            try:
                url = "http://localhost:" + str(PORT) + "/heatmap.html"
                webbrowser.open(url)
            except Exception as e:
                print(f"[*] Could not open browser automatically: {e}", file=sys.stderr)
                
        t = threading.Thread(target=open_browser, daemon=True)
        t.start()
    
    # Simple reuse port setup
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), UltronAPIHandler) as httpd:
        print(f"[+] Ultron Web Dashboard listening on http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[-] Shutting down Web Server.")

if __name__ == "__main__":
    serve()
