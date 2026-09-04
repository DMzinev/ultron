import os
import json
import tempfile
import unittest
import importlib.util
from unittest.mock import patch, MagicMock

# Check if optional skill script consult_plan_api.py exists
script_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", ".agents", "skills", "openai-plan-reviewer", "scripts", "consult_plan_api.py"
))
script_exists = os.path.exists(script_path)

if script_exists:
    spec = importlib.util.spec_from_file_location("consult_plan_api", script_path)
    consult_plan_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(consult_plan_module)
    check_proxy_online = consult_plan_module.check_proxy_online
    review_plan = consult_plan_module.review_plan
else:
    check_proxy_online = None
    review_plan = None


@unittest.skipUnless(script_exists, "Optional skill script consult_plan_api.py not found on disk")
class TestOpenAIPlanReviewer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.plan_path = os.path.join(self.temp_dir.name, "implementation_plan.md")
        with open(self.plan_path, "w", encoding="utf-8") as f:
            f.write("# Sample Plan\n\n1. Step One\n2. Step Two")

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("urllib.request.urlopen")
    def test_proxy_offline_fallback(self, mock_urlopen):
        """Verify that offline proxy triggers a clean fallback result without raising exceptions."""
        mock_urlopen.side_effect = Exception("Connection refused")

        result = review_plan(self.plan_path, base_url="http://127.0.0.1:10531/v1")
        
        self.assertEqual(result["status"], "offline")
        self.assertIn("is offline", result["message"])

    @patch("urllib.request.urlopen")
    def test_successful_plan_review(self, mock_urlopen):
        """Verify successful multi-turn plan review parsing."""
        # Mock models check response
        mock_models_resp = MagicMock()
        mock_models_resp.status = 200
        mock_models_resp.__enter__.return_value = mock_models_resp

        # Mock completion response
        mock_completion_resp = MagicMock()
        mock_completion_data = {
            "choices": [{"message": {"content": "Plan looks solid. Watch out for edge cases."}}]
        }
        json_bytes = json.dumps(mock_completion_data).encode("utf-8")
        mock_completion_resp.read.side_effect = [json_bytes, b"", json_bytes, b""]
        mock_completion_resp.__enter__.return_value = mock_completion_resp

        # Configure urlopen side effect: 1st call is check_proxy_online, subsequent are post_chat_completion
        mock_urlopen.side_effect = [mock_models_resp, mock_completion_resp, mock_completion_resp]

        result = review_plan(self.plan_path, turns=2, base_url="http://127.0.0.1:10531/v1")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["turns_completed"], 2)
        self.assertEqual(len(result["reviews"]), 2)
        self.assertIn("Plan looks solid", result["reviews"][0]["feedback"])

    @patch("urllib.request.urlopen")
    def test_convergence_early_stopping(self, mock_urlopen):
        """Verify early termination when model returns 'no blocking issues'."""
        mock_models_resp = MagicMock()
        mock_models_resp.status = 200
        mock_models_resp.__enter__.return_value = mock_models_resp

        mock_completion_resp = MagicMock()
        mock_completion_data = {
            "choices": [{"message": {"content": "Plan reviewed: No blocking issues found."}}]
        }
        json_bytes = json.dumps(mock_completion_data).encode("utf-8")
        mock_completion_resp.read.side_effect = [json_bytes, b""]
        mock_completion_resp.__enter__.return_value = mock_completion_resp

        mock_urlopen.side_effect = [mock_models_resp, mock_completion_resp, mock_completion_resp]

        result = review_plan(self.plan_path, turns=5, base_url="http://127.0.0.1:10531/v1")

        self.assertEqual(result["status"], "success")
        # Should stop on turn 1 due to convergence keyword
        self.assertEqual(result["turns_completed"], 1)

    def test_missing_plan_file(self):
        """Verify error status when plan path does not exist."""
        result = review_plan("nonexistent_plan.md", base_url="http://127.0.0.1:10531/v1")
        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["message"])

    def test_is_approved_negation_window(self):
        """Verify is_approved handles negations accurately without false positives."""
        is_approved_fn = consult_plan_module.is_approved
        
        # Affirmative cases -> True
        self.assertTrue(is_approved_fn("The plan is ready to approve."))
        self.assertTrue(is_approved_fn("There are no blocking issues found."))
        self.assertTrue(is_approved_fn("Plan is solid and looks good to approve."))
        
        # Negated cases -> False
        self.assertFalse(is_approved_fn("The plan is NOT ready to approve until step 2 is fixed."))
        self.assertFalse(is_approved_fn("We can't say it is ready to approve yet."))
        self.assertFalse(is_approved_fn("Never ready to approve in current state."))
        self.assertFalse(is_approved_fn("There are NOT no blocking issues."))


if __name__ == "__main__":
    unittest.main()
