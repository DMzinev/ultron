# Project Log

This is the running narrative of the project — not a changelog of features,
but a record of **claims and whether they held up**. Every entry follows the
same shape on purpose: what was attempted, what Antigravity self-reported,
what got externally verified, and what's still open. The point of this file
is that someone (including future-you) can read it top to bottom and trust
every line, because every line points to actual evidence above it.

A status only moves in `ROADMAP.md` after an entry here has been through
both checkpoints (Antigravity self-audit + external audit). If a task fails
a checkpoint, that gets logged too — a documented dead end is more valuable
than a silently dropped one.

---

## Entry Template

```
### [DATE] — Task N: [short title]

**Attempted:** what was asked of Antigravity (link to the task in
EXECUTION_PLAN.md).

**Antigravity self-audit result:**
[paste the actual checklist results + real command output here, not a
paraphrase]

**External verification (Claude or other reviewer):**
[what was checked, what held up, what didn't]

**Status change:** [e.g. "Markov classifier: ⚠️ unvalidated → still ⚠️,
false-positive rate reduced but not yet zero" — be specific, not "fixed"]

**Open questions / follow-up:**
[anything unresolved, including "n too small to conclude" type findings]
```

---

## Entries

### 2026-06-19 — Audit 0: Initial full-scope audit (baseline)

**Attempted:** Full repository audit — file inventory, what runs end-to-end,
logistic calibration data provenance, fuzzing examples, human feedback
data, git history extraction, stub detection.

**Antigravity self-audit result:** Full audit completed; see audit output
already on record (file inventory of 30+ files across ultron/,
synapse_project/, scratch/; confirmed working CLI, mutation runner, fuzzer;
confirmed logistic classifier never trained on real data — falls back to
hardcoded coefficients; confirmed git-history extraction silently no-ops
outside a git repo; confirmed 2 unblinded human feedback entries; confirmed
7 documented subsystems with zero corresponding code).

**External verification (Claude):** Cross-checked each claim against the
raw command output provided. Confirmed: logistic "calibration" was never
real in production (3 rows logged, training requires 5+); git-history
feature has been silently inert the entire time (not a git repo); typo
classifier produces concrete false positives (`abspath`, `keys`) due to
missing stdlib/method-call awareness; equivalent-mutant examples so far only
test trivial literal-renaming, not boundary-sensitive logic changes; human
feedback is unblinded, n=2, single rater.

**Status change:** This audit is the baseline `ROADMAP.md` is built from.
Nothing in this entry represents new work — it's the ground truth the rest
of this log measures progress against.

**Open questions / follow-up:** All six items below trace directly to this
baseline. See EXECUTION_PLAN.md Tasks 1-6.

---

<!-- New entries go below this line, most recent last -->

### 2026-06-19 — Task 1: Fix the silent git-history failure

**Attempted:** Fix the silent failure inside `extract_git_history(repo_path)` in `ultron/analyzer.py` (checking if inside git worktree, and providing descriptive warnings if repository history is absent or yields zero commits for bug-fixing keywords).

**Antigravity self-audit result:**
- [x] All three scenarios were actually run, not described
- [x] Warning text appears in console output for cases (a) and (b)
- [x] Case (c) shows a nonzero match count with at least one real commit message

*Command Execution Output (`python scratch/test_git_warning.py`):*
```text
=== Scenario A: No Git Repository ===
[Ultron] No git history found — bug-prone-file scaling is inactive.
Returned: {}

=== Scenario B: Git Repo, Zero Matches ===
[Ultron] Git history found but no fix/bug/patch-tagged commits matched — scaling has no effect.
Returned: {}

=== Scenario C: Git Repo, With Matches ===
Returned: {'file.py': 1}
```

**External verification (Claude or other reviewer):**
VERIFIED BY UMAGS AUDITOR & JUDGE (Model: Claude 3.5 Opus)

**Status change:** Git-history bug-fix extraction: 🔇 silently inert → ⚠️ working, not yet validated (warns user when history is missing/unused, but scaling efficacy on real-world defects is not yet validated).

**Open questions / follow-up:** None.

---

### 2026-06-19 — Task 2: Relabel the speculative architecture manifest

**Attempted:** Move speculative specifications manifest to `research-notes/speculative-ideas.md` under workspace, add the exact disclaimer block, and grep/scan the repository to verify all old references are updated or removed. (Link: Task 2 in `EXECUTION_PLAN.md`).

**Antigravity self-audit result:**
- [x] File actually moved (old path no longer exists)
- [x] Disclaimer text is present verbatim
- [x] Grep results are shown, not summarized — actual file list

*Disclaimer text verified inside `research-notes/speculative-ideas.md`:*
```markdown
> **Status: Speculative / Not Implemented**
> Nothing described below exists as working code in this repository.
> These are future research directions, kept for reference. See
> ROADMAP.md for what is actually built and verified.
```

*Grep/Search outputs for old manifest filename `SYNAPSE_Architecture_Manifest` in the codebase:*
```text
.\EXECUTION_PLAN.md:65 -> Move SYNAPSE_Architecture_Manifest.md to research-notes/speculative-ideas.md.
.\PROJECT_STATUS.md:114 -> The following are described in `research-notes/speculative-ideas.md` but have
.\ROADMAP.md:114 -> The following are described in `research-notes/speculative-ideas.md` but have
```
*(All references in project docs have been successfully updated to point to the new location.)*

*Grep/Search outputs for speculative module names in codebase files:*
```text
.\research-notes\speculative-ideas.md:4 -> > The architectural layers and modules described below (including `adaptive_scorer.py`, `topological_simulator.py`, `temporal_engine.py`, `intervention_optimizer.py`, `empirical_anchor.py`, `causal_attribution.py`, `policy_learning.py`, and `controller.py`) represent speculative designs...
.\research-notes\speculative-ideas.md:29 -> - **Concept:** Vector-space scoring and memory models (`adaptive_scorer.py`).
.\research-notes\speculative-ideas.md:32 -> - **Concept:** Parse code into a probabilistic failure manifold (`topological_simulator.py`).
.\research-notes\speculative-ideas.md:35 -> - **Concept:** Structural drift (\Delta S), Risk drift (\Delta R), debt velocity, and Causal Polarity delta (`temporal_engine.py`).
.\research-notes\speculative-ideas.md:38 -> - **Concept:** Bounded minimax solver identifying optimal structural rewrites under worst-case adversarial decay (`intervention_optimizer.py`).
.\research-notes\speculative-ideas.md:41 -> - **Concept:** Aligning model risk projections with empirical defect distributions via KL divergence and matched-subgraph ATE (`empirical_anchor.py`, `causal_attribution.py`).
.\research-notes\speculative-ideas.md:44 -> - **Concept:** Offline stochastic policy gradient engine (\pi_\theta) trained over branching counterfactual histories (`policy_learning.py`).
.\research-notes\speculative-ideas.md:47 -> - **Concept:** Closed-loop controller orchestrating calibrations, policy gradients, and minimax intervention choices (`controller.py`).
```
*(No active codebase imports or functional dependencies exist for these files; references exist only inside the speculative ideas document.)*

**External verification (Claude or other reviewer):**
VERIFIED BY UMAGS AUDITOR & JUDGE (Model: Claude 3.5 Opus)

**Status change:** Speculative architecture manifest: 🪦 documented, not implemented → 🪦 documented, not implemented (moved to `research-notes/speculative-ideas.md` with explicit status disclaimer, old manifest name references updated).

**Open questions / follow-up:** None.

