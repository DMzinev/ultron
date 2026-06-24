# What is in this folder

Two projects share this directory.

---

## 1. Cost Accounting Study Portal — **moved**

The interactive cost accounting learning app (`Study_Portal.html`, `cognitive/`,
`domain/`, `controllers/`, `storage/`, `ui/`, `utilities/`, `study_materials/`)
has been extracted to its own repository:

**`cost-accounting-study-app`** (sibling directory on Desktop)

History of all files prior to the split is preserved in the backup at
`cost_accounting_backup_20260623_140859`.

---

## 2. Ultron — Python Risk Scorer

Tells you which files in a Python codebase are risky to change, and why, in plain language.

### Use it right now

```
python ultron/ultron.py --repo <path-to-any-python-repo> --intent "describe what you want to change"
```

Add `--detail` for the underlying numbers (impact score, complexity, coupling count).

### What it actually does (and only this)

Reads a Python codebase, computes cyclomatic complexity and call-graph coupling per file,
combines them into an Impact Score, classifies files as HIGH / MEDIUM / LOW risk,
and outputs one plain sentence per file.

This part works and is validated. See ROADMAP.md for everything that is not yet validated.

### What it does NOT do yet

Several subsystems exist but are not yet validated against real-world defect data:
multi-signal fusion scoring, logistic calibration, design oracle, differential fuzzing.
They are documented in ROADMAP.md as UNVALIDATED. Do not rely on their output.

Human blind ratings (Tasks 4-5 in EXECUTION_PLAN.md) have not been completed yet.
Until they are, the risk tier thresholds are unvalidated heuristics.

### Where to start reading the code

- `SYSTEM_MAP.md` — what every file is and its current status
- `NEXT.md` — the one outstanding technical task
- `ROADMAP.md` — honest status of every feature
- `EXECUTION_PLAN.md` — task history (Tasks 1, 2, 3, 6 DONE; Tasks 4, 5 PARKED)

---

## 3. Synapse — Mutation Testing Engine

`synapse_project/` — generates mutants, runs tests, logs Mutation Kill Rate.
Working on trivial mutations only; boundary-sensitive mutations not yet exercised.
