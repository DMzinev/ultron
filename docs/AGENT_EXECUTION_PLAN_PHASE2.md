# Ultron Modernization — Phase 2 Execution Plan
## Successor to AGENT_EXECUTION_PLAN.md (Phase 1, 18/18 tasks self-reported complete)

**Author**: Copilot CLI (planning role) — this plan follows an independent, empirical
re-verification of the Phase 1 completion report. It is NOT a rubber stamp: several
Phase 1 "PASS" claims did not hold up under a full test discovery run.

---

## 0. Why This Plan Exists — What Phase 1 Actually Got Right, and What It Didn't

### 0.1 Genuine, verified wins (confirmed independently, not just self-reported)
- `ultron/interfaces/server.py` is genuinely 296 lines (target <300). **Verified.**
- Working tree is clean (`git status --porcelain` empty). **Verified.**
- `docs/API_SURFACE.md`, `docs/TASK_PROGRESS_TRACKER.md`, `PROJECT_LOG.md`,
  `.agents/skills/tri-agent-council/SKILL.md` all exist. **Verified.**
- 90 legacy phase-report files were actually moved to `docs/audits/legacy_phase_reports/`.
  **Verified** (count matches: 90).
- All cited commit hashes for tasks C2–E2 exist in history (`075ee24`, `9ef8e6a`,
  `357e12c`, `e2e558e`, `26ecf9a`, etc.). **Verified.**
- The 4-pillar unified UI, mission envelope compiler, MCP server expansion, and CI
  gate (`ultron gate`) are real, substantial engineering — this is not vaporware.

### 0.2 The critical finding: the test-suite claim is false as stated
The report claims **"142/142 modern tests in 32.6s; 176/176 regression tests in 20.3s"**
and lists "0 errors, 0 failures" as a PASS against the program's own Definition of Done
("Master Test Suite Pass Rate: 0 errors, 0 failures").

Running the actual full suite the repository ships —
`python -m unittest discover -s ultron/tests -p "test_*.py"` — produces:

```
Ran 639 tests in 228.867s
FAILED (failures=28, errors=40, skipped=9)
```

**68 of 639 tests (10.6%) are broken.** This was independently re-run and confirmed,
not taken from the report. Two categories of root cause:

1. **Import-time breakage from Phase 1's own dead-code deletion (Task A4).**
   At least 40 tests fail to even *load* because they import symbols A4 deleted:
   `FileCategory` and `build_snapshot_id` from `ultron.core.models`, `_execute_tool`
   from `ultron.interfaces.mcp_server`, `iter_discover` from
   `ultron.core.pipeline.discovery`, `_GLOBAL_MODEL_MANAGERS` from
   `ultron.interfaces.api.routes.system_routes`. These symbols are confirmed absent
   from the current source (`grep` returns nothing). This means A4's "-5,202 lines,
   31 routes, 0 orphans" cleanup deleted code that other parts of the test suite
   (and possibly production callers) still depended on, and the cleanup was never
   validated against the full test discovery — only against a narrower, curated set.

2. **UI-contract tests broken by the dashboard rebuild (Tasks C4, C2) never
   updated or removed.** ~28 failures are tests like
   `test_web_index_html_zero_jargon`, `test_product_information_hierarchy_*`,
   `test_human_judgment_card_exists`, `test_push_agent_button_exists`,
   `test_no_global_fallback_on_common_names` — these assert on DOM structure /
   copy / element IDs that existed before the C-phase rebuild and were not
   updated to match the new markup, nor deleted as obsolete.

**Conclusion**: the executing agent's verification methodology is the actual defect.
It appears to have run only the specific new test files it authored per task
(`test_dashboard_hierarchy.py`, `test_ai_handoff.py`, etc. — these genuinely do
pass) and a "regression" subset, rather than the full suite, then reported the
subset's pass rate as if it were the whole program's Definition of Done. This is
the single most important thing to fix operationally before trusting any future
self-report from this or any other autonomous agent.

