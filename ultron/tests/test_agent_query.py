"""
Ultron Unit Tests — Engineering Intelligence Query Protocol & Endpoint Tests
Campaign 34 / v2.6 — agent_routes.py Unit & Boundary Verification
"""

import json
import unittest
from typing import Dict, Any

from ultron.interfaces.api.router import APIRouter
from ultron.core.system_model import SystemModelManager, SystemNode, SystemNodeType, SystemEdge, SystemEdgeType, EvidenceObject
import ultron.interfaces.api.routes.agent_routes as agent_routes
from ultron.interfaces.api.routes.system_routes import _GLOBAL_MODEL_MANAGERS


class DummyHandler:
    def __init__(self, post_data: Dict[str, Any], query_string: str = ""):
        self.post_data = post_data
        self.query_string = query_string
        self.response_code = 0
        self.headers: Dict[str, str] = {}
        self.output_bytes = b""
        self.server = self
        self.current_repo_path = "."

    def get_post_data(self) -> Dict[str, Any]:
        return self.post_data

    def send_response(self, code: int):
        self.response_code = code

    def send_header(self, keyword: str, value: str):
        self.headers[keyword] = value

    def end_headers(self):
        pass

    @property
    def wfile(self):
        class WFile:
            def __init__(self, outer):
                self.outer = outer
            def write(self, b: bytes):
                self.outer.output_bytes += b
        return WFile(self)


