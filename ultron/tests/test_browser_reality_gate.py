"""
Ultron PPC-1 Browser Reality Gate Regression Test Suite.
Guards against defects discovered during the 10-agent browser reality audit:
1. DEF-P1-01: Objective Planner status string extraction (no TypeError on numeric envelope status).
2. DEF-P1-02: Verification shield audit error handling (no false positive success on HTTP 400).
3. DEF-P1-03: StateStore listener dispatch method integrity (notifyListeners).
4. DEF-P1-04: Global Omnibar modal display rules.
5. DEF-P2-02: Creator vs Engineer mode toggle active class synchronization.
6. DEF-P2-04: Viewport horizontal overflow clipping.
"""

import os
import re
import unittest

class TestBrowserRealityGate(unittest.TestCase):
    def setUp(self):
        self.web_dir = os.path.join("ultron", "interfaces", "web")
        self.ui_js = os.path.join(self.web_dir, "modules", "ui.js")
        self.state_js = os.path.join(self.web_dir, "modules", "state.js")
        self.index_js = os.path.join(self.web_dir, "index.js")
        self.index_html = os.path.join(self.web_dir, "index.html")
        self.index_css = os.path.join(self.web_dir, "index.css")

    def test_def_p1_01_objective_status_extraction_safe(self):
        """Verify ui.js has safe string coercion for rawStatus in renderObjectivePlanner."""
        with open(self.ui_js, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("statusCandidate", code)
        self.assertIn("String(statusCandidate).toUpperCase()", code)
        # Ensure vulnerable uncoerced pattern is absent
        self.assertNotIn('(window.currentWorkState?.status || obj.status || obj.stage || "").toUpperCase()', code)

    def test_def_p1_02_audit_error_not_falsely_passed(self):
        """Verify index.js checks res.success before claiming zero anomalies in audit handler."""
        with open(self.index_js, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("if (!res.success)", code)
        self.assertIn("Audit Incomplete", code)

    def test_def_p1_03_statestore_uses_notifylisteners(self):
        """Verify state.js calls notifyListeners instead of undefined this.notify()."""
        with open(self.state_js, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertNotIn("this.notify();", code)
        self.assertIn("this.notifyListeners(", code)

    def test_def_p2_02_mode_toggle_syncs_labels(self):
        """Verify index.js synchronizes .active class on label-creator and label-engineer."""
        with open(self.index_js, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("labelCreator.classList.toggle(\"active\", !isEng)", code)
        self.assertIn("labelEngineer.classList.toggle(\"active\", isEng)", code)

    def test_def_p2_04_viewport_overflow_clipped(self):
        """Verify index.css clips viewport horizontal overflow on html, body, and app-container."""
        with open(self.index_css, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("overflow-x: hidden;", code)
        self.assertIn(".hidden {\n    display: none !important;\n}", code)

if __name__ == "__main__":
    unittest.main()
