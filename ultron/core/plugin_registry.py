"""
Ultron Core — Modular Analytical Plugin Registry
Campaign 27 — Zero-Impact Extensibility, Dynamic Analysis Passes & Core Hardening
"""

import sys
import logging
from typing import Callable, Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class AnalysisPluginRegistry:
    _plugins: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    @classmethod
    def register_plugin(cls, name: str, plugin_func: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        """Registers a custom analytical inspection plugin pass."""
        cls._plugins[name] = plugin_func
        logger.info("[Plugin Registry] Registered analysis pass: '%s'", name)

    @classmethod
    def run_all_plugins(cls, codebase_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes all registered analysis plugins over codebase AST context.
        Returns aggregated plugin metrics dictionary.
        """
        results: Dict[str, Any] = {}
        for name, plugin_func in cls._plugins.items():
            try:
                pass_res = plugin_func(codebase_context)
                if isinstance(pass_res, dict):
                    results[name] = pass_res
            except Exception as err:
                logger.warning("[Plugin Warning] Analysis pass '%s' failed: %s", name, err)
                results[name] = {"status": "failed", "error": str(err)}
        return results

    @classmethod
    def clear(cls) -> None:
        """Clears all registered plugins (for unit testing)."""
        cls._plugins.clear()
