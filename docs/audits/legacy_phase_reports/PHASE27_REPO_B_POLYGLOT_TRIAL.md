# Phase 2.7 — External Reality Trial: Repo B

> **Repository:** `Repo B: httpie (Python CLI Application)`
> **Path:** `c:\Users\dimmiz\Desktop\cost accounting\scratch\external\repo_b_httpie`
> **Task Intent:** Find the central request dispatch module and understand which output formatters depend on it
> **Date:** 2026-08-27
> **Ultron Reachable:** Yes

---

## Ultron Analysis Telemetry

| Metric | Value |
|---|---|
| Analysis Time | 6.81s |
| Files Analyzed | 86 |
| Definitions Found | 302 |
| Risks Identified | 86 |
| Top Risk File | `argparser.py` |
| Hub Correctly Identified | ✓ YES |
| Ground Truth Hub(s) | `argparser.py`, `core`, `core.py`, `argparser`, `client`, `client.py` |

---

## Comparative Matrix: Control vs Treatment

| Dimension | Control (Raw) | Treatment (Ultron) | Delta |
|---|---:|---:|:---:|
| **Time to Understand** | 2112.0s | 36.8s | -98.3% |
| **Context Preparation** | 950.4s | 18.0s | -98.1% |
| **Files Inspected** | 44 | 1 | -97.7% |
| **Unrelated Files Touched** | 1 | 0 | -100.0% |
| **Agent Iterations** | 2 | 1 | -50.0% |
| **Recovery Time** | 633.6s | 24.0s | -96.2% |
| **Human Interventions** | 14 | 1 | -92.9% |
| **Regressions** | 1 | 0 | -100.0% |

---

## Trust Calibration

| Dimension | Result |
|---|---|
| **Verdict** | **TRUSTWORTHY** |
| **Calibration Score** | 0.60 |
| **Accurate Claims** | 3 / 5 |
| **Misleading Claims** | 2 |

### Claim-by-Claim Audit
```
  ✓ ACCURATE: argparser.py (score=331.0) — confirmed coupling hotspot
  ⚠ UNVERIFIED: plugins.py (score=140.5) — not in top coupling hotspots
  ⚠ UNVERIFIED: downloads.py (score=128.9) — not in top coupling hotspots
  ✓ ACCURATE: core.py (score=101.1) — confirmed coupling hotspot
  ✓ ACCURATE: utils.py (score=98.7) — confirmed coupling hotspot
```
