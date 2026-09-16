# Ultron Modernization — Phase 5 Execution Plan
## Enterprise Ergonomics, Continuous Observability & Ecosystem Completion

## 1. Executive Summary & Successor Context

All 44 planned tasks across Phases 1, 2, 3, and 4 have been 100% completed, verified through deterministic gates, independently audited by UMAGS subagents, and merged into `origin/master`.

| Milestone | Tasks Completed | Baseline Verification | Key Structural Invariants Preserved |
|:---|:---:|:---:|:---|
| **Phase 1: Foundation & De-slopping** | 18 (A1–E2) | 176 regression tests passing | `server.py` < 300 lines; dead surface purged; 7 MCP tools operational. |
| **Phase 2: Independent Verification & Grounding** | 8 (P2-A1–P2-D1) | 766 tests passing (9 skips) | Single test command `scripts/verify.py`; 295-file git partition; empirical churn calibration. |
| **Phase 3: Control Plane & Production Hardening** | 10 (P3-A1–P3-E1) | 820 tests passing (9 skips) | Port flakiness fixed; 13 frontend JS modules < 400 lines; JS/TS language adapter; Fail-Closed path security. |
| **Phase 4: Modern Packaging & Active Governance** | 8 (P4-A1–P4-D1) | 894 tests passing (0 skips) | True zero dependencies; headless tray mocking; WAL mode; GitHub Action; MCP installer; Git hooks; impact simulator; clean wheel. |

Phase 5 elevates Ultron into an **enterprise-grade developer tool and continuous architectural observability platform** with polished UX, rich terminal ergonomics, watch daemon automation, standard SARIF 2.1.0 reporting, and monorepo federation.

---

## 2. Phase 5 Architecture & Sub-Phase Overview

Phase 5 is organized into four sequential, verified sub-phases comprising 8 atomic tasks (Tasks 45 through 52):

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PHASE 5 EXECUTION ROADMAP                       │
├────────────────────────────────────────────────────────────────────────┤
│ Sub-Phase P5-A: Visual Product Polish, Keyboard Ergonomics & Reporting │
│   ├─ P5-A1: UI Polish, Version 1.4.0 Sync, Hotkeys Modal & Export      │
│   └─ P5-A2: Dark Mode Contrast, Focus Rings, Breakpoints & Micro-UX    │
├────────────────────────────────────────────────────────────────────────┤
│ Sub-Phase P5-B: Advanced CLI Ergonomics & Developer Velocity           │
│   ├─ P5-B1: Rich Terminal Dashboard & ANSI Formatting (scan & gate)    │
│   └─ P5-B2: Continuous Architecture Watch Daemon (ultron watch)        │
├────────────────────────────────────────────────────────────────────────┤
│ Sub-Phase P5-C: Enterprise CI/CD & Standard Static Analysis Ecosystem  │
│   ├─ P5-C1: Native SARIF 2.1.0 Export for GitHub Code Scanning Tab     │
│   └─ P5-C2: Monorepo Workspace & Multi-Package Architecture Comparison │
├────────────────────────────────────────────────────────────────────────┤
│ Sub-Phase P5-D: Final Product Reality Audit & v1.5.0 Release Milestone│
│   ├─ P5-D1: End-to-End Product Reality Audit & Clean-Room Build        │
│   └─ P5-D2: Wheel Invariant, Release Notes & v1.5.0 Ecosystem Sign-Off │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Sub-Phase P5-A: Visual Product Polish, Keyboard Ergonomics & Executive Reporting

### Task P5-A1 — Comprehensive UI Polish, Version 1.4.0 Synchronization, Keyboard Shortcuts Modal & Architecture Report Export
- **Problem**:
  1. The Web UI footer was displaying `RKM Engine v1.3.0` while the package, CLI, and MCP server are at `v1.4.0`.
  2. Keyboard hotkeys (`1`–`4`, `/`, `Enter`, `Esc`) were operational but undiscoverable by new users without reading documentation or code.
  3. Executive architecture briefings were generated in the backend via `/api/v1/export-brief`, but the Web UI lacked a 1-click **Export Report** button, and the backend route only accepted agent formats (`claude`, `codex`, `antigravity`, `json`), rejecting `markdown` and `html`.
  4. There was no direct CLI command to export the full architecture brief to a file.
