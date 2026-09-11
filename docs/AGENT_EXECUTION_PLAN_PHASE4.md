# Ultron Modernization — Phase 4 Execution Plan
## Product Packaging, Modern Distribution, Active Agent Governance & Final Polish

## 1. Executive Summary & Successor Context

All 36 planned tasks across Phases 1, 2, and 3 have been 100% completed, verified through deterministic gates, independently audited by UMAGS subagents, and merged cleanly into `origin/master`.

| Milestone | Tasks Completed | Baseline Verification | Key Structural Invariants Preserved |
|:---|:---:|:---:|:---|
| **Phase 1: Foundation & De-slopping** | 18 (A1–E2) | 176 regression tests passing | `server.py` < 300 lines; dead surface purged; 7 MCP tools operational. |
| **Phase 2: Independent Verification & Grounding** | 8 (P2-A1–P2-D1) | 766 tests passing (9 skips) | Single test command `scripts/verify.py`; 295-file git partition; empirical churn calibration. |
| **Phase 3: Control Plane & Production Hardening** | 10 (P3-A1–P3-E1) | 820 tests passing (9 skips) | Port flakiness fixed; 13 frontend JS modules < 400 lines; JS/TS language adapter; Fail-Closed path security. |

Phase 4 transitions Ultron from an internal hardened engine into a **production-grade, zero-dependency, easily distributable developer tool** with active agent governance capabilities.

---

## 2. Phase 4 Architecture & Sub-Phase Overview

Phase 4 is organized into four sequential, verified sub-phases comprising 8 atomic tasks (Tasks 37 through 44):

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PHASE 4 EXECUTION ROADMAP                       │
├────────────────────────────────────────────────────────────────────────┤
│ Sub-Phase P4-A: Modern Packaging, Distribution & Zero-Dependency PyPI  │
│   ├─ P4-A1: Modern pyproject.toml, True Zero-Dependency & v1.4.0 Sync │
│   ├─ P4-A2: Zero-Skip CI Environment & Headless Tray Mocking           │
│   └─ P4-A3: SQLite WAL Mode & High-Concurrency Locking                 │
├────────────────────────────────────────────────────────────────────────┤
│ Sub-Phase P4-B: Developer Integrations & Automated CI Actions          │
│   ├─ P4-B1: Official Standalone GitHub Action (DMzinev/ultron-action)  │
│   └─ P4-B2: Automated Multi-Client MCP Installer (ultron mcp install)  │
├────────────────────────────────────────────────────────────────────────┤
│ Sub-Phase P4-C: Active Agent Governance (The Supervisor Moat)          │
│   ├─ P4-C1: Native Git Pre-Commit & Pre-Push Hook (ultron hook install)│
│   └─ P4-C2: Differential Impact Simulator (ultron impact <file>)       │
├────────────────────────────────────────────────────────────────────────┤
│ Sub-Phase P4-D: Final Product Polish, Reality Verification & Release   │
│   └─ P4-D1: Clean-Room Build, Wheel Invariant & Reality Sign-Off       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Sub-Phase P4-A: Modern Packaging, Distribution & True Zero-Dependency PyPI Release

### Task P4-A1 — Modern `pyproject.toml`, True Zero-Dependency Decoupling & Version 1.4.0 Synchronization
- **Problem**:
  1. `setup.py` and `pyproject.toml` declared `radon` under mandatory runtime requirements (`install_requires` / `dependencies`), violating the pure standard library promise despite `ultron/core/risk/metrics.py` possessing a complete standard-library `ast` fallback.
  2. Packaging metadata was frozen at `version = "1.1.0"`, while the live MCP server (`mcp_server.py:418`) reports `1.4.0`, and `ultron/__init__.py` lacked `__version__`.
- **Solution**:
  1. Decouple `radon` into optional extras (`ultron[metrics]`, `ultron[dev]`). Set base `dependencies = []` and `install_requires = []`.
  2. Declare PEP 621 optional extras in `pyproject.toml` and `setup.py`: `tray` (`pystray`, `Pillow`), `metrics` (`radon`), and `dev`.
  3. Harmonize version `1.4.0` across `pyproject.toml`, `setup.py`, and `ultron/__init__.py`.
  4. Author automated packaging parity tests in `ultron/tests/test_distribution_packaging.py`.
- **Target Files**:
  - `docs/AGENT_EXECUTION_PLAN_PHASE4.md` [NEW]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `pyproject.toml` [MODIFY]
  - `setup.py` [MODIFY]
  - `ultron/__init__.py` [MODIFY]
  - `ultron/tests/test_distribution_packaging.py` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]
- **Acceptance Criteria**:
  - `pip install -e .` requires 0 external pip packages.
  - `python -c "import ultron; print(ultron.__version__)"` outputs `1.4.0`.
  - Packaging tests pass across supported Python versions (3.8+).

### Task P4-A2 — Zero-Skip CI Environment & Headless Tray Mocking
- **Problem**:
  - 9 tests in `ultron/tests/test_launchers.py` (`TestTrayLauncher`) are skipped whenever optional tray dependencies (`pystray`, `Pillow`) are missing. Headless CI environments currently output `820+ ran, 9 skipped`.
- **Solution**:
  - Implement a headless tray mock backend when `HAS_TRAY_DEPS` is false or `CI=true` / `ULTRON_HEADLESS=1` is set.
  - Allow headless environments to fully exercise tray event handlers, state transitions, and menu callbacks.
  - Target: Transition test suite to **`823+ ran, 0 skipped`** in standard CI runs.
- **Target Files**:
  - `ultron/interfaces/launcher.py` [MODIFY]
  - `ultron/tests/test_launchers.py` [MODIFY]
  - `ultron/tests/test_skip_invariants.py` [MODIFY]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]

