"""
Ultron REST API — Agent, AI & Design Oracle Route Mixin & Handlers
"""

import os
import sys
import json
import traceback
import urllib.request
import urllib.error
import socket
from typing import Any, Dict, List
from dataclasses import asdict

from ultron.core import analyzer
from ultron.core import risk
from ultron.core import prompt
from ultron.interfaces.api.router import APIRouter
from ultron.core.system_query import SystemQueryEngine
from ultron.interfaces.api.routes.system_routes import get_or_build_system_model

try:
    from ultron.experimental import design_oracle
except ImportError:
    design_oracle = None


class AgentRoutesMixin:
    """Provides all agent, AI push, context brief, and design oracle API endpoints."""

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

            target_str = f" Target file: {target_file}." if target_file else ""
            h_score = canonical_brief.get("health_score", 80.0)
            
            claude_snippet = f'claude -p "Analyze repository \'{repo_name}\' (Health Score: {h_score}/100).{target_str} Address top risk boundary rules and maintain architectural integrity."'
            
            codex_brief = f"# OpenAI Codex System Context Brief\nRepository: {repo_name}\nHealth Score: {h_score}/100\nTotal Files: {canonical_brief.get('total_files', 0)}\n{f'Target Entity: {target_file}' if target_file else ''}\n\n## Architectural Directives & Rules\n1. Preserves public API contracts in interfaces/api.\n2. Route logic through Repository Knowledge Model (RKM).\n3. Do not modify core analyzer models without backward compatibility review.\n\n## Top Active Risk Signals\n"
            for r in canonical_brief.get("top_risks", []):
                codex_brief += f"- **{r.get('entity_id')}** ({r.get('priority')} Priority, Reasons: {', '.join(r.get('reasons', []))})\n"
                
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
        try:
            data = self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"status": "error", "message": "Invalid JSON body payload."})
                return

            repo = data.get("repo", "")
            target_file = str(data.get("target_file", "")).strip()
            persona = str(data.get("persona", "developer")).strip().lower()

            repo_path = os.path.abspath(repo) if repo and repo.strip() else self.get_repo_root_path()
            
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
            
            proxy_url = "http://127.0.0.1:10531/v1/chat/completions"
            payload = json.dumps({
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are Ultron AI, an elite architectural refactoring engine."},
                    {"role": "user", "content": prompt_text}
                ],
                "temperature": 0.3
            }).encode("utf-8")

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
                pass

            if not ai_response_text:
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

    def handle_v1_ai_critique(self):
        try:
            data = self.get_request_data() if hasattr(self, "get_request_data") else self.get_post_data()
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
                
                from ultron.core.rkm.risk_intelligence import compute_risk_profile
                risk_profile = compute_risk_profile(entity_id, complexity=complexity, coupling_fanout=coupling)
                
                from ultron.core.rkm.policy_engine import evaluate_policy
                decision = evaluate_policy(risk_profile, business_criticality="DEFAULT")
                
                from ultron.core.translate import translate_decision, translate_decision_to_personas
                comm_personas = translate_decision_to_personas(decision)
                
                reasons_str = ", ".join(decision.reason_codes) if decision.reason_codes else "HIGH_RISK"
                trust_chain = {
                    "plain_label": f"High risk detected in {entity_id}: Priority {decision.priority}",
                    "entity": entity_id,
                    "rule_plain_name": "Code is too complex or coupled to modify safely",
                    "rule_technical_name": f"RKM-POLICY-{decision.policy_version}",
                    "severity": decision.priority,
                    "confidence": risk_profile.confidence_vector.get("overall", 0.65),
                    "signals": risk_profile.confidence_vector.get("signals_block", {}),
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


# Pre-existing route registered with APIRouter
@APIRouter.register("/api/v1/agent/context/query", "POST")
def handle_v1_agent_query(handler: Any) -> None:
    """
    POST /api/v1/agent/context/query — Engineering Intelligence Query Protocol.
    """
    post_data = {}
    if hasattr(handler, "get_post_data"):
        try:
            post_data = handler.get_post_data()
            if not isinstance(post_data, dict):
                handler.send_response(400)
                handler.send_header("Content-Type", "application/json; charset=utf-8")
                handler.end_headers()
                handler.wfile.write(json.dumps({"success": False, "data": None, "error": "Invalid JSON body format. Expected JSON object."}).encode("utf-8"))
                return
        except Exception as e:
            handler.send_response(400)
            handler.send_header("Content-Type", "application/json; charset=utf-8")
            handler.end_headers()
            handler.wfile.write(json.dumps({"success": False, "data": None, "error": f"Invalid JSON payload: {e}"}).encode("utf-8"))
            return

    query_type = post_data.get("query_type")
    target_entity = post_data.get("target_entity") or post_data.get("entity_id") or post_data.get("target") or post_data.get("file_path")
    try:
        depth = int(post_data.get("depth", 2))
    except (ValueError, TypeError):
        depth = 2

    supported_types = {
        "IMPACT_ANALYSIS", "DEPENDENCIES", "DEPENDENTS",
        "CALLERS", "TEST_COVERAGE", "RISK_EXPLANATION", "CHANGE_CONTEXT"
    }

    if not query_type or query_type not in supported_types:
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({
            "success": False,
            "data": None,
            "error": f"Invalid or missing 'query_type'. Supported types: {sorted(list(supported_types))}"
        }).encode("utf-8"))
        return

    if not target_entity or not isinstance(target_entity, str) or not target_entity.strip() or '\x00' in target_entity:
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({
            "success": False,
            "data": None,
            "error": "Field 'target_entity' or 'entity_id' or 'target' is required and must be a non-empty string"
        }).encode("utf-8"))
        return

    target_entity = target_entity.strip()

    manager = get_or_build_system_model(handler)
    query_engine = SystemQueryEngine(manager.graph)
    target_node = query_engine.find_node(target_entity)

    if not target_node:
        handler.send_response(404)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({
            "success": False,
            "data": None,
            "error": f"Target entity '{target_entity}' not found in SystemModel"
        }).encode("utf-8"))
        return

    nodes: List[Dict[str, Any]] = [target_node.to_dict()]
    edges: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []

    if query_type in ("IMPACT_ANALYSIS", "CHANGE_CONTEXT"):
        blast = query_engine.trace_blast_radius(target_entity, max_depth=depth)
        for dep in blast.get("affected_nodes", []):
            if dep != target_entity:
                d_node = query_engine.find_node(dep)
                if d_node:
                    nodes.append(d_node.to_dict())
        for edge in blast.get("trace_path", []):
            edges.append(edge)
        evidence.append({
            "type": "blast_radius",
            "metric": "affected_count",
            "value": len(blast.get("affected_nodes", [])),
            "description": f"Blast radius traces {len(blast.get('affected_nodes', []))} affected nodes to depth {depth}"
        })

    elif query_type == "DEPENDENCIES":
        deps = query_engine.get_downstream_dependents(target_entity)
        for d in deps:
            d_node = query_engine.find_node(d)
            if d_node:
                nodes.append(d_node.to_dict())
            edges.append({"source": target_entity, "target": d, "relation": "depends_on"})

    elif query_type in ("DEPENDENTS", "CALLERS"):
        callers = query_engine.get_upstream_callers(target_entity)
        for c in callers:
            c_node = query_engine.find_node(c)
            if c_node:
                nodes.append(c_node.to_dict())
            edges.append({"source": c, "target": target_entity, "relation": "calls"})

    elif query_type == "TEST_COVERAGE":
        evidence.append({
            "type": "coverage",
            "metric": "line_coverage",
            "value": None,
            "description": "Dynamic coverage telemetry is pending active test run"
        })

    elif query_type == "RISK_EXPLANATION":
        evidence.append({
            "type": "risk_explanation",
            "metric": "architectural_role",
            "value": target_node.architectural_role.value if hasattr(target_node.architectural_role, "value") else str(target_node.architectural_role),
            "description": f"Node role: {target_node.architectural_role}, change strategy: {target_node.change_strategy}"
        })

    payload = {
        "success": True,
        "data": {
            "query_type": query_type,
            "target": target_node.to_dict(),
            "nodes": nodes,
            "edges": edges,
            "evidence": evidence
        },
        "error": None
    }
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
