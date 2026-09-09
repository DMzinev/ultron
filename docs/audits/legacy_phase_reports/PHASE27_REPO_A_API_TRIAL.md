# Phase 2.7 — External Reality Trial: Repo A

> **Repository:** `Repo A: bottle (Python Micro-Framework)`
> **Path:** `c:\Users\dimmiz\Desktop\cost accounting\scratch\external\repo_a_bottle`
> **Task Intent:** Identify the most architecturally coupled module and understand its blast radius for safe modification
> **Date:** 2026-08-27
> **Ultron Reachable:** Yes

---

## Ultron Analysis Telemetry

| Metric | Value |
|---|---|
| Analysis Time | 2.07s |
| Files Analyzed | 29 |
| Definitions Found | 169 |
| Risks Identified | 29 |
| Top Risk File | `bottle.py` |
| Hub Correctly Identified | ✓ YES |
| Ground Truth Hub(s) | `bottle.py`, `bottle` |

---

## Comparative Matrix: Control vs Treatment

| Dimension | Control (Raw) | Treatment (Ultron) | Delta |
|---|---:|---:|:---:|
| **Time to Understand** | 180.0s | 32.1s | -82.2% |
| **Context Preparation** | 81.0s | 18.0s | -77.8% |
| **Files Inspected** | 2 | 1 | -50.0% |
| **Unrelated Files Touched** | 1 | 0 | -100.0% |
| **Agent Iterations** | 2 | 1 | -50.0% |
| **Recovery Time** | 54.0s | 24.0s | -55.6% |
| **Human Interventions** | 2 | 1 | -50.0% |
| **Regressions** | 1 | 0 | -100.0% |

---

## Trust Calibration

| Dimension | Result |
|---|---|
| **Verdict** | **PARTIALLY_TRUSTWORTHY** |
| **Calibration Score** | 0.40 |
| **Accurate Claims** | 2 / 5 |
| **Misleading Claims** | 3 |

### Claim-by-Claim Audit
```
  ✓ ACCURATE: bottle.py (score=2415.2) — confirmed coupling hotspot
  ✓ ACCURATE: tools.py (score=71.6) — confirmed coupling hotspot
  ⚠ UNVERIFIED: test_environ.py (score=49.5) — not in top coupling hotspots
  ⚠ UNVERIFIED: test_multipart.py (score=46.8) — not in top coupling hotspots
  ⚠ UNVERIFIED: test_wsgi.py (score=36.4) — not in top coupling hotspots
```
