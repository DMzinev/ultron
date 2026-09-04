# Untracked Files Inventory Classification (Task A2)

Generated for Task A2 (`agent/A2-reconcile-working-tree`) per `docs/AGENT_EXECUTION_PLAN.md`.

Classification buckets:
- **COMMIT**: Real source, tests, setup configs, or build scripts referenced in the codebase.
- **IGNORE**: Audit markdown reports, benchmark artifacts, scratch scripts, local dumps.
- **DELETE**: Fuzz test residue, invalid/path-traversal root filenames.

---

## 1. DELETE Bucket (Fuzz Residue & Path-Traversal Test Artifacts)

| Path | Bucket | Reason |
|:---|:---|:---|
| `%00` | **DELETE** | Null-byte path traversal test residue in repo root |
| `..%2F..%2Fetc%2Fpasswd` | **DELETE** | URL-encoded traversal test residue in repo root |
| `..%5c..%5c..%5cWindows%5cwin.ini` | **DELETE** | Windows traversal test residue in repo root |
| `aux` | **DELETE** | Windows reserved device name test residue |
| `con` | **DELETE** | Windows reserved device name test residue |
| `com1` | **DELETE** | Windows reserved device name test residue |
| `prn` | **DELETE** | Windows reserved device name test residue |

---

## 2. IGNORE Bucket (Generated Dumps, Audits, Benchmarks, Scratch)

| Path Pattern / File | Bucket | Reason |
|:---|:---|:---|
| `API_CONTRACT_CENSUS.md` | **IGNORE** | Generated API audit report |
| `BACKEND_FUNCTIONALITY_MATRIX.md` | **IGNORE** | Generated functionality audit report |
| `DOGFOODING_EXPERIMENT_LOG.md` | **IGNORE** | Generated local experiment session log |
| `FRONTEND_BACKEND_CONTRACT_MATRIX.md` | **IGNORE** | Generated UI/API matrix report |
| `FRONTEND_BACKEND_RUNTIME_TRACE.md` | **IGNORE** | Generated runtime trace report |
| `FRONTEND_CAPABILITY_MATRIX.json` | **IGNORE** | Generated capability dump |
| `FRONTEND_CAPABILITY_REALITY.json` | **IGNORE** | Generated capability dump |
| `FRONTEND_DEFECT_REGISTER.md` | **IGNORE** | Audit defect register |
| `FRONTEND_FUNCTIONALITY_AUDIT.md` | **IGNORE** | Audit markdown report |
| `GRAPH_VISUAL_REALITY_REPORT.md` | **IGNORE** | Audit visual report |
| `NEXT_FINDING_AUDIT.md` | **IGNORE** | Audit markdown report |
| `OSS_BENCHMARK_REPORT.md` | **IGNORE** | Generated benchmark run report |
| `P0_REPOSITORY_LOADING_REPORT.md` | **IGNORE** | Audit markdown report |
| `PHASE*.md` (all matching) | **IGNORE** | Ephemeral phase audit reports (PHASE0 to PHASE27) |
| `PHASE*.json` (all matching) | **IGNORE** | Ephemeral phase JSON audit data |
| `SEMANTIC_TRUTH_AUDIT.md` | **IGNORE** | Audit markdown report |
| `SYSTEM_RESPONSIBILITY_MAP.md` | **IGNORE** | Audit markdown report |
| `THREE_PILLAR_DEFECT_REGISTER.md` | **IGNORE** | Audit defect register |
| `UI_DELETION_LEDGER.md` | **IGNORE** | Audit markdown report |
| `UI_PRESENTATION_AUDIT.md` | **IGNORE** | Audit markdown report |
| `ULTRON_DOGFOOD_SESSION.md` | **IGNORE** | Local dogfooding session log |
| `ULTRON_PHASE_*.md` | **IGNORE** | Historical phase reports |
| `UX_FRICTION_LEDGER.md` | **IGNORE** | UX audit ledger |
| `benchmark_matrix.json` | **IGNORE** | Generated benchmark metrics |
| `live_api_census_results.json` | **IGNORE** | Ephemeral API census dump |
| `openai_model_feedback.md` | **IGNORE** | Local model feedback notes |
| `reality_audit.py` | **IGNORE** | One-off scratch audit script |
| `reality_audit_data.json` | **IGNORE** | Scratch audit data dump |
| `scratch_audit_results.json` | **IGNORE** | Scratch audit output |
| `scratch_live_audit.py` | **IGNORE** | One-off scratch test script |
| `release/three_pillars_adversarial_report.json` | **IGNORE** | Ephemeral release audit output |
| `ultron_report.md` | **IGNORE** | Generated scan report |
| `ultron/meta/dogfood_session.json` | **IGNORE** | Local session metadata |
| `ultron/meta/state_census.json` | **IGNORE** | Local state census dump |
| `uv.lock` | **IGNORE** | Ephemeral package lock |

---

## 3. COMMIT Bucket (Real Core Source, Tests, Build Configurations)

| Path | Bucket | Reason |
|:---|:---|:---|
| `MANIFEST.in` | **COMMIT** | Python packaging manifest |
| `setup.py` | **COMMIT** | Python setuptools installation script |
| `launcher.py` | **COMMIT** | Ultron application runner script |
| `docs/TASK_PROGRESS_TRACKER.md` | **COMMIT** | Progress and activity tracking ledger |
| `docs/UNTRACKED_INVENTORY.md` | **COMMIT** | Inventory classification ledger |
| `ultron/__main__.py` | **COMMIT** | Module execution entry point |
| `ultron/core/*.py` | **COMMIT** | Core analysis, pipeline, RKM, policy, verifier modules |
| `ultron/hooks/` | **COMMIT** | Workspace lifecycle hooks |
| `ultron/interfaces/api/routes/agent_routes.py` | **COMMIT** | Agent API route handlers |
| `ultron/interfaces/cli/commands/*.py` | **COMMIT** | Ultron CLI subcommands (ci, fix, gate, mcp) |
| `ultron/interfaces/web/modules/storage.js` | **COMMIT** | Web client local storage module |
| `ultron/release/version_manager.py` | **COMMIT** | Release versioning manager |
| `ultron/tests/test_*.py` | **COMMIT** | Validated test suites |
| `ultron/tests/run_academic_tests.py` | **COMMIT** | Academic test runner utility |
| `umags/budget_governor.py` | **COMMIT** | UMAGS budget governance |
| `umags/tools/` | **COMMIT** | UMAGS tooling modules |
