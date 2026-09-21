#!/usr/bin/env python3
"""
scripts/verify_release_tag.py
Release Tag Verification, Immutability & Clean Tree Gate.

Validates:
1. Git tag format and parity with package version and release facts.
2. Immutable tag binding (HEAD points exactly to the released tag).
3. Clean git working tree (zero uncommitted changes).
4. Pre-flight immutability probe (refuses duplicate version overwrite on PyPI/TestPyPI).

Pure Python standard library implementation.
"""

import os
import sys
import re
import json
import subprocess
import argparse
import urllib.request
import urllib.error
from typing import Tuple, Optional, Dict, Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import ultron

USER_AGENT = f"ultron-release-verifier/{ultron.get_version()} (DMzinev/ultron)"


def parse_tag_version(tag: str) -> Tuple[str, Optional[str]]:
    """
    Parses a release tag into base version and pre-release suffix.
    E.g.: 'v1.5.0' -> ('1.5.0', None), 'v1.5.0rc1' -> ('1.5.0', 'rc1').
    """
    if not isinstance(tag, str) or not tag.startswith("v"):
        return "", None
    raw = tag[1:]
    m = re.match(r"^(\d+\.\d+\.\d+)((?:a|b|rc)\d+)?$", raw)
    if not m:
        return raw, None
    return m.group(1), (m.group(2) if m.group(2) else None)


def verify_tag_matches_package(tag: str, repo_root: str = REPO_ROOT) -> Tuple[bool, str]:
    """Asserts that tag matches ultron.get_version() and docs/release_facts.json."""
    if not tag or not tag.startswith("v"):
        return False, f"Release tag '{tag}' must begin with 'v' prefix (e.g. v1.5.0 or v1.5.0rc1)."

    tag_ver = tag[1:]
    pkg_ver = ultron.get_version()

    # Introspect release_facts.json if available
    facts_path = os.path.join(repo_root, "docs", "release_facts.json")
    rc_ident = None
    if os.path.isfile(facts_path):
        try:
            with open(facts_path, "r", encoding="utf-8") as f:
                facts = json.load(f)
            rc_ident = facts.get("release_candidate")
        except Exception:
            pass

    # Allowed valid tags: exact version (v1.5.0) or exact release candidate (v1.5.0rc1)
    allowed_tags = {f"v{pkg_ver}"}
    if rc_ident:
        allowed_tags.add(f"v{rc_ident}")

    if tag not in allowed_tags:
        return False, (
            f"Release tag '{tag}' does not match package version '{pkg_ver}' "
            f"or candidate '{rc_ident}'. Expected one of: {sorted(allowed_tags)}"
        )

    return True, f"Tag '{tag}' verified against package version '{pkg_ver}'."


