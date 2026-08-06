from dataclasses import dataclass

from enum import Enum
from typing import Any

RKM_SCHEMA_VERSION = "1.3.0"
RKM_COMPATIBILITY = {
    "minimum_reader_version": "1.3.0",
    "maximum_writer_version": "1.x"
}

class EvaluationStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"

@dataclass
class RkmManifest:
    repository_uuid: str
    schema_version: str
    minimum_reader_version: str
    maximum_writer_version: str
    engine_version: str
    rule_pack_version: str
    snapshot_version: str
    created_at: str = None
    id: int = 1

@dataclass
class RepositoryMetadata:
    id: int
    repository_uuid: str
    name: str
    root_path: str
    language: str
    size: int
    rkm_version: str
    minimum_reader_version: str
    maximum_writer_version: str
    latest_analysis_run_id: int

@dataclass
class AnalysisRun:
    id: int
    repository_id: int
    timestamp: str
    duration: float
    engine_version: str
    rkm_version: str
    content_hash: str
    previous_run_id: int = None
    rule_pack_version: str = "1.0.0"
    semantic_hash: str = None
    archived: int = 0
    semantic_hash_strategy: str = "AST"

@dataclass
class RkmRule:
    id: str
    rule_pack_id: str
    name: str
    description: str
    predicate_type: str
    version: str = "1.0.0"

@dataclass
class RkmRuleInstance:
    id: int
    rule_id: str
    enabled: int
    severity: str
    predicate_config: dict[str, Any]
    version: str = "1.0.0"

@dataclass
class RkmEvaluation:
    id: int
    analysis_run_id: int
    rule_id: str
    status: EvaluationStatus
    started_at: str
    finished_at: str
    duration_ms: int
    engine_version: str
    rule_version: str

@dataclass
class RkmViolation:
    id: int
    evaluation_id: int
    file_id: int = None
    symbol_id: int = None
    details: str = None
    created_at: str = None

@dataclass
class RkmViolationEvidence:
    id: int
    violation_id: int
    evidence_type: str  # 'fact', 'metric', 'dependency', etc.
    evidence_id: int
    created_at: str = None


@dataclass
class FileRecord:
    id: int
    analysis_run_id: int
    path: str
    role: str
    package: str
    size: int
    last_modified: str
    created_at: str
    updated_at: str

@dataclass
class SymbolRecord:
    id: int
    file_id: int
    name: str
    type: str
    lineno: int

@dataclass
class DependencyRecord:
    id: int
    file_id: int
    target_path: str

@dataclass
class FactRecord:
    id: int
    file_id: int
    category: str
    metric: str
    value: str
    value_type: str
    source_type: str
    source_reference: str
    created_at: str
    updated_at: str

@dataclass
class InterpretationRecord:
    id: int
    fact_id: int
    rule: str
    result: str
    confidence: float
    created_at: str
    updated_at: str

@dataclass
class RecommendationRecord:
    id: int
    interpretation_id: int
    action: str
    confidence_type: str
    confidence_value: float
    status: str
    created_at: str
    updated_at: str

@dataclass
class MetricRecord:
    id: int
    file_id: int
    name: str
    value: float
    created_at: str
    updated_at: str

@dataclass
class ArchitectureRecord:
    id: int
    file_id: int
    layer: str
    role: str

@dataclass
class ProvenanceRecord:
    id: int
    fact_id: int
    generated_by: str
    engine_version: str
    rule_id: str = None
    model_name: str = None
    prompt_hash: str = None
    configuration_hash: str = None
    timestamp: str = None

@dataclass
class RunComparison:
    added_files: list[str]
    removed_files: list[str]
    modified_files: list[str]
    metric_delta: dict
    risk_delta: dict
    architecture_delta: dict
    dependency_delta: dict
    future_reserved: dict


@dataclass
class RkmEntityHistory:
    id: int
    entity_type: str
    entity_identifier: str
    analysis_run_id: int
    action: str
    signature: str = None
    created_at: str = None

@dataclass
class RkmDelta:
    delta_type: str
    entity_type: str
    entity_identifier: str
    before_value: Any
    after_value: Any
    details: str = None

@dataclass
class RkmHotspot:
    file_path: str
    change_count: int
    complexity_trend: str
    coupling_trend: str
    violation_count: int
    hotspot_score: float
    severity_level: str

@dataclass
class RkmTrend:
    entity_type: str
    entity_identifier: str
    metric_name: str
    direction: str
    velocity: float
    confidence: float = 1.0

@dataclass
class RkmEvolutionRun:
    analysis_run_id: int
    compare_run_id: int
    architecture_stability: float
    complexity_trend: float
    dependency_stability: float
    rule_compliance: float
    module_volatility: float
    documentation_coverage: float
    build_stability: float