### Task P4-A3 — SQLite WAL Mode & High-Concurrency Locking
- **Problem**:
  - Under heavy parallel execution or concurrent agent reads/writes, SQLite occasionally encounters database lock contention (`[*] Analysis note: DB locked`).
- **Solution**:
  - Enable Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) and `PRAGMA synchronous=NORMAL;` in `ultron/core/rkm/store.py`.
  - Configure busy timeouts (`PRAGMA busy_timeout=5000;`) for resilient lock acquisition.
  - Add concurrency stress tests proving zero `DB locked` errors under multi-threaded read/write workloads.
- **Target Files**:
  - `ultron/core/rkm/store.py` [MODIFY]
  - `ultron/tests/test_rkm_concurrency.py` [NEW]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]

---

## 4. Sub-Phase P4-B: Developer Integrations & Automated CI Actions

### Task P4-B1 — Official Standalone GitHub Action (`DMzinev/ultron-action@v1`)
- **Problem**:
  - CI integration currently requires users to manually copy multi-line workflow steps from `docs/GETTING_STARTED.md`.
- **Solution**:
  - Author official composite action `.github/actions/ultron-gate/action.yml` supporting 1-line CI integration:
    ```yaml
    - uses: DMzinev/ultron-action@v1
      with:
        repo-path: '.'
        max-high: '0'
        min-health: '80.0'
    ```
  - Validates exit codes (0/1) and emits native GitHub Actions PR annotations (`::error file=...::`).
- **Target Files**:
  - `.github/actions/ultron-gate/action.yml` [NEW]
  - `.github/workflows/test-action.yml` [NEW]
  - `docs/GETTING_STARTED.md` [MODIFY]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]

### Task P4-B2 — Automated Multi-Client MCP Installer (`ultron mcp install`)
- **Problem**:
  - Setting up Ultron in AI editor clients (Cursor, Claude Desktop, Windsurf) requires manual JSON file editing.
- **Solution**:
  - Implement `ultron mcp install --client [cursor|claude|windsurf|all]` CLI command.
  - Automatically discovers configuration paths across Windows, macOS, and Linux.
  - Safely reads, merges, and writes config files idempotently without overwriting existing client tools.
- **Target Files**:
  - `ultron/interfaces/cli/commands/mcp.py` [MODIFY]
  - `ultron/interfaces/ultron.py` [MODIFY]
  - `ultron/tests/test_mcp_installer.py` [NEW]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]

---

## 5. Sub-Phase P4-C: Active Agent Governance (The Supervisor Moat)

### Task P4-C1 — Native Git Pre-Commit & Pre-Push Quality Gate Hook (`ultron hook install`)
- **Problem**:
  - AI coding agents can commit architecture-degrading changes locally before CI runs.
- **Solution**:
  - Implement `ultron hook install` CLI subcommand to install standard `.git/hooks/pre-commit` and `pre-push` scripts.
  - Automatically executes `ultron gate` against staged or outgoing commits, preventing high-risk commits before they reach the remote repository.
- **Target Files**:
  - `ultron/interfaces/cli/commands/hook.py` [NEW]
  - `ultron/interfaces/ultron.py` [MODIFY]
  - `ultron/tests/test_git_hooks.py` [NEW]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]

### Task P4-C2 — Differential Impact Simulator (`ultron impact <file>`)
- **Problem**:
  - When an AI agent edits a file, running the full test suite can take minutes. Agents need to know the immediate topological blast radius and exactly which subset of tests must be executed.
- **Solution**:
  - Implement `ultron impact <file>` CLI command.
  - Traverses the dependency DAG to compute transitive blast radius and automatically maps affected production files to their corresponding test files.
  - Emits JSON envelope with `affected_files`, `affected_tests`, and recommended test runner command.
- **Target Files**:
  - `ultron/interfaces/cli/commands/impact.py` [NEW]
  - `ultron/interfaces/ultron.py` [MODIFY]
  - `ultron/tests/test_impact_simulator.py` [NEW]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]

---

## 6. Sub-Phase P4-D: Final Product Polish, Reality Verification & v1.4.0 Release

### Task P4-D1 — Clean-Room Build, Wheel Distribution Invariant & Documentation Reality Sign-Off
- **Problem**:
  - Prior to tagging `v1.4.0`, all package distribution wheels, documentation cross-references, CLI commands, and test suites must be validated in an isolated clean-room environment.
- **Solution**:
  - Run clean-room wheel build (`python -m build --wheel`).
  - Verify wheel installation in a pristine temporary environment.
  - Execute full test suite `scripts/verify.py` and invariant suites.
  - Synchronize documentation counters and release notes.
- **Target Files**:
  - `README.md` [MODIFY]
  - `docs/GETTING_STARTED.md` [MODIFY]
  - `docs/RESOURCES.md` [MODIFY]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]

---

## 7. Constitutional Invariants & Quality Gates

Throughout all Phase 4 tasks, the following invariants are non-negotiable:
1. **Ponytail Simplicity Ladder**: Standard library first. Zero unrequested dependencies. Base installation requires 0 external pip packages.
2. **Backend Server Ceiling**: `ultron/interfaces/server.py` strictly < 300 lines (currently 297 lines).
3. **Frontend Modularity Ceiling**: Every file in `ultron/interfaces/web/**/*.js` strictly < 400 lines (currently 13 modules).
4. **Deterministic Single-Source Gate**: Every task must pass `python scripts/verify.py` with 0 failures and 0 errors.
5. **No Blind Auto-Approvals**: Adhere to UMAGS anti-prompt injection and human-in-the-loop verification policies.
