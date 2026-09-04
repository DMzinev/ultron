"""
Ultron Core — Canonical System Model Datastructures & Pure Data Store
Campaign 28 / v2.3 — Canonical Software System Model Architecture
"""

import sys
import os
import json
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Tuple


class SystemNodeType(str, Enum):
    PACKAGE     = "PACKAGE"
    MODULE      = "MODULE"
    CLASS       = "CLASS"
    METHOD      = "METHOD"
    FUNCTION    = "FUNCTION"
    TEST        = "TEST"
    CONFIG      = "CONFIG"


class SystemEdgeType(str, Enum):
    CONTAINS    = "CONTAINS"
    IMPORTS     = "IMPORTS"
    CALLS       = "CALLS"
    INHERITS    = "INHERITS"
    IMPLEMENTS  = "IMPLEMENTS"
    READS       = "READS"
    WRITES      = "WRITES"
    TESTS       = "TESTS"
    MODIFIES    = "MODIFIES"
    DEPENDS_ON  = "DEPENDS_ON"
    EXPOSES     = "EXPOSES"


@dataclass
class EvidenceObject:
    """Immutable observation record backed by empirical measurement."""
    id: str
    type: str  # e.g., "AST_FACT", "GIT_HISTORY", "TEST_COVERAGE"
    subject_id: str
    measurement: Dict[str, Any]
    source: Dict[str, Any]
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceObject":
        return cls(
            id=data["id"],
            type=data["type"],
            subject_id=data["subject_id"],
            measurement=data.get("measurement", {}),
            source=data.get("source", {}),
            observed_at=data.get("observed_at", datetime.now(timezone.utc).isoformat()),
            model_version=data.get("model_version", "1.0")
        )


@dataclass
class SystemNode:
    """
    Canonical representation of a repository entity.
    Strictly separates objective observations ('facts') from derived interpretations.
    """
    id: str
    type: SystemNodeType
    file_path: str
    line_start: int = 1
    line_end: int = 1
    facts: Dict[str, Any] = field(default_factory=dict)
    evidence_ids: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Coerce type if string
        if isinstance(self.type, str):
            try:
                self.type = SystemNodeType(self.type)
            except ValueError:
                self.type = SystemNodeType.MODULE
        # Enforce POSIX forward-slashes for cross-platform deterministic node IDs
        self.file_path = os.path.normpath(self.file_path).replace("\\", "/")
        if not self.id:
            self.id = f"{self.type.value.lower()}:{self.file_path}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "facts": self.facts,
            "evidence_ids": self.evidence_ids
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemNode":
        return cls(
            id=data["id"],
            type=data["type"],
            file_path=data["file_path"],
            line_start=data.get("line_start", 1),
            line_end=data.get("line_end", 1),
            facts=data.get("facts", {}),
            evidence_ids=data.get("evidence_ids", [])
        )


@dataclass
class SystemEdge:
    """Relationship connecting two system nodes."""
    source_id: str
    target_id: str
    type: SystemEdgeType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.type, str):
            try:
                self.type = SystemEdgeType(self.type)
            except ValueError:
                self.type = SystemEdgeType.DEPENDS_ON
        self.source_id = self.source_id.replace("\\", "/")
        self.target_id = self.target_id.replace("\\", "/")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type.value,
            "weight": self.weight,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemEdge":
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            type=data["type"],
            weight=data.get("weight", 1.0),
            metadata=data.get("metadata", {})
        )


@dataclass
class SystemGraph:
    """Complete canonical system model graph payload."""
    nodes: Dict[str, SystemNode] = field(default_factory=dict)
    edges: List[SystemEdge] = field(default_factory=list)
    evidence: Dict[str, EvidenceObject] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: SystemNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: SystemEdge) -> None:
        self.edges.append(edge)

    def get_dependencies(self, node_id: str) -> List[str]:
        """Returns outgoing dependency IDs (nodes that node_id imports/calls)."""
        norm_id = node_id.replace("\\", "/")
        return sorted(list(set(e.target_id for e in self.edges if e.source_id == norm_id)))

    def get_dependents(self, node_id: str) -> List[str]:
        """Returns incoming dependent IDs (nodes that import/call node_id)."""
        norm_id = node_id.replace("\\", "/")
        return sorted(list(set(e.source_id for e in self.edges if e.target_id == norm_id)))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": {nid: node.to_dict() for nid, node in sorted(self.nodes.items())},
            "edges": [edge.to_dict() for edge in sorted(self.edges, key=lambda e: (e.source_id, e.target_id, e.type.value))],
            "evidence": {eid: ev.to_dict() for eid, ev in sorted(self.evidence.items())},
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemGraph":
        graph = cls()
        for nid, ndata in data.get("nodes", {}).items():
            graph.nodes[nid] = SystemNode.from_dict(ndata)
        for edata in data.get("edges", []):
            graph.edges.append(SystemEdge.from_dict(edata))
        for eid, evdata in data.get("evidence", {}).items():
            graph.evidence[eid] = EvidenceObject.from_dict(evdata)
        graph.metadata = data.get("metadata", {})
        return graph


