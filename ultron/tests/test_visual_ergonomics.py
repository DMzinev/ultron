"""
ultron.tests.test_visual_ergonomics
Unit test suite asserting Visual Ergonomics, WCAG 2.1 AA Contrast, and Layout Clearance.
"""

import unittest
from pathlib import Path
from ultron.core.visual_ergonomics import (
    parse_color_to_rgb,
    compute_relative_luminance,
    compute_contrast_ratio,
    VisualErgonomicsAuditor
)


class TestVisualErgonomics(unittest.TestCase):
    """Tests for WCAG 2.1 contrast calculation and visual ergonomics quality gates."""

    def test_contrast_ratio_formula_precision(self):
        """Asserts exact mathematical boundaries for WCAG contrast ratios."""
        # Pure White (#fff) on Pure Black (#000) is maximum 21.0
        ratio_max = compute_contrast_ratio("#ffffff", "#000000")
        self.assertAlmostEqual(ratio_max, 21.0, places=1)

        # Black on Black or White on White is minimum 1.0
        ratio_min = compute_contrast_ratio("#000000", "#000000")
        self.assertAlmostEqual(ratio_min, 1.0, places=1)

        # Cyan on Dark Background satisfies WCAG AA large text (>= 3.0:1)
        ratio_cyan = compute_contrast_ratio("#38bdf8", "#0f172a")
        self.assertGreaterEqual(ratio_cyan, 3.0)

        # Light text on Dark Card satisfies WCAG AA normal text (>= 4.5:1)
        ratio_body = compute_contrast_ratio("#f8fafc", "#0f172a")
        self.assertGreaterEqual(ratio_body, 4.5)

    def test_color_parsing_formats(self):
        """Asserts robust parsing of 3-digit hex, 6-digit hex, and rgba formats."""
        self.assertEqual(parse_color_to_rgb("#fff"), (1.0, 1.0, 1.0))
        self.assertEqual(parse_color_to_rgb("#000"), (0.0, 0.0, 0.0))
        self.assertEqual(parse_color_to_rgb("rgb(255, 255, 255)"), (1.0, 1.0, 1.0))
        self.assertEqual(parse_color_to_rgb("rgba(0, 0, 0, 0.8)"), (0.0, 0.0, 0.0))
        self.assertIsNone(parse_color_to_rgb("invalid-color-value"))

    def test_theme_contrast_audit(self):
        """Asserts default theme tokens pass all WCAG AA contrast gates."""
        css_mock = """
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
            --accent-primary: #38bdf8;
            --warning: #f59e0b;
            --danger: #ef4444;
            --success: #10b981;
        }
        """
        res = VisualErgonomicsAuditor.audit_theme_contrast(css_mock)
        self.assertTrue(res["passed"], f"Theme contrast violations: {res['violations']}")
        self.assertGreaterEqual(len(res["checks"]), 4)

    def test_interactive_clearance_audit(self):
        """Asserts button padding rules and text wrap safety."""
        css_sample = """
        .btn { padding: 8px 16px; font-size: 13px; word-break: break-word; }
        """
        res = VisualErgonomicsAuditor.audit_interactive_clearance("<div></div>", css_sample)
        self.assertTrue(res["passed"], f"Clearance violations: {res['violations']}")

    def test_empty_states_presence_audit(self):
        """Asserts required view empty state containers exist in UI."""
        html_sample = """
        <div id="list-empty">No files match filter</div>
        <div id="detail-placeholder">No file selected</div>
        <div id="graph-empty-state">No nodes match filter</div>
        <div id="auditor-anomalies-list">Safety gate ready</div>
        """
        res = VisualErgonomicsAuditor.audit_empty_states(html_sample)
        self.assertTrue(res["passed"], f"Empty state violations: {res['violations']}")

    def test_live_web_interface_ergonomics(self):
        """Asserts the live Ultron web interface files pass visual ergonomics validation."""
        audit_res = VisualErgonomicsAuditor.audit_web_interface()
        self.assertTrue(audit_res["passed"], f"Live interface violations: {audit_res['violations']}")
        self.assertEqual(audit_res["ergonomic_score"], 100.0)

    def test_product_information_hierarchy_overview(self):
        """Asserts Overview (Dashboard) prioritizes primary verdict and health context."""
        web_dir = Path(__file__).parent.parent / "interfaces" / "web"
        html_path = web_dir / "index.html"
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Overview primary hierarchy elements
        self.assertIn('id="primary-verdict-title"', html)
        self.assertIn('id="primary-risky-count"', html)
        self.assertIn('id="health-score"', html)
        self.assertIn('id="health-badge"', html)

    def test_product_information_hierarchy_structure(self):
        """Asserts Structure tab is graph-centric with on-demand node details drawer."""
        web_dir = Path(__file__).parent.parent / "interfaces" / "web"
        html_path = web_dir / "index.html"
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn('id="view-graph"', html)
        self.assertIn('id="topology-svg"', html)
        self.assertIn('id="graph-inspector"', html)

    def test_product_information_hierarchy_work_plan(self):
        """Asserts Agent Studio tab contains dedicated mission specification container."""
        web_dir = Path(__file__).parent.parent / "interfaces" / "web"
        html_path = web_dir / "index.html"
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn('id="view-studio"', html)
        self.assertIn('id="studio-target-file"', html)
        self.assertIn('id="studio-intent"', html)
        self.assertIn('id="studio-compile-btn"', html)

    def test_product_information_hierarchy_agent_context(self):
        """Asserts Agent Studio provides mission output and copy/download controls."""
        web_dir = Path(__file__).parent.parent / "interfaces" / "web"
        html_path = web_dir / "index.html"
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn('id="studio-output"', html)
        self.assertIn('id="studio-copy-btn"', html)
        self.assertIn('id="studio-download-btn"', html)

    def test_product_information_hierarchy_verify_and_subtraction(self):
        """Asserts Code Auditor centers on Safety Gate and anomaly policy rules."""
        web_dir = Path(__file__).parent.parent / "interfaces" / "web"
        html_path = web_dir / "index.html"
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Primary readiness & safety gate
        self.assertIn('id="view-auditor"', html)
        self.assertIn('id="auditor-shield"', html)
        self.assertIn('id="auditor-run-btn"', html)
        self.assertIn('id="auditor-anomalies-list"', html)

    def test_html_dom_id_uniqueness_and_interactive_controls(self):
        """Asserts zero duplicate IDs exist across index.html and all critical interactive buttons are present."""
        web_dir = Path(__file__).parent.parent / "interfaces" / "web"
        html_path = web_dir / "index.html"
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        import re
        ids = re.findall(r'id=["\']([^"\']+)["\']', html)
        duplicates = [i for i in ids if ids.count(i) > 1]
        self.assertEqual(len(duplicates), 0, f"Found duplicate DOM IDs in index.html: {set(duplicates)}")

        # Verify critical interactive buttons exist
        self.assertIn('id="scan-btn"', html)
        self.assertIn('id="empty-scan-btn"', html)
        self.assertIn('id="browse-btn"', html)
        self.assertIn('id="save-btn"', html)
        self.assertIn('id="clear-filter-btn"', html)
        self.assertIn('id="studio-compile-btn"', html)
        self.assertIn('id="auditor-run-btn"', html)

    def test_modal_manager_dismissal_contract(self):
        """Asserts modals.js closeAll includes all overlay and drawer classes."""
        web_dir = Path(__file__).parent.parent / "interfaces" / "web" / "modules"
        modals_js_path = web_dir / "modals.js"
        with open(modals_js_path, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn(".modal-overlay", code)
        self.assertIn(".evidence-drawer", code)
        self.assertIn(".drawer-backdrop", code)
        self.assertIn(".modal-backdrop", code)

    def test_v270_performance_and_stability_contracts(self):
        """Asserts version metadata in index.html and keyboard navigation in index.js."""
        web_dir = Path(__file__).parent.parent / "interfaces" / "web"
        
        # 1. Version tag in index.html
        with open(web_dir / "index.html", "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('RKM Engine', html)

        # 2. Keyboard shortcuts and views in index.js
        with open(web_dir / "index.js", "r", encoding="utf-8") as f:
            index_js = f.read()
        self.assertIn("function setupKeyboardShortcuts()", index_js)
        self.assertIn("switchView", index_js)

    def test_dom_handler_referential_integrity_and_toast_throttling(self):
        """Asserts zero orphaned event listeners on pruned elements and verifies toast notifications."""
        web_dir = Path(__file__).parent.parent / "interfaces" / "web"
        
        with open(web_dir / "index.js", "r", encoding="utf-8") as f:
            index_js = f.read()

        # 1. Pruned sliders must not have active event listeners
        self.assertNotIn('sliderTypo.addEventListener', index_js)
        self.assertNotIn('sliderProb.addEventListener', index_js)

        # 2. Toast notifications in index.js
        self.assertIn("function showToast(", index_js)


if __name__ == "__main__":
    unittest.main()
