# Ultron — Cognitive Software Architecture & Pre-Execution Intelligence Platform

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Security](https://img.shields.io/badge/privacy-100%25%20Local%20%2F%20Zero%20Network-blueviolet.svg)
![RKM Engine](https://img.shields.io/badge/RKM-v1.3.0-orange.svg)
![MCP Support](https://img.shields.io/badge/MCP-Stdio%20Middleware-cyan.svg)

**Ultron** tells you which files and modules in a Python codebase are risky to change — and *why* — before you edit them. It combines static McCabe complexity, coupling topology, Repository Knowledge Model (RKM) memory, and plain-language summaries into a futuristic Web SPA and Model Context Protocol (MCP) server for developer and AI agent workflows.

---

## 🌟 Core Guarantees & Features

*   **Zero Network Calls / 100% Local Privacy:** Ultron runs completely on your local machine. No source code or metadata leaves your system.
*   **Explainable & Traceable:** Every warning and refactoring opportunity follows a deterministic trail from AST measurements to software design principles (ADP, SDP, DIP, SRP). Zero speculative AI hallucinations.
*   **One-screen dashboard (`http://127.0.0.1:8000/`)** — scan a repository, read the ranked list of files that are risky to change, and copy a briefing for your coding agent. Every panel is backed by live data.
    *   **Change with care**: files ranked by impact score, each with the reason it scored that way (McCabe complexity, coupling, number of dependents).
    *   **Why / Code / Agent brief**: for any file, see its metrics and guidance, read the source, or generate a handoff payload.
    *   **Save this scan**: persists the run to the Repository Knowledge Model so repeat offenders and rule suggestions accumulate over time.
*   **AI Context Briefs & MCP Integration**:
    *   One-click AI Context Brief generator for Claude, ChatGPT/Codex, and Gemini/Antigravity orientation payloads.
    *   Native stdio JSON-RPC MCP server (`get_context_brief`, `evaluate_repository`, `explain_violation`).
*   **Closed-Loop Self-Optimization**:
    *   Ultron analyzes its own codebase (`./ultron`), identifies complexity hotspots, guides refactoring, and empirically measures health score improvements.


---

## 🚀 Quick Start

### Installation

Clone the repository and install standard requirements:
```bash
git clone https://github.com/your-username/ultron.git
cd ultron
pip install -r requirements.txt
```

### Launching the Web Portal SPA

Start the single-command launcher (scans repository, boots server on port 8000, and opens default browser):
```bash
python start.py
```
> **Windows Batch Alternative**: Double-click `start.bat` or run `start.bat` in Command Prompt.

---

## 🛠️ Command-Line & MCP Workflows

### 1. Analyze Specific Files
```bash
python ultron/interfaces/ultron.py --repo . --files ultron/core/analyzer.py --intent "refactor analyzer loop" --detail
```

### 2. Generate Codebase Context Brief for AI Coding Agents
```bash
python ultron/interfaces/ultron.py --repo . --brief
```

### 3. Run the Design Oracle (Coupling Debt & Refactoring Contracts)
```bash
python ultron/interfaces/ultron.py --repo . --oracle
```

### 4. Start the MCP Server Middleware
```bash
python -m ultron.interfaces.mcp_server
```

---

## 🧪 Testing & Verification

Run the master unit and integration test suite:
```bash
python -m unittest discover ultron/tests "test_*.py" -v
```

Verify frontend JavaScript syntax:
```bash
node -c ultron/interfaces/web/index.js
```

Run the UMAGS Governance Verification Loop:
```bash
python umags/run_verification_loop.py
```

---

## 📁 Repository Map

```
ultron/
├── core/                   # AST analyzer, complexity, coupling, RKM SQLite memory & policy engine
├── interfaces/
│   ├── web/                # Single-screen dashboard (index.*) + previous UI (legacy.*)
│   ├── server.py           # HTTP REST server router & API handlers
│   ├── ultron.py           # CLI entry point
│   ├── mcp_server.py       # Model Context Protocol stdio middleware
│   └── api/                # Modular API endpoints
├── release/                # Automated release audit & invariant policy evaluator
├── tests/                  # Master test suite (89 unit/integration/chaos tests)
├── start.py                # Zero-config single-file entry launcher
├── requirements.txt        # Root Python dependencies
└── pyproject.toml          # Package build configuration
```

---

## 📜 License

Licensed under the [MIT License](LICENSE).
