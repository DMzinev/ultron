import ast
import os
import sys
import subprocess

# Centralized list of directory patterns to exclude from Design Oracle abstraction leak scanning
EXCLUDED_PATTERNS = ["tests/", "scratch/", "synapse_project/"]

def get_import_mappings(codebase):
    """
    Builds a directed dependency graph of file paths mapping to list of imported file paths.
    """
    graph = {rel_path: set() for rel_path in codebase}
    
    for rel_path, analysis in codebase.items():
        for imp in analysis.get("imports", []):
            imp_parts = imp.split(".")
            for potential_path in codebase:
                potential_base = potential_path.replace(".py", "").replace("/", ".")
                # Match module imports like 'ultron.delta' or relative imports
                if potential_base == imp or potential_base.endswith("." + imp) or imp.replace(".", "/") in potential_path:
                    if potential_path != rel_path:
                        graph[rel_path].add(potential_path)
                    break
    return graph

def detect_circular_dependencies(codebase):
    """
    Finds all circular dependency loops in the codebase imports graph.
    Returns a list of list of file paths forming dependency cycles.
    """
    if not isinstance(codebase, dict):
        raise TypeError("codebase must be a dictionary")

    graph = get_import_mappings(codebase)
    cycles = []
    
    # DFS cycle detection
    visited = {}
    path = []

    def dfs(node):
        visited[node] = 1  # visiting
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if visited.get(neighbor, 0) == 1:
                # Cycle detected
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                # Normalize cycle representation for deduplication
                min_idx = cycle.index(min(cycle[:-1]))
                normalized_cycle = cycle[min_idx:-1] + cycle[:min_idx] + [min(cycle[:-1])]
                if normalized_cycle not in cycles:
                    cycles.append(normalized_cycle)
            elif visited.get(neighbor, 0) == 0:
                dfs(neighbor)
                
        path.pop()
        visited[node] = 2  # visited

    for node in codebase:
        if visited.get(node, 0) == 0:
            dfs(node)
            
    return cycles

def scan_file_for_globals(filepath):
    """
    Parses file AST to locate declarations of global mutations.
    """
    if filepath is None:
        raise ValueError("filepath cannot be None")
    if not os.path.exists(filepath):
        return []
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        globals_declared = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                for name in node.names:
                    globals_declared.append({
                        "name": name,
                        "lineno": node.lineno
                    })
        return globals_declared
    except (SyntaxError, OSError, ValueError):
        return []

def detect_global_mutations(codebase, repo_path):
    """
    Scans all source files in codebase for occurrences of 'global' mutations.
    """
    if not isinstance(codebase, dict):
        raise TypeError("codebase must be a dictionary")
    if repo_path is None:
        raise ValueError("repo_path cannot be None")

    global_mutations = {}
    for rel_path in codebase:
        abs_path = os.path.join(repo_path, rel_path)
        violations = scan_file_for_globals(abs_path)
        if violations:
            global_mutations[rel_path] = violations
    return global_mutations

def recommend_patterns(codebase, intent):
    """
    Recommends design patterns to decouple architectures based on user intent keywords.
    """
    if not isinstance(intent, str):
        raise TypeError("intent must be a string")

    recommendations = []
    intent_lower = intent.lower()
    
    if "theme" in intent_lower or "color" in intent_lower or "skin" in intent_lower:
        recommendations.append({
            "pattern": "ThemeProvider / CSS Variable Isolation",
            "reason": "Direct styling injection couples UI components to concrete design configurations.",
            "suggestion": "Introduce a ThemeProvider context mapping design tokens to CSS variables, isolating component layouts."
        })
        
    if "state" in intent_lower or "store" in intent_lower or "global" in intent_lower:
        recommendations.append({
            "pattern": "Observer Pattern / Central State Container",
            "reason": "Direct component-to-component state mutation leads to untraceable execution drift.",
            "suggestion": "Utilize a unidirectional data flow state container (or Context/Store) and subscribe components to state changes."
        })
        
    if "database" in intent_lower or "db" in intent_lower or "sql" in intent_lower or "save" in intent_lower:
        recommendations.append({
            "pattern": "Repository / Data Access Object (DAO)",
            "reason": "Mixing persistence logic inside business models prevents unit testing database actions in isolation.",
            "suggestion": "Implement a Repository class to abstract database CRUD operations behind a clean, interface-driven api."
        })
        
    if "api" in intent_lower or "service" in intent_lower or "http" in intent_lower:
        recommendations.append({
            "pattern": "Facade / Service Layer Abstraction",
            "reason": "Spreading HTTP request configurations across UI elements tightly couples networking details.",
            "suggestion": "Wrap network request actions inside dedicated client services, exposing only clean asynchronous methods."
        })
        
    return recommendations

