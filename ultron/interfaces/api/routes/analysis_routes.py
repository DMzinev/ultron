"""
Ultron REST API — Analysis Route Handler
"""

import sys
import os
from typing import Any

from ultron.interfaces.api.router import APIRouter

@APIRouter.register("/api/v1/analyze", method="POST")
def handle_v1_analyze(handler: Any) -> None:
    """POST /api/v1/analyze handler."""
    handler.handle_v1_analyze()

@APIRouter.register("/api/analyze", method=["GET", "POST"])
def handle_analyze(handler: Any) -> None:
    """GET/POST /api/analyze synchronous handler."""
    handler.handle_analyze()

@APIRouter.register("/api/v1/summary", method="GET")
def handle_v1_summary(handler: Any) -> None:
    """GET /api/v1/summary handler."""
    handler.handle_v1_summary()

@APIRouter.register("/api/v1/file-tree", method=["GET", "POST"], aliases=["/api/file-tree"])
def route_file_tree(handler: Any) -> None:
    """GET/POST /api/v1/file-tree handler."""
    handler.handle_file_tree()

@APIRouter.register("/api/v1/dependency-graph", method=["GET", "POST"], aliases=["/api/dependency-graph"])
def route_dependency_graph(handler: Any) -> None:
    """GET/POST /api/v1/dependency-graph handler."""
    handler.handle_dependency_graph()

@APIRouter.register("/api/v1/audit", method=["GET", "POST"], aliases=["/api/audit"])
def route_audit(handler: Any) -> None:
    """GET/POST /api/v1/audit handler."""
    handler.handle_audit()

@APIRouter.register("/api/v1/browse-folder", method="POST", aliases=["/api/browse-folder"])
def route_browse_folder(handler: Any) -> None:
    """POST /api/v1/browse-folder handler."""
    handler.handle_browse_folder()

@APIRouter.register("/api/v1/generate", method=["GET", "POST"], aliases=["/api/generate", "/api/v1/prompt"])
def route_generate(handler: Any) -> None:
    """GET/POST /api/v1/generate handler."""
    handler.handle_generate()

@APIRouter.register("/api/v1/run-tests", method=["GET", "POST"], aliases=["/api/run-tests", "/api/v1/tests"])
def route_run_tests(handler: Any) -> None:
    """GET/POST /api/v1/run-tests handler."""
    handler.handle_run_tests()

@APIRouter.register("/api/v1/test-status", method=["GET", "POST"], aliases=["/api/test-status"])
def route_test_status(handler: Any) -> None:
    """GET/POST /api/v1/test-status handler."""
    handler.handle_test_status()

@APIRouter.register("/api/v1/test-cancel", method="POST", aliases=["/api/test-cancel"])
def route_test_cancel(handler: Any) -> None:
    """POST /api/v1/test-cancel handler."""
    handler.handle_test_cancel()

@APIRouter.register("/api/v1/work/state", method=["GET", "POST"], aliases=["/api/work/state"])
def route_work_state(handler: Any) -> None:
    """GET/POST /api/v1/work/state handler."""
    handler.handle_work_state()

@APIRouter.register("/api/v1/work/advance", method="POST", aliases=["/api/work/advance"])
def route_work_advance(handler: Any) -> None:
    """POST /api/v1/work/advance handler."""
    handler.handle_work_advance()

@APIRouter.register("/api/v1/work/queue", method=["GET", "POST"], aliases=["/api/work/queue"])
def route_work_queue(handler: Any) -> None:
    """GET/POST /api/v1/work/queue handler."""
    handler.handle_work_queue()

@APIRouter.register("/api/v1/get-file", method=["GET", "POST"], aliases=["/api/get-file", "/api/v1/file"])
def route_get_file(handler: Any) -> None:
    """GET/POST /api/v1/get-file handler."""
    handler.handle_get_file()

@APIRouter.register("/api/v1/save-file", method="POST", aliases=["/api/save-file"])
def route_save_file(handler: Any) -> None:
    """POST /api/v1/save-file handler."""
    handler.handle_save_file()

@APIRouter.register("/api/v1/calibrate", method=["GET", "POST"], aliases=["/api/calibrate"])
def route_calibrate(handler: Any) -> None:
    """GET/POST /api/v1/calibrate handler."""
    handler.handle_calibrate()

@APIRouter.register("/api/v1/diff-risk", method="POST", aliases=["/api/diff-risk"])
def route_diff_risk(handler: Any) -> None:
    """POST /api/v1/diff-risk handler."""
    handler.handle_diff_risk()

@APIRouter.register("/api/v1/predict-impact", method="POST", aliases=["/api/predict-impact"])
def route_predict_impact(handler: Any) -> None:
    """POST /api/v1/predict-impact handler."""
    handler.handle_predict_impact()

@APIRouter.register("/api/v1/playground", method=["GET", "POST"], aliases=["/api/playground"])
def route_playground(handler: Any) -> None:
    """GET/POST /api/v1/playground handler."""
    handler.handle_playground()

@APIRouter.register("/api/v1/objective", method=["GET", "POST"])
def route_objective(handler: Any) -> None:
    """GET/POST /api/v1/objective handler."""
    if handler.command == "GET":
        handler.handle_v1_get_objective()
    else:
        handler.handle_v1_set_objective()

@APIRouter.register("/api/v1/objective/task/complete", method="POST")
def route_objective_task_complete(handler: Any) -> None:
    """POST /api/v1/objective/task/complete handler."""
    handler.handle_v1_complete_task()

@APIRouter.register("/api/v1/objective/task/add", method="POST")
def route_objective_task_add(handler: Any) -> None:
    """POST /api/v1/objective/task/add handler."""
    handler.handle_v1_add_task()

@APIRouter.register("/api/v1/agent/context", method=["GET", "POST"])
def route_agent_context_builder(handler: Any) -> None:
    """GET/POST /api/v1/agent/context handler."""
    handler.handle_v1_agent_context_builder()

@APIRouter.register("/api/v1/safety/evaluate", method=["GET", "POST"])
def route_safety_evaluate(handler: Any) -> None:
    """GET/POST /api/v1/safety/evaluate handler."""
    handler.handle_v1_safety_evaluate()

@APIRouter.register("/api/v1/session/current", method=["GET", "POST"], aliases=["/api/v1/session"])
def route_session_current(handler: Any) -> None:
    """GET/POST /api/v1/session/current handler."""
    handler.handle_v1_session_current()

@APIRouter.register("/api/v1/session/diff", method=["GET", "POST"])
def route_session_diff(handler: Any) -> None:
    """GET/POST /api/v1/session/diff handler."""
    handler.handle_v1_session_diff()

@APIRouter.register("/api/v1/workspace/watcher/scan", method="POST")
def route_workspace_watcher_scan(handler: Any) -> None:
    """POST /api/v1/workspace/watcher/scan handler."""
    handler.handle_v1_workspace_watcher_scan()

@APIRouter.register("/api/v1/mission/validate", method=["GET", "POST"])
def route_mission_validate(handler: Any) -> None:
    """GET/POST /api/v1/mission/validate handler."""
    handler.handle_v1_validate_mission()

@APIRouter.register("/api/v1/checkpoint", method=["GET", "POST"], aliases=["/api/v1/session/checkpoint"])
def route_checkpoint(handler: Any) -> None:
    """GET/POST /api/v1/checkpoint handler."""
    if handler.command == "GET":
        handler.handle_v1_get_checkpoints()
    else:
        handler.handle_v1_create_checkpoint()





