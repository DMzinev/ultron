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
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple, Any, Optional, Union

@dataclass
class RouteRecord:
    canonical_path: str
    methods: List[str]
    handler_func: Callable[[Any], None]
    aliases: List[str] = field(default_factory=list)
    module_name: str = "core"

    def to_dict(self) -> dict:
        return {
            "canonical_path": self.canonical_path,
            "methods": sorted(list(self.methods)),
            "aliases": sorted(list(self.aliases)),
            "handler": getattr(self.handler_func, "__name__", str(self.handler_func)),
            "module": self.module_name
        }


class APIRouter:
    _routes: Dict[Tuple[str, str], Callable[[Any], None]] = {}
    _records: Dict[str, RouteRecord] = {}

    @classmethod
    def register(cls, path: str, method: Union[str, List[str]] = "GET", aliases: Optional[List[str]] = None) -> Callable:
        """Decorator to register an API endpoint handler with optional multi-method and alias support."""
        methods = [method.upper()] if isinstance(method, str) else [m.upper() for m in method]
        alias_list = aliases or []

        def decorator(func: Callable[[Any], None]) -> Callable[[Any], None]:
            cls.add_route(path, methods, func, aliases=alias_list)
            return func
        return decorator

    @classmethod
    def add_route(cls, path: str, method: Union[str, List[str]], handler_func: Callable[[Any], None], aliases: Optional[List[str]] = None) -> None:
        """Programmatically registers a route handler function."""
        methods = [method.upper()] if isinstance(method, str) else [m.upper() for m in method]
        alias_list = aliases or []
        norm_canonical = path.lower().rstrip('/') or "/"

        rec = cls._records.get(norm_canonical)
        if not rec:
            rec = RouteRecord(
                canonical_path=path,
                methods=methods,
                handler_func=handler_func,
                aliases=alias_list,
                module_name=getattr(handler_func, "__module__", "core")
            )
            cls._records[norm_canonical] = rec
        else:
            for m in methods:
                if m not in rec.methods:
                    rec.methods.append(m)
            for a in alias_list:
                if a not in rec.aliases:
                    rec.aliases.append(a)

        all_paths = [path] + alias_list
        for p in all_paths:
            norm_p = p.lower().rstrip('/') or "/"
            for m in methods:
                cls._routes[(norm_p, m)] = handler_func

    @classmethod
    def list_routes(cls) -> List[dict]:
        """Returns all registered route records as inspectable dictionaries."""
        return [rec.to_dict() for rec in cls._records.values()]

    @classmethod
    def dispatch(cls, http_handler: Any, parsed_path: str, method: str) -> bool:
        """
        Dispatches request to registered handler.
        Returns True if route matched and executed, False if route not found.
        Includes exact path matching and header-aware exception boundaries.
        """
        norm_path = parsed_path.lower().rstrip('/') or "/"
        req_method = method.upper()

        key = (norm_path, req_method)
        handler_func = cls._routes.get(key)

        # Explicit wildcard match fallback (strictly for paths registered with trailing '/*')
        if not handler_func:
            for (r_path, r_method), func in cls._routes.items():
                if r_method == req_method and r_path.endswith("/*"):
                    prefix = r_path[:-2]
                    if norm_path == prefix or norm_path.startswith(prefix + "/"):
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
            # Header-aware exception boundary check to prevent duplicate header corruption
            headers_sent = getattr(http_handler, 'headers_sent', False) or (getattr(http_handler, '_headers_buffer', None) is not None and len(getattr(http_handler, '_headers_buffer', [])) > 0)
            if not headers_sent:
                try:
                    http_handler.send_response(500)
                    http_handler.send_header("Content-Type", "application/json; charset=utf-8")
                    http_handler.end_headers()
                    http_handler.wfile.write(json.dumps(payload).encode("utf-8"))
                except Exception as write_err:
                    sys.stderr.write(f"[Ultron Router Envelope Write Fail] {write_err}\n")
            return True


# Helper shortcut
router = APIRouter

