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

# Use the literal loopback IP rather than 'localhost'. The server listens on IPv4 only,
# and on Windows 'localhost' resolves to ::1 first, adding ~2s to every single request.
SERVER_HOST = "127.0.0.1"


def _safe_reconfigure_console():
    """Guard against Windows cp1252 console crashes on non-ASCII output."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass  # Already reconfigured or not a real TTY

def _init_rkm(root):
    """Initializes RKM by running repository analysis. Returns bundle or None on failure."""
    try:
        from ultron.core.pipeline.orchestrator import analyze_repository
        bundle = analyze_repository(root)
        print(f"  [+] Analysis Run Completed. Run ID: {getattr(bundle, 'repo_uuid', bundle)}")
        return bundle
    except Exception as e:
        print(f"  [*] Analysis note: {e}")
        return None


def _extract_summary_data(bundle, root):
    """Extracts (files, risks) from bundle or calculates them directly if bundle is None."""
    if bundle is not None and hasattr(bundle, "files") and hasattr(bundle, "risks"):
        return bundle.files, bundle.risks

    try:
        from ultron.core import analyzer
        from ultron.core import risk as risk_mod
        codebase = analyzer.analyze_directory(root)
        all_files = list(codebase.keys())
        risks = risk_mod.evaluate_risks(codebase, all_files, repo_path=root)
        return all_files, risks
    except Exception as e:
        print(f"  [*] Summary extraction note: {e}")
        return [], []


def _format_top_risk(risks):
    """Formats the top risk string or returns 'None detected'."""
    if not risks:
        return "None detected"
    sorted_risks = sorted(risks, key=lambda r: getattr(r, "impact_score", 0), reverse=True)
    top_risk = sorted_risks[0]
    return f"{top_risk.file_path} (Complexity: {top_risk.complexity})"


def _print_executive_summary(root, bundle):
    """Prints executive summary table."""
    try:
        all_files, risks = _extract_summary_data(bundle, root)
        high_count = sum(1 for r in risks if getattr(r, "level", "") == "HIGH")
        health = max(40, round(100 - (high_count * 8)))
        top_risk_str = _format_top_risk(risks)

        print("-" * 82)
        print(f"  REPOSITORY HEALTH:  [ {health} / 100 ]  ({len(all_files)} modules scanned)")
        print(f"  TOP RISK:           {top_risk_str}")
        print(f"  HIGH RISKS:         {high_count}  |  TOTAL MODULES:  {len(all_files)}")
        print("-" * 82)
    except Exception as e:
        print(f"  [*] Summary note: {e}")


def _is_port_in_use_error(e):
    """Checks whether an exception indicates the port is in use."""
    err_str = str(e).lower()
    if "address already in use" in err_str:
        return True
    if getattr(e, "winerror", None) == 10048 or getattr(e, "errno", None) in (10048, 98):
        return True
    return False


def _open_browser_delayed(port, delay=1.2):
    """Opens default browser to server after delay in a background thread."""
    def auto_open_browser(p=port):
        time.sleep(delay)
        try:
            webbrowser.open(f"http://{SERVER_HOST}:{p}/")
        except Exception:
            pass

    t = threading.Thread(target=auto_open_browser, daemon=True)
    t.start()
    return t


def _serve_port(port):
    """Attempts to bind and serve on the specified port. Returns 'STOPPED', 'IN_USE', or 'FAILED'."""
    from ultron.interfaces.server import serve
    _open_browser_delayed(port)
    try:
        serve(port=port)
        return "STOPPED"
    except OSError as e:
        if _is_port_in_use_error(e):
            print(f"  [!] Port {port} is already in use. Trying next port...")
            return "IN_USE"
        else:
            print(f"  [-] Server failed: {e}")
            return "FAILED"
    except KeyboardInterrupt:
        print("\n  [+] Ultron server stopped.")
        return "STOPPED"
    except Exception as e:
        print(f"  [-] Server error: {e}")
        return "FAILED"


def _run_server_loop(ports):
    """Tries ports in order until one succeeds or all fail."""
    for port in ports:
        print(f"\n  [3/3] Starting Server on http://{SERVER_HOST}:{port}/ ...")
        status = _serve_port(port)
        if status == "STOPPED":
            return True
        elif status == "IN_USE":
            continue
        elif status == "FAILED":
            return False

    print("\n  [-] Could not start server. Ports are all in use.")
    print("      Close the process using one of those ports, or run:")
    print("      python -c \"from ultron.interfaces.server import serve; serve(port=9000)\"")
    return False


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
    bundle = _init_rkm(ROOT)

    print("\n  [2/3] Computing Executive Summary from Analysis Run...")
    _print_executive_summary(ROOT, bundle)

    print(f"\n  [3/3] Starting Server...")
    _run_server_loop(_FALLBACK_PORTS)


if __name__ == "__main__":
    launch_ultron()
