# NEXT — one action only

This file contains exactly ONE thing to do. When it is done, update this file.
Do not start anything else until this is done.

---

## CURRENT NEXT ACTION

**Human must do the blind ratings.**

Everything that can be done by an AI is done. The one remaining technical
gap (classifier Markov false positives) is documented below as a known
architectural flaw — it requires a design decision, not a quick fix.

The only thing that unblocks the project is:

> Open a terminal. Run:
> ```
> python ultron/validation/blind_rate.py .
> ```
> Rate each file in `ultron/meta/blind_study_sample.txt` honestly.
> That file has ~15 filenames. Run the command once per file.
> Use your own judgment. Do not ask the AI to help rate.

Once you have ~15 real ratings in `ultron/meta/blind_feedback.jsonl`,
come back and say "ratings done" — then Tasks 4 and 5 can run.

---

## KNOWN OPEN ISSUES (not blocking, documented)

### Classifier Markov anomaly detector — architectural flaw

Real-file run confirmed 2026-06-21: `--check-anomaly` on `risk.py` produced
36 "Markov Causal Flow Anomaly" warnings, all with 0.00% probability. This
is not a bug fix failure — it is the expected output of a Markov model that:
- Is trained on the same codebase it audits (circular: your own code is the training set)
- Has a threshold of 0.0% (flags every transition that never appeared during training)
- Has a tiny training corpus (this repo has ~15 Python files)

The original two false positives (`abspath`, `keys`) are not visible in the
output — they are gone. But the Markov layer is generating ~35 new false positives
of a different kind.

**Fix requires a design decision, not a code tweak:**
Either (a) remove the Markov layer from production output entirely, or
(b) train on a larger external corpus, or (c) raise the threshold significantly.
This is a roadmap-level question. Do not ask an AI to pick one and implement it
autonomously — that is how scope creep happens.

### Logistic calibration weights
Still on hardcoded fallback. Will remain that way until blind study data exists.

---

## HOW TO USE ULTRON RIGHT NOW

```
python ultron/ultron.py --repo <path-to-any-python-repo> --intent "describe what you want to change"
```

With detail:
```
python ultron/ultron.py --repo <path> --intent "your intent" --detail
```

That is v1. It works. It is not perfect. See ROADMAP.md for what the gaps are.
