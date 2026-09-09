# Frontend-Backend Contract Matrix (Phase 0.5 Step 3: Pillar 2 Data Connectivity & Provenance)

**Evaluation Date:** 2026-08-20  
**Invariant:** **100% of primary factual UI data must have a traceable provenance path back to authoritative backend state with verified snapshot freshness.**  
**Status:** **7 / 7 Primary UI Facts Traceably Connected (100% PASS)**

---

## 1. End-to-End Field Lifecycle & Provenance Table

| Fact ID & UI Metric | Backend Source & Calculation | API Endpoint & Response Key | StateStore Path | UI Renderer & Event Target | DOM Element Binding | Provenance & Freshness Lifecycle | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **FACT-01: Health Score** | `scoring.py -> calculate_health_score()` | `POST /api/v1/analyze` $\rightarrow$ `overall_health_score` | `stateStore.lastAnalysisData.overall_health_score` | `modules/ui.js -> updateDashboard()` | `#overall-health-score` | **Provenance:** AST complexity + coupling + fix rate. **Freshness:** `snapshot_id` & `generated_at`. | **CONNECTED** |
| **FACT-02: Hotspots Table** | `scoring.py -> evaluate_risks()` | `POST /api/v1/analyze` $\rightarrow$ `risks[]` | `stateStore.lastAnalysisData.risks` | `modules/ui.js -> renderRiskTable()` | `#table-hotspots tbody, #risk-tbody` | **Provenance:** `AnalysisPacket` (`file_path`, `complexity`, `coupling`, `strategy`). **Freshness:** Active scan sync. | **CONNECTED** |
| **FACT-03: Topology Graph** | `analyzer.py -> build_dependency_graph()` | `POST /api/v1/analyze` $\rightarrow$ `dependency_graph` | `stateStore.lastAnalysisData.dependency_graph` | `modules/graph.js -> GraphView.render()` | `#graph-viewport (SVG)` | **Provenance:** AST imports and call references. **Freshness:** SQLite RKM snapshot hash. | **CONNECTED** |
| **FACT-04: Objective & Tasks** | `objective_tracker.py -> get_objective()` | `GET /api/v1/objective` $\rightarrow$ `data` | `stateStore.lastAnalysisData.objective` | `modules/ui.js -> renderObjectiveState()` | `#work-tasks-list, #overview-objective-title` | **Provenance:** `.ultron/objective.json`. **Freshness:** Atomic `updated_at` ISO string. | **CONNECTED** |
| **FACT-05: AI Critique** | `ai/client.py -> query_critique()` | `POST /api/v1/ai/critique` $\rightarrow$ `critique` | Transient node drawer state | `modules/graph.js -> renderNodeDrawer()` | `#drawer-ai-content` | **Provenance:** Local OpenAI proxy (port 10531) / Native AST synthesis. **Freshness:** On-demand per click. | **CONNECTED** |
| **FACT-06: Continuation Badge**| `safety_evaluator.py -> evaluate()` | `POST /api/v1/safety/evaluate` $\rightarrow$ `report` | `stateStore.lastAnalysisData.safetyReport` | `modules/ui.js -> renderSafetyReport()` | `#continuation-readiness-badge, #safety-checks-list` | **Provenance:** Multi-check evaluator over tests, diffs, cycles. **Freshness:** `checked_at` timestamp. | **CONNECTED** |
| **FACT-07: Agent Prompt** | `agent_context_builder.py -> build()` | `POST /api/v1/agent/context` $\rightarrow$ `prompt` | Transient prompt renderer state | `index.js -> updatePromptDisplay()` | `#prompt-display` | **Provenance:** Mission Envelope combining `ObjectiveState` + AST facts. **Freshness:** Header `generated_at`. | **CONNECTED** |

---

## 2. Field Name Consistency Audit

* **Snake_case vs CamelCase Consistency:** Confirmed that all backend JSON payloads use standard `snake_case` keys (`overall_health_score`, `dependency_graph`, `progress_pct`, `safe_to_continue`) and that frontend adapters correctly deserialize them into `StateStore` without dropping attributes.
* **Zero Choking Fallbacks:** Verified that when optional fields are null or empty, the frontend renders informative empty states ("No high-risk hotspots detected", "Test suite not yet executed") rather than choking or breaking the DOM layout.
