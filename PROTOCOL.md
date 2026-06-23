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

## One-line summary to keep in view

**Read the task. Say what you're about to do before doing it. If it
needs a real human, stop and say so. Show real output. Check it against
the rules. Log it fully. Don't move on until that's done.**
