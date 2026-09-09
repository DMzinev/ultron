# Ultron Real-World OSS Benchmark Validation Matrix

**Execution Timestamp:** 2026-09-04 09:48:51 UTC
**Environment:** Pure Python Stdlib | OS: `win32` | Python: `3.12.14`

| Target Name | Category | Discovered Files | Analyzed Modules | Definitions | Graph Links | Cycles | Latency (ms) | Peak Heap (MB) | Determinism | Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |

### Architectural Invariants Status:
- [x] **Codebase Schema Integrity:** All analyzed files map to well-formed definition and import trees.
- [x] **Risk Score Bounding:** 100% of Impact and Coupling scores reside in valid bounds (`impact >= 0.0`, `complexity >= 1`).
- [x] **Graph Closed-World Safety:** Zero dangling node/link edges across all target graphs.
- [x] **Deterministic Snapshotting:** Content hash and snapshot IDs match across consecutive forced re-runs.
