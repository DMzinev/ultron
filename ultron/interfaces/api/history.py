from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.evolution.timeline import DiffContext, HistoryContext

class HistoryAPI:
    @staticmethod
    def get_run_history(store: RepositoryStore, repo_id: int) -> list[dict]:
        context = HistoryContext(store, repo_id)
        return context.get_runs_timeline()

    @staticmethod
    def compare_runs(store: RepositoryStore, run_id_a: int, run_id_b: int) -> dict:
        context = DiffContext(store, run_id_a, run_id_b)
        return context.get_diff_summary()
