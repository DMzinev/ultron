# SYSTEM MAP
## Read this before any other file. This is the ground truth.

---

## What lives in this folder

Two unrelated things share this directory. Do not mix them up.

### 1. Cost Accounting Study Portal (JavaScript)
An interactive learning app. Nothing to do with Ultron or UMAGS.
**Do not touch these files unless the user asks about the study portal specifically.**

| File / Directory | What it is |
|---|---|
| `Study_Portal.html` | The app entry point |
| `cognitive/` | JS learning engines (belief, mastery, scaffolding, etc.) |
| `domain/` | Problem sets (ABC, CVP, costing, variance) |
| `controllers/` | Answer verification, practice session logic |
| `storage/` | Knowledge base, stats store |
| `ui/` | App UI, QA stress tester |

---

### 2. Ultron + UMAGS + Synapse (Python)
The risk-scoring / governance / mutation testing system.

---

## ULTRON — the product

**What it does:** Given a codebase, tells you which files are risky to change and why, in plain language.

| File | Status |
|---|---|
| `ultron/core/analyzer.py` | DONE — parses AST, call graph, git history |
| `ultron/core/risk.py` | DONE — Impact Score, HIGH/MEDIUM/LOW tiers |
| `ultron/core/translate.py` | DONE — plain English output, --detail flag (Task 6) |
| `ultron/interfaces/ultron.py` | DONE — CLI entry point |
| `ultron/core/classifier.py` | FIX UNCONFIRMED — stdlib false-positive fix landed but not tested on real files yet |
| `ultron/validation/blind_rate.py` | DONE — score-hidden human rating tool (Task 3) |
| `ultron/core/logistic.py` | UNVALIDATED — falls back to hardcoded weights (not enough real data) |
| `ultron/core/fuzz.py` | UNVALIDATED — random input pool, not boundary-aware |
| `ultron/core/predict.py` | UNVALIDATED |
| `ultron/core/guard.py` | UNVALIDATED |
| `ultron/experimental/design_oracle.py` | UNVALIDATED — reclassified from UMAGS 2026-06-21 |
| `ultron/experimental/reality_delta.py` | UNVALIDATED — reclassified from UMAGS 2026-06-21 |
| `ultron/experimental/delta.py` | UNVALIDATED — reclassified from UMAGS 2026-06-21 |
| `ultron/core/models.py` | STABLE — AnalysisPacket dataclass |
| `ultron/interfaces/server.py` | WORKING — HTTP API |
| `ultron/tests/run_tests.py` | 19 tests passing |

### ultron/meta/ — runtime data files

| File | State |
|---|---|
| `blind_feedback.jsonl` | EMPTY — no real human ratings yet |
| `blind_feedback_INVALID_self_rated.jsonl` | QUARANTINED — do not use |
| `blind_study_sample.txt` | Ready — waiting on human to do ratings |
| `blind_study_scores_DO_NOT_LOOK.csv` | Do not open until after rating |
| `human_feedback.jsonl` | 2 unblinded entries — not usable for validation |
| `experiment_log.jsonl` | Large (188KB) — all logged experiments |
| `fusion_weights.json` | No held-out split — not validated |
| `logistic_weights.json` | Hardcoded fallback — not enough real data |

---

## UMAGS — governance process only (not a product)

Contains NO risk-scoring code. The moment it does, it has become an undeclared second product.

| File | What it does |
|---|---|
| `UMAGS.md` | Protocol definition, scope table |
| `PROTOCOL.md` | Moment-to-moment rules |
| `umags/checks.py` | AST scope and diff verification |
| `umags/failure_space.py` | Pure counter: untested paths + missing boundaries = R |
| `umags/governor.py` | Compiles audit evidence |
| `umags/run_verification_loop.py` | Runs the B/A/J/H loop |
| `umags/tools/analyze_blind_study.py` | Spearman correlation calculation for study |
| `umags/tools/run_stratified_sampling.py` | Generates stratified samples for study |
| `umags/tools/compare_ai_ratings.py` | Compares AI ratings against formula |
| `ROADMAP.md` | Feature status (DONE / UNVALIDATED / INERT / SPECULATIVE) |
| `EXECUTION_PLAN.md` | Atomic task list with done/parked status |
| `PROJECT_LOG.md` | Claim-and-evidence log |

---

## SYNAPSE — mutation testing engine (largely untouched)

`synapse_project/` — mutation runner, ledger, demo target.

---

## WHAT IS DONE vs WHAT IS NOT

### DONE — do not redo these
- Task 1: git-history silent failure fixed
- Task 2: speculative manifest moved with disclaimer
- Task 3: `ultron/validation/blind_rate.py` built (score-hidden)
- Task 6: translate.py built, wired into CLI
- Reclassification: design_oracle, reality_delta, delta moved into Ultron ROADMAP

### ONE TECHNICAL TASK OUTSTANDING (AI can do this)
See NEXT.md — one command, nothing else.

### BLOCKED ON HUMAN INPUT — AI cannot do these
- Tasks 4 & 5: Human must run `ultron/validation/blind_rate.py` and actually rate files
- Logistic calibration: needs real feedback data (currently 0 valid entries)

### SPECULATIVE — no code exists, do not build
adaptive_scorer.py, topological_simulator.py, temporal_engine.py,
intervention_optimizer.py, controller.py
See research-notes/speculative-ideas.md

---

## SCRATCH — disposable scripts

scratch/ contains one-off diagnostic scripts. Most are safe to ignore.
ONE DANGEROUS FILE: DO_NOT_RUN_simulates_human_input.py — quarantined, never run.
