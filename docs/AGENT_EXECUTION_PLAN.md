# Ultron — Autonomous Agent Execution Plan

**Audience:** an agentic coding tool (Google Antigravity / Gemini Flash 3.8, high reasoning) executing tasks with minimal human supervision.
**Author role:** long-term goal owner. This document is the source of truth for *what* to build and *how success is proven*.
**Optimization target:** highest verified quality per token spent.

---

## 0. Verified Baseline — DO NOT RE-DISCOVER

Every number below was measured on commit `4fab9c7` (merge of `dimmiz1-app-review` into `master`).
Trust these. Do not spend tokens re-deriving them.

| Fact | Value | How it was measured |
|---|---|---|
| Tracked files | 195 | `git ls-tree -r master --name-only` |
| Test suite | 85 tests, 131 s, **1 error** | `python -m unittest discover -s ultron/tests -p "test_*.py"` |
| Failing test | `test_openai_plan_reviewer` | missing untracked `.agents/skills/openai-plan-reviewer/scripts/consult_plan_api.py` |
| Self-scan health score | **10 / 100** | `POST /api/architecture-health {"repo":"."}` |
| Rule violations on self | 89 | same |
| Files ranked | 71 | `POST /api/v1/overview` → `stats.total_files` |
| Risk distribution | **HIGH 41, MEDIUM 9, LOW 21** | same → `stats` |
| Dependency graph nodes | 684 (71 file nodes + 613 symbol nodes) | `POST /api/dependency-graph` |
| API routes defined | 43 | `server.py` route table |
| API routes used by UI | 12 | `index.js` fetch calls |
| Largest source file | `ultron/interfaces/server.py` — 2 619 lines | line count |
| Dead frontend still tracked | `ultron/interfaces/web/legacy.js` — 2 361 lines | line count |

### The five defects that matter

**D1 — The core claim is not delivered.** 58 % of files are labelled `HIGH`.
A ranking where the majority is "top priority" carries no information. Root cause is in
`ultron/core/risk/scoring.py`: the bands are **absolute constants** (`high_t = 10.0`,
`med_t = 3.0`) applied to an `impact_score` that scales with complexity. Any mature
codebase saturates them. This is the single highest-value fix in the repository.

**D2 — The health score is not calibrated.** Ultron scores its own repository 10/100.
Either the number is wrong, or the product is unusable — and there is no fixture proving
which. A score with no defined meaning cannot drive a decision.

**D3 — Mixed-granularity graph.** `/api/dependency-graph` returns file nodes
(`ultron/core/analyzer.py`) and symbol nodes (`start.py:launch_ultron`) in one flat list
with no granularity contract. The UI renders them identically and truncates to 90 nodes by
`impact_score`, so the picture is an arbitrary mix of two different abstraction levels.

**D4 — 72 % dead backend surface.** 31 of 43 endpoints have no UI caller. Each one is
context the agent must read, tokens it must spend, and a maintenance surface with no user.

**D5 — Unversioned working tree.** ~50 core modules, ~60 test files and ~80 audit markdown
reports exist on disk but are untracked. They are invisible to a fresh clone, excluded from
CI, and already cause one test failure. Work that is not in git does not exist.

---

## 1. Operating Protocol for the Executing Agent

These rules exist to maximise quality per token. Follow them literally.

### 1.1 Work unit
- **One task ID per branch, per session.** Never batch two task IDs.
- Branch name: `agent/<task-id>-<slug>` (e.g. `agent/B1-percentile-risk-bands`).
- A task is complete only when its **Acceptance Command** exits 0.

### 1.2 Reading discipline (biggest token lever)
- Read **only** the files listed under `Files` for the task.
- Always `grep` before you `view`. Never open a file to "look around".
- **Never open `ultron/interfaces/web/legacy.*`.** It is dead code scheduled for deletion.
- Never open `ultron/interfaces/server.py` in full. Grep for the handler name, then read
  a ±60-line window.
- Do not re-read a file you have already read in this session.

