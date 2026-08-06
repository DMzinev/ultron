import os
from abc import ABC, abstractmethod
from typing import Any
from ultron.core.rkm.schema import (
    RkmDelta, RkmHotspot, RkmEvolutionRun, RkmEntityHistory, RkmTrend, EvaluationStatus
)
from ultron.core.rkm.store import RepositoryStore

class HealthProvider(ABC):
    @abstractmethod
    def calculate(self, store: RepositoryStore, current_run_id: int) -> float:
        pass

class ArchitectureStabilityProvider(HealthProvider):
    def calculate(self, store: RepositoryStore, current_run_id: int) -> float:
        run = store.get_analysis_run(current_run_id)
        if not run or not run.previous_run_id:
            return 1.0
        
        files_curr = store.get_file_records_for_run(current_run_id)
        files_prev = store.get_file_records_for_run(run.previous_run_id)
        
        map_curr = {f.path: f for f in files_curr}
        map_prev = {f.path: f for f in files_prev}
        
        deps_curr = set()
        for f in files_curr:
            for d in store.get_dependencies(f.id):
                deps_curr.add((f.path, d.target_path))
                
        deps_prev = set()
        for f in files_prev:
            for d in store.get_dependencies(f.id):
                deps_prev.add((f.path, d.target_path))
                
        if not deps_prev:
            return 1.0
            
        common = deps_curr & deps_prev
        return len(common) / len(deps_prev)

class RuleComplianceProvider(HealthProvider):
    def calculate(self, store: RepositoryStore, current_run_id: int) -> float:
        evals = store.conn.execute(
            "SELECT status FROM rkm_evaluations WHERE analysis_run_id = ?",
            (current_run_id,)
        ).fetchall()
        if not evals:
            return 1.0
        passed = sum(1 for e in evals if e["status"] == EvaluationStatus.PASSED)
        return passed / len(evals)

class ComplexityTrendProvider(HealthProvider):
    def calculate(self, store: RepositoryStore, current_run_id: int) -> float:
        trends = EvolutionEngine.compute_trends(store, current_run_id, depth=3)
        comp_trends = [t for t in trends if t.metric_name == "complexity"]
        if not comp_trends:
            return 1.0
        non_increasing = sum(1 for t in comp_trends if t.direction != "increasing")
        return non_increasing / len(comp_trends)

