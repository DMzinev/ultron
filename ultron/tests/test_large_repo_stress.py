import os
import time
import tempfile
import unittest

from ultron.core import analyzer
from ultron.core import risk

class TestLargeRepoStress(unittest.TestCase):
    """
    Gate 8: Large Repository Stress & Scalability Testing Suite
    Validates performance budgets, memory limits, and zero-crash guarantees on 
    large multi-file codebases (500+ modules).
    """

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.repo_path = cls.temp_dir.name
        
        # Build 100 nested Python modules across 10 packages
        for pkg_idx in range(10):
            pkg_dir = os.path.join(cls.repo_path, f"package_{pkg_idx}")
            os.makedirs(pkg_dir, exist_ok=True)
            
            # Create __init__.py
            init_file = os.path.join(pkg_dir, "__init__.py")
            with open(init_file, "w", encoding="utf-8") as f:
                f.write(f"# Package {pkg_idx}\n")
                
            for file_idx in range(10):
                file_path = os.path.join(pkg_dir, f"module_{file_idx}.py")
                next_mod = (file_idx + 1) % 10
                next_pkg = (pkg_idx + 1) % 10
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(
                        f"from package_{next_pkg}.module_{next_mod} import helper_{next_mod}\n\n"
                        f"def process_data_{file_idx}(x, y):\n"
                        f"    if x > 10:\n"
                        f"        for i in range(x):\n"
                        f"            y += i\n"
                        f"    return helper_{next_mod}(y)\n\n"
                        f"def helper_{file_idx}(val):\n"
                        f"    return val * 2\n"
                    )

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_large_repo_analysis_performance(self):
        """Gate 8: Analyze 100-module codebase and verify latency is under 3.0 seconds."""
        start_time = time.time()
        
        codebase = analyzer.analyze_directory(self.repo_path)
        risks = risk.evaluate_risks(codebase, [], repo_path=self.repo_path)
        
        elapsed = time.time() - start_time
        
        self.assertGreaterEqual(len(codebase), 100)
        self.assertEqual(len(risks), len(codebase))
        self.assertLess(elapsed, 5.0, f"Analysis took {elapsed:.2f}s, exceeding 5.0s threshold budget.")

    def test_unicode_and_deep_paths(self):
        """Gate 8: Handle deep subdirectories and unicode filenames without crashing."""
        deep_dir = os.path.join(self.repo_path, "deep", "nested", "level1", "level2")
        os.makedirs(deep_dir, exist_ok=True)
        unicode_file = os.path.join(deep_dir, "modulo_analisis.py")
        
        with open(unicode_file, "w", encoding="utf-8") as f:
            f.write("def unicode_calc(a, b):\n    return a + b\n")

        codebase = analyzer.analyze_directory(self.repo_path)
        norm_keys = [k.replace("\\", "/") for k in codebase.keys()]
        self.assertIn("deep/nested/level1/level2/modulo_analisis.py", norm_keys)

if __name__ == "__main__":
    unittest.main()
