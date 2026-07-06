import sys
from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass
class Recommendation:
    """
    A prioritized refactoring recommendation mapping a codebase violation card
    to its proposed refactoring and expected metric delta.
    """
    filepath: str
    principle: str
    smell: str
    refactoring: str
    expected_delta: Dict[str, Any]
    severity: int
    priority_rank: int

    def __post_init__(self):
        # Type validations
        if not isinstance(self.filepath, str) or not self.filepath.strip():
            raise TypeError("filepath must be a non-empty string")
        if not isinstance(self.principle, str) or not self.principle.strip():
            raise TypeError("principle must be a non-empty string")
        if not isinstance(self.smell, str) or not self.smell.strip():
            raise TypeError("smell must be a non-empty string")
        if not isinstance(self.refactoring, str) or not self.refactoring.strip():
            raise TypeError("refactoring must be a non-empty string")
        if not isinstance(self.expected_delta, dict):
            raise TypeError("expected_delta must be a dictionary")
        if not isinstance(self.severity, int):
            raise TypeError("severity must be an integer")
        if not isinstance(self.priority_rank, int):
            raise TypeError("priority_rank must be an integer")

        # Value bounds validation
        if not (1 <= self.severity <= 5):
            raise ValueError("severity must be between 1 and 5 inclusive")
        if self.priority_rank < 1:
            raise ValueError("priority_rank must be >= 1")


# Static mapping from ReasoningCard principle strings to KnowledgeGraph smell keys.
_PRINCIPLE_TO_SMELL: Dict[str, str] = {
    "Acyclic Dependencies Principle (ADP)": "circular_dependency",
    "Stable Dependencies Principle (SDP)": "unstable_dependency",
    "Dependency Inversion Principle (DIP)": "high_fan_out",
    "Single Responsibility Principle (SRP - Abstraction Leak)": "abstraction_leak",
    "Single Responsibility Principle (SRP - God Object Hotspot)": "god_object_hotspot",
}


class RecommendationEngine:
    """
    Processes structural violation cards and maps them using the Knowledge Graph
    to produce prioritized refactoring recommendations.
    """

    def __init__(self, cards: list):
        if not isinstance(cards, list):
            raise TypeError("cards must be a list")
        self.cards = cards

    def generate(self) -> List[Recommendation]:
        """
        Processes cards, resolves smells, sorts, and ranks recommendations.
        """
        from knowledge_graph import lookup

        assert self.cards is not None, "Violation cards list cannot be None"
        recs: List[Recommendation] = []

        for card in self.cards:
            principle = getattr(card, "principle", None)
            filepath = getattr(card, "filepath", None)

            if not principle or not filepath:
                print(
                    "[-] RecommendationEngine: skipping card with missing principle or filepath.",
                    file=sys.stderr
                )
                continue

            smell = _PRINCIPLE_TO_SMELL.get(principle)
            if smell is None:
                print(
                    f"[-] RecommendationEngine: unrecognized principle '{principle}' – skipping.",
                    file=sys.stderr
                )
                continue

            try:
                edge = lookup(smell)
            except (KeyError, TypeError) as e:
                print(
                    f"[-] RecommendationEngine: failed to lookup smell '{smell}': {e} – skipping.",
                    file=sys.stderr
                )
                continue

            rec = Recommendation(
                filepath=filepath,
                principle=principle,
                smell=smell,
                refactoring=edge.refactoring,
                expected_delta=edge.expected_delta,
                severity=edge.severity,
                priority_rank=1  # placeholder
            )
            recs.append(rec)

        # Sort recommendations: lowest severity value first (severity ASC),
        # using alphabetical filepath as tie-breaker (filepath ASC).
        recs.sort(key=lambda x: (x.severity, x.filepath))

        # Assign stable 1-based priority_rank after sorting
        for idx, r in enumerate(recs, 1):
            r.priority_rank = idx

        return recs
