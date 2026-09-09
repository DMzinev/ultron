# UI Presentation & Cognitive Ergonomics Audit (Phase 0.5 Step 4: Pillar 3)

**Evaluation Date:** 2026-08-20  
**Design Standard:** **Maximum decision-relevant information per unit of attention. Primary user tasks must be completable without reading documentation.**  
**Status:** **5 / 5 Stages Verified Decision-Useful (100% PASS)**

---

## 1. Tab-by-Tab Cognitive Evaluation

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       ULTRON DEVELOPER SPA STAGES                                      │
├─────────────────┬─────────────────┬─────────────────┬────────────────────────┬─────────────────────────┤
│   1. OVERVIEW   │  2. STRUCTURE   │ 3. WORK & PLAN  │    4. AGENT CONTEXT    │    5. VERIFY & SAFETY   │
│ (Health & KPIs) │ (Force SVG Map) │ (Task Tracking) │  (AI Handoff Presets)  │ (Continuation Readiness)│
└─────────────────┴─────────────────┴─────────────────┴────────────────────────┴─────────────────────────┘
```

---

### Stage 1 — Overview Tab (`#dashboard-tab`)
* **Primary Task:** Assess repository health, identify the top architectural problem, and pick the next action in $<10\text{ seconds}$.
* **5 Core Questions Assessment:**
  1. *What repository am I looking at?* $\rightarrow$ **CLEAR:** Active path displayed prominently in the global top header (`#global-repo`).
  2. *Is it healthy?* $\rightarrow$ **CLEAR:** `#overall-health-score` displays single large composite score (e.g. `82/100`) with color-coded health badge.
  3. *What is the biggest current problem?* $\rightarrow$ **CLEAR:** Hotspots table (`#table-hotspots`) lists top high-risk files ranked by impact score, showing cyclomatic complexity, coupling, and change strategy.
  4. *What am I working on?* $\rightarrow$ **CLEAR:** Overview objective card (`#overview-objective-title`) shows the active goal and progress bar.
  5. *What should I do next?* $\rightarrow$ **CLEAR:** 3 primary action buttons ("Generate Agent Prompt", "Run Safety Audit", "Browse Graph") route directly to relevant tabs.
* **Cognitive Decision Rating:** **PASS** (Zero unnecessary clutter).

---

### Stage 2 — Structure Tab (`#graph-tab`)
* **Primary Task:** Inspect architectural topology, understand blast radius, and view AI recommendations before refactoring.
* **5 Core Questions Assessment:**
  1. *What is this component?* $\rightarrow$ **CLEAR:** Clicking any node in the SVG Force graph opens `#drawer-node-inspector` showing file path, role, and complexity.
  2. *What depends on it?* $\rightarrow$ **CLEAR:** Drawer displays exact caller list and fan-in metric.
  3. *What does it affect?* $\rightarrow$ **CLEAR:** Drawer displays exact dependencies and fan-out metric.
  4. *What can I safely change?* $\rightarrow$ **CLEAR:** Displays deterministic `ChangeStrategy` (e.g. `SAFE_EDIT` vs `REQUIRES_COMPATIBILITY_REVIEW`).
  5. *Can I get AI critique?* $\rightarrow$ **CLEAR:** Clicking "⚡ Explain AI" queries `/api/v1/ai/critique` and renders actionable refactoring advice.
* **Cognitive Decision Rating:** **PASS** (Force layout with node drawer prevents metric overload).

---

### Stage 3 — Work & Plan Tab (`#work-tab`)
* **Primary Task:** Track progressive development milestones, add new tasks, and maintain boundary constraints.
* **5 Core Questions Assessment:**
  1. *What is the active objective?* $\rightarrow$ **CLEAR:** Top card displays editable objective title and description.
  2. *What is the current task?* $\rightarrow$ **CLEAR:** First `in_progress` item is highlighted with progress percentage.
  3. *What is already done?* $\rightarrow$ **CLEAR:** Completed tasks are visually struck-through with completion timestamps.
  4. *What is next?* $\rightarrow$ **CLEAR:** Pending tasks listed below with 1-click status toggles.
  5. *What are the constraints?* $\rightarrow$ **CLEAR:** Boundary constraints card lists forbidden files and invariants.
* **Cognitive Decision Rating:** **PASS** (Clean kanban progression).

---

### Stage 4 — Agent Context Tab (`#prompt-tab`)
* **Primary Task:** Package bounded mission context for external AI coding agents (Claude, Cursor, AGY, Aider) with one-click clipboard copy.
* **5 Core Questions Assessment:**
  1. *What will the AI be told?* $\rightarrow$ **CLEAR:** `#prompt-display` previews the complete Markdown Mission Envelope.
  2. *What files are targeted?* $\rightarrow$ **CLEAR:** Target file signatures and public method contracts are explicitly embedded.
  3. *What must it not touch?* $\rightarrow$ **CLEAR:** Strict implementation checklist and forbidden files list are included.
  4. *How will success be verified?* $\rightarrow$ **CLEAR:** Canonical verification command (`python verify_release.py`) is specified.
  5. *Can I copy it easily?* $\rightarrow$ **CLEAR:** Top "Copy Prompt" button and dedicated CLI quick-connect preset tabs (`agy`, `claude`, `cursor`, `aider`).
* **Cognitive Decision Rating:** **PASS** (Zero prompt-engineering friction).

---

### Stage 5 — Verify & Safety Tab (`#auditor-tab`)
* **Primary Task:** Verify modifications, run test suites, check continuation readiness, and decide whether it is safe to continue building.
* **5 Core Questions Assessment:**
  1. *What changed?* $\rightarrow$ **CLEAR:** Active working tree diff summary displayed.
  2. *Did it work?* $\rightarrow$ **CLEAR:** Run Test Suite button invokes tests and displays real pass/fail counts.
  3. *What failed?* $\rightarrow$ **CLEAR:** Failed tests are isolated with failure reasons in the terminal drawer.
  4. *Can I continue building?* $\rightarrow$ **CLEAR:** Continuation Readiness badge clearly indicates `CONTINUE BUILDING` vs `PAUSE & REVIEW`.
  5. *What should I do if blocked?* $\rightarrow$ **CLEAR:** Diagnostic recommendation cards explain exactly which check failed.
* **Cognitive Decision Rating:** **PASS** (Truthful, non-speculative safety signals).
