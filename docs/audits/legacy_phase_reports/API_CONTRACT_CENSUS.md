# Ultron v2.7.1 — API Contract Census & Endpoint Authority Matrix

## 1. Executive Summary

This census maps all active backend REST API routes exposed by `ultron.interfaces.server` and `ultron.interfaces.api.routes.*` against the frontend callers in `ultron.interfaces.web`.

---

## 2. Active REST Route Census (Frontend Consumed)

| HTTP Method | Endpoint URI | Backend Handler | Request Payload | Response Schema | Frontend Caller |
|---|---|---|---|---|---|
| `GET` | `/api/v1/health` | `handle_v1_health` | Query params | `{"status": "ok", "version": "..."}` | Heartbeat badge |
| `POST` | `/api/v1/analyze` | `handle_v1_analyze` | `{"repo": str, "force": bool}` | `UnifiedAnalysisProjection` (v2.6.4) | `btn-load-repo` |
| `GET` | `/api/v1/progress` | `handle_v1_progress` | Query params | `{"status": str, "progress_pct": int, ...}` | Progress polling loop |
| `POST` | `/api/v1/cancel-analysis` | `handle_v1_cancel_analysis` | `{}` | `{"status": "cancelled"}` | `btn-cancel-analysis` |
| `GET` | `/api/v1/recommendations` | `handle_v1_recommendations` | `limit=20` | `{"recommendations": [...]}` | `btn-refresh-recs` |
| `GET` | `/api/v1/hotspots` | `handle_v1_hotspots` | `limit=10` | `{"hotspots": [...]}` | Overview Risk Table |
| `GET` | `/api/v1/objective` | `handle_v1_get_objective` | `repo=...` | `{"objective": {...}}` | Work & Plan tab |
| `POST` | `/api/v1/objective/task/complete` | `handle_v1_complete_task` | `{"repo": str, "task_id": str}` | `{"success": true, "objective": {...}}` | Task checkbox |
| `POST` | `/api/v1/objective/task/add` | `handle_v1_add_task` | `{"repo": str, "title": str}` | `{"success": true, "task": {...}}` | `btn-add-custom-task` |
| `POST` | `/api/v1/agent/context` | `handle_v1_agent_context_builder` | `{"repo": str, "provider": str}` | `{"provider": str, "context": str}` | Agent Context tab |
| `POST` | `/api/v1/safety/evaluate` | `handle_v1_safety_evaluate` | `{"repo": str, "test_results": {...}}` | `ContinuationReadinessReport` | Readiness Gate |
| `POST` | `/api/v1/workspace/watcher/scan` | `handle_v1_workspace_watcher_scan` | `{"repo": str}` | `{"success": true, "data": {...}}` | `btn-watch-mode-toggle` |
| `POST` | `/api/v1/run-tests` | `handle_run_tests` | `{"repo": str}` | `{"passed": bool, "summary": str}` | `btn-run-tests` |
| `POST` | `/api/v1/audit` | `handle_audit` | `{"repo": str, "code": str}` | `{"anomalies": [...]}` | `btn-run-audit` |
| `POST` | `/api/v1/calibrate` | `handle_calibrate` | `{"repo": str}` | `{"weights": {...}}` | `btn-calibrate` |
| `POST` | `/api/v1/save-file` | `handle_save_file` | `{"repo": str, "file": str, "content": str}` | `{"success": true}` | `btn-save-file` |
| `POST` | `/api/browse-folder` | `handle_browse_folder` | `{"initial_dir": str}` | `{"path": str, "cancelled": bool}` | `btn-browse-folder` |
| `POST` | `/api/v1/generate` | `handle_generate` | `{"repo": str, "intent": str}` | `{"prompt": str}` | `btn-generate-prompt` |
| `POST` | `/api/v1/ai/push` | `handle_v1_ai_push` | `{"repo": str, "target_file": str, ...}` | `{"translation": str}` | Persona Translation |
| `POST` | `/api/v1/export-brief` | `handle_v1_export_brief` | `{"format": str}` | `{"brief": str}` | `btn-copy-context-brief` |

---

## 3. Server Route Coverage & Contract Discrepancies

- **Unregistered Routes Identified in Audit**: 0
- **Broken Handlers**: 0
- **Payload Schema Drift**: 0 (all handlers conform to Unified JSON Envelopes).
