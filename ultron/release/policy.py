import os
import json
import sys

from ultron.release.schema import validate_report_schema

def evaluate_release_policy(report_file="release_report.json"):
    """
    Ultron Release Policy Evaluator.
    
    Evaluates `release_report.json` against production policy rules & the 6 Release Invariants.
    Issues 3-tier verdict: APPROVED, APPROVED_WITH_WARNINGS, or BLOCKED.
    """
    if not os.path.exists(report_file):
        print(f"[Policy Evaluator] ERROR: Canonical contract '{report_file}' not found.")
        return "BLOCKED", False
        
    with open(report_file, "r", encoding="utf-8") as f:
        report = json.load(f)
        
    is_valid, msg = validate_report_schema(report)
    if not is_valid:
        print(f"[Policy Evaluator] ERROR: Contract schema invalid: {msg}")
        return "BLOCKED", False
        
    print(f"[Policy Evaluator] Evaluating release contract for version {report.get('release_version')}...")
    ctx = report.get("audit_context", {})
    print(f"[Policy Evaluator] Environment: Python {ctx.get('python_version', '').split()[0]} on {ctx.get('platform')}")
    
    invariants = []
    
    # Invariant 1: Hard Freeze Active
    freeze_ok = report.get("hard_freeze_active", False)
    invariants.append(("Invariant 1: Hard Freeze Policy Active", freeze_ok, True)) # Name, status, critical
    
    # Invariant 2: 100% Test Suite Pass Rate (Zero Failures)
    test_data = report.get("test_suite", {})
    test_ok = test_data.get("passed", False) and test_data.get("failures", 1) == 0
    invariants.append((f"Invariant 2: Test Suite Pass Rate ({test_data.get('tests_run')} tests OK, 0 failures)", test_ok, True))
    
    # Invariant 3: Frontend JS Syntax Check
    js_data = report.get("frontend_syntax", {})
    js_ok = js_data.get("passed", False)
    invariants.append(("Invariant 3: Zero Uncaught Frontend JS Syntax Errors", js_ok, True))
    
    # Invariant 4: Workload Performance Benchmarks
    bench_data = report.get("performance_benchmark", {})
    bench_a = bench_data.get("benchmark_a_100_files", {})
    bench_b = bench_data.get("benchmark_b_1000_files", {})
    
    bench_a_ok = bench_a.get("passed", False) and (bench_a.get("latency_seconds", 99) < bench_a.get("budget_seconds", 2.0))
    bench_b_ok = bench_b.get("passed", False) and (bench_b.get("latency_seconds", 99) < bench_b.get("budget_seconds", 15.0))
    bench_ok = bench_a_ok and bench_b_ok
    
    invariants.append((f"Invariant 4: Workload Performance (100 files: {bench_a.get('latency_seconds')}s < 2.0s, 1000 files: {bench_b.get('latency_seconds')}s < 15.0s)", bench_ok, False))
    
    # Invariant 5: Security & Directory Traversal Protection
    sec_ok = test_data.get("passed", False) # Verified via test_security_and_migration
    invariants.append(("Invariant 5: Zero Critical Security Vulnerabilities", sec_ok, True))
    
    # Invariant 6: Reproducible Release Contract
    schema_ok = bool(report.get("audit_context"))
    invariants.append(("Invariant 6: Reproducible Contract & Audit Context", schema_ok, True))

    # Invariant 7: AI Review Presence (non-blocking advisory)
    ai_data = report.get("ai_review", {})
    ai_present = bool(ai_data.get("status"))
    invariants.append(("Invariant 7: AI Architectural Review Attached", ai_present, False))

    critical_failed = any((not status) for _, status, is_critical in invariants if is_critical)
    warning_failed = any((not status) for _, status, is_critical in invariants if not is_critical)

    print("\n--- RELEASE INVARIANTS EVALUATION ---")
    for name, status, is_critical in invariants:
        level_str = "CRITICAL" if is_critical else "WARNING"
        symbol = "[PASS]" if status else f"[FAIL-{level_str}]"
        print(f"{symbol} {name}")
    print("-------------------------------------")

    if critical_failed:
        verdict = "BLOCKED"
        success = False
    elif warning_failed:
        verdict = "APPROVED_WITH_WARNINGS"
        success = True
    else:
        verdict = "APPROVED"
        success = True

    print(f"[Policy Evaluator] Formal Release Verdict: {verdict}\n")
    return verdict, success

if __name__ == "__main__":
    verdict, success = evaluate_release_policy()
    sys.exit(0 if success else 1)
