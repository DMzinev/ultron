# 🚀 Ultron — Developer Control Plane for AI-Assisted Software Engineering

<p align="center">
  <img src="docs/images/ultron_control_plane_dashboard.svg" alt="Ultron Dashboard UI" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/DMzinev/ultron/actions/workflows/ci.yml"><img src="https://github.com/DMzinev/ultron/actions/workflows/ci.yml/badge.svg" alt="CI Build Status" /></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white" alt="Python Versions" /></a>
  <a href="scripts/verify.py"><img src="https://img.shields.io/badge/tests-801%20passed%20%7C%200%20failed-10B981?logo=githubactions&logoColor=white" alt="Tests" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" /></a>
  <a href="#-the-4-interactive-pillars"><img src="https://img.shields.io/badge/architecture%20health-100%2F100-10B981" alt="Architecture Health" /></a>
  <a href="#-honest-limitations"><img src="https://img.shields.io/badge/core%20runtime-zero%20dependencies-8B5CF6" alt="Zero Dependencies" /></a>
</p>

> **Ultron is the architectural control plane and safety engine for AI coding agents.** It protects Python codebases from agent-induced architectural degradation, calculates exact blast radius before edits, compiles bounded pre-flight mission context for Cursor, Claude Code, Windsurf, and Copilot, and enforces zero-regression quality gates in CI.

---

## 🛑 The Core Problem: Why Do AI Coding Agents Break Codebases?

When you ask an autonomous coding agent to refactor or add a feature, it operates with **local myopia**:
1. **Blind Edits**: The agent modifies a function signature in `auth.py` without knowing that 14 callers across 3 packages depend on its exact signature.
2. **Circular Dependency Loops**: The agent imports a utility from another module to solve a quick problem, inadvertently creating an import cycle (`A -> B -> C -> A`) that freezes runtime startup.
3. **Complexity Sprawl**: The agent writes deeply nested branch logic, turning a 20-line module into an untestable 400-line god file.
4. **Context Window Waste**: Dumping an entire 50,000-line repository into an LLM prompt burns tokens, costs money, and induces hallucination.

**Ultron solves this by acting as the architectural pre-flight tower between you and your AI agent:**
- It parses the codebase AST into an in-memory knowledge graph in milliseconds.
- It calculates the **exact blast radius** and public interface contracts of every file.
- It compiles a mathematically bounded **7-field Mission Envelope** for the agent before it touches code.
- It verifies via headless CI gates that the agent's PR never degrades repository health.

---

## 📸 System Architecture & Cognitive Flow

<p align="center">
  <img src="docs/images/ultron_architecture_flow.svg" alt="Ultron Architecture Flow" width="100%" />
</p>

Ultron sits directly between the **Developer** and the **Autonomous Coding Agent**:
1. **Developer Direction**: Specify the feature intent or target file.
2. **Ultron Control Plane Hub**: Maps AST complexity, coupling, circular cycles, git churn, and coverage.
3. **Bounded Mission Envelope**: Hands the AI agent the exact caller blast radius, complexity ceilings, and forbidden changes.
4. **Automated Truth Gate**: Validates that changes preserve contracts, resolve violations, and pass CI non-regression gates.

📖 **First time using Ultron?** Follow the [Visual Onboarding & Getting Started Guide](docs/GETTING_STARTED.md).  
📚 **Looking for full architecture & specs?** Explore the [Central Resources Hub](docs/RESOURCES.md).

---

## 🚀 Quick Start (Under 60 Seconds)

### 1. Install Ultron
```bash
git clone https://github.com/DMzinev/ultron.git
cd ultron
pip install -e .
```

> [!NOTE]
> **Empirical Install Latency**:
> - **Cold Clean-Machine Install** (`--no-cache-dir` in fresh virtual environment): **~11.0s** (`pip install -e .`), reaching interactive dashboard in **~19.5s** total (surpassing the `< 60s` program target by a $3\times$ margin).
> - **Incremental Reinstall** (cached wheels): **~1.8s**.
> - **First Screen Response**: `< 0.05s` (server startup and initial dashboard HTTP response).

