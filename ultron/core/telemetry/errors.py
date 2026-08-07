"""
Ultron Error Intelligence & Diagnostics Engine
Campaign 19 — Error Classification, Diagnostic Envelopes & Recovery Guidance
"""

import sys
import traceback
from typing import Dict, Any, Optional

class ErrorCategory:
    SYNTAX_ERROR = "SYNTAX_ERROR"
    PATH_ERROR = "PATH_ERROR"
    FILE_SYSTEM_ERROR = "FILE_SYSTEM_ERROR"
    TIMEOUT = "TIMEOUT"
    MALFORMED_INPUT = "MALFORMED_INPUT"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNKNOWN = "UNKNOWN"

class ErrorDiagnostics:
    @staticmethod
    def classify_exception(err: Exception) -> str:
        if isinstance(err, SyntaxError):
            return ErrorCategory.SYNTAX_ERROR
        elif isinstance(err, (FileNotFoundError, OSError)):
            return ErrorCategory.FILE_SYSTEM_ERROR
        elif isinstance(err, (ValueError, KeyError, TypeError)):
            return ErrorCategory.MALFORMED_INPUT
        elif isinstance(err, TimeoutError):
            return ErrorCategory.TIMEOUT
        return ErrorCategory.UNKNOWN

    @staticmethod
    def get_recovery_suggestion(category: str, detail: str = "") -> str:
        if category == ErrorCategory.SYNTAX_ERROR:
            return "Verify Python syntax in target file or add to .ultronignore."
        elif category == ErrorCategory.FILE_SYSTEM_ERROR:
            return "Check directory permissions and verify target path exists."
        elif category == ErrorCategory.MALFORMED_INPUT:
            return "Verify API request payload format and parameters."
        elif category == ErrorCategory.TIMEOUT:
            return "Operation timed out. Try analyzing a smaller sub-directory."
        elif category == ErrorCategory.UNAUTHORIZED:
            return "Provide a valid Ultron API auth token header."
        return "Review server logs in .ultron/server.log for details."

    @classmethod
    def format_error_envelope(cls, err_msg: str, err: Optional[Exception] = None, operation: str = "General") -> Dict[str, Any]:
        category = cls.classify_exception(err) if err else ErrorCategory.UNKNOWN
        suggestion = cls.get_recovery_suggestion(category, err_msg)
        
        # Log to stderr defensively
        sys.stderr.write(f"[Ultron Error Diagnostics] [{operation}] {category}: {err_msg}\n")
        
        return {
            "error": err_msg, # Backward-compatible top-level string key
            "diagnostics": {
                "category": category,
                "operation": operation,
                "message": err_msg,
                "recovery_suggestion": suggestion
            }
        }
