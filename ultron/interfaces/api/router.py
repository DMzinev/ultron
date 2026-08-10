"""
Ultron REST API — Extensible Modular Router & Dynamic Dispatcher
Campaign 26 — Modular Route Registry, Exception Boundaries & Extensible Endpoint Architecture
"""

import sys
import os
import json
import uuid
import traceback
from datetime import datetime, timezone
from typing import Callable, Dict, Tuple, Any, Optional

class APIRouter:
    _routes: Dict[Tuple[str, str], Callable[[Any], None]] = {}

    @classmethod
    def register(cls, path: str, method: str = "GET") -> Callable:
        """Decorator to register an API endpoint handler."""
        def decorator(func: Callable[[Any], None]) -> Callable[[Any], None]:
            cls._routes[(path.lower(), method.upper())] = func
            return func
        return decorator

    @classmethod
    def add_route(cls, path: str, method: str, handler_func: Callable[[Any], None]) -> None:
        """Programmatically registers a route handler function."""
        cls._routes[(path.lower(), method.upper())] = handler_func

    @classmethod
    def dispatch(cls, http_handler: Any, parsed_path: str, method: str) -> bool:
        """
        Dispatches request to registered handler.
        Returns True if route matched and executed, False if route not found.
        Includes full defensive exception boundary returning clean JSON error envelopes.
        """
        norm_path = parsed_path.lower().rstrip('/')
        if not norm_path:
            norm_path = "/"
            
        key = (norm_path, method.upper())
        handler_func = cls._routes.get(key)
        
        # Prefix / wildcard match fallback if exact match fails
        if not handler_func:
            for (r_path, r_method), func in cls._routes.items():
                if r_method == method.upper() and norm_path.startswith(r_path):
                    handler_func = func
                    break

        if not handler_func:
            return False

        try:
            handler_func(http_handler)
            return True
        except Exception as err:
            sys.stderr.write(f"[Ultron Router Error] [{method} {parsed_path}] {err}\n")
            req_id = f"req-{uuid.uuid4().hex[:8]}"
            payload = {
                "success": False,
                "data": None,
                "error": f"Internal Endpoint Error: {str(err)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": req_id
            }
            try:
                http_handler.send_response(500)
                http_handler.send_header("Content-Type", "application/json; charset=utf-8")
                http_handler.end_headers()
                http_handler.wfile.write(json.dumps(payload).encode("utf-8"))
            except Exception:
                pass
            return True

# Helper shortcut
router = APIRouter
