"""
Ultron Refactoring Impact & Maintenance Cost Estimator Engine
Campaign 23 — Actionable Refactoring Plans, Complexity Scores & Cost Reduction Metrics
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List

class RefactorEstimator:
    @staticmethod
    def calculate_cost_reduction(current_complexity: float, current_coupling: float, target_complexity: float = 5.0, target_coupling: float = 2.0) -> float:
        """
        Calculates estimated structural complexity reduction percentage using deterministic formula:
        Cost Reduction % = 100 * (1 - (target_comp * target_coup) / max(1, current_comp * current_coup))
        Bounded between 0.0% and 75.0%.
        """
        curr_prod = max(1.0, float(current_complexity) * float(current_coupling))
        target_prod = float(target_complexity) * float(target_coupling)
        
        reduction = 100.0 * (1.0 - (target_prod / curr_prod))
        return round(min(75.0, max(0.0, reduction)), 1)

    @classmethod
    def generate_refactoring_plan(cls, file_path: str, complexity: int, coupling: int, impact_score: float) -> Dict[str, Any]:
        """
        Generates an actionable step-by-step refactoring plan for a high-risk file.
        """
        norm_path = os.path.normpath(os.path.abspath(file_path)).replace("\\", "/") if file_path != ":memory:" else file_path
        file_name = os.path.basename(norm_path) if norm_path != ":memory:" else "memory_buffer"
        
        reduction_pct = cls.calculate_cost_reduction(complexity, coupling)
        
        refactor_tier = "LOW"
        if complexity > 15 or coupling > 8:
            refactor_tier = "HIGH"
        elif complexity > 8 or coupling > 4:
            refactor_tier = "MEDIUM"

        action_steps: List[str] = []
        if complexity > 10:
            action_steps.append(f"1. Decompose large functions in '{file_name}' to reduce McCabe complexity from {complexity} to <= 5.")
        if coupling > 5:
            action_steps.append(f"2. Decouple direct dependencies on external modules to reduce coupling from {coupling} to <= 2.")
        action_steps.append("3. Extract utility helper functions into decoupled module.")
        action_steps.append("4. Add unit test boundary assertions before modifying implementation.")

        return {
            "file": norm_path,
            "refactor_tier": refactor_tier,
            "structural_complexity_reduction_estimate_pct": reduction_pct,
            # Backward-compatible alias key for existing test/API consumers
            "estimated_maintenance_cost_reduction_pct": reduction_pct,
            "target_complexity": 5,
            "target_coupling": 2,
            "action_plan_steps": action_steps
        }