### 1.3 Writing discipline
- **Write the acceptance test before the implementation.** A failing test costs ~200
  tokens and eliminates entire wrong directions.
- Surgical edits only. Do not reformat, do not rename unrelated symbols, do not add
  comments explaining obvious code.
- No new dependencies unless the task explicitly authorises one.

### 1.4 Verification gate (non-negotiable)
Before declaring any task done, run:
```
python -m unittest discover -s ultron/tests -p "test_*.py"
```
**Required: ≥ 85 tests pass and the error count is ≤ the count when you started.**
Never make the suite worse. If your change breaks a test, fix the change — not the test —
unless the task explicitly says the test encoded wrong behaviour.

### 1.5 Stop conditions
- Acceptance Command passes → **stop immediately**, commit, report. Do not polish.
- Same failure twice in a row → stop, write findings to `docs/BLOCKED-<task-id>.md`, move on.
- Task requires a decision not covered here → stop and ask. Do not guess at product intent.

### 1.6 Commit format
```
<task-id>: <imperative one-line summary>

<what changed and the measured evidence it worked>
```

---

## 2. Phase A — Foundation (makes every later task cheaper)

> Rationale: Phase A is sequenced first not because it is user-visible, but because
> it reduces the token cost of Phases B–E. A 2 619-line `server.py` is a tax on every
> subsequent task. Pay it down once.

### A1 — Freeze a behavioural baseline with fixtures
**Problem:** "Improve risk scoring" is currently unfalsifiable. There is no repository
with a known-correct answer, so no change can be proven to be an improvement.

**Files:** create `ultron/tests/fixtures/`, `ultron/tests/test_signal_quality.py`

**Steps**
1. Create three synthetic mini-repos under `ultron/tests/fixtures/`:
   - `clean_repo/` — 8 files, low complexity, shallow imports, no cycles.
   - `tangled_repo/` — 8 files, one 400-line god module, a 3-file import cycle, deep fan-in.
   - `mixed_repo/` — 12 files, 2 genuinely risky, 10 benign.
2. Write `test_signal_quality.py` asserting **distribution properties**, not exact scores:
   - `clean_repo` → 0 HIGH files.
   - `tangled_repo` → the god module and every cycle member rank in the top 3.
   - `mixed_repo` → exactly the 2 planted files are HIGH.
3. Mark currently-failing assertions with `@unittest.expectedFailure` and a comment naming
   the task that will fix them (B1/B2). **Do not fix scoring in this task.**

**Acceptance Command**
```
python -m unittest ultron.tests.test_signal_quality
```
**Definition of done:** suite runs green (expected failures counted as expected), and the
file documents today's wrong behaviour as an executable specification.
**Budget:** medium. Fixtures are cheap to write and pay for themselves in Phase B.

---

### A2 — Reconcile the unversioned working tree
**Problem:** D5. ~190 untracked files. One test already fails because of it.

**Files:** repo root, `.gitignore`, `ultron/tests/test_openai_plan_reviewer.py`

**Steps**
1. `git status --porcelain` → classify every untracked path into exactly one bucket:
   - **COMMIT** — real source or tests referenced by imports anywhere in the tree.
   - **IGNORE** — generated output, scratch, `.json` audit dumps, `PHASE*_*.md` reports.
   - **DELETE** — path-traversal test artefacts in the repo root (`%00`, `..%2F..%2Fetc%2Fpasswd`,
     `aux`, `con`, `prn`, `com1`, `....`). These are fuzz residue, not source.
2. Write the classification to `docs/UNTRACKED_INVENTORY.md` (path → bucket → one-line reason)
   **before** moving anything.
3. Apply: `git add` the COMMIT set, extend `.gitignore` for the IGNORE set, delete the DELETE set.
4. Fix `test_openai_plan_reviewer`: `skipUnless` the skill script exists. A test must never
   fail because of an optional external asset.

