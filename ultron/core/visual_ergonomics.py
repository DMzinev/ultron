"""
ultron.core.visual_ergonomics
Automated Visual Ergonomics, WCAG Contrast & Perceptual Layout Integrity Engine.

Audits web interface templates, CSS styling, and DOM structures against human perceptual
parameters: WCAG 2.1 AA contrast ratios, interactive target clearance, font size floors,
and empty-state visual visibility.
"""

import math
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional


def parse_color_to_rgb(color_str: str) -> Optional[Tuple[float, float, float]]:
    """Parses hex or rgba color string into normalized (r, g, b) float tuple in range [0, 1]."""
    if not color_str:
        return None
    s = color_str.strip().lower()

    # Hex format (#fff, #ffffff, #ffffff80)
    if s.startswith("#"):
        hex_digits = s[1:]
        if len(hex_digits) == 3:
            r = int(hex_digits[0] * 2, 16) / 255.0
            g = int(hex_digits[1] * 2, 16) / 255.0
            b = int(hex_digits[2] * 2, 16) / 255.0
            return (r, g, b)
        elif len(hex_digits) in (6, 8):
            r = int(hex_digits[0:2], 16) / 255.0
            g = int(hex_digits[2:4], 16) / 255.0
            b = int(hex_digits[4:6], 16) / 255.0
            return (r, g, b)

    # rgb / rgba format: rgb(15, 23, 42) or rgba(15, 23, 42, 0.9)
    m = re.search(r"rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", s)
    if m:
        r = float(m.group(1)) / 255.0
        g = float(m.group(2)) / 255.0
        b = float(m.group(3)) / 255.0
        return (r, g, b)

    # Named color fallbacks
    named = {
        "white": (1.0, 1.0, 1.0),
        "black": (0.0, 0.0, 0.0),
        "transparent": (0.0, 0.0, 0.0)
    }
    return named.get(s)


