# Operating Protocol

This is the formula to run for **every single task**, whether or not
external review is happening live. The other four documents
(`ROADMAP.md`, `EXECUTION_PLAN.md`, `PROJECT_LOG.md`, `UMAGS.md`) define
*what* is true and *who* checks it. This document defines *how to act*,
moment to moment, so the discipline holds even when no one is watching.

## The Rule That Matters Most

> If you catch yourself building something that generates, simulates,
> automates, or stands in for an input that was supposed to be
> independent, human-sourced, or external to this system — that is the
> signal to stop immediately, not a problem to be clever about engineering
> around.

This is not a style preference. A task already failed this exact way:
a blinded human-rating study was replaced with a script that simulated
the rater, defeating the entire purpose of the study while producing
output that looked legitimate. No framing — "automating the interactive
flow," "acting as a blinded proxy," "simulating for testing" — makes this
acceptable when the task is collecting a human-only input. If a step is
blocked on something only a person can provide, the correct action is to
stop and say so, not to find a way to proceed anyway.

## The Formula

Run this for every task, no exceptions:

1. **READ** — Before touching anything, re-read the specific task in
   `EXECUTION_PLAN.md` and the current relevant section of `ROADMAP.md`.

2. **DECLARE** — Before acting, write one short line to `THOUGHT_LOG.md`:
   what you're about to do, and what would actually count as evidence it
   worked. Do this *before*, not as a summary after.

3. **HUMAN-ONLY CHECK** — Ask explicitly: does any part of this task
   require real human judgment, real-world data, or an input that's
   supposed to come from outside this system? If yes — stop here. Log
   `BLOCKED: requires human input — [what, specifically]` to
   `PROJECT_LOG.md` and wait. Do not write any code in service of working
   around this.

4. **ACT** — Do the smallest reversible piece of the task. Don't bundle
   multiple changes into one step.

5. **SHOW** — Paste raw output. Never paraphrase, never summarize a
   result in place of showing it.

6. **AUDIT** — Run both checklists from `UMAGS.md` against what just
   happened: Category A (code-level judgment) and Category B (mechanical,
   no-exceptions checklist for any claim involving data).

7. **LOG** — Append the full entry to `PROJECT_LOG.md` using the existing
   template, with verbatim evidence, not a summary. Leave "External
   verification" as `PENDING` — always, regardless of role, regardless of
   how confident the self-audit was.

8. **STOP** — Do not start a new task, and do not build anything not
   explicitly listed in `EXECUTION_PLAN.md`, until the current entry is
   fully logged. If something seems worth building that isn't on the
   list, add it to `EXECUTION_PLAN.md` as a future task instead of
   building it now.

## `THOUGHT_LOG.md` — why it's separate from `PROJECT_LOG.md`

`PROJECT_LOG.md` entries are written once a task is complete and verified
— polished, structured, final. `THOUGHT_LOG.md` is the opposite on
purpose: raw, timestamped, one or two lines at a time, written *during*
the work, including dead ends, doubts, and wrong turns.

The value of this is concrete, not procedural: if a one-line declared
thought like *"I'll write a script to simulate the rater's responses so I
don't have to wait"* exists in a live log, it's visible and catchable the
moment it's written — instead of being discovered after eight fake
ratings have already been produced and presented as real.

Format — append, never edit past entries:

```
[2026-06-21T09:30:00Z] About to start Task 5 prep. Plan: join ratings
against scores, compute Spearman + threshold sweep. Evidence of success:
real human ratings exist in blind_feedback.jsonl before I touch them.

[2026-06-21T09:34:00Z] blind_feedback.jsonl is still empty — ratings
haven't been collected by a human yet. This is a HUMAN-ONLY step.
Logging BLOCKED to PROJECT_LOG.md and stopping here.
```

## Task-Type Tiers: Matched Verification

Not all tasks are the same, and running the full verification suite on every task
regardless of what changed is the primary source of O(n_files) compute multipliers.

Before running `run_verification_loop.py`, classify the task as one of two types:

### STRUCTURE-ONLY
A task is STRUCTURE-ONLY if and only if **no file's logic or content changed** —
only its location, name, or import path changed. Examples: `git mv`, module renames,
import path updates, directory reorganizations.

