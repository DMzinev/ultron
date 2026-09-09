# Ultron System Responsibility Map (Reconciled Phase 0.6 Truth)

**Purpose:** Enforce strict single-responsibility boundaries across the 9 primary subsystems to eliminate layer bypasses, documentation drift, and failure propagation.

---

## 1. Subsystem Architecture Matrix

```text
┌────────────────────────────────────────────────────────────────────────┐
│                              BROWSER / UI                              │
│   UIManager (DOM / SVG)  <───>  StateStore (Single Source of Truth)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (JSON HTTP REST)
┌───────────────────────────────────▼────────────────────────────────────┐
│                        API & ORCHESTRATION LAYER                       │
│           Server (server.py)  <───>  APIRouter (router.py)            │
└──────┬─────────────┬─────────────┬─────────────┬─────────────┬─────────┘
       │             │             │             │             │
┌──────▼──────┐┌─────▼──────┐┌─────▼──────┐┌─────▼──────┐┌─────▼──────┐
│ SystemGraph ││    RKM     ││ Objective  ││    Agent   ││   Safety   │
│  (Analysis  ││  (SQLite   ││  Tracker   ││   Context  ││ Evaluator  │
│   Engine)   ││ Knowledge) ││  (Intent)  ││  (Prompt)  ││ (Readiness)│
└─────────────┘└────────────┘└────────────┘└────────────┘└────────────┘
```

---

## 2. Reconciled Responsibility Contracts

### 1. `SystemGraph` / `Analyzer` ([`ultron/core/analyzer.py`](file:///c:/Users/dimmiz/Desktop/cost%20accounting/ultron/core/analyzer.py), [`ultron/core/pipeline/`](file:///c:/Users/dimmiz/Desktop/cost%20accounting/ultron/core/pipeline))
* **OWNS:** AST traversal, dependency extraction, coupling analysis, cyclomatic complexity calculation.
* **READS:** Workspace source files (`.py`, `.ts`, `.js`, etc.).
* **WRITES:** Extracted factual records (`FileRecord`, `FunctionRecord`, `DependencyEdge`).
* **CALLS:** Language adapters (`PythonAdapter`).
* **MAY NOT OWN:** HTTP serialization, UI state, prompt generation, risk policy thresholds.

### 2. `RKM (Repository Knowledge Model)` ([`ultron/core/rkm/`](file:///c:/Users/dimmiz/Desktop/cost%20accounting/ultron/core/rkm))
* **OWNS:** Historical persistence, schema evolution, SQLite graph storage, policy rulepacks.
* **READS:** Extracted AST facts from `SystemGraph`.
* **WRITES:** SQLite database (`.ultron/repository.db`).
* **CALLS:** SQLite standard library, migration runners.
* **MAY NOT OWN:** Direct HTTP handling, DOM manipulation, active objective state.

### 3. `ObjectiveTracker` ([`ultron/core/objective_tracker.py`](file:///c:/Users/dimmiz/Desktop/cost%20accounting/ultron/core/objective_tracker.py))
* **OWNS:** Human developer intent, active goal, tasks list, milestone status.
* **READS:** `.ultron/objective.json`.
* **WRITES:** `.ultron/objective.json` via atomic `os.replace`.
* **CALLS:** Standard library `json`, `os`, `uuid`, `datetime`.
* **MAY NOT OWN:** Risk scoring, AST analysis, agent prompt formatting, SQLite database transactions.

### 4. `DevelopmentSession` ([`ultron/core/development_session.py`](file:///c:/Users/dimmiz/Desktop/cost%20accounting/ultron/core/development_session.py))
* **OWNS:** Current working session timer, session diffs, in-memory working copy checkpoints.
* **READS:** Git working tree status, active file modifications.
* **WRITES:** Session event records.
* **CALLS:** Git CLI adapter.
* **MAY NOT OWN:** AST generation, UI layout.

