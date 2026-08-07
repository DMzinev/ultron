"""
Ultron Unit Tests for Security Middleware
"""
import unittest
import os
from ultron.interfaces.middleware.security import SecurityMiddleware

class TestSecurityMiddleware(unittest.TestCase):
    def test_rate_limiting_passes_under_threshold(self):
        ok, msg = SecurityMiddleware.check_rate_limit("127.0.0.1")
        self.assertTrue(ok)
        self.assertIsNone(msg)

    def test_rate_limiting_blocks_overflow(self):
        import time
        SecurityMiddleware._LAST_REQUEST_TIMESTAMPS["10.0.0.1"] = time.time()
        SecurityMiddleware._REQUEST_COUNTS["10.0.0.1"] = 25
        ok, msg = SecurityMiddleware.check_rate_limit("10.0.0.1")
        self.assertFalse(ok)
        self.assertIn("Rate limit exceeded", msg)

    def test_auth_token_validation(self):
        os.environ["ULTRON_API_TOKEN"] = "test-secret-token"
        try:
            # Missing header -> fail
            ok, msg = SecurityMiddleware.validate_request({}, "127.0.0.2")
            self.assertFalse(ok)
            self.assertIn("Unauthorized", msg)

            # Valid header -> pass
            ok, msg = SecurityMiddleware.validate_request({"Authorization": "Bearer test-secret-token"}, "127.0.0.2")
            self.assertTrue(ok)
        finally:
            del os.environ["ULTRON_API_TOKEN"]

if __name__ == "__main__":
    unittest.main()
