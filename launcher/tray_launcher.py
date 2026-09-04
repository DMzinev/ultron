"""
launcher/tray_launcher.py — Ultron system-tray launcher

Usage (dev mode):
    pip install -r launcher/requirements-launcher.txt
    python launcher/tray_launcher.py

Usage (production):
    Build ultron-server.exe first:
        pyinstaller ultron.spec
    Then run:
        python launcher/tray_launcher.py
    (The launcher auto-detects the .exe and uses it when present.)

Tray menu:
    Open Dashboard  — opens http://localhost:8000 in the default browser
    Settings        — opens the folder-picker page in the default browser
    Quit            — gracefully terminates the server and exits
"""

import sys
import os
import json
import subprocess
import time
import webbrowser
import pathlib

# ---------------------------------------------------------------------------
# PIL / pystray guard — must come after stdlib imports so sys is available
# ---------------------------------------------------------------------------
try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit(
        "ERROR: Pillow is required.\n"
        "Run: pip install -r launcher/requirements-launcher.txt"
    )

try:
    import pystray
except ImportError:
    sys.exit(
        "ERROR: pystray is required.\n"
        "Run: pip install -r launcher/requirements-launcher.txt"
    )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_LAUNCHER_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT    = os.path.dirname(_LAUNCHER_DIR)          # one level up from launcher/

import socket
import atexit
import signal

CONFIG_DIR  = os.path.join(_REPO_ROOT, "ultron", ".ultron")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

SERVER_EXE  = os.path.join(_REPO_ROOT, "dist", "ultron-server.exe")
_FALLBACK_PORTS = [8000, 8001, 8002]
_active_port = 8000
_active_base_url = f"http://localhost:{_active_port}"

def _find_available_port(candidate_ports=_FALLBACK_PORTS):
    """Probe localhost sockets to discover an available port."""
    for p in candidate_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', p))
                return p
        except OSError:
            continue
    return candidate_ports[0]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_repo_root():
    """Return stored repo_root string, or None if absent / unreadable."""
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        val = cfg.get("repo_root")
        if isinstance(val, str) and os.path.isdir(val):
            return val
        return None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _open_url(url):
    """Open a URL in the default browser; log failures to stderr."""
    try:
        webbrowser.open(url)
    except Exception as exc:  # noqa: BLE001
        print(f"[tray] Could not open browser: {exc}", file=sys.stderr)


def _make_tray_icon():
    """Generate a minimal 64x64 tray icon programmatically using Pillow."""
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Cyan hexagon-ish filled circle — matches Ultron neon-cyan (#66fcf1)
    margin = 6
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(102, 252, 241, 255),
    )
    # Dark inner circle for a ring effect
    inner = 20
    draw.ellipse(
        [inner, inner, size - inner, size - inner],
        fill=(10, 11, 16, 255),
    )
    return img


def _build_server_cmd(port):
    """Return the command list to launch the server subprocess."""
    if os.path.isfile(SERVER_EXE):
        return [SERVER_EXE, "--port", str(port)]
    # Dev-mode fallback: run as module (requires ultron package on PYTHONPATH)
    return [sys.executable, "-m", "ultron.interfaces.server", "--port", str(port)]


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------

_server_proc = None  # type: subprocess.Popen | None
_log_file_handle = None


def _setup_log_file():
    """Prepare log file handle for server process output."""
    log_dir = os.path.join(os.path.expanduser("~"), ".ultron")
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, "server.log")
        return open(log_file_path, "a", encoding="utf-8")
    except Exception as exc:
        print(f"[tray] Failed to setup log file: {exc}", file=sys.stderr)
        return subprocess.DEVNULL


def _start_server():
    """Start the server subprocess. Stores handle in _server_proc."""
    global _server_proc, _log_file_handle, _active_port, _active_base_url
    _active_port = _find_available_port(_FALLBACK_PORTS)
    _active_base_url = f"http://localhost:{_active_port}"

    cmd = _build_server_cmd(_active_port)
    env = os.environ.copy()
    env["ULTRON_NO_OPEN"] = "1"   # suppress server's own browser-open
    
    _log_file_handle = _setup_log_file()
    print(f"[tray] Starting server on port {_active_port}: {' '.join(cmd)}", file=sys.stderr)
    _server_proc = subprocess.Popen(
        cmd,
        env=env,
        cwd=_REPO_ROOT,
        stdout=_log_file_handle,
        stderr=_log_file_handle,
    )


def _terminate_process(proc):
    """Gracefully terminate a subprocess; escalate to kill on timeout."""
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _close_log_file():
    """Safely close active log file handle."""
    global _log_file_handle
    if _log_file_handle and _log_file_handle != subprocess.DEVNULL:
        try:
            _log_file_handle.close()
        except Exception:
            pass
        _log_file_handle = None


def _stop_server():
    """Gracefully terminate the server; escalate to kill on timeout."""
    global _server_proc
    try:
        _terminate_process(_server_proc)
        _server_proc = None
    finally:
        _close_log_file()


atexit.register(_stop_server)
def _signal_handler(sig, frame):
    _stop_server()
    sys.exit(0)

try:
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _signal_handler)
except Exception:
    pass

# ---------------------------------------------------------------------------
# Tray menu callbacks
# ---------------------------------------------------------------------------

def _on_open_dashboard(icon, item):   # noqa: ARG001
    _open_url(_active_base_url)


def _on_settings(icon, item):         # noqa: ARG001
    _open_url(f"{_active_base_url}/folder_picker.html")


def _open_log_file_in_viewer(log_file_path):
    """Open log file using platform default viewer."""
    if sys.platform == "win32":
        os.startfile(log_file_path)
    else:
        webbrowser.open(pathlib.Path(log_file_path).as_uri())


def _on_view_log(icon, item):         # noqa: ARG001
    log_dir = os.path.join(os.path.expanduser("~"), ".ultron")
    log_file_path = os.path.join(log_dir, "server.log")
    if os.path.isfile(log_file_path) and os.path.getsize(log_file_path) > 0:
        try:
            _open_log_file_in_viewer(log_file_path)
        except Exception as exc:
            print(f"[tray] Failed to open log file: {exc}", file=sys.stderr)


def _on_quit(icon, item):             # noqa: ARG001
    _stop_server()
    icon.stop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _build_tray_menu():
    """Build and return the pystray Menu instance."""
    return pystray.Menu(
        pystray.MenuItem("Open Dashboard", _on_open_dashboard, default=True),
        pystray.MenuItem("Settings",       _on_settings),
        pystray.MenuItem("View Log",       _on_view_log),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit",           _on_quit),
    )


def main():
    # Check if repo root is configured; if not, open folder picker first
    repo_root = _read_repo_root()
    if repo_root is None:
        print(
            "[tray] No valid repo root configured — opening folder picker.",
            file=sys.stderr,
        )
        # Start server first (picker page is served by it), then open picker
        _start_server()
        time.sleep(1.5)   # give the server a moment to bind
        _open_url(f"{_active_base_url}/folder_picker.html")
    else:
        _start_server()

    # Build and run tray icon
    menu = _build_tray_menu()
    icon = pystray.Icon(
        name="ultron",
        icon=_make_tray_icon(),
        title="Ultron",
        menu=menu,
    )
    icon.run()


if __name__ == "__main__":
    main()
