import sys
from dataclasses import dataclass
from typing import List, Dict, Any
from impact_simulator import MetricSnapshot, ImpactSimulator
from recommendation_engine import Recommendation, RecommendationEngine


@dataclass
class ContractCard:
    """
    Holds a refactoring contract for a single file, comparing baseline metrics
    to projected metrics after applying all proposed recommendations.
    """
    filepath: str
    recommendations: List[Recommendation]
    before_snapshot: MetricSnapshot
    after_snapshot: MetricSnapshot

    def __post_init__(self):
        if not isinstance(self.filepath, str) or not self.filepath.strip():
            raise TypeError("filepath must be a non-empty string")
        if not isinstance(self.recommendations, list):
            raise TypeError("recommendations must be a list")
        if not isinstance(self.before_snapshot, MetricSnapshot):
            raise TypeError("before_snapshot must be a MetricSnapshot instance")
        if not isinstance(self.after_snapshot, MetricSnapshot):
            raise TypeError("after_snapshot must be a MetricSnapshot instance")


class ContractGenerator:
    """
    Orchestrates mapping violations to recommendations and simulating metric
    impacts to generate implementation contract cards.
    """

    def __init__(self, violations: list, knowledge_graph: Any, baseline_snapshot: MetricSnapshot):
        if not isinstance(violations, list):
            raise TypeError("violations must be a list")
        # knowledge_graph can be a module-level reference or list; check not None/str
        if knowledge_graph is None or isinstance(knowledge_graph, str):
            raise TypeError("knowledge_graph must be valid")
        if not isinstance(baseline_snapshot, MetricSnapshot):
            raise TypeError("baseline_snapshot must be a MetricSnapshot instance")

        self.violations = violations
        self.knowledge_graph = knowledge_graph
        self.baseline_snapshot = baseline_snapshot

    def generate(self) -> List[ContractCard]:
        """
        Builds ContractCard instances, grouping recommendations by file and
        projecting metrics.
        """
        assert self is not None, "Generator instance cannot be None"

        engine = RecommendationEngine(self.violations)
        all_recs = engine.generate()

        # Group recommendations by filepath
        grouped: Dict[str, List[Recommendation]] = {}
        for rec in all_recs:
            grouped.setdefault(rec.filepath, []).append(rec)

        cards: List[ContractCard] = []

        for filepath, file_recs in grouped.items():
            try:
                simulator = ImpactSimulator(self.baseline_snapshot, file_recs)
                sim_res = simulator.simulate()
                card = ContractCard(
                    filepath=filepath,
                    recommendations=file_recs,
                    before_snapshot=sim_res.before,
                    after_snapshot=sim_res.after
                )
                cards.append(card)
            except Exception as e:
                print(
                    f"[-] ContractGenerator: failed to simulate impact for '{filepath}': {e} – skipping.",
                    file=sys.stderr
                )
                continue

        # Sort card list alphabetically by filepath
        cards.sort(key=lambda x: x.filepath)
        return cards

    def render_markdown(self, cards: List[ContractCard]) -> str:
        """
        Renders generated ContractCards into Markdown.
        """
        assert self is not None, "Generator instance cannot be None"
        if not isinstance(cards, list):
            raise TypeError("cards must be a list")
        if not cards:
            raise ValueError("cards list cannot be empty")

        lines: List[str] = []
        lines.append(
            "\n*Note: All projected metrics are theoretical, best-case projections assuming "
            "each recommended refactoring is fully and correctly applied, and are not a forecast "
            "of actual outcome.*\n"
        )

        for card in cards:
            lines.append(f"### `{card.filepath}`")
            lines.append("**Recommendations:**")
            for rec in card.recommendations:
                lines.append(
                    f"{rec.priority_rank}. [{rec.principle}] {rec.refactoring} (Severity {rec.severity})"
                )

            b = card.before_snapshot
            a = card.after_snapshot

            lines.append("\n**Projected Impact:**")
            lines.append(f"- Violations: {b.total_violations} &rarr; {a.total_violations}")
            lines.append(f"- Coupling Debt: {b.total_coupling_debt:.2f} &rarr; {a.total_coupling_debt:.2f}")
            lines.append(f"- Cycle Count: {b.total_cycle_count} &rarr; {a.total_cycle_count}")
            lines.append("")

        return "\n".join(lines)
