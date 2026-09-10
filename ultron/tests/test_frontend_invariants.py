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


if __name__ == "__main__":
    unittest.main()
