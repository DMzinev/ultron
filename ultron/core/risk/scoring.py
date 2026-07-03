"""
risk/scoring.py — Main risk evaluation engine.

Responsibility: evaluate_risks()

Composes historical (I/O) + metrics (computation) + logistic (confidence)
to produce AnalysisPacket results for a list of target files.

The lazy `import analyzer` inside evaluate_risks is preserved to prevent
a circular import (analyzer imports risk, so risk cannot import analyzer
at module level).
"""
import os
import math

from models import AnalysisPacket
import logistic
from .historical import load_mkr_stats, load_human_feedback
from .metrics import get_file_complexity


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

    risks = []

    # Lazy import to prevent circular dependency (analyzer imports risk at module level)
    import analyzer
    bug_fixes = {}
    if repo_path:
        try:
            bug_fixes = analyzer.extract_git_history(repo_path)
        except Exception as e:
            print(f"Warning: failed to extract git history from {repo_path}: {e}")

    feedback = load_human_feedback()

    # Build global callers map once for all targets
    global_callers = {}
    for rel_path, analysis in codebase.items():
        for defn in analysis.get("definitions", []):
            for call in defn.get("calls", []):
                global_callers.setdefault(call, []).append(rel_path)
            if defn.get("type") == "class":
                for method in defn.get("methods", []):
                    for call in method.get("calls", []):
                        global_callers.setdefault(call, []).append(rel_path)

    for target in target_files:
        if target not in codebase:
            continue
        analysis = codebase[target]
        target_defs = analysis.get("definitions", [])

        downstream_files = []
        for defn in target_defs:
            name = defn.get("name")
            if name in global_callers:
                downstream_files.extend(global_callers[name])
            if defn.get("type") == "class":
                for method in defn.get("methods", []):
                    m_name = method.get("name")
                    if m_name in global_callers:
                        downstream_files.extend(global_callers[m_name])
        downstream_files = list(set(downstream_files))
        if target in downstream_files:
            downstream_files.remove(target)

        coupling_count = len(downstream_files)
        abs_target = os.path.join(repo_path, target) if repo_path else target
        complexity = get_file_complexity(abs_target)
        impact_score = complexity * math.log(math.e + coupling_count)
        is_public = target.endswith("__init__.py") or any(
            defn.get("name") == "__init__" for defn in target_defs
        )

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

        if impact_score >= high_t or is_public:
            level = "HIGH"
            mitigation = (
                f"Critical boundary. Impact Score: {impact_score:.2f} "
                f"(Threshold: {high_t:.2f}, Complexity: {complexity}, "
                f"Coupling: {coupling_count}). "
                f"Do NOT modify signatures without simultaneously refactoring callers."
            )
        elif impact_score >= med_t:
            level = "MEDIUM"
            mitigation = (
                f"Moderate coupling. Impact Score: {impact_score:.2f} "
                f"(Threshold: {med_t:.2f}, Complexity: {complexity}, "
                f"Coupling: {coupling_count}). "
                f"Review callers: {', '.join(downstream_files)}."
            )
        else:
            level = "LOW"
            mitigation = (
                f"Low risk leaf module. Impact Score: {impact_score:.2f} "
                f"(Complexity: {complexity}, Coupling: {coupling_count}). "
                f"Safe to modify."
            )

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
            callers=downstream_files,
        ))

    return risks