class EvolutionEngine:
    @staticmethod
    def compare_runs(store: RepositoryStore, run_id_a: int, run_id_b: int) -> list[RkmDelta]:
        run_a = store.get_analysis_run(run_id_a)
        run_b = store.get_analysis_run(run_id_b)
        if not run_a or not run_b:
            raise ValueError(f"Invalid run ID(s): {run_id_a}, {run_id_b}")

        files_a = store.get_file_records_for_run(run_id_a)
        files_b = store.get_file_records_for_run(run_id_b)

        map_a = {f.path: f for f in files_a}
        map_b = {f.path: f for f in files_b}

        deltas = []

        # 1. Added & Removed files
        added_files = set(map_b.keys()) - set(map_a.keys())
        removed_files = set(map_a.keys()) - set(map_b.keys())
        common_files = set(map_a.keys()) & set(map_b.keys())

        for p in added_files:
            deltas.append(RkmDelta("file_added", "file", p, None, p, f"File {p} added"))

        for p in removed_files:
            deltas.append(RkmDelta("file_removed", "file", p, p, None, f"File {p} removed"))

        # 2. Detailed common files comparisons
        for p in common_files:
            fa = map_a[p]
            fb = map_b[p]

            # Metrics comparison
            metrics_a = {m.name: m.value for m in store.get_metrics(fa.id)}
            metrics_b = {m.name: m.value for m in store.get_metrics(fb.id)}

            for mname in set(metrics_a.keys()) | set(metrics_b.keys()):
                val_a = metrics_a.get(mname, 0.0)
                val_b = metrics_b.get(mname, 0.0)
                if val_a != val_b:
                    dtype = "metric_increased" if val_b > val_a else "metric_decreased"
                    deltas.append(RkmDelta(
                        dtype, "metric", f"{p}:{mname}", str(val_a), str(val_b),
                        f"Metric {mname} changed from {val_a} to {val_b}"
                    ))

            # Dependencies comparison
            deps_a = {d.target_path for d in store.get_dependencies(fa.id)}
            deps_b = {d.target_path for d in store.get_dependencies(fb.id)}

            for d in deps_b - deps_a:
                deltas.append(RkmDelta(
                    "dependency_added", "dependency", f"{p}:{d}", None, d,
                    f"Dependency on {d} added to {p}"
                ))
            for d in deps_a - deps_b:
                deltas.append(RkmDelta(
                    "dependency_removed", "dependency", f"{p}:{d}", d, None,
                    f"Dependency on {d} removed from {p}"
                ))

        # 3. Violations comparison
        # get_violations returns list of tuples: (violation, rule, evidences)
        vios_a = store.get_violations(run_id_a)
        vios_b = store.get_violations(run_id_b)

        # Build maps of violations keyed by rule_id and details/evidence
        map_vios_a = {f"{v[1].id}:{v[0].details}": v[0] for v in vios_a}
        map_vios_b = {f"{v[1].id}:{v[0].details}": v[0] for v in vios_b}

        for k in set(map_vios_a.keys()) | set(map_vios_b.keys()):
            in_a = k in map_vios_a
            in_b = k in map_vios_b
            if in_b and not in_a:
                v = map_vios_b[k]
                deltas.append(RkmDelta("violation_introduced", "violation", k.split(":")[0], None, v.details, v.details))
            elif in_a and not in_b:
                v = map_vios_a[k]
                deltas.append(RkmDelta("violation_resolved", "violation", k.split(":")[0], v.details, None, f"Resolved: {v.details}"))

        return deltas

    @staticmethod
    def compute_trends(store: RepositoryStore, current_run_id: int, depth: int = 5) -> list[RkmTrend]:
        runs = []
        curr_id = current_run_id
        while curr_id and len(runs) < depth:
            run = store.get_analysis_run(curr_id)
            if not run:
                break
            runs.append(run)
            curr_id = run.previous_run_id

        if len(runs) < 2:
            return []

        # Reverse so they are chronologically ordered
        runs.reverse()

        # Collect metrics for all runs
        # Map of (file_path, metric_name) -> list of values corresponding to runs
        history = {}
        for r_idx, r in enumerate(runs):
            files = store.get_file_records_for_run(r.id)
            for f in files:
                metrics = store.get_metrics(f.id)
                for m in metrics:
                    key = (f.path, m.name)
                    if key not in history:
                        history[key] = [None] * len(runs)
                    history[key][r_idx] = m.value

        trends = []
        for (fpath, mname), vals in history.items():
            # Interpolate None values (using last known or 0.0)
            clean_vals = []
            last_known = 0.0
            for v in vals:
                if v is not None:
                    last_known = v
                clean_vals.append(last_known)

            # Perform velocity calculation: average successive differences
            diffs = [clean_vals[i] - clean_vals[i-1] for i in range(1, len(clean_vals))]
            velocity = sum(diffs) / len(diffs) if diffs else 0.0

            # Establish direction
            if abs(velocity) < 0.01:
                direction = "stable"
            elif velocity > 0:
                direction = "increasing"
            else:
                direction = "decreasing"

            # Custom override for high-level direction semantics
            # If complexity or coupling is decreasing, it is "improving". If increasing, "degrading".
            # For this dynamic engine, we will return standard enums: stable, increasing, decreasing
            trends.append(RkmTrend("file", fpath, mname, direction, velocity, 1.0))

        return trends

    @staticmethod
    def detect_hotspots(store: RepositoryStore, current_run_id: int) -> list[RkmHotspot]:
        files = store.get_file_records_for_run(current_run_id)
        trends = EvolutionEngine.compute_trends(store, current_run_id)
        
        # Build lookup maps for complexity & coupling trends
        comp_trends = {t.entity_identifier: t.direction for t in trends if t.metric_name == "complexity"}
        coup_trends = {t.entity_identifier: t.direction for t in trends if t.metric_name == "coupling"}
        
        # Get active violations
        vios = store.get_violations(current_run_id)
        
        hotspots = []
        for f in files:
            norm_path = os.path.normpath(f.path).replace("\\", "/")
            
            # Count historical entity modifications
            row = store.conn.execute(
                "SELECT COUNT(*) as cnt FROM rkm_entity_history WHERE entity_identifier = ? AND entity_type = 'file'",
                (norm_path,)
            ).fetchone()
            change_count = row["cnt"] if row else 0
            
            # Active violations count on this file
            vio_count = sum(1 for v in vios if v[0].file_id == f.id)
            
            c_trend = comp_trends.get(norm_path, "stable")
            cp_trend = coup_trends.get(norm_path, "stable")
            
            # Hotspot scoring formula
            score = change_count * 2.0 + vio_count * 3.0
            if c_trend == "increasing":
                score += 5.0
            if cp_trend == "increasing":
                score += 5.0
                
            if score >= 15.0:
                severity = "critical"
            elif score >= 10.0:
                severity = "high"
            elif score >= 5.0:
                severity = "medium"
            else:
                severity = "low"
                
            hotspots.append(RkmHotspot(norm_path, change_count, c_trend, cp_trend, vio_count, score, severity))
            
        hotspots.sort(key=lambda x: x.hotspot_score, reverse=True)
        return hotspots

    @staticmethod
    def evaluate_health_score(store: RepositoryStore, current_run_id: int) -> RkmEvolutionRun:
        run = store.get_analysis_run(current_run_id)
        if not run:
            raise ValueError(f"Run ID {current_run_id} not found")
            
        compare_run_id = run.previous_run_id if run.previous_run_id else current_run_id
        
        stability_provider = ArchitectureStabilityProvider()
        compliance_provider = RuleComplianceProvider()
        complexity_provider = ComplexityTrendProvider()
        
        arch_stability = stability_provider.calculate(store, current_run_id)
        rule_compliance = compliance_provider.calculate(store, current_run_id)
        complexity_trend = complexity_provider.calculate(store, current_run_id)
        
        return RkmEvolutionRun(
            analysis_run_id=current_run_id,
            compare_run_id=compare_run_id,
            architecture_stability=arch_stability,
            complexity_trend=complexity_trend,
            dependency_stability=arch_stability, # alias
            rule_compliance=rule_compliance,
            module_volatility=0.9, # stub values for other dimensions
            documentation_coverage=0.8,
            build_stability=1.0
        )

    @staticmethod
    def perform_impact_analysis(store: RepositoryStore, current_run_id: int, changed_files: list[str]) -> dict:
        # Normalize changed files
        normalized_changes = [os.path.normpath(f).replace("\\", "/") for f in changed_files]
        
        files = store.get_file_records_for_run(current_run_id)
        file_map = {f.path: f for f in files}
        
        # Build dependency graph: target -> list of source file paths depending on target
        dep_graph = {}
        for f in files:
            deps = store.get_dependencies(f.id)
            for d in deps:
                # Find matching target file path (handling imports)
                target = d.target_path
                # Simple import matching logic
                matched_target = None
                for candidate in file_map.keys():
                    if candidate.replace(".py", "").replace("/", ".").endswith(target):
                        matched_target = candidate
                        break
                if matched_target:
                    if matched_target not in dep_graph:
                        dep_graph[matched_target] = []
                    dep_graph[matched_target].append(f.path)

        # BFS/DFS traversal to collect impacted files
        impacted_files = set()
        queue = list(normalized_changes)
        while queue:
            curr = queue.pop(0)
            if curr not in impacted_files:
                impacted_files.add(curr)
                # Add callers depending on this file
                for caller in dep_graph.get(curr, []):
                    if caller not in impacted_files:
                        queue.append(caller)

        # Collect symbols impacted
        impacted_symbols = []
        for fpath in impacted_files:
            f_rec = file_map.get(fpath)
            if f_rec:
                symbols = store.conn.execute(
                    "SELECT name FROM rkm_symbols WHERE file_id = ?",
                    (f_rec.id,)
                ).fetchall()
                for s in symbols:
                    impacted_symbols.append(f"{fpath}:{s['name']}")

        # Affected rule evaluations
        vios = store.get_violations(current_run_id)
        affected_rules = set()
        for v in vios:
            v_file = store.conn.execute("SELECT path FROM rkm_files WHERE id = ?", (v[0].file_id,)).fetchone()
            if v_file and v_file["path"] in impacted_files:
                affected_rules.add(v[1].id)

        return {
            "impacted_files": sorted(list(impacted_files)),
            "impacted_symbols": sorted(impacted_symbols),
            "affected_rules": sorted(list(affected_rules))
        }
