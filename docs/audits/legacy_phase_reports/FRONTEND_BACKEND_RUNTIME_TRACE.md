# Ultron Frontend <-> Backend Runtime Trace

**Execution Timestamp**: 2026-08-20T17:24:45+0300
**Principle**: `VALID DATA > EXPLICIT DEGRADED/UNKNOWN > STALE DATA` (Zero silent zeroing of unexecuted metrics)

---

## Runtime Pipeline Trace Matrix

| Endpoint | End-to-End Pipeline Stage | Key Payload Fields / Invariants | Verification |
| :--- | :--- | :--- | :---: |
| `POST /api/v1/analyze` | **Analysis Payload -> StateStore** | `Snapshot: 0d09d8d4a80a88ce, AI Status: OFFLINE, Files: 132` | **PASSED** |
| `GET /api/v1/graph` | **Topology -> graph.js D3 Renderer** | `Nodes: 1377, Links: 3591, Sample: reality_audit.py` | **PASSED** |
| `GET /api/v1/recommendations` | **RKM Policy Engine -> UI Cards** | `Source: rkm_db, Count: 5` | **PASSED** |
| `POST /api/v1/agent/context` | **Mission Compiler -> Agent Prompt View** | `Prompt Length: 9102 chars` | **PASSED** |
| `POST /api/v1/safety/evaluate` | **Verify Gate -> Continue Action** | `Decision: CONTINUE, Status: None` | **PASSED** |

---

## Request Sequence & Concurrency Isolation
- `analysis:*`: Manual / explicit repository scan sequence namespace.
- `progress:*`: Real-time job polling namespace (100ms interval during scan, idle otherwise).
- `watcher:*`: Background filesystem delta scan namespace (never discards active scan envelopes).
- `context:*`: Agent instruction compiler and mission validity validation.
- `safety:*`: Checkpoint authorization and continuation readiness gating.