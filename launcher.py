#!/usr/bin/env python3
"""
Ultron Cognitive Repository Engine — Zero-Install Standalone Launcher
Run directly: python launcher.py [command] [options]
"""
import os
import sys
import time
import json
import argparse
import webbrowser
import threading

# Setup Root Path for Direct Zero-Install Execution
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

FALLBACK_PORTS = [8000, 8001, 8002, 8080, 9000]


def _safe_reconfigure_console():
    """Guard against Windows cp1252 console crashes on Unicode characters."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _render_health_bar(health_score: int, width: int = 10) -> str:
    """Renders a robust text-based visual health gauge."""
    clamped = max(0, min(100, int(health_score)))
    filled = int(round((clamped / 100.0) * width))
    bar = "=" * filled + "-" * (width - filled)
    status = "HEALTHY" if clamped >= 80 else "MODERATE" if clamped >= 60 else "DEGRADED"
    return f"[{bar}] {status}"


def _get_workspace_summary(repo_path: str):
    """Computes fast AST metrics and returns summary statistics."""
    try:
        from ultron.core import analyzer
        from ultron.core.risk import scoring
        codebase = analyzer.analyze_directory(repo_path)
        if not codebase:
            return 100, 0, "None detected", []
        all_files = list(codebase.keys())
        target_files = [f for f in all_files if f.endswith(".py")]
        risks = scoring.evaluate_risks(codebase, target_files, repo_path=repo_path)
        high_count = sum(1 for r in risks if getattr(r, "level", "LOW") == "HIGH")
        health = max(40, round(100 - (high_count * 8)))
        
        top_risk_desc = "None detected (Repository Clean)"
        if risks:
            sorted_risks = sorted(risks, key=lambda r: getattr(r, "impact_score", 0), reverse=True)
            top = sorted_risks[0]
            top_risk_desc = f"{getattr(top, 'file_path', getattr(top, 'file', 'unknown.py'))} (Complexity: {getattr(top, 'complexity', 1)}, Level: {getattr(top, 'level', 'LOW')})"
        return health, len(all_files), top_risk_desc, risks
    except Exception as e:
        return 85, 0, f"Analysis fallback: {e}", []


def print_welcoming_card(repo_path: str, health: int, file_count: int, top_risk: str):
    """Prints the Developer HUD welcoming card."""
    print("=" * 82)
    print("                 ULTRON -- AI ARCHITECTURAL RISK ENGINE (v0.2.0)                  ")
    print("=" * 82)
    print(f"  Target Workspace:   {repo_path}")
    print(f"  Modules Scanned:    {file_count} source files")
    print(f"  Repository Health:  [ {health} / 100 ]  {_render_health_bar(health)}")
    print("-" * 82)
    print(f"  TOP ARCHITECTURAL HOTSPOT:")
    print(f"    * {top_risk}")
    print("-" * 82)
    print("  QUICK ACTIONS (Run directly in terminal):")
    print("    [1] Start Web Dashboard:   python launcher.py")
    print("    [2] Generate AI Fix Prompt: python launcher.py fix --top")
    print("    [3] Connect MCP to IDE:     python launcher.py mcp")
    print("    [4] Run CI Quality Gate:    python launcher.py gate --strict")
    print("=" * 82)


def _open_browser_delayed(port: int, delay: float = 1.0):
    def _target():
        time.sleep(delay)
        try:
            webbrowser.open(f"http://localhost:{port}/")
        except Exception:
            pass
    threading.Thread(target=_target, daemon=True).start()


def run_dashboard_server(port: int = 8000, repo_path: str = ROOT, open_browser: bool = True):
    """Starts local web server with automatic port-in-use fallback."""
    from ultron.interfaces.server import serve
    
    ports_to_try = [port] + [p for p in FALLBACK_PORTS if p != port]
    for p in ports_to_try:
        try:
            print(f"\n[*] Starting Ultron Dashboard on http://localhost:{p}/ ...")
            if open_browser:
                _open_browser_delayed(p)
            serve(port=p, auto_fallback=False, target_repo=repo_path)
            return
        except OSError as e:
            err_str = str(e).lower()
            if "address already in use" in err_str or getattr(e, "errno", 0) in (10048, 48, 98):
                print(f"[!] Port {p} is currently in use. Trying next port...")
                continue
            print(f"[-] Server error on port {p}: {e}")
            break
        except KeyboardInterrupt:
            print("\n[+] Ultron server stopped.")
            return
    print("[-] All candidate ports are busy. Specify a custom port via: python launcher.py --port <PORT>")


def main():
    _safe_reconfigure_console()
    
    # Delegate CLI subcommands if supplied (e.g. python launcher.py fix --top or python launcher.py --repo my-repo fix)
    subcommands = {"demo", "scan", "suggest", "calibrate", "report", "ci", "gate", "mcp", "init", "analyze", "check", "explain", "history", "dashboard", "fix"}
    if any(arg in subcommands for arg in sys.argv[1:]):
        from ultron.interfaces.ultron import main as cli_main
        sys.exit(cli_main(sys.argv[1:]))
        
    parser = argparse.ArgumentParser(description="Ultron Standalone Launcher")
    parser.add_argument("--port", type=int, default=8000, help="Web dashboard port (default: 8000)")
    parser.add_argument("--repo", default=ROOT, help="Repository root path (default: current)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    parser.add_argument("--cli", action="store_true", help="Show workspace HUD and exit without starting web server")
    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo)
    health, file_count, top_risk, _ = _get_workspace_summary(repo_path)
    print_welcoming_card(repo_path, health, file_count, top_risk)

    if args.cli:
        sys.exit(0)

    run_dashboard_server(port=args.port, repo_path=repo_path, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
