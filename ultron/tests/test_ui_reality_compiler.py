"""
ultron.tests.test_ui_reality_compiler
Comprehensive Test Suite for UI Reality Compiler, Spatial Layout Verifier & Interaction Contract Gate ("Rust for UI").
"""

import os
import unittest
from ultron.core.ui_reality_compiler import (
    UIRealityCompiler,
    UIRealityReport,
    UICompileError,
    SpatialElement
)


class TestUIRealityCompiler(unittest.TestCase):
    """Test suite asserting compile-time reality invariants for Ultron Web UI."""

    def test_reality_compiler_full_audit_passes(self):
        """Asserts the active codebase passes the UI Reality Compiler without errors."""
        report = UIRealityCompiler.audit_full_reality()
        self.assertTrue(report.passed, f"UI Reality compilation failed: {report.contract_violations}")
        self.assertGreaterEqual(report.total_elements, 200)
        self.assertGreaterEqual(report.interactive_elements, 25)
        self.assertGreaterEqual(report.full_stack_contracts, 10)
        self.assertEqual(len(report.broken_routes), 0, f"Broken backend routes found: {report.broken_routes}")
        self.assertEqual(len(report.contract_violations), 0, f"Contract violations found: {report.contract_violations}")

    def test_spatial_scene_compilation_and_wireframes(self):
        """Asserts spatial layout bounding boxes and ASCII wireframes for all 5 stages."""
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        html_path = os.path.join(root, "ultron", "interfaces", "web", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        elements = UIRealityCompiler.compile_spatial_scene(html_content)
        self.assertGreater(len(elements), 100)

        # Verify wireframes for all 5 stages
        wireframes = UIRealityCompiler.render_ascii_wireframes(elements)
        for stage in ["OVERVIEW", "STRUCTURE", "WORK_PLAN", "AGENT_CONTEXT", "VERIFY"]:
            self.assertIn(stage, wireframes)
            self.assertIn(stage, wireframes[stage])
            self.assertIn("[TOP HEADER]", wireframes[stage])

    def test_fault_injection_missing_dom_id(self):
        """Fault injection: Asserts missing DOM ID in HTML is flagged as a contract violation."""
        synthetic_html = "<div><button id='btn-other'>Click</button></div>"
        synthetic_js = "document.getElementById('btn-load-repo').onclick = () => {};"
        registered_routes = {"/api/v1/analyze"}

        violations, broken, _ = UIRealityCompiler.verify_interaction_contracts(
            synthetic_html, synthetic_js, registered_routes
        )
        self.assertTrue(any(v.get("error") == "DOM_ID_MISSING" for v in violations))

    def test_fault_injection_missing_js_handler(self):
        """Fault injection: Asserts DOM element without JS listener is flagged."""
        synthetic_html = "<div><button id='btn-load-repo'>Load</button></div>"
        synthetic_js = "// Empty JS without handler"
        registered_routes = {"/api/v1/analyze"}

        violations, broken, _ = UIRealityCompiler.verify_interaction_contracts(
            synthetic_html, synthetic_js, registered_routes
        )
        self.assertTrue(any(v.get("error") == "JS_HANDLER_MISSING" for v in violations))

    def test_fault_injection_unregistered_backend_route(self):
        """Fault injection: Asserts missing backend route is detected."""
        synthetic_html = "<div><button id='btn-load-repo'>Load</button></div>"
        synthetic_js = "document.getElementById('btn-load-repo').onclick = () => {};"
        registered_routes = set()  # Empty routes

        violations, broken, _ = UIRealityCompiler.verify_interaction_contracts(
            synthetic_html, synthetic_js, registered_routes
        )
        self.assertIn("/api/v1/analyze", broken)
        self.assertTrue(any(v.get("error") == "BACKEND_ROUTE_UNREGISTERED" for v in violations))

    def test_fault_injection_spatial_collision(self):
        """Fault injection: Asserts overlapping bounding boxes on same z-index trigger collision."""
        elements = [
            SpatialElement(
                id="btn-alpha",
                tag="button",
                classes=["btn"],
                stage="OVERVIEW",
                category="BUTTON",
                x=100,
                y=100,
                width=100,
                height=40,
                z_index=1,
                is_interactive=True,
                visible=True
            ),
            SpatialElement(
                id="btn-beta",
                tag="button",
                classes=["btn"],
                stage="OVERVIEW",
                category="BUTTON",
                x=120,  # Overlaps horizontally
                y=110,  # Overlaps vertically
                width=100,
                height=40,
                z_index=1,
                is_interactive=True,
                visible=True
            )
        ]
        collisions = UIRealityCompiler.check_spatial_proximity_and_clearance(elements)
        self.assertEqual(len(collisions), 1)
        self.assertEqual(collisions[0]["type"], "SPATIAL_COLLISION")
        self.assertEqual(collisions[0]["element_a"], "btn-alpha")
        self.assertEqual(collisions[0]["element_b"], "btn-beta")


if __name__ == "__main__":
    unittest.main()
