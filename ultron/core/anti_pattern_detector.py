"""
ultron.core.anti_pattern_detector
Deterministic Architectural Anti-Pattern and Semantic Drift Detector.
"""

from typing import Dict, List, Any, Optional, Set


def norm_path(path_str: Any) -> str:
    """Normalizes file paths to POSIX forward slashes."""
    return str(path_str or "").replace("\\", "/").strip()


class AntiPatternDetector:
    """
    Deterministic detector for classic architectural anti-patterns:
    - GOD_OBJECT: Monolithic files with high LOC, cyclomatic complexity, and coupling fanout.
    - FEATURE_ENVY: Modules with disproportionate outbound coupling to foreign modules.
    - SHOTGUN_SURGERY: Highly coupled bottleneck files where changes force cascading modifications.
    - DEAD_ABSTRACTION: Abstract classes or interfaces with zero inbound caller references.
    """

    DETECTOR_VERSION = "1.0-architectural-anti-patterns"

    # Threshold constants
    GOD_OBJECT_LOC_THRESHOLD = 100
    GOD_OBJECT_COMPLEXITY_THRESHOLD = 14.0
    GOD_OBJECT_COUPLING_THRESHOLD = 5

    FEATURE_ENVY_CE_THRESHOLD = 4
    SHOTGUN_SURGERY_CA_THRESHOLD = 6

    @classmethod
    def detect_anti_patterns(
        cls,
        nodes: Optional[List[Any]] = None,
        edges: Optional[List[Any]] = None,
        risks: Optional[List[Dict[str, Any]]] = None,
        codebase: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Runs comprehensive anti-pattern detection across the entire codebase graph.
        Returns a deterministically sorted list of identified architectural smells.
        """
        nodes = nodes or []
        edges = edges or []
        risks = risks or []

        # Build afferent and efferent coupling sets
        afferent_map: Dict[str, Set[str]] = {}
        efferent_map: Dict[str, Set[str]] = {}
        all_files: Set[str] = set()

        for edge in edges:
            if isinstance(edge, dict):
                src = norm_path(edge.get("source") or edge.get("source_id"))
                tgt = norm_path(edge.get("target") or edge.get("target_id"))
            else:
                src = norm_path(getattr(edge, "source", getattr(edge, "source_id", "")))
                tgt = norm_path(getattr(edge, "target", getattr(edge, "target_id", "")))

            if src and tgt:
                all_files.add(src)
                all_files.add(tgt)
                efferent_map.setdefault(src, set()).add(tgt)
                afferent_map.setdefault(tgt, set()).add(src)

        # Map risks by normalized file path
        risk_map: Dict[str, Dict[str, Any]] = {}
        for r in risks:
            if isinstance(r, dict):
                p = norm_path(r.get("file") or r.get("file_path") or r.get("id"))
                if p:
                    all_files.add(p)
                    risk_map[p] = r

        detected_patterns: List[Dict[str, Any]] = []

        for file_path in sorted(list(all_files)):
            file_name = file_path.split("/")[-1] if file_path else "unknown"
            r = risk_map.get(file_path, {})

            ca = len(afferent_map.get(file_path, set()))
            ce = len(efferent_map.get(file_path, set()))
            total_coupling = ca + ce

            complexity = float(r.get("complexity", 0.0) or 0.0)
            loc = int(r.get("lines_of_code", r.get("loc", 0)) or 0)

            # 1. GOD_OBJECT Check
            if (loc >= cls.GOD_OBJECT_LOC_THRESHOLD or complexity >= cls.GOD_OBJECT_COMPLEXITY_THRESHOLD) and total_coupling >= cls.GOD_OBJECT_COUPLING_THRESHOLD:
                detected_patterns.append({
                    "id": f"AP-GOD-{file_name}",
                    "file_path": file_path,
                    "file_name": file_name,
                    "pattern_type": "GOD_OBJECT",
                    "pattern_name": "🏛️ God Object (Monolith)",
                    "severity": "HIGH",
                    "severity_class": "high",
                    "metrics": {
                        "lines_of_code": loc,
                        "complexity": complexity,
                        "total_coupling": total_coupling
                    },
                    "description": f"Module exhibits monolithic complexity (C={complexity}, LOC={loc}) and coordinates {total_coupling} foreign connections.",
                    "playbook": "Decompose into single-responsibility service components and extract cohesive helper subroutines."
                })

            # 2. FEATURE_ENVY Check
            elif ce >= cls.FEATURE_ENVY_CE_THRESHOLD and ce > (ca * 2):
                detected_patterns.append({
                    "id": f"AP-ENVY-{file_name}",
                    "file_path": file_path,
                    "file_name": file_name,
                    "pattern_type": "FEATURE_ENVY",
                    "pattern_name": "👀 Feature Envy (Outbound Skew)",
                    "severity": "MEDIUM",
                    "severity_class": "med",
                    "metrics": {
                        "efferent_ce": ce,
                        "afferent_ca": ca
                    },
                    "description": f"Module depends excessively on external modules (Ce={ce}) relative to incoming calls (Ca={ca}).",
                    "playbook": "Move envious operations closer to external target modules or inject dependencies via interfaces."
                })

            # 3. SHOTGUN_SURGERY Check
            if ca >= cls.SHOTGUN_SURGERY_CA_THRESHOLD:
                severity = "HIGH" if ca >= 10 else "MEDIUM"
                detected_patterns.append({
                    "id": f"AP-SHOTGUN-{file_name}",
                    "file_path": file_path,
                    "file_name": file_name,
                    "pattern_type": "SHOTGUN_SURGERY",
                    "pattern_name": "💥 Shotgun Surgery Bottleneck",
                    "severity": severity,
                    "severity_class": "high" if severity == "HIGH" else "med",
                    "metrics": {
                        "afferent_ca": ca,
                        "efferent_ce": ce
                    },
                    "description": f"Critical bottleneck module depended on by {ca} inbound callers; changes risk cascading multi-file edits.",
                    "playbook": "Introduce façade layer or publish-subscribe event bus to isolate cascading caller modifications."
                })

            # 4. DEAD_ABSTRACTION Check
            is_abstract_name = any(kw in file_name.lower() for kw in ["base", "interface", "abstract", "protocol", "stub"])
            if is_abstract_name and ca == 0 and ce == 0:
                detected_patterns.append({
                    "id": f"AP-DEAD-{file_name}",
                    "file_path": file_path,
                    "file_name": file_name,
                    "pattern_type": "DEAD_ABSTRACTION",
                    "pattern_name": "💤 Dead Abstraction",
                    "severity": "LOW",
                    "severity_class": "low",
                    "metrics": {
                        "afferent_ca": 0,
                        "efferent_ce": 0
                    },
                    "description": "Abstract naming/decorator detected but has zero inbound references or concrete callers.",
                    "playbook": "Verify concrete implementers or prune speculative dead abstraction."
                })

            # 5. BRAIN_METHOD / COMPLEXITY_SINK Check
            if complexity >= 18.0:
                detected_patterns.append({
                    "id": f"AP-BRAIN-{file_name}",
                    "file_path": file_path,
                    "file_name": file_name,
                    "pattern_type": "BRAIN_METHOD",
                    "pattern_name": "🧠 Brain Method / High Complexity Sink",
                    "severity": "HIGH",
                    "severity_class": "high",
                    "metrics": {
                        "complexity": complexity,
                        "lines_of_code": loc
                    },
                    "description": f"Module contains deeply nested algorithmic complexity (C={complexity:.1f}) exceeding safety thresholds.",
                    "playbook": "Extract nested branching conditionals into pure strategy methods or lookup tables."
                })

        # 6. CIRCULAR_DEPENDENCY Check (from edges)
        from ultron.core.cycle_detector import CycleDetector
        cycle_edges = [{"source": e.get("source") or e.get("source_id", ""), "target": e.get("target") or e.get("target_id", "")} if isinstance(e, dict) else {"source": getattr(e, "source", ""), "target": getattr(e, "target", "")} for e in edges]
        cycle_records = CycleDetector.find_all_cycles(edges=cycle_edges)
        import hashlib
        for c_rec in cycle_records:
            cycle = c_rec.get("cycle_path") or c_rec.get("path", [])
            cycle_str = " -> ".join(cycle)
            primary_file = cycle[0] if cycle else "unknown"
            file_name = primary_file.split("/")[-1]
            cycle_hash = hashlib.md5(cycle_str.encode("utf-8")).hexdigest()[:6]
            break_edge = c_rec.get("recommended_break_edge") or c_rec.get("break_edge")
            detected_patterns.append({
                "id": f"AP-CYCLE-{file_name}-{cycle_hash}",
                "file_path": primary_file,
                "file_name": file_name,
                "pattern_type": "CIRCULAR_DEPENDENCY",
                "pattern_name": "🔄 Circular Dependency Loop",
                "severity": "HIGH",
                "severity_class": "high",
                "metrics": {
                    "cycle_length": len(cycle),
                    "cycle_path": cycle,
                    "break_edge": break_edge
                },
                "description": f"Circular architectural dependency detected: {cycle_str}",
                "playbook": "Apply Dependency Inversion Principle (DIP) or extract shared interfaces to break circular coupling."
            })

        # Deterministic sorting: HIGH -> MEDIUM -> LOW, then file_path
        severity_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        detected_patterns.sort(key=lambda x: (severity_rank.get(x["severity"], 3), x["file_path"]))

        return detected_patterns
