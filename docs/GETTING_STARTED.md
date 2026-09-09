# 🚀 Ultron — Developer Onboarding & Visual Walkthrough Guide

Welcome to **Ultron: The Developer Control Plane for AI-Assisted Software Engineering**.

Whether you are an experienced architect or a "vibe coder" directing autonomous coding agents (Cursor, Claude Desktop, Antigravity, Windsurf, Aider), Ultron ensures you never get lost in generated code, never merge regressions, and always understand the blast radius of changes before applying them.

---

## 📸 System Overview

![Ultron Control Plane Dashboard](images/ultron_control_plane_dashboard.svg)

Ultron provides a local, private control plane sitting directly between you and your AI coding agents:
1. **Repository Health Radar**: Real-time 0–100 calibrated codebase health score.
2. **Interactive Dependency Graph**: Live blast-radius mapping with cycle detection.
3. **AI Agent Mission Studio**: Mathematical 7-field bounded context briefs.
4. **Automated Truth Gate**: Headless CI and MCP verification preventing regression.

---

## ⏱️ Quick Start: Clone to Screen in 19.5 Seconds

Ultron requires **zero external pip dependencies** and runs completely locally.

### Step 1: Clone and Install
```bash
git clone https://github.com/DMzinev/ultron.git
cd ultron
pip install -e .
```
> ⚡ **Cold Install Benchmark**: Even with `--no-cache-dir` in a clean virtualenv, installation takes **~11.0s**, reaching the first interactive screen in **19.5s** total.

### Step 2: Launch the Web Dashboard
```bash
ultron-server
```
Ultron deterministically finds an open port (default `8000`), starts the local server, and launches your browser to:
```
http://127.0.0.1:8000/
```

```text
[*] Ultron Dashboard Server running on http://127.0.0.1:8000/
[*] Scanning repository... done in 0.28s.
[*] Discovered 148 modules. Health Score: 92/100 (Optimal).
```

---

## 🏛️ The 4 Interactive Pillars

Ultron is structured around 4 distinct views, accessible via top navigation or keyboard shortcuts (`1`–`4`):

![Ultron Architecture Workflow](images/ultron_architecture_flow.svg)

### Pillar 1: 📊 Architecture Health Dashboard (`Key: 1`)
- **Composite Health Score (0–100)**: Evaluated from Cycle Stability (40%), Rule Compliance (40%), and Distribution Quality (20%).
- **Calibrated Risk Spectrum**:
  - 🟢 **LOW**: Safe, modular leaf files.
  - 🟡 **MEDIUM**: Moderately coupled modules or non-critical branching logic.
  - 🔴 **HIGH**: High-complexity god modules or dependency bottlenecks. (Strictly capped at $\le 15\%$ of files using hybrid percentiles).
- **Active Hotspots**: Clear list of files that carry architectural risk, ranked by impact score.

### Pillar 2: 🕸️ Interactive Blast-Radius Graph (`Key: 2`)
- **Visual Dependency Topology**: Force-directed or hierarchical graph of imports and callers.
- **Cycle Highlighting**: Circular dependency loops (`A -> B -> C -> A`) pulse in vivid amber/crimson.
- **Blast Radius Tracing**: Click any node to instantly isolate:
  - Upstream callers (modules that depend on this file).
  - Downstream dependencies (modules this file calls).
  - Transitive blast radius (total cascade impact).

### Pillar 3: 🤖 AI Agent Mission Studio (`Key: 3`)
When you want an AI agent (Cursor, Claude, Windsurf) to modify a file:
1. Click **"Prepare Agent Brief"** on any file or violation.
2. Ultron extracts the **Bounded 7-Field Envelope**:
   - `Intent`: What the agent is tasked to do.
   - `Blast Radius`: Modules that could break if this file is modified incorrectly.
   - `Must-Not-Touch`: Public functions and signatures callers rely on.
   - `Complexity Ceiling`: Maximum allowable McCabe complexity for new code.
   - `Verification Command`: The exact command the agent must execute to verify its patch.
3. Click **"Copy Envelope"** or push via MCP directly into Cursor/Claude!

### Pillar 4: ⚖️ Epistemic Truth Auditor (`Key: 4`)
Ultron never hallucinates confidence. Every score reveals its epistemic basis:
- **Observed**: Concrete AST syntax, function signatures, cyclomatic decision count.
- **Derived**: Import graph topology, circular cycle loops, fan-in/fan-out metrics.
- **Inferred**: Git commit churn, bug-fix defect correlation, test coverage.
- **Unknown**: Explicitly labeled missing signals (e.g. `Coverage: unavailable`), avoiding false security.

---

## 🔌 Connecting Ultron to Your AI Agents

### Option A: Automatic MCP Integration (Cursor / Claude Desktop / Windsurf)
Ultron includes an auto-installer for MCP clients:
```bash
ultron-mcp
```
Or start the MCP server directly over stdio:
```json
{
  "mcpServers": {
    "ultron": {
      "command": "ultron-mcp"
    }
  }
}
```
Available MCP Tools:
- `get_risk_profile`: Query file risk, cyclomatic complexity, and blast radius.
- `get_blast_radius`: Trace caller cascade before refactoring.
- `compile_mission`: Generate 7-field bounded prompt envelope.
- `get_context_brief`: Quick repository summary for agent system prompt.
- `evaluate_repository`: Repository health score and violation count.
- `audit_file`: Static code inspection for call anomalies.
- `explain_violation`: Plain-English architectural guidance.

### Option B: Headless Quality Gate in CI / Pre-Commit
Prevent agents or developers from introducing architectural rot:
```bash
# Add to your GitHub Actions workflow or pre-commit hook:
ultron gate --max-high 10 --min-health 65.0 --github-annotations
```
- **Exit Code 0**: Build passes.
- **Exit Code 1**: Quality threshold breached. Ultron emits inline GitHub annotations directly onto the Pull Request diff!

---

## 🎨 Visual Ergonomics & Keyboard Navigation

| Key | Action |
|:---:|:---|
| `1` | Switch to **Health Dashboard** |
| `2` | Switch to **Dependency Graph** |
| `3` | Switch to **AI Agent Studio** |
| `4` | Switch to **Truth Auditor** |
| `/` | Focus search filter bar |
| `Esc` | Dismiss active modal / drawer / search |
| `R` | Trigger instant incremental rescan |

---

## 💡 Troubleshooting & FAQ

#### Q: How does Ultron handle large repositories?
Ultron uses an incremental SQLite storage layer (`Repository Knowledge Model` or `RKM`). Parsing and scanning 1,000 files takes under **9.5 seconds**, with sub-millisecond memory footprint.

#### Q: What if my repository is not in a git repo?
Ultron gracefully degrades the git churn signal to neutral ($1.0\times$), displaying a visible `Confidence: 3 of 4 signals active` badge without breaking analysis.

#### Q: Can I run Ultron without opening a browser?
Yes! Use `ultron scan --json` or `ultron brief <file> --json` from any terminal or script.
