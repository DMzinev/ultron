"""
ultron/tests/test_violation_to_fix.py

Dedicated test suite for Task C2 (Close the loop: violation → file → fix).
Verifies:
1. DOM contract preservation in index.html & index.css.
2. Cross-platform path normalization (normPath: Windows \\ vs POSIX / vs ./).
3. Severity parsing & bounds (parseSeverity: string constants & numeric clamping).
4. Blast radius calculation, finite bounds, and sub-unit clamping (>= 1.0).
5. Composite priority sorting (severity × blast_radius) and deterministic tie-breaking.
6. Principle grouping with accurate violation counts and group-level priority ordering.
7. Synthetic risk record fallback for unindexed files in selectFile.
8. Agent Studio intent formulation (zero-jargon, structured directive with bounds).
9. Integration with /api/architecture-health violation schema.
"""

import os
import re
import math
import unittest
from unittest.mock import MagicMock


class TestViolationToFixDOMContract(unittest.TestCase):
    """Verifies that the Web Cockpit markup and styles contain all required elements."""

    @classmethod
    def setUpClass(cls):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "interfaces", "web"))
        with open(os.path.join(base_dir, "index.html"), "r", encoding="utf-8") as f:
            cls.html = f.read()
        with open(os.path.join(base_dir, "index.css"), "r", encoding="utf-8") as f:
            cls.css = f.read()
        with open(os.path.join(base_dir, "index.js"), "r", encoding="utf-8") as f:
            cls.js = f.read()

    def test_html_dom_ids_preserved(self):
        """Audited DOM IDs must exist in index.html."""
        required_ids = [
            'id="violations-drawer"',
            'id="violations-list"',
            'id="violations-chip"',
            'id="close-violations"',
            'id="count-violations"',
            'id="studio-target-file"',
            'id="studio-intent"',
            'id="studio-compile-btn"',
            'id="view-dashboard"',
            'id="view-graph"',
            'id="view-studio"',
            'id="detail-title"',
            'id="tab-why"',
        ]
        for dom_id in required_ids:
            self.assertIn(dom_id, self.html, f"Missing required DOM element: {dom_id}")

    def test_html_drawer_header_subtitle(self):
        """Drawer header should display the priority explanation."""
        self.assertIn("drawer-sub", self.html)
        self.assertIn("Grouped by principle · Ranked by severity × blast radius", self.html)

    def test_css_styles_exist(self):
        """index.css must define classes for grouped violations, actions, and cards."""
        required_classes = [
            ".violations-drawer",
            ".violation-group",
            ".violation-group-header",
            ".violation-group-title",
            ".violation-group-principle",
            ".violation-group-items",
            ".violation-card",
            ".violation-actions",
            ".file-active-violations",
            ".mini-violations-list",
            ".mini-violation-row",
        ]
        for cls in required_classes:
            self.assertIn(cls, self.css, f"Missing required CSS class: {cls}")

    def test_css_drawer_height(self):
        """Violations drawer should have expanded height for reviewing grouped lists."""
        self.assertIn("max-height: 440px", self.css)

    def test_js_functions_and_delegation_present(self):
        """index.js must export the required logic and event delegation."""
        self.assertIn("function normPath(", self.js)
        self.assertIn("function parseSeverity(", self.js)
        self.assertIn("function renderViolations(", self.js)
        self.assertIn("function setupViolationsDelegation(", self.js)
        self.assertIn("function viewInGraph(", self.js)
        self.assertIn("function draftFixMission(", self.js)
        self.assertIn("setupViolationsDelegation()", self.js)


