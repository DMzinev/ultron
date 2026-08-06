# Pure Language-Independent Risk Engine
import os
import json
from ultron.core.rkm.models import RiskSignal, RiskProfile

def compute_risk_profile(
    entity_id: str,
    complexity: float,
    coupling_fanout: int,
    coverage_percent: float = None,
    policy_path: str = None
) -> RiskProfile:
    """
    Computes pure numerical RiskProfile data object based on consolidated policy.
    Contains 0 English words inside calculation routines.
    """
    if not policy_path:
        policy_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "decision_policy.json")
        
    comp_w, coup_w, cov_w = 0.45, 0.30, 0.25
    comp_mult, coup_mult = 4.0, 10.0
    
    if os.path.exists(policy_path):
        try:
            with open(policy_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                weights = cfg.get("weights", {})
                scaling = cfg.get("scaling", {})
                comp_w = weights.get("complexity", 0.45)
                coup_w = weights.get("coupling", 0.30)
                cov_w = weights.get("coverage", 0.25)
                comp_mult = scaling.get("complexity_multiplier", 4.0)
                coup_mult = scaling.get("coupling_multiplier", 10.0)
        except Exception:
            pass

    norm_comp = min(float(complexity) * comp_mult, 100.0)
    norm_coup = min(float(coupling_fanout) * coup_mult, 100.0)
    
    cov_conf = 1.0
    if coverage_percent is not None:
        eff_coverage = float(coverage_percent)
    else:
        eff_coverage = 80.0
        cov_conf = 0.0  # Missing signal fallback
        
    norm_cov = max(0.0, min(100.0, 100.0 - eff_coverage))
    
    comp_contrib = round(comp_w * norm_comp, 2)
    coup_contrib = round(coup_w * norm_coup, 2)
    cov_contrib = round(cov_w * norm_cov, 2)
    
    raw_score = round(comp_contrib + coup_contrib + cov_contrib, 2)
    final_score = max(0.0, min(100.0, raw_score))
    
    signals = [
        RiskSignal(name="complexity", value=complexity, weight=comp_w, contribution=comp_contrib, confidence=1.0),
        RiskSignal(name="coupling", value=float(coupling_fanout), weight=coup_w, contribution=coup_contrib, confidence=0.95),
        RiskSignal(name="coverage", value=eff_coverage, weight=cov_w, contribution=cov_contrib, confidence=cov_conf)
    ]
    
    overall_confidence = round((1.0 + 0.95 + cov_conf) / 3.0, 2)
    confidence_vector = {
        "ast": 1.0,
        "coupling": 0.95,
        "coverage": cov_conf,
        "overall": overall_confidence
    }
    
    evidence_ids = ["ev_ast_01", "ev_coup_01"]
    
    return RiskProfile(
        entity_id=entity_id,
        score=final_score,
        signals=signals,
        confidence_vector=confidence_vector,
        evidence_ids=evidence_ids
    )