### 2. Launch the Web Dashboard
```bash
ultron-server
```
Ultron deterministically finds an open port (default `8000`), starts the local server, and launches your browser to:
```
http://127.0.0.1:8000/
```

---

## 🌟 The 4 Interactive Pillars

### 1. 📊 Architecture Health Dashboard
Ultron computes a calibrated composite $0-100$ repository health score derived from three bounded sub-signals:
- **Cycle Stability** (Weight: 40%): Penalizes circular import cycles.
- **Rule Compliance** (Weight: 40%): Evaluates architectural violation density per 1,000 LOC.
- **Distribution Quality** (Weight: 20%): Bounds high-risk outlier saturation.

#### Health Bands
- 🟢 **Healthy** ($85 - 100$): Clean modular architecture, low coupling, zero cycles.
- 🟡 **Watch** ($60 - 84$): Minor coupling debt or complexity hotspots requiring attention.
- 🟠 **Degraded** ($30 - 59$): Multiple architectural violations or significant coupling bottlenecks.
- 🔴 **Critical** ($0 - 29$): Circular dependency loops, god modules, or severe defect risks.

#### Calibrated Risk Bands (Hybrid Percentile Formula)
- **HIGH** (🔴): Score $\ge$ 90th percentile **AND** $\ge 10.0$ absolute floor (capped at $\le 15\%$ of files).
- **MEDIUM** (🟡): Score $\ge$ 65th percentile **AND** $\ge 5.0$ absolute floor (HIGH + MEDIUM $\le 45\%$ of files).
- **LOW** (🟢): All remaining modules.
- **Cycle Boost**: A $2.0\times$ multiplier automatically lifts circular dependency participants into the top risk tier.

### 2. 🕸️ Interactive Blast-Radius Graph
- **Real-Time Dependency Graph**: Visualizes module connections, caller hierarchies, and import paths.
- **Cycle Detection**: High-risk dependency cycles pulse visually in warning colors.
- **1-Click Remediation**: Clicking any node or violation isolates its callers, highlights blast radius, and generates a remediation brief.

### 3. 🤖 AI Agent Mission Studio (7-Field Envelope)
AI coding agents need bounded context, not raw repositories. `ultron brief` generates a mathematically grounded 7-field mission envelope:
1. **Intent**: Verbatim user task.
2. **Blast Radius**: Transitive downstream files at risk of breaking.
3. **Must-Not-Touch List**: Public signatures whose modification causes caller regressions.
4. **Complexity Ceiling**: McCabe cyclomatic complexity ceiling.
5. **Verification Command**: Exact non-regression test command.
6. **Rollback Instruction**: Step-by-step recovery commands.
7. **Token Budget Hint**: Ranked list of source files to read vs. ignore.

#### Real Terminal Example:
```bash
ultron brief ultron/core/analyzer.py --intent "optimize AST loop"
```
```text
================================================================================
           ULTRON AI MISSION ENVELOPE: ultron/core/analyzer.py
================================================================================

Target: `ultron/core/analyzer.py`
User Intent: optimize AST loop

[1. GROUND TRUTH EVIDENCE & RISK METRICS]
- Risk Level: HIGH (Impact Score: 8.5 / 10.0)
- McCabe Complexity: 18 (Ceiling: <= 8)
- Blast Radius: 7 downstream modules
- Inbound Callers (7): orchestrator.py, scoring.py, routes.py, etc.

[2. PUBLIC INTERFACE CONTRACTS (PRESERVE SIGNATURES)]
The following public interfaces are called across the codebase and must remain compatible:
```python
def analyze_file(file_path: str) -> dict: ...
def analyze_directory(dir_path: str, max_files: int = 5000) -> dict: ...
```

[3. FORBIDDEN REGRESSIONS & MUST-NOT-TOUCH]
- Do NOT alter return dictionary keys: `definitions`, `complexity`, `imports`
- Do NOT introduce circular dependencies with `orchestrator.py`

[4. ACCEPTANCE CRITERIA & VERIFICATION COMMAND]
Verify your fix by running the test suite:
```bash
python scripts/verify.py --pattern "test_analyzer*.py"
```
================================================================================
```

