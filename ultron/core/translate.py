# Plain Language Violation & Risk Translator

def translate_violation_to_plain_english(rule_name: str, details: str, entity: str) -> dict:
    """
    Translates technical architecture violations into Plain English lead explanations.
    """
    rule_lower = rule_name.lower()
    
    if "complexity" in rule_lower:
        return {
            "plain_rule": "Code is too complex to modify safely",
            "summary": f"The module '{entity}' has too many decision paths. Changes will require extra testing to prevent bugs.",
            "action": "Break down large functions into smaller, single-purpose helper functions."
        }
    elif "coupling" in rule_lower or "dependency" in rule_lower or "import" in rule_lower:
        return {
            "plain_rule": "Module depends directly on private internal logic",
            "summary": f"The file '{entity}' bypasses standard interfaces and imports internal engine code directly.",
            "action": "Route calls through the public API package (interfaces/api) instead of importing core directly."
        }
    elif "size" in rule_lower or "loc" in rule_lower:
        return {
            "plain_rule": "File is growing too large to maintain easily",
            "summary": f"The file '{entity}' has accumulated too many lines of code and responsibilities.",
            "action": "Split distinct responsibilities into separate sub-modules."
        }
    else:
        return {
            "plain_rule": "Architectural boundary warning",
            "summary": f"An architectural constraint violation was detected in '{entity}' ({details}).",
            "action": "Review module imports and verify architectural boundary compliance."
        }


def translate_dynamic_decision_to_plain_english(complexity: float, coupling: int, coverage: float = None) -> dict:
    try:
        from ultron.core.rkm.dynamic_decision import calculate_dynamic_risk
        risk_info = calculate_dynamic_risk(complexity, coupling, coverage)
        score = risk_info["dynamic_risk_score"]
        tier = risk_info["priority_tier"]
        action = risk_info.get("action_recommendation", "Review module metrics.")
        breakdown = risk_info.get("breakdown", "N/A")
    except (ImportError, Exception):
        raw_score = (complexity or 0.0) * (1.0 + (coupling or 0) * 0.1)
        score = round(min(100.0, raw_score * 10), 1)
        tier = "HIGH" if score >= 70.0 else ("MEDIUM" if score >= 30.0 else "LOW")
        action = "Review decision branches and connected callers for potential simplification."
        breakdown = f"Based on code structure: {complexity} decision branches, {coupling} connected callers."
    
    return {
        "plain_summary": f"Change Risk Score: {score}/100 ({tier} Priority)",
        "priority_tier": tier,
        "risk_score": score,
        "action_plan": action,
        "breakdown": breakdown
    }


def translate_decision_to_plain_english(decision) -> dict:
    """
    Communication Engine: Translates a structured Decision object into audience-aware English.
    """
    from dataclasses import asdict
    dec_dict = asdict(decision) if hasattr(decision, "__dataclass_fields__") else decision
    
    score = dec_dict.get("risk_score", 0.0)
    tier = dec_dict.get("priority_tier", "LOW")
    entity = dec_dict.get("target_entity", "module")
    driver = dec_dict.get("dominant_driver", "complexity")
    
    return {
        "plain_summary": f"Architectural Priority: {tier} ({score}/100) for '{entity}'",
        "priority_tier": tier,
        "risk_score": score,
        "confidence_overall": dec_dict.get("confidence_overall", 1.0),
        "dominant_driver": driver,
        "triggered_rules": dec_dict.get("triggered_rules", []),
        "developer_recommendation": f"Focus refactoring on '{entity}' to address primary risk driver: {driver}."
    }


def translate_decision_to_personas(decision) -> dict:
    """
    Communication Engine: Translates a Decision object into Developer, Manager, Founder, Security, and AI Agent persona explanations.
    """
    from dataclasses import asdict
    d = asdict(decision) if hasattr(decision, "__dataclass_fields__") else decision
    
    entity = d.get("entity_id", "module")
    priority = d.get("priority", "LOW")
    reasons = ", ".join(d.get("reason_codes", ["GENERAL_MAINTAINABILITY"]))
    
    developer_text = f"Module '{entity}' has priority {priority} ({reasons}). Consider breaking down large decision paths into smaller helper functions."
    manager_text = f"Component '{entity}' increases delivery risk due to high verification overhead ({reasons})."
    founder_text = f"Feature development velocity is impacted by structural complexity in '{entity}'."
    security_text = f"Security review required for '{entity}' due to operational complexity and architectural boundaries ({reasons})."
    ai_agent_text = f"Refactor goal: Reduce decision branches in '{entity}' to satisfy priority bounds ({priority})."
    
    return {
        "decision_id": d.get("decision_id"),
        "entity_id": entity,
        "priority": priority,
        "reason_codes": d.get("reason_codes", []),
        "personas": {
            "developer": developer_text,
            "manager": manager_text,
            "founder": founder_text,
            "security": security_text,
            "ai_agent": ai_agent_text
        }
    }


