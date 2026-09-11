"""
ultron.interfaces.cli.commands.gate
Headless Architectural Quality Gate & CI/CD Wire Protocol.
"""

import os
import sys
import json
import io
import tarfile
import tempfile
import subprocess
from typing import Optional, Dict, Any, List

from ultron.core.ci_reporter import CIReporter
from ultron.core import analyzer
from ultron.core.risk import scoring
from ultron.core.policy_engine import PolicyEngine


def serialize_risk_packet(r: Any) -> Dict[str, Any]:
    """Converts AnalysisPacket objects or dictionaries into clean JSON-serializable dictionaries."""
    if isinstance(r, dict):
        return r
    return {
        "file_path": getattr(r, "file_path", ""),
        "file": getattr(r, "file_path", ""),
        "complexity": getattr(r, "complexity", 1),
        "coupling_score": getattr(r, "coupling_score", 0.0),
        "impact_score": getattr(r, "impact_score", 0.0),
        "level": getattr(r, "level", "LOW"),
        "mitigation": getattr(r, "mitigation", "")
    }


def extract_current_analysis(repo_path: str) -> Dict[str, Any]:
    """
    Executes headless AST analysis, evaluates risk profiles, runs governance policy engine,
    and computes calibrated composite health score.
    """
    abs_repo = os.path.abspath(os.path.normpath(repo_path))
    try:
        codebase = analyzer.analyze_directory(abs_repo)
        if not codebase:
            return {
                "repo": abs_repo.replace("\\", "/"),
                "risks": [],
                "policy_violations": [],
                "health_score": 100.0,
                "total_files": 0
            }

        target_files = [f for f in codebase.keys() if f.endswith(".py")]
        raw_risks = scoring.evaluate_risks(codebase, target_files, repo_path=abs_repo)
        serialized_risks = [serialize_risk_packet(r) for r in raw_risks]

        engine = PolicyEngine(load_defaults=True)
        policy_res = engine.evaluate_codebase({
            "risks": serialized_risks,
            "edges": []
        })

        violations = policy_res.get("violations", [])

        # Calibrated health score via EvolutionEngine & RKM store
        db_path = os.path.join(abs_repo, ".ultron", "repository.db")
        health_score = 100.0
        try:
            from ultron.core.pipeline import orchestrator
            from ultron.core.rkm.store import RepositoryStore
            from ultron.core.rkm.evolution.engine import EvolutionEngine

            orchestrator.analyze_repository(abs_repo, force=True)
            if os.path.exists(db_path):
                store = RepositoryStore(db_path)
                try:
                    meta = store.get_metadata()
                    if meta and meta.latest_analysis_run_id:
                        health_run = EvolutionEngine.evaluate_health_score(store, meta.latest_analysis_run_id)
                        health_score = round(
                            (health_run.architecture_stability * 0.4 +
                             health_run.rule_compliance * 0.4 +
                             health_run.complexity_trend * 0.2) * 100, 1
                        )
                finally:
                    store.close()
            else:
                health_score = CIReporter._extract_health({"risks": serialized_risks})
        except Exception:
            health_score = CIReporter._extract_health({"risks": serialized_risks})

        return {
            "repo": abs_repo.replace("\\", "/"),
            "risks": serialized_risks,
            "policy_violations": violations,
            "health_score": health_score,
            "total_files": len(codebase)
        }
    except Exception as e:
        print(f"[Ultron Gate Warning] Current analysis encountered an issue: {e}", file=sys.stderr)
        return {
            "repo": abs_repo.replace("\\", "/"),
            "risks": [],
            "policy_violations": [],
            "health_score": 100.0,
            "total_files": 0
        }


