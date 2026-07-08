# Project Status & Roadmap

Last updated: 2026-07-04

---

## Strategic direction

**Ultron is an AI-assisted software architecture platform.**

It is not a code linter. It is not a static analyzer in the narrow sense. The progression
it is climbing is:

```
Linting → Static Analysis → Code Quality → Architecture Analysis → Architecture Reasoning → Architecture Design
```

Most tools stop at step three. Ultron is entering step five.

Every new feature must answer one question: **Does this help a developer make a better architectural decision?** If not, it belongs in UMAGS or nowhere.

---

## UMAGS is frozen at Kernel v1.0

UMAGS is infrastructure, not a product. It is complete. It provides:

- Scope verification (jurisdiction fraud prevention)
- Programmatic nullification (including new-file deletion mode)
- AST compliance checking
- Residual Risk scoring (R)
- Budget Governor (command caching, poll-depth guard)
- Builder / Auditor / Judge / Historian roles
- Full audit trail in `PROJECT_LOG.md`

**No new UMAGS features will be built unless they remove a confirmed existing weakness.**
Not because they are interesting. Only because they are necessary.
New ideas that would have previously become UMAGS modules should instead become Ultron capabilities.

---

## Ultron development roadmap — five steps

This is the active development frontier. Steps are ordered by dependency: each builds on the previous.

### Step 1 — Architectural Reasoning Layer *(next)*

Extend the Design Oracle output from metric numbers to structured explanations. For every finding, answer four questions:

```
Observation   → What the metric shows
Reason        → Why it is happening structurally
Principle     → Which software engineering principle is affected
Consequences  → What breaks or becomes harder as a result
```

Example — current output:
```
Coupling Debt: 36
```

Example — target output:
```
Observation: High coupling between RiskEngine and VerificationLoop.
Reason: RiskEngine depends on 14 external modules while acting as a central service.
Principle: Stable Dependencies Principle — stable modules should not depend on volatile ones.
Consequences: Difficult unit testing, higher regression probability, reduced replaceability.
```

**Implementation:** A mapping layer (`reasoning.py`) that takes Oracle metrics and traverses a static Knowledge Graph to produce structured explanations. No LLM inference in the reasoning path — the graph decides, the AI communicates.

---

### Step 2 — Knowledge Graph

Formalize the relationships between metrics, architectural smells, violated principles, refactoring candidates, and expected metric effects. The full set of relevant smells is small (~15-20) and the mappings are established in software engineering literature.

```
Metric → Architectural Smell → Violated Principle → Candidate Refactorings → Expected Metric Changes → Implementation Pattern
```

Example edge:
```
High fan-out → High Coupling → Stable Dependencies → Introduce Interface → Coupling −12 → Generate Interface Contract
```

**Every node is deterministic. Every edge is explainable.** This is engineering knowledge, not AI inference. The graph is a curated data structure (JSON or Python), not a learned model.

---

### Step 3 — Recommendation Engine

Use the Knowledge Graph to generate concrete, rule-based architectural improvement proposals. For each violated principle, produce:

```
Violation → Candidate Refactorings → Expected Benefits → Trade-offs
```

Example:
```
Violation: God Object (complexity 212, coupling 31)

Candidate refactorings:
  • Extract Class
  • Facade
  • Split Service
  • Pipeline

Benefits: Complexity ↓, Coupling ↓, Maintainability ↑
Trade-offs: Additional interfaces, more files, possible migration cost
```

Recommendations are ranked by expected metric impact, not by confidence scores. Confidence scores are not produced until real validation data exists.

---

### Step 4 — Impact Simulator

Before issuing an implementation contract, compute what the metrics *would* be after the proposed refactoring. This is deterministic: given a specific proposed decomposition boundary, the analyzer can compute the resulting complexity and coupling on the hypothetical post-refactoring structure.

```
Current: Complexity 212, Coupling 31, Circular Deps 2, Fan-out 28
       ↓ (proposed: extract MetricsEngine + separate IO layer)
Predicted: Complexity 124, Coupling 12, Circular Deps 0, Fan-out 18
```

Two or more candidate decompositions may be simulated in parallel to show trade-offs between boundary choices. The simulator never reports a single answer as the only option when multiple valid boundaries exist.

---

### Step 5 — Implementation Contract Generator

Translate an approved recommendation + simulation into an actionable UMAGS-compatible implementation contract: declared target files, expected outcomes, known limitations, test command. This closes the loop from architectural decision → coding agent → UMAGS verification → re-analysis.

The full pipeline:
```
Repository → Static Analyzer → Metrics Engine → Design Oracle
→ Architectural Reasoning Layer → Knowledge Graph → Recommendation Engine
→ Impact Simulator → Implementation Contract Generator
→ AI Coding Agent → UMAGS Verification Kernel → Re-analysis
```

At this point UMAGS is invisible infrastructure, exactly where it belongs.

---

## Current feature status

### ✅ Working & validated

**Static risk scoring** (`analyzer.py`, `risk/`)
Cyclomatic complexity × ln(e + coupling), scaled by bug-fix history. Impact Score drives HIGH / MEDIUM / LOW tiers. Runs end-to-end on real files; output confirmed correct against known values.

*Gap:* Absolute tier thresholds (10.0 HIGH / 3.0 MEDIUM) are calibrated heuristics, not validated against external defect ground truth. In dense codebases nearly all files exceed 10.0, producing skewed distributions. Percentile-based relative thresholds are the correct long-term fix; blocked on human feedback data.

