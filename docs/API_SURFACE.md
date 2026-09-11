# Ultron API Surface — Route Decision Table & Active Contract

**Single Source of Truth**: `docs/AGENT_EXECUTION_PLAN.md` (Task A4)  
**Invariant**: *Every retained route has an explicit named consumer — UI, CLI, MCP, or Test.*

---

## 1. Summary of Decisions

- **Initial Baseline Surface**: 43 endpoints
- **Legacy Web Assets Purged**: `legacy.html`, `legacy.css`, `legacy.js` (~2,900 lines removed)
- **Classified as DELETED**: 12 endpoints (orphan endpoints from retired legacy tabs with 0 consumers)
- **Classified as KEPT / ACTIVE**: 31 endpoints (all with verified, named consumers)

---

## 2. API Surface Decision Table (All 43 Endpoints)

| # | HTTP Method & Route | Handler | Decision | Consumer Category | Named Consumer(s) | Rationale |
|:---|:---|:---|:---|:---|:---|:---|
| 1 | `GET /api/analyze` | `handle_analyze` | **KEEP** | Test | `test_ai_handoff.py`, `test_chaos_recovery.py`, `test_kanban_release_stability.py` | Headless analysis triggering verification |
| 2 | `GET /api/architecture-health` | `handle_architecture_health` | **KEEP** | UI / Test | `index.js`, `run_tests.py` | Core pillar health score retrieval |
| 3 | `GET /api/audit` | `handle_audit` | **KEEP** | UI / Test | `index.js`, `run_academic_tests.py` | Identifier anomaly and audit scans |
| 4 | `GET /api/dependency-graph` | `handle_dependency_graph` | **KEEP** | UI / Test | `index.js`, `test_route_contract.py` | Architecture graph visualization pillar |
| 5 | `GET /api/file-tree` | `handle_file_tree` | **KEEP** | Test | `run_tests.py` | File system hierarchy and node traversal |
| 6 | `GET /api/get-repo-root` | `handle_get_repo_root` | **KEEP** | UI | `index.js`, `folder_picker.html` | Repository root detection & UI workspace header |
| 7 | `GET /api/list-dirs` | `handle_list_dirs` | **KEEP** | UI | `index.js` | Folder picker directory navigation |
| 8 | `GET /api/report` | `handle_report` | **KEEP** | Test | `run_academic_tests.py` | Pledge and calibration reporting engine |
| 9 | `GET /api/v1/decision` | `handle_v1_decision` | **DELETE** | None | None | Orphan endpoint from legacy prototype; superseded by overview |
| 10 | `GET /api/v1/health` | `handle_v1_health` | **KEEP** | UI / Test | `index.js`, `test_environment_health.py`, `test_server_dashboard_endpoints.py` | Server & RKM database liveness probes |
| 11 | `GET /api/v1/history` | `handle_v1_history` | **DELETE** | None | None | Orphan endpoint from legacy history tab; superseded by overview |
| 12 | `GET /api/v1/hotspots` | `handle_v1_hotspots` | **DELETE** | None | None | Orphan endpoint from legacy prototype; superseded by `/api/v1/overview` |
| 13 | `GET /api/v1/progress` | `handle_v1_progress` | **KEEP** | UI | `index.js` | Real-time analysis scan progress polling |
| 14 | `GET /api/v1/recommendations` | `handle_v1_recommendations` | **KEEP** | Test | `test_server_dashboard_endpoints.py`, `test_chaos_recovery.py` | Refactoring recommendation engine |
| 15 | `GET /api/v1/risk-profile` | `handle_v1_risk_profile` | **DELETE** | None | None | Orphan endpoint from legacy prototype; superseded by overview |
| 16 | `GET /api/v1/runs` | `handle_v1_runs` | **DELETE** | None | None | Orphan endpoint from legacy prototype; superseded by overview |
| 17 | `GET /api/v1/summary` | `handle_v1_summary` | **KEEP** | Test | `test_auditor_defect_sensitivity.py`, `test_server_dashboard_endpoints.py` | High-level analysis summary contract |
| 18 | `POST /api/analyze` | `handle_analyze` | **KEEP** | Test | `test_ai_handoff.py`, `test_chaos_recovery.py`, `test_quality_gates.py` | Backward-compatible POST analysis trigger |
| 19 | `POST /api/architecture-health` | `handle_architecture_health` | **KEEP** | UI / Test | `index.js`, `run_tests.py` | Pillar health score evaluation for target repo |
| 20 | `POST /api/audit` | `handle_audit` | **KEEP** | UI / Test | `index.js`, `run_academic_tests.py` | Target file anomaly and governance audit |
| 21 | `POST /api/calibrate` | `handle_calibrate` | **DELETE** | None | None | Orphan endpoint from deleted `legacy.html` calibration tab |
| 22 | `POST /api/config` | `handle_config` | **KEEP** | UI | `folder_picker.html` (via `/api/set-repo-root`) | Workspace configuration & repository path selection |
| 23 | `POST /api/dependency-graph` | `handle_dependency_graph` | **KEEP** | UI | `index.js` | Interactive topology explorer graph data |
| 24 | `POST /api/diff-risk` | `handle_diff_risk` | **DELETE** | None | None | Orphan endpoint from deleted `legacy.html` diff tab |
| 25 | `POST /api/file-tree` | `handle_file_tree` | **KEEP** | Test | `run_tests.py` | POST file hierarchy retrieval |
| 26 | `POST /api/generate` | `handle_generate` | **KEEP** | UI | `index.js` | AI Context prompt generation |
| 27 | `POST /api/get-file` | `handle_get_file` | **KEEP** | UI / Test | `index.js`, `run_tests.py` | File viewer and side inspector drawer content |
| 28 | `POST /api/log-risk-feedback` | `handle_log_risk_feedback` | **KEEP** | Test | `run_academic_tests.py` | Human feedback logging for calibration |
| 29 | `POST /api/playground` | `handle_playground` | **KEEP** | Test | `run_academic_tests.py` | Code snippet analysis sandbox |
| 30 | `POST /api/pledge/create` | `handle_pledge_create` | **KEEP** | Test | `run_academic_tests.py` | Architectural pledge creation |
| 31 | `POST /api/pledge/verify` | `handle_pledge_verify` | **KEEP** | Test | `run_academic_tests.py` | Architectural pledge compliance verification |
| 32 | `POST /api/predict-impact` | `handle_predict_impact` | **DELETE** | None | None | Orphan endpoint from deleted `legacy.html` impact prediction tab |
| 33 | `POST /api/run-tests` | `handle_run_tests` | **DELETE** | None | None | Orphan endpoint from deleted `legacy.html` test launcher |
| 34 | `POST /api/save-file` | `handle_save_file` | **KEEP** | Test | `run_tests.py` | In-browser file save and modification |
| 35 | `POST /api/save-session` | `handle_save_session` | **DELETE** | None | None | Orphan endpoint from deleted `legacy.html` session exporter |
| 36 | `POST /api/v1/ai/critique` | `handle_v1_ai_critique` | **KEEP** | UI | `modules/graph.js` | Graph node AI architectural critique |
| 37 | `POST /api/v1/analyze` | `handle_v1_analyze` | **KEEP** | UI / Test | `index.js`, `test_fault_injection.py`, `test_fuzzing.py` | Primary async repository analysis pipeline |
| 38 | `POST /api/v1/cancel-analysis` | `handle_v1_cancel_analysis` | **KEEP** | Test | `test_visual_ergonomics.py` | Analysis cancellation signal handler |
| 39 | `POST /api/v1/compare` | `handle_v1_compare` | **DELETE** | None | None | Orphan endpoint from deleted `legacy.html` run comparator |
| 40 | `POST /api/v1/context-brief` | `handle_v1_context_brief` | **KEEP** | UI / Test | `index.js`, `test_ai_handoff.py`, `test_quality_gates.py` | Bounded mission envelope AI context generation |
| 41 | `POST /api/v1/explain-violation` | `handle_v1_explain_violation` | **DELETE** | None | None | Orphan endpoint; MCP and CLI consume `translate` module directly |
| 42 | `POST /api/v1/export-brief` | `handle_v1_export_brief` | **KEEP** | Test | `test_server_dashboard_endpoints.py`, `test_fuzzing.py` | Exporting brief in markdown and JSON format |
| 43 | `POST /api/v1/overview` | `handle_v1_overview` | **KEEP** | UI | `index.js` | Unified dashboard data endpoint (four pillars) |

