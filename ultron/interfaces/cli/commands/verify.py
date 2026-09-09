"""
ultron.interfaces.cli.commands.verify
Single Source-of-Truth Test Suite Verification Engine & CLI Handler.

Per Task P2-B1 of docs/AGENT_EXECUTION_PLAN_PHASE2.md:
Discovers and executes the complete repository test suite without cherry-picking.
Emits a stable, greppable summary line:
    TESTS: <n> ran, <f> failed, <e> errors, <s> skipped
Guarantees exit code 0 on clean pass and exit code 1 on any failure or error.
"""

import os
import sys
import io
import json
import time
import argparse
import unittest
import contextlib
from typing import Optional, List, TextIO


def build_verify_parser(parser: Optional[argparse.ArgumentParser] = None) -> argparse.ArgumentParser:
    """Builds or configures the argument parser for 'ultron verify'."""
    if parser is None:
        parser = argparse.ArgumentParser(
            prog="ultron verify",
            description="Execute master repository test suite as the single source of truth."
        )
    parser.add_argument("--repo", default=".", help="Path to codebase repository (default: .)")
    parser.add_argument("--pattern", default="test_*.py", help="Test file naming pattern (default: test_*.py)")
    parser.add_argument("--test-dir", default="ultron/tests", help="Directory containing tests relative to repo (default: ultron/tests)")
    parser.add_argument("--failfast", action="store_true", default=False, help="Stop test execution on first failure or error")
    parser.add_argument("--json", action="store_true", default=False, help="Output machine-readable JSON summary exclusively")
    parser.add_argument("--quiet", action="store_true", default=False, help="Suppress runner progress and emit only the final summary line")
    return parser


def run_verify_command(
    repo_path: str = ".",
    pattern: str = "test_*.py",
    test_dir: str = "ultron/tests",
    failfast: bool = False,
    json_output: bool = False,
    quiet: bool = False,
    stream: Optional[TextIO] = None
) -> int:
    """
    Executes the master verification discovery suite.
    
    Returns:
        0 if all discovered tests pass without failures or errors.
        1 if any test fails, raises an error, or if test discovery encounters an exception.
    """
    abs_repo = os.path.abspath(os.path.normpath(repo_path))
    if not os.path.isdir(abs_repo):
        sys.stderr.write(f"[-] Error: Repository directory '{abs_repo}' not found.\n")
        sys.stderr.flush()
        return 1

    if abs_repo not in sys.path:
        sys.path.insert(0, abs_repo)

    abs_test_dir = os.path.normpath(os.path.join(abs_repo, test_dir))
    if not os.path.isdir(abs_test_dir):
        sys.stderr.write(f"[-] Error: Test directory '{abs_test_dir}' not found in repository.\n")
        sys.stderr.flush()
        return 1

    start_time = time.perf_counter()

    try:
        loader = unittest.defaultTestLoader
        suite = loader.discover(
            start_dir=abs_test_dir,
            pattern=pattern,
            top_level_dir=abs_repo
        )
    except Exception as e:
        sys.stderr.write(f"[-] Test discovery failed with exception: {e}\n")
        sys.stderr.flush()
        if json_output:
            print(json.dumps({
                "status": "ERROR",
                "passed": False,
                "exit_code": 1,
                "error": str(e)
            }, indent=2), file=sys.stdout, flush=True)
        return 1

    if json_output:
        # Silenced execution: trap both runner stream and stdout so JSON stdout remains pure
        runner_stream = io.StringIO()
        stdout_trap = io.StringIO()
        with contextlib.redirect_stdout(stdout_trap):
            runner = unittest.TextTestRunner(stream=runner_stream, failfast=failfast, verbosity=0)
            result = runner.run(suite)
    else:
        if quiet:
            runner_stream = io.StringIO()
            runner = unittest.TextTestRunner(stream=runner_stream, failfast=failfast, verbosity=0)
        else:
            runner_stream = stream or sys.stderr
            runner = unittest.TextTestRunner(stream=runner_stream, failfast=failfast, verbosity=1)
        result = runner.run(suite)

    elapsed = time.perf_counter() - start_time
    passed = result.wasSuccessful()
    exit_code = 0 if passed else 1

    ran_count = result.testsRun
    failed_count = len(result.failures)
    error_count = len(result.errors)
    skipped_count = len(result.skipped)

    if json_output:
        payload = {
            "status": "PASSED" if passed else "FAILED",
            "passed": passed,
            "exit_code": exit_code,
            "ran": ran_count,
            "failed": failed_count,
            "errors": error_count,
            "skipped": skipped_count,
            "duration": round(elapsed, 4)
        }
        print(json.dumps(payload, indent=2), file=sys.stdout, flush=True)
    else:
        summary_line = f"TESTS: {ran_count} ran, {failed_count} failed, {error_count} errors, {skipped_count} skipped"
        print(summary_line, file=sys.stdout, flush=True)

    sys.stdout.flush()
    sys.stderr.flush()
    return exit_code


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint for verify command."""
    parser = build_verify_parser()
    args = parser.parse_args(argv)
    return run_verify_command(
        repo_path=args.repo,
        pattern=args.pattern,
        test_dir=args.test_dir,
        failfast=args.failfast,
        json_output=args.json,
        quiet=args.quiet
    )


if __name__ == "__main__":
    sys.exit(main())
