"""
Ultron Unit Tests — JavaScript & TypeScript Language Adapter (Prototype Tier)
Task P3-D1 — Multi-Language Prototype Verification & Route Integration
"""

import os
import sys
import json
import tempfile
import unittest

from ultron.core.system_model import SystemNodeType, SystemEdgeType
from ultron.core.language_adapter import JavaScriptLanguageAdapter, MultiLanguageAdapter, PythonLanguageAdapter
from ultron.interfaces.server import UltronAPIHandler


class DummyWFile:
    def __init__(self):
        self.data = bytearray()
    def write(self, b):
        self.data.extend(b)


class DummyHandler:
    def __init__(self, post_data):
        self._post_data = post_data
        self.wfile = DummyWFile()
        self.status_code = None
        self.response_body = None

    def get_post_data(self):
        return self._post_data

    def get_repo_root_path(self):
        return "."

    def _memory_snapshot(self, repo_path):
        return {"initialized": False, "health_score": None}

    def send_json_response(self, code, data):
        self.status_code = code
        self.response_body = data


class TestJavaScriptLanguageAdapter(unittest.TestCase):
    """Test suite verifying JavaScriptLanguageAdapter and MultiLanguageAdapter."""

    @classmethod
    def setUpClass(cls):
        cls.fixture_repo = os.path.join(
            os.path.dirname(__file__), "fixtures", "js_sample_repo"
        )

    def test_js_file_discovery(self):
        """Discovers all supported JS/TS/CJS files while ignoring standard exclusions."""
        adapter = JavaScriptLanguageAdapter()
        graph = adapter.parse_repository(self.fixture_repo)

        module_ids = [n.id for n in graph.nodes.values() if n.type in (SystemNodeType.MODULE, SystemNodeType.TEST)]
        self.assertIn("module:src/calculator.js", module_ids)
        self.assertIn("module:src/index.js", module_ids)
        self.assertIn("module:src/legacy_logger.cjs", module_ids)
        self.assertIn("module:src/math.js", module_ids)
        self.assertIn("module:src/utils.ts", module_ids)
        self.assertIn("module:tests/calculator.test.js", module_ids)

        # Ensure exclusions work
        with tempfile.TemporaryDirectory() as tmpdir:
            nm_dir = os.path.join(tmpdir, "node_modules", "pkg")
            os.makedirs(nm_dir, exist_ok=True)
            with open(os.path.join(nm_dir, "leak.js"), "w", encoding="utf-8") as f:
                f.write("export const x = 1;\\n")
            with open(os.path.join(tmpdir, "valid.js"), "w", encoding="utf-8") as f:
                f.write("export const y = 2;\\n")

            g = adapter.parse_repository(tmpdir)
            self.assertIn("module:valid.js", g.nodes)
            self.assertNotIn("module:node_modules/pkg/leak.js", g.nodes)

    def test_import_and_export_edge_extraction(self):
        """Verifies ES imports, re-exports, and CommonJS requires extract canonical IMPORTS edges."""
        adapter = JavaScriptLanguageAdapter()
        graph = adapter.parse_repository(self.fixture_repo)

        calc_deps = graph.get_dependencies("module:src/calculator.js")
        self.assertIn("module:src/math.js", calc_deps)
        self.assertIn("module:src/utils.ts", calc_deps)

        index_deps = graph.get_dependencies("module:src/index.js")
        self.assertIn("module:src/calculator.js", index_deps)
        self.assertIn("module:src/legacy_logger.cjs", index_deps)
        self.assertIn("module:src/math.js", index_deps)

        logger_deps = graph.get_dependencies("module:src/legacy_logger.cjs")
        self.assertIn("module:path", logger_deps)

    def test_directory_relative_import_resolution(self):
        """Verifies imports resolve relative to importing directory (e.g. tests/ -> src/)."""
        adapter = JavaScriptLanguageAdapter()
        graph = adapter.parse_repository(self.fixture_repo)

        test_deps = graph.get_dependencies("module:tests/calculator.test.js")
        self.assertIn("module:src/calculator.js", test_deps)

        # Verify TESTS relationship edge
        tests_edges = [
            e for e in graph.edges
            if e.source_id == "module:tests/calculator.test.js" and e.type == SystemEdgeType.TESTS
        ]
        self.assertTrue(len(tests_edges) > 0)
        self.assertEqual(tests_edges[0].target_id, "module:src/calculator.js")

    def test_branching_complexity_proxy(self):
        """Verifies branching keyword density calculates cyclomatic complexity proxy."""
        adapter = JavaScriptLanguageAdapter()
        graph = adapter.parse_repository(self.fixture_repo)

        calc_node = graph.nodes.get("module:src/calculator.js")
        self.assertIsNotNone(calc_node)
        self.assertGreaterEqual(calc_node.facts.get("complexity", 0), 5)

        math_node = graph.nodes.get("module:src/math.js")
        self.assertIsNotNone(math_node)
        self.assertGreaterEqual(math_node.facts.get("complexity", 0), 3)

    def test_ts_optional_property_not_counted_as_branch(self):
        """Verifies TypeScript optional property syntax (?:) is not counted as a ternary branch."""
        adapter = JavaScriptLanguageAdapter()
        with tempfile.TemporaryDirectory() as tmpdir:
            ts_file = os.path.join(tmpdir, "types.ts")
            with open(ts_file, "w", encoding="utf-8") as f:
                f.write(
                    "export interface UserProfile {\n"
                    "  id: string;\n"
                    "  name?: string;\n"
                    "  email?: string;\n"
                    "  avatarUrl?: string;\n"
                    "}\n"
                )

            graph = adapter.parse_repository(tmpdir)
            types_node = graph.nodes.get("module:types.ts")
            self.assertIsNotNone(types_node)
            self.assertEqual(types_node.facts.get("complexity"), 1, "Optional property '?:' must not increase complexity")

    def test_symbol_extraction(self):
        """Verifies top-level named classes and functions are extracted and linked via CONTAINS."""
        adapter = JavaScriptLanguageAdapter()
        graph = adapter.parse_repository(self.fixture_repo)

        self.assertIn("class:src/calculator.js:Calculator", graph.nodes)
        self.assertIn("function:src/math.js:add", graph.nodes)
        self.assertIn("function:src/math.js:divide", graph.nodes)
        self.assertIn("function:src/utils.ts:formatResult", graph.nodes)

        calc_contains = [
            e.target_id for e in graph.edges
            if e.source_id == "module:src/calculator.js" and e.type == SystemEdgeType.CONTAINS
        ]
        self.assertIn("class:src/calculator.js:Calculator", calc_contains)

    def test_prototype_tier_and_confidence(self):
        """Verifies all JS/TS facts and evidence records are explicitly labeled with PROTOTYPE tier and 0.35 confidence."""
        adapter = JavaScriptLanguageAdapter()
        graph = adapter.parse_repository(self.fixture_repo)

        for nid, node in graph.nodes.items():
            if node.type in (SystemNodeType.MODULE, SystemNodeType.TEST):
                self.assertEqual(node.facts.get("tier"), "PROTOTYPE")
                self.assertEqual(node.facts.get("confidence"), 0.35)
                self.assertEqual(node.facts.get("support"), "prototype_regex_ast")

        for eid, ev in graph.evidence.items():
            if ev.type == "AST_FACT":
                self.assertEqual(ev.measurement.get("tier"), "PROTOTYPE")
                self.assertEqual(ev.measurement.get("confidence"), 0.35)

    def test_multi_language_adapter_unification(self):
        """Verifies MultiLanguageAdapter merges Python and JavaScript repos into a single canonical graph."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "server.py"), "w", encoding="utf-8") as f:
                f.write("def serve(): pass\n")
            with open(os.path.join(tmpdir, "client.js"), "w", encoding="utf-8") as f:
                f.write("export function connect() { return true; }\n")

            multi_adapter = MultiLanguageAdapter()
            graph = multi_adapter.parse_repository(tmpdir)

            self.assertIn("module:server.py", graph.nodes)
            self.assertIn("module:client.js", graph.nodes)
            self.assertEqual(graph.nodes["module:server.py"].facts["language"], "python")
            self.assertEqual(graph.nodes["module:client.js"].facts["language"], "javascript")
            self.assertEqual(graph.nodes["module:client.js"].facts["tier"], "PROTOTYPE")

    def test_overview_endpoint_mixed_repo(self):
        """Verifies POST /api/v1/overview reports multi-language file counts and prototype risk labeling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "app.py"), "w", encoding="utf-8") as f:
                f.write("def run_app(): return 1\n")
            with open(os.path.join(tmpdir, "widget.ts"), "w", encoding="utf-8") as f:
                f.write("export function renderWidget(title: string) { if (title) return title; return 'Default'; }\n")

            handler = DummyHandler({"repo": tmpdir})
            UltronAPIHandler.handle_v1_overview(handler)

            self.assertEqual(handler.status_code, 200)
            body = handler.response_body
            self.assertEqual(body.get("status"), "success")
            self.assertEqual(body.get("state"), "ok")

            # Route contract: exactly 8 keys
            expected_keys = ["health", "intent", "memory", "repo", "risks", "state", "stats", "status"]
            self.assertEqual(sorted(list(body.keys())), sorted(expected_keys))

            # Multi-language stats verification
            stats = body.get("stats", {})
            self.assertEqual(stats.get("total_files"), 2)
            self.assertEqual(stats.get("languages"), {"python": 1, "typescript": 1})

            # Risks verification
            risks = body.get("risks", [])
            self.assertEqual(len(risks), 2)
            ts_risk = next((r for r in risks if r.get("file") == "widget.ts"), None)
            self.assertIsNotNone(ts_risk)
            self.assertEqual(ts_risk.get("tier"), "PROTOTYPE")
            self.assertEqual(ts_risk.get("confidence"), 0.35)
            self.assertEqual(ts_risk.get("language"), "typescript")

    def test_syntax_error_and_unreadable_file_resilience(self):
        """Verifies malformed or unreadable files fail gracefully without crashing the adapter."""
        adapter = JavaScriptLanguageAdapter()
        with tempfile.TemporaryDirectory() as tmpdir:
            broken_file = os.path.join(tmpdir, "broken.js")
            with open(broken_file, "w", encoding="utf-8") as f:
                f.write("import { unterminated from './wherever'; function ( {{{")

            graph = adapter.parse_repository(tmpdir)
            self.assertIn("module:broken.js", graph.nodes)
            node = graph.nodes["module:broken.js"]
            self.assertGreaterEqual(node.facts.get("complexity", 0), 1)


if __name__ == "__main__":
    unittest.main()