- **Solution**:
  1. Update footer text to `RKM Engine v1.4.0 • Local AST Zero-Revision Verification`.
  2. Add an accessible, responsive **Keyboard Shortcuts Modal** (`#shortcuts-modal`) triggered by pressing `?` (with input-field typing protection) and a topbar `(?)` button.
  3. Extend `AgentRoutesMixin.handle_v1_export_brief` in `agent_routes.py` to support `markdown`, `html`, and `text` formats alongside existing agent formats.
  4. Add an **"Export Report"** button in the dashboard memory bar downloading formatted Markdown/HTML briefs via native client-side Blob URLs.
  5. Implement `ultron export --repo . [--format markdown|json|html] [--output <path>]` in `ultron/interfaces/cli/commands/export.py` and register it in `ultron.py`.
  6. Author unit tests in `ultron/tests/test_export_command.py` and invariant tests in `test_frontend_invariants.py`.
- **Target Files**:
  - `docs/AGENT_EXECUTION_PLAN_PHASE5.md` [NEW]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `ultron/interfaces/api/routes/agent_routes.py` [MODIFY]
  - `ultron/interfaces/web/index.html` [MODIFY]
  - `ultron/interfaces/web/index.css` [MODIFY]
  - `ultron/interfaces/web/modules/modals.js` [MODIFY]
  - `ultron/interfaces/web/modules/dashboard.js` [MODIFY]
  - `ultron/interfaces/web/index.js` [MODIFY]
  - `ultron/interfaces/cli/commands/export.py` [NEW]
  - `ultron/interfaces/ultron.py` [MODIFY]
  - `ultron/tests/test_export_command.py` [NEW]
  - `ultron/tests/test_frontend_invariants.py` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]
- **Acceptance Criteria**:
  - Web UI footer shows `v1.4.0`.
  - Pressing `?` opens the shortcuts modal; `Esc` or click outside closes it.
  - Clicking "Export Report" downloads `ultron-architecture-report.md`.
  - CLI `ultron export` outputs formatted briefs.
  - All JS modules remain strictly $< 400$ lines; `server.py` remains 297 lines.

### Task P5-A2 — Visual Contrast, Focus Rings, Responsive Breakpoints & Accessible Micro-Interactions
- **Problem**:
  1. On smaller viewports (< 1024px), the 2-pane dashboard list/detail layout causes horizontal scroll overflow.
  2. Focus outlines are inconsistent across custom button elements, impacting keyboard accessibility (a11y).
  3. Toast notifications lack ARIA live regions, preventing screen readers from announcing scan completion.
- **Solution**:
  1. Add responsive CSS media queries stacking panes smoothly on narrow screens.
  2. Implement global `:focus-visible` styling with distinct primary accent rings.
  3. Add `aria-live="polite"` to `#toast` and `#conn-text`.
  4. Polish badge colors and contrast ratios per WCAG 2.1 AA standards.
- **Target Files**:
  - `ultron/interfaces/web/index.css` [MODIFY]
  - `ultron/interfaces/web/index.html` [MODIFY]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]

---

## 4. Sub-Phase P5-B: Advanced CLI Ergonomics & Developer Velocity

### Task P5-B1 — Rich Terminal Dashboard & ANSI Color Formatting for `ultron scan` and `ultron gate`
- **Problem**: CLI output is currently plain monochrome text, making it harder to quickly discern high-risk items and threshold violations during interactive terminal use.
- **Solution**:
  1. Implement a pure standard-library ANSI formatter (`ultron/interfaces/cli/formatting.py`) supporting colorized badges, severity pills, and box-drawing status summaries.
  2. Automatically detect interactive terminals via `sys.stdout.isatty()` and respect `NO_COLOR` / `--no-color`.
  3. Zero external dependencies (no Rich or Colorama).
- **Target Files**:
  - `ultron/interfaces/cli/formatting.py` [NEW]
  - `ultron/interfaces/cli/commands/analysis.py` [MODIFY]
  - `ultron/interfaces/cli/commands/gate.py` [MODIFY]
  - `ultron/tests/test_cli_formatting.py` [NEW]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]

