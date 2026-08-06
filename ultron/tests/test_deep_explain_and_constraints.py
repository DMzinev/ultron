# Unit tests for Decision Traceability (--deep) & AI Constraint Resolver
import unittest
from ultron.core.context_brief import generate_vibe_context_package
from ultron.core.rkm.risk_intelligence import compute_risk_profile
from ultron.core.rkm.policy_engine import evaluate_policy

class TestDeepExplainAndConstraints(unittest.TestCase):

    def test_constraint_resolver_auth_feature(self):
        pkg = generate_vibe_context_package("Add user authentication system")
        self.assertEqual(pkg["status"], "success")
        self.assertIn("SAFE MODIFICATION ZONES", pkg["prompt_package"])
        self.assertIn("NEW: ultron/interfaces/auth.py", pkg["prompt_package"])
        self.assertIn("Forbidden Core Files", pkg["prompt_package"])

    def test_constraint_resolver_database_feature(self):
        pkg = generate_vibe_context_package("Add database storage connection")
        self.assertIn("NEW: ultron/services/storage.py", pkg["prompt_package"])

    def test_deep_explain_data_structures(self):
        profile = compute_risk_profile("ultron/core/analyzer.py", complexity=22.0, coupling_fanout=6, coverage_percent=40.0)
        decision = evaluate_policy(profile, business_criticality="DEFAULT")
        self.assertTrue(decision.decision_id.startswith("dec_"))
        self.assertIn("ast", profile.confidence_vector)
        self.assertIn("overall", profile.confidence_vector)

if __name__ == "__main__":
    unittest.main()
