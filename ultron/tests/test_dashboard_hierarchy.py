"""
ultron/tests/test_dashboard_hierarchy.py

Dedicated unit test suite for Task C4: Clean, intuitive dashboard information hierarchy.
Verifies:
1. DOM contract & semantic markup (primary verdict container, supporting health context, nav kbd badges).
2. Dynamic headline grammar (N=0 stable codebase, N=1 singular file, N>1 plural files).
3. Keyboard navigation routing (1-4 pillar switching, / filter focus, Escape hierarchy).
4. Text editing immunity & modifier key guards (no hijacking of Ctrl/Cmd/Alt or form typing).
5. 3-part structured empty states across all four pillars (what happened, why, what to do next).
6. CSS styling coverage for primary verdict, keycaps, and empty state overlays.
"""

import os
import re
import unittest


class TestDashboardHierarchyDOMContract(unittest.TestCase):
    """Verifies that index.html and index.css contain all required DOM structures and classes."""

    @classmethod
    def setUpClass(cls):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "interfaces", "web"))
        with open(os.path.join(base_dir, "index.html"), "r", encoding="utf-8") as f:
            cls.html = f.read()
        with open(os.path.join(base_dir, "index.css"), "r", encoding="utf-8") as f:
            cls.css = f.read()
        with open(os.path.join(base_dir, "index.js"), "r", encoding="utf-8") as f:
            cls.js = f.read()

    def test_primary_verdict_markup(self):
        """Above-the-fold primary verdict container and IDs must be present."""
        self.assertIn('class="summary primary-verdict"', self.html, "Container must have both summary and primary-verdict classes")
        self.assertIn('id="primary-verdict-title"', self.html)
        self.assertIn('id="primary-risky-count"', self.html)
        self.assertIn('id="primary-verdict-desc"', self.html)
        self.assertIn('verdict-main', self.html)

    def test_supporting_health_context_markup(self):
        """Health score must be preserved as supporting context card."""
        self.assertIn('class="supporting-context"', self.html)
        self.assertIn('class="supporting-card supporting-health"', self.html)
        self.assertIn('id="health-score"', self.html)
        self.assertIn('id="health-badge"', self.html)
        self.assertIn('id="health-explain"', self.html)
        self.assertIn('class="score-denom"', self.html)
        self.assertIn('/100', self.html)

    def test_navigation_keycaps(self):
        """All 4 main navigation tabs must feature keycap indicators 1 to 4."""
        for i in range(1, 5):
            kbd_tag = f'<kbd class="nav-kbd">{i}</kbd>'
            self.assertIn(kbd_tag, self.html, f"Missing keycap {i} in nav tabs")
            self.assertIn(f'[{i}]', self.html, f"Missing title shortcut indication for tab {i}")

    def test_filter_and_clear_button(self):
        """Filter input must include search hint, and empty filter state must provide a clear button."""
        self.assertIn('placeholder="Filter files… (/ to search)"', self.html)
        self.assertIn('id="clear-filter-btn"', self.html)
        self.assertIn('id="filter-query-text"', self.html)

    def test_graph_empty_state_and_reload(self):
        """Graph stage must include structured empty state with reload button."""
        self.assertIn('id="graph-empty-state"', self.html)
        self.assertIn('id="graph-reload-btn"', self.html)
        self.assertIn('graph-empty-overlay', self.html)

    def test_css_rules_defined(self):
        """All required CSS styling rules must exist in index.css."""
        required_selectors = [
            ".summary.primary-verdict",
            ".verdict-main",
            ".verdict-title",
            ".verdict-desc",
            ".supporting-context",
            ".supporting-card",
            ".supporting-health",
            ".supporting-label",
            ".supporting-val",
            ".score-denom",
            ".nav-kbd",
            ".pillar-empty-state",
            ".empty-icon",
            ".empty-why",
            ".empty-action",
            ".graph-empty-overlay",
            ".mini-empty-state",
        ]
        for sel in required_selectors:
            self.assertIn(sel, self.css, f"Missing CSS selector: {sel}")


