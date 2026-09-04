"""
risk/scoring.py — Main risk evaluation engine.

Responsibility: evaluate_risks()

Composes historical (I/O) + metrics (computation) + logistic (confidence)
to produce AnalysisPacket results for a list of target files.

The lazy `import analyzer` inside evaluate_risks is preserved to prevent
a circular import (analyzer imports risk, so risk cannot import analyzer
at module level).
"""
import ast
import os
import math
import sys

from ultron.core.models import AnalysisPacket, ArchitecturalRole, ChangeStrategy
from ultron.core.io import read_text
from ultron.core import logistic
from .historical import load_mkr_stats, load_human_feedback
from .metrics import get_file_complexity


# ---------------------------------------------------------------------------
# Public-module detection
# ---------------------------------------------------------------------------

def exports_via_all(abs_path):
    """
    Return True if the file defines __all__ at module level.

    Checks both plain assignments and type-annotated assignments.
    Also checks immediate children of top-level if/try blocks.
    Returns False on any exception (syntax error, missing file, directory, etc.).
    """
    try:
        src = read_text(abs_path)
        tree = ast.parse(src)
    except Exception:
        return False

    def _is_all_assignment(node):
        if isinstance(node, ast.Assign):
            return any(
                isinstance(t, ast.Name) and t.id == "__all__"
                for t in node.targets
            )
        if isinstance(node, ast.AnnAssign):
            return isinstance(node.target, ast.Name) and node.target.id == "__all__"
        return False

    for node in tree.body:
        if _is_all_assignment(node):
            return True
        # Also check immediate children of top-level if/try (conditional exports)
        if isinstance(node, (ast.If, ast.Try)):
            children = list(getattr(node, "body", [])) + list(getattr(node, "orelse", []))
            if isinstance(node, ast.Try):
                for handler in getattr(node, "handlers", []):
                    children.extend(getattr(handler, "body", []))
                children.extend(getattr(node, "finalbody", []))
            for child in children:
                if _is_all_assignment(child):
                    return True
    return False


# ---------------------------------------------------------------------------
# Ordered rules engine for architectural role
# ---------------------------------------------------------------------------

def _make_rules():
    """
    Returns an ordered list of (predicate, ArchitecturalRole) pairs.
    First match wins. Add new roles here — do not grow evaluate_risks().
    """
    def ends_init(p, _abs):      return p.endswith("__init__.py")
    def is_test(p, _abs):        return "tests/" in p or p.startswith("test_") or p.endswith("_test.py") or "/test_" in p
    def is_public(p, abs_p):     return bool(abs_p) and exports_via_all(abs_p)
    def is_experimental(p, _):   return "experimental" in p or "synapse_project" in p
    def is_cli(p, _abs):         return p in ("ultron/interfaces/ultron.py", "start_ultron.py")
    def is_server(p, _abs):      return p == "ultron/interfaces/server.py"
    def is_mcp(p, _abs):         return p == "ultron/interfaces/mcp_server.py"
    def is_core(p, _abs):        return p.startswith("ultron/core/")
    def is_script(p, _abs):      return p.startswith("scratch/")

    return [
        (ends_init,      ArchitecturalRole.PACKAGE_INITIALIZER),
        (is_test,        ArchitecturalRole.TEST),
        (is_public,      ArchitecturalRole.PUBLIC_MODULE),
        (is_experimental,ArchitecturalRole.EXPERIMENTAL),
        (is_cli,         ArchitecturalRole.CLI),
        (is_server,      ArchitecturalRole.SERVER),
        (is_mcp,         ArchitecturalRole.MCP_TOOL),
        (is_core,        ArchitecturalRole.CORE_ENGINE),
        (is_script,      ArchitecturalRole.SCRIPT),
    ]


_ROLE_RULES = _make_rules()


def determine_architectural_role(rel_path, abs_path=""):
    """Classify a file's architectural role via the ordered rules engine."""
    if not rel_path:
        return ArchitecturalRole.INTERNAL
    normalized = os.path.normpath(rel_path).replace(os.sep, "/").replace("\\", "/")
    for predicate, role in _ROLE_RULES:
        if predicate(normalized, abs_path):
            return role
    return ArchitecturalRole.INTERNAL


# ---------------------------------------------------------------------------
# Change strategy matrix
# ---------------------------------------------------------------------------