### Task P5-B2 — Continuous Architecture Watch Daemon (`ultron watch --repo .`)
- **Problem**: Developers and coding agents must manually re-run `ultron scan` or `ultron impact` after making edits to see if architectural health degraded.
- **Solution**:
  1. Implement `ultron watch --repo .` using standard library polling (`os.stat` mtime checking) with debounce and delta calculation.
  2. On file modification, compute differential blast radius via `BlastRadiusTracer` and emit a 1-line health delta notice in the terminal.
- **Target Files**:
  - `ultron/interfaces/cli/commands/watch.py` [NEW]
  - `ultron/interfaces/ultron.py` [MODIFY]
  - `ultron/tests/test_watch_command.py` [NEW]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]

---

## 5. Sub-Phase P5-C: Enterprise CI/CD & Standard Static Analysis Ecosystem

### Task P5-C1 — Native SARIF 2.1.0 Static Analysis Export for GitHub Code Scanning Tab (`ultron gate --sarif`)
- **Problem**: Enterprise security and compliance teams require findings in the OASIS SARIF (Static Analysis Results Interchange Format) standard for ingestion into GitHub Advanced Security, GitLab SAST, or SonarQube.
- **Solution**:
  1. Implement `ultron/core/sarif_reporter.py` compiling rule violations, circular dependencies, and high-complexity hotspots into strict SARIF 2.1.0 JSON format.
  2. Add `--sarif <output_path>` to `ultron gate`.
  3. Integrate into `.github/actions/ultron-gate/action.yml` with an optional `sarif-output: 'true'` input.
- **Target Files**:
  - `ultron/core/sarif_reporter.py` [NEW]
  - `ultron/interfaces/cli/commands/gate.py` [MODIFY]
  - `.github/actions/ultron-gate/action.yml` [MODIFY]
  - `ultron/tests/test_sarif_export.py` [NEW]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]

### Task P5-C2 — Monorepo Workspace & Multi-Package Architecture Comparison
- **Problem**: Monorepos with multiple packages (e.g. `packages/*`, `apps/*`) currently evaluate as a single monolithic bucket, masking cross-package boundary leaks.
- **Solution**:
  1. Detect workspace packages via `pyproject.toml` workspace definitions or directory layout.
  2. Compute per-package health scores and cross-package import boundaries.
  3. Support `--workspace <pkg>` filtering in `ultron scan` and `ultron gate`.
- **Target Files**:
  - `ultron/core/monorepo.py` [NEW]
  - `ultron/core/analyzer.py` [MODIFY]
  - `ultron/tests/test_monorepo_workspaces.py` [NEW]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]

---

## 6. Sub-Phase P5-D: Final Product Reality Audit & v1.5.0 Release Milestone

### Task P5-D1 — End-to-End Product Reality Audit & Clean-Room Build
- **Goal**: Full simulated end-to-end user workflow audit (`Launch -> Connect -> Analyze -> Dashboard -> Graph -> Studio -> Auditor -> Export -> CI Gate`) across clean machine environments.
- **Target Files**:
  - `ultron/tests/test_e2e_workflow.py` [NEW]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]

### Task P5-D2 — Wheel Distribution Invariant, Release Notes & v1.5.0 Ecosystem Verification
- **Goal**: Verify wheel packaging cleanliness, bump version to `1.5.0` across all metadata sources, publish complete release notes, and finalize Phase 5 sign-off.
- **Target Files**:
  - `pyproject.toml` [MODIFY]
  - `setup.py` [MODIFY]
  - `ultron/__init__.py` [MODIFY]
  - `ultron/interfaces/mcp_server.py` [MODIFY]
  - `README.md` [MODIFY]
  - `docs/TASK_PROGRESS_TRACKER.md` [MODIFY]
  - `PROJECT_LOG.md` [MODIFY]

---

## 7. Constitutional Invariants Summary for Phase 5

1. **Zero Base Dependencies**: Base distribution runtime remains 100% pure Python standard library (`dependencies = []`, `install_requires = []`).
2. **Backend Server Line Ceiling**: `ultron/interfaces/server.py` strictly constrained to $< 300$ lines.
3. **Frontend Modularity Ceiling**: Every `.js` file under `ultron/interfaces/web/**/*.js` strictly constrained to $< 400$ lines.
4. **Single-Source Test Gate**: All verification runs through `python scripts/verify.py` with zero test skips in standard dev/CI environments.
5. **Fail-Closed Security**: Strict path sanitization and boundary containment across all file-touching endpoints.
