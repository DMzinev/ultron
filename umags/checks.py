import ast
import os
import sys

def check_file_ast(filepath, changed_lines=None):
    """
    Parses a python file and runs AST-based validation checks.
    If changed_lines is provided (a set of 1-indexed line numbers), only violations on those lines
    will be returned.
    """
    violations = []
    if not os.path.exists(filepath):
        return violations
        
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        tree = ast.parse(content)
    except Exception as e:
        violations.append({
            "line": 0,
            "rule": "SyntaxError",
            "message": f"Could not parse file AST: {e}"
        })
        return violations

    class UMAGSVisitor(ast.NodeVisitor):
        def __init__(self):
            super().__init__()
            self.in_abstract_class = False

        def visit_ClassDef(self, node):
            old_abstract = self.in_abstract_class
            is_abstract = any(
                isinstance(base, ast.Name) and base.id in ("ABC", "abc.ABC")
                for base in node.bases
            )
            self.in_abstract_class = is_abstract
            self.generic_visit(node)
            self.in_abstract_class = old_abstract

        def visit_Call(self, node):
            # Check 1: open(...) without encoding parameter
            is_builtin_open = isinstance(node.func, ast.Name) and node.func.id == "open"
            is_io_open = (
                isinstance(node.func, ast.Attribute) and 
                isinstance(node.func.value, ast.Name) and 
                node.func.value.id == "io" and 
                node.func.attr == "open"
            )
            
            if is_builtin_open or is_io_open:
                has_encoding = any(kw.arg == "encoding" for kw in node.keywords)
                is_binary = False
                mode_val = None
                
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        mode_val = kw.value.value
                        
                if mode_val is None and len(node.args) >= 2:
                    if isinstance(node.args[1], ast.Constant):
                        mode_val = node.args[1].value
                        
                if isinstance(mode_val, str) and any(c in mode_val for c in ('b', 'B')):
                    is_binary = True
                    
                if not has_encoding and not is_binary:
                    violations.append({
                        "line": node.lineno,
                        "rule": "MissingFileEncoding",
                        "message": f"open() call is missing 'encoding' keyword argument (non-binary mode)."
                    })

            # Check 2: Path physics split on '/' or '\\'
            if isinstance(node.func, ast.Attribute) and node.func.attr == "split":
                if len(node.args) == 1 and isinstance(node.args[0], ast.Constant):
                    split_char = node.args[0].value
                    if split_char in ("/", "\\"):
                        violations.append({
                            "line": node.lineno,
                            "rule": "HardcodedPathSeparators",
                            "message": f"Hardcoded path split detected using '{split_char}'. Use os.path.split() or pathlib.Path."
                        })
            self.generic_visit(node)

        def visit_BinOp(self, node):
            # Check 3: Path physics string concatenation e.g. path + '/'
            if isinstance(node.op, ast.Add):
                left_is_slash = isinstance(node.left, ast.Constant) and node.left.value in ("/", "\\")
                right_is_slash = isinstance(node.right, ast.Constant) and node.right.value in ("/", "\\")
                if left_is_slash or right_is_slash:
                    violations.append({
                        "line": node.lineno,
                        "rule": "HardcodedPathSeparators",
                        "message": "String concatenation using hardcoded path separator ('/' or '\\'). Use os.path.join() or pathlib.Path."
                    })
            self.generic_visit(node)

        def visit_JoinedStr(self, node):
            # Check 4: Path physics in f-strings e.g. f"{path}/{file}"
            has_formatted = any(isinstance(val, ast.FormattedValue) for val in node.values)
            has_separator = False
            for i, val in enumerate(node.values):
                if isinstance(val, ast.Constant) and isinstance(val.value, str):
                    s = val.value
                    if "/" in s or "\\" in s:
                        if "http://" not in s and "https://" not in s:
                            is_path_sep = False
                            if s.strip() in ("/", "\\"):
                                is_path_sep = True
                            elif s.startswith("/") or s.endswith("/") or s.startswith("\\") or s.endswith("\\"):
                                is_path_sep = True
                            
                            if i > 0 and isinstance(node.values[i-1], ast.FormattedValue):
                                if s.startswith("/") or s.startswith("\\"):
                                    is_path_sep = True
                            if i < len(node.values) - 1 and isinstance(node.values[i+1], ast.FormattedValue):
                                if s.endswith("/") or s.endswith("\\"):
                                    is_path_sep = True
                                    
                            if is_path_sep:
                                has_separator = True
                                
            if has_formatted and has_separator:
                violations.append({
                    "line": node.lineno,
                    "rule": "HardcodedPathSeparators",
                    "message": "F-string contains hardcoded path separators adjacent to variable placeholders. Use os.path.join() or pathlib.Path."
                })
            self.generic_visit(node)

        def visit_ExceptHandler(self, node):
            # Check 5: Silent error handling (empty except/pass)
            is_silent = True
            for stmt in node.body:
                if not isinstance(stmt, (ast.Pass, ast.Expr)):
                    is_silent = False
                    break
                if isinstance(stmt, ast.Expr):
                    if not isinstance(stmt.value, ast.Constant):
                        is_silent = False
                        break
            if is_silent:
                violations.append({
                    "line": node.lineno,
                    "rule": "SilentErrorHandling",
                    "message": "Silent error handling detected in 'except' block (contains only 'pass' or string comments)."
                })
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            # Check 6: Stub detection
            is_stub = True
            is_abstract_or_overload = False
            for dec in node.decorator_list:
                dec_name = None
                if isinstance(dec, ast.Name):
                    dec_name = dec.id
                elif isinstance(dec, ast.Attribute):
                    dec_name = dec.attr
                if dec_name in ("abstractmethod", "overload"):
                    is_abstract_or_overload = True
                    break
            
            if not is_abstract_or_overload and not self.in_abstract_class:
                for stmt in node.body:
                    if not isinstance(stmt, (ast.Pass, ast.Expr)):
                        is_stub = False
                        break
                    if isinstance(stmt, ast.Expr):
                        if not isinstance(stmt.value, ast.Constant):
                            is_stub = False
                            break
                if is_stub and len(node.body) > 0:
                    violations.append({
                        "line": node.lineno,
                        "rule": "FunctionStub",
                        "message": f"Function '{node.name}' is an empty stub or placeholder (contains only 'pass' or docstrings)."
                    })
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)

    visitor = UMAGSVisitor()
    visitor.visit(tree)
    
    if changed_lines is not None:
        # Filter violations: keep syntax errors (line 0) and violations on modified lines
        violations = [v for v in violations if v["line"] == 0 or v["line"] in changed_lines]
        
    return violations

def main():
    if len(sys.argv) < 2:
        print("Usage: python checks.py <file_or_dir_path>")
        sys.exit(1)
        
    path = sys.argv[1]
    if os.path.isfile(path):
        violations = check_file_ast(path)
        for v in violations:
            print(f"[{v['rule']}] {path}:{v['line']} -> {v['message']}")
    else:
        all_violations = {}
        for root, _, files in os.walk(path):
            if any(x in root for x in (".git", "venv", "__pycache__", ".synapse")):
                continue
            for file in files:
                if file.endswith(".py"):
                    f_path = os.path.join(root, file)
                    v = check_file_ast(f_path)
                    if v:
                        all_violations[f_path] = v
                        
        for f, v_list in all_violations.items():
            for v in v_list:
                print(f"[{v['rule']}] {f}:{v['line']} -> {v['message']}")
                
if __name__ == "__main__":
    main()
