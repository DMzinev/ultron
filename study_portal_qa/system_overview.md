# System Overview: Innsbruck Cost Accounting Intelligent Tutoring System (ITS)

This document provides a technical and pedagogical blueprint of the Innsbruck Cost Accounting Study Portal, upgraded into an **Intelligent Tutoring System (ITS)**. It details the architecture, technologies, methods, and verification specs to allow other agents to evaluate, maintain, or evolve the system.

## Version
- **Revision:** 7
- **Last Agent:** Claude (second-agent audit & bug fixes)
- **Previous Agent:** Gemini (conversation 818451b5)
- **Date:** 2026-06-10

---

## 1. System Architecture & Tech Stack

*   **Architecture:** Single-Page Application (SPA) structure. The entire portal operates client-side to guarantee zero-latency responsiveness, data persistence, and offline functionality.
*   **Target Entry Point:** [Study_Portal.html](file:///c:/Users/This%20PC/Desktop/cost%20accounting/Study_Portal.html)
*   **Technology Stack:**
    1.  **Structure:** Semantic HTML5.
    2.  **Styling (CSS):** Vanilla CSS3 custom design system with slate/indigo/orange glassmorphic aesthetics, responsive layout grids, and smooth transitions.
    3.  **Core Logic:** Vanilla ES6+ JavaScript.
    4.  **Data Persistence:** LocalStorage (`innsbruck_gamification_stats_v3`).
    5.  **Visualizations:** Inline SVG elements generated dynamically based on randomized problem variables (e.g., CVP graphs, cost matrices, variance analysis maps).

---

## 2. State Schema Reference

### `stats` Object (localStorage)

```javascript
{
    xp: Number,                    // Total experience points earned
    streak: Number,                // Current consecutive correct answers
    totalAttempts: Number,         // Total practice attempts across all topics
    correctAttempts: Number,       // Total correct practice attempts
    masteryConcepts: Number,       // 0-100 mastery % (written by decay formula)
    masteryCosting: Number,        // 0-100 mastery %
    masteryCvp: Number,            // 0-100 mastery %
    masteryAbc: Number,            // 0-100 mastery %
    masteryVariance: Number,       // 0-100 mastery %
    spacedRepQueue: [              // Topics scheduled for review
        { category: String, name: String, dueDate: Number }
    ],
    calibrationStats: {            // Metacognitive confidence tracking
        highConfidenceCorrect: Number,   // conf=3 + correct
        highConfidenceIncorrect: Number, // conf=3 + wrong
        lowConfidenceCorrect: Number,    // conf=1 + correct
        lowConfidenceIncorrect: Number   // conf=1 + wrong
    },
    reflectionStats: {             // Error reflection checkpoint tracking
        reflectionAttempts: Number,
        reflectionCorrect: Number
    },
    consecutiveStats: {            // Per-topic adaptive difficulty state
        [topic]: {
            correct: Number,           // Consecutive correct streak
            incorrect: Number,         // Consecutive incorrect streak
            activeDifficulty: String,  // 'easy' | 'intermediate' | 'hard'
            hintsEnabled: Boolean      // Scaffolding hints on/off
        }
        // Topics: concepts, costing, cvp, abc, variance
    },
    topicStats: {                  // Per-topic performance for decay formula
        [topic]: {
            attempts: Number,
            correct: Number,
            highestDifficulty: Number, // 1=easy, 2=intermediate, 3=hard
            lastAttemptTime: Number    // Date.now() timestamp
        }
        // Topics: concepts, costing, cvp, abc, variance
    },
    mistakesLog: [                 // Most recent diagnosed misconceptions (max 5)
        { title, desc, remedy, explanation, category }
    ]
}
```

### `rsiState` Object (in-memory, rebuilt on load)

```javascript
{
    evolutionTier: Number,     // 1 (Standard), 2 (Adaptive), 3 (Master)
    activeMutations: [String], // Active rule descriptions
    weakestCategory: String,   // 'None' or topic key
    rangeMultiplier: Number    // 1.0 to 1.5 (scales adjustVal)
}
```

> [!IMPORTANT]
> **Category key mapping:** The practice generators use `'fifo'` for process costing problems, but all stat storage uses `'costing'`. The mapping `'fifo' → 'costing'` is applied in `updateTopicPerformance()`, `consecutiveStats` lookups, and `mistakesLog.category`.

---

## 3. Critical Function Index

| Function | Line | Purpose |
|----------|------|---------|
| `loadStats()` | ~L1750 | Loads localStorage, initializes missing fields, calls all UI updaters |
| `saveStats()` | ~L1801 | Persists to localStorage, calls `updateDecayedMastery` and all UI updaters |
| `updateDecayedMastery()` | L1140 | Calculates mastery using `Accuracy × Difficulty × Recency × Repetition` |
| `updateTopicPerformance(topic, isCorrect)` | L1161 | Increments `topicStats`, triggers `updateDecayedMastery` |
| `runRSIDiagnosticScan()` | L1029 | Analyzes `mistakesLog` to determine weakest category and evolution tier |
| `adjustVal(val)` | L1109 | Scales problem parameters by `rsiState.rangeMultiplier` |
| `updateCalibrationHUD()` | L1291 | Renders overconfidence/underconfidence rates and coaching tip |
| `submitRetrievalAnswer()` | L1354 | Processes retrieval pre-test answer via regex matching |
| `confirmRetrievalCheck(isMatch)` | L1387 | Records calibration stats and reveals the practice problem |
| `startPracticeChallenge()` | ~L2815 | Generates a randomized practice problem, reads adaptive difficulty |
| `verifyPracticeAnswer()` | ~L4267 | Checks answers, updates consecutiveStats, calls updateTopicPerformance |
| `diagnosePracticeMistake()` | L3166 | Heuristic misconception detector (12+ patterns) |
| `startExamSimulation()` | L4551 | Generates 5 mixed questions with 15-minute timer |
| `submitExam()` | L4757 | Grades exam, calls updateTopicPerformance per question |
| `getWalkthroughHTML()` | varies | Generates step-by-step worked solution HTML |
| `renderDynamicDiagram()` | varies | Draws SVG diagrams for CVP, variance, cost flow topics |

---

## 4. Advanced Pedagogical Methods (ITS Specs)

The system is designed around core learning science principles rather than superficial gamification:

1.  **Active Retrieval Pre-Test (Retrieval Practice):**
    *   **Method:** Displays a conceptual/formula question before the user sees the calculation problem to prime memory pathways.
    *   **Implementation:** Evaluates answers against key regex patterns (`Match Found` vs. `Review Suggested`) and lets the student self-grade after reviewing the true solution.
    *   **Metacognition:** The user selects their recall confidence (1 = Guessing, 2 = Somewhat Sure, 3 = Very Confident) which is saved to track calibration.
2.  **Memory Decay Tracker (Spaced Repetition):**
    *   **Method:** Predicts information retention based on accuracy, volume, and recency of practice.
    *   **Formula:** $Retained\% = \exp(-\Delta t / \tau)$, where $\Delta t$ is the time elapsed since the last practice attempt, and $\tau$ is the memory half-life parameter (set to 5 days).
    *   **Volume Factor:** Saturation is modeled logarithmically: $Repetition = \min(1.0, 0.2 + 0.8 \times \log_2(attempts + 1)/\log_2(10))$.
    *   **Mastery Formula:** $Mastery = Accuracy \times Difficulty \times Recency \times Repetition \times 100$.
    *   **Single source of truth:** `updateDecayedMastery()` is the sole writer to `stats.mastery*` keys (called from `saveStats()` on every action).
3.  **Prescriptive Study Planner:**
    *   **Method:** Recommends a daily study task based on the Memory Decay Tracker and mastery levels (prioritizing high-decay/low-mastery topics) and provides direct links to practice/exam modes.
4.  **Tutor Reflection Checkpoint:**
    *   **Method:** If a student submits an incorrect answer, the system intercepts the failure state *before* displaying the solution.
    *   **Implementation:** Forces the student to classify their error source (e.g. arithmetic, formula mix-up, rounding, misinterpretation) and write a self-correction note.
    *   **Incentive:** Awards $+2$ XP for completing the reflection checkpoint (versus $+5$ XP for correct retrieval).
5.  **Contextual Misconception Diagnostics:**
    *   **Method:** Uses input signature checks to diagnose *why* a student made a mistake, returning a conceptual explanation:
        *   *Weighted Average vs. FIFO:* Warns when WA equivalent units ($Completed + EWIP$) are entered instead of FIFO.
        *   *DM Price Variance Quantity Base:* Warns if price variance is computed using standard quantity ($SQ$) instead of actual quantity ($AQ$).
        *   *Static Budget Volume Error:* Warns if flexible budget variance uses static budgeted volume instead of actual volume.
        *   *Unrounded Breakeven Point:* Warns when CVP breakeven is entered as a decimal or rounded down.
6.  **Performance-Based Adaptive Difficulty (Faded Scaffolding):**
    *   **Method:** Adjusts difficulty inside the Zone of Proximal Development using `consecutiveStats` per topic.
    *   **Promotion:** After 3 consecutive correct answers in a topic, difficulty upgrades (`easy → intermediate → hard`) and scaffolding hints are disabled.
    *   **Demotion:** After 2 consecutive incorrect answers, difficulty downgrades and hints are re-enabled.
    *   **Implementation:** `startPracticeChallenge()` reads `stats.consecutiveStats[topic].activeDifficulty` to set the problem difficulty. `verifyPracticeAnswer()` updates the consecutive streaks after each attempt.

---

## 5. Cost Accounting Math Specifications

All calculations are verified against Benjamin Falch's seminar slides:

### Session 1: Cost Concepts (Ex 2.11 & 2.15)
*   **Fixed Costs:** Total remains constant regardless of volume; unit cost varies inversely with volume: $Unit\ Cost = Fixed\ Cost / Volume$.
*   **Direct vs. Indirect:** Traced directly to the cost object vs. allocated.

### Session 2: Job & Process Costing (Ex 3.12, 3.13, 4.13)
*   **Overhead Rate:** $Budgeted\ OH\ Rate = Budgeted\ Overhead / Budgeted\ Allocation\ Base$.
*   **Allocated Overhead:** $Actual\ Base\ Used \times Budgeted\ OH\ Rate$.
*   **Over/Under-allocated OH:** $Allocated\ Overhead - Actual\ Overhead\ Incurred$.
*   **FIFO Process Costing (Equivalent Units):**
    *   $EU\ (DM) = Completed + (Ending\ WIP \times \%DM) - (Opening\ WIP \times \%DM)$
    *   $EU\ (Conv) = Completed + (Ending\ WIP \times \%Conv) - (Opening\ WIP \times \%Conv)$

### Session 3: CVP & Bottlenecks (Ex 3.2 & 10.11)
*   **Contribution Margin per Unit (CMU):** $USP - UVC$ (Selling Price - Variable Cost).
*   **Breakeven Point (Units):** $\lceil Fixed\ Cost / CMU \rceil$ (strict integer ceiling).
*   **Operating Profit:** $(Sales\ Volume - Breakeven\ Units) \times CMU$ (or $Volume \times CMU - FC$).
*   **Bottleneck Allocation:** Prioritize products by $Contribution\ Margin\ per\ unit\ of\ bottleneck\ resource$ (e.g. CM per shelf-meter/day, or CM per machine-hour).

### Session 4: Activity-Based Costing (Ex 12.12)
*   **Overhead Rates:** Divided into multiple activity pools (e.g., Setups, Deliveries) using specific cost drivers.
*   **Cost Distortion:** Traditional volume-based allocation over-costs high-volume simple products and under-costs low-volume complex products; ABC corrects this distortion.

### Session 5: Variance Analysis (Ex 15.23 & 5.2)
*   **DM Price Variance:** $(SP - AP) \times AQ$ purchased/used. Positive is Favorable (F), negative is Unfavorable (U).
*   **DM Efficiency Variance:** $(SQ - AQ) \times SP$, where $SQ = actualVol \times stdDM\_qty$.
*   **DL Price Variance:** $(SR - AR) \times AH$.
*   **DL Efficiency Variance:** $(SH - AH) \times SR$.

---

## 6. Verification and Integrity Suite

The portal includes automated verification scripts and a client-side test suite:

1.  **Client-Side System Integrity Check:**
    *   Located in the collapsible Cockpit Panel at the bottom of the Dashboard.
    *   Runs automated assertions for equivalent units formulas, CVP breakeven ceilings, variance sign conventions, local storage state persistence, and RSI range scales.
2.  **Linting & AST Scripts:**
    *   `find_bracket_mismatch.py`: Parses the JavaScript block to identify unclosed brackets, braces, parentheses, or template literal string expressions.
    *   `lint_html_and_ids.py`: Audits HTML tags for well-formed nesting and maps `document.getElementById` calls to static markup IDs.

---

## 7. Known Limitations

1.  **localStorage-only persistence:** All student state is in `localStorage`. Clearing browser data or switching devices resets all progress.
2.  **Single misconception per check:** `diagnosePracticeMistake()` returns the *first* matching heuristic; no multi-diagnosis.
3.  **Confidence calibration tracks extremes only:** Only conf=1 (Guessing) and conf=3 (Very Confident) feed `calibrationStats`. conf=2 (Somewhat Sure) is ignored.
4.  **Difficulty affects numeric scaling, not template selection:** `'easy'`, `'intermediate'`, and `'hard'` scale `adjustVal()` via `rsiState.rangeMultiplier`, but do not change which problem template is selected.
5.  **Exam doesn't use adaptive difficulty:** `startExamSimulation()` always sets difficulty to `'intermediate'` for all 5 questions.

---

## 8. Change Log (Revision 7)

### Bugs Fixed
| Bug | Description | Fix |
|-----|-------------|-----|
| **Adaptive Difficulty Dead Code** | `consecutiveStats` was initialized but never updated after practice | Wired streak tracking into `verifyPracticeAnswer()` (correct → promote after 3, incorrect → demote after 2) |
| **RSI Weakness Targeting Broken** | `mistakesLog` entries had no `.category` field | Added `diag.category = ...` before pushing to log |
| **FIFO → Costing Key Mismatch** | `updateTopicPerformance('fifo')` silently failed because `topicStats` has no `'fifo'` key | Added `if (topic === 'fifo') topic = 'costing'` mapping at function entry |
| **Exam Didn't Feed Mastery** | `submitExam()` never called `updateTopicPerformance()` | Added call inside exam grading loop |
| **Practice Didn't Feed Decay Formula** | `updateTopicPerformance()` was defined but never called from `verifyPracticeAnswer()` | Added call after answer checking |
| **Dual Mastery Writes** | Flat `+10`/`-5` competed with decay formula on same keys | Removed flat `-5` penalty; decay formula via `updateDecayedMastery()` is now sole source of truth for mastery |
