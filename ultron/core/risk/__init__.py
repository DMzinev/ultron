"""
risk/__init__.py — Backward-compatibility shim.

Re-exports the full public API of the former risk.py monolith so that all
existing callers (`import risk; risk.evaluate_risks(...)`) work without
any modification.

Public API surface:
    evaluate_risks      — main risk scoring entry point (scoring.py)
    evaluate_diff_risk  — diff-level delta analysis (diff.py)
    load_mkr_stats      — Synapse mutation ledger reader (historical.py)
    load_human_feedback — human feedback reader (historical.py)

Private helpers (get_file_complexity, get_code_complexity, extract_ast_blocks)
are intentionally not re-exported here. Callers that need them should import
from risk.metrics directly.
"""
from .scoring   import evaluate_risks
from .diff      import evaluate_diff_risk
from .historical import load_mkr_stats, load_human_feedback

__all__ = [
    "evaluate_risks",
    "evaluate_diff_risk",
    "load_mkr_stats",
    "load_human_feedback",
]