# (ArchitecturalRole, risk_level) → ChangeStrategy
# Use sentinel "*" for "any level".
_STRATEGY_MATRIX = {
    (ArchitecturalRole.PACKAGE_INITIALIZER, "*"):    ChangeStrategy.REQUIRES_COMPATIBILITY_REVIEW,
    (ArchitecturalRole.TEST,               "*"):    ChangeStrategy.SAFE_EDIT,
    (ArchitecturalRole.SCRIPT,             "*"):    ChangeStrategy.SAFE_EDIT,
    (ArchitecturalRole.EXPERIMENTAL,       "*"):    ChangeStrategy.LOCAL_REFACTOR,

    (ArchitecturalRole.PUBLIC_MODULE,      "HIGH"): ChangeStrategy.REQUIRES_COMPATIBILITY_REVIEW,
    (ArchitecturalRole.PUBLIC_MODULE,      "MEDIUM"):ChangeStrategy.LOCAL_REFACTOR,
    (ArchitecturalRole.PUBLIC_MODULE,      "LOW"):  ChangeStrategy.LOCAL_REFACTOR,

    (ArchitecturalRole.CLI,                "HIGH"): ChangeStrategy.REQUIRES_COMPATIBILITY_REVIEW,
    (ArchitecturalRole.CLI,                "MEDIUM"):ChangeStrategy.LOCAL_REFACTOR,
    (ArchitecturalRole.CLI,                "LOW"):  ChangeStrategy.LOCAL_REFACTOR,

    (ArchitecturalRole.SERVER,             "HIGH"): ChangeStrategy.REQUIRES_COMPATIBILITY_REVIEW,
    (ArchitecturalRole.SERVER,             "MEDIUM"):ChangeStrategy.LOCAL_REFACTOR,
    (ArchitecturalRole.SERVER,             "LOW"):  ChangeStrategy.LOCAL_REFACTOR,

    (ArchitecturalRole.MCP_TOOL,           "HIGH"): ChangeStrategy.REQUIRES_COMPATIBILITY_REVIEW,
    (ArchitecturalRole.MCP_TOOL,           "MEDIUM"):ChangeStrategy.LOCAL_REFACTOR,
    (ArchitecturalRole.MCP_TOOL,           "LOW"):  ChangeStrategy.LOCAL_REFACTOR,

    (ArchitecturalRole.CORE_ENGINE,        "HIGH"): ChangeStrategy.INCREMENTAL_REFACTOR,
    (ArchitecturalRole.CORE_ENGINE,        "MEDIUM"):ChangeStrategy.LOCAL_REFACTOR,
    (ArchitecturalRole.CORE_ENGINE,        "LOW"):  ChangeStrategy.LOCAL_REFACTOR,

    (ArchitecturalRole.INTERNAL,           "HIGH"): ChangeStrategy.LOCAL_REFACTOR,
    (ArchitecturalRole.INTERNAL,           "MEDIUM"):ChangeStrategy.SAFE_EDIT,
    (ArchitecturalRole.INTERNAL,           "LOW"):  ChangeStrategy.SAFE_EDIT,
}


def get_change_strategy(role, level):
    """Return the ChangeStrategy for a given role + risk level."""
    return (
        _STRATEGY_MATRIX.get((role, "*"))
        or _STRATEGY_MATRIX.get((role, level))
        or ChangeStrategy.SAFE_EDIT
    )


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