### 5. `AgentContextBuilder` ([`ultron/core/agent_context_builder.py`](file:///c:/Users/dimmiz/Desktop/cost%20accounting/ultron/core/agent_context_builder.py))
* **OWNS:** Token-efficient prompt compilation formatted for AI coding agents (Claude, Cursor, AGY, Aider).
* **READS:** `ObjectiveTracker` intent, `SystemGraph` target node AST facts, active risks.
* **WRITES:** Bounded context payloads (`CanonicalAgentContext`).
* **CALLS:** Native synthesis / Local OpenAI proxy (if online).
* **MAY NOT OWN:** Repository graph extraction, database writes, task status mutation.

### 6. `SafetyEvaluator` ([`ultron/core/safety_evaluator.py`](file:///c:/Users/dimmiz/Desktop/cost%20accounting/ultron/core/safety_evaluator.py))
* **OWNS:** Continuation readiness verification (`CONTINUE BUILDING` vs `PAUSE & REVIEW`), boundary constraint checks.
* **READS:** Working tree diffs, test suite results, circular dependency analysis.
* **WRITES:** `ContinuationReadinessReport` envelope.
* **CALLS:** Risk scoring formulas.
* **MAY NOT OWN:** Test execution subprocesses, UI toast rendering.

### 7. `Server` & `APIRouter` ([`ultron/interfaces/server.py`](file:///c:/Users/dimmiz/Desktop/cost%20accounting/ultron/interfaces/server.py), [`ultron/interfaces/api/router.py`](file:///c:/Users/dimmiz/Desktop/cost%20accounting/ultron/interfaces/api/router.py))
* **OWNS:** HTTP request parsing, REST route dispatching, JSON response envelope formatting, CORS headers.
* **READS:** Incoming HTTP request headers & payloads.
* **WRITES:** HTTP status codes and JSON response bodies.
* **CALLS:** Subsystem engines (`SystemGraph`, `ObjectiveTracker`, `SafetyEvaluator`, etc.).
* **MAY NOT OWN:** Domain algorithms (risk scoring logic must reside in `core/risk/`, not in server methods).

### 8. `StateStore` ([`ultron/interfaces/web/modules/state.js`](file:///c:/Users/dimmiz/Desktop/cost%20accounting/ultron/interfaces/web/modules/state.js))
* **OWNS:** Single source of truth for frontend client state (`IDLE`, `ANALYZING`, `READY`, `DEGRADED`, `STALE`, `ERROR`), active repository path, hydrated projection.
* **READS:** API responses from `APIClient`.
* **WRITES:** Local reactive subscriber notifications.
* **CALLS:** `UIManager` render methods.
* **MAY NOT OWN:** Direct backend logic, duplicate detached local state variables.

### 9. `UIManager` ([`ultron/interfaces/web/modules/ui.js`](file:///c:/Users/dimmiz/Desktop/cost%20accounting/ultron/interfaces/web/modules/ui.js), [`graph.js`](file:///c:/Users/dimmiz/Desktop/cost%20accounting/ultron/interfaces/web/modules/graph.js), [`modals.js`](file:///c:/Users/dimmiz/Desktop/cost%20accounting/ultron/interfaces/web/modules/modals.js))
* **OWNS:** DOM element manipulation, SVG Force graph layout, modal visibility, toast alerts.
* **READS:** `StateStore` data.
* **WRITES:** Browser DOM and SVG elements.
* **CALLS:** Native browser APIs (`document`, `window`, `navigator.clipboard`).
* **MAY NOT OWN:** Business logic calculations, backend API route knowledge.

---

## 3. Failure-Containment & Resilience Invariant

> **A failure in one subsystem must not silently corrupt, invalidate, or overwrite valid state belonging to another subsystem.**

1. **Explicit Diagnostics:** Failures must produce structured envelopes (`Result<T, E>`) containing error codes and next-action recovery guidance.
2. **Rejection of Stale State:** If a payload contains a mismatched `snapshot_id` or `repository_id`, `StateStore` must reject the payload rather than render false state.
3. **Preference Hierarchy:**
   $$\text{Valid Data} > \text{Explicit Absence / Degraded} > \text{Stale Data (Rejected)}$$
