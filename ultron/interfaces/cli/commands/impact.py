"""
ultron.interfaces.cli.commands.impact
Differential Impact Simulator & Test Set Minimizer CLI Handler.
"""

import ast
import json
import os
import shlex
import sys
from typing import Any, Dict, List, Optional, Set, Tuple


def _is_test_file(rel_path: str) -> bool:
    """
    Returns True if the relative file path represents an actual test file,
    preventing non-test fixture data or production modules from being misidentified.
    """
    norm = rel_path.replace("\\", "/")
    base = os.path.basename(norm)

    # Explicitly reject fixtures, temporary dirs, and build artifacts
    if (
        "fixtures/" in norm
        or "/fixtures/" in norm
        or "fixture/" in norm
        or "/fixture/" in norm
        or "__pycache__" in norm
    ):
        return False

    # Check if inside a dedicated test directory
    in_test_dir = (
        norm.startswith("tests/")
        or "/tests/" in norm
        or norm.startswith("test/")
        or "/test/" in norm
    )

    if in_test_dir:
        return base.startswith("test_") or base.endswith("_test.py") or base == "tests.py"

    # Root-level test files
    if "/" not in norm:
        return base.startswith("test_") or base.endswith("_test.py")

    return False


def _discover_test_files(repo_path: str) -> List[str]:
    """
    Discovers all test files in repo_path, explicitly pruning fixtures, caches,
    and virtual environments to prevent fixture data file contamination.
    """
    prune_dirs = {
        "fixtures",
        "fixture",
        "__pycache__",
        ".git",
        "venv",
        ".venv",
        "env",
        "test_env",
        "node_modules",
        "dist",
        "build",
        "scratch",
        ".egg-info",
        "ultron_risk_scorer.egg-info",
    }

    test_files: List[str] = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in prune_dirs]
        for f in files:
            if not f.endswith(".py"):
                continue
            abs_f = os.path.join(root, f)
            try:
                rel_f = os.path.relpath(abs_f, repo_path).replace("\\", "/")
                if _is_test_file(rel_f):
                    test_files.append(rel_f)
            except ValueError:
                pass
    test_files.sort()
    return test_files


def _extract_ast_imports(abs_path: str) -> Set[str]:
    """
    Extracts module and symbol import names from a Python source file.
    Defensively wraps reading and AST parsing in try-except to guard against
    syntax errors, encoding issues, or incomplete edits.
    """
    imported_names: Set[str] = set()
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        tree = ast.parse(content, filename=abs_path)
    except (SyntaxError, UnicodeDecodeError, OSError):
        return imported_names

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_names.add(node.module)
                for alias in node.names:
                    imported_names.add(f"{node.module}.{alias.name}")
    return imported_names


