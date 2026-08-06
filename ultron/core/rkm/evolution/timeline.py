import os
from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.evolution.engine import EvolutionEngine

class DiffContext:
    def __init__(self, store: RepositoryStore, run_id_a: int, run_id_b: int):
        self.store = store
        self.run_id_a = run_id_a
        self.run_id_b = run_id_b

    def get_diff_summary(self) -> dict:
        deltas = EvolutionEngine.compare_runs(self.store, self.run_id_a, self.run_id_b)
        added = [d.entity_identifier for d in deltas if d.delta_type == "file_added"]
        removed = [d.entity_identifier for d in deltas if d.delta_type == "file_removed"]
        vios_added = [d.details for d in deltas if d.delta_type == "violation_introduced"]
        vios_resolved = [d.details for d in deltas if d.delta_type == "violation_resolved"]
        
        return {
            "run_id_before": self.run_id_a,
            "run_id_after": self.run_id_b,
            "files_added": added,
            "files_removed": removed,
            "violations_introduced": vios_added,
            "violations_resolved": vios_resolved,
            "total_deltas": len(deltas)
        }

class TrendContext:
    def __init__(self, store: RepositoryStore, current_run_id: int):
        self.store = store
        self.current_run_id = current_run_id

    def get_metric_trends(self) -> list[dict]:
        trends = EvolutionEngine.compute_trends(self.store, self.current_run_id)
        return [
            {
                "entity": t.entity_identifier,
                "metric": t.metric_name,
                "direction": t.direction,
                "velocity": t.velocity,
                "confidence": t.confidence
            }
            for t in trends
        ]

class HistoryContext:
    def __init__(self, store: RepositoryStore, repository_id: int):
        self.store = store
        self.repository_id = repository_id

    def get_runs_timeline(self) -> list[dict]:
        runs = self.store.get_analysis_runs(include_archived=False)
        # Filter for this repository specifically
        repo_runs = [r for r in runs if r.repository_id == self.repository_id]
        repo_runs.sort(key=lambda r: r.timestamp)
        return [
            {
                "run_id": r.id,
                "timestamp": r.timestamp,
                "duration": r.duration,
                "engine_version": r.engine_version,
                "semantic_hash": r.semantic_hash
            }
            for r in repo_runs
        ]

class EvolutionContext:
    def __init__(self, store: RepositoryStore, current_run_id: int):
        self.store = store
        self.current_run_id = current_run_id

    def get_evolution_brief(self) -> dict:
        health = EvolutionEngine.evaluate_health_score(self.store, self.current_run_id)
        hotspots = EvolutionEngine.detect_hotspots(self.store, self.current_run_id)
        critical_hotspots = [h.file_path for h in hotspots if h.severity_level == "critical"]
        
        return {
            "analysis_run_id": self.current_run_id,
            "health_metrics": {
                "architecture_stability": health.architecture_stability,
                "complexity_trend": health.complexity_trend,
                "rule_compliance": health.rule_compliance,
                "documentation_coverage": health.documentation_coverage
            },
            "critical_hotspots": critical_hotspots,
            "total_hotspots": len(hotspots)
        }
