"""
Ultron Historical Bug Prediction Validation & Precision/Recall Calibration Engine
Campaign 24 — Git Log Correlation, Precision/Recall Metrics & Multi-Signal Filtering
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Set

class BugPredictionValidator:
    @staticmethod
    def extract_bug_fix_files(repo_path: str = ".") -> Set[str]:
        """
        Extracts set of files modified in git commits matching bug fix keywords,
        while filtering out doc/typo commits (docs:, typo, readme, license, formatting).
        """
        norm_path = os.path.normpath(os.path.abspath(repo_path)).replace("\\", "/")
        if not os.path.exists(os.path.join(norm_path, ".git")):
            return set()

        try:
            cmd = ["git", "-C", norm_path, "log", '--pretty=format:COMMIT:%H%nSUBJECT:%s', "--name-only"]
            output = subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace")
            
            fix_files: Set[str] = set()
            current_subject = ""
            bug_keywords = ["fix", "bug", "issue", "patch", "revert"]
            ignore_keywords = ["docs:", "typo", "readme", "license", "formatting"]

            for line in output.splitlines():
                line_str = line.strip()
                if not line_str:
                    continue
                if line_str.startswith("SUBJECT:"):
                    current_subject = line_str[8:].lower()
                elif line_str.startswith("COMMIT:"):
                    pass
                else:
                    # Line is a modified file path
                    is_bug_commit = any(k in current_subject for k in bug_keywords)
                    is_doc_typo = any(k in current_subject for k in ignore_keywords)
                    if is_bug_commit and not is_doc_typo:
                        fix_files.add(line_str.replace("\\", "/"))

            return fix_files
        except Exception as err:
            sys.stderr.write(f"[Bug Prediction Warning] Failed to extract git history: {err}\n")
            return set()

    @classmethod
    def evaluate_predictions(cls, predicted_high_risk_files: List[str], repo_path: str = ".") -> Dict[str, Any]:
        """
        Evaluates Precision, Recall, and F1 Score of high-risk predictions against git bug fix history.
        Includes zero-division safety guards.
        """
        norm_path = os.path.normpath(os.path.abspath(repo_path)).replace("\\", "/")
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
