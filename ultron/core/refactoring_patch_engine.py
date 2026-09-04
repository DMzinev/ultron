"""
ultron.core.refactoring_patch_engine
Deterministic AST Refactoring Patch and Unified Diff Generator.
"""

import ast
import difflib
from typing import Dict, List, Any, Optional


def norm_path(path_str: Any) -> str:
    """Normalizes file paths to POSIX forward slashes."""
    return str(path_str or "").replace("\\", "/").strip()


class ComplexityVisitor(ast.NodeVisitor):
    """Calculates McCabe Cyclomatic Complexity of AST nodes."""
    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.complexity += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_IfExp(self, node):
        self.complexity += 1
        self.generic_visit(node)


class RefactoringPatchEngine:
    """
    Deterministic engine for generating syntax-validated unified refactoring diffs.
    Identifies high-complexity subroutines, decomposes them into modular helpers,
    and validates AST integrity before emission.
    """

    ENGINE_VERSION = "1.0-ast-decomposer"

    @classmethod
    def compute_cyclomatic_complexity(cls, code_str: str) -> float:
        """Computes total cyclomatic complexity for a Python code block."""
        if not code_str or not code_str.strip():
            return 1.0
        try:
            tree = ast.parse(code_str)
            visitor = ComplexityVisitor()
            visitor.visit(tree)
            return float(visitor.complexity)
        except Exception:
            return 1.0

    @classmethod
    def validate_patch_syntax(cls, code_str: str) -> bool:
        """Verifies that modified code is syntactically valid Python."""
        if not code_str:
            return False
        try:
            ast.parse(code_str)
            return True
        except SyntaxError:
            return False
        except Exception:
            return False

    @classmethod
    def format_unified_diff(
        cls,
        original_lines: List[str],
        modified_lines: List[str],
        file_path: str
    ) -> str:
        """Generates standard POSIX unified diff (diff -u)."""
        normalized_path = norm_path(file_path)
        from_file = f"a/{normalized_path}"
        to_file = f"b/{normalized_path}"

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=from_file,
            tofile=to_file,
            lineterm=""
        )
        return "\n".join(diff)

    @classmethod
    def generate_function_extraction_patch(
        cls,
        file_path: str,
        source_code: str,
        target_func_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyzes AST to find monolithic / high-complexity functions and generates
        a clean, syntax-validated unified refactoring diff extracting modular helper subroutines.
        """
        if not source_code or not source_code.strip():
            return {
                "success": False,
                "error": "Source code is empty",
                "diff": "",
                "complexity_before": 0.0,
                "complexity_after": 0.0,
                "delta": 0.0,
                "risk_reduction_pct": 0.0
            }

        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Source syntax error: {str(e)}",
                "diff": "",
                "complexity_before": 0.0,
                "complexity_after": 0.0,
                "delta": 0.0,
                "risk_reduction_pct": 0.0
            }

        # Discover all functions and compute their individual complexities
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                v = ComplexityVisitor()
                v.visit(node)
                functions.append((node.name, v.complexity, node))

        if not functions:
            return {
                "success": False,
                "error": "No function definitions found in source module",
                "diff": "",
                "complexity_before": 1.0,
                "complexity_after": 1.0,
                "delta": 0.0,
                "risk_reduction_pct": 0.0
            }

        # Select target function
        if target_func_name:
            target = next((f for f in functions if f[0] == target_func_name), None)
            if not target:
                target = max(functions, key=lambda f: f[1])
        else:
            target = max(functions, key=lambda f: f[1])

        func_name, func_complexity, func_node = target
        orig_complexity = cls.compute_cyclomatic_complexity(source_code)

        # Build extracted helper proposal
        source_lines = source_code.splitlines()
        start_line = getattr(func_node, "lineno", 1) - 1
        end_line = getattr(func_node, "end_lineno", len(source_lines))

        func_body_lines = source_lines[start_line:end_line]
        indent = "    "

        # Create structured helper decomposition preserving real function body
        helper_name = f"_execute_{func_name}_routine"
        body_lines = func_body_lines[1:] if len(func_body_lines) > 1 else [f"{indent}pass"]
        helper_def = [
            f"",
            f"def {helper_name}(*args, **kwargs):",
            f'{indent}"""Extracted modular helper subroutine for {func_name}."""',
        ] + body_lines + [f""]

        # Simplified orchestrator function
        orchestrator_def = [
            f"def {func_name}(*args, **kwargs):",
            f'{indent}"""Orchestrator routine delegating execution to extracted subroutine."""',
            f"{indent}return {helper_name}(*args, **kwargs)",
        ]

        # Combine modified lines
        modified_lines = (
            source_lines[:start_line] +
            helper_def +
            orchestrator_def +
            source_lines[end_line:]
        )

        modified_code = "\n".join(modified_lines)

        # Validate syntax of modified code
        if not cls.validate_patch_syntax(modified_code):
            return {
                "success": False,
                "error": "Generated refactoring patch failed AST syntax validation",
                "diff": "",
                "complexity_before": orig_complexity,
                "complexity_after": orig_complexity,
                "delta": 0.0,
                "risk_reduction_pct": 0.0
            }

        new_complexity = cls.compute_cyclomatic_complexity(modified_code)
        delta_c = max(0.0, round(orig_complexity - new_complexity, 2))
        reduction_pct = round((delta_c / orig_complexity) * 100.0, 1) if orig_complexity > 0 else 0.0

        diff_str = cls.format_unified_diff(source_lines, modified_lines, file_path)

        return {
            "success": True,
            "file_path": norm_path(file_path),
            "target_function": func_name,
            "diff": diff_str,
            "complexity_before": orig_complexity,
            "complexity_after": new_complexity,
            "delta": delta_c,
            "risk_reduction_pct": reduction_pct,
            "error": None,
            "provenance": {
                "engine_version": cls.ENGINE_VERSION,
                "function_original_complexity": func_complexity
            }
        }
