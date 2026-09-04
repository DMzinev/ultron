import os
import sys
from typing import Dict, Any, List, Optional


def _normalize_path(p: str) -> str:
    norm = os.path.normpath(str(p or "")).replace("\\", "/")
    if norm.startswith("./"):
        norm = norm[2:]
    return norm


def _discover_verification_command(repo_path: str, norm_target: str) -> str:
    """
    Dynamically discovers the appropriate non-regression test command for the target file
    within the given repository path without hardcoding foreign paths.
    """
    abs_repo = os.path.abspath(repo_path)
    base = os.path.splitext(os.path.basename(norm_target))[0]

    # 1. Target-specific test file discovery
    candidates = [
        os.path.join(abs_repo, "tests", f"test_{base}.py"),
        os.path.join(abs_repo, f"test_{base}.py"),
        os.path.join(abs_repo, "tests", f"{base}_test.py"),
        os.path.join(abs_repo, f"{base}_test.py"),
    ]
    if os.path.isdir(os.path.join(abs_repo, "ultron", "tests")):
        candidates.append(os.path.join(abs_repo, "ultron", "tests", f"test_{base}.py"))

    for c in candidates:
        if os.path.exists(c):
            rel_c = os.path.relpath(c, abs_repo).replace("\\", "/")
            return f"python -m unittest {rel_c}"

    # 2. General repo-level test runner discovery
    if os.path.isdir(os.path.join(abs_repo, "tests")):
        return 'python -m unittest discover -s tests -p "test_*.py"'
    elif os.path.isdir(abs_repo) and any(f.startswith("test_") and f.endswith(".py") for f in os.listdir(abs_repo) if os.path.isfile(os.path.join(abs_repo, f))):
        return 'python -m unittest discover -s . -p "test_*.py"'
    elif os.path.isdir(os.path.join(abs_repo, "ultron", "tests")):
        return 'python -m unittest discover -s ultron/tests -p "test_*.py"'

    # 3. Fallback when no tests exist in target repo: syntax and compilation validation
    return f"python -m py_compile {norm_target}"


