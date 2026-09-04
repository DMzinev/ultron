"""
Ultron REST API Routes Package
"""
from .analysis_routes import AnalysisRoutesMixin, handle_v1_analyze, handle_v1_summary
from .graph_routes import GraphRoutesMixin
from .agent_routes import AgentRoutesMixin
from .audit_routes import AuditRoutesMixin
from .system_routes import (
    SystemRoutesMixin,
    handle_v1_system_graph,
    handle_v1_system_node,
    handle_v1_agent_context,
)
from .health_routes import handle_v1_health
from .export_routes import handle_v1_export_brief
from .ai_routes import handle_v1_ai_critique

__all__ = [
    "AnalysisRoutesMixin",
    "GraphRoutesMixin",
    "AgentRoutesMixin",
    "AuditRoutesMixin",
    "SystemRoutesMixin",
    "handle_v1_analyze",
    "handle_v1_summary",
    "handle_v1_health",
    "handle_v1_export_brief",
    "handle_v1_ai_critique",
    "handle_v1_system_graph",
    "handle_v1_system_node",
    "handle_v1_agent_context",
]