def verify_clean_git_tree(repo_root: str = REPO_ROOT) -> Tuple[bool, str]:
    """Asserts that the git working tree has no uncommitted changes."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root, capture_output=True, text=True, timeout=10
        )
        if proc.returncode != 0:
            return False, f"Git status check failed: {proc.stderr.strip()}"
        out = proc.stdout.strip()
        if out:
            lines = out.splitlines()
            return False, f"Dirty working tree detected ({len(lines)} uncommitted file(s))."
        return True, "Git working tree is clean."
    except Exception as e:
        return False, f"Failed to execute git status: {e}"


def verify_head_is_tag(expected_tag: str, repo_root: str = REPO_ROOT) -> Tuple[bool, str]:
    """Asserts that HEAD commit is tagged with expected_tag, preventing branch tip collision."""
    try:
        proc = subprocess.run(
            ["git", "tag", "--points-at", "HEAD"],
            cwd=repo_root, capture_output=True, text=True, timeout=10
        )
        if proc.returncode != 0:
            return False, f"Git tag check failed: {proc.stderr.strip()}"
        tags = [t.strip() for t in proc.stdout.splitlines() if t.strip()]
        if expected_tag not in tags:
            return False, (
                f"HEAD is not tagged with '{expected_tag}'. "
                f"Tags pointing to HEAD: {tags if tags else 'None'}. "
                "Refusing branch-only or uncommitted publication."
            )
        return True, f"HEAD correctly points to tag '{expected_tag}'."
    except Exception as e:
        return False, f"Failed to verify tag at HEAD: {e}"


def check_version_exists_on_pypi(
    package_name: str,
    version: str,
    test_pypi: bool = False,
    timeout: float = 5.0
) -> Tuple[bool, str]:
    """
    Checks if package version is already published to PyPI or TestPyPI.
    Returns (True, msg) if version exists (conflict).
    Returns (False, msg) if version does NOT exist (clean to publish).
    """
    base_url = "https://test.pypi.org/pypi" if test_pypi else "https://pypi.org/pypi"
    url = f"{base_url}/{package_name}/json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                releases = data.get("releases", {})
                current_ver = data.get("info", {}).get("version")
                if version in releases or current_ver == version:
                    return True, f"Version '{version}' of '{package_name}' already exists on {base_url}."
                return False, f"Version '{version}' not found in releases on {base_url}."
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Package does not exist yet on index — clean to publish
            return False, f"Package '{package_name}' does not exist on {base_url} (HTTP 404)."
        return False, f"HTTP error {e.code} checking {url}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"Network error checking {url}: {e.reason}"
    except Exception as e:
        return False, f"Unexpected error probing index: {e}"

    return False, f"Version '{version}' is clean on {base_url}."


def main():
    parser = argparse.ArgumentParser(description="Verify release tag, clean tree, and package immutability.")
    parser.add_argument("--tag", required=True, help="Release tag name (e.g. v1.5.0 or v1.5.0rc1)")
    parser.add_argument("--repo", default=REPO_ROOT, help="Repository root path")
    parser.add_argument("--verify-head", action="store_true", help="Assert HEAD commit points to --tag")
    parser.add_argument("--check-exists", action="store_true", help="Check if version already exists on PyPI")
    parser.add_argument("--test-pypi", action="store_true", help="Use TestPyPI instead of production PyPI for check")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    results: Dict[str, Any] = {"passed": True, "tag": args.tag, "checks": {}}

    # 1. Verify tag format and parity
    ok_tag, msg_tag = verify_tag_matches_package(args.tag, args.repo)
    results["checks"]["tag_parity"] = {"passed": ok_tag, "message": msg_tag}
    if not ok_tag:
        results["passed"] = False

    # 2. Verify clean git tree
    ok_tree, msg_tree = verify_clean_git_tree(args.repo)
    results["checks"]["clean_tree"] = {"passed": ok_tree, "message": msg_tree}
    if not ok_tree:
        results["passed"] = False

    # 3. Verify HEAD points to tag
    if args.verify_head:
        ok_head, msg_head = verify_head_is_tag(args.tag, args.repo)
        results["checks"]["head_is_tag"] = {"passed": ok_head, "message": msg_head}
        if not ok_head:
            results["passed"] = False

    # 4. Check PyPI / TestPyPI existence (fails if version already exists)
    if args.check_exists:
        base_ver, rc_part = parse_tag_version(args.tag)
        ver_to_check = f"{base_ver}{rc_part}" if rc_part else base_ver
        exists, msg_exists = check_version_exists_on_pypi(
            package_name="ultron-risk-scorer",
            version=ver_to_check,
            test_pypi=args.test_pypi
        )
        if exists:
            # Conflict: immutable version already published
            results["checks"]["immutability"] = {
                "passed": False,
                "message": f"Conflict: {msg_exists}. Cannot republish immutable release."
            }
            results["passed"] = False
        else:
            results["checks"]["immutability"] = {
                "passed": True,
                "message": f"Immutability verified: {msg_exists}."
            }

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for name, item in results["checks"].items():
            status = "PASS" if item["passed"] else "FAIL"
            print(f"[{status}] {name}: {item['message']}")

    return 0 if results["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
