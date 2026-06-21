# NEXT — one action only

This file contains exactly ONE thing to do. When it is done, update this file.
Do not start anything else until this is done.

---

## CURRENT NEXT ACTION

**Confirm the classifier false-positive fix works on a real file.**

The fix to `ultron/classifier.py` (stdlib whitelisting, built-in method detection)
was merged 2026-06-21 with unit tests only. It has NOT been run against an actual
file to confirm the two known false positives are gone.

### The command

```
python ultron/ultron.py --check-anomaly ultron/risk.py
```

Run this from the repo root (`c:\Users\This PC\Desktop\cost accounting`).

### What DONE looks like

The output does NOT flag `abspath` or `keys` as anomalies.
Copy the full terminal output into PROJECT_LOG.md.

### What you do NOT do

- Do not modify classifier.py based on whatever output you see.
- Do not fix any new anomalies that appear.
- Do not update ROADMAP.md until after logging the output.
- Do not start Tasks 4 or 5 — those are blocked on human ratings.
- Do not build anything new.

---

## AFTER THIS IS DONE

Everything remaining is either:

1. **Human-gated** — User must run `blind_rate.py` against the files in
   `ultron/meta/blind_study_sample.txt`, one file at a time, honestly.
   AI cannot do this. Once ratings exist, Tasks 4 and 5 can unblock.

2. **Future validation work** — Documented in ROADMAP.md under UNVALIDATED.
   None of it should be started until the blind study has real data.

3. **Nothing** — The v1 deliverable (plain-language risk output) is complete.
   It can be used right now with `python ultron/ultron.py --repo <path> --intent <description>`.

---

## HOW TO USE ULTRON RIGHT NOW

```
python ultron/ultron.py --repo <path-to-any-python-repo> --intent "describe what you want to change"
```

With detail:
```
python ultron/ultron.py --repo <path> --intent "your intent" --detail
```

That is the product. It works. It is not perfect. See ROADMAP.md for what the gaps are.
