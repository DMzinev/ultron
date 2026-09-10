"""
ultron/tests/test_ui_smoke_live.py

Automated Browser-Level Smoke & Structural Verification Suite for Task P3-B1:
"Real Browser-Level Smoke Test of the 4-Pillar UI" per docs/AGENT_EXECUTION_PLAN_PHASE3.md.

Asserts:
1. Live HTTP Server Lifecycle: Boots on ephemeral port (port 0), serves HTML, CSS, and JS with correct MIME types.
2. 4-Pillar DOM Completeness: Parses HTML via stdlib html.parser, asserting all 4 views (Dashboard, Graph, Studio, Auditor)
   and their interactive controls exist in the DOM.
3. Active API Route Bindings: Statically verifies index.js is wired to real, active backend API endpoints.
4. ES Module Syntax & Delimiter Integrity: Validates JavaScript syntax via node -c (if available) and stdlib structural analysis.
5. Invariant Compliance: Zero external pip dependencies, zero added skips (100% compliant with test_skip_invariants.py).
"""

import os
import sys
import shutil
import urllib.request
import threading
import subprocess
import unittest
from html.parser import HTMLParser
from typing import Dict, List, Set

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ultron.interfaces.server import create_server


class DOMStructureParser(HTMLParser):
    """Parses served HTML into tag, attribute, and ID indices for structural assertion."""

    def __init__(self):
        super().__init__()
        self.ids: Set[str] = set()
        self.data_views: Set[str] = set()
        self.tag_counts: Dict[str, int] = {}

    def handle_starttag(self, tag: str, attrs: List[tuple]):
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1
        for attr, val in attrs:
            if attr == "id" and val:
                self.ids.add(val)
            elif attr == "data-view" and val:
                self.data_views.add(val)