class TestAgentQueryProtocol(unittest.TestCase):

    def setUp(self):
        # Build test system graph
        mgr = SystemModelManager()
        mod_node = SystemNode(id="module:ultron/core/system_model.py", type=SystemNodeType.MODULE, file_path="ultron/core/system_model.py")
        dep_node = SystemNode(id="module:ultron/core/git_adapter.py", type=SystemNodeType.MODULE, file_path="ultron/core/git_adapter.py")
        test_node = SystemNode(id="module:ultron/tests/test_system_model.py", type=SystemNodeType.TEST, file_path="ultron/tests/test_system_model.py")

        ev = EvidenceObject(
            id="ev_001",
            type="AST_FACT",
            subject_id="module:ultron/core/system_model.py",
            measurement={"total_functions": 12},
            source={"adapter": "python"}
        )

        mgr.add_node(mod_node)
        mgr.add_node(dep_node)
        mgr.add_node(test_node)
        mgr.add_edge(SystemEdge(source_id="module:ultron/core/system_model.py", target_id="module:ultron/core/git_adapter.py", type=SystemEdgeType.IMPORTS))
        mgr.add_edge(SystemEdge(source_id="module:ultron/tests/test_system_model.py", target_id="module:ultron/core/system_model.py", type=SystemEdgeType.TESTS))
        mgr.add_evidence(ev)

        # Set global model cache for route handlers
        import os
        import ultron.interfaces.api.routes.system_routes as sys_routes
        norm_path = os.path.normcase(os.path.abspath(".")).replace("\\", "/")
        sys_routes._GLOBAL_MODEL_MANAGERS[norm_path] = mgr

    def test_supported_query_types(self):
        query_types = [
            "IMPACT_ANALYSIS", "DEPENDENCIES", "DEPENDENTS",
            "CALLERS", "TEST_COVERAGE", "RISK_EXPLANATION", "CHANGE_CONTEXT"
        ]

        for qt in query_types:
            handler = DummyHandler({"query_type": qt, "target_entity": "ultron/core/system_model.py"})
            matched = APIRouter.dispatch(handler, "/api/v1/agent/context/query", "POST")
            self.assertTrue(matched, f"Route /api/v1/agent/context/query POST must match for {qt}")

            self.assertEqual(handler.response_code, 200, f"Query type {qt} failed with code {handler.response_code}")
            res = json.loads(handler.output_bytes.decode("utf-8"))
            self.assertTrue(res["success"])
            self.assertEqual(res["data"]["query_type"], qt)
            self.assertIn("model_hash", res["data"])
            self.assertIn("snapshot_id", res["data"])
            self.assertIsInstance(res["data"]["nodes"], list)
            self.assertIsInstance(res["data"]["edges"], list)
            self.assertIsInstance(res["data"]["evidence"], list)

    def test_missing_query_type(self):
        handler = DummyHandler({"target_entity": "ultron/core/system_model.py"})
        matched = APIRouter.dispatch(handler, "/api/v1/agent/context/query", "POST")
        self.assertTrue(matched)

        self.assertEqual(handler.response_code, 400)
        res = json.loads(handler.output_bytes.decode("utf-8"))
        self.assertFalse(res["success"])
        self.assertIn("Supported types", res["error"])

    def test_invalid_query_type(self):
        handler = DummyHandler({"query_type": "UNKNOWN_QUERY", "target_entity": "ultron/core/system_model.py"})
        matched = APIRouter.dispatch(handler, "/api/v1/agent/context/query", "POST")
        self.assertTrue(matched)

        self.assertEqual(handler.response_code, 400)
        res = json.loads(handler.output_bytes.decode("utf-8"))
        self.assertFalse(res["success"])

    def test_missing_target_entity(self):
        handler = DummyHandler({"query_type": "IMPACT_ANALYSIS"})
        matched = APIRouter.dispatch(handler, "/api/v1/agent/context/query", "POST")
        self.assertTrue(matched)

        self.assertEqual(handler.response_code, 400)
        res = json.loads(handler.output_bytes.decode("utf-8"))
        self.assertFalse(res["success"])

    def test_nonexistent_target_entity(self):
        handler = DummyHandler({"query_type": "IMPACT_ANALYSIS", "target_entity": "nonexistent_file.py"})
        matched = APIRouter.dispatch(handler, "/api/v1/agent/context/query", "POST")
        self.assertTrue(matched)

        self.assertEqual(handler.response_code, 404)
        res = json.loads(handler.output_bytes.decode("utf-8"))
        self.assertFalse(res["success"])
    def test_schema_completeness_and_determinism(self):
        """Asserts all 7 required query protocol schema keys are present and non-null."""
        handler = DummyHandler({"query_type": "IMPACT_ANALYSIS", "target_entity": "ultron/core/system_model.py"})
        matched = APIRouter.dispatch(handler, "/api/v1/agent/context/query", "POST")
        self.assertTrue(matched)
        self.assertEqual(handler.response_code, 200)

        res = json.loads(handler.output_bytes.decode("utf-8"))
        self.assertTrue(res["success"])
        data = res["data"]

        required_keys = ["query_type", "model_hash", "snapshot_id", "nodes", "edges", "evidence", "telemetry"]
        for key in required_keys:
            self.assertIn(key, data, f"Key '{key}' must be present in query response data")
            self.assertIsNotNone(data[key], f"Key '{key}' must not be None")

        telemetry = data["telemetry"]
        self.assertIn("node_count", telemetry)
        self.assertIn("edge_count", telemetry)
        self.assertIn("evidence_count", telemetry)
        self.assertIn("query_depth", telemetry)

    def test_canonical_serialization_determinism(self):
        """Asserts multiple identical query calls produce byte-for-byte identical output and sorted lists."""
        handler1 = DummyHandler({"query_type": "IMPACT_ANALYSIS", "target_entity": "ultron/core/system_model.py"})
        APIRouter.dispatch(handler1, "/api/v1/agent/context/query", "POST")

        handler2 = DummyHandler({"query_type": "IMPACT_ANALYSIS", "target_entity": "ultron/core/system_model.py"})
        APIRouter.dispatch(handler2, "/api/v1/agent/context/query", "POST")

        self.assertEqual(handler1.output_bytes, handler2.output_bytes, "Query outputs must be byte-for-byte identical")

        data = json.loads(handler1.output_bytes.decode("utf-8"))["data"]
        node_ids = [n["id"] for n in data["nodes"]]
        self.assertEqual(node_ids, sorted(node_ids), "Nodes list must be canonically sorted by id")


if __name__ == "__main__":
    unittest.main()