**Verification for STRUCTURE-ONLY tasks:**
- Run the full test suite **once** (`python ultron/tests/run_tests.py`)
- Confirm `git status` shows the expected file movements and nothing else
- Run one import-resolution check (`python -c "import ultron"` or equivalent)
- **Skip:** per-file nullification, per-file AST drift, per-file reality scoring, architecture drift detection
- **Rationale:** content did not change; per-file checks on relocated but unmodified code
  produce only false-positive noise (every moved function appears "new" in drift detection)

### LOGIC-CHANGE
A task is LOGIC-CHANGE if **any file's content changed** — new functions, modified
behavior, bug fixes, added tests, configuration changes.

**Verification for LOGIC-CHANGE tasks:**
- Run the full test suite
- Run per-file nullification check for all `.py` files in `CHANGED_FILES`
- Run AST compliance and residual-risk analysis
- Run cognitive LLM review if API key is available
- **Architecture drift detection** is informational only — do not fail on it for files
  that were moved in a prior commit

### How to declare in governor.py
Add `--task-type STRUCTURE_ONLY` or `--task-type LOGIC_CHANGE` as a CLI argument.
If omitted, the loop defaults to `LOGIC_CHANGE` (conservative).

---

## One-line summary to keep in view

**Read the task. Say what you're about to do before doing it. If it
needs a real human, stop and say so. Show real output. Check it against
the rules. Log it fully. Don't move on until that's done.**

---

## Efficiency & Escalation: The Pre-flight Gate

### Rule (permanent constraint, not a one-off patch)

Before any Builder/Auditor/Judge/Historian steps in `run_verification_loop.py`,
the loop calls Ultron's own `risk.evaluate_risks()` on the declared target files.
This is a local, no-LLM, O(1)-in-ceremony-cost operation. The tier it returns
decides how much verification ceremony the rest of the loop executes.

**The tier ordering is: HIGH > MEDIUM > LOW.**
(Never use string `max()` — `"MEDIUM" > "LOW" > "HIGH"` lexicographically,
which is wrong. The implementation uses `_TIER_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}`.)

### FAST PATH — `LOW/MEDIUM + STRUCTURE_ONLY + no Category-B`

Checks run:
- Scope verification (undeclared source files check)
- Single test suite run

Explicitly skipped:
- O(n) nullification loop
- Per-file AST drift and residual risk analysis
- Cognitive LLM review

Telemetry is written. The loop proceeds through all four roles (B/A/J/H)
but those roles perform only the fast-path subset of checks.

> [!NOTE]
> FAST PATH does not skip the independent Critic subagent review —
> that review happens at *planning time*, before governor is invoked.
> UMAGS §1 is satisfied by the planning-time Critic, not by the loop.

### FULL PATH — `HIGH tier`, OR `Category-B=true`, OR `LOGIC_CHANGE`

All existing checks run. At the end of the loop, if `tier=HIGH` or
`category_b=true`, the loop prints:

```
ESCALATE: requires external review
```

This means: paste the full output into `PROJECT_LOG.md` under the
`External verification` field. Only a human operator may fill that field.
No agent in the pipeline may generate, simulate, or pre-fill it.

### The O(n) Token-Budget Rule (permanent, enforced in code)

> **No check may scale with file count (O(n) per-file loops) unless the
> pre-flight tier is HIGH.**

The nullification loop is the primary O(n) offender (it runs tests once
per changed file). It only executes when `preflight_tier == "HIGH"`.
At LOW or MEDIUM tier, it is skipped with an explicit log line explaining
the reason. This is enforced in `run_verification_loop.py`, not advisory.

### Fail-safe (hard rule, no exceptions)

If the pre-flight gate itself throws an exception for any reason, the tier
defaults to `HIGH` and the full path runs. The system **never** silently
auto-approves on uncertainty. Uncertainty escalates — it does not wave through.

If the gate returns an empty risks list (non-Python targets, new files not
yet in the codebase scan), the tier is `LOW`. This is a valid result —
non-Python files have no coupling risk to the governance engine.

### Category-B flag

Any task containing numbers derived from data (precision, recall, F1,
rating comparisons, calibration scores, etc.) must pass `--category-b`
to `governor.py`. This stamps `CATEGORY_B: 'true'` in `audit_package.yaml`
and forces the full verification path plus an `ESCALATE` notice, regardless
of the pre-flight risk tier.

### Path normalization requirement

`evaluate_risks()` silently skips files whose paths do not match the keys
in the codebase dict produced by `analyze_directory()`. On Windows, declared
paths may use backslashes while codebase keys use forward slashes. The
pre-flight gate must normalize both to forward-slash relative paths before
comparison. This is implemented in `run_preflight_risk_gate()`.