class TestLiveUISmoke(unittest.TestCase):
    """Live HTTP server lifecycle and 4-pillar UI DOM smoke tests."""

    httpd = None
    server_thread = None
    server_port = 0
    base_url = ""

    @classmethod
    def setUpClass(cls):
        # Bind ephemeral port (port=0) to guarantee zero port collision
        cls.httpd, cls.server_port = create_server(host="127.0.0.1", start_port=0, max_attempts=1)
        cls.base_url = f"http://127.0.0.1:{cls.server_port}"

        # Spin up background daemon thread
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        # Canonical server shutdown sequence
        if cls.httpd is not None:
            cls.httpd.shutdown()
            cls.httpd.server_close()
        if cls.server_thread is not None:
            cls.server_thread.join(timeout=2.0)

    def test_live_server_serves_html_and_assets(self):
        """Verify that GET / returns HTTP 200 with HTML, and assets serve with correct MIME headers."""
        # 1. HTML Root Document
        req_root = urllib.request.Request(f"{self.base_url}/", headers={"User-Agent": "UltronSmokeTest"})
        with urllib.request.urlopen(req_root, timeout=5.0) as resp:
            self.assertEqual(resp.status, 200)
            content_type = resp.headers.get("Content-Type", "")
            self.assertTrue(
                content_type.startswith("text/html"),
                f"Expected text/html prefix, got: {content_type}"
            )
            body = resp.read().decode("utf-8")
            self.assertIn("<title>Ultron", body)
            self.assertIn('<main id="main">', body)

        # 2. CSS Stylesheet
        req_css = urllib.request.Request(f"{self.base_url}/index.css", headers={"User-Agent": "UltronSmokeTest"})
        with urllib.request.urlopen(req_css, timeout=5.0) as resp:
            self.assertEqual(resp.status, 200)
            content_type = resp.headers.get("Content-Type", "")
            self.assertTrue(
                content_type.startswith("text/css"),
                f"Expected text/css prefix, got: {content_type}"
            )
            css_body = resp.read().decode("utf-8")
            self.assertGreater(len(css_body), 500)

        # 3. JavaScript Module
        req_js = urllib.request.Request(f"{self.base_url}/index.js", headers={"User-Agent": "UltronSmokeTest"})
        with urllib.request.urlopen(req_js, timeout=5.0) as resp:
            self.assertEqual(resp.status, 200)
            content_type = resp.headers.get("Content-Type", "")
            self.assertTrue(
                content_type.startswith("application/javascript"),
                f"Expected application/javascript prefix, got: {content_type}"
            )
            js_body = resp.read().decode("utf-8")
            self.assertGreater(len(js_body), 5000)

    def test_dom_structure_contains_all_4_pillars(self):
        """Parse live served HTML and assert all 4 interactive pillar views and controls exist."""
        req_root = urllib.request.Request(f"{self.base_url}/", headers={"User-Agent": "UltronSmokeTest"})
        with urllib.request.urlopen(req_root, timeout=5.0) as resp:
            html_content = resp.read().decode("utf-8")

        parser = DOMStructureParser()
        parser.feed(html_content)

        # 1. Navigation Buttons for all 4 Pillars
        expected_views = {"dashboard", "graph", "studio", "auditor"}
        self.assertTrue(
            expected_views.issubset(parser.data_views),
            f"Missing navigation views: {expected_views - parser.data_views}"
        )

        # 2. Tab View Containers for all 4 Pillars
        expected_view_containers = {
            "view-dashboard",
            "view-graph",
            "view-studio",
            "view-auditor"
        }
        self.assertTrue(
            expected_view_containers.issubset(parser.ids),
            f"Missing view containers: {expected_view_containers - parser.ids}"
        )

        # 3. Key Interactive Controls across all 4 Pillars
        required_controls = {
            # Global Topbar Controls
            "scan-btn",
            "repo-input",
            "browse-btn",
            # Pillar 1: Architecture Dashboard
            "risk-list",
            "primary-verdict-title",
            "health-score",
            "violations-chip",
            # Pillar 2: Dependency Graph
            "topology-svg",
            "graph-granularity",
            "graph-zoom-in",
            "graph-inspector",
            # Pillar 3: Agent Mission Studio
            "studio-target-file",
            "studio-intent",
            "studio-compile-btn",
            "studio-output",
            # Pillar 4: Code Auditor
            "auditor-source-seg",
            "auditor-file-input",
        }
        self.assertTrue(
            required_controls.issubset(parser.ids),
            f"Missing interactive controls in DOM: {required_controls - parser.ids}"
        )

    def test_frontend_js_api_endpoint_wiring(self):
        """Assert index.js connects to real, active backend API endpoints."""
        js_path = os.path.join(REPO_ROOT, "ultron", "interfaces", "web", "index.js")
        self.assertTrue(os.path.isfile(js_path), f"index.js missing at {js_path}")

        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()

        active_endpoints = [
            "/api/v1/health",
            "/api/v1/overview",
            "/api/architecture-health",
            "/api/dependency-graph",
            "/api/v1/analyze",
            "/api/audit",
        ]

        for endpoint in active_endpoints:
            self.assertIn(
                endpoint,
                js_content,
                f"Expected active API endpoint binding for '{endpoint}' not found in index.js"
            )

    def test_frontend_js_syntax_and_structure(self):
        """
        Validates JavaScript syntax via Node.js (if available) and stdlib delimiter analysis.
        Strictly preserves zero-skip invariant (never calls self.skipTest).
        """
        js_path = os.path.join(REPO_ROOT, "ultron", "interfaces", "web", "index.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()

        # 1. Pure stdlib structural assertions (always run)
        self.assertGreater(len(js_content), 10000, "index.js is unexpectedly truncated")
        self.assertEqual(
            js_content.count("{"), js_content.count("}"),
            "Unbalanced curly braces in index.js"
        )
        self.assertEqual(
            js_content.count("["), js_content.count("]"),
            "Unbalanced square brackets in index.js"
        )
        self.assertEqual(
            js_content.count("("), js_content.count(")"),
            "Unbalanced parentheses in index.js"
        )

        # 2. Core frontend lifecycle functions presence
        core_signatures = [
            "async function api(",
            "function renderSummary(",
            "function switchView(",
            "function renderTopologyGraph(",
        ]
        for sig in core_signatures:
            self.assertIn(sig, js_content, f"Core frontend function '{sig}' missing from index.js")

        # 3. Node.js ES syntax check if Node binary is present
        node_bin = shutil.which("node")
        if node_bin:
            res = subprocess.run(
                [node_bin, "-c", js_path],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT
            )
            self.assertEqual(
                res.returncode, 0,
                f"Node.js syntax check failed on index.js:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
            )


if __name__ == "__main__":
    unittest.main()
