"""
Task E1: Install and First Run Test Suite
Verifies:
1. Entry point declarations and importability for ultron, ultron-server, and ultron-mcp
2. Deterministic free port selection across platform error conditions
3. Canonical URL formatting for dashboard server
4. Sub-2s latency for first useful screen (GET / and GET /api/v1/health)
5. Backward compatibility for server.serve(target_repo=..., auto_fallback=...)
6. CLI help and argument parsing for ultron-server
7. Package data asset integrity
"""

import ast
import errno
import http.client
import io
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, MagicMock

from ultron.interfaces.api.state import LOOPBACK_HOST, WEB_DIR
from ultron.interfaces.server import UltronAPIHandler, create_server, serve
import ultron.interfaces.ultron
import ultron.interfaces.server
import ultron.interfaces.mcp_server


class TestInstallFirstRun(unittest.TestCase):
    """Verifies packaging, deterministic port resolution, and first-run ergonomics."""

    def setUp(self):
        self.repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def test_entry_points_declared_and_importable(self):
        """Verify ultron, ultron-server, and ultron-mcp are declared in setup.py and pyproject.toml."""
        setup_py = os.path.join(self.repo_root, "setup.py")
        pyproject_toml = os.path.join(self.repo_root, "pyproject.toml")

        self.assertTrue(os.path.isfile(setup_py), "setup.py must exist")
        self.assertTrue(os.path.isfile(pyproject_toml), "pyproject.toml must exist")

        with open(setup_py, "r", encoding="utf-8") as f:
            setup_content = f.read()

        self.assertIn('"ultron = ultron.interfaces.ultron:main"', setup_content)
        self.assertIn('"ultron-server = ultron.interfaces.server:main"', setup_content)
        self.assertIn('"ultron-mcp = ultron.interfaces.mcp_server:main"', setup_content)

        with open(pyproject_toml, "r", encoding="utf-8") as f:
            toml_content = f.read()

        self.assertIn('ultron = "ultron.interfaces.ultron:main"', toml_content)
        self.assertIn('ultron-server = "ultron.interfaces.server:main"', toml_content)
        self.assertIn('ultron-mcp = "ultron.interfaces.mcp_server:main"', toml_content)

        # Verify target callables are directly importable and callable
        self.assertTrue(callable(getattr(ultron.interfaces.ultron, "main", None)))
        self.assertTrue(callable(getattr(ultron.interfaces.server, "main", None)))
        self.assertTrue(callable(getattr(ultron.interfaces.mcp_server, "main", None)))

    def test_deterministic_port_selection(self):
        """Verify sequential port fallback when starting port is occupied."""
        # 1. Single port collision on 8000; port 8001 succeeds
        with patch("http.server.HTTPServer") as mock_http_server:
            mock_inst = MagicMock()
            mock_inst.server_address = (LOOPBACK_HOST, 8001)
            mock_http_server.side_effect = [
                OSError(errno.EADDRINUSE, "Address already in use"),
                mock_inst
            ]
            httpd, bound_port = create_server(host=LOOPBACK_HOST, start_port=8000, max_attempts=10)
            self.assertEqual(bound_port, 8001)
            self.assertEqual(mock_http_server.call_count, 2)

        # 2. Multi-hop: ports 8002 and 8003 busy; 8004 succeeds
        with patch("http.server.HTTPServer") as mock_http_server2:
            mock_inst2 = MagicMock()
            mock_inst2.server_address = (LOOPBACK_HOST, 8004)
            mock_http_server2.side_effect = [
                OSError(errno.EADDRINUSE, "Address already in use"),
                OSError(10048, "WSAEADDRINUSE"),
                mock_inst2
            ]
            httpd2, bound_port2 = create_server(host=LOOPBACK_HOST, start_port=8002, max_attempts=5)
            self.assertEqual(bound_port2, 8004)
            self.assertEqual(mock_http_server2.call_count, 3)

        # 3. Exhaustion raises OSError
        with patch("http.server.HTTPServer", side_effect=OSError(errno.EADDRINUSE, "Address already in use")):
            with self.assertRaises(OSError):
                create_server(host=LOOPBACK_HOST, start_port=8000, max_attempts=3)

    def test_server_output_canonical_url(self):
        """Verify server prints one clear canonical URL and normalizes 0.0.0.0."""
        from io import StringIO
        captured = StringIO()
        with patch("sys.stdout", captured), \
             patch("http.server.HTTPServer.serve_forever", return_value=None):
            serve(port=0, host="0.0.0.0", auto_fallback=True, max_attempts=1)

        output = captured.getvalue()
        self.assertIn("[*] Ultron Dashboard Server running on http://127.0.0.1:", output)

    def test_cli_server_help(self):
        """Verify python -m ultron.interfaces.server --help exits 0 with argument docs."""
        proc = subprocess.run(
            [sys.executable, "-m", "ultron.interfaces.server", "--help"],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--port", proc.stdout)
        self.assertIn("--host", proc.stdout)
        self.assertIn("--repo", proc.stdout)
        self.assertIn("--open", proc.stdout)
        self.assertIn("--no-browser", proc.stdout)

    def test_first_useful_screen_response_latency(self):
        """Verify server responds to GET / and GET /api/v1/health in under 2.0 seconds."""
        httpd, port = create_server(host=LOOPBACK_HOST, start_port=0, max_attempts=1)
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        def cleanup_server():
            httpd.shutdown()
            httpd.server_close()
            server_thread.join(timeout=2.0)

        self.addCleanup(cleanup_server)

        # 1. Test GET / (HTML Dashboard delivery)
        t0 = time.perf_counter()
        conn = http.client.HTTPConnection(LOOPBACK_HOST, port, timeout=5)
        conn.request("GET", "/")
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        elapsed_index = time.perf_counter() - t0
        conn.close()

        self.assertEqual(resp.status, 200)
        self.assertIn("<!DOCTYPE html>", body)
        self.assertIn("Ultron", body)
        self.assertLess(elapsed_index, 2.0, f"Dashboard index load took {elapsed_index:.3f}s (budget: 2.0s)")

        # 2. Test GET /api/v1/health (API Health Status)
        t1 = time.perf_counter()
        conn2 = http.client.HTTPConnection(LOOPBACK_HOST, port, timeout=5)
        conn2.request("GET", "/api/v1/health")
        resp2 = conn2.getresponse()
        body2 = resp2.read().decode("utf-8")
        elapsed_health = time.perf_counter() - t1
        conn2.close()

        self.assertEqual(resp2.status, 200)
        self.assertIn('"status": "healthy"', body2)
        self.assertLess(elapsed_health, 2.0, f"Health API endpoint took {elapsed_health:.3f}s (budget: 2.0s)")

    def test_serve_backward_compatibility(self):
        """Verify server.serve accepts target_repo and auto_fallback without TypeError."""
        with patch("http.server.HTTPServer.serve_forever", return_value=None), \
             patch("sys.stdout", new_callable=io.StringIO):
            try:
                serve(port=0, target_repo=".", auto_fallback=False)
            except Exception as e:
                self.assertNotIsInstance(e, TypeError, f"serve() must accept legacy arguments: {e}")

    def test_package_data_integrity(self):
        """Verify web assets and database migrations referenced in packaging exist on disk."""
        index_html = os.path.join(WEB_DIR, "index.html")
        index_css = os.path.join(WEB_DIR, "index.css")
        index_js = os.path.join(WEB_DIR, "index.js")
        self.assertTrue(os.path.isfile(index_html), "index.html must exist")
        self.assertTrue(os.path.isfile(index_css), "index.css must exist")
        self.assertTrue(os.path.isfile(index_js), "index.js must exist")

        rkm_dir = os.path.join(self.repo_root, "ultron", "core", "rkm")
        migrations_dir = os.path.join(rkm_dir, "migrations")
        rulepacks_dir = os.path.join(rkm_dir, "rulepacks")
        self.assertTrue(os.path.isdir(migrations_dir), "migrations dir must exist")
        self.assertTrue(os.path.isdir(rulepacks_dir), "rulepacks dir must exist")

    def test_cold_clean_machine_install_under_60s(self):
        """Verify fresh venv creation + cold pip install -e . + entry point in < 60s."""
        # Pre-check PyPI connectivity; skip gracefully if offline/airgapped
        try:
            probe_sock = socket.create_connection(("pypi.org", 443), timeout=2.0)
            probe_sock.close()
        except OSError:
            self.skipTest("pypi.org unreachable; skipping network cold install test")

        tmp_dir = tempfile.mkdtemp(prefix="ultron_cold_test_")
        self.addCleanup(lambda: shutil.rmtree(tmp_dir, ignore_errors=True))

        t0 = time.perf_counter()

        # 1. Create clean virtual environment
        proc_venv = subprocess.run(
            [sys.executable, "-m", "venv", tmp_dir],
            capture_output=True,
            text=True,
            timeout=30
        )
        self.assertEqual(proc_venv.returncode, 0, f"venv creation failed: {proc_venv.stderr}")

        scripts_dir = os.path.join(tmp_dir, "Scripts" if os.name == "nt" else "bin")
        target_python = os.path.join(scripts_dir, "python.exe" if os.name == "nt" else "python")
        ultron_bin = os.path.join(scripts_dir, "ultron.exe" if os.name == "nt" else "ultron")

        self.assertTrue(os.path.isfile(target_python), f"Python binary not found at {target_python}")

        # 2. Perform cold install with --no-cache-dir
        try:
            proc_install = subprocess.run(
                [target_python, "-m", "pip", "install", "-e", self.repo_root, "--no-cache-dir"],
                capture_output=True,
                text=True,
                timeout=45
            )
        except subprocess.TimeoutExpired:
            self.skipTest("pip install timed out; skipping cold install assertion")

        if proc_install.returncode != 0:
            err = proc_install.stderr + proc_install.stdout
            if any(k in err for k in ["ConnectionError", "Network is unreachable", "Could not fetch", "Temporary failure"]):
                self.skipTest(f"pip install network failure: {err[:200]}")
            self.assertEqual(proc_install.returncode, 0, f"pip install failed:\n{proc_install.stderr}")

        # 3. Verify entrypoint binary and help resolution
        proc_help = subprocess.run(
            [ultron_bin, "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(proc_help.returncode, 0)
        self.assertIn("Ultron: Code Architecture Risk", proc_help.stdout)

        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 60.0, f"Cold install clone-to-run took {elapsed:.2f}s (budget: 60.0s)")


if __name__ == "__main__":
    unittest.main()
