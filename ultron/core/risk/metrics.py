"""
risk/metrics.py — Pure computational layer, minimal I/O.

Responsibilities:
    - get_file_complexity: reads a .py file, returns max McCabe complexity via radon
    - get_code_complexity: max McCabe complexity for a code string
    - extract_ast_blocks: parses code to AST, returns {name: {type, code, complexity}}

No I/O beyond the single file read in get_file_complexity. No network, no json, no ledgers.
"""
import os
import ast

try:
    from radon.visitors import ComplexityVisitor
except ImportError:
    ComplexityVisitor = None


def get_file_complexity(filepath):
    """
    Opens filepath and returns the maximum McCabe complexity of any block inside it.
    Defaults to 1 if no blocks exist or the file cannot be read.
    Raises ValueError if filepath is None.
    """
    if filepath is None:
        raise ValueError("filepath cannot be None")
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            code = f.read()
        return get_code_complexity(code)
    except Exception as e:
        print(f"Warning: failed to compute complexity of {filepath}: {e}")
    return 1


def get_code_complexity(code):
    """
    Computes maximum cyclomatic complexity for a given code segment string.
    Returns 1 if the code is empty, unparseable, or has no blocks.
    Raises ValueError if code is None.
    """
    if code is None:
        raise ValueError("code cannot be None")
    if ComplexityVisitor is not None:
        try:
            visitor = ComplexityVisitor.from_code(code)
            if visitor.blocks:
                return max(block.complexity for block in visitor.blocks)
        except Exception as e:
            print(f"Warning: failed to compute code complexity: {e}")
        return 1

    # Fallback AST branch counting when radon is missing: compute per-block max
    try:
        tree = ast.parse(code)
        branch_types = (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.BoolOp, ast.comprehension, ast.Assert)
        fn_nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if not fn_nodes:
            comp = 1
            for n in ast.walk(tree):
                if isinstance(n, branch_types):
                    comp += 1
            return comp

        block_complexities = []
        for fn in fn_nodes:
            comp = 1
            for n in ast.walk(fn):
                if n is not fn and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if isinstance(n, branch_types):
                    comp += 1
            block_complexities.append(comp)
        return max(block_complexities) if block_complexities else 1
    except Exception:
        return 1


def extract_ast_blocks(code):
    """
    Parses code to AST and extracts class/function blocks with source segments
    and cyclomatic complexity.

    Returns: {name: {'type': 'function'|'class', 'code': str, 'complexity': int}}
    Returns {} if code is empty or unparseable.
    Raises ValueError if code is None.
    """
    if code is None:
        raise ValueError("code cannot be None")
    blocks = {}
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                try:
                    segment = ast.get_source_segment(code, node)
                except Exception:
                    segment = ""
                blocks[name] = {
                    "type": "function",
                    "code": segment,
                    "complexity": get_code_complexity(segment) if segment else 1,
                }
            elif isinstance(node, ast.ClassDef):
                name = node.name
                try:
                    segment = ast.get_source_segment(code, node)
                except Exception:
                    segment = ""
                blocks[name] = {
                    "type": "class",
                    "code": segment,
                    "complexity": get_code_complexity(segment) if segment else 1,
                }
    except Exception as e:
        print(f"Warning: failed to extract AST blocks: {e}")
    return blocks
