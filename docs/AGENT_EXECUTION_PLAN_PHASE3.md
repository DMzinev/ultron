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

## 2. Additional Empirical Findings That Motivate a Larger Phase 3

Beyond the flakiness bug, a fresh pass over the live repository (not the report)
surfaced several structural gaps that Phase 1/2 never touched because both phases
were scoped to backend correctness and verification integrity, not product depth:

1. **Python-only, confirmed**: `ultron/core/language_adapter.py` defines exactly
   one concrete adapter, `PythonLanguageAdapter`. The README's "Honest Limitations"
   section states this plainly. For a tool whose stated mission is directing
   *any* "vibe coder's" autonomous agents, most real-world repos it will be pointed
   at are JS/TS/mixed-language — this is the single biggest gap between the tool's
   ambition and its actual reach.
2. **No onboarding/tutorial doc**: `docs/` contains only plan/tracker/inventory
   files (`AGENT_EXECUTION_PLAN*.md`, `API_SURFACE.md`, `TASK_PROGRESS_TRACKER.md`,
   `UNTRACKED_INVENTORY.md`) — nothing aimed at a first-time end user walking
   through "point Ultron at your repo, here's what you'll see, here's what to do
   next." The README covers install + capabilities but not a guided first session.
3. **MCP surface has grown organically to 9 tools** (up from the original 7 in
   Phase 1's D3), but nothing has re-validated that an actual agentic client
   (Cursor/Windsurf/Claude Desktop config, which the code already auto-installs
   per the P2-C1 log's `.cursor/mcp.json` output) can discover and successfully
   call all 9 end-to-end — only golden/adversarial unit tests exist.
4. **`index.js` has grown to 1,688 lines** in a single file (from the C-phase
   rebuild) with `index.html` at 414 lines. No modularization invariant exists
   for the frontend the way `server.py` has a hard 300-line ceiling for the
   backend — this is a maintainability risk symmetric to the one Phase 1's A3
   fixed on the backend, just never applied to the frontend.
5. **Coverage adapter exists but is unverified against a real repo with actual
   `coverage.py`/`pytest-cov` output** — `ultron/core/coverage_adapter.py` is
   present, but nothing in the reports demonstrates it parsing a real coverage
   XML/JSON report rather than a synthetic fixture.
6. **Path/security hygiene is only partially evidenced**: `browse_folder.py`
   normalizes paths via `os.path.abspath`/`normpath`, but no test file found
   during this pass exercises directory-traversal attempts (`../../etc`,
   symlink escapes) against the browse/scan endpoints — worth confirming
   explicitly rather than assuming safety from normalization alone.

None of these are regressions — they're simply scope the last two phases never
covered. Phase 3 below is sized to make real progress on all of them.

---

## 3. Phase 3 Execution Sequence

```
P3-A1 -> P3-A2                     [PHASE P3-A: Verification Integrity — must run first]
   │
   ▼
P3-B1 -> P3-B2 -> P3-B3            [PHASE P3-B: Prove the Product Actually Works End-to-End]
   │
   ▼
P3-C1 -> P3-C2                     [PHASE P3-C: Frontend Health & Original Simplicity Vision]
   │
   ▼
P3-D1 -> P3-D2                     [PHASE P3-D: Reach — Multi-Language & Onboarding]
   │
   ▼
P3-E1                              [PHASE P3-E: Security Hygiene Confirmation]
```

---

## 4. Phase P3-A: Verification Integrity (blocking, run first)

### Task P3-A1 — Eliminate Port-Bind Flakiness in the Verify Gate
- **Files**: search all of `ultron/tests/*.py` for hardcoded ports
  (`8000`, `8001`, `65255`-style leftover ephemeral values, etc.) and the server
  lifecycle helpers in `ultron/interfaces/server.py`.
- **Problem**: An observed full-suite run exited process code **1** while its own
  summary line read `0 failed, 0 errors` — logs showed
  `[-] Could not start server. Ports are all in use.` / `Server error: Bad arg`
  around a server-lifecycle test. A second run immediately after was clean.
  This is a real reproducibility bug in the "single source of truth" gate: if a
  clean run can spuriously fail, the inverse (a broken run spuriously passing due
  to the same port confusion swallowing a real crash) is also plausible and must
  be ruled out.
- **Steps**:
  1. Grep every test file for literal port numbers; replace fixed ports with
     `port=0` (OS-assigned ephemeral) plus reading back the bound port via
     `socket.getsockname()[1]`.
  2. Wrap every server-lifecycle test in `try/finally: httpd.server_close()`
     (mirroring the Phase 1 E1 invariant) so a failed assertion mid-test can't
     leak a bound socket into the next test process.
  3. Where `serve()`'s "port hopping" behavior is itself under test (deliberately
     simulating a busy port), use `unittest.mock` to fake `OSError` on `bind()`
     rather than actually occupying a real OS port with a second live process.
  4. Add a CI step that runs `scripts/verify.py` **twice back-to-back in the same
     job** and fails if either run's exit code or ran/failed/error counts differ.
- **Acceptance**: 5 consecutive local full-suite runs (`.venv\Scripts\python.exe
  scripts\verify.py`), all exit code 0, all identical `ran/failed/errors/skipped`.
- **DoD**: CI log showing the back-to-back double-run step passing.

### Task P3-A2 — Stabilize and Document the Skipped-Test Count
- **Files**: all files containing `@unittest.skip`/`skipIf`; `docs/TASK_PROGRESS_TRACKER.md`.
- **Problem**: Skip count varied 9→10 between the Phase 2 report and independent
  re-run in this session. An undocumented, ambient-state-dependent skip count
  undermines exactly the "unfakeable, reproducible" property Phase 2 set out to
  build.
- **Steps**: Enumerate every skip condition and its trigger (network absence, OS
  platform, missing optional binary, etc.). For any relying on live network
  access or other non-deterministic ambient state, either (a) make the condition
  deterministic by mocking the specific failure instead of depending on a real
  live probe, or (b) if truly environment-dependent by design, document it
  explicitly in `docs/TASK_PROGRESS_TRACKER.md` with the exact expected count per
  environment class (e.g., "offline CI runner: 10 skips; online dev machine:
  9 skips") so a future delta is recognized as expected, not investigated as a
  regression every time.
- **Acceptance**: A table in `docs/TASK_PROGRESS_TRACKER.md` listing every skip,
  its file, its trigger condition, and its expected-skip environment class.

---

## 5. Phase P3-B: Prove the Product Actually Works End-to-End

### Task P3-B1 — Real Browser-Level Smoke Test of the 4-Pillar UI
- **Files**: new `ultron/tests/test_ui_smoke_live.py`; may reuse
  `ultron/interfaces/server.py`'s `create_server()`.
- **Problem**: Across two full modernization phases, every verification has been
  at the unit or raw-HTTP-handler level. No test has ever loaded the actual
  rendered `index.html` + `index.js` in anything that executes JavaScript and
  confirmed the 4 pillar tabs (Dashboard/Graph/Studio/Auditor) each render
  non-empty, non-error content when clicked.
- **Steps**: Respect the "zero new third-party dependencies" invariant from
  Phase 2 — do not add Selenium/Playwright. Instead: spin up a live
  `create_server()` instance, fetch `/` via stdlib `http.client`, and add a
  minimal headless JS-execution check using Python's bundled tools only if
  truly necessary; otherwise settle for a strict DOM-structure + inline-script
  static assertion (e.g., verify every `data-view="dashboard|graph|studio|auditor"`
  panel element exists, has a matching nav tab, and that `index.js` contains a
  live fetch call wired to each pillar's backend endpoint) as a pragmatic
  stand-in for full browser execution, clearly documented as such.
- **Acceptance**: New test passes; a short note in `PROJECT_LOG.md` documenting
  exactly what was and wasn't verified (static structural check vs. true
  browser JS execution) so this isn't oversold as more than it is.

### Task P3-B2 — MCP Client-Compatibility Round Trip
- **Files**: `ultron/interfaces/mcp_server.py`; new
  `ultron/tests/test_mcp_client_roundtrip.py`.
- **Problem**: 9 MCP tools exist and pass golden/adversarial unit tests, but
  nothing simulates an actual external agent client's discovery + call sequence
  (`initialize` → `tools/list` → `tools/call` per tool) over the real stdio
  subprocess, the way a genuine Cursor/Claude Desktop/Antigravity client would.
- **Steps**: Write a subprocess-based test that spawns `ultron-mcp`, sends a
  realistic `initialize` handshake, requests `tools/list`, asserts all 9 tools
  are present with valid JSON schemas, then calls each tool once with a minimal
  valid payload and asserts a well-formed, non-error JSON-RPC response for each.
- **Acceptance**: New test passes; documents exact tool count and names
  confirmed reachable via the real protocol handshake (not just internal
  function calls).

### Task P3-B3 — Coverage Adapter Validated Against Real Coverage Output
- **Files**: `ultron/core/coverage_adapter.py`; new
  `ultron/tests/test_coverage_adapter_real.py`.
- **Problem**: The coverage signal (25% weight in the confidence model) has only
  been exercised against synthetic fixtures, per the available evidence. No test
  demonstrates it correctly parsing genuine `coverage.py` XML/JSON output.
- **Steps**: Run `coverage run -m pytest` (or `unittest`) on a small fixture repo
  under `ultron/tests/fixtures/`, generate a real coverage report, and add a test
  that feeds that real report through `coverage_adapter.py`, asserting it
  extracts sane per-file percentages that match the real tool's own summary.
- **Acceptance**: New test passes using a genuinely generated coverage report,
  not a hand-written synthetic one.

---

## 6. Phase P3-C: Frontend Health & the Original End-User Simplicity Vision

### Task P3-C1 — Apply a Frontend Modularity Invariant (Symmetric to `server.py`'s 300-Line Ceiling)
- **Files**: `ultron/interfaces/web/index.js` (currently 1,688 lines), split into
  cohesive ES modules (e.g., `modules/dashboard.js`, `modules/graph.js`,
  `modules/studio.js`, `modules/auditor.js`, `modules/api.js`, `modules/state.js`
  — some of these module names already exist per the summarized history; verify
  whether they were reintroduced/collapsed during the C-phase rebuild and
  restore proper separation if `index.js` absorbed them back into one file).
- **Problem**: The backend earned a hard <300-line invariant on `server.py`
  (Phase 1 Task A3) specifically to prevent god-file regrowth. No equivalent
  discipline exists on the frontend, and it has already grown to 1,688 lines in
  one file — the same failure mode Phase 1 fixed on the backend is quietly
  recurring on the frontend.
- **Steps**: Extract cohesive concerns into separate files loaded as ES modules
  (`<script type="module">`), add a lint/size check (e.g., a small
  `scripts/check_frontend_size.py` asserting no single frontend JS file exceeds
  a defined ceiling, say 400 lines) wired into `scripts/verify.py` or CI.
- **Acceptance**: No single `ultron/interfaces/web/**/*.js` file exceeds the
  chosen ceiling; existing UI behavior/tests (`test_dashboard_hierarchy.py`,
  `test_violation_to_fix.py`, etc.) still pass unmodified in behavior.

### Task P3-C2 — Revisit the Original "Not a Cockpit" Simplicity Goal
- **Files**: `ultron/interfaces/web/index.html`, `index.js`.
- **Problem**: The user's original, foundational ask (before Phase 1 even began)
  was explicitly to make the UI feel less like a "pilot cockpit" — high
  information density, many controls, high cognitive load. Two full
  modernization phases have focused entirely on backend correctness and
  verification integrity; the actual end-user simplicity goal has not been
  re-measured since the initial C-phase rebuild, and Phase 1/2's restoration of
  several legacy route handlers (e.g., P2-A1's restored `handle_v1_agent_handoff`,
  `handle_v1_agent_context_builder`, work-state handlers) raises a real question
  of whether backend restorations quietly re-exposed old UI affordances or
  controls that the C4 redesign had deliberately removed.
- **Steps**: Take a fresh screenshot/DOM snapshot of the live dashboard. Audit
  every visible control/panel/button against the C4 "what's risky to change
  right now, above the fold" goal. Identify anything reintroduced by backend
  restoration work that doesn't serve an end user directly (vs. serving an
  agent/API consumer, which is fine to keep backend-only). Produce a short
  before/after comparison and a concrete simplification list.
- **Acceptance**: A written comparison note plus, if the user approves the
  proposed simplifications after reviewing them, an implementation pass —
  **do not auto-remove UI elements without a review checkpoint**, since a past
  simplification without validation is exactly how the original cockpit
  complaint arose in the first place.

---

## 7. Phase P3-D: Reach — Multi-Language Support & Onboarding

### Task P3-D1 — Prototype a Second Language Adapter (JavaScript/TypeScript)
- **Files**: `ultron/core/language_adapter.py` (add `JavaScriptLanguageAdapter`
  alongside the existing `PythonLanguageAdapter`); new fixture repo under
  `ultron/tests/fixtures/js_sample_repo/`.
- **Problem**: The tool's stated mission is to help *any* vibe-coder direct
  autonomous agents across real repos, but it can currently only analyze Python.
  Most real-world "vibe coded" repos are JS/TS. This is the single largest gap
  between Ultron's ambition and its actual usefulness.
- **Steps**: Using only the standard library (respecting the "zero new
  dependencies" invariant, or explicitly proposing and getting sign-off on one
  well-justified lightweight JS/TS parser dependency if a stdlib-only approach
  proves too limited for real import/call-graph extraction), implement a minimal
  adapter that can at least: discover `.js`/`.ts` files, extract `import`/
  `require`/`export` statements for a dependency graph, and compute a basic
  cyclomatic-complexity-style proxy metric (e.g., branching keyword density) if
  full AST-level McCabe isn't feasible without a new dependency. Explicitly scope
  this as a **prototype/experimental adapter**, not full parity with the Python
  adapter, and document exactly what is and isn't supported.
- **Acceptance**: New adapter passes a basic self-test against the fixture repo;
  `/api/v1/overview` correctly reports file counts for a mixed Python+JS repo
  pointed at the tool, with JS files clearly labeled with a lower-confidence/
  prototype tier so nobody mistakes it for full parity.

### Task P3-D2 — First-Time User Onboarding Walkthrough
- **Files**: new `docs/GETTING_STARTED.md`; possibly a first-run in-app tour
  triggered by `ultron-server` on an empty/first analysis.
- **Problem**: No document currently walks a brand-new user through "here's
  what you'll see the first time you point Ultron at your repo, here's how to
  read the health score, here's how to use the mission compiler to hand off a
  fix to an AI agent." The README documents capabilities and honest limits but
  isn't a guided first session.
- **Steps**: Write a concrete, screenshot-or-DOM-annotated walkthrough covering:
  first scan → reading the dashboard's "risky files" list → opening the
  dependency graph → compiling a mission for one real violation → handing that
  mission to an external coding agent → interpreting the CI gate. Link it from
  `README.md`.
- **Acceptance**: New doc exists, reviewed for accuracy against the actual live
  UI (not aspirational copy — every step must correspond to a real, working
  screen/action).

---

## 8. Phase P3-E: Security Hygiene Confirmation

### Task P3-E1 — Directory-Traversal and Symlink-Escape Test Coverage for Browse/Scan Endpoints
- **Files**: `ultron/interfaces/api/browse_folder.py`; new
  `ultron/tests/test_path_security.py`.
- **Problem**: `browse_folder.py` normalizes paths via `os.path.abspath`/
  `os.path.normpath`, but no test file found in this pass explicitly exercises
  adversarial inputs (`../../../etc`, absolute paths outside any allowed root,
  symlink escapes on platforms that support them) against the browse/scan
  endpoints to confirm normalization alone actually prevents escaping an
  intended root directory.
- **Steps**: Add explicit adversarial test cases: relative traversal sequences,
  UNC/absolute path injection on Windows, and (where the OS supports it) a
  symlink pointing outside the intended root. Assert the endpoint either
  rejects these with a clear error or safely clamps to a permitted root — pick
  and document one policy explicitly (currently undocumented).
- **Acceptance**: New test suite passes; `docs/API_SURFACE.md` gets a short
  note stating the enforced path-safety policy for browse/scan endpoints.

---

## 9. Program Definition of Done for Phase 3

| # | Criterion | Target | Verification |
|---|---|---|---|
| 1 | Verify-gate reproducibility | 5 consecutive clean runs, identical results | Manual + CI double-run step |
| 2 | Skip count documented | Every skip enumerated with trigger + expected environment class | Table in `TASK_PROGRESS_TRACKER.md` |
| 3 | UI smoke-tested end-to-end | New live smoke test passing, scope honestly documented | `test_ui_smoke_live.py` + `PROJECT_LOG.md` note |
| 4 | MCP protocol round-trip proven | All 9 tools reachable via real stdio handshake | `test_mcp_client_roundtrip.py` |
| 5 | Coverage adapter proven on real data | Parses genuine `coverage.py` output correctly | `test_coverage_adapter_real.py` |
| 6 | Frontend size discipline | No single JS file exceeds defined ceiling | `scripts/check_frontend_size.py` in CI |
| 7 | Simplicity goal re-validated | Written before/after comparison, user-reviewed | Comparison note + (optional) approved simplification pass |
| 8 | Second language prototyped | JS/TS adapter passes basic self-test, clearly scoped as prototype | New adapter + fixture test |
| 9 | Onboarding doc exists | Accurate, screenshot/DOM-verified walkthrough | `docs/GETTING_STARTED.md` |
| 10 | Path-traversal safety confirmed | Adversarial path tests pass with a documented policy | `test_path_security.py` |

Order matters: **P3-A must complete first** (it's about trusting the gate itself);
everything after can be parallelized across separate agent sessions/branches if
desired, since B/C/D/E tasks touch disjoint files.

---

## 10. Kickoff Prompt for the Executing Agent

> Phase 2 held up under independent audit — full suite genuinely shows 766 ran,
> 0 failed, 0 errors, and the confidence-weight calibration and MCP hardening
> work is real. Phase 3 is larger: start with Task P3-A1 (fix a real port-bind
> flakiness bug where `scripts/verify.py` exited code 1 despite reporting 0
> failed/0 errors — reproduce it, then fix it structurally, not by retrying),
> then P3-A2 (document the skip count so it's never ambiguous again). Once the
> gate itself is trustworthy, move to Phase P3-B: nothing in this project has
> ever verified the rendered UI in anything beyond raw HTTP handlers, or proven
> the MCP server works via a real client handshake, or proven the coverage
> adapter against genuine `coverage.py` output — close all three gaps. Then
> Phase P3-C: apply the same <300-line-style discipline Phase 1 put on
> `server.py` to the frontend (`index.js` is now 1,688 lines in one file), and
> — critically — re-examine whether Phase 1/2's backend restorations quietly
> reintroduced UI complexity the original C4 redesign removed; get user
> sign-off before removing anything, don't just auto-simplify. Then Phase P3-D:
> prototype a second language adapter (JS/TS) since Ultron is currently
> Python-only despite its mission being repo-agnostic, and write a real
> first-time-user onboarding doc. Finally Phase P3-E: add adversarial path-
> traversal tests for the browse/scan endpoints since normalization alone has
> never been explicitly proven safe. As always: report full
> `scripts/verify.py` output (not a subset) before and after every task, and
> log it in `PROJECT_LOG.md` with the `full_suite_before`/`full_suite_after`
> fields Phase 2's P2-B2 made mandatory.
