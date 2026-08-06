from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.schema import RunComparison

def _validate_path(path: str) -> str:
    if path is None:
        raise TypeError("Path cannot be None")
    if not isinstance(path, str):
        raise TypeError("Path must be a string")
    if not path.strip():
        raise ValueError("Path cannot be empty")
    return path.replace("\\", "/")

class QueryRepository:
    def __init__(self, db_path: str):
        self.store = RepositoryStore(db_path)

    def get_files(self, include_archived: bool = False):
        if not isinstance(include_archived, bool):
            raise TypeError("include_archived must be a boolean")
        return self.store.get_files(include_archived=include_archived)

    def get_file_detail(self, path: str, include_archived: bool = False) -> dict:
        if not isinstance(include_archived, bool):
            raise TypeError("include_archived must be a boolean")
        normalized_path = _validate_path(path)
        files = self.store.get_files(include_archived=include_archived)
        file_rec = next((f for f in files if f.path == normalized_path), None)
        if not file_rec:
            return {}

        symbols = self.store.get_symbols(file_rec.id)
        deps = self.store.get_dependencies(file_rec.id)
        metrics = self.store.get_metrics(file_rec.id)
        facts = self.store.get_facts(file_rec.id)
        arch = self.store.get_architecture(file_rec.id)

        # Build diagnostic chain
        diagnostic_chain = []
        for fact in facts:
            interpretations = self.store.get_interpretations(fact.id)
            for inter in interpretations:
                recs = self.store.get_recommendations(inter.id)
                diagnostic_chain.append({
                    "fact": {
                        "category": fact.category,
                        "metric": fact.metric,
                        "value": fact.value,
                        "value_type": fact.value_type,
                        "source_type": fact.source_type,
                        "source_reference": fact.source_reference
                    },
                    "interpretation": {
                        "rule": inter.rule,
                        "result": inter.result,
                        "confidence": inter.confidence
                    },
                    "recommendations": [
                        {
                            "action": r.action,
                            "confidence_type": r.confidence_type,
                            "confidence_value": r.confidence_value,
                            "status": r.status
                        }
                        for r in recs
                    ]
                })

        return {
            "file": {
                "path": file_rec.path,
                "role": file_rec.role,
                "package": file_rec.package,
                "size": file_rec.size,
                "last_modified": file_rec.last_modified
            },
            "symbols": [{"name": s.name, "type": s.type, "lineno": s.lineno} for s in symbols],
            "dependencies": [d.target_path for d in deps],
            "metrics": {m.name: m.value for m in metrics},
            "architecture": [{"layer": a.layer, "role": a.role} for a in arch],
            "diagnostic_chain": diagnostic_chain
        }

    def get_dependencies(self, path: str, include_archived: bool = False) -> list[str]:
        if not isinstance(include_archived, bool):
            raise TypeError("include_archived must be a boolean")
        normalized_path = _validate_path(path)
        files = self.store.get_files(include_archived=include_archived)
        file_rec = next((f for f in files if f.path == normalized_path), None)
        if not file_rec:
            return []
        deps = self.store.get_dependencies(file_rec.id)
        return [d.target_path for d in deps]

    def get_hotspots(self, include_archived: bool = False) -> list[dict]:
        if not isinstance(include_archived, bool):
            raise TypeError("include_archived must be a boolean")
        files = self.store.get_files(include_archived=include_archived)
        hotspots = []
        for f in files:
            metrics = self.store.get_metrics(f.id)
            hotspot_metric = next((m for m in metrics if m.name == "hotspot_score"), None)
            if hotspot_metric:
                hotspots.append({
                    "file": f.path,
                    "hotspot_score": hotspot_metric.value
                })
        hotspots.sort(key=lambda x: x["hotspot_score"], reverse=True)
        return hotspots

    def get_diagnostic_chain(self, file_path: str, include_archived: bool = False) -> list[dict]:
        if not isinstance(include_archived, bool):
            raise TypeError("include_archived must be a boolean")
        normalized_path = _validate_path(file_path)
        detail = self.get_file_detail(normalized_path, include_archived=include_archived)
        return detail.get("diagnostic_chain", [])

    def get_analysis_history(self, include_archived: bool = False) -> list[dict]:
        if not isinstance(include_archived, bool):
            raise TypeError("include_archived must be a boolean")
        runs = self.store.get_analysis_runs(include_archived=include_archived)
        return [
            {
                "id": run.id,
                "timestamp": run.timestamp,
                "duration": run.duration,
                "engine_version": run.engine_version,
                "rkm_version": run.rkm_version,
                "content_hash": run.content_hash,
                "previous_run_id": run.previous_run_id,
                "rule_pack_version": run.rule_pack_version,
                "semantic_hash": run.semantic_hash,
                "archived": run.archived
            }
            for run in runs
        ]

    def get_fact_run(self, fact_id: int):
        row = self.store.conn.execute(
            """SELECT r.* FROM rkm_analysis_runs r
               JOIN rkm_files f ON f.analysis_run_id = r.id
               JOIN rkm_facts fact ON fact.file_id = f.id
               WHERE fact.id = ?""",
            (fact_id,)
        ).fetchone()
        return self.store._parse_analysis_run(row)

    def get_metric_run(self, metric_id: int):
        row = self.store.conn.execute(
            """SELECT r.* FROM rkm_analysis_runs r
               JOIN rkm_files f ON f.analysis_run_id = r.id
               JOIN rkm_metrics m ON m.file_id = f.id
               WHERE m.id = ?""",
            (metric_id,)
        ).fetchone()
        return self.store._parse_analysis_run(row)

    def get_interpretation_run(self, interpretation_id: int):
        row = self.store.conn.execute(
            """SELECT r.* FROM rkm_analysis_runs r
               JOIN rkm_files f ON f.analysis_run_id = r.id
               JOIN rkm_facts fact ON fact.file_id = f.id
               JOIN rkm_interpretations inter ON inter.fact_id = fact.id
               WHERE inter.id = ?""",
            (interpretation_id,)
        ).fetchone()
        return self.store._parse_analysis_run(row)

    def compare_runs(self, run_id_a: int, run_id_b: int) -> RunComparison:
        run_a = self.store.get_analysis_run(run_id_a)
        run_b = self.store.get_analysis_run(run_id_b)
        if not run_a or not run_b:
            raise ValueError(f"Invalid run ID(s): {run_id_a}, {run_id_b}")

        files_a = self.store.get_file_records_for_run(run_id_a)
        files_b = self.store.get_file_records_for_run(run_id_b)

        map_a = {f.path: f for f in files_a}
        map_b = {f.path: f for f in files_b}

        added_files = sorted(list(set(map_b.keys()) - set(map_a.keys())))
        removed_files = sorted(list(set(map_a.keys()) - set(map_b.keys())))
        common_files = set(map_a.keys()) & set(map_b.keys())

        modified_files = []
        metric_delta = {}
        risk_delta = {}
        architecture_delta = {}
        dependency_delta = {}

        for path in common_files:
            file_a = map_a[path]
            file_b = map_b[path]

            # 1. Metrics delta
            metrics_a = {m.name: m.value for m in self.store.get_metrics(file_a.id)}
            metrics_b = {m.name: m.value for m in self.store.get_metrics(file_b.id)}
            file_metrics = {}
            for name in set(metrics_a.keys()) | set(metrics_b.keys()):
                val_a = metrics_a.get(name, 0.0)
                val_b = metrics_b.get(name, 0.0)
                if val_a != val_b:
                    file_metrics[name] = {"before": val_a, "after": val_b, "delta": val_b - val_a}
            if file_metrics:
                metric_delta[path] = file_metrics

            # 2. Risk delta
            facts_a = {f.metric: f.value for f in self.store.get_facts(file_a.id) if f.category == "risk"}
            facts_b = {f.metric: f.value for f in self.store.get_facts(file_b.id) if f.category == "risk"}
            file_risk = {}
            for name in set(facts_a.keys()) | set(facts_b.keys()):
                val_a = facts_a.get(name)
                val_b = facts_b.get(name)
                if val_a != val_b:
                    file_risk[name] = {"before": val_a, "after": val_b}
            if file_risk:
                risk_delta[path] = file_risk

            # 3. Dependency delta
            deps_a = sorted([d.target_path for d in self.store.get_dependencies(file_a.id)])
            deps_b = sorted([d.target_path for d in self.store.get_dependencies(file_b.id)])
            if deps_a != deps_b:
                dependency_delta[path] = {
                    "removed": sorted(list(set(deps_a) - set(deps_b))),
                    "added": sorted(list(set(deps_b) - set(deps_a)))
                }

            # 4. Architecture delta
            arch_a = {a.layer: a.role for a in self.store.get_architecture(file_a.id)}
            arch_b = {a.layer: a.role for a in self.store.get_architecture(file_b.id)}
            if arch_a != arch_b:
                architecture_delta[path] = {"before": arch_a, "after": arch_b}

            # If any delta occurred or file size changed, mark as modified
            if file_metrics or file_risk or deps_a != deps_b or arch_a != arch_b or file_a.size != file_b.size:
                modified_files.append(path)

        modified_files.sort()

        return RunComparison(
            added_files=added_files,
            removed_files=removed_files,
            modified_files=modified_files,
            metric_delta=metric_delta,
            risk_delta=risk_delta,
            architecture_delta=architecture_delta,
            dependency_delta=dependency_delta,
            future_reserved={}
        )

    def get_file_history(self, path: str, include_archived: bool = False) -> list[dict]:
        if not isinstance(include_archived, bool):
            raise TypeError("include_archived must be a boolean")
        normalized_path = _validate_path(path)
        runs = self.store.get_analysis_runs(include_archived=include_archived)
        history = []
        for run in runs:
            files = self.store.get_file_records_for_run(run.id)
            file_rec = next((f for f in files if f.path == normalized_path), None)
            if file_rec:
                metrics = {m.name: m.value for m in self.store.get_metrics(file_rec.id)}
                facts = {f.metric: f.value for f in self.store.get_facts(file_rec.id)}
                history.append({
                    "run_id": run.id,
                    "timestamp": run.timestamp,
                    "size": file_rec.size,
                    "role": file_rec.role,
                    "metrics": metrics,
                    "facts": facts
                })
        return history

    def close(self):
        self.store.close()