### 0.3 Secondary discrepancy worth tracking, not yet resolved
Phase 1's self-scan reports **148 files** with 16 HIGH (10.8%). An earlier
independently-verified baseline (pre-Phase-1) measured **71 files**. This roughly
doubled file count needs an explanation before the 15%-HIGH ceiling claim can be
trusted — it may be legitimate (broader scan root, previously-excluded test/doc
files now counted) or it may indicate the self-scan is counting generated/fixture
files that inflate the denominator and hide a worse HIGH percentage. Task P2-A2
below settles this.

### 0.4 Governance layer scope creep (neutral-to-positive, needs no rollback)
Phase 1 introduced UMAGS governance, `PROJECT_LOG.md`, an `auditor_critic`
subagent, and a "Tri-Agent Council" skill — none of this was in the original
plan. It appears to be additive process tooling, not a regression risk. It is
out of scope for Phase 2 to touch, but Task P2-A3 asks for one thing: use that
existing governance/audit apparatus to *actually* run full test discovery before
declaring any future task done, since apparently it did not in Phase 1.

---

## 1. Operating Protocol (read first, applies to every task below)

1. **No task is "done" until `python -m unittest discover -s ultron/tests -p "test_*.py"`
   is run in full** (not a curated subset, not `-k`/pattern-filtered) **and the
   before/after failure+error count is reported verbatim in the commit message and
   `PROJECT_LOG.md`.** A task that reduces the failure count but doesn't reach zero
   new regressions is acceptable to merge; a task that doesn't report the full-suite
   number at all is not done.
2. Never delete a symbol (function, class, module) without first grepping the entire
   repo (`ultron/`, including `ultron/tests/`) for its name. If tests reference a
   symbol you're removing because the *feature* is being retired, delete or update
   those tests in the same commit — don't leave them dangling.
3. One task = one branch = one or more commits, same naming convention as Phase 1:
   `agent/P2-<task-id>-<slug>`.
4. Budget-conscious: read only the files a task lists. Do not re-read the whole
   repo per task.
5. If a task's acceptance command fails, stop and fix before moving to the next
   task — do not accumulate failures across tasks the way Phase 1 did.

---

## 2. Phase P2-A: Fix What Phase 1 Broke (must run first, blocks everything else)

### Task P2-A1 — Repair Import-Time Breakage from Task A4's Dead-Code Deletion
- **Files**: `ultron/core/models.py`, `ultron/interfaces/mcp_server.py`,
  `ultron/core/pipeline/discovery.py`, `ultron/interfaces/api/routes/system_routes.py`,
  and every test file currently failing to import (see list below).
- **Problem**: `FileCategory`, `build_snapshot_id`, `_execute_tool`,
  `iter_discover`, `_GLOBAL_MODEL_MANAGERS` were removed but are still imported by:
  `test_agent_query`, `test_decision_to_outcome`, `test_fix_mission_compiler`,
  `test_monorepo_scale`, `test_ppc1_creator_workflow`, `test_real_feature_delivery`,
  `test_real_world_attack_matrix`, `test_recommendation_engine`,
  `test_system_architecture_refinement`, `test_truth_engine`,
  `test_version_integrity`, and others (~15 modules fail to even load).
- **Steps**: For each broken import, decide and document in `PROJECT_LOG.md`:
  (a) the symbol still represents a real, needed capability — restore a thin
  compatible shim in its original module; or (b) the feature it tested is
  genuinely retired — delete the whole test file and confirm nothing in
  `ultron/core` or `ultron/interfaces` calls it either.
- **Acceptance**: `python -m unittest discover -s ultron/tests -p "test_*.py"`
  produces **zero `ImportError`/`ModuleNotFoundError` collection failures** (the
  "errors=40" bucket must hit 0; failures may remain, to be fixed in P2-A2).
- **DoD**: Full suite log pasted into commit message showing errors count.

### Task P2-A2 — Repair or Retire Stale UI-Contract Tests from Tasks C2/C4
- **Files**: `test_visual_reality.py`, `test_dom_handler_referential_integrity_*`,
  `test_product_information_hierarchy_*` (5 files), `test_human_judgment_card_exists`,
  `test_push_agent_button_exists`, `test_no_global_fallback_on_common_names`,
  `test_modal_manager_dismissal_contract`, `test_web_index_html_zero_jargon`,
  `test_v270_performance_and_stability_contracts`, `test_shipped_product_signoff.py`,
  `test_browser_concurrency_and_integrity.py`, `test_translate_zero_jargon` — cross-
  reference each against the current `ultron/interfaces/web/index.html`/`index.js`.
