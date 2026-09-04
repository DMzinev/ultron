"""
Ultron REST API — Graph & File Tree Route Mixin & Handlers
"""

import os
import sys
import json
import traceback
from typing import Any

from ultron.core import analyzer
from ultron.core import risk
from ultron.core import translate


class GraphRoutesMixin:
    """Provides dependency graph and file tree API endpoints for UltronAPIHandler."""

    def handle_dependency_graph(self):
        try:
            if hasattr(self, "get_request_data"):
                data = self.get_request_data()
            elif hasattr(self, "get_post_data"):
                data = self.get_post_data()
            else:
                data = {}

            if not isinstance(data, dict):
                self.send_json_response(400, {"error": "Invalid payload"})
                return
            repo = data.get("repo", "") or os.getcwd()
            repo_path = os.path.abspath(repo)
            if not os.path.isdir(repo_path):
                self.send_json_response(400, {"error": f"Not a directory: {repo_path}"})
                return

            granularity = str(data.get("granularity", "file")).lower().strip()
            if granularity not in ("file", "symbol"):
                granularity = "file"

            codebase = analyzer.analyze_directory(repo_path)
            target_files = [k for k in codebase.keys() if k.endswith(".py")] if isinstance(codebase, dict) else []
            risks = risk.evaluate_risks(codebase, target_files, repo_path=repo_path)
            risk_index = {r.file_path.replace('\\', '/'): r for r in risks}

            # Compute repo medians for the "Why?" context panel
            complexities = sorted(r.complexity for r in risks)
            couplings = sorted(int(r.coupling_score) for r in risks)
            mid = lambda lst: lst[len(lst) // 2] if lst else 0
            medians = {"complexity": mid(complexities), "coupling": mid(couplings)}

            raw_graph = analyzer.build_dependency_graph(codebase, granularity=granularity)

            # Cycle detection for file granularity
            cycle_files = set()
            cycle_edges = set()
            if granularity == "file":
                try:
                    from ultron.core.cycle_detector import CycleDetector
                    file_edges = [
                        {
                            "source": str(l.get("source", "")).replace('\\', '/'),
                            "target": str(l.get("target", "")).replace('\\', '/')
                        }
                        for l in raw_graph.get("links", [])
                    ]
                    detected_cycles = CycleDetector.find_all_cycles(edges=file_edges)
                    for c in detected_cycles:
                        nodes_in_c = [str(n).replace('\\', '/') for n in c.get("nodes", [])]
                        cycle_files.update(nodes_in_c)
                        for i in range(len(nodes_in_c)):
                            c_src = nodes_in_c[i]
                            c_tgt = nodes_in_c[(i + 1) % len(nodes_in_c)]
                            cycle_edges.add((c_src, c_tgt))
                except Exception as cyc_err:
                    sys.stderr.write(f"[Ultron] Warning: cycle detection in graph route failed: {cyc_err}\n")

            enriched_nodes = []
            for node in raw_graph.get("nodes", []):
                nid = node.get("id", "").replace('\\', '/')
                ntype = node.get("type", "file")
                r = risk_index.get(nid)
                arch_role = getattr(r, "architectural_role", None)
                strat = getattr(r, "change_strategy", None)
                pkg = os.path.dirname(nid).replace('\\', '/') or "(root)"
                coupling = int(r.coupling_score) if r else 0
                node_dict = {
                    "id": nid,
                    "label": os.path.basename(nid) if ntype == "file" else nid,
                    "type": ntype,
                    "level": r.level if r else "LOW",
                    "role": arch_role.value if hasattr(arch_role, "value") else "INTERNAL",
                    "role_display": arch_role.display_name if hasattr(arch_role, "display_name") else "Internal",
                    "complexity": r.complexity if r else 1,
                    "coupling": coupling,
                    "impact_score": round(r.impact_score, 2) if r else 0.0,
                    "strategy_display": strat.display_name if hasattr(strat, "display_name") else "Safe internal edits",
                    "package": pkg,
                    "blast_radius": coupling,
                    "in_cycle": nid in cycle_files,
                }
                enriched_nodes.append(node_dict)

            normalized_links = []
            for link in raw_graph.get("links", []):
                src = str(link.get("source", "")).replace('\\', '/')
                tgt = str(link.get("target", "")).replace('\\', '/')
                ltype = link.get("type", "import")
                in_cyc = (src, tgt) in cycle_edges
                normalized_links.append({
                    "source": src,
                    "target": tgt,
                    "type": ltype,
                    "in_cycle": in_cyc
                })

            self.send_json_response(200, {
                "success": True,
                "nodes": enriched_nodes,
                "links": normalized_links,
                "medians": medians,
            })
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_file_tree(self):
        try:
            data = self.get_request_data() if hasattr(self, "get_request_data") else self.get_post_data()
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
