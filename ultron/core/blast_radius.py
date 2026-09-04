"""
ultron.core.blast_radius
Deterministic graph traversal, blast-radius impact analysis, and dependency path tracing.
"""

from collections import deque
from typing import Dict, List, Any, Optional, Set, Tuple


def norm_id(identifier: Any) -> str:
    """Normalizes graph node and edge identifiers to POSIX forward slashes."""
    return str(identifier or "").replace("\\", "/").strip()


class BlastRadiusTracer:
    """
    High-performance, cycle-safe graph reachability and blast-radius impact engine.
    Computes upstream callers, downstream dependents, and shortest path chains.
    """

    @staticmethod
    def _build_adjacency_maps(
        edges: List[Any]
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]:
        """
        Constructs forward (outbound) and backward (inbound) adjacency lookup maps.
        Edge model: (source -> target) denotes 'source depends on / calls / imports target'.
        """
        outbound: Dict[str, List[Dict[str, Any]]] = {}
        inbound: Dict[str, List[Dict[str, Any]]] = {}

        for edge in edges:
            if isinstance(edge, dict):
                src = norm_id(edge.get("source") or edge.get("source_id"))
                tgt = norm_id(edge.get("target") or edge.get("target_id"))
                edge_type = edge.get("type", "imports")
            else:
                src = norm_id(getattr(edge, "source", None) or getattr(edge, "source_id", None))
                tgt = norm_id(getattr(edge, "target", None) or getattr(edge, "target_id", None))
                edge_type = getattr(edge, "type", "imports")

            if not src or not tgt:
                continue

            if src not in outbound:
                outbound[src] = []
            outbound[src].append({"target": tgt, "type": edge_type})

            if tgt not in inbound:
                inbound[tgt] = []
            inbound[tgt].append({"source": src, "type": edge_type})

        return outbound, inbound

    @classmethod
    def find_upstream_dependencies(
        cls,
        nodes: List[Any],
        edges: List[Any],
        target_id: str,
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Finds all modules that call or import target_id (inbound callers/parents).
        """
        normalized_target = norm_id(target_id)
        _, inbound = cls._build_adjacency_maps(edges)

        direct_parents: List[str] = []
        transitive_parents: List[str] = []
        visited: Set[str] = {normalized_target}
        cycle_detected = False
        queue: deque = deque([(normalized_target, 0, {normalized_target})])

        while queue:
            curr, depth, path_ancestors = queue.popleft()
            if depth >= max_depth:
                continue

            for edge in inbound.get(curr, []):
                src = edge["source"]
                if src in path_ancestors:
                    cycle_detected = True
                    continue

                if src not in visited:
                    visited.add(src)
                    if depth == 0:
                        direct_parents.append(src)
                    else:
                        transitive_parents.append(src)

                    queue.append((src, depth + 1, path_ancestors | {src}))

        direct_parents.sort()
        transitive_parents.sort()

        return {
            "target_id": normalized_target,
            "direct_parents": direct_parents,
            "transitive_parents": transitive_parents,
            "total_upstream_count": len(direct_parents) + len(transitive_parents),
            "cycle_detected": cycle_detected,
            "max_depth_evaluated": max_depth
        }

    @classmethod
    def find_downstream_dependents(
        cls,
        nodes: List[Any],
        edges: List[Any],
        target_id: str,
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Finds all modules that target_id depends on, imports, or calls (outbound dependents).
        """
        normalized_target = norm_id(target_id)
        outbound, _ = cls._build_adjacency_maps(edges)

        direct_dependents: List[str] = []
        transitive_dependents: List[str] = []
        visited: Set[str] = {normalized_target}
        cycle_detected = False
        queue: deque = deque([(normalized_target, 0, {normalized_target})])

        while queue:
            curr, depth, path_ancestors = queue.popleft()
            if depth >= max_depth:
                continue

            for edge in outbound.get(curr, []):
                tgt = edge["target"]
                if tgt in path_ancestors:
                    cycle_detected = True
                    continue

                if tgt not in visited:
                    visited.add(tgt)
                    if depth == 0:
                        direct_dependents.append(tgt)
                    else:
                        transitive_dependents.append(tgt)

                    queue.append((tgt, depth + 1, path_ancestors | {tgt}))

        direct_dependents.sort()
        transitive_dependents.sort()

        return {
            "target_id": normalized_target,
            "direct_dependents": direct_dependents,
            "transitive_dependents": transitive_dependents,
            "total_downstream_count": len(direct_dependents) + len(transitive_dependents),
            "cycle_detected": cycle_detected,
            "max_depth_evaluated": max_depth
        }

    @classmethod
    def find_shortest_path(
        cls,
        nodes: List[Any],
        edges: List[Any],
        source_id: str,
        target_id: str
    ) -> List[str]:
        """
        Finds the shortest directed chain from source_id to target_id via BFS.
        """
        src = norm_id(source_id)
        tgt = norm_id(target_id)

        if not src or not tgt:
            return []
        if src == tgt:
            return [src]

        outbound, _ = cls._build_adjacency_maps(edges)
        visited: Set[str] = {src}
        queue: deque = deque([[src]])

        while queue:
            path = queue.popleft()
            current_node = path[-1]

            for edge in outbound.get(current_node, []):
                neighbor = edge["target"]
                if neighbor == tgt:
                    return path + [tgt]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])

        return []

    @classmethod
    def compute_blast_radius_score(
        cls,
        target_id: str,
        nodes: List[Any],
        edges: List[Any],
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Computes a deterministic blast-radius score based on transitive reachability
        and node complexity factors.
        """
        upstream = cls.find_upstream_dependencies(nodes, edges, target_id, max_depth)
        downstream = cls.find_downstream_dependents(nodes, edges, target_id, max_depth)

        upstream_set = set(upstream.get("direct_parents", [])) | set(upstream.get("transitive_parents", []))
        downstream_set = set(downstream.get("direct_dependents", [])) | set(downstream.get("transitive_dependents", []))
        all_impacted_ids = upstream_set | downstream_set
        total_impacted = len(all_impacted_ids)

        # Calculate average complexity if node metadata exists
        node_lookup = {}
        for n in nodes:
            nid = norm_id(n.get("id") if isinstance(n, dict) else getattr(n, "id", None))
            c = n.get("complexity", 1.0) if isinstance(n, dict) else getattr(n, "complexity", 1.0)
            node_lookup[nid] = float(c or 1.0)

        target_complexity = node_lookup.get(norm_id(target_id), 1.0)
        blast_score = round((downstream["total_downstream_count"] * 1.5 + upstream["total_upstream_count"] * 1.0) * (target_complexity ** 0.5), 2)

        return {
            "target_id": norm_id(target_id),
            "blast_score": blast_score,
            "total_impacted_modules": total_impacted,
            "upstream": upstream,
            "downstream": downstream
        }
