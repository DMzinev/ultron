# Unit tests for Decision Intelligence v1 End-to-End Vertical Slice
import unittest
from ultron.core.rkm.risk_intelligence import compute_risk_profile
from ultron.core.rkm.policy_engine import evaluate_policy
from ultron.core.translate import translate_decision_to_personas

class TestDecisionV1VerticalSlice(unittest.TestCase):

    def test_pipeline_integrity_zero_prose(self):
        profile = compute_risk_profile("ultron/core/analyzer.py", complexity=20.0, coupling_fanout=5, coverage_percent=70.0)
        self.assertIsInstance(profile.score, float)
        self.assertEqual(len(profile.signals), 3)
        
        decision = evaluate_policy(profile, business_criticality="DEFAULT")
        self.assertIn(decision.priority, ["HIGH", "CRITICAL", "MEDIUM", "LOW"])
        self.assertIsInstance(decision.reason_codes, list)
        self.assertTrue(decision.decision_id.startswith("dec_"))

    def test_weight_sensitivity(self):
        p_low = compute_risk_profile("a.py", complexity=5.0, coupling_fanout=1, coverage_percent=95.0)
        p_high = compute_risk_profile("a.py", complexity=25.0, coupling_fanout=8, coverage_percent=30.0)
        self.assertGreater(p_high.score, p_low.score)

    def test_policy_independence(self):
        p = compute_risk_profile("auth.py", complexity=15.0, coupling_fanout=4)
        dec1 = evaluate_policy(p, business_criticality="DEFAULT")
        dec2 = evaluate_policy(p, business_criticality="CRITICAL_PATH")
        # RiskProfile score must remain identical regardless of policy criticality multiplier
        self.assertEqual(p.score, evaluate_policy(p, business_criticality="EXPERIMENTAL").risk_score)

    def test_multi_persona_translations(self):
        p = compute_risk_profile("server.py", complexity=22.0, coupling_fanout=6, coverage_percent=40.0)
        dec = evaluate_policy(p, business_criticality="DEFAULT")
        personas = translate_decision_to_personas(dec)
        
        self.assertIn("developer", personas["personas"])
        self.assertIn("manager", personas["personas"])
        self.assertIn("founder", personas["personas"])
        self.assertIn("server.py", personas["personas"]["developer"])

if __name__ == "__main__":
    unittest.main()
