"""
Ultron Unit Tests for Bug Prediction Validation Engine
"""
import unittest
import os
import tempfile
import shutil
from unittest.mock import patch
from ultron.core.rkm.bug_prediction import BugPredictionValidator

class TestBugPrediction(unittest.TestCase):
    def test_evaluate_predictions_non_git_dir(self):
        temp_dir = tempfile.mkdtemp()
        try:
            res = BugPredictionValidator.evaluate_predictions(["foo.py"], temp_dir)
            self.assertEqual(res["status"], "inactive")
            self.assertEqual(res["precision"], 0.0)
            self.assertEqual(res["recall"], 0.0)
            self.assertEqual(res["f1_score"], 0.0)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_evaluate_predictions_mock_data(self):
        with patch.object(BugPredictionValidator, "extract_bug_fix_files", return_value={"ultron/core/analyzer.py", "ultron/interfaces/server.py"}):
            res = BugPredictionValidator.evaluate_predictions(["ultron/core/analyzer.py"], ".")
            self.assertEqual(res["status"], "active")
            self.assertEqual(res["true_positives"], 1)
            self.assertGreater(res["precision"], 0.0)
            self.assertGreater(res["recall"], 0.0)

if __name__ == "__main__":
    unittest.main()
