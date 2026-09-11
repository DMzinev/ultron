"""
Ultron REST API — Analysis Route Mixin & Handlers
"""

import os
import sys
import json
import traceback
import threading
import uuid
from typing import Any

from ultron.core import analyzer
from ultron.core import risk
from ultron.core import predict
from ultron.core.telemetry import PerformanceTimer, get_performance_summary, reset_performance_summary
from ultron.interfaces.api.state import (
    LAST_ANALYSIS,
    ACTIVE_JOB,
    coerce_file_list,
    CONFIG_FILE,
)


class AnalysisRoutesMixin:
    """Provides all analysis-related API endpoints for UltronAPIHandler."""

    def _build_analysis_payload(self, repo_dir: str, force: bool = True) -> dict:
        """Builds a unified analysis payload dictionary containing snapshot_id, model_hash, identity, dependency_graph, risks, and stats."""
        from ultron.core.pipeline.orchestrator import analyze_repository
        from ultron.core import analyzer
        from ultron.core import risk
        
        abs_repo = os.path.abspath(repo_dir)
        bundle = analyze_repository(abs_repo, force=force)
        codebase = getattr(bundle, "codebase", None)
        if not codebase:
            codebase = analyzer.analyze_directory(abs_repo)
        
        risks_raw = getattr(bundle, "risks", None)
        if not risks_raw:
            risks_raw = risk.evaluate_risks(codebase, list(codebase.keys()), repo_path=abs_repo)
            
        risks = [r.to_dict() if hasattr(r, "to_dict") else r for r in risks_raw]
        
        for r in risks:
            if isinstance(r, dict):
                imp = r.get("impact_score")
                if imp is None or str(imp).lower() == "nan":
                    r["impact_score"] = 0.0
                comp = r.get("complexity")
                if comp is None or str(comp).lower() == "nan":
                    r["complexity"] = 1

        total_files = len(codebase)
        total_definitions = sum(len(c.get("definitions", [])) for c in codebase.values())
        high_count = sum(1 for r in risks if (r.get("level") == "HIGH" if isinstance(r, dict) else False))

        dependency_graph = analyzer.build_dependency_graph(codebase)

        model_hash = getattr(bundle, "content_hash", "") or getattr(bundle, "repo_fingerprint", "") or "default_hash"
        snapshot_id = getattr(bundle, "snapshot_id", "") or f"snap-{model_hash[:16]}"

        return {
            "snapshot_id": snapshot_id,
            "model_hash": model_hash,
            "identity": {
                "repo_path": abs_repo,
                "repository_uuid": getattr(bundle, "repo_uuid", str(bundle)),
                "repo_fingerprint": getattr(bundle, "repo_fingerprint", ""),
            },
            "dependency_graph": dependency_graph,
            "risks": risks,
            "stats": {
                "total_files": total_files,
                "total_definitions": total_definitions,
                "high_risks": high_count,
            }
        }

    def handle_analyze(self):
        try:
            data = self.get_request_data() if hasattr(self, "get_request_data") else self.get_post_data()
            if not isinstance(data, dict):
                self.send_json_response(400, {"status": "error", "message": "Invalid JSON body payload.", "error": "Invalid JSON body payload."})
                return
            repo = str(data.get("repo", "")).strip()
            # --- Path security guard (Fail-Closed Policy) ---
            if "\0" in repo:
                msg = "Invalid repository path: null byte detected."
                self.send_json_response(400, {"status": "error", "message": msg, "error": msg})
                return
            if repo:
                stem = os.path.splitext(os.path.basename(repo))[0].rstrip(":").upper()
                from ultron.interfaces.api.browse_folder import WINDOWS_RESERVED_NAMES
                if stem in WINDOWS_RESERVED_NAMES:
                    msg = f"Invalid repository path: reserved device name '{stem}'."
                    self.send_json_response(400, {"status": "error", "message": msg, "error": msg})
                    return
            if not repo:
                repo_path = self.get_repo_root_path()
            else:
                repo_path = os.path.abspath(repo)

            if repo_path in ("/", "\\") or os.path.dirname(repo_path) == repo_path:
                msg = "Analyzing system root filesystem is strictly prohibited."
                self.send_json_response(400, {"status": "error", "message": msg, "error": msg})
                return

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

            intent_matched = True
            if intent and not target_files and not risks:
                intent_matched = False
                risks = risk.evaluate_risks(codebase, [], "", repo_path=repo_path)
            
            total_files = len(codebase)
            total_definitions = sum(len(c.get("definitions", [])) for c in codebase.values())
            
            churn_active = any(
                (r.to_dict().get("churn", {}).get("status") == "active") if hasattr(r, "to_dict")
                else (isinstance(r, dict) and r.get("churn", {}).get("status") == "active")
                for r in risks
            )
            coverage_active = any(
                (r.to_dict().get("signals", {}).get("coverage", {}).get("status") == "active") if hasattr(r, "to_dict")
                else False
                for r in risks
            )
            
            resp_payload = {
                "status": "success",
                "success": True,
                "stats": {
                    "total_files": total_files,
                    "total_definitions": total_definitions,
                    "signals": {
                        "ast":      {"status": "active",                                      "weight": 0.35},
                        "coupling": {"status": "active",                                      "weight": 0.25},
                        "churn":    {"status": "active" if churn_active else "unavailable",    "weight": 0.15},
                        "coverage": {"status": "active" if coverage_active else "unavailable", "weight": 0.25},
                    }
                },
                "intent": {
                    "text": intent,
                    "matched": intent_matched,
                    "message": "" if intent_matched else (
                        f"No files matched \"{intent}\". Showing the whole repository instead."
                    )
                },
                "risks": [r.to_dict() for r in risks],
            }
            if isinstance(data, dict) and (data.get("include_recommendations") or data.get("recommendations")):
                resp_payload["recommendations"] = []
            self.send_json_response(200, resp_payload)
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
            from ultron.core.language_adapter import JavaScriptLanguageAdapter
            from ultron.core.system_model import SystemNodeType
            js_adapter = JavaScriptLanguageAdapter()
            js_graph = js_adapter.parse_repository(repo_path)
            js_modules = [n for n in js_graph.nodes.values() if n.type in (SystemNodeType.MODULE, SystemNodeType.TEST)]

            if not codebase and not js_modules:
                self.send_json_response(200, {
                    "status": "success",
                    "state": "analysis_empty",
                    "repo": repo_block,
                    "message": "No Python or JavaScript files found here. Pick a folder that contains source code.",
                    "stats": {"total_files": 0, "total_definitions": 0, "high": 0, "medium": 0, "low": 0},
                    "health": {"score": None, "source": "none", "explanation": "Nothing to measure yet."},
                    "intent": {"text": intent, "matched": True, "message": ""},
                    "risks": [],
                    "memory": self._memory_snapshot(repo_path)
                })
                return

            risks = []
            if codebase:
                risks = risk.evaluate_risks(codebase, target_files, intent, repo_path=repo_path)
            intent_matched = True
            if intent and not target_files and not risks and codebase:
                intent_matched = False
                risks = risk.evaluate_risks(codebase, [], "", repo_path=repo_path)

            js_risks = []
            for jn in js_modules:
                cplx = jn.facts.get("complexity", 1)
                fanout = len(js_graph.get_dependencies(jn.id)) + len(js_graph.get_dependents(jn.id))
                impact = round(min(10.0, cplx * 0.4 + fanout * 0.5), 2)
                level = "LOW" if cplx < 5 else ("MEDIUM" if cplx < 10 else "HIGH")
                js_risk_item = {
                    "file": jn.file_path,
                    "file_path": jn.file_path,
                    "filepath": os.path.basename(jn.file_path),
                    "impact_score": impact,
                    "coupling_score": float(fanout),
                    "coupling": float(fanout),
                    "mk_r": 1.0,
                    "mkr": 1.0,
                    "delta_cest": 0.0,
                    "confidence": 0.35,
                    "tier": "PROTOTYPE",
                    "language": jn.facts.get("language", "javascript"),
                    "level": level,
                    "boundary_type": "Internal",
                    "architectural_role": "EXPERIMENTAL",
                    "change_strategy": "SAFE_EDIT",
                    "change_strategy_display": "Safe internal edits",
                    "complexity": cplx,
                    "mitigation": "Prototype JS/TS adapter: regex-extracted dependencies and branching keyword complexity proxy. Tier: PROTOTYPE (confidence 0.35).",
                    "callers": [],
                    "changes": [],
                    "churn": {"commits": 0, "authors": 0, "bug_fixes": 0, "multiplier": 1.0, "status": "unavailable"},
                    "signals": {
                        "ast": {"status": "active", "weight": 0.35, "tier": "PROTOTYPE", "confidence": 0.35},
                        "coupling": {"status": "active", "weight": 0.25, "tier": "PROTOTYPE", "confidence": 0.35},
                        "churn": {"status": "unavailable", "weight": 0.15, "tier": "INFERRED"},
                        "coverage": {"status": "unavailable", "weight": 0.25, "tier": "VERIFIED"}
                    }
                }
                js_risks.append(js_risk_item)

            all_risks = list(risks) + js_risks
            ranked = sorted(
                all_risks,
                key=lambda r: getattr(r, "impact_score", 0.0) if hasattr(r, "impact_score") else r.get("impact_score", 0.0),
                reverse=True
            )
            levels = [
                getattr(r, "level", "LOW") if hasattr(r, "level") else r.get("level", "LOW")
                for r in ranked
            ]
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

            risks_serialized = [(r.to_dict() if hasattr(r, "to_dict") else dict(r)) for r in ranked]

            js_def_count = sum(
                len([n for n in js_graph.nodes.values() if n.file_path == jn.file_path and n.type in (SystemNodeType.FUNCTION, SystemNodeType.CLASS)])
                for jn in js_modules
            )
            js_count = len([n for n in js_modules if n.facts.get("language") == "javascript"])
            ts_count = len([n for n in js_modules if n.facts.get("language") == "typescript"])

            languages_stat = {"python": len(codebase)}
            if js_count > 0:
                languages_stat["javascript"] = js_count
            if ts_count > 0:
                languages_stat["typescript"] = ts_count

            stats_payload = {
                "total_files": len(codebase) + len(js_modules),
                "total_definitions": sum(len(c.get("definitions", [])) for c in codebase.values()) + js_def_count,
                "high": high,
                "medium": medium,
                "low": low,
                "languages": languages_stat,
                "signals": (risks_serialized[0].get("signals") if risks_serialized else {
                    "ast":      {"status": "active",      "weight": 0.35},
                    "coupling": {"status": "active",      "weight": 0.25},
                    "churn":    {"status": "unavailable", "weight": 0.15},
                    "coverage": {"status": "unavailable", "weight": 0.25},
                })
            }

            self.send_json_response(200, {
                "status": "success",
                "state": "ok",
                "repo": repo_block,
                "stats": stats_payload,
                "health": health,
                "intent": {
                    "text": intent,
                    "matched": intent_matched,
                    "message": "" if intent_matched else f"No files matched \"{intent}\". Showing the whole repository instead."
                },
                "risks": risks_serialized,
                "memory": memory
            })
        except PermissionError as e:
            self.send_json_response(400, {"status": "error", "message": f"Permission denied: {e}"})
        except Exception as e:
            self.send_json_response(500, {"status": "error", "message": str(e)})

    def handle_v1_progress(self):
        global ACTIVE_JOB
        self.send_json_response(200, {
            "status": ACTIVE_JOB["status"],
            "progress_step": ACTIVE_JOB["progress_step"],
            "error": ACTIVE_JOB["error"],
            "job_id": ACTIVE_JOB["job_id"]
        })


    def handle_v1_analyze(self):
        data = self.get_request_data() if hasattr(self, "get_request_data") else self.get_post_data()
        if data is None:
            self.send_json_response(400, None, "Invalid or corrupted JSON body")
            return
        if isinstance(data, dict) and "repo" in data and not data.get("repo"):
            self.send_json_response(400, None, "Repository path string must not be empty.")
            return
        # --- Path security guards (Fail-Closed Policy) ---
        if isinstance(data, dict) and data.get("repo"):
            raw_repo = str(data["repo"])
            if "\0" in raw_repo:
                self.send_json_response(400, None, "Invalid repository path: null byte detected.")
                return
            stem = os.path.splitext(os.path.basename(raw_repo))[0].rstrip(":").upper()
            from ultron.interfaces.api.browse_folder import WINDOWS_RESERVED_NAMES
            if stem in WINDOWS_RESERVED_NAMES:
                self.send_json_response(400, None, f"Invalid repository path: reserved device name '{stem}'.")
                return
            norm_p = os.path.normpath(os.path.abspath(raw_repo))
            # Root filesystem prohibition (mirrors handle_analyze)
            if norm_p in ("/", "\\") or os.path.dirname(norm_p) == norm_p:
                self.send_json_response(400, None, "Analyzing system root filesystem is strictly prohibited.")
                return

        global ACTIVE_JOB
        if ACTIVE_JOB["status"] == "running":
            self.send_json_response(400, {"error": "Analysis is already running"})
            return

        body = data if isinstance(data, dict) else {}
        requested_repo = str(body.get("repo", "")).strip() if isinstance(body, dict) else ""
        repo_root = os.path.abspath(requested_repo) if requested_repo else self.get_repo_root_path()
        if not os.path.isdir(repo_root):
            self.send_json_response(400, {"error": f"Repository path '{repo_root}' is not a directory."})
            return

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


