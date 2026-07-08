"""
risk/diff.py — Diff-level risk analysis engine.

Responsibility: evaluate_diff_risk()

Compares old vs new code AST structures to compute function-level delta
impact scores (Delta I). Composed from metrics (AST parsing) and
historical (MKR loading).
"""
import os
import math

from ultron.core.models import AnalysisPacket
from .metrics import extract_ast_blocks, get_code_complexity
from .historical import load_mkr_stats


def evaluate_diff_risk(codebase, filepath, old_code, new_code):
    """
    Compares old vs new AST structures to compute function-level delta impact scores.

    Args:
        codebase:  output of analyzer.analyze_directory (used for coupling calculation)
        filepath:  relative path of the changed file (used for MKR lookup)
        old_code:  original source code string
        new_code:  updated source code string

    Returns:
        AnalysisPacket with .changes (list of per-function deltas) and .delta_score

    Raises:
        ValueError if filepath, old_code, or new_code is None
    """
    if filepath is None:
        raise ValueError("filepath cannot be None")
    if old_code is None:
        raise ValueError("old_code cannot be None")
    if new_code is None:
        raise ValueError("new_code cannot be None")

    old_blocks = extract_ast_blocks(old_code)
    new_blocks = extract_ast_blocks(new_code)

    # Build global callers map for coupling calculation
    global_callers = {}
    for rel_path, analysis in codebase.items():
        for defn in analysis.get("definitions", []):
            for call in defn.get("calls", []):
                global_callers.setdefault(call, []).append(rel_path)
            if defn.get("type") == "class":
                for method in defn.get("methods", []):
                    for call in method.get("calls", []):
                        global_callers.setdefault(call, []).append(rel_path)

    changes = []
    total_delta = 0.0
    all_names = set(old_blocks.keys()).union(new_blocks.keys())

    for name in all_names:
        action = None
        block_type = None
        comp_before = 0
        comp_after = 0

        if name in new_blocks and name not in old_blocks:
            action = "added"
            block_type = new_blocks[name]["type"]
            comp_after = new_blocks[name]["complexity"]
        elif name in old_blocks and name not in new_blocks:
            action = "deleted"
            block_type = old_blocks[name]["type"]
            comp_before = old_blocks[name]["complexity"]
        else:
            block_type = new_blocks[name]["type"]
            comp_before = old_blocks[name]["complexity"]
            comp_after = new_blocks[name]["complexity"]
            if old_blocks[name]["code"] != new_blocks[name]["code"]:
                action = "modified"

        if action:
            coupling = len(set(global_callers.get(name, [])))
            impact_before = comp_before * math.log(math.e + coupling) if comp_before > 0 else 0.0
            impact_after = comp_after * math.log(math.e + coupling) if comp_after > 0 else 0.0
            delta = impact_after - impact_before
            total_delta += delta
            changes.append({
                "name": name,
                "type": block_type,
                "action": action,
                "complexity_before": comp_before,
                "complexity_after": comp_after,
                "coupling": coupling,
                "impact_before": impact_before,
                "impact_after": impact_after,
                "delta": delta,
            })

    mkr_map = load_mkr_stats()
    mkr = 1.0
    target_base = os.path.basename(filepath)
    for k, v in mkr_map.items():
        if os.path.basename(k) == target_base:
            mkr = v
            break

    confidence = mkr / (1.0 + 0.1 * abs(total_delta))

    return AnalysisPacket(
        file_path=filepath,
        impact_score=total_delta,
        coupling_score=0.0,
        mk_r=mkr,
        delta_cest=0.0,
        confidence=confidence,
        changes=changes,
        delta_score=total_delta,
    )
