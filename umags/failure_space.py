# UMAGS Verification
import ast
import os
import sys

def check_function_guards(func_node):
    """
    Checks if a function definition node contains input validation / guards.
    Checks the first 5 statements in the function body.
    """
    for stmt in func_node.body[:5]:
        if isinstance(stmt, ast.Assert):
            return True
        if isinstance(stmt, ast.Raise):
            return True
        if isinstance(stmt, ast.If):
            cond_dump = ast.dump(stmt.test)
            if any(term in cond_dump for term in ("None", "isinstance", "Not", "Eq", "Compare")):
                return True
    return False

class TestSuiteVisitor(ast.NodeVisitor):
    def __init__(self, target_functions):
        self.target_functions = target_functions
        self.tested = {name: False for name in target_functions}
        self.negative_tested = {name: False for name in target_functions}
        self.current_with_assert_raises = False

    def visit_With(self, node):
        old_with = self.current_with_assert_raises
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                call = item.context_expr
                func_name = None
                if isinstance(call.func, ast.Name):
                    func_name = call.func.id
                elif isinstance(call.func, ast.Attribute):
                    func_name = call.func.attr
                
                if func_name in ("assertRaises", "assertRaisesRegex", "fails"):
                    self.current_with_assert_raises = True
        self.generic_visit(node)
        self.current_with_assert_raises = old_with

    def visit_Call(self, node):
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in self.target_functions:
            self.tested[func_name] = True
            if self.current_with_assert_raises:
                self.negative_tested[func_name] = True
            
            boundary_values = (None, "", [], {})
            for arg in node.args:
                if isinstance(arg, ast.Constant) and arg.value in boundary_values:
                    self.negative_tested[func_name] = True
                elif isinstance(arg, (ast.List, ast.Dict)) and len(arg.elts if isinstance(arg, ast.List) else arg.keys) == 0:
                    self.negative_tested[func_name] = True
                    
            for kw in node.keywords:
                if isinstance(kw.value, ast.Constant) and kw.value.value in boundary_values:
                    self.negative_tested[func_name] = True
                elif isinstance(kw.value, (ast.List, ast.Dict)) and len(kw.value.elts if isinstance(kw.value, ast.List) else kw.value.keys) == 0:
                    self.negative_tested[func_name] = True

        self.generic_visit(node)

def analyze_failure_space(repo_path, changed_files, diff_lines=None):
    """
    Computes untested_paths and missing_boundary_cases for all functions in changed_files.
    Only checks functions that were modified in the diff if diff_lines is provided.
    Returns:
      - untested_paths: list of function names
      - missing_boundary_cases: list of function names
      - R: Residual Risk Score (untested_paths + missing_boundary_cases)
    """
    target_functions = {}
    
    for f in changed_files:
        f_abs = os.path.join(repo_path, f)
        if not os.path.exists(f_abs) or not f.endswith(".py"):
            continue
            
        # Exclude test files from target analysis (tests don't need tests themselves)
        f_lower = f.lower()
        if "test" in f_lower or "runner" in f_lower:
            continue
            
        try:
            with open(f_abs, "r", encoding="utf-8", errors="ignore") as file_obj:
                tree = ast.parse(file_obj.read())
                
            class FuncDefVisitor(ast.NodeVisitor):
                def visit_FunctionDef(self, node):
                    if node.name.startswith("__") and node.name.endswith("__"):
                        return
                        
                    is_modified = True
                    if diff_lines is not None:
                        f_norm = f.replace("\\", "/").lower()
                        file_changed_lines = diff_lines.get(f_norm, set())
                        
                        start = node.lineno
                        end = getattr(node, "end_lineno", start)
                        func_lines = set(range(start, end + 1))
                        
                        # Function is modified only if its range overlaps with modified lines
                        if not func_lines.intersection(file_changed_lines):
                            is_modified = False
                            
                    if is_modified:
                        has_guard = check_function_guards(node)
                        target_functions[node.name] = {
                            "file": f,
                            "has_guard": has_guard,
                            "line": node.lineno
                        }
                    self.generic_visit(node)
                    
                def visit_AsyncFunctionDef(self, node):
                    self.visit_FunctionDef(node)
                    
            visitor = FuncDefVisitor()
            visitor.visit(tree)
        except Exception as e:
            _err = e

    if not target_functions:
        return [], [], 0

    visitor = TestSuiteVisitor(list(target_functions.keys()))
    
    test_dirs = ["ultron", "tests", "scratch", "study_portal_qa", "synapse_project"]
    for d in test_dirs:
        d_abs = os.path.join(repo_path, d)
        if os.path.exists(d_abs):
            for root, _, files in os.walk(d_abs):
                for file in files:
                    if file.endswith(".py") and any(term in file.lower() for term in ("test", "fuzz", "run")):
                        filepath = os.path.join(root, file)
                        try:
                            with open(filepath, "r", encoding="utf-8", errors="ignore") as file_obj:
                                tree = ast.parse(file_obj.read())
                            visitor.visit(tree)
                        except Exception as e:
                            _err = e

    untested_paths = []
    missing_boundary_cases = []
    
    for name, info in target_functions.items():
        is_tested = visitor.tested[name]
        is_neg_tested = visitor.negative_tested[name]
        has_guard = info["has_guard"]
        
        if not is_tested:
            untested_paths.append(name)
            
        if not has_guard and not is_neg_tested:
            missing_boundary_cases.append(name)

    R = len(untested_paths) + len(missing_boundary_cases)
    return untested_paths, missing_boundary_cases, R

def main():
    if len(sys.argv) < 3:
        print("Usage: python failure_space.py <repo_path> <comma_separated_changed_files>")
        sys.exit(1)
        
    repo = sys.argv[1]
    files = [f.strip() for f in sys.argv[2].split(",") if f.strip()]
    
    untested, missing_bounds, R = analyze_failure_space(repo, files)
    print(f"--- UMAGS Failure Space Analysis ---")
    print(f"Untested Paths ({len(untested)}): {', '.join(untested) if untested else 'None'}")
    print(f"Missing Boundary Cases ({len(missing_bounds)}): {', '.join(missing_bounds) if missing_bounds else 'None'}")
    print(f"Residual Risk Score (R): {R}")
    
if __name__ == "__main__":
    main()
