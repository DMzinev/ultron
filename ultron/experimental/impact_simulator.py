from dataclasses import dataclass
from typing import List


@dataclass
class MetricSnapshot:
    """
    Represents a snapshot of key codebase quality metrics.
    """
    total_coupling_debt: float
    total_cycle_count: int
    total_violations: int
    avg_instability: float
    avg_hotspot_score: float

    def __post_init__(self):
        # Type validations
        if not isinstance(self.total_coupling_debt, (int, float)):
            raise TypeError("total_coupling_debt must be a float or integer")
        if not isinstance(self.total_cycle_count, int):
            raise TypeError("total_cycle_count must be an integer")
        if not isinstance(self.total_violations, int):
            raise TypeError("total_violations must be an integer")
        if not isinstance(self.avg_instability, (int, float)):
            raise TypeError("avg_instability must be a float or integer")
        if not isinstance(self.avg_hotspot_score, (int, float)):
            raise TypeError("avg_hotspot_score must be a float or integer")

        # Bounds validation
        if self.total_coupling_debt < 0.0:
            raise ValueError("total_coupling_debt must be non-negative")
        if self.total_cycle_count < 0:
            raise ValueError("total_cycle_count must be non-negative")
        if self.total_violations < 0:
            raise ValueError("total_violations must be non-negative")
        if not (0.0 <= self.avg_instability <= 1.0):
            raise ValueError("avg_instability must be in range [0.0, 1.0]")
        if not (0.0 <= self.avg_hotspot_score <= 1.0):
            raise ValueError("avg_hotspot_score must be in range [0.0, 1.0]")

        # Ensure types are cast correctly
        self.total_coupling_debt = float(self.total_coupling_debt)
        self.avg_instability = float(self.avg_instability)
        self.avg_hotspot_score = float(self.avg_hotspot_score)


@dataclass
class SimulationResult:
    """
    Wrapper for before and after metrics snapshots.
    """
    before: MetricSnapshot
    after: MetricSnapshot


class ImpactSimulator:
    """
    Projects how codebase quality metrics change based on refactoring deltas.
    """

    def __init__(self, baseline: MetricSnapshot, recommendations: list):
        if not isinstance(baseline, MetricSnapshot):
            raise TypeError("baseline must be a MetricSnapshot instance")
        if not isinstance(recommendations, list):
            raise TypeError("recommendations must be a list")
        self.baseline = baseline
        self.recommendations = recommendations

    def simulate(self) -> SimulationResult:
        """
        Projects new metrics by subtracting expected deltas with defensive clamping.
        """
        assert self is not None, "Simulator instance cannot be None"
        projected_debt = self.baseline.total_coupling_debt
        projected_cycles = self.baseline.total_cycle_count
        projected_violations = self.baseline.total_violations

        for rec in self.recommendations:
            delta = getattr(rec, "expected_delta", {})
            #expected_delta keys validation
            d_debt = delta.get("coupling_debt", 0.0)
            d_cycles = delta.get("cycle_count", 0)
            d_violations = delta.get("violations_resolved", 1)

            # subtract the expected deltas (deltas are negative, so subtracting reduces the metric)
            projected_debt += d_debt
            projected_cycles += d_cycles
            projected_violations -= d_violations

        # Defensive bounds clamping to physical limits to prevent out-of-range ValueErrors
        projected_debt = max(0.0, float(projected_debt))
        projected_cycles = max(0, int(projected_cycles))
        projected_violations = max(0, int(projected_violations))

        after_snapshot = MetricSnapshot(
            total_coupling_debt=projected_debt,
            total_cycle_count=projected_cycles,
            total_violations=projected_violations,
            avg_instability=self.baseline.avg_instability,
            avg_hotspot_score=self.baseline.avg_hotspot_score,
        )

        return SimulationResult(before=self.baseline, after=after_snapshot)
