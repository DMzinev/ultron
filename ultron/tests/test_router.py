"""
Ultron Unit Tests for APIRouter Extensible Route Dispatcher
"""
import unittest
from unittest.mock import MagicMock
from ultron.interfaces.api.router import APIRouter

class TestAPIRouter(unittest.TestCase):
    def setUp(self):
        APIRouter._routes.clear()

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

    def test_exception_boundary_returns_clean_envelope(self):
        mock_handler = MagicMock()
        mock_handler.wfile = MagicMock()

        @APIRouter.register("/api/v1/failing", "POST")
        def failing_route(h):
            raise ValueError("Deliberate failure in route")

        handled = APIRouter.dispatch(mock_handler, "/api/v1/failing", "POST")
        self.assertTrue(handled)
        mock_handler.send_response.assert_called_with(500)

if __name__ == "__main__":
    unittest.main()