### 4. ⚖️ Epistemic Truth Auditor & 4-Signal Model
Ultron never guesses or hides missing data behind silent degradation. Every risk assessment exposes its explicit confidence vector:
- **AST Structural Complexity** (Weight: 0.35)
- **Dependency Coupling & Blast Radius** (Weight: 0.25)
- **Git Commit & Bug-Fix Churn** (Weight: 0.15)
- **Test Line Coverage** (Weight: 0.25)

When test coverage or git history is absent, Ultron flags that signal as `unavailable` with a visible confidence badge (`Confidence: N of 4 signals active`). Read the [Confidence Weight Calibration Report](docs/calibration/CONFIDENCE_WEIGHT_CALIBRATION.md) for empirical validation against 373 churn files.

---

## 🔌 Model Context Protocol (MCP) Integration

AI coding agents (Cursor, Claude Desktop, Antigravity, Windsurf) can query Ultron directly over stdio JSON-RPC without opening a browser:
```bash
ultron-mcp
```

### Cursor Configuration (`.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "ultron": {
      "command": "ultron-mcp"
    }
  }
}
```

### Claude Desktop Configuration (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "ultron": {
      "command": "ultron-mcp"
    }
  }
}
```

### Active MCP Tools:
- `get_risk_profile`: Computes file risk tier, impact score, and 4-signal confidence basis.
- `get_blast_radius`: Analyzes transitive downstream dependencies and caller chains.
- `compile_mission`: Assembles the structured 7-field AI agent mission envelope.
- `audit_file`: Audits a Python file for identifier confusion, typos, and call anomalies.
- `get_context_brief`: Generates a compact markdown orientation package.
- `evaluate_repository`: Returns repository-level complexity, coupling, and health metrics.
- `explain_violation`: Explains architectural rule violations in plain English.

---

## 🛡️ Headless CI Quality Gate

Prevent AI agents and developers from merging architectural debt into `master`:
```bash
ultron gate --repo . --max-high 10 --min-health 60.0 --github-annotations
```

### Real Terminal Output (Gate Breach with PR Annotations):
```text
$ ultron gate --repo . --max-high 2 --min-health 80.0 --github-annotations
[*] Analyzing repository topology...
[-] Architectural Quality Gate BREACHED:
    Found 4 HIGH risk files (threshold: max 2).
    Codebase health score: 71.4/100 (threshold: min 80.0).

::error file=ultron/core/engine.py,line=42::High risk hotspot (McCabe complexity 24, impact score 9.2). Mitigate coupling before merging.
::error file=ultron/core/cycle.py,line=1::Circular import cycle detected: engine.py -> cycle.py -> engine.py.
```
- **Exit Code 0**: Build passed gate criteria.
- **Exit Code 1**: Threshold breached. Emits GitHub Actions workflow annotations (`::error file=...,line=...::...`) that render directly on Pull Request diffs.

---

## 🧭 Repository Sources Tour

Ultron is structured cleanly into cohesive subsystems:
- **`ultron/core/`**: The static analysis core — AST traversal (`analyzer.py`), dependency topology (`graph.py`), cycle detection (`cycle_detector.py`), git churn (`git_adapter.py`), coverage ingestion (`coverage_adapter.py`), and RKM store (`rkm/store.py`).
- **`ultron/interfaces/`**: Developer interfaces — local dashboard server (`server.py`, strictly < 300 lines), unified CLI (`ultron.py`), MCP server (`mcp_server.py`), and vanilla web assets (`web/`).
- **`ultron/tests/`**: 801+ automated tests partitioned strictly across unit, integration, and security boundaries.
- **`scripts/`**: Automation entry points including canonical test runner (`verify.py`).
- **`docs/`**: Complete architecture specifications, benchmarks, and guides.

---

## 📚 Resources & Documentation Hub

