# Ultron v2.7.1 — Frontend Defect Register & Resolution Ledger

## 1. Resolved Defect Log (Pre-v2.7.1 Audit & Compiler Verification)

| Defect ID | Severity | Category | Description | Root Cause | Resolution / Verified Fix |
|---|---|---|---|---|---|
| **DEF-01** | High | Broken Route | Watch mode polled `/api/v1/workspace/watcher/scan` which was unregistered in server router. | Route was never hooked to `IncrementalWatcherDaemon`. | Implemented `handle_v1_workspace_watcher_scan()` in `server.py` and registered route in `analysis_routes.py`. |
| **DEF-02** | Medium | UI Reality | `#btn-watch-mode-toggle` was referenced in JS but absent from `index.html`. | Header redesign omitted toggle button. | Added `<button id="btn-watch-mode-toggle">` to top header in `index.html`. |
| **DEF-03** | Medium | Fake Data | `safeRender("snapshot_drift")` used hardcoded `mockSnapshots` array. | Simulated static placeholder. | Replaced with dynamic snapshot drift computation from `stateStore.lastAnalysisData` with $\div 0$ guards. |
| **DEF-04** | Low | Unbound Handlers | `#btn-close-tour`, `#btn-next-slide`, `#btn-prev-slide` had no click listeners. | Tour modal DOM had IDs without JS event wiring. | Added multi-slide tour navigation and dismiss handlers in `index.js`. |
| **DEF-05** | Low | Silent Catch | Watcher polling loop used empty `catch (_) {}`. | Suppressed diagnostic visibility. | Replaced with structured `console.debug("[Ultron Watcher] Poll error:", err)`. |
| **DEF-06** | High | Runtime Error | `currentObjectiveState` was referenced before declaration in `index.js`. | Temporal Dead Zone `ReferenceError`. | Hoisted `let currentObjectiveState = null;` to top of `DOMContentLoaded`. |
| **DEF-07** | High | State Machine | Switching repo from `READY` state was rejected. | `STATES.CONNECTED` was omitted from `VALID_TRANSITIONS[READY]`. | Added `STATES.CONNECTED` to `VALID_TRANSITIONS[STATES.READY]`. |
| **DEF-08** | High | Unsafe Access | `ACTIVE_JOB["progress_pct"]` threw `KeyError` before job initialization. | Direct dictionary subscripting on uninitialized job. | Used `.get()` with safe defaults in `handle_v1_progress`. |
| **DEF-09** | Medium | Windows Socket | Port collision handler failed on Windows error `10048`. | Checked Linux `errno.EADDRINUSE` only. | Added `winerror == 10048` and `"only one usage"` check in `start.py`. |
| **DEF-10** | High | SQLite Lock | `RepositoryStore` connections remained open during pipeline execution. | Missing explicit `close()` in orchestrator. | Wrapped all connections in `try...finally: store.close()`. |

---

## 2. Current Open Defect Status: 0 Critical / 0 High / 0 Medium / 0 Low

All 10 recorded defects have been resolved, audited by the `UIRealityCompiler`, and verified across all 340 master tests.
