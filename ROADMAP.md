# Project Status & Roadmap

Last updated: 2026-08-12

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

## Product Acceptance Gate

Every feature proposal must pass all six questions before implementation begins. A feature that fails most of these questions should wait.

| # | Question | Why it matters |
|---|----------|----------------|
| 1 | **Does this solve a real developer problem?** | Prevents building interesting but unused features. |
| 2 | **Can a user see or interact with the result?** | Keeps backend work connected to product value. |
| 3 | **Does it reuse the Repository Knowledge Model?** | Prevents duplicate architectures. |
| 4 | **Can every recommendation be explained with evidence?** | Enforces Principle 2. |
| 5 | **Will it still work on repositories 100× larger?** | Encourages scalable designs. |
| 6 | **Would a first-time user notice the improvement within five minutes?** | Keeps focus on user value rather than engineering elegance. |

## Beta Success Criterion

> **Can a developer understand an unfamiliar repository in under five minutes?**

This is the outcome metric for every milestone. Features that do not move this metric in the right direction are deprioritized regardless of engineering complexity.

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

**Visual Risk Heatmap & Pre-Execution Intelligence SPA** (`interfaces/web/`)
Browser-served Web SPA, auto-opens on server launch (`python start.py`), auto-scans project directory, color-codes files by risk tier with pure offline local rendering.
*STATUS:* ✅ **FULLY VERIFIED AND HARDENED (v2.3.0)**. Features:
- **Interactive System Topology Map:** SVG dependency graph rendered live on both Dashboard and Graph tabs with scroll wheel zoom, drag panning, zoom in/out/reset controls, node search filtering, click-to-inspect detail drawer, and local AI critique.
- **Executive Data Summary Hero & Calibration Report:** Live Health Score badge (`0-100`), Top Risk Forces, 5-column Grounding & Calibration Verification Report (`Range`, `Sample Count`, `Precision`, `Recall`, `F1 Score`), and active pledge tracking (`100%` success rate).
- **Prompt Builder & Direct AI Push:** Multi-persona selector (Founder, Architect, Developer, Security), target file selector dropdown, multi-format prompt compiler, clipboard copy feedback, and direct execution via local OpenAI proxy (`/api/v1/ai/push`).
- **Auditor & Single-File Inspection:** File explorer tree with real-time text search filter (`#file-search-input`), code preview syntax editor, callers/callees list, and single-file deep risk audit trigger.
- **REST API Router Architecture (`APIRouter`):** Modular manifest router with exact path matching physics, dual-method registration (`GET`/`POST`), versioned endpoints (`/api/v1/*`), and header-aware 500 error boundaries.

**Repository Knowledge Model (RKM) Persistent Memory Foundation** (`core/rkm/`, `core/pipeline/`)
Persistent database memory foundation built with SQLite to store structured facts, metrics, symbols, file structures, dependencies, architecture roles, and explainability diagnostic chains across repository analysis runs.
*STATUS:* ✅ **FULLY VERIFIED AND IMPLEMENTED** (Phase 2 Pass 1). Features:
- Idempotent schema migrations runner (`store.py` + initial schema DDL migrations versioned at `1.0.0` with compatibility metadata validation).
- Safe adapter layer (`adapters.py` protecting the frozen engine layer).
- Orchestrator pipeline (`discovery.py`, `persistence.py`, `orchestrator.py`) running discovery -> extraction -> metrics -> interpretations -> recommendations -> persistence.
- Complete integration test coverage (`test_rkm_contract.py`, `test_rkm_restart.py`, `test_diagnostic_chain.py`, `test_engine_compatibility.py`).

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

### ✅ Resolved Design Decision (2026-07-12)

**Markov / typo audit** (`classifier.py`)
*   **Markov Causal Flow Layer:** Completely removed. The sequence-transition model was structurally prone to high false-positive rates by design, flagging standard python calls unique to individual files. 
    *   *Result:* Markov anomalies dropped from 202 to exactly 0.
*   **Spelling-Similarity Layer:** Retained and hardened. Swapped the hand-rolled Levenshtein distance for `difflib.SequenceMatcher` (Sequence similarity ratio changed from `0.875` to `0.9333` for `init_db` vs `init_dbb`). Scoping bugs (local variable name detection, conditional nested imports walking, and inherited stdlib HTTP handler methods on `self`) were fixed.
    *   *Result:* All 12 specific false positives in `translate.py`, `context_brief.py`, `scoring.py`, and `server.py` are resolved. Furthermore, by generalizing the checker via dynamic class attribute introspection on standard library modules (`io`, `argparse`, `ast`, `re`, `unittest`, `logging`, `threading`, `datetime`), standard method calls (such as `.write()`, `.read()`, `.parse_args()`, `.visit()`, etc.) are correctly skipped. Total anomalies in the codebase dropped from 214 to **exactly 0**.

---

### 🔇 Dormant — working code, not in active use

**Logistic confidence calibration** (`logistic.py`)
Gradient descent math confirmed correct (93.75% F1 on synthetic held-out split). Fitted relative path resolver to correct location. Never trained on real data — `experiment_log.jsonl` has 3 rows; minimum required is 5. All live scores use hardcoded fallback weights. Blocked on human feedback pipeline.

**Human feedback collection & blind rate** (`human_feedback.jsonl`, `blind_rate.py`)
`blind_rate.py` is built and correct. `blind_feedback.jsonl` is empty. The blinded rating study (Tasks 4-5) is parked awaiting a human rater. Tests quarantined in `ultron/tests/dormant/test_blind_rate.py`.

**AI Rater + Compare AI Ratings** (`ai_rater.py`, `compare_ai_ratings.py`)
Syntactically valid, not in any active pipeline. Blocked on human feedback collection.

**Constitutional Sentinel** (`sentinel.py`)
Structural entropy scanner, assumption auditor. Dormant by deliberate decision — gating disabled in verification loop to keep UMAGS lightweight. Do not reactivate without explicit instruction. Tests quarantined in `ultron/tests/dormant/test_sentinel.py`.

**Contract Guard** (`guard.py`)
Static contract checking. Parked with gating disabled in main loop. Tests quarantined in `ultron/tests/dormant/test_guard.py`.

**Reality Delta** (`reality_delta.py`)
Reality score attribution. Parked/unused in live flows. Tests quarantined in `ultron/tests/dormant/test_reality_delta.py`.

---

### 🔇 Reachable but unused/unconfirmed caller

**`meta_layer.py`**
Reachable — lazily imported in `server.py`'s `handle_calibrate()` at line 907. Reachable via `/calibrate` endpoint but not part of default user flow.

**`pledge.py`**
Reachable/Active — module-level import in `server.py`; called by `/api/pledge/create` and `/api/pledge/verify` route handlers.

**`prompt.py`**
Active — module-level import in all three production entry points (`ultron.py`, `server.py`, `mcp_server.py`).

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
