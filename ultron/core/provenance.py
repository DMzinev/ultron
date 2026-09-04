"""
Ultron Provenance Lineage Engine (v2.6)
Tracks structural graph facts back to empirical EvidenceObject IDs (AST_FACT, GIT_HISTORY, COVERAGE)
"""

from typing import Dict, List, Any, Optional
import time

class EvidenceReference:
    """Represents a direct link to an empirical evidence object ID."""
    def __init__(self, evidence_id: str, source_type: str, confidence: float = 1.0, details: Optional[Dict[str, Any]] = None):
        self.evidence_id = evidence_id
        self.source_type = source_type
        self.confidence = confidence
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "confidence": self.confidence,
            "details": self.details
        }

class ProvenanceChain:
    """Full provenance chain tracing a derived metric or structural node back to ground-truth evidence."""
    def __init__(self, target_id: str, classification: str = "DERIVED_CODE"):
        self.target_id = target_id
        self.classification = classification
        self.references: List[EvidenceReference] = []
        self.created_at = time.time()

    def add_reference(self, evidence_id: str, source_type: str, confidence: float = 1.0, details: Optional[Dict[str, Any]] = None):
        ref = EvidenceReference(evidence_id, source_type, confidence, details)
        self.references.append(ref)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "classification": self.classification,
            "references": [r.to_dict() for r in self.references],
            "created_at": self.created_at
        }

class ProvenanceTracker:
    """In-memory registry of provenance chains for repository snapshots."""
    def __init__(self):
        self._chains: Dict[str, ProvenanceChain] = {}

    def record_provenance(self, target_id: str, classification: str, evidence_id: str, source_type: str, confidence: float = 1.0, details: Optional[Dict[str, Any]] = None) -> ProvenanceChain:
        if target_id not in self._chains:
            self._chains[target_id] = ProvenanceChain(target_id, classification)
        self._chains[target_id].add_reference(evidence_id, source_type, confidence, details)
        return self._chains[target_id]

    def get_provenance(self, target_id: str) -> Optional[ProvenanceChain]:
        return self._chains.get(target_id)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in self._chains.items()}