**Acceptance Command**
```
git status --porcelain
python -m unittest discover -s ultron/tests -p "test_*.py"
```
**Definition of done:** `git status --porcelain` prints nothing; suite reports **0 errors**.
**Budget:** high volume, low reasoning. Batch aggressively; do not read the contents of
audit markdown files to classify them — the filename is sufficient.

---

### A3 — Decompose `server.py` behind a contract test
**Problem:** D4 + a 2 619-line god object holding 43 handlers with business logic inline.
This is the main token tax on the whole repository.

**Files:** `ultron/interfaces/server.py`, `ultron/interfaces/api/routes/*.py` (package already exists),
create `ultron/tests/test_route_contract.py`

**Steps — order matters**
1. **First**, write `test_route_contract.py`: for all 43 routes, call the handler in-process
   and snapshot the **response shape** (status code + sorted top-level JSON keys, not values)
   to `ultron/tests/fixtures/route_contract.json`. Run it against the *current* code and commit
   the snapshot. This is your safety net.
2. Then move handlers out of `server.py` into the existing `routes/` modules, grouped by
   domain: `analysis_routes`, `graph_routes`, `agent_routes`, `audit_routes`, `system_routes`.
   **Move only — no logic changes in this task.**
3. `server.py` becomes a thin dispatcher: a route table mapping path → handler. Target **< 300 lines**.

**Acceptance Command**
```
python -m unittest ultron.tests.test_route_contract
python -m unittest discover -s ultron/tests -p "test_*.py"
```
**Definition of done:** contract snapshot is byte-identical before and after; `server.py` < 300 lines.
**Budget:** the largest single task in this plan. Do it in one focused session; splitting it
across sessions costs more in re-reading than it saves.

---

### A4 — Delete dead surface
**Depends on:** A3

**Files:** `ultron/interfaces/web/legacy.{html,css,js}`, `docs/API_SURFACE.md`

**Steps**
1. Delete `legacy.html`, `legacy.css`, `legacy.js` (~2 900 lines). They were superseded by
   the unified four-pillar UI. Grep first to confirm nothing references them.
2. For each of the 31 UI-unreferenced endpoints, classify: **DELETE** / **WIRE** (a pillar
   needs it) / **KEEP** (CLI, MCP or test consumer — name the consumer).
3. Record the decision table in `docs/API_SURFACE.md`.
4. Delete the DELETE set, including handler bodies and their route entries.

**Invariant to enforce from here on:** *every route has a named consumer — UI, CLI, MCP, or test.*

**Acceptance Command**
```
python -m unittest discover -s ultron/tests -p "test_*.py"
```
**Definition of done:** `docs/API_SURFACE.md` accounts for all remaining routes; no orphan handlers.

---

### A5 — Logging discipline
**Problem:** `[Ultron] No git history found` prints dozens of times per test run, drowning
real signal and inflating every log the agent has to read.

**Files:** `ultron/core/git_adapter.py`, `ultron/core/analyzer.py`, and any module using bare `print()`
for diagnostics.

**Steps**
1. Replace diagnostic `print()` with the `logging` module. Reserve `print` for CLI user output only.
2. Emit "no git history" **once per process**, at `INFO`.
3. Default console level `WARNING`; `ULTRON_LOG_LEVEL` env var overrides.

**Acceptance Command**
```
python -m unittest discover -s ultron/tests -p "test_*.py" 2>&1 | Select-String "No git history" | Measure-Object
```
**Definition of done:** count ≤ 1.

---

## 3. Phase B — Fix the Core Signal (the product's actual value)

> This is where user-visible value is created. Do not start Phase B before A1 exists —
> without fixtures you cannot prove an improvement, and unprovable work is wasted tokens.

### B1 — Distribution-aware risk bands ⭐ HIGHEST VALUE TASK
**Depends on:** A1
**Problem:** D1. Absolute thresholds saturate on real codebases → 58 % HIGH → zero information.

**Files:** `ultron/core/risk/scoring.py`, `ultron/tests/test_signal_quality.py`

