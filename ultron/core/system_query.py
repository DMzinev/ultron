"""
Ultron Core — Dedicated System Query Engine
Campaign 30 / v2.3 — Bounded Query Engine & Agent Context Extraction
"""

import os
from typing import Dict, List, Any, Optional, Set

from ultron.core.system_model import SystemGraph, SystemNode, SystemEdge, SystemNodeType, SystemEdgeType


class SystemQueryEngine:
    """
    Dedicated Query Engine over Canonical SystemGraph.
    INVARIANT 2: Contains ZERO scoring or risk rating logic. Pure query & topology retrieval.
    """

    def __init__(self, graph: SystemGraph):
        self.graph = graph

    def _normalize_id(self, target: str) -> str:
        """Normalizes query target string to POSIX forward-slashes."""
        norm = target.replace("\\", "/").strip().rstrip('/')
        if norm.startswith("module:") or norm.startswith("class:") or norm.startswith("function:") or norm.startswith("package:"):
            return norm
        return f"module:{norm}"

    def find_node(self, target: str) -> Optional[SystemNode]:
        """Level 1 Primitive: Direct node lookup."""
        norm_id = self._normalize_id(target)
        if norm_id in self.graph.nodes:
            return self.graph.nodes[norm_id]
        
        # Fallback search by file_path or matching suffix
        clean_target = target.replace("\\", "/").strip()
        for nid, node in self.graph.nodes.items():
            if node.file_path == clean_target or nid.endswith(clean_target):
                return node
        return None

    def find_dependencies(self, target: str, depth: int = 1) -> List[SystemNode]:
        """Level 2 Primitive: Find outgoing dependencies with visited set cycle prevention."""
        start_node = self.find_node(target)
        if not start_node or depth < 1:
            return []

        visited: Set[str] = {start_node.id}
        queue = [(start_node.id, 0)]
        results: List[SystemNode] = []

        while queue:
            curr_id, curr_depth = queue.pop(0)
            if curr_depth >= depth:
                continue

            for edge in self.graph.edges:
                if edge.source_id == curr_id and edge.target_id not in visited:
                    visited.add(edge.target_id)
                    target_node = self.graph.nodes.get(edge.target_id)
                    if target_node:
                        results.append(target_node)
                        queue.append((edge.target_id, curr_depth + 1))

        return results

    def find_dependents(self, target: str, depth: int = 1) -> List[SystemNode]:
        """Level 2 Primitive: Find incoming dependents with visited set cycle prevention."""
        start_node = self.find_node(target)
        if not start_node or depth < 1:
            return []

        visited: Set[str] = {start_node.id}
        queue = [(start_node.id, 0)]
        results: List[SystemNode] = []

        while queue:
            curr_id, curr_depth = queue.pop(0)
            if curr_depth >= depth:
                continue

            for edge in self.graph.edges:
                if edge.target_id == curr_id and edge.source_id not in visited:
                    visited.add(edge.source_id)
                    source_node = self.graph.nodes.get(edge.source_id)
                    if source_node:
                        results.append(source_node)
                        queue.append((edge.source_id, curr_depth + 1))

        return results

    def find_callers(self, target: str) -> List[SystemNode]:
        """Level 3 Primitive: Find nodes that call or import target."""
        return self.find_dependents(target, depth=1)

    def find_tests_for(self, target: str) -> List[SystemNode]:
        """Level 3 Primitive: Find test modules or test functions associated with target."""
        start_node = self.find_node(target)
        if not start_node:
            return []

        dependents = self.find_dependents(target, depth=2)
        tests = [node for node in dependents if node.type == SystemNodeType.TEST or "test" in node.file_path]
        return tests

    def get_downstream_dependents(self, target: str) -> List[str]:
        """Returns canonical string IDs of outgoing dependencies."""
        deps = self.find_dependencies(target, depth=1)
        return [node.id for node in deps]

    def get_upstream_callers(self, target: str) -> List[str]:
        """Returns canonical string IDs of incoming callers/dependents."""
        callers = self.find_callers(target)
        return [node.id for node in callers]

    def trace_blast_radius(self, target: str, max_depth: int = 2) -> Dict[str, Any]:
        """Traces blast radius for an entity up to max_depth returning affected node IDs and trace path edges."""
        start_node = self.find_node(target)
        if not start_node:
            return {"affected_nodes": [], "trace_path": []}

        visited: Set[str] = {start_node.id}
        queue = [(start_node.id, 0)]
        trace_path = []

        while queue:
            curr_id, curr_depth = queue.pop(0)
            if curr_depth >= max_depth:
                continue

            for edge in self.graph.edges:
                if edge.target_id == curr_id:
                    trace_path.append({
                        "source": edge.source_id,
                        "target": edge.target_id,
                        "relation": edge.type.value if hasattr(edge.type, "value") else str(edge.type)
                    })
                    if edge.source_id not in visited:
                        visited.add(edge.source_id)
                        queue.append((edge.source_id, curr_depth + 1))

        return {
            "affected_nodes": sorted(list(visited)),
            "trace_path": trace_path
        }

    def get_agent_context(self, target_path: str, depth: int = 2) -> Dict[str, Any]:
        """
        Level 4 Primitive: Targeted Agent Context Extraction.
        INVARIANT 6: Agent context is a projection of the canonical model, not a second representation.
        """
        target_node = self.find_node(target_path)
        if not target_node:
            return {
                "target": target_path,
                "found": False,
                "error": f"Target entity '{target_path}' not found in SystemModel",
                "nodes": [],
                "edges": [],
                "evidence": []
            }

        deps = self.find_dependencies(target_node.id, depth=depth)
        dependents = self.find_dependents(target_node.id, depth=depth)
        tests = self.find_tests_for(target_node.id)

        all_nodes = {target_node.id: target_node}
        for n in deps + dependents + tests:
            all_nodes[n.id] = n

        # Filter relevant edges between extracted node set
        extracted_node_ids = set(all_nodes.keys())
        relevant_edges = [
            edge for edge in self.graph.edges
            if edge.source_id in extracted_node_ids and edge.target_id in extracted_node_ids
        ]

        # Gather evidence objects attached to extracted nodes
        relevant_evidence = []
        for n in all_nodes.values():
            for eid in n.evidence_ids:
                if eid in self.graph.evidence:
                    relevant_evidence.append(self.graph.evidence[eid].to_dict())

        return {
            "target": target_node.file_path,
            "found": True,
            "target_node": target_node.to_dict(),
            "nodes": [node.to_dict() for node in all_nodes.values()],
            "edges": [edge.to_dict() for edge in relevant_edges],
            "evidence": relevant_evidence,
            "summary": {
                "total_nodes": len(all_nodes),
                "dependencies_count": len(deps),
                "dependents_count": len(dependents),
                "tests_count": len(tests)
            }
        }
