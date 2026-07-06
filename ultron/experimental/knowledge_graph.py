from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class KnowledgeEdge:
    """
    Represents an edge in the design smell catalog linking a smell key to
    its metric deltas and refactoring recommendations.
    """
    smell_key: str
    refactoring: str
    expected_delta: Dict[str, Any]
    severity: int

    def __post_init__(self):
        # Type validation
        if not isinstance(self.smell_key, str) or not self.smell_key.strip():
            raise TypeError("smell_key must be a non-empty string")
        if not isinstance(self.refactoring, str) or not self.refactoring.strip():
            raise TypeError("refactoring must be a non-empty string")
        if not isinstance(self.expected_delta, dict):
            raise TypeError("expected_delta must be a dictionary")
        if not isinstance(self.severity, int):
            raise TypeError("severity must be an integer")

        # Value bounds validation
        if not (1 <= self.severity <= 5):
            raise ValueError("severity must be between 1 and 5 inclusive")

        # expected_delta required keys validation
        required_keys = {"coupling_debt", "cycle_count", "violations_resolved"}
        if not required_keys.issubset(self.expected_delta.keys()):
            raise ValueError(f"expected_delta must contain keys: {required_keys}")

        # expected_delta values type validation
        if not isinstance(self.expected_delta["coupling_debt"], (int, float)):
            raise TypeError("coupling_debt delta must be a float or int")
        if not isinstance(self.expected_delta["cycle_count"], int):
            raise TypeError("cycle_count delta must be an integer")
        if not isinstance(self.expected_delta["violations_resolved"], int):
            raise TypeError("violations_resolved delta must be an integer")


KNOWLEDGE_GRAPH: List[KnowledgeEdge] = [
    KnowledgeEdge(
        smell_key="circular_dependency",
        refactoring="Break circular dependency by extracting a shared interface or using dependency injection.",
        expected_delta={"coupling_debt": -15.0, "cycle_count": -1, "violations_resolved": 1},
        severity=1
    ),
    KnowledgeEdge(
        smell_key="unstable_dependency",
        refactoring="Encapsulate volatile details or introduce an abstraction layer.",
        expected_delta={"coupling_debt": -10.0, "cycle_count": 0, "violations_resolved": 1},
        severity=2
    ),
    KnowledgeEdge(
        smell_key="stable_depends_on_volatile",
        refactoring="Invert dependency using Stable Dependencies Principle; depend on abstractions.",
        expected_delta={"coupling_debt": -8.0, "cycle_count": 0, "violations_resolved": 1},
        severity=2
    ),
    KnowledgeEdge(
        smell_key="high_fan_out",
        refactoring="Apply Dependency Inversion Principle; decouple callers from concrete details.",
        expected_delta={"coupling_debt": -5.0, "cycle_count": 0, "violations_resolved": 1},
        severity=3
    ),
    KnowledgeEdge(
        smell_key="abstraction_leak",
        refactoring="Refactor single-responsibility violation; extract helper classes.",
        expected_delta={"coupling_debt": -2.0, "cycle_count": 0, "violations_resolved": 1},
        severity=4
    ),
    KnowledgeEdge(
        smell_key="god_object_hotspot",
        refactoring="Decompose large module/class into cohesive, independent subsystems.",
        expected_delta={"coupling_debt": -5.0, "cycle_count": 0, "violations_resolved": 1},
        severity=5
    )
]

# O(1) Cache map
_GRAPH_CACHE: Dict[str, KnowledgeEdge] = {edge.smell_key: edge for edge in KNOWLEDGE_GRAPH}


def lookup(smell_key: str) -> KnowledgeEdge:
    """
    Performs O(1) cached lookup of a design smell key.
    Raises KeyError if unrecognized.
    """
    # Defensive inputs
    if not isinstance(smell_key, str) or not smell_key.strip():
        raise TypeError("smell_key must be a non-empty string")

    if smell_key not in _GRAPH_CACHE:
        raise KeyError(f"Smell key '{smell_key}' not found in Knowledge Graph catalog")

    return _GRAPH_CACHE[smell_key]
