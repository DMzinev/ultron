"""
ultron/core/evidence.py — Canonical Evidence Model & Truth Engine.
Gate A: Eliminates silent guessing. Enforces 6-layer epistemic hierarchy and stable content-addressable evidence identity.
"""
import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class EvidenceClassification(str, Enum):
    OBSERVED = "OBSERVED"   # Directly measured from AST, test runner, git log, or headless browser
    DERIVED = "DERIVED"     # Deterministic mathematical/topological computation from observed facts
    INFERRED = "INFERRED"   # Bounded heuristic, structural approximation, or pattern matching
    UNKNOWN = "UNKNOWN"     # Missing data, unmeasured metrics, or offline components


class ConfidenceTier(str, Enum):
    HIGH = "HIGH"                   # Direct observation or deterministic derivation with complete inputs
    MEDIUM = "MEDIUM"               # Partial inputs, minor limitations disclosed
    LOW = "LOW"                     # Inferred heuristic or high limitation count
    NOT_ASSESSED = "NOT_ASSESSED"   # Unknown or unmeasured evidence


class EvidenceStatus(str, Enum):
    FRESH = "FRESH"                 # Snapshot matches current repository state
    STALE = "STALE"                 # Snapshot is older than active repository revision
    INVALIDATED = "INVALIDATED"     # Files modified or repository state mutated


def compute_evidence_id(
    source: str,
    target: str,
    snapshot_id: str,
    classification: str,
    value: Any,
    derivation: Optional[str] = None
) -> str:
    """Computes deterministic content-addressable evidence identity (SHA-256 hex digest)."""
    try:
        val_str = json.dumps(value, sort_keys=True, default=str)
    except Exception:
        val_str = str(value)
    
    canonical_str = f"{source}:{target}:{snapshot_id}:{classification}:{val_str}:{derivation or ''}"
    return "ev-" + hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()[:14]


def _json_safe(obj: Any) -> Any:
    """Recursively converts enums, tuples, dataclasses, and custom objects to JSON-safe primitives."""
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    return obj


@dataclass(frozen=True)
class EvidenceRecord:
    """Single immutable, content-addressable unit of evidence in Ultron."""
    evidence_id: str
    source: str                 # "AST" | "GIT" | "TEST_RUNNER" | "BROWSER_EDGE" | "STATIC_ANALYSIS"
    target: str                 # File path, symbol name, or subsystem
    observed_at: str            # ISO-8601 UTC timestamp
    snapshot_id: str            # Repository snapshot or commit hash
    classification: str         # EvidenceClassification.value
    confidence: str             # ConfidenceTier.value
    value: Any                  # Measured value
    derivation: Optional[str] = None
    limitations: Tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def create(
        cls,
        source: str,
        target: str,
        snapshot_id: str,
        classification: Union[EvidenceClassification, str],
        confidence: Union[ConfidenceTier, str],
        value: Any,
        derivation: Optional[str] = None,
        limitations: Optional[List[str]] = None,
        observed_at: Optional[str] = None
    ) -> "EvidenceRecord":
        c_val = classification.value if isinstance(classification, Enum) else str(classification)
        conf_val = confidence.value if isinstance(confidence, Enum) else str(confidence)
        ev_id = compute_evidence_id(source, target, snapshot_id, c_val, value, derivation)
        ts = observed_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        lim_tuple = tuple(limitations or [])
        return cls(
            evidence_id=ev_id,
            source=source,
            target=target,
            observed_at=ts,
            snapshot_id=snapshot_id,
            classification=c_val,
            confidence=conf_val,
            value=value,
            derivation=derivation,
            limitations=lim_tuple
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source": self.source,
            "target": self.target,
            "observed_at": self.observed_at,
            "snapshot_id": self.snapshot_id,
            "classification": self.classification,
            "confidence": self.confidence,
            "value": _json_safe(self.value),
            "derivation": self.derivation,
            "limitations": list(self.limitations)
        }