def evaluate_risks(codebase, target_files, intent="", repo_path="", os=os):
    """
    Evaluates integration risks for targeted files based on global coupling and complexity.

    Args:
        codebase:     output of analyzer.analyze_directory
        target_files: list of relative file paths to evaluate
        intent:       natural language user request description (used for auto-targeting)
        repo_path:    absolute path of the repository to resolve files for complexity analysis
        os:           injected os module (default: os) — allows mocking in tests

    Returns:
        list[AnalysisPacket]
    """
    if not codebase:
        return []

    target_files = [t.replace("\\", "/") for t in target_files]
    caller_had_targets = bool(target_files)
    caller_had_intent = bool(intent)

    if not target_files and intent:
        keywords = [w.lower() for w in intent.split() if len(w) > 3]
        for rel_path, analysis in codebase.items():
            match = False
            for kw in keywords:
                if kw in rel_path.lower():
                    match = True
                    break
                for defn in analysis.get("definitions", []):
                    if kw in defn.get("name", "").lower():
                        match = True
                        break
                    if defn.get("type") == "class":
                        for m in defn.get("methods", []):
                            if kw in m.get("name", "").lower():
                                match = True
                                break
            if match:
                target_files.append(rel_path.replace("\\", "/"))
        target_files = list(set(target_files))

    # Full-repo scan: only when caller provided neither targets nor intent
    if not target_files and not caller_had_targets and not caller_had_intent:
        target_files = [k.replace("\\", "/") for k in codebase.keys()]

    if not target_files:
        return []

    risks = []

    # v2.5 Canonical GitEvidenceAdapter Integration
    from ultron.core.git_adapter import GitEvidenceAdapter
    bug_fixes = {}
    if repo_path:
        try:
            adapter = GitEvidenceAdapter()
            evidence_records = adapter.parse_git_history(repo_path)
            for ev in evidence_records:
                rel_f = ev.source.get("file", "").replace("\\", "/")
                n_fixes = ev.measurement.get("bug_fixes", 0)
                if rel_f and n_fixes > 0:
                    bug_fixes[rel_f] = n_fixes
        except Exception as e:
            print(f"Warning: failed to extract git history from {repo_path}: {e}")

    feedback = load_human_feedback()

    # Detect circular dependencies across codebase via CycleDetector
    cycle_files = set()
    try:
        from ultron.core.cycle_detector import CycleDetector
        mod_map = {}
        for f in codebase:
            norm_f = f.replace("\\", "/")
            base = os.path.splitext(os.path.basename(norm_f))[0]
            if base != "__init__":
                mod_map[base] = norm_f
            mod_path = norm_f[:-3].replace("/", ".") if norm_f.endswith(".py") else norm_f.replace("/", ".")
            mod_map[mod_path] = norm_f

        edges = []
        for f, analysis in codebase.items():
            norm_f = f.replace("\\", "/")
            for imp in analysis.get("imports", []):
                parts = imp.split(".")
                for i in range(len(parts), 0, -1):
                    prefix = ".".join(parts[:i])
                    if prefix in mod_map:
                        tgt = mod_map[prefix]
                        if tgt != norm_f:
                            edges.append({"source": norm_f, "target": tgt})
                        break
        detected_cycles = CycleDetector.find_all_cycles(edges=edges)
        for c in detected_cycles:
            cycle_files.update(c.get("nodes", []))
    except Exception as e:
        sys.stderr.write(f"[Ultron] Warning: cycle detection unavailable ({type(e).__name__}: {e})\n")
        cycle_files = set()

    # Build global callers map once for all targets using set for O(1) deduplication
    global_callers = {}
    for rel_path, analysis in codebase.items():
        for defn in analysis.get("definitions", []):
            for call in defn.get("calls", []):
                global_callers.setdefault(call, set()).add(rel_path)
            if defn.get("type") == "class":
                for method in defn.get("methods", []):
                    for call in method.get("calls", []):
                        global_callers.setdefault(call, set()).add(rel_path)

    # Pre-compute metrics & raw impact scores for all files across codebase
    codebase_metrics = {}
    for f, analysis in codebase.items():
        target_defs = analysis.get("definitions", [])
        downstream_files = set()
        for defn in target_defs:
            name = defn.get("name")
            if name in global_callers:
                downstream_files.update(global_callers[name])
            if defn.get("type") == "class":
                for method in defn.get("methods", []):
                    m_name = method.get("name")
                    if m_name in global_callers:
                        downstream_files.update(global_callers[m_name])
        downstream_files.discard(f)
        coupling_count = len(downstream_files)
        abs_f = os.path.join(repo_path, f) if repo_path else f
        complexity = get_file_complexity(abs_f)
        cycle_mult = 2.0 if (f in cycle_files or f.replace("\\", "/") in cycle_files) else 1.0
        raw_score = complexity * math.log(math.e + coupling_count) * cycle_mult
        codebase_metrics[f] = {
            "complexity": complexity,
            "coupling_count": coupling_count,
            "downstream_files": downstream_files,
            "impact_score": raw_score,
            "abs_path": abs_f,
        }

    N = len(codebase)
    all_scores = [m["impact_score"] for m in codebase_metrics.values()]
    # Strict deterministic primary, secondary, tertiary tie-breaker:
    # (-impact_score, -complexity, file_path)
    sorted_files = sorted(
        codebase_metrics.keys(),
        key=lambda f: (-codebase_metrics[f]["impact_score"], -codebase_metrics[f]["complexity"], f)
    )
    has_high_outlier = any(s >= 10.0 for s in all_scores)
    has_med_outlier = any(s >= 3.0 for s in all_scores)
    max_high = max(1 if has_high_outlier else 0, math.ceil(0.15 * N)) if N > 0 else 0
    max_med_high = max(1 if has_med_outlier else 0, math.ceil(0.45 * N)) if N > 0 else 0

    HIGH_FLOOR = 10.0
    MED_FLOOR = 3.0

    for target in target_files:
        norm_target = target.replace("\\", "/")
        m = codebase_metrics.get(norm_target) or codebase_metrics.get(target)
        if not m:
            continue
        target_key = norm_target if norm_target in sorted_files else target
        complexity = m["complexity"]
        coupling_count = m["coupling_count"]
        downstream_files = m["downstream_files"]
        impact_score = m["impact_score"]
        abs_target = m["abs_path"]

        role = determine_architectural_role(target, abs_target)

        # Percentile rank within repository
        pct_rank = (sum(1 for s in all_scores if s <= impact_score) / N) * 100.0 if N > 0 else 100.0
        rank_1based = sorted_files.index(target_key) + 1 if target_key in sorted_files else 1
        top_pct = max(1, round((rank_1based / N) * 100)) if N > 0 else 1

        n_fixes = bug_fixes.get(target, 0)
        feedback_accurate = feedback.get(target, None)

        # Percentile cutoffs adjusted by bug fixes and human feedback
        high_p = 90.0 - 5.0 * n_fixes
        med_p = 65.0 - 3.0 * n_fixes
        if feedback_accurate is True:
            high_p -= 5.0
            med_p -= 3.0
        elif feedback_accurate is False:
            high_p += 5.0
            med_p += 3.0

        high_p = max(75.0, min(95.0, high_p))
        med_p = max(50.0, min(80.0, med_p))

        is_within_high_cap = rank_1based <= max_high
        is_within_med_cap = rank_1based <= max_med_high

        if impact_score >= HIGH_FLOOR and pct_rank >= high_p and is_within_high_cap:
            level = "HIGH"
            mitigation = (
                f"High risk implementation: in the top {top_pct}% of this repository by blast radius "
                f"(Impact Score: {impact_score:.2f}, Complexity: {complexity}, "
                f"Coupling: {coupling_count})."
            )
        elif impact_score >= MED_FLOOR and pct_rank >= med_p and is_within_med_cap:
            level = "MEDIUM"
            mitigation = (
                f"Moderate risk implementation: in the top {top_pct}% of this repository by blast radius "
                f"(Impact Score: {impact_score:.2f}, Complexity: {complexity}, "
                f"Coupling: {coupling_count})."
            )
        else:
            level = "LOW"
            mitigation = (
                f"Low risk implementation (Impact Score: {impact_score:.2f}, "
                f"Complexity: {complexity}, Coupling: {coupling_count})."
            )

        if role == ArchitecturalRole.PACKAGE_INITIALIZER:
            mitigation += " Public package boundary: changes may affect package imports."
        elif role == ArchitecturalRole.PUBLIC_MODULE:
            mitigation += " Exported public module: review __all__ before merging changes."

        change_strategy = get_change_strategy(role, level)

        mkr_map = load_mkr_stats()
        mkr = 1.0
        target_base = os.path.basename(target)
        for k, v in mkr_map.items():
            if os.path.basename(k) == target_base:
                mkr = v
                break

        try:
            defect_prob = logistic.predict_defect_probability(impact_score, mkr)
            confidence = 1.0 - defect_prob
        except Exception as e:
            # Do not fail silently: a broken model here previously looked identical to a
            # working one, which is how the KeyError on the coefficients file went
            # unnoticed. Fall back, but say so.
            sys.stderr.write(
                f"[Ultron] Logistic model unavailable ({type(e).__name__}: {e}); "
                f"using heuristic confidence fallback for {target}.\n"
            )
            confidence = mkr / (1.0 + 0.1 * impact_score)

        risks.append(AnalysisPacket(
            file_path=target,
            impact_score=impact_score,
            coupling_score=float(coupling_count),
            mk_r=mkr,
            delta_cest=0.0,
            confidence=confidence,
            level=level,
            complexity=complexity,
            mitigation=mitigation,
            callers=sorted(list(downstream_files)),
            architectural_role=role,
            change_strategy=change_strategy,
        ))

    return risks