**Steps**
1. Replace the absolute banding with a **hybrid** rule, computed per scan:
   - Compute the `impact_score` distribution across all analysed files.
   - `HIGH` = score ≥ 90th percentile **AND** ≥ an absolute floor (so a genuinely clean repo
     yields zero HIGH files rather than manufacturing a top decile).
   - `MEDIUM` = score ≥ 65th percentile AND ≥ a lower floor.
   - `LOW` = everything else.
2. Keep the existing bug-fix-history and human-feedback adjustments, but apply them to the
   **percentile cut points**, not to raw absolute thresholds.
3. Enforce hard invariants in code, asserted by tests:
   - `HIGH ≤ 15 %` of files, `HIGH + MEDIUM ≤ 45 %` of files.
   - A repo with zero complexity outliers produces zero HIGH.
4. Change `mitigation` text to state the **relative** fact — "in the top 6 % of this
   repository by blast radius" — not a bare threshold comparison. Relative statements are
   what a human can act on.
5. Remove the `@unittest.expectedFailure` markers from A1 that this task fixes.

**Acceptance Command**
```
python -m unittest ultron.tests.test_signal_quality
python -m unittest discover -s ultron/tests -p "test_*.py"
```
**Definition of done:** self-scan of this repo yields **HIGH ≤ 11 of 71 files**;
`clean_repo` fixture yields 0 HIGH; `mixed_repo` flags exactly the 2 planted files.
**Budget:** high reasoning, low volume. Think hard, write ~80 lines.

---

### B2 — Calibrate the health score
**Depends on:** B1
**Problem:** D2. 10/100 on its own repo, with no defined meaning.

**Files:** `ultron/interfaces/api/routes/*` (architecture-health handler), `ultron/core/rkm/evolution/engine.py`,
`ultron/tests/test_signal_quality.py`

**Steps**
1. Define and document the bands in a module docstring:
   `85–100 healthy · 60–84 watch · 30–59 degraded · 0–29 critical`.
2. Re-derive the score from **normalised, bounded** sub-signals — violation density per
   1 000 lines, cycle count, HIGH-file ratio — not from unbounded raw counts. An unbounded
   count guarantees large repos always score 0.
3. Assert calibration against fixtures: `clean_repo ≥ 80`, `tangled_repo ≤ 40`.
4. Surface the three sub-scores in the API response and in the dashboard tooltip, so the
   number is explainable rather than oracular.

**Acceptance Command**
```
python -m unittest ultron.tests.test_signal_quality
```
**Definition of done:** fixture calibration passes; self-scan produces a score the
`explanation` string can justify from its own sub-scores.

---

### B3 — Activate the git-churn signal
**Problem:** `bug-prone-file scaling is inactive` — the highest-value real-world risk
signal (files that change often and get fixed often) is silently switched off.

**Files:** `ultron/core/git_adapter.py`, `ultron/core/risk/scoring.py`, create `ultron/tests/test_churn_signal.py`

**Steps**
1. Diagnose why history is not found — likely worktree/CWD resolution, not absence of history.
2. Extract per-file: commit count, distinct authors, and commits whose message matches
   `fix|bug|hotfix|revert` over the last 180 days.
3. Feed churn into `impact_score` as a **bounded multiplier** (cap the contribution so a
   noisy file cannot dominate structural signal).
4. Build the test fixture with a real temporary git repo and scripted commits.
5. **Degrade honestly:** when history is genuinely unavailable, the API must return
   `signals.churn = "unavailable"` and the UI must say so. Never silently drop a signal.

**Acceptance Command**
```
python -m unittest ultron.tests.test_churn_signal
```
**Definition of done:** on this repository the churn signal is active and a file's commit
count measurably shifts its rank.

---

### B4 — Honest confidence, not silent degradation
**Problem:** `compute_risk_profile` reports confidence 0.0 for the missing coverage signal,
but the UI shows the verdict with no visible caveat.

**Files:** risk-profile handler, `ultron/core/rkm/risk_intelligence.py`,
`ultron/interfaces/web/index.js`, `ultron/interfaces/web/index.css`

