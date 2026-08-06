# Ultron Observation Data Pipeline Architecture

This document defines the core data pipeline architecture for **Ultron Platform v1.4.0**, shifting the center of gravity from specialized engines to a **unified scientific observation pipeline** and a **multi-audience plain-language translator**.

---

## 1. Pipeline Layer Architecture

`	ext
               Repository
                    │
        ────────────┼────────────
                    │
             Discovery Layer (Layer 1)
                    │
             Data Collectors (Layer 2)
                    │
             Data Validators (Layer 3)
                    │
            Observation Model (Layer 4)
                    │
                SQLite RKM
                    │
       ┌────────────┼────────────┐
       │            │            │
  Rule Engine  History Engine Graph Engine (Layer 5)
       │            │            │
       └────────────┼────────────┘
                    │
            Interpretation Layer (Layer 6)
                    │
           Plain Language Layer (4 Tiers)
                    │
             API / Dashboard / CLI
                    │
                Human / AI
`

---

## 2. Unified Observation Schema

All facts collected by Layer 2 and validated by Layer 3 are normalized into a single Observation dataclass before persisting into SQLite RKM:

`python
@dataclass
class Observation:
    id: Optional[int]
    entity_type: str        # 'file', 'symbol', 'repository', 'package'
    entity_identifier: str  # 'ultron/interfaces/server.py'
    property_name: str      # 'mccabe_complexity', 'coupling_fan_out', 'layer_type'
    property_value: str     # '19', '12', 'interface'
    value_type: str         # 'int', 'float', 'string', 'bool'
    unit: str               # 'branches', 'count', 'ratio'
    confidence: float       # 1.0 = AST parsed, 0.7 = heuristic match
    source_collector: str   # 'radon_ast', 'ast_import_visitor'
    validator_status: str   # 'PASSED', 'WARNING', 'UNVERIFIED'
    timestamp: str          # ISO-8601 UTC string
`

---

## 3. The 4-Tier Audience Translation Matrix

| Tier | Target Audience | Focus Area | Example Output for McCabe Complexity: 18 |
| :--- | :--- | :--- | :--- |
| **Tier 1** | **Raw Metrics** | Numerical measurement | Cyclomatic Complexity: 18 |
| **Tier 2** | **Developer** | Technical impact & unit test effort | High decision branching. Testing effort and edge-case bug risks increase significantly. |
| **Tier 3** | **Engineering Manager** | Maintenance velocity & regression risk | Module maintenance effort is rising. Future changes carry a high probability of regression. |
| **Tier 4** | **Founder / Executive** | Business cost & feature delivery speed | Accumulated complexity in core routing will slow down new feature delivery and increase maintenance overhead. |

---

## 4. Storage Responsibility Matrix

| Data Type | Target Storage | Rationale |
| :--- | :--- | :--- |
| **Repository Metadata** | SQLite (.ultron/repository.db) | Transactional relational query source of truth |
| **Observations & Facts** | SQLite (
km_observations) | Indexed relational observations table |
| **Graph Edges / Lineage** | SQLite (
km_dependencies) | Relational dependency graph |
| **Constraint Rules** | JSON (
ules.json) | Human-editable declarative rule definitions |
| **System Settings** | JSON (settings.json) | User-configurable runtime defaults |
| **Dashboard Layout** | JSON (preferences.json) | UI configuration state |
| **Portable Export** | JSON (snapshot.json) | Interchange format for sharing repository state |
| **Event Telemetry** | JSONL (udit_telemetry.jsonl) | Append-only event log |
