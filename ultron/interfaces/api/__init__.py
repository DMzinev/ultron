"""Ultron Public API Package."""
from .repository import RepositoryAPI
from .history import HistoryAPI
from .reports import ReportsAPI, MetricsAPI, ViolationsAPI

class AnalysisAPI:
    """Public Analysis API accessor."""
    pass

class DashboardAPI:
    """Public Dashboard API accessor."""
    pass

class RuleAPI:
    """Public Rule API accessor."""
    pass

__all__ = [
    "RepositoryAPI",
    "AnalysisAPI",
    "HistoryAPI",
    "DashboardAPI",
    "ReportsAPI",
    "MetricsAPI",
    "ViolationsAPI",
    "RuleAPI"
]

