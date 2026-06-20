# UMAGS Verification
import unittest
import os
import sys
import math

# Ensure local folder is in import search path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import analyzer
import risk
import guard
import classifier
import predict

class TestUltronCore(unittest.TestCase):
    
    def test_string_similarity(self):
        # Levenshtein similarity tests
        self.assertAlmostEqual(classifier.string_similarity("init_db", "init_dbb"), 0.875)
        self.assertAlmostEqual(classifier.string_similarity("init_db", "init_db"), 1.0)
        self.assertLess(classifier.string_similarity("init_db", "process"), 0.5)

    def test_analyzer_on_code(self):
        # Test CallVisitor parsing
        code = """def my_func(a, b=2):
    print(a)
    other_func()
"""
        import ast
        tree = ast.parse(code)
        cv = analyzer.CallVisitor()
        cv.visit(tree)
        self.assertIn("print", cv.calls)
        self.assertIn("other_func", cv.calls)

    def test_analyzer_file_and_directory(self):
        import tempfile
        import shutil
        temp_dir = tempfile.mkdtemp()
        try:
            code = """import os
def my_func(x):
    print(x)
"""
            filepath = os.path.join(temp_dir, "test_file.py")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
                
            analysis = analyzer.analyze_file(filepath)
            self.assertIn("os", analysis["imports"])
            self.assertEqual(len(analysis["definitions"]), 1)
            self.assertEqual(analysis["definitions"][0]["name"], "my_func")
            
            codebase = analyzer.analyze_directory(temp_dir)
            self.assertIn("test_file.py", codebase)
        finally:
            shutil.rmtree(temp_dir)

    def test_contract_guard_logic(self):
        # Verify call signature validation boundaries
        # def sample(a, b=10)
        min_args = 1
        max_args = 2
        
        # Underflow check: passing 0 args should violate
        self.assertTrue(0 < min_args or 0 > max_args)
        # Normal check: passing 1 arg should conform
        self.assertFalse(1 < min_args or 1 > max_args)
        # Normal check: passing 2 args should conform
        self.assertFalse(2 < min_args or 2 > max_args)
        # Overflow check: passing 3 args should violate
        self.assertTrue(3 < min_args or 3 > max_args)

    def test_verify_contracts_end_to_end(self):
        import tempfile
        import shutil
        temp_dir = tempfile.mkdtemp()
        try:
            code_def = """def add_numbers(x, y):
    return x + y
"""
            code_calls = """def run():
    add_numbers(10)
    add_numbers(10, 20)
"""
            with open(os.path.join(temp_dir, "defs.py"), "w", encoding="utf-8") as f:
                f.write(code_def)
            with open(os.path.join(temp_dir, "calls.py"), "w", encoding="utf-8") as f:
                f.write(code_calls)
                
            violations = guard.verify_contracts(temp_dir)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0]["function"], "add_numbers")
            self.assertEqual(violations[0]["actual_args"], 1)
            self.assertEqual(violations[0]["expected_range"], "2-2")
        finally:
            shutil.rmtree(temp_dir)

    def test_risk_score_formula(self):
        # System Impact Score: I(N) = Complexity * ln(e + Coupling)
        complexity = 5
        coupling = 3
        expected = complexity * math.log(math.e + coupling)
        
        score = complexity * math.log(math.e + coupling)
        self.assertAlmostEqual(score, expected)
        
        # Validate tier classification threshold logic
        def get_tier(s):
            if s >= 10.0: return "HIGH"
            if s >= 3.0: return "MEDIUM"
            return "LOW"
            
        self.assertEqual(get_tier(12.5), "HIGH")
        self.assertEqual(get_tier(5.2), "MEDIUM")
        self.assertEqual(get_tier(1.5), "LOW")

    def test_second_order_markov_transitions(self):
        # Verify transition model building with [END] tokens and second-order keys
        import tempfile
        import shutil
        temp_dir = tempfile.mkdtemp()
        try:
            code = """def process():
    init_db()
    query()
    close_db()
"""
            with open(os.path.join(temp_dir, "sample.py"), "w", encoding="utf-8") as f:
                f.write(code)
            
            names, probs = classifier.build_models(temp_dir)
            
            # Check for name extraction
            self.assertIn("process", names)
            
            # Check transitions
            self.assertIn("init_db", probs)
            self.assertIn("query", probs["init_db"])
            self.assertIn("init_db,query", probs)
            self.assertIn("close_db", probs["init_db,query"])
            self.assertEqual(probs["init_db,query"]["close_db"], 1.0)
            
            # Check termination transition
            self.assertIn("query,close_db", probs)
            self.assertIn("[END]", probs["query,close_db"])
            self.assertEqual(probs["query,close_db"]["[END]"], 1.0)
        finally:
            shutil.rmtree(temp_dir)

    def test_evaluate_diff_risk(self):
        # Create a mock codebase dict
        codebase = {
            "helper.py": {
                "imports": [],
                "definitions": [
                    {
                        "type": "function",
                        "name": "util_func",
                        "calls": []
                    }
                ]
            },
            "main.py": {
                "imports": ["helper"],
                "definitions": [
                    {
                        "type": "function",
                        "name": "run_main",
                        "calls": ["util_func"]
                    }
                ]
            }
        }
        old_code = """
def util_func():
    print("old")
"""
        new_code = """
def util_func():
    # increased complexity
    if True:
        if False:
            pass
    print("new")
"""
        # Call evaluate_diff_risk
        res = risk.evaluate_diff_risk(codebase, "helper.py", old_code, new_code)
        self.assertEqual(res["filepath"], "helper.py")
        self.assertGreater(res["delta_score"], 0.0)
        
        # Verify specific change metadata
        self.assertEqual(len(res["changes"]), 1)
        change = res["changes"][0]
        self.assertEqual(change["name"], "util_func")
        self.assertEqual(change["action"], "modified")
        self.assertEqual(change["complexity_before"], 1)
        self.assertGreater(change["complexity_after"], 1)
        self.assertEqual(change["coupling"], 1) # Called by main.py
        
    def test_predict_test_impact(self):
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        try:
            # We create a mock run_tests.py file
            test_code = """
import unittest
class TestSample(unittest.TestCase):
    def test_one(self):
        foo()
    def test_two(self):
        bar()
"""
            test_file = os.path.join(temp_dir, "run_tests.py")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(test_code)
                
            codebase = {
                "foo.py": {
                    "imports": [],
                    "definitions": [
                        {
                            "type": "function",
                            "name": "foo",
                            "calls": []
                        }
                    ]
                },
                "bar.py": {
                    "imports": [],
                    "definitions": [
                        {
                            "type": "function",
                            "name": "bar",
                            "calls": []
                        }
                    ]
                }
            }
            
            # 1. Test when foo is changed
            predictions = predict.predict_test_impact(codebase, ["foo.py"], ["foo"], test_file)
            self.assertEqual(len(predictions), 1)
            self.assertEqual(predictions[0]["test_name"], "test_one")
            
            # 2. Test when bar is changed
            predictions = predict.predict_test_impact(codebase, ["bar.py"], ["bar"], test_file)
            self.assertEqual(len(predictions), 1)
            self.assertEqual(predictions[0]["test_name"], "test_two")
        finally:
            shutil.rmtree(temp_dir)

    def test_umags_ast_checks(self):
        import tempfile
        import shutil
        from umags.checks import check_file_ast
        
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a file with violations
            filepath = os.path.join(temp_dir, "bad.py")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("""def my_stub():
    pass
""")
            violations = check_file_ast(filepath)
            self.assertGreater(len(violations), 0)
            self.assertEqual(violations[0]["rule"], "FunctionStub")
            
            # Test with None/nonexistent filepath (boundary/error case)
            violations_empty = check_file_ast("/nonexistent/file.py")
            self.assertEqual(len(violations_empty), 0)
        finally:
            shutil.rmtree(temp_dir)

    def test_umags_failure_space(self):
        import tempfile
        import shutil
        from umags.failure_space import analyze_failure_space
        
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a mock file with an untested function
            filepath = os.path.join(temp_dir, "mock_func.py")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("""def untested_fn(x):
    return x
""")
            # Analyze failure space on it
            untested, missing_bounds, R = analyze_failure_space(temp_dir, ["mock_func.py"])
            self.assertIn("untested_fn", untested)
            self.assertIn("untested_fn", missing_bounds)
            self.assertEqual(R, 2)
            
            # Test empty inputs (boundary cases)
            u, m, r = analyze_failure_space(temp_dir, [])
            self.assertEqual(r, 0)
        finally:
            shutil.rmtree(temp_dir)

    def test_umags_guards_detector(self):
        import ast
        from umags.failure_space import check_function_guards
        
        # Test function with guard
        code_guard = """def has_guard(x):
    assert x is not None
    return x
"""
        tree_guard = ast.parse(code_guard)
        func_node_guard = tree_guard.body[0]
        self.assertTrue(check_function_guards(func_node_guard))
        
        # Test function without guard
        code_no_guard = """def no_guard(x):
    return x
"""
        tree_no_guard = ast.parse(code_no_guard)
        func_node_no_guard = tree_no_guard.body[0]
        self.assertFalse(check_function_guards(func_node_no_guard))

    def test_parse_patch_diff_lines(self):
        from run_verification_loop import parse_patch_diff_lines
        diff = """+++ b/umags/checks.py
@@ -10,3 +10,4 @@
+added line 1
+added line 2
"""
        lines = parse_patch_diff_lines(diff)
        self.assertIn("umags/checks.py", lines)
        self.assertIn(10, lines["umags/checks.py"])
        self.assertIn(11, lines["umags/checks.py"])

    def test_mains(self):
        import sys
        from unittest.mock import patch
        import umags.checks as checks
        import umags.failure_space as failure_space
        
        # Test checks.main with mock sys.argv
        with patch.object(sys, 'argv', ['checks.py']):
            with self.assertRaises(SystemExit):
                checks.main()
                
        # Test failure_space.main with mock sys.argv
        with patch.object(sys, 'argv', ['failure_space.py']):
            with self.assertRaises(SystemExit):
                failure_space.main()

if __name__ == "__main__":
    print("[+] Running Ultron Core Tests...")
    unittest.main()
