"""
Unit Test Suite for SafetyEvaluator
"""

import unittest
from ultron.core.safety_evaluator import SafetyEvaluator, SafetyReport


class TestSafetyEvaluator(unittest.TestCase):
    def test_all_passing_greenlight(self):
        test_res = {"passed": True, "passed_count": 293, "failed_count": 0}
        report = SafetyEvaluator.evaluate(
            test_results=test_res,
            modified_files=["ultron/core/agent_context_builder.py"],
            boundary_constraints=["Preserve public API signatures", "Do not modify payments"],
            acceptance_criteria=["Zero regressions"],
            cycle_count=0
        )
        self.assertTrue(report.safe_to_continue)
        self.assertEqual(report.badge, "CONTINUE BUILDING")
        self.assertEqual(len(report.recommendations), 0)

    def test_failing_tests_pauses_build(self):
        test_res = {"passed": False, "passed_count": 290, "failed_count": 3}
        report = SafetyEvaluator.evaluate(
            test_results=test_res,
            modified_files=["ultron/core/foo.py"]
        )
        self.assertFalse(report.safe_to_continue)
        self.assertEqual(report.badge, "PAUSE & REVIEW")
        self.assertTrue(any("failing test" in rec.lower() for rec in report.recommendations))

    def test_boundary_violation_detection(self):
        test_res = {"passed": True, "passed_count": 10, "failed_count": 0}
        report = SafetyEvaluator.evaluate(
            test_results=test_res,
            modified_files=["ultron/payments/stripe_client.py", "ultron/core/utils.py"],
            boundary_constraints=["Do not modify payments", "Preserve existing models"]
        )
        self.assertFalse(report.safe_to_continue)
        self.assertEqual(report.badge, "PAUSE & REVIEW")
        self.assertTrue(any(c["severity"] == "BLOCKING" for c in report.checks if not c["passed"]))

    def test_circular_dependency_blocking(self):
        test_res = {"passed": True, "passed_count": 10, "failed_count": 0}
        report = SafetyEvaluator.evaluate(
            test_results=test_res,
            cycle_count=2
        )
        self.assertFalse(report.safe_to_continue)
        self.assertEqual(report.badge, "PAUSE & REVIEW")

    def test_missing_tests_blocks_continuation(self):
        report = SafetyEvaluator.evaluate(test_results=None)
        self.assertFalse(report.safe_to_continue)  # Missing evidence != Safe
        self.assertEqual(report.badge, "PAUSE & REVIEW")
        self.assertIn("TESTS_UNEXECUTED", report.reason_codes)
        self.assertTrue(any(c["name"] == "Test Suite Execution" and not c["passed"] for c in report.checks))


if __name__ == "__main__":
    unittest.main()
