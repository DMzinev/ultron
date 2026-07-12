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

## Ultron architectural reasoning pipeline — STATUS: COMPLETE (all 5 steps)

All five steps below were built, verified, and are integrated into the
`--oracle` CLI output. Note: Steps 2-5 were initially built too fast,
without individual approval, in a single unauthorized pass — this was
caught, fully reverted, and a real platform-level cause was found (an
"auto-approve" setting silently bypassing review). See PROJECT_LOG.md's
"Steps 2-5 built without approval" entry for the full incident record.
Each step was then rebuilt correctly, one at a time, with its own
approved plan. What follows is the final, real, verified pipeline.

### Step 1 — Architectural Reasoning Layer: **DONE.**

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

**Implementation:** A mapping layer (`reasoning.py`) that takes Oracle metrics and traverses a static Knowledge Graph to produce structured explanations. No LLM inference in the reasoning path — the graph decides, the AI communicates. Thresholds calibrated against a real distribution (namespace_count > 8 AND complexity > 8, not the originally-proposed >3), after the first version produced 54 violations that were 98% false positives.

---

### Step 2 — Knowledge Graph: **DONE.**

Formalize the relationships between metrics, architectural smells, violated principles, refactoring candidates, and expected metric effects. The full set of relevant smells is small (~15-20) and the mappings are established in software engineering literature.

```
Metric → Architectural Smell → Violated Principle → Candidate Refactorings → Expected Metric Changes → Implementation Pattern
```

Example edge:
```
High fan-out → High Coupling → Stable Dependencies → Introduce Interface → Coupling −12 → Generate Interface Contract
```

**Every node is deterministic. Every edge is explainable.** This is engineering knowledge, not AI inference. The graph is a curated data structure (JSON or Python), not a learned model.
**Implementation:** `knowledge_graph.py`, 6 canonical smell edges, O(1) lookup.

---

### Step 3 — Recommendation Engine: **DONE.**

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
**Implementation:** `recommendation_engine.py`, deterministic severity+filepath sorting.

---

### Step 4 — Impact Simulator: **DONE.**

Before issuing an implementation contract, compute what the metrics *would* be after the proposed refactoring. This is deterministic: given a specific proposed decomposition boundary, the analyzer can compute the resulting complexity and coupling on the hypothetical post-refactoring structure.

```
Current: Complexity 212, Coupling 31, Circular Deps 2, Fan-out 28
       ↓ (proposed: extract MetricsEngine + separate IO layer)
Predicted: Complexity 124, Coupling 12, Circular Deps 0, Fan-out 18
```

Two or more candidate decompositions may be simulated in parallel to show trade-offs between boundary choices. The simulator never reports a single answer as the only option when multiple valid boundaries exist.
**Implementation:** `impact_simulator.py`. Important caveat that must stay attached to this feature permanently: all projected deltas are theoretical best-case numbers assuming every recommendation is applied perfectly and in isolation — NOT a forecast of real outcome. This framing is already correctly baked into the actual rendered report text; keep it there.

---

### Step 5 — Implementation Contract Generator: **DONE**, but only after a real bug was found and fixed: the first version showed the IDENTICAL whole-repo violation count on every single file's card (e.g. "Violations: 20 → 19" repeated 18 times). Fixed to show genuinely per-file numbers. See PROJECT_LOG.md's Task-ContractGeneratorFix entry.

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

**Architectural Reasoning Pipeline** (`reasoning.py`, `knowledge_graph.py`, `recommendation_engine.py`, `impact_simulator.py`, `contract_generator.py`)
Full 5-step pipeline wired into `--oracle`. Deterministic, rule-based throughout — no LLM inference in the reasoning path, no confidence scores. Impact Simulator's projections are explicitly labeled best-case/theoretical in the rendered output, not a real forecast.

**Pip distribution** (`pyproject.toml`)
Ultron packages and installs via `pip install`. Verified: built a real wheel, installed into a fresh virtualenv OUTSIDE the source repo, ran `ultron` / `ultron --brief` / `ultron --oracle` against a separate test repo with real output shown. Zero runtime dependencies except `radon` (pre-existing, now formally declared).

**Visual Risk Heatmap Dashboard** (`interfaces/web/heatmap.*`)
Browser-served dashboard, auto-opens on server launch, auto-scans the launch directory, color-codes files by risk tier. Built with path traversal protection, safe defaults (parser failures → HIGH, never silently LOW), and zero external network calls (no Google Fonts — system font stack only, per the project's local-only guarantee).
*STATUS NOTE:* verification is not fully closed — a screenshot was referenced by local file path rather than actually shown for review. Confirm this is genuinely done by pasting a real screenshot before marking this ✅ instead of ⚠️.

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

**Evidence Engine** (`evidence_engine.py`)
Built (medians, percentiles across codebase metrics), but per a later Ponytail-style dead-code audit, appears to only be imported by its own tests — not actually wired into design_oracle.py's real report generation. Confirm whether integration was simply never finished (worth completing) or whether this was scope that never needed to exist (worth removing) before deciding its fate.

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

A pip-installable local tool (`pip install`, zero network calls) with:
static risk scoring, plain-English translation, a context brief for AI
agent orientation, and a full 5-step architectural reasoning pipeline
(Design Oracle → named principle violations → ranked recommendations →
simulated best-case impact → per-file implementation contracts) exposed
via `--oracle`. A browser-served visual risk heatmap dashboard is also
built (pending final screenshot confirmation). MCP server exposes risk
scoring and context brief as agent-callable tools. UMAGS is the
development-time governance loop that verified every change to get here
— it never ships as part of the package.