Explore deep architectural documentation in our [Central Resources Hub](docs/RESOURCES.md):
- **[Visual Onboarding Guide](docs/GETTING_STARTED.md)**: First-time developer walkthrough.
- **[API Surface Census](docs/API_SURFACE.md)**: 31 active REST API routes with request/response schemas.
- **[Confidence Weight Calibration](docs/calibration/CONFIDENCE_WEIGHT_CALIBRATION.md)**: Empirical evaluation against git defect history.
- **[System Architecture Map](docs/architecture/SYSTEM_MAP.md)**: Subsystem boundaries and communication flow.
- **[Observation Data Pipeline](docs/architecture/OBSERVATION_DATA_PIPELINE.md)**: End-to-end data processing specification.
- **[Task Progress Tracker](docs/TASK_PROGRESS_TRACKER.md)**: 36-task execution ledger and verified commit hashes.
- **[Contributing Guide](CONTRIBUTING.md)**: Development environment and code review guidelines.
- **[Security Policy](SECURITY.md)**: Vulnerability disclosure and privacy architecture.

---

## ⚖️ Honest Limitations

Ultron is built on strict engineering honesty. Know what it does and does not do:

1. **Python Only**: Ultron analyzes Python source code ($\\ge 3.10$) via standard AST parsing. It does not parse JavaScript, TypeScript, Go, Rust, or other polyglot codebases.
2. **Syntactic & Topological, Not Dynamic**: Ultron evaluates syntactic McCabe complexity and static import graphs. It does **not** run code dynamically, infer runtime types, perform abstract interpretation, or execute formal symbolic verification.
3. **Git History Dependency**: The churn multiplier ($1.0\times - 2.0\times$) requires an initialized Git repository with commit history. Non-git folders gracefully fall back to $1.0\times$ (neutral churn).
4. **Coverage Ingestion Dependency**: Ultron reads existing Cobertura `coverage.xml` or SQLite `.coverage` files generated by your test runner (`pytest`, `coverage.py`). Ultron does not run test suites itself to generate coverage.

---

## 🛠️ CLI Reference

```bash
# Scan a repository and output machine-readable JSON
ultron scan --repo . --json

# Generate a 7-field AI mission brief for a target file
ultron brief ultron/core/analyzer.py --intent "optimize loop performance" --json

# Enforce architectural thresholds in CI pipelines
ultron gate --repo . --max-high 12 --min-health 65.0 --github-annotations

# Execute master test verification with greppable summary
ultron verify

# Or output clean JSON for pipeline metrics
ultron verify --json

# Initialize Repository Knowledge Model (RKM) database
ultron init --repo .

# Launch local dashboard server
ultron-server --port 8000 --host 127.0.0.1
```

---

## 🧪 Verification & Testing

Ultron provides a single source-of-truth canonical test verification runner that executes full discovery across all unit, integration, and architecture tests, fails loudly on any test failure or runtime error, and outputs a standardized, greppable summary line:

```bash
# Canonical test verification via CLI
ultron verify

# Direct script execution (standard CI entry point)
python scripts/verify.py

# Machine-readable JSON metrics for CI dashboards
python scripts/verify.py --json

# Run targeted pattern subsets
python scripts/verify.py --pattern "test_verify_*.py"
```

The canonical summary format strictly adheres to:
```text
TESTS: <ran> ran, <failed> failed, <errors> errors, <skipped> skipped
```
- **Exit Code 0**: All discovered tests passed cleanly (or skipped).
- **Exit Code 1**: Any test failed or encountered a runtime error.

---

## 🤝 Community & Contributing

We welcome contributions from developers, researchers, and AI tool builders!
- **[Contributing Guide](CONTRIBUTING.md)**: Setup, architectural guidelines, and test verification standards.
- **[Code of Conduct](CODE_OF_CONDUCT.md)**: Contributor Covenant v2.1.
- **[Security Policy](SECURITY.md)**: Vulnerability reporting and local privacy architecture.
- **[Report a Bug](https://github.com/DMzinev/ultron/issues/new?template=bug_report.md)** or **[Request a Feature](https://github.com/DMzinev/ultron/issues/new?template=feature_request.md)**.

---

## 📄 License

Ultron is open-source software licensed under the [MIT License](LICENSE).
Copyright (c) 2026 Ultron Contributors.
