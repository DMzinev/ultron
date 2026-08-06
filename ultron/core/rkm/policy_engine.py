# Policy Engine for Decisions and Initiatives
import os
import json
import uuid
from datetime import datetime, timezone
from ultron.core.rkm.models import RiskProfile, Decision, Initiative

def evaluate_policy(
    risk_profile: RiskProfile,
    business_criticality: str = 'DEFAULT',
    policy_path: str = None
) -> Decision:
    res_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'resources')
    if not policy_path:
        policy_path = os.path.join(res_dir, 'decision_policy.json')
        
    crit_mult = 1.00
    policy_ver = '1.0.0'
    crit_thresh, high_thresh, med_thresh = 75.0, 50.0, 25.0
    
    if os.path.exists(policy_path):
        try:
            with open(policy_path, 'r', encoding='utf-8') as f:
                p_data = json.load(f)
                policy_ver = p_data.get('version', '1.0.0')
                crit_mult = p_data.get('criticality', {}).get(business_criticality.upper(), 1.00)
                p_t = p_data.get('thresholds', {})
                crit_thresh = p_t.get('CRITICAL', 75.0)
                high_thresh = p_t.get('HIGH', 50.0)
                med_thresh = p_t.get('MEDIUM', 25.0)
        except Exception:
            pass

    score = risk_profile.score * crit_mult
    
    if score >= crit_thresh:
        priority = 'CRITICAL'
    elif score >= high_thresh:
        priority = 'HIGH'
    elif score >= med_thresh:
        priority = 'MEDIUM'
    else:
        priority = 'LOW'
        
    reason_codes = []
    for s in risk_profile.signals:
        if s.name == 'complexity' and s.contribution >= 15.0:
            reason_codes.append('HIGH_COMPLEXITY')
        elif s.name == 'coupling' and s.contribution >= 10.0:
            reason_codes.append('HIGH_COUPLING')
        elif s.name == 'coverage' and s.contribution >= 10.0:
            reason_codes.append('LOW_TEST_COVERAGE')
            
    decision_id = f'dec_{uuid.uuid4().hex[:8]}'
    created_at = datetime.now(timezone.utc).isoformat()
    
    return Decision(
        entity_id=risk_profile.entity_id,
        priority=priority,
        risk_score=risk_profile.score,
        reason_codes=reason_codes,
        decision_id=decision_id,
        policy_version=policy_ver,
        evidence_ids=risk_profile.evidence_ids,
        created_at=created_at
    )

def generate_initiatives(violations: list) -> list:
    if not violations:
        return []
        
    comp_v = [v for v in violations if 'complexity' in str(v.get('rule', '')).lower() or 'HIGH_COMPLEXITY' in str(v.get('rule', '')).upper()]
    
    initiatives = []
    if comp_v:
        initiatives.append(Initiative(
            title='Function Complexity Reduction',
            target_entity=comp_v[0].get('file', 'Core'),
            expected_reduction=40.0
        ))
    return initiatives