def extract_baseline_from_git(repo_path: str, base_ref: str) -> Optional[Dict[str, Any]]:
    """
    Extracts git archive snapshot of base_ref into a temporary directory, runs analyzer,
    and returns baseline analysis dictionary without leaving persistent disk artifacts.
    """
    abs_repo = os.path.abspath(os.path.normpath(repo_path))
    try:
        proc = subprocess.run(
            ["git", "archive", base_ref],
            cwd=abs_repo,
            capture_output=True,
            timeout=15.0
        )
        if proc.returncode != 0:
            print(
                f"[Ultron Gate Warning] Failed to git archive ref '{base_ref}': {proc.stderr.decode('utf-8', errors='replace').strip()}",
                file=sys.stderr
            )
            return None

        with tempfile.TemporaryDirectory() as temp_dir:
            tar_stream = io.BytesIO(proc.stdout)
            with tarfile.open(fileobj=tar_stream, mode="r:*") as tar:
                if hasattr(tarfile, 'data_filter'):
                    tar.extractall(path=temp_dir, filter='data')
                else:
                    tar.extractall(path=temp_dir)
            return extract_current_analysis(temp_dir)

    except (subprocess.SubprocessError, FileNotFoundError, OSError) as err:
        print(f"[Ultron Gate Warning] Could not extract git baseline from '{base_ref}': {err}", file=sys.stderr)
        return None


def safe_print(text: str, file=sys.stdout) -> None:
    """Safely prints UTF-8 text to stdout/stderr across Windows charmap (cp1252) and POSIX."""
    try:
        print(text, file=file)
    except UnicodeEncodeError:
        if hasattr(file, "buffer"):
            try:
                file.buffer.write((text + "\n").encode("utf-8", errors="replace"))
                file.flush()
                return
            except Exception:
                pass
        print(text.encode("ascii", errors="replace").decode("ascii"), file=file)


