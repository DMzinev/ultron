"""
Ultron Unit Tests for APIRouter Extensible Route Dispatcher
"""
import unittest
from unittest.mock import MagicMock
from ultron.interfaces.api.router import APIRouter, RouteRecord

class TestAPIRouter(unittest.TestCase):
    def setUp(self):
        self._initial_routes = dict(APIRouter._routes)
        self._initial_records = dict(APIRouter._records)

    def tearDown(self):
        APIRouter._routes.clear()
        APIRouter._routes.update(self._initial_routes)
        APIRouter._records.clear()
        APIRouter._records.update(self._initial_records)

    def test_register_and_dispatch_success(self):
        mock_handler = MagicMock()
        
        @APIRouter.register("/api/v1/test", "GET")
        def sample_route(h):
            h.called = True

        handled = APIRouter.dispatch(mock_handler, "/api/v1/test", "GET")
        self.assertTrue(handled)
        self.assertTrue(mock_handler.called)

    def test_dispatch_unmatched_route_returns_false(self):
        mock_handler = MagicMock()
        handled = APIRouter.dispatch(mock_handler, "/api/v1/nonexistent", "GET")
        self.assertFalse(handled)

    def test_exact_path_matching_no_prefix_leakage(self):
        mock_handler = MagicMock()
        
        @APIRouter.register("/api/v1/analyze", "POST")
        def analyze_route(h):
            h.route = "analyze"

        # /api/v1/analyze_summary should NOT match /api/v1/analyze
        handled = APIRouter.dispatch(mock_handler, "/api/v1/analyze_summary", "POST")
        self.assertFalse(handled)

        handled_exact = APIRouter.dispatch(mock_handler, "/api/v1/analyze", "POST")
        self.assertTrue(handled_exact)
        self.assertEqual(mock_handler.route, "analyze")

    def test_multi_method_and_alias_registration(self):
        mock_handler = MagicMock()

        @APIRouter.register("/api/v1/file-tree", method=["GET", "POST"], aliases=["/api/file-tree"])
        def file_tree_route(h):
            h.called = True

        self.assertTrue(APIRouter.dispatch(mock_handler, "/api/v1/file-tree", "GET"))
        self.assertTrue(APIRouter.dispatch(mock_handler, "/api/v1/file-tree", "POST"))
        self.assertTrue(APIRouter.dispatch(mock_handler, "/api/file-tree", "GET"))
        self.assertTrue(APIRouter.dispatch(mock_handler, "/api/file-tree", "POST"))

    def test_route_record_list_routes_introspection(self):
        @APIRouter.register("/api/v1/audit", method="POST", aliases=["/api/audit"])
        def audit_route(h):
            pass

        routes = APIRouter.list_routes()
        self.assertGreaterEqual(len(routes), 1)
        audit_rec = next(r for r in routes if r["canonical_path"] == "/api/v1/audit")
        self.assertIn("POST", audit_rec["methods"])
        self.assertIn("/api/audit", audit_rec["aliases"])

    def test_exception_boundary_returns_clean_envelope(self):
        mock_handler = MagicMock()
        mock_handler.headers_sent = False
        mock_handler.wfile = MagicMock()

        @APIRouter.register("/api/v1/failing", "POST")
        def failing_route(h):
            raise ValueError("Deliberate failure in route")

        handled = APIRouter.dispatch(mock_handler, "/api/v1/failing", "POST")
        self.assertTrue(handled)
        mock_handler.send_response.assert_called_with(500)

    def test_header_aware_exception_boundary_prevents_duplicate_headers(self):
        mock_handler = MagicMock()
        mock_handler.headers_sent = True  # Headers already sent!
        mock_handler.wfile = MagicMock()

        @APIRouter.register("/api/v1/failing_midstream", "GET")
        def failing_midstream_route(h):
            raise RuntimeError("Failure after headers sent")

        handled = APIRouter.dispatch(mock_handler, "/api/v1/failing_midstream", "GET")
        self.assertTrue(handled)
        # send_response should NOT be called since headers were already sent
        mock_handler.send_response.assert_not_called()

if __name__ == "__main__":
    unittest.main()