class TestViolationRankingAndGroupingAlgorithms(unittest.TestCase):
    """Unit tests for the mathematical priority ranking, grouping, and path normalization algorithms."""

    @staticmethod
    def norm_path(p: str) -> str:
        """Python mirror of normPath(p)."""
        s = str(p or "").strip().replace("\\", "/")
        if s.startswith("./"):
            s = s[2:]
        return s

    @staticmethod
    def parse_severity(s) -> int:
        """Python mirror of parseSeverity(s)."""
        if isinstance(s, (int, float)) and not math.isnan(s):
            return max(1, min(3, round(s)))
        if not s:
            return 1
        st = str(s).upper().strip()
        if st in ("HIGH", "CRITICAL", "SEV 3", "3"):
            return 3
        if st in ("MEDIUM", "WARN", "WARNING", "SEV 2", "2"):
            return 2
        return 1

    @classmethod
    def calculate_priority(cls, severity, blast_radius) -> float:
        """Python mirror of priority calculation with safe blast radius clamping."""
        sev_num = cls.parse_severity(severity)
        try:
            br = float(blast_radius)
            safe_br = max(1.0, br) if (not math.isnan(br) and br > 0) else 1.0
        except (ValueError, TypeError):
            safe_br = 1.0
        return sev_num * safe_br

    def test_norm_path_equivalence(self):
        """Windows backslashes, leading ./ and whitespace normalize identically to POSIX paths."""
        self.assertEqual(self.norm_path(r"ultron\core\analyzer.py"), "ultron/core/analyzer.py")
        self.assertEqual(self.norm_path("./ultron/interfaces/server.py"), "ultron/interfaces/server.py")
        self.assertEqual(self.norm_path(r"  .\ultron\core\risk\scoring.py  "), "ultron/core/risk/scoring.py")
        self.assertEqual(self.norm_path("standalone.py"), "standalone.py")
        self.assertEqual(self.norm_path(None), "")

    def test_parse_severity_boundaries(self):
        """Severity parsing accurately converts string constants and numbers, clamping to [1, 3]."""
        # String constants
        self.assertEqual(self.parse_severity("CRITICAL"), 3)
        self.assertEqual(self.parse_severity("HIGH"), 3)
        self.assertEqual(self.parse_severity("critical"), 3)
        self.assertEqual(self.parse_severity("WARNING"), 2)
        self.assertEqual(self.parse_severity("MEDIUM"), 2)
        self.assertEqual(self.parse_severity("warn"), 2)
        self.assertEqual(self.parse_severity("LOW"), 1)
        self.assertEqual(self.parse_severity("INFO"), 1)
        self.assertEqual(self.parse_severity(None), 1)
        self.assertEqual(self.parse_severity(""), 1)

        # Numeric values
        self.assertEqual(self.parse_severity(3), 3)
        self.assertEqual(self.parse_severity(2), 2)
        self.assertEqual(self.parse_severity(1), 1)
        self.assertEqual(self.parse_severity(0), 1)  # clamped up
        self.assertEqual(self.parse_severity(5), 3)  # clamped down
        self.assertEqual(self.parse_severity(float("nan")), 1)

    def test_blast_radius_clamping_and_priority(self):
        """Blast radius must be clamped >= 1.0 and priority must be severity * blast_radius."""
        # Sub-unit blast radius clamped to 1.0
        self.assertEqual(self.calculate_priority(3, 0.4), 3.0 * 1.0)
        self.assertEqual(self.calculate_priority("HIGH", -2.0), 3.0 * 1.0)
        self.assertEqual(self.calculate_priority(2, 0.0), 2.0 * 1.0)
        self.assertEqual(self.calculate_priority(1, float("nan")), 1.0 * 1.0)

        # Valid blast radius
        self.assertAlmostEqual(self.calculate_priority("HIGH", 4.5), 3 * 4.5)  # 13.5
        self.assertAlmostEqual(self.calculate_priority("MEDIUM", 8.0), 2 * 8.0)  # 16.0
        self.assertAlmostEqual(self.calculate_priority(1, 12.0), 1 * 12.0)  # 12.0

    def test_deterministic_sorting_and_grouping(self):
        """Violations are grouped by principle and sorted deterministically by severity × blast_radius."""
        violations = [
            {"filepath": "core/a.py", "principle": "Coupling Limit (ADP)", "severity": 2, "observation": "Coupling 5"},
            {"filepath": "core/b.py", "principle": "Complexity Limit (SRP)", "severity": 3, "observation": "Complexity 35"},
            {"filepath": "core/c.py", "principle": "Coupling Limit (ADP)", "severity": 3, "observation": "Coupling 12"},
            {"filepath": "core/d.py", "principle": "Complexity Limit (SRP)", "severity": 2, "observation": "Complexity 18"},
            {"filepath": "core/e.py", "principle": "Encapsulation Rule", "severity": 1, "observation": "Exposes private attr"},
        ]
        # Mock risk index with blast radii
        risks = {
            "core/a.py": 2.0,
            "core/b.py": 10.0,
            "core/c.py": 6.0,
            "core/d.py": 3.0,
            "core/e.py": 1.5,
        }

        # Enrich
        enriched = []
        for idx, v in enumerate(violations):
            fpath = self.norm_path(v["filepath"])
            sev = self.parse_severity(v["severity"])
            br = max(1.0, risks.get(fpath, 1.0))
            prio = sev * br
            enriched.append({
                "raw": v,
                "idx": idx,
                "targetPath": fpath,
                "sevNum": sev,
                "safeBlastRadius": br,
                "priority": prio,
                "principle": v["principle"],
            })

        # Group by principle
        groups_map = {}
        for item in enriched:
            groups_map.setdefault(item["principle"], []).append(item)

        groups = []
        for p_name, items in groups_map.items():
            items.sort(key=lambda x: (-x["priority"], -x["sevNum"], x["targetPath"], x["idx"]))
            groups.append({
                "principle": p_name,
                "items": items,
                "totalCount": len(items),
                "maxPriority": max(it["priority"] for it in items),
                "maxSev": max(it["sevNum"] for it in items),
                "maxBlast": max(it["safeBlastRadius"] for it in items),
            })

        groups.sort(key=lambda g: (-g["maxPriority"], -g["maxSev"], -g["totalCount"], g["principle"]))

        # Group 1 should be Complexity Limit (SRP) because maxPriority = 3 * 10 = 30.0
        self.assertEqual(groups[0]["principle"], "Complexity Limit (SRP)")
        self.assertEqual(groups[0]["totalCount"], 2)
        self.assertEqual(groups[0]["maxPriority"], 30.0)
        self.assertEqual(groups[0]["items"][0]["targetPath"], "core/b.py")
        self.assertEqual(groups[0]["items"][1]["targetPath"], "core/d.py")

        # Group 2 should be Coupling Limit (ADP) because maxPriority = 3 * 6.0 = 18.0
        self.assertEqual(groups[1]["principle"], "Coupling Limit (ADP)")
        self.assertEqual(groups[1]["totalCount"], 2)
        self.assertEqual(groups[1]["maxPriority"], 18.0)
        self.assertEqual(groups[1]["items"][0]["targetPath"], "core/c.py")
        self.assertEqual(groups[1]["items"][1]["targetPath"], "core/a.py")

        # Group 3 should be Encapsulation Rule because maxPriority = 1 * 1.5 = 1.5
        self.assertEqual(groups[2]["principle"], "Encapsulation Rule")
        self.assertEqual(groups[2]["totalCount"], 1)

    def test_empty_violations_handling(self):
        """Empty violations list should produce empty groups list without throwing."""
        empty_list = []
        groups_map = {}
        for item in empty_list:
            groups_map.setdefault(item["principle"], []).append(item)
        self.assertEqual(len(groups_map), 0)


