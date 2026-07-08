# UMAGS — Unified Multi-Agent Governance System

## Scope (what belongs here and what doesn't)

UMAGS is **process**, not product. It contains:

| Belongs in UMAGS | Does NOT belong in UMAGS |
|---|---|
| The four-role protocol (Builder / Auditor Critic / Judge / Historian) | Any code that scores, predicts, or weights risk |
| The Category A / B review checklists | `design_oracle.py` — static analysis / risk tooling (→ Ultron) |
| `PROJECT_LOG.md` logging format | `reality_delta.py` — multi-signal fusion scorer (→ Ultron) |
| `umags/failure_space.py` — pure mechanical path-coverage counter | `delta.py` — change-risk prediction model with learned weights (→ Ultron) |
| `umags/checks.py` — AST scope and diff verification | Any future learned model, calibration engine, or prediction layer |
| `PROTOCOL.md`, `UMAGS.md`, `AGENTS.md` governance documents | |

The moment UMAGS contains something that scores or predicts risk, it has stopped being governance and become an undeclared second product. The three files in the "Does NOT belong" column were built during UMAGS sessions and implicitly filed here — that is corrected as of 2026-06-21. They live in `ROADMAP.md` under ⚠️ Working, not yet validated.

---

## Why this exists

Adversarial review only works if the reviewer can actually see what the Builder can't. Session isolation (separate conversation, no access to the Builder's reasoning trace) buys real independence from one failure mode: the Critic getting talked into agreement by a confident explanation. It does **not** buy independence from a different failure mode: Builder and Critic sharing the same underlying model, and therefore the same default assumptions about what counts as sufficient evidence.

This project has already been burned by that second failure mode four times — a perfect F1 score evaluated on a single mocked data point, a "calibrated" classifier that was never trained on real data, a silently inert git-history feature, an unblinded human-feedback sample of two. None of those were caught by clever adversarial thinking; they were caught by asking a specific, boring factual question and demanding a real answer.

So UMAGS has two layers: the Critic's own hostile judgment (good at code-level bugs), and a fixed checklist it must complete regardless of its own judgment (the only reliable catch for methodological self-deception).

---

## The Four Roles

### 1. Builder
Executes one atomic task from `EXECUTION_PLAN.md`. Reports what it did with real command output, not a summary of intent.

### 2. Auditor Critic
Separate session, no access to Builder's reasoning trace, hostile system prompt. Splits its review into two categories that are handled differently:

**Category A — code-level correctness** (free judgment applies):
cross-platform issues, signature mismatches, untested edge cases, silent exception handling, off-by-one errors. The Critic's adversarial instincts are well-suited to this category as-is.

**Category B — any claim involving a number derived from data** (mechanical checklist applies, no exceptions, regardless of whether the Critic's own judgment would have flagged anything):

For every Category B claim, answer these explicitly and show evidence — not paraphrase, not assume:

1.  **CALIBRATION / PRECISION / RECALL / F1 CLAIMS**
    *   Exact data source and row count ($n$)?
    *   Is the evaluation set disjoint from the training set? Show this, don't assert it.
2.  **HUMAN FEEDBACK / RATING CLAIMS**
    *   Was the score/result hidden from the rater during rating (blinded)?
    *   Number of distinct raters? Number of distinct items rated?
3.  **EXTERNAL DATA DEPENDENCIES (git history, logs, ledgers, config)**
    *   Confirm the data source is non-empty and exists. Show the real count. Do not assume the code path succeeded just because it didn't error.
4.  **MUTATION TESTING / FUZZING CLAIMS**
    *   Was at least one boundary-sensitive case tested (e.g. `>` vs `>=`, off-by-one), not only trivial literal-value substitutions?
5.  **SILENT FAILURE CHECK**
    *   What happens on missing/empty input? Show that output explicitly, not just the happy path.
6.  **CAUSAL / PROBABILISTIC CLAIMS**
    *   Does this claim use causal/probabilistic language (causal, counterfactual, Bayesian, etc.)? If so, name the actual technique being used underneath, and confirm the vocabulary matches the method.

*If any answer is "assumed" or "unknown," the claim is NOT verified.*
*That is the correct answer to log — not a guess to fill the gap with.*

This checklist is a living document — append a new item any time a future audit (internal or external) catches a category of false claim not already covered above.

### 3. Judge
Mechanical only, by design — runs the test suite, reports pass/fail. This role should stay exactly this narrow. The moment "Judge" starts making judgment calls about whether a result is *meaningful*, that responsibility has silently migrated away from the Auditor Critic, where it belongs.

### 4. Historian
Appends an entry to `PROJECT_LOG.md` using the existing template, including the Critic's full Category B checklist answers verbatim — not a summary of them. A summary is exactly the kind of compression that let the original F1=1.00 claim slip through unchallenged.

---

## Verification Rules & Constraints

1.  **External Verification Constraint:** The "External verification" field in `PROJECT_LOG.md` must be left as `PENDING — not yet reviewed by an external party.` by the Builder, Auditor, Judge, and Historian. It may ONLY be filled in by the human operator pasting in an actual external review — it must never be generated, simulated, or pre-filled by any agent in this pipeline, including the Historian.

---

## Where external audit (Claude) fits

External audit sits **after** Judge, and specifically reviews the Category B checklist answers before `ROADMAP.md` status is allowed to change from ⚠️ to ✅. UMAGS reduces how often something false reaches this step — it doesn't remove the step. Treat external audit as the layer that catches shared-blind-spot errors the Critic's checklist didn't anticipate yet; each time that happens, the new check gets added to the Category B list above, so the system actually accumulates judgment over time instead of repeating the same class of miss.

---

## The loop, end to end

```
Builder executes one EXECUTION_PLAN.md task
        ↓
Auditor Critic reviews (Category A: free judgment;
                        Category B: mechanical checklist, no exceptions)
        ↓
Judge runs tests — pass/fail only, no interpretation
        ↓
Historian logs full results (verbatim, not summarized) to PROJECT_LOG.md
        ↓
External audit reviews Category B answers specifically (filling in PENDING status)
        ↓
ROADMAP.md status updated — only after the above, never before
```
