"""
ultron.core.export_engine
Deterministic Architecture Export Engine for generating standalone offline HTML reports,
executive Markdown dossiers, and canonical JSON telemetry bundles.
"""

import json
import html
import time
from typing import Dict, Any, Optional


def norm_path(path_str: Any) -> str:
    """Normalizes file paths to POSIX forward slashes."""
    return str(path_str or "").replace("\\", "/").strip()


class ExportEngine:
    """
    Deterministic export engine providing zero-dependency, self-contained architecture reports.
    """

    EXPORT_VERSION = "1.0-export-bundle"

    @classmethod
    def _normalize_data(cls, analysis_data: Any) -> Dict[str, Any]:
        """Ensures input is a clean dictionary."""
        if analysis_data is None:
            return {}
        if hasattr(analysis_data, "to_dict") and callable(getattr(analysis_data, "to_dict")):
            return analysis_data.to_dict() or {}
        if isinstance(analysis_data, dict):
            return dict(analysis_data)
        return {}

    @classmethod
    def generate_json_bundle(cls, analysis_data: Any) -> str:
        """Generates formatted canonical JSON string."""
        data = cls._normalize_data(analysis_data)
        payload = {
            "export_type": "ultron_architecture_bundle",
            "export_version": cls.EXPORT_VERSION,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "data": data
        }
        return json.dumps(payload, indent=2, default=str)

    @classmethod
    def generate_markdown_dossier(cls, analysis_data: Any, project_name: Optional[str] = None) -> str:
        """Generates an executive Markdown architecture dossier."""
        data = cls._normalize_data(analysis_data)
        name = project_name or data.get("project_name") or "Codebase"
        risks = data.get("risks", []) or []
        modularity = data.get("modularity", {}) or {}
        anti_patterns = data.get("anti_patterns", []) or []
        recommendations = data.get("recommendations", []) or []

        total_modules = len(risks) if risks else int(data.get("total_modules", 0))
        health_score = float(modularity.get("health_score", data.get("health_score", 100.0)) or 100.0)
        grade = modularity.get("grade", "A")

        md_lines = [
            f"# 🛡️ Ultron Executive Architecture Dossier: {name}",
            f"> Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())} | Engine: Ultron v{cls.EXPORT_VERSION}",
            "",
            "## 1. Executive Summary & Health Grade",
            f"- **Architectural Health Grade**: `{grade}` ({health_score:.1f} / 100)",
            f"- **Total Modules Scanned**: `{total_modules}`",
            f"- **Mean Modularity Instability (I)**: `{modularity.get('mean_instability', 0.0):.2f}`",
            f"- **Mean Distance from Main Sequence (D)**: `{modularity.get('mean_distance', 0.0):.2f}`",
            "",
            "## 2. Codebase Risk Matrix (Top Impact Modules)",
            "| Module | Impact Score | Complexity | Coupling (Ca/Ce) | Status |",
            "| :--- | :---: | :---: | :---: | :---: |"
        ]

        if not risks:
            md_lines.append("| *No risk records found* | - | - | - | CLEAN |")
        else:
            sorted_risks = sorted(risks, key=lambda r: float(r.get("impact_score", r.get("risk_score", 0.0)) or 0.0), reverse=True)
            for r in sorted_risks[:15]:
                p = norm_path(r.get("file", r.get("file_path", "unknown")))
                impact = float(r.get("impact_score", r.get("risk_score", 0.0)) or 0.0)
                comp = float(r.get("complexity", 1.0) or 1.0)
                coup = float(r.get("coupling_score", 0.0) or 0.0)
                status = "⚠️ REVIEW" if impact > 10.0 else "✅ STABLE"
                md_lines.append(f"| `{p}` | {impact:.2f} | {comp:.1f} | {coup:.1f} | {status} |")

        md_lines.extend([
            "",
            "## 3. Architectural Anti-Patterns & Drift Warnings",
            "| Severity | Pattern | Module | Remediation Playbook |",
            "| :--- | :--- | :--- | :--- |"
        ])

        if not anti_patterns:
            md_lines.append("| `CLEAN` | None Detected | All Modules | Architecture complies with modularity standards. |")
        else:
            for ap in anti_patterns:
                sev = ap.get("severity", "LOW")
                pname = ap.get("pattern_name", ap.get("pattern_type", "Smell"))
                p = norm_path(ap.get("file_path", "unknown"))
                pb = ap.get("playbook", "Review module cohesion.")
                md_lines.append(f"| `{sev}` | {pname} | `{p}` | {pb} |")

        if recommendations:
            md_lines.extend([
                "",
                "## 4. Recommended Refactoring Actions",
                ""
            ])
            for idx, rec in enumerate(recommendations[:5], 1):
                title = rec.get("title", f"Recommendation #{idx}")
                desc = rec.get("description", "")
                md_lines.append(f"### {idx}. {title}")
                md_lines.append(f"{desc}")
                md_lines.append("")

        return "\n".join(md_lines)

    @classmethod
    def generate_standalone_html(cls, analysis_data: Any, project_name: Optional[str] = None) -> str:
        """
        Generates a standalone, zero-dependency HTML report with embedded responsive styling.
        """
        data = cls._normalize_data(analysis_data)
        raw_name = project_name or data.get("project_name") or "Codebase"
        name = html.escape(str(raw_name))

        risks = data.get("risks", []) or []
        modularity = data.get("modularity", {}) or {}
        anti_patterns = data.get("anti_patterns", []) or []

        total_modules = len(risks) if risks else int(data.get("total_modules", 0))
        health_score = float(modularity.get("health_score", data.get("health_score", 100.0)) or 100.0)
        grade = html.escape(str(modularity.get("grade", "A")))
        timestamp = html.escape(time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))

        # Build Risk Rows
        risk_rows = []
        if not risks:
            risk_rows.append("<tr><td colspan='5' style='text-align:center; padding:16px; color:#94a3b8;'>No module risk records found.</td></tr>")
        else:
            sorted_risks = sorted(risks, key=lambda r: float(r.get("impact_score", r.get("risk_score", 0.0)) or 0.0), reverse=True)
            for r in sorted_risks[:25]:
                p = html.escape(norm_path(r.get("file", r.get("file_path", "unknown"))))
                impact = float(r.get("impact_score", r.get("risk_score", 0.0)) or 0.0)
                comp = float(r.get("complexity", 1.0) or 1.0)
                coup = float(r.get("coupling_score", 0.0) or 0.0)
                badge_class = "badge-high" if impact > 10.0 else ("badge-med" if impact > 5.0 else "badge-low")
                risk_rows.append(
                    f"<tr>"
                    f"<td><code>{p}</code></td>"
                    f"<td style='font-family:monospace; font-weight:700; color:#38bdf8;'>{impact:.2f}</td>"
                    f"<td style='font-family:monospace;'>{comp:.1f}</td>"
                    f"<td style='font-family:monospace;'>{coup:.1f}</td>"
                    f"<td><span class='badge {badge_class}'>{'HIGH' if impact > 10 else ('MED' if impact > 5 else 'LOW')}</span></td>"
                    f"</tr>"
                )

        # Build Anti Pattern Rows
        ap_rows = []
        if not anti_patterns:
            ap_rows.append("<tr><td colspan='4' style='text-align:center; padding:16px; color:#10b981;'>✓ Zero structural anti-patterns detected. Codebase is clean.</td></tr>")
        else:
            for ap in anti_patterns:
                sev = html.escape(str(ap.get("severity", "LOW")))
                pname = html.escape(str(ap.get("pattern_name", ap.get("pattern_type", "Smell"))))
                p = html.escape(norm_path(ap.get("file_path", "unknown")))
                pb = html.escape(str(ap.get("playbook", "Review module structure.")))
                badge_class = "badge-high" if sev == "HIGH" else ("badge-med" if sev == "MEDIUM" else "badge-low")
                ap_rows.append(
                    f"<tr>"
                    f"<td><span class='badge {badge_class}'>{sev}</span></td>"
                    f"<td><strong>{pname}</strong><br><code>{p}</code></td>"
                    f"<td style='font-size:13px; color:#cbd5e1;'>{pb}</td>"
                    f"</tr>"
                )

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ultron Architecture Audit: {name}</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --surface-glass: rgba(30, 41, 59, 0.7);
            --border: rgba(255, 255, 255, 0.1);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --cyan: #38bdf8;
            --emerald: #10b981;
            --amber: #fbbf24;
            --rose: #f43f5e;
            --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg);
            color: var(--text-main);
            font-family: var(--font);
            line-height: 1.5;
            padding: 24px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 24px;
        }}
        h1 {{ font-size: 1.6rem; font-weight: 800; color: var(--cyan); }}
        .subtitle {{ font-size: 0.85rem; color: var(--text-muted); }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .card {{
            background: var(--surface-glass);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
        }}
        .metric-label {{ font-size: 0.8rem; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px; }}
        .metric-val {{ font-size: 1.8rem; font-weight: 800; font-family: var(--font-mono); color: var(--cyan); }}
        .section-title {{ font-size: 1.2rem; font-weight: 700; margin-bottom: 12px; color: #e2e8f0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 0.9rem; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{ background: rgba(15, 23, 42, 0.6); color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; }}
        code {{ font-family: var(--font-mono); font-size: 0.82rem; background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px; color: #e2e8f0; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; font-family: var(--font-mono); }}
        .badge-high {{ background: rgba(244, 63, 94, 0.2); color: var(--rose); border: 1px solid rgba(244, 63, 94, 0.4); }}
        .badge-med {{ background: rgba(251, 191, 36, 0.2); color: var(--amber); border: 1px solid rgba(251, 191, 36, 0.4); }}
        .badge-low {{ background: rgba(16, 185, 129, 0.2); color: var(--emerald); border: 1px solid rgba(16, 185, 129, 0.4); }}
        footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--border); font-size: 0.8rem; color: var(--text-muted); text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>🛡️ Ultron Architecture Audit</h1>
                <div class="subtitle">Repository: <strong>{name}</strong> · Generated at {timestamp}</div>
            </div>
            <div>
                <span class="badge badge-low" style="font-size: 0.9rem; padding: 6px 12px;">Grade {grade} ({health_score:.1f} / 100)</span>
            </div>
        </header>

        <div class="grid">
            <div class="card">
                <div class="metric-label">Health Score</div>
                <div class="metric-val" style="color: var(--emerald);">{health_score:.1f}</div>
            </div>
            <div class="card">
                <div class="metric-label">Total Modules</div>
                <div class="metric-val">{total_modules}</div>
            </div>
            <div class="card">
                <div class="metric-label">Mean Instability (I)</div>
                <div class="metric-val">{modularity.get('mean_instability', 0.0):.2f}</div>
            </div>
            <div class="card">
                <div class="metric-label">Distance from Main Seq (D)</div>
                <div class="metric-val">{modularity.get('mean_distance', 0.0):.2f}</div>
            </div>
        </div>

        <div class="card" style="margin-bottom: 24px;">
            <h2 class="section-title">📊 Codebase Risk Matrix (Top Impact Modules)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Module File Path</th>
                        <th>Impact Score</th>
                        <th>Complexity</th>
                        <th>Coupling</th>
                        <th>Risk Tier</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(risk_rows)}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2 class="section-title">⚠️ Architectural Anti-Patterns &amp; Drift Alerts</h2>
            <table>
                <thead>
                    <tr>
                        <th>Severity</th>
                        <th>Pattern / Target Module</th>
                        <th>Remediation Playbook</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(ap_rows)}
                </tbody>
            </table>
        </div>

        <footer>
            Generated by <strong>Ultron Software Architecture Intelligence</strong> · Standalone Zero-Dependency Audit Export
        </footer>
    </div>
</body>
</html>"""
        return html_doc
