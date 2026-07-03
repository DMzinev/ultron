"""
ultron/core/execution_kernel.py

The internal execution, verification, and reflection kernel for Ultron.
Runs plan, execute, verify, and reflect phases locally.
"""
import os
import sys
import json
import subprocess
import shlex
import ast
import time

import analyzer
from risk import evaluate_risks
from design_oracle import (
    score_coupling_debt,
    detect_abstraction_leaks,
    compute_hotspot_scores,
    detect_circular_dependencies,
)
from umags.checks import check_file_ast


class ExecutionKernel:
    def __init__(self, repo_path):
        """
        Initializes the ExecutionKernel with a target repository path.
        Raises ValueError if repo_path is not specified or None.
        """
        if not repo_path:
            raise ValueError("repo_path must be specified")
        self.repo_path = os.path.abspath(repo_path)
        self.backups = {}

    def plan(self, task_description):
        """
        Formulates an execution plan by targeting files based on keywords/intent
        within task_description, estimating risks, coupling debt, and design hotspots.

        Returns:
            dict containing target_files, risks, hotspots, circular_dependencies
        """
        if not task_description:
            raise ValueError("task_description cannot be empty")

        # Scan codebase
        codebase = analyzer.analyze_directory(self.repo_path)

        # Target mapping based on keyword match
        keywords = [w.lower() for w in task_description.split() if len(w) > 3]
        target_files = []
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

        # Evaluate risks
        risks = evaluate_risks(codebase, target_files, intent=task_description, repo_path=self.repo_path)
        risk_dicts = []
        for r in risks:
            risk_dicts.append({
                "file_path": r.file_path,
                "impact_score": r.impact_score,
                "level": r.level,
                "complexity": r.complexity,
                "coupling_score": r.coupling_score,
                "confidence": r.confidence,
                "mitigation": r.mitigation,
            })

        # Design metrics from Oracle
        hotspots = []
        circular_deps = []
        if codebase:
            try:
                hotspots = compute_hotspot_scores(codebase, self.repo_path, risks)
            except Exception as e:
                print(f"Warning: failed to compute hotspot scores: {e}", file=sys.stderr)
            try:
                circular_deps = detect_circular_dependencies(codebase)
            except Exception as e:
                print(f"Warning: failed to detect circular dependencies: {e}", file=sys.stderr)

        return {
            "target_files": target_files,
            "risks": risk_dicts,
            "hotspots": hotspots,
            "circular_dependencies": circular_deps,
        }

    def execute(self, file_edits):
        """
        Applies code edits to target files.
        file_edits: dict of {relative_filepath: new_code_string}

        Saves backups for rollbacks and reflection comparison.
        Returns True if all edits are applied successfully, False otherwise.
        """
        if not isinstance(file_edits, dict):
            raise TypeError("file_edits must be a dictionary")

        self.backups = {}
        for rel_path, new_code in file_edits.items():
            abs_path = os.path.join(self.repo_path, rel_path)

            # Backup existing
            original_code = None
            if os.path.exists(abs_path):
                try:
                    with open(abs_path, "r", encoding="utf-8") as f:
                        original_code = f.read()
                except OSError as e:
                    print(f"Warning: backup failed for {rel_path}: {e}", file=sys.stderr)

            self.backups[rel_path] = original_code

            # Ensure parent directories exist
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            try:
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(new_code)
            except OSError as e:
                print(f"Error: failed to write {rel_path}: {e}", file=sys.stderr)
                self.rollback()
                return False

        return True

    def rollback(self):
        """
        Reverts the changes made in the last execute() call using the backups.
        """
        for rel_path, original_code in self.backups.items():
            abs_path = os.path.join(self.repo_path, rel_path)
            if original_code is None:
                if os.path.exists(abs_path):
                    try:
                        os.remove(abs_path)
                    except OSError as e:
                        print(f"Warning: rollback failed to remove new file {rel_path}: {e}", file=sys.stderr)
            else:
                try:
                    with open(abs_path, "w", encoding="utf-8") as f:
                        f.write(original_code)
                except OSError as e:
                    print(f"Warning: rollback failed to write {rel_path}: {e}", file=sys.stderr)

    def verify(self, test_cmd="python ultron/tests/run_tests.py"):
        """
        Performs local verification of the applied changes.
        Returns:
            dict containing success, test_passed, scope_matched, ast_violations
        """
        # 1. Unit Tests
        test_passed = False
        try:
            parts = shlex.split(test_cmd, posix=(sys.platform != "win32"))
            res = subprocess.run(parts, capture_output=True, text=True, cwd=self.repo_path, timeout=90)
            test_passed = (res.returncode == 0)
        except Exception as e:
            print(f"Warning: verification test run failed: {e}", file=sys.stderr)
            test_passed = False

        # 2. Scope Checks
        scope_matched = True
        modified_files = set()
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=10
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if line.strip():
                        parts = line.strip().split(None, 1)
                        if len(parts) == 2:
                            modified_files.add(parts[1].replace("\\", "/"))
        except Exception as e:
            print(f"Warning: failed to retrieve git status: {e}", file=sys.stderr)

        active_edits = set(self.backups.keys())
        if not active_edits:
            active_edits = modified_files

        modified_sources = {f for f in modified_files if f.endswith(".py")}
        active_sources = {f for f in active_edits if f.endswith(".py")}

        if active_sources and not active_sources.issubset(modified_sources):
            scope_matched = False

        # 3. AST compliance checks on active edits
        ast_violations = {}
        for rel_path in active_edits:
            abs_path = os.path.join(self.repo_path, rel_path)
            if os.path.exists(abs_path) and rel_path.endswith(".py"):
                try:
                    violations = check_file_ast(abs_path)
                    if violations:
                        ast_violations[rel_path] = violations
                except Exception as e:
                    ast_violations[rel_path] = [{"line": 0, "rule": "ASTError", "message": f"AST check exception: {e}"}]

        success = test_passed and scope_matched and (not ast_violations)

        return {
            "success": success,
            "test_passed": test_passed,
            "scope_matched": scope_matched,
            "ast_violations": ast_violations,
        }

    def reflect(self, initial_plan):
        """
        Runs post-change design oracle evaluation and compares metrics
        against initial_plan to determine if design quality improved.
        """
        if not isinstance(initial_plan, dict):
            raise TypeError("initial_plan must be a dictionary")

        codebase = analyzer.analyze_directory(self.repo_path)
        hotspots = []
        circular_deps = []
        if codebase:
            try:
                target_files = initial_plan.get("target_files", [])
                risks = evaluate_risks(codebase, target_files, repo_path=self.repo_path)
                hotspots = compute_hotspot_scores(codebase, self.repo_path, risks)
            except Exception as e:
                print(f"Warning: failed to compute post-change hotspot scores: {e}", file=sys.stderr)
            try:
                circular_deps = detect_circular_dependencies(codebase)
            except Exception as e:
                print(f"Warning: failed to detect circular dependencies: {e}", file=sys.stderr)

        before_hotspots = {h["file"]: h for h in initial_plan.get("hotspots", [])}
        after_hotspots = {h["file"]: h for h in hotspots}

        delta_complexity = 0
        delta_coupling_debt = 0
        delta_hotspot_score = 0.0

        for f in after_hotspots:
            if f in before_hotspots:
                delta_complexity += (after_hotspots[f]["complexity"] - before_hotspots[f]["complexity"])
                delta_coupling_debt += (after_hotspots[f]["coupling_debt"] - before_hotspots[f]["coupling_debt"])
                delta_hotspot_score += (after_hotspots[f]["hotspot_score"] - before_hotspots[f]["hotspot_score"])

        summary = {
            "delta_complexity": delta_complexity,
            "delta_coupling_debt": delta_coupling_debt,
            "delta_hotspot_score": round(delta_hotspot_score, 4),
            "before_circular_dependencies_count": len(initial_plan.get("circular_dependencies", [])),
            "after_circular_dependencies_count": len(circular_deps),
        }

        # Save to ledger
        ledger_dir = os.path.join(self.repo_path, "ultron", "meta")
        os.makedirs(ledger_dir, exist_ok=True)
        ledger_path = os.path.join(ledger_dir, "kernel_ledger.jsonl")

        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "summary": summary,
            "target_files": initial_plan.get("target_files", []),
        }

        try:
            with open(ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except OSError as e:
            print(f"Warning: failed to write to kernel ledger: {e}", file=sys.stderr)

        return summary
