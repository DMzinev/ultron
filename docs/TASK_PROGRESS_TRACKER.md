# Ultron — Lifetime Activity & Task Progress Tracker

**Single Source of Truth**: `docs/AGENT_EXECUTION_PLAN.md`  
**Total Planned Tasks**: 18  
**Completed**: 1 / 18 (Task A1)  
**Current Active Task**: A2 (`agent/A2-reconcile-working-tree`)

---

## 1. Execution Sequence & Lifecycle Status

| # | Task ID | Branch | Status | Commit Hash | Verified Acceptance Evidence |
|:---|:---|:---|:---|:---|:---|
| 1 | **A1** | `agent/A1-freeze-baseline-fixtures` | **COMPLETED** | `1b5c5b4` | `python -m unittest ultron.tests.test_signal_quality` → Ran 11 tests in 0.401s, OK (expected failures=2) |
| 2 | **A2** | `agent/A2-reconcile-working-tree` | **IN PROGRESS** | - | `git status --porcelain` is clean; `UNTRACKED_INVENTORY.md` created; 0 test errors |
| 3 | **C3** | `agent/C3-prove-auditor-detects-defects` | PENDING | - | Prove the auditor actually detects defects |
| 4 | **A3** | `agent/A3-decompose-server` | PENDING | - | `server.py` decomposed behind contract tests (< 300 lines) |
| 5 | **A4** | `agent/A4-delete-dead-surface` | PENDING | - | Legacy frontend and dead endpoints removed |
| 6 | **A5** | `agent/A5-logging-discipline` | PENDING | - | "No git history" console spam eliminated |
| 7 | **B1** | `agent/B1-percentile-risk-bands` | PENDING | - | Distribution-aware risk bands (HIGH <= 15%) |
| 8 | **B2** | `agent/B2-calibrate-health-score` | PENDING | - | Health score calibrated against clean & tangled fixtures |
| 9 | **B3** | `agent/B3-git-churn-signal` | PENDING | - | Git churn signal active & bounded |
| 10 | **B4** | `agent/B4-honest-confidence` | PENDING | - | Explicit signal confidence status in API & UI |
| 11 | **C1** | `agent/C1-graph-granularity` | PENDING | - | File vs symbol granularity contract in graph |
| 12 | **C2** | `agent/C2-violation-to-fix` | PENDING | - | Actionable link from policy violation to fix |
| 13 | **C4** | `agent/C4-dashboard-hierarchy` | PENDING | - | Clean, intuitive dashboard information hierarchy |
| 14 | **D1** | `agent/D1-mission-envelope-quality` | PENDING | - | Bounded AI prompt missions with blast radius |
| 15 | **D2** | `agent/D2-contract-ci-gate` | PENDING | - | Machine-readable contract and CI gate |
| 16 | **D3** | `agent/D3-mcp-parity` | PENDING | - | Full MCP stdio tool parity |
| 17 | **E1** | `agent/E1-install-first-run` | PENDING | - | First-run setup & zero-config verification |
| 18 | **E2** | `agent/E2-docs-match-reality` | PENDING | - | Documentation strictly matches real shipped system |

---

## 2. Directory & Component State History

- `ultron/tests/fixtures/`:
  - `clean_repo/` (8 files): Standard low-complexity baseline.
  - `tangled_repo/` (8 files): 401-line god module, 3-file cycle, deep fan-in.
  - `mixed_repo/` (12 files): 2 planted risky files, 10 benign.
- `ultron/tests/test_signal_quality.py`:
  - Behavioral distribution tests for fixtures.
- `ultron/interfaces/api/routes/system_routes.py`:
  - Fixed missing `Optional` typing import.

---

## 3. Anti-Circular Guardrails

1. **One Task Per Branch**: Never mix changes across tasks.
2. **Acceptance Precedes Commit**: No commit without passing the task acceptance command.
3. **No Speculative Rewrites**: Only touch files declared under `Files` for the active task.
4. **Permanent Inventory**: Any untracked or deleted file is recorded in `docs/UNTRACKED_INVENTORY.md`.
