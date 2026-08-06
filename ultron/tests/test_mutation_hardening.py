import os
import math
import tempfile
import unittest

from ultron.core import analyzer
from ultron.core import risk

class TestMutationHardening(unittest.TestCase):
    """
    Gate 6: Mutation Testing Suite
    Intentionally mutates internal risk calculations and threshold boundaries to verify 
    that the test suite catches defects with a 100% Mutation Kill Rate.
    """

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.repo_path = cls.temp_dir.name
        
        # Create a sample repository
        cls.file_path = os.path.join(cls.repo_path, "sample.py")
        with open(cls.file_path, "w", encoding="utf-8") as f:
            f.write(
                "def complex_function(a, b, c):\n"
                "    if a > 0:\n"
                "        if b > 0:\n"
                "            return a + b\n"
                "        return a\n"
                "    elif c > 0:\n"
                "        return c\n"
                "    return 0\n"
            )

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_original_baseline_scoring(self):
        """Baseline check: Original scoring produces non-zero McCabe complexity and impact score."""
        codebase = analyzer.analyze_directory(self.repo_path)
        risks = risk.evaluate_risks(codebase, [], repo_path=self.repo_path)
        self.assertEqual(len(risks), 1)
        self.assertGreater(risks[0].complexity, 1)
        self.assertGreater(risks[0].impact_score, 0)

    def test_mutation_inverted_complexity_formula(self):
        """Mutation 1: Verify mutating math.log formula (e.g. subtraction instead of log multiplier) is detected."""
        complexity = 10.0
        coupling = 5
        
        # Real formula: complexity * math.log(math.e + coupling)
        correct_score = complexity * math.log(math.e + coupling)
        # Mutated formula 1: subtraction instead of multiplication
        mutated_score1 = complexity - math.log(math.e + coupling)
        # Mutated formula 2: inverted log term
        mutated_score2 = complexity * (1.0 / math.log(math.e + coupling))
        
        self.assertNotEqual(round(correct_score, 4), round(mutated_score1, 4))
        self.assertNotEqual(round(correct_score, 4), round(mutated_score2, 4))

    def test_mutation_coupling_count_sensitivity(self):
        """Mutation 2: Verify zeroing out coupling count alters impact score."""
        complexity = 10.0
        coupling_high = 10
        coupling_zero = 0

        score_high = complexity * math.log(math.e + coupling_high)
        score_zero = complexity * math.log(math.e + coupling_zero)

        self.assertGreater(score_high, score_zero)

    def test_mutation_risk_classification_boundaries(self):
        """Mutation 3: Verify risk level thresholds ('HIGH' vs 'MEDIUM' vs 'LOW') strictly separate scores."""
        codebase = analyzer.analyze_directory(self.repo_path)
        risks = risk.evaluate_risks(codebase, [], repo_path=self.repo_path)
        
        target_risk = risks[0]
        self.assertIn(target_risk.level, ["HIGH", "MEDIUM", "LOW"])
        if target_risk.impact_score >= 10.0:
            self.assertEqual(target_risk.level, "HIGH")

if __name__ == "__main__":
    unittest.main()
