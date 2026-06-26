import os
import ast
import re
import subprocess
from radon.visitors import ComplexityVisitor

def get_file_ast_and_metadata(content):
    """
    Parses python code content and returns its AST, McCabe complexity,
    imports count, function count, total lines, and comment lines.
    """
    try:
        tree = ast.parse(content)
    except Exception:
        # Fallback for syntax errors or non-python code
        return None, 1, 0, 0, 1, 0

    # 1. Cyclomatic Complexity
    complexity = 0
    try:
        visitor = ComplexityVisitor.from_code(content)
        complexity = sum(block.complexity for block in visitor.blocks)
    except Exception:
        pass
    if complexity == 0:
        complexity = 1

    # 2. Imports (Coupling) & Functions count
    imports_count = 0
    functions_count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports_count += len(node.names)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions_count += 1

    # 3. Lines & Comments
    lines = content.splitlines()
    total_lines = len(lines)
    comment_lines = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            comment_lines += 1

    return tree, complexity, imports_count, functions_count, total_lines, comment_lines


def get_file_content(repo_path, rel_path, original_base=False):
    """
    Loads code content for a file. If original_base is True, tries Git show or .bak fallback.
    """
    abs_path = os.path.join(repo_path, rel_path)
    if original_base:
        # 1. Try Git show
        git_path = rel_path.replace("\\", "/")
        try:
            res = subprocess.run(
                ["git", "show", f"HEAD:{git_path}"],
                capture_output=True,
                text=True,
                cwd=repo_path,
                errors="ignore"
            )
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass

        # 2. Try .bak fallback
        bak_path = abs_path + ".bak"
        if os.path.exists(bak_path):
            try:
                with open(bak_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if len(content.strip()) > 20: # skip deleted sentinel
                        return content
            except Exception:
                pass

    # Fallback to current file content
    if os.path.exists(abs_path):
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            pass

    return ""


def calculate_entropy(repo_path, changed_files, original_base=False):
    """
    Computes normalized architecture entropy:
    E = (avg_complexity * avg_coupling * total_functions) / (comment_density + 0.1)
    """
    python_files = []
    for rel_path in changed_files:
        norm_path = os.path.normpath(rel_path).replace("\\", "/")
        if norm_path.endswith(".py"):
            python_files.append(norm_path)

    if not python_files:
        return 0.0

    total_complexity = 0
    total_coupling = 0
    total_functions = 0
    total_lines = 0
    total_comments = 0
    file_count = 0

    for rel_path in python_files:
        content = get_file_content(repo_path, rel_path, original_base=original_base)
        if not content.strip():
            continue
        _, comp, coup, funcs, lns, comms = get_file_ast_and_metadata(content)
        total_complexity += comp
        total_coupling += coup
        total_functions += funcs
        total_lines += lns
        total_comments += comms
        file_count += 1

    if file_count == 0:
        return 0.0

    avg_complexity = total_complexity / file_count
    avg_coupling = total_coupling / file_count
    comment_density = total_comments / max(total_lines, 1)

    entropy = (avg_complexity * avg_coupling * total_functions) / (comment_density + 0.1)
    return round(entropy, 4)


def scan_assumptions(file_path, original_code, modified_code):
    """
    Checks the modified file content for silent assumptions:
    - Missing encoding in open()
    - Hardcoded hosts/IPs/ports or absolute paths
    - Unhandled division (ast.Div)
    - Unannotated parameters or missing boundary checks
    """
    violations = []
    
    # Empty or deleted file boundary case
    if not modified_code.strip():
        return [], 1.0

    try:
        tree = ast.parse(modified_code)
    except Exception:
        return ["Syntax Error: Cannot parse code AST"], 0.0

    # 1. AST Scan for encoding on open()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
            has_encoding = False
            for kw in node.keywords:
                if kw.arg == "encoding":
                    has_encoding = True
                    break
            if not has_encoding:
                violations.append("Implicit encoding assumed in open() call.")

    # 2. Regex scan for hardcoded values (IPs, credentials, local paths)
    # Search for hardcoded ports, localhost, local Windows drives
    if re.search(r"localhost|127\.0\.0\.1", modified_code, re.IGNORECASE):
        violations.append("Assumes localhost or loopback address availability.")
    if re.search(r"\bport\s*=\s*\d+", modified_code, re.IGNORECASE):
        violations.append("Assumes static hardcoded port availability.")
    if re.search(r"^[A-Za-z]:[/\\]", modified_code, re.MULTILINE):
        violations.append("Assumes Windows local drive paths.")

    # 3. AST scan for division nodes
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            # Check if denominator is a simple variable name (implying possible division by zero assumption)
            if isinstance(node.right, ast.Name):
                violations.append(f"Assumes non-zero denominator for variable '{node.right.id}'.")

    # 4. AST scan for missing type hints on function definitions
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in node.args.args:
                if arg.arg != "self" and not arg.annotation:
                    violations.append(f"Implicit parameter type assumed for function '{node.name}' argument '{arg.arg}'.")

    # Calculate foundation integrity
    # Base 1.0, reduce by 0.05 per violation, clamp to [0.0, 1.0]
    integrity = max(0.0, min(1.0, 1.0 - (0.05 * len(violations))))
    return violations, round(integrity, 2)


def scan_future_risks(file_path, original_code, modified_code):
    """
    Checks for future/temporal fragility:
    - Modification of public signatures (args length/name changes)
    - Introduction of new global variables
    """
    risks = []
    
    if not modified_code.strip():
        return [], 0.0

    # Parse original and modified ASTs
    orig_tree = None
    if original_code.strip():
        try:
            orig_tree = ast.parse(original_code)
        except Exception:
            pass

    try:
        mod_tree = ast.parse(modified_code)
    except Exception:
        return ["Syntax Error: Cannot parse modified code AST"], 1.0

    # 1. Compare public function signatures
    orig_signatures = {}
    if orig_tree:
        for node in ast.walk(orig_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private functions (start with _)
                if not node.name.startswith("_"):
                    orig_signatures[node.name] = [arg.arg for arg in node.args.args]

    for node in ast.walk(mod_tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_") and node.name in orig_signatures:
                mod_args = [arg.arg for arg in node.args.args]
                orig_args = orig_signatures[node.name]
                if mod_args != orig_args:
                    risks.append(f"Public signature change in '{node.name}' (original: {orig_args}, modified: {mod_args}). Could break downstream callers.")

    # 2. Detect new global variables
    orig_globals = set()
    if orig_tree:
        for node in orig_tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        orig_globals.add(target.id)

    for node in mod_tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if not target.id.startswith("_") and target.id not in orig_globals:
                        risks.append(f"New public global variable '{target.id}' added. Increases architecture coupling and mutable state risk.")

    # Calculate future fragility
    # Base 0.0, increase by 0.1 per risk, clamp to [0.0, 1.0]
    fragility = max(0.0, min(1.0, 0.0 + (0.1 * len(risks))))
    return risks, round(fragility, 2)


def detect_abstraction_bloat(file_path, original_code, modified_code):
    """
    Scans for abstraction bloat (e.g. trivial delegation wrappers with no logic).
    """
    bloat_instances = []
    
    if not modified_code.strip():
        return [], 0.0

    try:
        tree = ast.parse(modified_code)
    except Exception:
        return ["Syntax Error: Cannot parse code AST"], 1.0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check if function body is just a return statement calling another function
            if len(node.body) == 1:
                stmt = node.body[0]
                if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call):
                    call = stmt.value
                    if isinstance(call.func, ast.Name):
                        # Trivial wrapper/delegation
                        bloat_instances.append(f"Function '{node.name}' is a pass-through wrapper for '{call.func.id}'. Direct call is cleaner.")
                elif isinstance(stmt, ast.Pass):
                    # Empty function stub
                    bloat_instances.append(f"Empty pass-through function stub '{node.name}'.")

    # Clamped score based on bloat instances count
    bloat_score = max(0.0, min(1.0, 0.1 * len(bloat_instances)))
    return bloat_instances, round(bloat_score, 2)
