"""
launcher/tray_launcher.py — Ultron system-tray launcher

Usage (dev mode):
    pip install -e .[tray]
    python launcher/tray_launcher.py

Usage (production):
    Build ultron-server.exe first:
        pyinstaller ultron.spec
    Then run:
        python launcher/tray_launcher.py
    (The launcher auto-detects the .exe and uses it when present.)

Tray menu:
    Open Dashboard  — opens http://127.0.0.1:8000 in the default browser
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
import socket

# ---------------------------------------------------------------------------
# PIL / pystray guard — optional desktop dependencies
# ---------------------------------------------------------------------------
try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None
    ImageDraw = None

try:
    import pystray
except ImportError:
    pystray = None

HAS_TRAY_DEPS = (Image is not None and pystray is not None)


class _HeadlessIcon:
    """Headless mock representation for tray icon when Pillow is absent."""
    def __init__(self, size=(64, 64), mode="RGBA"):
        self.size = size
        self.mode = mode


class _HeadlessMenu:
    """Headless mock representation for tray menu when pystray is absent."""
    def __init__(self, *items):
        self.items = items


# ---------------------------------------------------------------------------
# Constants & Runtime State
# ---------------------------------------------------------------------------
_LAUNCHER_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT    = os.path.dirname(_LAUNCHER_DIR)          # one level up from launcher/

CONFIG_DIR  = os.path.join(_REPO_ROOT, "ultron", ".ultron")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

SERVER_EXE  = os.path.join(_REPO_ROOT, "dist", "ultron-server.exe")
SERVER_PORT = 8000
BASE_URL    = f"http://127.0.0.1:{SERVER_PORT}"
_active_base_url = BASE_URL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_available_port(ports=None):
    """Find the first available TCP port among candidate ports."""
    if ports is None:
        ports = [8000, 8001, 8002]
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return ports[0] if ports else 8000


def _read_repo_root():
    """Return stored repo_root string, or None if absent / unreadable."""
    try:
        if not os.path.exists(CONFIG_FILE):
            return None
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
    """Generate a minimal 64x64 tray icon programmatically using Pillow or headless fallback."""
    if Image is None or ImageDraw is None:
        return _HeadlessIcon(size=(64, 64), mode="RGBA")
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


def _build_server_cmd(port=None):
    """Return the command list to launch the server subprocess."""
    if os.path.isfile(SERVER_EXE):
        cmd = [SERVER_EXE]
    else:
        # Dev-mode fallback: run as module (requires ultron package on PYTHONPATH)
        cmd = [sys.executable, "-m", "ultron.interfaces.server"]
    if port is not None:
        cmd.extend(["--port", str(port)])
    return cmd


def _terminate_process(proc):
    """Terminate process cleanly; escalate to kill on timeout."""
    if proc is None:
        return
    if proc.poll() is not None:
        # Already exited
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        # Did not exit within 5 s — escalate
        proc.kill()
        proc.wait()


def _close_log_file():
    """Safely close and reset the server log file handle."""
    global _log_file_handle
    if _log_file_handle and _log_file_handle != subprocess.DEVNULL:
        try:
            _log_file_handle.close()
        except Exception:
            pass
    _log_file_handle = None


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------

_server_proc = None  # type: subprocess.Popen | None
_log_file_handle = None


def _start_server(port=None):
    """Start the server subprocess. Stores handle in _server_proc."""
    global _server_proc, _log_file_handle, _active_base_url
    if port is not None:
        _active_base_url = f"http://127.0.0.1:{port}"
    cmd = _build_server_cmd(port)
    env = os.environ.copy()
    env["ULTRON_NO_OPEN"] = "1"   # suppress server's own browser-open
    
    log_dir = os.path.join(os.path.expanduser("~"), ".ultron")
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, "server.log")
        _log_file_handle = open(log_file_path, "a", encoding="utf-8")
    except Exception as exc:
        print(f"[tray] Failed to setup log file: {exc}", file=sys.stderr)
        _log_file_handle = subprocess.DEVNULL

    print(f"[tray] Starting server: {' '.join(cmd)}", file=sys.stderr)
    _server_proc = subprocess.Popen(
        cmd,
        env=env,
        cwd=_REPO_ROOT,
        stdout=_log_file_handle,
        stderr=_log_file_handle,
    )


def _stop_server():
    """Gracefully terminate the server; escalate to kill on timeout."""
    global _server_proc
    try:
        if _server_proc is not None:
            _terminate_process(_server_proc)
            _server_proc = None
    finally:
        _close_log_file()


# ---------------------------------------------------------------------------
# Tray menu & callbacks
# ---------------------------------------------------------------------------

def _build_tray_menu():
    """Build and return the system tray menu, or headless fallback."""
    if pystray is None:
        return _HeadlessMenu("Open Dashboard", "Settings", "View Log", "Quit")
    return pystray.Menu(
        pystray.MenuItem("Open Dashboard", _on_open_dashboard, default=True),
        pystray.MenuItem("Settings",       _on_settings),
        pystray.MenuItem("View Log",       _on_view_log),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit",           _on_quit),
    )


def _on_open_dashboard(icon, item):   # noqa: ARG001
    _open_url(_active_base_url)


def _on_settings(icon, item):         # noqa: ARG001
    _open_url(f"{_active_base_url}/folder_picker.html")


def _on_view_log(icon, item):         # noqa: ARG001
    log_dir = os.path.join(os.path.expanduser("~"), ".ultron")
    log_file_path = os.path.join(log_dir, "server.log")
    if os.path.isfile(log_file_path) and os.path.getsize(log_file_path) > 0:
        try:
            if sys.platform == "win32":
                os.startfile(log_file_path)
            else:
                webbrowser.open(pathlib.Path(log_file_path).as_uri())
        except Exception as exc:
            print(f"[tray] Failed to open log file: {exc}", file=sys.stderr)


def _on_quit(icon, item):             # noqa: ARG001
    _stop_server()
    if icon is not None and hasattr(icon, "stop"):
        icon.stop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    global _active_base_url
    if not HAS_TRAY_DEPS:
        sys.exit(
            "ERROR: Pillow and pystray are required for tray launcher.\n"
            "Run: pip install -e .[tray]"
        )

    port = _find_available_port([SERVER_PORT, 8001, 8002])
    _active_base_url = f"http://127.0.0.1:{port}"

    # Check if repo root is configured; if not, open folder picker first
    repo_root = _read_repo_root()
    if repo_root is None:
        print(
            "[tray] No valid repo root configured — opening folder picker.",
            file=sys.stderr,
        )
        # Start server first (picker page is served by it), then open picker
        _start_server(port)
        time.sleep(1.5)   # give the server a moment to bind
        _open_url(f"{_active_base_url}/folder_picker.html")
    else:
        _start_server(port)

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
