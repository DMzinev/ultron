# Decision Intelligence v1 Frozen Data Contracts (Corrected)
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass(frozen=True)
class RiskSignal:
    name: str
    value: float
    weight: float
    contribution: float
    confidence: float

@dataclass(frozen=True)
class RiskProfile:
    entity_id: str
    score: float
    signals: List[RiskSignal]
    confidence_vector: Dict[str, float]
    evidence_ids: List[str]

@dataclass(frozen=True)
class Initiative:
    title: str
    target_entity: str
    expected_reduction: float

@dataclass(frozen=True)
class Decision:
    entity_id: str
    priority: str
    risk_score: float
    reason_codes: List[str]
    decision_id: str
    policy_version: str
    evidence_ids: List[str]
    created_at: str
