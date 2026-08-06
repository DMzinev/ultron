-- depends_on: 003_manifest_event_hardening.sql

-- 1. Create rkm_rules table
CREATE TABLE IF NOT EXISTS rkm_rules (
    id TEXT PRIMARY KEY,
    rule_pack_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    predicate_type TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0.0'
);

-- 2. Create rkm_rule_instances table
CREATE TABLE IF NOT EXISTS rkm_rule_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    severity TEXT NOT NULL DEFAULT 'warning',
    predicate_config TEXT NOT NULL, -- JSON string
    version TEXT NOT NULL DEFAULT '1.0.0',
    FOREIGN KEY (rule_id) REFERENCES rkm_rules (id) ON DELETE CASCADE
);

-- 3. Create rkm_evaluations table
CREATE TABLE IF NOT EXISTS rkm_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_run_id INTEGER NOT NULL,
    rule_id TEXT NOT NULL,
    status TEXT NOT NULL, -- 'PENDING', 'RUNNING', 'PASSED', 'FAILED', 'ERROR', 'SKIPPED'
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    engine_version TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    FOREIGN KEY (analysis_run_id) REFERENCES rkm_analysis_runs (id) ON DELETE CASCADE,
    FOREIGN KEY (rule_id) REFERENCES rkm_rules (id) ON DELETE CASCADE
);

-- 4. Create rkm_violations table
CREATE TABLE IF NOT EXISTS rkm_violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_id INTEGER NOT NULL,
    file_id INTEGER,
    symbol_id INTEGER,
    details TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evaluation_id) REFERENCES rkm_evaluations (id) ON DELETE CASCADE,
    FOREIGN KEY (file_id) REFERENCES rkm_files (id) ON DELETE CASCADE,
    FOREIGN KEY (symbol_id) REFERENCES rkm_symbols (id) ON DELETE CASCADE
);

-- 5. Create rkm_violation_evidence table
CREATE TABLE IF NOT EXISTS rkm_violation_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    violation_id INTEGER NOT NULL,
    evidence_type TEXT NOT NULL, -- 'fact', 'metric', 'dependency', etc.
    evidence_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (violation_id) REFERENCES rkm_violations (id) ON DELETE CASCADE
);

-- 6. Alter rkm_analysis_runs to add semantic_hash_strategy column
ALTER TABLE rkm_analysis_runs ADD COLUMN semantic_hash_strategy TEXT NOT NULL DEFAULT 'AST';
