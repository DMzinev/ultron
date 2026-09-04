"""
ultron.core.adaptive_verifier
Deterministic Delta Debugging (ddmin) Minimal Reproduction Shrinker & Parameter Boundary Explorer.

Design Constraints (Phase 1.6 Refinement):
- Kept deliberately lean and reproduction-focused (not a speculative universal fuzzer).
- Focused on: strings, file paths, JSON/API payloads, repository selection inputs, mission inputs.
- Objective: Failure -> Minimal reproducible input -> Issue memory -> Permanent regression guard.
"""

from __future__ import annotations

import os
import re
import sys
import json
from typing import Callable, List, Any, Dict, Optional, Union


def _safe_test_predicate(predicate: Callable[[str], bool], candidate: str) -> bool:
    """Executes predicate safely; returns False on any exception."""
    if not callable(predicate):
        return False
    try:
        return bool(predicate(candidate))
    except Exception:
        return False


def _extract_chunks(current: str, n: int) -> List[str]:
    """Divides string current into n deterministic chunks."""
    step = len(current) / n
    return [current[int(i * step):int((i + 1) * step)] for i in range(n)]


def _try_reduction(predicate: Callable[[str], bool], current: str, chunks: List[str]) -> Optional[str]:
    """Evaluates individual chunks and complements to find a smaller failing candidate."""
    # 1. Try single chunks (sub-parts)
    for chunk in chunks:
        if chunk and chunk != current and _safe_test_predicate(predicate, chunk):
            return chunk

    # 2. Try complements (everything except one chunk)
    for i in range(len(chunks)):
        complement = "".join(chunks[:i] + chunks[i + 1:])
        if complement and complement != current and _safe_test_predicate(predicate, complement):
            return complement

    return None


def ddmin_shrink(
    predicate: Callable[[str], bool],
    failing_input: Optional[str],
    max_iterations: int = 1000
) -> str:
    """
    Deterministic Delta Debugging (ddmin) minimal reproduction algorithm.
    Bisects the failing input string to find the 1-minimal substring that still triggers predicate(c) == True.
    """
    if failing_input is None:
        return ""

    if not isinstance(failing_input, str):
        failing_input = str(failing_input)

    if not failing_input:
        return ""

    if not callable(predicate):
        return failing_input

    # 0-minimal check (empty string failure)
    if _safe_test_predicate(predicate, ""):
        return ""

    # Baseline failure check
    if not _safe_test_predicate(predicate, failing_input):
        return failing_input

    n = 2
    current = failing_input
    iterations = 0

    while len(current) >= 2 and iterations < max_iterations:
        iterations += 1
        n = min(n, len(current))
        chunks = _extract_chunks(current, n)
        candidate = _try_reduction(predicate, current, chunks)

        if candidate is not None:
            current = candidate
            n = 2
        else:
            if n < len(current):
                n = min(len(current), n * 2)
            else:
                break

    return current


class AdaptiveBoundaryVerifier:
    """
    Lightweight parameter boundary explorer and reproduction shrinker.
    Provides canonical test vectors for security boundaries and parameter fuzzing.
    """

    BOUNDARY_MUTATIONS: Dict[str, List[Any]] = {
        "path": [
            "",
            " ",
            None,
            ".",
            "..",
            "nonexistent_dir_9999",
            "C:\\",
            "/dev/null",
            "./../sibling_escape",
            "../../../../../../etc/shadow",
            "..\\..\\..\\windows\\win.ini",
            "invalid\x00path",
            "path with spaces/file.py",
            "long_path_" + ("nested/" * 25) + "file.py"
        ],
        "string": [
            "",
            " ",
            "\t\n\r",
            None,
            "\x00",
            "<script>alert(1)</script>",
            "' OR '1'='1",
            "'; DROP TABLE rkm_files; --",
            "; rm -rf / ;",
            "| cat /etc/passwd",
            "$(whoami)",
            "`id`",
            "%HOMEPATH%",
            "🚀🔥✨",
            "A" * 1024
        ],
        "json": [
            "",
            " ",
            None,
            "{}",
            "[]",
            "null",
            "true",
            "false",
            "123",
            '{"unclosed": ',
            '{"null_key": null}',
            '{"nested": {"depth": {"value": 1}}}',
            '{"__proto__": {"polluted": true}}'
        ],
        "file_list": [
            [],
            [""],
            [None],
            ["nonexistent.py"],
            ["a.py", "a.py"],
            ["../escape.py"],
            ["../../../../etc/passwd"]
        ],
        "repo_input": [
            "",
            " ",
            None,
            "/nonexistent/repo/dir",
            "./../parent_escape",
            "C:\\Windows\\System32"
        ],
        "mission_input": [
            "",
            " ",
            None,
            {},
            {"prompt": ""},
            {"prompt": None},
            {"options": None}
        ],
        "number": [
            None,
            0,
            -1,
            1,
            999999,
            float("nan"),
            float("inf")
        ]
    }

    CATEGORY_ALIASES: Dict[str, str] = {
        "filepath": "path",
        "file_path": "path",
        "str": "string",
        "text": "string",
        "payload": "json",
        "files": "file_list",
        "repo": "repo_input",
        "mission": "mission_input",
        "int": "number",
        "integer": "number"
    }

    _TRAVERSAL_PATTERN = re.compile(r"(\.\.[/\\])|(%2e%2e)|(\x00)|([/\\]\.\.)", re.IGNORECASE)
    _SHELL_INJECTION_PATTERN = re.compile(r"[;&|`$><]", re.IGNORECASE)

    @classmethod
    def generate_boundary_variants(cls, param_type: Optional[str]) -> List[Any]:
        """Returns standard boundary exploration variants for a given parameter class."""
        if not param_type or not isinstance(param_type, str):
            return ["", None, "test"]

        norm_key = param_type.lower().strip()
        canonical_key = cls.CATEGORY_ALIASES.get(norm_key, norm_key)
        variants = cls.BOUNDARY_MUTATIONS.get(canonical_key)
        if variants is not None:
            return list(variants)
        return ["", None, "test"]

    @classmethod
    def shrink_reproduction(cls, predicate: Callable[[str], bool], initial_failure: Optional[str]) -> str:
        """Shrinks a failing reproduction string down to its minimal reproducible core."""
        return ddmin_shrink(predicate, initial_failure)

    @classmethod
    def is_path_traversal(cls, path: Any) -> bool:
        """Detects if a path string attempts directory traversal or null-byte injection."""
        if not path or not isinstance(path, str):
            return False
        return bool(cls._TRAVERSAL_PATTERN.search(path))

    @classmethod
    def is_shell_injection(cls, value: Any) -> bool:
        """Detects common shell injection metacharacters in input strings."""
        if not value or not isinstance(value, str):
            return False
        return bool(cls._SHELL_INJECTION_PATTERN.search(value))

    @classmethod
    def safe_str(cls, value: Any, default: str = "") -> str:
        """Converts any value to a sanitized string with null bytes stripped."""
        if value is None:
            return default
        try:
            return str(value).replace("\x00", "")
        except Exception:
            return default
