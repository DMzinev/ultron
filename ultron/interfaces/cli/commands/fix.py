"""
ultron.interfaces.cli.commands.fix
Developer-Centric AI Fix Generator and Self-Healing Prompt Envelope Generator.
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional

from ultron.core import analyzer
from ultron.core.risk import scoring
from ultron.core.agent_context_builder import AgentContextBuilder, CanonicalAgentContext
from ultron.core.refactoring_patch_engine import RefactoringPatchEngine
from ultron.core.rkm.refactor_estimator import RefactorEstimator


def _normalize_path(p: str) -> str:
    return os.path.normpath(str(p or "")).replace("\\", "/")


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


def build_fix_envelope_for_file(
    repo_path: str,
    target_file: str,
    codebase: Optional[Dict[str, Any]] = None,
    risks: Optional[List[Any]] = None,
    include_diff: bool = False,
    provider: str = "markdown"
) -> Dict[str, Any]:
    """
    Builds a grounded, self-contained AI Fix Envelope for a specific target file.
    """
    abs_repo = os.path.abspath(os.path.normpath(repo_path))
    rel_target = _normalize_path(os.path.relpath(os.path.join(abs_repo, target_file), abs_repo) if os.path.isabs(target_file) else target_file)
    abs_target = os.path.join(abs_repo, rel_target)

    # 1. Analyze codebase if not supplied
    if codebase is None:
        codebase = analyzer.analyze_directory(abs_repo)
    if risks is None:
        target_files = [f for f in codebase.keys() if f.endswith(".py")]
        risks = scoring.evaluate_risks(codebase, target_files, repo_path=abs_repo)

    # 2. Find matching risk profile
    matching_risk = None
    for r in risks:
        rf = _normalize_path(getattr(r, "file_path", getattr(r, "file", "")))
        if rf == rel_target or rf.endswith("/" + rel_target) or rel_target.endswith("/" + rf):
            matching_risk = r
            rel_target = rf
            break

    # Extract metrics
    complexity = int(getattr(matching_risk, "complexity", 1) if matching_risk else 1)
    coupling = int(getattr(matching_risk, "coupling_score", getattr(matching_risk, "coupling", 0)) if matching_risk else 0)
    impact = float(getattr(matching_risk, "impact_score", 0.0) if matching_risk else 0.0)
    level = str(getattr(matching_risk, "level", "LOW") if matching_risk else "LOW").upper()
    callers = [str(c).replace("\\", "/") for c in (getattr(matching_risk, "callers", []) if matching_risk else [])]

    # 3. Build Canonical Mission Envelope
    mission_ctx = AgentContextBuilder.build_file_mission(
        repo_path=abs_repo,
        target_file=rel_target
    )

    # 4. Extract AST Interface Signatures
    signatures = []
    file_analysis = codebase.get(rel_target, {})
    if not file_analysis and os.path.exists(abs_target):
        file_analysis = analyzer.analyze_file(abs_target)

    for defn in file_analysis.get("definitions", [])[:15]:
        if defn.get("type") == "function":
            args_str = ", ".join(str(a) for a in defn.get("args", []))
            signatures.append(f"def {defn.get('name', 'func')}({args_str}): ...")
        elif defn.get("type") == "class":
            signatures.append(f"class {defn.get('name', 'Cls')}:")
            for m in defn.get("methods", [])[:8]:
                m_args = ", ".join(str(a) for a in m.get("args", []))
                signatures.append(f"    def {m.get('name', 'method')}({m_args}): ...")

    # 5. Action plan from RefactorEstimator
    estimator_plan = RefactorEstimator.generate_refactoring_plan(rel_target, complexity, coupling, impact)
    action_steps = estimator_plan.get("action_plan_steps", [])

    # 6. Check RKM database for specific violations
    db_path = os.path.join(abs_repo, ".ultron", "repository.db")
    violations = []
    if os.path.exists(db_path):
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT v.id, f.path as file_path, v.details, r.id as rule_id, r.name as rule_name "
                "FROM rkm_violations v "
                "JOIN rkm_evaluations e ON e.id = v.evaluation_id "
                "JOIN rkm_rules r ON r.id = e.rule_id "
                "JOIN rkm_files f ON f.id = v.file_id "
                "WHERE f.path = ? OR f.path LIKE ?",
                (rel_target, f"%{rel_target}")
            ).fetchall()
            for row in rows:
                violations.append({
                    "rule_id": row["rule_id"],
                    "rule_name": row["rule_name"],
                    "details": row["details"]
                })
            conn.close()
        except Exception:
            pass

    # 7. Optional Diff generation
    diff_text = None
    if include_diff and os.path.exists(abs_target):
        try:
            with open(abs_target, "r", encoding="utf-8", errors="replace") as f:
                src = f.read()
            patch_res = RefactoringPatchEngine.generate_function_extraction_patch(rel_target, src)
            if patch_res.get("success"):
                diff_text = patch_res.get("diff")
        except Exception:
            pass

    # 8. Render provider prompt
    prov_lower = provider.lower()
    if prov_lower == "claude":
        rendered_prompt = AgentContextBuilder.render_claude(mission_ctx)
    elif prov_lower in ("cursor", "codex"):
        rendered_prompt = AgentContextBuilder.render_cursor(mission_ctx)
    elif prov_lower in ("antigravity", "umags"):
        rendered_prompt = AgentContextBuilder.render_antigravity(mission_ctx)
    elif prov_lower == "aider":
        rendered_prompt = AgentContextBuilder.render_aider(mission_ctx)
    else:
        # Default rich markdown envelope
        envelope_lines = [
            "================================================================================",
            f"           ULTRON AI FIX ENVELOPE: {rel_target}",
            "================================================================================",
            "",
            "You are instructed to refactor and fix architectural risks in the following file:",
            f"Target: `{rel_target}`",
            "",
            "[1. GROUND TRUTH EVIDENCE & RISK METRICS]",
            f"- Risk Level: {level} (Impact Score: {impact:.1f} / 10.0)",
            f"- Code Complexity (Decision Paths): {complexity} (Ceiling: <= 8)",
            f"- Blast Radius (Connected Modules): {coupling} modules",
            f"- Inbound Callers ({len(callers)}): {', '.join(callers[:6]) if callers else 'Leaf module (no direct inbound callers)'}",
            f"- Co-Change Companions: {', '.join(mission_ctx.affected_components[1:]) if len(mission_ctx.affected_components) > 1 else 'None'}",
            ""
        ]

        if violations:
            envelope_lines.append("[2. ACTIVE POLICY & RULE VIOLATIONS]")
            for v in violations:
                envelope_lines.append(f"- [{v['rule_id'].upper()}] {v['details']}")
            envelope_lines.append("")

        if signatures:
            envelope_lines.append("[3. PUBLIC INTERFACE CONTRACTS (PRESERVE SIGNATURES)]")
            envelope_lines.append("The following public interfaces are called across the codebase and must remain compatible:")
            envelope_lines.append("```python")
            envelope_lines.extend(signatures[:12])
            envelope_lines.append("```")
            envelope_lines.append("")

        envelope_lines.append("[4. ACTIONABLE REFACTORING PLAN]")
        for step in action_steps:
            envelope_lines.append(f"- {step}")
        envelope_lines.append("")

        if diff_text:
            envelope_lines.append("[5. PROPOSED SAFE CODE REFACTOR (UNIFIED DIFF)]")
            envelope_lines.append("```diff")
            envelope_lines.append(diff_text)
            envelope_lines.append("```")
            envelope_lines.append("")

        envelope_lines.append("[6. ACCEPTANCE CRITERIA & VERIFICATION COMMAND]")
        envelope_lines.append("Verify your fix by running the test suite and checking that all tests pass without regressions:")
        envelope_lines.append("```bash")
        envelope_lines.append(mission_ctx.verification_command)
        envelope_lines.append("```")
        envelope_lines.append("================================================================================")
        rendered_prompt = "\n".join(envelope_lines)

    return {
        "status": "success",
        "target": rel_target,
        "risk_level": level,
        "metrics": {
            "complexity": complexity,
            "coupling": coupling,
            "impact_score": impact,
            "callers_count": len(callers)
        },
        "callers": callers,
        "co_change_companions": mission_ctx.affected_components[1:] if len(mission_ctx.affected_components) > 1 else [],
        "forbidden_changes": mission_ctx.forbidden_changes,
        "violations": violations,
        "interface_signatures": signatures,
        "action_plan_steps": action_steps,
        "diff": diff_text,
        "verification_command": mission_ctx.verification_command,
        "prompt_envelope": rendered_prompt,
        "semantic_hash": mission_ctx.semantic_mission_hash()
    }


def run_fix_command(args: Any) -> int:
    """CLI execution entrypoint for 'ultron fix'."""
    repo_path = getattr(args, "repo", ".") or "."
    abs_repo = os.path.abspath(os.path.normpath(repo_path))
    target = getattr(args, "target", None)
    is_top = getattr(args, "top", False)
    limit = max(1, getattr(args, "limit", 1))
    is_json = getattr(args, "json", False)
    show_diff = getattr(args, "show_diff", False)
    output_file = getattr(args, "output", None)
    provider = getattr(args, "provider", "markdown") or "markdown"

    # 1. Load codebase & risks
    codebase = analyzer.analyze_directory(abs_repo)
    if not codebase:
        msg = "[-] Error: No Python files found in target repository."
        if is_json:
            safe_print(json.dumps({"status": "error", "error": msg}))
        else:
            safe_print(msg, file=sys.stderr)
        return 1

    target_files = [f for f in codebase.keys() if f.endswith(".py")]
    risks = scoring.evaluate_risks(codebase, target_files, repo_path=abs_repo)
    sorted_risks = sorted(risks, key=lambda r: getattr(r, "impact_score", 0.0), reverse=True)

    # 2. Resolve target file(s)
    targets_to_fix = []
    if target:
        # Check if target is a number (violation ID) or file path
        if str(target).isdigit():
            # Resolve violation from DB
            db_path = os.path.join(abs_repo, ".ultron", "repository.db")
            resolved_file = None
            if os.path.exists(db_path):
                try:
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    r = conn.execute("SELECT f.path FROM rkm_violations v JOIN rkm_files f ON f.id = v.file_id WHERE v.id = ?", (target,)).fetchone()
                    if r:
                        resolved_file = r["path"]
                    conn.close()
                except Exception:
                    pass
            targets_to_fix.append(resolved_file or (sorted_risks[0].file_path if sorted_risks else "core.py"))
        else:
            targets_to_fix.append(target)
    else:
        # Default to top hotspot(s)
        count = limit if is_top else 1
        for r in sorted_risks[:count]:
            rf = getattr(r, "file_path", getattr(r, "file", ""))
            if rf:
                targets_to_fix.append(rf)

    if not targets_to_fix:
        if sorted_risks:
            targets_to_fix = [getattr(sorted_risks[0], "file_path", getattr(sorted_risks[0], "file", "core.py"))]
        else:
            targets_to_fix = [list(codebase.keys())[0]]

    # 3. Generate fix envelopes
    results = []
    for t in targets_to_fix:
        env = build_fix_envelope_for_file(
            repo_path=abs_repo,
            target_file=t,
            codebase=codebase,
            risks=sorted_risks,
            include_diff=show_diff,
            provider=provider
        )
        results.append(env)

    # 4. Output Formatting
    if is_json:
        payload = results[0] if len(results) == 1 else {"status": "success", "fixes": results}
        json_str = json.dumps(payload, indent=2)
        if output_file:
            with open(os.path.normpath(output_file), "w", encoding="utf-8") as f:
                f.write(json_str)
            safe_print(f"[+] JSON fix envelope exported to {output_file}", file=sys.stderr)
        else:
            safe_print(json_str)
    else:
        out_text = "\n\n".join(r["prompt_envelope"] for r in results)
        if output_file:
            with open(os.path.normpath(output_file), "w", encoding="utf-8") as f:
                f.write(out_text)
            safe_print(f"[+] Markdown fix envelope exported to {output_file}", file=sys.stderr)
        else:
            safe_print(out_text)

    return 0
