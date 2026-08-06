-- depends_on: 004_constraint_violations.sql

CREATE TABLE rkm_entity_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('file', 'symbol')),
    entity_identifier TEXT NOT NULL,
    analysis_run_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('added', 'modified', 'removed')),
    signature TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (analysis_run_id) REFERENCES rkm_analysis_runs(id) ON DELETE CASCADE,
    CONSTRAINT unique_entity_history UNIQUE (analysis_run_id, entity_type, entity_identifier)
);

UPDATE rkm_manifest SET schema_version = '1.3.0', minimum_reader_version = '1.3.0' WHERE id = 1;