def translate_decision(decision, audience: str = "developer") -> dict:
    """
    Communication Engine: Extensible translator taking a Decision object and an audience parameter.
    Audiences: 'developer', 'manager', 'founder', 'security', 'ai_agent'.
    """
    from dataclasses import asdict
    d = asdict(decision) if hasattr(decision, "__dataclass_fields__") else decision
    
    entity = d.get("entity_id", "module")
    priority = d.get("priority", "LOW")
    reasons = ", ".join(d.get("reason_codes", ["GENERAL_MAINTAINABILITY"]))
    aud = audience.lower().strip()
    
    if aud == "manager":
        explanation = f"Component '{entity}' increases delivery risk due to high verification overhead ({reasons})."
    elif aud == "founder":
        explanation = f"Feature development velocity is impacted by structural complexity in '{entity}'."
    elif aud == "security":
        explanation = f"Security review required for '{entity}' due to high operational complexity ({reasons})."
    elif aud == "ai_agent":
        explanation = f"Refactor goal: Reduce decision branches in '{entity}' to satisfy priority bounds ({priority})."
    else:  # 'developer' default
        explanation = f"Module '{entity}' has priority {priority} ({reasons}). Consider breaking down large decision paths into smaller helper functions."
        
    return {
        "decision_id": d.get("decision_id"),
        "entity_id": entity,
        "priority": priority,
        "audience": aud,
        "explanation": explanation,
        "reason_codes": d.get("reason_codes", []),
        "created_at": d.get("created_at")
    }


def plain_language_summary(packet) -> str:
    """
    Returns a human-style Plain English summary for an AnalysisPacket or risk dict.
    """
    file_path = getattr(packet, "file_path", None) or (packet.get("file") if isinstance(packet, dict) else "")
    level = (getattr(packet, "level", None) or (packet.get("level") if isinstance(packet, dict) else "LOW")).upper()
    callers = getattr(packet, "callers", None) if not isinstance(packet, dict) else packet.get("callers")
    if callers is not None and isinstance(callers, list):
        coupling_count = len(callers)
    else:
        coupling_score = getattr(packet, "coupling_score", None) if not isinstance(packet, dict) else packet.get("coupling_score")
        coupling_count = int(coupling_score) if coupling_score is not None else 0

    if level == "HIGH":
        dep_str = f"{coupling_count} other file{'s' if coupling_count != 1 else ''} depend on it directly"
        return f"{file_path} - High risk to change. {dep_str}."
    elif level == "MEDIUM":
        return f"{file_path} - Moderate risk. Changes require care."
    else:
        return f"{file_path} - Low risk. Nothing else in the project depends on this directly."


def detailed_breakdown(packet) -> str:
    """
    Returns technical details breakdown string for an AnalysisPacket or risk dict.
    """
    file_path = getattr(packet, "file_path", None) or (packet.get("file") if isinstance(packet, dict) else "")
    impact_score = float(getattr(packet, "impact_score", 0.0) or (packet.get("impact_score") if isinstance(packet, dict) else 0.0))
    callers = getattr(packet, "callers", None) if not isinstance(packet, dict) else packet.get("callers")
    if callers is not None and isinstance(callers, list):
        coupling_count = len(callers)
    else:
        coupling_score = getattr(packet, "coupling_score", None) if not isinstance(packet, dict) else packet.get("coupling_score")
        coupling_count = int(coupling_score) if coupling_score is not None else 0

    strategy = "Critical Hub (High Blast Radius)" if coupling_count >= 5 else ("Requires Review" if coupling_count >= 2 else "Safe to Edit (Isolated)")

    return (
        f"Detailed Risk Breakdown for {file_path}:\n"
        f"  Impact Score: {impact_score:.4f}\n"
        f"  Coupling Count: {coupling_count} (Blast Radius: {coupling_count} connected modules)\n"
        f"  Refactor Strategy: {strategy}\n"
        f"  Formula: Impact = Complexity * (1 + Coupling) (Decision Complexity weighted by connected callers)"
    )


