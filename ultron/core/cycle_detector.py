"""
ultron.core.cycle_detector
Deterministic circular import and cyclic dependency cycle detection engine.
"""

import time
from typing import Dict, List, Set, Any, Optional, Tuple


def norm_id(node_id: Any) -> str:
    """Normalizes node IDs and file paths to POSIX forward slashes."""
    return str(node_id or "").replace("\\", "/").strip()


class CycleDetector:
    """
    Deterministic graph cycle detector for finding circular dependencies and circular imports.
    Finds simple cycles, canonicalizes paths, computes severity, and suggests break edges.
    """

    @classmethod
    def _build_adjacency_map(cls, edges: List[Any]) -> Dict[str, List[str]]:
        """Constructs a deterministic sorted adjacency list from edge records."""
        adj: Dict[str, Set[str]] = {}
        if not edges:
            return {}

        for edge in edges:
            if isinstance(edge, dict):
                src = edge.get("source") or edge.get("source_id")
                tgt = edge.get("target") or edge.get("target_id")
            else:
                src = getattr(edge, "source", getattr(edge, "source_id", None))
                tgt = getattr(edge, "target", getattr(edge, "target_id", None))

            src_norm = norm_id(src)
            tgt_norm = norm_id(tgt)

            if src_norm and tgt_norm:
                if src_norm not in adj:
                    adj[src_norm] = set()
                adj[src_norm].add(tgt_norm)
                if tgt_norm not in adj:
                    adj[tgt_norm] = set()

        return {k: sorted(list(v)) for k, v in sorted(adj.items())}

    @classmethod
    def _canonicalize_cycle(cls, cycle: List[str]) -> Tuple[str, ...]:
        """
        Rotates a cycle so it starts with the lexicographically smallest node.
        Example: ['B', 'C', 'A'] -> ('A', 'B', 'C')
        """
        if not cycle:
            return ()
        min_idx = min(range(len(cycle)), key=lambda i: cycle[i])
        return tuple(cycle[min_idx:] + cycle[:min_idx])

    @classmethod
    def find_all_cycles(
        cls,
        nodes: Optional[List[Any]] = None,
        edges: Optional[List[Any]] = None,
        node_lookup: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Finds all elementary cycles in the dependency graph deterministically.
        Returns a sorted list of cycle descriptor dictionaries.
        """
        if not edges:
            return []

        adj = cls._build_adjacency_map(edges)
        all_nodes = sorted(list(adj.keys()))

        # 1. Tarjan's Strongly Connected Components (SCC) in O(V + E) to prune acyclic subgraphs
        index = 0
        indices = {}
        lowlink = {}
        on_stack = set()
        stack = []
        sccs = []

        def strongconnect(v):
            nonlocal index
            indices[v] = index
            lowlink[v] = index
            index += 1
            stack.append(v)
            on_stack.add(v)

            for w in adj.get(v, []):
                if w not in indices:
                    strongconnect(w)
                    lowlink[v] = min(lowlink[v], lowlink[w])
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], indices[w])

            if lowlink[v] == indices[v]:
                scc = set()
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.add(w)
                    if w == v:
                        break
                # Only keep non-trivial components (size > 1 or self-loop)
                if len(scc) > 1 or v in adj.get(v, []):
                    sccs.append(scc)

        for node in all_nodes:
            if node not in indices:
                strongconnect(node)

        discovered_cycles: Set[Tuple[str, ...]] = set()
        start_time = time.time()
        MAX_CYCLES = 500
        MAX_DEPTH = 30
        TIMEOUT_SEC = 1.0

        for scc in sccs:
            if len(discovered_cycles) >= MAX_CYCLES or (time.time() - start_time) > TIMEOUT_SEC:
                break
            scc_nodes = sorted(list(scc))
            for start_node in scc_nodes:
                if len(discovered_cycles) >= MAX_CYCLES or (time.time() - start_time) > TIMEOUT_SEC:
                    break

                def dfs(current: str, start: str, path: List[str], visited_in_path: Set[str]):
                    if len(path) > MAX_DEPTH or len(discovered_cycles) >= MAX_CYCLES or (time.time() - start_time) > TIMEOUT_SEC:
                        return
                    for neighbor in adj.get(current, []):
                        if neighbor not in scc:
                            continue
                        if neighbor == start:
                            # Completed a cycle
                            canonical = cls._canonicalize_cycle(path)
                            if canonical:
                                discovered_cycles.add(canonical)
                        elif neighbor not in visited_in_path:
                            # Pruning: Only explore nodes lexicographically >= start
                            if neighbor >= start:
                                visited_in_path.add(neighbor)
                                path.append(neighbor)
                                dfs(neighbor, start, path, visited_in_path)
                                path.pop()
                                visited_in_path.remove(neighbor)

                dfs(start_node, start_node, [start_node], {start_node})

        # Process detected cycles
        result = []
        for canonical_tuple in sorted(list(discovered_cycles)):
            cycle_nodes = list(canonical_tuple)
            cycle_path = cycle_nodes + [cycle_nodes[0]]
            severity = cls.compute_cycle_severity(cycle_nodes, node_lookup)
            break_edge = cls.suggest_break_cycle_edge(cycle_path, edges, node_lookup)

            result.append({
                "cycle_id": "->".join(cycle_path),
                "nodes": cycle_nodes,
                "cycle_path": cycle_path,
                "length": len(cycle_nodes),
                "severity_score": severity,
                "recommended_break_edge": break_edge,
                "display_label": " ➔ ".join([n.split('/')[-1] for n in cycle_path])
            })

        # Sort by severity descending, then length descending, then cycle_id ascending
        result.sort(key=lambda c: (-c["severity_score"], -c["length"], c["cycle_id"]))
        return result

    @classmethod
    def compute_cycle_severity(
        cls,
        cycle_nodes: List[str],
        node_lookup: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculates deterministic severity score for a cycle:
        Severity = (Sum of Complexities in Cycle) * (Length * 0.75)
        """
        if not cycle_nodes:
            return 0.0

        total_complexity = 0.0
        for n in cycle_nodes:
            norm_n = norm_id(n)
            meta = (node_lookup or {}).get(norm_n, {})
            c = float(meta.get("complexity", meta.get("mccabe_complexity", 1.0)))
            total_complexity += max(1.0, c)

        length_factor = max(1.0, len(cycle_nodes) * 0.75)
        return round(total_complexity * length_factor, 2)

    @classmethod
    def suggest_break_cycle_edge(
        cls,
        cycle_path: List[str],
        edges: Optional[List[Any]] = None,
        node_lookup: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Identifies the optimal candidate edge to break in a cycle to minimize architecture damage.
        Picks the edge pointing to the target with the lowest fan-in / complexity.
        """
        if not cycle_path or len(cycle_path) < 2:
            return {"source": "", "target": "", "reason": "No cycle path provided"}

        candidates = []
        for i in range(len(cycle_path) - 1):
            src = cycle_path[i]
            tgt = cycle_path[i + 1]

            src_meta = (node_lookup or {}).get(src, {})
            tgt_meta = (node_lookup or {}).get(tgt, {})

            src_complexity = float(src_meta.get("complexity", 1.0))
            tgt_complexity = float(tgt_meta.get("complexity", 1.0))
            tgt_fanout = float(tgt_meta.get("coupling", tgt_meta.get("fanout", 1.0)))

            # Lowest combined friction score is best candidate to invert/break
            friction_score = (tgt_complexity * 0.5) + (tgt_fanout * 0.5)
            candidates.append({
                "source": src,
                "target": tgt,
                "friction_score": friction_score,
                "source_name": src.split('/')[-1],
                "target_name": tgt.split('/')[-1]
            })

        # Deterministic sort: lowest friction score, then lexical source
        candidates.sort(key=lambda c: (c["friction_score"], c["source"], c["target"]))
        best = candidates[0]

        return {
            "source": best["source"],
            "target": best["target"],
            "source_name": best["source_name"],
            "target_name": best["target_name"],
            "reason": f"Lowest decoupling friction ({best['source_name']} ➔ {best['target_name']})",
            "friction_score": round(best["friction_score"], 2)
        }