**Steps**
1. Optionally ingest `coverage.xml` / `.coverage` from the repo root when present.
2. Always return a `signals` block: each signal → `active | unavailable` plus its weight.
3. Render a "confidence: N signals of M active" chip in the dashboard summary, with the
   missing signals named on hover.

**Acceptance Command**
```
python -m unittest discover -s ultron/tests -p "test_*.py"
```
**Definition of done:** no verdict is displayed without its confidence basis.

---

## 4. Phase C — Make the Four Pillars Trustworthy

### C1 — Graph granularity contract
**Depends on:** A3
**Problem:** D3. Files and symbols in one undifferentiated list.

**Files:** graph route module, `ultron/interfaces/web/index.js`, `ultron/interfaces/web/index.css`

**Steps**
1. Add `granularity` to the request: `file` (default) or `symbol`. Every node carries an
   explicit `type`.
2. Cluster file nodes by package and colour by package; size by blast radius.
3. Render detected import cycles as highlighted edges — cycles are the most actionable
   architectural finding the engine produces and are currently invisible in the graph.
4. Replace the fixed 90-node truncation with progressive disclosure: render the top cluster
   set, expand a cluster on click. Add an explicit "showing N of M" label — never truncate silently.

**Acceptance Command**
```
python -m unittest ultron.tests.test_route_contract
```
**Definition of done:** a self-scan graph is legible at a glance and every visible node is
the same kind of thing.

---

### C2 — Close the loop: violation → file → fix
**Problem:** 89 violations are listed but a user cannot get from a violation to a change.

**Files:** `ultron/interfaces/web/index.js`, `ultron/interfaces/web/index.css`

**Steps**
1. Make each violation card click through to that file's detail pane.
2. Group violations by principle with counts; sort by severity × blast radius, not by file order.
3. Add "Draft fix mission" on each violation → Agent Studio pre-filled with that violation as intent.

**Definition of done:** every violation is one click from an executable next action.

---

### C3 — Prove the auditor actually detects defects ⚠️
**Problem:** `/api/audit` returned **0 anomalies** on a 2 619-line file. That is either a
genuinely clean file or a silently non-functional detector. Right now nobody knows which —
and a safety gate that never fires is worse than no gate, because it manufactures false confidence.

**Files:** `ultron/core/classifier.py`, create `ultron/tests/test_auditor_sensitivity.py`

**Steps**
1. Write mutation tests: take a clean fixture file and plant known defects — a misspelled
   identifier (`respones`), a call to an undefined name, a signature-arity mismatch, an
   out-of-baseline naming convention.
2. Assert the auditor flags each planted defect. Measure and record the true-positive rate.
3. If detection fails, fix the detector. If a defect class is genuinely out of scope, say so
   explicitly in the UI copy rather than implying full coverage.
4. Display the detector's scope in the auditor panel: "checks naming drift, call sequences,
   signature conformity — does not check logic or types."

**Acceptance Command**
```
python -m unittest ultron.tests.test_auditor_sensitivity
```
**Definition of done:** every planted defect class is either detected or documented as out of scope.
**This task is a truthfulness gate. Do not skip it.**

---

### C4 — Dashboard information hierarchy
**Files:** `ultron/interfaces/web/index.css`, `index.html`

**Steps**
1. One primary answer above the fold: *"These 4 files are risky to change, here is why."*
2. Demote health score to supporting context — a single number is not a decision.
3. Empty and error states for every pillar: what happened, why, what to do next.
4. Keyboard navigation: `1–4` switch pillars, `/` focuses filter, `Esc` closes overlays.

---

## 5. Phase D — Agent-Native Output (the actual moat)

> Ultron's defensible position is not "another code metrics dashboard". It is
> *the pre-execution grounding layer that makes a coding agent succeed on the first attempt.*
> Everything in Phase D serves that.

### D1 — Mission envelope quality
**Files:** `ultron/core/context_brief.py`, `ultron/core/prompt.py`, `ultron/tests/test_ai_handoff.py`

