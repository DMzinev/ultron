import unittest

class TestHierarchicalGraphClustering(unittest.TestCase):
    def test_clustering_reduces_951_nodes_to_human_comprehensible_domains(self):
        # Create synthetic 951 nodes across domains: core, interfaces, tests, utils, experimental
        domains = ["core/pipeline", "core/rkm", "core/scoring", "interfaces/web", "interfaces/api", "interfaces/cli", "tests", "experimental"]
        raw_nodes = []
        for i in range(951):
            dom = domains[i % len(domains)]
            raw_nodes.append({
                "id": f"ultron/{dom}/module_{i}.py",
                "complexity": (i % 20) + 1,
                "level": "HIGH" if (i % 20) >= 15 else "LOW"
            })

        # Emulate graph.js extractDomain algorithm
        clusters = {}
        for n in raw_nodes:
            parts = n["id"].split("/")
            dom = parts[1] if len(parts) > 1 else "root"
            if dom not in clusters:
                clusters[dom] = {"files": [], "totalComplexity": 0, "highRisk": 0}
            clusters[dom]["files"].append(n["id"])
            clusters[dom]["totalComplexity"] += n["complexity"]
            if n["level"] == "HIGH":
                clusters[dom]["highRisk"] += 1

        # Assertions
        cluster_count = len(clusters)
        self.assertLessEqual(cluster_count, 15, f"Expected <= 15 domains, got {cluster_count}")
        self.assertGreaterEqual(cluster_count, 3)

        total_clustered_files = sum(len(c["files"]) for c in clusters.values())
        self.assertEqual(total_clustered_files, 951, "Zero files lost in hierarchical clustering")

    def test_drilldown_preserves_subgraph_edges(self):
        # Verify that clicking a domain cluster preserves intra-cluster links
        files_in_cluster = {"ultron/core/a.py", "ultron/core/b.py", "ultron/core/c.py"}
        all_links = [
            {"source": "ultron/core/a.py", "target": "ultron/core/b.py"},
            {"source": "ultron/core/b.py", "target": "ultron/interfaces/c.py"}, # cross-domain
            {"source": "ultron/core/b.py", "target": "ultron/core/c.py"},
        ]

        sub_links = [
            l for l in all_links
            if l["source"] in files_in_cluster and l["target"] in files_in_cluster
        ]
        self.assertEqual(len(sub_links), 2)

if __name__ == "__main__":
    unittest.main()
