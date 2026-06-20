# Project Status & Roadmap

## Why this document exists

It's easy for an AI-assisted project to accumulate features that *run* without
being *true* — code that executes cleanly but doesn't yet measure what it
claims to measure. This document is an honest accounting of where every
feature actually stands, based on a direct code-and-output audit (not on
prior summaries or test-pass messages).

Status is split into four categories:

- ✅ **Working & validated** — runs end-to-end, and there's real evidence it
  measures the right thing.
- ⚠️ **Working, not yet validated** — runs end-to-end, produces output, but
  no one has checked whether that output is *correct* against real-world
  ground truth.
- 🔇 **Silently inert** — runs without error, but is currently doing nothing
  useful, with no warning to the user.
- 🪦 **Documented, not implemented** — described somewhere in the repo's docs,
  but no code exists for it.

---

## ✅ Working & validated

### Static risk scoring (`analyzer.py`, `risk.py`)
Computes cyclomatic complexity and call-graph coupling, combines them into an
Impact Score, and classifies files into HIGH / MEDIUM / LOW risk tiers. This
runs end-to-end on real files and produces a coherent, inspectable output
(confirmed against `risk.py` itself: Impact Score 83.79, 5 callers correctly
identified).

**Not yet done:** the *cutoff values* (10.0 / 3.0) and the formula's
coefficients are still inherited defaults, not calibrated against human
judgment. This is the planned Phase 1 study — blinded ratings across a
stratified file sample. Until that happens, treat this as "a reasonable,
working heuristic," not "a validated measure of risk."

---

## ⚠️ Working, not yet validated

### Git-history bug-fix extraction (`extract_git_history`)
**Confirmed:** the feature runs and correctly parses commit history. If the repo is missing or contains zero matches, it outputs clear warnings rather than failing silently.

**Gap:** the efficacy of using bug-fix commit frequency to scale static risk warnings is not yet validated against real-world defect density.

### Mutation testing / Mutation Kill Rate (`synapse_mutator/run.py`)
Generates mutants, runs the real test suite against them, logs results to
`ledger.jsonl`. This genuinely works on real code (`demo_target/math_ops.py`
confirmed).

**Gap:** only tested so far on a trivial, literal-substitution mutation
(`1.15` → a renamed constant of the same value). This is closer to a
no-op than a real behavior change. The mutation types that actually matter
for catching weak tests — flipped comparisons, off-by-one boundaries, swapped
operands — haven't been exercised yet.

### CEST / differential fuzzing (`fuzz.py`)
Computes behavioral divergence between original and mutated code by running
both against a pool of randomly sampled inputs.

**Gap:** input generation is random sampling from a fixed pool of generic
values (`0, 1, -1, "", [], {}`, etc.), not type-aware or boundary-aware. This
means a mutant can be mislabeled "semantically equivalent" simply because the
random inputs never landed near the value where the behavior actually
diverges — false equivalence, not true equivalence. All three logged examples
so far are trivial refactors; none test a boundary-sensitive case like
`>` vs `>=`.

### Markov / typo audit (`classifier.py`)
Flags identifiers that look like likely misspellings of names used elsewhere
in the codebase.

**Gap, confirmed by direct testing:** it has no model of standard-library or
imported names, and doesn't distinguish method calls from global functions.
Running it on `risk.py` produced two confirmed false positives — flagging
`abspath` (a real `os.path` function) as a typo of an internal `abs_path`,
and flagging `keys` (almost certainly `dict.keys()`) as a typo of `key`. The
underlying idea may still be useful, but the current false-positive rate
makes it noisy rather than trustworthy as-is.

### Logistic confidence calibration (`logistic.py`)
**Status, confirmed by audit:** in production, this has never actually
trained on real data. `experiment_log.jsonl` as 3 rows; the training code
requires at least 5 before running. Every "calibrated" score currently in
use is the hardcoded fallback (`beta_0=-1.0, beta_1=0.1, beta_2=0.5`), not a
learned value.

A synthetic 100-record train/test split *does* confirm the gradient descent
math itself is implemented correctly (93.75% F1 on a genuinely held-out
split) — so the code is sound. What's missing is real data to train it on.
This is blocked on the same human-feedback pipeline as risk scoring.

---

## 🔇 Silently inert


### Human feedback collection (`human_feedback.jsonl`)
**Confirmed:** 2 entries, covering 1 file, no rater identity tracked, no
blinding — the risk score is visible before the rating is given. This isn't
broken, but it's not yet data; it's a UI control waiting for an actual
study to use it properly (see Phase 1 plan).

---

## 🪦 Documented, not implemented

The following are described in `research-notes/speculative-ideas.md` but have
**no corresponding code anywhere in the repository**:

- Vector Scoring Engine (`adaptive_scorer.py`)
- Topological Simulator (`topological_simulator.py`)
- Temporal Drift & Causal Polarity Engine (`temporal_engine.py`)
- Minimax Solver / Control Layer (`intervention_optimizer.py`)
- Empirical Anchoring & Causal Attribution (`empirical_anchor.py`, `causal_attribution.py`)
- Counterfactual Simulation / Policy Gradient (`policy_learning.py`)
- Structural Decision-Theoretic Controller (`controller.py`)

**Decision:** these are interesting future directions, not current
features. The manifest describing them has been moved to
`research-notes/speculative-ideas.md` with an explicit disclaimer, so it's
clear to anyone reading the repo that nothing in that document is live code.

---

## What v1 actually ships

Given the above, the first public release is scoped deliberately small:

1. Static risk scoring, translated into plain language (no jargon required
   to read the output; technical detail available on click-through).
2. An honest "what this doesn't do yet" section in the main README, linking
   here.
3. Everything in the ⚠️ and 🔇 sections above stays out of the default
   pipeline until it has real validation behind it.

The goal isn't to hide unfinished work — it's to be precise about which
claims are earned and which are still open questions. That precision is the
actual point of the project.
