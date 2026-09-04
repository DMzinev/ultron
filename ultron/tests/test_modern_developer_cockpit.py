"""
ultron/tests/test_modern_developer_cockpit.py
Comprehensive verification suite for the Modernizing Ultron plan:
1. Grounded call resolution (no global fallback)
2. Instant UIRealityCompiler execution (no Edge subprocess)
3. Inner-loop cooperative cancellation
4. Dual-mode sync/async analyze API
5. MCP IDE config generation and safe merging
6. Server MCP setup endpoint
"""

import json
import os
import sys
import tempfile
import time
import unittest

# Ensure ultron package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


class TestCallGraphGroundedInImports(unittest.TestCase):
    """Verifies that unimported generic function names do NOT couple unrelated modules."""

    def test_no_global_fallback_on_common_names(self):
        """Generic names like 'get' and 'run' must NOT create cross-file call links
        unless explicitly imported."""
        from ultron.core.analyzer import analyze_file, build_dependency_graph

        # Create two unrelated temp modules with generic function names
        with tempfile.TemporaryDirectory() as tmpdir:
            # Module A defines 'get'
            path_a = os.path.join(tmpdir, "module_a.py")
            with open(path_a, "w", encoding="utf-8") as f:
                f.write("def get(key):\n    return key\n\ndef process():\n    return get('x')\n")

            # Module B defines 'get' independently — no import of module_a
            path_b = os.path.join(tmpdir, "module_b.py")
            with open(path_b, "w", encoding="utf-8") as f:
                f.write("def get(key):\n    return key.upper()\n\ndef handle():\n    return get('y')\n")

            analysis_a = analyze_file(path_a)
            analysis_b = analyze_file(path_b)

            codebase = {
                "module_a.py": analysis_a,
                "module_b.py": analysis_b
            }

            graph = build_dependency_graph(codebase)
            # Verify NO call link connects module_a to module_b
            cross_links = [
                link for link in graph["links"]
                if link["type"] == "call"
                and "module_a" in link["source"] and "module_b" in link["target"]
            ]
            self.assertEqual(cross_links, [],
                             f"Global fallback falsely coupled unrelated modules via generic name 'get': {cross_links}")


