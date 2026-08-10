"""
Ultron REST API — Canonical System Model & Agent Context Routes
Campaign 31 / v2.3 — System Model REST API & Agent Context Protocol
"""

import os
import json
import logging
from typing import Any, Dict

from ultron.interfaces.api.router import APIRouter
from ultron.core.language_adapter import PythonLanguageAdapter
from ultron.core.system_query import SystemQueryEngine
from ultron.core.system_model import SystemModelManager

logger = logging.getLogger(__name__)

# Shared in-memory system model manager cache
_GLOBAL_MODEL_MANAGER: Optional[SystemModelManager] = None


def get_or_build_system_model(handler: Any) -> SystemModelManager:
    """Helper to retrieve or build the canonical SystemModel for the active repository."""
    global _GLOBAL_MODEL_MANAGER
    if _GLOBAL_MODEL_MANAGER is not None:
        return _GLOBAL_MODEL_MANAGER

    repo_path = "."
    if hasattr(handler, "get_repo_root_path"):
        try:
            repo_path = handler.get_repo_root_path()
        except Exception:
            repo_path = "."

    adapter = PythonLanguageAdapter()
    graph = adapter.parse_repository(repo_path)
    manager = SystemModelManager()
    manager.graph = graph
    _GLOBAL_MODEL_MANAGER = manager
    return manager


def reset_system_model_cache() -> None:
    """Resets global in-memory model manager cache."""
    global _GLOBAL_MODEL_MANAGER
    _GLOBAL_MODEL_MANAGER = None


@APIRouter.register("/api/v1/system/graph", "GET")
def handle_v1_system_graph(handler: Any) -> None:
    """GET /api/v1/system/graph — Returns full canonical SystemGraph payload."""
    manager = get_or_build_system_model(handler)
    payload = {
        "success": True,
        "data": manager.serialize(),
        "error": None
    }
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


@APIRouter.register("/api/v1/system/node", "GET")
def handle_v1_system_node(handler: Any) -> None:
    """GET /api/v1/system/node?id=... — Returns metadata for a target SystemNode."""
    target_id = ""
    if hasattr(handler, "path") and "?" in handler.path:
        query_str = handler.path.split("?", 1)[1]
        for param in query_str.split("&"):
            if param.startswith("id="):
                target_id = param.split("=", 1)[1]
                break

    if not target_id:
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"success": False, "data": None, "error": "Query parameter 'id' is required"}).encode("utf-8"))
        return

    manager = get_or_build_system_model(handler)
    query_engine = SystemQueryEngine(manager.graph)
    node = query_engine.find_node(target_id)

    if not node:
        handler.send_response(404)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"success": False, "data": None, "error": f"Node '{target_id}' not found in SystemModel"}).encode("utf-8"))
        return

    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps({"success": True, "data": node.to_dict(), "error": None}, ensure_ascii=False).encode("utf-8"))


@APIRouter.register("/api/v1/agent/context", "POST")
def handle_v1_agent_context(handler: Any) -> None:
    """POST /api/v1/agent/context — Returns targeted agent context subgraph."""
    post_data = {}
    if hasattr(handler, "get_post_data"):
        try:
            post_data = handler.get_post_data() or {}
        except Exception as e:
            handler.send_response(400)
            handler.send_header("Content-Type", "application/json; charset=utf-8")
            handler.end_headers()
            handler.wfile.write(json.dumps({"success": False, "data": None, "error": f"Invalid JSON payload: {e}"}).encode("utf-8"))
            return

    target = post_data.get("target") or post_data.get("file_path") or post_data.get("node_id")
    if not target:
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"success": False, "data": None, "error": "Field 'target' or 'file_path' is required in POST body"}).encode("utf-8"))
        return

    depth = int(post_data.get("depth", 2))
    manager = get_or_build_system_model(handler)
    query_engine = SystemQueryEngine(manager.graph)
    ctx = query_engine.get_agent_context(target, depth=depth)

    if not ctx.get("found"):
        handler.send_response(404)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({"success": False, "data": ctx, "error": ctx.get("error")}).encode("utf-8"))
        return

    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps({"success": True, "data": ctx, "error": None}, ensure_ascii=False).encode("utf-8"))