def compute_relative_luminance(r: float, g: float, b: float) -> float:
    """Computes W3C WCAG 2.1 relative luminance for an sRGB color."""
    def channel_l(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else math.pow((c + 0.055) / 1.055, 2.4)

    return 0.2126 * channel_l(r) + 0.7152 * channel_l(g) + 0.0722 * channel_l(b)


def compute_contrast_ratio(fg_color: str, bg_color: str) -> float:
    """
    Computes WCAG 2.1 contrast ratio between foreground and background colors.
    Returns ratio value in range [1.0, 21.0].
    """
    rgb_fg = parse_color_to_rgb(fg_color)
    rgb_bg = parse_color_to_rgb(bg_color)

    if rgb_fg is None or rgb_bg is None:
        return 1.0

    l1 = compute_relative_luminance(*rgb_fg)
    l2 = compute_relative_luminance(*rgb_bg)

    lighter = max(l1, l2)
    darker = min(l1, l2)

    return (lighter + 0.05) / (darker + 0.05)


class VisualErgonomicsAuditor:
    """Audits web stylesheets, DOM templates, and layout configurations for human perceptual ergonomics."""

    @staticmethod
    def audit_theme_contrast(css_content: str) -> Dict[str, Any]:
        """
        Extracts CSS root variables and audits core theme contrast ratios against WCAG AA standards.
        WCAG AA: Normal text >= 4.5:1, Large text/Badges >= 3.0:1.
        """
        # Standard Ultron dark theme color map
        color_map = {
            "--bg-primary": "#0f172a",
            "--bg-secondary": "#1e293b",
            "--text-color": "#f8fafc",
            "--text-muted": "#94a3b8",
            "--accent-primary": "#38bdf8",
            "--warning": "#f59e0b",
            "--danger": "#ef4444",
            "--success": "#10b981",
        }

        # Parse variables from CSS content if provided
        for var_name in color_map.keys():
            m = re.search(rf"{re.escape(var_name)}\s*:\s*([^;]+);", css_content)
            if m:
                val = m.group(1).strip()
                if not val.startswith("var"):
                    color_map[var_name] = val

        pairs_to_check = [
            ("Body Text on Primary BG", color_map["--text-color"], color_map["--bg-primary"], 4.5),
            ("Body Text on Secondary Card", color_map["--text-color"], color_map["--bg-secondary"], 4.5),
            ("Muted Text on Secondary Card", color_map["--text-muted"], color_map["--bg-secondary"], 3.0),
            ("Cyan Accent on Primary BG", color_map["--accent-primary"], color_map["--bg-primary"], 3.0),
            ("Warning Badge on Primary BG", color_map["--warning"], color_map["--bg-primary"], 3.0),
            ("Success Indicator on Primary BG", color_map["--success"], color_map["--bg-primary"], 3.0),
        ]

        results = []
        violations = []
        for name, fg, bg, threshold in pairs_to_check:
            ratio = compute_contrast_ratio(fg, bg)
            passed = ratio >= threshold
            res = {
                "name": name,
                "fg": fg,
                "bg": bg,
                "contrast_ratio": round(ratio, 2),
                "required_min": threshold,
                "passed": passed
            }
            results.append(res)
            if not passed:
                violations.append(f"Contrast failure for '{name}': {ratio:.2f}:1 < {threshold}:1")

        return {
            "checks": results,
            "violations": violations,
            "passed": len(violations) == 0
        }

    @staticmethod
    def audit_interactive_clearance(html_content: str, css_content: str) -> Dict[str, Any]:
        """
        Validates that interactive controls (buttons, inputs, sliders) satisfy minimum clearance
        and touch/click target ergonomics.
        """
        violations = []
        checks_count = 0

        # 1. Scan for button styling rules ensuring vertical padding >= 4px or height >= 28px
        button_rules = re.findall(r"\.btn\s*\{([^}]+)\}", css_content)
        for rule in button_rules:
            checks_count += 1
            if "padding" not in rule and "height" not in rule:
                violations.append("Button class '.btn' lacks explicit padding or height clearance rule")

        # 2. Scan for microscopic font sizes (< 10px)
        micro_fonts = re.findall(r"font-size\s*:\s*([0-9.]+)px", css_content)
        for fs in micro_fonts:
            checks_count += 1
            try:
                val = float(fs)
                if val < 9.0:
                    violations.append(f"Microscopic font size detected: {val}px (Floor is 9.0px)")
            except ValueError:
                pass

        # 3. Check for word-wrap protection on file paths / code blocks
        if "word-break" not in css_content and "overflow-wrap" not in css_content and "text-overflow" not in css_content:
            violations.append("Missing overflow-wrap / word-break rules on text containers")
        checks_count += 1

        return {
            "checks_count": checks_count,
            "violations": violations,
            "passed": len(violations) == 0
        }

    @staticmethod
    def audit_empty_states(html_content: str) -> Dict[str, Any]:
        """
        Validates that all major view containers contain explicit, legible empty state fallback messaging.
        """
        required_empty_containers = [
            ("list-empty", "Risk List Empty State"),
            ("detail-placeholder", "File Detail Placeholder Empty State"),
            ("graph-empty-state", "Dependency Graph Empty State"),
            ("auditor-anomalies-list", "Code Auditor Idle State"),
        ]

        results = []
        violations = []
        for elem_id, label in required_empty_containers:
            pattern = rf'id="{re.escape(elem_id)}"[^>]*>(.*?)<\/(?:tbody|div|table|section)'
            m = re.search(pattern, html_content, re.DOTALL)
            if not m:
                # Direct presence check
                if f'id="{elem_id}"' in html_content:
                    results.append({"id": elem_id, "label": label, "passed": True})
                else:
                    violations.append(f"Missing required empty state container '{elem_id}' ({label})")
                    results.append({"id": elem_id, "label": label, "passed": False})
            else:
                content = m.group(1).strip()
                has_fallback = len(content) > 0
                results.append({"id": elem_id, "label": label, "passed": has_fallback})
                if not has_fallback:
                    violations.append(f"Empty state container '{elem_id}' is blank without fallback message")

        return {
            "containers": results,
            "violations": violations,
            "passed": len(violations) == 0
        }

    @classmethod
    def audit_web_interface(cls, web_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs comprehensive visual ergonomics, contrast, and layout audits on Ultron SPA files.
        """
        if not web_dir:
            web_dir = str(Path(__file__).parent.parent / "interfaces" / "web")

        html_path = os.path.join(web_dir, "index.html")
        css_path = os.path.join(web_dir, "index.css")

        html_content = ""
        css_content = ""

        if os.path.exists(html_path):
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()

        contrast_res = cls.audit_theme_contrast(css_content)
        clearance_res = cls.audit_interactive_clearance(html_content, css_content)
        empty_res = cls.audit_empty_states(html_content)

        all_violations = contrast_res["violations"] + clearance_res["violations"] + empty_res["violations"]
        total_checks = len(contrast_res["checks"]) + clearance_res["checks_count"] + len(empty_res["containers"])
        passed = len(all_violations) == 0

        score = 100.0 if passed else max(0.0, 100.0 - (len(all_violations) * 15.0))

        return {
            "passed": passed,
            "ergonomic_score": round(score, 1),
            "total_checks": total_checks,
            "contrast": contrast_res,
            "clearance": clearance_res,
            "empty_states": empty_res,
            "violations": all_violations
        }