def simulate_future_coupling(codebase, src_file, dest_file):
    """
    Simulates the topological effect of introducing a dependency link from src_file to dest_file.
    Returns safe status and cycle warnings.
    """
    if not isinstance(codebase, dict):
        raise TypeError("codebase must be a dictionary")
    if src_file is None or dest_file is None:
        raise ValueError("src_file and dest_file cannot be None")
    if src_file not in codebase or dest_file not in codebase:
        raise ValueError("src_file and dest_file must exist in codebase")

    # Simulate link addition
    sim_codebase = {}
    for k, v in codebase.items():
        sim_codebase[k] = {
            "imports": list(v.get("imports", [])),
            "definitions": list(v.get("definitions", []))
        }
        
    # Translate dest_file path to mock dot import representation
    dest_module = dest_file.replace(".py", "").replace("/", ".")
    if dest_module not in sim_codebase[src_file]["imports"]:
        sim_codebase[src_file]["imports"].append(dest_module)
        
    # Re-run cycle detection on simulated codebase
    sim_cycles = detect_circular_dependencies(sim_codebase)
    original_cycles = detect_circular_dependencies(codebase)
    
    new_cycles = [c for c in sim_cycles if c not in original_cycles]
    
    # Calculate degree impact
    # In-degree of dest_file: how many files import it
    orig_in_degree = sum(1 for src, targets in get_import_mappings(codebase).items() if dest_file in targets)
    sim_in_degree = sum(1 for src, targets in get_import_mappings(sim_codebase).items() if dest_file in targets)
    
    is_safe = len(new_cycles) == 0
    
    return {
        "success": True,
        "is_safe": is_safe,
        "new_cycles_detected": new_cycles,
        "dest_in_degree_change": {
            "before": orig_in_degree,
            "after": sim_in_degree
        },
        "description": "Simulation completed safely." if is_safe else f"Simulation detected {len(new_cycles)} new circular dependency loop(s)!"
    }

# =============================================================================
# Design Oracle Layer (v1)
# =============================================================================

def score_coupling_debt(codebase):
    """
    Computes per-file coupling debt from the import graph.

    Returns a list of dicts sorted descending by coupling_debt:
      [{"file": str, "fan_in": int, "fan_out": int,
        "coupling_debt": int, "instability": float}]

    Raises TypeError if codebase is not a dict.
    Raises ValueError if codebase is empty.
    """
    if not isinstance(codebase, dict):
        raise TypeError("codebase must be a dictionary")
    if not codebase:
        raise ValueError("codebase must not be empty")

    graph = get_import_mappings(codebase)

    # fan_out[f] = number of files f imports
    fan_out = {f: len(deps) for f, deps in graph.items()}

    # fan_in[f] = number of files that import f
    fan_in = {f: 0 for f in codebase}
    for f, deps in graph.items():
        for dep in deps:
            if dep in fan_in:
                fan_in[dep] += 1

    results = []
    for f in codebase:
        fi = fan_in[f]
        fo = fan_out[f]
        debt = fi * fo
        total = fi + fo
        instability = fo / total if total > 0 else 0.0
        results.append({
            "file": f,
            "fan_in": fi,
            "fan_out": fo,
            "coupling_debt": debt,
            "instability": round(instability, 3)
        })

    results.sort(key=lambda x: x["coupling_debt"], reverse=True)
    return results