---

## 3. Retained Active Surface Breakdown (31 Endpoints)

### UI-Referenced Endpoints (16 endpoints)
- `GET /api/v1/health`
- `GET /api/v1/progress`
- `GET /api/get-repo-root`
- `GET /api/list-dirs`
- `GET /api/architecture-health` (fallback)
- `GET /api/dependency-graph` (fallback)
- `POST /api/v1/overview`
- `POST /api/v1/analyze`
- `POST /api/architecture-health`
- `POST /api/dependency-graph`
- `POST /api/get-file`
- `POST /api/v1/context-brief`
- `POST /api/generate`
- `POST /api/audit`
- `POST /api/config` (invoked via `/api/set-repo-root`)
- `POST /api/v1/ai/critique`

### Test-Referenced Endpoints (15 endpoints)
- `GET /api/analyze`
- `GET /api/audit`
- `GET /api/file-tree`
- `GET /api/report`
- `GET /api/v1/recommendations`
- `GET /api/v1/summary`
- `POST /api/analyze`
- `POST /api/file-tree`
- `POST /api/log-risk-feedback`
- `POST /api/playground`
- `POST /api/pledge/create`
- `POST /api/pledge/verify`
- `POST /api/save-file`
- `POST /api/v1/cancel-analysis`
- `POST /api/v1/export-brief`

---

## 4. Path-Safety & Boundary Defense Policy (Task P3-E1)

All filesystem-touching endpoints enforce a **Fail-Closed Strict Rejection** policy. Invalid or adversarial paths are explicitly rejected with HTTP 400 — they are never silently clamped or normalized to a fallback.

### Defense Layers

| Layer | Threat | Response |
|:---|:---|:---|
| **Null-byte injection** | `\0` in any path parameter | HTTP 400 `"Invalid path: null byte detected."` |
| **Directory traversal** | `../../../` escaping repo boundary | HTTP 400 via `realpath` + `startswith` containment |
| **Root filesystem scan** | Targeting `/` or `C:\` | HTTP 400 `"Analyzing system root filesystem is strictly prohibited."` |
| **Symlink escape** | Symlink resolving outside repo | HTTP 400 via `os.path.realpath()` boundary check |
| **Windows reserved devices** | `CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9` | HTTP 400 `"Invalid path: reserved device name."` |

### Covered Endpoints

- `GET /api/list-dirs` — null-byte guard, device name guard
- `POST /api/browse-folder` — null-byte guard, device name guard, `allowed_root` boundary
- `POST /api/get-file` — null-byte guard, `realpath` + `startswith` containment
- `POST /api/save-file` — null-byte guard, `realpath` + `startswith` containment
- `POST /api/analyze` — null-byte guard, root filesystem prohibition
- `POST /api/v1/analyze` — null-byte guard, device name guard, root filesystem prohibition
