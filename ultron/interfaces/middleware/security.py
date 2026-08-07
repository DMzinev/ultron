"""
Ultron Security & Authentication Middleware
Campaign 21 — Token Authorization & Rate Limiting Guards
"""

import time
import os
import sys
from typing import Dict, Tuple, Optional

class SecurityMiddleware:
    _LAST_REQUEST_TIMESTAMPS: Dict[str, float] = {}
    _REQUEST_COUNTS: Dict[str, int] = {}
    _MAX_REQUESTS_PER_SEC = 20

    @classmethod
    def check_rate_limit(cls, client_ip: str = "127.0.0.1") -> Tuple[bool, Optional[str]]:
        """Guards against rapid request flooding (max 20 requests / sec)."""
        now = time.time()
        last_time = cls._LAST_REQUEST_TIMESTAMPS.get(client_ip, 0.0)

        if now - last_time < 1.0:
            count = cls._REQUEST_COUNTS.get(client_ip, 0) + 1
            cls._REQUEST_COUNTS[client_ip] = count
            if count > cls._MAX_REQUESTS_PER_SEC:
                return False, "Rate limit exceeded (max 20 requests/sec)."
        else:
            cls._LAST_REQUEST_TIMESTAMPS[client_ip] = now
            cls._REQUEST_COUNTS[client_ip] = 1

        return True, None

    @classmethod
    def validate_request(cls, handler_headers: dict, client_ip: str = "127.0.0.1") -> Tuple[bool, Optional[str]]:
        """Validates rate limits and optional auth headers."""
        ok, msg = cls.check_rate_limit(client_ip)
        if not ok:
            return False, msg

        # Token validation is active if ULTRON_API_TOKEN environment variable is configured
        required_token = os.environ.get("ULTRON_API_TOKEN")
        if required_token:
            auth_header = handler_headers.get("Authorization", "")
            if not auth_header.endswith(required_token):
                return False, "Unauthorized: Invalid or missing API token."

        return True, None
