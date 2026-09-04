"""
ultron.tests.test_policy_engine
Unit test suite asserting architectural governance policy rules and violation detection.
"""

import unittest
from ultron.core.policy_engine import PolicyEngine, norm_path


class TestPolicyEngine(unittest.TestCase):
    """Unit tests for PolicyEngine."""

    def test_norm_path(self):
        """Asserts path normalization to POSIX slashes."""
        self.assertEqual(norm_path("ultron\\interfaces\\web\\api.py"), "ultron/interfaces/web/api.py")
        self.assertEqual(norm_path(None), "")

    def test_forbidden_dependency_violation(self):
        """Asserts forbidden dependency rule triggers on matching edges."""
        engine = PolicyEngine(load_defaults=True)
        data = {
            "dependency_graph": {
                "edges": [
                    {"source": "controllers/auth_controller.py", "target": "repositories/user_repo.py"},
                    {"source": "services/auth_service.py", "target": "repositories/user_repo.py"}
                ]
            },
            "risks": []
        }
        res = engine.evaluate_codebase(data)
        self.assertEqual(res["status"], "VIOLATIONS_DETECTED")
        self.assertEqual(res["total_violations"], 1)
        v = res["violations"][0]
        self.assertEqual(v["rule_id"], "POL-NO-DIRECT-DB-FROM-CONTROLLER")
        self.assertEqual(v["severity"], "HIGH")

    def test_max_complexity_violation(self):
        """Asserts complexity threshold breaches trigger violations."""
        engine = PolicyEngine(load_defaults=True)
        data = {
            "risks": [
                {"file": "core/parser.py", "complexity": 18.0, "coupling_score": 2.0},
                {"file": "core/utils.py", "complexity": 3.0, "coupling_score": 1.0}
            ],
            "dependency_graph": {"edges": []}
        }
        res = engine.evaluate_codebase(data)
        self.assertEqual(res["status"], "VIOLATIONS_DETECTED")
        self.assertEqual(res["total_violations"], 1)
        v = res["violations"][0]
        self.assertEqual(v["rule_id"], "POL-MAX-MODULE-COMPLEXITY")
        self.assertIn("18.0", v["violating_value"])

    def test_max_coupling_violation(self):
        """Asserts coupling threshold breaches trigger violations."""
        engine = PolicyEngine(load_defaults=True)
        data = {
            "risks": [
                {"file": "core/hub.py", "complexity": 4.0, "coupling_score": 14.0}
            ],
            "dependency_graph": {"edges": []}
        }
        res = engine.evaluate_codebase(data)
        self.assertEqual(res["status"], "VIOLATIONS_DETECTED")
        self.assertEqual(res["total_violations"], 1)
        v = res["violations"][0]
        self.assertEqual(v["rule_id"], "POL-MAX-MODULE-COUPLING")
        self.assertEqual(v["severity"], "HIGH")

    def test_clean_codebase_compliant(self):
        """Asserts compliant codebase yields zero violations."""
        engine = PolicyEngine(load_defaults=True)
        data = {
            "risks": [
                {"file": "services/user_service.py", "complexity": 4.0, "coupling_score": 2.0}
            ],
            "dependency_graph": {
                "edges": [
                    {"source": "services/user_service.py", "target": "repositories/user_repo.py"}
                ]
            }
        }
        res = engine.evaluate_codebase(data)
        self.assertEqual(res["status"], "COMPLIANT")
        self.assertEqual(res["total_violations"], 0)
        self.assertEqual(len(res["violations"]), 0)

    def test_add_custom_rule_and_evaluation(self):
        """Asserts adding custom rule and evaluating it properly."""
        engine = PolicyEngine(load_defaults=False)
        engine.add_rule({
            "id": "CUSTOM-NO-SYS-IMPORTS",
            "name": "Prohibit direct sys imports in domain models",
            "type": "FORBIDDEN_DEPENDENCY",
            "source_pattern": r"domain/",
            "target_pattern": r"os|sys",
            "severity": "HIGH",
            "message": "Domain entities must not access OS/sys directly."
        })
        self.assertEqual(len(engine.list_rules()), 1)

        data = {
            "dependency_graph": {
                "edges": [
                    {"source": "domain/entity.py", "target": "sys.py"}
                ]
            }
        }
        res = engine.evaluate_codebase(data)
        self.assertEqual(res["status"], "VIOLATIONS_DETECTED")
        self.assertEqual(res["violations"][0]["rule_id"], "CUSTOM-NO-SYS-IMPORTS")


if __name__ == "__main__":
    unittest.main()
