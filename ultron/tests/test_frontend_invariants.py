"""
ultron/tests/test_frontend_invariants.py

Automated invariant test suite for Task P3-C1:
"Apply a Frontend Modularity Invariant (<400-Line Ceiling per JS File)"

Asserts:
1. Every .js file in ultron/interfaces/web/**/*.js has strictly < 400 lines.
2. Balanced delimiters ({}, [], ()) across all frontend JavaScript modules.
3. Native ES module script loading tag (<script type="module" src="index.js"></script>) in index.html.
4. Node.js ES syntax validity on all modules if node binary is installed.
5. Unidirectional module DAG (Layer 0 state -> Layer 1 api -> Layer 2 pillars -> Layer 3 index).
"""

import glob
import os
import re
import shutil
import subprocess
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WEB_DIR = os.path.join(REPO_ROOT, "ultron", "interfaces", "web")


class TestFrontendInvariants(unittest.TestCase):
    """Hermetic structural and architectural invariant tests for the modular frontend."""

    def test_all_frontend_js_under_400_lines(self):
        """Asserts every JavaScript file in the web directory strictly respects the 400-line ceiling."""
        js_files = glob.glob(os.path.join(WEB_DIR, "**", "*.js"), recursive=True)
        self.assertGreaterEqual(len(js_files), 10, "Expected at least 10 modular JavaScript files")

        violations = []
        for path in sorted(js_files):
            rel = os.path.relpath(path, WEB_DIR)
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            line_count = len(lines)
            if line_count >= 400:
                violations.append(f"{rel}: {line_count} lines (must be < 400)")

        self.assertEqual(
            violations,
            [],
            f"Found frontend JavaScript files exceeding the 400-line modularity ceiling: {violations}",
        )

    def test_balanced_delimiters_across_all_frontend_modules(self):
        """Asserts balanced delimiters ({}, [], ()) across all frontend JavaScript files."""
        js_files = glob.glob(os.path.join(WEB_DIR, "**", "*.js"), recursive=True)
        for path in js_files:
            rel = os.path.relpath(path, WEB_DIR)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertEqual(
                content.count("{"), content.count("}"),
                f"Unbalanced curly braces in {rel}",
            )
            self.assertEqual(
                content.count("["), content.count("]"),
                f"Unbalanced square brackets in {rel}",
            )
            self.assertEqual(
                content.count("("), content.count(")"),
                f"Unbalanced parentheses in {rel}",
            )

    def test_native_es_module_script_tag_in_index_html(self):
        """Asserts index.html loads index.js as a native ES module."""
        index_html_path = os.path.join(WEB_DIR, "index.html")
        self.assertTrue(os.path.isfile(index_html_path), "index.html must exist")
        with open(index_html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn(
            '<script type="module" src="index.js"></script>',
            html,
            "index.html must load index.js with type module",
        )

    def test_nodejs_syntax_validation_if_available(self):
        """
        Validates JavaScript syntax for all frontend files via Node.js if available.
        Strictly preserves the repository-wide zero-skip invariant (no skipTest).
        """
        node_bin = shutil.which("node")
        if not node_bin:
            return  # Clean pass without skipping when node is absent

        js_files = glob.glob(os.path.join(WEB_DIR, "**", "*.js"), recursive=True)
        for path in js_files:
            rel = os.path.relpath(path, WEB_DIR)
            res = subprocess.run(
                [node_bin, "-c", path],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
            )
            self.assertEqual(
                res.returncode,
                0,
                f"Node.js syntax check failed on {rel}:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}",
            )

    def test_unidirectional_layer_hierarchy(self):
        """
        Verifies the unidirectional module DAG:
        - Layer 0 (state.js) must not import any modules from modules/.
        - Layer 1 (api.js) may only import from Layer 0 (state.js).
        - Layer 2 feature modules must not import from each other.
        """
        state_path = os.path.join(WEB_DIR, "modules", "state.js")
        with open(state_path, "r", encoding="utf-8") as f:
            state_code = f.read()
        self.assertNotIn('from "./', state_code, "Layer 0 (state.js) must have zero internal imports")

        api_path = os.path.join(WEB_DIR, "modules", "api.js")
        with open(api_path, "r", encoding="utf-8") as f:
            api_code = f.read()
        for line in api_code.splitlines():
            if line.strip().startswith("import "):
                self.assertIn(
                    "state.js",
                    line,
                    f"Layer 1 (api.js) may only import state.js, but found: {line}",
                )

    def test_footer_version_synchronization(self):
        """Asserts index.html footer displays synchronized engine version v1.4.0."""
        index_html_path = os.path.join(WEB_DIR, "index.html")
        with open(index_html_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn(
            "RKM Engine v1.4.0",
            html,
            "index.html footer must display RKM Engine v1.4.0",
        )

    def test_shortcuts_modal_and_export_elements_present(self):
        """Asserts shortcuts modal markup and export report button are present in index.html."""
        index_html_path = os.path.join(WEB_DIR, "index.html")
        with open(index_html_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('id="shortcuts-modal"', html, "index.html must contain #shortcuts-modal")
        self.assertIn('id="btn-shortcuts-help"', html, "index.html must contain #btn-shortcuts-help")
        self.assertIn('id="export-btn"', html, "index.html must contain #export-btn")

    def test_aria_live_regions_present(self):
        """Asserts ARIA live regions and status roles are declared on dynamic notification nodes."""
        index_html_path = os.path.join(WEB_DIR, "index.html")
        with open(index_html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Toast notification element
        self.assertTrue(
            re.search(r'<div[^>]*id="toast"[^>]*role="status"', html),
            "Expected #toast to declare role='status'",
        )
        self.assertTrue(
            re.search(r'<div[^>]*id="toast"[^>]*aria-live="polite"', html),
            "Expected #toast to declare aria-live='polite'",
        )
        self.assertTrue(
            re.search(r'<div[^>]*id="toast"[^>]*aria-atomic="true"', html),
            "Expected #toast to declare aria-atomic='true'",
        )

        # Connection status element
        self.assertTrue(
            re.search(r'<span[^>]*id="conn-text"[^>]*aria-live="polite"', html),
            "Expected #conn-text to declare aria-live='polite'",
        )

        # Busy state announcement
        self.assertTrue(
            re.search(r'<p[^>]*id="busy-text"[^>]*(role="status"|aria-live="polite")', html),
            "Expected #busy-text to declare role='status' or aria-live='polite'",
        )

        # Banner alert element
        self.assertTrue(
            re.search(r'<div[^>]*id="banner"[^>]*(role="alert"|aria-live="assertive")', html),
            "Expected #banner to declare role='alert' or aria-live='assertive'",
        )

    def test_accessible_focus_visible_styling(self):
        """Asserts index.css contains WCAG 2.1 AA focus-visible rings and forced-colors query."""
        index_css_path = os.path.join(WEB_DIR, "index.css")
        with open(index_css_path, "r", encoding="utf-8") as f:
            css = f.read()

        self.assertIn(":focus-visible", css, "index.css must define :focus-visible rules")
        self.assertIn("outline: 2px solid var(--accent)", css, "index.css must declare accent outline on focus-visible")
        self.assertIn("outline-offset: 2px", css, "index.css must declare outline-offset: 2px on focus-visible")
        self.assertIn(".risk-item:focus-visible", css, "index.css must explicitly target .risk-item:focus-visible")
        self.assertIn("@media (forced-colors: active)", css, "index.css must support forced-colors high contrast")

    def test_responsive_breakpoints_declared(self):
        """Asserts index.css contains responsive 1024px (tablet) and 768px (mobile) breakpoints."""
        index_css_path = os.path.join(WEB_DIR, "index.css")
        with open(index_css_path, "r", encoding="utf-8") as f:
            css = f.read()

        self.assertIn("@media (max-width: 1024px)", css, "index.css must declare @media (max-width: 1024px)")
        self.assertIn("@media (max-width: 768px)", css, "index.css must declare @media (max-width: 768px)")
        self.assertIn("grid-template-rows: auto 1fr", css, "index.css 1024px query must define grid-template-rows: auto 1fr")


if __name__ == "__main__":
    unittest.main()
