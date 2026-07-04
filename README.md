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

## 2. Ultron — Python Codebase Risk Analyzer

Tells you which files in a Python codebase are risky to change, and why, before you touch them.
Generates structured context for AI agents working on the codebase.

### Quick start

**Score specific files before changing them:**
```
python ultron/interfaces/ultron.py --repo . --files path/to/file.py --intent "describe what you want to change" --detail
```

**Generate a full codebase context brief (for AI agent orientation):**
```
python ultron/interfaces/ultron.py --repo . --brief
```

**Run the Design Oracle (coupling debt, abstraction leaks, architectural hotspots):**
```
python ultron/interfaces/ultron.py --repo . --oracle
```

**Start the MCP server (for IDE / AI tool-call integration):**
```
python start_ultron.py
```

### What it actually does

Reads a Python codebase and produces:

| Output | How |
|---|---|
| Risk tier per file (HIGH / MEDIUM / LOW) | Cyclomatic complexity × ln(e + call-graph coupling), scaled by bug-fix history |
| Plain-English explanation per file | `translate.py` converts the score into one sentence |
| Codebase context brief | `context_brief.py` — structured markdown snapshot of directory, top-risk files, architecture notes |
| Design Oracle report | Coupling debt score, abstraction leaks, hotspot ranking, circular dependency detection |
| MCP tool calls | `mcp_server.py` exposes risk scoring and briefing as tool-callable endpoints |

All five outputs are real and working. The context brief and MCP server were added and validated during this project.

### What is validated vs. unvalidated

**Validated (safe to rely on):**
- Risk tier classification (HIGH / MEDIUM / LOW) — thresholds calibrated against this codebase's own bug history
- Complexity and coupling metrics — deterministic, audited against known values
- Context brief generation — output is accurate and up to date on each run
- Design Oracle coupling and hotspot scores — deterministic static analysis

**Unvalidated (exist, do not rely on):**
- Multi-signal fusion weights (`reality_delta.py`) — calibrated on 109 transactions from a single codebase, not validated against external defect data
- Logistic calibration (`logistic.py`) — implemented but human blind-rating ground truth not yet collected
- Mutation kill rate signal (`fuzz.py`, `synapse_project/`) — working on trivial mutations only; boundary-sensitive mutations not exercised

See `ROADMAP.md` for the honest status of every feature, and `PROJECT_LOG.md` for the full audit trail of every change.

### Where to start reading the code

- `SYSTEM_MAP.md` — every file and its current status
- `ROADMAP.md` — feature-by-feature validation status
- `PROJECT_LOG.md` — full UMAGS audit trail (what changed, why, who reviewed it)
- `ultron/interfaces/ultron.py` — CLI entry point
- `ultron/core/` — risk scoring, complexity, coupling, translate, context brief
- `umags/` — UMAGS governance loop (governor, verification loop, budget governor)

---

## 3. Synapse — Mutation Testing Engine

`synapse_project/` — generates mutants, runs tests, logs Mutation Kill Rate.
Working on trivial mutations only; boundary-sensitive mutations not yet exercised.

