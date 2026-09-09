#!/usr/bin/env python3
"""
scripts/verify.py
Standalone Master Verification Script (Single Source of Truth).

Discovers and executes all tests in the repository.
Outputs:
    TESTS: <n> ran, <f> failed, <e> errors, <s> skipped
Exits with code 0 on clean pass, code 1 on failure or error.
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from ultron.interfaces.cli.commands.verify import main


if __name__ == "__main__":
    sys.exit(main())
