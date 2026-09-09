# Ultron Modernization — Phase 3 Execution Plan
## Successor to Phase 2 (independently verified below)

## 1. Independent Verification of the Phase 2 Report

Unlike the Phase 1 report, Phase 2's central claim was re-run and largely **holds up**:

| Claim | Verified? | Evidence |
|---|---|---|
| `python scripts/verify.py` → `766 ran, 0 failed, 0 errors` | ✅ Confirmed (2 independent runs) | Skipped count was 10, not 9 as reported — trivial, environment-dependent (likely an offline-network skip), not a red flag. |
| All 9 Phase 2 commit hashes + branches exist | ✅ Confirmed | `git log`/`git branch -a` |
| `server.py` still 296 lines | ✅ Confirmed | |
| New files exist: `test_self_scan_integrity.py`, `test_project_log_compliance.py`, `test_confidence_calibration.py`, `test_mcp_adversarial.py`, `test_verify_command.py`, `docs/calibration/CONFIDENCE_WEIGHT_CALIBRATION.md`, `scripts/verify.py` | ✅ Confirmed | |
| CI wired to `scripts/verify.py` | ✅ Confirmed | `.github/workflows/ci.yml:45` |
| `PROJECT_LOG.md` backfilled with `NOT_CAPTURED` honesty markers | ✅ Confirmed | |
| README cold-install numbers (~11.0s / ~19.5s / 26 of 26 tracker) | ✅ Confirmed | |
| 148/119/28 = 295 file partition claim | Not re-derived independently this pass, but structurally plausible and backed by a dedicated regression test (`test_self_scan_integrity.py`) — accepted. |

**One real finding**: the very first `scripts/verify.py` run in this session exited with
process code **1** while still printing `766 ran, 0 failed, 0 errors` — a contradiction,
since the script's own logic returns 0 whenever `failures==0 and errors==0`. The run's
log showed `[-] Could not start server. Ports are all in use.` / `Server error: Bad arg`
around a server-lifecycle test. A second, clean run immediately after returned exit 0
with an identical test count. This points to **test-order/port-reuse flakiness**
(likely a fixed-port bind — 8000/8001 — colliding with a leftover process from a prior
run on the same machine) rather than a fabricated result. It's real, but it undermines
the "unfakeable gate" goal if a flaky run can occasionally return a nonzero exit for
unrelated infra reasons, or — worse — could theoretically mask a real failure behind
port noise in the other direction. **This is Phase 3's top priority (P3-A1).**

**Verdict**: Phase 2 is a genuine, verified improvement over Phase 1. The agent did what
was asked — ran full discovery, fixed the real regressions, grounded the confidence
weights against git history, hardened MCP, and was honest about historical gaps in
`PROJECT_LOG.md` instead of fabricating retroactive data. Recommend accepting Phase 2
as done, with Phase 3 addressing the flakiness finding and closing remaining depth gaps.

---

## 2. Phase 3 Tasks

### Task P3-A1 — Eliminate Port-Bind Flakiness in the Verify Gate (blocking)
- **Problem**: A full suite run intermittently exits nonzero despite `0 failed, 0 errors`
  because at least one test binds a fixed port (8000/8001) instead of an OS-assigned
  ephemeral port, and fails to clean up/release before a subsequent run.
- **Steps**: Grep all tests for hardcoded `8000`/`8001`/similar ports; convert to
  `port=0` + read back the OS-assigned port, or add a retry/backoff + guaranteed
  `finally: server_close()` around every server-lifecycle test. Add a repeat-run
  CI matrix step (`scripts/verify.py` run twice back-to-back) to prove the flake
  is gone.
- **Acceptance**: 5 consecutive full-suite runs, all exit 0, all report identical
  ran/failed/errors counts.

### Task P3-A2 — Stabilize the Skipped-Test Count
- **Problem**: Skip count varied 9→10 between the Phase 2 report and this
  independent re-run. Skips that depend on ambient state (network availability,
  OS) make the "single source of truth" summary line non-reproducible.
- **Steps**: Enumerate all `@unittest.skip`/`skipIf` conditions; for any relying on
  live network access, make them deterministic (mock the specific socket failure
  instead of a real one) or explicitly document them as "environment-dependent,
  expected" in `docs/TASK_PROGRESS_TRACKER.md` so a future skip-count delta isn't
  mistaken for a regression.
- **Acceptance**: Documented, reproducible skip list with reasons.

### Task P3-B1 — Real End-to-End Smoke Test of the 4-Pillar UI in a Browser
- **Problem**: All prior verification has been unit/HTTP-handler level. Nobody has
  confirmed the actual rendered dashboard works in a real browser after two phases
  of backend/test churn.
- **Steps**: Add a lightweight Selenium/Playwright (or stdlib-only, if the
  "zero new dependencies" invariant must hold, a headless `http.client` DOM-string
  assertion) smoke test that loads `/`, switches all 4 pillar tabs, and asserts
  each renders non-empty content from a live server instance.
- **Acceptance**: New smoke test passes; screenshot or DOM dump attached as evidence
  in `PROJECT_LOG.md`.

### Task P3-C1 — Push Toward the Original User Vision: Reduce Perceived Complexity Further
- **Problem**: The user's original ask (before Phase 1) was explicitly to make the
  UI feel less like a "pilot cockpit." Two phases have focused entirely on backend
  correctness and verification integrity — legitimate and necessary, but the
  actual end-user simplicity goal hasn't been revisited since the initial rebuild.
- **Steps**: Get a fresh screenshot of the current dashboard, compare information
  density against the C4 "risky files above the fold" redesign goal, and identify
  if any of the Phase 1/2 backend restorations (e.g., legacy route handlers
  restored in P2-A1) leaked complexity back into the UI. Trim anything that
  doesn't serve the "what's risky to change right now" question.
- **Acceptance**: Side-by-side before/after screenshot + a short list of what was
  removed/simplified, reviewed with the user before merging.

---

## 3. Kickoff Prompt for the Executing Agent

> Phase 2 held up under independent audit — well done. One flakiness bug was found:
> `scripts/verify.py` can exit code 1 on an otherwise-clean run due to a port-bind
> collision in a server-lifecycle test. Fix that first (Task P3-A1), stabilize the
> skip count (P3-A2), then add a real browser-level smoke test of the 4-pillar UI
> (P3-B1) since no phase so far has verified the actual rendered page. Finally,
> revisit the original end-user complexity goal (P3-C1) — check whether backend
> restorations reintroduced UI clutter, and simplify if so. As always: report full
> `scripts/verify.py` output (not a subset) before and after every task.
