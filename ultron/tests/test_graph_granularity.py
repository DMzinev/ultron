"""
Ultron Graph Granularity & Cycle Highlighting Test Suite
Validates Task C1:
- File vs symbol granularity contract
- Package clustering & blast radius attributes
- Import cycle edge detection and in_cycle flags
- Referential integrity closure
- Graceful fallbacks and route contract preservation
"""

import os
import sys
import unittest
import tempfile
import shutil

from ultron.core import analyzer
from ultron.interfaces.server import UltronAPIHandler


class DummyGraphServer:
    """Mock server context for testing handler mixins directly."""
    def __init__(self, repo_path):
        self.repo_path = repo_path
        self._sent_code = None
        self._sent_data = None

    def get_request_data(self):
        return self._request_data

    def get_post_data(self):
        return self._request_data

    def send_json_response(self, code, data):
        self._sent_code = code
        self._sent_data = data


class TestGraphGranularity(unittest.TestCase):
    def setUp(self):
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        self.clean_repo = os.path.join(self.fixtures_dir, "clean_repo")
        self.tangled_repo = os.path.join(self.fixtures_dir, "tangled_repo")
        self.ultron_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def _invoke_graph(self, repo_path, granularity="file"):
        server = DummyGraphServer(repo_path)
        server._request_data = {"repo": repo_path, "granularity": granularity}
        # Call the mixin method directly bound to server
        UltronAPIHandler.handle_dependency_graph(server)
        return server._sent_code, server._sent_data

    def test_default_granularity_is_file(self):
        """Default granularity returns 100% file nodes."""
        code, data = self._invoke_graph(self.clean_repo, granularity="file")
        self.assertEqual(code, 200)
        self.assertTrue(data["success"])
        nodes = data["nodes"]
        self.assertGreater(len(nodes), 0)
        for n in nodes:
            self.assertEqual(n["type"], "file", f"Node {n['id']} has non-file type {n['type']}")
            self.assertIn("package", n)
            self.assertIn("blast_radius", n)
            self.assertIn("in_cycle", n)

    def test_symbol_granularity_symbols_only(self):
        """Symbol granularity returns only function, class, and method nodes."""
        code, data = self._invoke_graph(self.clean_repo, granularity="symbol")
        self.assertEqual(code, 200)
        self.assertTrue(data["success"])
        nodes = data["nodes"]
        self.assertGreater(len(nodes), 0)
        for n in nodes:
            self.assertIn(
                n["type"],
                ("function", "class", "method"),
                f"Node {n['id']} has unexpected type {n['type']}"
            )

    def test_referential_integrity_closure_file_granularity(self):
        """Every link in file granularity must connect nodes that exist in nodes list."""
        code, data = self._invoke_graph(self.clean_repo, granularity="file")
        self.assertEqual(code, 200)
        node_ids = {n["id"] for n in data["nodes"]}
        for link in data["links"]:
            self.assertIn(
                link["source"], node_ids,
                f"Dangling link source: {link['source']} not in nodes"
            )
            self.assertIn(
                link["target"], node_ids,
                f"Dangling link target: {link['target']} not in nodes"
            )

    def test_referential_integrity_closure_symbol_granularity(self):
        """Every link in symbol granularity must connect nodes that exist in symbol nodes list."""
        code, data = self._invoke_graph(self.clean_repo, granularity="symbol")
        self.assertEqual(code, 200)
        node_ids = {n["id"] for n in data["nodes"]}
        for link in data["links"]:
            self.assertIn(
                link["source"], node_ids,
                f"Dangling link source: {link['source']} not in symbol nodes"
            )
            self.assertIn(
                link["target"], node_ids,
                f"Dangling link target: {link['target']} not in symbol nodes"
            )

    def test_package_and_blast_radius_attributes(self):
        """File nodes carry package (with forward slashes or '(root)') and non-negative blast radius."""
        code, data = self._invoke_graph(self.clean_repo, granularity="file")
        self.assertEqual(code, 200)
        for n in data["nodes"]:
            self.assertIsInstance(n["package"], str)
            self.assertNotIn("\\", n["package"], "Package must not contain Windows backslashes")
            self.assertGreaterEqual(n["blast_radius"], 0)

    def test_cycle_edge_highlighting_on_tangled_repo(self):
        """tangled_repo fixture must have detected cycle edges with in_cycle == True."""
        code, data = self._invoke_graph(self.tangled_repo, granularity="file")
        self.assertEqual(code, 200)
        nodes = data["nodes"]
        links = data["links"]

        cycle_nodes = [n for n in nodes if n.get("in_cycle")]
        cycle_links = [l for l in links if l.get("in_cycle")]

        self.assertGreater(len(cycle_nodes), 0, "Expected cycle participant nodes in tangled_repo")
        self.assertGreater(len(cycle_links), 0, "Expected in_cycle links in tangled_repo")

        # Verify cycle link attributes
        for cl in cycle_links:
            self.assertTrue(cl["in_cycle"])
            self.assertEqual(cl["type"], "import", "Foundational link type 'import' must be preserved")

    def test_acyclic_repo_has_zero_cycles(self):
        """clean_repo fixture must have 0 cycle nodes and 0 cycle links."""
        code, data = self._invoke_graph(self.clean_repo, granularity="file")
        self.assertEqual(code, 200)
        cycle_nodes = [n for n in data["nodes"] if n.get("in_cycle")]
        cycle_links = [l for l in data["links"] if l.get("in_cycle")]
        self.assertEqual(len(cycle_nodes), 0, "Acyclic clean_repo should have 0 cycle nodes")
        self.assertEqual(len(cycle_links), 0, "Acyclic clean_repo should have 0 cycle links")

    def test_invalid_granularity_fallback(self):
        """Invalid granularity safely falls back to 'file' without error."""
        code, data = self._invoke_graph(self.clean_repo, granularity="bogus_granularity")
        self.assertEqual(code, 200)
        self.assertTrue(data["success"])
        for n in data["nodes"]:
            self.assertEqual(n["type"], "file")

    def test_empty_codebase_handling(self):
        """Empty directory returns 200 with empty nodes and links without throwing."""
        temp_dir = tempfile.mkdtemp(prefix="ultron_empty_graph_")
        try:
            code, data = self._invoke_graph(temp_dir, granularity="file")
            self.assertEqual(code, 200)
            self.assertTrue(data["success"])
            self.assertEqual(data["nodes"], [])
            self.assertEqual(data["links"], [])
            self.assertEqual(data["medians"]["complexity"], 0)
            self.assertEqual(data["medians"]["coupling"], 0)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_route_contract_exact_keys(self):
        """Response keys must strictly match ['links', 'medians', 'nodes', 'success']."""
        code, data = self._invoke_graph(self.clean_repo, granularity="file")
        self.assertEqual(code, 200)
        expected_keys = sorted(["links", "medians", "nodes", "success"])
        actual_keys = sorted(list(data.keys()))
        self.assertEqual(actual_keys, expected_keys)


if __name__ == "__main__":
    unittest.main()
