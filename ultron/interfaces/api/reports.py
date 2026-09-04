import os
from typing import Optional, Dict, List, Any
from ultron.core.rkm.store import RepositoryStore


class MetricsAPI:
    @staticmethod
    def get_metrics_summary(store: Optional[RepositoryStore], run_id: Optional[int]) -> list[dict]:
        if not store or getattr(store, "conn", None) is None or run_id is None:
            return []
        try:
            files = store.get_file_records_for_run(int(run_id))
        except Exception:
            return []
        if not files:
            return []
        results = []
        for f in files:
            if not f or getattr(f, "id", None) is None:
                continue
            try:
                metrics = store.get_metrics(f.id)
                results.append({
                    "file": getattr(f, "path", "") or "",
                    "metrics": {m.name: m.value for m in metrics if m and getattr(m, "name", None) is not None}
                })
            except Exception:
                continue
        return results

    @staticmethod
    def get_file_metrics(store: Optional[RepositoryStore], run_id: Optional[int], file_path: Optional[str]) -> dict:
        if not store or getattr(store, "conn", None) is None or run_id is None or not file_path or not isinstance(file_path, str):
            return {}
        try:
            norm_path = os.path.normpath(file_path).replace("\\", "/")
            row = store.conn.execute(
                "SELECT id FROM rkm_files WHERE analysis_run_id = ? AND path = ?",
                (int(run_id), norm_path)
            ).fetchone()
            if not row:
                return {}
            metrics = store.get_metrics(row["id"])
            return {m.name: m.value for m in metrics if m and getattr(m, "name", None) is not None}
        except Exception:
            return {}


class ViolationsAPI:
    @staticmethod
    def get_violations(store: Optional[RepositoryStore], run_id: Optional[int]) -> list[dict]:
        if not store or getattr(store, "conn", None) is None or run_id is None:
            return []
        try:
            vios = store.get_violations(int(run_id))
        except Exception:
            return []
        if not vios:
            return []
        results = []
        for vio, rule, evidence in vios:
            if not vio:
                continue
            file_path = None
            if getattr(vio, "file_id", None):
                try:
                    file_row = store.conn.execute(
                        "SELECT path FROM rkm_files WHERE id = ?",
                        (vio.file_id,)
                    ).fetchone()
                    if file_row:
                        file_path = file_row["path"]
                except Exception:
                    file_path = None

            evidence_list = []
            if evidence:
                for ev in evidence:
                    if ev:
                        evidence_list.append({
                            "evidence_type": getattr(ev, "evidence_type", None),
                            "evidence_id": getattr(ev, "evidence_id", None)
                        })

            results.append({
                "violation_id": getattr(vio, "id", None),
                "rule_id": getattr(rule, "id", None) if rule else None,
                "rule_name": getattr(rule, "name", None) if rule else None,
                "description": getattr(rule, "description", None) if rule else None,
                "details": getattr(vio, "details", None),
                "file_path": file_path,
                "evidence": evidence_list
            })
        return results


class ReportsAPI:
    @staticmethod
    def get_metrics_summary(store: Optional[RepositoryStore], run_id: Optional[int]) -> list[dict]:
        return MetricsAPI.get_metrics_summary(store, run_id)


