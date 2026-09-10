# 📚 Ultron — Sources, Architecture & Resources Directory

Welcome to the central documentation and engineering resources hub for **Ultron: The Developer Control Plane for AI-Assisted Software Engineering**.

This document provides a comprehensive tour of the codebase, its architectural components, technical specifications, and developer guides.

---

## 🧭 Repository Sources Tour

Ultron is architected with a strict separation of concerns, zero external pip dependencies for its core runtime, and pure standard library execution.

```text
ultron/
├── core/                        # Core static analysis & repository modeling engine
│   ├── analyzer.py              # AST traversal, McCabe complexity, and definition extraction
│   ├── graph.py                 # Dependency graph modeling and topological sorting
│   ├── cycle_detector.py        # Tarjan's strongly connected components (SCC) cycle detection
│   ├── language_adapter.py      # Multi-language adapter interface and PythonLanguageAdapter
│   ├── git_adapter.py           # Git history extraction, churn metrics, and co-change analysis
│   ├── coverage_adapter.py      # Cobertura XML and SQLite .coverage ingestion
│   ├── pipeline/                # Repository scanning orchestrator and file discovery
│   │   ├── discovery.py         # Ignored path filtering, symlink safety, and file discovery
│   │   └── orchestrator.py      # Pipeline coordination and cryptographic content hashing
│   ├── risk/                    # Risk classification and scoring engine
│   │   ├── scoring.py           # 4-signal confidence model (AST, Coupling, Churn, Coverage)
│   │   ├── rules.py             # Architectural rule engine and threshold evaluation
│   │   └── prompts.py           # 7-field AI agent mission envelope compiler
│   └── rkm/                     # Repository Knowledge Model (RKM) persistence
│       ├── schema.py            # SQLite schema and data structures
│       ├── store.py             # WAL-mode transactional store and event logging
│       └── bug_prediction.py    # Empirical defect correlation and heuristic validation
│
├── interfaces/                  # Developer & agent interaction surfaces
│   ├── server.py                # Local HTTP dashboard server (strictly < 300 lines)
│   ├── ultron.py                # Unified CLI entry point (`scan`, `brief`, `gate`, `verify`)
│   ├── mcp_server.py            # Model Context Protocol (MCP) JSON-RPC 2.0 server
│   ├── api/                     # Modular HTTP route handlers
│   │   ├── router.py            # Header-aware HTTP router with exact path matching
│   │   ├── routes/              # Modular endpoint implementations
│   │   │   ├── analysis_routes.py   # Repository scanning & synchronous analysis
│   │   │   ├── graph_routes.py      # Topology graph & cycle inspection
│   │   │   ├── system_routes.py     # Health checks, folder browsing, and state
│   │   │   └── mission_routes.py    # AI mission compilation and handoff
│   │   └── middleware/          # Security, error handling, and payload validation
│   ├── cli/                     # CLI subcommand implementations
│   │   └── commands/            # Handlers for `scan`, `brief`, `gate`, `verify`, `init`
│   └── web/                     # Interactive control plane frontend (Zero external JS/CSS frameworks)
│       ├── index.html           # 4-pillar UI layout (Dashboard, Graph, Studio, Auditor)
│       ├── index.css            # Dark-theme responsive ergonomics and typography
│       └── index.js             # Client-side state, D3-compatible SVG rendering, and API bridge
│
├── tests/                       # 769+ automated tests partitioned across boundaries
│   ├── fixtures/                # Standard test repositories (clean_repo, tangled_repo, mixed_repo)
│   ├── test_self_scan_integrity.py  # Partition invariant: zero test/fixture leakage in production
│   ├── test_documentation_reality.py # Enforces 100% sync between docs and real code
│   ├── test_skip_invariants.py  # AST static analysis enforcing authorized skip inventory
│   ├── test_mcp_adversarial.py  # Defensive exception shielding and stdio stream stress tests
│   ├── test_monorepo_scale.py   # 10,000-file discovery, sub-second sync, and heap ceiling benchmarks
│   └── test_ui_smoke_live.py    # Live HTTP server lifecycle, DOM verification, and ES module syntax
│
├── scripts/                     # Developer and CI automation entry points
│   └── verify.py                # Single source-of-truth verification runner
│
└── docs/                        # Architecture specs, calibration documents, and onboarding guides
```

---

## 📖 Complete Documentation Index

### 1. Product Vision & Guides
- **[README.md](../README.md)**: Main project overview, quickstart, capabilities, and badges.
- **[GETTING_STARTED.md](GETTING_STARTED.md)**: Step-by-step visual onboarding guide for first-time developers and AI coding practitioners.
- **[CONTRIBUTING.md](../CONTRIBUTING.md)**: Developer setup, coding standards, verification protocol, and PR checklist.
- **[CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)**: Contributor Covenant v2.1 community standard.
- **[SECURITY.md](../SECURITY.md)**: Vulnerability disclosure policy, local loopback architecture, and zero-telemetry guarantee.

