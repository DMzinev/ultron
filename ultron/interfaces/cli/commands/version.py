"""
ultron.interfaces.cli.commands.version
Dedicated Version CLI Command Handler.
"""

import os
import sys
import json
import argparse
from importlib.util import find_spec
from typing import Dict, Any, List, Optional

import ultron
from ultron import get_version


def _probe(name: str) -> bool:
    """Return True if an optional module is discoverable without importing it."""
    try:
        return find_spec(name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def get_version_info() -> Dict[str, Any]:
    """Compiles structured version and capability diagnostic info."""
    pkg_path = os.path.dirname(os.path.abspath(ultron.__file__))
    return {
        "version": get_version(),
        "python": sys.version,
        "path": pkg_path,
        "capabilities": {
            "radon": _probe("radon"),
            "pystray": _probe("pystray"),
            "pillow": _probe("PIL"),
        },
        "schema_version": "1.0.0",
    }


def run_version_command(argv: Optional[List[str]] = None) -> int:
    """
    Executes 'ultron version'.
    Strictly parses arguments using parse_args (rejecting unknown options).
    Supports --json and --help.
    """
    if argv is None:
        argv = sys.argv[2:] if (len(sys.argv) > 1 and sys.argv[1] == "version") else []

    parser = argparse.ArgumentParser(
        prog="ultron version",
        description="Display Ultron version and environment capabilities.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output machine-readable JSON format",
    )
    args = parser.parse_args(argv)

    if args.json:
        info = get_version_info()
        print(json.dumps(info, indent=2))
    else:
        print(f"ultron {get_version()}")
    return 0
