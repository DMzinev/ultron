"""
Ultron REST API — Engineering Intelligence Query Protocol Endpoint
Campaign 33 / v2.6 — Agent Query Protocol Handler
"""

import json
from typing import Any, Dict, List

from ultron.interfaces.api.router import APIRouter
from ultron.core.system_query import SystemQueryEngine
from ultron.interfaces.api.routes.system_routes import get_or_build_system_model


@APIRouter.register("/api/v1/agent/context/query", "POST")
def handle_v1_agent_query(handler: Any) -> None:
    """
    POST /api/v1/agent/context/query — Engineering Intelligence Query Protocol.
    Supports 7 explicit query types:
      - IMPACT_ANALYSIS
      - DEPENDENCIES
      - DEPENDENTS
      - CALLERS
      - TEST_COVERAGE
      - RISK_EXPLANATION
      - CHANGE_CONTEXT
    """
    post_data = {}
    if hasattr(handler, "get_post_data"):
        try:
            post_data = handler.get_post_data()
            if not isinstance(post_data, dict):
                handler.send_response(400)
                handler.send_header("Content-Type", "application/json; charset=utf-8")
                handler.end_headers()
                handler.wfile.write(json.dumps({"success": False, "data": None, "error": "Invalid JSON body format. Expected JSON object."}).encode("utf-8"))
                return
        except Exception as e:
            handler.send_response(400)
            handler.send_header("Content-Type", "application/json; charset=utf-8")
            handler.end_headers()
            handler.wfile.write(json.dumps({"success": False, "data": None, "error": f"Invalid JSON payload: {e}"}).encode("utf-8"))
            return

    query_type = post_data.get("query_type")
    target_entity = post_data.get("target_entity") or post_data.get("entity_id") or post_data.get("target") or post_data.get("file_path")
    try:
        depth = int(post_data.get("depth", 2))
    except (ValueError, TypeError):
        depth = 2

    supported_types = {
        "IMPACT_ANALYSIS", "DEPENDENCIES", "DEPENDENTS",
        "CALLERS", "TEST_COVERAGE", "RISK_EXPLANATION", "CHANGE_CONTEXT"
    }

    if not query_type or query_type not in supported_types:
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({
            "success": False,
            "data": None,
            "error": f"Invalid or missing 'query_type'. Supported types: {sorted(list(supported_types))}"
        }).encode("utf-8"))
        return

    if not target_entity or not isinstance(target_entity, str) or not target_entity.strip() or '\x00' in target_entity:
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({
            "success": False,
            "data": None,
            "error": "Field 'target_entity' or 'entity_id' or 'target' is required and must be a non-empty string"
        }).encode("utf-8"))
        return

    target_entity = target_entity.strip()

    manager = get_or_build_system_model(handler)
    query_engine = SystemQueryEngine(manager.graph)
    target_node = query_engine.find_node(target_entity)

    if not target_node:
        handler.send_response(404)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(json.dumps({
            "success": False,
            "data": None,
            "error": f"Target entity '{target_entity}' not found in SystemModel"
        }).encode("utf-8"))
        return

    # Dispatch query type over SystemQueryEngine and SystemGraph
    nodes: List[Dict[str, Any]] = [target_node.to_dict()]
    edges: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []

    if query_type in ("IMPACT_ANALYSIS", "CHANGE_CONTEXT"):
        ctx = query_engine.get_agent_context(target_node.id, depth=depth)
        nodes = ctx.get("nodes", [target_node.to_dict()])
        edges = ctx.get("edges", [])
        evidence = ctx.get("evidence", [])

    elif query_type == "DEPENDENCIES":
        deps = query_engine.find_dependencies(target_node.id, depth=depth)
        nodes.extend([d.to_dict() for d in deps])
        node_ids = {n["id"] for n in nodes}
        edges = [e.to_dict() for e in manager.graph.edges if e.source_id in node_ids and e.target_id in node_ids]

    elif query_type == "DEPENDENTS":
        deps = query_engine.find_dependents(target_node.id, depth=depth)
        nodes.extend([d.to_dict() for d in deps])
        node_ids = {n["id"] for n in nodes}
        edges = [e.to_dict() for e in manager.graph.edges if e.source_id in node_ids and e.target_id in node_ids]

    elif query_type == "CALLERS":
        callers = query_engine.find_callers(target_node.id)
        nodes.extend([c.to_dict() for c in callers])
        node_ids = {n["id"] for n in nodes}
        edges = [e.to_dict() for e in manager.graph.edges if e.source_id in node_ids and e.target_id in node_ids]

    elif query_type == "TEST_COVERAGE":
        tests = query_engine.find_tests_for(target_node.id)
        nodes.extend([t.to_dict() for t in tests])
        node_ids = {n["id"] for n in nodes}
        edges = [e.to_dict() for e in manager.graph.edges if e.source_id in node_ids and e.target_id in node_ids]

    elif query_type == "RISK_EXPLANATION":
        ctx = query_engine.get_agent_context(target_node.id, depth=1)
        nodes = ctx.get("nodes", [target_node.to_dict()])
        edges = ctx.get("edges", [])
        evidence = ctx.get("evidence", [])

    # Gather evidence for returned nodes if not already populated
    if not evidence:
        node_ids = {n["id"] for n in nodes if "id" in n}
        for nid in node_ids:
            node_obj = manager.graph.nodes.get(nid)
            if node_obj:
                for eid in node_obj.evidence_ids:
                    if eid in manager.graph.evidence:
                        evidence.append(manager.graph.evidence[eid].to_dict())

    # Canonical Deduplication & Referential Integrity Filtering
    unique_nodes = {n["id"]: n for n in nodes if isinstance(n, dict) and "id" in n}
    canonical_nodes = sorted(unique_nodes.values(), key=lambda x: str(x.get("id", "")))

    valid_node_ids = set(unique_nodes.keys())
    unique_edges = {}
    for e in edges:
        if isinstance(e, dict):
            src = str(e.get("source_id", ""))
            tgt = str(e.get("target_id", ""))
            etype = str(e.get("type", ""))
            if src in valid_node_ids and tgt in valid_node_ids:
                unique_edges[(src, tgt, etype)] = e
    canonical_edges = sorted(unique_edges.values(), key=lambda x: (str(x.get("source_id", "")), str(x.get("target_id", "")), str(x.get("type", ""))))

    unique_evidence = {ev["id"]: ev for ev in evidence if isinstance(ev, dict) and "id" in ev}
    canonical_evidence = sorted(unique_evidence.values(), key=lambda x: str(x.get("id", "")))

    model_hash = manager.compute_hash()
    snapshot_id = manager.graph.metadata.get("snapshot_id", f"snap_{model_hash[:16]}")

    response_data = {
        "query_type": query_type,
        "target_entity": target_entity,
        "entity_id": target_entity,
        "model_hash": model_hash,
        "snapshot_id": snapshot_id,
        "nodes": canonical_nodes,
        "edges": canonical_edges,
        "evidence": canonical_evidence,
        "telemetry": {
            "node_count": len(canonical_nodes),
            "edge_count": len(canonical_edges),
            "evidence_count": len(canonical_evidence),
            "query_depth": depth
        }
    }

    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps({
        "success": True,
        "data": response_data,
        "error": None
    }, ensure_ascii=False).encode("utf-8"))

