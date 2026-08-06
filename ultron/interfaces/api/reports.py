from ultron.core.rkm.store import RepositoryStore

class MetricsAPI:
    @staticmethod
    def get_metrics_summary(store: RepositoryStore, run_id: int) -> list[dict]:
        files = store.get_file_records_for_run(run_id)
        results = []
        for f in files:
            metrics = store.get_metrics(f.id)
            results.append({
                "file": f.path,
                "metrics": {m.name: m.value for m in metrics}
            })
        return results

    @staticmethod
    def get_file_metrics(store: RepositoryStore, run_id: int, file_path: str) -> dict:
        import os
        norm_path = os.path.normpath(file_path).replace("\\", "/")
        row = store.conn.execute(
            "SELECT id FROM rkm_files WHERE analysis_run_id = ? AND path = ?",
            (run_id, norm_path)
        ).fetchone()
        if not row:
            return {}
        metrics = store.get_metrics(row["id"])
        return {m.name: m.value for m in metrics}


class ViolationsAPI:
    @staticmethod
    def get_violations(store: RepositoryStore, run_id: int) -> list[dict]:
        vios = store.get_violations(run_id)
        results = []
        for vio, rule, evidence in vios:
            results.append({
                "violation_id": vio.id,
                "rule_id": rule.id,
                "rule_name": rule.name,
                "description": rule.description,
                "details": vio.details,
                "file_path": store.conn.execute("SELECT path FROM rkm_files WHERE id = ?", (vio.file_id,)).fetchone()["path"] if vio.file_id else None,
                "evidence": [
                    {"evidence_type": ev.evidence_type, "evidence_id": ev.evidence_id}
                    for ev in evidence
                ]
            })
        return results


class ReportsAPI:
    @staticmethod
    def get_metrics_summary(store: RepositoryStore, run_id: int) -> list[dict]:
        return MetricsAPI.get_metrics_summary(store, run_id)

