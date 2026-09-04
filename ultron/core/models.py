import os
from dataclasses import dataclass, asdict, field
from enum import Enum
from ultron.core.evidence import (
    EvidenceClassification, ConfidenceTier, EvidenceStatus,
    EvidenceRecord, EvidenceBundle
)


# ---------------------------------------------------------------------------
# Enums — describe what a file IS and how to approach changing it
# ---------------------------------------------------------------------------

_ROLE_DISPLAY = {
    "INTERNAL":           "Internal",
    "PACKAGE_INITIALIZER":"Package Initializer",
    "PUBLIC_MODULE":      "Public Module",
    "CLI":                "CLI Entry Point",
    "SERVER":             "Web Server",
    "MCP_TOOL":           "MCP Tool Server",
    "TEST":               "Test Module",
    "SCRIPT":             "Script File",
    "EXPERIMENTAL":       "Experimental Feature",
    "CORE_ENGINE":        "Core Engine",
    "CONFIGURATION":      "Configuration",
    "DOCUMENTATION":      "Documentation",
    "TOOLING":            "Development Tooling",
}

_STRATEGY_DISPLAY = {
    "SAFE_EDIT":                    "Safe internal edits",
    "LOCAL_REFACTOR":               "Local refactoring",
    "INCREMENTAL_REFACTOR":         "Incremental refactoring",
    "EXTRACT_MODULE":               "Extract module / decompose",
    "REQUIRES_COMPATIBILITY_REVIEW":"Compatibility review required",
    "REQUIRES_REGRESSION_TESTS":    "Requires regression tests",
}


class FileCategory(str, Enum):
    """
    High-level partition of files to prevent category mistakes.
    Tests, docs, and configs never compete with production code for development recommendations.
    """
    PRODUCTION_CODE = "PRODUCTION_CODE"
    TEST_CODE       = "TEST_CODE"
    CONFIGURATION   = "CONFIGURATION"
    GENERATED       = "GENERATED"
    DOCUMENTATION   = "DOCUMENTATION"
    TOOLING         = "TOOLING"
    UNKNOWN         = "UNKNOWN"


class RecommendationAction(str, Enum):
    """
    First-class action guidance for development recommendations.
    """
    INVESTIGATE      = "INVESTIGATE"
    REFACTOR         = "REFACTOR"
    PROTECT          = "PROTECT"
    DEFER            = "DEFER"
    DO_NOT_RECOMMEND = "DO_NOT_RECOMMEND"


class ArchitecturalRole(str, Enum):
    """
    Stable classification of module responsibility.

    Describes what a file IS, not how risky it is.
    Adding a new role = adding one entry here + one rule in scoring.py.
    """
    INTERNAL            = "INTERNAL"
    PACKAGE_INITIALIZER = "PACKAGE_INITIALIZER"
    PUBLIC_MODULE       = "PUBLIC_MODULE"
    CLI                 = "CLI"
    SERVER              = "SERVER"
    MCP_TOOL            = "MCP_TOOL"
    TEST                = "TEST"
    SCRIPT              = "SCRIPT"
    EXPERIMENTAL        = "EXPERIMENTAL"
    CORE_ENGINE         = "CORE_ENGINE"
    CONFIGURATION       = "CONFIGURATION"
    DOCUMENTATION       = "DOCUMENTATION"
    TOOLING             = "TOOLING"

    @property
    def display_name(self):
        return _ROLE_DISPLAY.get(self.value, self.value.replace("_", " ").title())


class ChangeStrategy(str, Enum):
    """
    How cautiously a developer should modify a file.

    Derived from Role + Risk tier. Stable identifiers for AI agent consumption.
    """
    SAFE_EDIT                     = "SAFE_EDIT"
    LOCAL_REFACTOR                = "LOCAL_REFACTOR"
    INCREMENTAL_REFACTOR          = "INCREMENTAL_REFACTOR"
    EXTRACT_MODULE                = "EXTRACT_MODULE"
    REQUIRES_COMPATIBILITY_REVIEW = "REQUIRES_COMPATIBILITY_REVIEW"
    REQUIRES_REGRESSION_TESTS     = "REQUIRES_REGRESSION_TESTS"

    @property
    def display_name(self):
        return _STRATEGY_DISPLAY.get(self.value, self.value.replace("_", " ").title())


# Reverse-lookup maps for __post_init__ coercion
_DISPLAY_TO_ROLE = {v: k for k, v in _ROLE_DISPLAY.items()}


# ---------------------------------------------------------------------------
# AnalysisPacket
# ---------------------------------------------------------------------------

