# 🚀 Ultron — Developer Control Plane for AI-Assisted Software Engineering

<p align="center">
  <img src="docs/images/ultron_control_plane_dashboard.svg" alt="Ultron Dashboard UI" width="100%" />
</p>

<p align="center">
  <a href="#-quick-start-under-60-seconds"><img src="https://img.shields.io/badge/install-clone--to--screen%2019.5s-10B981?style=for-the-badge&logo=rocket" alt="Quick Start" /></a>
  <a href="#-verification--testing"><img src="https://img.shields.io/badge/tests-769%20passed%20%7C%200%20failed-10B981?style=for-the-badge&logo=checkmarx" alt="Tests Passing" /></a>
  <a href="#-model-context-protocol-mcp-parity"><img src="https://img.shields.io/badge/MCP-7%20Tools%20Active-06B6D4?style=for-the-badge&logo=anthropic" alt="MCP Active" /></a>
  <a href="#-honest-limitations"><img src="https://img.shields.io/badge/dependencies-0%20external%20pip-8B5CF6?style=for-the-badge" alt="Zero Dependencies" /></a>
  <a href="#-license"><img src="https://img.shields.io/badge/license-MIT-3B82F6?style=for-the-badge" alt="MIT License" /></a>
</p>

> **"Ultron is a cognitive control plane for AI-assisted software development that lets any vibe coder use any agentic coding tool to build software far beyond what they could comfortably build alone—while preserving context, architectural understanding, verification, and control."**

Ultron tells you which files in a Python codebase are risky to change — and *why* — before you or an AI agent edit them. It combines static McCabe complexity, package coupling topology, git churn history, and test coverage into an interactive Web Dashboard, a headless CI quality gate, and a Model Context Protocol (MCP) server for developer and agent workflows.

---

## 📸 System Architecture & Cognitive Flow

<p align="center">
  <img src="docs/images/ultron_architecture_flow.svg" alt="Ultron Architecture Flow" width="100%" />
</p>

Ultron sits between the **Creator** and the **Autonomous Coding Agent**:
1. **Developer / Creator Direction**: Define project goals, intent, and architectural boundaries.
2. **Ultron Control Plane Hub**: Maps the repository into an actionable knowledge graph, evaluating health, blast radius, and defect risk.
3. **Bounded Context Envelopes**: Packages the exact 7-field context (signatures, caller blast radius, complexity limits) for Cursor, Claude, Windsurf, or Copilot.
4. **Automated Truth Gate**: Validates that agent changes preserve contracts and never degrade repository health.

📖 **Looking for a guided first session?** Read the [Getting Started & Visual Walkthrough Guide](docs/GETTING_STARTED.md).

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
> - **Cold Clean-Machine Install** (`--no-cache-dir` in a fresh virtual environment): **~11.0s** (`pip install -e .`), total clone-to-first-screen **~19.5s** (surpassing the `< 60s` program target by a $3\times$ margin).
> - **Incremental Reinstall** (cached wheels): **~1.8s**.
> - **First Screen Latency**: `< 0.05s` (server startup and initial dashboard HTTP response).

### 2. Launch the Web Dashboard
```bash
ultron-server
```
Ultron deterministically finds a free port (defaulting to 8000), starts the local HTTP server, and opens your browser directly to:
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

### 4. ⚖️ Epistemic Truth Auditor & 4-Signal Model
Ultron never guesses or hides missing data behind silent degradation. Every risk assessment exposes its explicit confidence vector:
- **AST Structural Complexity** (Weight: 0.35)
- **Dependency Coupling & Blast Radius** (Weight: 0.25)
- **Git Commit & Bug-Fix Churn** (Weight: 0.15)
- **Test Line Coverage** (Weight: 0.25)

When test coverage or git history is absent, Ultron flags that signal as `unavailable` with a visible confidence badge (`Confidence: N of 4 signals active`).

---

## 🔌 Model Context Protocol (MCP) Parity

AI coding agents (Cursor, Claude Desktop, Antigravity, Windsurf) can query Ultron directly over stdio JSON-RPC without a browser:
```bash
ultron-mcp
```

### Active Tools:
- `get_risk_profile`: Computes file risk tier, impact score, and 4-signal confidence basis.
- `get_blast_radius`: Analyzes transitive downstream dependencies and caller chains.
- `compile_mission`: Assembles the structured 7-field AI agent mission envelope.
- `audit_file`: Audits a Python file for identifier confusion, typos, and call anomalies.
- `get_context_brief`: Generates a compact markdown orientation package.
- `evaluate_repository`: Returns repository-level complexity, coupling, and health metrics.
- `explain_violation`: Explains architectural rule violations in plain English.

---

## 🛡️ Headless CI Quality Gate

Fail CI builds on architectural regression or excessive risk:
```bash
ultron gate --repo . --max-high 10 --min-health 60.0 --github-annotations
```
- **Exit Code 0**: Build passed gate criteria.
- **Exit Code 1**: Threshold breached. Emits GitHub Actions workflow annotations (`::error file=...,line=...::...`) that render directly on Pull Request diffs.

---

## ⚖️ Honest Limitations

Ultron is built on strict engineering honesty. Know what it does and does not do:

1. **Python Only**: Ultron analyzes Python source code ($\ge 3.10$) via standard AST parsing. It does not parse JavaScript, TypeScript, Go, Rust, or other polyglot codebases.
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

## 📄 License

Ultron is open-source software licensed under the MIT License.
