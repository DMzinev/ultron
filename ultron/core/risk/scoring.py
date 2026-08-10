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
    target_files = list(target_files)
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
                target_files.append(rel_path)
        target_files = list(set(target_files))

    # Full-repo scan: only when caller provided neither targets nor intent
    if not target_files and not caller_had_targets and not caller_had_intent:
        target_files = list(codebase.keys())

    risks = []

    # v2.5 Canonical GitEvidenceAdapter Integration
    from ultron.core.git_adapter import GitEvidenceAdapter
    bug_fixes = {}
    if repo_path:
        try:
            adapter = GitEvidenceAdapter()
            evidence_records = adapter.parse_git_history(repo_path)
            for ev in evidence_records:
                rel_f = ev.source.get("file", "")
                n_fixes = ev.measurement.get("bug_fixes", 0)
                if rel_f and n_fixes > 0:
                    bug_fixes[rel_f] = n_fixes
        except Exception as e:
            print(f"Warning: failed to extract git history from {repo_path}: {e}")

    feedback = load_human_feedback()

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

    for target in target_files:
        if target not in codebase:
            continue
        analysis = codebase[target]
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
        downstream_files.discard(target)

        coupling_count = len(downstream_files)
        abs_target = os.path.join(repo_path, target) if repo_path else target
        complexity = get_file_complexity(abs_target)
        impact_score = complexity * math.log(math.e + coupling_count)

        # Architectural role via ordered rules engine
        role = determine_architectural_role(target, abs_target)

        n_fixes = bug_fixes.get(target, 0)
        feedback_accurate = feedback.get(target, None)

        # Dynamic thresholds — adjusted by bug-fix history and human feedback
        high_t = 10.0
        med_t = 3.0
        high_t -= 1.5 * n_fixes
        med_t -= 0.5 * n_fixes
        if feedback_accurate is True:
            high_t -= 2.0
            med_t -= 1.0
        elif feedback_accurate is False:
            high_t += 3.0
            med_t += 1.5
        high_t = max(3.0, min(15.0, high_t))
        med_t = max(1.0, min(8.0, med_t))

        if impact_score >= high_t:
            level = "HIGH"
            mitigation = (
                f"High risk implementation. Impact Score: {impact_score:.2f} "
                f"(Threshold: {high_t:.2f}, Complexity: {complexity}, "
                f"Coupling: {coupling_count})."
            )
        elif impact_score >= med_t:
            level = "MEDIUM"
            mitigation = (
                f"Moderate risk implementation. Impact Score: {impact_score:.2f} "
                f"(Threshold: {med_t:.2f}, Complexity: {complexity}, "
                f"Coupling: {coupling_count})."
            )
        else:
            level = "LOW"
            mitigation = (
                f"Low risk implementation. Impact Score: {impact_score:.2f} "
                f"(Complexity: {complexity}, Coupling: {coupling_count})."
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
        except Exception:
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