# Backward-compatible function delegates
def handle_v1_analyze(handler: Any) -> None:
    """Delegates to handler instance method."""
    data = handler.get_request_data() if hasattr(handler, "get_request_data") else handler.get_post_data()
    if data is None:
        handler.send_json_response(400, None, "Invalid or corrupted JSON body")
        return
    if isinstance(data, dict) and "repo" in data and not data.get("repo"):
        handler.send_json_response(400, None, "Repository path string must not be empty.")
        return
    # --- Path security guards (Fail-Closed Policy) ---
    if isinstance(data, dict) and data.get("repo"):
        raw_repo = str(data["repo"])
        if "\0" in raw_repo:
            handler.send_json_response(400, None, "Invalid repository path: null byte detected.")
            return
        stem = os.path.splitext(os.path.basename(raw_repo))[0].rstrip(":").upper()
        from ultron.interfaces.api.browse_folder import WINDOWS_RESERVED_NAMES
        if stem in WINDOWS_RESERVED_NAMES:
            handler.send_json_response(400, None, f"Invalid repository path: reserved device name '{stem}'.")
            return
        norm_p = os.path.normpath(os.path.abspath(raw_repo))
        if norm_p in ("/", "\\") or os.path.dirname(norm_p) == norm_p:
            handler.send_json_response(400, None, "Analyzing system root filesystem is strictly prohibited.")
            return
    handler.handle_v1_analyze()


def handle_v1_summary(handler: Any) -> None:
    """Delegates to handler instance method."""
    handler.handle_v1_summary()
