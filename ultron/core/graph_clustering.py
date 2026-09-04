"""
ultron.core.graph_clustering
Deterministic Multi-Level Graph Clustering Engine (System -> Domain -> Module -> File).
"""

from typing import Dict, Any, List, Optional


class GraphClusterEngine:
    """
    Partitions granular AST dependency graphs into multi-level hierarchical abstractions:
    - System View: Top-level architectural domains / packages
    - Module View: Sub-package component boundaries
    - File View: Granular file-level AST dependency graph
    """

    @classmethod
    def _normalize_path(cls, path_str: str) -> str:
        """Strips leading relative dots, drive letters, and normalizes to forward slashes."""
        p = str(path_str or "").replace("\\", "/").strip("/")
        if len(p) > 2 and p[1] == ":" and p[2] == "/":
            p = p[3:]  # Strip C:/
        if p.startswith("./"):
            p = p[2:]
        return p.strip("/")

    @classmethod
    def _detect_common_prefix(cls, paths: List[str]) -> Optional[str]:
        """Detects if all paths share a single common top-level root directory (e.g. 'ultron/')."""
        if not paths:
            return None
        first_segments = []
        for p in paths:
            parts = [seg for seg in cls._normalize_path(p).split("/") if seg]
            if len(parts) > 1:
                first_segments.append(parts[0])
            else:
                return None  # Has root-level files, so no universal common prefix
        if first_segments and all(seg == first_segments[0] for seg in first_segments):
            return first_segments[0]
        return None

    SOURCE_ROOT_WRAPPERS = {"src", "lib", "app", "pkg", "packages"}

    @classmethod
    def _extract_domain(cls, file_path: str, depth: int = 1, common_prefix: Optional[str] = None) -> str:
        """Extracts deterministic domain label based on hierarchy depth."""
        norm = cls._normalize_path(file_path)
        parts = [seg for seg in norm.split("/") if seg]
        if not parts:
            return "(root)"

        # Strip standard source directory root wrappers like src/, lib/, etc. if followed by subdirectories
        if parts[0].lower() in cls.SOURCE_ROOT_WRAPPERS and len(parts) > 2:
            parts = parts[1:]
        elif common_prefix and parts[0] == common_prefix and len(parts) > 1:
            parts = parts[1:]

        if len(parts) <= 1:
            return "(root)"

        if depth == 1:
            return parts[0]
        else:
            return "/".join(parts[:min(depth, len(parts) - 1)])

    @classmethod
    def cluster_graph(cls, dependency_graph: Optional[Dict[str, Any]], level: str = "system") -> Dict[str, Any]:
        """
        Transforms raw AST dependency graph into a clustered hierarchical view.
        Supported levels: 'system', 'module', 'file'.
        """
        graph = dependency_graph or {}
        raw_nodes = graph.get("nodes", [])
        raw_links = graph.get("links") or graph.get("edges") or []

        # Convert dict nodes if necessary
        if isinstance(raw_nodes, dict):
            node_list = [{"id": k, **v} if isinstance(v, dict) else {"id": k} for k, v in raw_nodes.items()]
        elif isinstance(raw_nodes, list):
            node_list = raw_nodes
        else:
            node_list = []

        if level == "file" or not node_list:
            return {
                "level": "file",
                "nodes": node_list,
                "links": raw_links,
                "stats": {
                    "total_clusters": len(node_list),
                    "total_edges": len(raw_links),
                    "total_files": len(node_list)
                }
            }

        depth = 1 if level == "system" else 2
        all_paths = [str(n.get("id") or n.get("file") or "") for n in node_list]
        common_prefix = cls._detect_common_prefix(all_paths)

        # 1. Cluster nodes by domain
        clusters: Dict[str, Dict[str, Any]] = {}
        node_to_cluster: Dict[str, str] = {}

        for n in node_list:
            node_id = str(n.get("id") or n.get("file") or "unknown")
            domain = cls._extract_domain(node_id, depth=depth, common_prefix=common_prefix)
            node_to_cluster[node_id] = domain

            if domain not in clusters:
                clusters[domain] = {
                    "id": domain,
                    "label": domain.upper(),
                    "level": "LOW",
                    "files": [],
                    "total_complexity": 0,
                    "high_risk_count": 0,
                    "internal_coupling": 0
                }

            clusters[domain]["files"].append(node_id)
            comp = Number_val(n.get("complexity") or n.get("cyclomatic_complexity") or 1)
            clusters[domain]["total_complexity"] += comp
            if n.get("level") == "HIGH":
                clusters[domain]["high_risk_count"] += 1

        # Adaptive Anti-Collapse Rule:
        # If clustering collapsed a multi-node graph into <= 1 cluster, fall back adaptively
        # so developers never see a dead single-circle diagram on flat or shallow projects.
        if len(clusters) <= 1 and len(node_list) > 1:
            if len(node_list) <= 60:
                return {
                    "level": "file",
                    "nodes": node_list,
                    "links": raw_links,
                    "stats": {
                        "total_clusters": len(node_list),
                        "total_edges": len(raw_links),
                        "total_files": len(node_list),
                        "adaptive_fallback": True
                    }
                }
            else:
                # For large flat repos (>60 files), try secondary prefix-based clustering
                prefix_clusters: Dict[str, Dict[str, Any]] = {}
                prefix_node_to_cluster: Dict[str, str] = {}
                for n in node_list:
                    nid = str(n.get("id") or n.get("file") or "unknown")
                    base = cls._normalize_path(nid).split("/")[-1]
                    name_part = base.split(".")[0]
                    if "_" in name_part:
                        pfx = name_part.split("_")[0]
                    elif "-" in name_part:
                        pfx = name_part.split("-")[0]
                    else:
                        pfx = name_part[:4] if len(name_part) >= 6 else name_part
                    pfx = pfx.strip().lower() or "misc"
                    prefix_node_to_cluster[nid] = pfx
                    if pfx not in prefix_clusters:
                        prefix_clusters[pfx] = {
                            "id": pfx,
                            "label": pfx.upper(),
                            "level": "LOW",
                            "files": [],
                            "total_complexity": 0,
                            "high_risk_count": 0,
                            "internal_coupling": 0
                        }
                    prefix_clusters[pfx]["files"].append(nid)
                    comp = Number_val(n.get("complexity") or n.get("cyclomatic_complexity") or 1)
                    prefix_clusters[pfx]["total_complexity"] += comp
                    if n.get("level") == "HIGH":
                        prefix_clusters[pfx]["high_risk_count"] += 1

                if len(prefix_clusters) >= 2:
                    clusters = prefix_clusters
                    node_to_cluster = prefix_node_to_cluster

        # 2. Aggregate macro-edges and weights between clusters
        edge_map: Dict[str, Dict[str, Any]] = {}

        for link in raw_links:
            src = str(link.get("source") or link.get("src") or "")
            tgt = str(link.get("target") or link.get("tgt") or "")
            weight = Number_val(link.get("weight") or link.get("coupling") or 1)

            c_src = node_to_cluster.get(src, cls._extract_domain(src, depth, common_prefix))
            c_tgt = node_to_cluster.get(tgt, cls._extract_domain(tgt, depth, common_prefix))

            if c_src == c_tgt:
                if c_src in clusters:
                    clusters[c_src]["internal_coupling"] += weight
            else:
                edge_key = f"{c_src}--->{c_tgt}"
                if edge_key not in edge_map:
                    edge_map[edge_key] = {
                        "source": c_src,
                        "target": c_tgt,
                        "weight": 0,
                        "sub_links_count": 0
                    }
                edge_map[edge_key]["weight"] += weight
                edge_map[edge_key]["sub_links_count"] += 1

        # 3. Format cluster nodes with health and size metrics
        cluster_nodes_list = []
        for d_id, c in clusters.items():
            f_count = len(c["files"])
            avg_comp = round(c["total_complexity"] / max(1, f_count), 1)
            high_count = c["high_risk_count"]
            health = round(max(0.0, min(100.0, 100.0 - (high_count * 15.0 + avg_comp * 1.5))), 1)
            c_level = "HIGH" if high_count > 0 else ("MED" if avg_comp >= 8 else "LOW")

            cluster_nodes_list.append({
                "id": d_id,
                "label": d_id,
                "file_count": f_count,
                "files": c["files"],
                "health_score": health,
                "level": c_level,
                "avg_complexity": avg_comp,
                "total_complexity": c["total_complexity"],
                "internal_coupling": c["internal_coupling"]
            })

        cluster_nodes_list.sort(key=lambda x: x["file_count"], reverse=True)
        aggregated_edges = list(edge_map.values())
        aggregated_edges.sort(key=lambda x: x["weight"], reverse=True)

        return {
            "level": level,
            "nodes": cluster_nodes_list,
            "links": aggregated_edges,
            "stats": {
                "total_clusters": len(cluster_nodes_list),
                "total_edges": len(aggregated_edges),
                "total_files": len(node_list)
            }
        }


def Number_val(val: Any) -> int:
    """Safe numeric conversion helper."""
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 1
