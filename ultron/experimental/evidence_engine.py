from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class MetricEvidence:
    metric_name: str
    observed_value: float
    threshold_value: float
    median_value: float
    percentile: float
    source: str

    def __post_init__(self):
        if not isinstance(self.metric_name, str) or not self.metric_name.strip():
            raise TypeError("metric_name must be a non-empty string")
        if not isinstance(self.source, str) or not self.source.strip():
            raise TypeError("source must be a non-empty string")
        
        # Cast numeric values to float
        try:
            self.observed_value = float(self.observed_value)
            self.threshold_value = float(self.threshold_value)
            self.median_value = float(self.median_value)
            self.percentile = float(self.percentile)
        except (ValueError, TypeError) as e:
            raise TypeError(f"Numeric parameters must be convertible to float: {e}")

        if not (0.0 <= self.percentile <= 100.0):
            raise ValueError(f"Percentile must be in the range [0.0, 100.0], got {self.percentile}")


@dataclass
class EvidenceBundle:
    filepath: str
    violation_type: str
    metrics: List[MetricEvidence] = field(default_factory=list)
    historical_bug_fixes: int = 0

    def __post_init__(self):
        if not isinstance(self.filepath, str) or not self.filepath.strip():
            raise TypeError("filepath must be a non-empty string")
        if not isinstance(self.violation_type, str) or not self.violation_type.strip():
            raise TypeError("violation_type must be a non-empty string")
        if not isinstance(self.metrics, list):
            raise TypeError("metrics must be a list of MetricEvidence")
        for metric in self.metrics:
            if not isinstance(metric, MetricEvidence):
                raise TypeError("metrics list must only contain MetricEvidence instances")
        
        try:
            self.historical_bug_fixes = int(self.historical_bug_fixes)
        except (ValueError, TypeError) as e:
            raise TypeError(f"historical_bug_fixes must be an integer: {e}")


