"""
Ultron Historical Bug Prediction Validation & Precision/Recall Calibration Engine
Campaign 24 — Git Log Correlation, Precision/Recall Metrics & Disjoint Evaluation
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Set

class BugPredictionValidator:
    @staticmethod
    def extract_bug_fix_files(repo_path: str = ".") -> Set[str]:
        """Extracts set of files modified in git commits matching bug fix keywords."""
        norm_path = os.path.normpath(os.path.abspath(repo_path))
        if not os.path.exists(os.path.join(norm_path, ".git")):
            return set()

        try:
            cmd = ["git", "-C", norm_path, "log", "--grep=fix\\|bug\\|issue\\|patch", "-i", "--name-only", "--pretty=format:"]
            output = subprocess.check_output(cmd, text=True, encoding="utf-8", errors="ignore")
            fix_files = {line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()}
            return fix_files
        except Exception:
            return set()

    @classmethod
    def evaluate_predictions(cls, predicted_high_risk_files: List[str], repo_path: str = ".") -> Dict[str, Any]:
        """
        Evaluates Precision, Recall, and F1 Score of high-risk predictions against git bug fix history.
        Includes zero-division safety guards.
        """
        norm_path = os.path.normpath(os.path.abspath(repo_path))
        if not os.path.exists(os.path.join(norm_path, ".git")):
            return {
                "status": "inactive",
                "reason": "No git repository found in target directory.",
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0
            }

        fix_files = cls.extract_bug_fix_files(norm_path)
        if not fix_files:
            return {
                "status": "inactive",
                "reason": "No bug fix commits identified in git history.",
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0
            }

        pred_set = {f.replace("\\", "/") for f in predicted_high_risk_files}
        
        tp = len(pred_set.intersection(fix_files))
        fp = len(pred_set - fix_files)
        fn = len(fix_files - pred_set)

        precision = round(tp / max(1.0, float(tp + fp)), 3) if (tp + fp) > 0 else 0.0
        recall = round(tp / max(1.0, float(tp + fn)), 3) if (tp + fn) > 0 else 0.0
        f1 = round((2 * precision * recall) / max(0.001, (precision + recall)), 3) if (precision + recall) > 0 else 0.0

        return {
            "status": "active",
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": precision,
            "recall": recall,
            "f1_score": f1
        }