def run_gate_command(
    repo_path: str = ".",
    base: Optional[str] = None,
    baseline: Optional[str] = None,
    max_health_drop: float = 5.0,
    fail_on_regression: bool = True,
    fail_on_high: bool = False,
    strict: bool = False,
    json_output: bool = False,
    output_comment: Optional[str] = None,
    max_high: Optional[int] = None,
    min_health: Optional[float] = None,
    github_annotations: bool = False,
    output_json: Optional[str] = None,
    comment_pr: bool = False,
    github_token: Optional[str] = None
) -> int:
    """
    Executes the Ultron Architectural Quality Gate.
    Returns 0 on PASS, 1 on FAIL.
    """
    repo = os.path.abspath(os.path.normpath(repo_path))

    # Strict mode overrides
    if strict:
        max_health_drop = 0.0
        fail_on_high = True
        fail_on_regression = True

    # 1. Analyze Current Codebase
    current_analysis = extract_current_analysis(repo)

    # 2. Resolve Baseline Analysis
    baseline_analysis = None
    if baseline:
        base_file = os.path.abspath(os.path.normpath(baseline))
        if os.path.exists(base_file):
            try:
                with open(base_file, "r", encoding="utf-8") as f:
                    baseline_analysis = json.load(f)
            except Exception as e:
                safe_print(f"[Ultron Gate Warning] Could not parse baseline JSON '{base_file}': {e}", file=sys.stderr)
        else:
            safe_print(f"[Ultron Gate Warning] Baseline JSON file '{base_file}' not found.", file=sys.stderr)
    elif base:
        baseline_analysis = extract_baseline_from_git(repo, base)

    # 3. Evaluate Quality Gate Decision
    gate_decision = CIReporter.evaluate_regression_gate(
        current_analysis=current_analysis,
        baseline_analysis=baseline_analysis,
        max_health_drop=max_health_drop,
        fail_on_high=fail_on_high,
        max_high=max_high,
        min_health=min_health
    )

    # If strict, ensure any negative health delta is explicitly flagged
    if strict and baseline_analysis and gate_decision["health_delta"] < 0:
        gate_decision["passed"] = False
        strict_msg = f"Strict mode violated: Health dropped by {abs(gate_decision['health_delta'])} pts."
        if strict_msg not in gate_decision["reasons"]:
            gate_decision["reasons"].append(strict_msg)

    # 4. Generate PR Comment Markdown
    project_name = os.path.basename(repo) or "Ultron Codebase"
    pr_comment = CIReporter.generate_pr_comment(
        current_analysis=current_analysis,
        baseline_analysis=baseline_analysis,
        project_name=project_name,
        max_health_drop=max_health_drop,
        fail_on_high=fail_on_high,
        max_high=max_high,
        min_health=min_health
    )

    # 5. Output to Markdown file if specified
    if output_comment:
        out_file = os.path.abspath(os.path.normpath(output_comment))
        os.makedirs(os.path.dirname(out_file), exist_ok=True) if os.path.dirname(out_file) else None
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(pr_comment)
        if not json_output:
            safe_print(f"[Ultron Gate] PR comment written to: {out_file}", file=sys.stderr)

    # 6. Build Result Payload
    result_payload = {
        "status": "PASSED" if gate_decision["passed"] else "FAILED",
        "passed": gate_decision["passed"],
        "exit_code": 0 if (gate_decision["passed"] or not fail_on_regression) else 1,
        "gate_decision": gate_decision,
        "current_analysis": {
            "health_score": current_analysis.get("health_score", 100.0),
            "total_files": current_analysis.get("total_files", 0),
            "high_violations_count": gate_decision.get("high_violations_count", 0),
            "total_violations_count": gate_decision.get("total_violations_count", 0),
            "high_risk_count": gate_decision.get("high_risk_count", 0)
        },
        "thresholds": {
            "max_health_drop": max_health_drop,
            "fail_on_high": fail_on_high,
            "strict": strict,
            "fail_on_regression": fail_on_regression,
            "max_high": max_high,
            "min_health": min_health
        }
    }

    # 7. Output to JSON file if specified
    if output_json:
        out_json_file = os.path.abspath(os.path.normpath(output_json))
        os.makedirs(os.path.dirname(out_json_file), exist_ok=True) if os.path.dirname(out_json_file) else None
        with open(out_json_file, "w", encoding="utf-8") as f:
            json.dump(result_payload, f, indent=2)
        if not json_output:
            safe_print(f"[Ultron Gate] JSON analysis written to: {out_json_file}", file=sys.stderr)

    # 8. Append to GitHub Step Summary if running in GitHub Actions
    github_step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_step_summary:
        try:
            with open(github_step_summary, "a", encoding="utf-8") as f:
                f.write(pr_comment + "\n\n")
            if not json_output:
                safe_print(f"[Ultron Gate] Step summary appended to $GITHUB_STEP_SUMMARY", file=sys.stderr)
        except Exception as e:
            safe_print(f"[Ultron Gate Warning] Failed writing to GITHUB_STEP_SUMMARY: {e}", file=sys.stderr)

    # 9. Append to GitHub Output if running in GitHub Actions
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        try:
            with open(github_output, "a", encoding="utf-8") as f:
                f.write(f"passed={'true' if gate_decision['passed'] else 'false'}\n")
                f.write(f"health-score={gate_decision.get('current_health', 100.0):.1f}\n")
                f.write(f"health-delta={gate_decision.get('health_delta', 0.0):+.1f}\n")
                f.write(f"exit-code={1 if (fail_on_regression and not gate_decision['passed']) else 0}\n")
        except Exception as e:
            safe_print(f"[Ultron Gate Warning] Failed writing to GITHUB_OUTPUT: {e}", file=sys.stderr)

    # 10. Post PR Review Comment via GitHub REST API if requested
    if comment_pr:
        CIReporter.post_pr_comment(pr_comment, github_token=github_token)

    # 11. Emit GitHub Actions Workflow Annotations
    should_emit_annotations = github_annotations or (os.environ.get("GITHUB_ACTIONS") == "true")
    if should_emit_annotations:
        annotations = CIReporter.format_github_annotations(gate_decision, current_analysis)
        for ann in annotations:
            safe_print(ann, file=sys.stdout if not json_output else sys.stderr)

    # 12. Output Result Payload to stdout
    if json_output:
        safe_print(json.dumps(result_payload, indent=2))
    else:
        if not output_comment and not github_step_summary:
            safe_print(pr_comment)
        if not gate_decision["passed"]:
            safe_print("\n[Ultron Gate: FAILED] Quality gate thresholds breached:", file=sys.stderr)
            for reason in gate_decision.get("reasons", []):
                safe_print(f"  - ❌ {reason}", file=sys.stderr)
        else:
            safe_print(f"\n[Ultron Gate: PASSED] Codebase health: {gate_decision.get('current_health', 100.0):.1f}/100 (delta: {gate_decision.get('health_delta', 0.0):+.1f} pts).", file=sys.stderr)

    # 13. Return Exit Code
    if fail_on_regression and not gate_decision["passed"]:
        return 1
    return 0