### 2. Architecture & Design Principles
- **[System Responsibility Map](architecture/SYSTEM_MAP.md)**: Subsystem boundaries, component responsibilities, and communication paths.
- **[Observation Data Pipeline](architecture/OBSERVATION_DATA_PIPELINE.md)**: End-to-end data transformation pipeline from filesystem observation to UI rendering.
- **[UMAGS Cognitive Governance](architecture/UMAGS.md)**: The multi-agent constitutional framework governing verified development in this repository.

### 3. Calibration, Benchmarks & Metrics
- **[Confidence Weight Calibration](calibration/CONFIDENCE_WEIGHT_CALIBRATION.md)**: Empirical evaluation of the 4-signal confidence model across 373 churn files in git history, case studies, and scientific disclaimers.
- **[OSS Benchmark Validation Report](benchmarks/OSS_BENCHMARK_REPORT.md)**: Monorepo scale benchmarks, memory ceiling audits (<50MB for 10k files), and sub-second incremental sync metrics.

### 4. API & Protocol Specifications
- **[API Surface Census](API_SURFACE.md)**: Authoritative census of all 31 active REST API endpoints, supported HTTP methods, parameter contracts, and response schemas.
- **Model Context Protocol (MCP)**: JSON-RPC 2.0 stdio server specification exposing 7 canonical tools (`get_risk_profile`, `get_blast_radius`, `compile_mission`, `audit_file`, `get_context_brief`, `evaluate_repository`, `explain_violation`).

### 5. Tracking & Forensic Verification
- **[Task Progress Tracker](TASK_PROGRESS_TRACKER.md)**: Lifetime execution sequence of all 36 planned tasks across Phase 1, Phase 2, and Phase 3, commit hashes, and acceptance evidence.
- **[Project Log](../PROJECT_LOG.md)**: Forensic verification ledger with standard before/after test suite counts and Category B empirical checklists.
- **[Untracked Inventory](UNTRACKED_INVENTORY.md)**: Audit record of temporary scratch scripts and artifacts.

---

## 🛠️ The 4 Core Product Capabilities

| Pillar | Developer Problem | Ultron Solution | Primary Interface |
| :--- | :--- | :--- | :--- |
| **1. Architecture Health** | Developers merge PRs that introduce circular imports, bloated god-modules, or fragile coupling bottlenecks. | Calculates a calibrated composite $0-100$ repository health score derived from Cycle Stability (40%), Rule Compliance (40%), and Distribution Quality (20%). | Web Dashboard (`/`) & CLI (`ultron scan`) |
| **2. Blast-Radius Topology** | AI agents edit a function signature without knowing that 14 callers across 3 packages depend on it. | Force-directed and hierarchical dependency graph isolating upstream callers, downstream imports, and circular cycle loops. | Web Dashboard (`Tab 2`) & MCP (`get_blast_radius`) |
| **3. AI Mission Studio** | AI coding agents hallucinate solutions or over-edit code when given raw, unconstrained repository context. | Compiles a mathematically bounded 7-field mission envelope containing exact signatures, caller constraints, and complexity ceilings. | Web Dashboard (`Tab 3`) & CLI (`ultron brief`) |
| **4. Headless CI Quality Gate** | Architectural debt silently accumulates in pull requests without failing standard unit test suites. | Non-zero exit code gate enforcing maximum high-risk files and minimum health score with native GitHub Actions PR annotations. | CLI (`ultron gate`) & CI Workflows |

---

## 🔌 Agentic Integration Protocols

### Cursor MCP Configuration
Add Ultron to your project's `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "ultron": {
      "command": "ultron-mcp"
    }
  }
}
```

### Claude Desktop Configuration
Add Ultron to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "ultron": {
      "command": "ultron-mcp"
    }
  }
}
```

---

## ⚡ Technical Invariants & Governance

1. **Zero External Dependencies**: Core runtime is 100% pure standard library Python ($\ge 3.10$).
2. **Backend Server Discipline**: `ultron/interfaces/server.py` is constrained to strictly `< 300` lines to prevent god-file regrowth.
3. **Single Source-of-Truth Test Gate**: All verification executes through `python scripts/verify.py`, running 769+ tests with greppable output and clean JSON serialization.
4. **Hermetic Local Loopback**: All network communication is bound strictly to `127.0.0.1`. Zero external telemetry, tracking, or telemetry reporting.
