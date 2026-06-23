# Execution Plan

Each task below is meant to be run **one at a time**. Don't queue multiple
tasks at once — finish one, log it, verify it, then move to the next. This
is slower but it's the entire point: speed is not the bottleneck here,
unverified claims are.

## How to use this file

For each task:
1. Copy the text inside the `ANTIGRAVITY INSTRUCTION` block exactly, paste
   it into Antigravity, let it run.
2. When it reports done, do NOT take "done" at face value. Make it walk
   through the **Self-Audit Checklist** for that task, with real command
   output — not a summary.
3. Append an entry to `PROJECT_LOG.md` using the template there, pasting in
   what Antigravity actually showed you.
4. Bring that log entry back to Claude. Claude cross-checks it the same way
   the last full audit was done, and tells you whether `ROADMAP.md` status
   should actually change.
5. Only after that — update `ROADMAP.md`.

This is the two-checkpoint loop: Antigravity self-audits against a written
checklist (catches obvious gaps), Claude audits the self-audit (catches the
subtle ones, like synthetic data dressed as real validation).

---

## Task 1 — Fix the silent git-history failure ✅ DONE

**Why first:** it's the cheapest possible fix and it's currently failing
*silently*, which is the worst kind of bug to leave sitting in a trust tool.

```
ANTIGRAVITY INSTRUCTION:
In ultron/analyzer.py, find extract_git_history(repo_path). Currently, if
repo_path is not a git repository, it silently returns an empty dict. Change
this so that:
1. It explicitly checks if repo_path is inside a git repository.
2. If it is NOT, it returns an empty dict AND prints/logs a visible warning:
   "[Ultron] No git history found — bug-prone-file scaling is inactive."
3. If it IS a git repo but the keyword search matches zero commits, it
   prints a different warning: "[Ultron] Git history found but no fix/bug/
   patch-tagged commits matched — scaling has no effect."
Then run it against a real git repo (init one in a scratch folder if needed
with a few dummy commits, some with "fix" in the message) and show the
actual console output for: (a) no git repo, (b) git repo with zero matches,
(c) git repo with matches. Paste all three outputs.
```

**Self-Audit Checklist:**
- [ ] All three scenarios were actually run, not described
- [ ] Warning text appears in console output for cases (a) and (b)
- [ ] Case (c) shows a nonzero match count with at least one real commit message

---

## Task 2 — Relabel the speculative architecture manifest ✅ DONE

**Why second:** also cheap, and it's the single biggest credibility risk if
this repo goes public as-is.

```
ANTIGRAVITY INSTRUCTION:
Move SYNAPSE_Architecture_Manifest.md to research-notes/speculative-ideas.md.
At the very top of the file, add this exact block:

> **Status: Speculative / Not Implemented**
> Nothing described below exists as working code in this repository.
> These are future research directions, kept for reference. See
> ROADMAP.md for what is actually built and verified.

Then grep the entire repo for any remaining references to the old filename
or to the names of the unimplemented modules (adaptive_scorer.py,
topological_simulator.py, temporal_engine.py, intervention_optimizer.py,
empirical_anchor.py, causal_attribution.py, policy_learning.py,
controller.py) in any README, doc, or comment. List every file where a
reference was found and confirm each one was either removed or updated to
point to the new speculative-ideas.md location.
```

**Self-Audit Checklist:**
- [ ] File actually moved (old path no longer exists)
- [ ] Disclaimer text is present verbatim
- [ ] Grep results are shown, not summarized — actual file list

---

## Task 3 — Build a genuinely blinded feedback capture tool ✅ DONE

**Why this is its own task:** the existing dashboard feedback buttons show
the score before asking for a rating, which makes the data useless for
validation. This needs a separate, score-hidden capture path.

```
ANTIGRAVITY INSTRUCTION:
Create a new standalone script, ultron/blind_rate.py, that:
1. Takes a repo path as input.
2. Picks one file at random from that repo that has NOT yet been rated
   (check against existing entries in ultron/meta/blind_feedback.jsonl).
3. Prints ONLY the file's code and, separately, a list of which other files
   call into it (the caller list) — but does NOT print or compute the
   Impact Score, complexity number, or risk tier anywhere in this flow.
4. Prompts the rater for exactly two inputs:
   a. "On a scale of 1-5, how risky does this feel to modify?"
   b. "Would you call this a critical system boundary? (y/n)"
   c. Optional free-text: "Why?"
5. Logs the rating to ultron/meta/blind_feedback.jsonl with fields: file,
   rater_id (free text the rater types once), complexity_rating,
   critical_boundary (bool), reasoning, timestamp. Do NOT log or reference
   the computed risk score anywhere in this file.
6. Confirm by running it twice on two different files, showing the actual
   terminal interaction and the resulting two JSONL lines.
```

**Self-Audit Checklist:**
- [ ] Script genuinely never prints the I/C/K score during the rating flow
      (grep the script's own code to confirm no risk.py import is used
      before the rating is captured)
- [ ] Two real JSONL entries are shown, not just claimed to exist
- [ ] File selection avoids re-rating the same file twice in the same run

---

## Task 4 — Generate a stratified file sample for the blind study [PARKED]

