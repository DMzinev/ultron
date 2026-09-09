# Ultron Phase 2.7 — Adversarial Secondary Ranking & Trust Calibration Audit

> **Target:** Evaluating the 4 core product questions on secondary ranking and trust calibration across the 3 external repositories ([bottle](https://github.com/bottlepy/bottle), [httpie](https://github.com/httpie/cli), [requests](https://github.com/psf/requests)).
> **Date:** 2026-08-27
> **Evaluator:** Antigravity (Adversarial Engineering Lens)

---

## 1. Empirical Top-5 Ranking Across External Repositories

Using the live RKM engine (`/api/v1/analyze`) with impact-score sorting:

### Repo A: `bottle` (Single-File Monolith, 4,585 lines, 29 files)

| Rank | File | Impact Score | Coupling | Complexity | Callers | Classified Role |
|:---:|---|---:|---:|---:|---:|---|
| **#1** | `bottle.py` | **2,415.2** | 25 | 727 | 25 | `INTERNAL` |
| **#2** | `test/tools.py` | **71.6** | 13 | 26 | 13 | `INTERNAL` (Test Helper) |
| **#3** | `test/test_environ.py` | **49.5** | 4 | 26 | 4 | `TEST` |
| **#4** | `test/test_multipart.py` | **46.8** | 9 | 19 | 9 | `TEST` |
| **#5** | `test/test_wsgi.py` | **36.4** | 7 | 16 | 7 | `TEST` |

### Repo B: `httpie` (Multi-Package CLI, 86 files)

| Rank | File | Impact Score | Coupling | Complexity | Callers | Classified Role |
|:---:|---|---:|---:|---:|---:|---|
| **#1** | `httpie/cli/argparser.py` | **331.0** | 16 | 113 | 16 | `CLI` |
| **#2** | `httpie/manager/tasks/plugins.py` | **140.5** | 20 | 45 | 20 | `INTERNAL` |
| **#3** | `httpie/downloads.py` | **128.9** | 16 | 44 | 16 | `INTERNAL` |
| **#4** | `httpie/core.py` | **101.1** | 3 | 58 | 3 | `INTERNAL` |
| **#5** | `httpie/utils.py` | **98.7** | 36 | 27 | 36 | `INTERNAL` |

### Repo C: `requests` (Coupling Chain, 20 files)

| Rank | File | Impact Score | Coupling | Complexity | Callers | Classified Role |
|:---:|---|---:|---:|---:|---:|---|
| **#1** | `src/requests/models.py` | **366.1** | 7 | 161 | 7 | `INTERNAL` |
| **#2** | `src/requests/utils.py` | **337.2** | 4 | 177 | 4 | `INTERNAL` |
| **#3** | `src/requests/sessions.py` | **194.4** | 9 | 79 | 9 | `INTERNAL` |
| **#4** | `src/requests/cookies.py` | **183.1** | 10 | 72 | 10 | `INTERNAL` |
| **#5** | `src/requests/adapters.py` | **132.1** | 6 | 61 | 6 | `INTERNAL` |

---

## 2. Adversarial Evaluation of the 4 Core Questions

### Question 1: Can Ultron identify the right problem?
*Verdict:* **YES for Multi-Package Repos; TRIVIAL for Monoliths.**
- In `requests`: `models.py` defines `Request`, `Response`, and `PreparedRequest` — the canonical currency passed through the entire library. It is indeed the primary architectural hub.
- In `httpie`: `argparser.py` is the entry point that parses command-line flags and determines which plugin, session, or dispatch routine executes.
- In `bottle`: `bottle.py` is #1, but trivially so because it is the **only** non-test Python file in the repository. On a monolith, repository-level file ranking is insufficient; intra-file structural localization (which class/function within `bottle.py`) is required.

---

### Question 2: Can Ultron distinguish "important" from merely "complex"?
*Verdict:* **PARTIAL — CC Inflation Defect Identified.**
- **The Defect:** Ultron calculates impact as `complexity * log(e + coupling)`.
- **The Evidence:**
  In `requests`:
  - `utils.py` has **Complexity = 177**, **Coupling = 4** $\rightarrow$ Impact = **337.2** (#2)
  - `sessions.py` has **Complexity = 79**, **Coupling = 9** $\rightarrow$ Impact = **194.4** (#3)
- **The Architectural Reality:** `sessions.py` is the operational heart of `requests` (managing HTTP sessions, connection adapters, cookie persistence, and redirects). `utils.py` is merely a utility drawer of string and URL helpers with many `if/elif` branches.
- **Root Cause:** The formula gives linear weight to Cyclomatic Complexity (`comp`), while coupling is compressed logarithmically (`log(e + coup)`). Consequently, a messy utility file with many branches outranks a cleaner, higher-consequence operational engine.

---

### Question 3: Can it explain *why* the recommendation is important?
*Verdict:* **WEAK in Backend API; IMPROVED in Frontend Overview.**
- **What the API Emits Today:**
  > `"High risk implementation. Impact Score: 366.12 (Threshold: 8.50, Complexity: 161, Coupling: 7)."`
- **Why This Fails a Developer:**
  A developer does not care about "Threshold 8.50" or an arbitrary composite score of 366.12. Those are engine internals.
- **What the Developer Needs to Know:**
  > `"src/requests/models.py defines core Request/Response structures. Modifying this affects 7 downstream modules including sessions.py, adapters.py, and api.py. Any change risks breaking response handling across all HTTP requests."`
- The Phase 2.5 frontend card (*What Matters Decision Surface*) started doing this translation, but the underlying API packet still emits formula numbers rather than plain-English architectural consequence.

---

### Question 4: Can it rank the next 3–5 actions sensibly?
*Verdict:* **MIXED — Strong on Layered Libraries, Broken on Monoliths with Tests.**
- **On Layered Repos (`requests`, `httpie`):** Ranks 2–5 are all genuine, high-importance subsystems (`sessions`, `cookies`, `adapters` in requests; `plugins`, `downloads`, `core` in httpie). While `utils.py` is slightly over-ranked due to CC inflation, all 5 are real code modules.
- **On Monoliths (`bottle`):** Ranks 2–5 are all **test files** (`test/tools.py`, `test_environ.py`, `test_multipart.py`). To a developer trying to fix a bug in `bottle`, ranking test suites as "risky code modules to modify" is confusing and misleading. Test suites should be recognized as verification suites that *validate* changes, not targets for refactoring.

---

## 3. Concrete Recommendations for Pre-V1 Refinement

1. **Re-weight Impact Score (Downweight CC, Upweight Consequence):**
   - Shift from `comp * log(e + coup)` to a formula where coupling and downstream call reach dominate: e.g., `coup * log(e + comp)`. An architecturally coupled file with low CC is more dangerous than an isolated utility file with high CC.
2. **Filter Test Suites from Production Risk Recommendations:**
   - Files classified as `ArchitecturalRole.TEST` should be presented in a separate "Verification Coverage" section rather than competing with production source code in the Risk Matrix.
3. **Ground Explanations in Callers, Not Formulas:**
   - Replace `"Impact Score: 366.12 (Threshold: 8.50)"` with: `"Coupled to N downstream files: [caller_1, caller_2]. Modifying this changes behavior across [subsystem]."`
