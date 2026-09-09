# Ultron — Code Architecture Risk & AI Mission Control

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Privacy](https://img.shields.io/badge/privacy-100%25%20Local%20%2F%20Zero%20Network-blueviolet.svg)
![RKM Engine](https://img.shields.io/badge/RKM-v1.1.0-orange.svg)
![MCP Support](https://img.shields.io/badge/MCP-7%20Tools%20Active-cyan.svg)

**Ultron** tells you which files in a Python codebase are risky to change — and *why* — before you edit them. It combines static McCabe complexity, package coupling topology, git churn history, and test coverage into a focused Web Dashboard, a headless CI quality gate, and a Model Context Protocol (MCP) server for developer and AI agent workflows.

---

## 🚀 Quick Start (Under 60 Seconds)

### 1. Install Ultron
```bash
git clone https://github.com/your-username/ultron.git
cd ultron
pip install -e .
```

### 2. Launch the Web Dashboard
```bash
ultron-server
```
Ultron deterministically finds a free port (defaulting to 8000), starts the local HTTP server, and opens your browser directly to:
```
http://127.0.0.1:8000/
```

---

## 🌟 Modern Core Capabilities

### 1. Distribution-Aware Hybrid Risk Bands
Absolute threshold rules fail on real codebases by either flagging 60% of files as HIGH or 0%. Ultron uses a calibrated **hybrid percentile formula**:
- **HIGH**: Score $\ge$ 90th percentile **AND** $\ge 10.0$ absolute floor (capped at $\le 15\%$ of files).
- **MEDIUM**: Score $\ge$ 65th percentile **AND** $\ge 5.0$ absolute floor (HIGH + MEDIUM $\le 45\%$ of files).
- **LOW**: All remaining modules.
- **Cycle Boost**: A $2.0\times$ multiplier automatically lifts circular dependency participants into the top risk tier.
- **Clean Baseline**: A codebase without complexity or coupling outliers produces **zero** HIGH risk files.

### 2. Calibrated Composite Health Score
Ultron computes a single, honest $0-100$ repository health score derived from three bounded sub-signals:
1. **Cycle Stability** (Weight: 40%): Penalizes circular import cycles.
2. **Rule Compliance** (Weight: 40%): Evaluates architectural violation density per 1,000 LOC.
3. **Distribution Quality** (Weight: 20%): Bounds high-risk outlier saturation.

#### Health Bands
- 🟢 **Healthy** ($85 - 100$): Clean modular architecture, low coupling, no cycles.
- 🟡 **Watch** ($60 - 84$): Minor coupling debt or complexity hotspots requiring attention.
- 🟠 **Degraded** ($30 - 59$): Multiple architectural violations or significant coupling bottlenecks.
- 🔴 **Critical** ($0 - 29$): Circular dependency loops, god modules, or severe defect risks.

### 3. 4-Signal Honest Confidence Model
Ultron never guesses or hides missing data behind silent degradation. Every risk assessment exposes its explicit confidence vector:
- **AST Structural Complexity** (Weight: 0.35)
- **Dependency Coupling & Blast Radius** (Weight: 0.25)
- **Git Commit & Bug-Fix Churn** (Weight: 0.15)
- **Test Line Coverage** (Weight: 0.25)

When test coverage or git history is absent, Ultron flags that signal as `unavailable` with a visible confidence badge (`Confidence: N of 4 signals active`), preserving architectural integrity.

### 4. Closed-Loop Developer Dashboard
- **Primary Answer Above the Fold**: "These N files are risky to change, here is why."
- **1-Click Remediation Loop**: Clicking any architectural violation inspects the offending file, highlights its cycle edges in the dependency graph, and drafts a targeted fix mission in Agent Studio with one click.
- **Full Keyboard Navigation**:
  - `1`–`4`: Switch between Pillars (Overview, Graph, Details, Agent Studio).
  - `/`: Focus search filter.
  - `Esc`: Dismiss drawers, modals, and search queries.

### 5. AI Agent Mission Control (7-Field Envelope)
AI coding agents need bounded context, not raw repositories. `ultron brief` generates a mathematically grounded 7-field mission envelope:
1. **Intent**: Verbatim user task.
2. **Blast Radius**: Transitive downstream files at risk of breaking.
3. **Must-Not-Touch List**: Public signatures whose modification causes caller regressions.
4. **Complexity Ceiling**: McCabe cyclomatic complexity ceiling.
5. **Verification Command**: Exact non-regression test command.
6. **Rollback Instruction**: Step-by-step recovery commands.
7. **Token Budget Hint**: Ranked list of source files to read vs. ignore.

### 6. Headless CI Quality Gate
Fails CI builds on architectural regression or excessive risk:
```bash
ultron gate --max-high 10 --min-health 60 --github-annotations
```
- **Exit Code 0**: Build passed gate criteria.
- **Exit Code 1**: Threshold breached. Emits GitHub Actions workflow annotations (`::error file=...,line=...::...`) that render directly on Pull Request diffs.

### 7. Model Context Protocol (MCP) Parity
AI coding agents (Cursor, Claude Desktop, Antigravity, Windsurf) can query Ultron directly over stdio JSON-RPC without a browser:
```bash
ultron-mcp
```
Active Tools:
- `get_risk_profile`: Computes file risk tier, impact score, and 4-signal confidence basis.
- `get_blast_radius`: Analyzes transitive downstream dependencies and caller chains.
- `compile_mission`: Assembles the structured 7-field AI agent mission envelope.
- `audit_file`: Audits a Python file for identifier confusion, typos, and call anomalies.
- `get_context_brief`: Generates a compact markdown orientation package.
- `evaluate_repository`: Returns repository-level complexity, coupling, and health metrics.
- `explain_violation`: Explains architectural rule violations in plain English.

---

## ⚖️ Honest Limitations

Ultron is built on strict engineering honesty. Know what it does and does not do:

1. **Python Only**: Ultron analyzes Python source code ($\ge 3.10$) via standard AST parsing. It does not parse JavaScript, TypeScript, Go, Rust, or other polyglot codebases.
2. **Syntactic & Topological, Not Dynamic**: Ultron evaluates syntactic McCabe complexity and static import graphs. It does **not** run code dynamically, infer runtime types, perform abstract interpretation, or execute formal symbolic verification.
3. **Git History Dependency**: The churn multiplier ($1.0\times - 2.0\times$) requires an initialized Git repository with commit history. Non-git folders gracefully fall back to $1.0\times$ (neutral churn).
4. **Coverage Ingestion Dependency**: Ultron reads existing Cobertura `coverage.xml` or SQLite `.coverage` files generated by your test runner (`pytest`, `coverage.py`). Ultron does not run test suites itself to generate coverage.

---

## 🏗️ Architecture & Component Flow

```
   ┌─────────────────────────────────────────────────────────────┐
   │                     Ultron Core Engine                      │
   │                                                             │
   │   AST Parser  ──►  Dependency Graph  ──►  Risk Scorer       │
   │       │                     │                   │           │
   │   Git Adapter       Policy Engine       Confidence Model    │
   │       │                     │                   │           │
   │       ▼                     ▼                   ▼           │
   │   [Git Churn]         [RKM SQLite DB]     [Coverage XML]    │
   └─────────────────────────────┬───────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
 ┌───────────────┐       ┌───────────────┐       ┌───────────────┐
 │ Web Dashboard │       │    CLI Gate   │       │   MCP Server  │
 │ (ultron-server│       │ (ultron gate) │       │  (ultron-mcp) │
 │  port 8000)   │       │               │       │  stdio JSON-RPC
 └───────────────┘       └───────────────┘       └───────────────┘
```

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