@dataclass
class SystemModelSnapshot:
    """Immutable snapshot wrapper for system model versioning."""
    snapshot_id: str
    model_hash: str
    timestamp: str
    graph_data: Dict[str, Any]


class SystemModelManager:
    """
    Pure Data Store & Manager for Canonical System Model.
    INVARIANT 1: Contains ZERO risk evaluation, scoring, or recommendation logic.
    """
    def __init__(self, graph: Optional[SystemGraph] = None):
        if graph is not None:
            self.graph = graph
        else:
            self.graph = SystemGraph(metadata={
                "schema_version": "1.0",
                "adapter": {"name": "python", "version": "1.0"},
                "created_at": datetime.now(timezone.utc).isoformat()
            })

    def clear(self) -> None:
        self.graph = SystemGraph(metadata={
            "schema_version": "1.0",
            "adapter": {"name": "python", "version": "1.0"},
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    def add_node(self, node: SystemNode) -> None:
        self.graph.nodes[node.id] = node

    def get_node(self, node_id: str) -> Optional[SystemNode]:
        norm_id = node_id.replace("\\", "/")
        return self.graph.nodes.get(norm_id)

    def add_edge(self, edge: SystemEdge) -> None:
        self.graph.edges.append(edge)

    def add_evidence(self, evidence: EvidenceObject) -> None:
        self.graph.evidence[evidence.id] = evidence
        if evidence.subject_id in self.graph.nodes:
            node = self.graph.nodes[evidence.subject_id]
            if evidence.id not in node.evidence_ids:
                node.evidence_ids.append(evidence.id)

    def compute_completeness_telemetry(self, files_discovered: int) -> Dict[str, Any]:
        """Calculates graph completeness telemetry metrics with zero-division safety."""
        module_nodes = [n for n in self.graph.nodes.values() if n.type == SystemNodeType.MODULE or n.type == SystemNodeType.TEST]
        syntax_errors = len([n for n in module_nodes if "parse_error" in n.facts])
        files_parsed = len(module_nodes)

        parse_coverage_pct = round((files_parsed / files_discovered * 100.0) if files_discovered > 0 else 100.0, 1)

        total_classes = len([n for n in self.graph.nodes.values() if n.type == SystemNodeType.CLASS])
        total_functions = len([n for n in self.graph.nodes.values() if n.type == SystemNodeType.FUNCTION or n.type == SystemNodeType.METHOD])

        telemetry = {
            "files_discovered": files_discovered,
            "files_parsed": files_parsed,
            "syntax_errors": syntax_errors,
            "parse_coverage_pct": parse_coverage_pct,
            "total_classes": total_classes,
            "total_functions": total_functions,
            "total_edges": len(self.graph.edges)
        }
        self.graph.metadata["completeness"] = telemetry
        return telemetry

    def compute_hash(self) -> str:
        """
        Computes byte-identical SHA-256 digest over canonical system model structure.
        INVARIANT 4: Explicitly excludes runtime timestamps to guarantee scan(repo) -> H determinism.
        """
        canonical_nodes = [
            (nid, self.graph.nodes[nid].to_dict())
            for nid in sorted(self.graph.nodes.keys())
        ]
        canonical_edges = [
            (e.source_id, e.target_id, e.type.value, e.weight)
            for e in sorted(self.graph.edges, key=lambda x: (x.source_id, x.target_id, x.type.value))
        ]
        digest_payload = {
            "schema_version": self.graph.metadata.get("schema_version", "1.0"),
            "adapter": self.graph.metadata.get("adapter", {}),
            "nodes": canonical_nodes,
            "edges": canonical_edges
        }
        serialized = json.dumps(digest_payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def serialize(self) -> Dict[str, Any]:
        d = self.graph.to_dict()
        d["metadata"]["model_hash"] = self.compute_hash()
        return d

    def serialize_json(self) -> str:
        d = self.graph.to_dict()
        d["metadata"]["model_hash"] = self.compute_hash()
        return json.dumps(d, indent=2, ensure_ascii=False)

    def deserialize_json(self, raw_json: str) -> None:
        data = json.loads(raw_json)
        self.graph = SystemGraph.from_dict(data)

    def create_snapshot(self) -> SystemModelSnapshot:
        m_hash = self.compute_hash()
        snap_id = f"snap-{m_hash[:12]}"
        return SystemModelSnapshot(
            snapshot_id=snap_id,
            model_hash=m_hash,
            timestamp=datetime.now(timezone.utc).isoformat(),
            graph_data=self.graph.to_dict()
        )
