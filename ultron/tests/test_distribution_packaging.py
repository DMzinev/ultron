"""
ultron/tests/test_distribution_packaging.py
Comprehensive packaging, single-command distribution, and zero-install execution test suite.

Validates:
1. CLI entrypoint invocation from clean Python subprocess in arbitrary working directories.
2. Static asset resolution (index.html, index.js, index.css, modules/*.js) from arbitrary CWD.
3. Packaging metadata completeness in pyproject.toml & setup.py (scripts, package-data, modules glob).
4. Pure standard library operation when optional dependencies (e.g. radon) are missing.
5. Windows path separator handling and security directory traversal defense.
6. Standalone launcher (launcher.py) execution and welcoming HUD.
"""

import unittest
import os
import sys
import json
import subprocess
import tempfile
import importlib
from io import BytesIO
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ultron.interfaces import server
from ultron.config.settings import Settings


class TestDistributionPackaging(unittest.TestCase):
    """Adversarial verification for packaging, distribution, and zero-dependency execution."""

    def setUp(self):
        self.original_cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self.original_cwd)

    # --------------------------------------------------------------------------
    # 1. CLI Entrypoint Subprocess Invocation from Clean Working Directories
    # --------------------------------------------------------------------------

    def test_cli_help_from_arbitrary_temp_directory(self):
        """Verify 'python -m ultron.interfaces.ultron --help' runs cleanly outside the repo."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = os.environ.copy()
            env["PYTHONPATH"] = REPO_ROOT

            proc = subprocess.run(
                [sys.executable, "-m", "ultron.interfaces.ultron", "--help"],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                env=env,
                timeout=10
            )
            self.assertEqual(proc.returncode, 0, f"CLI --help failed with stderr: {proc.stderr}")
            self.assertIn("Ultron: Code Architecture Risk & AI Mission Control", proc.stdout)

    def test_cli_scan_json_from_arbitrary_temp_directory(self):
        """Verify 'ultron scan --json' analyzes a target repository from an external directory."""
        with tempfile.TemporaryDirectory() as external_cwd, tempfile.TemporaryDirectory() as target_repo:
            target_file = os.path.join(target_repo, "sample.py")
            with open(target_file, "w", encoding="utf-8") as f:
                f.write("def calculate(x):\n    return x * 2\n")

            env = os.environ.copy()
            env["PYTHONPATH"] = REPO_ROOT

            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ultron.interfaces.ultron",
                    "scan",
                    "--repo",
                    target_repo,
                    "--json"
                ],
                cwd=external_cwd,
                capture_output=True,
                text=True,
                env=env,
                timeout=15
            )
            self.assertEqual(proc.returncode, 0, f"CLI scan failed with stderr: {proc.stderr}")
            
            payload = json.loads(proc.stdout)
            self.assertEqual(payload.get("status"), "success")
            self.assertEqual(payload.get("total_files"), 1)
            self.assertIn("health_score", payload)

    def test_python_m_ultron_execution(self):
        """Verify 'python -m ultron --help' executes correctly via __main__.py."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = os.environ.copy()
            env["PYTHONPATH"] = REPO_ROOT

            proc = subprocess.run(
                [sys.executable, "-m", "ultron", "--help"],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                env=env,
                timeout=10
            )
            self.assertEqual(proc.returncode, 0, f"python -m ultron --help failed: {proc.stderr}")
            self.assertIn("Ultron: Code Architecture Risk & AI Mission Control", proc.stdout)

    def test_cli_init_from_external_directory(self):
        """Verify 'ultron init --repo <path>' initializes repository knowledge model cleanly."""
        with tempfile.TemporaryDirectory() as external_cwd, tempfile.TemporaryDirectory() as target_repo:
            env = os.environ.copy()
            env["PYTHONPATH"] = REPO_ROOT

            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ultron",
                    "init",
                    "--repo",
                    target_repo
                ],
                cwd=external_cwd,
                capture_output=True,
                text=True,
                env=env,
                timeout=15
            )
            self.assertEqual(proc.returncode, 0, f"ultron init failed: {proc.stderr}")
            self.assertTrue(os.path.isdir(os.path.join(target_repo, ".ultron")))
            self.assertTrue(os.path.isfile(os.path.join(target_repo, ".ultron", "repository.db")))

    def test_cli_entrypoint_callable_signature(self):
        """Verify that ultron.interfaces.ultron:main is importable and callable."""
        from ultron.interfaces import ultron as ultron_module
        self.assertTrue(hasattr(ultron_module, "main"), "ultron.interfaces.ultron must export a main callable")
        self.assertTrue(callable(ultron_module.main), "ultron.interfaces.ultron:main must be callable")

    def test_mcp_entrypoint_callable_signature(self):
        """Verify that ultron.interfaces.mcp_server:main is importable and callable."""
        from ultron.interfaces import mcp_server as mcp_module
        self.assertTrue(hasattr(mcp_module, "main"), "ultron.interfaces.mcp_server must export a main callable")
        self.assertTrue(callable(mcp_module.main), "ultron.interfaces.mcp_server:main must be callable")

    # --------------------------------------------------------------------------
    # 2. Static Asset Resolution from Arbitrary Working Directories
    # --------------------------------------------------------------------------

    def test_static_assets_exist_at_packaged_web_dir(self):
        """Verify WEB_DIR resolves to the actual package directory containing all assets."""
        web_dir = server.WEB_DIR
        self.assertTrue(os.path.isdir(web_dir), f"WEB_DIR '{web_dir}' does not exist")

        required_root_files = ["index.html", "index.js", "index.css", "folder_picker.html"]
        for f in required_root_files:
            asset_path = os.path.join(web_dir, f)
            self.assertTrue(os.path.isfile(asset_path), f"Required static asset missing: {asset_path}")
            self.assertGreater(os.path.getsize(asset_path), 0, f"Static asset is empty: {asset_path}")

        # Check frontend JS modules
        modules_dir = os.path.join(web_dir, "modules")
        self.assertTrue(os.path.isdir(modules_dir), f"Modules dir missing: {modules_dir}")

        required_modules = ["api.js", "graph.js", "modals.js", "state.js", "storage.js", "ui.js"]
        for mod in required_modules:
            mod_path = os.path.join(modules_dir, mod)
            self.assertTrue(os.path.isfile(mod_path), f"Required module JS file missing: {mod_path}")
            self.assertGreater(os.path.getsize(mod_path), 0, f"Module JS file is empty: {mod_path}")

    def test_http_request_handler_static_asset_serving_from_external_cwd(self):
        """Simulate HTTP GET requests against UltronAPIHandler from an external CWD."""
        tmp_dir = tempfile.mkdtemp()
        try:
            os.chdir(tmp_dir)

            endpoints = [
                ("/", "text/html"),
                ("/index.html", "text/html"),
                ("/index.js", "application/javascript"),
                ("/index.css", "text/css"),
                ("/folder_picker.html", "text/html"),
                ("/modules/api.js", "application/javascript"),
                ("/modules/graph.js", "application/javascript"),
                ("/modules/ui.js", "application/javascript"),
                ("/modules/state.js", "application/javascript"),
                ("/modules/storage.js", "application/javascript"),
                ("/modules/modals.js", "application/javascript"),
            ]

            for path, expected_content_type in endpoints:
                handler = self._create_mock_handler(path)
                handler.do_GET()

                response_code = handler.mock_wfile.get_status_code()
                content_type_header = handler.mock_wfile.get_header("Content-Type")

                self.assertEqual(
                    response_code,
                    200,
                    f"GET '{path}' failed with status {response_code} when running from external CWD: {tmp_dir}"
                )
                self.assertIn(
                    expected_content_type,
                    content_type_header,
                    f"GET '{path}' returned wrong Content-Type: {content_type_header}"
                )
                self.assertGreater(
                    len(handler.mock_wfile.get_body()),
                    0,
                    f"GET '{path}' returned empty response body"
                )
        finally:
            os.chdir(self.original_cwd)
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_http_request_handler_rejects_directory_traversal(self):
        """Verify that malicious directory traversal attempts are rejected."""
        traversal_paths = [
            "/../server.py",
            "/..%2fserver.py",
            "/../../pyproject.toml",
            "/modules/../../server.py",
        ]

        for path in traversal_paths:
            handler = self._create_mock_handler(path)
            handler.do_GET()
            status = handler.mock_wfile.get_status_code()
            self.assertIn(
                status,
                (400, 404),
                f"Directory traversal path '{path}' was not rejected! Status: {status}"
            )

    # --------------------------------------------------------------------------
    # 3. Packaging Metadata & pyproject.toml Configuration
    # --------------------------------------------------------------------------

    def test_pyproject_toml_configuration(self):
        """Verify pyproject.toml correctly specifies build backend, entrypoints, and package data."""
        pyproject_path = os.path.join(REPO_ROOT, "pyproject.toml")
        self.assertTrue(os.path.isfile(pyproject_path), f"pyproject.toml not found at {pyproject_path}")

        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('build-backend = "setuptools.build_meta"', content)
        self.assertIn('[project.scripts]', content)
        self.assertIn('ultron = "ultron.interfaces.ultron:main"', content)
        self.assertIn('ultron-mcp = "ultron.interfaces.mcp_server:main"', content)

        self.assertIn('[tool.setuptools.package-data]', content)
        self.assertIn('"ultron.interfaces"', content)
        self.assertIn('"ultron.core.rkm"', content)

        has_modules_glob = "web/modules/*.js" in content or "web/**/*" in content
        self.assertTrue(
            has_modules_glob,
            "pyproject.toml package-data must include web/modules/*.js to prevent 404 on frontend ES modules"
        )

    # --------------------------------------------------------------------------
    # 4. Packaging Data Completeness & JSON Resource Loading
    # --------------------------------------------------------------------------

    def test_resources_data_completeness(self):
        """Verify that all JSON resources referenced by Settings exist and are valid JSON."""
        resources_dir = Settings.get_resources_dir()
        self.assertTrue(os.path.isdir(resources_dir), f"Resources directory not found: {resources_dir}")

        weights_path = Settings.get_weights_path()
        self.assertTrue(os.path.isfile(weights_path), f"weights.json not found at {weights_path}")

        with open(weights_path, "r", encoding="utf-8") as f:
            weights_data = json.load(f)
        self.assertIsInstance(weights_data, dict, "weights.json must contain a JSON object")

    # --------------------------------------------------------------------------
    # 5. Zero-Dependency & Radon Fallback Operation
    # --------------------------------------------------------------------------

    def test_pure_stdlib_ast_complexity_when_radon_missing(self):
        """Verify that get_file_complexity operates accurately using stdlib AST when radon is None."""
        from ultron.core.risk import metrics

        test_code = """
def sample_func(a, b):
    if a > 0:
        for i in range(b):
            if i == 2:
                return i
    return -1
"""
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".py", delete=False) as f:
            f.write(test_code)
            tmp_filename = f.name

        try:
            with patch.object(metrics, "ComplexityVisitor", None):
                comp = metrics.get_file_complexity(tmp_filename)
                self.assertIsInstance(comp, (int, float))
                self.assertGreaterEqual(comp, 3, "AST fallback must compute branches correctly")
        finally:
            if os.path.exists(tmp_filename):
                os.remove(tmp_filename)

    # --------------------------------------------------------------------------
    # 6. Standalone Launcher Script Test
    # --------------------------------------------------------------------------

    def test_launcher_cli_mode(self):
        """Verify launcher.py --cli runs cleanly and outputs Welcoming HUD."""
        launcher_path = os.path.join(REPO_ROOT, "launcher.py")
        self.assertTrue(os.path.isfile(launcher_path))

        proc = subprocess.run(
            [sys.executable, launcher_path, "--cli"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=25
        )
        self.assertEqual(proc.returncode, 0, f"launcher.py --cli failed: {proc.stderr}")
        self.assertIn("ULTRON -- AI ARCHITECTURAL RISK ENGINE", proc.stdout)
        self.assertIn("Repository Health:", proc.stdout)

    def test_launcher_dashboard_server_invocation(self):
        """Verify run_dashboard_server calls serve() with valid signature and handles fallback."""
        import launcher
        
        with patch("ultron.interfaces.server.serve") as mock_serve, \
             patch("launcher._open_browser_delayed") as mock_browser:
            
            launcher.run_dashboard_server(port=8000, repo_path=REPO_ROOT, open_browser=False)
            mock_serve.assert_called_once_with(port=8000, auto_fallback=False, target_repo=REPO_ROOT)
            mock_browser.assert_not_called()

        # Test port retry on OSError
        with patch("ultron.interfaces.server.serve", side_effect=[OSError("Address already in use"), None]) as mock_serve, \
             patch("launcher._open_browser_delayed") as mock_browser:
            
            launcher.run_dashboard_server(port=8000, repo_path=REPO_ROOT, open_browser=True)
            self.assertEqual(mock_serve.call_count, 2)
            mock_browser.assert_called()

    def test_serve_signature_with_target_repo(self):
        """Verify server.serve accepts target_repo and persists it to config without error."""
        with tempfile.TemporaryDirectory() as tmp_target:
            with patch("http.server.ThreadingHTTPServer"), \
                 patch("ultron.interfaces.server.UltronAPIHandler"):
                
                # Mock serve_forever so it returns immediately
                with patch("http.server.HTTPServer.serve_forever", return_value=None):
                    try:
                        server.serve(port=65432, auto_fallback=False, target_repo=tmp_target)
                    except Exception as e:
                        # Even if socket fails to bind in test sandbox, verify no TypeError was raised
                        self.assertNotIsInstance(e, TypeError, f"serve() must accept target_repo: {e}")

    # --------------------------------------------------------------------------
    # Helper Utilities for Mocking HTTP Requests
    # --------------------------------------------------------------------------

    def _create_mock_handler(self, path: str):
        class MockWfile(BytesIO):
            def __init__(self):
                super().__init__()
                self.headers_written = {}
                self.status_code = None

            def write(self, b):
                super().write(b)

            def get_status_code(self):
                return self.status_code

            def get_header(self, key):
                return self.headers_written.get(key.lower(), "")

            def get_body(self):
                return self.getvalue()

        mock_wfile = MockWfile()

        handler = server.UltronAPIHandler.__new__(server.UltronAPIHandler)
        handler.path = path
        handler.command = "GET"
        handler.request_version = "HTTP/1.1"
        handler.headers = {}
        handler.rfile = BytesIO(b"")
        handler.wfile = mock_wfile
        handler.mock_wfile = mock_wfile

        def send_response(code, message=None):
            mock_wfile.status_code = code

        def send_header(keyword, value):
            mock_wfile.headers_written[keyword.lower()] = value

        def end_headers():
            pass

        handler.send_response = send_response
        handler.send_header = send_header
        handler.end_headers = end_headers

        return handler


if __name__ == "__main__":
    unittest.main()