**Plain-English translation** (`translate.py`)
Converts Impact Score + coupling count into one sentence per file. Working and wired into CLI.

**Context Brief** (`context_brief.py`)
Generates a structured markdown snapshot of the codebase for AI agent orientation. Working and wired into `--brief`.

**UMAGS governance loop** (`umags/`)
Full Builder/Auditor/Judge/Historian loop with budget control, nullification, AST checking. Frozen at Kernel v1.0.

---

### ⚠️ Working, not yet validated

**Design Oracle** (`design_oracle.py`) — wired via `--oracle`
Coupling debt, abstraction leaks, hotspot ranking, circular dependency detection. Produces real output. Not validated against ground-truth defect data. No negative test cases on pathological graphs (self-loops, highly-connected subgraphs).

*Note on Graph Correction:* Discovered and resolved an alphabetical import-mapping collision bug in `get_import_mappings()` where production imports matched to alphabetically prior scratch/test files and broke early. Resolved by symmetrically filtering out `EXCLUDED_PATTERNS` from the codebase keys and introducing a rank-based matching heuristic (Exact=3, Suffix=2, Substring=1) to ensure robust import resolution.

*Simplification:* Uses a module-level `EXCLUDED_PATTERNS` configuration to ignore tests/scratch/experimental directories for abstraction leaks; in Step 5, this should be replaced by dynamic scope-aware metadata checking.

*Next:* Step 1 (Architectural Reasoning Layer) is the planned extension of this output.

**Multi-Signal Risk Fusion** (`reality_delta.py`, `delta.py`)
Six-weight fusion layer combining test, git, runtime, human, and interaction signals. Runs automatically in the verification loop. Calibrated on 109 transactions from this single codebase — not validated against external data, no held-out evaluation set.

**Git-history bug-fix scaling** (`analyzer.py` — `extract_git_history`)
Correctly parses commit history and scales risk scores. Runs without silent failures. Efficacy not validated against real-world defect density.

**MCP server** (`interfaces/mcp_server.py`)
Exposes risk scoring and context brief as tool-callable endpoints. Running. Not battle-tested against diverse client integrations.

**Mutation testing / MKR** (`synapse_project/`)
Generates mutants and logs kill rates. Only tested on trivial literal-substitution mutations. Boundary-sensitive cases (`>` vs `>=`, off-by-one) not exercised.

**CEST / differential fuzzing** (`fuzz.py`)
Behavioral divergence between original and mutant code. Input pool is generic random values, not type-aware or boundary-aware — false equivalence risk on boundary-sensitive mutations.

---

### ⚠️ Requires a design decision before any fix

**Markov / typo audit** (`classifier.py`)
Flags likely misspellings. The false-positive fix for `abspath` / `keys` worked, but the Markov Causal Flow layer now generates ~35 new anomalies at 0.00% probability. Root cause: trained on the same codebase it audits.

Three options — do not implement any without user decision:
- **Option A:** Remove Markov transition layer from production output (keep spelling-similarity only)
- **Option B:** Train on an external Python corpus
- **Option C:** Raise transition-probability threshold to a non-zero value

---

### 🔇 Dormant — working code, not in active use

**Logistic confidence calibration** (`logistic.py`)
Gradient descent math confirmed correct (93.75% F1 on synthetic held-out split). Never trained on real data — `experiment_log.jsonl` has 3 rows; minimum required is 5. All live scores use hardcoded fallback weights. Blocked on human feedback pipeline.

**Human feedback collection** (`human_feedback.jsonl`, `blind_rate.py`)
`blind_rate.py` is built and correct. `blind_feedback.jsonl` is empty. The blinded rating study (Tasks 4-5) is parked awaiting a human rater.

**AI Rater + Compare AI Ratings** (`ai_rater.py`, `compare_ai_ratings.py`)
Syntactically valid, not in any active pipeline. Blocked on human feedback collection.

**Constitutional Sentinel** (`sentinel.py`)
Structural entropy scanner, assumption auditor. Dormant by deliberate decision — gating disabled in verification loop to keep UMAGS lightweight. Do not reactivate without explicit instruction.

---

### 🔇 Silently inert

**`meta_layer.py`, `pledge.py`, `prompt.py`**
Not wired into any active path. No current plan.

---

### 🪦 Documented, not implemented

The following are described in `research-notes/speculative-ideas.md` but have no code anywhere in the repository:

- Vector Scoring Engine (`adaptive_scorer.py`)
- Topological Simulator (`topological_simulator.py`)
- Temporal Drift & Causal Polarity Engine (`temporal_engine.py`)
- Minimax Solver / Control Layer (`intervention_optimizer.py`)
- Structural Decision-Theoretic Controller (`controller.py`)

These are not planned. The manifest is preserved in `research-notes/` with an explicit disclaimer.

---

## What the current release is

Static risk scoring with plain-English output, context brief for AI agent orientation, Design Oracle for coupling and hotspot analysis, and MCP server for tool integration. The governance loop (UMAGS) is the development-time infrastructure that verified every change made to get here.

The next release adds the Architectural Reasoning Layer: structured explanations of why each finding matters, which principles are affected, and what the consequences are. No ML. No confidence scores without validation data. Deterministic and explainable throughout.
