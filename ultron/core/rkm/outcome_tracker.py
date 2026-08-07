"""
Ultron Closed-Loop Prediction vs Reality Outcome Tracker Engine
Campaign 25 — Outcome Tracking, Prediction Variance & Feedback Loops
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

class OutcomeTracker:
    @staticmethod
    def calculate_actual_reduction(baseline_complexity: float, current_complexity: float) -> float:
        """
        Calculates actual complexity reduction percentage post-refactor.
        Safe division clamp max(1.0, float(baseline_complexity)).
        """
        base_comp = max(1.0, float(baseline_complexity))
        curr_comp = max(0.0, float(current_complexity))
        reduction = 100.0 * (1.0 - (curr_comp / base_comp))
        return round(min(100.0, max(-100.0, reduction)), 1)

    @classmethod
    def evaluate_refactoring_outcome(cls, file_path: str, baseline_complexity: float, current_complexity: float, predicted_reduction_pct: float) -> Dict[str, Any]:
        """
        Compares predicted complexity reduction vs actual post-refactor complexity.
        Returns structured prediction_vs_reality_delta metrics.
        """
        norm_path = os.path.normpath(os.path.abspath(file_path)).replace("\\", "/") if file_path != ":memory:" else file_path
        
        actual_reduction_pct = cls.calculate_actual_reduction(baseline_complexity, current_complexity)
        variance_pct = round(abs(predicted_reduction_pct - actual_reduction_pct), 1)

        is_accurate = variance_pct <= 15.0 # Accurate if within 15% tolerance

        return {
            "status": "active",
            "file": norm_path,
            "baseline_complexity": baseline_complexity,
            "current_complexity": current_complexity,
            "predicted_reduction_pct": predicted_reduction_pct,
            "actual_reduction_pct": actual_reduction_pct,
            "variance_pct": variance_pct,
            "prediction_accurate": is_accurate,
            "feedback": "Prediction matched reality within tolerance." if is_accurate else f"Variance of {variance_pct}% detected between prediction and reality."
        }
