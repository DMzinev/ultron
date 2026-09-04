"""
ultron.core.ci_reporter
Automated CI/CD GitHub Action PR Review Commenter & Quality Regression Gate.
Synthesizes developer context, PR delta impact, omitted co-changes, and actionable remediations.
"""

import json
from typing import Dict, List, Any, Optional, Set, Tuple


class CIReporter:
    """
    Evaluates architectural regression against baseline analysis snapshots,
    detects omitted co-change dependencies, and renders rich, actionable
    GitHub/GitLab PR review comments.
    """

    @classmethod
    def _extract_health(cls, analysis: Optional[Dict[str, Any]]) -> float:
        """Extracts codebase health score from analysis dictionary (defaults to 100.0)."""
        if not analysis:
            return 100.0
        if "health_score" in analysis:
            return float(analysis["health_score"])
        if "modularity" in analysis and "overall_health_score" in analysis["modularity"]:
            return float(analysis["modularity"]["overall_health_score"])
        
        # Approximate health from risks if not explicitly scored
        risks = analysis.get("risks", [])
        if not risks:
            return 100.0
        high_count = sum(1 for r in risks if (r.get("level") == "HIGH" or (float(r.get("impact_score", 0)) >= 8.0)))
        med_count = sum(1 for r in risks if (r.get("level") == "MEDIUM" or (4.0 <= float(r.get("impact_score", 0)) < 8.0)))
        penalty = (high_count * 10.0) + (med_count * 3.0)
        return max(0.0, min(100.0, round(100.0 - penalty, 2)))

    @classmethod
    def _extract_averages(cls, analysis: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """Extracts average complexity and coupling."""
        if not analysis or "risks" not in analysis or not analysis["risks"]:
            return {"avg_complexity": 1.0, "avg_coupling": 0.0}
        risks = analysis["risks"]
        comp = sum(float(r.get("complexity", 1.0)) for r in risks) / len(risks)
        coup = sum(float(r.get("coupling_score", 0.0)) for r in risks) / len(risks)
        return {"avg_complexity": round(comp, 2), "avg_coupling": round(coup, 2)}

    @classmethod
    def _compute_pr_delta_impact(
        cls,
        current_analysis: Dict[str, Any],
        baseline_analysis: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Computes per-file delta impact for files touched in the PR:
        complexity introduced, coupling added, and risk level transitions.
        """
        curr_risks = {
            str(r.get("file_path", r.get("file", ""))).replace("\\", "/"): r
            for r in current_analysis.get("risks", [])
        }
        base_risks = {
            str(r.get("file_path", r.get("file", ""))).replace("\\", "/"): r
            for r in (baseline_analysis.get("risks", []) if baseline_analysis else [])
        }

        # If explicit changed_files provided:
        explicit_changed = [str(f).replace("\\", "/") for f in current_analysis.get("changed_files", [])]
        candidate_files = explicit_changed if explicit_changed else list(curr_risks.keys())

        delta_table: List[Dict[str, Any]] = []

        for fp in candidate_files:
            if not fp:
                continue
            curr_r = curr_risks.get(fp, {})
            base_r = base_risks.get(fp, {})

            curr_comp = float(curr_r.get("complexity", 1.0))
            base_comp = float(base_r.get("complexity", curr_comp if not baseline_analysis else 0.0))
            comp_diff = round(curr_comp - base_comp, 2) if (baseline_analysis and fp in base_risks) else 0.0

            curr_coup = float(curr_r.get("coupling_score", 0.0))
            base_coup = float(base_r.get("coupling_score", curr_coup if not baseline_analysis else 0.0))
            coup_diff = round(curr_coup - base_coup, 2) if (baseline_analysis and fp in base_risks) else 0.0

            curr_impact = float(curr_r.get("impact_score", 0.0))
            base_impact = float(base_r.get("impact_score", curr_impact if not baseline_analysis else 0.0))
            impact_diff = round(curr_impact - base_impact, 2) if (baseline_analysis and fp in base_risks) else 0.0

            is_new = bool(baseline_analysis and fp not in base_risks)
            level = curr_r.get("level", "LOW")

            # Determine status description
            if is_new:
                status_desc = "✨ New File"
            elif comp_diff > 2.0 or coup_diff > 2.0 or impact_diff > 2.0:
                status_desc = "⚠️ Complexity Surge" if comp_diff > 2.0 else "⚠️ Coupling Surge"
            elif comp_diff < 0 or coup_diff < 0:
                status_desc = "🟢 Refactored"
            else:
                status_desc = "Stable"

            delta_table.append({
                "file": fp,
                "curr_complexity": curr_comp,
                "base_complexity": base_comp,
                "complexity_delta": comp_diff,
                "curr_coupling": curr_coup,
                "base_coupling": base_coup,
                "coupling_delta": coup_diff,
                "curr_impact": curr_impact,
                "impact_delta": impact_diff,
                "is_new": is_new,
                "level": level,
                "status": status_desc
            })

        # Sort files by highest complexity delta / impact score
        delta_table.sort(key=lambda x: (x["complexity_delta"], x["curr_impact"]), reverse=True)
        return delta_table

    @classmethod
    def _detect_omitted_co_changes(
        cls,
        current_analysis: Dict[str, Any],
        baseline_analysis: Optional[Dict[str, Any]] = None,
        min_ratio: float = 0.50
    ) -> List[Dict[str, Any]]:
        """
        Identifies files that strongly co-evolve with files changed in the PR
        but were omitted from the current PR commit/analysis.
        """
        # 1. Determine changed files
        changed_files: Set[str] = set()
        if "changed_files" in current_analysis and current_analysis["changed_files"]:
            changed_files = {str(f).replace("\\", "/") for f in current_analysis["changed_files"]}
        else:
            curr_risks = {
                str(r.get("file_path", r.get("file", ""))).replace("\\", "/"): r
                for r in current_analysis.get("risks", [])
            }
            base_risks = {
                str(r.get("file_path", r.get("file", ""))).replace("\\", "/"): r
                for r in (baseline_analysis.get("risks", []) if baseline_analysis else [])
            }

            if base_risks:
                for f, curr_r in curr_risks.items():
                    if f not in base_risks:
                        changed_files.add(f)
                    else:
                        base_r = base_risks[f]
                        if (curr_r.get("complexity") != base_r.get("complexity") or
                            curr_r.get("coupling_score") != base_r.get("coupling_score") or
                            curr_r.get("impact_score") != base_r.get("impact_score")):
                            changed_files.add(f)
            else:
                changed_files = set(curr_risks.keys())

        # 2. Extract co-change matrix
        co_change_map: Dict[str, List[Dict[str, Any]]] = {}
        if "co_change_matrix" in current_analysis:
            co_change_map = current_analysis["co_change_matrix"]
        elif "git" in current_analysis and isinstance(current_analysis["git"], dict) and "co_change_matrix" in current_analysis["git"]:
            co_change_map = current_analysis["git"]["co_change_matrix"]
        else:
            for r in current_analysis.get("risks", []):
                fp = str(r.get("file_path", r.get("file", ""))).replace("\\", "/")
                if "co_changes" in r and r["co_changes"]:
                    co_change_map[fp] = r["co_changes"]

        omitted: List[Dict[str, Any]] = []
        seen_pairs: Set[Tuple[str, str]] = set()

        for changed_f in sorted(changed_files):
            partners = co_change_map.get(changed_f, [])
            for p in partners:
                partner_f = str(p.get("file", "")).replace("\\", "/")
                if not partner_f or partner_f == changed_f:
                    continue
                ratio = float(p.get("co_change_ratio", 0.0))
                joint = int(p.get("joint_commits", 0))
                if ratio >= min_ratio and partner_f not in changed_files:
                    pair_key = (changed_f, partner_f)
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        percent = int(round(ratio * 100))
                        omitted.append({
                            "changed_file": changed_f,
                            "omitted_file": partner_f,
                            "co_change_ratio": ratio,
                            "percentage": percent,
                            "joint_commits": joint,
                            "warning": f"⚠️ Forgotten Dependency: '{partner_f}' frequently changes alongside '{changed_f}' ({percent}% rate) but was omitted from this PR."
                        })

        omitted.sort(key=lambda x: (x["co_change_ratio"], x["joint_commits"]), reverse=True)
        return omitted

    @classmethod
    def _generate_remediations(
        cls,
        gate: Dict[str, Any],
        current_analysis: Dict[str, Any],
        omitted_co_changes: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Produces concise, plain-English instructions on how to resolve failures,
        reduce complexity surges, fix policy violations, and handle forgotten dependencies.
        """
        remediations: List[str] = []

        # 1. Health Drop Remediation
        if not gate["passed"]:
            if gate["health_delta"] < -abs(gate["thresholds"]["max_health_drop"]):
                remediations.append(
                    f"**Architectural Health Recovery:** Overall health score dropped by `{abs(gate['health_delta'])} pts`. "
                    f"Review high-complexity modules and split monolithic functions into smaller, single-purpose utilities."
                )

        # 2. Policy Violations Remediation
        violations = current_analysis.get("policy_violations", [])
        for v in violations:
            if v.get("severity") in ("CRITICAL", "HIGH", "MEDIUM"):
                rule = v.get("rule_type") or v.get("rule_name") or "ARCH_POLICY"
                target = str(v.get("source", v.get("source_file", v.get("target", "")))).replace("\\", "/")
                msg = v.get("message", "Policy threshold breached.")
                remed = v.get("remediation", "Refactor the module to respect architectural boundaries.")
                remediations.append(
                    f"**Fix Policy Breach in `{target}` (`{rule}`):** {msg} *Remediation:* {remed}"
                )

        # 3. Omitted Co-Changes Remediation
        if omitted_co_changes:
            for oc in omitted_co_changes[:3]:
                remediations.append(
                    f"**Verify Omitted Dependency `{oc['omitted_file']}`:** Historically changed in {oc['percentage']}% of commits with `{oc['changed_file']}`. "
                    f"Verify if interfaces, types, or tests in `{oc['omitted_file']}` require synchronized updates."
                )

        # 4. If passed and clean
        if not remediations:
            remediations.append(
                "✅ **Clean Architecture:** No quality blockers or omitted dependencies detected. Ready for merge."
            )

        return remediations

    @classmethod
    def evaluate_regression_gate(
        cls,
        current_analysis: Dict[str, Any],
        baseline_analysis: Optional[Dict[str, Any]] = None,
        max_health_drop: float = 5.0,
        fail_on_high: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluates whether the current PR passes architectural quality gates.
        Returns structured decision payload with deterministic reasons.
        """
        curr_health = cls._extract_health(current_analysis)
        base_health = cls._extract_health(baseline_analysis) if baseline_analysis else curr_health
        health_delta = round(curr_health - base_health, 2)

        curr_avg = cls._extract_averages(current_analysis)
        base_avg = cls._extract_averages(baseline_analysis) if baseline_analysis else curr_avg

        complexity_delta = round(curr_avg["avg_complexity"] - base_avg["avg_complexity"], 2)
        coupling_delta = round(curr_avg["avg_coupling"] - base_avg["avg_coupling"], 2)

        # Policy Violations
        violations = current_analysis.get("policy_violations", [])
        high_violations = [v for v in violations if v.get("severity") in ("CRITICAL", "HIGH")]

        reasons: List[str] = []
        passed = True

        # Gate 1: Max Health Drop
        if baseline_analysis and health_delta < -abs(max_health_drop):
            passed = False
            reasons.append(f"Architectural Health dropped by {abs(health_delta)} pts (allowed: {max_health_drop} pts).")

        # Gate 2: High Severity Violations
        if fail_on_high and high_violations:
            passed = False
            reasons.append(f"{len(high_violations)} HIGH/CRITICAL policy violation(s) detected in PR branch.")

        return {
            "passed": passed,
            "current_health": curr_health,
            "baseline_health": base_health,
            "health_delta": health_delta,
            "avg_complexity_delta": complexity_delta,
            "avg_coupling_delta": coupling_delta,
            "high_violations_count": len(high_violations),
            "total_violations_count": len(violations),
            "reasons": reasons,
            "thresholds": {
                "max_health_drop": max_health_drop,
                "fail_on_high": fail_on_high
            }
        }

    @classmethod
    def generate_pr_comment(
        cls,
        current_analysis: Dict[str, Any],
        baseline_analysis: Optional[Dict[str, Any]] = None,
        project_name: str = "Ultron Architecture",
        max_health_drop: float = 5.0,
        fail_on_high: bool = True
    ) -> str:
        """
        Generates rich, deterministic GitHub Action / GitLab sticky PR comment Markdown.
        Includes Pass/Fail status banner, KPI deltas, PR delta impact table,
        omitted co-change warnings, and actionable remediation steps.
        """
        gate = cls.evaluate_regression_gate(
            current_analysis,
            baseline_analysis,
            max_health_drop=max_health_drop,
            fail_on_high=fail_on_high
        )

        passed = gate["passed"]
        shield_badge = (
            "https://img.shields.io/badge/Architecture_Gate-PASSED-brightgreen"
            if passed
            else "https://img.shields.io/badge/Architecture_Gate-FAILED-red"
        )

        curr_health = gate["current_health"]
        base_health = gate["baseline_health"]
        h_delta = gate["health_delta"]
        h_sign = f"+{h_delta}" if h_delta > 0 else f"{h_delta}"
        h_status = "✅ PASS" if h_delta >= 0 else ("⚠️ DROP" if h_delta >= -abs(max_health_drop) else "❌ FAIL")

        curr_avg = cls._extract_averages(current_analysis)
        base_avg = cls._extract_averages(baseline_analysis) if baseline_analysis else curr_avg
        c_delta = gate["avg_complexity_delta"]
        c_sign = f"+{c_delta}" if c_delta > 0 else f"{c_delta}"

        coup_delta = gate["avg_coupling_delta"]
        coup_sign = f"+{coup_delta}" if coup_delta > 0 else f"{coup_delta}"

        md_lines = [
            f"## 🏛️ {project_name} — CI/CD Architectural Gate",
            f"",
            f"![Ultron Gate Status]({shield_badge})",
            f"",
            f"### 📊 Key Performance Indicators (KPIs)",
            f"| Architectural Metric | Baseline | PR Branch | Delta | Status |",
            f"|---|---|---|---|---|",
            f"| **Health Score** | {base_health:.1f} / 100 | {curr_health:.1f} / 100 | `{h_sign}` | {h_status} |",
            f"| **Avg Complexity** | {base_avg['avg_complexity']:.2f} | {curr_avg['avg_complexity']:.2f} | `{c_sign}` | {'✅' if c_delta <= 0 else '⚠️'} |",
            f"| **Avg Coupling** | {base_avg['avg_coupling']:.2f} | {curr_avg['avg_coupling']:.2f} | `{coup_sign}` | {'✅' if coup_delta <= 0 else '⚠️'} |",
            f"| **Policy Violations** | 0 | {gate['total_violations_count']} | `+{gate['total_violations_count']}` | {'✅' if gate['high_violations_count'] == 0 else '❌'} |",
            f""
        ]

        if not passed and gate["reasons"]:
            md_lines.append("### ❌ Quality Gate Failures")
            for r in gate["reasons"]:
                md_lines.append(f"- **BLOCKER**: {r}")
            md_lines.append("")

        # 1. PR Delta Impact Table
        delta_table = cls._compute_pr_delta_impact(current_analysis, baseline_analysis)
        if delta_table:
            md_lines.append("### 📈 PR Delta Impact Breakdown")
            md_lines.append("| Changed File | Complexity | Coupling | Net Risk Impact | Change Status |")
            md_lines.append("|---|---|---|---|---|")
            for row in delta_table[:8]:
                fp = f"`{row['file']}`"
                if row["is_new"]:
                    comp_str = f"{row['curr_complexity']:.1f} (`NEW`)"
                    coup_str = f"{row['curr_coupling']:.1f} (`NEW`)"
                    impact_str = f"{row['curr_impact']:.2f} (`NEW`)"
                else:
                    c_diff_str = f"+{row['complexity_delta']}" if row['complexity_delta'] > 0 else f"{row['complexity_delta']}"
                    comp_str = f"{row['curr_complexity']:.1f} (`{c_diff_str}`)"

                    cp_diff_str = f"+{row['coupling_delta']}" if row['coupling_delta'] > 0 else f"{row['coupling_delta']}"
                    coup_str = f"{row['curr_coupling']:.1f} (`{cp_diff_str}`)"

                    imp_diff_str = f"+{row['impact_delta']}" if row['impact_delta'] > 0 else f"{row['impact_delta']}"
                    impact_str = f"{row['curr_impact']:.2f} (`{imp_diff_str}`)"

                md_lines.append(f"| {fp} | {comp_str} | {coup_str} | {impact_str} | {row['status']} |")
            md_lines.append("")

        # 2. Omitted Co-Change Warnings (Hidden Dependencies)
        omitted_warnings = cls._detect_omitted_co_changes(current_analysis, baseline_analysis)
        if omitted_warnings:
            md_lines.append("### ⚠️ Forgotten Co-Change Warnings")
            md_lines.append("> Temporal coupling analysis detected files that strongly co-evolve with your changes but were omitted from this PR:")
            for ow in omitted_warnings:
                commits_info = f", {ow['joint_commits']} shared commits" if ow["joint_commits"] > 0 else ""
                md_lines.append(
                    f"- ⚠️ **Forgotten Dependency:** `{ow['omitted_file']}` frequently changes alongside "
                    f"`{ow['changed_file']}` (**{ow['percentage']}% rate**{commits_info}) but was omitted from this PR."
                )
            md_lines.append("")

        # 3. Actionable Remediation Section
        remediations = cls._generate_remediations(gate, current_analysis, omitted_warnings)
        md_lines.append("### 🛠️ Actionable Remediation & Next Steps")
        md_lines.append("To resolve regressions and bring this PR into compliance:")
        for idx, step in enumerate(remediations, 1):
            md_lines.append(f"{idx}. {step}")
        md_lines.append("")
        md_lines.append("💡 **Verify Locally:**")
        md_lines.append("```bash")
        md_lines.append("python -m ultron ci --repo . --baseline baseline.json")
        md_lines.append("```")
        md_lines.append("")

        # 4. Top 5 High-Impact File Hotspots in PR (Collapsible)
        risks = current_analysis.get("risks", [])
        if risks:
            top_risks = sorted(risks, key=lambda x: float(x.get("impact_score", 0)), reverse=True)[:5]
            md_lines.append("<details>")
            md_lines.append("<summary><b>🔍 Top 5 High-Impact File Hotspots in PR</b></summary>")
            md_lines.append("")
            md_lines.append("| File Module | Complexity | Coupling | Impact Score | Risk Level |")
            md_lines.append("|---|---|---|---|---|")
            for r in top_risks:
                fp = str(r.get("file_path", r.get("file", ""))).replace("\\", "/")
                comp = r.get("complexity", 1)
                coup = r.get("coupling_score", 0)
                impact = float(r.get("impact_score", 0))
                lvl = r.get("level", "LOW")
                md_lines.append(f"| `{fp}` | {comp} | {coup} | {impact:.2f} | **{lvl}** |")
            md_lines.append("")
            md_lines.append("</details>")
            md_lines.append("")

        # 5. Policy Violations Detail (Collapsible)
        violations = current_analysis.get("policy_violations", [])
        if violations:
            md_lines.append("<details open>")
            md_lines.append("<summary><b>⚠️ Policy Governance Violations</b></summary>")
            md_lines.append("")
            md_lines.append("| Severity | Rule Type | Source Target | Message |")
            md_lines.append("|---|---|---|---|")
            for v in violations:
                sev = v.get("severity", "MEDIUM")
                rtype = v.get("rule_type", "POLICY")
                target = str(v.get("source", v.get("source_file", v.get("target", "")))).replace("\\", "/")
                msg = v.get("message", "")
                md_lines.append(f"| **{sev}** | `{rtype}` | `{target}` | {msg} |")
            md_lines.append("")
            md_lines.append("</details>")
            md_lines.append("")

        md_lines.append("---")
        md_lines.append("*Generated by [Ultron Risk Scorer](https://github.com/DMzinev/ultron) — Continuous Architectural Intelligence Engine.*")

        return "\n".join(md_lines)

