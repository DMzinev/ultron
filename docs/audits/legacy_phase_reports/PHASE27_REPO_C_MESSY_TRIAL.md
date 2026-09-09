# Phase 2.7 — External Reality Trial: Repo C

> **Repository:** `Repo C: requests (Python HTTP Library)`
> **Path:** `c:\Users\dimmiz\Desktop\cost accounting\scratch\external\repo_c_requests`
> **Task Intent:** Identify the central session/request dispatch module and understand how models, adapters, and auth modules couple together
> **Date:** 2026-08-27
> **Ultron Reachable:** Yes

---

## Ultron Analysis Telemetry

| Metric | Value |
|---|---|
| Analysis Time | 2.28s |
| Files Analyzed | 20 |
| Definitions Found | 126 |
| Risks Identified | 20 |
| Top Risk File | `models.py` |
| Hub Correctly Identified | ✓ YES |
| Ground Truth Hub(s) | `models.py`, `models`, `adapters.py`, `adapters`, `sessions.py`, `sessions` |

---

## Comparative Matrix: Control vs Treatment

| Dimension | Control (Raw) | Treatment (Ultron) | Delta |
|---|---:|---:|:---:|
| **Time to Understand** | 528.0s | 32.3s | -93.9% |
| **Context Preparation** | 237.6s | 18.0s | -92.4% |
| **Files Inspected** | 11 | 1 | -90.9% |
| **Unrelated Files Touched** | 1 | 0 | -100.0% |
| **Agent Iterations** | 2 | 1 | -50.0% |
| **Recovery Time** | 158.4s | 24.0s | -84.8% |
| **Human Interventions** | 3 | 1 | -66.7% |
| **Regressions** | 1 | 0 | -100.0% |

---

## Trust Calibration

| Dimension | Result |
|---|---|
| **Verdict** | **TRUSTWORTHY** |
| **Calibration Score** | 0.80 |
| **Accurate Claims** | 4 / 5 |
| **Misleading Claims** | 1 |

### Claim-by-Claim Audit
```
  ✓ ACCURATE: models.py (score=366.1) — confirmed coupling hotspot
  ✓ ACCURATE: utils.py (score=337.2) — confirmed coupling hotspot
  ✓ ACCURATE: sessions.py (score=194.4) — confirmed coupling hotspot
  ⚠ UNVERIFIED: cookies.py (score=183.1) — not in top coupling hotspots
  ✓ ACCURATE: adapters.py (score=132.1) — confirmed coupling hotspot
```