def _build_exact_dependency_edges(codebase: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Constructs exact file nodes and import dependency edges from codebase facts,
    guaranteeing no false-positive substring matches (e.g. stdlib 'ast' matching 'blast_radius.py').
    """
    mod_map: Dict[str, str] = {}
    for f in codebase:
        norm_f = f.replace("\\", "/")
        base = norm_f[:-3] if norm_f.endswith(".py") else norm_f
        mod_map[base.replace("/", ".")] = norm_f
        mod_name = os.path.basename(base)
        if mod_name != "__init__":
            mod_map[mod_name] = norm_f

    nodes = [{"id": f.replace("\\", "/")} for f in codebase]
    edges: List[Dict[str, Any]] = []

    for src_file, data in codebase.items():
        norm_src = src_file.replace("\\", "/")
        for imp in data.get("imports", []):
            parts = imp.split(".")
            matched_tgt = None
            for i in range(len(parts), 0, -1):
                pfx = ".".join(parts[:i])
                if pfx in mod_map:
                    tgt = mod_map[pfx]
                    if tgt != norm_src:
                        matched_tgt = tgt
                    break
            if not matched_tgt:
                for pot_path in codebase:
                    pot_norm = pot_path.replace("\\", "/")
                    pot_base = pot_norm[:-3] if pot_norm.endswith(".py") else pot_norm
                    pot_mod = pot_base.replace("/", ".")
                    if pot_mod == imp or pot_mod.endswith("." + imp):
                        if pot_norm != norm_src:
                            matched_tgt = pot_norm
                        break
            if matched_tgt:
                edges.append({
                    "source": norm_src,
                    "target": matched_tgt,
                    "type": "imports"
                })
    return nodes, edges


def _map_affected_files_to_tests(
    repo_path: str,
    affected_files: List[str],
    all_test_files: List[str]
) -> List[str]:
    """
    Maps affected production files to corresponding test suites using
    AST import reachability and naming convention heuristics.
    """
    affected_tests: Set[str] = set()

    # Pre-compute exact module identifiers and basenames for each affected file
    file_identifiers: Dict[str, Set[str]] = {}
    file_basenames: Dict[str, str] = {}
    for af in affected_files:
        norm_af = af.replace("\\", "/")
        base_name = os.path.splitext(os.path.basename(norm_af))[0]
        if base_name == "__init__":
            parent = os.path.basename(os.path.dirname(norm_af))
            base_name = parent or "init"
        file_basenames[norm_af] = base_name

        identifiers = {norm_af, base_name}
        if norm_af.endswith(".py"):
            dotted = norm_af[:-3].replace("/", ".")
            identifiers.add(dotted)
        file_identifiers[norm_af] = identifiers

    for tf in all_test_files:
        norm_tf = tf.replace("\\", "/")
        abs_tf = os.path.join(repo_path, norm_tf)
        test_base = os.path.splitext(os.path.basename(norm_tf))[0]

        # If the test file itself is in affected files
        if norm_tf in affected_files:
            affected_tests.add(norm_tf)
            continue

        # 1. Naming convention heuristic: test_<module>.py or <module>_test.py
        for af, base_name in file_basenames.items():
            if (
                test_base == f"test_{base_name}"
                or test_base == f"{base_name}_test"
                or test_base.startswith(f"test_{base_name}_")
                or f"_{base_name}_" in test_base
                or test_base.endswith(f"_{base_name}")
            ):
                affected_tests.add(norm_tf)
                break

        if norm_tf in affected_tests:
            continue

        # 2. AST Import reachability
        imported = _extract_ast_imports(abs_tf)
        matched = False
        for af, identifiers in file_identifiers.items():
            for id_str in identifiers:
                if id_str in imported:
                    affected_tests.add(norm_tf)
                    matched = True
                    break
                # Check dotted module containment
                if "." in id_str:
                    for imp in imported:
                        if imp == id_str or imp.startswith(f"{id_str}."):
                            affected_tests.add(norm_tf)
                            matched = True
                            break
                if matched:
                    break
            if matched:
                break

    return sorted(list(affected_tests))


def _detect_test_runner(repo_path: str) -> str:
    """
    Detects repository test runner preference.
    Resolves to 'pytest' if pytest config files exist, else defaults to 'unittest'.
    """
    for indicator in ("pytest.ini", "conftest.py", "tox.ini"):
        if os.path.isfile(os.path.join(repo_path, indicator)):
            return "pytest"

    pyproject_path = os.path.join(repo_path, "pyproject.toml")
    if os.path.isfile(pyproject_path):
        try:
            with open(pyproject_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "[tool.pytest" in content:
                return "pytest"
        except OSError:
            pass

    return "unittest"


def _synthesize_test_command(runner: str, affected_tests: List[str]) -> str:
    """Synthesizes minimal shell-escaped test execution command."""
    if not affected_tests:
        if runner == "pytest":
            return "pytest"
        return "python -m unittest discover"

    quoted_tests = [shlex.quote(t) if " " in t else t for t in affected_tests]
    if runner == "pytest":
        return f"pytest {' '.join(quoted_tests)}"
    return f"python -m unittest {' '.join(quoted_tests)}"


def run_impact_command(
    target_file: str,
    repo_path: str = ".",
    max_depth: int = 5,
    runner: str = "auto",
    json_output: bool = False
) -> int:
    """
    Executes the 'ultron impact <file>' command.
    Computes topological blast radius and affected test suite set.
    Returns 0 on SUCCESS, 1 on FAILURE (e.g. invalid target or path escape).
    """
    # 1. Null-byte guard
    if target_file and "\0" in target_file:
        msg = "Invalid target file path: null-byte detected."
        if json_output:
            print(json.dumps({"status": "error", "error": msg}))
        else:
            sys.stderr.write(f"[-] Error: {msg}\n")
        return 1

    # 2. Missing target argument
    if not target_file or not str(target_file).strip():
        msg = "Missing required target file argument."
        if json_output:
            print(json.dumps({"status": "error", "error": msg}))
        else:
            sys.stderr.write(f"[-] Error: {msg}\n")
        return 1

    # 3. Repository directory validation
    abs_repo = os.path.abspath(os.path.normpath(repo_path))
    if not os.path.isdir(abs_repo):
        msg = f"Repository directory '{abs_repo}' not found."
        if json_output:
            print(json.dumps({"status": "error", "error": msg}))
        else:
            sys.stderr.write(f"[-] Error: {msg}\n")
        return 1

    # 4. Target file resolution & containment validation
    abs_target = os.path.abspath(os.path.join(abs_repo, target_file)) if not os.path.isabs(target_file) else os.path.abspath(target_file)

    try:
        if os.path.commonpath([abs_repo, abs_target]) != abs_repo:
            msg = f"Path traversal escape detected: target '{target_file}' is outside repository '{abs_repo}'."
            if json_output:
                print(json.dumps({"status": "error", "error": msg}))
            else:
                sys.stderr.write(f"[-] Error: {msg}\n")
            return 1
    except ValueError:
        msg = f"Cross-drive path access detected: target '{target_file}' is outside repository '{abs_repo}'."
        if json_output:
            print(json.dumps({"status": "error", "error": msg}))
        else:
            sys.stderr.write(f"[-] Error: {msg}\n")
        return 1

    if not os.path.isfile(abs_target):
        msg = f"Target file '{target_file}' does not exist in repository '{abs_repo}'."
        if json_output:
            print(json.dumps({"status": "error", "error": msg}))
        else:
            sys.stderr.write(f"[-] Error: {msg}\n")
        return 1

    try:
        norm_target = os.path.relpath(abs_target, abs_repo).replace("\\", "/")
    except ValueError:
        norm_target = os.path.normpath(target_file).replace("\\", "/").lstrip("./")

    # 5. Determine if target is a test file
    target_is_test = _is_test_file(norm_target)
    all_tests = _discover_test_files(abs_repo)

    if target_is_test:
        direct_callers: List[str] = []
        transitive_callers: List[str] = []
        affected_files: List[str] = [norm_target]
        affected_tests: List[str] = [norm_target] if norm_target in all_tests or norm_target.endswith(".py") else []
        blast_score = 0.0
        severity = "LOW"
        total_impacted_modules = 1
    else:
        # Production module blast radius analysis
        from ultron.core import analyzer
        from ultron.core.blast_radius import BlastRadiusTracer

        codebase = analyzer.analyze_directory(abs_repo)
        nodes, edges = _build_exact_dependency_edges(codebase)

        upstream = BlastRadiusTracer.find_upstream_dependencies(
            nodes=nodes,
            edges=edges,
            target_id=norm_target,
            max_depth=max_depth
        )
        direct_callers = upstream.get("direct_parents", [])
        transitive_callers = upstream.get("transitive_parents", [])

        blast_info = BlastRadiusTracer.compute_blast_radius_score(
            target_id=norm_target,
            nodes=nodes,
            edges=edges,
            max_depth=max_depth
        )
        blast_score = float(blast_info.get("blast_score", 0.0))
        total_impacted_modules = int(blast_info.get("total_impacted_modules", len(direct_callers) + len(transitive_callers)))

        affected_files = sorted(list({norm_target} | set(direct_callers) | set(transitive_callers)))

        # Condition 6: Deterministic severity classification
        if blast_score >= 15.0 or total_impacted_modules > 8:
            severity = "HIGH"
        elif blast_score >= 5.0 or total_impacted_modules >= 3:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        # Map affected files to corresponding test suites
        affected_tests = _map_affected_files_to_tests(abs_repo, affected_files, all_tests)

    # 6. Test runner selection and synthesis (Condition 7)
    chosen_runner = _detect_test_runner(abs_repo) if runner == "auto" else runner
    recommended_cmd = _synthesize_test_command(chosen_runner, affected_tests)

    explanation = (
        f"{len(affected_files)} file(s) affected by changes to '{norm_target}'. "
        f"{len(affected_tests)} mapped test file(s) identified."
        if affected_tests
        else f"{len(affected_files)} file(s) affected by changes to '{norm_target}'. "
        f"No mapped test files found for affected modules."
    )

    # 7. Output Emission
    if json_output:
        res_payload = {
            "schema_version": "1.0.0",
            "status": "success",
            "target_file": norm_target,
            "severity": severity,
            "blast_score": blast_score,
            "affected_files": affected_files,
            "affected_files_count": len(affected_files),
            "affected_tests": affected_tests,
            "affected_tests_count": len(affected_tests),
            "direct_callers": direct_callers,
            "transitive_callers": transitive_callers,
            "recommended_test_command": recommended_cmd,
            "runner": chosen_runner,
            "explanation": explanation
        }
        print(json.dumps(res_payload, indent=2))
        return 0

    # Console HUD presentation
    print("=" * 80)
    print("[ULTRON] DIFFERENTIAL IMPACT SIMULATOR")
    print("=" * 80)
    print(f"Target File:      {norm_target}")
    print(f"Impact Severity:  {severity} (Blast Score: {blast_score:.2f})")
    print(f"Affected Modules: {len(affected_files)} production file(s)")
    print(f"Mapped Tests:     {len(affected_tests)} test suite(s)")

    if direct_callers:
        print(f"\n[+] Direct Callers ({len(direct_callers)}):")
        for c in direct_callers:
            print(f"  - {c}")

    if transitive_callers:
        print(f"\n[+] Transitive Callers ({len(transitive_callers)}):")
        for c in transitive_callers:
            print(f"  - {c}")

    if affected_tests:
        print(f"\n[+] Affected Test Suites ({len(affected_tests)}):")
        for t in affected_tests:
            print(f"  - {t}")
    else:
        print(f"\n[!] Notice: No mapped test files found. Test coverage gap detected for affected files.")

    print(f"\n[+] Recommended Test Execution Command:")
    print(f"  {recommended_cmd}")
    print("=" * 80)
    return 0