```
ANTIGRAVITY INSTRUCTION:
Run the existing risk scorer across every file in the target repo and
output a CSV with: filename, impact_score, tier (HIGH/MEDIUM/LOW). Then,
WITHOUT revealing this list to the rater, randomly select roughly 5-7 files
from each tier (15-21 total) and save that subset's filenames (only the
filenames, not the scores) to ultron/meta/blind_study_sample.txt. Print the
full scored CSV to a separate, clearly-labeled file
(ultron/meta/blind_study_scores_DO_NOT_LOOK.csv) so it exists for later
comparison but isn't accidentally seen during rating.
```

**Self-Audit Checklist:**
- [ ] Sample file contains only filenames, no scores
- [ ] Roughly even split across tiers is confirmed by count, not estimate
- [ ] The "DO_NOT_LOOK" file is in a clearly separate location from the sample list

> **This is where you (not Antigravity) do the actual rating** — go through
> `blind_study_sample.txt` using `blind_rate.py`, file by file, honestly,
> without peeking at the scores file. This step can't be automated away;
> it's the actual ground-truth collection.

---

## Task 5 — Compare blind ratings against the formula [PARKED]

```
ANTIGRAVITY INSTRUCTION:
Write a script, scratch/analyze_blind_study.py, that:
1. Loads ultron/meta/blind_feedback.jsonl and
   ultron/meta/blind_study_scores_DO_NOT_LOOK.csv.
2. Joins them on filename.
3. Computes the Spearman correlation between impact_score and
   complexity_rating, with the correlation coefficient and p-value.
4. Using critical_boundary as the binary ground-truth label, sweeps impact
   score thresholds from 1.0 to 20.0 in steps of 0.5, and reports which
   threshold maximizes F1 against that label.
5. Prints all of this plainly, plus the raw joined table, so nothing is
   hidden in a summary statistic.
Run it on whatever real blind ratings currently exist, even if the sample is
still small, and report the actual numbers — including if the sample is too
small to draw a real conclusion yet. Say so explicitly if n is too low for
the correlation to be meaningful.
```

**Self-Audit Checklist:**
- [ ] Raw joined table is shown, not just the correlation number
- [ ] Sample size (n) is explicitly stated next to every metric
- [ ] If n is small, the script says so rather than presenting the number as conclusive

---

## Task 6 — Build the plain-language translation layer ✅ DONE

**This is the actual v1 user-facing deliverable.** Only start this once
Task 5 has run at least once — even on a small sample — so the tier cutoffs
being translated aren't pure guesses.

```
ANTIGRAVITY INSTRUCTION:
Create ultron/translate.py with a function plain_language_summary(file_result)
that takes the existing risk.py output for one file and returns:
1. One plain sentence with no jargon, following this pattern:
   - HIGH: "{filename} — High risk to change. {N} other files depend on
     it directly, so changes here can break things elsewhere without warning."
   - MEDIUM: "{filename} — Moderate risk. A few other parts of the project
     rely on this; double check anything that calls it after editing."
   - LOW: "{filename} — Low risk. Nothing else in the project depends on
     this directly — safe to experiment with."
2. A second function, detailed_breakdown(file_result), that returns the
   actual numbers (impact score, complexity, coupling count, formula) for
   anyone who wants to expand past the plain sentence.
Wire this into ultron.py's CLI output so running it normally shows ONLY the
plain sentence per file, with a --detail flag that also shows the numbers.
Run it on three real files (one from each tier) and show both the default
and --detail output for each.
```

**Self-Audit Checklist:**
- [ ] Default output contains zero numbers or technical terms
- [ ] `--detail` output shows the real underlying numbers, not placeholders
- [ ] All three tiers were actually exercised, not just one

---

## Later (not yet scoped into atomic tasks)
- **[Outstanding]** Run `python ultron/interfaces/ultron.py --check-anomaly ultron/core/risk.py` with the updated classifier to confirm the two known false positives (`abspath`, `keys`) no longer appear. This is the real-file confirmation missing from the 2026-06-21 unit-test-only fix.
- Fix the typo-classifier false positives (stdlib + method-call awareness) — *partial fix landed 2026-06-21; real-file confirmation above is still outstanding*
- Test mutation/fuzzing against a boundary-sensitive mutation (`>` vs `>=`),
  not just literal renames
- Package as `pip install`-able CLI
- README rewrite
- **Validate `design_oracle.py` against real defect data** — currently ⚠️, never run against a codebase with known circular-dependency bugs to confirm true-positive rate.
- **Validate `delta.py` / `reality_delta.py` fusion weights** — currently ⚠️, trained with no held-out evaluation set.

These will get broken into the same atomic format once Tasks 1-6 are
verified and the v1 shape is proven out.

---

## Reclassification log

**2026-06-21** — `design_oracle.py`, `reality_delta.py`, `delta.py` were
built during UMAGS-scoped sessions and implicitly filed as governance
infrastructure. They are risk-scoring and prediction code — Ultron's domain,
not UMAGS's. Moved to `ROADMAP.md` under ⚠️ Working, not yet validated.
`umags/failure_space.py` confirmed to stay in UMAGS: its Residual Risk Score
is a pure unweighted integer count (`len(untested_paths) + len(missing_boundary_cases)`),
no learned coefficients, no prediction model.
