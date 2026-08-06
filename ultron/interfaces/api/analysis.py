import os
from typing import Optional
from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.schema import AnalysisRun

class AnalysisAPI:
    @staticmethod
    def get_analysis_run(store: RepositoryStore, run_id: int) -> Optional[AnalysisRun]:
        return store.get_analysis_run(run_id)

    @staticmethod
    def get_latest_run(store: RepositoryStore, repo_id: int) -> Optional[AnalysisRun]:
        row = store.conn.execute(
            "SELECT * FROM rkm_analysis_runs WHERE repository_id = ? AND archived = 0 ORDER BY id DESC LIMIT 1",
            (repo_id,)
        ).fetchone()
        if not row:
            return None
        return store._parse_analysis_run(row)
