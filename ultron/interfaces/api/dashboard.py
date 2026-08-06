from ultron.core.rkm.store import RepositoryStore

class DashboardAPI:
    @staticmethod
    def get_dashboard_summary(store: RepositoryStore, run_id: int) -> dict:
        files = store.get_file_records_for_run(run_id)
        violations = store.get_violations(run_id)
        return {
            "run_id": run_id,
            "total_files": len(files),
            "total_violations": len(violations)
        }
