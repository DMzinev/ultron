# Single-File Launcher for Ultron Cognitive Repository Engine
import os
import sys
import time
import webbrowser
import threading

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Error vocabulary (shared with frontend) ──────────────────────────
PORT_IN_USE = "PORT_IN_USE"
_FALLBACK_PORTS = [8000, 8001, 8002]


def _safe_reconfigure_console():
    """Guard against Windows cp1252 console crashes on non-ASCII output."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass  # Already reconfigured or not a real TTY


def launch_ultron():
    """
    Single-file entry point:
    1. Evaluates repository RKM facts & complexity
    2. Displays executive summary table
    3. Launches server & auto-opens browser
    """
    _safe_reconfigure_console()

    print("==================================================================================")
    print("           ULTRON COGNITIVE REPOSITORY ENGINE -- SINGLE-FILE LAUNCHER            ")
    print("==================================================================================")
    print("  [1/3] Initializing Repository Knowledge Model (RKM)...")

    try:
        from ultron.core.pipeline.orchestrator import analyze_repository
        run_id = analyze_repository(ROOT)
        print(f"  [+] Analysis Run Completed. Run ID: {run_id}")
    except Exception as e:
        print(f"  [*] Analysis note: {e}")

    print("\n  [2/3] Computing Executive Summary from Analysis Run...")
    try:
        from ultron.core import analyzer
        from ultron.core import risk as risk_mod
        codebase = analyzer.analyze_directory(ROOT)
        all_files = list(codebase.keys())
        risks = risk_mod.evaluate_risks(codebase, all_files, repo_path=ROOT)

        sorted_risks = sorted(risks, key=lambda r: r.impact_score, reverse=True)
        high_count = sum(1 for r in risks if r.level == "HIGH")
        health = max(40, round(100 - (high_count * 8)))

        top_risk = sorted_risks[0] if sorted_risks else None
        top_risk_str = f"{top_risk.file_path} (Complexity: {top_risk.complexity})" if top_risk else "None detected"

        print("-" * 82)
        print(f"  REPOSITORY HEALTH:  [ {health} / 100 ]  ({len(all_files)} modules scanned)")
        print(f"  TOP RISK:           {top_risk_str}")
        print(f"  HIGH RISKS:         {high_count}  |  TOTAL MODULES:  {len(all_files)}")
        print("-" * 82)
    except Exception as e:
        print(f"  [*] Summary note: {e}")

    # ── Port fallback loop ────────────────────────────────────────────
    from ultron.interfaces.server import serve
    bound_port = None

    for port in _FALLBACK_PORTS:
        try:
            print(f"\n  [3/3] Starting Server on http://localhost:{port}/ ...")

            def auto_open_browser(p=port):
                time.sleep(1.2)
                try:
                    webbrowser.open(f"http://localhost:{p}/")
                except Exception:
                    pass

            threading.Thread(target=auto_open_browser, daemon=True).start()
            bound_port = port
            serve(port=port)
            break  # serve_forever blocks; break is reached only after shutdown
        except OSError as e:
            if "address already in use" in str(e).lower() or getattr(e, "errno", 0) == 10048:
                print(f"  [!] Port {port} is already in use. Trying next port...")
                continue
            else:
                print(f"  [-] Server failed: {e}")
                break
        except KeyboardInterrupt:
            print("\n  [+] Ultron server stopped.")
            break
        except Exception as e:
            print(f"  [-] Server error: {e}")
            break
    else:
        # All ports exhausted
        print("\n  [-] Could not start server. Ports 8000-8002 are all in use.")
        print("      Close the process using one of those ports, or run:")
        print("      python -c \"from ultron.interfaces.server import serve; serve(port=9000)\"")


if __name__ == "__main__":
    launch_ultron()