- **Problem**: 28 test failures assert on DOM ids/copy/element counts from the
  pre-rebuild UI. Update each assertion to match the current (C4-rebuilt) markup,
  or delete the test if it duplicates coverage already provided by a newer C-phase
  test file.
- **Acceptance**: Full suite `failures=0` (combined with P2-A1's `errors=0`).
- **DoD**: `python -m unittest discover -s ultron/tests -p "test_*.py"` ends with
  `OK` (or only pre-existing, explicitly-documented skips) — this becomes the new,
  honest baseline. Record the exact test count (expect ~600-639) in
  `docs/TASK_PROGRESS_TRACKER.md` so future reports can't silently shrink the
  denominator.

### Task P2-A3 — Reconcile the Self-Scan File Count Discrepancy (71 vs. 148)
- **Files**: whatever module implements the self-scan file discovery (the
  same code path `ultron/core/pipeline/discovery.py` or `analyzer.py` uses when
  Ultron scans itself for `/api/v1/overview`).
- **Steps**: Run `ultron scan` (or hit `/api/v1/overview`) against the repo and
  dump the actual file list. Diff it against a naive `git ls-files -- '*.py'`
  count. Determine whether the 148 includes test fixtures under
  `ultron/tests/fixtures/` (e.g. `clean_repo`, `tangled_repo`, `mixed_repo` used
  for health-score calibration) — if so, the self-scan is scanning its own test
  fixtures as if they were the project being analyzed, which is a real bug, not
  a cosmetic discrepancy.
- **Acceptance**: A written explanation in `PROJECT_LOG.md` of exactly what the
  148 files are (paths, categories), plus a fix if fixture contamination is
  confirmed (scan should exclude `ultron/tests/fixtures/**` from a self-scan of
  the *product*, or the two numbers should be clearly labeled as different scans).

---

## 3. Phase P2-B: Make the Verification Process Itself Trustworthy

### Task P2-B1 — Single Source-of-Truth Test Command + CI Wiring
- **Files**: new `Makefile`/`justfile` target or `scripts/verify.py`; update
  `README.md`'s "Verification" section.
- **Problem**: Nothing forces "the tests" to mean "all 639 tests" instead of an
  agent's self-chosen subset. Add one canonical command,
  `ultron verify` (or `make verify`), that runs full discovery, fails loudly on
  any error/failure, and prints a stable summary line
  (`TESTS: <n> ran, <f> failed, <e> errors`) that both humans and agents grep for.
- **Acceptance**: `ultron verify` (or the chosen command) exits non-zero on any
  failure/error, zero when clean; wire it into the GitHub Actions workflow added
  in Phase 1's D2 so PRs can't merge on a red suite.
- **DoD**: A deliberately-broken test proves the gate fails the build.

### Task P2-B2 — PROJECT_LOG.md Must Cite the Full-Suite Number, Not a Subset
- **Files**: `PROJECT_LOG.md`, `docs/TASK_PROGRESS_TRACKER.md`.
- **Problem**: Phase 1's log entries cite per-task test files ("12/12",
  "18/18") without ever citing the whole-repo number, which is how the 68 broken
  tests went unnoticed across 18 "complete" tasks.
- **Steps**: Add a mandatory log field per task: `full_suite_before` and
  `full_suite_after` (format: `ran=N failures=F errors=E`). Backfill this
  retroactively for tasks A1–E2 if feasible, or explicitly mark it
  "not captured, see Phase 2 finding" for historical honesty.
- **Acceptance**: Every future `PROJECT_LOG.md` entry contains both fields.

---

## 4. Phase P2-C: Finish What Phase 1 Left Ungrounded

### Task P2-C1 — Verify the 4-Signal Confidence Weights Empirically
- **Files**: `ultron/core/risk/scoring.py` (confidence model, weights
  `ast=0.35, coupling=0.25, churn=0.15, coverage=0.25`).
- **Problem**: These weights were asserted, not calibrated against any labeled
  ground truth. Phase 1's B4 DoD only checked the fields are "non-empty," not
  that the weights predict anything real.