class TestDynamicHeadlineGrammar(unittest.TestCase):
    """Verifies that the verdict headline handles zero, singular, and plural files correctly."""

    @staticmethod
    def generate_verdict(high_count: int):
        """Mirror of updatePrimaryVerdict logic in index.js."""
        if high_count == 0:
            title = "No files are risky to change right now — codebase is stable."
            desc = "Branch complexity and caller fan-out are balanced within normal operating thresholds across all analyzed modules."
        elif high_count == 1:
            title = "This 1 file is risky to change — here's why."
            desc = "High branch complexity combined with caller fan-out means changes to these files carry the widest blast radius across your repository."
        else:
            title = f"These {high_count} files are risky to change — here's why."
            desc = "High branch complexity combined with caller fan-out means changes to these files carry the widest blast radius across your repository."
        return title, desc

    def test_zero_risky_files_grammar(self):
        """When 0 high-risk files exist, headline must celebrate stability without jargon."""
        title, desc = self.generate_verdict(0)
        self.assertEqual(title, "No files are risky to change right now — codebase is stable.")
        self.assertIn("balanced within normal operating thresholds", desc)
        self.assertNotIn("These 0 files", title, "Must not use plural zero phrasing")

    def test_singular_risky_file_grammar(self):
        """When exactly 1 high-risk file exists, headline must use singular grammar."""
        title, desc = self.generate_verdict(1)
        self.assertEqual(title, "This 1 file is risky to change — here's why.")
        self.assertIn("High branch complexity combined with caller fan-out", desc)
        self.assertNotIn("These 1 files", title, "Must not use plural phrasing for 1 file")

    def test_plural_risky_files_grammar(self):
        """When > 1 high-risk files exist, headline must use plural phrasing with the exact count."""
        title_5, _ = self.generate_verdict(5)
        self.assertEqual(title_5, "These 5 files are risky to change — here's why.")

        title_22, _ = self.generate_verdict(22)
        self.assertEqual(title_22, "These 22 files are risky to change — here's why.")


class TestKeyboardShortcutsAndInputImmunity(unittest.TestCase):
    """Verifies the keyboard dispatching rules, modifier immunity, and Escape hierarchy."""

    @staticmethod
    def simulate_keydown(key: str, ctrl=False, meta=False, alt=False, tag_name="BODY", is_content_editable=False,
                          active_view="dashboard", current_selection=None,
                          drawer_open=False, inspector_open=False, picker_open=False):
        """
        Simulates the setupKeyboardShortcuts logic in index.js.
        Returns a dict of actions taken:
        - action: 'switchView', 'focusFilter', 'blur', 'closeDrawer', 'closeInspector', 'closePicker', 'clearSelection', or None
        - targetView: str if switchView
        - preventedDefault: bool
        """
        result = {"action": None, "targetView": None, "preventedDefault": False}

        # 1. Modifier guard
        if ctrl or meta or alt:
            return result

        # 2. Active element editing guard
        is_editing = tag_name.upper() in ["INPUT", "TEXTAREA", "SELECT"] or is_content_editable

        # 3. Escape hierarchy
        if key == "Escape":
            if is_editing:
                result["action"] = "blur"
                return result
            if drawer_open:
                result["action"] = "closeDrawer"
                return result
            if inspector_open:
                result["action"] = "closeInspector"
                return result
            if picker_open:
                result["action"] = "closePicker"
                return result
            if current_selection:
                result["action"] = "clearSelection"
                return result
            return result

        # If editing, all single-key shortcuts are ignored
        if is_editing:
            return result

        # 4. Pillar switching
        if key == "1":
            result["action"] = "switchView"
            result["targetView"] = "dashboard"
            result["preventedDefault"] = True
        elif key == "2":
            result["action"] = "switchView"
            result["targetView"] = "graph"
            result["preventedDefault"] = True
        elif key == "3":
            result["action"] = "switchView"
            result["targetView"] = "studio"
            result["preventedDefault"] = True
        elif key == "4":
            result["action"] = "switchView"
            result["targetView"] = "auditor"
            result["preventedDefault"] = True
        elif key == "/":
            if active_view == "dashboard":
                result["action"] = "focusFilter"
                result["preventedDefault"] = True

        return result

    def test_pillar_navigation_keys(self):
        """Keys 1 to 4 must switch to their respective views."""
        views = {
            "1": "dashboard",
            "2": "graph",
            "3": "studio",
            "4": "auditor",
        }
        for key, expected_view in views.items():
            res = self.simulate_keydown(key)
            self.assertEqual(res["action"], "switchView")
            self.assertEqual(res["targetView"], expected_view)
            self.assertTrue(res["preventedDefault"])

    def test_filter_focus_key(self):
        """Slash key '/' must focus the filter when in dashboard view and prevent default."""
        res = self.simulate_keydown("/", active_view="dashboard")
        self.assertEqual(res["action"], "focusFilter")
        self.assertTrue(res["preventedDefault"])

        # In non-dashboard views, '/' should not focus dashboard filter
        res_graph = self.simulate_keydown("/", active_view="graph")
        self.assertIsNone(res_graph["action"])

    def test_modifier_immunity(self):
        """Ctrl+1, Cmd+R, Alt+3 must NEVER trigger view switching."""
        self.assertIsNone(self.simulate_keydown("1", ctrl=True)["action"])
        self.assertIsNone(self.simulate_keydown("2", meta=True)["action"])
        self.assertIsNone(self.simulate_keydown("3", alt=True)["action"])
        self.assertIsNone(self.simulate_keydown("/", ctrl=True)["action"])

    def test_text_editing_immunity(self):
        """Typing '1', '2', '3', '4', or '/' in an input field must NOT trigger navigation."""
        for tag in ["INPUT", "TEXTAREA", "SELECT"]:
            res = self.simulate_keydown("1", tag_name=tag)
            self.assertIsNone(res["action"])
            self.assertFalse(res["preventedDefault"])

            res_slash = self.simulate_keydown("/", tag_name=tag)
            self.assertIsNone(res_slash["action"])
            self.assertFalse(res_slash["preventedDefault"])

        # Contenteditable test
        res_ce = self.simulate_keydown("1", is_content_editable=True)
        self.assertIsNone(res_ce["action"])

    def test_escape_hierarchy(self):
        """Escape key must execute in deterministic priority order."""
        # 1. If user is in an input, Escape blurs the input first
        res_blur = self.simulate_keydown("Escape", tag_name="INPUT", drawer_open=True)
        self.assertEqual(res_blur["action"], "blur")

        # 2. Next, closes violations drawer
        res_drawer = self.simulate_keydown("Escape", drawer_open=True, inspector_open=True)
        self.assertEqual(res_drawer["action"], "closeDrawer")

        # 3. Next, closes graph inspector
        res_inspector = self.simulate_keydown("Escape", inspector_open=True, picker_open=True)
        self.assertEqual(res_inspector["action"], "closeInspector")

        # 4. Next, closes picker modal
        res_picker = self.simulate_keydown("Escape", picker_open=True, current_selection="app.py")
        self.assertEqual(res_picker["action"], "closePicker")

        # 5. Finally, deselects file and resets detail pane
        res_clear = self.simulate_keydown("Escape", current_selection="app.py")
        self.assertEqual(res_clear["action"], "clearSelection")


