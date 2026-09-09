# Ultron Real-World OSS Benchmark Validation Matrix

**Execution Timestamp:** 2026-09-09 12:53:55 UTC
**Environment:** Pure Python Stdlib | OS: `win32` | Python: `3.12.14`

| Target Name | Category | Discovered Files | Analyzed Modules | Definitions | Graph Links | Cycles | Latency (ms) | Peak Heap (MB) | Determinism | Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ultron Self (Dogfood)** | Real OSS Core | 293 | 134 | 883 | 3509 | 37 | 11612.06 | 9.60 | PASS | PASS |
| **Small OSS CLI Utility** | Synthetic Archetype (~50 files) | 55 | 55 | 200 | 350 | 1 | 1176.79 | 0.49 | PASS | PASS |
| **Medium Layered Service App** | Synthetic Archetype (~300 files) | 315 | 315 | 900 | 1480 | 0 | 5740.40 | 2.15 | PASS | PASS |
| **Large Scale Monorepo** | Synthetic Archetype (~1k files) | 930 | 930 | 900 | 900 | 0 | 11672.76 | 4.88 | PASS | PASS |

### Architectural Invariants Status:
- [x] **Codebase Schema Integrity:** All analyzed files map to well-formed definition and import trees.
- [x] **Risk Score Bounding:** 100% of Impact and Coupling scores reside in valid bounds (`impact >= 0.0`, `complexity >= 1`).
- [x] **Graph Closed-World Safety:** Zero dangling node/link edges across all target graphs.
- [x] **Deterministic Snapshotting:** Content hash and snapshot IDs match across consecutive forced re-runs.
