# Phase 2.7 — Trust Calibration Audit

> **Core Question:** Did the developer correctly understand what Ultron was telling them?
> A fast wrong answer is worse than a slow right one.

## Repo A: Repo A: bottle (Python Micro-Framework)

- **Verdict:** PARTIALLY_TRUSTWORTHY
- **Calibration Score:** 0.40
- **Accurate Claims:** 2 / 5
- **Hub Correctly Identified:** ✓
- **Top Risk File:** `bottle.py`

### Claim Details
```
  ✓ ACCURATE: bottle.py (score=2415.2) — confirmed coupling hotspot
  ✓ ACCURATE: tools.py (score=71.6) — confirmed coupling hotspot
  ⚠ UNVERIFIED: test_environ.py (score=49.5) — not in top coupling hotspots
  ⚠ UNVERIFIED: test_multipart.py (score=46.8) — not in top coupling hotspots
  ⚠ UNVERIFIED: test_wsgi.py (score=36.4) — not in top coupling hotspots
```

---

## Repo B: Repo B: httpie (Python CLI Application)

- **Verdict:** TRUSTWORTHY
- **Calibration Score:** 0.60
- **Accurate Claims:** 3 / 5
- **Hub Correctly Identified:** ✓
- **Top Risk File:** `argparser.py`

### Claim Details
```
  ✓ ACCURATE: argparser.py (score=331.0) — confirmed coupling hotspot
  ⚠ UNVERIFIED: plugins.py (score=140.5) — not in top coupling hotspots
  ⚠ UNVERIFIED: downloads.py (score=128.9) — not in top coupling hotspots
  ✓ ACCURATE: core.py (score=101.1) — confirmed coupling hotspot
  ✓ ACCURATE: utils.py (score=98.7) — confirmed coupling hotspot
```

---

## Repo C: Repo C: requests (Python HTTP Library)

- **Verdict:** TRUSTWORTHY
- **Calibration Score:** 0.80
- **Accurate Claims:** 4 / 5
- **Hub Correctly Identified:** ✓
- **Top Risk File:** `models.py`

### Claim Details
```
  ✓ ACCURATE: models.py (score=366.1) — confirmed coupling hotspot
  ✓ ACCURATE: utils.py (score=337.2) — confirmed coupling hotspot
  ✓ ACCURATE: sessions.py (score=194.4) — confirmed coupling hotspot
  ⚠ UNVERIFIED: cookies.py (score=183.1) — not in top coupling hotspots
  ✓ ACCURATE: adapters.py (score=132.1) — confirmed coupling hotspot
```

---