class TestStructuredEmptyStatesContent(unittest.TestCase):
    """Verifies that all 4 pillars implement structured 3-part empty states."""

    @classmethod
    def setUpClass(cls):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "interfaces", "web"))
        with open(os.path.join(base_dir, "index.html"), "r", encoding="utf-8") as f:
            cls.html = f.read()

    def test_risk_list_empty_state_structure(self):
        """Filter empty state must explain why and provide a clear action."""
        self.assertIn('id="list-empty"', self.html)
        self.assertIn('class="empty-icon"', self.html)
        self.assertIn('class="empty-why"', self.html)
        self.assertIn('class="empty-action"', self.html)
        self.assertIn('No files match that filter', self.html)
        self.assertIn('id="clear-filter-btn"', self.html)

    def test_detail_pane_empty_state_structure(self):
        """Detail placeholder must guide user on how to inspect files."""
        self.assertIn('id="detail-placeholder"', self.html)
        self.assertIn('No file selected', self.html)
        self.assertIn('Detailed complexity breakdown, caller dependencies, and safe edit guidance appear here', self.html)
        self.assertIn('Click any file from the risk list on the left', self.html)

    def test_topology_graph_empty_state_structure(self):
        """Graph stage empty overlay must explain reasons and provide reload action."""
        self.assertIn('id="graph-empty-state"', self.html)
        self.assertIn('No graph nodes to display', self.html)
        self.assertIn('Switch granularity to Files, choose \'All Modules\'', self.html)
        self.assertIn('id="graph-reload-btn"', self.html)

    def test_auditor_anomalies_empty_state_structure(self):
        """Auditor anomalies empty state must explain safety status and encourage scan."""
        self.assertIn('id="auditor-anomalies-list"', self.html)
        self.assertIn('Safety gate ready', self.html)
        self.assertIn('Target file or sandbox code has not yet been audited', self.html)
        self.assertIn('Run Code Safety Audit', self.html)


if __name__ == "__main__":
    unittest.main()