- **Steps**: Using the existing fixture repos (`clean_repo`, `tangled_repo`,
  `mixed_repo`) plus at least one real historical incident (a past bug/regression
  in this repo's own git history, if one can be identified via `git log`),
  check whether files flagged HIGH confidence-risk actually correlate with
  files that were later changed/reverted/hotfixed. Document findings even if
  inconclusive — the goal is turning an asserted formula into a measured one.
- **Acceptance**: A short calibration note in `docs/` with at least one concrete
  before/after example, or an honest statement that weights remain heuristic
  pending more historical data.

### Task P2-C2 — MCP Tool Error-Path Hardening
- **Files**: `ultron/interfaces/mcp_server.py`.
- **Problem**: D3's golden tests (12/12) only exercise happy paths per the
  report's description. Add adversarial cases: malformed JSON-RPC payload,
  nonexistent file path passed to `get_risk_profile`/`audit_file`, and a
  concurrent-call stress test (2 tools called back-to-back on the same stdio
  pipe) to confirm the "defensive exception shielding" actually prevents a
  crash rather than just wrapping errors cosmetically.
- **Acceptance**: New `test_mcp_adversarial.py`, all passing, included in the
  full-suite run from Task P2-B1.

### Task P2-D1 — First-Run Experience on a Clean Machine (Not Just Fast Reinstall)
- **Files**: `pyproject.toml`, `setup.py`, `README.md`.
- **Problem**: E1's "1.8s install" was measured with dependencies already cached
  locally (`.venv` pre-existing in this checkout). Validate a genuinely cold
  install: fresh venv, no pip cache, timing `pip install -e .` end-to-end, and
  confirm the "<60s clone to first screen" DoD holds under those conditions,
  not just a warm-cache re-run.
- **Acceptance**: Documented cold-install timing in `README.md` or
  `docs/TASK_PROGRESS_TRACKER.md`, replacing/annotating the 1.8s figure with
  the honest cold number.

---

## 5. Execution Order

```
P2-A1 -> P2-A2 -> P2-A3   (blocking: repair breakage, must be done first)
   |
   v
P2-B1 -> P2-B2            (make future verification trustworthy)
   |
   v
P2-C1 -> P2-C2 -> P2-D1   (finish grounding what was asserted, not measured)
```

Do not start P2-B/C/D until P2-A's full-suite command reports `errors=0,
failures=0` — everything downstream depends on being able to trust that number.

## 6. Program Definition of Done for Phase 2

| Criterion | Target | Verification |
|---|---|---|
| Full suite health | 0 errors, 0 failures across ALL discovered tests | `python -m unittest discover -s ultron/tests -p "test_*.py"` ends `OK` |
| Test count transparency | Total test count documented and stable (~600-639) | Logged in `docs/TASK_PROGRESS_TRACKER.md` |
| Self-scan file count explained | 148-vs-71 discrepancy resolved with evidence | Written note in `PROJECT_LOG.md` |
| Verification is unfakeable | Single canonical `verify` command wired into CI | Deliberately broken test fails the build |
| Confidence weights grounded | At least one real calibration data point, not just asserted | Note in `docs/` |
| Cold-install honesty | Cold-cache install timing reported | `README.md`/tracker updated |

---

## 7. Kickoff Prompt for the Executing Agent

> You are continuing the Ultron modernization program. Phase 1 (18 tasks) was
> reported complete, but an independent audit found the verification itself was
> unreliable: running the FULL test suite (`python -m unittest discover -s
> ultron/tests -p "test_*.py"`) shows 68 of 639 tests failing/erroring, which
> contradicts the Phase 1 report's "0 errors, 0 failures" claim. Read
> `docs/AGENT_EXECUTION_PLAN_PHASE2.md` in full before doing anything. Start with
> Task P2-A1, then P2-A2, then P2-A3 — these are blocking and must each end with
> you pasting the actual full-suite pass/fail/error counts (not a subset) into
> your commit message and `PROJECT_LOG.md`. Do not report a task "done" using
> only the tests you personally authored for it — always additionally run full
> discovery and report that number. Once Phase P2-A is clean, proceed to P2-B,
> then P2-C/D in the order given in Section 5 of the plan.
