MAX_INTENT_CHARS = 2000
MAX_SIGNATURE_LINES = 40
MAX_SIGNATURE_ARG_CHARS = 120
MAX_PROMPT_CHARS = 8000

def generate_optimized_prompt(intent, codebase, risks, max_budget_chars: int = MAX_PROMPT_CHARS):
    """
    Builds a structured prompt for the LLM coding agent, embedding
    the intent, risk profile, and interface contracts to prevent glitches.
    Enforces strict token budgeting and truncation caps.
    """
    clean_intent = str(intent or "").strip()
    if len(clean_intent) > MAX_INTENT_CHARS:
        clean_intent = clean_intent[:MAX_INTENT_CHARS] + "\n... [User Intent truncated to fit token budget]"

    prompt = []
    prompt.append("=== ULTRON PRE-EXECUTION INTELLIGENCE LAYER: CONTRACT SPECIFICATION ===")
    prompt.append("\nYou are a coding agent instructed to modify a software codebase.")
    prompt.append("To ensure zero-revision success, follow the strict dependency limits mapped below.")
    
    prompt.append("\n[USER INTENT]")
    prompt.append(f"Modify the code according to this goal:\n{clean_intent or 'Improve system architecture and maintain contracts.'}")
    
    prompt.append("\n[TARGET FILE COUPLING & RISK ASSESSMENT]")
    for risk in (risks or [])[:10]:
        fp = str(risk.get('file') or risk.get('file_path') or 'unknown').replace("\\", "/")[:150]
        level = str(risk.get('level', 'MEDIUM')).upper()
        impact = float(risk.get('impact_score', 0.0))
        comp = int(risk.get('complexity', 1))
        coup = risk.get('coupling_score', risk.get('coupling', 0))
        mitigation = str(risk.get('mitigation', 'Refactor into localized helper routines.'))[:200]
        callers = [str(c).replace("\\", "/")[:100] for c in (risk.get('callers', []) or [])[:8]]
        prompt.append(f"- File: `{fp}`")
        prompt.append(f"  Risk Level: {level} (Impact Score: {impact:.2f}, Complexity: {comp}, Coupling: {coup} callers)")
        prompt.append(f"  Mitigation: {mitigation}")
        if callers:
            prompt.append(f"  Callers to review: {', '.join(callers)}")
            
    prompt.append("\n[INTERFACE CONTRACTS (SIGNATURES)]")
    sig_lines_count = 0
    for risk in (risks or [])[:5]:
        if sig_lines_count >= MAX_SIGNATURE_LINES:
            prompt.append("  ... [Remaining interface signatures truncated for token budget]")
            break
        target = risk.get('file') or risk.get('file_path')
        if not target or target not in codebase:
            continue
        clean_target = str(target).replace("\\", "/")
        prompt.append(f"\nSignatures for `{clean_target}`:")
        sig_lines_count += 1
        analysis = codebase[target]
        for defn in analysis.get("definitions", [])[:15]:
            if sig_lines_count >= MAX_SIGNATURE_LINES:
                break
            if defn.get("type") == "function":
                args_str = ', '.join(str(a) for a in defn.get('args', []))[:MAX_SIGNATURE_ARG_CHARS]
                prompt.append(f"  - def {defn.get('name', 'func')}({args_str})")
                sig_lines_count += 1
            elif defn.get("type") == "class":
                prompt.append(f"  - class {defn.get('name', 'Cls')}:")
                sig_lines_count += 1
                for method in defn.get("methods", [])[:10]:
                    if sig_lines_count >= MAX_SIGNATURE_LINES:
                        break
                    m_args = ', '.join(str(a) for a in method.get('args', []))[:MAX_SIGNATURE_ARG_CHARS]
                    prompt.append(f"      def {method.get('name', 'method')}({m_args})")
                    sig_lines_count += 1
                    
    prompt.append("\n[STRICT IMPLEMENTATION CHECKLIST]")
    prompt.append("1. Read target files and analyze how the targeted variables or states function.")
    prompt.append("2. Implement the requested changes locally inside the target files.")
    prompt.append("3. DO NOT alter the argument names, counts, or order of the interface signatures listed above, unless explicitly required.")
    prompt.append("4. If signatures must change, you are REQUIRED to update all callers listed in the Risk Assessment section concurrently.")
    prompt.append("5. Ensure all unit tests run and pass without side-effects.")
    prompt.append("\n======================================================================")
    
    result = "\n".join(prompt)
    if len(result) > max_budget_chars:
        result = result[:max_budget_chars] + "\n... [Prompt bounded by token budget envelope]\n======================================================================"
    return result
