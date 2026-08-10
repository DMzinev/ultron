"""
Ultron Core — System Model Structural Diffing Engine
Campaign 36 / v2.4 — Structural Change Tracking & Model Evolution
"""

import sys
import os
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Set, Tuple

from ultron.core.system_model import SystemGraph, SystemNode, SystemEdge


@dataclass
class ModelDiffResult:
    """Structured result envelope for graph diffing between two SystemGraph instances."""
    before_hash: str
    after_hash: str
    added_nodes: List[str] = field(default_factory=list)
    removed_nodes: List[str] = field(default_factory=list)
    modified_nodes: List[Dict[str, Any]] = field(default_factory=list)
    added_edges: List[Dict[str, Any]] = field(default_factory=list)
    removed_edges: List[Dict[str, Any]] = field(default_factory=list)
    structural_change_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SystemModelDiff:
    """
    Computes structural differences and evolution score between SystemGraph(t0) and SystemGraph(t1).
    """

    @staticmethod
    def _edge_key(edge: SystemEdge) -> Tuple[str, str, str]:
        return (edge.source_id, edge.target_id, edge.type.value if hasattr(edge.type, "value") else str(edge.type))

    @classmethod
    def diff(cls, graph_before: SystemGraph, graph_after: SystemGraph) -> ModelDiffResult:
        """
        Calculates node/edge diffs and computes structural change score.
        Formula: 2.0 * (|N_added| + |N_removed|) + 1.0 * (|E_added| + |E_removed|) + 0.1 * sum(|delta LOC|)
        """
        before_hash = graph_before.metadata.get("model_hash", "")
        after_hash = graph_after.metadata.get("model_hash", "")

        nodes_before_ids = set(graph_before.nodes.keys())
        nodes_after_ids = set(graph_after.nodes.keys())

        added_nodes = sorted(list(nodes_after_ids - nodes_before_ids))
        removed_nodes = sorted(list(nodes_before_ids - nodes_after_ids))
        common_nodes = nodes_before_ids.intersection(nodes_after_ids)

        modified_nodes: List[Dict[str, Any]] = []
        loc_delta_sum = 0.0

        for nid in sorted(common_nodes):
            n_before = graph_before.nodes[nid]
            n_after = graph_after.nodes[nid]

            loc_b = n_before.facts.get("loc", 0) if n_before.facts else 0
            loc_a = n_after.facts.get("loc", 0) if n_after.facts else 0
            comp_b = n_before.facts.get("complexity", 1) if n_before.facts else 1
            comp_a = n_after.facts.get("complexity", 1) if n_after.facts else 1

            loc_diff = loc_a - loc_b
            comp_diff = comp_a - comp_b

            if loc_diff != 0 or comp_diff != 0:
                loc_delta_sum += abs(loc_diff)
                modified_nodes.append({
                    "id": nid,
                    "file_path": n_after.file_path,
                    "loc_before": loc_b,
                    "loc_after": loc_a,
                    "loc_delta": loc_diff,
                    "complexity_delta": comp_diff
                })

        # Process edges
        edges_before_map = {cls._edge_key(e): e for e in graph_before.edges}
        edges_after_map = {cls._edge_key(e): e for e in graph_after.edges}

        edges_before_keys = set(edges_before_map.keys())
        edges_after_keys = set(edges_after_map.keys())

        added_edge_keys = sorted(list(edges_after_keys - edges_before_keys))
        removed_edge_keys = sorted(list(edges_before_keys - edges_after_keys))

        added_edges = [edges_after_map[k].to_dict() for k in added_edge_keys]
        removed_edges = [edges_before_map[k].to_dict() for k in removed_edge_keys]

        # Calculate structural change score
        score = (
            2.0 * (len(added_nodes) + len(removed_nodes)) +
            1.0 * (len(added_edges) + len(removed_edges)) +
            0.1 * loc_delta_sum
        )

        return ModelDiffResult(
            before_hash=before_hash,
            after_hash=after_hash,
            added_nodes=added_nodes,
            removed_nodes=removed_nodes,
            modified_nodes=modified_nodes,
            added_edges=added_edges,
            removed_edges=removed_edges,
            structural_change_score=round(score, 2)
        )