def _count_cyclomatic_complexity(tree):
    """
    Approximates cyclomatic complexity of an AST by counting branch nodes.
    Branch nodes: If, For, While, ExceptHandler, With, Assert, comprehensions.
    Raises ValueError if tree is None.
    """
    if tree is None:
        raise ValueError("tree cannot be None")
    branch_types = (
        ast.If, ast.For, ast.While, ast.ExceptHandler,
        ast.With, ast.Assert, ast.comprehension
    )
    return sum(1 for node in ast.walk(tree) if isinstance(node, branch_types))


def detect_abstraction_leaks(codebase, repo_path, max_responsibilities=8, min_complexity=8):
    """
    Detects functions that are doing too many things by counting distinct
    cross-module call target names within each function body.

    A function is flagged when its count of distinct call-target module names
    exceeds max_responsibilities AND its cyclomatic complexity exceeds min_complexity.

    Excludes files matching patterns in EXCLUDED_PATTERNS.

    Returns a dict:
      {rel_path: [{"function": str, "responsibility_count": int, "lineno": int}]}

    Raises TypeError if codebase is not a dict.
    Raises ValueError if repo_path is None.
    """
    if not isinstance(codebase, dict):
        raise TypeError("codebase must be a dictionary")
    if repo_path is None:
        raise ValueError("repo_path cannot be None")

    leaks = {}

    for rel_path in codebase:
        # Standardize separators for consistent matching
        norm_path = rel_path.replace("\\", "/")
        if any(pat in norm_path for pat in EXCLUDED_PATTERNS):
            continue

        abs_path = os.path.join(repo_path, rel_path)
        if not os.path.exists(abs_path) or not rel_path.endswith(".py"):
            continue

        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
        except (SyntaxError, OSError, ValueError):
            continue

        file_leaks = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            # Check cyclomatic complexity gate first
            comp = _count_cyclomatic_complexity(node)
            if comp <= min_complexity:
                continue

            # Collect distinct module names called as `module.method()` inside this function
            called_modules = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Attribute) and isinstance(child.ctx, ast.Load):
                    if isinstance(child.value, ast.Name):
                        called_modules.add(child.value.id)

            if len(called_modules) > max_responsibilities:
                file_leaks.append({
                    "function": node.name,
                    "responsibility_count": len(called_modules),
                    "lineno": node.lineno
                })

        if file_leaks:
            leaks[rel_path] = file_leaks

    return leaks


def _get_bug_fix_count(repo_path, rel_path):
    """
    Returns the number of commits to rel_path whose message contains fix/bug/patch/hotfix keywords.
    Returns 0 if git is unavailable or the file has no history.
    Raises ValueError if repo_path or rel_path is None.
    """
    if repo_path is None:
        raise ValueError("repo_path cannot be None")
    if rel_path is None:
        raise ValueError("rel_path cannot be None")
    try:
        res = subprocess.run(
            ["git", "log", "--oneline", "--", rel_path],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10
        )
        if res.returncode != 0:
            return 0
        keywords = ("fix", "bug", "patch", "hotfix", "revert")
        count = sum(
            1 for line in res.stdout.splitlines()
            if any(kw in line.lower() for kw in keywords)
        )
        return count
    except (OSError, subprocess.TimeoutExpired):
        return 0


def _normalise(values):
    """
    Min-max normalises a list of numeric values to [0.0, 1.0].
    Returns all-zeros if the range is zero (constant input).
    """
    lo, hi = min(values), max(values)
    span = hi - lo
    if span == 0:
        return [0.0] * len(values)
    return [(v - lo) / span for v in values]