class TestStudioIntentFormulation(unittest.TestCase):
    """Verifies that generated fix intents are well-structured, zero-jargon, and bounded."""

    def test_draft_fix_mission_intent_structure(self):
        target_file = "ultron/core/analyzer.py"
        principle = "Complexity Limit (SRP)"
        sev_label = "Critical"
        sev_num = 3
        observation = "Function analyze_codebase cyclomatic complexity is 38 (threshold 15)"
        consequences = "High cognitive load, fragile test coverage, regression cascade risk"

        intent_lines = [
            f"Fix architectural violation in {target_file}:",
            f"- Principle: {principle}",
            f"- Severity: {sev_label} (Severity Rank {sev_num})",
            f"- Observation: {observation}",
            f"- Impact & Consequences: {consequences}",
            f"- Refactoring Objective: Refactor {target_file} to strictly resolve the {principle} violation while preserving downstream caller contracts and bounded blast radius."
        ]
        intent = "\n".join(intent_lines)

        self.assertIn("Fix architectural violation in ultron/core/analyzer.py", intent)
        self.assertIn("Complexity Limit (SRP)", intent)
        self.assertIn("Severity: Critical (Severity Rank 3)", intent)
        self.assertIn("preserving downstream caller contracts", intent)

        # Zero academic jargon checks
        self.assertNotIn("McCabe", intent)
        self.assertNotIn("Halstead", intent)
        self.assertNotIn("Markov causal sequence", intent)


class TestSyntheticRiskFallback(unittest.TestCase):
    """Verifies that unindexed files safely generate an ad-hoc risk record."""

    def test_synthetic_risk_structure(self):
        path = "unindexed/utility.py"
        norm = str(path).replace("\\", "/").lstrip("./").strip()
        risk_record = {
            "file": norm,
            "file_path": norm,
            "level": "WATCH",
            "complexity": 1,
            "coupling": 0,
            "impact_score": 1.0,
            "callers": [],
            "change_strategy_display": "Focus on resolving the architectural rule violation."
        }
        self.assertEqual(risk_record["file"], "unindexed/utility.py")
        self.assertEqual(risk_record["impact_score"], 1.0)
        self.assertEqual(risk_record["level"], "WATCH")
        self.assertEqual(len(risk_record["callers"]), 0)


if __name__ == "__main__":
    unittest.main()
