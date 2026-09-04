"""
ultron.release.version_manager — Granular Continuous Versioning & Micro-Sprint Engine.
"""

import re
from typing import Tuple
from ultron.release import __version__ as CANONICAL_VERSION

_SEMVER_REGEX = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")

class VersionManager:
    """Stateless utility engine for semantic micro-sprint version operations."""

    @staticmethod
    def get_canonical_version() -> str:
        """Returns the canonical package version constant."""
        return CANONICAL_VERSION

    @staticmethod
    def parse_version(version_str: str) -> Tuple[int, int, int, str, bool]:
        """
        Parses a semver string into (major, minor, micro, pre_release, has_v_prefix).
        Raises ValueError on malformed input.
        """
        if not version_str or not isinstance(version_str, str):
            raise ValueError("Version string must be a non-empty string.")
        
        cleaned = version_str.strip()
        has_v = cleaned.startswith("v") or cleaned.startswith("V")
        match = _SEMVER_REGEX.match(cleaned)
        if not match:
            raise ValueError(f"Invalid semver version string: '{version_str}'")
        
        major, minor, micro, pre = match.groups()
        return int(major), int(minor), int(micro), pre or "", has_v

    @staticmethod
    def increment_micro(version_str: str, amount: int = 1) -> str:
        """
        Increments the micro version by `amount` (default 1).
        Preserves leading 'v' prefix if present.
        Example: '0.1.0' + 1 -> '0.1.1', 'v0.1.9' + 1 -> 'v0.1.10'.
        """
        if amount <= 0:
            raise ValueError("Increment amount must be a positive integer.")

        major, minor, micro, pre, has_v = VersionManager.parse_version(version_str)
        new_micro = micro + amount
        prefix = "v" if has_v else ""
        suffix = f"-{pre}" if pre else ""
        return f"{prefix}{major}.{minor}.{new_micro}{suffix}"

    @staticmethod
    def format_sprint_tag(version_str: str, sprint_name: str) -> str:
        """Formats a micro-sprint tag for release tracking."""
        if not sprint_name or not isinstance(sprint_name, str):
            raise ValueError("Sprint name must be a non-empty string.")
        version = version_str.strip()
        if not version.startswith("v") and not version.startswith("V"):
            version = f"v{version}"
        clean_sprint = re.sub(r"[^\w\.-]", "-", sprint_name.strip().lower())
        return f"{version}-{clean_sprint}"