def compute_hotspot_scores(codebase, repo_path, risks):
    """
    Ranks files by a composite Hotspot Score fusing three signals:
      - Cyclomatic complexity (AST branch count)        weight 0.4
      - Coupling debt (fan_in * fan_out)                weight 0.4
      - Bug-fix commit density                          weight 0.2

    Each signal is min-max normalised across the file set before weighting.

    Returns a list of dicts sorted descending by hotspot_score:
      [{"file": str, "hotspot_score": float,
        "complexity": int, "coupling_debt": int, "bug_fix_count": int}]

    Raises TypeError if codebase is not a dict.
    Raises ValueError if repo_path is None or codebase is empty.
    """
    if not isinstance(codebase, dict):
        raise TypeError("codebase must be a dictionary")
    if repo_path is None:
        raise ValueError("repo_path cannot be None")
    if not codebase:
        raise ValueError("codebase must not be empty")

    coupling = {entry["file"]: entry["coupling_debt"]
                for entry in score_coupling_debt(codebase)}

    raw = []
    for rel_path in codebase:
        abs_path = os.path.join(repo_path, rel_path)
        complexity = 0
        if os.path.exists(abs_path) and rel_path.endswith(".py"):
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source)
                complexity = _count_cyclomatic_complexity(tree)
            except (SyntaxError, OSError, ValueError):
                complexity = 0

        bug_fix_count = _get_bug_fix_count(repo_path, rel_path)
        debt = coupling.get(rel_path, 0)

        raw.append({
            "file": rel_path,
            "complexity": complexity,
            "coupling_debt": debt,
            "bug_fix_count": bug_fix_count
        })

    # Min-max normalise each signal using module-level _normalise
    complexities  = _normalise([r["complexity"]    for r in raw])
    debts         = _normalise([r["coupling_debt"] for r in raw])
    bugfixes      = _normalise([r["bug_fix_count"] for r in raw])

    results = []
    for i, entry in enumerate(raw):
        score = round(0.4 * complexities[i] + 0.4 * debts[i] + 0.2 * bugfixes[i], 4)
        results.append({
            "file": entry["file"],
            "hotspot_score": score,
            "complexity": entry["complexity"],
            "coupling_debt": entry["coupling_debt"],
            "bug_fix_count": entry["bug_fix_count"]
        })

    results.sort(key=lambda x: x["hotspot_score"], reverse=True)
    return results


