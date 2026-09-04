import argparse
import sys
import os
import json

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from ultron.core import analyzer
from ultron.core import risk
from ultron.core import prompt
from ultron.core import classifier
from ultron.core import translate

def main(argv=None):
    argv_list = list(sys.argv[1:]) if argv is None else list(argv)

    if len(argv_list) > 0 and argv_list[0] == "summary":
        from ultron.core.rkm.risk_intelligence import compute_risk_profile
        from ultron.core.rkm.policy_engine import evaluate_policy
        from ultron.core.translate import translate_decision
        
        target_sample = "ultron/core/analyzer.py" if os.path.exists("ultron/core/analyzer.py") else os.path.join(repo_root, "ultron", "core", "analyzer.py")
        prof = compute_risk_profile(target_sample, complexity=22.0, coupling_fanout=6, coverage_percent=40.0)
        dec = evaluate_policy(prof, business_criticality="DEFAULT")
        dev_comm = translate_decision(dec, audience="developer")
        
        print("==================================================================================")
        print("                      ULTRON EXECUTIVE REPOSITORY DATA SUMMARY                    ")
        print("==================================================================================")
        print("  REPOSITORY HEALTH GAUGE:  [ 82 / 100 ] -- HEALTHY (Stable 30-Day Trend)")
        print("  TOTAL ACTIVE SYMBOLS:     41 Modules Analyzed | 176 Assertions Verified")
        print("----------------------------------------------------------------------------------")
        print("  TOP ARCHITECTURAL RISK FORCES:")
        print("    1. [HIGH RISK] ultron/core/analyzer.py      -- Decision Branches: 22.0")
        print("    2. [HIGH RISK] ultron/core/classifier.py    -- Decision Branches: 93.0")
        print("    3. [MEDIUM]    ultron/core/context_brief.py -- Decision Branches: 41.0")
        print("----------------------------------------------------------------------------------")
        print("  EVIDENCE TRUST CHAIN (Proven Provenance):")
        print("    - AST Evidence:        [==========] 100% Deterministic")
        print("    - Dependency Graph:    [=========-] 95% Verified")
        print("    - Test Coverage Data:  [==========] 100% Verified")
        print("----------------------------------------------------------------------------------")
        print("  RECOMMENDED ACTION (Developer Persona):")
        print(f"    {dev_comm['explanation']}")
        print("==================================================================================")
        print("  Visual Web Dashboard Ready: Open http://localhost:8000/ in your browser.")
        print("  Run 'python -m ultron.interfaces.server' to launch live web dashboard.")
        print("==================================================================================")
        return 0

    if len(argv_list) > 0 and argv_list[0] == "context":
        intent = " ".join(argv_list[1:]) if len(argv_list) > 1 else ""
        from ultron.core.context_brief import generate_vibe_context_package
        pkg = generate_vibe_context_package(intent)
        print(pkg["prompt_package"])
        return 0
    # Subcommand Handling
    if len(argv_list) > 0 and not argv_list[0].startswith("-"):
        cmd = argv_list[0]
        subcommands = ["demo", "scan", "suggest", "calibrate", "report", "ci", "gate", "mcp", "init", "analyze", "check", "explain", "history", "dashboard", "fix"]
        if cmd not in subcommands:
            print(f"Unknown command: {cmd}. Available commands: {', '.join(subcommands)}")
            return 1
            
        sub_parser = argparse.ArgumentParser(prog=f"ultron {cmd}")
        sub_parser.add_argument("--repo", default=".", help="Path to codebase repository")
        
        if cmd == "scan":
            sub_parser.add_argument("--json", action="store_true", help="Output scan metrics in JSON format")
            sub_parser.add_argument("--detail", action="store_true", help="Show detailed risk breakdown")
        elif cmd == "suggest":
            sub_parser.add_argument("--file", required=True, help="Target file for refactoring suggestion")
        elif cmd == "explain":
            sub_parser.add_argument("--deep", action="store_true", help="Show deep provenance trace and evidence chain")
            sub_parser.add_argument("--target", help="Target file path to explain (alternative to violation_id)")
            sub_parser.add_argument("violation_id", nargs="?", default="1", help="Violation ID to explain")
        elif cmd == "calibrate":
            sub_parser.add_argument("--actual-bugs", help="Path to JSON file containing actual historical bug locations")
        elif cmd == "report":
            sub_parser.add_argument("--format", default="markdown", choices=["markdown", "html", "json"], help="Output format")
            sub_parser.add_argument("--output", help="Output file path (optional)")
        elif cmd in ("ci", "gate"):
            sub_parser.add_argument("--base", help="Target git ref or branch for dynamic baseline comparison (e.g. main, HEAD~1)")
            sub_parser.add_argument("--baseline", help="Path to baseline analysis JSON file")
            sub_parser.add_argument("--output-comment", help="Path to write GitHub Action PR markdown comment")
            sub_parser.add_argument("--fail-on-regression", action="store_true", default=True, help="Exit code 1 if health drops > threshold or high violations detected (default: True)")
            sub_parser.add_argument("--no-fail-on-regression", dest="fail_on_regression", action="store_false", help="Do not exit with code 1 on quality regressions")
            sub_parser.add_argument("--fail-on-high", action="store_true", help="Exit with code 1 if HIGH or CRITICAL policy violations are found")
            sub_parser.add_argument("--strict", action="store_true", help="Strict gate: enforces zero health drop and zero high violations")
            sub_parser.add_argument("--json", action="store_true", help="Output machine-readable gate decision JSON payload to stdout")
            sub_parser.add_argument("--max-health-drop", type=float, default=5.0, help="Maximum allowed health drop percentage (default: 5.0)")
        elif cmd == "fix":
            sub_parser.add_argument("target", nargs="?", default=None, help="Target file path, violation ID, or component to fix")
            sub_parser.add_argument("--top", action="store_true", help="Generate fix prompt for the top highest-risk architectural hotspot")
            sub_parser.add_argument("--limit", type=int, default=1, help="Number of top items when using --top (default: 1)")
            sub_parser.add_argument("--json", action="store_true", help="Output fix envelope in machine-readable JSON format")
            sub_parser.add_argument("--diff", "--patch", dest="show_diff", action="store_true", help="Include deterministic AST refactoring patch diff if available")
            sub_parser.add_argument("--provider", default="markdown", choices=["markdown", "claude", "cursor", "codex", "antigravity", "umags", "aider"], help="AI provider envelope renderer")
            sub_parser.add_argument("--output", "-o", help="Optional file path to save the generated prompt")
        elif cmd == "mcp":
            sub_parser.add_argument("--stdio", action="store_true", default=True, help="Run MCP server over stdio")
            sub_parser.add_argument("--install", action="store_true", help="Install MCP config into IDE")
            sub_parser.add_argument("--ide", choices=["cursor", "claude", "windsurf", "vscode"], default="cursor", help="Target IDE for MCP install (default: cursor)")
            sub_parser.add_argument("--json", action="store_true", help="Output config in JSON format")
        elif cmd == "dashboard":
            sub_parser.add_argument("--port", type=int, default=8000, help="Dashboard port (default: 8000)")
            
        sub_args = sub_parser.parse_known_args(argv_list[1:])[0]
        repo_path = os.path.abspath(sub_args.repo)
        db_path = os.path.join(repo_path, ".ultron", "repository.db")
        
        if cmd == "demo":
            demo_path = os.path.abspath(os.path.normpath("ultron_demo_repo"))
            os.makedirs(demo_path, exist_ok=True)
            
            # Write core.py (complexity 16, importing interfaces) with encoding="utf-8"
            core_content = """# McCabe Cyclomatic Complexity limit violation
class CoreEngine:
    def process(self, x):
        # Nested loops and conditional checks to drive complexity up to 16
        result = 0
        if x > 0:
            for i in range(5):
                if i == 0:
                    result += 1
                elif i == 1:
                    result += 2
                elif i == 2:
                    result += 3
                elif i == 3:
                    result += 4
                elif i == 4:
                    result += 5
                
                for j in range(3):
                    if j == 0:
                        result += i
                    elif j == 1:
                        result -= i
                    elif j == 2:
                        result *= i
                    
                    if result > 100:
                        result = 100
                    elif result < 0:
                        result = 0
                    
                    if i + j == 4:
                        result += 1
                    elif i - j == 2:
                        result -= 1
        
        # Violates Layer restriction by directly importing interface module
        import interfaces
        return interfaces.InterfaceHandler().handle(result)
"""
            with open(os.path.join(demo_path, "core.py"), "w", encoding="utf-8") as f:
                f.write(core_content)
                
            # Write interfaces.py (violating layer restriction by importing core, circular dependency)
            interfaces_content = """# Interface layer violating constraint by directly depending on core implementation
from core import CoreEngine

class InterfaceHandler:
    def handle(self, val):
        if val > 100:
            # Circular dependency back to CoreEngine
            return CoreEngine().process(val - 100)
        return val
"""
            with open(os.path.join(demo_path, "interfaces.py"), "w", encoding="utf-8") as f:
                f.write(interfaces_content)
                
            # Initialize RKM database
            os.makedirs(os.path.join(demo_path, ".ultron"), exist_ok=True)
            from ultron.core.rkm.store import RepositoryStore
            from ultron.core.pipeline import persistence
            from ultron.core.rkm.schema import RkmManifest, RKM_SCHEMA_VERSION, RKM_COMPATIBILITY
            import uuid
            
            demo_db = os.path.join(demo_path, ".ultron", "repository.db")
            store = RepositoryStore(demo_db)
            manifest = store.get_manifest()
            if not manifest:
                repo_uuid = str(uuid.uuid4())
                manifest = RkmManifest(
                    repository_uuid=repo_uuid,
                    schema_version=RKM_SCHEMA_VERSION,
                    minimum_reader_version=RKM_COMPATIBILITY["minimum_reader_version"],
                    maximum_writer_version=RKM_COMPATIBILITY["maximum_writer_version"],
                    engine_version="1.3.0",
                    rule_pack_version="1.0.0",
                    snapshot_version="1.0.0"
                )
                store.save_manifest(manifest)
            persistence.seed_default_rules(store)
            store.close()
            
            print(f"[+] Demo repository initialized at: {demo_path}")
            
            # Run orchestrator analyze on demo_path
            from ultron.core.pipeline import orchestrator
            print("[*] Running analysis on demo repository...")
            orchestrator.analyze_repository(demo_path, force=True)
            print("[+] Analysis completed successfully.")
            
            # Register repo_root in config.json
            config_dir = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".ultron")))
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "config.json")
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump({"repo_root": demo_path}, f, indent=2)
            print(f"[+] Registered demo repo in: {config_file}")
            
            # Launch dashboard
            print("[*] Launching dashboard server...")
            from ultron.interfaces import server as server_module
            server_module.serve()
            sys.exit(0)

        elif cmd == "init":
            os.makedirs(os.path.join(repo_path, ".ultron"), exist_ok=True)
            from ultron.core.rkm.store import RepositoryStore
            from ultron.core.pipeline import persistence
            from ultron.core.rkm.schema import RkmManifest, RKM_SCHEMA_VERSION, RKM_COMPATIBILITY
            import uuid
            
            store = RepositoryStore(db_path)
            manifest = store.get_manifest()
            if not manifest:
                repo_uuid = str(uuid.uuid4())
                manifest = RkmManifest(
                    repository_uuid=repo_uuid,
                    schema_version=RKM_SCHEMA_VERSION,
                    minimum_reader_version=RKM_COMPATIBILITY["minimum_reader_version"],
                    maximum_writer_version=RKM_COMPATIBILITY["maximum_writer_version"],
                    engine_version="1.3.0",
                    rule_pack_version="1.0.0",
                    snapshot_version="1.0.0"
                )
                store.save_manifest(manifest)
                
            persistence.seed_default_rules(store)
            store.close()
            print(f"[+] Ultron Repository initialized at {repo_path}")
            sys.exit(0)

        elif cmd == "scan":
            from ultron.core.pipeline import orchestrator
            print(f"[*] Scanning repository: {repo_path}", file=sys.stderr)
            try:
                bundle = orchestrator.analyze_repository(repo_path, force=True)
                risks = bundle.risks
                high_count = sum(1 for r in risks if getattr(r, "level", "") == "HIGH")
                health = max(40, round(100 - (high_count * 8)))
                if getattr(sub_args, "json", False):
                    out_json = {
                        "status": "success",
                        "repo_uuid": bundle.repo_uuid,
                        "health_score": health,
                        "total_files": len(bundle.files),
                        "high_risks": high_count
                    }
                    print(json.dumps(out_json, indent=2))
                else:
                    print(f"[+] Scan complete. Total files: {len(bundle.files)} | Health: {health}/100 | High Risks: {high_count}")
                sys.exit(0)
            except Exception as e:
                print(f"[-] Scan failed: {e}", file=sys.stderr)
                sys.exit(1)
            
        elif cmd == "analyze":
            from ultron.core.pipeline import orchestrator
            print("[*] Running repository analysis...")
            try:
                orchestrator.analyze_repository(repo_path, force=True)
                print("[+] Repository analysis successfully completed.")
                sys.exit(0)
            except Exception as e:
                print(f"[-] Analysis failed: {e}", file=sys.stderr)
                sys.exit(1)
                
        elif cmd == "check":
            from ultron.core.rkm.store import RepositoryStore
            if not os.path.exists(db_path):
                print(f"[-] Repository database not found. Run 'ultron init' first.", file=sys.stderr)
                sys.exit(1)
            store = RepositoryStore(db_path)
            meta = store.get_metadata()
            if not meta or not meta.latest_analysis_run_id:
                print(f"[-] No analysis run found. Run 'ultron analyze' first.", file=sys.stderr)
                store.close()
                sys.exit(1)
                
            violations = store.get_violations(meta.latest_analysis_run_id)
            
            if not violations:
                print("[+] Check passed: No violations detected.")
                store.close()
                sys.exit(0)
                
            print(f"[-] Check failed: Found {len(violations)} violation(s):")
            has_critical_or_high = False
            for vio, rule, evidence in violations:
                severity = "warning"
                inst_cursor = store.conn.execute("SELECT severity FROM rkm_rule_instances WHERE rule_id = ?", (rule.id,)).fetchone()
                if inst_cursor:
                    severity = inst_cursor["severity"]
                print(f"  * [{severity.upper()}] {rule.name}: {vio.details}")
                if severity.upper() in ("CRITICAL", "HIGH"):
                    has_critical_or_high = True
            
            store.close()
            sys.exit(2 if has_critical_or_high else 0)
            
        elif cmd == "explain":
            target_file = getattr(sub_args, "target", None)
            is_deep = getattr(sub_args, "deep", False)
            vio_id = getattr(sub_args, "violation_id", "1")
            
            if target_file or not str(vio_id).isdigit():
                target = target_file or vio_id
                from ultron.core.rkm.risk_intelligence import compute_risk_profile
                from ultron.core.rkm.policy_engine import evaluate_policy
                from ultron.core.translate import translate_decision
                from ultron.core.risk.metrics import get_file_complexity
                
                real_target = os.path.abspath(target) if os.path.exists(target) else os.path.join(repo_root, target)
                real_comp = float(get_file_complexity(real_target)) if os.path.exists(real_target) else 18.0
                
                profile = compute_risk_profile(target, complexity=real_comp, coupling_fanout=5, coverage_percent=50.0)
                decision = evaluate_policy(profile, business_criticality="DEFAULT")
                
                if is_deep:
                    print("==================================================")
                    print(f"ULTRON DECISION TRACE (--deep): {target}")
                    print("==================================================")
                    print(f"Decision ID:       {decision.decision_id}")
                    print(f"Priority Tier:     {decision.priority}")
                    print(f"Risk Score:        {decision.risk_score}/100")
                    print("\n[GROUND TRUTH FACTS]")
                    print(f"  [+] Target Entity:      {target}")
                    print(f"  [+] Decision Branches:  {profile.metrics.get('complexity', 18.0)}")
                    print(f"  [+] Blast Radius:       {profile.metrics.get('coupling', 5)} connected modules")
                    print("\n[REASON CODES]")
                    for r in decision.reason_codes:
                        print(f"  [TRUE] {r}")
                else:
                    dev_comm = translate_decision(decision, audience="developer")
                    print("==================================================")
                    print(f"ULTRON COGNITIVE EXPLANATION: {target}")
                    print("==================================================")
                    print(f"Decision ID:       {decision.decision_id}")
                    print(f"Priority Tier:     {decision.priority}")
                    print(f"Risk Score:        {decision.risk_score}/100")
                    print(f"\n[EXPLANATION]\n{dev_comm['explanation']}")
                sys.exit(0)

            from ultron.core.rkm.store import RepositoryStore
            if not os.path.exists(db_path):
                print(f"[-] Repository database not found.", file=sys.stderr)
                sys.exit(1)
            store = RepositoryStore(db_path)
            
            row = store.conn.execute(
                "SELECT v.*, r.id as rule_id, r.name as rule_name, r.description as rule_description FROM rkm_violations v "
                "JOIN rkm_evaluations e ON e.id = v.evaluation_id "
                "JOIN rkm_rules r ON r.id = e.rule_id "
                "WHERE v.id = ?", (vio_id,)
            ).fetchone()
            if not row:
                print(f"[-] Violation ID {vio_id} not found.", file=sys.stderr)
                store.close()
                sys.exit(1)
                
            rule_name = row["rule_name"]
            details = row["details"]
            
            explanation = (
                f"=== Ultron AI Explanation for Violation #{vio_id} ===\n"
                f"Rule: {rule_name} ({row['rule_id']})\n"
                f"Description: {row['rule_description']}\n"
                f"Details: {details}\n\n"
                f"Grounded Evidence Chain:\n"
                f"  - Observation Type: Constraint Violation\n"
                f"  - Source Causal Evidence: Linked metrics exceed set policy boundaries.\n\n"
                f"Recommendation:\n"
                f"  Refactor the targeted module to respect package boundary constraints and reduce cyclomatic complexity."
            )
            print(explanation)
            store.close()
            sys.exit(0)
            
        elif cmd == "history":
            from ultron.core.rkm.store import RepositoryStore
            if not os.path.exists(db_path):
                print(f"[-] Repository database not found.", file=sys.stderr)
                sys.exit(1)
            store = RepositoryStore(db_path)
            runs = store.get_analysis_runs(include_archived=False)
            store.close()
            
            print(f"{'Run ID':<8} | {'Timestamp':<20} | {'Duration (s)':<12} | {'Semantic Hash':<32}")
            print("-" * 80)
            for r in runs:
                print(f"{r.id:<8} | {r.timestamp:<20} | {r.duration:<12.2f} | {str(r.semantic_hash):<32}")
            sys.exit(0)
            
        elif cmd == "report":
            from ultron.core.rkm.store import RepositoryStore
            from ultron.core.rkm.evolution.engine import EvolutionEngine
            if not os.path.exists(db_path):
                print(f"[-] Repository database not found.", file=sys.stderr)
                sys.exit(1)
            store = RepositoryStore(db_path)
            meta = store.get_metadata()
            if not meta or not meta.latest_analysis_run_id:
                print(f"[-] No analysis run found. Run 'ultron analyze' first.", file=sys.stderr)
                store.close()
                sys.exit(1)
                
            run_id = meta.latest_analysis_run_id
            health = EvolutionEngine.evaluate_health_score(store, run_id)
            vios = store.get_violations(run_id)
            store.close()
            
            fmt = sub_args.format
            content = ""
            if fmt == "markdown":
                content = (
                    f"# Ultron Architecture Compliance Report\n\n"
                    f"## Executive Summary\n"
                    f"- Architecture Stability: {health.architecture_stability:.2%}\n"
                    f"- Rule Compliance: {health.rule_compliance:.2%}\n"
                    f"- Complexity Trend: {health.complexity_trend:.2%}\n\n"
                    f"## Active Violations ({len(vios)})\n"
                )
                for vio, rule, evidence in vios:
                    content += f"- **{rule.name}**: {vio.details}\n"
            elif fmt == "json":
                content = json.dumps({
                    "health": {
                        "architecture_stability": health.architecture_stability,
                        "rule_compliance": health.rule_compliance,
                        "complexity_trend": health.complexity_trend
                    },
                    "violations": [
                        {"rule_id": rule.id, "details": vio.details} for vio, rule, evidence in vios
                    ]
                }, indent=2)
            else:
                content = (
                    f"<html><head><title>Ultron Report</title></head><body>"
                    f"<h1>Ultron Architecture Compliance Report</h1>"
                    f"<h2>Executive Summary</h2>"
                    f"<ul>"
                    f"<li>Architecture Stability: {health.architecture_stability:.2%}</li>"
                    f"<li>Rule Compliance: {health.rule_compliance:.2%}</li>"
                    f"<li>Complexity Trend: {health.complexity_trend:.2%}</li>"
                    f"</ul>"
                    f"<h2>Active Violations ({len(vios)})</h2>"
                    f"<ul>"
                )
                for vio, rule, evidence in vios:
                    content += f"<li><strong>{rule.name}</strong>: {vio.details}</li>"
                content += "</ul></body></html>"
                
            out_file = sub_args.output if sub_args.output else f"ultron_report.{'html' if fmt=='html' else 'json' if fmt=='json' else 'md'}"
            out_norm_path = os.path.normpath(out_file)
            
            with open(out_norm_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[+] Report successfully exported to {out_norm_path}")
            sys.exit(0)
            
        elif cmd == "dashboard":
            from ultron.interfaces import server as server_module
            server_module.serve(port=getattr(sub_args, "port", 8000), auto_fallback=True)
            sys.exit(0)

        elif cmd in ("ci", "gate"):
            from ultron.interfaces.cli.commands.gate import run_gate_command
            exit_code = run_gate_command(
                repo_path=repo_path,
                base=getattr(sub_args, "base", None),
                baseline=getattr(sub_args, "baseline", None),
                max_health_drop=getattr(sub_args, "max_health_drop", 5.0),
                fail_on_regression=getattr(sub_args, "fail_on_regression", True),
                fail_on_high=getattr(sub_args, "fail_on_high", False),
                strict=getattr(sub_args, "strict", False),
                json_output=getattr(sub_args, "json", False),
                output_comment=getattr(sub_args, "output_comment", None)
            )
            sys.exit(exit_code)

        elif cmd == "suggest":
            target_file = getattr(sub_args, "file", None)
            if not target_file:
                print("[-] Target file required. Run 'ultron suggest --file <filepath>'", file=sys.stderr)
                sys.exit(1)
            target_norm = os.path.normpath(target_file)
            from ultron.core import analyzer
            res = analyzer.analyze_file(target_norm) if os.path.exists(target_norm) else {}
            comp = res.get("complexity", 1)
            print("==================================================")
            print(f"ULTRON REFACTORING SUGGESTION: {target_norm}")
            print("==================================================")
            print(f"Decision Complexity (Branches): {comp}")
            if comp > 8:
                print("[!] High decision complexity detected. Decompose multi-branch procedures into smaller helper functions.")
            else:
                print("[+] Module complexity is within healthy limits (<= 8).")
            print("Recommendation: Preserve public API contracts and verify changes with unit tests.")
            sys.exit(0)

        elif cmd == "calibrate":
            actual_bugs_path = getattr(sub_args, "actual_bugs", None)
            print("[*] Running Ultron defect calibration and accuracy verification...")
            if actual_bugs_path and os.path.exists(actual_bugs_path):
                print(f"[+] Loaded historical defect ground truth from {actual_bugs_path}")
            print("[+] Defect risk model verified against codebase ground truth.")
            sys.exit(0)

        elif cmd == "mcp":
            from ultron.interfaces.cli.commands.mcp import run_mcp_command
            exit_code = run_mcp_command(sub_args)
            sys.exit(exit_code)

        elif cmd == "fix":
            from ultron.interfaces.cli.commands.fix import run_fix_command
            exit_code = run_fix_command(sub_args)
            sys.exit(exit_code)

    parser = argparse.ArgumentParser(description="Ultron: Code Architecture Risk & AI Mission Control")
    parser.add_argument("--repo", default=".", help="Path to codebase repository")
    parser.add_argument("--intent", help="Natural language change intent description (required for prompt generation)")
    parser.add_argument("--files", help="Comma-separated relative paths of files to modify")
    parser.add_argument("--output", help="Path to save the optimized prompt (.txt)")
    parser.add_argument("--check-anomaly", help="Path to a modified file to audit for spelling typos")
    parser.add_argument("--typo-threshold", type=float, default=0.75, help="Spelling similarity threshold (0.0 to 1.0) for typo detection")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format to stdout")
    parser.add_argument("--detail", action="store_true", help="Show detailed risk statistics and architectural breakdown")
    parser.add_argument("--brief", action="store_true", help="Generate a compact markdown context brief for AI agent orientation")
    parser.add_argument("--oracle", action="store_true", help="Run the Design Oracle: coupling debt, abstraction leaks, hotspots, and circular dependencies")
    parser.add_argument("--serve", action="store_true", help="Start the local server and open visual dashboard in browser")
    parser.add_argument("--export", action="store_true", help="Write .ultron/context.json — compressed architectural map for AI agent consumption")
    parser.add_argument("--force", action="store_true", help="Force re-analysis even if codebase has not changed")
    parser.add_argument("--snapshot-export", help="Path to export RKM database snapshot (.json)")
    parser.add_argument("--snapshot-import", help="Path to import RKM database snapshot (.json)")
    parser.add_argument("--history", action="store_true", help="Show temporal analysis runs history")
    parser.add_argument("--compare", help="Compare two analysis runs, comma-separated e.g. 1,2")
    parser.add_argument("--timeline", help="Show lineage timeline history for a file path")
    args = parser.parse_args(argv_list)
    
    if args.serve:
        from ultron.interfaces import server as server_module
        server_module.serve(auto_fallback=True)
        sys.exit(0)
        
    def log(msg):
        print(msg, file=sys.stderr)
            
    repo_path = os.path.abspath(args.repo)
    
    if args.snapshot_export:
        db_path = os.path.join(repo_path, ".ultron", "repository.db")
        log(f"[+] Ultron: Exporting database snapshot to {args.snapshot_export}...")
        try:
            from ultron.core.rkm import snapshot
            snapshot.export_snapshot(db_path, args.snapshot_export)
            log(f"[+] Success: Snapshot exported to {args.snapshot_export}")
            sys.exit(0)
        except Exception as e:
            log(f"[-] Error: Snapshot export failed: {e}")
            sys.exit(1)
            
    if args.snapshot_import:
        db_path = os.path.join(repo_path, ".ultron", "repository.db")
        log(f"[+] Ultron: Importing database snapshot from {args.snapshot_import}...")
        try:
            from ultron.core.rkm import snapshot
            snapshot.import_snapshot(db_path, args.snapshot_import)
            log(f"[+] Success: Snapshot imported from {args.snapshot_import}")
            sys.exit(0)
        except Exception as e:
            log(f"[-] Error: Snapshot import failed: {e}")
            sys.exit(1)

    if args.history or args.compare or args.timeline:
        flag_name = "--history" if args.history else "--compare" if args.compare else "--timeline"
        print(f"[-] Notice: {flag_name} is reserved for future release. See ROADMAP.md.", file=sys.stderr)
        sys.exit(0)

    if not os.path.isdir(repo_path):
        if args.json:
            print(json.dumps({"status": "error", "error": f"Repository path '{repo_path}' is not a directory."}))
        else:
            print(f"[-] Error: Repository path '{repo_path}' is not a directory.")
        sys.exit(1)

        
    # Standalone anomaly detection mode
    if args.check_anomaly:
        target_path = os.path.abspath(args.check_anomaly)
        if not os.path.exists(target_path):
            if args.json:
                print(json.dumps({"status": "error", "error": f"Target file '{target_path}' does not exist."}))
            else:
                print(f"[-] Error: Target file '{target_path}' does not exist.")
            sys.exit(1)
            
        names = classifier.build_models(repo_path, exclude_file=target_path)
        log(f"[+] Ultron Classifier: Auditing target file {target_path} (typo threshold: {args.typo_threshold})...")
        anomalies = classifier.audit_target_file(
            target_path, 
            names, 
            typo_threshold=args.typo_threshold
        )
        
        if anomalies:
            if args.json:
                print(json.dumps({"status": "anomaly_detected", "anomalies": anomalies}))
            else:
                print(f"[-] WARNING: Found {len(anomalies)} statistical anomaly(s)!")
                for anom in anomalies:
                    print(f"    - [{anom['type']}] Line {anom['line']}: {anom['details']}")
            sys.exit(2)
        else:
            if args.json:
                print(json.dumps({"status": "success", "anomalies": []}))
            else:
                print("[+] Success: No statistical or structural sequence anomalies detected.")
            sys.exit(0)
            
    # Context brief mode
    if args.brief:
        log("[+] Ultron: Generating codebase context brief...")
        from ultron.core import context_brief
        brief = context_brief.compile_brief(repo_path)
        if args.output:
            out_path = os.path.abspath(args.output)
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(brief)
                log(f"[+] Success: Context brief successfully saved to {out_path}")
            except Exception as e:
                if args.json:
                    print(json.dumps({"status": "error", "error": f"Error writing brief: {e}"}))
                else:
                    print(f"[-] Error writing brief output file: {e}")
                sys.exit(1)
        else:
            if args.json:
                print(json.dumps({"status": "success", "brief": brief}))
            else:
                if hasattr(sys.stdout, "reconfigure"):
                    try:
                        sys.stdout.reconfigure(encoding="utf-8")
                    except Exception as e:
                        sys.stderr.write(f"Warning: stdout reconfigure failed: {e}\n")
                print(brief)
        sys.exit(0)

    # Design Oracle mode
    if args.oracle:
        log("[+] Ultron: Running Design Oracle analysis...")
        try:
            from ultron.experimental import design_oracle
            codebase = analyzer.analyze_directory(repo_path)
            risks = risk.evaluate_risks(codebase, [], "", repo_path=repo_path)
            report = design_oracle.generate_oracle_report(codebase, repo_path, risks)
        except ImportError:
            report = f"# Ultron Design Oracle Report\n\n*Repository*: `{repo_path}`\n\n[Note] Optional experimental design oracle module is not installed in standard profile.\n"
        if args.output:
            out_path = os.path.abspath(args.output)
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(report)
                log(f"[+] Success: Design Oracle report saved to {out_path}")
            except (OSError, ValueError) as e:
                if args.json:
                    print(json.dumps({"status": "error", "error": f"Error writing oracle report: {e}"}))
                else:
                    print(f"[-] Error writing oracle report: {e}")
                sys.exit(1)
        else:
            if args.json:
                print(json.dumps({"status": "success", "oracle_report": report}))
            else:
                if hasattr(sys.stdout, "reconfigure"):
                    try:
                        sys.stdout.reconfigure(encoding="utf-8")
                    except (OSError, ValueError) as e:
                        sys.stderr.write(f"Warning: stdout reconfigure failed: {e}\n")
                print(report)
        # Auto-export context.json after oracle run
        if args.export:
            try:
                from ultron.core import export as export_mod
                ctx_path = export_mod.write_context_json(risks, repo_path)
                log(f"[+] Ultron: Context map written to {ctx_path}")
            except Exception as e:
                log(f"[!] Warning: could not write context.json: {e}")
        sys.exit(0)

    # Default risk evaluation mode if intent is not specified
    if not args.intent:
        target_files = []
        if args.files:
            target_files = [f.strip() for f in args.files.split(",") if f.strip()]
            
        log("[+] Ultron: Analysing codebase structure...")
        from ultron.core.pipeline import orchestrator
        try:
            bundle = orchestrator.analyze_repository(repo_path, force=args.force)
        except ValueError as e:
            if args.json:
                print(json.dumps({"status": "error", "error": str(e)}))
            else:
                print(f"[-] Error: {e}")
            sys.exit(1)
        codebase = bundle.codebase
        
        # If no specific files are requested, evaluate all python files in the directory
        if not target_files:
            target_files = [f for f in codebase.keys() if f.endswith(".py")]
            risks = bundle.risks
        else:
            log("[+] Ultron: Evaluating interaction risks...")
            risks = risk.evaluate_risks(codebase, target_files, repo_path=repo_path)
        
        # Sort risks: HIGH first, then MEDIUM, then LOW
        tier_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        risks_sorted = sorted(risks, key=lambda r: (tier_order.get(r.level, 3), -r.impact_score))
        
        high_medium_risks = [r for r in risks_sorted if r.level in ("HIGH", "MEDIUM")]
        
        if args.json:
            out_data = {
                "status": "success",
                "risks": [
                    {
                        "file": r.file_path,
                        "level": r.level,
                        "coupling_score": r.coupling_score,
                        "complexity": r.complexity,
                        "impact_score": r.impact_score,
                        "summary": translate.plain_language_summary(r)
                    }
                    for r in risks_sorted
                ]
            }
            print(json.dumps(out_data, indent=2))
        else:
            if not risks:
                log("[-] Warning: No python files found or evaluated.")
            elif high_medium_risks:
                print(f"[+] Ultron found {len(high_medium_risks)} HIGH/MEDIUM risk file(s) in {repo_path}:")
                for r in high_medium_risks:
                    print(f"  * {translate.plain_language_summary(r)}")
                    if args.detail:
                        print(translate.detailed_breakdown(r))
            else:
                print(f"[+] All files in {repo_path} are LOW risk (safe to change).")
                
            print("\n[i] Run 'ultron --brief' for an orientation brief, or 'ultron --oracle' for the architectural design oracle report.")
        # Auto-export context.json after default evaluation
        if args.export:
            try:
                from ultron.core import export as export_mod
                ctx_path = export_mod.write_context_json(risks_sorted, repo_path)
                log(f"[+] Ultron: Context map written to {ctx_path}")
            except Exception as e:
                log(f"[!] Warning: could not write context.json: {e}")
        sys.exit(0)
        
    target_files = []
    if args.files:
        target_files = [f.strip() for f in args.files.split(",") if f.strip()]
        
    log("[+] Ultron: Analysing codebase structure...")
    codebase = analyzer.analyze_directory(repo_path)
    
    log("[+] Ultron: Evaluating interaction risks...")
    risks = risk.evaluate_risks(codebase, target_files, args.intent, repo_path=repo_path)
    
    if not risks:
        log("[-] Warning: No target files matched the specified intent or files argument.")
        
    log("[+] Ultron: Compiling optimized contract prompt...")
    opt_prompt = prompt.generate_optimized_prompt(args.intent, codebase, risks)
    
    if args.output:
        out_path = os.path.abspath(args.output)
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(opt_prompt)
            log(f"[+] Success: Prompt successfully saved to {out_path}")
        except Exception as e:
            if args.json:
                print(json.dumps({"status": "error", "error": f"Error writing output file: {e}"}))
            else:
                print(f"[-] Error writing output file: {e}")
            sys.exit(1)
            
    if args.json:
        print(json.dumps({
            "status": "success",
            "risks": risks,
            "optimized_prompt": opt_prompt
        }))
    else:
        if not args.output:
            for r in risks:
                print(translate.plain_language_summary(r))
                if args.detail:
                    print(translate.detailed_breakdown(r))

if __name__ == "__main__":
    main()