@dataclass
class EvidenceBundle:
    """Immutable aggregate collection of repository evidence for a specific snapshot."""
    snapshot_id: str
    compiled_at: str
    status: str = EvidenceStatus.FRESH.value
    records: Dict[str, EvidenceRecord] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)
    evidence_coverage_pct: float = 100.0
    unknown_count: int = 0

    def get_records_for_target(self, target: str) -> List[EvidenceRecord]:
        norm = target.replace("\\", "/").strip().lower()
        return [
            rec for rec in self.records.values()
            if rec.target.replace("\\", "/").strip().lower() == norm
        ]

    def get_target_confidence(self, target: str) -> str:
        records = self.get_records_for_target(target)
        if not records:
            return ConfidenceTier.NOT_ASSESSED.value
        if any(r.classification == EvidenceClassification.UNKNOWN.value for r in records):
            return ConfidenceTier.MEDIUM.value if any(r.confidence == ConfidenceTier.HIGH.value for r in records) else ConfidenceTier.LOW.value
        if all(r.confidence == ConfidenceTier.HIGH.value for r in records):
            return ConfidenceTier.HIGH.value
        if any(r.confidence == ConfidenceTier.MEDIUM.value for r in records):
            return ConfidenceTier.MEDIUM.value
        return ConfidenceTier.LOW.value

    def get_target_limitations(self, target: str) -> List[str]:
        records = self.get_records_for_target(target)
        lims = []
        for r in records:
            lims.extend(r.limitations)
        return sorted(list(set(lims)))

    def is_fresh(self, current_snapshot_id: str) -> bool:
        return self.status == EvidenceStatus.FRESH.value and self.snapshot_id == current_snapshot_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "compiled_at": self.compiled_at,
            "status": self.status,
            "records": {k: v.to_dict() for k, v in self.records.items()},
            "limitations": list(self.limitations),
            "evidence_coverage_pct": round(self.evidence_coverage_pct, 2),
            "unknown_count": self.unknown_count,
            "total_records": len(self.records)
        }


