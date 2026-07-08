import sys
from dataclasses import dataclass
from typing import List, Dict, Any
from ultron.experimental.impact_simulator import MetricSnapshot, ImpactSimulator
from ultron.experimental.recommendation_engine import Recommendation, RecommendationEngine


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

    def __init__(self, violations: list, knowledge_graph: Any, baseline_snapshot: MetricSnapshot,
                 debt_scores: list = None, cycles: list = None, hotspots: list = None):
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
        self.debt_scores = debt_scores
        self.cycles = cycles
        self.hotspots = hotspots

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
                # Compute localized per-file baseline snapshot
                # Violations: count of static violations for this file
                file_violations = len([v for v in self.violations if getattr(v, "filepath", None) == filepath])

                # Coupling Debt: file's coupling debt score if available
                if self.debt_scores is not None:
                    file_debt = next((e["coupling_debt"] for e in self.debt_scores if e.get("file") == filepath), 0.0)
                else:
                    file_debt = self.baseline_snapshot.total_coupling_debt

                # Cycle Count: count of circular dependency loops this file is part of
                if self.cycles is not None:
                    file_cycles = sum(1 for c in self.cycles if filepath in c)
                else:
                    file_cycles = self.baseline_snapshot.total_cycle_count

                # Instability: file's instability score if available
                if self.debt_scores is not None:
                    file_inst = next((e["instability"] for e in self.debt_scores if e.get("file") == filepath), 0.0)
                else:
                    file_inst = self.baseline_snapshot.avg_instability

                # Hotspot Score: file's hotspot score if available
                if self.hotspots is not None:
                    file_hs = next((e["hotspot_score"] for e in self.hotspots if e.get("file") == filepath), 0.0)
                else:
                    file_hs = self.baseline_snapshot.avg_hotspot_score

                # Clamp values to valid ranges defensively
                file_violations = max(0, file_violations)
                file_debt = max(0.0, float(file_debt))
                file_cycles = max(0, file_cycles)
                file_inst = max(0.0, min(1.0, float(file_inst)))
                file_hs = max(0.0, min(1.0, float(file_hs)))

                file_baseline = MetricSnapshot(
                    total_coupling_debt=file_debt,
                    total_cycle_count=file_cycles,
                    total_violations=file_violations,
                    avg_instability=file_inst,
                    avg_hotspot_score=file_hs
                )

                simulator = ImpactSimulator(file_baseline, file_recs)
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
            for idx, rec in enumerate(card.recommendations, 1):
                lines.append(
                    f"{idx}. (Priority #{rec.priority_rank}) [{rec.principle}] {rec.refactoring} (Severity {rec.severity})"
                )

            b = card.before_snapshot
            a = card.after_snapshot

            lines.append("\n**Projected Impact:**")
            lines.append(f"- Violations: {b.total_violations} &rarr; {a.total_violations}")
            lines.append(f"- Coupling Debt: {b.total_coupling_debt:.2f} &rarr; {a.total_coupling_debt:.2f}")
            lines.append(f"- Cycle Count: {b.total_cycle_count} &rarr; {a.total_cycle_count}")
            lines.append("")

        return "\n".join(lines)