A compiled mission must contain, and be tested for, all seven fields:
1. **Intent** — verbatim user goal.
2. **Blast radius** — the exact files a change to the target can break, derived from the graph.
3. **Must-not-touch list** — public API surfaces whose signature changes break callers.
4. **Complexity ceiling** — "this file is at McCabe 114; do not add branches".
5. **Verification command** — the specific test command proving non-regression.
6. **Rollback instruction** — how to undo.
7. **Token budget hint** — which files the agent should read, ranked, and which to ignore.

**Acceptance:** extend `test_ai_handoff.py` to assert all seven sections are present and
non-empty for a target file in each fixture repo.

**Definition of done:** a mission envelope is sufficient for an agent that has never seen
the repository to make a safe change.

---

### D2 — Machine-readable contract + CI gate
**Files:** `ultron/interfaces/cli/commands/`, export route

**Steps**
1. `ultron brief <file> --json` → stable schema, versioned (`schema_version`).
2. `ultron gate --max-high 12 --min-health 60` → exit code 0/1 for CI.
3. Emit GitHub Actions annotations so violations appear inline on a pull request diff.

**Definition of done:** Ultron can fail a build, which is what makes it adopted rather than admired.

---

### D3 — MCP parity
**Files:** `ultron/interfaces/mcp_server.py`

Expose as MCP tools: `get_risk_profile`, `get_blast_radius`, `compile_mission`, `audit_file`.
Every tool must have a golden test. An agent should reach Ultron without a browser.

---

## 6. Phase E — Distribution

### E1 — Install and first run
- `pip install -e .` works from a clean venv; `ultron` and `ultron-server` entry points resolve.
- Target: clone → first useful screen in **under 60 seconds**.
- Server picks a free port deterministically and prints one clear URL.

### E2 — Documentation that matches reality
- `README.md`: what it does, the one command to run, one screenshot, honest limits
  (Python-only analysis, no type/logic checking).
- Delete or archive the ~80 `PHASE*_*.md` audit reports — they are process residue and they
  poison every agent's context window.

---

## 7. Execution Order

```
A1 ──► B1 ──► B2 ──► B4
 │      │      │
 │      └──────┴────► C2 ──► C4
 │
A2 ──► A3 ──► A4 ──► C1
        │      │
        │      └────► D2 ──► D3
        └────► A5
B3 ──────────────────► D1 ──► E1 ──► E2
C3 (independent — run early, it is a truthfulness gate)
```

**Recommended sequence:** `A1 → A2 → C3 → A3 → A4 → A5 → B1 → B2 → B3 → B4 → C1 → C2 → C4 → D1 → D2 → D3 → E1 → E2`

`C3` is placed early despite being a Phase C task: if the auditor does not work, the product
is making a safety claim it cannot honour, and that must be known before more is built on it.

---

## 8. Definition of Done for the Whole Programme

The programme succeeds when all of the following are objectively true:

1. `git status --porcelain` is empty; every source file is tracked.
2. Test suite: **0 errors, 0 failures**, ≥ 120 tests, under 180 s.
3. Self-scan: **HIGH ≤ 15 %** of files, and each HIGH file's reason survives human review.
4. Health score is calibrated against fixtures and every point of it is explainable.
5. `server.py` < 300 lines; no source file > 600 lines.
6. Every API route has a named consumer.
7. The auditor has a measured true-positive rate on planted defects.
8. A mission envelope contains all seven D1 fields and is verified by test.
9. `ultron gate` can fail a CI build.
10. Clone → first useful screen in under 60 seconds.

---

## 9. Standing Principles

- **Never fabricate a signal.** An honest "unavailable" beats a plausible number. Ultron's
  entire value is that its output can be trusted by an agent that cannot check it.
- **Relative beats absolute.** "Top 6 % of this repo" is actionable; "score 14.2" is not.
- **Every number must be explainable** by the system that produced it.
- **Delete more than you add.** This repository's main problem is accumulated surface area.
- **A test that never fails is not a test.** A gate that never blocks is not a gate.