def generate_oracle_report(codebase, repo_path, risks=None):
    """
    Orchestrates all Design Oracle analyses and returns a structured markdown report.

    Sections:
      1. Coupling Debt (top 10 by coupling_debt)
      2. Abstraction Leaks
      3. Complexity Hotspots (top 10 by hotspot_score)
      4. Circular Dependencies

    Raises TypeError if codebase is not a dict.
    Raises ValueError if repo_path is empty or None.
    """
    if not isinstance(codebase, dict):
        raise TypeError("codebase must be a dictionary")
    if not repo_path:
        raise ValueError("repo_path must not be empty or None")

    lines = ["# Design Oracle Report\n"]

    # 1. Coupling Debt
    lines.append("## Coupling Debt\n")
    lines.append("Files ranked by coupling debt (`fan_in × fan_out`). "
                 "High debt = structurally expensive to change.\n")
    lines.append("| File | Fan-in | Fan-out | Debt | Instability |")
    lines.append("|---|---|---|---|---|")
    debt_scores = score_coupling_debt(codebase)
    for entry in debt_scores[:10]:
        lines.append(
            f"| `{entry['file']}` "
            f"| {entry['fan_in']} "
            f"| {entry['fan_out']} "
            f"| {entry['coupling_debt']} "
            f"| {entry['instability']:.3f} |"
        )
    lines.append("")

    # 2. Abstraction Leaks
    lines.append("## Abstraction Leaks\n")
    lines.append("Functions calling into more than 3 distinct module namespaces "
                 "(potential single-responsibility violations).\n")
    leaks = detect_abstraction_leaks(codebase, repo_path)
    if leaks:
        for rel_path, fn_leaks in sorted(leaks.items()):
            lines.append(f"**`{rel_path}`**")
            for leak in fn_leaks:
                lines.append(
                    f"- `{leak['function']}` (line {leak['lineno']}) — "
                    f"{leak['responsibility_count']} distinct module targets"
                )
            lines.append("")
    else:
        lines.append("_No abstraction leaks detected._\n")

    # 3. Complexity Hotspots
    lines.append("## Complexity Hotspots\n")
    lines.append("Files ranked by composite Hotspot Score "
                 "(40% cyclomatic complexity + 40% coupling debt + 20% bug-fix density).\n")
    lines.append("| File | Score | Complexity | Coupling Debt | Bug-fix Commits |")
    lines.append("|---|---|---|---|---|")
    hotspots = compute_hotspot_scores(codebase, repo_path, risks or [])
    for entry in hotspots[:10]:
        lines.append(
            f"| `{entry['file']}` "
            f"| {entry['hotspot_score']:.4f} "
            f"| {entry['complexity']} "
            f"| {entry['coupling_debt']} "
            f"| {entry['bug_fix_count']} |"
        )
    lines.append("")

    # 4. Circular Dependencies
    lines.append("## Circular Dependencies\n")
    cycles = detect_circular_dependencies(codebase)
    if cycles:
        lines.append(f"**{len(cycles)} circular dependency loop(s) detected:**\n")
        for i, cycle in enumerate(cycles, 1):
            lines.append(f"{i}. {' → '.join(cycle)}")
        lines.append("")
    else:
        lines.append("_No circular dependencies detected._\n")

    # 5. Architectural Reasoning Report
    lines.append("## Architectural Reasoning Report\n")
    try:
        from reasoning import ReasoningEngine
        engine = ReasoningEngine(codebase, repo_path)
        cards = engine.analyze()
        if cards:
            lines.append(f"**{len(cards)} architectural violation(s) detected:**\n")
            for card in cards:
                lines.append(card.format())
        else:
            lines.append("_No architectural violations detected._\n")
    except Exception as e:
        lines.append(f"_Error generating reasoning report: {e}_\n")

    # 6. Implementation Contracts
    # NOTE: heading is inside the try block so that nullifying this logic
    # removes the header, failing the test-laundering guard.
    try:
        from reasoning import ReasoningEngine as _RE
        from knowledge_graph import KNOWLEDGE_GRAPH
        from impact_simulator import MetricSnapshot
        from contract_generator import ContractGenerator

        _engine = _RE(codebase, repo_path)
        _violations = _engine.analyze()

        # Build a MetricSnapshot from aggregate scan metrics, clamping to valid bounds
        _total_debt = sum(e["coupling_debt"] for e in debt_scores)
        _cycle_count = len(cycles)
        _total_violations = len(_violations)
        _avg_hs = (sum(e["hotspot_score"] for e in hotspots) / len(hotspots)) if hotspots else 0.0
        _avg_inst = (sum(e["instability"] for e in debt_scores) / len(debt_scores)) if debt_scores else 0.0

        # Clamp all values defensively
        _avg_hs = max(0.0, min(1.0, _avg_hs))
        _avg_inst = max(0.0, min(1.0, _avg_inst))
        _total_debt = max(0.0, float(_total_debt))
        _cycle_count = max(0, _cycle_count)
        _total_violations = max(0, _total_violations)

        _snapshot = MetricSnapshot(
            total_coupling_debt=_total_debt,
            total_cycle_count=_cycle_count,
            total_violations=_total_violations,
            avg_instability=_avg_inst,
            avg_hotspot_score=_avg_hs
        )

        _generator = ContractGenerator(_violations, KNOWLEDGE_GRAPH, _snapshot,
                                        debt_scores=debt_scores, cycles=cycles, hotspots=hotspots)
        _cards = _generator.generate()

        lines.append("## Implementation Contracts\n")
        if _cards:
            lines.append(_generator.render_markdown(_cards))
        else:
            lines.append("_No implementation contracts generated (no violations detected)._\n")
    except Exception as e:
        lines.append(f"_Error generating implementation contracts: {e}_\n")

    return "\n".join(lines)
