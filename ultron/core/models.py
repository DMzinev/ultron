import os
from dataclasses import dataclass, asdict
from enum import Enum


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
}

_STRATEGY_DISPLAY = {
    "SAFE_EDIT":                    "Safe internal edits",
    "LOCAL_REFACTOR":               "Local refactoring",
    "INCREMENTAL_REFACTOR":         "Incremental refactoring",
    "EXTRACT_MODULE":               "Extract module / decompose",
    "REQUIRES_COMPATIBILITY_REVIEW":"Compatibility review required",
    "REQUIRES_REGRESSION_TESTS":    "Requires regression tests",
}


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
    churn:       dict  = None
    signals:     dict  = None

    # ---- new semantic dimensions ----
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
        if self.churn is None:
            d['churn'] = {"commits": 0, "authors": 0, "bug_fixes": 0, "multiplier": 1.0, "status": "unavailable"}
        if self.signals is None:
            d['signals'] = {
                "ast":      {"status": "active",      "weight": 0.35},
                "coupling": {"status": "active",      "weight": 0.25},
                "churn":    {"status": "unavailable",  "weight": 0.15},
                "coverage": {"status": "unavailable",  "weight": 0.25},
            }
        return d

    def __getitem__(self, key):
        d = self.to_dict()
        if key in d:
            return d[key]
        raise KeyError(key)

    def get(self, key, default=None):
        return self.to_dict().get(key, default)
