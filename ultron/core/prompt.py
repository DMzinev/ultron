def generate_optimized_prompt(intent, codebase, risks):
    """
    Builds a structured prompt for the LLM coding agent, embedding
    the intent, risk profile, and interface contracts to prevent glitches.
    """
    prompt = []
    prompt.append("=== ULTRON PRE-EXECUTION INTELLIGENCE LAYER: CONTRACT SPECIFICATION ===")
    prompt.append("\nYou are a coding agent instructed to modify a software codebase.")
    prompt.append("To ensure zero-revision success, follow the strict dependency limits mapped below.")
    
    prompt.append("\n[USER INTENT]")
    prompt.append(f"Modify the code according to this goal:\n{intent}")
    
    prompt.append("\n[TARGET FILE COUPLING & RISK ASSESSMENT]")
    for risk in risks:
        prompt.append(f"- File: `{risk['file']}`")
        prompt.append(f"  Risk Level: {risk['level']} (Impact Score: {risk['impact_score']:.2f}, Complexity: {risk['complexity']}, Coupling: {risk['coupling']} callers)")
        prompt.append(f"  Mitigation: {risk['mitigation']}")
        if risk['callers']:
            prompt.append(f"  Callers to review: {', '.join(risk['callers'])}")
            
    prompt.append("\n[INTERFACE CONTRACTS (SIGNATURES)]")
    for risk in risks:
        target = risk['file']
        if target not in codebase:
            continue
        prompt.append(f"\nSignatures for `{target}`:")
        analysis = codebase[target]
        for defn in analysis.get("definitions", []):
            if defn.get("type") == "function":
                prompt.append(f"  - def {defn['name']}({', '.join(defn['args'])})")
            elif defn.get("type") == "class":
                prompt.append(f"  - class {defn['name']}:")
                for method in defn.get("methods", []):
                    prompt.append(f"      def {method['name']}({', '.join(method['args'])})")
                    
    prompt.append("\n[STRICT IMPLEMENTATION CHECKLIST]")
    prompt.append("1. Read target files and analyze how the targeted variables or states function.")
    prompt.append("2. Implement the requested changes locally inside the target files.")
    prompt.append("3. DO NOT alter the argument names, counts, or order of the interface signatures listed above, unless explicitly required.")
    prompt.append("4. If signatures must change, you are REQUIRED to update all callers listed in the Risk Assessment section concurrently.")
    prompt.append("5. Ensure all unit tests run and pass without side-effects.")
    
    prompt.append("\n======================================================================")
    
    return "\n".join(prompt)
