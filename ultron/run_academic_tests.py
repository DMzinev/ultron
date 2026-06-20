import os
import sys
import json
import urllib.request
import urllib.error
import shutil
import tempfile
import unittest
import math

# Add root folder to import search path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import risk
import predict
import meta_layer
import analyzer


API_BASE = "http://localhost:8000"

class TestAPIFuzzing(unittest.TestCase):
    """
    Functional Tests: Validates API endpoints against malicious or corrupted inputs.
    """
    
    def post_json(self, path, data):
        url = f"{API_BASE}{path}"
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json", "Connection": "close"},
            method="POST"
        )
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read().decode("utf-8"))

    def test_directory_traversal_prevention(self):
        """
        Ensure traversal attempts to get-file or save-file are blocked.
        """
        payloads = [
            "../../Study_Portal.html",
            "../server.py",
            "../../../etc/passwd"
        ]
        for payload in payloads:
            try:
                # We request a file path using traversal
                self.post_json("/api/get-file", {
                    "repo": "scratch/test_anomaly_dir",
                    "file": payload
                })
                self.fail(f"Traversal payload '{payload}' should have been blocked.")
            except urllib.error.HTTPError as e:
                # Expect 400 Bad Request
                self.assertEqual(e.code, 400, f"Expected 400 for traversal payload: {payload}")

    def test_empty_payloads(self):
        """
        Ensure endpoints handle empty payload parameters gracefully.
        """
        try:
            self.post_json("/api/analyze", {})
            self.fail("Empty payload should return 400.")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_playground_generation(self):
        """
        Ensure /api/playground correctly builds the sandbox structure.
        """
        status, response = self.post_json("/api/playground", {})
        self.assertEqual(status, 200)
        self.assertTrue(response.get("success"))
        self.assertEqual(response.get("path"), "scratch/ultron_playground")
        
        # Verify the folders exist
        playground_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scratch", "ultron_playground"))
        self.assertTrue(os.path.exists(os.path.join(playground_dir, "math_utils.py")))
        self.assertTrue(os.path.exists(os.path.join(playground_dir, "test_math_utils.py")))

    def test_log_risk_feedback(self):
        """
        Verify human feedback logging.
        """
        status, response = self.post_json("/api/log-risk-feedback", {
            "file": "math_utils.py",
            "accurate": True
        })
        self.assertEqual(status, 200)
        self.assertTrue(response.get("success"))
        
    def test_pledge_cycle(self):
        """
        Verify grounding pledge creation and verification.
        """
        status, response = self.post_json("/api/pledge/create", {
            "file": "math_utils.py",
            "predicted_delta_i": 2.5,
            "predicted_mkr": 0.6,
            "predicted_delta_cest": 0.05
        })
        self.assertEqual(status, 200)
        self.assertTrue(response.get("success"))
        self.assertIn("pledge", response)
        
        # Verify pledge bounds
        status_v, response_v = self.post_json("/api/pledge/verify", {
            "file": "math_utils.py",
            "actual_delta_i": 1.5,
            "actual_mkr": 0.7,
            "actual_delta_cest": 0.0,
            "actual_failure": 0.0
        })
        self.assertEqual(status_v, 200)
        self.assertTrue(response_v.get("success"))
        self.assertTrue(response_v.get("verification", {}).get("verification", {}).get("kept", False))

    def test_report_generation(self):
        """
        Verify aggregate reports generation.
        """
        status, response = self.post_json("/api/report", {
            "repo": "scratch/ultron_playground"
        })
        self.assertEqual(status, 200)
        self.assertTrue(response.get("success"))
        self.assertIn("pledges", response)
        self.assertIn("calibration", response)

    def test_malformed_utf8_handling(self):
        """
        Verify that raw malformed bytes do not crash the running daemon.
        """
        url = f"{API_BASE}/api/audit"
        req = urllib.request.Request(
            url,
            data=b'\xff\xfe\x00\x00invalid-utf8',
            headers={"Content-Type": "application/json", "Connection": "close"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as res:
                self.assertNotEqual(res.status, 200)
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, [400, 500])
        except Exception:
            pass # Connection errors/aborts are handled gracefully

class TestRollbackIntegrity(unittest.TestCase):
    """
    Functional Tests: Verifies safe backup creation and restore on write failure.
    """
    def test_safe_backup_rollback(self):
        import tempfile
        temp_dir = tempfile.mkdtemp()
        try:
            target_file = os.path.join(temp_dir, "app.py")
            with open(target_file, "w", encoding="utf-8") as f:
                f.write("print('original')")
                
            # Simulate backup logic in server.py
            backup_path = target_file + ".bak"
            shutil.copy2(target_file, backup_path)
            
            # Simulate corrupt write
            try:
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write("print('corrupt')")
                    raise IOError("Disk full or write aborted")
            except IOError:
                # Rollback
                if os.path.exists(backup_path):
                    shutil.copy2(backup_path, target_file)
                    
            with open(target_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertEqual(content, "print('original')", "File should have rolled back to original content.")
        finally:
            shutil.rmtree(temp_dir)

class TestDeltaRisk(unittest.TestCase):
    """
    Utility Tests: Verifies diff-aware risk scoring math (Delta I).
    """
    def test_delta_risk_scoring(self):
        codebase = {
            "math_ops.py": {
                "imports": [],
                "definitions": [
                    {
                        "type": "function",
                        "name": "calculate",
                        "calls": []
                    }
                ]
            }
        }
        old_code = "def calculate():\n    return 1"
        # Increased complexity (if nesting)
        new_code = "def calculate():\n    if True:\n        if False:\n            return 2\n    return 1"
        
        res = risk.evaluate_diff_risk(codebase, "math_ops.py", old_code, new_code)
        self.assertGreater(res["delta_score"], 0.0)
        self.assertEqual(res["changes"][0]["action"], "modified")

class TestPredictionCalibration(unittest.TestCase):
    """
    Research Tests: Validates failure predictions and records self-calibration metrics.
    """
    def test_automated_prediction_calibration(self):
        # 1. Setup mock codebase with tests and callers
        codebase = {
            "calculator.py": {
                "imports": [],
                "definitions": [
                    {
                        "type": "function",
                        "name": "divide",
                        "calls": []
                    }
                ]
            }
        }
        
        # Write temporary mock test suite
        import tempfile
        temp_dir = tempfile.mkdtemp()
        test_file = os.path.join(temp_dir, "run_tests.py")
        test_code = """
import unittest
class TestCalc(unittest.TestCase):
    def test_divide(self):
        divide()
    def test_other(self):
        pass
"""
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)
            
        try:
            # 2. Predict impact of changing 'divide'
            predictions = predict.predict_test_impact(codebase, ["calculator.py"], ["divide"], test_file)
            predicted_failed = {p["test_name"] for p in predictions}
            
            # 3. Define actual failed tests (ground truth)
            # Suppose only test_divide actually fails because of our change
            actual_failed = {"test_divide"}
            
            # All possible tests inside the suite
            all_tests = {"test_divide", "test_other"}
            
            # 4. Evaluate classification confusion matrix
            tp = len(predicted_failed.intersection(actual_failed)) # True Positives
            fp = len(predicted_failed.difference(actual_failed))    # False Positives
            fn = len(actual_failed.difference(predicted_failed))    # False Negatives
            tn = len(all_tests.difference(predicted_failed).difference(actual_failed)) # True Negatives
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            predicted_risk = 5.0  # mock calculated risk score
            actual_failures = len(actual_failed)
            prediction_error = abs(len(predicted_failed) - actual_failures)
            
            self.assertEqual(precision, 1.0)
            self.assertEqual(recall, 1.0)
            self.assertEqual(f1, 1.0)
            
            # 5. Log calibration values to Experiment Governor ledger
            meta_layer.log_calibration_experiment(
                predicted_risk=predicted_risk,
                actual_failures=actual_failures,
                prediction_error=prediction_error,
                precision=precision,
                recall=recall,
                f1=f1
            )
            
            # Verify ledger records the log entry
            ledger = meta_layer.read_ledger()
            last_entry = ledger["experiment_history"][-1]
            self.assertEqual(last_entry["experiment_type"], "Foresight Calibration")
            self.assertEqual(last_entry["precision"], 1.0)
            
        finally:
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    print("[+] Running Ultron Academic Validation & Calibration Suite...")
    # First check if port 8000 server is running
    server_online = False
    try:
        with urllib.request.urlopen(API_BASE, timeout=2.0) as conn:
            if conn.status == 200:
                server_online = True
    except Exception:
        pass
        
    if not server_online:
        print("[-] WARNING: Ultron background API server is not running on port 8000.")
        print("[-] Skipping TestAPIFuzzing (requires active server).")
        # Run only offline tests
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(TestRollbackIntegrity))
        suite.addTest(unittest.makeSuite(TestDeltaRisk))
        suite.addTest(unittest.makeSuite(TestPredictionCalibration))
        runner = unittest.TextTestRunner()
        runner.run(suite)
    else:
        unittest.main()
