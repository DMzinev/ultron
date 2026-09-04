"""
Mixed repository fixture - Genuinely risky dispatcher module.
High cyclomatic complexity and wide fan-out.
"""
from .risky_core import RiskyCoreEngine
from .formatters import format_currency, format_status
from .helpers import clean_string, sanitize_dict
from .logger import log_event
from .exceptions import DispatchError


class RiskyDispatcher:
    def __init__(self):
        self.engine = RiskyCoreEngine()

    def route_request(self, command, payload, ctx):
        if not command:
            raise DispatchError("Empty command")

        if command == "PROCESS":
            if ctx.get("role") == "admin":
                return self.engine.process_batch(payload.get("batches", []))
            elif ctx.get("role") == "user":
                if payload.get("restricted"):
                    raise DispatchError("Access denied")
                return self.engine.evaluate_transaction(
                    payload.get("id"), payload.get("records", []), {}, {}
                )
            else:
                log_event("WARN", "Unknown role")
                return None
        elif command == "AUDIT":
            records = payload.get("records", [])
            flagged = []
            for r in records:
                s = r.get("status")
                if s == "flagged":
                    flagged.append(format_status(s))
                elif s == "suspect":
                    if r.get("score", 0) > 80:
                        flagged.append("HIGH_RISK")
                    elif r.get("score", 0) > 50:
                        flagged.append("MED_RISK")
                    else:
                        flagged.append("LOW_RISK")
                elif s == "unknown":
                    flagged.append("REVIEW")
            return flagged
        elif command == "EXPORT":
            if not payload:
                return ""
            mode = ctx.get("format", "csv")
            if mode == "csv":
                return ",".join([str(x) for x in payload.get("data", [])])
            elif mode == "json":
                return sanitize_dict(payload)
            else:
                return clean_string(str(payload))
        else:
            raise DispatchError(f"Unknown command: {command}")
