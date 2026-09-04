"""
ultron.core.refactoring_roi
Deterministic refactoring return-on-investment (ROI) calculations and LOC effort estimation.
"""

from typing import Dict, List, Any, Optional


def norm_path(path_str: Any) -> str:
    """Normalizes paths to POSIX forward slashes."""
    return str(path_str or "").replace("\\", "/").strip()


class RefactoringROIEngine:
    """
    Deterministic mathematical engine evaluating refactoring leverage across codebase modules.
    Computes ROI, effort budget in LOC, projected risk reduction %, and opportunity tiers.
    """

    FORMULA_VERSION = "1.0-deterministic-ast"

    @classmethod
    def estimate_refactor_effort_loc(
        cls,
        complexity: float,
        coupling: float,
        total_loc: Optional[int] = None
    ) -> int:
        """
        Estimates a realistic Lines of Code (LOC) refactoring budget based on AST metrics.
        """
        c = max(0.0, float(complexity or 0.0))
        k = max(0.0, float(coupling or 0.0))

        if c == 0.0 and k == 0.0:
            return 1

        # Heuristic baseline: 3 LOC per complexity point + 2.5 LOC per coupling fanout
        estimated = int(round(max(5.0, c * 3.0 + k * 2.5)))

        if total_loc is not None and total_loc > 0:
            return max(1, min(int(total_loc), estimated))
        return max(1, estimated)

    @classmethod
    def compute_module_roi(
        cls,
        module_risk: Dict[str, Any],
        node_facts: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Computes deterministic ROI score, projected risk reduction %, and opportunity tier for a module.
        """
        if not isinstance(module_risk, dict):
            module_risk = {}

        file_path = norm_path(
            module_risk.get("file_path") or
            module_risk.get("file") or
            module_risk.get("id") or
            "unknown"
        )
        file_name = file_path.split("/")[-1] if file_path else "unknown"

        complexity = float(
            module_risk.get("complexity") or
            module_risk.get("mccabe_complexity") or
            0.0
        )
        coupling = float(
            module_risk.get("coupling_score") or
            module_risk.get("coupling") or
            module_risk.get("fanout") or
            0.0
        )
        impact = float(
            module_risk.get("impact_score") or
            module_risk.get("score") or
            module_risk.get("risk_score") or
            0.0
        )
        raw_loc = module_risk.get("loc") or module_risk.get("lines_of_code")
        total_loc = int(raw_loc) if raw_loc is not None else None

        effort_loc = cls.estimate_refactor_effort_loc(complexity, coupling, total_loc)

        # ROI formula: ((K * 0.6 + C * 0.4) * Impact) / max(1, Effort_LOC) * 10
        raw_numerator = (coupling * 0.6 + complexity * 0.4) * impact
        roi_score = round((raw_numerator / max(1, effort_loc)) * 10.0, 2)

        # Projected Risk Reduction %
        if complexity > 4.0:
            reduction_pct = min(75.0, max(0.0, round(((complexity - 4.0) / complexity) * 100.0, 1)))
        else:
            reduction_pct = 0.0

        # Opportunity Tier Categorization
        if roi_score >= 5.0 and effort_loc <= 35:
            tier = "HIGH_LEVERAGE_QUICK_WIN"
            tier_label = "⚡ High-Leverage Quick Win"
        elif impact >= 4.0 or coupling >= 5.0:
            tier = "DEEP_ARCHITECTURAL_DECOUPLING"
            tier_label = "🏗️ Deep Architectural Decoupling"
        else:
            tier = "ROUTINE_CLEANUP"
            tier_label = "🧹 Routine Cleanup"

        return {
            "file_path": file_path,
            "file_name": file_name,
            "complexity": complexity,
            "coupling": coupling,
            "impact_score": impact,
            "estimated_loc": effort_loc,
            "roi_score": roi_score,
            "projected_risk_reduction_pct": reduction_pct,
            "tier": tier,
            "tier_label": tier_label,
            "provenance": {
                "formula_version": cls.FORMULA_VERSION,
                "raw_numerator": round(raw_numerator, 3),
                "denominator_loc": effort_loc
            }
        }

    @classmethod
    def rank_refactoring_opportunities(
        cls,
        risks: List[Dict[str, Any]],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Ranks all codebase modules by calculated refactoring ROI descending.
        """
        if not risks or not isinstance(risks, list):
            return []

        evaluated = []
        for r in risks:
            roi_data = cls.compute_module_roi(r)
            if roi_data["roi_score"] > 0.0 or roi_data["impact_score"] > 0.0:
                evaluated.append(roi_data)

        # Deterministic sort: ROI descending, then impact descending, then path ascending
        evaluated.sort(key=lambda x: (-x["roi_score"], -x["impact_score"], x["file_path"]))
        return evaluated[:limit]