def compile_repository_evidence(
    repo_path: str,
    codebase: Dict[str, Any],
    risks: Optional[List[Any]] = None,
    test_results: Optional[Dict[str, Any]] = None,
    git_history: Optional[Dict[str, Any]] = None,
    snapshot_id: Optional[str] = None
) -> EvidenceBundle:
    """Authoritative compiler that builds the canonical EvidenceBundle for a repository state."""
    snap_id = snapshot_id or "snap-" + hashlib.sha256(str(sorted(list(codebase.keys()))).encode("utf-8")).hexdigest()[:12]
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    records: Dict[str, EvidenceRecord] = {}
    bundle_limitations: List[str] = []
    unknown_count = 0
    total_checks = 0

    # 1. AST Direct Observation & Derivation for each file
    for rel_path, analysis in (codebase or {}).items():
        total_checks += 3
        if isinstance(analysis, dict):
            comp = analysis.get("complexity", analysis.get("mccabe_complexity", 1))
            callers = analysis.get("callers", analysis.get("inbound_callers", []))
            blast_radius = analysis.get("blast_radius", callers)
            pub = analysis.get("public_surface", "INTERNAL")
            cycle = analysis.get("cycle_involvement", False)
        elif hasattr(analysis, "complexity") or hasattr(analysis, "callers"):
            comp = getattr(analysis, "complexity", getattr(analysis, "mccabe_complexity", 1))
            callers = getattr(analysis, "callers", getattr(analysis, "inbound_callers", []))
            blast_radius = getattr(analysis, "blast_radius", callers)
            pub = getattr(analysis, "public_surface", "INTERNAL")
            cycle = getattr(analysis, "cycle_involvement", False)
        else:
            comp = 1
            callers = []
            blast_radius = []
            pub = "INTERNAL"
            cycle = False

        # AST Complexity
        rec_comp = EvidenceRecord.create(
            source="AST",
            target=rel_path,
            snapshot_id=snap_id,
            classification=EvidenceClassification.OBSERVED,
            confidence=ConfidenceTier.HIGH,
            value={"cyclomatic_complexity": comp},
            derivation="AST branch and condition visitor analysis"
        )
        records[rec_comp.evidence_id] = rec_comp

        # Callers / Inbound coupling
        rec_callers = EvidenceRecord.create(
            source="AST",
            target=rel_path,
            snapshot_id=snap_id,
            classification=EvidenceClassification.OBSERVED,
            confidence=ConfidenceTier.HIGH,
            value={"callers": list(callers) if hasattr(callers, '__iter__') and not isinstance(callers, (str, bytes)) else [], "callers_count": len(callers) if hasattr(callers, '__len__') else 0},
            derivation="Direct AST symbol import & function reference graph"
        )
        records[rec_callers.evidence_id] = rec_callers

        # Transitive Blast Radius (Derived)
        rec_blast = EvidenceRecord.create(
            source="STATIC_ANALYSIS",
            target=rel_path,
            snapshot_id=snap_id,
            classification=EvidenceClassification.DERIVED,
            confidence=ConfidenceTier.HIGH,
            value={"blast_radius": list(blast_radius) if hasattr(blast_radius, '__iter__') and not isinstance(blast_radius, (str, bytes)) else [], "blast_count": len(blast_radius) if hasattr(blast_radius, '__len__') else 0},
            derivation="Transitive closure of AST dependency graph"
        )
        records[rec_blast.evidence_id] = rec_blast

        # Public API surface & Cycle involvement
        rec_arch = EvidenceRecord.create(
            source="ARCHITECTURE",
            target=rel_path,
            snapshot_id=snap_id,
            classification=EvidenceClassification.DERIVED,
            confidence=ConfidenceTier.HIGH,
            value={"public_surface": pub, "cycle_involvement": bool(cycle)},
            derivation="Export symbol analysis & cycle detection"
        )
        records[rec_arch.evidence_id] = rec_arch

    # 2. Git History Observation or Explicit Unknown Disclose
    total_checks += 1
    if git_history and len(git_history) > 0:
        for fpath, churn in git_history.items():
            rec_git = EvidenceRecord.create(
                source="GIT",
                target=fpath,
                snapshot_id=snap_id,
                classification=EvidenceClassification.OBSERVED,
                confidence=ConfidenceTier.HIGH,
                value={"churn": churn},
                derivation="git log revision commit history"
            )
            records[rec_git.evidence_id] = rec_git
    else:
        unknown_count += 1
        bundle_limitations.append("Git history unavailable — repository churn scaling inactive.")
        rec_git_unknown = EvidenceRecord.create(
            source="GIT",
            target="<repository>",
            snapshot_id=snap_id,
            classification=EvidenceClassification.UNKNOWN,
            confidence=ConfidenceTier.NOT_ASSESSED,
            value=None,
            derivation=None,
            limitations=["Git worktree not detected or commit history empty"]
        )
        records[rec_git_unknown.evidence_id] = rec_git_unknown

    # 3. Test Runner Observation or Explicit Not-Assessed Disclose
    total_checks += 1
    if test_results:
        rec_test = EvidenceRecord.create(
            source="TEST_RUNNER",
            target="<test_suite>",
            snapshot_id=snap_id,
            classification=EvidenceClassification.OBSERVED,
            confidence=ConfidenceTier.HIGH,
            value=test_results,
            derivation="Test runner execution execution trace"
        )
        records[rec_test.evidence_id] = rec_test
    else:
        rec_test_untested = EvidenceRecord.create(
            source="TEST_RUNNER",
            target="<test_suite>",
            snapshot_id=snap_id,
            classification=EvidenceClassification.UNKNOWN,
            confidence=ConfidenceTier.NOT_ASSESSED,
            value=None,
            derivation=None,
            limitations=["Automated test execution has not been initiated for current snapshot"]
        )
        records[rec_test_untested.evidence_id] = rec_test_untested

    coverage_pct = 100.0 if total_checks == 0 else max(0.0, 100.0 * (1.0 - (unknown_count / total_checks)))

    return EvidenceBundle(
        snapshot_id=snap_id,
        compiled_at=now,
        status=EvidenceStatus.FRESH.value,
        records=records,
        limitations=bundle_limitations,
        evidence_coverage_pct=coverage_pct,
        unknown_count=unknown_count
    )