class EvidenceEngine:
    def __init__(self, codebase: dict, coupling: list, hotspots: list, leaks: dict, git_history: dict, cycles: list):
        if not isinstance(codebase, dict):
            raise TypeError("codebase must be a dictionary")
        if not isinstance(coupling, list):
            raise TypeError("coupling must be a list")
        if not isinstance(hotspots, list):
            raise TypeError("hotspots must be a list")
        if not isinstance(leaks, dict):
            raise TypeError("leaks must be a dictionary")
        if not isinstance(git_history, dict):
            raise TypeError("git_history must be a dictionary")
        if not isinstance(cycles, list):
            raise TypeError("cycles must be a list")

        self.codebase = codebase
        self.coupling = coupling
        self.hotspots = hotspots
        self.leaks = leaks
        self.git_history = git_history
        self.cycles = cycles

        # Fast lookup mapping dictionaries
        self.coupling_by_file = {entry["file"]: entry for entry in coupling if "file" in entry}
        self.hotspot_by_file = {entry["file"]: entry for entry in hotspots if "file" in entry}

        # Distributions dictionary to compute medians/percentiles
        self.distributions: Dict[str, List[float]] = {
            "coupling_debt": [],
            "fan_in": [],
            "fan_out": [],
            "instability": [],
            "hotspot_score": [],
            "complexity": [],
            "leak_count": [],
            "max_leak_namespaces": [],
            "cycles_count": [],
            "bug_fix_count": []
        }

        # Medians cache
        self.medians: Dict[str, float] = {}

        self._populate_distributions()
        self._calculate_medians()

    def _populate_distributions(self):
        for f in self.codebase:
            # 1. Coupling metrics
            c_info = self.coupling_by_file.get(f, {})
            self.distributions["coupling_debt"].append(float(c_info.get("coupling_debt", 0.0)))
            self.distributions["fan_in"].append(float(c_info.get("fan_in", 0.0)))
            self.distributions["fan_out"].append(float(c_info.get("fan_out", 0.0)))
            self.distributions["instability"].append(float(c_info.get("instability", 0.0)))

            # 2. Hotspots metrics
            h_info = self.hotspot_by_file.get(f, {})
            self.distributions["hotspot_score"].append(float(h_info.get("hotspot_score", 0.0)))
            self.distributions["complexity"].append(float(h_info.get("complexity", 0.0)))

            # 3. Leaks metrics
            f_leaks = self.leaks.get(f, [])
            self.distributions["leak_count"].append(float(len(f_leaks)))
            max_ns = max([leak.get("responsibility_count", 0) for leak in f_leaks], default=0)
            self.distributions["max_leak_namespaces"].append(float(max_ns))

            # 4. Cycles count
            c_count = sum(1 for cycle in self.cycles if f in cycle)
            self.distributions["cycles_count"].append(float(c_count))

            # 5. Git fixes
            self.distributions["bug_fix_count"].append(float(self.git_history.get(f, 0)))

        # Sort all distributions to speed up percentile lookup
        for key in self.distributions:
            self.distributions[key].sort()

    def _calculate_medians(self):
        for key, dist in self.distributions.items():
            self.medians[key] = self._compute_median(dist)

    def _compute_median(self, values: List[float]) -> float:
        n = len(values)
        if n == 0:
            return 0.0
        if n % 2 == 1:
            return values[n // 2]
        else:
            return (values[n // 2 - 1] + values[n // 2]) / 2.0

    def _compute_percentile(self, metric_key: str, value: float) -> float:
        dist = self.distributions.get(metric_key, [])
        n = len(dist)
        if n == 0:
            return 100.0
        # Calculate how many elements are <= value
        count = sum(1 for x in dist if x <= value)
        return (count / n) * 100.0

    def generate_bundle(self, filepath: str, violation_type: str) -> EvidenceBundle:
        assert self is not None, "UMAGS Guard: Instance must not be None"

        if not isinstance(filepath, str) or not filepath.strip():
            raise TypeError("filepath must be a non-empty string")
        if not isinstance(violation_type, str) or not violation_type.strip():
            raise TypeError("violation_type must be a non-empty string")

        valid_types = [
            "Acyclic Dependencies Principle (ADP)",
            "Stable Dependencies Principle (SDP)",
            "Dependency Inversion Principle (DIP)",
            "Single Responsibility Principle (SRP - Abstraction Leak)",
            "Single Responsibility Principle (SRP - God Object Hotspot)"
        ]

        if violation_type not in valid_types:
            raise ValueError(f"Unrecognized violation_type: {violation_type}")

        metrics_evidence = []

        # Extract values
        c_info = self.coupling_by_file.get(filepath, {})
        h_info = self.hotspot_by_file.get(filepath, {})
        f_leaks = self.leaks.get(filepath, [])

        if violation_type == "Acyclic Dependencies Principle (ADP)":
            c_count = sum(1 for cycle in self.cycles if filepath in cycle)
            metrics_evidence.append(MetricEvidence(
                metric_name="Circular Dependency Loops",
                observed_value=c_count,
                threshold_value=1.0,
                median_value=self.medians["cycles_count"],
                percentile=self._compute_percentile("cycles_count", c_count),
                source="Coupling"
            ))

        elif violation_type == "Stable Dependencies Principle (SDP)":
            debt = float(c_info.get("coupling_debt", 0.0))
            fi = float(c_info.get("fan_in", 0.0))
            fo = float(c_info.get("fan_out", 0.0))
            instability = float(c_info.get("instability", 0.0))

            metrics_evidence.append(MetricEvidence(
                metric_name="Coupling Debt",
                observed_value=debt,
                threshold_value=20.0,
                median_value=self.medians["coupling_debt"],
                percentile=self._compute_percentile("coupling_debt", debt),
                source="Coupling"
            ))
            metrics_evidence.append(MetricEvidence(
                metric_name="Fan-in",
                observed_value=fi,
                threshold_value=0.0,
                median_value=self.medians["fan_in"],
                percentile=self._compute_percentile("fan_in", fi),
                source="Coupling"
            ))
            metrics_evidence.append(MetricEvidence(
                metric_name="Fan-out",
                observed_value=fo,
                threshold_value=0.0,
                median_value=self.medians["fan_out"],
                percentile=self._compute_percentile("fan_out", fo),
                source="Coupling"
            ))
            metrics_evidence.append(MetricEvidence(
                metric_name="Instability",
                observed_value=instability,
                threshold_value=0.3,
                median_value=self.medians["instability"],
                percentile=self._compute_percentile("instability", instability),
                source="Coupling"
            ))

        elif violation_type == "Dependency Inversion Principle (DIP)":
            fo = float(c_info.get("fan_out", 0.0))
            metrics_evidence.append(MetricEvidence(
                metric_name="Fan-out",
                observed_value=fo,
                threshold_value=8.0,
                median_value=self.medians["fan_out"],
                percentile=self._compute_percentile("fan_out", fo),
                source="Coupling"
            ))

        elif violation_type == "Single Responsibility Principle (SRP - Abstraction Leak)":
            l_count = float(len(f_leaks))
            max_ns = float(max([leak.get("responsibility_count", 0) for leak in f_leaks], default=0.0))

            metrics_evidence.append(MetricEvidence(
                metric_name="Abstraction Leaks Count",
                observed_value=l_count,
                threshold_value=1.0,
                median_value=self.medians["leak_count"],
                percentile=self._compute_percentile("leak_count", l_count),
                source="AST"
            ))
            metrics_evidence.append(MetricEvidence(
                metric_name="Max Leak Namespaces",
                observed_value=max_ns,
                threshold_value=8.0,
                median_value=self.medians["max_leak_namespaces"],
                percentile=self._compute_percentile("max_leak_namespaces", max_ns),
                source="AST"
            ))

        elif violation_type == "Single Responsibility Principle (SRP - God Object Hotspot)":
            score = float(h_info.get("hotspot_score", 0.0))
            complexity = float(h_info.get("complexity", 0.0))

            metrics_evidence.append(MetricEvidence(
                metric_name="Hotspot Score",
                observed_value=score,
                threshold_value=0.6,
                median_value=self.medians["hotspot_score"],
                percentile=self._compute_percentile("hotspot_score", score),
                source="Risk"
            ))
            metrics_evidence.append(MetricEvidence(
                metric_name="Cyclomatic Complexity",
                observed_value=complexity,
                threshold_value=40.0,
                median_value=self.medians["complexity"],
                percentile=self._compute_percentile("complexity", complexity),
                source="McCabe"
            ))

        bug_fixes = int(self.git_history.get(filepath, 0))

        return EvidenceBundle(
            filepath=filepath,
            violation_type=violation_type,
            metrics=metrics_evidence,
            historical_bug_fixes=bug_fixes
        )
