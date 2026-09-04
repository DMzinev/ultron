"""
Ultron REST API — Audit, Report, Calibration & Playground Route Mixin
"""

import os
import sys
import json
import time
import traceback
from typing import Any

from ultron.core import classifier
from ultron.core import pledge
from ultron.core import analyzer
from ultron.core import risk


class AuditRoutesMixin:
    """Provides audit, report, calibration, pledge and playground API endpoints."""

    def measure_entity(self, entity):
        """
        Resolve `entity` to a real file inside the repository and measure it.
        Returns (complexity, coupling_fanout, error_response).
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
            playground_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scratch", "ultron_playground"))
            os.makedirs(playground_dir, exist_ok=True)
            
            math_utils_code = """# Ultron Playground Sample Module
import time

def add_elements(a, b):
    return a + b

def complex_operation(x, y, op="add"):
    if op == "add":
        return x + y
    elif op == "subtract":
        return x - y
    else:
        result = 0
        for i in range(abs(int(x))):
            result += y
        return result

def highly_coupled_calculator(val1, val2, operation):
    print(f"Executing coupled calculator on {val1} and {val2} using {operation}")
    step1 = add_elements(val1, 10)
    step2 = complex_operation(step1, val2, op=operation)
    return step2
"""
            with open(os.path.join(playground_dir, "math_utils.py"), "w", encoding="utf-8") as f:
                f.write(math_utils_code)
                
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
                
            synapse_mutator_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "synapse_project", "synapse_mutator"))
            os.makedirs(synapse_mutator_dir, exist_ok=True)
            ledger_file = os.path.join(synapse_mutator_dir, "ledger.jsonl")
            
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
            _root = os.path.abspath(os.path.join(_dir, "..", "..", ".."))
            feedback_path = os.path.join(_root, "ultron", "meta", "human_feedback.jsonl")
            os.makedirs(os.path.dirname(feedback_path), exist_ok=True)
            
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
            _root = os.path.abspath(os.path.join(_dir, "..", "..", ".."))
            log_path = os.path.join(_root, "ultron", "meta", "experiment_log.jsonl")
            
            total_pledges = 0
            kept_pledges = 0
            errors = []
            
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
                        
                        if "verification" in entry:
                            total_pledges += 1
                            if entry["verification"].get("kept", False):
                                kept_pledges += 1
                                
                        pred = entry.get("prediction", {}) or {}
                        act = entry.get("actual", {}) or {}
                        err = entry.get("error", {}) or {}
                        
                        pred_risk = pred.get("predicted_risk")
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
                            
            pledge_success_rate = (kept_pledges / total_pledges) if total_pledges > 0 else 1.0
            mean_error = (sum(errors) / len(errors)) if errors else 0.0
            
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