@dataclass
class AnalysisPacket:
    # ---- non-default fields (must come first) ----
    file_path:     str
    impact_score:  float
    coupling_score:float
    mk_r:          float
    delta_cest:    float
    confidence:    float

    # ---- optional metadata (default values) ----
    level:       str   = "LOW"
    boundary_type: str = "Internal"   # legacy display string — do not use in new code
    complexity:  int   = 1
    mitigation:  str   = ""
    callers:     list  = None
    changes:     list  = None
    delta_score: float = 0.0

    # ---- new semantic dimensions ----
    category:           str               = "PRODUCTION_CODE"
    architectural_role: ArchitecturalRole = ArchitecturalRole.INTERNAL
    change_strategy:    ChangeStrategy    = ChangeStrategy.SAFE_EDIT

    def __post_init__(self):
        # Coerce string → enum (handles dicts / JSON deserialization)
        if isinstance(self.architectural_role, str):
            try:
                self.architectural_role = ArchitecturalRole(self.architectural_role)
            except ValueError:
                # Try legacy display name (e.g. "Package Initializer")
                key = _DISPLAY_TO_ROLE.get(self.architectural_role)
                self.architectural_role = ArchitecturalRole(key) if key else ArchitecturalRole.INTERNAL

        if isinstance(self.change_strategy, str):
            try:
                self.change_strategy = ChangeStrategy(self.change_strategy)
            except ValueError:
                self.change_strategy = ChangeStrategy.SAFE_EDIT

        # Sync boundary_type ← role so legacy attribute reads stay correct
        self.boundary_type = self.architectural_role.display_name

    def to_dict(self):
        if self is None:
            raise ValueError("self cannot be None")
        d = asdict(self)
        # Legacy aliases (UI backward compat)
        d['file']     = self.file_path
        d['filepath'] = os.path.basename(self.file_path) if self.file_path else ""
        d['score']    = round(self.impact_score, 2)
        d['coupling'] = self.coupling_score
        d['mkr']      = self.mk_r
        # boundary_type kept for legacy UI consumers; new code should read architectural_role
        d['boundary_type']       = self.architectural_role.display_name
        # Stable enum identifiers for AI agents and new UI code
        d['architectural_role']  = self.architectural_role.value
        d['change_strategy']     = self.change_strategy.value
        d['change_strategy_display'] = self.change_strategy.display_name
        if self.callers is None:
            d['callers'] = []
        if self.changes is None:
            d['changes'] = []
        return d

    def __getitem__(self, key):
        d = self.to_dict()
        if key in d:
            return d[key]
        raise KeyError(key)

    def get(self, key, default=None):
        return self.to_dict().get(key, default)


def build_snapshot_id(content_hash: str) -> str:
    """
    Canonical helper for generating deterministic, state-bound snapshot identifiers.
    Invariant: Identical content_hash yields identical snapshot_id.
    """
    if not content_hash or not isinstance(content_hash, str):
        return "snap-0000000000000000"
    clean_hash = content_hash.strip().lower()
    return f"snap-{clean_hash[:16]}"


@dataclass
class RecommendationPacket:
    target_file: str
    category: str                          # FileCategory.value
    priority_score: float                  # Continuous ranking metric
    priority_level: str                    # "HIGH" | "MEDIUM" | "LOW"
    confidence_tier: str                   # "HIGH" | "MEDIUM" | "LOW"
    recommendation_action: str             # "INVESTIGATE" | "REFACTOR" | "PROTECT" | "DEFER" | "DO_NOT_RECOMMEND"
    
    # 7-Question Explainability Contract
    why_this: str                          # Q1: Plain-English role & identity
    why_now: str                           # Q2: Priority justification & workflow centrality / intent
    what_it_affects: list                  # Q3: Direct downstream dependents
    what_could_break: str                  # Q4: Plain-English downstream risk explanation
    evidence_tier: str                     # Q5: "OBSERVED" | "DERIVED" | "INFERRED" | "UNKNOWN"
    confidence_reason: str                 # Q6: Why confidence is High/Med/Low
    next_action: str                       # Q7: Specific actionable next step

    # Structural Telemetry (Collapsible under 'Technical Details')
    complexity: int = 1
    coupling: int = 0
    impact_score: float = 0.0
    public_surface: str = "INTERNAL"
    cycle_involvement: bool = False
    alternatives_compared: list = field(default_factory=list)
    evidence_records: list = field(default_factory=list)
    limitations: list = field(default_factory=list)
    policy_version: str = "consequence_v1"
    engine_version: str = "1.0.0"

    def to_dict(self) -> dict:
        return asdict(self)

    def __getitem__(self, key):
        d = self.to_dict()
        if key in d:
            return d[key]
        raise KeyError(key)

    def get(self, key, default=None):
        return self.to_dict().get(key, default)


class SelectionOutcome(str, Enum):
    """Epistemic 5-state evaluation outcome for recommendations."""
    USEFUL                = "USEFUL"
    PLAUSIBLE             = "PLAUSIBLE"
    WRONG                 = "WRONG"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    PENDING               = "PENDING"


class DecisionOutcome(str, Enum):
    """Final development lifecycle outcome of a selected target."""
    RESOLVED    = "RESOLVED"
    ABANDONED   = "ABANDONED"
    REVERTED    = "REVERTED"
    NO_DECISION = "NO_DECISION"
    PENDING     = "PENDING"


@dataclass
class DecisionRecord:
    decision_id: str
    recommendation_id: str
    policy_version: str = "consequence_v1"
    engine_version: str = "1.0.0"
    created_at: str = ""
    recommended_target: str = ""
    human_selected_target: str = ""
    final_target_changed: bool = False
    top_alternatives: list = field(default_factory=list)
    confidence_tier: str = "HIGH"
    evidence_tier: str = "OBSERVED"
    selection_source: str = "HUMAN"               # "HUMAN" | "AGENT" | "AUTO"
    selection_outcome: str = "PENDING"             # SelectionOutcome.value
    human_feedback: str = ""
    mission_id: str = ""
    attempt_id: str = ""
    checkpoint_id: str = ""
    outcome_of_selected_target: str = "PENDING"   # DecisionOutcome.value
    value_delta: dict = field(default_factory=dict)
    priority_score: float = 0.0
    recommendation_action: str = "INVESTIGATE"
    why_this: str = ""
    evidence_ids: list = field(default_factory=list)
    evidence_status: str = "FRESH"

    def to_dict(self) -> dict:
        return asdict(self)

    def __getitem__(self, key):
        d = self.to_dict()
        if key in d:
            return d[key]
        raise KeyError(key)

    def get(self, key, default=None):
        return self.to_dict().get(key, default)


