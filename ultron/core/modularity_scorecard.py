"""
ultron.core.modularity_scorecard
Deterministic AST Modularity, Robert C. Martin Instability Index, and SoC Health Scorecard.
"""

from typing import Dict, List, Any, Optional, Union


def norm_path(path_str: Any) -> str:
    """Normalizes paths to POSIX forward slashes."""
    return str(path_str or "").replace("\\", "/").strip()


class ModularityScorecardEngine:
    """
    Deterministic engine for computing module coupling instability, abstractness balance,
    distance from the Main Sequence (Robert C. Martin metrics), and architectural health grades.
    """

    METRICS_VERSION = "1.0-martin-modularity"

    @classmethod
    def compute_module_instability(
        cls,
        afferent_ca: Union[int, float],
        efferent_ce: Union[int, float]
    ) -> float:
        """
        Computes Robert C. Martin's Package Instability Index:
        I = Ce / (Ca + Ce)
        Where:
        - Ca (Afferent Coupling): Number of inbound modules that depend on this module.
        - Ce (Efferent Coupling): Number of outbound modules this module depends on.
        - I = 0.0: Maximally stable (depended on by many, depends on none).
        - I = 1.0: Maximally unstable / flexible (depends on many, depended on by none).
        """
        ca = max(0.0, float(afferent_ca or 0.0))
        ce = max(0.0, float(efferent_ce or 0.0))

        total = ca + ce
        if total == 0.0:
            return 0.0

        return round(ce / total, 3)

    @classmethod
    def compute_main_sequence_distance(
        cls,
        abstractness_a: float,
        instability_i: float
    ) -> Dict[str, Any]:
        """
        Computes normalized Distance from the Main Sequence:
        D = |A + I - 1.0|
        - D = 0.0: Ideal architectural balance on the Main Sequence.
        - Zone of Pain (A + I < 1.0, D > 0.35): Concrete, rigid, highly depended on.
        - Zone of Uselessness (A + I > 1.0, D > 0.35): Highly abstract, unused.
        """
        a = max(0.0, min(1.0, float(abstractness_a or 0.0)))
        i = max(0.0, min(1.0, float(instability_i or 0.0)))

        distance = round(abs(a + i - 1.0), 3)

        if distance <= 0.35:
            zone = "MAIN_SEQUENCE"
            zone_label = "⚖️ Balanced on Main Sequence"
            zone_class = "zone-balanced"
        elif (a + i) < 1.0:
            zone = "ZONE_OF_PAIN"
            zone_label = "⚠️ Zone of Pain (Rigid / High Coupling)"
            zone_class = "zone-pain"
        else:
            zone = "ZONE_OF_USELESSNESS"
            zone_label = "💤 Zone of Uselessness (Over-Abstracted)"
            zone_class = "zone-useless"

        return {
            "abstractness": a,
            "instability": i,
            "distance": distance,
            "zone": zone,
            "zone_label": zone_label,
            "zone_class": zone_class
        }

    @classmethod
    def evaluate_codebase_modularity(
        cls,
        nodes: Optional[List[Any]] = None,
        edges: Optional[List[Any]] = None,
        risks: Optional[List[Dict[str, Any]]] = None,
        codebase: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Evaluates overall architectural modularity health across all codebase modules.
        Returns aggregate metrics, health score, letter grade (A/B/C/D/F), and module details.
        """
        nodes = nodes or []
        edges = edges or []
        risks = risks or []

        # Build afferent and efferent coupling sets per node
        afferent_map: Dict[str, set] = {}
        efferent_map: Dict[str, set] = {}
        all_node_keys: set = set()

        for edge in edges:
            if isinstance(edge, dict):
                src = norm_path(edge.get("source") or edge.get("source_id"))
                tgt = norm_path(edge.get("target") or edge.get("target_id"))
            else:
                src = norm_path(getattr(edge, "source", getattr(edge, "source_id", "")))
                tgt = norm_path(getattr(edge, "target", getattr(edge, "target_id", "")))

            if src and tgt:
                all_node_keys.add(src)
                all_node_keys.add(tgt)
                efferent_map.setdefault(src, set()).add(tgt)
                afferent_map.setdefault(tgt, set()).add(src)

        # Incorporate risk records
        for r in risks:
            p = norm_path(r.get("file") or r.get("file_path") or r.get("id"))
            if p:
                all_node_keys.add(p)

        if not all_node_keys:
            return {
                "health_score": 100.0,
                "health_grade": "A",
                "mean_instability": 0.0,
                "mean_distance": 0.0,
                "total_modules": 0,
                "zone_distribution": {
                    "main_sequence": 0,
                    "zone_of_pain": 0,
                    "zone_of_uselessness": 0
                },
                "modules": [],
                "provenance": {"version": cls.METRICS_VERSION}
            }

        module_reports = []
        total_instability = 0.0
        total_distance = 0.0
        zone_counts = {"main_sequence": 0, "zone_of_pain": 0, "zone_of_uselessness": 0}

        for node_id in sorted(list(all_node_keys)):
            ca = len(afferent_map.get(node_id, set()))
            ce = len(efferent_map.get(node_id, set()))
            instability = cls.compute_module_instability(ca, ce)

            # Compute abstractness from definitions if available, otherwise baseline 0.1
            abstractness = 0.1
            if codebase and isinstance(codebase, dict) and node_id in codebase:
                c_defs = codebase[node_id].get("definitions", [])
                if c_defs:
                    abstract_defs = sum(1 for d in c_defs if d.get("is_abstract") or "Protocol" in str(d.get("bases", [])) or "ABC" in str(d.get("bases", [])))
                    abstractness = round(abstract_defs / len(c_defs), 2)
            elif "interface" in node_id.lower() or "base" in node_id.lower() or "abstract" in node_id.lower():
                abstractness = 0.7

            seq_data = cls.compute_main_sequence_distance(abstractness, instability)
            distance = seq_data["distance"]
            zone = seq_data["zone"]

            total_instability += instability
            total_distance += distance

            if zone == "MAIN_SEQUENCE":
                zone_counts["main_sequence"] += 1
            elif zone == "ZONE_OF_PAIN":
                zone_counts["zone_of_pain"] += 1
            else:
                zone_counts["zone_of_uselessness"] += 1

            file_name = node_id.split('/')[-1] if node_id else "unknown"
            module_reports.append({
                "file_path": node_id,
                "file_name": file_name,
                "afferent_ca": ca,
                "efferent_ce": ce,
                "instability": instability,
                "abstractness": abstractness,
                "distance": distance,
                "zone": zone,
                "zone_label": seq_data["zone_label"],
                "zone_class": seq_data["zone_class"]
            })

        n = len(module_reports)
        mean_instability = round(total_instability / n, 3) if n > 0 else 0.0
        mean_distance = round(total_distance / n, 3) if n > 0 else 0.0

        # Health score: 100 - (mean_distance * 80 + (pain_fraction * 20))
        pain_fraction = (zone_counts["zone_of_pain"] / n) if n > 0 else 0.0
        health_score = round(max(0.0, min(100.0, 100.0 - (mean_distance * 60.0 + pain_fraction * 40.0))), 1)

        if health_score >= 85.0:
            grade = "A"
        elif health_score >= 70.0:
            grade = "B"
        elif health_score >= 55.0:
            grade = "C"
        elif health_score >= 40.0:
            grade = "D"
        else:
            grade = "F"

        # Sort module reports: Zone of Pain first (highest distance), then path ascending
        module_reports.sort(key=lambda m: (0 if m["zone"] == "ZONE_OF_PAIN" else 1, -m["distance"], m["file_path"]))

        return {
            "health_score": health_score,
            "health_grade": grade,
            "mean_instability": mean_instability,
            "mean_distance": mean_distance,
            "total_modules": n,
            "zone_distribution": zone_counts,
            "modules": module_reports,
            "provenance": {
                "version": cls.METRICS_VERSION,
                "pain_fraction": round(pain_fraction, 3)
            }
        }
