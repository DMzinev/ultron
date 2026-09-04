"""Ultron root launcher (compatible with launcher.py and legacy start script)."""
import os
import sys
import time
import webbrowser
import threading

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PORT_IN_USE = "PORT_IN_USE"
_FALLBACK_PORTS = [8000, 8001, 8002]


def _safe_reconfigure_console():
    """Guard against Windows cp1252 console crashes on non-ASCII output."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _init_rkm(repo_path):
    """Run initial RKM analysis on repository."""
    try:
        from ultron.core.pipeline.orchestrator import analyze_repository, compute_repository_content_hash
        bundle = analyze_repository(repo_path)
        try:
            from ultron.interfaces import server
            norm_p = os.path.normpath(repo_path).replace("\\", "/")
            raw_hash = compute_repository_content_hash(repo_path, bundle.files)
            server._ANALYSIS_CACHE["repo_path"] = norm_p
            server._ANALYSIS_CACHE["bundle"] = bundle
            server._ANALYSIS_CACHE["content_hash"] = raw_hash
        except Exception:
            pass
        return bundle
    except Exception as e:
        print(f"  [*] Analysis note: {e}")
        return None


def _extract_summary_data(bundle, repo_path):
    """Extract files and risks from bundle or direct fallback analysis."""
    if bundle:
        return bundle.files, bundle.risks
    from ultron.core import analyzer
    from ultron.core import risk as risk_mod
    codebase = analyzer.analyze_directory(repo_path)
    all_files = list(codebase.keys())
    risks = risk_mod.evaluate_risks(codebase, all_files, repo_path=repo_path)
    return all_files, risks


def _format_top_risk(risks):
    """Format top risk description string."""
    if not risks:
        return "None detected"
    sorted_risks = sorted(risks, key=lambda r: r.impact_score, reverse=True)
    top = sorted_risks[0]
    return f"{top.file_path} (Complexity: {top.complexity})"


def _print_executive_summary(repo_path, bundle):
    """Compute and display executive summary metrics."""
    try:
        all_files, risks = _extract_summary_data(bundle, repo_path)
        high_count = sum(1 for r in risks if r.level == "HIGH")
        health = max(40, round(100 - (high_count * 8)))
        top_risk_str = _format_top_risk(risks)

        print("-" * 82)
        print(f"  REPOSITORY HEALTH:  [ {health} / 100 ]  ({len(all_files)} modules scanned)")
        print(f"  TOP RISK:           {top_risk_str}")
        print(f"  HIGH RISKS:         {high_count}  |  TOTAL MODULES:  {len(all_files)}")
        print("-" * 82)
    except Exception as e:
        print(f"  [*] Summary note: {e}")


def _is_port_in_use_error(exc):
    """Determine whether an OSError indicates that the port is already in use."""
    err_str = str(exc).lower()
    return (
        "address already in use" in err_str
        or "only one usage" in err_str
        or getattr(exc, "errno", 0) in (10048, 48, 98)
        or getattr(exc, "winerror", 0) == 10048
    )


def _open_browser_delayed(port, delay=1.2):
    """Open browser in a background thread after a brief delay."""
    def _target():
        time.sleep(delay)
        try:
            webbrowser.open(f"http://localhost:{port}/")
        except Exception:
            pass

    threading.Thread(target=_target, daemon=True).start()


def _serve_port(port):
    """Attempt to run the server on port."""
    from ultron.interfaces.server import serve

    _open_browser_delayed(port)
    try:
        serve(port=port)
        return "STOPPED"
    except OSError as e:
        if _is_port_in_use_error(e):
            return "IN_USE"
        return "FAILED"
    except KeyboardInterrupt:
        return "STOPPED"
    except Exception:
        return "FAILED"


def _run_server_loop(ports=_FALLBACK_PORTS):
    """Iterate candidate ports until server binds or list is exhausted."""
    for port in ports:
        status = _serve_port(port)
        if status != "IN_USE":
            return True
    return False


def launch_ultron():
    """Single-file entry point."""
    _safe_reconfigure_console()
    bundle = _init_rkm(ROOT)
    _print_executive_summary(ROOT, bundle)
    _run_server_loop(_FALLBACK_PORTS)


if __name__ == "__main__":
    from launcher import main
    main()