def compile_mission_envelope(
    intent: str,
    target_file: Optional[str] = None,
    repo_path: Optional[str] = None,
    codebase: Optional[Dict[str, Any]] = None,
    risks: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    Compiles a bounded, grounded mission envelope for an AI coding agent with all 7 fields:
    1. Intent: verbatim user goal.
    2. Blast radius: exact dependent files from graph (or explicit leaf note).
    3. Must-not-touch list: public API surfaces (filtering private symbols).
    4. Complexity ceiling: McCabe cyclomatic complexity limit ("this file is at McCabe {N}; do not add branches").
    5. Verification command: dynamic test command proving non-regression.
    6. Rollback instruction: git restore command with relative path.
    7. Token budget hint: ranked reading list and ignore list.
    """
    abs_repo = os.path.abspath(repo_path or os.getcwd())
    raw_intent = str(intent or "").strip()
    verbatim_intent = raw_intent if raw_intent else "Implement requested changes with zero revision debt and maintain architectural integrity."

    # 1. Analyze codebase if needed
    if codebase is None:
        try:
            from ultron.core import analyzer
            codebase = analyzer.analyze_directory(abs_repo)
        except Exception:
            codebase = {}

    # 2. Resolve target file
    resolved_target = target_file
    if not resolved_target:
        if risks:
            first_r = risks[0]
            resolved_target = getattr(first_r, "file_path", None) or (first_r.get("file") if isinstance(first_r, dict) else None)
        if not resolved_target and codebase:
            resolved_target = next(iter(codebase.keys()), "main.py")
        if not resolved_target:
            resolved_target = "main.py"

    abs_target = os.path.abspath(os.path.join(abs_repo, resolved_target)) if not os.path.isabs(resolved_target) else resolved_target
    try:
        norm_target = os.path.relpath(abs_target, abs_repo).replace("\\", "/")
    except ValueError:
        norm_target = _normalize_path(resolved_target)

    # 3. Evaluate risks if needed
    matching_risk = None
    if risks is None:
        try:
            from ultron.core.risk import scoring
            target_list = [norm_target] if norm_target in codebase else list(codebase.keys())
            risks = scoring.evaluate_risks(codebase, target_list, intent=verbatim_intent, repo_path=abs_repo)
        except Exception:
            risks = []

    for r in (risks or []):
        rf = _normalize_path(getattr(r, "file_path", None) or (r.get("file") if isinstance(r, dict) else ""))
        if rf == norm_target or rf.endswith("/" + norm_target) or norm_target.endswith("/" + rf):
            matching_risk = r
            break

    # 4. Extract metrics
    if matching_risk:
        if isinstance(matching_risk, dict):
            comp = int(matching_risk.get("complexity", 1))
            callers = [str(c).replace("\\", "/") for c in matching_risk.get("callers", [])]
            impact = float(matching_risk.get("impact_score", 0.0))
            level = str(matching_risk.get("level", "LOW")).upper()
        else:
            comp = int(getattr(matching_risk, "complexity", 1))
            callers = [str(c).replace("\\", "/") for c in getattr(matching_risk, "callers", [])]
            impact = float(getattr(matching_risk, "impact_score", 0.0))
            level = str(getattr(matching_risk, "level", "LOW")).upper()
    else:
        comp = 1
        if os.path.exists(abs_target):
            try:
                from ultron.core import analyzer
                f_facts = analyzer.analyze_file(abs_target)
                comp = int(f_facts.get("complexity", 1))
            except Exception:
                comp = 1
        callers = []
        impact = 1.0
        level = "LOW"

    # Field 2: Blast Radius
    blast_radius_list = [c for c in callers if c != norm_target]
    if blast_radius_list:
        blast_radius_text = f"The following {len(blast_radius_list)} file(s) directly import or depend on `{norm_target}` and can break on incompatible changes:\n" + "\n".join(f"- `{c}`" for c in blast_radius_list)
    else:
        blast_radius_text = f"None - `{norm_target}` is a leaf module with no downstream dependents (blast radius: 0 files)."

    # Field 3: Must-Not-Touch List (Public API Signatures)
    target_analysis = codebase.get(norm_target, {})
    if not target_analysis and os.path.exists(abs_target):
        try:
            from ultron.core import analyzer
            target_analysis = analyzer.analyze_file(abs_target)
        except Exception:
            target_analysis = {}

    signatures = []
    raw_defs = target_analysis.get("definitions", [])
    for defn in raw_defs:
        d_name = defn.get("name", "")
        if d_name.startswith("_") and d_name != "__init__":
            continue
        if defn.get("type") == "function":
            args_str = ", ".join(str(a) for a in defn.get("args", []))
            signatures.append(f"def {d_name}({args_str})")
        elif defn.get("type") == "class":
            signatures.append(f"class {d_name}:")
            for m in defn.get("methods", []):
                m_name = m.get("name", "")
                if m_name.startswith("_") and m_name != "__init__":
                    continue
                m_args = ", ".join(str(a) for a in m.get("args", []))
                signatures.append(f"    def {m_name}({m_args})")

    if signatures:
        must_not_touch_text = (
            "The following public interfaces are exposed by this module. "
            "Do NOT alter parameter names, argument counts, or return semantics without updating callers:\n" +
            "\n".join(f"- `{sig}`" for sig in signatures[:20])
        )
    else:
        must_not_touch_text = f"No public function or class definitions exposed in `{norm_target}`."

    # Field 4: Complexity Ceiling
    complexity_ceiling = f"This file is at McCabe {comp}; do not add branches (maintain complexity <= {comp})."

    # Field 5: Verification Command
    verification_cmd = _discover_verification_command(abs_repo, norm_target)

    # Field 6: Rollback Instruction
    rollback_cmd = f"git restore {norm_target}"

    # Field 7: Token Budget Hint
    token_budget_text = (
        f"1. Rank 1 (Target): `{norm_target}` — Read in full.\n"
        f"2. Rank 2 (Blast Radius Callers): {', '.join(f'`{c}`' for c in blast_radius_list) if blast_radius_list else 'None'} — Read interface call-sites only; do not load full files.\n"
        "3. Ignore: All other repository files, test fixtures, virtual environments, and configuration to conserve token budget."
    )

    prompt_lines = [
        "=== ULTRON PRE-EXECUTION INTELLIGENCE LAYER: MISSION ENVELOPE ===",
        "You are an AI coding agent instructed to modify a software codebase.",
        "To ensure zero-revision success, follow the strict dependency limits and contracts below.",
        "",
        "[1. INTENT] (User Intent)",
        verbatim_intent,
        "",
        "[2. BLAST RADIUS] (Target File Coupling & Risk Assessment)",
        f"- Target File: `{norm_target}`",
        f"- Risk Tier: {level} (Impact Score: {impact:.2f}, Complexity: {comp})",
        f"- Blast Radius Count: {len(blast_radius_list)} module(s)",
        blast_radius_text,
        "",
        "[3. MUST-NOT-TOUCH LIST] (Interface Contracts & Signatures)",
        must_not_touch_text,
        "",
        "[4. COMPLEXITY CEILING]",
        complexity_ceiling,
        "",
        "[5. VERIFICATION COMMAND]",
        f"```bash\n{verification_cmd}\n```",
        "",
        "[6. ROLLBACK INSTRUCTION]",
        f"```bash\n{rollback_cmd}\n```",
        "",
        "[7. TOKEN BUDGET HINT]",
        token_budget_text,
        "",
        "[STRICT IMPLEMENTATION CHECKLIST]",
        "1. Read target files and analyze how the targeted variables or states function.",
        "2. Implement the requested changes locally inside the target files.",
        "3. DO NOT alter the argument names, counts, or order of the interface signatures listed above, unless explicitly required.",
        "4. If signatures must change, you are REQUIRED to update all callers listed in the Blast Radius section concurrently.",
        f"5. Run the verification command (`{verification_cmd}`) and ensure all tests pass without regressions.",
        f"6. If verification fails or breaks architectural boundaries, immediately rollback via `{rollback_cmd}`.",
        "",
        "======================================================================"
    ]
    rendered_prompt = "\n".join(prompt_lines)

    return {
        "intent": verbatim_intent,
        "target_file": norm_target,
        "blast_radius": blast_radius_list,
        "must_not_touch": signatures,
        "complexity_ceiling": complexity_ceiling,
        "verification_command": verification_cmd,
        "rollback_instruction": rollback_cmd,
        "token_budget_hint": {
            "rank_1_target": norm_target,
            "rank_2_callers": blast_radius_list,
            "ignore": "All other repository files, fixtures, caches, and configuration."
        },
        "rendered_prompt": rendered_prompt
    }


def generate_optimized_prompt(
    intent: str,
    codebase: Optional[Dict[str, Any]] = None,
    risks: Optional[List[Any]] = None,
    repo_path: Optional[str] = None,
    target_file: Optional[str] = None
) -> str:
    """
    Builds a structured prompt for the LLM coding agent, embedding
    the intent, risk profile, and interface contracts to prevent glitches.
    Guarantees inclusion of all seven required mission envelope fields.
    """
    envelope = compile_mission_envelope(
        intent=intent,
        target_file=target_file,
        repo_path=repo_path,
        codebase=codebase,
        risks=risks
    )
    return envelope["rendered_prompt"]
