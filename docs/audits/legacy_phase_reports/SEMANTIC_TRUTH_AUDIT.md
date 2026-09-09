# Ultron Semantic Truth & Product Coherence Audit (Phase 0.7)

**Core System Invariant:**  
> **"Ultron must never convert absence of evidence into evidence of absence."**

---

## 1. The Three Orthogonal Semantic Axes

To prevent overloaded enums and conceptual confusion, system state is governed by three independent axes:

```text
┌───────────────────────────────────────┬───────────────────────────────────────┬───────────────────────────────────────┐
│     1. EVIDENCE AVAILABILITY          │           2. METRIC STATE             │        3. RUNTIME / APP STATE         │
│ (Are external data sources online?)   │ (How was this specific value derived?)│  (What is the overall system status?) │
├───────────────────────────────────────┼───────────────────────────────────────┼───────────────────────────────────────┤
│ • FULL (AST + Git + AI Proxy)         │ • OBSERVED (Direct raw extraction)    │ • READY (All operations valid)        │
│ • REDUCED (AST + Git, AI Offline)     │ • DERIVED (Deterministic formula)     │ • PARTIAL (Some parse errors present) │
│ • UNAVAILABLE (Data source missing)   │ • ESTIMATED (Heuristic extrapolation) │ • DEGRADED (Optional source offline)  │
│                                       │ • UNKNOWN (Check unexecuted)          │ • STALE (Mismatched snapshot rejected)│
│                                       │ • UNAVAILABLE (Engine offline)        │ • BLOCKED (Safety conditions tripped) │
│                                       │ • NOT_APPLICABLE (Not relevant)       │ • ERROR (Fatal failure)               │
└───────────────────────────────────────┴───────────────────────────────────────┴───────────────────────────────────────┘
```

---

## 2. Metric-by-Metric Semantic Truth Table

| UI Fact / Metric | Authoritative Engine | Metric State | Valid Condition | Missing / Offline Fallback State | Strictly Prohibited Falsehood |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **System Health** (`#overall-health-score`) | `scoring.py -> evaluate_risks()` | `DERIVED` | $\ge 1$ parsed AST module. | Displays score on **analyzed modules only**; if 0 files, `UNAVAILABLE`. | Never display 100/100 as "complete repository healthy" when parse errors exist. |
| **Analysis Completeness** (`#analysis-completeness`) | `orchestrator.py / discovery.py` | `OBSERVED` | `files_parsed / files_discovered`. | Displays percentage (e.g. `99% PARTIAL (1 Parse Error)`). | Never display `100% Complete` when files have syntax failures. |
| **Risk Hotspots** (`#table-hotspots`) | `scoring.py -> AnalysisPacket` | `DERIVED` | McCabe & coupling computed. | Renders `"Risk analysis unavailable"`. | Never display `0 High Risks` when risk engine is offline. |
| **Git Churn Weighting** | `git_adapter.py` | `OBSERVED` | Git repository initialized. | Renders `EVIDENCE: AST ONLY (Git Churn Inactive)`. | Never display `0 churn` as if the repo has zero historical bugs. |
| **AI Node Critique** (`#drawer-ai-content`) | `ai/client.py` | `DERIVED` (Fallback) | Local proxy on port 10531. | Renders `ULTRON NATIVE AST SYNTHESIS (OFFLINE FALLBACK)`. | Never format fallback text as if it were returned by an external LLM. |
| **Continuation Readiness** (`#continuation-readiness-badge`)| `safety_evaluator.py` | `UNKNOWN` (If no tests) | Test results executed & diff bound. | `PAUSE & REVIEW` with reason `TESTS_UNEXECUTED`. | **NEVER** return `CONTINUE BUILDING` on missing test results. |
| **Objective Progress** (`#work-progress-bar`) | `objective_tracker.py` | `DERIVED` | Valid tasks array in storage. | Reset to default clean state; `0.0%` with recovery notice. | Never corrupt `.ultron/objective.json` or display NaN. |

---

## 3. Four Decoupled Dashboard Dimensions

When presenting repository state to a developer, the UI guarantees four independent signals:

```text
┌──────────────────────────────────┬──────────────────────────────────┐
│ 1. ANALYSIS STATUS               │ 2. SYSTEM HEALTH                 │
│ PARTIAL — 99% (1 Parse Error)    │ 100/100 (On Analyzed Code)       │
├──────────────────────────────────┼──────────────────────────────────┤
│ 3. EVIDENCE LEVEL                │ 4. CONTINUATION READINESS        │
│ AST + Git (AI Proxy Offline)     │ PAUSE & REVIEW (Tests Unexecuted)│
└──────────────────────────────────┴──────────────────────────────────┘
```

**Dominance Rule:** When `Completeness < 100%` or `Readiness == PAUSE & REVIEW`, the status badges visually dominate over the raw numeric health score.