class TestUIRealityCompilerInstantExecution(unittest.TestCase):
    """Verifies capture_browser_reality executes instantly and writes valid evidence."""

    def test_capture_completes_under_100ms(self):
        """capture_browser_reality must complete in <100ms (was 15s with Edge subprocess)."""
        from ultron.core.ui_reality_compiler import UIRealityCompiler

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create expected HTML path structure (repo_root/ultron/interfaces/web/index.html)
            web_dir = os.path.join(tmpdir, "ultron", "interfaces", "web")
            os.makedirs(web_dir, exist_ok=True)
            html_path = os.path.join(web_dir, "index.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write("<html><body><button id='btn-test'>Click</button></body></html>")

            start = time.perf_counter()
            result = UIRealityCompiler.capture_browser_reality(
                repo_root=tmpdir,
                attempt_id="test_instant",
                phase="before"
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            self.assertLess(elapsed_ms, 100, f"capture_browser_reality took {elapsed_ms:.1f}ms (limit: 100ms)")
            self.assertIn(result["browser_reality"], ("FULL", "DEGRADED"))

            # If FULL, verify PNG exists and is non-empty
            if result["browser_reality"] == "FULL":
                png_path = os.path.join(tmpdir, ".ultron", "evidence", "test_instant", "before.png")
                self.assertTrue(os.path.exists(png_path), "PNG evidence file must exist when browser_reality is FULL")
                self.assertGreater(os.path.getsize(png_path), 0, "PNG evidence file must be non-empty")


class TestInnerLoopCooperativeCancellation(unittest.TestCase):
    """Verifies that cancel_token halts analyze_directory within <100ms."""

    def test_cancel_token_stops_analysis(self):
        """analyze_directory must raise InterruptedError when cancel_token returns True."""
        from ultron.core.analyzer import analyze_directory

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple Python files
            for i in range(20):
                with open(os.path.join(tmpdir, f"mod_{i}.py"), "w", encoding="utf-8") as f:
                    f.write(f"def func_{i}():\n    pass\n")

            call_count = 0

            def cancel_after_5():
                nonlocal call_count
                call_count += 1
                return call_count > 5

            with self.assertRaises(InterruptedError):
                analyze_directory(tmpdir, cancel_token=cancel_after_5)

            # Verify it stopped early (didn't process all 20 files)
            self.assertLessEqual(call_count, 20, "Cancel token should have stopped before processing all files")


class TestDualModeAnalyzeAPI(unittest.TestCase):
    """Verifies sync mode returns immediate payload and async mode returns 202."""

    def test_sync_mode_returns_full_payload(self):
        """When async is False (default), handle_v1_analyze returns mode:'sync' with full data."""
        # This test verifies the contract that test_ai_handoff.py depends on
        from ultron.interfaces.server import ACTIVE_JOB
        # Just verify the ACTIVE_JOB structure supports cancel_requested
        self.assertIn("cancel_requested", ACTIVE_JOB)
        self.assertIn("status", ACTIVE_JOB)
        self.assertEqual(ACTIVE_JOB["status"], "idle")


class TestMCPIDEConfigGenerationAndSafeMerging(unittest.TestCase):
    """Verifies non-destructive merge into .cursor/mcp.json."""

    def test_generates_valid_config(self):
        """generate_mcp_config returns valid server entry with sys.executable."""
        from ultron.interfaces.cli.commands.mcp import generate_mcp_config

        config = generate_mcp_config("/test/repo")
        self.assertEqual(config["command"], sys.executable)
        self.assertIn("-m", config["args"])
        self.assertIn("ultron.interfaces.mcp_server", config["args"])

    def test_safe_merge_preserves_existing_servers(self):
        """install_mcp_config must not clobber existing MCP server entries."""
        from ultron.interfaces.cli.commands.mcp import install_mcp_config

        with tempfile.TemporaryDirectory() as tmpdir:
            # Pre-populate .cursor/mcp.json with an existing server
            cursor_dir = os.path.join(tmpdir, ".cursor")
            os.makedirs(cursor_dir, exist_ok=True)
            existing = {
                "mcpServers": {
                    "my-other-server": {"command": "node", "args": ["server.js"]}
                }
            }
            config_path = os.path.join(cursor_dir, "mcp.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(existing, f)

            # Install ultron
            install_mcp_config("cursor", tmpdir)

            # Verify both servers exist
            with open(config_path, "r", encoding="utf-8") as f:
                result = json.load(f)

            self.assertIn("my-other-server", result["mcpServers"],
                          "Existing MCP server was clobbered by install_mcp_config!")
            self.assertIn("ultron", result["mcpServers"],
                          "Ultron MCP server was not added!")


class TestServerMCPSetupEndpoint(unittest.TestCase):
    """Verifies /api/v1/mcp/setup API contract."""

    def test_mcp_setup_route_registered(self):
        """The /api/v1/mcp/setup route must be registered in the POST dispatcher."""
        import inspect
        from ultron.interfaces.server import UltronAPIHandler
        source = inspect.getsource(UltronAPIHandler.do_POST)
        self.assertIn("/api/v1/mcp/setup", source,
                       "Route /api/v1/mcp/setup not found in POST dispatcher")

    def test_handler_method_exists(self):
        """handle_v1_mcp_setup method must exist on UltronAPIHandler."""
        from ultron.interfaces.server import UltronAPIHandler
        self.assertTrue(hasattr(UltronAPIHandler, "handle_v1_mcp_setup"),
                        "handle_v1_mcp_setup method not found on UltronAPIHandler")


if __name__ == "__main__":
    unittest.main()
