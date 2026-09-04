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

    def handle_analyze(self):
        try:
            data = self.get_request_data() if hasattr(self, "get_request_data") else self.get_post_data()
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

            intent_matched = True
            if intent and not target_files and not risks:
                intent_matched = False
                risks = risk.evaluate_risks(codebase, [], "", repo_path=repo_path)
            
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
            LAST_ANALYSIS["file_path"] = filepath
            LAST_ANALYSIS["delta_i"] = res.impact_score
            LAST_ANALYSIS["mkr"] = res.mk_r
            LAST_ANALYSIS["delta_cest"] = res.delta_cest
            
            self.send_json_response(200, {
                "success": True,
                "diff_risk": res.to_dict()
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

    def handle_v1_history(self):
        self.handle_v1_runs()

    def handle_v1_analyze(self):
        data = self.get_request_data() if hasattr(self, "get_request_data") else self.get_post_data()
        if data is None:
            self.send_json_response(400, None, "Invalid or corrupted JSON body")
            return
        if isinstance(data, dict) and "repo" in data and not data.get("repo"):
            self.send_json_response(400, None, "Repository path string must not be empty.")
            return
        if isinstance(data, dict) and data.get("repo"):
            norm_p = os.path.normpath(os.path.abspath(data["repo"]))
            if not os.path.exists(norm_p):
                self.send_json_response(400, None, f"Repository path does not exist: '{data['repo']}'")
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
    if isinstance(data, dict) and data.get("repo"):
        norm_p = os.path.normpath(os.path.abspath(data["repo"]))
        if not os.path.exists(norm_p):
            handler.send_json_response(400, None, f"Repository path does not exist: '{data['repo']}'")
            return
    handler.handle_v1_analyze()


def handle_v1_summary(handler: Any) -> None:
    """Delegates to handler instance method."""
    handler.handle_v1_summary()
